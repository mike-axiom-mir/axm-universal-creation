"""Execute the original Rivetwing authoring requests as a real dependency graph."""
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from sticker_assembly_proof import make
from axm_uc.parallel_create import build, SCHEMA
from axm_uc.game_pose_runtime import GamePoseAsset


def graph(requests):
    tasks = []
    for request in requests:
        dependencies = set()
        def convert(value):
            if isinstance(value, dict):
                if value.get('schema') == 'axm.sticker-instance/v1':
                    task = value['sticker']['id']; dependencies.add(task)
                    return {'$instance': {'task': task, 'id': value['id'],
                        'overrides': value['overrides'], 'placement': value['placement']}}
                return {k: convert(v) for k, v in value.items()}
            if isinstance(value, list): return [convert(v) for v in value]
            return value
        converted = convert(request)
        tasks.append({'id': request['id'], 'dependencies': sorted(dependencies), 'request': converted})
    return {'schema': SCHEMA, 'tasks': tasks, 'result': 'rivetwing'}


def main(destination):
    root = Path(destination); root.mkdir(parents=True, exist_ok=False)
    make(root / 'reference')
    plan = graph(json.loads((root / 'reference/create-requests.json').read_text()))
    (root / 'plan.json').write_text(json.dumps(plan, indent=2) + '\n')
    timings = {}; receipts = {}
    for name, workers in [('serial', 1), ('parallel', 4)]:
        start = time.perf_counter()
        receipts[name] = build(plan, root / name, workers=workers)
        timings[name] = time.perf_counter() - start
    expected = (root / 'reference/rivetwing.glb').read_bytes()
    assert expected == (root / 'serial/asset.glb').read_bytes() == (root / 'parallel/asset.glb').read_bytes()
    assert (root / 'serial/library.json').read_bytes() == (root / 'parallel/library.json').read_bytes()
    asset = GamePoseAsset(expected)
    assert asset.sample('AssemblyMotion', 0)['world_matrices'] == asset.sample('AssemblyMotion', 2)['world_matrices']
    assert asset.sample('AssemblyMotion', 0)['world_matrices'] != asset.sample('AssemblyMotion', .5)['world_matrices']
    outputs = {r['taskId']: r['output'] for r in receipts['parallel']['outputs']}
    for task in plan['tasks']:
        for dependency in task['dependencies']:
            assert outputs[task['id']]['started_ns'] >= outputs[dependency]['finished_ns']
    events = sorted((t, d) for r in outputs.values() for t, d in
                    [(r['processStartedMs'], 1), (r['processFinishedMs'], -1)])
    active = peak = 0
    for _, delta in events: active += delta; peak = max(peak, active)
    assert 1 < peak <= 4
    result = {'tasks': len(plan['tasks']), 'distinct_processes': len({r['pid'] for r in outputs.values()}),
              'peak_process_overlap': peak, 'wall_seconds': timings, 'byte_exact_reference_and_serial': True,
              'dependencies_observed_in_order': True, 'exact_motion_loop': True,
              'note': 'Process overlap is observed, not a CPU utilization or speedup claim. Small tasks can cost more to launch than execute.'}
    (root / 'verification.json').write_text(json.dumps(result, indent=2) + '\n')
    (root / 'README.md').write_text('''# Deterministic parallel Rivetwing creation

19 actual creation jobs: 15 reusable parts, three subassemblies and the final
animated creature. The same recipe executes with one or four local workers.
`parallel/asset.glb` is byte-identical to the earlier direct creation path.
`parallel/library.json` retains the complete editable dependency closure;
`parallel/stickers.sqlite` also keeps every successful task as a reusable part.

Run `axm-create-parallel plan.json NEW_DIRECTORY --workers 4` with the installed
UC package, local Python and Node 20+. No donor repository/service/AI is needed.
The original renderer/geometry and motion are unchanged; this proof verifies
parallel execution and deterministic assembly, not new visual quality or physics.
''')
    print(json.dumps(result, indent=2))


if __name__ == '__main__': main(sys.argv[1])

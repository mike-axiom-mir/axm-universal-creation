"""Real process execution, deterministic artifacts and rejected broken graphs."""
import copy
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from axm_uc.parallel_create import build, validate_plan, CreationFailed, SCHEMA, DATA
from axm_uc.game_pose_runtime import GamePoseAsset
from axm_stickers import Registry
from axm_stickers.assembly import import_library
from axm_stickers.placement import identity
from axm_uc.sticker_assembly import export_assembly

ORIGIN = {'author': 'AXM', 'license': 'CC0-1.0', 'source': 'Original parallel creation fixture'}


def plan():
    tasks = []
    for i in range(4):
        id = 'part' + str(i)
        tasks.append({'id': id, 'dependencies': [], 'request': {
            'operation': 'create_3d', 'id': id, 'name': id, 'socket': 'mount', **ORIGIN,
            'spec': {'schema': 'axm.procedural-3d/v0.1', 'name': id, 'primitives': [
                {'id': 'body', 'type': 'box', 'size': [.2, .3, .4], 'translation': [0, 0, 0],
                 'material': {'color': '#BF8738', 'metallic': .5, 'roughness': .6}}]}}})
    a = identity(); b = identity(); b[7] = .5
    children = [{'instance': {'$instance': {'task': t['id'], 'id': t['id']}},
                 'target': {'space': '3d', 'socket': 'mount', 'frame': a}, 'clip': None,
                 'motion': [{'time': 0, 'frame': a}, {'time': 1, 'frame': b}, {'time': 2, 'frame': a}]}
                for t in tasks]
    tasks.append({'id': 'group', 'dependencies': [t['id'] for t in tasks], 'request': {
        'operation': 'save_assembly', 'id': 'group', 'name': 'Moving group', 'children': children, 'origin': ORIGIN}})
    return {'schema': SCHEMA, 'tasks': tasks, 'result': 'group'}


@unittest.skipUnless(shutil.which('node'), 'parallel adapter requires local Node 20+')
class ParallelCreationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_processes_overlap_but_artifacts_and_motion_match_serial(self):
        p = plan(); original = copy.deepcopy(p)
        serial = build(p, self.root / 'one', workers=1)
        parallel = build(p, self.root / 'four', workers=4)
        self.assertEqual(p, original)
        for file in ('asset.glb', 'library.json', 'plan.json'):
            self.assertEqual((self.root / 'one' / file).read_bytes(), (self.root / 'four' / file).read_bytes())
        for receipt, cap in [(serial, 1), (parallel, 4)]:
            outputs = {r['taskId']: r['output'] for r in receipt['outputs']}
            self.assertEqual(len({v['pid'] for v in outputs.values()}), 5)
            events = sorted((time, delta) for v in outputs.values()
                            for time, delta in [(v['processStartedMs'], 1), (v['processFinishedMs'], -1)])
            active = peak = 0
            for _, delta in events: active += delta; peak = max(peak, active)
            self.assertLessEqual(peak, cap)
            if cap > 1: self.assertGreater(peak, 1)
            for dep in p['tasks'][-1]['dependencies']:
                self.assertGreaterEqual(outputs['group']['started_ns'], outputs[dep]['finished_ns'])
        asset = GamePoseAsset((self.root / 'four/asset.glb').read_bytes())
        self.assertEqual(asset.sample('AssemblyMotion', 0)['world_matrices'], asset.sample('AssemblyMotion', 2)['world_matrices'])
        self.assertNotEqual(asset.sample('AssemblyMotion', 0)['world_matrices'], asset.sample('AssemblyMotion', 1)['world_matrices'])
        with Registry(self.root / 'import.sqlite') as registry:
            import_library(registry, json.loads((self.root / 'four/library.json').read_text()))
            self.assertEqual(export_assembly(registry, 'group', 1)['body'], (self.root / 'four/asset.glb').read_bytes())

    def test_invalid_plans_rejected_before_processes_or_output(self):
        mutations = [lambda p: p['tasks'][0].update(dependencies=['group']),
                     lambda p: p['tasks'][0].update(dependencies=['missing']),
                     lambda p: p['tasks'][0].update(id='../escape'),
                     lambda p: p['tasks'][0].update(id='part1'),
                     lambda p: p['tasks'][-1].update(dependencies=[]),
                     lambda p: p['tasks'][0]['request'].update(operation='shell'),
                     lambda p: p.update(result='missing'),
                     lambda p: p.update(checkpoint={})]
        with patch('axm_uc.parallel_create.subprocess.Popen') as popen:
            for mutate in mutations:
                p = plan(); mutate(p)
                with self.assertRaises(ValueError): build(p, self.root / 'out')
            for cap in (0, 9, True, 1.5):
                with self.assertRaises(ValueError): build(plan(), self.root / 'out', workers=cap)
            popen.assert_not_called()
        self.assertFalse((self.root / 'out').exists())

    def test_failed_piece_blocks_assembly_preserves_independent_receipts(self):
        p = plan(); p['tasks'][0]['request']['spec']['primitives'][0]['type'] = 'not-a-shape'
        with self.assertRaises(CreationFailed) as caught: build(p, self.root / 'failed', workers=2)
        outputs = {o['taskId']: o['status'] for o in caught.exception.receipt['outputs']}
        self.assertEqual(outputs['part0'], 'FAILED')
        self.assertEqual(outputs['group'], 'BLOCKED_DEPENDENCY')
        self.assertEqual(outputs['part1'], 'COMPLETED')
        self.assertFalse((self.root / 'failed').exists())

    def test_conflicting_definitions_never_publish(self):
        p = plan(); p['tasks'][1]['request']['id'] = 'part0'
        p['tasks'][1]['request']['spec']['primitives'][0]['size'] = [1, 1, 1]
        # Independent output still conflicts at final merge even if unused by result.
        p['tasks'][-1]['dependencies'].remove('part1')
        p['tasks'][-1]['request']['children'].pop(1)
        with self.assertRaises(CreationFailed) as caught: build(p, self.root / 'conflict')
        self.assertEqual(caught.exception.receipt['status'], 'MERGE_REJECTED')
        self.assertFalse((self.root / 'conflict').exists())

    def test_no_clobber_and_missing_node_are_explicit(self):
        output = self.root / 'existing'; output.mkdir(); (output / 'mine').write_text('retain')
        with self.assertRaises(FileExistsError): build(plan(), output)
        self.assertEqual((output / 'mine').read_text(), 'retain')
        with patch('axm_uc.parallel_create.shutil.which', return_value=None):
            with self.assertRaisesRegex(RuntimeError, 'local Node'): build(plan(), self.root / 'missing')

    def test_timeout_kills_worker_before_dependent_launch(self):
        # A local fixed test executable deliberately blocks; no arbitrary command
        # selection is exposed by the public plan/API.
        worker = self.root / 'blocked.py'
        worker.write_text('import time\ntime.sleep(30)\n')
        if sys.platform == 'win32': self.skipTest('POSIX executable fixture; main adapter remains portable')
        launcher = self.root / 'blocked'
        launcher.write_text('#!' + sys.executable + '\nimport time\ntime.sleep(30)\n'); launcher.chmod(0o755)
        job = {'root': str(self.root), 'python': str(launcher), 'workers': 1, 'timeout': 1, 'digest': 'timeout',
               'tasks': [{'id': 'first', 'operation': 'test', 'dependencies': [], 'digest': '1', 'input': 'unused'},
                         {'id': 'next', 'operation': 'test', 'dependencies': ['first'], 'digest': '2', 'input': 'unused'}]}
        (self.root / 'job.json').write_text(json.dumps(job))
        subprocess.run(['node', str(DATA / 'bridge.mjs'), str(self.root / 'job.json'), str(self.root / 'receipt.json')], check=True, timeout=8)
        receipt = json.loads((self.root / 'receipt.json').read_text())
        self.assertEqual([o['status'] for o in receipt['outputs']], ['FAILED', 'BLOCKED_DEPENDENCY'])


if __name__ == '__main__': unittest.main()

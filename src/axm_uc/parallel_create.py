"""Bounded deterministic part creation using the bundled AXM parallel scheduler.

The same JSON plan works for humans, software and AI. Each task runs in its own
Python process and registry. Completed libraries are merged in declaration order
into a new output directory only after every task passes. No AI/service needed.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

from axm_stickers import Registry, instance
from axm_stickers.assembly import import_library, library_bundle
from .sticker_create import execute
from .sticker_assembly import export_assembly
from axm_stickers.assembly import CREATIVE
from .creative_tasks import OPERATIONS as CREATIVE_OPERATIONS, execute_creative, export_creative, export_creative_sources

SCHEMA = 'axm.parallel-creation/v1'
MAX_BYTES = 48 * 1024 * 1024
OPERATIONS = ('create_3d', 'save_assembly') + CREATIVE_OPERATIONS
DATA = Path(__file__).parent / 'data' / 'parallel'


def encode(value):
    return json.dumps(value, separators=(',', ':'), allow_nan=False).encode()


def sha(body):
    return hashlib.sha256(body).hexdigest()


def read(path):
    with Path(path).open('rb') as stream:
        body = stream.read(MAX_BYTES + 1)
    if len(body) > MAX_BYTES:
        raise ValueError('creation input exceeds 48 MiB')
    return json.loads(body)


def write(path, value):
    body = encode(value)
    if len(body) > MAX_BYTES:
        raise ValueError('creation output exceeds 48 MiB')
    Path(path).write_bytes(body)


def references(value):
    if isinstance(value, dict):
        if '$asset' in value:
            ref = value['$asset']
            if set(value) != {'$asset'} or not isinstance(ref,dict) or set(ref) != {'task','key'} or not all(isinstance(v,str) for v in ref.values()):
                raise ValueError('asset reference requires task and key')
            yield ref['task']
            return
        if '$task' in value:
            if set(value) != {'$task'} or not isinstance(value['$task'],str):
                raise ValueError('task reference requires a task ID')
            yield value['$task']
            return
        if '$instance' in value:
            if set(value) != {'$instance'} or not isinstance(value['$instance'], dict):
                raise ValueError('invalid instance reference')
            ref = value['$instance']
            if not {'task', 'id'} <= set(ref) or set(ref) - {'task', 'id', 'overrides', 'placement'}:
                raise ValueError('instance reference requires task/id and optional overrides/placement')
            if not isinstance(ref['task'], str):
                raise ValueError('instance task must be a string')
            yield ref['task']
        else:
            for child in value.values():
                yield from references(child)
    elif isinstance(value, list):
        for child in value:
            yield from references(child)


def validate_plan(plan):
    # Freeze the caller's state and reject non-JSON/NaN inputs before execution.
    body = encode(plan)
    if len(body) > MAX_BYTES:
        raise ValueError('plan exceeds 48 MiB')
    plan = json.loads(body)
    if not isinstance(plan, dict) or set(plan) != {'schema', 'tasks', 'result'} or plan['schema'] != SCHEMA:
        raise ValueError('plan requires schema, tasks and result')
    tasks = plan['tasks']
    if not isinstance(tasks, list) or not 1 <= len(tasks) <= 256:
        raise ValueError('plan requires 1..256 tasks')
    ids = set()
    for task in tasks:
        if not isinstance(task, dict) or set(task) != {'id', 'dependencies', 'request'}:
            raise ValueError('task requires id, dependencies and request')
        id = task['id']
        if not isinstance(id, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]{0,79}', id) or id in ids:
            raise ValueError('invalid or duplicate task id')
        ids.add(id)
        deps = task['dependencies']
        if not isinstance(deps, list) or any(not isinstance(d, str) for d in deps) or len(set(deps)) != len(deps):
            raise ValueError('dependencies must be unique task IDs')
        req = task['request']
        if not isinstance(req, dict) or req.get('operation') not in OPERATIONS:
            raise ValueError('unsupported parallel creation operation')
        if set(references(req)) - set(deps):
            raise ValueError('instance reference must name a declared dependency')
    if not isinstance(plan['result'], str) or plan['result'] not in ids:
        raise ValueError('result must name a task')
    complete = set()
    while len(complete) < len(ids):
        ready = {t['id'] for t in tasks if set(t['dependencies']) <= complete} - complete
        if not ready:
            raise ValueError('cycle or missing dependency')
        complete.update(ready)
    return plan


def resolve_references(value, definitions):
    if isinstance(value, dict):
        if '$instance' in value:
            ref = dict(value['$instance'])
            return instance(definitions[ref.pop('task')], **ref)
        return {k: resolve_references(v, definitions) for k, v in value.items()}
    if isinstance(value, list):
        return [resolve_references(v, definitions) for v in value]
    return value


def run_worker(input_path):
    started = time.time_ns()
    path = Path(input_path)
    job = read(path)
    with Registry(path.parent / 'private.sqlite') as registry:
        definitions = {}
        for task, source in job['dependencies'].items():
            bundle = read(source)
            import_library(registry, bundle)
            root = bundle['root']
            definitions[task] = registry.get(root['id'], root['version'])
        request = resolve_references(job['request'], definitions)
        if request.get('operation') not in OPERATIONS:
            raise ValueError('unsupported worker operation')
        if request['operation'] in CREATIVE_OPERATIONS:
            definition = execute_creative(registry, request, path.parent, definitions)
        else:
            definition = execute(registry, request, path.parent)
        bundle = library_bundle(registry, definition['id'], definition['version'])
        write(path.parent / 'library.json', bundle)
        return {'root': bundle['root'], 'bundle_sha256': sha(encode(bundle)),
                'pid': os.getpid(), 'started_ns': started, 'finished_ns': time.time_ns()}


class CreationFailed(RuntimeError):
    def __init__(self, receipt):
        super().__init__('parallel creation failed; no output published')
        self.receipt = receipt


def build(plan, output, *, workers=4, timeout=120):
    """Publish a new local asset folder; worker count affects execution, not content.

    timeout bounds each worker in seconds. No shared writable registry, arbitrary
    commands, network dispatch, checkpoint reuse or hidden AI calls are exposed.
    Worker isolation is for state ownership, not a hostile-code security sandbox.
    """
    plan = validate_plan(plan)
    if type(workers) is not int or not 1 <= workers <= 8:
        raise ValueError('workers must be an integer in 1..8')
    if type(timeout) is not int or not 1 <= timeout <= 600:
        raise ValueError('timeout must be an integer in 1..600 seconds')
    node = shutil.which('node')
    if node is None:
        raise RuntimeError('parallel creation requires local Node 20+; sequential creator remains available')
    output = Path(output).absolute()
    if output.exists():
        raise FileExistsError(output)
    if not output.parent.is_dir():
        raise FileNotFoundError(output.parent)
    with tempfile.TemporaryDirectory(prefix='.axm-create-', dir=output.parent) as temporary:
        root = Path(temporary)
        (root / 'tasks').mkdir()
        job = {'root': str(root), 'python': sys.executable, 'workers': workers,
               'timeout': timeout, 'digest': sha(encode(plan)), 'tasks': []}
        directories = {t['id']: root / 'tasks' / str(i) for i, t in enumerate(plan['tasks'])}
        for task in plan['tasks']:
            directory = directories[task['id']]; directory.mkdir()
            data = {'request': task['request'], 'dependencies': {
                dep: str(directories[dep] / 'library.json') for dep in task['dependencies']}}
            write(directory / 'input.json', data)
            job['tasks'].append({'id': task['id'], 'dependencies': task['dependencies'],
                'operation': task['request']['operation'], 'digest': sha(encode(task)),
                'input': str(directory / 'input.json')})
        write(root / 'job.json', job)
        env = dict(os.environ)
        env['PYTHONPATH'] = str(Path(__file__).resolve().parent.parent) + os.pathsep + env.get('PYTHONPATH', '')
        # File-backed logs prevent unbounded stdout accumulation in the parent.
        with (root / 'scheduler.log').open('wb') as log:
            process = subprocess.Popen([node, str(DATA / 'bridge.mjs'), str(root / 'job.json'),
                                        str(root / 'receipt.json')], env=env, stdout=log, stderr=log)
            try:
                process.wait(timeout=(timeout + 5) * len(plan['tasks']) + 30)
            except BaseException:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill(); process.wait()
                raise
        if process.returncode:
            with (root / 'scheduler.log').open('rb') as log:
                message = log.read(65536).decode(errors='replace')
            raise RuntimeError('parallel scheduler failed: ' + message)
        receipt = read(root / 'receipt.json')
        if receipt['status'] != 'COMPLETED':
            raise CreationFailed(receipt)
        staged = root / 'published'; staged.mkdir()
        try:
            with Registry(staged / 'stickers.sqlite') as registry:
                for task, result in zip(plan['tasks'], receipt['outputs'], strict=True):
                    if result['taskId'] != task['id'] or result['status'] != 'COMPLETED':
                        raise ValueError('scheduler task receipt mismatch')
                    bundle = read(directories[task['id']] / 'library.json')
                    if sha(encode(bundle)) != result['output']['bundle_sha256'] or bundle['root'] != result['output']['root']:
                        raise ValueError('worker library receipt mismatch')
                    import_library(registry, bundle)
                chosen = next(r['output']['root'] for r in receipt['outputs'] if r['taskId'] == plan['result'])
                bundle = library_bundle(registry, chosen['id'], chosen['version'])
                definition = registry.get(chosen['id'], chosen['version'])
                if definition['adapter'] == CREATIVE:
                    realization = export_creative(registry, definition, staged)
                    realization['sources'] = export_creative_sources(registry, definition, staged)
                    output_fields = {'asset_sha256':realization['sha256'], 'primary':realization['primary'], 'export':realization}
                else:
                    artifact = export_assembly(registry, chosen['id'], chosen['version'])
                    (staged / 'asset.glb').write_bytes(artifact['body'])
                    output_fields = {'glb_sha256':sha(artifact['body']), 'primary':'asset.glb', 'export':artifact['receipt']}
                write(staged / 'library.json', bundle)
            receipt['creation'] = {'plan_sha256': job['digest'], **output_fields,
                'result': chosen, 'workers': workers,
                'limits': 'Local authored creation; no physics or engine playback acceptance.'}
            write(staged / 'plan.json', plan); write(staged / 'receipt.json', receipt)
            # Atomic no-clobber reservation, then move only into our own directory.
            output.mkdir()
            try:
                for file in staged.iterdir():
                    file.rename(output / file.name)
            except BaseException:
                shutil.rmtree(output)
                raise
        except (ValueError, KeyError) as exc:
            receipt['status'] = 'MERGE_REJECTED'
            receipt['merge_error'] = str(exc)
            raise CreationFailed(receipt) from exc
        return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('plan', type=Path)
    parser.add_argument('output', type=Path, nargs='?')
    parser.add_argument('--workers', type=int, default=4)
    parser.add_argument('--timeout', type=int, default=120)
    parser.add_argument('--worker', action='store_true', help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.worker:
        result = run_worker(args.plan)
    else:
        if args.output is None:
            parser.error('output directory required')
        try:
            result = build(read(args.plan), args.output, workers=args.workers, timeout=args.timeout)
        except CreationFailed as exc:
            print(json.dumps(exc.receipt, allow_nan=False), file=sys.stderr)
            return 1
    print(json.dumps(result, allow_nan=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())

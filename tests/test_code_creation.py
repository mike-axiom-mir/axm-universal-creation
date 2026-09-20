import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'src'))
from axm_uc.grammar_workbench import run_grammar_tool
from axm_uc.machine import UniversalCreationMachine


@unittest.skipUnless(shutil.which('node'), 'Node is required for generated code')
class CodeCreationTests(unittest.TestCase):
    def request(self):
        return json.loads((ROOT / 'examples/code/restock-workflow.json').read_text())

    def run_job(self, request):
        return run_grammar_tool(ROOT, 'code-workflow', request)

    def test_catalog_compiler_and_repeatable_candidate(self):
        catalog = run_grammar_tool(ROOT, 'code-program', {'action': 'catalog'})
        self.assertEqual(len(catalog['operations']), 48)
        self.assertEqual(catalog['languages'], ['javascript', 'python'])
        workflow = self.run_job({'action': 'catalog'})
        self.assertEqual(len(workflow['stations']), 6)
        request = self.request(); request['action'] = 'build'
        before = copy.deepcopy(request)
        one = self.run_job(request)
        self.assertEqual(one['result'], 'CANDIDATE', one)
        self.assertIsNone(one['qa'])
        self.assertEqual(one, self.run_job(request))
        self.assertEqual(request, before)
        for target in one['build']['targets']:
            for artifact in target['artifacts']:
                self.assertEqual(hashlib.sha256(artifact['content'].encode()).hexdigest(), artifact['sha256'])

    def test_custom_multifunction_program_executes_on_both_runtimes(self):
        result = self.run_job(self.request())
        self.assertEqual(result['result'], 'VERIFIED_FOR_CASES', result)
        self.assertTrue(all(r['passed'] for r in result['qa']['requirementCoverage']))
        self.assertEqual(len(result['qa']['observations']), 4)
        self.assertEqual(len(result['retention']['archive']['entries']), 2)
        for observation in result['qa']['observations']:
            self.assertEqual(observation['status'], 'COMPLETE')
            cases = {c['id']: c for c in observation['cases']}
            self.assertEqual(cases['mixed']['actual'], [{'sku': 'AXLE', 'quantity': 6}, {'sku': 'BOLT', 'quantity': 8}])
            self.assertEqual(cases['whole-units']['actual'], [{'sku': 'PART', 'quantity': 2}])
            self.assertEqual(cases['invalid-record']['error'], 'VALUE_TYPE')
            self.assertTrue(all(c['inputUnchanged'] for c in observation['cases']))

    def test_restore_then_compose_new_capability_and_retain(self):
        original = self.run_job(self.request())
        archive = original['retention']['archive']
        root = next(c for c in original['retention']['captured'] if c['function'] == 'restock')
        restored = run_grammar_tool(ROOT, 'code-program', {'action': 'restore', 'archive': archive,
            'structuralSha256': root['structuralSha256'], 'name': 'restockParts'})
        function = next(f for f in restored['functions'] if f['name'] == 'restockParts')
        # A new function composes retained construction with a fold; no copied source text.
        restored['functions'].append({'name': 'totalUnits', 'params': [{'name': 'items', 'type': function['params'][0]['type']}],
            'returns': 'number', 'body': {'op': 'fold',
                'input': {'op': 'call', 'function': 'restockParts', 'args': [{'op': 'ref', 'name': 'items'}]},
                'item': 'order', 'acc': 'units', 'initial': {'op': 'literal', 'type': 'number', 'value': 0},
                'body': {'op': 'add', 'left': {'op': 'ref', 'name': 'units'},
                         'right': {'op': 'field', 'value': {'op': 'ref', 'name': 'order'}, 'key': 'quantity'}}}})
        restored['exports'] = ['totalUnits']
        original_cases = self.request()['job']['cases']
        cases = [{'id': 'mixed-total', 'function': 'totalUnits', 'args': original_cases[0]['args'], 'expected': 14},
                 {'id': 'empty-total', 'function': 'totalUnits', 'args': [[]], 'expected': 0}]
        job = {'id': 'restock-total', 'program': restored, 'cases': cases,
               'requirements': [{'id': 'sum-units', 'statement': 'Total the accepted restock quantities.', 'cases': [c['id'] for c in cases]}]}
        result = self.run_job({'action': 'retain', 'job': job, 'archive': archive})
        self.assertEqual(result['result'], 'VERIFIED_FOR_CASES', result)
        self.assertEqual(len(archive['entries']), 2)
        self.assertEqual(len(result['retention']['archive']['entries']), 3)

    def test_project_route_writes_standalone_modules_and_construction(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'project'
            request = {'kind': 'code-program-project', 'inputs': {'path': str(target), 'request': self.request()}}
            result = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(result['type'], 'CREATION_RESULT', result)
            self.assertTrue(result['result']['published'])
            self.assertTrue(result['result']['validation']['passed'])
            self.assertTrue(result['result']['code_workflow']['archiveWritten'])
            for name in ['construction.json', 'workflow.json', 'archive.json', 'request.json', 'LICENSE-MPL-2.0.txt']:
                self.assertTrue((target / name).is_file(), name)
            for command in [['node', 'javascript/selftest.js'], [sys.executable, 'python/selftest.py']]:
                run = subprocess.run(command, cwd=target, capture_output=True, text=True, timeout=30)
                self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            # Existing accepted data cannot be replaced by repeating the request.
            before = (target / 'construction.json').read_bytes()
            again = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(again['type'], 'CREATION_ERROR')
            self.assertEqual((target / 'construction.json').read_bytes(), before)

    def test_failed_expectation_writes_no_project_or_archive(self):
        request = self.request(); request['job']['cases'][0]['expected'][0]['quantity'] = 999
        result = self.run_job(request)
        self.assertEqual(result['result'], 'HOLD')
        self.assertIsNone(result['retention'])
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'failed'
            result = UniversalCreationMachine(ROOT).create({'kind': 'code-program-project', 'inputs': {'path': str(target), 'request': request}})
            self.assertEqual(result['type'], 'CREATION_ERROR')
            self.assertFalse(target.exists())

    def test_machine_body_and_replacement_flags_remain_protected(self):
        request = self.request(); request['action'] = 'build'
        machine = UniversalCreationMachine(ROOT)
        result = machine.create({'kind': 'code-program-project', 'inputs': {'path': str(ROOT / 'src/forbidden-code-project'), 'request': request}})
        self.assertEqual(result['type'], 'CREATION_ERROR')
        self.assertIn('machine body', result['message'])
        result = machine.create({'kind': 'code-program-project', 'inputs': {'path': 'creations/unused', 'request': request, 'replace': True}})
        self.assertEqual(result['type'], 'CREATION_ERROR')

    def test_conflicts_missing_cases_and_arbitrary_source_are_held(self):
        request = self.request()
        bad = copy.deepcopy(request); bad['job']['cases'] = []
        self.assertIn('ACCEPTANCE_CASES_REQUIRED', self.run_job(bad)['diagnostic'])
        bad = copy.deepcopy(request); bad['job']['program']['functions'][0]['body'] = {'op': 'raw', 'source': 'process.exit()'}
        self.assertIn('PROGRAM_HELD', self.run_job(bad)['diagnostic'])
        bad = copy.deepcopy(request); bad['observations'] = [{'status': 'PASS'}]
        self.assertEqual(self.run_job(bad)['result'], 'HOLD')
        bad = copy.deepcopy(request); bad['job']['languages'] = ['rust']
        self.assertEqual(self.run_job(bad)['result'], 'HOLD')
        bad = copy.deepcopy(request); bad['job']['cases'].append({**bad['job']['cases'][1], 'id': 'conflict', 'expected': [{'sku': 'X', 'quantity': 1}]})
        self.assertIn('CONFLICTING_EXPECTATIONS', self.run_job(bad)['diagnostic'])

    def test_malformed_and_large_request_are_rejected_before_subprocess(self):
        with patch('axm_uc.grammar_workbench.subprocess.run') as run:
            for request in [{'action': 'catalog', 'extra': float('nan')}, {'action': 'catalog', 'extra': 'x' * 1048576}]:
                with self.assertRaises(ValueError):
                    self.run_job(request)
            run.assert_not_called()

    def test_relocated_bundle_has_no_donor_checkout_dependency(self):
        # Copy only UC's adapter and bundled sources, outside UC and every donor checkout.
        with tempfile.TemporaryDirectory(prefix='uc-code-standalone-') as td:
            root = Path(td)
            for name in ['grammar-workbench', 'code-professions']:
                shutil.copytree(ROOT / 'third_party' / name, root / 'third_party' / name)
            shutil.copyfile(ROOT / 'src/axm_uc/grammar_workbench.py', root / 'adapter.py')
            runner = root / 'run.py'
            runner.write_text('import json\nfrom pathlib import Path\nfrom adapter import run_grammar_tool\n'
                'print(json.dumps(run_grammar_tool(Path(__file__).parent, "code-workflow", '
                '{"action":"verify","job":{"id":"offline","recipeId":"split-and-join"}})))\n')
            result = subprocess.run([sys.executable, str(runner)], cwd=root, capture_output=True, text=True, timeout=150)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['result'], 'VERIFIED_FOR_CASES')
            source = root / 'third_party/code-professions/source/workflows/code/index.mjs'
            source.write_text(source.read_text() + '\n// changed\n')
            with self.assertRaisesRegex(ValueError, 'profession donor digest mismatch'):
                run_grammar_tool(root, 'code-workflow', {'action': 'catalog'})
            archive = root / 'third_party/grammar-workbench/grammar-102.tgz'
            archive.write_bytes(archive.read_bytes() + b'changed')
            with self.assertRaisesRegex(ValueError, 'pinned donor digest mismatch'):
                run_grammar_tool(root, 'code-program', {'action': 'catalog'})

    def test_cli_reports_held_request_as_nonzero(self):
        with tempfile.TemporaryDirectory() as td:
            request = Path(td) / 'request.json'
            request.write_text('{"action":"verify","job":{"id":"missing"}}')
            result = subprocess.run([sys.executable, '-m', 'axm_uc', '--root', str(ROOT), 'code-workflow', str(request)],
                                    capture_output=True, text=True, timeout=150)
            self.assertEqual(result.returncode, 2, result.stderr)
            self.assertEqual(json.loads(result.stdout)['result'], 'HOLD')


if __name__ == '__main__':
    unittest.main()

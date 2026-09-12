"""Execute emitted JavaScript semantics; browser rendering remains separate."""
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from test_browser_game import ROOT, game_spec, request
from axm_uc.machine import UniversalCreationMachine


class BrowserGameRuntimeTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node is required for generated JavaScript logic checks')
    def test_generated_input_lifecycle_and_terminal_states(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / 'arena'
            result = UniversalCreationMachine(ROOT).create(request(target, game_spec()))
            self.assertEqual(result['type'], 'CREATION_RESULT', result)
            run = subprocess.run(
                ['node', str(ROOT / 'tests/browser_arena_runtime.cjs'), str(target / 'game.js')],
                capture_output=True, text=True, timeout=20,
            )
            self.assertEqual(run.returncode, 0, run.stdout + run.stderr)
            self.assertIn('GENERATED_GAME_LOGIC_OK', run.stdout)

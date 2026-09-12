import copy,shutil,subprocess,tempfile,unittest
from pathlib import Path
from test_browser_game import ROOT,game_spec,request
from test_browser_construction import construction_spec
from axm_uc.machine import UniversalCreationMachine
from axm_uc.browser_game import validate_browser_game_spec,BrowserGameError


class WaveTests(unittest.TestCase):
    def test_closed_plan_validation_and_roundtrip(self):
        spec=game_spec();spec['waves']={'count':3,'health_step':.25,'speed_step':.1,'clear_bonus':60}
        result=validate_browser_game_spec(spec);self.assertEqual(validate_browser_game_spec(result),result)
        for key,val in [('count',0),('count',True),('count',13),('health_step',float('nan')),('speed_step',-1),('clear_bonus',-1)]:
            bad=copy.deepcopy(spec);bad['waves'][key]=val
            with self.assertRaises(BrowserGameError):validate_browser_game_spec(bad)

    @unittest.skipUnless(shutil.which('node'),'Node required')
    def test_wave_clear_launch_carryover_and_final_outcome(self):
        with tempfile.TemporaryDirectory() as td:
            spec=game_spec();spec['construction']=construction_spec();spec['waves']={'count':3,'health_step':.25,'speed_step':.1,'clear_bonus':60}
            target=Path(td)/'waves';result=UniversalCreationMachine(ROOT).create(request(target,spec))
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            run=subprocess.run(['node',str(ROOT/'tests/browser_arena_runtime.cjs'),str(target/'game.js')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

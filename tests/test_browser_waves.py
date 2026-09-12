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

    def test_rosters_validate_and_do_not_alias_caller_data(self):
        spec=game_spec();ids=[e['id'] for e in spec['enemies']]
        spec['waves']={'count':3,'health_step':.25,'speed_step':.1,'clear_bonus':60,
                       'rosters':[[ids[1]],ids[1:],list(reversed(ids))]}
        normalized=validate_browser_game_spec(spec)
        self.assertEqual(validate_browser_game_spec(normalized),normalized)
        normalized['waves']['rosters'][0].clear()
        self.assertEqual(spec['waves']['rosters'][0],[ids[1]])
        for bad in (None, [], [[],ids,ids], [[ids[0],ids[0]],ids,ids],
                    [['missing'],ids,ids], [[{}],ids,ids], ['scout-left',ids,ids]):
            candidate=copy.deepcopy(spec);candidate['waves']['rosters']=bad
            with self.subTest(rosters=bad), self.assertRaises(BrowserGameError):
                validate_browser_game_spec(candidate)

    @unittest.skipUnless(shutil.which('node'),'Node required')
    def test_roster_runtime_order_scaling_and_source_preservation(self):
        import json
        from axm_uc.browser_waves import WAVES_JS
        spec=game_spec();ids=[e['id'] for e in spec['enemies']]
        plan={'count':3,'health_step':.25,'speed_step':.1,'clear_bonus':60,
              'rosters':[[ids[1]],ids[1:],list(reversed(ids))]}
        script=WAVES_JS+'\nconst assert=require("node:assert/strict");\n'
        script+='const base='+json.dumps(spec['enemies'])+';const plan='+json.dumps(plan)+';\n'
        script+='''
const before=JSON.stringify(base), planBefore=JSON.stringify(plan);
assert.deepEqual(WaveCycle.enemies(base,plan,0).map(e=>e.id),plan.rosters[0]);
const second=WaveCycle.enemies(base,plan,1);
assert.deepEqual(second.map(e=>e.id),plan.rosters[1]);
assert.equal(second[0].health,Math.round(base[1].health*1.25));
assert.equal(second[0].speed,base[1].speed*1.1);
assert.deepEqual(WaveCycle.enemies(base,plan,2).map(e=>e.id),plan.rosters[2]);
second[0].health=0;
assert.equal(JSON.stringify(base),before);assert.equal(JSON.stringify(plan),planBefore);
assert.equal(WaveCycle.enemies(base,null,0).length,base.length);
assert.throws(()=>WaveCycle.enemies(base,plan,3));
'''
        run=subprocess.run(['node','-e',script],capture_output=True,text=True)
        self.assertEqual(run.returncode,0,run.stdout+run.stderr)
        with tempfile.TemporaryDirectory() as td:
            spec['waves']=plan
            result=UniversalCreationMachine(ROOT).create(request(Path(td)/'rosters',spec))
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            self.assertTrue(result['result']['validation']['passed'])

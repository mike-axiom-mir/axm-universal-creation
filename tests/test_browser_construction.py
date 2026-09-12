import copy,json,shutil,subprocess,tempfile,unittest
from pathlib import Path
from test_browser_game import ROOT,game_spec,request
from axm_uc.browser_game import validate_browser_game_spec,BrowserGameError
from axm_uc.browser_construction_source import CONSTRUCTION_JS
from axm_uc.machine import UniversalCreationMachine


def construction_spec():
    return {'cell_size':60,'initial_credits':200,'blocked':[[0,0]],'catalog':{k:{'label':k,'cost':cost,'rate':rate,'range':230} for k,cost,rate in [('generator',60,6),('turret',90,25),('repair',50,5)]}}


class ConstructionTests(unittest.TestCase):
    def test_contract_roundtrip_and_invalid_values(self):
        s=game_spec();s['construction']=construction_spec();before=copy.deepcopy(s)
        valid=validate_browser_game_spec(s)
        self.assertEqual(s,before);self.assertEqual(validate_browser_game_spec(valid),valid)
        self.assertIn([0,0],valid['construction']['blocked'])
        for field,value in [('initial_credits',True),('cell_size',0),('blocked',[[999,0]]),('catalog',{})]:
            bad=copy.deepcopy(s);bad['construction'][field]=value
            with self.assertRaises(BrowserGameError):validate_browser_game_spec(bad)

    @unittest.skipUnless(shutil.which('node'),'Node required')
    def test_atomic_placement_and_integer_economy(self):
        s=game_spec();s['construction']=construction_spec();c=validate_browser_game_spec(s)['construction']
        script=CONSTRUCTION_JS+'\nconst assert=require("node:assert/strict");const spec='+json.dumps(c)+''';
const state=Construction.create(spec);
for(const args of [['turret',-1,1],['turret',0,0],['missing',1,1],['generator',NaN,1]]){
 const before=JSON.stringify(state);assert.equal(Construction.place(spec,state,...args).ok,false);assert.equal(JSON.stringify(state),before);
}
assert.equal(Construction.place(spec,state,'generator',1,1).ok,true);assert.equal(state.credits,140);
let before=JSON.stringify(state);assert.equal(Construction.place(spec,state,'repair',1,1).ok,false);assert.equal(JSON.stringify(state),before);
assert.equal(Construction.place(spec,state,'turret',2,1).ok,true);assert.equal(state.credits,50);
before=JSON.stringify(state);assert.equal(Construction.place(spec,state,'generator',3,1).ok,false);assert.equal(JSON.stringify(state),before);
Construction.tick(spec,state,10);assert.equal(state.credits,110);assert.equal(state.ticks,10);
before=JSON.stringify(state);assert.throws(()=>Construction.tick(spec,state,-1));assert.equal(JSON.stringify(state),before);
Construction.reward(state,1000000000);assert.equal(state.credits,1000000000);
'''
        run=subprocess.run(['node','-e',script],capture_output=True,text=True);self.assertEqual(run.returncode,0,run.stderr)

    @unittest.skipUnless(shutil.which('node'),'Node required')
    def test_generated_outpost_support_and_pause_reset(self):
        with tempfile.TemporaryDirectory() as td:
            s=game_spec();s['construction']=construction_spec();target=Path(td)/'outpost'
            result=UniversalCreationMachine(ROOT).create(request(target,s))
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            self.assertTrue(result['result']['validation']['passed'])
            run=subprocess.run(['node',str(ROOT/'tests/browser_arena_runtime.cjs'),str(target/'game.js')],capture_output=True,text=True)
            self.assertEqual(run.returncode,0,run.stdout+run.stderr)

import copy,json,shutil,subprocess,unittest
from pathlib import Path
from axm_uc.grammar_workbench import run_grammar_tool
ROOT=Path(__file__).resolve().parents[1]
@unittest.skipUnless(shutil.which('node'),'Node required for donor tools')
class GrammarWorkbenchTests(unittest.TestCase):
    def test_capsule_resolution_repeat_and_conflict(self):
        req={'filePath':'src/world.rs','operation':'refactor'}
        a=run_grammar_tool(ROOT,'grammar-capsule',req)
        self.assertEqual(a['languageId'],'rust')
        self.assertEqual(a,run_grammar_tool(ROOT,'grammar-capsule',req))
        conflict=run_grammar_tool(ROOT,'grammar-capsule',{'filePath':'x.py','languageId':'rust'})
        self.assertNotEqual(conflict['result'],a['result'])
        self.assertFalse(a['authority']['toolExecution'])
    def test_sparse_equivalence_and_projection(self):
        req=json.loads((ROOT/'examples/grammar/ripple.json').read_text());before=copy.deepcopy(req)
        r=run_grammar_tool(ROOT,'state-ripple',req)
        self.assertEqual(r['result'],'STATE_RIPPLE_SPARSE_FULL_EQUIVALENCE_PASS')
        self.assertEqual(r['sparseExecutedNodeCount'],2);self.assertEqual(r['sparseReusedNodeCount'],1)
        self.assertEqual(r['sparse']['finalState']['summary']['total'],10)
        self.assertEqual(req,before)
        atoms=[{'atomId':str(i),'languageId':'a' if i%2 else 'b'} for i in range(1000)]
        p=run_grammar_tool(ROOT,'render-budget',{'atoms':atoms,'mode':'SAFE'})
        self.assertEqual(p['renderedAtomCount'],384);self.assertEqual(p['projectionHeldAtomCount'],616)
        self.assertEqual(len(atoms),1000);self.assertEqual(p['languageCoverageCount'],2)
    def test_pinned_glass_regressions(self):
        folder=ROOT/'third_party/grammar-workbench'
        for name in ('state-ripple','state-ripple-validation','state-ripple-baseline-admission','render-budget'):
            r=subprocess.run(['node',str(folder/('selftest-'+name+'.js'))],capture_output=True,text=True,timeout=30)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

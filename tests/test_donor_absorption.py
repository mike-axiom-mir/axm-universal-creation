import json,shutil,subprocess,unittest
from pathlib import Path
from axm_uc.timeline_tracks import sample_track
from axm_uc.donor_voice.core import Ref,CommunicationKind
from axm_uc.donor_voice.outcome import CriterionObservation,produce_criterion_outcome
ROOT=Path(__file__).resolve().parents[1]
class DonorTests(unittest.TestCase):
    def test_timeline_endpoints_order_and_hold(self):
        self.assertEqual(sample_track({'from':0,'to':100},5,0,11),50)
        self.assertEqual(sample_track({'from':0,'to':100,'easing':'smoothstep'},10,0,11),100)
        t={'keyframes':[{'frame':0,'value':4,'easing':'hold'},{'frame':10,'value':9}]}
        self.assertEqual(sample_track(t,9),4);self.assertEqual(sample_track(t,10),9)
        for bad in (True,{'from':0,'easing':'unknown'},{'keyframes':[]},{'keyframes':[{'frame':1,'value':0},{'frame':1,'value':2}]}):
            with self.assertRaises(ValueError):sample_track(bad,2)
    def test_outcome_requires_complete_positive_evidence(self):
        a,b=Ref('criterion','a'),Ref('criterion','b')
        def run(obs):
            return produce_criterion_outcome(event_id='test',source=Ref('machine','uc'),activity=Ref('activity','test'),attempt=Ref('attempt','one'),attempt_evidence=(Ref('evidence','attempt'),),criteria_contract=Ref('contract','one'),required_criteria=(a,b),criteria_evidence=(Ref('evidence','contract'),),observations=obs)
        def obs(c,ok):return CriterionObservation(c,Ref('observation',c.id),ok,(Ref('evidence',c.id),))
        self.assertIsNone(run((obs(a,True),)))
        self.assertEqual(run((obs(a,True),obs(b,True))).kind,CommunicationKind.SUCCESS)
        self.assertEqual(run((obs(a,False),)).kind,CommunicationKind.FAILURE)
    @unittest.skipUnless(shutil.which('node'),'Node required for JavaScript donor tools')
    def test_material_donor_suites(self):
        for filename in ('premade-composer-core.test.js','conformance-core.test.js'):
            r=subprocess.run(['node',str(ROOT/'third_party/material-surface/tests'/filename)],capture_output=True,text=True)
            self.assertEqual(r.returncode,0,r.stdout+r.stderr)

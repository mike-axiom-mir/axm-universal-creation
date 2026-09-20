from copy import deepcopy
import json
import math
from pathlib import Path
import tempfile
import unittest

from axm_uc.character_controller import CharacterController
from axm_uc.character_motion import CharacterMotionError
from axm_uc.machine import UniversalCreationMachine

ROOT = Path(__file__).resolve().parents[1]


def recipe():
    return json.loads((ROOT/'examples/character-motion/seedling-performance.json').read_text())['inputs']['recipe']


class CharacterControllerTests(unittest.TestCase):
    def test_sparse_baked_keys_drift_but_query_time_solve_preserves_contact(self):
        r=recipe();r['performance']['clips'][0]['samples']=3
        controller=CharacterController(r)
        node=controller.joint_nodes['left-ankle']
        wanted=controller.landmarks['left-ankle']
        baked=controller.asset.point(controller.asset.sample('walk',.37),node)
        actual=controller.asset.point(controller.sample('walk',.37),node)
        self.assertGreater(math.dist(baked,wanted),.001)
        self.assertLess(math.dist(actual,wanted),1e-8)
        report=controller.measure('walk',[4*i/80 for i in range(81)],
                                  feet={'left-ankle':'left-foot','right-ankle':'right-foot'})
        self.assertLess(report['metrics']['maximum_contact_slip_m'],1e-7)
        self.assertLess(report['metrics']['foot_penetration_m'],1e-7)
        self.assertGreater(report['metrics']['peak_foot_lift_m'],.1)

    def test_root_travel_crosses_cycles_and_query_order_does_not_change_state(self):
        r=recipe();before=deepcopy(r)
        c=CharacterController(r)
        body=c.built['body']
        first=c.sample('walk',.23,vertices=True)
        far=c.sample('walk',20.23,vertices=True)
        self.assertEqual(first,c.sample('walk',.23,vertices=True))
        root=c.joint_nodes['root']
        a,b=c.asset.point(first,root),c.asset.point(far,root)
        self.assertLess(math.dist([y-x for x,y in zip(a,b)],[0,2.2,0]),1e-7)
        for joint in ('left-ankle','right-ankle'):
            a,b=c.asset.point(first,c.joint_nodes[joint]),c.asset.point(far,c.joint_nodes[joint])
            self.assertLess(math.dist([y-x for x,y in zip(a,b)],[0,2.2,0]),1e-7)
        self.assertEqual(body,c.built['body'])
        self.assertEqual(r,before)
        a=c.asset.point(c.sample('walk',1.999999),root)
        b=c.asset.point(c.sample('walk',2.000001),root)
        self.assertLess(math.dist(a,b),1e-5)

    def test_unreachable_between_key_motion_is_refused_when_queried(self):
        r=recipe();r['performance']['clips'][0].update(samples=3,lift=2)
        c=CharacterController(r)
        with self.assertRaises(CharacterMotionError):
            c.sample('walk',1.6)
        for time in (-1,float('nan')):
            with self.assertRaises(CharacterMotionError):c.sample('walk',time)
        with self.assertRaises(CharacterMotionError):c.sample('reach',3)
        with self.assertRaises(CharacterMotionError):c.sample('missing',0)

    def test_override_validation_and_missing_contact_evidence(self):
        c=CharacterController(recipe())
        for rows in ([{'node':9999,'translation':[0,0,0]}],
                     [{'node':0,'rotation':[0,0,0,0]}],
                     [{'node':0,'translation':[0,0,0]}]*2,
                     [{'node':0,'scale':[1,1,1]}],
                     [{'node':0,'translation':[float('inf'),0,0]}]):
            with self.assertRaises(ValueError):c.asset.sample(overrides=rows)
        report=c.measure('walk',[0,1.5],feet={'left-ankle':'left-foot','right-ankle':'right-foot'})
        self.assertNotIn('maximum_contact_slip_m',report['metrics'])

    def test_live_probe_keeps_recipe_and_observed_poses(self):
        with tempfile.TemporaryDirectory() as t:
            path=Path(t)/'probe.json'
            result=UniversalCreationMachine(ROOT).create({'kind':'character-controller','inputs':{
                'path':str(path),'recipe':recipe(),'clip':'walk','times':[0,.37,2.37,4.37]}})
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            observed=json.loads(path.read_text())
            self.assertEqual(len(observed['poses']),4)
            self.assertTrue(observed['source_authority'])
            self.assertEqual(observed['recipe'],recipe())
            self.assertEqual(observed['poses'][-1]['performance']['elapsed_s'],4.37)


if __name__=='__main__':unittest.main()

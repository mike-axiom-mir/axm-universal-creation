from copy import deepcopy
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.construction_search import search_construction, publish_search
from axm_uc.character_controller import CharacterController
from axm_uc.machine import UniversalCreationMachine

ROOT = Path(__file__).resolve().parents[1]


def contract(name='broader-walker'):
    return json.loads((ROOT/f'examples/construction-search/{name}.json').read_text())['inputs']['search']


class ConstructionSearchTests(unittest.TestCase):
    def test_shape_and_motion_search_is_repeatable_and_meets_declared_checks(self):
        q=contract();before=deepcopy(q)
        a,b=search_construction(q),search_construction(q)
        self.assertEqual(a,b)
        self.assertEqual(q,before)
        self.assertEqual(a['status'],'CRITERIA_MET')
        self.assertTrue(all(c['passed'] for c in a['selected']['checks']))
        self.assertNotEqual(a['selected']['recipe'],q['recipe'])
        self.assertLess(a['counts']['deep_validations'],a['counts']['evaluated'])
        self.assertLess(a['counts']['visited'],a['counts']['declared_combinations'])
        self.assertIsNone(a['acceptance']['probability'])
        self.assertFalse(a['growth_candidate']['automatic_canon_admission'])
        # Different verification times from the search itself observe the actual winner.
        c=CharacterController(a['selected']['recipe'])
        proof=c.measure('walk',[4*i/97 for i in range(98)],feet=q['motion_probe']['feet'])
        self.assertLess(proof['metrics']['maximum_contact_slip_m'],1e-6)
        self.assertGreater(proof['metrics']['peak_foot_lift_m'],.15)

    def test_retained_settings_accelerate_reuse_but_are_rechecked_for_new_intent(self):
        q=contract()
        first=search_construction(q)
        q['warm_starts']=[first['growth_candidate']['warm_start']]
        reused=search_construction(q)
        self.assertEqual(reused['status'],'CRITERIA_MET')
        self.assertEqual(reused['counts']['visited'],1)
        q['criteria'][0].update(min=.85,max=.9)
        changed=search_construction(q)
        self.assertEqual(changed['history'][0]['status'],'GEOMETRY_REJECTED')
        self.assertEqual(changed['status'],'CRITERIA_MET')
        self.assertNotEqual(changed['selected']['settings'],first['selected']['settings'])

    def test_search_can_repair_a_measured_skin_distortion(self):
        q=contract('deformation-repair')
        times=[4*i/64 for i in range(65)]
        before=CharacterController(q['recipe']).measure('walk',times)['metrics']
        self.assertLess(before['minimum_area_ratio'],.72)
        result=search_construction(q)
        self.assertEqual(result['status'],'CRITERIA_MET')
        after=result['selected']['metrics']
        self.assertGreaterEqual(after['minimum_area_ratio'],.77)
        self.assertLessEqual(after['maximum_edge_ratio'],1.02)
        self.assertEqual(result['selected']['recipe']['form'],q['recipe']['form'])
        self.assertNotEqual(result['selected']['recipe']['performance']['bindings'],q['recipe']['performance']['bindings'])

    def test_budget_and_exhaustion_never_promote_a_failed_candidate(self):
        q=contract();q['budget']['candidates']=1
        result=search_construction(q)
        self.assertEqual(result['status'],'BUDGET_EXHAUSTED')
        self.assertIsNone(result['selected'])
        self.assertIsNone(result['growth_candidate'])
        q['criteria'][0]['scale']=1e-320
        bounded=search_construction(q)
        self.assertEqual(bounded['status'],'BUDGET_EXHAUSTED')
        json.dumps(bounded,allow_nan=False)
        q=contract('vessel');q['criteria'][0].update(min=50,max=60)
        q['budget']['candidates']=256
        result=search_construction(q)
        self.assertEqual(result['status'],'SPACE_EXHAUSTED')
        self.assertIsNone(result['selected'])
        self.assertEqual(result,search_construction(q))

    def test_dense_verification_can_refuse_a_coarse_success(self):
        q=contract()
        q['controls'][0]['values']=[.4];q['controls'][1]['values']=[.2]
        q['criteria'].append({'metric':'maximum_bend_degrees','max':83})
        result=search_construction(q)
        self.assertIsNone(result['selected'])
        self.assertEqual(result['counts']['deep_validations'],1)
        self.assertEqual(result['history'][0]['status'],'VALIDATION_FAILED')

    def test_cosmetic_variants_deduplicate_without_hiding_invalid_construction(self):
        q=contract('vessel')
        q['controls']=[{'id':'paint','paths':[['parts',0,'material','color']],
                        'values':['#4C9B91FF','#FFCC00FF','#AACC11FF']}]
        q['criteria']=[{'metric':'extent_x_m','min':50}]
        result=search_construction(q)
        self.assertEqual(result['counts']['evaluated'],1)
        self.assertEqual(result['counts']['deduplicated'],2)
        q['recipe']=search_construction(contract('vessel'))['selected']['recipe']
        q['controls'][0]['values']=['invalid-color','#4C9B91FF']
        q['recipe']['parts'][0]['material']['color']='invalid-color'
        q['criteria']=[{'metric':'extent_x_m','min':.7}]
        result=search_construction(q)
        self.assertEqual(result['status'],'CRITERIA_MET')
        self.assertEqual(result['counts']['evaluated'],2)

    def test_live_route_publishes_verified_source_and_existing_outputs_survive(self):
        with tempfile.TemporaryDirectory() as t:
            target=Path(t)/'search'
            q=contract('vessel')
            result=UniversalCreationMachine(ROOT).create({'kind':'headless-shape-search','inputs':{
                'path':str(target),'search':q}})
            self.assertEqual(result['type'],'CREATION_RESULT',result)
            report=json.loads((target/'search.json').read_text())
            self.assertEqual(report['status'],'CRITERIA_MET')
            source=json.loads((target/'winner.glb.source.json').read_text())
            self.assertEqual(source['recipe'],report['selected']['recipe'])
            self.assertEqual(source['artifact']['sha256'],report['selected']['evidence']['source_sha256'])
            before=(target/'winner.glb').read_bytes()
            with self.assertRaises(ValueError):publish_search(target,q)
            self.assertEqual(before,(target/'winner.glb').read_bytes())

    def test_unmeasurable_or_conflicting_search_contracts_are_rejected(self):
        mutations=[lambda q:q['criteria'].append({'metric':'beauty','min':99}),
                   lambda q:q['budget'].update(candidates=True),
                   lambda q:q['budget'].update(validation_samples=100000),
                   lambda q:q['controls'].append(deepcopy(q['controls'][0])),
                   lambda q:q['controls'][0].update(paths=[['metadata','missing']]),
                   lambda q:q['controls'][0].update(values=[float('nan')]),
                   lambda q:q.update(warm_starts=[{'body-width':.9,'foot-lift':.12}]),
                   lambda q:q.pop('motion_probe')]
        for mutate in mutations:
            with self.subTest(mutate=mutate):
                q=contract();mutate(q)
                with self.assertRaises(ValueError):search_construction(q)


if __name__=='__main__':unittest.main()

import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from axm_uc.pipeline_map import map_capabilities, map_nodes, installed_nodes
ROOT=Path(__file__).resolve().parents[1]

def node(name, provides, requires=(), types=None):
    n={'id':name,'module':'test','provides':list(provides),'accepts':list(requires),
       'requires':list(requires),'required_parameters':[], 'project_types':types or []}
    return n

class PipelineMapTests(unittest.TestCase):
    def test_live_inventory_media_routes_and_read_only(self):
        from axm_uc.capabilities import CapabilityStore
        before=(ROOT/'state/machine.json').read_bytes()
        with patch.object(CapabilityStore,'invoke',side_effect=AssertionError('must not execute')):
            r=map_capabilities(ROOT,'result.kind.mixed-project-directory')
        self.assertEqual(len(r['pipelines']),6)
        self.assertEqual({p['nodes'][0] for p in r['pipelines']},
                         {'request-builder::'+n for n in ('metal','fabric','bitmap-label','normalize-wav','survivor-workshop','rts-reference-pack')})
        self.assertTrue(all(p['status']=='declared_contract_path_not_tested' for p in r['pipelines']))
        self.assertEqual(before,(ROOT/'state/machine.json').read_bytes())
        self.assertEqual(r,map_capabilities(ROOT,'result.kind.mixed-project-directory'))
        self.assertFalse(r['search']['truncated'])

    def test_goal_scope_cycles_and_budget(self):
        ns=[node('a',['x'],['z']),node('b',['y'],['x']),node('c',['z'],['y'])]
        original=copy.deepcopy(ns)
        r=map_nodes(ns,'z',max_hops=6)
        self.assertTrue(r['pipelines'])
        self.assertTrue(all(len(p['nodes'])==len(set(p['nodes'])) for p in r['pipelines']))
        self.assertEqual(ns,original)
        low=map_nodes(ns,search_budget=1)
        self.assertEqual(low['search']['states_visited'],1)
        self.assertTrue(low['search']['truncated'])
        self.assertFalse(low['search']['complete_within_hop_limit'])
        self.assertEqual(map_nodes(ns,'absent')['pipelines'],[])
        dense=[node(str(i),['shared'],['shared']) for i in range(30)]
        bounded=map_nodes(dense,search_budget=17)
        self.assertLessEqual(bounded['search']['states_visited'],17)
        self.assertTrue(bounded['search']['truncated'])
        for kwargs in ({'limit':0},{'max_hops':True},{'search_budget':0},{'goal':''}):
            with self.assertRaises(ValueError):map_nodes(ns,**kwargs)

    def test_fanin_is_not_silently_satisfied_and_project_types_intersect(self):
        r=map_nodes([node('a',['x']),node('b',['y'],['x','missing'])],'y')
        self.assertEqual(r['pipelines'][0]['additional_required_interfaces'],
                         [{'node':'test::b','interfaces':['missing']}])
        self.assertEqual(r['missing_interface_providers'],[{'node':'test::b','interface':'missing'}])
        # Pairwise intersections alone are insufficient for a full project chain.
        ns=[node('a',['x'],types=['web']),node('b',['y'],['x'],['web','python']),node('c',['z'],['y'],['python'])]
        r=map_nodes(ns,'z')
        self.assertFalse(any(len(p['nodes'])==3 for p in r['pipelines']))

    def test_exact_tokens_and_single_provider(self):
        r=map_nodes([node('a',['Color']),node('b',['out'],['color'])],'out')
        self.assertEqual(r['graph']['edge_count'],0)
        self.assertEqual(r['single_capabilities'],['test::b'])
        self.assertEqual(r['pipelines'],[])
        with self.assertRaises(ValueError):map_nodes([node('a',[]),node('a',[])])

    def test_source_absence_and_digest_change(self):
        # Minimal root without the full registry is tested by replacing catalog readers.
        from axm_uc.capabilities import CapabilityStore
        from axm_uc.organ_library import ExecutableOrganLibrary
        with tempfile.TemporaryDirectory() as td, patch.object(CapabilityStore,'live',return_value=[]), patch.object(ExecutableOrganLibrary,'list',return_value=[]):
            root=Path(td)
            # CapabilityStore's Registry requires its baseline; avoid initialization only here.
            with patch.object(CapabilityStore,'__init__',return_value=None), patch.object(ExecutableOrganLibrary,'__init__',return_value=None):
                ns,identity=installed_nodes(root)
                self.assertEqual(ns,[]);self.assertEqual(len(identity['excluded_adapters']),6)
                path=root/'src/axm_uc/fabric_material.py';path.parent.mkdir(parents=True)
                path.write_text('def fabric_request():\n    pass\n')
                ns,new=installed_nodes(root)
                self.assertEqual(len(ns),1);self.assertNotEqual(identity['catalog_sha256'],new['catalog_sha256'])
                path.write_text('def different_function():\n    pass\n')
                self.assertEqual(installed_nodes(root)[0],[])

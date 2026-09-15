"""Typed tool composition and human-editable source round trips."""
import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_stickers import Registry, instance
from axm_stickers.assembly import CREATIVE, import_library, library_bundle, library_definitions
from axm_uc.creative_tasks import execute_creative, export_creative
from axm_uc.parallel_create import build, validate_plan, CreationFailed
from axm_uc.surface_creation import create_surface, compile_surface, SURFACE
from axm_uc.studio_compositor import compose_studio_project
from axm_uc.game_material_bridge import load_material_bundle
from axm_uc.game_material_styles import game_material_request
from axm_uc.procedural_effects import build_electric_arc


@unittest.skipUnless(shutil.which('node'),'local Node required by Studio')
class CreativeTaskTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.controls = {'schema':SURFACE,'name':'Coil housing','size':64,'seed':41,'color':[40,78,88]}

    def test_single_creation_controls_compile_and_execute_same_serial_parallel(self):
        original = copy.deepcopy(self.controls)
        a = create_surface(self.controls,self.root/'one',workers=1)
        b = create_surface(self.controls,self.root/'four',workers=4)
        self.assertEqual(self.controls,original)
        self.assertEqual(a['creation']['asset_sha256'],b['creation']['asset_sha256'])
        for name in ('asset.png','library.json','studio-project.json','plan.json'):
            self.assertEqual((self.root/'one'/name).read_bytes(),(self.root/'four'/name).read_bytes())
        body = (self.root/'four/asset.png').read_bytes()
        project = json.loads((self.root/'four/studio-project.json').read_text())
        self.assertEqual(compose_studio_project(project,self.root/'four')['png'],body)
        sources = json.loads((self.root/'four/source-index.json').read_text())
        material = next(e for e in sources if e['operation']=='create_material')
        loaded = load_material_bundle(self.root/'four'/material['folder'])
        self.assertIn('normal',loaded['pngs']); self.assertIn('exposed_mask',loaded['pngs'])
        with Registry(self.root/'reimport.sqlite') as registry:
            bundle = json.loads((self.root/'four/library.json').read_text()); import_library(registry,bundle)
            self.assertEqual(len(bundle['definitions']),4)
            self.assertEqual(library_bundle(registry,'finished',1),bundle)
            d = registry.get('finished',1)
            replay = self.root/'replay'; replay.mkdir(); export_creative(registry,d,replay)
            self.assertEqual((replay/'asset.png').read_bytes(),body)
            # The final library still contains the exact earlier editable step.
            before = registry.get('composed',1)
            self.assertNotIn('filters',before['recipe']['project']['recipe']['layers'][0])
            self.assertIn('filters',d['recipe']['project']['recipe']['layers'][0])

    def test_material_and_effect_preserve_original_mechanisms_and_topology(self):
        plan = compile_surface(self.controls)
        with Registry(self.root/'r.sqlite') as registry:
            mat = execute_creative(registry,plan['tasks'][0]['request'],self.root,{})
            spec = plan['tasks'][0]['request']['settings']
            plain = game_material_request('unused',family=spec['family'],size=64,seed=41,color=spec['color'])
            # Actual requested coat changes physical maps, not merely a tint.
            self.assertNotEqual(json.loads(registry.asset(mat['assets']['material']))['maps']['normal']['sha256'],
                                json.loads(plain['inputs']['text_files']['game-material.json'])['maps']['normal']['sha256'])
            arc = execute_creative(registry,plan['tasks'][1]['request'],self.root,{})
            expected = build_electric_arc(plan['tasks'][1]['request']['settings'])['graph']
            self.assertEqual(json.loads(registry.asset(arc['assets']['graph'])),expected)
            self.assertTrue(registry.asset(arc['assets']['image']).startswith(b'\x89PNG'))
            changed = copy.deepcopy(plan['tasks'][1]['request']); changed['id']='red'
            changed['settings']['realization']['color']='#ff3300'
            red = execute_creative(registry,changed,self.root,{})
            self.assertEqual(arc['assets']['graph'],red['assets']['graph'])
            self.assertNotEqual(arc['assets']['image'],red['assets']['image'])

    def test_typed_inputs_reject_paths_wrong_media_and_undeclared_dependencies(self):
        plan = compile_surface(self.controls)
        bad = copy.deepcopy(plan); bad['tasks'][2]['dependencies']=[]
        with self.assertRaisesRegex(ValueError,'declared dependency'): validate_plan(bad)
        bad = copy.deepcopy(plan); bad['tasks'][2]['request']['project']['sources']['paint']='../../private.png'
        with self.assertRaises(CreationFailed): build(bad,self.root/'bad-path')
        bad = copy.deepcopy(plan); bad['tasks'][2]['request']['project']['sources']['paint']['$asset']['key']='material'
        with self.assertRaises(CreationFailed): build(bad,self.root/'bad-media')
        self.assertFalse((self.root/'bad-path').exists()); self.assertFalse((self.root/'bad-media').exists())

    def test_dependency_library_rejects_missing_tampered_and_extra_definitions_atomically(self):
        create_surface(self.controls,self.root/'valid')
        bundle = json.loads((self.root/'valid/library.json').read_text())
        with Registry(self.root/'empty.sqlite') as registry:
            for kind in ('missing','pin','extra'):
                bad = copy.deepcopy(bundle)
                if kind=='missing': bad['definitions'].pop()
                elif kind=='pin': bad['definitions'][0]['recipe']['dependencies'][0]['digest']='0'*64
                else:
                    extra = copy.deepcopy(bad['definitions'][-1]);extra['id']='foreign';bad['definitions'].append(extra)
                with self.assertRaises(ValueError): import_library(registry,bad)
                self.assertEqual(registry.search()['entries'],[])

    def test_all_layer_edit_verbs_operate_on_a_copy(self):
        plan = compile_surface(self.controls)
        plan['tasks'][-1]['request']['edits'] = [
            {'op':'add','layer':{'id':'grade','fill':'#112244','opacity':.1}},
            {'op':'move','id':'grade','before':'charge'},
            {'op':'change','id':'charge','patch':{'opacity':.5}},
            {'op':'remove','id':'grade'}]
        build(plan,self.root/'edited')
        with Registry(self.root/'edited/stickers.sqlite') as registry:
            original = registry.get('composed',1)['recipe']['project']['recipe']['layers']
            revised = registry.get('finished',1)['recipe']['project']['recipe']['layers']
            self.assertEqual(original[1]['opacity'],.8);self.assertEqual(revised[1]['opacity'],.5)
            self.assertEqual([v['id'] for v in revised],['paint','charge'])


if __name__=='__main__': unittest.main()

import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core','visual.broadcast.core','visual.diagram.core','visual.atlas.core','visual.novel.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':19,'primitives':136,'screens':174,'products':17})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.','visual.broadcast.','visual.diagram.','visual.atlas.','visual.novel.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11,'visual.cinematic.core':10,'visual.broadcast.core':10,'visual.diagram.core':10,'visual.atlas.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_novel_product_preserves_branching_source_truth(self):
        product=vt.get('visual.novel.core')
        required={'visual.novel.project-hub','visual.novel.scene-editor','visual.novel.character-stage','visual.novel.dialogue-editor','visual.novel.choice-editor','visual.novel.branch-graph','visual.novel.state-inspector','visual.novel.history-log','visual.novel.save-checkpoint','visual.novel.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.novel.story')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('speaker text',quality)
        self.assertIn('character identity',quality)
        self.assertIn('runtime flags',quality)
        self.assertIn('branching narrative source',quality)
        self.assertIn('dialogue_safe_ratio',vt.get('visual.novel.scene-editor')['math_hooks'])
        self.assertIn('node_spacing_ratio',vt.get('visual.novel.branch-graph')['math_hooks'])

    def test_products_resolve_and_previews_parse(self):
        for pid in PRODUCTS:
            definition=vt.get(pid)
            for width,height in SIZES:
                out=vt.product_resolution(pid,width,height)
                self.assertEqual([x['template']['id'] for x in out['screens']],definition['screens'])
            project=vt.product_project(pid,1280,720)
            svgs=[v for k,v in project['files'].items() if k.endswith('.svg')]
            self.assertEqual(len(svgs),len(definition['screens']))
            for svg in svgs: ElementTree.fromstring(svg)

    def test_registry_installs_all_exact_definitions(self):
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pins=vt.install_builtins(registry)
                self.assertEqual(len(pins),191)
                novel=registry.search(adapter=vt.ADAPTER,tag='novel',limit=100)['entries']
                self.assertEqual(len(novel),10)
                d=registry.get('visual.visual.novel.scene-editor',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_novel_scene_character_dialogue_branch_and_save_contracts(self):
        required={'scene-background','character-stage','dialogue-block','choice-option','branch-node','story-flag','history-entry','save-checkpoint','scene-transition','novel-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['scene-background']['source_and_transform_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['character-stage']['identity_pose_expression_source_required'])
        self.assertTrue(vt.PRIMITIVES['dialogue-block']['speaker_text_voice_ref_exact'])
        self.assertTrue(vt.PRIMITIVES['choice-option']['id_label_target_conditions_required'])
        self.assertTrue(vt.PRIMITIVES['branch-node']['identity_and_edges_required'])
        self.assertTrue(vt.PRIMITIVES['story-flag']['name_value_source_required'])
        self.assertTrue(vt.PRIMITIVES['history-entry']['sequence_and_source_required'])
        self.assertTrue(vt.PRIMITIVES['save-checkpoint']['state_identity_digest_required'])
        self.assertTrue(vt.PRIMITIVES['scene-transition']['from_to_identity_required'])
        self.assertTrue(vt.PRIMITIVES['novel-export-target']['requirements_must_be_visible'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['map-coordinate']['system_source_precision_required'])
        self.assertTrue(vt.PRIMITIVES['relationship-edge']['endpoints_and_relation_type_required'])
        self.assertTrue(vt.PRIMITIVES['source-window']['source_identity_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['title-card']['text_layout_timing_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.novel.scene-editor',1920,1080); b=vt.resolve('visual.novel.scene-editor',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.novel.scene-editor'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.novel.scene-editor')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.novel.scene-editor',1920,1080,variant='unknown')
        bad=vt.get('visual.novel.branch-graph'); bad['variants']['standard']['graph']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

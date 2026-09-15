import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core','visual.broadcast.core','visual.diagram.core','visual.atlas.core','visual.novel.core','visual.showroom.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':20,'primitives':146,'screens':184,'products':18})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.','visual.broadcast.','visual.diagram.','visual.atlas.','visual.novel.','visual.showroom.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11,'visual.cinematic.core':10,'visual.broadcast.core':10,'visual.diagram.core':10,'visual.atlas.core':10,'visual.novel.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_showroom_product_preserves_object_and_presentation_truth(self):
        product=vt.get('visual.showroom.core')
        required={'visual.showroom.project-hub','visual.showroom.object-stage','visual.showroom.orbit-camera','visual.showroom.material-editor','visual.showroom.variant-editor','visual.showroom.annotation-editor','visual.showroom.comparison','visual.showroom.detail-view','visual.showroom.turntable','visual.showroom.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.showroom.studio')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('source asset identity',quality)
        self.assertIn('availability',quality)
        self.assertIn('value, unit and source',quality)
        self.assertIn('showroom source state',quality)
        self.assertIn('hero_coverage_ratio',vt.get('visual.showroom.object-stage')['math_hooks'])
        self.assertIn('detail_coverage_ratio',vt.get('visual.showroom.detail-view')['math_hooks'])

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
                self.assertEqual(len(pins),202)
                showroom=registry.search(adapter=vt.ADAPTER,tag='showroom',limit=100)['entries']
                self.assertEqual(len(showroom),10)
                d=registry.get('visual.visual.showroom.object-stage',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_showroom_object_camera_material_variant_and_measurement_contracts(self):
        required={'showroom-object','orbit-rig','camera-preset','material-slot','variant-option','object-annotation','comparison-object','turntable-state','measurement-callout','showroom-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['showroom-object']['source_identity_version_required'])
        self.assertTrue(vt.PRIMITIVES['orbit-rig']['target_pivot_range_required'])
        self.assertTrue(vt.PRIMITIVES['camera-preset']['projection_lens_transform_required'])
        self.assertTrue(vt.PRIMITIVES['material-slot']['part_material_source_required'])
        self.assertTrue(vt.PRIMITIVES['variant-option']['identity_properties_availability_required'])
        self.assertTrue(vt.PRIMITIVES['object-annotation']['target_anchor_content_required'])
        self.assertTrue(vt.PRIMITIVES['comparison-object']['reference_and_fields_required'])
        self.assertTrue(vt.PRIMITIVES['turntable-state']['target_angle_speed_required'])
        self.assertTrue(vt.PRIMITIVES['measurement-callout']['value_unit_source_required'])
        self.assertTrue(vt.PRIMITIVES['showroom-export-target']['requirements_must_be_visible'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['save-checkpoint']['state_identity_digest_required'])
        self.assertTrue(vt.PRIMITIVES['map-coordinate']['system_source_precision_required'])
        self.assertTrue(vt.PRIMITIVES['relationship-edge']['endpoints_and_relation_type_required'])
        self.assertTrue(vt.PRIMITIVES['source-window']['source_identity_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['title-card']['text_layout_timing_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.showroom.object-stage',1920,1080); b=vt.resolve('visual.showroom.object-stage',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.showroom.object-stage'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.showroom.object-stage')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.showroom.object-stage',1920,1080,variant='unknown')
        bad=vt.get('visual.showroom.object-stage'); bad['variants']['standard']['stage']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

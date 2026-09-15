import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':13,'primitives':76,'screens':113,'products':11})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.')):
                self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_keyart_product_preserves_editable_composition(self):
        product=vt.get('visual.keyart.core')
        required={'visual.keyart.project-hub','visual.keyart.composition-editor','visual.keyart.subject-stage','visual.keyart.type-editor','visual.keyart.lighting-effects','visual.keyart.background-atmosphere','visual.keyart.crop-variants','visual.keyart.variant-board','visual.keyart.review-compare','visual.keyart.export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.keyart.cinematic')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('source composition',quality)
        self.assertIn('exact variants',quality)
        self.assertIn('hero_focus_ratio',vt.get('visual.keyart.composition-editor')['math_hooks'])
        self.assertIn('safe_inset_ratio',vt.get('visual.keyart.crop-variants')['math_hooks'])

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
                self.assertEqual(len(pins),124)
                keyart=registry.search(adapter=vt.ADAPTER,tag='keyart',limit=100)['entries']
                self.assertEqual(len(keyart),10)
                d=registry.get('visual.visual.keyart.composition-editor',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_reusable_state_contracts(self):
        required={'inventory-slot','truth-state','layer-row','speech-bubble','hero-subject','depth-layer','focal-mask','title-lockup','credit-block','lighting-pass','crop-safe-frame','variant-card','export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['hero-subject']['source_and_transform_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['depth-layer']['order_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['focal-mask']['mask_must_not_replace_source_art'])
        self.assertTrue(vt.PRIMITIVES['title-lockup']['text_and_layout_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['lighting-pass']['effect_must_remain_non_authoritative'])
        self.assertTrue(vt.PRIMITIVES['crop-safe-frame']['crop_must_not_modify_source_geometry'])
        self.assertTrue(vt.PRIMITIVES['variant-card']['variant_identity_must_be_exact'])
        self.assertTrue(vt.PRIMITIVES['export-target']['target_requirements_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.keyart.composition-editor',1920,1080); b=vt.resolve('visual.keyart.composition-editor',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.keyart.composition-editor'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.keyart.composition-editor')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.keyart.composition-editor',1920,1080,variant='unknown')
        bad=vt.get('visual.keyart.crop-variants'); bad['variants']['standard']['crops']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

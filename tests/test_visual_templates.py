import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':15,'primitives':96,'screens':134,'products':13})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_cinematic_product_preserves_exact_timed_source_state(self):
        product=vt.get('visual.cinematic.core')
        required={'visual.cinematic.project-hub','visual.cinematic.title-editor','visual.cinematic.chapter-editor','visual.cinematic.lower-third','visual.cinematic.subtitle-editor','visual.cinematic.credits-editor','visual.cinematic.overlay-timeline','visual.cinematic.transition-editor','visual.cinematic.aspect-variants','visual.cinematic.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.cinematic.motion')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('exact names',quality)
        self.assertIn('safe-area',quality)
        self.assertIn('source state',quality)
        self.assertIn('title_safe_ratio',vt.get('visual.cinematic.title-editor')['math_hooks'])
        self.assertIn('subtitle_safe_ratio',vt.get('visual.cinematic.subtitle-editor')['math_hooks'])
        self.assertIn('safe_inset_ratio',vt.get('visual.cinematic.aspect-variants')['math_hooks'])

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
                self.assertEqual(len(pins),147)
                cinematic=registry.search(adapter=vt.ADAPTER,tag='cinematic',limit=100)['entries']
                self.assertEqual(len(cinematic),10)
                d=registry.get('visual.visual.cinematic.title-editor',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_cinematic_source_timing_and_safe_area_contracts(self):
        required={'title-card','lower-third','subtitle-cue','credit-line','time-cue','safe-zone','transition-cue','chapter-marker','overlay-track','logo-lockup'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['title-card']['text_layout_timing_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['lower-third']['content_anchor_duration_explicit'])
        self.assertTrue(vt.PRIMITIVES['subtitle-cue']['text_and_timing_must_be_exact'])
        self.assertTrue(vt.PRIMITIVES['credit-line']['content_and_order_must_remain_exact'])
        self.assertTrue(vt.PRIMITIVES['time-cue']['start_end_required'])
        self.assertTrue(vt.PRIMITIVES['safe-zone']['guide_must_not_rewrite_source_layout'])
        self.assertTrue(vt.PRIMITIVES['transition-cue']['transition_must_not_replace_source_states'])
        self.assertTrue(vt.PRIMITIVES['chapter-marker']['time_and_label_required'])
        self.assertTrue(vt.PRIMITIVES['overlay-track']['overlaps_must_remain_visible'])
        self.assertTrue(vt.PRIMITIVES['logo-lockup']['source_and_transform_remain_separate'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['crop-safe-frame']['crop_must_not_modify_source_geometry'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['inventory-slot']['ownership_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.cinematic.title-editor',1920,1080); b=vt.resolve('visual.cinematic.title-editor',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.cinematic.title-editor'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.cinematic.title-editor')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.cinematic.title-editor',1920,1080,variant='unknown')
        bad=vt.get('visual.cinematic.aspect-variants'); bad['variants']['standard']['variants']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':14,'primitives':86,'screens':124,'products':12})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_card_product_preserves_editable_card_and_deck_state(self):
        product=vt.get('visual.cards.core')
        required={'visual.cards.project-hub','visual.cards.face-editor','visual.cards.back-editor','visual.cards.artwork-editor','visual.cards.text-stats','visual.cards.ability-layout','visual.cards.rarity-style','visual.cards.effects-finish','visual.cards.deck-builder','visual.cards.print-sheet','visual.cards.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.cards.collectible')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('rules text',quality)
        self.assertIn('face and back',quality)
        self.assertIn('print/digital export',quality)
        self.assertIn('artwork_area_ratio',vt.get('visual.cards.face-editor')['math_hooks'])
        self.assertIn('bleed_ratio',vt.get('visual.cards.print-sheet')['math_hooks'])

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
                self.assertEqual(len(pins),136)
                cards=registry.search(adapter=vt.ADAPTER,tag='cards',limit=100)['entries']
                self.assertGreaterEqual(len(cards),12)
                d=registry.get('visual.visual.cards.face-editor',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_card_source_and_output_contracts(self):
        required={'card-frame','artwork-window','stat-block','ability-row','rarity-badge','cost-symbol','card-state','deck-slot','foil-pass','print-safe-frame'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['artwork-window']['source_and_crop_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['stat-block']['label_value_pair_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['ability-row']['rules_text_must_remain_exact'])
        self.assertTrue(vt.PRIMITIVES['rarity-badge']['must_not_depend_on_color'])
        self.assertTrue(vt.PRIMITIVES['cost-symbol']['value_and_resource_type_required'])
        self.assertTrue(vt.PRIMITIVES['card-state']['state_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['deck-slot']['card_reference_must_be_exact'])
        self.assertTrue(vt.PRIMITIVES['foil-pass']['finish_must_not_replace_base_art'])
        self.assertTrue(vt.PRIMITIVES['print-safe-frame']['guide_must_not_mutate_source_layout'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['crop-safe-frame']['crop_must_not_modify_source_geometry'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['inventory-slot']['ownership_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.cards.face-editor',1920,1080); b=vt.resolve('visual.cards.face-editor',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.cards.face-editor'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.cards.face-editor')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.cards.face-editor',1920,1080,variant='unknown')
        bad=vt.get('visual.cards.print-sheet'); bad['variants']['standard']['sheet']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

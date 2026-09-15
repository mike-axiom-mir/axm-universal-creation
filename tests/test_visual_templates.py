import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':12,'primitives':67,'screens':103,'products':10})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(('game.','editor.creative.','comic.narrative.','axm.system.')):
                self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)
        self.assertIn('game.racing.hud.split',vt.get('game.racing.full')['screens'])
        self.assertIn('comic.narrative.dialogue-editor',vt.get('comic.narrative.core')['screens'])

    def test_shared_gameplay_product_covers_near_term_gaps(self):
        product=vt.get('game.shared.core')
        required={'game.shared.inventory','game.shared.skill-tree','game.shared.mission-briefing','game.shared.world-map','game.shared.objective-log','game.shared.upgrade-shop','game.shared.codex','game.shared.revive-overlay','game.shared.boss-encounter-hud','game.shared.spectator','game.shared.end-session-summary','game.shared.challenge-board'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'game.shared.adventure')
        self.assertIn('revive-expired',{c for _,_,c in product['flow']})
        self.assertIn('encounter-complete',{c for _,_,c in product['flow']})

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
                self.assertEqual(len(pins),113)
                self.assertEqual(len(registry.search(adapter=vt.ADAPTER,tag='axm',limit=100)['entries']),12)
                shared=registry.search(adapter=vt.ADAPTER,tag='shared',limit=100)['entries']
                self.assertGreaterEqual(len(shared),12)
                d=registry.get('visual.game.shared.inventory',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_reusable_state_contracts(self):
        required={'truth-state','registry-entry','layer-row','speech-bubble','inventory-slot','skill-node','objective-row','shop-offer','codex-entry','revive-state','boss-phase','spectator-seat','challenge-card','session-stat'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['inventory-slot']['ownership_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['skill-node']['prerequisites_and_cost_must_be_visible'])
        self.assertTrue(vt.PRIMITIVES['codex-entry']['undiscovered_content_must_not_be_faked'])
        self.assertTrue(vt.PRIMITIVES['revive-state']['timer_and_actor_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['boss-phase']['phase_change_needs_non_color_cue'])
        self.assertTrue(vt.PRIMITIVES['challenge-card']['progress_and_reward_must_be_explicit'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('game.shared.inventory',1920,1080); b=vt.resolve('game.shared.inventory',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('game.shared.inventory'); copy['name']='changed'
        self.assertNotEqual(vt.get('game.shared.inventory')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('game.shared.inventory',1920,1080,variant='unknown')
        bad=vt.get('game.shared.world-map'); bad['variants']['standard']['map']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

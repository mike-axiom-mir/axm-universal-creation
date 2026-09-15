import json
from pathlib import Path
import sys
import tempfile
import unittest
from xml.etree import ElementTree

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt


SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]


class VisualTemplateTests(unittest.TestCase):
    def test_catalog_is_valid_and_professional_pack_is_present(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':7,'primitives':24,'screens':39,'products':5})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        products={p['id'] for p in vt.catalog()['products']}
        self.assertTrue({'game.racing.performance','game.racing.full','game.coop.action','game.rts.command','software.creator.studio'} <= products)

    def test_all_resolutions_stay_in_viewport(self):
        for tid in vt.SCREEN_TEMPLATES:
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for box in out['regions'].values():
                    x,y,w,h=box
                    self.assertGreaterEqual(x,0); self.assertGreaterEqual(y,0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_game_screens_supply_all_three_responsive_variants(self):
        for tid,screen in vt.SCREEN_TEMPLATES.items():
            if tid.startswith('game.'):
                self.assertEqual(set(screen['variants']),{'compact','standard','wide'},tid)

    def test_deterministic_copy_safe_and_strict_variant(self):
        a=vt.resolve('game.racing.hud.performance',1920,1080)
        b=vt.resolve('game.racing.hud.performance',1920,1080)
        self.assertEqual(a,b)
        got=vt.get('game.racing.hud.performance'); got['name']='mutated'
        self.assertNotEqual(vt.get('game.racing.hud.performance')['name'],'mutated')
        with self.assertRaises(ValueError):
            vt.resolve('game.racing.hud.performance',1920,1080,variant='unknown')

    def test_full_racing_product_has_professional_shell(self):
        product=vt.get('game.racing.full')
        self.assertEqual(len(product['screens']),19)
        required={
            'game.racing.home','game.racing.vehicle-select','game.racing.tuning','game.racing.livery',
            'game.racing.pre-race','game.racing.loading','game.racing.countdown','game.racing.hud.performance',
            'game.racing.hud.split','game.racing.recovery','game.racing.results','game.racing.replay',
            'game.racing.season','game.racing.settings','game.racing.accessibility',
        }
        self.assertTrue(required <= set(product['screens']))
        flow={(a,b,action) for a,b,action in product['flow']}
        self.assertIn(('game.racing.loading','game.racing.countdown','ready'),flow)
        self.assertIn(('game.racing.countdown','game.racing.hud.performance','start-race'),flow)
        self.assertIn(('game.racing.hud.performance','game.racing.recovery','connection-loss'),flow)

    def test_game_products_resolve_exact_screens_across_viewports(self):
        for product_id in ('game.racing.full','game.coop.action','game.rts.command'):
            product=vt.get(product_id)
            for width,height in SIZES:
                out=vt.product_resolution(product_id,width,height)
                self.assertEqual([x['template']['id'] for x in out['screens']],product['screens'])
                self.assertEqual(len(out['flow']),len(product['flow']))

    def test_preview_projects_are_parseable(self):
        screen=vt.screen_project('game.racing.hud.performance',1280,720)
        ElementTree.fromstring(screen['files']['screen.svg'])
        json.loads(screen['files']['template.json'])
        for product_id in ('game.racing.full','game.coop.action','game.rts.command'):
            product=vt.product_project(product_id,1280,720)
            svgs=[name for name in product['files'] if name.endswith('.svg')]
            self.assertEqual(len(svgs),len(vt.get(product_id)['screens']))
            for name in svgs: ElementTree.fromstring(product['files'][name])

    def test_builtins_install_in_existing_sticker_registry(self):
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pins=vt.install_builtins(registry)
                self.assertEqual(len(pins),44)
                racing=registry.search(adapter=vt.ADAPTER,tag='racing',limit=100)['entries']
                game=registry.search(adapter=vt.ADAPTER,tag='game',limit=100)['entries']
                self.assertGreaterEqual(len(racing),19)
                self.assertGreaterEqual(len(game),34)
                definition=registry.get('visual.game.racing.hud.performance',1)
                self.assertEqual(definition['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(definition,sort_keys=True))

    def test_reusable_game_primitives_cover_mature_product_states(self):
        required={
            'player-seat','selection-card','stat-comparison','slider-row','countdown','loading-state',
            'recovery-banner','telemetry-strip','input-hint','modal','empty-state','tab-strip',
        }
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['loading-state']['fake_progress_forbidden'])
        self.assertTrue(vt.PRIMITIVES['player-seat']['ownership_must_be_explicit'])

    def test_slot_binding_requires_exact_pin_and_contract(self):
        definition={
            'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster',
            'tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},
            'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},
            'recipe':{},'assets':{},'parameters':{},
        }
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(definition)
                bound=vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})
                self.assertEqual(bound['bindings']['speed-cluster'],pin)
                bad=dict(pin); bad['digest']='0'*64
                with self.assertRaises(ValueError):
                    vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':bad})

    def test_bad_geometry_fails(self):
        d=vt.get('game.racing.hud.performance')
        d['variants']['standard']['speed']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(d)


if __name__=='__main__': unittest.main()

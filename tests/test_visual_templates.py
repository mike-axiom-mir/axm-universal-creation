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


class VisualTemplateTests(unittest.TestCase):
    def test_catalog_is_valid_and_broad(self):
        counts=vt.validate_catalog()
        self.assertGreaterEqual(counts['screens'],10)
        self.assertGreaterEqual(counts['products'],2)
        self.assertGreaterEqual(counts['styles'],5)
        self.assertIn('game.racing.performance',[p['id'] for p in vt.catalog()['products']])

    def test_all_resolutions_stay_in_viewport(self):
        sizes=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
        for tid in vt.SCREEN_TEMPLATES:
            for width,height in sizes:
                out=vt.resolve(tid,width,height)
                for box in out['regions'].values():
                    x,y,w,h=box
                    self.assertGreaterEqual(x,0); self.assertGreaterEqual(y,0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_deterministic_copy_safe_and_strict_variant(self):
        a=vt.resolve('game.racing.hud.performance',1920,1080)
        b=vt.resolve('game.racing.hud.performance',1920,1080)
        self.assertEqual(a,b)
        got=vt.get('game.racing.hud.performance'); got['name']='mutated'
        self.assertNotEqual(vt.get('game.racing.hud.performance')['name'],'mutated')
        with self.assertRaises(ValueError):
            vt.resolve('game.racing.hud.performance',1920,1080,variant='unknown')

    def test_whole_product_resolves_exact_screens(self):
        out=vt.product_resolution('game.racing.performance',1920,1080)
        product=vt.get('game.racing.performance')
        self.assertEqual([x['template']['id'] for x in out['screens']],product['screens'])
        self.assertEqual(len(out['flow']),len(product['flow']))

    def test_preview_projects_are_parseable(self):
        screen=vt.screen_project('game.racing.hud.performance',1280,720)
        ElementTree.fromstring(screen['files']['screen.svg'])
        json.loads(screen['files']['template.json'])
        product=vt.product_project('game.racing.performance',1280,720)
        svgs=[name for name in product['files'] if name.endswith('.svg')]
        self.assertEqual(len(svgs),len(vt.get('game.racing.performance')['screens']))
        for name in svgs: ElementTree.fromstring(product['files'][name])

    def test_builtins_install_in_existing_sticker_registry(self):
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pins=vt.install_builtins(registry)
                self.assertEqual(len(pins),len(vt.SCREEN_TEMPLATES)+len(vt.PRODUCT_ARCHETYPES))
                found=registry.search(adapter=vt.ADAPTER,tag='racing',limit=100)['entries']
                self.assertGreaterEqual(len(found),6)
                definition=registry.get('visual.game.racing.hud.performance',1)
                self.assertEqual(definition['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(definition,sort_keys=True))

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

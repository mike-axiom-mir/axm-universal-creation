import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','editor.creative.core','comic.narrative.core','axm.system.shell')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':11,'primitives':57,'screens':91,'products':9})
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
                    self.assertLessEqual(x+w,width+1e-6)
                    self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        self.assertEqual(len(vt.get('game.racing.full')['screens']),19)
        self.assertEqual(len(vt.get('game.system.shell')['screens']),18)
        self.assertEqual(len(vt.get('editor.creative.core')['screens']),12)
        self.assertEqual(len(vt.get('comic.narrative.core')['screens']),10)
        self.assertIn('game.racing.hud.split',vt.get('game.racing.full')['screens'])
        self.assertIn('game.system.privacy-consent',vt.get('game.system.shell')['screens'])
        self.assertIn('editor.creative.node-graph',vt.get('editor.creative.core')['screens'])
        self.assertIn('comic.narrative.dialogue-editor',vt.get('comic.narrative.core')['screens'])

    def test_axm_system_shell(self):
        product=vt.get('axm.system.shell')
        required={'axm.system.home','axm.system.registry','axm.system.capability-browser','axm.system.cartridge-loader','axm.system.machine-state','axm.system.evidence-review','axm.system.workflow','axm.system.specialists','axm.system.workfloor','axm.system.snapshots','axm.system.settings','axm.system.recovery'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'axm.machine.glass')
        flow={(a,b,c) for a,b,c in product['flow']}
        self.assertIn(('axm.system.cartridge-loader','axm.system.machine-state','inspect-state'),flow)
        self.assertIn(('axm.system.snapshots','axm.system.recovery','recover'),flow)

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
                self.assertEqual(len(pins),100)
                self.assertEqual(len(registry.search(adapter=vt.ADAPTER,tag='axm',limit=100)['entries']),12)
                self.assertEqual(len(registry.search(adapter=vt.ADAPTER,tag='comic',limit=100)['entries']),10)
                d=registry.get('visual.axm.system.registry',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_reusable_state_contracts(self):
        required={'player-seat','loading-state','layer-row','timeline-track','node-card','speech-bubble','reading-order-marker','truth-state','capability-card','registry-entry','evidence-chip','state-diff','cartridge-card','specialist-card','workfloor-lane','snapshot-entry','recovery-choice'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])
        self.assertTrue(vt.PRIMITIVES['registry-entry']['no_floating_latest'])
        self.assertTrue(vt.PRIMITIVES['snapshot-entry']['restore_is_explicit'])
        self.assertTrue(vt.PRIMITIVES['recovery-choice']['consequence_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('axm.system.home',1920,1080); b=vt.resolve('axm.system.home',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('axm.system.home'); copy['name']='changed'
        self.assertNotEqual(vt.get('axm.system.home')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('axm.system.home',1920,1080,variant='unknown')
        bad=vt.get('axm.system.registry'); bad['variants']['standard']['entries']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

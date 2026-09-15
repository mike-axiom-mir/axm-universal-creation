import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core','visual.broadcast.core','visual.diagram.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':17,'primitives':116,'screens':154,'products':15})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.','visual.broadcast.','visual.diagram.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11,'visual.cinematic.core':10,'visual.broadcast.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_diagram_product_preserves_semantic_evidence_truth(self):
        product=vt.get('visual.diagram.core')
        required={'visual.diagram.project-hub','visual.diagram.canvas-editor','visual.diagram.node-editor','visual.diagram.relationship-editor','visual.diagram.evidence-editor','visual.diagram.annotation-editor','visual.diagram.legend-style','visual.diagram.layout-variants','visual.diagram.review-compare','visual.diagram.export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.diagram.evidence')
        quality=' '.join(product['quality']).lower()
        self.assertIn('visual adjacency',quality)
        self.assertIn('relationship direction',quality)
        self.assertIn('missing evidence',quality)
        self.assertIn('semantic relationships',quality)
        self.assertIn('node_spacing_ratio',vt.get('visual.diagram.canvas-editor')['math_hooks'])
        self.assertIn('group_gap_ratio',vt.get('visual.diagram.layout-variants')['math_hooks'])

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
                self.assertEqual(len(pins),169)
                diagram=registry.search(adapter=vt.ADAPTER,tag='diagram',limit=100)['entries']
                self.assertEqual(len(diagram),10)
                d=registry.get('visual.visual.diagram.canvas-editor',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_diagram_semantic_evidence_and_layout_contracts(self):
        required={'diagram-node','relationship-edge','evidence-reference','data-field','annotation-pin','legend-entry','group-boundary','layout-guide','callout-card','diagram-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['diagram-node']['identity_must_be_exact'])
        self.assertTrue(vt.PRIMITIVES['relationship-edge']['endpoints_and_relation_type_required'])
        self.assertTrue(vt.PRIMITIVES['evidence-reference']['source_and_status_required'])
        self.assertTrue(vt.PRIMITIVES['data-field']['value_unit_source_period_required'])
        self.assertTrue(vt.PRIMITIVES['annotation-pin']['target_reference_must_be_exact'])
        self.assertTrue(vt.PRIMITIVES['legend-entry']['meaning_must_not_depend_on_color_only'])
        self.assertTrue(vt.PRIMITIVES['group-boundary']['membership_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['layout-guide']['guide_must_not_change_semantic_relationships'])
        self.assertTrue(vt.PRIMITIVES['callout-card']['content_and_evidence_status_separate'])
        self.assertTrue(vt.PRIMITIVES['diagram-export-target']['target_requirements_must_be_visible'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['source-window']['source_identity_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['title-card']['text_layout_timing_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['crop-safe-frame']['crop_must_not_modify_source_geometry'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['inventory-slot']['ownership_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.diagram.canvas-editor',1920,1080); b=vt.resolve('visual.diagram.canvas-editor',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.diagram.canvas-editor'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.diagram.canvas-editor')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.diagram.canvas-editor',1920,1080,variant='unknown')
        bad=vt.get('visual.diagram.layout-variants'); bad['variants']['standard']['variants']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

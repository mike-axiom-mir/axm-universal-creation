import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core','visual.broadcast.core','visual.diagram.core','visual.atlas.core','visual.novel.core','visual.showroom.core','visual.music.core','visual.presentation.core','visual.character.core','visual.configurator.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':24,'primitives':186,'screens':224,'products':22})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.','visual.broadcast.','visual.diagram.','visual.atlas.','visual.novel.','visual.showroom.','visual.music.','visual.presentation.','visual.character.','visual.configurator.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11,'visual.cinematic.core':10,'visual.broadcast.core':10,'visual.diagram.core':10,'visual.atlas.core':10,'visual.novel.core':10,'visual.showroom.core':10,'visual.music.core':10,'visual.presentation.core':10,'visual.character.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_character_product_preserves_identity_measurement_and_reference_truth(self):
        product=vt.get('visual.character.core')
        required={'visual.character.project-hub','visual.character.turnaround','visual.character.proportions','visual.character.expressions','visual.character.poses','visual.character.materials','visual.character.callouts','visual.character.scale-variants','visual.character.reference-board','visual.character.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.character.reference')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('canonical character/creature identity',quality)
        self.assertIn('unit, source and precision/assumption state',quality)
        self.assertIn('exact anatomical, gear or feature targets',quality)
        self.assertIn('richer character source state',quality)
        self.assertIn('figure_height_ratio',vt.get('visual.character.turnaround')['math_hooks'])

    def test_configurator_product_preserves_source_configuration_truth(self):
        product=vt.get('visual.configurator.core')
        required={'visual.configurator.project-hub','visual.configurator.object-stage','visual.configurator.socket-editor','visual.configurator.exploded-view','visual.configurator.stat-editor','visual.configurator.variant-material','visual.configurator.compatibility','visual.configurator.comparison','visual.configurator.loadout-presets','visual.configurator.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.configurator.precision')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('source object or equipped configuration',quality)
        self.assertIn('compatibility stays explicit',quality)
        self.assertIn('unit, source and configuration context/version state',quality)
        self.assertIn('richer configuration source state',quality)
        self.assertIn('hero_coverage_ratio',vt.get('visual.configurator.object-stage')['math_hooks'])
        self.assertIn('explode_spread_ratio',vt.get('visual.configurator.exploded-view')['math_hooks'])

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
                self.assertEqual(len(pins),246)
                configurator=registry.search(adapter=vt.ADAPTER,tag='configurator',limit=100)['entries']
                self.assertEqual(len(configurator),10)
                expected={f'visual.visual.configurator.{name}' for name in ('project-hub','object-stage','socket-editor','exploded-view','stat-editor','variant-material','compatibility','comparison','loadout-presets','review-export')}
                self.assertEqual(expected,{entry['id'] for entry in configurator})
                d=registry.get('visual.visual.configurator.object-stage',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_configurator_source_socket_component_compatibility_and_stat_contracts(self):
        required={'configurable-source','attachment-socket','component-part','compatibility-rule','config-stat-field','configuration-state','exploded-view-state','config-material-variant','config-annotation','configurator-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['configurable-source']['identity_source_version_required'])
        self.assertTrue(vt.PRIMITIVES['attachment-socket']['socket_identity_type_status_required'])
        self.assertTrue(vt.PRIMITIVES['component-part']['source_parent_transform_required'])
        self.assertTrue(vt.PRIMITIVES['compatibility-rule']['subject_target_rule_status_required'])
        self.assertTrue(vt.PRIMITIVES['config-stat-field']['value_unit_source_context_required'])
        self.assertTrue(vt.PRIMITIVES['configuration-state']['base_attachment_variant_digest_required'])
        self.assertTrue(vt.PRIMITIVES['exploded-view-state']['source_part_offset_non_authoritative'])
        self.assertTrue(vt.PRIMITIVES['config-material-variant']['target_variant_source_availability_required'])
        self.assertTrue(vt.PRIMITIVES['config-annotation']['target_content_source_required'])
        self.assertTrue(vt.PRIMITIVES['configurator-export-target']['requirements_must_be_visible'])

    def test_character_source_view_measurement_material_scale_and_export_contracts(self):
        required={'character-source','turnaround-view','proportion-guide','expression-state','pose-reference','character-material','character-callout','scale-reference','character-variant','reference-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['character-source']['identity_source_version_required'])
        self.assertTrue(vt.PRIMITIVES['turnaround-view']['identity_view_camera_required'])
        self.assertTrue(vt.PRIMITIVES['proportion-guide']['anchors_value_unit_source_required'])
        self.assertTrue(vt.PRIMITIVES['expression-state']['identity_name_source_required'])
        self.assertTrue(vt.PRIMITIVES['pose-reference']['identity_pose_source_required'])
        self.assertTrue(vt.PRIMITIVES['character-material']['part_material_source_required'])
        self.assertTrue(vt.PRIMITIVES['character-callout']['target_content_source_required'])
        self.assertTrue(vt.PRIMITIVES['scale-reference']['reference_value_unit_source_required'])
        self.assertTrue(vt.PRIMITIVES['character-variant']['base_delta_status_required'])
        self.assertTrue(vt.PRIMITIVES['reference-export-target']['requirements_must_be_visible'])

    def test_prior_source_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['presentation-page']['identity_role_order_required'])
        self.assertTrue(vt.PRIMITIVES['music-track-source']['identity_source_digest_duration_required'])
        self.assertTrue(vt.PRIMITIVES['showroom-object']['source_identity_version_required'])
        self.assertTrue(vt.PRIMITIVES['save-checkpoint']['state_identity_digest_required'])
        self.assertTrue(vt.PRIMITIVES['map-coordinate']['system_source_precision_required'])
        self.assertTrue(vt.PRIMITIVES['relationship-edge']['endpoints_and_relation_type_required'])
        self.assertTrue(vt.PRIMITIVES['source-window']['source_identity_must_be_explicit'])
        self.assertTrue(vt.PRIMITIVES['title-card']['text_layout_timing_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'])
        self.assertTrue(vt.PRIMITIVES['speech-bubble']['text_and_tail_remain_separate'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.configurator.object-stage',1920,1080); b=vt.resolve('visual.configurator.object-stage',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.configurator.object-stage'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.configurator.object-stage')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.configurator.object-stage',1920,1080,variant='unknown')
        bad=vt.get('visual.configurator.object-stage'); bad['variants']['standard']['stage']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

import json
from pathlib import Path
import sys,tempfile,unittest
from xml.etree import ElementTree
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'src'))
from axm_stickers import Registry
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=('game.racing.full','game.coop.action','game.rts.command','game.system.shell','game.shared.core','editor.creative.core','comic.narrative.core','axm.system.shell','visual.keyart.core','visual.cards.core','visual.cinematic.core','visual.broadcast.core','visual.diagram.core','visual.atlas.core','visual.novel.core','visual.showroom.core','visual.music.core','visual.presentation.core','visual.character.core','visual.configurator.core','visual.motion.core','visual.brand.core','visual.environment.core','visual.vfx.core','visual.mission.core','visual.hud.core','visual.look.core','visual.camera.core','visual.inventory.core')

class VisualTemplateTests(unittest.TestCase):
    def test_catalog_counts_and_products(self):
        counts=vt.validate_catalog()
        self.assertEqual(counts,{'styles':33,'primitives':276,'screens':314,'products':31})
        self.assertEqual(vt.CATALOG_COMPOSITION['counts'],counts)
        ids={p['id'] for p in vt.catalog()['products']}
        self.assertTrue(set(PRODUCTS)|{'game.racing.performance','software.creator.studio'} <= ids)

    def test_all_geometry_and_major_variants(self):
        prefixes=('game.','editor.creative.','comic.narrative.','axm.system.','visual.keyart.','visual.cards.','visual.cinematic.','visual.broadcast.','visual.diagram.','visual.atlas.','visual.novel.','visual.showroom.','visual.music.','visual.presentation.','visual.character.','visual.configurator.','visual.motion.','visual.brand.','visual.environment.','visual.vfx.','visual.mission.','visual.hud.','visual.look.','visual.camera.','visual.inventory.')
        for tid,definition in vt.SCREEN_TEMPLATES.items():
            if tid.startswith(prefixes): self.assertEqual(set(definition['variants']),{'compact','standard','wide'},tid)
            for width,height in SIZES:
                out=vt.resolve(tid,width,height)
                for x,y,w,h in out['regions'].values():
                    self.assertGreaterEqual(min(x,y,w,h),0)
                    self.assertLessEqual(x+w,width+1e-6); self.assertLessEqual(y+h,height+1e-6)

    def test_existing_product_depth_is_retained(self):
        expected={'game.racing.full':19,'game.system.shell':18,'game.shared.core':12,'editor.creative.core':12,'comic.narrative.core':10,'axm.system.shell':12,'visual.keyart.core':10,'visual.cards.core':11,'visual.cinematic.core':10,'visual.broadcast.core':10,'visual.diagram.core':10,'visual.atlas.core':10,'visual.novel.core':10,'visual.showroom.core':10,'visual.music.core':10,'visual.presentation.core':10,'visual.character.core':10,'visual.configurator.core':10,'visual.motion.core':10,'visual.brand.core':10,'visual.environment.core':10,'visual.vfx.core':10,'visual.mission.core':10,'visual.hud.core':10,'visual.look.core':10,'visual.camera.core':10}
        for pid,count in expected.items(): self.assertEqual(len(vt.get(pid)['screens']),count)

    def test_camera_product_preserves_rig_target_lens_and_authority_truth(self):
        product=vt.get('visual.camera.core')
        required={'visual.camera.project-hub','visual.camera.rig-editor','visual.camera.target-framing','visual.camera.lens-fov','visual.camera.constraints','visual.camera.transitions','visual.camera.runtime-bindings','visual.camera.platform-variants','visual.camera.compare-preview','visual.camera.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.camera.system')
        quality=' '.join(product['quality']).lower()
        self.assertIn('never silently moves world objects or rewrites authoritative transforms',quality)
        self.assertIn('fov_degrees',vt.get('visual.camera.lens-fov')['math_hooks'])

    def test_inventory_product_preserves_identity_ownership_and_stat_truth(self):
        product=vt.get('visual.inventory.core')
        required={'visual.inventory.project-hub','visual.inventory.item-inspector','visual.inventory.grid-containers','visual.inventory.equipment-slots','visual.inventory.stats-condition','visual.inventory.compatibility','visual.inventory.comparison','visual.inventory.presentation-variants','visual.inventory.ownership-history','visual.inventory.review-export'}
        self.assertEqual(set(product['screens']),required)
        self.assertEqual(product['style'],'visual.inventory.system')
        quality=' '.join(product['quality']).lower()
        self.assertIn('separately editable',quality)
        self.assertIn('never proves item ownership, rarity, equip state or compatibility',quality)
        self.assertIn('never silently changes authoritative inventory or loadout state',quality)
        self.assertIn('exact unit, source and configuration/context',quality)
        self.assertIn('gameplay semantics',quality)
        self.assertIn('item_coverage_ratio',vt.get('visual.inventory.item-inspector')['math_hooks'])

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
                self.assertEqual(len(pins),345)
                inventory=registry.search(adapter=vt.ADAPTER,tag='inventory',limit=100)['entries']
                expected={f'visual.visual.inventory.{name}' for name in ('project-hub','item-inspector','grid-containers','equipment-slots','stats-condition','compatibility','comparison','presentation-variants','ownership-history','review-export')}
                self.assertTrue(expected <= {entry['id'] for entry in inventory})
                d=registry.get('visual.visual.inventory.item-inspector',1)
                self.assertEqual(d['recipe']['visual_template']['schema'],vt.SCHEMA)
                self.assertNotIn('"latest"',json.dumps(d,sort_keys=True))

    def test_inventory_source_instance_stack_durability_slot_compatibility_stat_variant_contracts(self):
        required={'item-source','inventory-instance','item-stack-state','item-durability-state','equipment-slot','item-compatibility-rule','item-stat-field','item-presentation-variant','item-comparison-state','inventory-export-target'}
        self.assertTrue(required <= set(vt.PRIMITIVES))
        self.assertTrue(vt.PRIMITIVES['item-source']['identity_source_version_owner_required'])
        self.assertTrue(vt.PRIMITIVES['inventory-instance']['item_instance_owner_status_required'])
        self.assertTrue(vt.PRIMITIVES['item-stack-state']['item_quantity_capacity_source_required'])
        self.assertTrue(vt.PRIMITIVES['item-durability-state']['value_range_unit_source_required'])
        self.assertTrue(vt.PRIMITIVES['equipment-slot']['slot_category_occupancy_source_required'])
        self.assertTrue(vt.PRIMITIVES['item-compatibility-rule']['subjects_rule_result_source_required'])
        self.assertTrue(vt.PRIMITIVES['item-stat-field']['value_unit_source_context_required'])
        self.assertTrue(vt.PRIMITIVES['item-presentation-variant']['base_delta_context_source_required'])
        self.assertTrue(vt.PRIMITIVES['item-comparison-state']['item_refs_fields_source_required'])
        self.assertTrue(vt.PRIMITIVES['inventory-export-target']['requirements_must_be_visible'])

    def test_camera_look_hud_mission_vfx_environment_and_prior_boundaries_remain_present(self):
        self.assertTrue(vt.PRIMITIVES['camera-source']['identity_source_version_owner_required'])
        self.assertTrue(vt.PRIMITIVES['camera-runtime-binding']['state_camera_source_authority_required'])
        self.assertTrue(vt.PRIMITIVES['look-source']['identity_source_version_context_required'])
        self.assertTrue(vt.PRIMITIVES['scene-look-binding']['target_look_source_activation_required'])
        self.assertTrue(vt.PRIMITIVES['hud-source']['identity_source_version_context_required'])
        self.assertTrue(vt.PRIMITIVES['hud-data-binding']['subject_field_source_freshness_required'])
        self.assertTrue(vt.PRIMITIVES['mission-source']['identity_source_version_context_required'])
        self.assertTrue(vt.PRIMITIVES['objective-state']['identity_type_status_source_required'])
        self.assertTrue(vt.PRIMITIVES['vfx-source']['identity_source_version_purpose_required'])
        self.assertTrue(vt.PRIMITIVES['vfx-interaction-hook']['subject_event_response_source_required'])
        self.assertTrue(vt.PRIMITIVES['environment-source']['identity_source_version_scope_required'])
        self.assertTrue(vt.PRIMITIVES['environment-measurement']['value_unit_source_precision_required'])
        self.assertTrue(vt.PRIMITIVES['brand-asset-source']['identity_source_version_provenance_required'])
        self.assertTrue(vt.PRIMITIVES['motion-state']['source_target_identity_required'])
        self.assertTrue(vt.PRIMITIVES['configuration-state']['base_attachment_variant_digest_required'])
        self.assertTrue(vt.PRIMITIVES['character-source']['identity_source_version_required'])
        self.assertTrue(vt.PRIMITIVES['presentation-page']['identity_role_order_required'])
        self.assertTrue(vt.PRIMITIVES['music-track-source']['identity_source_digest_duration_required'])
        self.assertTrue(vt.PRIMITIVES['showroom-object']['source_identity_version_required'])
        self.assertTrue(vt.PRIMITIVES['save-checkpoint']['state_identity_digest_required'])
        self.assertTrue(vt.PRIMITIVES['map-coordinate']['system_source_precision_required'])
        self.assertTrue(vt.PRIMITIVES['relationship-edge']['endpoints_and_relation_type_required'])
        self.assertTrue(vt.PRIMITIVES['truth-state']['source_must_be_visible'])

    def test_copy_safety_variant_rejection_and_bad_geometry(self):
        a=vt.resolve('visual.inventory.item-inspector',1920,1080); b=vt.resolve('visual.inventory.item-inspector',1920,1080)
        self.assertEqual(a,b)
        copy=vt.get('visual.inventory.item-inspector'); copy['name']='changed'
        self.assertNotEqual(vt.get('visual.inventory.item-inspector')['name'],'changed')
        with self.assertRaises(ValueError): vt.resolve('visual.inventory.item-inspector',1920,1080,variant='unknown')
        bad=vt.get('visual.inventory.item-inspector'); bad['variants']['standard']['preview']=[.9,.9,.2,.2]
        with self.assertRaises(ValueError): vt.validate_screen(bad)

    def test_exact_sticker_slot_binding_is_retained(self):
        d={'schema':'axm.sticker/v1','id':'test-speed-cluster','version':1,'name':'Test speed cluster','tags':['hud','metric'],'origin':{'author':'test','license':'test','source':'test'},'adapter':'test/v1','attachment':{'space':'2d','socket':'surface','anchor':[0,0]},'recipe':{},'assets':{},'parameters':{}}
        with tempfile.TemporaryDirectory() as td:
            with Registry(Path(td)/'stickers.sqlite') as registry:
                pin=registry.register(d)
                self.assertEqual(vt.bind_sticker_slots('game.racing.hud.performance',registry,{'speed-cluster':pin})['bindings']['speed-cluster'],pin)

if __name__=='__main__': unittest.main()

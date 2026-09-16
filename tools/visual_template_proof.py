#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core","visual.cinematic.core","visual.broadcast.core","visual.diagram.core","visual.atlas.core","visual.novel.core","visual.showroom.core","visual.music.core","visual.presentation.core","visual.character.core","visual.configurator.core","visual.motion.core","visual.brand.core","visual.environment.core","visual.vfx.core","visual.mission.core","visual.hud.core","visual.look.core","visual.camera.core","visual.inventory.core")

def _write(project,target):
    target.mkdir(); out=[]
    for name,body in project['files'].items():
        path=target/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(body,encoding='utf-8')
        if name.endswith('.svg'): ElementTree.fromstring(body)
        out.append(str(path))
    return out

def main(argv):
    if len(argv)!=2: raise SystemExit('usage: python tools/visual_template_proof.py NEW_OUTPUT_DIRECTORY')
    out=Path(argv[1])
    if out.exists(): raise SystemExit('output path already exists')
    out.mkdir(parents=True)
    try:
        counts=vt.validate_catalog()
        if counts!={'styles':33,'primitives':276,'screens':314,'products':31}: raise AssertionError(counts)
        evidence=[]
        for pid in PRODUCTS:
            expected=vt.get(pid)
            for width,height in SIZES:
                resolved=vt.product_resolution(pid,width,height)
                if [x['template']['id'] for x in resolved['screens']]!=expected['screens']: raise AssertionError('screen order drift '+pid)
                for row in resolved['screens']:
                    for name,(x,y,w,h) in row['regions'].items():
                        if min(x,y,w,h)<0 or x+w>width+1e-6 or y+h>height+1e-6: raise AssertionError(f"out of bounds {row['template']['id']} {name}")
                evidence.append({'product':pid,'viewport':[width,height],'screens':len(resolved['screens']),'flow_edges':len(resolved['flow'])})
        galleries=(
            ('game.racing.full',1920,1080,'racing-full','AXM Full Racing Foundation'),('game.coop.action',1280,720,'coop-action','AXM Co-op Action Foundation'),('game.rts.command',1920,1080,'rts-command','AXM RTS Command Foundation'),('game.system.shell',1280,720,'game-system','AXM Shared Game-System Foundation'),('game.shared.core',1920,1080,'game-shared','AXM Shared Gameplay Systems'),('editor.creative.core',1920,1080,'creative-editor','AXM Creative Editor Foundation'),('comic.narrative.core',1920,1080,'comic-narrative','AXM Editable Comic Foundation'),('axm.system.shell',1920,1080,'axm-system','AXM System Shell Foundation'),('visual.keyart.core',1920,1080,'keyart','AXM Editable Key Art Foundation'),('visual.cards.core',1920,1080,'cards','AXM Editable Card and Deck Foundation'),('visual.cinematic.core',1920,1080,'cinematic','AXM Cinematic Title and Overlay Foundation'),('visual.broadcast.core',1920,1080,'broadcast','AXM Video and Stream Overlay Foundation'),('visual.diagram.core',1920,1080,'diagram','AXM Evidence-Aware Diagram Foundation'),('visual.atlas.core',1920,1080,'atlas','AXM World-Map and Lore-Atlas Foundation'),('visual.novel.core',1920,1080,'visual-novel','AXM Branching Visual-Novel Foundation'),('visual.showroom.core',1920,1080,'showroom','AXM 3D Showroom and Gallery Foundation'),('visual.music.core',1920,1080,'music','AXM Music Visualizer and Album-Art Foundation'),('visual.presentation.core',1920,1080,'presentation','AXM Presentation and Explainer Foundation'),('visual.character.core',1920,1080,'character-reference','AXM Character and Creature Reference Foundation'),('visual.configurator.core',1920,1080,'configurator','AXM Equipment and Vehicle Configurator Foundation'),('visual.motion.core',1920,1080,'motion','AXM Source-Bound UI Motion Foundation'),('visual.brand.core',1920,1080,'brand','AXM Source-Bound Brand Identity Foundation'),('visual.environment.core',1920,1080,'environment','AXM Environment and Level Reference Foundation'),('visual.vfx.core',1920,1080,'vfx','AXM VFX and Particle Foundation'),('visual.mission.core',1920,1080,'mission','AXM Quest and Mission Flow Foundation'),('visual.hud.core',1920,1080,'hud','AXM Source-Bound HUD Theme Foundation'),('visual.look.core',1920,1080,'lighting-look','AXM Lighting and Post-Process Look Foundation'),('visual.camera.core',1920,1080,'camera','AXM Camera and Shot Reference Foundation'),('visual.inventory.core',1920,1080,'inventory','AXM Inventory and Item Reference Foundation'))
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        product=vt.get('visual.inventory.core')
        required={'visual.inventory.project-hub','visual.inventory.item-inspector','visual.inventory.grid-containers','visual.inventory.equipment-slots','visual.inventory.stats-condition','visual.inventory.compatibility','visual.inventory.comparison','visual.inventory.presentation-variants','visual.inventory.ownership-history','visual.inventory.review-export'}
        if set(product['screens'])!=required: raise AssertionError('inventory pack lost required surfaces')
        checks={
            'item_identity_source_owner':vt.PRIMITIVES['item-source']['identity_source_version_owner_required'],
            'instance_item_owner_status':vt.PRIMITIVES['inventory-instance']['item_instance_owner_status_required'],
            'stack_quantity_capacity_source':vt.PRIMITIVES['item-stack-state']['item_quantity_capacity_source_required'],
            'durability_value_range_unit_source':vt.PRIMITIVES['item-durability-state']['value_range_unit_source_required'],
            'slot_category_occupancy_source':vt.PRIMITIVES['equipment-slot']['slot_category_occupancy_source_required'],
            'compatibility_subjects_rule_result_source':vt.PRIMITIVES['item-compatibility-rule']['subjects_rule_result_source_required'],
            'stat_value_unit_source_context':vt.PRIMITIVES['item-stat-field']['value_unit_source_context_required'],
            'presentation_base_delta_context_source':vt.PRIMITIVES['item-presentation-variant']['base_delta_context_source_required'],
            'comparison_item_refs_fields_source':vt.PRIMITIVES['item-comparison-state']['item_refs_fields_source_required'],
            'export_requirements_visible':vt.PRIMITIVES['inventory-export-target']['requirements_must_be_visible'],
        }
        if not all(checks.values()): raise AssertionError('inventory source/ownership contract failed')
        retained={
            'camera_source':vt.PRIMITIVES['camera-source']['identity_source_version_owner_required'],
            'camera_runtime':vt.PRIMITIVES['camera-runtime-binding']['state_camera_source_authority_required'],
            'look_source':vt.PRIMITIVES['look-source']['identity_source_version_context_required'],
            'hud_source':vt.PRIMITIVES['hud-source']['identity_source_version_context_required'],
            'mission_source':vt.PRIMITIVES['mission-source']['identity_source_version_context_required'],
            'vfx_source':vt.PRIMITIVES['vfx-source']['identity_source_version_purpose_required'],
            'environment_source':vt.PRIMITIVES['environment-source']['identity_source_version_scope_required'],
            'brand_asset':vt.PRIMITIVES['brand-asset-source']['identity_source_version_provenance_required'],
            'motion_state':vt.PRIMITIVES['motion-state']['source_target_identity_required'],
            'config_digest':vt.PRIMITIVES['configuration-state']['base_attachment_variant_digest_required'],
            'character_identity':vt.PRIMITIVES['character-source']['identity_source_version_required'],
            'presentation_page':vt.PRIMITIVES['presentation-page']['identity_role_order_required'],
            'music_track':vt.PRIMITIVES['music-track-source']['identity_source_digest_duration_required'],
            'showroom_object':vt.PRIMITIVES['showroom-object']['source_identity_version_required'],
            'novel_save':vt.PRIMITIVES['save-checkpoint']['state_identity_digest_required'],
            'atlas_coordinate':vt.PRIMITIVES['map-coordinate']['system_source_precision_required'],
        }
        if not all(retained.values()): raise AssertionError('prior visual source boundary failed')
        receipt={'schema':'axm.visual-template-proof/v27','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'inventory_checks':checks,'retained_checks':retained,'truth':'Offline structural evidence only. Game balance, economy design, runtime ownership correctness, item usefulness, accessibility acceptance, input ergonomics and aesthetic quality were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

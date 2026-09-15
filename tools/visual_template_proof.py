#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core","visual.cinematic.core","visual.broadcast.core","visual.diagram.core","visual.atlas.core","visual.novel.core","visual.showroom.core")

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
        if counts!={'styles':20,'primitives':146,'screens':184,'products':18}: raise AssertionError(counts)
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
            ('game.racing.full',1920,1080,'racing-full','AXM Full Racing Foundation'),
            ('game.coop.action',1280,720,'coop-action','AXM Co-op Action Foundation'),
            ('game.rts.command',1920,1080,'rts-command','AXM RTS Command Foundation'),
            ('game.system.shell',1280,720,'game-system','AXM Shared Game-System Foundation'),
            ('game.shared.core',1920,1080,'game-shared','AXM Shared Gameplay Systems'),
            ('editor.creative.core',1920,1080,'creative-editor','AXM Creative Editor Foundation'),
            ('comic.narrative.core',1920,1080,'comic-narrative','AXM Editable Comic Foundation'),
            ('axm.system.shell',1920,1080,'axm-system','AXM System Shell Foundation'),
            ('visual.keyart.core',1920,1080,'keyart','AXM Editable Key Art Foundation'),
            ('visual.cards.core',1920,1080,'cards','AXM Editable Card and Deck Foundation'),
            ('visual.cinematic.core',1920,1080,'cinematic','AXM Cinematic Title and Overlay Foundation'),
            ('visual.broadcast.core',1920,1080,'broadcast','AXM Video and Stream Overlay Foundation'),
            ('visual.diagram.core',1920,1080,'diagram','AXM Evidence-Aware Diagram Foundation'),
            ('visual.atlas.core',1920,1080,'atlas','AXM World-Map and Lore-Atlas Foundation'),
            ('visual.novel.core',1920,1080,'visual-novel','AXM Branching Visual-Novel Foundation'),
            ('visual.showroom.core',1920,1080,'showroom','AXM 3D Showroom and Gallery Foundation'),
        )
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        product=vt.get('visual.showroom.core')
        required={'visual.showroom.project-hub','visual.showroom.object-stage','visual.showroom.orbit-camera','visual.showroom.material-editor','visual.showroom.variant-editor','visual.showroom.annotation-editor','visual.showroom.comparison','visual.showroom.detail-view','visual.showroom.turntable','visual.showroom.review-export'}
        if set(product['screens'])!=required: raise AssertionError('showroom pack lost required surfaces')
        checks={
            'object_source_identity_version':vt.PRIMITIVES['showroom-object']['source_identity_version_required'],
            'orbit_target_pivot_range':vt.PRIMITIVES['orbit-rig']['target_pivot_range_required'],
            'camera_projection_lens_transform':vt.PRIMITIVES['camera-preset']['projection_lens_transform_required'],
            'material_part_source':vt.PRIMITIVES['material-slot']['part_material_source_required'],
            'variant_identity_properties_availability':vt.PRIMITIVES['variant-option']['identity_properties_availability_required'],
            'annotation_target_anchor_content':vt.PRIMITIVES['object-annotation']['target_anchor_content_required'],
            'comparison_reference_fields':vt.PRIMITIVES['comparison-object']['reference_and_fields_required'],
            'turntable_target_angle_speed':vt.PRIMITIVES['turntable-state']['target_angle_speed_required'],
            'measurement_value_unit_source':vt.PRIMITIVES['measurement-callout']['value_unit_source_required'],
            'export_requirements_visible':vt.PRIMITIVES['showroom-export-target']['requirements_must_be_visible'],
        }
        if not all(checks.values()): raise AssertionError('showroom object/presentation contract failed')
        receipt={'schema':'axm.visual-template-proof/v14','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'showroom_checks':checks,'truth':'Offline structural evidence only. Renderer fidelity, geometry correctness, physical scale, material realism, lighting quality, product availability and aesthetic acceptance were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

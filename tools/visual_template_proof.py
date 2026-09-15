#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core","visual.cinematic.core","visual.broadcast.core","visual.diagram.core","visual.atlas.core")

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
        if counts!={'styles':18,'primitives':126,'screens':164,'products':16}: raise AssertionError(counts)
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
        )
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        product=vt.get('visual.atlas.core')
        required={'visual.atlas.project-hub','visual.atlas.map-editor','visual.atlas.region-editor','visual.atlas.route-editor','visual.atlas.poi-lore','visual.atlas.layer-editor','visual.atlas.timeline-state','visual.atlas.coordinate-source','visual.atlas.review-compare','visual.atlas.export'}
        if set(product['screens'])!=required: raise AssertionError('atlas pack lost required surfaces')
        checks={
            'region_geometry_source':vt.PRIMITIVES['map-region']['geometry_source_required'],
            'route_endpoints_status':vt.PRIMITIVES['route-path']['endpoints_and_status_required'],
            'poi_location_source':vt.PRIMITIVES['poi-marker']['location_source_required'],
            'layer_source':vt.PRIMITIVES['map-layer']['layer_source_required'],
            'time_period_status':vt.PRIMITIVES['time-slice']['period_and_status_required'],
            'lore_target_source':vt.PRIMITIVES['lore-reference']['target_and_source_required'],
            'boundary_type_source':vt.PRIMITIVES['boundary-line']['boundary_type_and_source_required'],
            'coordinate_system_source_precision':vt.PRIMITIVES['map-coordinate']['system_source_precision_required'],
            'overlay_source_time':vt.PRIMITIVES['state-overlay']['source_and_time_required'],
            'export_requirements_visible':vt.PRIMITIVES['atlas-export-target']['requirements_must_be_visible'],
        }
        if not all(checks.values()): raise AssertionError('atlas spatial/source contract failed')
        receipt={'schema':'axm.visual-template-proof/v12','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'atlas_checks':checks,'truth':'Offline structural evidence only. Coordinate accuracy, route truth, boundary claims, chronology correctness, lore truth and aesthetic acceptance were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

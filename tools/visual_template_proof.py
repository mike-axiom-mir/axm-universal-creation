#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core","visual.cinematic.core","visual.broadcast.core")

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
        if counts!={'styles':16,'primitives':106,'screens':144,'products':14}: raise AssertionError(counts)
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
        )
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        product=vt.get('visual.broadcast.core')
        required={'visual.broadcast.project-hub','visual.broadcast.scene-editor','visual.broadcast.source-router','visual.broadcast.camera-editor','visual.broadcast.score-status','visual.broadcast.alert-editor','visual.broadcast.chat-social','visual.broadcast.scene-set','visual.broadcast.format-variants','visual.broadcast.review-output'}
        if set(product['screens'])!=required: raise AssertionError('broadcast pack lost required surfaces')
        checks={
            'source_identity_explicit':vt.PRIMITIVES['source-window']['source_identity_must_be_explicit'],
            'camera_source_crop_separate':vt.PRIMITIVES['camera-slot']['source_and_crop_remain_separate'],
            'status_source_freshness':vt.PRIMITIVES['status-field']['value_source_freshness_required'],
            'alert_no_fake_success':vt.PRIMITIVES['alert-cue']['unobserved_success_forbidden'],
            'chat_delivery_explicit':vt.PRIMITIVES['chat-panel']['delivery_state_must_be_explicit'],
            'scene_identity_exact':vt.PRIMITIVES['scene-state']['scene_identity_must_be_exact'],
            'overlay_conflicts_visible':vt.PRIMITIVES['overlay-zone']['overlap_conflicts_must_be_visible'],
            'identity_source_transform_separate':vt.PRIMITIVES['identity-panel']['source_and_transform_remain_separate'],
            'transition_from_to_exact':vt.PRIMITIVES['transition-state']['from_to_identity_required'],
            'output_state_observed':vt.PRIMITIVES['output-monitor']['target_state_must_be_observed'],
        }
        if not all(checks.values()): raise AssertionError('broadcast source/state contract failed')
        receipt={'schema':'axm.visual-template-proof/v10','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'broadcast_checks':checks,'truth':'Offline structural evidence only. Live capture, score correctness, message delivery, encoder/output health, platform integration, latency and aesthetic acceptance were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

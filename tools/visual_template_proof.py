#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core","visual.cinematic.core")

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
        if counts!={'styles':15,'primitives':96,'screens':135,'products':13}: raise AssertionError(counts)
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
            ('visual.cinematic.core',1920,1080,'cinematic','AXM Editable Cinematic Overlay Foundation'),
        )
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        cinematic=vt.get('visual.cinematic.core')
        required={'visual.cinematic.project-hub','visual.cinematic.title-card-editor','visual.cinematic.lower-third-editor','visual.cinematic.chapter-card-editor','visual.cinematic.subtitle-editor','visual.cinematic.credits-editor','visual.cinematic.overlay-timeline','visual.cinematic.transition-editor','visual.cinematic.trailer-layout','visual.cinematic.end-card-editor','visual.cinematic.review-export'}
        if set(cinematic['screens'])!=required: raise AssertionError('cinematic pack lost required surfaces')
        checks={
            'title_text_timing_layout_separate':vt.PRIMITIVES['title-card']['text_timing_layout_separate'],
            'lower_third_timing_explicit':vt.PRIMITIVES['lower-third']['identity_and_timing_must_be_explicit'],
            'subtitle_exact_timecode':vt.PRIMITIVES['subtitle-cue']['text_and_timecode_must_be_exact'],
            'credit_text_exact':vt.PRIMITIVES['credit-entry']['credit_text_must_remain_exact'],
            'timeline_range_explicit':vt.PRIMITIVES['timeline-cue']['time_range_must_be_explicit'],
            'transition_required_content_safe':vt.PRIMITIVES['transition-safe-zone']['transition_cannot_silently_occlude_required_content'],
            'overlay_order_timing_explicit':vt.PRIMITIVES['overlay-track']['order_and_timing_must_be_explicit'],
            'shot_marker_exact':vt.PRIMITIVES['shot-marker']['marker_identity_and_time_required'],
            'end_card_duration_explicit':vt.PRIMITIVES['end-card']['content_and_duration_must_be_explicit'],
            'legal_text_exact':vt.PRIMITIVES['legal-line']['content_must_remain_exact'],
        }
        if not all(checks.values()): raise AssertionError('cinematic editability contract failed')
        receipt={'schema':'axm.visual-template-proof/v9','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'cinematic_checks':checks,'truth':'Offline structural evidence only. Motion-render quality, subtitle accuracy against real audio, trailer editorial quality, transition rendering and aesthetic acceptance were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

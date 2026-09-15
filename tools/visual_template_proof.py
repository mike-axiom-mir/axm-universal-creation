#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations
import json,shutil,sys
from pathlib import Path
from xml.etree import ElementTree
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from axm_uc import visual_templates as vt

SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
PRODUCTS=("game.racing.full","game.coop.action","game.rts.command","game.system.shell","game.shared.core","editor.creative.core","comic.narrative.core","axm.system.shell","visual.keyart.core","visual.cards.core")

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
        if counts!={'styles':14,'primitives':86,'screens':124,'products':12}: raise AssertionError(counts)
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
        )
        outputs=[]
        for pid,w,h,folder,title in galleries: outputs+=_write(vt.product_project(pid,w,h,title),out/folder)
        outputs+=_write(vt.screen_project('product.mobile.home',1080,1920,'AXM Mobile Foundation'),out/'mobile-home')
        cards=vt.get('visual.cards.core')
        required={'visual.cards.project-hub','visual.cards.face-editor','visual.cards.back-editor','visual.cards.artwork-editor','visual.cards.text-stats','visual.cards.ability-layout','visual.cards.rarity-style','visual.cards.effects-finish','visual.cards.deck-builder','visual.cards.print-sheet','visual.cards.review-export'}
        if set(cards['screens'])!=required: raise AssertionError('card/deck pack lost required surfaces')
        checks={
            'frame_geometry_editable':vt.PRIMITIVES['card-frame']['geometry_must_remain_editable'],
            'art_source_crop_separate':vt.PRIMITIVES['artwork-window']['source_and_crop_remain_separate'],
            'stats_explicit':vt.PRIMITIVES['stat-block']['label_value_pair_must_be_explicit'],
            'rules_text_exact':vt.PRIMITIVES['ability-row']['rules_text_must_remain_exact'],
            'rarity_noncolor':vt.PRIMITIVES['rarity-badge']['must_not_depend_on_color'],
            'cost_type_value_explicit':vt.PRIMITIVES['cost-symbol']['value_and_resource_type_required'],
            'card_state_explicit':vt.PRIMITIVES['card-state']['state_must_be_explicit'],
            'deck_reference_exact':vt.PRIMITIVES['deck-slot']['card_reference_must_be_exact'],
            'foil_preserves_art':vt.PRIMITIVES['foil-pass']['finish_must_not_replace_base_art'],
            'print_guides_preserve_source':vt.PRIMITIVES['print-safe-frame']['guide_must_not_mutate_source_layout'],
        }
        if not all(checks.values()): raise AssertionError('card/deck editability contract failed')
        receipt={'schema':'axm.visual-template-proof/v8','catalog':counts,'composition':vt.CATALOG_COMPOSITION,'product_evidence':evidence,'galleries':{pid:{'screens':len(vt.get(pid)['screens']),'path':folder+'/index.html'} for pid,_,_,folder,_ in galleries},'parsed_svg_count':sum(p.endswith('.svg') for p in outputs),'card_deck_checks':checks,'truth':'Offline structural evidence only. Card-game balance, rules correctness, artwork quality, foil rendering, print production, physical color management and aesthetic acceptance were not observed.'}
        (out/'receipt.json').write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding='utf-8')
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True); raise
    return 0

if __name__=='__main__': raise SystemExit(main(sys.argv))

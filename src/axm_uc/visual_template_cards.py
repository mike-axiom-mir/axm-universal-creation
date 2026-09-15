"""Editable card, deck and collectible visual foundations for AXM visual templates."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"card/deck {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_card_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.cards.collectible':{
        'intent':'high-readability collectible/card composition with strong artwork identity, exact game text and separately editable finish layers',
        'tokens':{'canvas':'#0b0d12','surface':'#171b23','surface_raised':'#222936','text':'#f5f3ec','muted':'#ada99e','accent':'#dfbd70','warning':'#e99c65','danger':'#e66f73','line':'#474c58'},
        'shape':{'panel_radius_ratio':0.018,'cut_ratio':0.004,'line_ratio':0.0013},
        'type':{'display_weight':760,'body_weight':500,'metric_scale':1.55,'tracking':0.012},
        'depth':{'layers':6,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':85,'standard_ms':170,'slow_ms':300,'principle':'card state, text and selection before decorative finish'},
    }},'style')

    _merge(primitives,{
        'card-frame':{'role':'editable card face structure with named content regions and safe area','states':['face','back','selected','locked'],'geometry_must_remain_editable':True},
        'artwork-window':{'role':'source artwork viewport with crop, focus and mask state','states':['active','selected','overflow','missing-source'],'source_and_crop_remain_separate':True},
        'stat-block':{'role':'stable label/value group for card statistics','states':['normal','modified','warning','hidden'],'label_value_pair_must_be_explicit':True},
        'ability-row':{'role':'one named ability/effect with cost, rules text and state','states':['active','selected','disabled','overflow'],'rules_text_must_remain_exact':True},
        'rarity-badge':{'role':'rarity/tier identity with text/symbol in addition to color','states':['common','uncommon','rare','epic','legendary','custom'],'must_not_depend_on_color':True},
        'cost-symbol':{'role':'one explicit resource/cost requirement','states':['available','insufficient','conditional','none'],'value_and_resource_type_required':True},
        'card-state':{'role':'ownership/deck/playability state for a card instance','states':['unowned','owned','in-deck','selected','locked','unavailable'],'state_must_be_explicit':True},
        'deck-slot':{'role':'one deck position or count with card reference and limit state','states':['empty','occupied','selected','over-limit','invalid'],'card_reference_must_be_exact':True},
        'foil-pass':{'role':'separate decorative/reflective finish layer','states':['active','selected','muted','disabled'],'finish_must_not_replace_base_art':True},
        'print-safe-frame':{'role':'trim, bleed and safe-content guide for physical output','states':['trim','bleed','safe','selected'],'guide_must_not_mutate_source_layout':True},
    },'primitive')

    q=['artwork, frame, game text, statistics, rarity and finish remain separately editable','rules text and numeric card state remain exact instead of being inferred from art','face and back remain distinct source structures','foil and decorative finish never replace base artwork','print/digital export variants remain derived from richer card source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.cards.project-hub':screen('visual.cards.project-hub','Card project and set hub','creative.cards','visual.cards.collectible','browse sets, card definitions, variants, deck lists and output targets with source completeness visible',v(
        {'header':(.03,.03,.94,.08),'sets':(.03,.14,.94,.28),'cards':(.03,.45,.55,.41),'details':(.61,.45,.36,.29),'actions':(.61,.77,.36,.09)},
        {'header':(.02,.03,.96,.075),'sets':(.02,.14,.20,.82),'cards':(.245,.14,.48,.82),'details':(.75,.14,.23,.56),'actions':(.75,.73,.23,.23)},
        {'header':(.015,.03,.97,.07),'sets':(.015,.13,.18,.84),'cards':(.215,.13,.52,.84),'details':(.755,.13,.23,.57),'actions':(.755,.73,.23,.24)}),tags=['visual','cards','project','set'],quality=q),
      'visual.cards.face-editor':screen('visual.cards.face-editor','Card face editor','creative.cards','visual.cards.collectible','edit face layout, artwork, title, stats, abilities, costs and rarity as independent source regions',v(
        {'toolbar':(.02,.02,.96,.07),'face':(.22,.11,.56,.58),'regions':(.02,.11,.17,.58),'properties':(.81,.11,.17,.58),'layers':(.02,.72,.45,.26),'checks':(.50,.72,.48,.26)},
        {'toolbar':(.015,.02,.97,.065),'regions':(.015,.105,.16,.78),'face':(.20,.105,.47,.78),'properties':(.695,.105,.29,.55),'layers':(.695,.69,.14,.29),'checks':(.845,.69,.14,.29)},
        {'toolbar':(.012,.02,.976,.06),'regions':(.012,.10,.14,.80),'face':(.18,.10,.50,.80),'properties':(.705,.10,.283,.57),'layers':(.705,.70,.135,.28),'checks':(.85,.70,.138,.28)}),tags=['visual','cards','face','editor'],math_hooks={'artwork_area_ratio':[0.35,0.62],'text_area_ratio':[0.22,0.42]},quality=q),
      'visual.cards.back-editor':screen('visual.cards.back-editor','Card back editor','creative.cards','visual.cards.collectible','edit shared or variant card backs, identity mark, pattern, border and orientation independently from card faces',v(
        {'toolbar':(.02,.02,.96,.07),'back':(.22,.11,.56,.58),'layers':(.02,.11,.17,.58),'properties':(.81,.11,.17,.58),'variants':(.02,.72,.45,.26),'actions':(.50,.72,.48,.26)},
        {'toolbar':(.015,.02,.97,.065),'layers':(.015,.105,.16,.78),'back':(.20,.105,.47,.78),'properties':(.695,.105,.29,.55),'variants':(.695,.69,.14,.29),'actions':(.845,.69,.14,.29)},
        {'toolbar':(.012,.02,.976,.06),'layers':(.012,.10,.14,.80),'back':(.18,.10,.50,.80),'properties':(.705,.10,.283,.57),'variants':(.705,.70,.135,.28),'actions':(.85,.70,.138,.28)}),tags=['visual','cards','back','editor'],quality=q),
      'visual.cards.artwork-editor':screen('visual.cards.artwork-editor','Card artwork editor','creative.cards','visual.cards.collectible','edit source artwork, crop, focal mask and safe window without merging artwork into the frame',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'sources':(.03,.59,.30,.28),'crop':(.36,.59,.29,.28),'mask':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.18,.72),'preview':(.225,.14,.52,.72),'crop':(.77,.14,.21,.34),'mask':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.16,.74),'preview':(.195,.13,.56,.74),'crop':(.775,.13,.21,.35),'mask':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cards','artwork','crop'],quality=q),
      'visual.cards.text-stats':screen('visual.cards.text-stats','Card text and statistics editor','creative.cards','visual.cards.collectible','edit title, type line, flavor text and structured statistics with overflow and exact values visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'text':(.03,.48,.45,.39),'stats':(.51,.48,.46,.39),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'fields':(.02,.14,.25,.72),'preview':(.295,.14,.42,.72),'stats':(.745,.14,.235,.54),'actions':(.745,.71,.235,.15)},
        {'header':(.015,.03,.97,.07),'fields':(.015,.13,.23,.74),'preview':(.265,.13,.45,.74),'stats':(.74,.13,.245,.55),'actions':(.74,.71,.245,.16)}),tags=['visual','cards','text','stats'],quality=q),
      'visual.cards.ability-layout':screen('visual.cards.ability-layout','Card ability and rules editor','creative.cards','visual.cards.collectible','compose ordered abilities, costs, icons and exact rules text while preserving available text area',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'abilities':(.03,.48,.58,.39),'details':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'abilities':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'abilities':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cards','ability','rules'],quality=q),
      'visual.cards.rarity-style':screen('visual.cards.rarity-style','Card rarity and style editor','creative.cards','visual.cards.collectible','edit tier identity, frame/material style and symbols with non-color rarity cues and exact variant state',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'tiers':(.03,.51,.45,.34),'style':(.51,.51,.46,.34),'actions':(.03,.88,.94,.09)},
        {'header':(.02,.03,.96,.075),'tiers':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'style':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'tiers':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'style':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cards','rarity','style'],quality=q),
      'visual.cards.effects-finish':screen('visual.cards.effects-finish','Card finish and foil editor','creative.cards','visual.cards.collectible','build decorative foil, gloss, texture and effect passes separately from base face and artwork',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'passes':(.03,.56,.42,.31),'properties':(.48,.56,.49,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'passes':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'properties':(.77,.14,.21,.55),'actions':(.77,.72,.21,.14)},
        {'header':(.015,.03,.97,.07),'passes':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'properties':(.775,.13,.21,.56),'actions':(.775,.72,.21,.15)}),tags=['visual','cards','foil','effects'],quality=q),
      'visual.cards.deck-builder':screen('visual.cards.deck-builder','Deck builder','creative.cards','visual.cards.collectible','build a deck from exact card references while showing counts, limits, curve/stat summary and invalid states',v(
        {'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.09),'library':(.03,.26,.45,.55),'deck':(.51,.26,.46,.55),'summary':(.03,.84,.58,.12),'actions':(.64,.84,.33,.12)},
        {'header':(.02,.03,.96,.075),'filters':(.02,.14,.15,.82),'library':(.19,.14,.34,.82),'deck':(.55,.14,.28,.82),'summary':(.85,.14,.13,.58),'actions':(.85,.75,.13,.21)},
        {'header':(.015,.03,.97,.07),'filters':(.015,.13,.14,.84),'library':(.175,.13,.36,.84),'deck':(.555,.13,.29,.84),'summary':(.865,.13,.12,.59),'actions':(.865,.75,.12,.22)}),tags=['visual','cards','deck','builder'],quality=q),
      'visual.cards.print-sheet':screen('visual.cards.print-sheet','Card print and sheet layout','creative.cards','visual.cards.collectible','arrange exact card fronts/backs into print sheets with bleed, trim, safe zones and duplex orientation visible',v(
        {'header':(.03,.03,.94,.08),'sheet':(.03,.14,.94,.43),'guides':(.03,.60,.45,.27),'cards':(.51,.60,.46,.27),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'cards':(.02,.14,.18,.72),'sheet':(.225,.14,.52,.72),'guides':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'cards':(.015,.13,.16,.74),'sheet':(.195,.13,.56,.74),'guides':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cards','print','sheet'],math_hooks={'bleed_ratio':[0.02,0.08],'safe_inset_ratio':[0.03,0.10]},quality=q),
      'visual.cards.review-export':screen('visual.cards.review-export','Card set review and export','creative.cards','visual.cards.collectible','review face/back pairing, text overflow, deck/set consistency, digital targets and print requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','cards','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.cards.core','version':1,'name':'Editable card and deck core','kind':'product','domain':'creative.cards','tags':['visual','cards','deck','collectible','product'],'origin':origin(),'style':'visual.cards.collectible','intent':'source-first card and deck editing for game, collectible, lore and printable cards with separate face/back/art/text/rules/rarity/finish/deck/print state','screens':ids,'flow':[
      ['visual.cards.project-hub','visual.cards.face-editor','edit-face'],['visual.cards.face-editor','visual.cards.artwork-editor','edit-artwork'],['visual.cards.face-editor','visual.cards.text-stats','edit-text-stats'],['visual.cards.face-editor','visual.cards.ability-layout','edit-rules'],['visual.cards.face-editor','visual.cards.rarity-style','edit-rarity'],['visual.cards.face-editor','visual.cards.effects-finish','edit-finish'],['visual.cards.project-hub','visual.cards.back-editor','edit-back'],['visual.cards.project-hub','visual.cards.deck-builder','build-deck'],['visual.cards.face-editor','visual.cards.print-sheet','prepare-print'],['visual.cards.print-sheet','visual.cards.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.cards.core':product},'product')

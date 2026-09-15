"""Editable cinematic title, credits and trailer-overlay foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"cinematic {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_cinematic_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.cinematic.motion':{
        'intent':'cinematic motion graphics with strong hierarchy, readable timing and safe overlay composition while preserving separately editable text, cue and transition state',
        'tokens':{'canvas':'#07090d','surface':'#121720','surface_raised':'#1a2230','text':'#f4f4f0','muted':'#a6adb6','accent':'#8ec7ff','warning':'#efb56f','danger':'#ef7676','line':'#35404d'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':780,'body_weight':500,'metric_scale':1.65,'tracking':0.020},
        'depth':{'layers':6,'shadow':'cinematic','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':180,'slow_ms':420,'principle':'timing and readability before decorative transition'},
    }},'style')

    _merge(primitives,{
        'title-card':{'role':'primary cinematic title composition with text, timing and safe-area state','states':['draft','timed','approved','overflow'],'text_timing_layout_separate':True},
        'lower-third':{'role':'lower-third identity/information overlay with exact anchor and duration','states':['hidden','entering','visible','exiting'],'identity_and_timing_must_be_explicit':True},
        'subtitle-cue':{'role':'timed subtitle/caption cue with exact text, speaker and interval','states':['draft','timed','overlap','approved'],'text_and_timecode_must_be_exact':True},
        'credit-entry':{'role':'one exact credit item or grouped credit block','states':['draft','approved','overflow','hidden'],'credit_text_must_remain_exact':True},
        'timeline-cue':{'role':'named overlay event pinned to exact start/end or marker','states':['draft','active','locked','conflict'],'time_range_must_be_explicit':True},
        'transition-safe-zone':{'role':'protected region that remains readable through incoming/outgoing transitions','states':['safe','warning','unsafe','selected'],'transition_cannot_silently_occlude_required_content':True},
        'overlay-track':{'role':'ordered layer/track of timed overlays','states':['active','muted','locked','hidden'],'order_and_timing_must_be_explicit':True},
        'shot-marker':{'role':'exact shot/beat/chapter marker used to align overlays and edit decisions','states':['beat','shot','chapter','selected'],'marker_identity_and_time_required':True},
        'end-card':{'role':'final callout/title/link/credit composition with explicit duration and safe area','states':['draft','timed','approved','overflow'],'content_and_duration_must_be_explicit':True},
        'legal-line':{'role':'small exact legal/copyright/disclaimer text with minimum readability contract','states':['draft','approved','overflow','hidden'],'content_must_remain_exact':True},
    },'primitive')

    q=['text, timing, layout and transition state remain separately editable','required text may not be silently hidden by transitions or crops','subtitle and credit content remain exact source text','overlay tracks preserve explicit order and time ranges','derived trailer/export outputs never replace richer editable timing source']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.cinematic.project-hub':screen('visual.cinematic.project-hub','Cinematic overlay project hub','creative.cinematic','visual.cinematic.motion','browse sequences, title systems, cue tracks and output targets with source completeness visible',v(
        {'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.31),'sequences':(.03,.48,.55,.38),'details':(.61,.48,.36,.27),'actions':(.61,.78,.36,.08)},
        {'header':(.02,.03,.96,.075),'projects':(.02,.14,.22,.82),'sequences':(.27,.14,.48,.82),'details':(.78,.14,.20,.56),'actions':(.78,.73,.20,.23)},
        {'header':(.015,.03,.97,.07),'projects':(.015,.13,.20,.84),'sequences':(.24,.13,.51,.84),'details':(.775,.13,.21,.57),'actions':(.775,.73,.21,.24)}),tags=['visual','cinematic','project','motion'],quality=q),
      'visual.cinematic.title-card-editor':screen('visual.cinematic.title-card-editor','Title card editor','creative.cinematic','visual.cinematic.motion','edit title/subtitle/mark hierarchy, composition, entrance/hold/exit timing and transition-safe placement',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'text':(.03,.59,.29,.28),'timing':(.35,.59,.29,.28),'layout':(.67,.59,.30,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'text':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'timing':(.77,.14,.21,.34),'layout':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'text':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'timing':(.775,.13,.21,.35),'layout':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cinematic','title','timing'],math_hooks={'title_safe_ratio':[0.06,0.20],'hold_time_ratio':[0.35,0.70]},quality=q),
      'visual.cinematic.lower-third-editor':screen('visual.cinematic.lower-third-editor','Lower-third editor','creative.cinematic','visual.cinematic.motion','edit exact identity text, anchor, entrance/exit animation and duration against video-safe context',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'content':(.03,.59,.30,.28),'position':(.36,.59,.29,.28),'timing':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'content':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'position':(.77,.14,.21,.34),'timing':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'content':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'position':(.775,.13,.21,.35),'timing':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cinematic','lower-third','identity'],quality=q),
      'visual.cinematic.chapter-card-editor':screen('visual.cinematic.chapter-card-editor','Chapter and beat card editor','creative.cinematic','visual.cinematic.motion','edit chapter/mission/act cards with exact markers, visual hierarchy and sequence-safe timing',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'chapters':(.03,.56,.42,.31),'details':(.48,.56,.49,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'chapters':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'details':(.77,.14,.21,.55),'actions':(.77,.72,.21,.14)},
        {'header':(.015,.03,.97,.07),'chapters':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'details':(.775,.13,.21,.56),'actions':(.775,.72,.21,.15)}),tags=['visual','cinematic','chapter','marker'],quality=q),
      'visual.cinematic.subtitle-editor':screen('visual.cinematic.subtitle-editor','Subtitle and caption editor','creative.cinematic','visual.cinematic.motion','edit exact subtitle text, speaker, start/end timing, overlap warnings and safe placement',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'cues':(.03,.48,.58,.39),'details':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'cues':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'cues':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cinematic','subtitle','caption'],quality=q),
      'visual.cinematic.credits-editor':screen('visual.cinematic.credits-editor','Credits editor','creative.cinematic','visual.cinematic.motion','manage exact credit entries, grouping, roll/card timing, readability and overflow without rewriting names or roles',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'credits':(.03,.48,.58,.39),'layout':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'credits':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'layout':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'credits':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'layout':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cinematic','credits','exact-text'],quality=q),
      'visual.cinematic.overlay-timeline':screen('visual.cinematic.overlay-timeline','Overlay timeline editor','creative.cinematic','visual.cinematic.motion','coordinate overlay tracks, shot markers, titles, subtitles, lower thirds and end cards on one explicit time axis',v(
        {'toolbar':(.02,.02,.96,.07),'preview':(.03,.11,.94,.35),'tracks':(.03,.49,.94,.36),'details':(.03,.88,.58,.10),'actions':(.64,.88,.33,.10)},
        {'toolbar':(.015,.02,.97,.065),'tracks':(.015,.105,.22,.875),'preview':(.26,.105,.52,.55),'details':(.805,.105,.18,.55),'timeline':(.26,.68,.725,.30)},
        {'toolbar':(.012,.02,.976,.06),'tracks':(.012,.10,.20,.88),'preview':(.235,.10,.55,.56),'details':(.805,.10,.183,.56),'timeline':(.235,.69,.753,.29)}),tags=['visual','cinematic','timeline','overlay'],math_hooks={'timeline_track_ratio':[0.05,0.10]},quality=q),
      'visual.cinematic.transition-editor':screen('visual.cinematic.transition-editor','Transition and safe-zone editor','creative.cinematic','visual.cinematic.motion','edit incoming/outgoing transition timing and masks while proving required text remains readable through the transition',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'transition':(.03,.59,.45,.28),'safe':(.51,.59,.46,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'transition':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'safe':(.77,.14,.21,.55),'actions':(.77,.72,.21,.14)},
        {'header':(.015,.03,.97,.07),'transition':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'safe':(.775,.13,.21,.56),'actions':(.775,.72,.21,.15)}),tags=['visual','cinematic','transition','safe-zone'],quality=q),
      'visual.cinematic.trailer-layout':screen('visual.cinematic.trailer-layout','Trailer overlay and beat layout','creative.cinematic','visual.cinematic.motion','arrange title beats, gameplay callouts, quotes, chapter cards and transitions against explicit shot/beat markers',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'beats':(.03,.48,.58,.39),'overlays':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'beats':(.02,.14,.27,.72),'preview':(.315,.14,.45,.72),'overlays':(.79,.14,.19,.54),'actions':(.79,.71,.19,.15)},
        {'header':(.015,.03,.97,.07),'beats':(.015,.13,.25,.74),'preview':(.29,.13,.47,.74),'overlays':(.785,.13,.20,.55),'actions':(.785,.71,.20,.16)}),tags=['visual','cinematic','trailer','beat'],quality=q),
      'visual.cinematic.end-card-editor':screen('visual.cinematic.end-card-editor','End card editor','creative.cinematic','visual.cinematic.motion','edit final title, callout, marks, legal line, duration and safe area as an explicit timed composition',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'content':(.03,.59,.30,.28),'legal':(.36,.59,.29,.28),'timing':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'content':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'legal':(.77,.14,.21,.34),'timing':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'content':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'legal':(.775,.13,.21,.35),'timing':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cinematic','end-card','legal'],quality=q),
      'visual.cinematic.review-export':screen('visual.cinematic.review-export','Cinematic overlay review and export','creative.cinematic','visual.cinematic.motion','review timing conflicts, text overflow, safe-zone violations, cue completeness and output targets before rendering derived assets',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','cinematic','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.cinematic.core','version':1,'name':'Editable cinematic overlay core','kind':'product','domain':'creative.cinematic','tags':['visual','cinematic','motion','titles','product'],'origin':origin(),'style':'visual.cinematic.motion','intent':'source-first title, credits, subtitle and trailer-overlay editing with exact text, cues, track order, safe zones and derived export targets','screens':ids,'flow':[
      ['visual.cinematic.project-hub','visual.cinematic.overlay-timeline','open-sequence'],['visual.cinematic.overlay-timeline','visual.cinematic.title-card-editor','edit-title'],['visual.cinematic.overlay-timeline','visual.cinematic.lower-third-editor','edit-lower-third'],['visual.cinematic.overlay-timeline','visual.cinematic.chapter-card-editor','edit-chapter'],['visual.cinematic.overlay-timeline','visual.cinematic.subtitle-editor','edit-subtitles'],['visual.cinematic.overlay-timeline','visual.cinematic.credits-editor','edit-credits'],['visual.cinematic.overlay-timeline','visual.cinematic.transition-editor','edit-transition'],['visual.cinematic.overlay-timeline','visual.cinematic.trailer-layout','edit-trailer'],['visual.cinematic.overlay-timeline','visual.cinematic.end-card-editor','edit-end-card'],['visual.cinematic.overlay-timeline','visual.cinematic.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.cinematic.core':product},'product')

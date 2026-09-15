"""Editable cinematic titles, credits and timed overlay foundations."""
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
        'intent':'cinematic identity and timed overlays with exact text/timing, strong hierarchy and editable safe-area adaptation',
        'tokens':{'canvas':'#08090d','surface':'#141720','surface_raised':'#202633','text':'#f6f2ea','muted':'#a9a6a0','accent':'#e7c47a','warning':'#e89b68','danger':'#e36f76','line':'#454b57'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':780,'body_weight':500,'metric_scale':1.70,'tracking':0.025},
        'depth':{'layers':6,'shadow':'cinematic','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':180,'slow_ms':420,'principle':'timing and readability before flourish'},
    }},'style')

    _merge(primitives,{
        'title-card':{'role':'editable title/subtitle identity plus layout and timing','states':['draft','selected','approved','overflow'],'text_layout_timing_remain_separate':True},
        'lower-third':{'role':'named information overlay with exact text, anchor and duration','states':['hidden','active','selected','overflow'],'content_anchor_duration_explicit':True},
        'subtitle-cue':{'role':'one exact subtitle/caption cue with start/end and speaker/language state','states':['draft','active','approved','conflict'],'text_and_timing_must_be_exact':True},
        'credit-line':{'role':'one ordered credit entry with role/name grouping','states':['active','selected','overflow','hidden'],'content_and_order_must_remain_exact':True},
        'time-cue':{'role':'explicit in/out timing reference for a visual element','states':['before','active','after','conflict'],'start_end_required':True},
        'safe-zone':{'role':'target-format protected region for titles/subtitles/logos','states':['action-safe','title-safe','subtitle-safe','selected'],'guide_must_not_rewrite_source_layout':True},
        'transition-cue':{'role':'derived transition between exact source states','states':['cut','fade','wipe','custom','disabled'],'transition_must_not_replace_source_states':True},
        'chapter-marker':{'role':'named structural moment with exact timeline position','states':['draft','active','selected','published'],'time_and_label_required':True},
        'overlay-track':{'role':'ordered timed overlay lane with explicit overlap/conflict state','states':['active','muted','locked','conflict'],'overlaps_must_remain_visible':True},
        'logo-lockup':{'role':'identity mark with source, scale, anchor and safe-area state','states':['active','selected','alternate','missing-source'],'source_and_transform_remain_separate':True},
    },'primitive')

    q=['text, layout, timing and transition state remain separately editable','exact names, credits and subtitles are never inferred from imagery','safe-area variants never rewrite richer source composition','timed conflicts and overflows remain visible instead of silently clipping','exported video/frames remain derived from editable source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.cinematic.project-hub':screen('visual.cinematic.project-hub','Cinematic identity project hub','creative.cinematic','visual.cinematic.motion','browse sequences, title systems, chapters, overlay tracks and target formats before editing',v(
        {'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.31),'sequences':(.03,.48,.55,.38),'targets':(.61,.48,.36,.27),'actions':(.61,.78,.36,.08)},
        {'header':(.02,.03,.96,.075),'projects':(.02,.14,.22,.82),'sequences':(.27,.14,.48,.82),'targets':(.78,.14,.20,.55),'actions':(.78,.72,.20,.14)},
        {'header':(.015,.03,.97,.07),'projects':(.015,.13,.20,.84),'sequences':(.24,.13,.52,.84),'targets':(.785,.13,.20,.57),'actions':(.785,.73,.20,.14)}),tags=['visual','cinematic','project','hub'],quality=q),
      'visual.cinematic.title-editor':screen('visual.cinematic.title-editor','Title card editor','creative.cinematic','visual.cinematic.motion','edit title/subtitle/logo hierarchy, layout, entry/exit timing and safe-area state independently',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'content':(.03,.59,.30,.28),'layout':(.36,.59,.29,.28),'timing':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'content':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'layout':(.77,.14,.21,.34),'timing':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'content':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'layout':(.775,.13,.21,.35),'timing':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cinematic','title','editor'],math_hooks={'title_safe_ratio':[0.06,0.18]},quality=q),
      'visual.cinematic.chapter-editor':screen('visual.cinematic.chapter-editor','Chapter and intertitle editor','creative.cinematic','visual.cinematic.motion','edit chapter labels, numbering, visual identity and exact timeline markers as structural moments',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.37),'chapters':(.03,.54,.45,.33),'details':(.51,.54,.46,.33),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'chapters':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'chapters':(.015,.13,.22,.74),'preview':(.265,.13,.48,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','cinematic','chapter','intertitle'],quality=q),
      'visual.cinematic.lower-third':screen('visual.cinematic.lower-third','Lower-third editor','creative.cinematic','visual.cinematic.motion','edit exact names/labels, anchor, hierarchy, in/out timing and safe region against scene context',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'content':(.03,.59,.30,.28),'position':(.36,.59,.29,.28),'timing':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'content':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'position':(.77,.14,.21,.34),'timing':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'content':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'position':(.775,.13,.21,.35),'timing':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','cinematic','lower-third','overlay'],quality=q),
      'visual.cinematic.subtitle-editor':screen('visual.cinematic.subtitle-editor','Subtitle and caption editor','creative.cinematic','visual.cinematic.motion','edit exact cue text, language/speaker, start/end timing, reading load and target-format safe position',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'cues':(.03,.49,.58,.38),'details':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'cues':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'cues':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cinematic','subtitle','caption'],math_hooks={'subtitle_safe_ratio':[0.06,0.16]},quality=q),
      'visual.cinematic.credits-editor':screen('visual.cinematic.credits-editor','Credits editor','creative.cinematic','visual.cinematic.motion','edit ordered names/roles/groups, roll/card timing, typography and overflow without losing exact credit text',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'credits':(.03,.49,.58,.38),'format':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'credits':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'format':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'credits':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'format':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','cinematic','credits','editor'],quality=q),
      'visual.cinematic.overlay-timeline':screen('visual.cinematic.overlay-timeline','Timed overlay timeline','creative.cinematic','visual.cinematic.motion','coordinate exact title, lower-third, subtitle, logo and chapter cues on inspectable tracks with overlap conflicts visible',v(
        {'toolbar':(.02,.02,.96,.07),'preview':(.03,.11,.94,.38),'tracks':(.03,.52,.94,.35),'details':(.03,.90,.58,.07),'actions':(.64,.90,.33,.07)},
        {'toolbar':(.015,.02,.97,.065),'tracks':(.015,.105,.24,.78),'preview':(.28,.105,.50,.58),'details':(.80,.105,.185,.58),'timeline':(.28,.71,.705,.17),'actions':(.80,.90,.185,.07)},
        {'toolbar':(.012,.02,.976,.06),'tracks':(.012,.10,.22,.80),'preview':(.255,.10,.53,.59),'details':(.805,.10,.183,.59),'timeline':(.255,.72,.733,.18),'actions':(.805,.92,.183,.06)}),tags=['visual','cinematic','timeline','overlay'],quality=q),
      'visual.cinematic.transition-editor':screen('visual.cinematic.transition-editor','Transition editor','creative.cinematic','visual.cinematic.motion','edit derived transitions between exact source states with duration/easing and before/after context visible',v(
        {'header':(.03,.03,.94,.08),'before':(.03,.14,.45,.36),'after':(.52,.14,.45,.36),'transition':(.03,.53,.58,.34),'details':(.64,.53,.33,.24),'actions':(.64,.80,.33,.07)},
        {'header':(.02,.03,.96,.075),'before':(.02,.14,.31,.48),'after':(.35,.14,.31,.48),'preview':(.68,.14,.30,.48),'transition':(.02,.66,.64,.20),'details':(.68,.66,.30,.20),'actions':(.68,.89,.30,.07)},
        {'header':(.015,.03,.97,.07),'before':(.015,.13,.32,.50),'after':(.35,.13,.32,.50),'preview':(.685,.13,.30,.50),'transition':(.015,.67,.655,.20),'details':(.685,.67,.30,.20),'actions':(.685,.90,.30,.06)}),tags=['visual','cinematic','transition','timing'],quality=q),
      'visual.cinematic.aspect-variants':screen('visual.cinematic.aspect-variants','Cinematic aspect and safe-area variants','creative.cinematic','visual.cinematic.motion','compare landscape, portrait, square and vertical variants while preserving exact text/timing and protected regions',v(
        {'header':(.03,.03,.94,.08),'source':(.03,.14,.94,.27),'variants':(.03,.44,.94,.34),'safe':(.03,.81,.55,.15),'actions':(.61,.81,.36,.15)},
        {'header':(.02,.03,.96,.075),'source':(.02,.14,.38,.72),'variants':(.43,.14,.55,.50),'safe':(.43,.67,.31,.19),'actions':(.77,.67,.21,.19)},
        {'header':(.015,.03,.97,.07),'source':(.015,.13,.36,.74),'variants':(.40,.13,.585,.51),'safe':(.40,.67,.34,.20),'actions':(.765,.67,.22,.20)}),tags=['visual','cinematic','aspect','variants'],math_hooks={'safe_inset_ratio':[0.04,0.14]},quality=q),
      'visual.cinematic.review-export':screen('visual.cinematic.review-export','Cinematic title and overlay review/export','creative.cinematic','visual.cinematic.motion','review exact text, timing conflicts, safe-area compliance, variant coverage and output targets before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','cinematic','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.cinematic.core','version':1,'name':'Editable cinematic titles and overlays core','kind':'product','domain':'creative.cinematic','tags':['visual','cinematic','title','credits','overlay','product'],'origin':origin(),'style':'visual.cinematic.motion','intent':'source-first cinematic title, credit, subtitle and timed overlay editing with exact content/timing and safe-area variants','screens':ids,'flow':[
      ['visual.cinematic.project-hub','visual.cinematic.title-editor','edit-title'],['visual.cinematic.title-editor','visual.cinematic.overlay-timeline','place-title'],['visual.cinematic.project-hub','visual.cinematic.chapter-editor','edit-chapters'],['visual.cinematic.project-hub','visual.cinematic.lower-third','edit-lower-thirds'],['visual.cinematic.project-hub','visual.cinematic.subtitle-editor','edit-subtitles'],['visual.cinematic.project-hub','visual.cinematic.credits-editor','edit-credits'],['visual.cinematic.overlay-timeline','visual.cinematic.transition-editor','edit-transitions'],['visual.cinematic.overlay-timeline','visual.cinematic.aspect-variants','adapt-formats'],['visual.cinematic.aspect-variants','visual.cinematic.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.cinematic.core':product},'product')

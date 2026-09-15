"""Editable video, program and stream overlay foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"video overlay {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_video_overlay_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.broadcast.modular':{
        'intent':'modular live/program presentation with source truth, readable status hierarchy and separately editable scene composition',
        'tokens':{'canvas':'#0a0c11','surface':'#151922','surface_raised':'#202735','text':'#f2f5f7','muted':'#a4adb8','accent':'#79c9ff','warning':'#efb76f','danger':'#e8797e','line':'#424a57'},
        'shape':{'panel_radius_ratio':0.012,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.55,'tracking':0.012},
        'depth':{'layers':6,'shadow':'tight','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':160,'slow_ms':320,'principle':'source and status truth before decorative motion'},
    }},'style')

    _merge(primitives,{
        'source-window':{'role':'one bound video/image/program source with exact source identity and crop/fit state','states':['live','preview','offline','missing','selected'],'source_identity_must_be_explicit':True},
        'camera-slot':{'role':'camera/source presentation region with source, crop, framing and privacy state','states':['live','preview','muted','blocked','missing'],'source_and_crop_remain_separate':True},
        'status-field':{'role':'one observed score/status/value field with source and freshness state','states':['current','stale','unknown','error'],'value_source_freshness_required':True},
        'alert-cue':{'role':'one timed alert/notification overlay with source, payload and lifecycle','states':['queued','active','dismissed','failed'],'unobserved_success_forbidden':True},
        'chat-panel':{'role':'message/event feed with delivery/source/moderation state','states':['active','muted','offline','error'],'delivery_state_must_be_explicit':True},
        'scene-state':{'role':'one exact scene/layout identity with current/preview/transition state','states':['preview','live','transitioning','blocked'],'scene_identity_must_be_exact':True},
        'overlay-zone':{'role':'named presentation region with anchor, priority and safe-area state','states':['active','selected','hidden','conflict'],'overlap_conflicts_must_be_visible':True},
        'identity-panel':{'role':'show/channel/event identity with source assets and editable placement','states':['active','selected','alternate','missing-source'],'source_and_transform_remain_separate':True},
        'transition-state':{'role':'derived scene transition with from/to scene, duration and progress','states':['ready','active','complete','failed'],'from_to_identity_required':True},
        'output-monitor':{'role':'one program/output target with dimensions, frame rate and health/status state','states':['ready','live','warning','offline','error'],'target_state_must_be_observed':True},
    },'primitive')

    q=['every live-looking value keeps explicit source and freshness state','scene/source identity remains exact through preview, live and transition states','camera/source crop never replaces source identity','alerts and message delivery never imply unobserved success','output variants remain derived from richer scene composition']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.broadcast.project-hub':screen('visual.broadcast.project-hub','Broadcast/stream project hub','creative.broadcast','visual.broadcast.modular','browse scene sets, source health, identity assets and output targets before going live or exporting',v(
        {'header':(.03,.03,.94,.08),'scenes':(.03,.14,.94,.30),'sources':(.03,.47,.45,.38),'outputs':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'scenes':(.02,.14,.22,.82),'sources':(.27,.14,.46,.82),'outputs':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'scenes':(.015,.13,.20,.84),'sources':(.24,.13,.50,.84),'outputs':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','broadcast','stream','project'],quality=q),
      'visual.broadcast.scene-editor':screen('visual.broadcast.scene-editor','Scene layout editor','creative.broadcast','visual.broadcast.modular','compose source windows, cameras, identity, score/status and alerts into one exact scene definition',v(
        {'toolbar':(.02,.02,.96,.07),'canvas':(.12,.11,.76,.56),'layers':(.02,.11,.08,.56),'properties':(.90,.11,.08,.56),'scenes':(.02,.70,.46,.28),'status':(.51,.70,.47,.28)},
        {'toolbar':(.015,.02,.97,.065),'layers':(.015,.105,.16,.75),'canvas':(.19,.105,.58,.75),'properties':(.79,.105,.195,.75),'scenes':(.19,.88,.38,.10),'status':(.59,.88,.395,.10)},
        {'toolbar':(.012,.02,.976,.06),'layers':(.012,.10,.14,.77),'canvas':(.17,.10,.62,.77),'properties':(.805,.10,.183,.77),'scenes':(.17,.90,.40,.08),'status':(.59,.90,.398,.08)}),tags=['visual','broadcast','scene','editor'],math_hooks={'safe_inset_ratio':[0.03,0.10]},quality=q),
      'visual.broadcast.source-router':screen('visual.broadcast.source-router','Source router and health','creative.broadcast','visual.broadcast.modular','bind exact source identities, preview state, fallback behavior and source health without pretending unavailable feeds exist',v(
        {'header':(.03,.03,.94,.08),'sources':(.03,.14,.94,.40),'preview':(.03,.57,.58,.30),'details':(.64,.57,.33,.22),'actions':(.64,.82,.33,.05)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','broadcast','source','router'],quality=q),
      'visual.broadcast.camera-editor':screen('visual.broadcast.camera-editor','Camera/source frame editor','creative.broadcast','visual.broadcast.modular','edit source framing, crop, masks, privacy/visibility state and composition without changing source identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.42),'sources':(.03,.59,.30,.28),'crop':(.36,.59,.29,.28),'state':(.68,.59,.29,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.18,.72),'preview':(.225,.14,.52,.72),'crop':(.77,.14,.21,.34),'state':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.16,.74),'preview':(.195,.13,.56,.74),'crop':(.775,.13,.21,.35),'state':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','broadcast','camera','source'],quality=q),
      'visual.broadcast.score-status':screen('visual.broadcast.score-status','Score and status field editor','creative.broadcast','visual.broadcast.modular','bind visible score/status fields to exact observed data sources with freshness and unknown/error states visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'fields':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'fields':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'fields':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','broadcast','score','status'],quality=q),
      'visual.broadcast.alert-editor':screen('visual.broadcast.alert-editor','Alert and notification editor','creative.broadcast','visual.broadcast.modular','edit alert source, payload, timing, priority and failure state without implying delivery/success that was not observed',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'alerts':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'alerts':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'alerts':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','broadcast','alert','notification'],quality=q),
      'visual.broadcast.chat-social':screen('visual.broadcast.chat-social','Chat and event-feed editor','creative.broadcast','visual.broadcast.modular','compose message/event feeds with exact source, delivery, moderation and offline/error state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'feed':(.03,.49,.58,.38),'details':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'feed':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'feed':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','broadcast','chat','feed'],quality=q),
      'visual.broadcast.scene-set':screen('visual.broadcast.scene-set','Scene set and switching editor','creative.broadcast','visual.broadcast.modular','manage exact scene identities, preview/live state and explicit transitions between scenes without hidden scene substitution',v(
        {'header':(.03,.03,.94,.08),'scenes':(.03,.14,.94,.42),'preview':(.03,.59,.55,.28),'transition':(.61,.59,.36,.19),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'scenes':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'transition':(.80,.14,.18,.48),'actions':(.80,.65,.18,.21)},
        {'header':(.015,.03,.97,.07),'scenes':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'transition':(.795,.13,.19,.49),'actions':(.795,.65,.19,.22)}),tags=['visual','broadcast','scene','switching'],quality=q),
      'visual.broadcast.format-variants':screen('visual.broadcast.format-variants','Overlay format and safe-area variants','creative.broadcast','visual.broadcast.modular','compare landscape, portrait, square and vertical layouts while preserving exact source bindings and scene state',v(
        {'header':(.03,.03,.94,.08),'source':(.03,.14,.94,.27),'variants':(.03,.44,.94,.34),'safe':(.03,.81,.55,.15),'actions':(.61,.81,.36,.15)},
        {'header':(.02,.03,.96,.075),'source':(.02,.14,.38,.72),'variants':(.43,.14,.55,.50),'safe':(.43,.67,.31,.19),'actions':(.77,.67,.21,.19)},
        {'header':(.015,.03,.97,.07),'source':(.015,.13,.36,.74),'variants':(.40,.13,.585,.51),'safe':(.40,.67,.34,.20),'actions':(.765,.67,.22,.20)}),tags=['visual','broadcast','format','variants'],math_hooks={'safe_inset_ratio':[0.03,0.12]},quality=q),
      'visual.broadcast.review-output':screen('visual.broadcast.review-output','Broadcast/stream review and output','creative.broadcast','visual.broadcast.modular','review source health, stale/unknown status, scene identity, overlap conflicts and exact output targets before live/program/export use',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'outputs':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'outputs':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'outputs':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','broadcast','review','output'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.broadcast.core','version':1,'name':'Editable video and stream overlay core','kind':'product','domain':'creative.broadcast','tags':['visual','broadcast','stream','overlay','product'],'origin':origin(),'style':'visual.broadcast.modular','intent':'source-first scene/overlay editing for video, program and stream presentation with exact source/status/scene/output state','screens':ids,'flow':[
      ['visual.broadcast.project-hub','visual.broadcast.scene-editor','edit-scene'],['visual.broadcast.scene-editor','visual.broadcast.source-router','bind-sources'],['visual.broadcast.scene-editor','visual.broadcast.camera-editor','edit-camera'],['visual.broadcast.scene-editor','visual.broadcast.score-status','edit-status'],['visual.broadcast.scene-editor','visual.broadcast.alert-editor','edit-alerts'],['visual.broadcast.scene-editor','visual.broadcast.chat-social','edit-feed'],['visual.broadcast.scene-editor','visual.broadcast.scene-set','edit-scene-set'],['visual.broadcast.scene-set','visual.broadcast.format-variants','adapt-formats'],['visual.broadcast.format-variants','visual.broadcast.review-output','review-output']], 'quality':q}
    _merge(products,{'visual.broadcast.core':product},'product')

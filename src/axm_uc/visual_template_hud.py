"""Source-bound HUD theme, skin and readability foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"hud {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_hud_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.hud.system':{
        'intent':'source-bound HUD theming with exact component identity, data bindings, layout anchors, readability constraints and platform/input variants',
        'tokens':{'canvas':'#0a0e12','surface':'#151c22','surface_raised':'#202932','text':'#eef3f5','muted':'#9faab2','accent':'#84c8b6','warning':'#e3ba6c','danger':'#df7678','line':'#3e4d57'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.5,'tracking':0.010},
        'depth':{'layers':7,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':300,'principle':'readability and gameplay state before decoration'},
    }},'style')

    _merge(primitives,{
        'hud-source':{'role':'exact HUD family identity with source/version/digest and owning game/product context','states':['known','active','deprecated','unknown'],'identity_source_version_context_required':True},
        'hud-component':{'role':'exact HUD component identity/role/source with semantic purpose and status','states':['active','optional','hidden','unknown'],'identity_role_source_required':True},
        'hud-layout-anchor':{'role':'component layout anchor with exact viewport/region/constraint and source state','states':['bound','adaptive','locked','unknown'],'component_region_constraints_required':True},
        'hud-data-binding':{'role':'exact gameplay/system data binding with subject/field/source/freshness and fallback state','states':['live','stale','missing','unknown'],'subject_field_source_freshness_required':True},
        'hud-readability-rule':{'role':'readability constraint with exact target, viewing/input context, threshold and evidence/source','states':['pass','warning','fail','unknown'],'target_context_threshold_source_required':True},
        'hud-safe-region':{'role':'platform/view safe region with exact viewport/platform/source and margins','states':['active','constrained','unknown'],'viewport_platform_source_required':True},
        'hud-alert-state':{'role':'semantic alert/feedback state with exact source, severity, visual/audio channels and acknowledgement state','states':['info','warning','critical','resolved','unknown'],'source_severity_channels_required':True},
        'hud-platform-variant':{'role':'platform/input HUD variant with exact base, deltas, device/input context and availability','states':['active','alternate','restricted','unknown'],'base_delta_device_input_required':True},
        'hud-theme-variant':{'role':'skin/theme variant with exact base, token/component deltas and intended context','states':['active','alternate','event','archived'],'base_token_component_delta_required':True},
        'hud-export-target':{'role':'HUD export target with exact components, bindings, layouts, platform variants, readability and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['HUD identity, components, data bindings, layout anchors, alerts, themes and platform variants remain separately editable','a polished HUD preview never proves gameplay/system state is true','component position never creates a data binding and icon/color alone never carries critical meaning','readability remains bound to exact viewing, platform and input context with source/evidence visible','platform and reduced-information variants preserve required semantic feedback rather than hiding essential state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.hud.project-hub':screen('visual.hud.project-hub','HUD system project hub','creative.hud','visual.hud.system','browse HUD families, component coverage, platform variants, readability state and export targets',v(
        {'header':(.03,.03,.94,.08),'families':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'variants':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'families':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'variants':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'families':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'variants':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','hud','game','project'],quality=q),
      'visual.hud.components':screen('visual.hud.components','HUD component library','creative.hud','visual.hud.system','edit exact HUD component identity, role, source and semantic purpose without flattening components into one image',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'components':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'components':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'components':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','hud','component','library'],quality=q),
      'visual.hud.layout':screen('visual.hud.layout','HUD layout and anchor editor','creative.hud','visual.hud.system','edit exact component anchors, viewport regions, constraints and safe areas across compact/standard/wide contexts',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.42),'anchors':(.03,.59,.55,.28),'details':(.61,.59,.36,.20),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'anchors':(.02,.14,.22,.72),'stage':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'anchors':(.015,.13,.20,.74),'stage':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','hud','layout','anchor'],math_hooks={'safe_margin_ratio':[0.01,0.12],'cluster_gap_ratio':[0.01,0.08]},quality=q),
      'visual.hud.data-bindings':screen('visual.hud.data-bindings','HUD data-binding editor','creative.hud','visual.hud.system','bind exact gameplay/system subjects and fields to HUD components with source/freshness/fallback state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'bindings':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'bindings':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'bindings':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','hud','data','binding'],quality=q),
      'visual.hud.readability':screen('visual.hud.readability','HUD readability editor','creative.hud','visual.hud.system','edit readability constraints per exact target, viewport, viewing distance/platform/input context and evidence source',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'rules':(.03,.51,.55,.34),'evidence':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'rules':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'evidence':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'rules':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'evidence':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','hud','readability','accessibility'],quality=q),
      'visual.hud.alerts-feedback':screen('visual.hud.alerts-feedback','HUD alerts and feedback editor','creative.hud','visual.hud.system','author exact semantic alert states with source, severity and multi-channel feedback instead of color/icon implication alone',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'alerts':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'alerts':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'alerts':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','hud','alert','feedback'],quality=q),
      'visual.hud.platform-input':screen('visual.hud.platform-input','HUD platform and input variant editor','creative.hud','visual.hud.system','edit exact platform/input/device variants as deltas from a named HUD base while preserving semantic information',v(
        {'header':(.03,.03,.94,.08),'default':(.03,.14,.45,.42),'variant':(.52,.14,.45,.42),'rules':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'default':(.02,.14,.36,.63),'variant':(.40,.14,.36,.63),'rules':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'default':(.015,.13,.37,.65),'variant':(.405,.13,.37,.65),'rules':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','hud','platform','input'],quality=q),
      'visual.hud.theme-skin':screen('visual.hud.theme-skin','HUD theme and skin editor','creative.hud','visual.hud.system','edit exact theme/skin token and component deltas without changing data bindings or gameplay state',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'themes':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'themes':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'themes':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','hud','theme','skin'],quality=q),
      'visual.hud.compare-preview':screen('visual.hud.compare-preview','HUD comparison and preview','creative.hud','visual.hud.system','compare exact HUD variants across viewport/platform/input states while showing data/readability status independently',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.48),'right':(.52,.14,.45,.48),'checks':(.03,.65,.58,.22),'actions':(.64,.65,.33,.22)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.36,.63),'right':(.40,.14,.36,.63),'checks':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.37,.65),'right':(.405,.13,.37,.65),'checks':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','hud','compare','preview'],quality=q),
      'visual.hud.review-export':screen('visual.hud.review-export','HUD review and export','creative.hud','visual.hud.system','review missing bindings, unreadable states, unsafe regions, platform gaps, alert semantics and export requirements',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','hud','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.hud.core','version':1,'name':'Source-bound HUD theme and skin core','kind':'product','domain':'creative.hud','tags':['visual','hud','game','ui','product'],'origin':origin(),'style':'visual.hud.system','intent':'source-first HUD authoring with exact components, data bindings, layout/readability rules, alerts, platform/input variants and themes','screens':ids,'flow':[
      ['visual.hud.project-hub','visual.hud.components','edit-components'],['visual.hud.components','visual.hud.layout','edit-layout'],['visual.hud.components','visual.hud.data-bindings','edit-bindings'],['visual.hud.project-hub','visual.hud.readability','edit-readability'],['visual.hud.project-hub','visual.hud.alerts-feedback','edit-alerts'],['visual.hud.project-hub','visual.hud.platform-input','edit-platforms'],['visual.hud.project-hub','visual.hud.theme-skin','edit-theme'],['visual.hud.project-hub','visual.hud.compare-preview','compare'],['visual.hud.project-hub','visual.hud.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.hud.core':product},'product')

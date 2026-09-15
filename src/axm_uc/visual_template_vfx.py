"""Source-bound VFX and particle reference-authoring foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"vfx {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_vfx_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.vfx.effect':{
        'intent':'state-bound VFX/particle authoring with exact emitter identity, spawn/timing/module/layer state, interaction hooks and reduced-effect equivalents',
        'tokens':{'canvas':'#090e13','surface':'#151d25','surface_raised':'#202b35','text':'#eef4f7','muted':'#9eabb4','accent':'#83c9dc','warning':'#e5b86a','danger':'#df7379','line':'#3b4c58'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.004,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.5,'tracking':0.011},
        'depth':{'layers':8,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':70,'standard_ms':160,'slow_ms':300,'principle':'runtime/state truth before effect spectacle'},
    }},'style')

    _merge(primitives,{
        'vfx-source':{'role':'exact effect identity with source/version/digest and semantic purpose','states':['known','active','deprecated','unknown'],'identity_source_version_purpose_required':True},
        'emitter-state':{'role':'exact emitter identity/configuration with trigger, lifetime, rate/burst and enabled state','states':['idle','armed','emitting','disabled'],'trigger_lifetime_rate_required':True},
        'spawn-region':{'role':'exact particle spawn region/shape with source transform, dimensions and distribution state','states':['point','line','surface','volume','mesh'],'shape_transform_dimensions_required':True},
        'emission-curve':{'role':'bounded time/value curve for emission, size, opacity, color or other explicit channel','states':['constant','curve','event','unknown'],'channel_time_value_required':True},
        'particle-module':{'role':'named particle behavior module with exact parameters, order and source/status','states':['enabled','disabled','conditional','unknown'],'identity_parameters_order_required':True},
        'vfx-layer':{'role':'effect layer with exact identity, blend/order/depth relation and source state','states':['active','muted','solo','unknown'],'identity_blend_order_required':True},
        'vfx-interaction-hook':{'role':'runtime interaction/collision/gameplay hook with exact subject/event/response/source status','states':['active','disabled','conditional','unknown'],'subject_event_response_source_required':True},
        'vfx-timing-event':{'role':'exact event marker on effect timeline with trigger/source and semantic purpose','states':['armed','fired','suppressed','unknown'],'time_event_source_required':True},
        'reduced-effect-rule':{'role':'reduced/off effect variant preserving required semantic feedback while lowering visual intensity','states':['default','reduced','minimal','off'],'equivalent_semantic_feedback_required':True},
        'vfx-export-target':{'role':'effect export target with exact source, modules, timing, runtime hooks, performance/accessibility requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['effect identity, emitters, spawn regions, curves, modules, layers and interaction hooks remain separately editable','a spectacular preview never proves that a runtime/gameplay event occurred','collision, damage, interaction or trigger semantics require exact source-bound hooks rather than visual implication','timing and emission curves remain explicit channels instead of hidden animation baked into preview output','reduced-effect variants preserve required semantic feedback while reducing visual intensity or clutter']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.vfx.project-hub':screen('visual.vfx.project-hub','VFX project hub','creative.vfx','visual.vfx.effect','browse effects, runtime coverage, module sets, reduced-effect variants and output targets',v(
        {'header':(.03,.03,.94,.08),'effects':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'variants':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'effects':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'variants':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'effects':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'variants':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','vfx','particle','project'],quality=q),
      'visual.vfx.effect-stage':screen('visual.vfx.effect-stage','VFX effect stage','creative.vfx','visual.vfx.effect','preview exact effect identity, layers and source state while keeping runtime/gameplay status separate from presentation',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.48),'identity':(.03,.65,.45,.22),'runtime':(.51,.65,.46,.22),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'identity':(.02,.14,.18,.72),'stage':(.225,.14,.55,.72),'runtime':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'identity':(.015,.13,.16,.74),'stage':(.195,.13,.58,.74),'runtime':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','vfx','effect','stage'],math_hooks={'effect_coverage_ratio':[0.38,0.78],'safe_margin_ratio':[0.01,0.08]},quality=q),
      'visual.vfx.emitter-editor':screen('visual.vfx.emitter-editor','Emitter state editor','creative.vfx','visual.vfx.effect','edit exact emitter trigger, lifetime, rate/burst, enabled state and source identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'emitters':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'emitters':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'emitters':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','vfx','emitter','state'],quality=q),
      'visual.vfx.spawn-region':screen('visual.vfx.spawn-region','Particle spawn-region editor','creative.vfx','visual.vfx.effect','edit exact spawn shape, source transform, dimensions and distribution without conflating preview spread with source geometry',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'regions':(.03,.53,.45,.34),'details':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'regions':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'regions':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','vfx','spawn','region'],quality=q),
      'visual.vfx.curves-timing':screen('visual.vfx.curves-timing','VFX curves and timing editor','creative.vfx','visual.vfx.effect','edit exact named channels, time/value curves and event markers with bounded values and semantic purpose',v(
        {'header':(.03,.03,.94,.08),'curve':(.03,.14,.94,.34),'channels':(.03,.51,.55,.34),'events':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'channels':(.02,.14,.25,.72),'curve':(.30,.14,.45,.72),'events':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'channels':(.015,.13,.23,.74),'curve':(.265,.13,.49,.74),'events':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','vfx','curve','timing'],math_hooks={'timeline_duration_ratio':[0.08,4.0],'curve_sample_ratio':[0.01,0.20]},quality=q),
      'visual.vfx.modules':screen('visual.vfx.modules','Particle module editor','creative.vfx','visual.vfx.effect','edit exact ordered particle behavior modules and parameters with enable/conditional state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'modules':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'modules':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'modules':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','vfx','module','particle'],quality=q),
      'visual.vfx.layers-composite':screen('visual.vfx.layers-composite','VFX layer and composite editor','creative.vfx','visual.vfx.effect','edit exact layer identity, blend/order/depth relationships without flattening source layers into one canonical image',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'layers':(.03,.57,.45,.30),'details':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'layers':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'layers':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','vfx','layer','composite'],quality=q),
      'visual.vfx.interaction-hooks':screen('visual.vfx.interaction-hooks','VFX runtime interaction-hook editor','creative.vfx','visual.vfx.effect','bind collision, impact, gameplay and state-change hooks to exact subjects/events/responses with source/status explicit',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'hooks':(.03,.49,.58,.38),'details':(.64,.49,.33,.28),'actions':(.64,.80,.33,.07)},
        {'header':(.02,.03,.96,.075),'hooks':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'hooks':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','vfx','interaction','runtime'],quality=q),
      'visual.vfx.reduced-performance':screen('visual.vfx.reduced-performance','Reduced-effect and performance variant editor','creative.vfx','visual.vfx.effect','author reduced/minimal variants that preserve required semantic feedback while controlling intensity, count and runtime budget',v(
        {'header':(.03,.03,.94,.08),'default':(.03,.14,.45,.42),'reduced':(.52,.14,.45,.42),'rules':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'default':(.02,.14,.36,.63),'reduced':(.40,.14,.36,.63),'rules':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'default':(.015,.13,.37,.65),'reduced':(.405,.13,.37,.65),'rules':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','vfx','reduced-effect','performance'],quality=q),
      'visual.vfx.review-export':screen('visual.vfx.review-export','VFX review and export','creative.vfx','visual.vfx.effect','review missing hooks, unknown timing/state, layer/module coverage, semantic feedback variants and runtime/export requirements',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','vfx','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.vfx.core','version':1,'name':'Source-bound VFX and particle authoring core','kind':'product','domain':'creative.vfx','tags':['visual','vfx','particle','effect','product'],'origin':origin(),'style':'visual.vfx.effect','intent':'source-first VFX/particle authoring with exact effect/emitter/spawn/timing/module/layer/interaction and reduced-effect state','screens':ids,'flow':[
      ['visual.vfx.project-hub','visual.vfx.effect-stage','open-effect'],['visual.vfx.effect-stage','visual.vfx.emitter-editor','edit-emitter'],['visual.vfx.emitter-editor','visual.vfx.spawn-region','edit-spawn'],['visual.vfx.effect-stage','visual.vfx.curves-timing','edit-timing'],['visual.vfx.effect-stage','visual.vfx.modules','edit-modules'],['visual.vfx.effect-stage','visual.vfx.layers-composite','edit-layers'],['visual.vfx.effect-stage','visual.vfx.interaction-hooks','edit-hooks'],['visual.vfx.project-hub','visual.vfx.reduced-performance','edit-reduced'],['visual.vfx.project-hub','visual.vfx.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.vfx.core':product},'product')

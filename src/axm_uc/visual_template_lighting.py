"""Source-bound lighting, atmosphere and post-process look foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"lighting {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_lighting_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.look.system':{
        'intent':'source-bound lighting/post-process look authoring with exact exposure, tone, grade, fog, bloom, layer, scene-binding and platform states',
        'tokens':{'canvas':'#090d11','surface':'#141b22','surface_raised':'#202832','text':'#eff3f5','muted':'#9fa9b1','accent':'#8bc6c4','warning':'#e2b969','danger':'#de7477','line':'#3e4b56'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.48,'tracking':0.010},
        'depth':{'layers':8,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':300,'principle':'world/source state before presentation look'},
    }},'style')

    _merge(primitives,{
        'look-source':{'role':'exact look/preset identity with source/version/digest, owning scene/product context and purpose','states':['known','active','archived','unknown'],'identity_source_version_context_required':True},
        'exposure-state':{'role':'explicit exposure/brightness adaptation state with value/range, source and context','states':['manual','auto','bounded','unknown'],'value_range_source_context_required':True},
        'tone-map-state':{'role':'tone-mapping operator/state with exact operator, parameters, output space and source','states':['active','alternate','disabled','unknown'],'operator_parameters_output_source_required':True},
        'color-grade-state':{'role':'color-grade transform with exact source/LUT-or-curves, working/output spaces and intensity','states':['active','alternate','disabled','unknown'],'transform_spaces_intensity_source_required':True},
        'fog-atmosphere-state':{'role':'fog/atmosphere state with exact density/range/color/scattering source and context','states':['active','bounded','disabled','unknown'],'density_range_scattering_source_required':True},
        'bloom-glare-state':{'role':'bloom/glare state with exact threshold/intensity/radius/quality and source','states':['active','reduced','disabled','unknown'],'threshold_intensity_radius_source_required':True},
        'postprocess-layer':{'role':'ordered post-process layer with exact identity, parameters, blend/order/scope and source','states':['active','muted','conditional','unknown'],'identity_parameters_blend_order_scope_required':True},
        'scene-look-binding':{'role':'exact scene/camera/region to look binding with target identity, source and activation state','states':['bound','conditional','disabled','unknown'],'target_look_source_activation_required':True},
        'look-platform-variant':{'role':'performance/accessibility/platform look variant with exact base, deltas, context and availability','states':['active','reduced','alternate','unknown'],'base_delta_platform_context_required':True},
        'look-export-target':{'role':'look-system export target with exact states, bindings, color spaces, variants and runtime requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['exposure, tone mapping, grading, fog, bloom, layers, bindings and platform variants remain separately editable','a convincing look preview never silently becomes authoritative world lighting or gameplay state','color grade and post-process transforms never replace source materials, lights, geometry or environment state','scene/camera application requires exact source-bound bindings rather than visual similarity or proximity','performance and accessibility variants preserve required visibility/state legibility while changing presentation cost or intensity']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.look.project-hub':screen('visual.look.project-hub','Lighting and look project hub','creative.look','visual.look.system','browse source-bound looks, scene bindings, state coverage, platform variants and export targets',v(
        {'header':(.03,.03,.94,.08),'looks':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'variants':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'looks':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'variants':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'looks':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'variants':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','lighting','look','project'],quality=q),
      'visual.look.exposure-tone':screen('visual.look.exposure-tone','Exposure and tone-map editor','creative.look','visual.look.system','edit exact exposure ranges/adaptation and tone-mapping operator/output space without rewriting world lighting',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.38),'exposure':(.03,.55,.45,.32),'tone':(.51,.55,.46,.32),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'exposure':(.02,.14,.23,.72),'preview':(.28,.14,.47,.72),'tone':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'exposure':(.015,.13,.21,.74),'preview':(.26,.13,.49,.74),'tone':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','lighting','exposure','tone'],math_hooks={'exposure_ev_range':[-12,20],'highlight_headroom_ratio':[0.02,0.35]},quality=q),
      'visual.look.color-grade':screen('visual.look.color-grade','Color-grade editor','creative.look','visual.look.system','edit exact grade transforms, LUT/curve source, color spaces and intensity while preserving source material identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'transforms':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'transforms':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'transforms':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','lighting','color-grade','lut'],quality=q),
      'visual.look.fog-atmosphere':screen('visual.look.fog-atmosphere','Fog and atmosphere editor','creative.look','visual.look.system','edit exact fog density/range/scattering/color state and source without baking atmosphere into base environment identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.38),'states':(.03,.55,.55,.32),'details':(.61,.55,.36,.24),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'states':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'states':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','lighting','fog','atmosphere'],quality=q),
      'visual.look.bloom-glare':screen('visual.look.bloom-glare','Bloom and glare editor','creative.look','visual.look.system','edit exact bloom/glare threshold, intensity, radius and quality with reduced/disabled states explicit',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.38),'states':(.03,.55,.55,.32),'details':(.61,.55,.36,.24),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'states':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'states':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','lighting','bloom','glare'],quality=q),
      'visual.look.layer-stack':screen('visual.look.layer-stack','Post-process layer-stack editor','creative.look','visual.look.system','edit ordered source-bound post-process layers, parameters, blend and scope without flattening them into one canonical output',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'layers':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'layers':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'layers':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','lighting','postprocess','layer'],quality=q),
      'visual.look.scene-bindings':screen('visual.look.scene-bindings','Scene and camera look-binding editor','creative.look','visual.look.system','bind exact scenes, cameras or regions to exact look identities with activation/source state explicit',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'bindings':(.03,.49,.58,.38),'details':(.64,.49,.33,.28),'actions':(.64,.80,.33,.07)},
        {'header':(.02,.03,.96,.075),'bindings':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'bindings':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','lighting','scene','binding'],quality=q),
      'visual.look.platform-performance':screen('visual.look.platform-performance','Lighting look platform and performance variants','creative.look','visual.look.system','author exact reduced/performance/accessibility variants preserving visibility and state legibility while changing presentation cost',v(
        {'header':(.03,.03,.94,.08),'default':(.03,.14,.45,.42),'variant':(.52,.14,.45,.42),'rules':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'default':(.02,.14,.36,.63),'variant':(.40,.14,.36,.63),'rules':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'default':(.015,.13,.37,.65),'variant':(.405,.13,.37,.65),'rules':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','lighting','platform','performance'],quality=q),
      'visual.look.compare-preview':screen('visual.look.compare-preview','Lighting look comparison preview','creative.look','visual.look.system','compare exact looks and variants while keeping scene/source state and applied look bindings visible independently',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.48),'right':(.52,.14,.45,.48),'checks':(.03,.65,.58,.22),'actions':(.64,.65,.33,.22)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.36,.63),'right':(.40,.14,.36,.63),'checks':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.37,.65),'right':(.405,.13,.37,.65),'checks':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','lighting','compare','preview'],quality=q),
      'visual.look.review-export':screen('visual.look.review-export','Lighting look review and export','creative.look','visual.look.system','review unknown color spaces, missing scene bindings, unsafe visibility, unsupported variants and export/runtime requirements',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','lighting','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.look.core','version':1,'name':'Source-bound lighting and post-process look core','kind':'product','domain':'creative.look','tags':['visual','lighting','postprocess','look','product'],'origin':origin(),'style':'visual.look.system','intent':'source-first lighting/look authoring with exact exposure, tone, grade, fog, bloom, ordered layers, scene bindings and platform variants','screens':ids,'flow':[
      ['visual.look.project-hub','visual.look.exposure-tone','edit-exposure-tone'],['visual.look.project-hub','visual.look.color-grade','edit-grade'],['visual.look.project-hub','visual.look.fog-atmosphere','edit-atmosphere'],['visual.look.project-hub','visual.look.bloom-glare','edit-bloom'],['visual.look.project-hub','visual.look.layer-stack','edit-layers'],['visual.look.project-hub','visual.look.scene-bindings','bind-scenes'],['visual.look.project-hub','visual.look.platform-performance','edit-variants'],['visual.look.project-hub','visual.look.compare-preview','compare'],['visual.look.project-hub','visual.look.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.look.core':product},'product')

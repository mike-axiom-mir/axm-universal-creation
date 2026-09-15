"""Editable 3D showroom, object gallery and comparison foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"showroom {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_showroom_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.showroom.studio':{
        'intent':'premium object presentation with exact asset, camera, material, variant and annotation identity kept separate from presentation',
        'tokens':{'canvas':'#0a0c10','surface':'#151922','surface_raised':'#222833','text':'#f3f4f2','muted':'#a8afb8','accent':'#8fd6ff','warning':'#e4bc70','danger':'#dd7278','line':'#424a56'},
        'shape':{'panel_radius_ratio':0.015,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.5,'tracking':0.012},
        'depth':{'layers':8,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':360,'principle':'object identity and state before showcase motion'},
    }},'style')

    _merge(primitives,{
        'showroom-object':{'role':'exact object/asset identity with source/version and presentation state','states':['loaded','selected','missing','unknown'],'source_identity_version_required':True},
        'orbit-rig':{'role':'camera/orbit target with exact pivot, angle/range and interaction bounds','states':['idle','orbiting','locked','unknown'],'target_pivot_range_required':True},
        'camera-preset':{'role':'named view with exact projection/lens/transform state','states':['active','selected','invalid','unknown'],'projection_lens_transform_required':True},
        'material-slot':{'role':'exact object part/material binding with source and variant state','states':['bound','selected','missing','unknown'],'part_material_source_required':True},
        'variant-option':{'role':'exact product/object variant with properties and availability/source state','states':['available','selected','unavailable','unknown'],'identity_properties_availability_required':True},
        'object-annotation':{'role':'annotation bound to exact object/component/local anchor and content','states':['visible','selected','hidden','unresolved'],'target_anchor_content_required':True},
        'comparison-object':{'role':'exact comparison object/variant reference and comparable-field set','states':['loaded','selected','missing','incompatible'],'reference_and_fields_required':True},
        'turntable-state':{'role':'derived rotation presentation state with exact target, angle/speed and playback state','states':['idle','playing','paused','blocked'],'target_angle_speed_required':True},
        'measurement-callout':{'role':'dimension/performance/spec callout with exact value, unit and source','states':['observed','declared','derived','unknown'],'value_unit_source_required':True},
        'showroom-export-target':{'role':'output target with object/variant/camera/material/annotation inclusion requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['object identity, camera, material, variant and annotation state remain separately editable','preview geometry or material appearance never substitutes for exact source asset identity','variant availability and specifications remain explicit rather than inferred from appearance','comparison fields and measurements retain value, unit and source','turntable and export presentation remain derived from richer showroom source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.showroom.project-hub':screen('visual.showroom.project-hub','Showroom project hub','creative.showroom','visual.showroom.studio','browse objects, variants, material sets, camera sets and output targets with missing source state visible',v(
        {'header':(.03,.03,.94,.08),'objects':(.03,.14,.94,.30),'variants':(.03,.47,.45,.38),'targets':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'objects':(.02,.14,.22,.82),'variants':(.27,.14,.46,.82),'targets':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'objects':(.015,.13,.20,.84),'variants':(.24,.13,.50,.84),'targets':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','showroom','object','project'],quality=q),
      'visual.showroom.object-stage':screen('visual.showroom.object-stage','Hero object stage','creative.showroom','visual.showroom.studio','present and edit exact object source, staging, scale/reference frame and lighting sockets without replacing source identity',v(
        {'toolbar':(.02,.02,.96,.07),'stage':(.10,.11,.80,.56),'objects':(.02,.11,.06,.56),'properties':(.92,.11,.06,.56),'source':(.02,.70,.46,.28),'checks':(.51,.70,.47,.28)},
        {'toolbar':(.015,.02,.97,.065),'objects':(.015,.105,.15,.76),'stage':(.19,.105,.58,.76),'properties':(.79,.105,.195,.76),'source':(.19,.89,.38,.09),'checks':(.59,.89,.395,.09)},
        {'toolbar':(.012,.02,.976,.06),'objects':(.012,.10,.13,.78),'stage':(.165,.10,.63,.78),'properties':(.81,.10,.178,.78),'source':(.165,.90,.40,.08),'checks':(.59,.90,.398,.08)}),tags=['visual','showroom','object','stage'],math_hooks={'hero_coverage_ratio':[0.42,0.72],'stage_margin_ratio':[0.03,0.12]},quality=q),
      'visual.showroom.orbit-camera':screen('visual.showroom.orbit-camera','Orbit and camera editor','creative.showroom','visual.showroom.studio','edit exact orbit target/pivot, camera projection, lens/transform and saved views with invalid state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.38),'rig':(.03,.55,.45,.32),'camera':(.51,.55,.46,.32),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'rig':(.02,.14,.23,.72),'preview':(.28,.14,.47,.72),'camera':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'rig':(.015,.13,.21,.74),'preview':(.26,.13,.49,.74),'camera':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','showroom','orbit','camera'],quality=q),
      'visual.showroom.material-editor':screen('visual.showroom.material-editor','Material and paint editor','creative.showroom','visual.showroom.studio','bind exact object parts to material/paint sources and variants while preserving missing/unknown bindings',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'slots':(.03,.51,.45,.34),'materials':(.51,.51,.46,.25),'actions':(.51,.79,.46,.06)},
        {'header':(.02,.03,.96,.075),'slots':(.02,.14,.25,.72),'preview':(.30,.14,.45,.72),'materials':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'slots':(.015,.13,.23,.74),'preview':(.265,.13,.49,.74),'materials':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','showroom','material','paint'],quality=q),
      'visual.showroom.variant-editor':screen('visual.showroom.variant-editor','Object variant editor','creative.showroom','visual.showroom.studio','edit exact model/configuration variants, properties and known/unknown availability without inferring differences from appearance',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'variants':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','showroom','variant','configuration'],quality=q),
      'visual.showroom.annotation-editor':screen('visual.showroom.annotation-editor','Object annotation and callout editor','creative.showroom','visual.showroom.studio','bind exact component anchors to labels, measurements/specifications and source-aware explanatory callouts',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'annotations':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'annotations':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'annotations':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','showroom','annotation','callout'],quality=q),
      'visual.showroom.comparison':screen('visual.showroom.comparison','Object and variant comparison','creative.showroom','visual.showroom.studio','compare exact object/variant references, known comparable fields and source-bound measurements side by side',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.44),'right':(.52,.14,.45,.44),'fields':(.03,.61,.58,.26),'actions':(.64,.61,.33,.26)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.38,.63),'right':(.42,.14,.38,.63),'fields':(.82,.14,.16,.45),'actions':(.82,.62,.16,.15)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.39,.65),'right':(.42,.13,.39,.65),'fields':(.825,.13,.16,.47),'actions':(.825,.63,.16,.15)}),tags=['visual','showroom','comparison','variant'],quality=q),
      'visual.showroom.detail-view':screen('visual.showroom.detail-view','Object detail and inspection view','creative.showroom','visual.showroom.studio','inspect exact component/object references at close range with annotation, source and measurement state visible',v(
        {'header':(.03,.03,.94,.08),'detail':(.03,.14,.94,.44),'annotations':(.03,.61,.45,.26),'source':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'annotations':(.02,.14,.20,.72),'detail':(.245,.14,.50,.72),'source':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'annotations':(.015,.13,.18,.74),'detail':(.215,.13,.54,.74),'source':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','showroom','detail','inspection'],math_hooks={'detail_coverage_ratio':[0.50,0.82],'annotation_clearance_ratio':[0.01,0.07]},quality=q),
      'visual.showroom.turntable':screen('visual.showroom.turntable','Turntable and showcase-motion editor','creative.showroom','visual.showroom.studio','edit derived rotation/showcase motion around an exact object target with angle, speed and playback state explicit',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'timeline':(.03,.57,.58,.30),'motion':(.64,.57,.33,.22),'actions':(.64,.82,.33,.05)},
        {'header':(.02,.03,.96,.075),'timeline':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'motion':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'timeline':(.015,.13,.22,.74),'preview':(.265,.13,.49,.74),'motion':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','showroom','turntable','motion'],quality=q),
      'visual.showroom.review-export':screen('visual.showroom.review-export','Showroom review and export','creative.showroom','visual.showroom.studio','review missing assets/materials, invalid cameras, unknown variants/specifications and output requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','showroom','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.showroom.core','version':1,'name':'Editable 3D showroom and gallery core','kind':'product','domain':'creative.showroom','tags':['visual','showroom','3d','gallery','product'],'origin':origin(),'style':'visual.showroom.studio','intent':'source-first object/vehicle/product presentation with exact asset, camera, material, variant, annotation, comparison and showcase-motion state','screens':ids,'flow':[
      ['visual.showroom.project-hub','visual.showroom.object-stage','stage-object'],['visual.showroom.object-stage','visual.showroom.orbit-camera','edit-camera'],['visual.showroom.object-stage','visual.showroom.material-editor','edit-materials'],['visual.showroom.object-stage','visual.showroom.variant-editor','edit-variants'],['visual.showroom.object-stage','visual.showroom.annotation-editor','add-callouts'],['visual.showroom.object-stage','visual.showroom.comparison','compare'],['visual.showroom.object-stage','visual.showroom.detail-view','inspect-detail'],['visual.showroom.object-stage','visual.showroom.turntable','edit-showcase-motion'],['visual.showroom.object-stage','visual.showroom.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.showroom.core':product},'product')

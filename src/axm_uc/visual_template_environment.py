"""Source-bound environment and level-reference foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"environment {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_environment_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.environment.reference':{
        'intent':'source-bound environment and level reference boards with exact location identity, scale, modular kit, props, materials, lighting and traversal annotations',
        'tokens':{'canvas':'#0b1012','surface':'#172024','surface_raised':'#222d31','text':'#eef2ed','muted':'#a5b0a8','accent':'#88c6ad','warning':'#dfb96d','danger':'#da7775','line':'#43534f'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':730,'body_weight':500,'metric_scale':1.48,'tracking':0.011},
        'depth':{'layers':7,'shadow':'subtle','glass':'none'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':320,'principle':'environment source and scale truth before atmosphere'},
    }},'style')

    _merge(primitives,{
        'environment-source':{'role':'exact location/environment identity with source/version/digest and scope','states':['known','active','archived','unknown'],'identity_source_version_scope_required':True},
        'environment-zone':{'role':'named level/location zone with exact geometry/source/status','states':['known','selected','blocked','unknown'],'geometry_source_status_required':True},
        'environment-measurement':{'role':'scale/dimension measurement with value, unit, source and precision/assumption state','states':['exact','measured','estimated','unknown'],'value_unit_source_precision_required':True},
        'modular-environment-piece':{'role':'kit/module piece with exact source identity, socket/connection semantics and transform','states':['available','placed','disabled','unknown'],'source_socket_transform_required':True},
        'environment-prop':{'role':'prop reference with exact identity, source, placement context and gameplay/visual status','states':['required','optional','decorative','unknown'],'identity_source_context_status_required':True},
        'environment-material':{'role':'surface/material binding with exact target, material source and usage context','states':['active','alternate','damaged','unknown'],'target_material_source_context_required':True},
        'environment-lighting-state':{'role':'lighting/weather/time reference state with source, time, weather and exposure/status','states':['day','night','weather','interior','unknown'],'source_time_weather_exposure_required':True},
        'traversal-reference':{'role':'traversal/gameplay annotation bound to exact target with type, source and status','states':['walkable','blocked','climbable','hazard','unknown'],'target_type_source_status_required':True},
        'environment-variant':{'role':'environment/biome/state variant with exact base, deltas, context and source','states':['active','alternate','event','archived'],'base_delta_context_source_required':True},
        'environment-export-target':{'role':'reference-board export target with exact source coverage, measurements, materials, props, lighting and annotation requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['location identity, geometry, scale, kit pieces, props, materials, lighting and traversal annotations remain separately editable','a beautiful reference board never silently becomes authoritative level geometry','scale is never inferred solely from perspective appearance when no measurement/source exists','prop proximity does not imply gameplay linkage and traversal annotations require exact source-bound targets','lighting, weather and biome variants remain source/state references rather than hidden rewrites of the base environment']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.environment.project-hub':screen('visual.environment.project-hub','Environment reference project hub','creative.environment','visual.environment.reference','browse locations, variants, source coverage, scale evidence, kit/prop coverage and exports',v(
        {'header':(.03,.03,.94,.08),'locations':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'variants':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'locations':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'variants':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'locations':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'variants':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','environment','level','project'],quality=q),
      'visual.environment.identity-board':screen('visual.environment.identity-board','Environment identity board','creative.environment','visual.environment.reference','stage exact location identity, source references, scope, mood references and variant context without collapsing them into one flattened image',v(
        {'header':(.03,.03,.94,.08),'hero':(.03,.14,.94,.42),'sources':(.03,.59,.45,.28),'identity':(.51,.59,.46,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.22,.72),'hero':(.27,.14,.48,.72),'identity':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.20,.74),'hero':(.24,.13,.51,.74),'identity':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','environment','identity','reference'],math_hooks={'hero_coverage_ratio':[0.44,0.72],'reference_gap_ratio':[0.01,0.06]},quality=q),
      'visual.environment.zones-layout':screen('visual.environment.zones-layout','Environment zone and layout editor','creative.environment','visual.environment.reference','edit exact zones, geometry/source status and adjacency references without treating diagram layout as final level geometry',v(
        {'header':(.03,.03,.94,.08),'layout':(.03,.14,.94,.38),'zones':(.03,.55,.55,.32),'details':(.61,.55,.36,.24),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'zones':(.02,.14,.25,.72),'layout':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'zones':(.015,.13,.23,.74),'layout':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','environment','zone','layout'],quality=q),
      'visual.environment.scale-measurements':screen('visual.environment.scale-measurements','Scale and measurement editor','creative.environment','visual.environment.reference','edit exact dimensions, scale anchors, units, source and precision/assumption state rather than estimating scale from perspective alone',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'measurements':(.03,.53,.55,.34),'source':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'measurements':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'source':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'measurements':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'source':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','environment','scale','measurement'],quality=q),
      'visual.environment.modular-kit':screen('visual.environment.modular-kit','Modular kit and prop editor','creative.environment','visual.environment.reference','catalog exact modular pieces, connection semantics, props, placement contexts and source identity for environment production',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'kit':(.03,.57,.45,.30),'details':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'kit':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'kit':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','environment','modular','prop'],quality=q),
      'visual.environment.materials':screen('visual.environment.materials','Environment material and surface editor','creative.environment','visual.environment.reference','bind exact surfaces/targets to material references and context/state while retaining source provenance',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'surfaces':(.03,.53,.45,.34),'materials':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'surfaces':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'materials':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'surfaces':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'materials':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','environment','material','surface'],quality=q),
      'visual.environment.lighting-weather':screen('visual.environment.lighting-weather','Lighting weather and time reference editor','creative.environment','visual.environment.reference','author exact lighting/weather/time states with source and exposure/context rather than baking atmosphere into location identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'states':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'states':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'states':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','environment','lighting','weather'],quality=q),
      'visual.environment.traversal-annotations':screen('visual.environment.traversal-annotations','Traversal and gameplay annotation editor','creative.environment','visual.environment.reference','bind traversal, hazard, route and gameplay annotations to exact targets with explicit source/status rather than visual implication',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'annotations':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'annotations':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'annotations':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','environment','traversal','gameplay'],quality=q),
      'visual.environment.variants':screen('visual.environment.variants','Environment and biome variant editor','creative.environment','visual.environment.reference','edit exact base/delta/source context for biome, damage, season, event or state variants without rewriting the base location',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'variants':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','environment','variant','biome'],quality=q),
      'visual.environment.review-export':screen('visual.environment.review-export','Environment reference review and export','creative.environment','visual.environment.reference','review missing scale/source evidence, unresolved geometry, material/prop coverage, lighting state and traversal annotations before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','environment','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.environment.core','version':1,'name':'Source-bound environment and level reference core','kind':'product','domain':'creative.environment','tags':['visual','environment','level','reference','product'],'origin':origin(),'style':'visual.environment.reference','intent':'source-first environment/level reference authoring with exact location identity, zones, scale, kit/props, materials, lighting/weather, traversal and variants','screens':ids,'flow':[
      ['visual.environment.project-hub','visual.environment.identity-board','open-location'],['visual.environment.identity-board','visual.environment.zones-layout','edit-zones'],['visual.environment.identity-board','visual.environment.scale-measurements','edit-scale'],['visual.environment.identity-board','visual.environment.modular-kit','edit-kit'],['visual.environment.identity-board','visual.environment.materials','edit-materials'],['visual.environment.identity-board','visual.environment.lighting-weather','edit-lighting'],['visual.environment.identity-board','visual.environment.traversal-annotations','edit-traversal'],['visual.environment.project-hub','visual.environment.variants','edit-variants'],['visual.environment.project-hub','visual.environment.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.environment.core':product},'product')

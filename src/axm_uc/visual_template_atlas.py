"""Editable world-map, lore-atlas and state-overlay foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"atlas {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_atlas_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.atlas.cartographic':{
        'intent':'layered map and lore-atlas presentation with explicit spatial truth, provenance, chronology and narrative references',
        'tokens':{'canvas':'#0b1011','surface':'#182022','surface_raised':'#242e30','text':'#eef1e9','muted':'#a5afa8','accent':'#8ec7a6','warning':'#e3bd72','danger':'#dc7c77','line':'#465452'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':720,'body_weight':500,'metric_scale':1.45,'tracking':0.012},
        'depth':{'layers':7,'shadow':'subtle','glass':'none'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':320,'principle':'spatial/state truth before flourish'},
    }},'style')

    _merge(primitives,{
        'map-region':{'role':'named spatial region with exact geometry/source and state','states':['known','selected','disputed','unknown'],'geometry_source_required':True},
        'route-path':{'role':'explicit route/path with exact endpoints and observed/declared status','states':['known','planned','blocked','unknown'],'endpoints_and_status_required':True},
        'poi-marker':{'role':'point of interest with exact identity and location source/status','states':['known','selected','hidden','unknown'],'location_source_required':True},
        'map-layer':{'role':'named independently toggleable map/state layer with provenance','states':['visible','hidden','selected','unavailable'],'layer_source_required':True},
        'time-slice':{'role':'one exact chronology/state snapshot with period and provenance','states':['current','historical','projected','unknown'],'period_and_status_required':True},
        'lore-reference':{'role':'narrative/lore reference bound to exact entity/place/event','states':['observed','canon-source','claimed','disputed'],'target_and_source_required':True},
        'boundary-line':{'role':'explicit border/boundary with type, source and uncertainty state','states':['known','disputed','historical','unknown'],'boundary_type_and_source_required':True},
        'map-coordinate':{'role':'coordinate/location value with coordinate system/source/precision state','states':['exact','approximate','derived','unknown'],'system_source_precision_required':True},
        'state-overlay':{'role':'derived state visualization bound to exact source/time slice','states':['active','selected','stale','unknown'],'source_and_time_required':True},
        'atlas-export-target':{'role':'output target with extent/layers/labels/provenance inclusion state','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['map geometry, labels, routes and lore references remain separately editable','unknown coordinates or routes are never invented to make the map look complete','time/state overlays remain bound to explicit source and period','visual boundaries do not become factual borders without declared source/type','derived exports never replace richer editable atlas source']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.atlas.project-hub':screen('visual.atlas.project-hub','Atlas project hub','creative.atlas','visual.atlas.cartographic','browse maps, source coverage, layer sets, time slices and export targets before editing',v(
        {'header':(.03,.03,.94,.08),'maps':(.03,.14,.94,.30),'sources':(.03,.47,.45,.38),'targets':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'maps':(.02,.14,.22,.82),'sources':(.27,.14,.46,.82),'targets':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'maps':(.015,.13,.20,.84),'sources':(.24,.13,.50,.84),'targets':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','atlas','map','project'],quality=q),
      'visual.atlas.map-editor':screen('visual.atlas.map-editor','World-map editor','creative.atlas','visual.atlas.cartographic','edit base geometry, regions, layers, labels and source coverage without inventing missing spatial facts',v(
        {'toolbar':(.02,.02,.96,.07),'map':(.12,.11,.76,.56),'layers':(.02,.11,.08,.56),'properties':(.90,.11,.08,.56),'sources':(.02,.70,.46,.28),'checks':(.51,.70,.47,.28)},
        {'toolbar':(.015,.02,.97,.065),'layers':(.015,.105,.16,.75),'map':(.19,.105,.58,.75),'properties':(.79,.105,.195,.75),'sources':(.19,.88,.38,.10),'checks':(.59,.88,.395,.10)},
        {'toolbar':(.012,.02,.976,.06),'layers':(.012,.10,.14,.77),'map':(.17,.10,.62,.77),'properties':(.805,.10,.183,.77),'sources':(.17,.90,.40,.08),'checks':(.59,.90,.398,.08)}),tags=['visual','atlas','map','editor'],math_hooks={'label_clearance_ratio':[0.01,0.06],'region_gap_ratio':[0.0,0.03]},quality=q),
      'visual.atlas.region-editor':screen('visual.atlas.region-editor','Region and boundary editor','creative.atlas','visual.atlas.cartographic','edit exact region geometry, names, boundaries, source/status and historical/disputed variants',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'regions':(.03,.53,.30,.34),'boundary':(.36,.53,.29,.34),'source':(.68,.53,.29,.34),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'regions':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'boundary':(.77,.14,.21,.34),'source':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'regions':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'boundary':(.775,.13,.21,.35),'source':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','atlas','region','boundary'],quality=q),
      'visual.atlas.route-editor':screen('visual.atlas.route-editor','Route and path editor','creative.atlas','visual.atlas.cartographic','edit exact route endpoints, geometry, route type and known/planned/blocked/unknown status without inventing connectivity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'routes':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'routes':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'routes':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','atlas','route','path'],quality=q),
      'visual.atlas.poi-lore':screen('visual.atlas.poi-lore','POI and lore-reference editor','creative.atlas','visual.atlas.cartographic','bind exact places/events/entities to location source and lore/narrative references with status visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'poi':(.03,.47,.45,.39),'lore':(.51,.47,.46,.39),'actions':(.03,.89,.94,.08)},
        {'header':(.02,.03,.96,.075),'poi':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'lore':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'poi':(.015,.13,.22,.74),'preview':(.265,.13,.48,.74),'lore':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','atlas','poi','lore'],quality=q),
      'visual.atlas.layer-editor':screen('visual.atlas.layer-editor','Atlas layer editor','creative.atlas','visual.atlas.cartographic','compose independent terrain, political, infrastructure, narrative and state layers with source/provenance visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'layers':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'layers':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'layers':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','atlas','layer','state'],quality=q),
      'visual.atlas.timeline-state':screen('visual.atlas.timeline-state','Atlas timeline and state overlays','creative.atlas','visual.atlas.cartographic','edit exact historical/current/projected time slices and source-bound state overlays without presenting projection as observation',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'timeline':(.03,.48,.58,.39),'state':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'timeline':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'state':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'timeline':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'state':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','atlas','timeline','state'],quality=q),
      'visual.atlas.coordinate-source':screen('visual.atlas.coordinate-source','Coordinate and spatial-source editor','creative.atlas','visual.atlas.cartographic','edit coordinate system, source, precision, approximate/derived/unknown state and spatial source coverage',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.31),'coordinates':(.03,.48,.45,.39),'sources':(.51,.48,.46,.39),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'coordinates':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'sources':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'coordinates':(.015,.13,.22,.74),'preview':(.265,.13,.48,.74),'sources':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','atlas','coordinate','source'],quality=q),
      'visual.atlas.review-compare':screen('visual.atlas.review-compare','Atlas review and comparison','creative.atlas','visual.atlas.cartographic','review missing spatial evidence, disputed boundaries, unknown coordinates/routes, time-state distinctions and lore provenance before export',v(
        {'header':(.03,.03,.94,.08),'primary':(.03,.14,.45,.45),'alternate':(.52,.14,.45,.45),'checks':(.03,.62,.58,.26),'actions':(.64,.62,.33,.26)},
        {'header':(.02,.03,.96,.075),'primary':(.02,.14,.38,.63),'alternate':(.42,.14,.38,.63),'checks':(.82,.14,.16,.45),'actions':(.82,.62,.16,.15)},
        {'header':(.015,.03,.97,.07),'primary':(.015,.13,.39,.65),'alternate':(.42,.13,.39,.65),'checks':(.825,.13,.16,.47),'actions':(.825,.63,.16,.15)}),tags=['visual','atlas','review','truth'],quality=q),
      'visual.atlas.export':screen('visual.atlas.export','Atlas export matrix','creative.atlas','visual.atlas.cartographic','review exact extent, included layers, label/lore/source-note state and output requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'targets':(.03,.47,.58,.39),'details':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'targets':(.43,.14,.34,.72),'details':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'targets':(.40,.13,.37,.74),'details':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','atlas','export','target'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.atlas.core','version':1,'name':'Editable world-map and lore-atlas core','kind':'product','domain':'creative.atlas','tags':['visual','atlas','map','lore','product'],'origin':origin(),'style':'visual.atlas.cartographic','intent':'source-first world-map and lore-atlas editing with exact regions, routes, POIs, layers, coordinates, chronology/state and narrative references','screens':ids,'flow':[
      ['visual.atlas.project-hub','visual.atlas.map-editor','edit-map'],['visual.atlas.map-editor','visual.atlas.region-editor','edit-regions'],['visual.atlas.map-editor','visual.atlas.route-editor','edit-routes'],['visual.atlas.map-editor','visual.atlas.poi-lore','edit-poi-lore'],['visual.atlas.map-editor','visual.atlas.layer-editor','edit-layers'],['visual.atlas.map-editor','visual.atlas.timeline-state','edit-time-state'],['visual.atlas.map-editor','visual.atlas.coordinate-source','edit-spatial-source'],['visual.atlas.map-editor','visual.atlas.review-compare','review'],['visual.atlas.review-compare','visual.atlas.export','export']], 'quality':q}
    _merge(products,{'visual.atlas.core':product},'product')

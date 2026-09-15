"""Editable vehicle, game-equipment and attachment configuration foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"configuration {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_configuration_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.configuration.technical':{
        'intent':'production-grade vehicle and game-equipment configuration with exact base asset, sockets, attachments, compatibility, stats and source identity preserved',
        'tokens':{'canvas':'#0b0e13','surface':'#161c24','surface_raised':'#222b35','text':'#f2f5f5','muted':'#a8b1b8','accent':'#85d7d0','warning':'#e6bb72','danger':'#e07179','line':'#43505a'},
        'shape':{'panel_radius_ratio':0.013,'cut_ratio':0.004,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.55,'tracking':0.012},
        'depth':{'layers':8,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':320,'principle':'configuration/state truth before mechanical flourish'},
    }},'style')

    _merge(primitives,{
        'config-base-asset':{'role':'exact vehicle/equipment base identity with source/version and configuration schema','states':['loaded','selected','missing','unknown'],'identity_source_version_schema_required':True},
        'config-socket':{'role':'exact attachment socket with parent/anchor/type/constraints and source state','states':['empty','occupied','selected','invalid'],'parent_anchor_type_constraints_required':True},
        'config-attachment':{'role':'exact attachment/item identity with source/version, compatible socket types and state','states':['available','equipped','selected','incompatible'],'identity_source_socket_types_required':True},
        'compatibility-rule':{'role':'explicit compatibility/incompatibility rule with involved ids, condition and source','states':['satisfied','blocked','conditional','unknown'],'ids_condition_source_required':True},
        'configuration-state':{'role':'exact named configuration with base plus ordered socket-to-attachment bindings and digest','states':['valid','selected','invalid','incomplete'],'base_bindings_digest_required':True},
        'configuration-stat':{'role':'exact gameplay/product stat with value, unit/context, source and derivation status','states':['observed','declared','derived','unknown'],'value_unit_context_source_required':True},
        'exploded-part':{'role':'exact part/attachment reference with derived exploded-view transform and parent identity','states':['assembled','exploded','selected','unresolved'],'reference_parent_transform_required':True},
        'configuration-material':{'role':'exact part/material/paint binding with source and variant state','states':['bound','selected','missing','unknown'],'part_material_source_required':True},
        'configuration-comparison':{'role':'exact configuration reference plus comparable stat/feature dimension set','states':['loaded','selected','missing','incomparable'],'reference_dimensions_required':True},
        'configuration-export-target':{'role':'output target with base, binding, stat, material, evidence and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['base asset, sockets, attachments, compatibility rules, configuration bindings, stats and materials remain separately editable','visual mounting never substitutes for exact socket or compatibility state','stat changes retain exact value, context, source and derivation status rather than being inferred from appearance','exploded/detail views remain derived presentation of exact referenced parts and attachments','preview/export never replaces richer configuration source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.configuration.project-hub':screen('visual.configuration.project-hub','Configuration project hub','game.configuration','visual.configuration.technical','browse base assets, saved configurations, attachment libraries, compatibility coverage and output targets',v(
        {'header':(.03,.03,.94,.08),'assets':(.03,.14,.94,.28),'configs':(.03,.45,.45,.40),'coverage':(.51,.45,.46,.27),'actions':(.51,.75,.46,.10)},
        {'header':(.02,.03,.96,.075),'assets':(.02,.14,.22,.82),'configs':(.27,.14,.46,.82),'coverage':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'assets':(.015,.13,.20,.84),'configs':(.24,.13,.50,.84),'coverage':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','configuration','vehicle','equipment'],quality=q),
      'visual.configuration.base-editor':screen('visual.configuration.base-editor','Base asset and configuration identity editor','game.configuration','visual.configuration.technical','edit exact base asset source/version, configuration schema and current named configuration identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'identity':(.03,.51,.45,.34),'source':(.51,.51,.46,.25),'actions':(.51,.79,.46,.06)},
        {'header':(.02,.03,.96,.075),'identity':(.02,.14,.25,.72),'preview':(.30,.14,.45,.72),'source':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'identity':(.015,.13,.23,.74),'preview':(.265,.13,.49,.74),'source':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configuration','base','identity'],quality=q),
      'visual.configuration.socket-editor':screen('visual.configuration.socket-editor','Socket and mount graph editor','game.configuration','visual.configuration.technical','edit exact parent/anchor/socket type/constraints and occupied binding state without inferring mount compatibility',v(
        {'header':(.03,.03,.94,.08),'graph':(.03,.14,.94,.40),'sockets':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'sockets':(.02,.14,.25,.72),'graph':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sockets':(.015,.13,.23,.74),'graph':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configuration','socket','mount'],math_hooks={'socket_marker_ratio':[0.008,0.035],'graph_spacing_ratio':[0.02,0.10]},quality=q),
      'visual.configuration.attachment-editor':screen('visual.configuration.attachment-editor','Attachment and compatibility editor','game.configuration','visual.configuration.technical','inspect exact attachment identity/source/socket types and explicit compatibility rules before binding',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'library':(.03,.51,.45,.34),'rules':(.51,.51,.46,.25),'actions':(.51,.79,.46,.06)},
        {'header':(.02,.03,.96,.075),'library':(.02,.14,.25,.72),'preview':(.30,.14,.45,.72),'rules':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'library':(.015,.13,.23,.74),'preview':(.265,.13,.49,.74),'rules':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configuration','attachment','compatibility'],quality=q),
      'visual.configuration.builder':screen('visual.configuration.builder','Configuration builder','game.configuration','visual.configuration.technical','compose exact socket-to-attachment bindings with invalid/incomplete states and configuration digest visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'bindings':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'bindings':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'bindings':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','configuration','builder','binding'],quality=q),
      'visual.configuration.stats-evidence':screen('visual.configuration.stats-evidence','Stats and evidence editor','game.configuration','visual.configuration.technical','inspect exact configuration stats, units/context, source and derivation status alongside binding changes',v(
        {'header':(.03,.03,.94,.08),'stats':(.03,.14,.94,.27),'changes':(.03,.44,.45,.43),'evidence':(.51,.44,.46,.31),'actions':(.51,.78,.46,.09)},
        {'header':(.02,.03,.96,.075),'stats':(.02,.14,.25,.72),'changes':(.30,.14,.45,.72),'evidence':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'stats':(.015,.13,.23,.74),'changes':(.265,.13,.49,.74),'evidence':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configuration','stats','evidence'],quality=q),
      'visual.configuration.exploded-detail':screen('visual.configuration.exploded-detail','Exploded and detail presentation editor','game.configuration','visual.configuration.technical','present exact referenced parts/attachments in derived exploded/detail transforms with parent identity and source state visible',v(
        {'header':(.03,.03,.94,.08),'view':(.03,.14,.94,.44),'parts':(.03,.61,.45,.26),'details':(.51,.61,.46,.20),'actions':(.51,.84,.46,.03)},
        {'header':(.02,.03,.96,.075),'parts':(.02,.14,.20,.72),'view':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'parts':(.015,.13,.18,.74),'view':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','configuration','exploded','detail'],math_hooks={'explosion_distance_ratio':[0.03,0.30],'detail_coverage_ratio':[0.45,0.82]},quality=q),
      'visual.configuration.material-finish':screen('visual.configuration.material-finish','Material paint and finish editor','game.configuration','visual.configuration.technical','bind exact base/attachment parts to material, paint and finish sources independently from configuration identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'parts':(.03,.51,.45,.34),'materials':(.51,.51,.46,.25),'actions':(.51,.79,.46,.06)},
        {'header':(.02,.03,.96,.075),'parts':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'materials':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'parts':(.015,.13,.22,.74),'preview':(.265,.13,.49,.74),'materials':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configuration','material','finish'],quality=q),
      'visual.configuration.comparison':screen('visual.configuration.comparison','Configuration comparison','game.configuration','visual.configuration.technical','compare exact configuration references across shared stat/feature dimensions with incompatible/missing state visible',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.44),'right':(.52,.14,.45,.44),'dimensions':(.03,.61,.58,.26),'sources':(.64,.61,.33,.26)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.38,.63),'right':(.42,.14,.38,.63),'dimensions':(.82,.14,.16,.45),'sources':(.82,.62,.16,.15)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.39,.65),'right':(.42,.13,.39,.65),'dimensions':(.825,.13,.16,.47),'sources':(.825,.63,.16,.15)}),tags=['visual','configuration','comparison','stats'],quality=q),
      'visual.configuration.review-export':screen('visual.configuration.review-export','Configuration review and export','game.configuration','visual.configuration.technical','review invalid sockets, incompatible attachments, unknown stats/materials and provenance/output requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','configuration','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.configuration.core','version':1,'name':'Editable vehicle and game-equipment configuration core','kind':'product','domain':'game.configuration','tags':['visual','configuration','vehicle','equipment','product'],'origin':origin(),'style':'visual.configuration.technical','intent':'source-first vehicle and game-equipment configuration with exact base/socket/attachment bindings, compatibility, stats, materials and comparison state','screens':ids,'flow':[
      ['visual.configuration.project-hub','visual.configuration.base-editor','bind-base'],['visual.configuration.base-editor','visual.configuration.socket-editor','edit-sockets'],['visual.configuration.socket-editor','visual.configuration.attachment-editor','inspect-attachments'],['visual.configuration.attachment-editor','visual.configuration.builder','build-configuration'],['visual.configuration.builder','visual.configuration.stats-evidence','inspect-stats'],['visual.configuration.builder','visual.configuration.exploded-detail','inspect-parts'],['visual.configuration.builder','visual.configuration.material-finish','edit-materials'],['visual.configuration.builder','visual.configuration.comparison','compare-configurations'],['visual.configuration.builder','visual.configuration.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.configuration.core':product},'product')

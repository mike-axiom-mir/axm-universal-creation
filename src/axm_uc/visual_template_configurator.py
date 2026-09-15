"""Editable equipment, vehicle and weapon configuration foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"configurator {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_configurator_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.configurator.precision':{
        'intent':'high-readability object configuration with exact source identity, sockets, components, compatibility, stats and variants separated from presentation polish',
        'tokens':{'canvas':'#0c1014','surface':'#161d24','surface_raised':'#202a34','text':'#eef4f6','muted':'#9faeb8','accent':'#7fd0c2','warning':'#e6bb68','danger':'#e17474','line':'#3c4b55'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.004,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.52,'tracking':0.012},
        'depth':{'layers':7,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':310,'principle':'configuration truth before flourish'},
    }},'style')

    _merge(primitives,{
        'configurable-source':{'role':'exact configurable object identity with source/version/digest and base state','states':['known','selected','missing','unknown'],'identity_source_version_required':True},
        'attachment-socket':{'role':'exact named socket with socket type, accepted category and availability/state','states':['empty','occupied','blocked','unknown'],'socket_identity_type_status_required':True},
        'component-part':{'role':'exact component/attachment with source identity, parent socket and transform state','states':['available','equipped','disabled','unknown'],'source_parent_transform_required':True},
        'compatibility-rule':{'role':'explicit compatibility rule between exact subject and target with result/reason/status','states':['compatible','incompatible','conditional','unknown'],'subject_target_rule_status_required':True},
        'config-stat-field':{'role':'configuration statistic with value, unit, source and context/version state','states':['base','modified','warning','unknown'],'value_unit_source_context_required':True},
        'configuration-state':{'role':'exact assembled configuration with base identity, attachment set, variants and digest','states':['draft','valid','invalid','saved'],'base_attachment_variant_digest_required':True},
        'exploded-view-state':{'role':'derived exploded/detail presentation of exact source parts with non-authoritative offsets','states':['assembled','exploded','selected','hidden'],'source_part_offset_non_authoritative':True},
        'config-material-variant':{'role':'material/skin/finish variant bound to exact target with source and availability state','states':['active','available','locked','unknown'],'target_variant_source_availability_required':True},
        'config-annotation':{'role':'callout bound to exact socket/component/stat target with source/status','states':['visible','selected','hidden','unresolved'],'target_content_source_required':True},
        'configurator-export-target':{'role':'output target with exact configuration, views, stats, labels and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['base object identity, sockets, components, stats, variants and presentation remain separately editable','presentation never silently rewrites the source object or equipped configuration','attachment compatibility stays explicit rather than inferred from visual fit','stat values retain unit, source and configuration context/version state','exploded, detail, comparison and export views remain derived from richer configuration source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.configurator.project-hub':screen('visual.configurator.project-hub','Configurator project hub','creative.configurator','visual.configurator.precision','browse configurable objects, saved configurations, component coverage, compatibility warnings and outputs',v(
        {'header':(.03,.03,.94,.08),'objects':(.03,.14,.94,.30),'configs':(.03,.47,.45,.38),'coverage':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'objects':(.02,.14,.22,.82),'configs':(.27,.14,.46,.82),'coverage':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'objects':(.015,.13,.20,.84),'configs':(.24,.13,.50,.84),'coverage':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','configurator','equipment','project'],quality=q),
      'visual.configurator.object-stage':screen('visual.configurator.object-stage','Configurable object stage','creative.configurator','visual.configurator.precision','stage exact vehicle, weapon, device or item identity while keeping current configuration and source state inspectable',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.48),'identity':(.03,.65,.45,.22),'config':(.51,.65,.46,.22),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'identity':(.02,.14,.18,.72),'stage':(.225,.14,.55,.72),'config':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'identity':(.015,.13,.16,.74),'stage':(.195,.13,.58,.74),'config':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','configurator','object','stage'],math_hooks={'hero_coverage_ratio':[0.48,0.74],'control_clearance_ratio':[0.015,0.06]},quality=q),
      'visual.configurator.socket-editor':screen('visual.configurator.socket-editor','Attachment socket editor','creative.configurator','visual.configurator.precision','edit exact sockets, socket types, accepted categories, occupancy and availability without inferring connection from geometry',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.36),'sockets':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'sockets':(.02,.14,.25,.72),'stage':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sockets':(.015,.13,.23,.74),'stage':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configurator','socket','attachment'],quality=q),
      'visual.configurator.exploded-view':screen('visual.configurator.exploded-view','Exploded component editor','creative.configurator','visual.configurator.precision','inspect exact parts and parent/socket identity using derived exploded offsets that never become source transforms',v(
        {'header':(.03,.03,.94,.08),'exploded':(.03,.14,.94,.44),'parts':(.03,.61,.45,.26),'details':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'parts':(.02,.14,.20,.72),'exploded':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'parts':(.015,.13,.18,.74),'exploded':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','configurator','exploded','component'],math_hooks={'explode_spread_ratio':[0.04,0.32],'part_label_clearance_ratio':[0.01,0.06]},quality=q),
      'visual.configurator.stat-editor':screen('visual.configurator.stat-editor','Configuration stat editor','creative.configurator','visual.configurator.precision','review exact base and modified stat values with units, source and configuration context rather than decorative bars alone',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.30),'stats':(.03,.47,.58,.40),'source':(.64,.47,.33,.27),'actions':(.64,.77,.33,.10)},
        {'header':(.02,.03,.96,.075),'stats':(.02,.14,.28,.72),'stage':(.33,.14,.44,.72),'source':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'stats':(.015,.13,.26,.74),'stage':(.305,.13,.47,.74),'source':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','configurator','stats','compare'],quality=q),
      'visual.configurator.variant-material':screen('visual.configurator.variant-material','Variant and material editor','creative.configurator','visual.configurator.precision','bind exact target parts to material, skin, paint or finish variants with source and availability visible',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.36),'targets':(.03,.53,.45,.34),'variants':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'targets':(.02,.14,.22,.72),'stage':(.27,.14,.48,.72),'variants':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'targets':(.015,.13,.20,.74),'stage':(.24,.13,.51,.74),'variants':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','configurator','variant','material'],quality=q),
      'visual.configurator.compatibility':screen('visual.configurator.compatibility','Compatibility rule editor','creative.configurator','visual.configurator.precision','inspect exact component-to-socket compatibility results, rules, reasons and conditional requirements',v(
        {'header':(.03,.03,.94,.08),'matrix':(.03,.14,.94,.36),'rules':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'rules':(.02,.14,.28,.72),'matrix':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'rules':(.015,.13,.26,.74),'matrix':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','configurator','compatibility','rule'],quality=q),
      'visual.configurator.comparison':screen('visual.configurator.comparison','Configuration comparison','creative.configurator','visual.configurator.precision','compare exact saved or candidate configurations while preserving source identities, attachment sets, variants and stat contexts',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.42),'right':(.52,.14,.45,.42),'metrics':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.36,.63),'right':(.40,.14,.36,.63),'metrics':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.37,.65),'right':(.405,.13,.37,.65),'metrics':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','configurator','comparison','configuration'],quality=q),
      'visual.configurator.loadout-presets':screen('visual.configurator.loadout-presets','Preset and loadout editor','creative.configurator','visual.configurator.precision','save and inspect exact configuration identities, component sets, variants, compatibility status and digests',v(
        {'header':(.03,.03,.94,.08),'presets':(.03,.14,.45,.72),'stage':(.51,.14,.46,.40),'details':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'presets':(.02,.14,.25,.72),'stage':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'presets':(.015,.13,.23,.74),'stage':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','configurator','preset','loadout'],quality=q),
      'visual.configurator.review-export':screen('visual.configurator.review-export','Configurator review and export','creative.configurator','visual.configurator.precision','review unresolved sockets, compatibility failures, unknown stats, unavailable variants and exact configuration/export requirements before derived output',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','configurator','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.configurator.core','version':1,'name':'Editable equipment and vehicle configurator core','kind':'product','domain':'creative.configurator','tags':['visual','configurator','equipment','vehicle','weapon','product'],'origin':origin(),'style':'visual.configurator.precision','intent':'source-first equipment, vehicle, weapon and device configuration with exact object identity, sockets, components, compatibility, stats, variants, presets and derived presentation views','screens':ids,'flow':[
      ['visual.configurator.project-hub','visual.configurator.object-stage','open-object'],['visual.configurator.object-stage','visual.configurator.socket-editor','edit-sockets'],['visual.configurator.object-stage','visual.configurator.exploded-view','inspect-components'],['visual.configurator.object-stage','visual.configurator.stat-editor','inspect-stats'],['visual.configurator.object-stage','visual.configurator.variant-material','edit-variants'],['visual.configurator.socket-editor','visual.configurator.compatibility','check-compatibility'],['visual.configurator.project-hub','visual.configurator.comparison','compare-configurations'],['visual.configurator.project-hub','visual.configurator.loadout-presets','manage-presets'],['visual.configurator.project-hub','visual.configurator.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.configurator.core':product},'product')

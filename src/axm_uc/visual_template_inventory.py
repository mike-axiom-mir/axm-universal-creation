"""Source-bound inventory, item and equipment reference foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"inventory {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_inventory_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.inventory.system':{
        'intent':'source-bound inventory/item authoring with exact identity, ownership, quantities, stats, slots, compatibility, provenance and presentation variants',
        'tokens':{'canvas':'#0b0f13','surface':'#171e25','surface_raised':'#232c35','text':'#f0f3f5','muted':'#a2abb2','accent':'#89c8b6','warning':'#e2b968','danger':'#df7679','line':'#414f59'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.48,'tracking':0.010},
        'depth':{'layers':7,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':300,'principle':'item/gameplay source state before iconography or rarity styling'},
    }},'style')

    _merge(primitives,{
        'item-source':{'role':'exact item identity with source/version/digest, owner/context and provenance','states':['known','active','archived','unknown'],'identity_source_version_owner_required':True},
        'inventory-instance':{'role':'owned item instance with exact item identity, instance id, owner/container and lifecycle status','states':['owned','equipped','stored','consumed','unknown'],'item_instance_owner_status_required':True},
        'item-stack-state':{'role':'quantity/stack state with exact item/instance, quantity, capacity, unit/source and freshness','states':['available','full','depleted','unknown'],'item_quantity_capacity_source_required':True},
        'item-durability-state':{'role':'durability/condition state with exact value/range, unit/source and repair/broken status','states':['healthy','worn','broken','unknown'],'value_range_unit_source_required':True},
        'equipment-slot':{'role':'equipment/container slot with exact identity, accepted categories, occupancy and source/status','states':['empty','occupied','locked','unknown'],'slot_category_occupancy_source_required':True},
        'item-compatibility-rule':{'role':'exact item/slot or item/item compatibility rule with subjects, rule, result and source/status','states':['compatible','incompatible','conditional','unknown'],'subjects_rule_result_source_required':True},
        'item-stat-field':{'role':'item stat/attribute with exact value, unit, source, context/version and confidence/status','states':['known','derived','conditional','unknown'],'value_unit_source_context_required':True},
        'item-presentation-variant':{'role':'rarity/theme/icon/card presentation variant with exact base item, deltas, context and source','states':['active','alternate','event','archived'],'base_delta_context_source_required':True},
        'item-comparison-state':{'role':'comparison between exact item identities/configurations with field set, source and context','states':['ready','partial','blocked','unknown'],'item_refs_fields_source_required':True},
        'inventory-export-target':{'role':'inventory/item export target with exact identity, stats, ownership, slots, compatibility and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['item identity, ownership, quantities, durability, stats, slots, compatibility and presentation variants remain separately editable','an icon, rarity color, card frame or slot position never proves item ownership, rarity, equip state or compatibility','equipped-looking presentation never silently changes authoritative inventory or loadout state','stat values retain exact unit, source and configuration/context rather than being inferred from bars or comparison styling','presentation variants may change visual language while preserving exact item identity, provenance and gameplay semantics']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.inventory.project-hub':screen('visual.inventory.project-hub','Inventory and item project hub','creative.inventory','visual.inventory.system','browse item definitions, instances, containers, equipment sets, variants and export coverage',v(
        {'header':(.03,.03,.94,.08),'items':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'sets':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'items':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'sets':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'items':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'sets':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','inventory','item','project'],quality=q),
      'visual.inventory.item-inspector':screen('visual.inventory.item-inspector','Item identity and instance inspector','creative.inventory','visual.inventory.system','inspect exact item definition, instance identity, owner/container, provenance and lifecycle state separately from presentation',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'identity':(.03,.57,.45,.30),'instance':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'identity':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'instance':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'identity':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'instance':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','inventory','item','identity'],math_hooks={'item_coverage_ratio':[0.24,0.72],'detail_density_ratio':[0.10,0.80]},quality=q),
      'visual.inventory.grid-containers':screen('visual.inventory.grid-containers','Inventory grid and container editor','creative.inventory','visual.inventory.system','edit exact container/slot occupancy, instances and quantities without deriving ownership from screen position',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.44),'containers':(.03,.61,.45,.26),'details':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'containers':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'containers':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','inventory','grid','container'],quality=q),
      'visual.inventory.equipment-slots':screen('visual.inventory.equipment-slots','Equipment slot and loadout editor','creative.inventory','visual.inventory.system','edit exact slot identity/categories, occupancy and compatibility while keeping visual attachment separate from authoritative equip state',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.40),'slots':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'slots':(.02,.14,.25,.72),'stage':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'slots':(.015,.13,.23,.74),'stage':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','inventory','equipment','slot'],quality=q),
      'visual.inventory.stats-condition':screen('visual.inventory.stats-condition','Item stats durability and quantity editor','creative.inventory','visual.inventory.system','edit exact stat, stack and durability values with units/source/context rather than visual bars alone',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'stats':(.03,.51,.45,.36),'condition':(.51,.51,.46,.36),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'stats':(.02,.14,.26,.72),'preview':(.31,.14,.44,.72),'condition':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'stats':(.015,.13,.24,.74),'preview':(.285,.13,.47,.74),'condition':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','inventory','stats','durability'],quality=q),
      'visual.inventory.compatibility':screen('visual.inventory.compatibility','Item and slot compatibility editor','creative.inventory','visual.inventory.system','edit exact item/slot and item/item compatibility rules, conditions, result/source and unresolved states',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'rules':(.03,.49,.58,.38),'details':(.64,.49,.33,.28),'actions':(.64,.80,.33,.07)},
        {'header':(.02,.03,.96,.075),'rules':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'rules':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','inventory','compatibility','rule'],quality=q),
      'visual.inventory.comparison':screen('visual.inventory.comparison','Item comparison editor','creative.inventory','visual.inventory.system','compare exact item identities/configurations and explicit stat fields without presenting a visual winner as objective truth',v(
        {'header':(.03,.03,.94,.08),'left':(.03,.14,.45,.48),'right':(.52,.14,.45,.48),'fields':(.03,.65,.58,.22),'actions':(.64,.65,.33,.22)},
        {'header':(.02,.03,.96,.075),'left':(.02,.14,.36,.63),'right':(.40,.14,.36,.63),'fields':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'left':(.015,.13,.37,.65),'right':(.405,.13,.37,.65),'fields':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','inventory','compare','stats'],quality=q),
      'visual.inventory.presentation-variants':screen('visual.inventory.presentation-variants','Item icon rarity and presentation variants','creative.inventory','visual.inventory.system','edit exact visual presentation variants as source-bound deltas without changing item/gameplay identity or ownership',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'variants':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','inventory','rarity','variant'],quality=q),
      'visual.inventory.ownership-history':screen('visual.inventory.ownership-history','Item ownership and provenance inspector','creative.inventory','visual.inventory.system','inspect exact ownership/container transitions, source/provenance and lifecycle history without inferring ownership from current UI placement',v(
        {'header':(.03,.03,.94,.08),'timeline':(.03,.14,.94,.36),'history':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'history':(.02,.14,.28,.72),'timeline':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'history':(.015,.13,.26,.74),'timeline':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','inventory','ownership','provenance'],quality=q),
      'visual.inventory.review-export':screen('visual.inventory.review-export','Inventory and item review/export','creative.inventory','visual.inventory.system','review unresolved ownership, missing stat sources, invalid slots/compatibility, stale quantities and export requirements',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','inventory','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.inventory.core','version':1,'name':'Source-bound inventory and item-reference core','kind':'product','domain':'creative.inventory','tags':['visual','inventory','item','equipment','product'],'origin':origin(),'style':'visual.inventory.system','intent':'source-first inventory/item authoring with exact identity, instances/ownership, stacks/durability, slots/compatibility, stats, comparison and presentation variants','screens':ids,'flow':[
      ['visual.inventory.project-hub','visual.inventory.item-inspector','inspect-item'],['visual.inventory.project-hub','visual.inventory.grid-containers','edit-containers'],['visual.inventory.project-hub','visual.inventory.equipment-slots','edit-loadout'],['visual.inventory.item-inspector','visual.inventory.stats-condition','edit-stats'],['visual.inventory.equipment-slots','visual.inventory.compatibility','edit-compatibility'],['visual.inventory.item-inspector','visual.inventory.comparison','compare'],['visual.inventory.item-inspector','visual.inventory.presentation-variants','edit-presentation'],['visual.inventory.item-inspector','visual.inventory.ownership-history','inspect-history'],['visual.inventory.project-hub','visual.inventory.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.inventory.core':product},'product')

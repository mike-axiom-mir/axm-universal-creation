"""Source-bound quest, mission and objective-flow reference foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"mission {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_mission_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.mission.flow':{
        'intent':'source-bound quest and mission flow authoring with exact objectives, conditions, branches, world references, rewards, failure/retry and runtime state',
        'tokens':{'canvas':'#0b1014','surface':'#172027','surface_raised':'#222d36','text':'#eef3f5','muted':'#a2adb5','accent':'#82c8ba','warning':'#e2b96b','danger':'#dc7678','line':'#40505a'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.5,'tracking':0.011},
        'depth':{'layers':7,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':315,'principle':'objective and branch truth before presentation'},
    }},'style')

    _merge(primitives,{
        'mission-source':{'role':'exact mission/quest identity with source/version/digest and owning context','states':['known','active','archived','unknown'],'identity_source_version_context_required':True},
        'objective-state':{'role':'exact objective identity/type/status with completion source and ordering state','states':['locked','available','active','complete','failed','unknown'],'identity_type_status_source_required':True},
        'mission-condition':{'role':'explicit prerequisite/condition with subject, operator, value, source and evaluation state','states':['true','false','unresolved','unknown'],'subject_operator_value_source_required':True},
        'mission-edge':{'role':'exact flow/branch edge with from/to identity, transition type and condition references','states':['available','blocked','taken','unknown'],'from_to_type_conditions_required':True},
        'mission-world-reference':{'role':'exact map/zone/poi/entity reference with source/status and optional spatial binding','states':['known','active','unavailable','unknown'],'target_source_status_required':True},
        'mission-reward-reference':{'role':'exact reward/outcome reference with source, amount/state and delivery status','states':['planned','available','granted','failed','unknown'],'reward_source_amount_status_required':True},
        'mission-failure-recovery':{'role':'failure condition with exact retry/recovery/checkpoint destination and state consequences','states':['armed','failed','retryable','terminal','unknown'],'condition_recovery_consequence_required':True},
        'mission-runtime-flag':{'role':'exact mission runtime flag/value with source and freshness/version state','states':['set','unset','stale','unknown'],'identity_value_source_required':True},
        'mission-variant':{'role':'mission variant/difficulty/state profile with exact base, deltas, context and availability','states':['active','alternate','restricted','archived'],'base_delta_context_required':True},
        'mission-export-target':{'role':'mission package/export target with objectives, conditions, branches, references, rewards and recovery requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['mission identity, objectives, conditions, branches, world references, rewards and runtime state remain separately editable','visual flow never implies that a branch is reachable or an objective is complete','map proximity never creates a mission/world binding without an exact reference','reward icons never prove a reward exists or was granted','failure, retry, recovery and checkpoint consequences remain explicit source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.mission.project-hub':screen('visual.mission.project-hub','Mission project hub','creative.mission','visual.mission.flow','browse missions, source coverage, runtime state, variants and validation/export targets',v(
        {'header':(.03,.03,.94,.08),'missions':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'state':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'missions':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'state':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'missions':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'state':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','mission','quest','project'],quality=q),
      'visual.mission.objectives':screen('visual.mission.objectives','Objective editor','creative.mission','visual.mission.flow','edit exact objective identity/type/order/status and completion source without inferring completion from presentation',v(
        {'header':(.03,.03,.94,.08),'flow':(.03,.14,.94,.36),'objectives':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'objectives':(.02,.14,.28,.72),'flow':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'objectives':(.015,.13,.26,.74),'flow':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','mission','objective','state'],quality=q),
      'visual.mission.conditions':screen('visual.mission.conditions','Prerequisite and condition editor','creative.mission','visual.mission.flow','edit explicit prerequisite and branch conditions with subject/operator/value/source and unresolved state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'conditions':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'conditions':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'conditions':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','mission','condition','prerequisite'],quality=q),
      'visual.mission.branch-flow':screen('visual.mission.branch-flow','Mission branch and flow editor','creative.mission','visual.mission.flow','edit exact flow nodes and branch edges while keeping reachability dependent on explicit conditions/runtime state',v(
        {'header':(.03,.03,.94,.08),'graph':(.03,.14,.94,.44),'nodes':(.03,.61,.45,.26),'edges':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'nodes':(.02,.14,.20,.72),'graph':(.245,.14,.50,.72),'edges':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'nodes':(.015,.13,.18,.74),'graph':(.215,.13,.54,.74),'edges':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','mission','branch','flow'],math_hooks={'node_spacing_ratio':[0.02,0.12],'edge_clearance_ratio':[0.01,0.06]},quality=q),
      'visual.mission.world-bindings':screen('visual.mission.world-bindings','World and map binding editor','creative.mission','visual.mission.flow','bind missions/objectives to exact map zones, POIs, entities or world references with source/status explicit',v(
        {'header':(.03,.03,.94,.08),'world':(.03,.14,.94,.40),'bindings':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'bindings':(.02,.14,.22,.72),'world':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'bindings':(.015,.13,.20,.74),'world':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','mission','world','map'],quality=q),
      'visual.mission.rewards-outcomes':screen('visual.mission.rewards-outcomes','Rewards and outcomes editor','creative.mission','visual.mission.flow','edit exact reward/outcome references, amount/state, source and grant/delivery status without implying success from icons',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'rewards':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'rewards':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'rewards':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','mission','reward','outcome'],quality=q),
      'visual.mission.failure-retry':screen('visual.mission.failure-retry','Failure retry and recovery editor','creative.mission','visual.mission.flow','edit exact failure conditions, retry/recovery targets, checkpoints and state consequences',v(
        {'header':(.03,.03,.94,.08),'flow':(.03,.14,.94,.34),'failures':(.03,.51,.55,.34),'recovery':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'failures':(.02,.14,.28,.72),'flow':(.33,.14,.44,.72),'recovery':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'failures':(.015,.13,.26,.74),'flow':(.305,.13,.47,.74),'recovery':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','mission','failure','retry'],quality=q),
      'visual.mission.runtime-state':screen('visual.mission.runtime-state','Mission runtime state inspector','creative.mission','visual.mission.flow','inspect exact mission flags, objective state, branch state and freshness/version without manufacturing runtime truth',v(
        {'header':(.03,.03,.94,.08),'timeline':(.03,.14,.94,.30),'flags':(.03,.47,.45,.40),'state':(.51,.47,.46,.40),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'flags':(.02,.14,.24,.72),'timeline':(.29,.14,.46,.72),'state':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'flags':(.015,.13,.22,.74),'timeline':(.265,.13,.48,.74),'state':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','mission','runtime','flag'],quality=q),
      'visual.mission.variants':screen('visual.mission.variants','Mission variant editor','creative.mission','visual.mission.flow','edit difficulty/state/context variants as exact deltas from a named base mission without silently branching canon',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'variants':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','mission','variant','difficulty'],quality=q),
      'visual.mission.review-export':screen('visual.mission.review-export','Mission review and export','creative.mission','visual.mission.flow','review unresolved conditions, unreachable/unknown branches, missing world/reward refs and incomplete failure/recovery state before export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','mission','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.mission.core','version':1,'name':'Source-bound quest and mission flow core','kind':'product','domain':'creative.mission','tags':['visual','mission','quest','objective','product'],'origin':origin(),'style':'visual.mission.flow','intent':'source-first mission/quest authoring with exact objectives, conditions, branches, world references, rewards, failure/retry and runtime state','screens':ids,'flow':[
      ['visual.mission.project-hub','visual.mission.objectives','edit-objectives'],['visual.mission.objectives','visual.mission.conditions','edit-conditions'],['visual.mission.objectives','visual.mission.branch-flow','edit-flow'],['visual.mission.project-hub','visual.mission.world-bindings','edit-world'],['visual.mission.project-hub','visual.mission.rewards-outcomes','edit-rewards'],['visual.mission.project-hub','visual.mission.failure-retry','edit-failure'],['visual.mission.project-hub','visual.mission.runtime-state','inspect-runtime'],['visual.mission.project-hub','visual.mission.variants','edit-variants'],['visual.mission.project-hub','visual.mission.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.mission.core':product},'product')

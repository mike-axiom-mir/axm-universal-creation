"""Editable visual novel and branching narrative foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"visual novel {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_novel_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.novel.story':{
        'intent':'character-first branching narrative presentation with exact dialogue, scene identity, choices, state and history kept inspectable',
        'tokens':{'canvas':'#0d0d13','surface':'#181923','surface_raised':'#242637','text':'#f4f1eb','muted':'#aaa6b4','accent':'#d8a3ff','warning':'#e7bd73','danger':'#df777f','line':'#49465c'},
        'shape':{'panel_radius_ratio':0.018,'cut_ratio':0.004,'line_ratio':0.0012},
        'type':{'display_weight':730,'body_weight':500,'metric_scale':1.45,'tracking':0.010},
        'depth':{'layers':7,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':85,'standard_ms':180,'slow_ms':340,'principle':'narrative state before flourish'},
    }},'style')

    _merge(primitives,{
        'scene-background':{'role':'exact background/source asset plus independent crop/transform state','states':['known','selected','missing','unknown'],'source_and_transform_remain_separate':True},
        'character-stage':{'role':'one exact character identity with pose/expression/source and stage placement','states':['present','selected','hidden','unknown'],'identity_pose_expression_source_required':True},
        'dialogue-block':{'role':'exact speaker/text/voice-reference unit','states':['current','queued','history','missing-voice'],'speaker_text_voice_ref_exact':True},
        'choice-option':{'role':'one exact player choice with id, label, target and availability/requirements','states':['available','selected','locked','resolved'],'id_label_target_conditions_required':True},
        'branch-node':{'role':'exact narrative node with incoming/outgoing references and node type','states':['current','visited','unvisited','unreachable'],'identity_and_edges_required':True},
        'story-flag':{'role':'named runtime narrative variable with explicit value/source/change point','states':['set','unset','unknown','conflict'],'name_value_source_required':True},
        'history-entry':{'role':'ordered immutable narrative event/dialogue/choice record','states':['observed','derived','imported','unknown'],'sequence_and_source_required':True},
        'save-checkpoint':{'role':'exact restorable story state with scene/node/flags/history digest','states':['valid','selected','incompatible','corrupt'],'state_identity_digest_required':True},
        'scene-transition':{'role':'derived transition between exact source and destination scene/node states','states':['ready','preview','blocked','unknown'],'from_to_identity_required':True},
        'novel-export-target':{'role':'output target with included assets/text/branches/state metadata requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['scene, background, character staging, dialogue, choices and branch state remain separately editable','speaker text and choice targets remain exact rather than inferred from artwork','character identity, pose and expression never collapse into a decorative sprite','runtime flags, history and save checkpoints remain explicit state','derived presentation or export never replaces richer branching narrative source']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.novel.project-hub':screen('visual.novel.project-hub','Visual-novel project hub','creative.novel','visual.novel.story','browse scenes, branch coverage, characters, scripts, saves and export targets with missing state visible',v(
        {'header':(.03,.03,.94,.08),'scenes':(.03,.14,.94,.29),'branches':(.03,.46,.45,.39),'characters':(.51,.46,.46,.26),'actions':(.51,.75,.46,.10)},
        {'header':(.02,.03,.96,.075),'scenes':(.02,.14,.22,.82),'branches':(.27,.14,.46,.82),'characters':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'scenes':(.015,.13,.20,.84),'branches':(.24,.13,.50,.84),'characters':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','novel','narrative','project'],quality=q),
      'visual.novel.scene-editor':screen('visual.novel.scene-editor','Scene and background editor','creative.novel','visual.novel.story','edit exact scene identity, background source, crop/transform, staging zones and transition references',v(
        {'toolbar':(.02,.02,.96,.07),'stage':(.10,.11,.80,.55),'scenes':(.02,.11,.06,.55),'properties':(.92,.11,.06,.55),'background':(.02,.69,.46,.29),'checks':(.51,.69,.47,.29)},
        {'toolbar':(.015,.02,.97,.065),'scenes':(.015,.105,.15,.76),'stage':(.19,.105,.58,.76),'properties':(.79,.105,.195,.76),'background':(.19,.89,.38,.09),'checks':(.59,.89,.395,.09)},
        {'toolbar':(.012,.02,.976,.06),'scenes':(.012,.10,.13,.78),'stage':(.165,.10,.63,.78),'properties':(.81,.10,.178,.78),'background':(.165,.90,.40,.08),'checks':(.59,.90,.398,.08)}),tags=['visual','novel','scene','background'],math_hooks={'dialogue_safe_ratio':[0.18,0.34],'character_stage_margin_ratio':[0.03,0.12]},quality=q),
      'visual.novel.character-stage':screen('visual.novel.character-stage','Character staging editor','creative.novel','visual.novel.story','stage exact character identities, poses, expressions, depth and transforms without losing source identity',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.40),'characters':(.03,.57,.30,.30),'pose':(.36,.57,.29,.30),'source':(.68,.57,.29,.30),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'characters':(.02,.14,.20,.72),'stage':(.245,.14,.50,.72),'pose':(.77,.14,.21,.34),'source':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'characters':(.015,.13,.18,.74),'stage':(.215,.13,.54,.74),'pose':(.775,.13,.21,.35),'source':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','novel','character','staging'],quality=q),
      'visual.novel.dialogue-editor':screen('visual.novel.dialogue-editor','Dialogue and voice-reference editor','creative.novel','visual.novel.story','edit exact speaker identity, text, voice/audio reference, timing hints and presentation independently',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'script':(.03,.49,.58,.38),'details':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'script':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'script':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','novel','dialogue','script'],quality=q),
      'visual.novel.choice-editor':screen('visual.novel.choice-editor','Choice and condition editor','creative.novel','visual.novel.story','edit exact choice ids, labels, target nodes, ordering, conditions and availability without inventing branch outcomes',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'choices':(.03,.47,.55,.39),'conditions':(.61,.47,.36,.27),'actions':(.61,.77,.36,.09)},
        {'header':(.02,.03,.96,.075),'choices':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'conditions':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'choices':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'conditions':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','novel','choice','branch'],quality=q),
      'visual.novel.branch-graph':screen('visual.novel.branch-graph','Branch graph editor','creative.novel','visual.novel.story','edit exact narrative nodes and edges while keeping unreachable, unresolved and conditional routes visibly distinct',v(
        {'header':(.03,.03,.94,.08),'graph':(.03,.14,.94,.44),'nodes':(.03,.61,.45,.26),'edges':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'nodes':(.02,.14,.18,.72),'graph':(.225,.14,.53,.72),'edges':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'nodes':(.015,.13,.16,.74),'graph':(.195,.13,.56,.74),'edges':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','novel','branch','graph'],math_hooks={'node_spacing_ratio':[0.03,0.12],'edge_clearance_ratio':[0.01,0.06]},quality=q),
      'visual.novel.state-inspector':screen('visual.novel.state-inspector','Narrative state and flag inspector','creative.novel','visual.novel.story','inspect exact current node, flags, variables, character states and last-change source without guessing hidden runtime state',v(
        {'header':(.03,.03,.94,.08),'current':(.03,.14,.94,.20),'flags':(.03,.37,.45,.49),'characters':(.51,.37,.46,.35),'actions':(.51,.75,.46,.11)},
        {'header':(.02,.03,.96,.075),'flags':(.02,.14,.27,.72),'current':(.32,.14,.43,.72),'characters':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'flags':(.015,.13,.25,.74),'current':(.29,.13,.46,.74),'characters':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','novel','state','flags'],quality=q),
      'visual.novel.history-log':screen('visual.novel.history-log','Narrative history and decision log','creative.novel','visual.novel.story','inspect ordered observed dialogue, choices, transitions and state changes without rewriting prior events',v(
        {'header':(.03,.03,.94,.08),'history':(.03,.14,.94,.48),'filters':(.03,.65,.30,.22),'details':(.36,.65,.61,.22),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'filters':(.02,.14,.18,.72),'history':(.225,.14,.53,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'filters':(.015,.13,.16,.74),'history':(.195,.13,.56,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','novel','history','decision'],quality=q),
      'visual.novel.save-checkpoint':screen('visual.novel.save-checkpoint','Save and checkpoint editor','creative.novel','visual.novel.story','inspect and manage exact restorable story states with node, flags, history digest and compatibility visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'saves':(.03,.47,.55,.39),'details':(.61,.47,.36,.27),'actions':(.61,.77,.36,.09)},
        {'header':(.02,.03,.96,.075),'saves':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'saves':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','novel','save','checkpoint'],quality=q),
      'visual.novel.review-export':screen('visual.novel.review-export','Visual-novel review and export','creative.novel','visual.novel.story','review missing scenes/assets, broken branch targets, unresolved conditions, state compatibility and export requirements before derived output',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','novel','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.novel.core','version':1,'name':'Editable branching visual-novel core','kind':'product','domain':'creative.novel','tags':['visual','novel','narrative','branching','product'],'origin':origin(),'style':'visual.novel.story','intent':'source-first branching narrative editing with exact scene, character, dialogue, choice, graph, runtime state, history and save/checkpoint identity','screens':ids,'flow':[
      ['visual.novel.project-hub','visual.novel.scene-editor','edit-scene'],['visual.novel.scene-editor','visual.novel.character-stage','stage-characters'],['visual.novel.scene-editor','visual.novel.dialogue-editor','edit-dialogue'],['visual.novel.dialogue-editor','visual.novel.choice-editor','edit-choices'],['visual.novel.choice-editor','visual.novel.branch-graph','edit-branches'],['visual.novel.branch-graph','visual.novel.state-inspector','inspect-state'],['visual.novel.state-inspector','visual.novel.history-log','inspect-history'],['visual.novel.state-inspector','visual.novel.save-checkpoint','manage-save'],['visual.novel.branch-graph','visual.novel.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.novel.core':product},'product')

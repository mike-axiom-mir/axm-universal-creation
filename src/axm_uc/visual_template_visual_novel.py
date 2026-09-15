"""Editable visual-novel, branching dialogue and story-state foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"visual-novel {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_visual_novel_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.novel.stage':{
        'intent':'story-first dialogue and character staging with exact branching state, readable choices and restrained editorial chrome',
        'tokens':{'canvas':'#0c0d12','surface':'#171a22','surface_raised':'#232936','text':'#f3f1ea','muted':'#aaa7a0','accent':'#e6b86d','warning':'#dfaa67','danger':'#dc7278','line':'#464b57'},
        'shape':{'panel_radius_ratio':0.012,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.5,'tracking':0.012},
        'depth':{'layers':7,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':85,'standard_ms':175,'slow_ms':320,'principle':'speaker, choice and branch truth before flourish'},
    }},'style')

    _merge(primitives,{
        'dialogue-line':{'role':'one exact spoken/narrated line with speaker and source identity','states':['draft','ready','selected','missing-speaker'],'speaker_text_source_required':True},
        'choice-option':{'role':'one player choice with exact id, label, availability condition and destination','states':['available','selected','locked','hidden'],'id_condition_destination_required':True},
        'character-stage-slot':{'role':'staged character identity with pose/expression/source kept separate','states':['active','focused','dimmed','absent'],'identity_pose_expression_separate':True},
        'scene-background':{'role':'scene/background source with exact location/variant identity','states':['active','alternate','missing','unknown'],'source_and_scene_identity_required':True},
        'branch-edge':{'role':'directed story transition with exact from/to and condition','states':['unconditional','conditional','blocked','unknown'],'from_to_condition_required':True},
        'story-variable':{'role':'named typed story/runtime variable with explicit value source','states':['known','changed','unset','invalid'],'name_type_value_source_required':True},
        'history-entry':{'role':'resolved dialogue/choice history entry tied to exact scene/line/choice identity','states':['spoken','chosen','system','unknown'],'resolved_identity_required':True},
        'save-snapshot':{'role':'save/load point bound to exact scene, variables and snapshot identity','states':['valid','selected','stale','invalid'],'scene_state_digest_required':True},
        'voice-cue':{'role':'optional voice/audio cue bound to exact dialogue line and source','states':['linked','playing','missing','disabled'],'line_and_source_required':True},
        'story-state-diff':{'role':'explicit before/after state changes caused by a resolved branch','states':['empty','changed','conflict','unknown'],'before_after_and_cause_required':True},
    },'primitive')

    q=['dialogue text, speaker identity, character staging, choices and branch state remain separately editable','choice availability and destination remain exact instead of inferred from layout','character pose/expression never replace persistent character identity','resolved history and save state remain tied to exact scene and variable state','preview playback never becomes authoritative story source']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.novel.project-hub':screen('visual.novel.project-hub','Visual-novel project hub','creative.novel','visual.novel.stage','browse stories, scenes, branches, characters, variables and test states before editing',v(
        {'header':(.03,.03,.94,.08),'stories':(.03,.14,.94,.28),'scenes':(.03,.45,.55,.41),'state':(.61,.45,.36,.29),'actions':(.61,.77,.36,.09)},
        {'header':(.02,.03,.96,.075),'stories':(.02,.14,.20,.82),'scenes':(.245,.14,.48,.82),'state':(.75,.14,.23,.56),'actions':(.75,.73,.23,.23)},
        {'header':(.015,.03,.97,.07),'stories':(.015,.13,.18,.84),'scenes':(.215,.13,.52,.84),'state':(.755,.13,.23,.57),'actions':(.755,.73,.23,.24)}),tags=['visual','novel','story','project'],quality=q),
      'visual.novel.scene-editor':screen('visual.novel.scene-editor','Story scene editor','creative.novel','visual.novel.stage','compose background, character staging, current dialogue and exact scene state without flattening story structure',v(
        {'toolbar':(.02,.02,.96,.07),'stage':(.08,.11,.84,.51),'layers':(.02,.11,.05,.51),'properties':(.94,.11,.04,.51),'dialogue':(.02,.65,.62,.27),'state':(.67,.65,.31,.27)},
        {'toolbar':(.015,.02,.97,.065),'scenes':(.015,.105,.15,.76),'stage':(.185,.105,.58,.58),'properties':(.785,.105,.20,.58),'dialogue':(.185,.71,.58,.27),'state':(.785,.71,.20,.27)},
        {'toolbar':(.012,.02,.976,.06),'scenes':(.012,.10,.14,.77),'stage':(.17,.10,.61,.59),'properties':(.80,.10,.188,.59),'dialogue':(.17,.72,.61,.26),'state':(.80,.72,.188,.26)}),tags=['visual','novel','scene','editor'],math_hooks={'dialogue_height_ratio':[0.18,0.32],'character_safe_ratio':[0.04,0.12]},quality=q),
      'visual.novel.dialogue-editor':screen('visual.novel.dialogue-editor','Dialogue editor','creative.novel','visual.novel.stage','edit exact speaker, text, voice cue, tags and line ordering with scene preview visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'lines':(.03,.47,.55,.39),'details':(.61,.47,.36,.29),'actions':(.61,.79,.36,.07)},
        {'header':(.02,.03,.96,.075),'lines':(.02,.14,.29,.72),'preview':(.34,.14,.43,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'lines':(.015,.13,.27,.74),'preview':(.31,.13,.46,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','novel','dialogue','speaker'],quality=q),
      'visual.novel.choice-editor':screen('visual.novel.choice-editor','Choice and consequence editor','creative.novel','visual.novel.stage','edit choice ids, visible labels, availability conditions, destinations and explicit state consequences',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.28),'choices':(.03,.45,.48,.41),'conditions':(.54,.45,.43,.28),'effects':(.54,.76,.43,.10)},
        {'header':(.02,.03,.96,.075),'choices':(.02,.14,.28,.72),'preview':(.33,.14,.42,.72),'conditions':(.78,.14,.20,.34),'effects':(.78,.51,.20,.35)},
        {'header':(.015,.03,.97,.07),'choices':(.015,.13,.26,.74),'preview':(.305,.13,.45,.74),'conditions':(.775,.13,.21,.35),'effects':(.775,.51,.21,.36)}),tags=['visual','novel','choice','branch'],quality=q),
      'visual.novel.character-stage':screen('visual.novel.character-stage','Character staging editor','creative.novel','visual.novel.stage','stage exact character identities while editing pose, expression, placement and focus as separate state',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.42),'characters':(.03,.59,.45,.28),'properties':(.51,.59,.46,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'characters':(.02,.14,.18,.72),'stage':(.225,.14,.52,.72),'properties':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'characters':(.015,.13,.16,.74),'stage':(.195,.13,.56,.74),'properties':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','novel','character','stage'],quality=q),
      'visual.novel.background-editor':screen('visual.novel.background-editor','Background and scene-source editor','creative.novel','visual.novel.stage','edit exact background/location source, crop, layers and variants without changing scene identity silently',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'sources':(.03,.56,.30,.31),'crop':(.36,.56,.29,.31),'layers':(.68,.56,.29,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.18,.72),'preview':(.225,.14,.52,.72),'crop':(.77,.14,.21,.34),'layers':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.16,.74),'preview':(.195,.13,.56,.74),'crop':(.775,.13,.21,.35),'layers':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','novel','background','source'],quality=q),
      'visual.novel.branch-graph':screen('visual.novel.branch-graph','Story branch graph','creative.novel','visual.novel.stage','inspect exact scene nodes, branch edges, conditions and unreachable/conflicting states without inventing transitions',v(
        {'header':(.03,.03,.94,.08),'graph':(.03,.14,.94,.52),'nodes':(.03,.69,.45,.28),'details':(.52,.69,.45,.28)},
        {'header':(.02,.03,.96,.075),'nodes':(.02,.14,.18,.72),'graph':(.225,.14,.54,.72),'details':(.79,.14,.19,.72)},
        {'header':(.015,.03,.97,.07),'nodes':(.015,.13,.16,.74),'graph':(.195,.13,.58,.74),'details':(.795,.13,.19,.74)}),tags=['visual','novel','branch','graph'],math_hooks={'node_spacing_ratio':[0.02,0.09],'edge_clearance_ratio':[0.01,0.05]},quality=q),
      'visual.novel.history-state':screen('visual.novel.history-state','History and story-state inspector','creative.novel','visual.novel.stage','inspect resolved dialogue/choices, variable values and exact before/after state changes for a test path',v(
        {'header':(.03,.03,.94,.08),'history':(.03,.14,.94,.31),'variables':(.03,.48,.45,.39),'diff':(.51,.48,.46,.39),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'history':(.02,.14,.28,.72),'variables':(.33,.14,.28,.72),'diff':(.64,.14,.34,.56),'actions':(.64,.73,.34,.13)},
        {'header':(.015,.03,.97,.07),'history':(.015,.13,.27,.74),'variables':(.305,.13,.29,.74),'diff':(.62,.13,.365,.57),'actions':(.62,.73,.365,.14)}),tags=['visual','novel','history','state'],quality=q),
      'visual.novel.save-state':screen('visual.novel.save-state','Save and snapshot editor','creative.novel','visual.novel.stage','review exact scene/branch/variable snapshot identity for save/load and deterministic test states',v(
        {'header':(.03,.03,.94,.08),'slots':(.03,.14,.94,.32),'details':(.03,.49,.58,.38),'state':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'slots':(.02,.14,.27,.72),'details':(.32,.14,.43,.72),'state':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'slots':(.015,.13,.25,.74),'details':(.29,.13,.47,.74),'state':(.785,.13,.20,.55),'actions':(.785,.71,.20,.16)}),tags=['visual','novel','save','snapshot'],quality=q),
      'visual.novel.review-playback':screen('visual.novel.review-playback','Story review and deterministic playback','creative.novel','visual.novel.stage','review a chosen path with exact dialogue, choices, branch edges, state diffs and unresolved conditions before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'path':(.03,.47,.58,.39),'checks':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'path':(.43,.14,.34,.72),'checks':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'path':(.40,.13,.37,.74),'checks':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','novel','review','playback'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.novel.core','version':1,'name':'Editable visual-novel and branching-dialogue core','kind':'product','domain':'creative.novel','tags':['visual','novel','dialogue','branching','story','product'],'origin':origin(),'style':'visual.novel.stage','intent':'source-first branching dialogue and story editing with exact speakers, choices, conditions, character staging, variables, history and save-state identity','screens':ids,'flow':[
      ['visual.novel.project-hub','visual.novel.scene-editor','edit-scene'],['visual.novel.scene-editor','visual.novel.dialogue-editor','edit-dialogue'],['visual.novel.scene-editor','visual.novel.choice-editor','edit-choices'],['visual.novel.scene-editor','visual.novel.character-stage','stage-characters'],['visual.novel.scene-editor','visual.novel.background-editor','edit-background'],['visual.novel.scene-editor','visual.novel.branch-graph','inspect-branches'],['visual.novel.branch-graph','visual.novel.history-state','test-path'],['visual.novel.history-state','visual.novel.save-state','snapshot'],['visual.novel.history-state','visual.novel.review-playback','review']], 'quality':q}
    _merge(products,{'visual.novel.core':product},'product')

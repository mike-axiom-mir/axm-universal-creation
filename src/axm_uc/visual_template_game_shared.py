"""Reusable gameplay-system visual foundations for the existing AXM template catalog."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"game shared {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_game_shared_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'game.shared.adventure':{
        'intent':'high-readability reusable game-system language for progression, inventory, objectives, encounters and post-session state',
        'tokens':{'canvas':'#0a0f15','surface':'#131c25','surface_raised':'#1c2934','text':'#eef5f3','muted':'#9eadb4','accent':'#8bd9b7','warning':'#efc36e','danger':'#ee7474','line':'#354650'},
        'shape':{'panel_radius_ratio':0.015,'cut_ratio':0.004,'line_ratio':0.0013},
        'type':{'display_weight':730,'body_weight':500,'metric_scale':1.55,'tracking':0.014},
        'depth':{'layers':5,'shadow':'tight','glass':'restrained'},
        'motion':{'fast_ms':85,'standard_ms':170,'slow_ms':300,'principle':'game state and player choice before flourish'},
    }},'style')

    _merge(primitives,{
        'inventory-slot':{'role':'one item/equipment location with quantity, ownership and compatibility state','states':['empty','occupied','selected','equipped','locked','incompatible'],'ownership_must_be_explicit':True},
        'skill-node':{'role':'one progression choice with prerequisites, cost and unlock state','states':['locked','available','owned','selected','maxed'],'prerequisites_and_cost_must_be_visible':True},
        'objective-row':{'role':'one objective with explicit lifecycle and optional progress','states':['inactive','active','complete','failed','optional'],'state_must_not_depend_on_color':True},
        'shop-offer':{'role':'one purchase/upgrade offer with exact cost and ownership state','states':['available','owned','unaffordable','locked','selected'],'cost_and_result_must_be_visible':True},
        'codex-entry':{'role':'one discovered knowledge entry with source/discovery state','states':['unknown','discovered','new','read','selected'],'undiscovered_content_must_not_be_faked':True},
        'revive-state':{'role':'downed-player recovery status with actor, time and availability','states':['downed','revivable','reviving','revived','expired'],'timer_and_actor_must_be_explicit':True},
        'boss-phase':{'role':'major encounter state with phase, vulnerability and objective cues','states':['intro','active','transition','vulnerable','enraged','defeated'],'phase_change_needs_non_color_cue':True},
        'spectator-seat':{'role':'spectator target and control context','states':['free','following','locked-target','unavailable'],'target_identity_must_be_visible':True},
        'challenge-card':{'role':'challenge goal, progress, reward and availability','states':['available','active','complete','claimed','expired'],'progress_and_reward_must_be_explicit':True},
        'session-stat':{'role':'comparable post-session metric with source and personal/team scope','states':['normal','personal-best','team-best','unavailable'],'scope_must_be_visible':True},
    },'primitive')

    q=['player-owned state and costs remain explicit','selection and progress do not depend on color alone','irreversible choices show consequence before commitment','unknown or unavailable information remains visibly unknown instead of invented']
    def v(compact,standard,wide): return {'compact':compact,'standard':standard,'wide':wide}
    additions={
      'game.shared.inventory':screen('game.shared.inventory','Shared game inventory','game.shared','game.shared.adventure','browse, compare, equip and move owned items while keeping capacity, compatibility and selection clear',v(
        {'header':(.03,.03,.94,.08),'character':(.03,.14,.94,.18),'items':(.03,.35,.58,.51),'details':(.64,.35,.33,.38),'actions':(.64,.76,.33,.10)},
        {'header':(.02,.03,.96,.075),'equipment':(.02,.14,.20,.82),'items':(.245,.14,.48,.82),'details':(.755,.14,.225,.62),'actions':(.755,.79,.225,.17)},
        {'header':(.015,.03,.97,.07),'equipment':(.015,.13,.18,.84),'items':(.215,.13,.52,.84),'details':(.755,.13,.23,.63),'actions':(.755,.79,.23,.18)}),tags=['game','shared','inventory','equipment'],quality=q),
      'game.shared.skill-tree':screen('game.shared.skill-tree','Skill and upgrade tree','game.shared','game.shared.adventure','show progression paths, prerequisites, costs and current build without hiding locked dependencies',v(
        {'header':(.03,.03,.94,.08),'summary':(.03,.14,.94,.14),'tree':(.03,.31,.94,.45),'details':(.03,.79,.55,.17),'actions':(.61,.79,.36,.17)},
        {'header':(.02,.03,.96,.075),'categories':(.02,.14,.16,.82),'tree':(.20,.14,.56,.82),'details':(.78,.14,.20,.57),'actions':(.78,.74,.20,.22)},
        {'header':(.015,.03,.97,.07),'categories':(.015,.13,.14,.84),'tree':(.175,.13,.60,.84),'details':(.795,.13,.19,.58),'actions':(.795,.74,.19,.23)}),tags=['game','shared','skill','progression'],quality=q),
      'game.shared.mission-briefing':screen('game.shared.mission-briefing','Mission briefing','game.shared','game.shared.adventure','present objective, route, threats, team/loadout context and launch consequences before commitment',v(
        {'header':(.03,.03,.94,.08),'objective':(.03,.14,.94,.18),'map':(.03,.35,.94,.31),'threats':(.03,.69,.45,.20),'team':(.51,.69,.46,.20),'launch':(.03,.92,.94,.06)},
        {'header':(.02,.03,.96,.075),'objective':(.02,.14,.23,.72),'map':(.28,.14,.44,.55),'threats':(.75,.14,.23,.31),'team':(.75,.48,.23,.21),'launch':(.28,.73,.70,.13)},
        {'header':(.015,.03,.97,.07),'objective':(.015,.13,.21,.74),'map':(.25,.13,.48,.57),'threats':(.755,.13,.23,.32),'team':(.755,.48,.23,.22),'launch':(.25,.75,.735,.12)}),tags=['game','shared','mission','briefing'],quality=q),
      'game.shared.world-map':screen('game.shared.world-map','World and mission map','game.shared','game.shared.adventure','keep world geography primary while exposing discovered locations, objectives, filters and route planning',v(
        {'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.09),'map':(.03,.26,.94,.51),'details':(.03,.80,.58,.16),'actions':(.64,.80,.33,.16)},
        {'header':(.02,.03,.96,.075),'filters':(.02,.14,.16,.82),'map':(.20,.14,.57,.82),'details':(.79,.14,.19,.58),'actions':(.79,.75,.19,.21)},
        {'header':(.015,.03,.97,.07),'filters':(.015,.13,.14,.84),'map':(.175,.13,.61,.84),'details':(.805,.13,.18,.59),'actions':(.805,.75,.18,.22)}),tags=['game','shared','world','map'],quality=q),
      'game.shared.objective-log':screen('game.shared.objective-log','Objective and quest log','game.shared','game.shared.adventure','show active, optional, complete and failed objectives with exact progress and context',v(
        {'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.09),'objectives':(.03,.26,.55,.70),'details':(.61,.26,.36,.70)},
        {'header':(.02,.03,.96,.075),'categories':(.02,.14,.17,.82),'objectives':(.21,.14,.40,.82),'details':(.635,.14,.345,.82)},
        {'header':(.015,.03,.97,.07),'categories':(.015,.13,.15,.84),'objectives':(.185,.13,.43,.84),'details':(.635,.13,.35,.84)}),tags=['game','shared','objective','quest'],quality=q),
      'game.shared.upgrade-shop':screen('game.shared.upgrade-shop','Upgrade shop','game.shared','game.shared.adventure','compare upgrades, exact costs and resulting state before purchase or equip',v(
        {'header':(.03,.03,.94,.08),'currency':(.03,.14,.94,.10),'offers':(.03,.27,.58,.55),'details':(.64,.27,.33,.39),'actions':(.64,.69,.33,.13)},
        {'header':(.02,.03,.96,.075),'categories':(.02,.14,.17,.82),'offers':(.21,.14,.47,.82),'details':(.70,.14,.28,.56),'actions':(.70,.73,.28,.23)},
        {'header':(.015,.03,.97,.07),'categories':(.015,.13,.15,.84),'offers':(.185,.13,.50,.84),'details':(.705,.13,.28,.57),'actions':(.705,.73,.28,.24)}),tags=['game','shared','shop','upgrade'],quality=q),
      'game.shared.codex':screen('game.shared.codex','Game codex and lore','game.shared','game.shared.adventure','browse only discovered knowledge while keeping categories, source context and unread state clear',v(
        {'header':(.03,.03,.94,.08),'categories':(.03,.14,.94,.09),'entries':(.03,.26,.45,.70),'content':(.51,.26,.46,.70)},
        {'header':(.02,.03,.96,.075),'categories':(.02,.14,.17,.82),'entries':(.21,.14,.28,.82),'content':(.515,.14,.465,.82)},
        {'header':(.015,.03,.97,.07),'categories':(.015,.13,.15,.84),'entries':(.185,.13,.30,.84),'content':(.505,.13,.48,.84)}),tags=['game','shared','codex','lore'],quality=q),
      'game.shared.revive-overlay':screen('game.shared.revive-overlay','Co-op revive overlay','game.shared','game.shared.adventure','surface downed state, reviver identity, remaining time and alternatives without obscuring nearby danger',v(
        {'world':(0,0,1,1),'state':(.30,.28,.40,.18),'timer':(.40,.49,.20,.13),'reviver':(.28,.65,.44,.12),'options':(.25,.80,.50,.13)},
        {'world':(0,0,1,1),'state':(.35,.30,.30,.16),'timer':(.42,.49,.16,.12),'reviver':(.33,.64,.34,.10),'options':(.34,.80,.32,.11)},
        {'world':(0,0,1,1),'state':(.38,.30,.24,.15),'timer':(.43,.48,.14,.11),'reviver':(.36,.63,.28,.10),'options':(.37,.79,.26,.11)}),tags=['game','shared','coop','revive'],quality=q),
      'game.shared.boss-encounter-hud':screen('game.shared.boss-encounter-hud','Boss encounter HUD','game.shared','game.shared.adventure','show boss phase, health, mechanic/objective, team danger and player state while preserving encounter visibility',v(
        {'boss':(.20,.03,.60,.10),'objective':(.30,.15,.40,.09),'world':(0,0,1,1),'team':(.02,.73,.20,.24),'player':(.38,.82,.24,.14),'warnings':(.75,.72,.23,.24)},
        {'boss':(.27,.03,.46,.09),'objective':(.35,.14,.30,.08),'world':(0,0,1,1),'team':(.02,.76,.17,.20),'player':(.41,.82,.18,.14),'warnings':(.78,.76,.20,.20)},
        {'boss':(.31,.03,.38,.085),'objective':(.39,.135,.22,.075),'world':(0,0,1,1),'team':(.015,.78,.15,.18),'player':(.425,.825,.15,.13),'warnings':(.82,.78,.165,.18)}),tags=['game','shared','boss','hud'],quality=q),
      'game.shared.spectator':screen('game.shared.spectator','Spectator and follow view','game.shared','game.shared.adventure','keep viewed player/seat identity and spectator controls explicit while leaving gameplay readable',v(
        {'world':(0,0,1,1),'target':(.03,.03,.32,.10),'status':(.65,.03,.32,.10),'controls':(.22,.83,.56,.13)},
        {'world':(0,0,1,1),'target':(.02,.03,.24,.09),'status':(.74,.03,.24,.09),'controls':(.32,.84,.36,.11)},
        {'world':(0,0,1,1),'target':(.015,.03,.20,.085),'status':(.785,.03,.20,.085),'controls':(.36,.85,.28,.10)}),tags=['game','shared','spectator','seat'],quality=q),
      'game.shared.end-session-summary':screen('game.shared.end-session-summary','End-session summary','game.shared','game.shared.adventure','summarize outcome, player/team statistics, rewards, progression and next actions with stable comparisons',v(
        {'headline':(.04,.05,.92,.12),'outcome':(.04,.20,.28,.24),'stats':(.35,.20,.61,.24),'rewards':(.04,.47,.45,.30),'progress':(.52,.47,.44,.30),'actions':(.04,.81,.92,.13)},
        {'headline':(.04,.05,.92,.11),'outcome':(.04,.19,.22,.54),'stats':(.29,.19,.34,.25),'rewards':(.66,.19,.30,.25),'progress':(.29,.47,.67,.26),'actions':(.29,.78,.67,.13)},
        {'headline':(.05,.05,.90,.10),'outcome':(.05,.19,.19,.55),'stats':(.27,.19,.35,.25),'rewards':(.65,.19,.30,.25),'progress':(.27,.47,.68,.27),'actions':(.27,.79,.68,.12)}),tags=['game','shared','session','summary'],quality=q),
      'game.shared.challenge-board':screen('game.shared.challenge-board','Challenges and goals board','game.shared','game.shared.adventure','show available goals, exact progress, expiry and rewards without implying incomplete work is earned',v(
        {'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.09),'challenges':(.03,.26,.58,.70),'details':(.64,.26,.33,.50),'actions':(.64,.79,.33,.17)},
        {'header':(.02,.03,.96,.075),'categories':(.02,.14,.17,.82),'challenges':(.21,.14,.47,.82),'details':(.70,.14,.28,.58),'actions':(.70,.75,.28,.21)},
        {'header':(.015,.03,.97,.07),'categories':(.015,.13,.15,.84),'challenges':(.185,.13,.50,.84),'details':(.705,.13,.28,.59),'actions':(.705,.75,.28,.22)}),tags=['game','shared','challenge','progress'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'game.shared.core','version':1,'name':'Shared gameplay systems core','kind':'product','domain':'game.shared','tags':['game','shared','systems','product'],'origin':origin(),'style':'game.shared.adventure','intent':'reusable game-system surfaces for inventory, progression, missions, maps, objectives, upgrades, codex, encounter recovery, boss state, spectating, session results and challenges','screens':ids,'flow':[
      ['game.shared.mission-briefing','game.shared.world-map','inspect-route'],['game.shared.world-map','game.shared.objective-log','inspect-objectives'],['game.shared.inventory','game.shared.upgrade-shop','browse-upgrades'],['game.shared.upgrade-shop','game.shared.inventory','return-inventory'],['game.shared.skill-tree','game.shared.challenge-board','inspect-goals'],['game.shared.revive-overlay','game.shared.spectator','revive-expired'],['game.shared.boss-encounter-hud','game.shared.end-session-summary','encounter-complete'],['game.shared.end-session-summary','game.shared.challenge-board','review-progress'],['game.shared.codex','game.shared.world-map','locate-entry']], 'quality':q}
    _merge(products,{'game.shared.core':product},'product')

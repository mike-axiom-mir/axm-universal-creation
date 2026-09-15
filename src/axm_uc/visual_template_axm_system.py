"""AXM system-shell visual foundations using the existing v1 template catalog."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"AXM {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_axm_system_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'axm.machine.glass':{
        'intent':'layered metallic/glass machine interface with calm hierarchy, progressive detail and evidence-first status',
        'tokens':{'canvas':'#071018','surface':'#0f1c27','surface_raised':'#172b38','text':'#eef8f7','muted':'#9fb4b7','accent':'#78e0d0','warning':'#edc56f','danger':'#ef7474','line':'#31515b'},
        'shape':{'panel_radius_ratio':0.015,'cut_ratio':0.006,'line_ratio':0.0013},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.55,'tracking':0.016},
        'depth':{'layers':6,'shadow':'tight','glass':'layered'},
        'motion':{'fast_ms':85,'standard_ms':170,'slow_ms':300,'principle':'status changes remain traceable'},
    }},'style')
    _merge(primitives,{
        'truth-state':{'role':'show observed, inferred, proposed, blocked or unknown status','states':['observed','inferred','proposed','blocked','unknown'],'source_must_be_visible':True},
        'capability-card':{'role':'show one capability with scope, inputs, outputs and evidence','states':['available','sleeping','degraded','blocked','unknown'],'identity_must_be_exact':True},
        'registry-entry':{'role':'show one registered item with source and version','states':['active','available','missing-source','conflict','deprecated'],'no_floating_latest':True},
        'evidence-chip':{'role':'compact evidence state linked to source','states':['pass','fail','partial','not-tested','not-applicable'],'claim_source_required':True},
        'state-diff':{'role':'explicit before/after state difference','states':['added','changed','removed','unchanged','conflict'],'silent_rewrite_forbidden':True},
        'cartridge-card':{'role':'portable package and compatibility state','states':['ready','checking','incompatible','corrupt','mounted','unmounted'],'identity_must_be_pinned':True},
        'specialist-card':{'role':'one specialist perspective and contribution','states':['idle','working','blocked','dissent','complete'],'evidence_field_required':True},
        'workfloor-lane':{'role':'one bounded work lane over shared state','states':['idle','active','blocked','review','complete'],'shared_state_reference_required':True},
        'snapshot-entry':{'role':'recovery checkpoint with source and verification','states':['verified','unverified','restoring','failed','available'],'restore_is_explicit':True},
        'recovery-choice':{'role':'bounded recovery choice with consequence','states':['safe','destructive','blocked','unavailable'],'consequence_must_be_visible':True},
    },'primitive')

    q=['show simple current state first and reveal detail progressively','observed facts, inferences, proposals and unknowns remain distinguishable','source/version/evidence remain inspectable when they affect trust','recovery actions expose consequences before commitment']
    layouts={
      'home':({'identity':(.03,.03,.94,.09),'state':(.03,.15,.94,.21),'active':(.03,.39,.94,.25),'exceptions':(.03,.67,.45,.28),'actions':(.51,.67,.46,.28)}, {'nav':(.015,.02,.14,.96),'identity':(.18,.03,.80,.08),'state':(.18,.14,.52,.27),'active':(.18,.44,.52,.52),'exceptions':(.73,.14,.25,.35),'actions':(.73,.52,.25,.44)}, {'nav':(.012,.02,.11,.96),'identity':(.145,.03,.835,.075),'state':(.145,.14,.56,.28),'active':(.145,.45,.56,.51),'exceptions':(.73,.14,.25,.36),'actions':(.73,.53,.25,.43)}),
      'browser':({'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.10),'entries':(.03,.27,.58,.68),'details':(.64,.27,.33,.68)}, {'header':(.02,.03,.96,.075),'categories':(.02,.14,.16,.82),'entries':(.20,.14,.48,.82),'details':(.70,.14,.28,.82)}, {'header':(.015,.03,.97,.07),'categories':(.015,.13,.14,.84),'entries':(.175,.13,.52,.84),'details':(.715,.13,.27,.84)}),
      'three':({'header':(.03,.03,.94,.08),'primary':(.03,.14,.94,.38),'secondary':(.03,.55,.45,.41),'details':(.51,.55,.46,.41)}, {'header':(.02,.03,.96,.075),'primary':(.02,.14,.48,.82),'secondary':(.52,.14,.22,.82),'details':(.76,.14,.22,.82)}, {'header':(.015,.03,.97,.07),'primary':(.015,.13,.51,.84),'secondary':(.545,.13,.20,.84),'details':(.765,.13,.22,.84)}),
      'lanes':({'header':(.03,.03,.94,.08),'summary':(.03,.14,.94,.14),'lanes':(.03,.31,.94,.45),'details':(.03,.79,.94,.17)}, {'header':(.02,.03,.96,.075),'summary':(.02,.14,.20,.82),'lanes':(.245,.14,.50,.82),'details':(.77,.14,.21,.82)}, {'header':(.015,.03,.97,.07),'summary':(.015,.13,.18,.84),'lanes':(.215,.13,.54,.84),'details':(.775,.13,.21,.84)}),
      'settings':({'header':(.04,.03,.92,.08),'categories':(.04,.14,.92,.15),'settings':(.04,.32,.92,.52),'actions':(.04,.87,.92,.10)}, {'header':(.03,.03,.94,.08),'categories':(.03,.14,.22,.82),'settings':(.28,.14,.46,.82),'evidence':(.77,.14,.20,.58),'actions':(.77,.75,.20,.21)}, {'header':(.025,.03,.95,.075),'categories':(.025,.14,.19,.82),'settings':(.24,.14,.50,.82),'evidence':(.765,.14,.21,.58),'actions':(.765,.75,.21,.21)}),
    }
    def variants(key):
        a,b,c=layouts[key]; return {'compact':a,'standard':b,'wide':c}
    specs=[
      ('axm.system.home','AXM system home','home','overview of current machine state, active work, exceptions and next actions',['axm','system','home','machine']),
      ('axm.system.registry','AXM registry browser','browser','browse exact registered items with source and version visible',['axm','system','registry','source']),
      ('axm.system.capability-browser','Capability browser','browser','inspect capability scope, inputs, outputs, dependencies, evidence and availability',['axm','system','capability','browser']),
      ('axm.system.cartridge-loader','Monolith cartridge loader','three','inspect and explicitly load a portable package with compatibility and contents visible',['axm','system','monolith','cartridge']),
      ('axm.system.machine-state','Machine state inspector','three','inspect current state, active or dormant systems, dependencies and explicit changes',['axm','system','state','inspect']),
      ('axm.system.evidence-review','Evidence and truth review','three','review claims against evidence, source boundaries and untested gaps',['axm','system','evidence','truth']),
      ('axm.system.workflow','Workflow and creation flow','lanes','show requested work as explicit stages with dependencies, blockers and outputs',['axm','system','workflow','state']),
      ('axm.system.specialists','Specialist perspectives','three','show specialist scopes, evidence, dissent and contributions',['axm','system','specialists','dissent']),
      ('axm.system.workfloor','Machine workfloor','lanes','visualize concurrent bounded work lanes over shared canonical state',['axm','system','workfloor','lanes']),
      ('axm.system.snapshots','Snapshots and continuity','three','inspect checkpoints, verification, differences and restore consequences',['axm','system','snapshot','continuity']),
      ('axm.system.settings','AXM system settings','settings','edit explicit user or device policies and optional connections',['axm','system','settings','policy']),
      ('axm.system.recovery','AXM recovery and repair','three','show failure state, safe state, evidence and bounded recovery choices',['axm','system','recovery','repair']),
    ]
    additions={sid:screen(sid,name,'software.axm','axm.machine.glass',intent,variants(layout),tags=tags,quality=q) for sid,name,layout,intent,tags in specs}
    _merge(screens,additions,'screen')
    ids=[x[0] for x in specs]
    product={'schema':'axm.visual-product/v1','id':'axm.system.shell','version':1,'name':'AXM machine and monolith shell','kind':'product','domain':'software.axm','tags':['axm','system','machine','product'],'origin':origin(),'style':'axm.machine.glass','intent':'a progressively disclosed control shell for registry, capabilities, portable packages, state, evidence, workflows, specialists, workfloor, continuity and recovery','screens':ids,'flow':[
      ['axm.system.home','axm.system.registry','browse-registry'],['axm.system.home','axm.system.capability-browser','browse-capabilities'],['axm.system.home','axm.system.cartridge-loader','load-cartridge'],['axm.system.cartridge-loader','axm.system.machine-state','inspect-state'],['axm.system.machine-state','axm.system.evidence-review','review-evidence'],['axm.system.home','axm.system.workflow','inspect-work'],['axm.system.workflow','axm.system.specialists','inspect-perspectives'],['axm.system.workflow','axm.system.workfloor','inspect-workfloor'],['axm.system.home','axm.system.snapshots','inspect-continuity'],['axm.system.snapshots','axm.system.recovery','recover'],['axm.system.home','axm.system.settings','configure'],['axm.system.recovery','axm.system.home','return-home']], 'quality':q}
    _merge(products,{'axm.system.shell':product},'product')

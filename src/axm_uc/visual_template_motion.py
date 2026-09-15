"""Source-bound UI motion and transition archetypes."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"motion {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_motion_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.motion.system':{
        'intent':'state-first interface motion with exact transition identity, timing, focus continuity, interruption/recovery and reduced-motion behavior',
        'tokens':{'canvas':'#0c1014','surface':'#171d24','surface_raised':'#222b34','text':'#eff4f6','muted':'#a2adb6','accent':'#83c9bd','warning':'#e2b96d','danger':'#df7979','line':'#3d4b55'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.48,'tracking':0.010},
        'depth':{'layers':6,'shadow':'subtle','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':320,'principle':'state change before animation; reduced motion preserves meaning'},
    }},'style')

    _merge(primitives,{
        'motion-state':{'role':'exact source/target UI state identity for one motion edge','states':['source','target','active','unknown'],'source_target_identity_required':True},
        'transition-edge-state':{'role':'transition contract with exact trigger, source, target, duration and completion semantics','states':['ready','running','cancelled','completed'],'trigger_source_target_duration_required':True},
        'timing-curve':{'role':'explicit timing/easing curve with duration and bounded parameters','states':['linear','ease','spring','custom'],'duration_curve_parameters_required':True},
        'focus-motion-path':{'role':'focus/navigation motion bound to exact prior/next focus identities and semantic order','states':['forward','backward','restored','unknown'],'focus_from_to_order_required':True},
        'spatial-anchor-transition':{'role':'shared/spatial continuity transition bound to exact source and target anchors','states':['matched','entering','exiting','unresolved'],'source_target_anchor_required':True},
        'interruption-recovery':{'role':'explicit interrupted/cancelled transition with recovery or rollback destination','states':['interruptible','interrupted','recovering','resolved'],'interrupt_recovery_state_required':True},
        'progress-motion-state':{'role':'motion around observed loading/progress state without inventing completion','states':['idle','active','stalled','complete','unknown'],'progress_source_status_required':True},
        'reduced-motion-rule':{'role':'behavior-preserving reduced-motion variant for exact transition family','states':['default','reduced','off'],'equivalent_state_result_required':True},
        'motion-trigger':{'role':'exact event/input/state trigger for motion with provenance and debounce/repeat semantics','states':['armed','fired','suppressed','unknown'],'event_source_repeat_required':True},
        'motion-export-target':{'role':'motion system export target with exact transitions, timing, accessibility and runtime requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['source state, target state, trigger, timing, focus and recovery remain separately editable','animation never manufactures a state change or completion that source state has not observed','focus and spatial continuity stay bound to exact semantic identities rather than visual proximity','interruption, cancellation and rollback destinations remain explicit','reduced-motion variants preserve the same state result while reducing unnecessary motion']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.motion.project-hub':screen('visual.motion.project-hub','Motion system project hub','creative.motion','visual.motion.system','browse transition families, state coverage, accessibility variants, interruptions and runtime/export targets',v(
        {'header':(.03,.03,.94,.08),'families':(.03,.14,.94,.30),'coverage':(.03,.47,.45,.38),'accessibility':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'families':(.02,.14,.22,.82),'coverage':(.27,.14,.46,.82),'accessibility':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'families':(.015,.13,.20,.84),'coverage':(.24,.13,.50,.84),'accessibility':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','motion','transition','project'],quality=q),
      'visual.motion.transition-editor':screen('visual.motion.transition-editor','State transition editor','creative.motion','visual.motion.system','edit exact source/target state, trigger, timing and completion semantics for one transition',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'states':(.03,.53,.45,.34),'contract':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'states':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'contract':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'states':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'contract':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','motion','transition','state'],math_hooks={'travel_ratio':[0.0,0.24],'duration_ms':[60,650]},quality=q),
      'visual.motion.focus-navigation':screen('visual.motion.focus-navigation','Focus and navigation motion editor','creative.motion','visual.motion.system','edit focus movement and navigation continuity while preserving exact semantic focus order and source/target identities',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'path':(.03,.56,.45,.31),'details':(.51,.56,.46,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'path':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'path':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','motion','focus','navigation'],quality=q),
      'visual.motion.spatial-continuity':screen('visual.motion.spatial-continuity','Spatial continuity editor','creative.motion','visual.motion.system','bind shared-element and spatial transitions to exact source/target anchors rather than visual resemblance alone',v(
        {'header':(.03,.03,.94,.08),'source':(.03,.14,.45,.42),'target':(.52,.14,.45,.42),'anchors':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'source':(.02,.14,.36,.63),'target':(.40,.14,.36,.63),'anchors':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'source':(.015,.13,.37,.65),'target':(.405,.13,.37,.65),'anchors':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','motion','spatial','anchor'],quality=q),
      'visual.motion.timing-curves':screen('visual.motion.timing-curves','Timing and easing editor','creative.motion','visual.motion.system','edit bounded timing/easing parameters, durations and motion family tokens without changing source/target state',v(
        {'header':(.03,.03,.94,.08),'curve':(.03,.14,.94,.34),'presets':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'presets':(.02,.14,.28,.72),'curve':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'presets':(.015,.13,.26,.74),'curve':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','motion','timing','easing'],quality=q),
      'visual.motion.interruption-recovery':screen('visual.motion.interruption-recovery','Interruption and recovery editor','creative.motion','visual.motion.system','edit cancellation points, interruption behavior, rollback/recovery state and resumed transition identity explicitly',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'interrupts':(.03,.51,.55,.34),'recovery':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'interrupts':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'recovery':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'interrupts':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'recovery':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','motion','interrupt','recovery'],quality=q),
      'visual.motion.progress-loading':screen('visual.motion.progress-loading','Progress and loading motion editor','creative.motion','visual.motion.system','edit loading/progress/stall/completion motion while binding every visual state to observed progress/status evidence',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'states':(.03,.51,.55,.34),'source':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'states':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'source':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'states':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'source':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','motion','progress','loading'],quality=q),
      'visual.motion.reduced-motion':screen('visual.motion.reduced-motion','Reduced-motion variant editor','creative.motion','visual.motion.system','author reduced/off variants that preserve the same semantic state result while reducing travel, parallax, flashing or unnecessary motion',v(
        {'header':(.03,.03,.94,.08),'default':(.03,.14,.45,.42),'reduced':(.52,.14,.45,.42),'rules':(.03,.59,.58,.28),'actions':(.64,.59,.33,.28)},
        {'header':(.02,.03,.96,.075),'default':(.02,.14,.36,.63),'reduced':(.40,.14,.36,.63),'rules':(.78,.14,.20,.48),'actions':(.78,.65,.20,.12)},
        {'header':(.015,.03,.97,.07),'default':(.015,.13,.37,.65),'reduced':(.405,.13,.37,.65),'rules':(.795,.13,.19,.49),'actions':(.795,.65,.19,.13)}),tags=['visual','motion','reduced-motion','accessibility'],quality=q),
      'visual.motion.trigger-matrix':screen('visual.motion.trigger-matrix','Motion trigger matrix','creative.motion','visual.motion.system','bind exact events/inputs/state changes to transition identities with source, repeat/debounce and suppression behavior visible',v(
        {'header':(.03,.03,.94,.08),'matrix':(.03,.14,.94,.36),'triggers':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'triggers':(.02,.14,.28,.72),'matrix':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'triggers':(.015,.13,.26,.74),'matrix':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','motion','trigger','event'],quality=q),
      'visual.motion.review-export':screen('visual.motion.review-export','Motion system review and export','creative.motion','visual.motion.system','review missing transitions, invalid state edges, inaccessible variants, unresolved interruptions and runtime/export requirements',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','motion','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.motion.core','version':1,'name':'Source-bound UI motion and transition core','kind':'product','domain':'creative.motion','tags':['visual','motion','transition','accessibility','product'],'origin':origin(),'style':'visual.motion.system','intent':'state-first motion authoring with exact source/target states, triggers, timing, focus/spatial continuity, interruption/recovery and reduced-motion variants','screens':ids,'flow':[
      ['visual.motion.project-hub','visual.motion.transition-editor','edit-transition'],['visual.motion.transition-editor','visual.motion.focus-navigation','edit-focus'],['visual.motion.transition-editor','visual.motion.spatial-continuity','edit-spatial'],['visual.motion.transition-editor','visual.motion.timing-curves','edit-timing'],['visual.motion.transition-editor','visual.motion.interruption-recovery','edit-recovery'],['visual.motion.transition-editor','visual.motion.progress-loading','edit-progress'],['visual.motion.transition-editor','visual.motion.reduced-motion','edit-reduced'],['visual.motion.project-hub','visual.motion.trigger-matrix','edit-triggers'],['visual.motion.project-hub','visual.motion.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.motion.core':product},'product')

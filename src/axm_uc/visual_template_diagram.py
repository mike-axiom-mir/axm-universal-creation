"""Editable evidence-aware infographic and diagram foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"diagram {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_diagram_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.diagram.evidence':{
        'intent':'high-clarity diagrams and infographics where relationship meaning, provenance and uncertainty remain inspectable',
        'tokens':{'canvas':'#0b0f14','surface':'#161d25','surface_raised':'#202b36','text':'#edf3f6','muted':'#9eacb6','accent':'#76c6df','warning':'#e8bd70','danger':'#e47a7d','line':'#40505b'},
        'shape':{'panel_radius_ratio':0.012,'cut_ratio':0.002,'line_ratio':0.0013},
        'type':{'display_weight':720,'body_weight':500,'metric_scale':1.45,'tracking':0.010},
        'depth':{'layers':5,'shadow':'subtle','glass':'none'},
        'motion':{'fast_ms':80,'standard_ms':160,'slow_ms':280,'principle':'meaning and evidence before decorative movement'},
    }},'style')

    _merge(primitives,{
        'diagram-node':{'role':'one exact entity/concept/state node with identity and source/provenance state','states':['active','selected','unknown','disputed'],'identity_must_be_exact':True},
        'relationship-edge':{'role':'explicit relation from one exact node to another with relation type and direction','states':['active','selected','uncertain','disputed'],'endpoints_and_relation_type_required':True},
        'evidence-reference':{'role':'source/evidence reference supporting a node, edge or statement','states':['observed','derived','claimed','missing'],'source_and_status_required':True},
        'data-field':{'role':'one quantitative/categorical value with source, unit and freshness/period state','states':['current','historical','unknown','stale','error'],'value_unit_source_period_required':True},
        'annotation-pin':{'role':'annotation/callout bound to one exact target','states':['active','selected','orphaned','hidden'],'target_reference_must_be_exact':True},
        'legend-entry':{'role':'legend mapping for symbol/pattern/line semantics','states':['active','selected','unused'],'meaning_must_not_depend_on_color_only':True},
        'group-boundary':{'role':'explicit visual grouping with named membership/criteria','states':['active','selected','collapsed','uncertain'],'membership_must_be_explicit':True},
        'layout-guide':{'role':'derived alignment/routing guide that may aid composition but is not semantic source','states':['active','selected','hidden'],'guide_must_not_change_semantic_relationships':True},
        'callout-card':{'role':'explanatory claim/note with source/status separate from presentation','states':['observed','derived','claimed','warning'],'content_and_evidence_status_separate':True},
        'diagram-export-target':{'role':'one exact output target with dimensions, crop and content-inclusion state','states':['ready','warning','blocked','exported'],'target_requirements_must_be_visible':True},
    },'primitive')

    q=['visual adjacency alone must never imply an undeclared relationship','relationship direction and meaning remain explicit source state','claims, observations, derivations and missing evidence remain distinguishable','layout/routing changes cannot silently rewrite semantic relationships','derived exports never replace richer editable diagram source']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.diagram.project-hub':screen('visual.diagram.project-hub','Diagram and infographic project hub','creative.diagram','visual.diagram.evidence','browse diagrams, evidence coverage, source completeness, variants and output targets before editing',v(
        {'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.30),'sources':(.03,.47,.45,.38),'outputs':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'projects':(.02,.14,.22,.82),'sources':(.27,.14,.46,.82),'outputs':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'projects':(.015,.13,.20,.84),'sources':(.24,.13,.50,.84),'outputs':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','diagram','infographic','project'],quality=q),
      'visual.diagram.canvas-editor':screen('visual.diagram.canvas-editor','Diagram canvas editor','creative.diagram','visual.diagram.evidence','compose exact nodes, relationships, groups, labels and evidence references in one source-first diagram workspace',v(
        {'toolbar':(.02,.02,.96,.07),'canvas':(.12,.11,.76,.56),'library':(.02,.11,.08,.56),'properties':(.90,.11,.08,.56),'evidence':(.02,.70,.46,.28),'checks':(.51,.70,.47,.28)},
        {'toolbar':(.015,.02,.97,.065),'library':(.015,.105,.16,.75),'canvas':(.19,.105,.58,.75),'properties':(.79,.105,.195,.75),'evidence':(.19,.88,.38,.10),'checks':(.59,.88,.395,.10)},
        {'toolbar':(.012,.02,.976,.06),'library':(.012,.10,.14,.77),'canvas':(.17,.10,.62,.77),'properties':(.805,.10,.183,.77),'evidence':(.17,.90,.40,.08),'checks':(.59,.90,.398,.08)}),tags=['visual','diagram','canvas','editor'],math_hooks={'node_spacing_ratio':[0.02,0.12],'edge_clearance_ratio':[0.01,0.06]},quality=q),
      'visual.diagram.node-editor':screen('visual.diagram.node-editor','Diagram node editor','creative.diagram','visual.diagram.evidence','edit node identity, label, type, state, evidence and styling without merging semantics into appearance',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'identity':(.03,.53,.30,.34),'state':(.36,.53,.29,.34),'evidence':(.68,.53,.29,.34),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'identity':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'state':(.77,.14,.21,.34),'evidence':(.77,.51,.21,.23),'actions':(.77,.77,.21,.09)},
        {'header':(.015,.03,.97,.07),'identity':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'state':(.775,.13,.21,.35),'evidence':(.775,.51,.21,.24),'actions':(.775,.78,.21,.09)}),tags=['visual','diagram','node','editor'],quality=q),
      'visual.diagram.relationship-editor':screen('visual.diagram.relationship-editor','Relationship editor','creative.diagram','visual.diagram.evidence','edit exact from/to nodes, relation type, direction, confidence/status and supporting evidence',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'relations':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'relations':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'relations':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','diagram','relationship','edge'],quality=q),
      'visual.diagram.evidence-editor':screen('visual.diagram.evidence-editor','Evidence and data binding editor','creative.diagram','visual.diagram.evidence','bind exact sources, claims, observations, values, units, periods and freshness to diagram elements without fabricating missing evidence',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'sources':(.03,.47,.58,.39),'details':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.30,.72),'preview':(.35,.14,.40,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.28,.74),'preview':(.32,.13,.43,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','diagram','evidence','data'],quality=q),
      'visual.diagram.annotation-editor':screen('visual.diagram.annotation-editor','Annotation and callout editor','creative.diagram','visual.diagram.evidence','edit exact target-bound annotations, explanatory claims and evidence status while preserving source diagram context',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'annotations':(.03,.51,.55,.34),'details':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'annotations':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'annotations':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','diagram','annotation','callout'],quality=q),
      'visual.diagram.legend-style':screen('visual.diagram.legend-style','Legend and semantic style editor','creative.diagram','visual.diagram.evidence','edit symbol, line, pattern, label and group semantics with non-color cues and explicit meaning',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'legend':(.03,.51,.45,.34),'style':(.51,.51,.46,.34),'actions':(.03,.88,.94,.09)},
        {'header':(.02,.03,.96,.075),'legend':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'style':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'legend':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'style':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','diagram','legend','style'],quality=q),
      'visual.diagram.layout-variants':screen('visual.diagram.layout-variants','Diagram layout variants','creative.diagram','visual.diagram.evidence','compare alternate routing/grouping/layouts while preserving exact semantic nodes, edges, memberships and evidence',v(
        {'header':(.03,.03,.94,.08),'source':(.03,.14,.94,.27),'variants':(.03,.44,.94,.34),'checks':(.03,.81,.55,.15),'actions':(.61,.81,.36,.15)},
        {'header':(.02,.03,.96,.075),'source':(.02,.14,.38,.72),'variants':(.43,.14,.55,.50),'checks':(.43,.67,.31,.19),'actions':(.77,.67,.21,.19)},
        {'header':(.015,.03,.97,.07),'source':(.015,.13,.36,.74),'variants':(.40,.13,.585,.51),'checks':(.40,.67,.34,.20),'actions':(.765,.67,.22,.20)}),tags=['visual','diagram','layout','variants'],math_hooks={'group_gap_ratio':[0.03,0.14],'label_clearance_ratio':[0.01,0.06]},quality=q),
      'visual.diagram.review-compare':screen('visual.diagram.review-compare','Diagram review and truth check','creative.diagram','visual.diagram.evidence','review semantic completeness, missing evidence, orphan annotations, ambiguous edges and misleading visual proximity before export',v(
        {'header':(.03,.03,.94,.08),'primary':(.03,.14,.45,.45),'alternate':(.52,.14,.45,.45),'checks':(.03,.62,.58,.26),'actions':(.64,.62,.33,.26)},
        {'header':(.02,.03,.96,.075),'primary':(.02,.14,.38,.63),'alternate':(.42,.14,.38,.63),'checks':(.82,.14,.16,.45),'actions':(.82,.62,.16,.15)},
        {'header':(.015,.03,.97,.07),'primary':(.015,.13,.39,.65),'alternate':(.42,.13,.39,.65),'checks':(.825,.13,.16,.47),'actions':(.825,.63,.16,.15)}),tags=['visual','diagram','review','truth'],quality=q),
      'visual.diagram.export':screen('visual.diagram.export','Diagram export matrix','creative.diagram','visual.diagram.evidence','review exact output targets, inclusion/exclusion, crop, source-note and evidence-status requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'targets':(.03,.47,.58,.39),'details':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'targets':(.43,.14,.34,.72),'details':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'targets':(.40,.13,.37,.74),'details':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','diagram','export','target'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.diagram.core','version':1,'name':'Editable evidence-aware diagram core','kind':'product','domain':'creative.diagram','tags':['visual','diagram','infographic','evidence','product'],'origin':origin(),'style':'visual.diagram.evidence','intent':'source-first diagram and infographic editing with exact entities, relations, data/evidence, annotations, semantic legends and layout variants','screens':ids,'flow':[
      ['visual.diagram.project-hub','visual.diagram.canvas-editor','edit-diagram'],['visual.diagram.canvas-editor','visual.diagram.node-editor','edit-node'],['visual.diagram.canvas-editor','visual.diagram.relationship-editor','edit-relationship'],['visual.diagram.canvas-editor','visual.diagram.evidence-editor','bind-evidence'],['visual.diagram.canvas-editor','visual.diagram.annotation-editor','edit-annotations'],['visual.diagram.canvas-editor','visual.diagram.legend-style','edit-legend'],['visual.diagram.canvas-editor','visual.diagram.layout-variants','compare-layouts'],['visual.diagram.layout-variants','visual.diagram.review-compare','review'],['visual.diagram.review-compare','visual.diagram.export','export']], 'quality':q}
    _merge(products,{'visual.diagram.core':product},'product')

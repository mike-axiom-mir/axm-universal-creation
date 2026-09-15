"""Editable character, creature and asset reference-sheet foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"character-reference {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_character_reference_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.character.reference':{
        'intent':'production reference clarity with exact character identity, proportions, views, materials and source provenance separated from presentation polish',
        'tokens':{'canvas':'#0e1012','surface':'#191d21','surface_raised':'#242b31','text':'#f2f3ef','muted':'#a7adae','accent':'#8fc7bb','warning':'#deb86d','danger':'#d87578','line':'#454d50'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0011},
        'type':{'display_weight':735,'body_weight':500,'metric_scale':1.48,'tracking':0.010},
        'depth':{'layers':6,'shadow':'subtle','glass':'none'},
        'motion':{'fast_ms':80,'standard_ms':160,'slow_ms':280,'principle':'reference identity and measurement truth before flourish'},
    }},'style')

    _merge(primitives,{
        'character-source':{'role':'exact character/creature identity with source/version/digest and ownership/reference state','states':['known','selected','missing','unknown'],'identity_source_version_required':True},
        'turnaround-view':{'role':'named orthographic/perspective reference view bound to exact identity and camera/view state','states':['front','side','back','three-quarter','custom'],'identity_view_camera_required':True},
        'proportion-guide':{'role':'measurement/proportion guide with exact anchors, values, unit and source/precision','states':['exact','approximate','derived','unknown'],'anchors_value_unit_source_required':True},
        'expression-state':{'role':'named expression/emotion reference with exact character identity and source/derivation state','states':['neutral','active','selected','unknown'],'identity_name_source_required':True},
        'pose-reference':{'role':'named pose/action reference with exact identity, skeleton/anchor state and provenance','states':['rest','action','selected','unknown'],'identity_pose_source_required':True},
        'character-material':{'role':'material/surface/color assignment bound to exact body/gear part and source','states':['bound','selected','missing','unknown'],'part_material_source_required':True},
        'character-callout':{'role':'annotation bound to exact anatomical/gear/feature target with source/status','states':['visible','selected','hidden','unresolved'],'target_content_source_required':True},
        'scale-reference':{'role':'scale comparison with exact reference object/person, unit and source/assumption state','states':['exact','approximate','derived','unknown'],'reference_value_unit_source_required':True},
        'character-variant':{'role':'exact character/creature variant with base identity, deltas and availability/status','states':['active','alternate','archived','unknown'],'base_delta_status_required':True},
        'reference-export-target':{'role':'output target with exact views, dimensions, variants, callouts, sources and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['character identity, turnaround views, proportions, expressions, poses, materials and variants remain separately editable','presentation views never silently rewrite the canonical character/creature identity','measurements and scale retain unit, source and precision/assumption state','callouts stay bound to exact anatomical, gear or feature targets','derived reference sheets and exports never replace richer character source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.character.project-hub':screen('visual.character.project-hub','Character reference project hub','creative.character','visual.character.reference','browse exact characters/creatures, variants, reference coverage, source completeness and outputs',v(
        {'header':(.03,.03,.94,.08),'characters':(.03,.14,.94,.30),'variants':(.03,.47,.45,.38),'coverage':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'characters':(.02,.14,.22,.82),'variants':(.27,.14,.46,.82),'coverage':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'characters':(.015,.13,.20,.84),'variants':(.24,.13,.50,.84),'coverage':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','character','creature','reference'],quality=q),
      'visual.character.turnaround':screen('visual.character.turnaround','Character turnaround editor','creative.character','visual.character.reference','edit front/side/back/three-quarter reference views bound to exact character identity and view state',v(
        {'header':(.03,.03,.94,.08),'views':(.03,.14,.94,.50),'guide':(.03,.67,.45,.20),'details':(.51,.67,.46,.20),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'list':(.02,.14,.18,.72),'views':(.225,.14,.55,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'list':(.015,.13,.16,.74),'views':(.195,.13,.58,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','character','turnaround','view'],math_hooks={'figure_height_ratio':[0.55,0.88],'view_gap_ratio':[0.015,0.08]},quality=q),
      'visual.character.proportions':screen('visual.character.proportions','Proportion and measurement editor','creative.character','visual.character.reference','edit exact measurement anchors, proportion guides, units, precision and source while showing character reference view',v(
        {'header':(.03,.03,.94,.08),'figure':(.03,.14,.94,.36),'guides':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'guides':(.02,.14,.25,.72),'figure':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'guides':(.015,.13,.23,.74),'figure':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','character','proportion','measurement'],quality=q),
      'visual.character.expressions':screen('visual.character.expressions','Expression sheet editor','creative.character','visual.character.reference','edit named expression references, identity and source state without flattening expression into character identity',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.50),'list':(.03,.67,.45,.20),'details':(.51,.67,.46,.20),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'list':(.02,.14,.20,.72),'grid':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'list':(.015,.13,.18,.74),'grid':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','character','expression','face'],quality=q),
      'visual.character.poses':screen('visual.character.poses','Pose and action reference editor','creative.character','visual.character.reference','edit exact pose/action references, skeleton/anchor state and provenance with canonical identity preserved',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.40),'poses':(.03,.57,.45,.30),'details':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'poses':(.02,.14,.20,.72),'stage':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'poses':(.015,.13,.18,.74),'stage':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','character','pose','action'],quality=q),
      'visual.character.materials':screen('visual.character.materials','Character material and surface editor','creative.character','visual.character.reference','bind exact body/gear parts to material/surface/color sources while keeping assignment identity explicit',v(
        {'header':(.03,.03,.94,.08),'figure':(.03,.14,.94,.36),'parts':(.03,.53,.45,.34),'materials':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'parts':(.02,.14,.22,.72),'figure':(.27,.14,.48,.72),'materials':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'parts':(.015,.13,.20,.74),'figure':(.24,.13,.51,.74),'materials':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','character','material','surface'],quality=q),
      'visual.character.callouts':screen('visual.character.callouts','Feature and equipment callout editor','creative.character','visual.character.reference','bind annotations to exact anatomy, gear or feature targets with source/status visible',v(
        {'header':(.03,.03,.94,.08),'figure':(.03,.14,.94,.39),'callouts':(.03,.56,.45,.31),'details':(.51,.56,.46,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'callouts':(.02,.14,.20,.72),'figure':(.245,.14,.50,.72),'details':(.77,.14,.21,.54),'actions':(.77,.71,.21,.15)},
        {'header':(.015,.03,.97,.07),'callouts':(.015,.13,.18,.74),'figure':(.215,.13,.54,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','character','callout','gear'],quality=q),
      'visual.character.scale-variants':screen('visual.character.scale-variants','Scale and character-variant editor','creative.character','visual.character.reference','compare scale against exact references and edit variants as explicit deltas from canonical identity',v(
        {'header':(.03,.03,.94,.08),'comparison':(.03,.14,.94,.36),'scale':(.03,.53,.45,.34),'variants':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'scale':(.02,.14,.22,.72),'comparison':(.27,.14,.48,.72),'variants':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'scale':(.015,.13,.20,.74),'comparison':(.24,.13,.51,.74),'variants':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','character','scale','variant'],quality=q),
      'visual.character.reference-board':screen('visual.character.reference-board','Character source/reference board','creative.character','visual.character.reference','organize source/reference material with role, provenance and exact relation to character features without treating inspiration as canonical source',v(
        {'header':(.03,.03,.94,.08),'board':(.03,.14,.94,.43),'references':(.03,.60,.55,.27),'details':(.61,.60,.36,.27),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'references':(.02,.14,.23,.72),'board':(.28,.14,.47,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'references':(.015,.13,.21,.74),'board':(.26,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','character','reference','source'],quality=q),
      'visual.character.review-export':screen('visual.character.review-export','Character reference review and export','creative.character','visual.character.reference','review missing views, inconsistent measurements, unresolved callouts/materials, variants and source requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','character','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.character.core','version':1,'name':'Editable character and creature reference core','kind':'product','domain':'creative.character','tags':['visual','character','creature','reference','product'],'origin':origin(),'style':'visual.character.reference','intent':'source-first character/creature reference editing with exact identity, views, proportions, expressions, poses, materials, callouts, scale and variants','screens':ids,'flow':[
      ['visual.character.project-hub','visual.character.turnaround','edit-turnaround'],['visual.character.turnaround','visual.character.proportions','edit-proportions'],['visual.character.project-hub','visual.character.expressions','edit-expressions'],['visual.character.project-hub','visual.character.poses','edit-poses'],['visual.character.turnaround','visual.character.materials','edit-materials'],['visual.character.turnaround','visual.character.callouts','edit-callouts'],['visual.character.project-hub','visual.character.scale-variants','edit-scale-variants'],['visual.character.project-hub','visual.character.reference-board','inspect-references'],['visual.character.project-hub','visual.character.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.character.core':product},'product')

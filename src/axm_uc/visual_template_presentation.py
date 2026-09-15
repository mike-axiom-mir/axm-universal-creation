"""Editable presentation, explainer-page and source-bound storytelling foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"presentation {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_presentation_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.presentation.story':{
        'intent':'high-clarity visual explanation with exact source, figure, section and narrative ordering preserved beneath flexible presentation',
        'tokens':{'canvas':'#0d0f13','surface':'#181c23','surface_raised':'#242b35','text':'#f3f4f1','muted':'#a8afb4','accent':'#83c9de','warning':'#dfb96f','danger':'#dc7378','line':'#444d56'},
        'shape':{'panel_radius_ratio':0.013,'cut_ratio':0.002,'line_ratio':0.0011},
        'type':{'display_weight':760,'body_weight':500,'metric_scale':1.55,'tracking':0.012},
        'depth':{'layers':7,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':320,'principle':'meaning and source continuity before flourish'},
    }},'style')

    _merge(primitives,{
        'presentation-page':{'role':'exact page/slide identity with role, order and source state','states':['draft','selected','ready','missing'],'identity_role_order_required':True},
        'content-block':{'role':'typed content block with exact source/content identity and semantic role','states':['ready','selected','overflow','missing-source'],'type_content_source_required':True},
        'source-footnote':{'role':'citation/provenance reference bound to exact claim/figure/block target','states':['observed','derived','claimed','missing'],'target_source_status_required':True},
        'figure-frame':{'role':'embedded image/diagram/chart/atlas/showroom reference with exact source and caption','states':['ready','selected','missing','stale'],'source_caption_identity_required':True},
        'presentation-section':{'role':'named ordered page membership and section intent','states':['active','selected','collapsed','invalid'],'membership_order_required':True},
        'emphasis-cue':{'role':'derived visual emphasis bound to exact content target without changing meaning','states':['active','selected','muted','disabled'],'target_required':True,'must_not_rewrite_source_meaning':True},
        'speaker-note':{'role':'non-rendered presenter/editor note with exact page/block target and author/source state','states':['draft','ready','selected','hidden'],'target_and_source_required':True},
        'embed-binding':{'role':'exact reusable template/artifact embedding with version/digest and selected view','states':['bound','selected','missing','incompatible'],'identity_version_view_required':True},
        'presentation-transition':{'role':'derived transition between exact ordered pages','states':['cut','fade','move','disabled'],'from_to_identity_required':True,'must_not_change_page_order':True},
        'presentation-export-target':{'role':'output target with exact page range, aspect, assets, source-note and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['page identity, content, figures, source references, section order and speaker notes remain separately editable','layout, emphasis and transitions never rewrite exact source meaning or narrative order','embedded diagrams, key art, atlas, showroom and other artifacts retain exact identity/version/view bindings','missing or disputed source state remains visible rather than being hidden by polished presentation','preview/export remains derived from richer presentation source state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.presentation.project-hub':screen('visual.presentation.project-hub','Presentation project hub','creative.presentation','visual.presentation.story','browse decks/explainers, sections, source coverage, embedded assets and output targets before editing',v(
        {'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.30),'pages':(.03,.47,.55,.38),'coverage':(.61,.47,.36,.27),'actions':(.61,.77,.36,.08)},
        {'header':(.02,.03,.96,.075),'sections':(.02,.14,.20,.82),'pages':(.245,.14,.48,.82),'coverage':(.75,.14,.23,.55),'actions':(.75,.72,.23,.14)},
        {'header':(.015,.03,.97,.07),'sections':(.015,.13,.18,.84),'pages':(.215,.13,.52,.84),'coverage':(.755,.13,.23,.57),'actions':(.755,.73,.23,.14)}),tags=['visual','presentation','project','explainer'],quality=q),
      'visual.presentation.page-editor':screen('visual.presentation.page-editor','Presentation page editor','creative.presentation','visual.presentation.story','compose one exact page from independently editable content, figures, callouts and source references',v(
        {'toolbar':(.02,.02,.96,.07),'page':(.12,.11,.76,.56),'blocks':(.02,.11,.08,.56),'properties':(.90,.11,.08,.56),'notes':(.02,.70,.45,.28),'sources':(.50,.70,.48,.28)},
        {'toolbar':(.015,.02,.97,.065),'blocks':(.015,.105,.16,.76),'page':(.195,.105,.55,.76),'properties':(.77,.105,.215,.56),'notes':(.77,.69,.105,.17),'sources':(.88,.69,.105,.17)},
        {'toolbar':(.012,.02,.976,.06),'blocks':(.012,.10,.14,.78),'page':(.17,.10,.59,.78),'properties':(.78,.10,.208,.58),'notes':(.78,.71,.098,.17),'sources':(.89,.71,.098,.17)}),tags=['visual','presentation','page','editor'],math_hooks={'page_safe_ratio':[0.035,0.12],'headline_area_ratio':[0.08,0.25]},quality=q),
      'visual.presentation.outline-editor':screen('visual.presentation.outline-editor','Narrative outline and section editor','creative.presentation','visual.presentation.story','edit exact section membership, page ordering and narrative roles without presentation layout silently changing sequence',v(
        {'header':(.03,.03,.94,.08),'sections':(.03,.14,.94,.28),'pages':(.03,.45,.55,.41),'details':(.61,.45,.36,.29),'actions':(.61,.77,.36,.09)},
        {'header':(.02,.03,.96,.075),'sections':(.02,.14,.23,.72),'pages':(.28,.14,.48,.72),'details':(.79,.14,.19,.54),'actions':(.79,.71,.19,.15)},
        {'header':(.015,.03,.97,.07),'sections':(.015,.13,.21,.74),'pages':(.26,.13,.50,.74),'details':(.785,.13,.20,.55),'actions':(.785,.71,.20,.16)}),tags=['visual','presentation','outline','section'],quality=q),
      'visual.presentation.block-editor':screen('visual.presentation.block-editor','Content block editor','creative.presentation','visual.presentation.story','edit typed content blocks, semantic roles, exact text/data and source identity with overflow visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'blocks':(.03,.49,.55,.38),'details':(.61,.49,.36,.28),'actions':(.61,.80,.36,.07)},
        {'header':(.02,.03,.96,.075),'blocks':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'blocks':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','presentation','content','block'],quality=q),
      'visual.presentation.figure-editor':screen('visual.presentation.figure-editor','Figure and reusable-artifact editor','creative.presentation','visual.presentation.story','bind exact diagrams, key art, atlas, showroom or other artifacts and edit crop/caption/view separately from source identity',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'figures':(.03,.53,.45,.34),'binding':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'figures':(.02,.14,.23,.72),'preview':(.28,.14,.47,.72),'binding':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'figures':(.015,.13,.21,.74),'preview':(.26,.13,.49,.74),'binding':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','presentation','figure','embed'],quality=q),
      'visual.presentation.source-editor':screen('visual.presentation.source-editor','Source, citation and evidence editor','creative.presentation','visual.presentation.story','bind claims/figures/blocks to exact source references and observed/derived/claimed/missing status',v(
        {'header':(.03,.03,.94,.08),'page':(.03,.14,.94,.28),'sources':(.03,.45,.58,.42),'details':(.64,.45,.33,.29),'actions':(.64,.77,.33,.10)},
        {'header':(.02,.03,.96,.075),'targets':(.02,.14,.25,.72),'sources':(.30,.14,.47,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'targets':(.015,.13,.23,.74),'sources':(.265,.13,.50,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','presentation','source','citation'],quality=q),
      'visual.presentation.emphasis-layout':screen('visual.presentation.emphasis-layout','Emphasis and layout-variant editor','creative.presentation','visual.presentation.story','edit responsive layout and emphasis cues while keeping exact content meaning, page identity and source bindings unchanged',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.38),'variants':(.03,.55,.45,.32),'emphasis':(.51,.55,.46,.25),'actions':(.51,.83,.46,.04)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'emphasis':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'emphasis':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','presentation','layout','emphasis'],quality=q),
      'visual.presentation.notes-review':screen('visual.presentation.notes-review','Speaker notes and review editor','creative.presentation','visual.presentation.story','review page-specific notes, source gaps, overflow, continuity and unresolved claims without putting private notes into rendered output',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'notes':(.03,.47,.45,.39),'checks':(.51,.47,.46,.29),'actions':(.51,.79,.46,.07)},
        {'header':(.02,.03,.96,.075),'notes':(.02,.14,.27,.72),'preview':(.32,.14,.43,.72),'checks':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'notes':(.015,.13,.25,.74),'preview':(.29,.13,.46,.74),'checks':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','presentation','notes','review'],quality=q),
      'visual.presentation.sequence-preview':screen('visual.presentation.sequence-preview','Presentation sequence and transition preview','creative.presentation','visual.presentation.story','preview exact page order and derived transitions while preserving original page/content/source identities',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'sequence':(.03,.57,.58,.30),'transition':(.64,.57,.33,.22),'actions':(.64,.82,.33,.05)},
        {'header':(.02,.03,.96,.075),'sequence':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'transition':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'sequence':(.015,.13,.22,.74),'preview':(.265,.13,.49,.74),'transition':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','presentation','sequence','transition'],quality=q),
      'visual.presentation.export':screen('visual.presentation.export','Presentation review and export matrix','creative.presentation','visual.presentation.story','review page range, source completeness, embedded artifact identity, output aspect and provenance requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','presentation','export','evidence'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.presentation.core','version':1,'name':'Editable presentation and explainer core','kind':'product','domain':'creative.presentation','tags':['visual','presentation','explainer','storytelling','product'],'origin':origin(),'style':'visual.presentation.story','intent':'source-first presentation and explainer editing with exact page order, content/source identity, reusable artifact bindings, notes and output requirements','screens':ids,'flow':[
      ['visual.presentation.project-hub','visual.presentation.outline-editor','edit-outline'],['visual.presentation.outline-editor','visual.presentation.page-editor','edit-page'],['visual.presentation.page-editor','visual.presentation.block-editor','edit-content'],['visual.presentation.page-editor','visual.presentation.figure-editor','edit-figures'],['visual.presentation.page-editor','visual.presentation.source-editor','bind-sources'],['visual.presentation.page-editor','visual.presentation.emphasis-layout','edit-layout'],['visual.presentation.page-editor','visual.presentation.notes-review','review-notes'],['visual.presentation.outline-editor','visual.presentation.sequence-preview','preview-sequence'],['visual.presentation.sequence-preview','visual.presentation.export','review-export']], 'quality':q}
    _merge(products,{'visual.presentation.core':product},'product')

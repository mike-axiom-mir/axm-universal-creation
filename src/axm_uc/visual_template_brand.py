"""Source-bound brand, identity and usage-system foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"brand {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_brand_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.brand.identity':{
        'intent':'source-bound identity systems with exact marks, typography, icon families, tokens, spacing and usage rules separated from mockup presentation',
        'tokens':{'canvas':'#0d1014','surface':'#181d24','surface_raised':'#232a33','text':'#f2f3ef','muted':'#a7adaf','accent':'#91c6b7','warning':'#deb76b','danger':'#dd7777','line':'#444d54'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.001,'line_ratio':0.0012},
        'type':{'display_weight':740,'body_weight':500,'metric_scale':1.5,'tracking':0.012},
        'depth':{'layers':6,'shadow':'subtle','glass':'none'},
        'motion':{'fast_ms':80,'standard_ms':165,'slow_ms':300,'principle':'identity/source truth before presentation flourish'},
    }},'style')

    _merge(primitives,{
        'brand-asset-source':{'role':'exact logo/mark/wordmark asset identity with source/version/digest and rights/provenance state','states':['known','active','archived','unknown'],'identity_source_version_provenance_required':True},
        'brand-lockup':{'role':'exact composition of identity assets with relative layout, spacing and approved-use identity','states':['primary','secondary','compact','forbidden'],'asset_refs_layout_status_required':True},
        'brand-type-role':{'role':'typography role bound to exact family/style/source plus semantic use','states':['display','heading','body','caption','fallback'],'font_source_role_required':True},
        'brand-icon-family':{'role':'icon family identity with source/version, construction rules and member references','states':['active','draft','deprecated','unknown'],'family_source_members_required':True},
        'brand-token':{'role':'named identity token with exact value, unit/context, source and usage role','states':['active','alternate','deprecated','unknown'],'value_context_source_required':True},
        'brand-clearspace-rule':{'role':'protection/spacing rule bound to exact mark/lockup and measurement basis','states':['required','advisory','exception','unknown'],'target_measurement_basis_required':True},
        'brand-usage-rule':{'role':'allowed/forbidden/conditional usage rule with exact subject, context and rationale/source','states':['allowed','forbidden','conditional','unknown'],'subject_context_status_source_required':True},
        'brand-application':{'role':'application/mockup bound to exact identity assets/tokens and target surface state','states':['preview','approved','exception','unknown'],'asset_token_target_refs_required':True},
        'brand-variant':{'role':'exact identity variant with base reference, deltas, intended context and availability','states':['active','alternate','restricted','archived'],'base_delta_context_required':True},
        'brand-export-target':{'role':'identity-system export target with exact assets, tokens, rules, formats and provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['marks, typography, icons, tokens, rules, variants and applications remain separately editable','a polished mockup never silently becomes canonical identity source','spacing and protection rules retain exact target and measurement basis','usage variants and exceptions remain explicit rather than inferred from visual similarity','exports remain derived packages from exact identity assets, tokens, rules and provenance']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.brand.project-hub':screen('visual.brand.project-hub','Brand identity project hub','creative.brand','visual.brand.identity','browse identity assets, systems, approved variants, rule coverage and export targets',v(
        {'header':(.03,.03,.94,.08),'assets':(.03,.14,.94,.30),'systems':(.03,.47,.45,.38),'coverage':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'assets':(.02,.14,.22,.82),'systems':(.27,.14,.46,.82),'coverage':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'assets':(.015,.13,.20,.84),'systems':(.24,.13,.50,.84),'coverage':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','brand','identity','project'],quality=q),
      'visual.brand.marks-lockups':screen('visual.brand.marks-lockups','Marks and lockup editor','creative.brand','visual.brand.identity','edit exact logos, marks, wordmarks and lockups while preserving asset/source identity and approved-use status',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.42),'assets':(.03,.59,.45,.28),'rules':(.51,.59,.46,.28),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'assets':(.02,.14,.22,.72),'stage':(.27,.14,.48,.72),'rules':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'assets':(.015,.13,.20,.74),'stage':(.24,.13,.51,.74),'rules':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','brand','logo','lockup'],math_hooks={'mark_coverage_ratio':[0.24,0.70],'clearspace_ratio':[0.04,0.50]},quality=q),
      'visual.brand.typography':screen('visual.brand.typography','Brand typography editor','creative.brand','visual.brand.identity','bind typography roles to exact families/styles/sources and semantic uses with fallback state visible',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'roles':(.03,.53,.55,.34),'details':(.61,.53,.36,.25),'actions':(.61,.81,.36,.06)},
        {'header':(.02,.03,.96,.075),'roles':(.02,.14,.25,.72),'preview':(.30,.14,.45,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'roles':(.015,.13,.23,.74),'preview':(.265,.13,.49,.74),'details':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','brand','typography','type'],quality=q),
      'visual.brand.icons':screen('visual.brand.icons','Icon family editor','creative.brand','visual.brand.identity','edit exact icon-family identity, construction rules, member references and deprecation state without mixing unrelated icon sources',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.44),'families':(.03,.61,.45,.26),'details':(.51,.61,.46,.26),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'families':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'families':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','brand','icon','family'],quality=q),
      'visual.brand.tokens':screen('visual.brand.tokens','Identity token editor','creative.brand','visual.brand.identity','edit named color, spacing, shape, depth and other identity tokens with exact values, context, units and source',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'tokens':(.03,.49,.58,.38),'details':(.64,.49,.33,.28),'actions':(.64,.80,.33,.07)},
        {'header':(.02,.03,.96,.075),'tokens':(.02,.14,.28,.72),'preview':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'tokens':(.015,.13,.26,.74),'preview':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','brand','token','system'],quality=q),
      'visual.brand.spacing-usage':screen('visual.brand.spacing-usage','Clearspace and usage-rule editor','creative.brand','visual.brand.identity','edit exact clearspace/protection measurements and allowed, forbidden or conditional usage contexts',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'spacing':(.03,.51,.45,.36),'usage':(.51,.51,.46,.36),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'spacing':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'usage':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'spacing':(.015,.13,.22,.74),'preview':(.265,.13,.48,.74),'usage':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','brand','spacing','usage'],quality=q),
      'visual.brand.variants':screen('visual.brand.variants','Identity variant editor','creative.brand','visual.brand.identity','edit exact primary, compact, monochrome, contextual or restricted variants as deltas from named base identity',v(
        {'header':(.03,.03,.94,.08),'grid':(.03,.14,.94,.40),'variants':(.03,.57,.55,.30),'details':(.61,.57,.36,.22),'actions':(.61,.82,.36,.05)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.22,.72),'grid':(.27,.14,.48,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.20,.74),'grid':(.24,.13,.51,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','brand','variant','identity'],quality=q),
      'visual.brand.applications':screen('visual.brand.applications','Brand application editor','creative.brand','visual.brand.identity','apply exact identity assets and tokens to target surfaces while keeping the mockup derived and its bindings inspectable',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'applications':(.03,.57,.45,.30),'bindings':(.51,.57,.46,.22),'actions':(.51,.82,.46,.05)},
        {'header':(.02,.03,.96,.075),'applications':(.02,.14,.22,.72),'preview':(.27,.14,.48,.72),'bindings':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'applications':(.015,.13,.20,.74),'preview':(.24,.13,.51,.74),'bindings':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','brand','application','mockup'],quality=q),
      'visual.brand.review-audit':screen('visual.brand.review-audit','Identity review and rule audit','creative.brand','visual.brand.identity','review missing provenance, inconsistent assets/tokens, spacing violations, forbidden usage and unresolved variants before export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'issues':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'issues':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'issues':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','brand','review','audit'],quality=q),
      'visual.brand.export':screen('visual.brand.export','Brand-system export matrix','creative.brand','visual.brand.identity','review exact assets, variants, typography, icons, tokens, rules, formats and provenance requirements before derived package export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'targets':(.03,.47,.58,.39),'details':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'targets':(.43,.14,.34,.72),'details':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'targets':(.40,.13,.37,.74),'details':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','brand','export','identity'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.brand.core','version':1,'name':'Source-bound brand and identity system core','kind':'product','domain':'creative.brand','tags':['visual','brand','identity','system','product'],'origin':origin(),'style':'visual.brand.identity','intent':'source-first identity authoring with exact marks, lockups, typography, icons, tokens, spacing/usage rules, variants, applications and provenance-backed exports','screens':ids,'flow':[
      ['visual.brand.project-hub','visual.brand.marks-lockups','edit-marks'],['visual.brand.project-hub','visual.brand.typography','edit-type'],['visual.brand.project-hub','visual.brand.icons','edit-icons'],['visual.brand.project-hub','visual.brand.tokens','edit-tokens'],['visual.brand.marks-lockups','visual.brand.spacing-usage','edit-rules'],['visual.brand.project-hub','visual.brand.variants','edit-variants'],['visual.brand.project-hub','visual.brand.applications','edit-applications'],['visual.brand.project-hub','visual.brand.review-audit','review'],['visual.brand.review-audit','visual.brand.export','export']], 'quality':q}
    _merge(products,{'visual.brand.core':product},'product')

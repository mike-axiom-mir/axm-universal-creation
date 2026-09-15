"""Editable key-art, poster and cover composition foundations for AXM visual templates."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"keyart {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_keyart_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.keyart.cinematic':{
        'intent':'high-impact visual composition with strong focal hierarchy while preserving separately editable subject, atmosphere, type and export state',
        'tokens':{'canvas':'#09090d','surface':'#15161d','surface_raised':'#20232d','text':'#f5f2ed','muted':'#afa9a0','accent':'#f0bd68','warning':'#ee9964','danger':'#e86f74','line':'#454955'},
        'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':780,'body_weight':500,'metric_scale':1.65,'tracking':0.018},
        'depth':{'layers':7,'shadow':'cinematic','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':160,'slow_ms':300,'principle':'preserve focal hierarchy and editable composition state'},
    }},'style')

    _merge(primitives,{
        'hero-subject':{'role':'primary visual subject with source, crop, depth and transform state','states':['active','selected','masked','occluded','missing-source'],'source_and_transform_must_remain_editable':True},
        'depth-layer':{'role':'ordered foreground/midground/background layer with explicit depth relationship','states':['foreground','midground','background','selected','hidden'],'order_must_be_explicit':True},
        'focal-mask':{'role':'editable focus/attention region used to protect composition hierarchy','states':['active','selected','disabled'],'mask_must_not_replace_source_art':True},
        'title-lockup':{'role':'title/subtitle/logo grouping with hierarchy, alignment and safe-area state','states':['rest','selected','overflow','alternate'],'text_and_layout_remain_separate':True},
        'credit-block':{'role':'credits/legal/byline block with exact content and placement','states':['rest','selected','overflow','hidden'],'content_must_remain_exact':True},
        'lighting-pass':{'role':'separate lighting/effect contribution over composition source','states':['active','selected','muted','disabled'],'effect_must_remain_non_authoritative':True},
        'crop-safe-frame':{'role':'target-format crop and protected content region','states':['portrait','landscape','square','banner','selected'],'crop_must_not_modify_source_geometry':True},
        'variant-card':{'role':'one explicit alternate composition with pinned source state','states':['draft','selected','approved','rejected'],'variant_identity_must_be_exact':True},
        'export-target':{'role':'one output target with dimensions, crop, quality and file-state expectations','states':['ready','warning','blocked','exported'],'target_requirements_must_be_visible':True},
    },'primitive')

    q=['hero subject, typography, atmosphere and effects remain separately editable','focal hierarchy survives crop variants unless explicitly changed','derived crop/export output never replaces richer source composition','title and credit overflow remain visible instead of silently clipping','alternate compositions remain exact variants rather than hidden random rewrites']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.keyart.project-hub':screen('visual.keyart.project-hub','Key art project hub','creative.keyart','visual.keyart.cinematic','browse compositions, variants, target formats and source completeness before editing',v(
        {'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.38),'variants':(.03,.55,.55,.31),'targets':(.61,.55,.36,.31),'actions':(.03,.89,.94,.08)},
        {'header':(.02,.03,.96,.075),'projects':(.02,.14,.28,.72),'variants':(.33,.14,.42,.72),'targets':(.78,.14,.20,.50),'actions':(.78,.67,.20,.19)},
        {'header':(.015,.03,.97,.07),'projects':(.015,.13,.25,.74),'variants':(.285,.13,.46,.74),'targets':(.765,.13,.22,.52),'actions':(.765,.69,.22,.18)}),tags=['visual','keyart','project','hub'],quality=q),
      'visual.keyart.composition-editor':screen('visual.keyart.composition-editor','Key art composition editor','creative.keyart','visual.keyart.cinematic','compose hero subject, depth layers, title, effects and crop-safe hierarchy in one source-first workspace',v(
        {'toolbar':(.02,.02,.96,.07),'canvas':(.12,.11,.76,.56),'layers':(.02,.11,.08,.56),'properties':(.90,.11,.08,.56),'variants':(.02,.70,.46,.28),'targets':(.51,.70,.47,.28)},
        {'toolbar':(.015,.02,.97,.065),'layers':(.015,.105,.16,.75),'canvas':(.19,.105,.58,.75),'properties':(.79,.105,.195,.75),'variants':(.19,.88,.38,.10),'targets':(.59,.88,.395,.10)},
        {'toolbar':(.012,.02,.976,.06),'layers':(.012,.10,.14,.77),'canvas':(.17,.10,.62,.77),'properties':(.805,.10,.183,.77),'variants':(.17,.90,.40,.08),'targets':(.59,.90,.398,.08)}),tags=['visual','keyart','composition','editor'],math_hooks={'hero_focus_ratio':[0.32,0.62],'title_safe_ratio':[0.06,0.20]},quality=q),
      'visual.keyart.subject-stage':screen('visual.keyart.subject-stage','Hero subject staging','creative.keyart','visual.keyart.cinematic','edit subject source, mask, pose/crop, scale, overlap and depth without flattening the visual stack',v(
        {'header':(.03,.03,.94,.08),'stage':(.03,.14,.94,.43),'sources':(.03,.60,.29,.28),'mask':(.35,.60,.29,.28),'transform':(.67,.60,.30,.28),'actions':(.03,.91,.94,.06)},
        {'header':(.02,.03,.96,.075),'sources':(.02,.14,.17,.72),'stage':(.21,.14,.53,.72),'mask':(.765,.14,.215,.34),'transform':(.765,.51,.215,.35),'actions':(.21,.89,.77,.07)},
        {'header':(.015,.03,.97,.07),'sources':(.015,.13,.15,.74),'stage':(.185,.13,.57,.74),'mask':(.78,.13,.205,.35),'transform':(.78,.51,.205,.36),'actions':(.185,.90,.80,.06)}),tags=['visual','keyart','subject','mask'],quality=q),
      'visual.keyart.type-editor':screen('visual.keyart.type-editor','Title and typography editor','creative.keyart','visual.keyart.cinematic','edit title/subtitle/marks/credits with hierarchy, safe area and overflow visible against composition context',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.37),'hierarchy':(.03,.54,.29,.32),'type':(.35,.54,.30,.32),'credits':(.68,.54,.29,.32),'actions':(.03,.89,.94,.08)},
        {'header':(.02,.03,.96,.075),'hierarchy':(.02,.14,.20,.72),'preview':(.245,.14,.49,.72),'type':(.76,.14,.22,.42),'credits':(.76,.59,.22,.27),'actions':(.245,.89,.735,.07)},
        {'header':(.015,.03,.97,.07),'hierarchy':(.015,.13,.18,.74),'preview':(.215,.13,.53,.74),'type':(.765,.13,.22,.43),'credits':(.765,.59,.22,.28),'actions':(.215,.90,.77,.06)}),tags=['visual','keyart','typography','title'],quality=q),
      'visual.keyart.lighting-effects':screen('visual.keyart.lighting-effects','Lighting and effects editor','creative.keyart','visual.keyart.cinematic','build separate lighting, glow, atmosphere and effect passes while keeping contribution order and intensity inspectable',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'passes':(.03,.56,.42,.31),'properties':(.48,.56,.49,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'passes':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'properties':(.77,.14,.21,.55),'actions':(.77,.72,.21,.14)},
        {'header':(.015,.03,.97,.07),'passes':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'properties':(.775,.13,.21,.56),'actions':(.775,.72,.21,.15)}),tags=['visual','keyart','lighting','effects'],quality=q),
      'visual.keyart.background-atmosphere':screen('visual.keyart.background-atmosphere','Background and atmosphere editor','creative.keyart','visual.keyart.cinematic','edit environment, depth layers, haze/color atmosphere and supporting elements without competing with focal subject',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.39),'layers':(.03,.56,.42,.31),'atmosphere':(.48,.56,.49,.31),'actions':(.03,.90,.94,.07)},
        {'header':(.02,.03,.96,.075),'layers':(.02,.14,.20,.72),'preview':(.245,.14,.50,.72),'atmosphere':(.77,.14,.21,.55),'actions':(.77,.72,.21,.14)},
        {'header':(.015,.03,.97,.07),'layers':(.015,.13,.18,.74),'preview':(.215,.13,.54,.74),'atmosphere':(.775,.13,.21,.56),'actions':(.775,.72,.21,.15)}),tags=['visual','keyart','background','atmosphere'],quality=q),
      'visual.keyart.crop-variants':screen('visual.keyart.crop-variants','Crop and format variants','creative.keyart','visual.keyart.cinematic','compare portrait, landscape, square and banner crops while protecting focal subject, title and credits',v(
        {'header':(.03,.03,.94,.08),'source':(.03,.14,.94,.28),'crops':(.03,.45,.94,.33),'safe':(.03,.81,.55,.15),'actions':(.61,.81,.36,.15)},
        {'header':(.02,.03,.96,.075),'source':(.02,.14,.38,.72),'crops':(.43,.14,.55,.50),'safe':(.43,.67,.31,.19),'actions':(.77,.67,.21,.19)},
        {'header':(.015,.03,.97,.07),'source':(.015,.13,.36,.74),'crops':(.40,.13,.585,.51),'safe':(.40,.67,.34,.20),'actions':(.765,.67,.22,.20)}),tags=['visual','keyart','crop','variants'],math_hooks={'safe_inset_ratio':[0.04,0.12],'focal_keep_ratio':[0.55,0.90]},quality=q),
      'visual.keyart.variant-board':screen('visual.keyart.variant-board','Composition variant board','creative.keyart','visual.keyart.cinematic','compare exact alternate compositions side by side with identity, notes and selection state visible',v(
        {'header':(.03,.03,.94,.08),'variants':(.03,.14,.94,.56),'compare':(.03,.73,.58,.23),'actions':(.64,.73,.33,.23)},
        {'header':(.02,.03,.96,.075),'filters':(.02,.14,.16,.82),'variants':(.20,.14,.55,.82),'compare':(.77,.14,.21,.56),'actions':(.77,.73,.21,.23)},
        {'header':(.015,.03,.97,.07),'filters':(.015,.13,.14,.84),'variants':(.175,.13,.59,.84),'compare':(.785,.13,.20,.57),'actions':(.785,.73,.20,.24)}),tags=['visual','keyart','variant','compare'],quality=q),
      'visual.keyart.review-compare':screen('visual.keyart.review-compare','Key art review and comparison','creative.keyart','visual.keyart.cinematic','review selected variants, focal hierarchy, crop safety, text overflow and source completeness before export approval',v(
        {'header':(.03,.03,.94,.08),'primary':(.03,.14,.45,.45),'alternate':(.52,.14,.45,.45),'checks':(.03,.62,.58,.26),'actions':(.64,.62,.33,.26)},
        {'header':(.02,.03,.96,.075),'primary':(.02,.14,.38,.63),'alternate':(.42,.14,.38,.63),'checks':(.82,.14,.16,.45),'actions':(.82,.62,.16,.15)},
        {'header':(.015,.03,.97,.07),'primary':(.015,.13,.39,.65),'alternate':(.42,.13,.39,.65),'checks':(.825,.13,.16,.47),'actions':(.825,.63,.16,.15)}),tags=['visual','keyart','review','compare'],quality=q),
      'visual.keyart.export':screen('visual.keyart.export','Key art export matrix','creative.keyart','visual.keyart.cinematic','review explicit output targets, dimensions, crop variants, quality state and filenames before publishing derived files',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'targets':(.03,.47,.58,.39),'details':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'targets':(.43,.14,.34,.72),'details':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'targets':(.40,.13,.37,.74),'details':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','keyart','export','target'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.keyart.core','version':1,'name':'Editable key art composition core','kind':'product','domain':'creative.keyart','tags':['visual','keyart','poster','cover','product'],'origin':origin(),'style':'visual.keyart.cinematic','intent':'source-first key art, poster, cover and banner composition with editable subject, depth, type, atmosphere, effects, variants and crop-safe export targets','screens':ids,'flow':[
      ['visual.keyart.project-hub','visual.keyart.composition-editor','open-composition'],['visual.keyart.composition-editor','visual.keyart.subject-stage','edit-subject'],['visual.keyart.composition-editor','visual.keyart.type-editor','edit-type'],['visual.keyart.composition-editor','visual.keyart.lighting-effects','edit-lighting'],['visual.keyart.composition-editor','visual.keyart.background-atmosphere','edit-background'],['visual.keyart.composition-editor','visual.keyart.crop-variants','adapt-formats'],['visual.keyart.crop-variants','visual.keyart.variant-board','compare-variants'],['visual.keyart.variant-board','visual.keyart.review-compare','review'],['visual.keyart.review-compare','visual.keyart.export','export']], 'quality':q}
    _merge(products,{'visual.keyart.core':product},'product')

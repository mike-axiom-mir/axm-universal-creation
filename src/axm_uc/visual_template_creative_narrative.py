"""Creative-editor and editable visual-narrative foundations for AXM visual templates.

This extension keeps editability visible: source structure, layers, tracks, panels,
dialogue and references remain separate semantic regions instead of being flattened
into one output image. It extends the existing v1 catalog only.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _merge_unique(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap:
        raise RuntimeError(f"creative/narrative {label} extension collides: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_creative_narrative_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    new_styles={
        'creative.workbench': {
            'intent':'professional multi-surface editing with stable tools, visible source state and dense but inspectable controls',
            'tokens':{'canvas':'#090d12','surface':'#121922','surface_raised':'#1a2530','text':'#eef4f6','muted':'#9cacb6','accent':'#72c7ff','warning':'#efc46e','danger':'#ee7474','line':'#33434f'},
            'shape':{'panel_radius_ratio':0.010,'cut_ratio':0.002,'line_ratio':0.0012},
            'type':{'display_weight':720,'body_weight':490,'metric_scale':1.46,'tracking':0.010},
            'depth':{'layers':6,'shadow':'subtle','glass':'none'},
            'motion':{'fast_ms':75,'standard_ms':150,'slow_ms':260,'principle':'preserve selection and editing context'},
        },
        'narrative.ink': {
            'intent':'story-first visual composition with strong page rhythm, editable dialogue and restrained editorial chrome',
            'tokens':{'canvas':'#0c0c0f','surface':'#17171c','surface_raised':'#222229','text':'#f4f1ea','muted':'#b8b2a7','accent':'#f2bf68','warning':'#e79b63','danger':'#e87373','line':'#45444a'},
            'shape':{'panel_radius_ratio':0.008,'cut_ratio':0.0,'line_ratio':0.0013},
            'type':{'display_weight':750,'body_weight':500,'metric_scale':1.52,'tracking':0.012},
            'depth':{'layers':5,'shadow':'soft','glass':'none'},
            'motion':{'fast_ms':90,'standard_ms':180,'slow_ms':320,'principle':'reading order and story state before decoration'},
        },
    }
    new_primitives={
        'layer-row':{'role':'editable ordered visual layer with visibility, lock and selection state','states':['visible','hidden','locked','selected','nested'],'order_must_be_explicit':True},
        'timeline-track':{'role':'time-based property or media lane','states':['idle','armed','muted','locked','selected'],'time_range_must_be_explicit':True},
        'keyframe':{'role':'editable value at an exact timeline position','states':['rest','selected','held','interpolated'],'time_and_value_must_be_inspectable':True},
        'node-card':{'role':'inspectable operation in a visual graph','states':['rest','selected','warning','error','disabled'],'operation_identity_must_be_explicit':True},
        'socket-port':{'role':'typed graph connection point','states':['open','connected','incompatible','invalid'],'type_mismatch_must_be_visible':True},
        'inspector-field':{'role':'edit one explicit property without hiding source value','states':['rest','focused','modified','invalid','read-only'],'modified_state_must_be_visible':True},
        'asset-tile':{'role':'browse one source asset with identity and provenance','states':['rest','selected','missing','linked','embedded'],'source_identity_must_be_visible':True},
        'panel-frame':{'role':'editable comic/story panel boundary','states':['rest','selected','locked','overflow'],'geometry_must_remain_editable':True},
        'panel-gutter':{'role':'explicit spacing between narrative panels','states':['normal','selected'],'spacing_is_structure':True},
        'speech-bubble':{'role':'editable spoken dialogue container tied to a speaker/target','states':['rest','selected','overflow','unresolved-speaker'],'text_and_tail_remain_separate':True},
        'caption-box':{'role':'editable narration or contextual text','states':['rest','selected','overflow'],'reading_order_must_be_explicit':True},
        'storyboard-card':{'role':'scene or shot summary preserving order and status','states':['draft','ready','blocked','selected'],'sequence_position_must_be_visible':True},
        'reading-order-marker':{'role':'explicit panel/dialogue reading sequence','states':['rest','selected','conflict'],'order_conflicts_must_fail_visible':True},
        'character-reference-card':{'role':'persistent visual/identity reference for a character','states':['active','alternate','missing-reference'],'reference_source_must_be_explicit':True},
        'story-beat-link':{'role':'directed narrative transition between beats/scenes','states':['normal','conditional','blocked'],'transition_semantics_must_be_explicit':True},
    }
    _merge_unique(styles,new_styles,'style'); _merge_unique(primitives,new_primitives,'primitive')

    editor_quality=[
        'editable source state outranks preview convenience',
        'selection, active tool and modified state remain visible',
        'derived previews never replace richer canonical project state',
        'destructive edits expose scope and recovery consequence before commitment',
    ]
    comic_quality=[
        'panel geometry, source art, dialogue and reading order remain independently editable',
        'flattened preview is never authoritative source state',
        'speaker/reference identity remains inspectable instead of inferred silently',
        'overflow and reading-order conflicts remain visible',
    ]

    editor_screens={
        'editor.creative.project-hub': screen('editor.creative.project-hub','Creative project hub','software.creator','creative.workbench','resume, create and inspect creative projects without losing status or source identity',{
            'compact':{'header':(.03,.03,.94,.08),'recent':(.03,.14,.94,.38),'templates':(.03,.55,.94,.25),'actions':(.03,.83,.94,.13)},
            'standard':{'header':(.025,.03,.95,.08),'recent':(.025,.14,.57,.70),'templates':(.62,.14,.355,.48),'actions':(.62,.66,.355,.18)},
            'wide':{'header':(.02,.03,.96,.075),'recent':(.02,.14,.60,.72),'templates':(.65,.14,.33,.49),'actions':(.65,.67,.33,.19)}},tags=['software','creator','project','editor'],quality=editor_quality),
        'editor.creative.asset-browser': screen('editor.creative.asset-browser','Creative asset browser','software.creator','creative.workbench','browse source assets with provenance, filters, preview and explicit insertion target',{
            'compact':{'header':(.03,.03,.94,.08),'filters':(.03,.14,.94,.10),'assets':(.03,.27,.58,.68),'preview':(.64,.27,.33,.50),'details':(.64,.80,.33,.15)},
            'standard':{'header':(.025,.03,.95,.08),'sources':(.025,.14,.16,.82),'assets':(.21,.14,.48,.82),'preview':(.715,.14,.26,.54),'details':(.715,.71,.26,.25)},
            'wide':{'header':(.02,.03,.96,.075),'sources':(.02,.14,.14,.82),'assets':(.18,.14,.52,.82),'preview':(.72,.14,.26,.55),'details':(.72,.72,.26,.24)}},tags=['software','creator','assets','browser'],quality=editor_quality),
        'editor.creative.layer-editor': screen('editor.creative.layer-editor','Layer and composition editor','software.creator','creative.workbench','edit ordered visual layers while keeping canvas, hierarchy and properties simultaneously inspectable',{
            'compact':{'toolbar':(.02,.02,.96,.07),'canvas':(.14,.11,.84,.55),'tools':(.02,.11,.10,.55),'layers':(.02,.69,.45,.29),'properties':(.50,.69,.48,.29)},
            'standard':{'toolbar':(.015,.02,.97,.065),'tools':(.015,.105,.055,.67),'layers':(.085,.105,.17,.67),'canvas':(.27,.105,.50,.67),'properties':(.79,.105,.195,.67),'status':(.085,.80,.90,.18)},
            'wide':{'toolbar':(.012,.02,.976,.06),'tools':(.012,.10,.045,.69),'layers':(.07,.10,.15,.69),'canvas':(.235,.10,.54,.69),'properties':(.79,.10,.198,.69),'status':(.07,.82,.918,.16)}},tags=['software','creator','layers','composition'],quality=editor_quality),
        'editor.creative.timeline': screen('editor.creative.timeline','Creative timeline editor','software.creator','creative.workbench','edit temporal structure with tracks, exact playhead, curves and preview in one stable workspace',{
            'compact':{'transport':(.03,.03,.94,.08),'preview':(.03,.14,.94,.32),'tracks':(.03,.49,.94,.33),'properties':(.03,.85,.94,.12)},
            'standard':{'transport':(.02,.03,.96,.075),'preview':(.02,.14,.32,.54),'tracks':(.37,.14,.61,.54),'properties':(.02,.72,.32,.24),'curves':(.37,.72,.61,.24)},
            'wide':{'transport':(.015,.03,.97,.07),'preview':(.015,.13,.29,.56),'tracks':(.33,.13,.655,.56),'properties':(.015,.72,.29,.25),'curves':(.33,.72,.655,.25)}},tags=['software','creator','timeline','animation'],quality=editor_quality),
        'editor.creative.node-graph': screen('editor.creative.node-graph','Node graph editor','software.creator','creative.workbench','compose inspectable operations with typed connections, graph context and selected-node properties',{
            'compact':{'toolbar':(.03,.03,.94,.08),'graph':(.03,.14,.94,.52),'library':(.03,.69,.45,.28),'properties':(.52,.69,.45,.28)},
            'standard':{'toolbar':(.02,.03,.96,.075),'library':(.02,.14,.17,.82),'graph':(.21,.14,.56,.82),'properties':(.79,.14,.19,.82)},
            'wide':{'toolbar':(.015,.03,.97,.07),'library':(.015,.13,.15,.84),'graph':(.18,.13,.60,.84),'properties':(.795,.13,.19,.84)}},tags=['software','creator','nodes','graph'],quality=editor_quality),
        'editor.creative.inspector': screen('editor.creative.inspector','Deep property inspector','software.creator','creative.workbench','inspect and edit exact selected-object properties with defaults, deltas, provenance and validation',{
            'compact':{'header':(.04,.03,.92,.08),'identity':(.04,.14,.92,.15),'fields':(.04,.32,.92,.52),'actions':(.04,.87,.92,.10)},
            'standard':{'header':(.03,.03,.94,.08),'groups':(.03,.14,.22,.82),'fields':(.28,.14,.46,.82),'evidence':(.77,.14,.20,.58),'actions':(.77,.75,.20,.21)},
            'wide':{'header':(.025,.03,.95,.075),'groups':(.025,.14,.19,.82),'fields':(.24,.14,.50,.82),'evidence':(.765,.14,.21,.58),'actions':(.765,.75,.21,.21)}},tags=['software','creator','inspector','properties'],quality=editor_quality),
        'editor.creative.animation': screen('editor.creative.animation','Animation editing workspace','software.creator','creative.workbench','edit rigs, poses, clips and curves while preserving exact scene and timeline context',{
            'compact':{'toolbar':(.02,.02,.96,.07),'viewport':(.02,.11,.96,.43),'rig':(.02,.57,.30,.28),'timeline':(.35,.57,.63,.28),'properties':(.02,.88,.96,.10)},
            'standard':{'toolbar':(.015,.02,.97,.065),'rig':(.015,.105,.16,.66),'viewport':(.19,.105,.50,.66),'properties':(.705,.105,.28,.66),'timeline':(.19,.795,.805,.185)},
            'wide':{'toolbar':(.012,.02,.976,.06),'rig':(.012,.10,.14,.68),'viewport':(.17,.10,.54,.68),'properties':(.725,.10,.263,.68),'timeline':(.17,.80,.818,.18)}},tags=['software','creator','animation','rig'],quality=editor_quality),
        'editor.creative.effects': screen('editor.creative.effects','Effects editing workspace','software.creator','creative.workbench','compose visual effects from emitters, materials, timing and previewable parameters without flattening recipes',{
            'compact':{'toolbar':(.02,.02,.96,.07),'preview':(.02,.11,.96,.40),'stack':(.02,.54,.35,.32),'properties':(.40,.54,.58,.32),'timeline':(.02,.89,.96,.09)},
            'standard':{'toolbar':(.015,.02,.97,.065),'stack':(.015,.105,.18,.68),'preview':(.21,.105,.49,.68),'properties':(.715,.105,.27,.68),'timeline':(.21,.80,.775,.18)},
            'wide':{'toolbar':(.012,.02,.976,.06),'stack':(.012,.10,.16,.69),'preview':(.19,.10,.52,.69),'properties':(.725,.10,.263,.69),'timeline':(.19,.81,.798,.17)}},tags=['software','creator','effects','vfx'],quality=editor_quality),
        'editor.creative.cutscene': screen('editor.creative.cutscene','Cutscene editor','software.creator','creative.workbench','coordinate shots, cameras, dialogue, animation and timing with explicit sequence structure',{
            'compact':{'toolbar':(.02,.02,.96,.07),'preview':(.02,.11,.96,.38),'shots':(.02,.52,.34,.32),'timeline':(.39,.52,.59,.32),'properties':(.02,.87,.96,.11)},
            'standard':{'toolbar':(.015,.02,.97,.065),'shots':(.015,.105,.17,.68),'preview':(.20,.105,.50,.52),'properties':(.715,.105,.27,.52),'timeline':(.20,.65,.785,.33)},
            'wide':{'toolbar':(.012,.02,.976,.06),'shots':(.012,.10,.15,.69),'preview':(.18,.10,.54,.52),'properties':(.735,.10,.253,.52),'timeline':(.18,.65,.808,.33)}},tags=['software','creator','cutscene','cinematic'],quality=editor_quality),
        'editor.creative.material': screen('editor.creative.material','Material editor','software.creator','creative.workbench','edit material channels, procedural graph and object preview with source maps remaining inspectable',{
            'compact':{'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.33),'channels':(.03,.50,.45,.33),'graph':(.51,.50,.46,.33),'actions':(.03,.86,.94,.10)},
            'standard':{'header':(.02,.03,.96,.075),'channels':(.02,.14,.20,.82),'preview':(.245,.14,.35,.56),'graph':(.61,.14,.37,.56),'actions':(.245,.74,.735,.22)},
            'wide':{'header':(.015,.03,.97,.07),'channels':(.015,.13,.18,.84),'preview':(.215,.13,.37,.58),'graph':(.61,.13,.375,.58),'actions':(.215,.75,.77,.22)}},tags=['software','creator','material','shader'],quality=editor_quality),
        'editor.creative.audio': screen('editor.creative.audio','Audio editing workspace','software.creator','creative.workbench','edit clips, levels, routing and timeline placement while retaining source and meter context',{
            'compact':{'header':(.03,.03,.94,.08),'waveform':(.03,.14,.94,.28),'mixer':(.03,.45,.45,.38),'timeline':(.51,.45,.46,.38),'actions':(.03,.86,.94,.10)},
            'standard':{'header':(.02,.03,.96,.075),'sources':(.02,.14,.16,.82),'waveform':(.20,.14,.49,.33),'mixer':(.715,.14,.265,.52),'timeline':(.20,.50,.49,.46),'actions':(.715,.70,.265,.26)},
            'wide':{'header':(.015,.03,.97,.07),'sources':(.015,.13,.14,.84),'waveform':(.175,.13,.53,.34),'mixer':(.725,.13,.26,.53),'timeline':(.175,.50,.53,.47),'actions':(.725,.70,.26,.27)}},tags=['software','creator','audio','timeline'],quality=editor_quality),
        'editor.creative.review-export': screen('editor.creative.review-export','Creative review and export','software.creator','creative.workbench','compare output, source state, checks and export targets before explicit publication',{
            'compact':{'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'checks':(.03,.51,.45,.31),'export':(.51,.51,.46,.31),'actions':(.03,.85,.94,.11)},
            'standard':{'header':(.02,.03,.96,.075),'preview':(.02,.14,.55,.66),'checks':(.60,.14,.18,.66),'export':(.80,.14,.18,.48),'actions':(.80,.66,.18,.14)},
            'wide':{'header':(.015,.03,.97,.07),'preview':(.015,.13,.58,.68),'checks':(.615,.13,.17,.68),'export':(.805,.13,.18,.49),'actions':(.805,.66,.18,.15)}},tags=['software','creator','review','export'],quality=editor_quality),
    }

    comic_screens={
        'comic.narrative.library': screen('comic.narrative.library','Narrative project library','creative.comic','narrative.ink','browse stories, episodes, pages and source references without flattening project structure',{
            'compact':{'header':(.03,.03,.94,.08),'projects':(.03,.14,.94,.40),'episodes':(.03,.57,.45,.29),'references':(.51,.57,.46,.29),'actions':(.03,.89,.94,.08)},
            'standard':{'header':(.025,.03,.95,.08),'projects':(.025,.14,.26,.72),'episodes':(.315,.14,.42,.72),'references':(.76,.14,.215,.55),'actions':(.76,.72,.215,.14)},
            'wide':{'header':(.02,.03,.96,.075),'projects':(.02,.14,.23,.73),'episodes':(.275,.14,.46,.73),'references':(.76,.14,.22,.56),'actions':(.76,.74,.22,.13)}},tags=['comic','narrative','library','project'],quality=comic_quality),
        'comic.narrative.page-editor': screen('comic.narrative.page-editor','Comic page editor','creative.comic','narrative.ink','edit page geometry, panels, gutters, overlays and page-level reading order while source art stays separate',{
            'compact':{'toolbar':(.02,.02,.96,.07),'page':(.12,.11,.76,.57),'panels':(.02,.11,.08,.57),'layers':(.02,.71,.45,.27),'properties':(.50,.71,.48,.27)},
            'standard':{'toolbar':(.015,.02,.97,.065),'pages':(.015,.105,.13,.875),'page':(.17,.105,.52,.79),'layers':(.715,.105,.13,.79),'properties':(.845,.105,.14,.79),'status':(.17,.915,.815,.065)},
            'wide':{'toolbar':(.012,.02,.976,.06),'pages':(.012,.10,.11,.88),'page':(.145,.10,.56,.80),'layers':(.725,.10,.12,.80),'properties':(.86,.10,.128,.80),'status':(.145,.925,.843,.055)}},tags=['comic','narrative','page','editor'],math_hooks={'page_focus_ratio':[0.50,0.66],'gutter_ratio':[0.01,0.05]},quality=comic_quality),
        'comic.narrative.panel-editor': screen('comic.narrative.panel-editor','Comic panel editor','creative.comic','narrative.ink','edit one panel crop, depth, source art, effects and embedded dialogue while preserving page context',{
            'compact':{'header':(.03,.03,.94,.08),'panel':(.03,.14,.94,.43),'sources':(.03,.60,.30,.27),'layers':(.36,.60,.29,.27),'properties':(.68,.60,.29,.27),'actions':(.03,.90,.94,.07)},
            'standard':{'header':(.02,.03,.96,.075),'page-context':(.02,.14,.17,.70),'panel':(.21,.14,.50,.70),'layers':(.735,.14,.11,.70),'properties':(.86,.14,.12,.70),'actions':(.21,.88,.77,.08)},
            'wide':{'header':(.015,.03,.97,.07),'page-context':(.015,.13,.15,.72),'panel':(.18,.13,.54,.72),'layers':(.74,.13,.10,.72),'properties':(.855,.13,.13,.72),'actions':(.18,.89,.805,.07)}},tags=['comic','narrative','panel','editor'],quality=comic_quality),
        'comic.narrative.dialogue-editor': screen('comic.narrative.dialogue-editor','Dialogue and lettering editor','creative.comic','narrative.ink','edit dialogue text, speaker identity, bubble shape/tail and reading order as separate state',{
            'compact':{'header':(.03,.03,.94,.08),'panel-preview':(.03,.14,.94,.35),'dialogue':(.03,.52,.45,.34),'bubble':(.51,.52,.46,.34),'order':(.03,.89,.94,.08)},
            'standard':{'header':(.02,.03,.96,.075),'dialogue':(.02,.14,.24,.72),'panel-preview':(.285,.14,.46,.72),'bubble':(.765,.14,.215,.54),'order':(.765,.72,.215,.14)},
            'wide':{'header':(.015,.03,.97,.07),'dialogue':(.015,.13,.22,.74),'panel-preview':(.255,.13,.49,.74),'bubble':(.765,.13,.22,.56),'order':(.765,.73,.22,.14)}},tags=['comic','narrative','dialogue','lettering'],quality=comic_quality),
        'comic.narrative.character-sheet': screen('comic.narrative.character-sheet','Character reference sheet','creative.comic','narrative.ink','keep identity, visual references, expressions, outfits and continuity notes together without collapsing variants',{
            'compact':{'header':(.03,.03,.94,.08),'hero':(.03,.14,.94,.30),'expressions':(.03,.47,.45,.28),'outfits':(.51,.47,.46,.28),'notes':(.03,.78,.94,.18)},
            'standard':{'header':(.02,.03,.96,.075),'hero':(.02,.14,.32,.70),'expressions':(.37,.14,.28,.34),'outfits':(.68,.14,.30,.34),'notes':(.37,.51,.61,.33)},
            'wide':{'header':(.015,.03,.97,.07),'hero':(.015,.13,.30,.72),'expressions':(.35,.13,.29,.35),'outfits':(.67,.13,.315,.35),'notes':(.35,.51,.635,.34)}},tags=['comic','narrative','character','reference'],quality=comic_quality),
        'comic.narrative.scene-graph': screen('comic.narrative.scene-graph','Narrative scene graph','creative.comic','narrative.ink','map story beats, branches, dependencies and unresolved transitions without hiding alternate paths',{
            'compact':{'header':(.03,.03,.94,.08),'graph':(.03,.14,.94,.51),'beats':(.03,.68,.45,.29),'properties':(.51,.68,.46,.29)},
            'standard':{'header':(.02,.03,.96,.075),'beats':(.02,.14,.18,.82),'graph':(.22,.14,.56,.82),'properties':(.80,.14,.18,.82)},
            'wide':{'header':(.015,.03,.97,.07),'beats':(.015,.13,.16,.84),'graph':(.19,.13,.60,.84),'properties':(.81,.13,.175,.84)}},tags=['comic','narrative','scene','graph'],quality=comic_quality),
        'comic.narrative.storyboard': screen('comic.narrative.storyboard','Storyboard editor','creative.comic','narrative.ink','arrange shots/pages/beats in explicit sequence with reference imagery and status visible',{
            'compact':{'header':(.03,.03,.94,.08),'board':(.03,.14,.94,.55),'details':(.03,.72,.58,.24),'references':(.64,.72,.33,.24)},
            'standard':{'header':(.02,.03,.96,.075),'sequence':(.02,.14,.16,.82),'board':(.20,.14,.55,.82),'details':(.775,.14,.205,.47),'references':(.775,.64,.205,.32)},
            'wide':{'header':(.015,.03,.97,.07),'sequence':(.015,.13,.14,.84),'board':(.175,.13,.59,.84),'details':(.785,.13,.20,.48),'references':(.785,.64,.20,.33)}},tags=['comic','narrative','storyboard','sequence'],quality=comic_quality),
        'comic.narrative.motion-timeline': screen('comic.narrative.motion-timeline','Motion-comic timeline','creative.comic','narrative.ink','time panel movement, camera, dialogue reveals, effects and audio while preserving the static page/story source',{
            'compact':{'transport':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'tracks':(.03,.51,.94,.32),'properties':(.03,.86,.94,.11)},
            'standard':{'transport':(.02,.03,.96,.075),'preview':(.02,.14,.38,.54),'tracks':(.43,.14,.55,.54),'properties':(.02,.72,.38,.24),'curves':(.43,.72,.55,.24)},
            'wide':{'transport':(.015,.03,.97,.07),'preview':(.015,.13,.36,.56),'tracks':(.40,.13,.585,.56),'properties':(.015,.72,.36,.25),'curves':(.40,.72,.585,.25)}},tags=['comic','narrative','motion','timeline'],quality=comic_quality),
        'comic.narrative.reader-preview': screen('comic.narrative.reader-preview','Comic reader preview','creative.comic','narrative.ink','preview reading sequence, page transitions and text fit without replacing editable source',{
            'compact':{'reader':(.05,.04,.90,.80),'navigation':(.05,.87,.90,.09)},
            'standard':{'context':(.02,.04,.16,.92),'reader':(.21,.04,.58,.92),'navigation':(.82,.04,.16,.92)},
            'wide':{'context':(.015,.04,.14,.92),'reader':(.18,.04,.62,.92),'navigation':(.83,.04,.155,.92)}},tags=['comic','narrative','reader','preview'],quality=comic_quality),
        'comic.narrative.export': screen('comic.narrative.export','Narrative review and export','creative.comic','narrative.ink','review pages, source completeness, reading order and export targets before explicit publication',{
            'compact':{'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'checks':(.03,.51,.45,.31),'export':(.51,.51,.46,.31),'actions':(.03,.85,.94,.11)},
            'standard':{'header':(.02,.03,.96,.075),'preview':(.02,.14,.55,.66),'checks':(.60,.14,.18,.66),'export':(.80,.14,.18,.48),'actions':(.80,.66,.18,.14)},
            'wide':{'header':(.015,.03,.97,.07),'preview':(.015,.13,.58,.68),'checks':(.615,.13,.17,.68),'export':(.805,.13,.18,.49),'actions':(.805,.66,.18,.15)}},tags=['comic','narrative','review','export'],quality=comic_quality),
    }
    _merge_unique(screens,editor_screens|comic_screens,'screen')

    editor_ids=list(editor_screens)
    comic_ids=list(comic_screens)
    new_products={
        'editor.creative.core':{
            'schema':'axm.visual-product/v1','id':'editor.creative.core','version':1,'name':'Creative editor core','kind':'product','domain':'software.creator','tags':['software','creator','editor','product'],'origin':origin(),'style':'creative.workbench','intent':'a reusable professional editing shell that preserves source state across asset, layer, timeline, graph, animation, effects, audio and export work','screens':editor_ids,
            'flow':[
                ['editor.creative.project-hub','editor.creative.asset-browser','open-project'],
                ['editor.creative.asset-browser','editor.creative.layer-editor','insert-asset'],
                ['editor.creative.layer-editor','editor.creative.timeline','edit-time'],
                ['editor.creative.timeline','editor.creative.animation','edit-animation'],
                ['editor.creative.animation','editor.creative.effects','edit-effects'],
                ['editor.creative.effects','editor.creative.audio','edit-audio'],
                ['editor.creative.audio','editor.creative.review-export','review'],
                ['editor.creative.node-graph','editor.creative.inspector','inspect-node'],
                ['editor.creative.cutscene','editor.creative.timeline','edit-sequence'],
                ['editor.creative.material','editor.creative.inspector','inspect-material'],
            ],'quality':editor_quality,
        },
        'comic.narrative.core':{
            'schema':'axm.visual-product/v1','id':'comic.narrative.core','version':1,'name':'Editable comic and visual narrative core','kind':'product','domain':'creative.comic','tags':['comic','narrative','editor','product'],'origin':origin(),'style':'narrative.ink','intent':'an editable visual-story shell where page structure, panel art, dialogue, character continuity, branching story and motion remain separable source state','screens':comic_ids,
            'flow':[
                ['comic.narrative.library','comic.narrative.page-editor','open-story'],
                ['comic.narrative.page-editor','comic.narrative.panel-editor','edit-panel'],
                ['comic.narrative.panel-editor','comic.narrative.dialogue-editor','edit-dialogue'],
                ['comic.narrative.dialogue-editor','comic.narrative.page-editor','return-page'],
                ['comic.narrative.library','comic.narrative.character-sheet','edit-character'],
                ['comic.narrative.library','comic.narrative.scene-graph','edit-story'],
                ['comic.narrative.scene-graph','comic.narrative.storyboard','board-story'],
                ['comic.narrative.storyboard','comic.narrative.motion-timeline','add-motion'],
                ['comic.narrative.motion-timeline','comic.narrative.reader-preview','preview'],
                ['comic.narrative.reader-preview','comic.narrative.export','review-export'],
            ],'quality':comic_quality,
        },
    }
    _merge_unique(products,new_products,'product')

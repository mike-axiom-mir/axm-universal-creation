"""Editable music visualizer, album-art and track-identity foundations."""
from __future__ import annotations
from copy import deepcopy
from typing import Any


def _merge(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap: raise RuntimeError(f"music visual {label} collision: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_music_catalog(namespace: dict[str, Any]) -> None:
    styles=namespace['STYLE_SYSTEMS']; primitives=namespace['PRIMITIVES']
    screens=namespace['SCREEN_TEMPLATES']; products=namespace['PRODUCT_ARCHETYPES']
    screen=namespace['_screen']; origin=namespace['_origin']

    _merge(styles,{'visual.music.resonant':{
        'intent':'track-first visual identity and reactive presentation with exact audio/source/analysis/timing state kept separate from generated visuals',
        'tokens':{'canvas':'#0b0b12','surface':'#171825','surface_raised':'#25263a','text':'#f3f2f6','muted':'#aaa7b7','accent':'#bda0ff','warning':'#e5bc72','danger':'#df737d','line':'#48475d'},
        'shape':{'panel_radius_ratio':0.016,'cut_ratio':0.003,'line_ratio':0.0012},
        'type':{'display_weight':745,'body_weight':500,'metric_scale':1.5,'tracking':0.012},
        'depth':{'layers':8,'shadow':'soft','glass':'restrained'},
        'motion':{'fast_ms':80,'standard_ms':170,'slow_ms':340,'principle':'track and timing truth before reactive flourish'},
    }},'style')

    _merge(primitives,{
        'music-track-source':{'role':'exact track/audio identity with source, version/digest and duration state','states':['loaded','selected','missing','unknown'],'identity_source_digest_duration_required':True},
        'music-analysis':{'role':'derived audio analysis with algorithm/source/version/status explicit','states':['observed','derived','stale','unavailable'],'analysis_source_version_status_required':True},
        'beat-marker':{'role':'timing marker bound to exact track position and derivation/source status','states':['observed','derived','manual','unknown'],'time_source_status_required':True},
        'waveform-source':{'role':'waveform/energy representation bound to exact track and analysis source','states':['ready','selected','stale','missing'],'track_and_analysis_source_required':True},
        'cover-composition':{'role':'editable album/single cover structure with independent art/type/identity layers','states':['draft','selected','ready','overflow'],'layers_must_remain_editable':True},
        'reactive-visual-layer':{'role':'visual layer driven by explicit input mapping from track/analysis state','states':['active','selected','muted','unbound'],'input_mapping_required':True},
        'music-marker-cue':{'role':'named non-lyrical timing/event cue bound to exact track time','states':['active','selected','disabled','unknown'],'name_time_source_required':True},
        'album-variant':{'role':'exact cover/visual variant with base identity, changed properties and intended output','states':['active','alternate','archived','unknown'],'base_delta_target_required':True},
        'track-list-entry':{'role':'ordered track reference with exact identity and sequence position','states':['ready','selected','missing','unknown'],'track_identity_and_order_required':True},
        'music-export-target':{'role':'output target with exact track/variant/aspect/timing/provenance requirements','states':['ready','warning','blocked','exported'],'requirements_must_be_visible':True},
    },'primitive')

    q=['track identity, cover composition, timing markers, audio analysis and reactive visual mappings remain separately editable','reactive visuals never imply beat, waveform or analysis state that has not been observed or explicitly derived','cover artwork and typography remain richer editable source rather than flattened output','track-list ordering and visual variants retain exact identities and targets','derived playback previews and exports never replace source audio or project state']
    def v(c,s,w): return {'compact':c,'standard':s,'wide':w}
    additions={
      'visual.music.project-hub':screen('visual.music.project-hub','Music visual project hub','creative.music','visual.music.resonant','browse tracks, cover/visual variants, analysis availability, sequences and output targets with missing source state visible',v(
        {'header':(.03,.03,.94,.08),'tracks':(.03,.14,.94,.30),'variants':(.03,.47,.45,.38),'targets':(.51,.47,.46,.27),'actions':(.51,.77,.46,.08)},
        {'header':(.02,.03,.96,.075),'tracks':(.02,.14,.22,.82),'variants':(.27,.14,.46,.82),'targets':(.76,.14,.22,.55),'actions':(.76,.72,.22,.14)},
        {'header':(.015,.03,.97,.07),'tracks':(.015,.13,.20,.84),'variants':(.24,.13,.50,.84),'targets':(.77,.13,.215,.57),'actions':(.77,.73,.215,.14)}),tags=['visual','music','project','track'],quality=q),
      'visual.music.cover-editor':screen('visual.music.cover-editor','Album and single cover editor','creative.music','visual.music.resonant','edit artwork, title/artist identity, typography and layer geometry independently across exact variants',v(
        {'toolbar':(.02,.02,.96,.07),'cover':(.20,.11,.60,.56),'layers':(.02,.11,.16,.56),'properties':(.82,.11,.16,.56),'variants':(.02,.70,.45,.28),'checks':(.50,.70,.48,.28)},
        {'toolbar':(.015,.02,.97,.065),'layers':(.015,.105,.16,.76),'cover':(.195,.105,.52,.76),'properties':(.735,.105,.25,.56),'variants':(.735,.69,.12,.17),'checks':(.865,.69,.12,.17)},
        {'toolbar':(.012,.02,.976,.06),'layers':(.012,.10,.14,.78),'cover':(.17,.10,.56,.78),'properties':(.75,.10,.238,.58),'variants':(.75,.71,.112,.17),'checks':(.875,.71,.113,.17)}),tags=['visual','music','cover','editor'],math_hooks={'cover_safe_ratio':[0.04,0.12],'title_area_ratio':[0.12,0.38]},quality=q),
      'visual.music.track-identity':screen('visual.music.track-identity','Track identity and source editor','creative.music','visual.music.resonant','inspect exact track source, digest/version, duration, metadata identity and missing/unknown source state',v(
        {'header':(.03,.03,.94,.08),'identity':(.03,.14,.94,.24),'source':(.03,.41,.45,.45),'metadata':(.51,.41,.46,.34),'actions':(.51,.78,.46,.08)},
        {'header':(.02,.03,.96,.075),'tracks':(.02,.14,.22,.72),'identity':(.27,.14,.46,.72),'source':(.76,.14,.22,.54),'actions':(.76,.71,.22,.15)},
        {'header':(.015,.03,.97,.07),'tracks':(.015,.13,.20,.74),'identity':(.24,.13,.50,.74),'source':(.77,.13,.215,.55),'actions':(.77,.71,.215,.16)}),tags=['visual','music','track','source'],quality=q),
      'visual.music.analysis-waveform':screen('visual.music.analysis-waveform','Waveform and audio-analysis editor','creative.music','visual.music.resonant','inspect waveform/energy/analysis representations with exact track, analysis source/version and availability visible',v(
        {'header':(.03,.03,.94,.08),'waveform':(.03,.14,.94,.32),'analysis':(.03,.49,.58,.38),'details':(.64,.49,.33,.27),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'analysis':(.02,.14,.28,.72),'waveform':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'analysis':(.015,.13,.26,.74),'waveform':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','music','waveform','analysis'],quality=q),
      'visual.music.marker-timing':screen('visual.music.marker-timing','Beat and timing-marker editor','creative.music','visual.music.resonant','edit observed/derived/manual beat and non-lyrical event markers at exact track times with source/status visible',v(
        {'header':(.03,.03,.94,.08),'timeline':(.03,.14,.94,.31),'markers':(.03,.48,.58,.39),'details':(.64,.48,.33,.28),'actions':(.64,.79,.33,.08)},
        {'header':(.02,.03,.96,.075),'markers':(.02,.14,.28,.72),'timeline':(.33,.14,.44,.72),'details':(.80,.14,.18,.54),'actions':(.80,.71,.18,.15)},
        {'header':(.015,.03,.97,.07),'markers':(.015,.13,.26,.74),'timeline':(.305,.13,.47,.74),'details':(.795,.13,.19,.55),'actions':(.795,.71,.19,.16)}),tags=['visual','music','beat','timing'],math_hooks={'marker_spacing_ratio':[0.004,0.04],'timeline_label_ratio':[0.03,0.12]},quality=q),
      'visual.music.reactive-editor':screen('visual.music.reactive-editor','Reactive visual mapping editor','creative.music','visual.music.resonant','bind visual layers to explicit track/analysis inputs and mappings without fabricating unavailable audio state',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.36),'layers':(.03,.53,.45,.34),'mapping':(.51,.53,.46,.25),'actions':(.51,.81,.46,.06)},
        {'header':(.02,.03,.96,.075),'layers':(.02,.14,.23,.72),'preview':(.28,.14,.47,.72),'mapping':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'layers':(.015,.13,.21,.74),'preview':(.26,.13,.49,.74),'mapping':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','music','reactive','visualizer'],quality=q),
      'visual.music.tracklist-sequence':screen('visual.music.tracklist-sequence','Track-list and sequence editor','creative.music','visual.music.resonant','edit exact ordered track references and per-track visual identity without inferring missing source content',v(
        {'header':(.03,.03,.94,.08),'tracks':(.03,.14,.55,.52),'preview':(.61,.14,.36,.36),'details':(.61,.53,.36,.25),'actions':(.03,.69,.55,.18)},
        {'header':(.02,.03,.96,.075),'tracks':(.02,.14,.31,.72),'preview':(.36,.14,.39,.72),'details':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'tracks':(.015,.13,.29,.74),'preview':(.33,.13,.42,.74),'details':(.775,.13,.21,.55),'actions':(.775,.71,.21,.16)}),tags=['visual','music','tracklist','sequence'],quality=q),
      'visual.music.crop-variants':screen('visual.music.crop-variants','Music visual format and crop variants','creative.music','visual.music.resonant','adapt exact cover/visual compositions to square, portrait, landscape and banner outputs without rewriting richer source layers',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.34),'variants':(.03,.51,.55,.34),'safe':(.61,.51,.36,.25),'actions':(.61,.79,.36,.06)},
        {'header':(.02,.03,.96,.075),'variants':(.02,.14,.23,.72),'preview':(.28,.14,.47,.72),'safe':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'variants':(.015,.13,.21,.74),'preview':(.26,.13,.49,.74),'safe':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','music','crop','variant'],quality=q),
      'visual.music.playback-preview':screen('visual.music.playback-preview','Music visual playback preview','creative.music','visual.music.resonant','preview exact track/timing/visual mappings while showing analysis availability and current derived state separately from source',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.40),'timeline':(.03,.57,.58,.30),'state':(.64,.57,.33,.22),'actions':(.64,.82,.33,.05)},
        {'header':(.02,.03,.96,.075),'timeline':(.02,.14,.24,.72),'preview':(.29,.14,.46,.72),'state':(.78,.14,.20,.54),'actions':(.78,.71,.20,.15)},
        {'header':(.015,.03,.97,.07),'timeline':(.015,.13,.22,.74),'preview':(.265,.13,.49,.74),'state':(.78,.13,.205,.55),'actions':(.78,.71,.205,.16)}),tags=['visual','music','playback','preview'],quality=q),
      'visual.music.review-export':screen('visual.music.review-export','Music visual review and export','creative.music','visual.music.resonant','review missing tracks/analysis, invalid mappings, cover overflow, variant targets and output requirements before derived export',v(
        {'header':(.03,.03,.94,.08),'preview':(.03,.14,.94,.30),'checks':(.03,.47,.58,.39),'targets':(.64,.47,.33,.27),'actions':(.64,.77,.33,.09)},
        {'header':(.02,.03,.96,.075),'preview':(.02,.14,.38,.72),'checks':(.43,.14,.34,.72),'targets':(.79,.14,.19,.48),'actions':(.79,.65,.19,.21)},
        {'header':(.015,.03,.97,.07),'preview':(.015,.13,.36,.74),'checks':(.40,.13,.37,.74),'targets':(.79,.13,.195,.49),'actions':(.79,.65,.195,.22)}),tags=['visual','music','review','export'],quality=q),
    }
    _merge(screens,additions,'screen')
    ids=list(additions)
    product={'schema':'axm.visual-product/v1','id':'visual.music.core','version':1,'name':'Editable music visualizer and album-art core','kind':'product','domain':'creative.music','tags':['visual','music','album','visualizer','product'],'origin':origin(),'style':'visual.music.resonant','intent':'source-first music visual identity and reactive editing with exact track, analysis, timing, cover, mapping, sequence and output state','screens':ids,'flow':[
      ['visual.music.project-hub','visual.music.track-identity','inspect-track'],['visual.music.project-hub','visual.music.cover-editor','edit-cover'],['visual.music.track-identity','visual.music.analysis-waveform','inspect-analysis'],['visual.music.analysis-waveform','visual.music.marker-timing','edit-markers'],['visual.music.marker-timing','visual.music.reactive-editor','map-visuals'],['visual.music.project-hub','visual.music.tracklist-sequence','edit-sequence'],['visual.music.cover-editor','visual.music.crop-variants','adapt-formats'],['visual.music.reactive-editor','visual.music.playback-preview','preview'],['visual.music.playback-preview','visual.music.review-export','review-export']], 'quality':q}
    _merge(products,{'visual.music.core':product},'product')

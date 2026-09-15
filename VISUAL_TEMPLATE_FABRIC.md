# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, broadcast/video overlays, evidence-aware diagrams, world-map/lore-atlas editing, branching visual novels, 3D showroom/gallery presentation and music visual/album-art editing. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v13 candidate census

- **156 reusable visual/state primitives**
- **21 coherent style systems**
- **194 responsive screen archetypes**
- **19 whole-product archetypes**
- **213 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Music visual / album-art foundation

`visual.music.core` provides ten source-first surfaces:

- project / music-visual hub;
- album / single cover editor;
- track identity / source inspector;
- waveform / audio-analysis editor;
- beat and non-lyrical timing-marker editor;
- reactive visual mapping editor;
- track-list / sequence editor;
- format / crop variants;
- playback preview;
- review / export.

Its `visual.music.resonant` style is replaceable. Track and analysis truth stays explicit:

- `music-track-source` preserves exact track identity, source/digest and duration;
- `music-analysis` records analysis source/algorithm version/status rather than pretending analysis is source audio;
- `beat-marker` preserves exact time plus observed/derived/manual status;
- `waveform-source` binds the representation to exact track and analysis source;
- `cover-composition` keeps artwork, type and identity layers editable;
- `reactive-visual-layer` requires an explicit input mapping;
- `music-marker-cue` is a named non-lyrical event cue with exact time/source;
- `album-variant` preserves base identity, delta and output target;
- `track-list-entry` preserves exact track identity and sequence order;
- `music-export-target` keeps track/variant/aspect/timing/provenance requirements visible.

A visualizer-looking result is not evidence that beat, waveform, spectral or timing analysis exists. Analysis must be observed or explicitly derived from a declared track source. Unknown, stale and unavailable state stays visible.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.music.core
axm-visual-templates render visual.music.core creations/music --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v13 gate requires:

- exact census: 21 styles / 156 primitives / 194 screens / 19 products;
- all 194 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.music.core`;
- all 213 screen/product definitions install through Sticker Registry;
- exact track identity/source/digest/duration, attributed analysis state, timing-marker provenance, waveform source, cover-layer editability, reactive mappings, variant identity and track-list order remain present;
- prior showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove audio-analysis correctness, musical timing quality, loudness/mastering quality, rights/licensing, renderer fidelity or aesthetic acceptance.

Consuming products must provide real audio/project state. Unknown, missing, stale and unavailable state stays distinguishable. Richer editable source remains authoritative over previews/exports.

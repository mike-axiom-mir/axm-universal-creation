# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, broadcast/video overlays, evidence-aware diagrams, world-map/lore-atlas editing, branching visual novels, 3D showroom/gallery presentation, music visuals/album art and source-bound presentation/explainer systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v14 candidate census

- **166 reusable visual/state primitives**
- **22 coherent style systems**
- **204 responsive screen archetypes**
- **20 whole-product archetypes**
- **224 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Presentation / explainer foundation

`visual.presentation.core` provides ten source-first surfaces:

- project / presentation hub;
- page editor;
- narrative outline / section editor;
- content block editor;
- figure / reusable-artifact editor;
- source / citation / evidence editor;
- emphasis / layout variants;
- speaker notes / review;
- sequence / transition preview;
- export matrix.

Its `visual.presentation.story` style is replaceable. Communication structure remains distinct from source truth:

- `presentation-page` preserves exact page identity, role and order;
- `content-block` keeps type, content/source identity and semantic role explicit;
- `source-footnote` binds exact claims/figures/blocks to source plus evidence status;
- `figure-frame` preserves exact source and caption identity;
- `presentation-section` preserves ordered membership;
- `emphasis-cue` may alter visual emphasis but cannot rewrite source meaning;
- `speaker-note` remains non-rendered note state bound to an exact target/source;
- `embed-binding` preserves exact artifact identity/version/view;
- `presentation-transition` stays derived between exact pages and cannot change page order;
- `presentation-export-target` keeps page range/aspect/assets/source/provenance requirements visible.

A polished explainer is not evidence that its claims are true or adequately sourced. Layout, emphasis, sequence and transitions can shape communication but cannot create evidence or silently alter included source meaning.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.presentation.core
axm-visual-templates render visual.presentation.core creations/presentation --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v14 gate requires:

- exact census: 22 styles / 166 primitives / 204 screens / 20 products;
- all 204 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.presentation.core`;
- all 224 screen/product definitions install through Sticker Registry;
- exact page/order, content/source, citation/evidence, figure identity, section membership, speaker-note, embed identity/version/view, semantic-preserving emphasis and transition-order contracts remain present;
- prior music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove claim truth, source reliability, audience understanding, speaking quality, accessibility compliance or aesthetic acceptance.

Consuming products must provide real content/source state. Unknown, disputed, derived and missing information stays distinguishable. Richer editable source remains authoritative over previews/exports.

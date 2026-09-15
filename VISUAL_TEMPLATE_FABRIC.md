# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, broadcast/video overlays, evidence-aware diagrams, world-map/lore-atlas editing, branching visual novels, 3D showroom/gallery presentation, music visuals/album art, source-bound presentation/explainers and character/creature reference systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v15 candidate census

- **176 reusable visual/state primitives**
- **23 coherent style systems**
- **214 responsive screen archetypes**
- **21 whole-product archetypes**
- **235 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Character / creature reference foundation

`visual.character.core` provides ten source-first production-reference surfaces:

- project / character hub;
- turnaround editor;
- proportions / measurement editor;
- expression sheet editor;
- pose / action reference editor;
- materials / surfaces editor;
- feature / equipment callouts;
- scale / variant editor;
- source / reference board;
- review / export.

Its `visual.character.reference` style is replaceable. Character identity and production truth remain explicit:

- `character-source` preserves exact character/creature identity plus source/version;
- `turnaround-view` binds named views to exact identity and view/camera state;
- `proportion-guide` preserves anchors, values, units, source and precision;
- `expression-state` keeps expression identity/source separate from canonical identity;
- `pose-reference` keeps pose/action state and provenance explicit;
- `character-material` binds exact body/gear parts to exact material sources;
- `character-callout` binds annotations to exact anatomy/gear/feature targets;
- `scale-reference` preserves exact comparison reference, value, unit and source/assumption state;
- `character-variant` preserves base identity, deltas and status;
- `reference-export-target` keeps required views/dimensions/variants/callouts/provenance visible.

A polished reference sheet is not proof that anatomy, proportions, scale, materials, riggability or 3D geometry are correct. Presentation views cannot silently redefine canonical character identity, and inspiration/reference material is not treated as canonical source unless explicitly bound.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.character.core
axm-visual-templates render visual.character.core creations/character --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v15 gate requires:

- exact census: 23 styles / 176 primitives / 214 screens / 21 products;
- all 214 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.character.core`;
- all 235 screen/product definitions install through Sticker Registry;
- exact identity/source/version, view/camera, measurement anchors/value/unit/source, expression and pose provenance, material-part bindings, callout targets, scale references and variant state remain present;
- prior presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove anatomy quality, modelability, rig compatibility, art quality, physical scale correctness or aesthetic acceptance.

Consuming products must provide real character/reference state. Unknown, approximate, derived and missing information stays distinguishable. Richer editable source remains authoritative over previews/exports.

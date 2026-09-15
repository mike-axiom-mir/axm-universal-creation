# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems and environment/level references. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v19 candidate census

- **216 reusable visual/state primitives**
- **27 coherent style systems**
- **254 responsive screen archetypes**
- **25 whole-product archetypes**
- **279 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound environment / level-reference foundation

`visual.environment.core` provides ten production-reference surfaces:

- project / location hub;
- environment identity board;
- zone / layout editor;
- scale / measurement editor;
- modular kit / prop editor;
- material / surface editor;
- lighting / weather / time reference editor;
- traversal / gameplay annotation editor;
- environment / biome variant editor;
- review / export.

Its `visual.environment.reference` style is replaceable. Environment truth remains explicit:

- `environment-source` preserves exact location identity, source, version, digest and scope;
- `environment-zone` preserves exact geometry/source/status;
- `environment-measurement` preserves value, unit, source and precision/assumption state;
- `modular-environment-piece` preserves exact kit source, connection semantics and transform;
- `environment-prop` preserves prop identity/source, placement context and gameplay/visual status;
- `environment-material` preserves exact target/material/source/context;
- `environment-lighting-state` preserves source, time, weather and exposure/state;
- `traversal-reference` binds exact targets to traversal/gameplay type, source and status;
- `environment-variant` preserves exact base, deltas, context and source;
- `environment-export-target` keeps source-coverage, scale, material, prop, lighting and annotation requirements visible.

A beautiful reference board never becomes authoritative level geometry merely because it looks coherent. Physical scale is not inferred solely from perspective imagery. Prop proximity does not establish gameplay linkage. Lighting/weather/biome variants remain explicit state references rather than hidden rewrites of the base environment.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.environment.core
axm-visual-templates render visual.environment.core creations/environment --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v19 gate requires:

- exact census: 27 styles / 216 primitives / 254 screens / 25 products;
- all 254 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.environment.core`;
- all 279 screen/product definitions install through Sticker Registry;
- exact environment identity/source/scope, zone geometry, measurements, modular kit, prop/material context, lighting state, traversal targets and environment variants remain present;
- prior brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove final level geometry, physical scale, collision/navigation, gameplay quality, lighting correctness, performance or aesthetic acceptance.

Consuming projects must supply real environment state. Unknown, estimated, decorative, optional, unavailable and unresolved information stays distinguishable. Richer editable source remains authoritative over reference boards/previews/exports.

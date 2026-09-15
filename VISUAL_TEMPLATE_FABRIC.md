# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems, environment/level references, and VFX/particle authoring. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v20 candidate census

- **226 reusable visual/state primitives**
- **28 coherent style systems**
- **264 responsive screen archetypes**
- **26 whole-product archetypes**
- **290 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound VFX / particle foundation

`visual.vfx.core` provides ten effect-authoring surfaces:

- project / effect hub;
- effect stage;
- emitter-state editor;
- spawn-region editor;
- curves / timing editor;
- particle-module editor;
- layer / composite editor;
- runtime interaction-hook editor;
- reduced-effect / performance editor;
- review / export.

Its `visual.vfx.effect` style is replaceable. Effect truth stays explicit:

- `vfx-source` preserves exact effect identity, source, version and semantic purpose;
- `emitter-state` preserves trigger, lifetime, rate/burst and enabled state;
- `spawn-region` preserves exact shape, source transform, dimensions and distribution;
- `emission-curve` preserves an explicit channel and its time/value state;
- `particle-module` preserves module identity, parameters and order;
- `vfx-layer` preserves exact layer identity, blend/order/depth relationship and source state;
- `vfx-interaction-hook` binds exact subjects/events/responses to source/runtime state;
- `vfx-timing-event` preserves exact timeline markers and semantic purpose;
- `reduced-effect-rule` preserves required semantic feedback while reducing intensity;
- `vfx-export-target` keeps exact source/module/timing/hook/performance/accessibility requirements visible.

A spectacular preview never proves that a collision, hit, damage event, gameplay trigger or other runtime state actually happened. Those semantics require exact source-bound interaction hooks. Spawn previews do not rewrite source spawn geometry, and compositing does not flatten canonical source layers.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.vfx.core
axm-visual-templates render visual.vfx.core creations/vfx --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v20 gate requires:

- exact census: 28 styles / 226 primitives / 264 screens / 26 products;
- all 264 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.vfx.core`;
- all 290 screen/product definitions install through Sticker Registry;
- exact effect identity/source/purpose, emitter, spawn geometry, curves, modules, layers, runtime hooks, timing events and reduced-effect semantic-feedback contracts remain present;
- prior environment/brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove runtime integration, collision or damage correctness, gameplay balance, GPU cost, accessibility acceptance, frame pacing or aesthetic quality.

Consuming products must supply real runtime/gameplay state. Unknown, disabled, conditional and unresolved information stays distinguishishable. Richer editable source remains authoritative over previews/composites/exports.

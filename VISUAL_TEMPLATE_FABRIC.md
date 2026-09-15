# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems, environment/level references, VFX/particle authoring, quest/mission flow systems, HUD theme/skin systems, and lighting/post-process look systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v23 candidate census

- **256 reusable visual/state primitives**
- **31 coherent style systems**
- **294 responsive screen archetypes**
- **29 whole-product archetypes**
- **323 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound lighting / post-process look foundation

`visual.look.core` provides ten look-authoring surfaces:

- project / look hub;
- exposure / tone-map editor;
- color-grade editor;
- fog / atmosphere editor;
- bloom / glare editor;
- post-process layer-stack editor;
- scene / camera binding editor;
- platform / performance variant editor;
- comparison / preview;
- review / export.

Its `visual.look.system` style is replaceable. Presentation state stays explicit:

- `look-source` preserves exact look/preset identity, source, version and owning context;
- `exposure-state` preserves exact value/range, adaptation source and context;
- `tone-map-state` preserves exact operator, parameters, output space and source;
- `color-grade-state` preserves exact transform source, working/output spaces and intensity;
- `fog-atmosphere-state` preserves exact density/range/scattering source and context;
- `bloom-glare-state` preserves exact threshold/intensity/radius/quality and source;
- `postprocess-layer` preserves exact ordered layer identity, parameters, blend, scope and source;
- `scene-look-binding` binds exact scenes/cameras/regions to exact look identities with source/activation state;
- `look-platform-variant` preserves exact base, deltas and platform/performance/accessibility context;
- `look-export-target` keeps exact look/binding/color-space/variant/runtime requirements visible.

A convincing look preview never becomes authoritative world lighting or gameplay state. Grade/post-process transforms do not replace source materials, lights, geometry or environment state. Visual similarity does not bind a look to a scene. Reduced/performance variants must preserve required visibility and state legibility.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.look.core
axm-visual-templates render visual.look.core creations/lighting-look --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v23 gate requires:

- exact census: 31 styles / 256 primitives / 294 screens / 29 products;
- all 294 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.look.core`;
- all 323 screen/product definitions install through Sticker Registry;
- exact look identity/exposure/tone/grade/fog/bloom/layer/scene-binding/platform contracts remain present;
- prior HUD/mission/VFX/environment/brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove physical lighting correctness, calibrated color output, accessibility acceptance, GPU cost, target-engine parity or aesthetic quality.

Consuming products must supply real world/scene/camera state and output-space context. Unknown, unsupported, disabled, reduced and unbound state stays distinguishishable. Richer editable source remains authoritative over look previews/exports.

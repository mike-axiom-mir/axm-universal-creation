# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems, environment/level references, VFX/particle authoring, quest/mission flow systems, HUD theme/skin systems, lighting/post-process look systems, and camera/shot reference systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v24 candidate census

- **266 reusable visual/state primitives**
- **32 coherent style systems**
- **304 responsive screen archetypes**
- **30 whole-product archetypes**
- **334 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound camera / shot reference foundation

`visual.camera.core` provides ten camera-authoring surfaces:

- project / shot hub;
- camera rig editor;
- target / framing editor;
- lens / projection / FOV editor;
- movement / collision / occlusion constraint editor;
- camera transition editor;
- runtime binding editor;
- platform / accessibility variant editor;
- shot comparison preview;
- review / export.

Its `visual.camera.system` style is replaceable. Camera state stays explicit:

- `camera-source` preserves exact camera/shot identity, source, version and owner/context;
- `camera-rig` preserves exact parent/pivot/transform/source and ownership;
- `camera-target` preserves exact target/anchor/source and tracking status;
- `lens-state` preserves exact projection, lens/FOV/aperture/focus values and source units;
- `framing-guide` preserves exact viewport/aspect/target guide and source;
- `camera-transition` preserves exact from/to camera states, trigger, duration/curve and ownership;
- `camera-constraint` preserves exact subject/rule/source/status for motion, collision and occlusion;
- `camera-runtime-binding` binds exact gameplay/cinematic states to exact rigs/shots with source/authority;
- `camera-platform-variant` preserves exact base, deltas and platform/input/accessibility context;
- `camera-export-target` keeps exact rig/lens/target/transition/binding requirements visible.

Preview framing never moves world objects or rewrites authoritative transforms. A cinematic-looking shot never implies gameplay camera ownership or input authority. Lens/FOV values are not inferred solely from appearance. Visual similarity does not create a target or runtime binding. Platform/accessibility variants must preserve required targeting, orientation and semantic feedback.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.camera.core
axm-visual-templates render visual.camera.core creations/camera --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v24 gate requires:

- exact census: 32 styles / 266 primitives / 304 screens / 30 products;
- all 304 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.camera.core`;
- all 334 screen/product definitions install through Sticker Registry;
- exact camera identity/rig/target/lens/framing/transition/constraint/runtime-authority/platform contracts remain present;
- prior lighting/HUD/mission/VFX/environment/brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove camera feel, motion comfort, collision behavior, target-engine parity, gameplay suitability or aesthetic quality.

Consuming products must supply real world, scene, camera and runtime ownership state. Unknown, lost, disabled, advisory, reduced and unbound state stays distinguishable. Richer editable source remains authoritative over camera previews/exports.

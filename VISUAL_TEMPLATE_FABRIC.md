# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration and source-bound UI motion. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v17 candidate census

- **196 reusable visual/state primitives**
- **25 coherent style systems**
- **234 responsive screen archetypes**
- **23 whole-product archetypes**
- **257 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound UI motion foundation

`visual.motion.core` provides ten state-first motion surfaces:

- project / motion-system hub;
- state-transition editor;
- focus / navigation motion editor;
- spatial / shared-element continuity editor;
- timing / easing editor;
- interruption / recovery editor;
- progress / loading motion editor;
- reduced-motion variant editor;
- trigger matrix;
- review / export.

Its `visual.motion.system` style is replaceable. The contract is semantic state before animation:

- `motion-state` keeps exact source/target identities;
- `transition-edge-state` keeps trigger, source, target, duration and completion semantics explicit;
- `timing-curve` preserves explicit duration/easing parameters;
- `focus-motion-path` preserves exact focus identities and semantic order;
- `spatial-anchor-transition` requires exact source/target anchor IDs;
- `interruption-recovery` keeps cancellation and rollback/recovery state explicit;
- `progress-motion-state` binds motion to observed progress/status, never inferred completion;
- `reduced-motion-rule` preserves the same semantic result while reducing unnecessary motion;
- `motion-trigger` binds transitions to exact events/inputs/state changes;
- `motion-export-target` keeps runtime/accessibility requirements visible.

Animation is never evidence that state changed. Animation completion cannot manufacture task completion. Visual proximity cannot define focus order or shared-element identity. Reduced-motion is first-class and must preserve the same destination/meaning.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.motion.core
axm-visual-templates render visual.motion.core creations/motion --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v17 gate requires:

- exact census: 25 styles / 196 primitives / 234 screens / 23 products;
- all 234 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.motion.core`;
- all 257 screen/product definitions install through Sticker Registry;
- exact state edge, trigger, timing, focus order, anchor identity, interruption/recovery, progress source and reduced-motion parity contracts remain present;
- prior configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove perceptual motion quality, vestibular comfort, target-framework behavior, frame pacing, input latency or accessibility acceptance.

Consuming products must provide real state transitions and runtime evidence. Unknown, interrupted, stalled and incomplete state stays distinguishable. Richer editable source remains authoritative over previews/exports.

# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems, environment/level references, VFX/particle authoring, quest/mission flow systems, and HUD theme/skin systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v22 candidate census

- **246 reusable visual/state primitives**
- **30 coherent style systems**
- **284 responsive screen archetypes**
- **28 whole-product archetypes**
- **312 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound HUD theme / skin foundation

`visual.hud.core` provides ten HUD-authoring surfaces:

- project / HUD hub;
- component library;
- layout / anchor editor;
- data-binding editor;
- readability editor;
- alerts / feedback editor;
- platform / input variant editor;
- theme / skin editor;
- comparison / preview;
- review / export.

Its `visual.hud.system` style is replaceable. HUD truth stays explicit:

- `hud-source` preserves exact HUD family identity, source, version and owning context;
- `hud-component` preserves exact component identity, role, source and semantic purpose;
- `hud-layout-anchor` preserves exact component region/viewport constraints;
- `hud-data-binding` binds exact gameplay/system subject + field to source/freshness/fallback state;
- `hud-readability-rule` preserves exact target, viewing/platform/input context, threshold and evidence source;
- `hud-safe-region` preserves exact viewport/platform/source and safe margins;
- `hud-alert-state` preserves exact semantic source, severity, feedback channels and acknowledgement state;
- `hud-platform-variant` preserves exact base, deltas, device/input context and availability;
- `hud-theme-variant` preserves exact base theme plus token/component deltas;
- `hud-export-target` keeps exact component/binding/layout/readability/platform/provenance requirements visible.

Screen position never creates a data binding. A meter looking full never proves the underlying value is full. Icon or color alone cannot carry critical gameplay meaning. Theme/skin changes do not rewrite gameplay state, and platform variants must preserve required semantic feedback and readability.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.hud.core
axm-visual-templates render visual.hud.core creations/hud --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v22 gate requires:

- exact census: 30 styles / 246 primitives / 284 screens / 28 products;
- all 284 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.hud.core`;
- all 312 screen/product definitions install through Sticker Registry;
- exact HUD identity/component/layout/data/readability/safe-region/alert/platform/theme contracts remain present;
- prior mission/VFX/environment/brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove gameplay correctness, real-device readability, accessibility acceptance, input ergonomics, target-engine rendering or aesthetic quality.

Consuming products must supply real gameplay/system data and device context. Unknown, stale, missing, hidden, constrained and unreadable state stays distinguishable. Richer editable source remains authoritative over previews/skins/exports.

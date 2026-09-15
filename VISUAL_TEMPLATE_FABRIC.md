# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic/broadcast overlays, diagrams, atlas/map editing, branching narrative, 3D showroom, music, presentation/explainers, character reference, equipment configuration, source-bound UI motion, brand/identity systems, environment/level references, VFX/particle authoring, and quest/mission flow systems. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v21 candidate census

- **236 reusable visual/state primitives**
- **29 coherent style systems**
- **274 responsive screen archetypes**
- **27 whole-product archetypes**
- **301 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Source-bound quest / mission-flow foundation

`visual.mission.core` provides ten mission-authoring surfaces:

- project / mission hub;
- objective editor;
- prerequisite / condition editor;
- branch / flow graph;
- world / map binding editor;
- rewards / outcomes editor;
- failure / retry / recovery editor;
- runtime-state / flag inspector;
- mission variant editor;
- review / export.

Its `visual.mission.flow` style is replaceable. Mission truth stays explicit:

- `mission-source` preserves exact mission/quest identity, source, version and owning context;
- `objective-state` preserves exact objective ID/type/status and completion source;
- `mission-condition` preserves exact subject/operator/value/source and evaluation state;
- `mission-edge` preserves exact from/to identities, transition type and condition references;
- `mission-world-reference` binds exact map/zone/POI/entity targets to source/status;
- `mission-reward-reference` preserves exact reward/outcome source, amount/state and delivery status;
- `mission-failure-recovery` preserves exact failure condition, retry/recovery/checkpoint destination and consequences;
- `mission-runtime-flag` preserves exact flag identity/value/source/freshness;
- `mission-variant` preserves exact base mission, deltas, context and availability;
- `mission-export-target` keeps objective/condition/branch/reference/reward/recovery requirements visible.

A flow line never proves a branch is reachable. Objective presentation never proves completion. Map proximity never creates a mission binding, and reward presentation never proves delivery. Runtime flags, failure consequences and recovery destinations stay explicit source state.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.mission.core
axm-visual-templates render visual.mission.core creations/mission --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v21 gate requires:

- exact census: 29 styles / 236 primitives / 274 screens / 27 products;
- all 274 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.mission.core`;
- all 301 screen/product definitions install through Sticker Registry;
- exact mission identity/source/context, objective completion source, conditions, branch edges, world references, reward delivery state, failure/recovery, runtime flags and variants remain present;
- prior VFX/environment/brand/motion/configurator/character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove mission balance, narrative quality, runtime branch reachability, reward correctness, map correctness or gameplay acceptance.

Consuming products must supply real mission/runtime state. Unknown, unresolved, blocked, stale, failed and undelivered information stays distinguishable. Richer editable source remains authoritative over graphs/previews/exports.

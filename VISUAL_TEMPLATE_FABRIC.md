# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, broadcast/video overlays, evidence-aware diagrams, world-map/lore-atlas editing, branching visual novels, 3D showroom/gallery presentation, music visuals/album art, source-bound presentation/explainers, character/creature references, and equipment/vehicle/weapon configuration. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v16 candidate census

- **186 reusable visual/state primitives**
- **24 coherent style systems**
- **224 responsive screen archetypes**
- **22 whole-product archetypes**
- **246 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Equipment / vehicle / weapon configurator foundation

`visual.configurator.core` provides ten source-first configuration surfaces:

- project / configurator hub;
- configurable object stage;
- attachment socket editor;
- exploded component editor;
- configuration stat editor;
- variant / material editor;
- compatibility rule editor;
- configuration comparison;
- preset / loadout editor;
- review / export.

Its `visual.configurator.precision` style is replaceable. Configuration truth remains explicit:

- `configurable-source` preserves exact object identity, source and version;
- `attachment-socket` preserves socket identity/type/category/status;
- `component-part` preserves exact part source, parent socket and source transform;
- `compatibility-rule` preserves exact subject/target/rule/result/status;
- `config-stat-field` keeps value, unit, source and configuration context;
- `configuration-state` preserves base identity, attachment set, variants and digest;
- `exploded-view-state` uses derived presentation offsets that never replace source transforms;
- `config-material-variant` preserves exact target, variant source and availability;
- `config-annotation` binds exact targets to content/source/status;
- `configurator-export-target` keeps output requirements visible.

A component looking like it fits a socket is never treated as compatibility evidence. Unknown compatibility remains unknown, conditional rules remain explicit, and invalid configurations stay visible. Derived exploded, comparison and export views cannot silently modify the authoritative configuration.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.configurator.core
axm-visual-templates render visual.configurator.core creations/configurator --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v16 gate requires:

- exact census: 24 styles / 186 primitives / 224 screens / 22 products;
- all 224 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.configurator.core`;
- all 246 screen/product definitions install through Sticker Registry;
- exact object identity/source/version, socket identity/type/status, component parent/source transform, compatibility rule state, stat value/unit/source/context, configuration digest, variant availability and derived exploded-view boundaries remain present;
- prior character/presentation/music/showroom/visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove real-world attachment fit, mechanical compatibility, gameplay balance, stat correctness, physical dimensions, target-engine rendering or aesthetic acceptance.

Consuming products must provide real configuration state. Unknown, conditional, unavailable and invalid information stays distinguishable. Richer editable source remains authoritative over previews/exports.

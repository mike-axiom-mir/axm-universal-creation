# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, video/broadcast overlays, evidence-aware diagrams, world-map/lore-atlas editing, branching visual novels and 3D showroom/gallery presentation. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v12 candidate census

- **146 reusable visual/state primitives**
- **20 coherent style systems**
- **184 responsive screen archetypes**
- **18 whole-product archetypes**
- **202 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Product foundations

The catalog retains the merged game, creative-editor, comic, AXM-system, key-art, card/deck, cinematic, broadcast, diagram, atlas and visual-novel products, and adds `visual.showroom.core`.

## 3D showroom / object gallery foundation

`visual.showroom.core` provides ten source-first presentation surfaces:

- project / showroom hub;
- hero object stage;
- orbit / camera editor;
- material / paint editor;
- object variant editor;
- annotation / callout editor;
- side-by-side comparison;
- detail / inspection view;
- turntable / showcase-motion editor;
- review / export.

Its `visual.showroom.studio` style is replaceable. Object truth remains explicit:

- `showroom-object` preserves exact source asset identity/version;
- `orbit-rig` preserves exact target, pivot and orbit range;
- `camera-preset` keeps projection, lens and transform explicit;
- `material-slot` binds an exact object part to an exact material source;
- `variant-option` preserves exact variant identity, properties and availability/source state;
- `object-annotation` binds content to an exact object/component/local anchor;
- `comparison-object` preserves exact object/variant references and comparable fields;
- `turntable-state` remains derived presentation state around an exact target;
- `measurement-callout` preserves value, unit and source;
- `showroom-export-target` keeps output requirements visible.

A convincing 3D preview does not prove geometry, scale, materials, measurements, availability or rendering quality. Camera, turntable and showcase motion remain presentation state rather than object truth.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.showroom.core
axm-visual-templates render visual.showroom.core creations/showroom --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v12 gate requires:

- exact census: 20 styles / 146 primitives / 184 screens / 18 products;
- all 184 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.showroom.core`;
- all 202 screen/product definitions install through Sticker Registry;
- exact object/version, orbit target/pivot/range, camera state, material bindings, variant identity/availability, annotation anchors, comparison references, turntable state and measurement value/unit/source remain present;
- prior visual-novel/atlas/diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove renderer fidelity, 3D geometry correctness, physical scale, material realism, lighting quality, product availability or aesthetic acceptance.

Consuming products must provide real source/project state. Unknown, missing, unavailable and incompatible state stays distinguishable. Richer editable source remains authoritative over previews/exports.

# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, video/broadcast overlays, evidence-aware diagrams and world-map/lore-atlas editing. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v10 candidate census

- **126 reusable visual/state primitives**
- **18 coherent style systems**
- **164 responsive screen archetypes**
- **16 whole-product archetypes**
- **180 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Product foundations

The catalog retains the merged game, creative-editor, comic, AXM-system, key-art, card/deck, cinematic, broadcast and diagram products, and adds `visual.atlas.core`.

## World-map / lore-atlas foundation

`visual.atlas.core` provides ten source-first surfaces:

- project / atlas hub;
- world-map editor;
- region / boundary editor;
- route / path editor;
- POI / lore-reference editor;
- layer editor;
- timeline / state-overlay editor;
- coordinate / spatial-source editor;
- review / comparison;
- export matrix.

Its `visual.atlas.cartographic` style is replaceable. Spatial and narrative truth remains explicit:

- `map-region` requires exact geometry/source state;
- `route-path` requires exact endpoints plus known/planned/blocked/unknown status;
- `poi-marker` keeps identity and location source/status explicit;
- `map-layer` preserves independent layer provenance;
- `time-slice` preserves period plus current/historical/projected/unknown status;
- `lore-reference` binds exact target and source/status;
- `boundary-line` requires boundary type, source and uncertainty state;
- `map-coordinate` keeps coordinate system, source and precision explicit;
- `state-overlay` stays bound to exact source and time slice;
- `atlas-export-target` keeps extent/layer/label/provenance requirements visible.

**Unknown coordinates, routes or boundaries are never invented merely to make a map look complete.** Projected state remains distinguishable from observed/current state, and visual boundaries do not become factual borders without declared type/source.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition. Definitions use exact id/version/digest identity; there is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.atlas.core
axm-visual-templates render visual.atlas.core creations/atlas --width 1920 --height 1080
```

Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v10 gate requires:

- exact census: 18 styles / 126 primitives / 164 screens / 16 products;
- all 164 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.atlas.core`;
- all 180 screen/product definitions install through Sticker Registry;
- exact region geometry/source, route endpoints/status, POI location source, layer provenance, time-slice status, lore target/source, boundary type/source, coordinate precision/source and overlay source/time remain present;
- prior diagram/broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural/editability contracts only. It does **not** prove coordinate accuracy, route existence, border/geopolitical claims, chronology correctness, lore truth, source reliability or aesthetic acceptance.

Consuming products must provide real source state. Unknown, disputed, approximate, derived and projected information stays distinguishable. Richer editable source remains authoritative over previews/exports.

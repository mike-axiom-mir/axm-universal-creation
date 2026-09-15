# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. Explicit extension packs now cover games/product plumbing, creative editors, comics, AXM system surfaces, key art, cards/decks, cinematic overlays, video/broadcast overlays and evidence-aware diagrams. Sticker Fabric remains the immutable/versioned registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v9 candidate census

- **116 reusable visual/state primitives**
- **17 coherent style systems**
- **154 responsive screen archetypes**
- **15 whole-product archetypes**
- **169 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Major product foundations

- `game.racing.performance`, `game.racing.full`, `game.coop.action`, `game.rts.command`, `game.system.shell`, `game.shared.core`
- `editor.creative.core`
- `comic.narrative.core`
- `axm.system.shell`
- `visual.keyart.core`
- `visual.cards.core`
- `visual.cinematic.core`
- `visual.broadcast.core`
- `visual.diagram.core`

The previously merged packs preserve exact source/edit state: game ownership/progression/runtime status, editor layers/timelines/graphs, comic page/panel/dialogue state, AXM source/evidence/recovery state, key-art subject/type/crop state, card rules/face/back/deck/print state, cinematic text/timing/credits state, and broadcast source/freshness/delivery/output state.

## Evidence-aware diagrams / infographics

`visual.diagram.core` provides ten source-first diagram surfaces:

- project / diagram hub;
- canvas editor;
- node editor;
- relationship editor;
- evidence / data binding editor;
- annotation / callout editor;
- legend / semantic style editor;
- layout variants;
- review / truth check;
- export matrix.

Its `visual.diagram.evidence` style is replaceable. The semantic contract matters more than appearance:

- `diagram-node` keeps exact entity/concept/state identity;
- `relationship-edge` requires exact endpoints, relation type and direction;
- `evidence-reference` keeps source plus observed/derived/claimed/missing status;
- `data-field` keeps value, unit, source and period/freshness explicit;
- `annotation-pin` requires an exact target;
- `legend-entry` cannot depend on color alone;
- `group-boundary` keeps membership/criteria explicit;
- `layout-guide` cannot change semantic relationships;
- `callout-card` keeps content and evidence status separate;
- `diagram-export-target` keeps output requirements explicit.

**Visual proximity is never allowed to imply an undeclared relationship.** Alternate layouts/routing may improve readability but cannot add, remove or retype semantic edges.

## Registry and identity

Every built-in screen/product can be wrapped as an immutable Sticker definition:

```python
from axm_stickers import Registry
from axm_uc.visual_templates import install_builtins

with Registry('stickers.sqlite') as registry:
    pins = install_builtins(registry)
```

Definitions use exact id/version/digest identity. There is no floating `latest`, silent upgrade or automatic canon.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.diagram.core
axm-visual-templates render visual.diagram.core creations/diagram --width 1920 --height 1080
```

A product preview contains structural SVGs plus exact resolved source metadata and a local gallery. Preview/export remains derived inspection output, never authoritative source.

## Evidence gate

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v9 gate requires:

- exact census: 17 styles / 116 primitives / 154 screens / 15 products;
- all 154 screens stay within six representative viewport shapes;
- exact product screen order and flows resolve across those viewports;
- parseable galleries for all prior proof products plus `visual.diagram.core`;
- all 169 screen/product definitions install through Sticker Registry;
- exact nodes, relationship endpoints/types, evidence/source status, value/unit/source/period, target-bound annotations, non-color legends and explicit group membership remain present;
- layout variants cannot rewrite semantic relationships;
- prior broadcast/cinematic/card/key-art/comic/game/AXM source boundaries remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker-slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural and semantic/editability contracts only. It does **not** prove that a diagrammed relationship is true, causal, sufficiently evidenced or statistically valid; it does not prove numerical data correctness, source reliability, accessibility compliance or aesthetic acceptance.

Consuming products must provide real source/evidence state. Missing, disputed, derived and claimed information stays distinguishable. Richer editable source remains authoritative over previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

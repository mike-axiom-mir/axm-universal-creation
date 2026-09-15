# Visual Template / Archetype Fabric

Universal Creation has a deterministic layer between low-level format scaffolds and finished products: **known visual archetypes**.

A visual archetype is not finished art and it is not canon. It is a versioned, inspectable answer to a recurring structural problem: where important information belongs, what should dominate, how a layout adapts, what visual language holds it together, what reusable asset sockets exist, and which quality constraints should survive variation.

This extends, rather than replaces, the existing systems:

- `format_templates.py` still owns physical/screen canvases and simple semantic rectangles;
- deterministic project templates still instantiate exact files;
- Sticker Fabric remains the immutable/versioned local registry and reusable-part system;
- visual archetypes supply stronger screen and whole-product foundations those systems can consume;
- separate mathematical work can enrich declared ratios/ranges through `math_hooks` without silently replacing template identity.

## One composed catalog

The public module is `axm_uc.visual_templates`.

Its retained deterministic kernel lives in `visual_template_core.py`. Genre/product growth lives in `visual_template_growth.py`. Shared professional game-product surfaces live in `visual_template_game_systems.py`. Creative-editor and editable-narrative surfaces live in `visual_template_creative_narrative.py`. The public facade composes those dictionaries, rejects collisions, validates the resulting catalog, then exposes the same v1 schemas and functions.

This is intentionally **one catalog**, not competing template systems and not multiple registries.

Current deterministic catalog in the v2 lane:

- **47 reusable primitives**;
- **10 coherent style systems**;
- **79 responsive screen archetypes**;
- **8 whole-product archetypes**.

## Layers

1. **Primitives** — reusable state/interaction contracts such as panel, navigation, player seat, loading state, layer row, timeline track, graph node, panel frame, speech bubble and reading-order marker.
2. **Style systems** — coherent surface, type, depth, shape and motion language. These are semantic visual systems, not one-off color themes.
3. **Screen archetypes** — normalized responsive region geometry, slots, math hooks, intent and quality constraints.
4. **Whole-product archetypes** — exact screen sets plus explicit flow edges and product-level coherence rules.

Primitives describe reusable behavior/state expectations; they are not hidden widget implementations. A target product can realize them differently while preserving the contract that matters.

## Game foundations

The merged v1 foundation remains intact:

- `game.racing.performance` — compact six-screen racing shell;
- `game.racing.full` — 19-screen professional racing foundation;
- `game.coop.action` — reusable co-op action shell;
- `game.rts.command` — persistent-world RTS command shell;
- `game.system.shell` — 18 optional genre-neutral professional product surfaces.

Those foundations include truthful loading/recovery, explicit player-seat ownership, split-screen support, controller remapping, save/load, accessibility, privacy/consent, language/localization and other reusable product plumbing. Optional network/account surfaces remain capabilities, not requirements for local/offline games.

## Creative editor foundation

`editor.creative.core` is a 12-screen professional editing foundation:

- project hub;
- asset browser;
- layer/composition editor;
- timeline editor;
- node graph;
- deep inspector;
- animation workspace;
- effects workspace;
- cutscene editor;
- material editor;
- audio editor;
- review/export.

Its `creative.workbench` visual language prioritizes stable editing context and dense inspectable state. New primitives include `layer-row`, `timeline-track`, `keyframe`, `node-card`, `socket-port`, `inspector-field` and `asset-tile`.

The contract is deliberately source-first: selected state, modified state, graph typing, timeline position, provenance and richer editable source remain visible. A derived preview/export never becomes authoritative merely because it is easier to render.

## Editable comics and visual narrative

`comic.narrative.core` is a 10-screen visual-story foundation:

- story/project library;
- page editor;
- panel editor;
- dialogue/lettering editor;
- character reference sheet;
- scene graph;
- storyboard;
- motion-comic timeline;
- reader preview;
- review/export.

The important boundary is **editability**, not just appearance. Page geometry, panel geometry, source art, crops/depth, dialogue text, bubble shape/tail, captions, character references, reading order, branching story beats and motion timing remain distinct semantic state.

Reusable narrative primitives include `panel-frame`, `panel-gutter`, `speech-bubble`, `caption-box`, `storyboard-card`, `reading-order-marker`, `character-reference-card` and `story-beat-link`.

The `narrative.ink` style gives the pack a coherent editorial starting language, but a comic may replace that style without replacing its structural/editability contract.

## Responsive geometry

Screen regions are stored in normalized `0..1` coordinates. `resolve()` turns them into exact pixels for a supplied viewport. Current game, creative-editor and comic screens ship all three variants:

- `compact`: width below 900 px or portrait/narrow ratio below 1.15;
- `wide`: aspect ratio at least 1.9;
- `standard`: everything between.

Callers can request a declared variant explicitly. Unknown explicit variants fail; they do not silently fall back.

The current geometry is a known structural foundation. Mathematical growth can later replace or enrich ratio/range derivation through `math_hooks` without changing product/template identity or silently rewriting source state.

## Sticker Fabric / registry bridge

Every built-in screen or whole-product archetype can be wrapped as an ordinary immutable Sticker definition:

```python
from axm_stickers import Registry
from axm_uc.visual_templates import install_builtins

with Registry('stickers.sqlite') as registry:
    pins = install_builtins(registry)
```

The wrapper keeps the exact visual template inside the sticker recipe. Existing Sticker Registry guarantees still apply: exact id/version/digest pins, no floating `latest`, no silent upgrades, explicit registration and portable offline state.

The v2 catalog contains 79 screens + 8 products, so explicit built-in installation currently registers **87 exact visual definitions**.

The bridge does **not** turn every Sticker into UI. It lets visual foundations use the same proven immutable local registry when desired.

Screen archetypes may declare Sticker slots. `bind_sticker_slots()` accepts only explicit `{id, version, digest}` pins and validates socket/tag requirements. It never searches for or chooses a replacement on the caller's behalf.

## CLI

List the composed catalog:

```sh
axm-visual-templates catalog
```

Inspect exact foundations:

```sh
axm-visual-templates show game.racing.full
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
```

Write local structural previews:

```sh
axm-visual-templates render game.racing.full creations/racing-foundation --width 1920 --height 1080
axm-visual-templates render editor.creative.core creations/creative-editor --width 1920 --height 1080
axm-visual-templates render comic.narrative.core creations/comic-editor --width 1920 --height 1080
```

A product preview contains one SVG per screen, `product.json` with exact resolved structure, and a local HTML gallery. A screen preview contains `screen.svg`, `template.json` and HTML.

## Evidence

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The deterministic suite now checks:

- exact composed catalog counts: 10 styles / 47 primitives / 79 screens / 8 products;
- all 79 screens across six representative viewport shapes/sizes;
- compact/standard/wide coverage for game, creative-editor and comic screens;
- strict unknown-variant rejection;
- exact product screen ordering and flow references;
- professional racing and shared game-system coverage;
- 12-screen creative editor coverage;
- 10-screen editable comic/narrative coverage;
- separation of comic page/panel/dialogue/scene/motion surfaces;
- explicit speech text/tail separation and visible reading-order conflicts;
- SVG parseability;
- actual Sticker Registry installation of all 87 screens/products;
- exact Sticker slot pins and invalid-geometry rejection.

The proof generates galleries for racing, co-op, RTS, shared game systems, the creative editor and editable comic system, plus a portrait mobile reference. It resolves all six proof products at 640×360, 1080×1920, 1280×720, 1920×1080, 2560×1080 and 3840×2160 and rejects any region that escapes its viewport.

## Truth boundary

Current claims are intentionally narrow:

- these are known structural foundations, **not** professional-quality guarantees by themselves;
- generated SVG is an offline structural preview, not target-engine rendering;
- creative/editor templates do not prove actual authoring behavior, undo/redo correctness, file compatibility or export fidelity;
- comic templates do not prove drawing quality, lettering quality, reading experience, localization or aesthetic acceptance;
- preserving separate semantic regions is structural editability evidence, not proof that a finished GUI exposes every operation perfectly;
- having accessibility/privacy surfaces does not establish accessibility or legal compliance;
- loading, recovery and availability contracts forbid fake state, but the real product still has to connect them to observed runtime evidence;
- color/style tokens express coherent intent but do not replace final art direction;
- the machine may mutate, combine, replace or ignore a template when evidence and user intent support doing so;
- no template becomes canon merely because it is built in or registered.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

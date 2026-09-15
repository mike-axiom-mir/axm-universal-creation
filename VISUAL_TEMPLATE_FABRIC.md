# Visual Template / Archetype Fabric

Universal Creation has a deterministic layer between low-level format scaffolds and finished products: **known visual archetypes**.

A visual archetype is not finished art and it is not canon. It is a versioned, inspectable answer to a recurring structural problem: where important information belongs, what should dominate, how a layout adapts, what visual language holds it together, what reusable asset sockets exist, and which quality constraints should survive variation.

This extends, rather than replaces, the existing systems:

- `format_templates.py` still owns physical/screen canvases and simple semantic rectangles;
- deterministic project templates still instantiate exact files;
- Sticker Fabric remains the immutable/versioned local registry and reusable-part system;
- visual archetypes supply stronger screen and whole-product foundations those systems can consume;
- separate mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## One composed catalog

The public module is `axm_uc.visual_templates`.

Its retained deterministic kernel lives in `visual_template_core.py`. Genre/product growth lives in `visual_template_growth.py`. Shared professional game-product surfaces live in `visual_template_game_systems.py`. Creative-editor and editable-narrative surfaces live in `visual_template_creative_narrative.py`. AXM-native machine/system surfaces live in `visual_template_axm_system.py`. The public facade composes those dictionaries, rejects collisions, validates the resulting catalog, then exposes the same v1 schemas and functions.

This is intentionally **one catalog**, not competing template systems and not multiple registries.

Current deterministic catalog in the v3 lane:

- **57 reusable primitives**;
- **11 coherent style systems**;
- **91 responsive screen archetypes**;
- **9 whole-product archetypes**.

## Layers

1. **Primitives** — reusable state/interaction contracts such as player seat, loading state, layer row, graph node, panel frame, speech bubble, truth state, capability card and recovery choice.
2. **Style systems** — coherent surface, type, depth, shape and motion language. These are semantic visual systems, not one-off color themes.
3. **Screen archetypes** — normalized responsive region geometry, slots, math hooks, intent and quality constraints.
4. **Whole-product archetypes** — exact screen sets plus explicit flow edges and product-level coherence rules.

Primitives describe reusable behavior/state expectations; they are not hidden widget implementations. A target product can realize them differently while preserving the contract that matters.

## Game foundations

The merged game foundations remain intact:

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

The contract is source-first: selected state, modified state, graph typing, timeline position, provenance and richer editable source remain visible. A derived preview/export never becomes authoritative merely because it is easier to render.

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

## AXM system / monolith shell

`axm.system.shell` is a 12-screen AXM-native machine/product foundation:

- home/current-state overview;
- registry browser;
- capability browser;
- monolith/cartridge loader;
- machine-state inspector;
- evidence/truth review;
- workflow/creation flow;
- specialist perspectives;
- machine workfloor;
- snapshots/continuity;
- settings/policy;
- recovery/repair.

Its `axm.machine.glass` style is a layered metallic/glass starting language, not canonical identity. The structural rule is progressive detail: ordinary use sees a calm summary first, while source, version, evidence, dependency and recovery detail remains available when needed.

Reusable AXM primitives include `truth-state`, `capability-card`, `registry-entry`, `evidence-chip`, `state-diff`, `cartridge-card`, `specialist-card`, `workfloor-lane`, `snapshot-entry` and `recovery-choice`.

These templates represent machine state; they do not manufacture it. A real product must connect status, package compatibility, capability availability, snapshots and recovery outcomes to actual observed runtime state.

## Responsive geometry

Screen regions are stored in normalized `0..1` coordinates. `resolve()` turns them into exact pixels for a supplied viewport. Current game, creative-editor, comic and AXM-system screens ship all three variants:

- `compact`: width below 900 px or portrait/narrow ratio below 1.15;
- `wide`: aspect ratio at least 1.9;
- `standard`: everything between.

Callers can request a declared variant explicitly. Unknown explicit variants fail; they do not silently fall back.

The current geometry is a known structural foundation. Mathematical growth can later replace or enrich ratio/range derivation through `math_hooks` without changing product/template identity or rewriting source state.

## Sticker Fabric / registry bridge

Every built-in screen or whole-product archetype can be wrapped as an ordinary immutable Sticker definition:

```python
from axm_stickers import Registry
from axm_uc.visual_templates import install_builtins

with Registry('stickers.sqlite') as registry:
    pins = install_builtins(registry)
```

The wrapper keeps the exact visual template inside the sticker recipe. Existing Sticker Registry guarantees still apply: exact id/version/digest pins, no floating `latest`, no silent upgrades, explicit registration and portable offline state.

The v3 catalog contains 91 screens + 9 products, so explicit built-in installation currently registers **100 exact visual definitions**.

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
axm-visual-templates show axm.system.shell
```

Write local structural previews:

```sh
axm-visual-templates render game.racing.full creations/racing-foundation --width 1920 --height 1080
axm-visual-templates render editor.creative.core creations/creative-editor --width 1920 --height 1080
axm-visual-templates render comic.narrative.core creations/comic-editor --width 1920 --height 1080
axm-visual-templates render axm.system.shell creations/axm-system --width 1920 --height 1080
```

A product preview contains one SVG per screen, `product.json` with exact resolved structure, and a local HTML gallery. A screen preview contains `screen.svg`, `template.json` and HTML.

## Evidence

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The deterministic suite now checks:

- exact composed catalog counts: 11 styles / 57 primitives / 91 screens / 9 products;
- all 91 screens across six representative viewport shapes/sizes;
- compact/standard/wide coverage for game, editor, comic and AXM-system screens;
- exact product screen ordering and flow references;
- retained racing/game-system/editor/comic depth;
- 12-screen AXM system-shell coverage;
- source/version/evidence/recovery contracts in AXM primitives;
- SVG parseability;
- actual Sticker Registry installation of all 100 screens/products;
- exact Sticker slot pins and invalid-geometry rejection.

The proof generates galleries for racing, co-op, RTS, shared game systems, the creative editor, editable comic system and AXM system shell, plus a portrait mobile reference. It resolves all seven proof products at 640×360, 1080×1920, 1280×720, 1920×1080, 2560×1080 and 3840×2160 and rejects any region that escapes its viewport.

## Truth boundary

Current claims are intentionally narrow:

- these are known structural foundations, **not** professional-quality guarantees by themselves;
- generated SVG is an offline structural preview, not target-engine rendering;
- creative/editor templates do not prove actual authoring behavior, undo/redo correctness, file compatibility or export fidelity;
- comic templates do not prove drawing quality, lettering quality, reading experience, localization or aesthetic acceptance;
- AXM system templates do not prove package mounting, machine execution, capability availability, snapshot restore or recovery success;
- preserving separate semantic regions is structural evidence, not proof that a finished GUI exposes every operation perfectly;
- having accessibility/privacy surfaces does not establish accessibility or legal compliance;
- loading, recovery and availability contracts require real products to connect displayed state to actual evidence;
- color/style tokens express coherent intent but do not replace final art direction;
- the machine may mutate, combine, replace or ignore a template when evidence and user intent support doing so;
- no template becomes canon merely because it is built in or registered.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

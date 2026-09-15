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

Its retained deterministic kernel lives in `visual_template_core.py`. Genre/product growth lives in `visual_template_growth.py`. Shared professional game-product surfaces live in `visual_template_game_systems.py`. The public facade composes those dictionaries, rejects collisions, validates the resulting catalog, then exposes the same v1 schemas and functions.

This is intentionally **one catalog**, not competing template systems and not multiple registries.

Current deterministic catalog:

- **32 reusable primitives**;
- **8 coherent style systems**;
- **57 responsive screen archetypes**;
- **6 whole-product archetypes**.

## Layers

1. **Primitives** — reusable state/interaction contracts such as panel, navigation, player seat, selection card, stat comparison, slider row, countdown, loading state, recovery banner, keybind row, save slot and confirmation summary.
2. **Style systems** — coherent surface, type, depth, shape and motion language. These are semantic visual systems, not one-off color themes.
3. **Screen archetypes** — normalized responsive region geometry, slots, math hooks, intent and quality constraints.
4. **Whole-product archetypes** — exact screen sets plus explicit flow edges and product-level coherence rules.

Primitives describe reusable behavior/state expectations; they are not hidden widget implementations. A target product can realize them differently while preserving the contract that matters.

## Racing foundations

Two racing products are retained deliberately:

- `game.racing.performance` — the smaller six-screen racing shell: lobby, event selection, garage, driving HUD, pause and results.
- `game.racing.full` — the professional 19-screen foundation intended for a complete game shell.

`game.racing.full` covers:

- home / main menu;
- co-op lobby;
- event selection;
- vehicle selection;
- garage;
- detailed reversible tuning + telemetry;
- livery / appearance editing;
- pre-race briefing and grid;
- truthful loading/readiness;
- start countdown;
- primary driving HUD;
- split-screen HUD with explicit seat identity;
- pause;
- disconnect / reconnection / recovery;
- results and rewards;
- replay / photo review;
- season / progression;
- settings;
- accessibility.

The product carries one shared `racing.performance` language and explicit flow edges between those surfaces. Driving views reduce chrome relative to setup views. Loading and recovery templates explicitly forbid pretending an unobserved state succeeded.

This is deliberately useful for AXM Wreckline-like work without hard-coding one game's identity into Universal Creation. A game can inherit the structure and mutate its art direction, slots, geometry, content or whole screens.

## Reusable co-op game foundation

`game.coop.action` supplies a generic co-op action shell rather than copying the racing product:

- home;
- party lobby;
- loadout;
- action HUD;
- pause/session overlay;
- mission results;
- settings with local-vs-party scope.

The reusable `player-seat` contract includes empty, joining, ready, not-ready, disconnected and AI-seat states. Seat ownership is explicit. Human and machine players can therefore use the same player-facing presentation contract instead of receiving hidden privileged paths.

## Reusable RTS foundation

`game.rts.command` supplies a macro-scale command shell for persistent RTS-style worlds:

- world-entry lobby;
- persistent world map;
- command HUD;
- production/build planner;
- research/technology;
- diplomacy;
- pause/strategic overview;
- battle/world outcome.

Its quality contract keeps the strategic map/world as the referent while command panels change. Selection, ownership, resources, production and strategic consequences retain stable anchors rather than turning the experience into unrelated dashboards.

## Shared professional game-system shell

`game.system.shell` is a genre-neutral library of **18 optional product surfaces**. It exists so every new AXM game does not have to rediscover the non-gameplay half of being a professional product.

It contains:

- player profile;
- party / seat management;
- matchmaking queue;
- server/session browser;
- controller/input remapping;
- display/graphics settings;
- audio settings;
- shared accessibility settings;
- save/load slots;
- achievements/challenges;
- tutorial/training;
- photo mode;
- credits/licenses;
- error/recovery;
- notifications;
- text chat/channels;
- privacy/consent;
- language/localization selection.

These screens are **capabilities, not assumptions**. A local/offline game does not suddenly require accounts, matchmaking, servers or chat because templates exist for them. A game selects only the surfaces relevant to its real product state.

Truth-sensitive contracts include:

- fake loading/progress state is forbidden;
- server/session availability must be observed;
- pending/failed chat delivery cannot look delivered;
- corrupt/incompatible saves remain visible as such rather than being silently rewritten;
- input conflicts must be shown before replacement;
- display changes can expose a bounded revert path;
- consent is not preselected merely to improve conversion and revocation remains discoverable;
- errors say what failed, what remains safe and what recovery evidence exists.

## Responsive geometry

Screen regions are stored in normalized `0..1` coordinates. `resolve()` turns them into exact pixels for a supplied viewport. Game screens currently ship all three variants:

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
axm-visual-templates show game.coop.action
axm-visual-templates show game.rts.command
axm-visual-templates show game.system.shell
```

Write local structural previews:

```sh
axm-visual-templates render game.racing.full creations/racing-foundation --width 1920 --height 1080
axm-visual-templates render game.coop.action creations/coop-foundation --width 1280 --height 720
axm-visual-templates render game.rts.command creations/rts-foundation --width 1920 --height 1080
axm-visual-templates render game.system.shell creations/game-system-foundation --width 1280 --height 720
```

A product preview contains one SVG per screen, `product.json` with exact resolved structure, and a local HTML gallery. A screen preview contains `screen.svg`, `template.json` and HTML.

Explicitly install all built-ins into a Sticker Registry:

```sh
axm-visual-templates install-registry creations/stickers.sqlite
```

## Evidence

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The deterministic test suite checks:

- exact composed catalog counts;
- all 57 screens across six representative viewport shapes/sizes;
- compact/standard/wide coverage for game screens;
- strict unknown-variant rejection;
- exact product screen ordering and flow references;
- the 19-screen professional racing shell and key loading/recovery transitions;
- the 18-screen shared system shell including consent/recovery/input/persistence surfaces;
- racing, co-op, RTS and shared-system product resolution;
- SVG parseability;
- actual Sticker Registry installation of all 63 screens/products;
- exact Sticker slot pins;
- rejection of invalid geometry;
- mature reusable primitives including truthful loading, observed availability and explicit player-seat ownership.

The proof generates galleries for `game.racing.full`, `game.coop.action`, `game.rts.command` and `game.system.shell`, plus a portrait mobile foundation. It resolves all four game products at 640×360, 1080×1920, 1280×720, 1920×1080, 2560×1080 and 3840×2160 and rejects any region that escapes its viewport.

## Truth boundary

Current claims are intentionally narrow:

- these are known structural foundations, **not** professional-quality guarantees by themselves;
- generated SVG is an offline structural preview, not target-engine rendering;
- no gameplay, controller feel, interaction timing, localization, font rendering, network behavior, save reliability, runtime performance, accessibility audit or aesthetic acceptance is proven by the template resolver;
- having an accessibility template does not mean a finished product is accessible; it prevents that product surface from being absent by default;
- having privacy/consent templates does not establish legal compliance; it preserves a non-manipulative explicit-choice starting structure;
- color/style tokens express coherent intent but do not replace final art direction;
- loading, recovery and availability contracts forbid fake state, but the real product still has to connect them to observed runtime evidence;
- the machine may mutate, combine, replace or ignore a template when evidence and user intent support doing so;
- no template becomes canon merely because it is built in or registered.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth and room for better solutions.

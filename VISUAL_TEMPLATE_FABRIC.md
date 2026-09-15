# Visual Template / Archetype Fabric

Universal Creation now has a deterministic layer between low-level format scaffolds and finished products: **known visual archetypes**.

A visual archetype is not finished art and it is not canon. It is a versioned, inspectable answer to a recurring structural problem: where important information belongs, what should dominate, how a layout adapts, what visual language holds it together, what reusable asset sockets exist, and which quality constraints should survive variation.

This extends, rather than replaces, the existing systems:

- `format_templates.py` still owns physical/screen canvases and simple semantic rectangles;
- deterministic project templates still instantiate exact files;
- Sticker Fabric remains the immutable/versioned local registry and reusable-part system;
- the new visual fabric supplies stronger screen and whole-product foundations that those systems can consume.

## Layers

The built-in catalog starts with four layers:

1. **Primitives** — panel, primary action, metric, progress, navigation, list row, viewport and toast behavior contracts.
2. **Style systems** — coherent surface, type, depth, shape and motion language. These are semantic visual systems, not one-off color themes.
3. **Screen archetypes** — normalized responsive region geometry, slots, math hooks, intent and quality constraints.
4. **Whole-product archetypes** — exact screen sets plus explicit flow edges and product-level coherence rules.

The first pack contains 11 screen archetypes, 5 style systems, 8 primitives and 2 whole-product archetypes.

## Racing foundation

`game.racing.performance` is the first full game product foundation. It currently composes:

- co-op lobby;
- event selection;
- garage / vehicle setup;
- performance racing HUD;
- pause overlay;
- results / rewards.

The product carries one shared `racing.performance` visual language and explicit transitions between screens. The HUD has compact, standard and wide variants and keeps the driving world primary while speed, route, position, vehicle state and immediate events remain readable.

This is deliberately useful for AXM Wreckline-like work without hard-coding one game's identity into Universal Creation. A game can inherit this structure and replace its style, slots, geometry or whole screens.

## Responsive geometry

Screen regions are stored in normalized `0..1` coordinates. `resolve()` turns them into exact pixels for a supplied viewport. The default deterministic variant selector uses:

- `compact`: width below 900 px or portrait/narrow ratio below 1.15;
- `wide`: aspect ratio at least 1.9;
- `standard`: everything between.

Callers can request a declared variant explicitly. Unknown explicit variants fail; they do not silently fall back.

The current geometry is a known structural foundation. The separate mathematical growth lane can replace or enrich these ratio/range rules through the exposed `math_hooks` without changing the product/template identity contract.

## Sticker Fabric / registry bridge

Every built-in screen or whole-product archetype can be wrapped as an ordinary immutable Sticker definition:

```python
from axm_stickers import Registry
from axm_uc.visual_templates import install_builtins

with Registry('stickers.sqlite') as registry:
    pins = install_builtins(registry)
```

The wrapper keeps the exact visual template inside the sticker recipe. Existing Sticker Registry guarantees therefore still apply: exact id/version/digest pins, no floating `latest`, no silent upgrades, explicit registration, portable offline state.

The bridge does **not** change all Sticker semantics into UI semantics. It simply lets visual foundations use the same proven immutable local registry when desired.

Screen archetypes may also declare Sticker slots. `bind_sticker_slots()` accepts only explicit `{id, version, digest}` pins and validates socket/tag requirements. It never searches for or chooses a replacement on the caller's behalf.

## CLI

List the catalog:

```sh
axm-visual-templates catalog
```

Inspect one exact foundation:

```sh
axm-visual-templates show game.racing.hud.performance
```

Write a local structural preview:

```sh
axm-visual-templates render game.racing.performance creations/racing-foundation --width 1920 --height 1080
```

The product preview contains one SVG per screen, `product.json` with exact resolved structure, and a local HTML gallery. A screen preview contains `screen.svg`, `template.json` and HTML.

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

Tests cover catalog validation, deterministic copy-safe resolution, viewport bounds across six representative shapes/sizes, strict breakpoint handling, whole-product references/flows, SVG parseability, actual Sticker Registry installation, exact slot pins and rejection of bad geometry.

The proof writes a full racing-product gallery and a portrait mobile foundation, and checks every racing screen at 640×360, 1080×1920, 1280×720, 1920×1080, 2560×1080 and 3840×2160.

## Truth boundary

Current claims are intentionally narrow:

- these are known structural foundations, not professional-quality guarantees;
- generated SVG is an offline structural preview, not target-engine rendering;
- no gameplay, controller flow, interaction timing, text localization, font rendering, performance, accessibility audit or aesthetic acceptance is proven by the template resolver;
- color/style tokens express coherent intent but do not replace final art direction;
- the machine may mutate, combine, replace or ignore a template when evidence and user intent support doing so;
- no template becomes canon merely because it is built in or registered.

The goal is to stop every creation from beginning at zero while preserving agency and exact source truth.

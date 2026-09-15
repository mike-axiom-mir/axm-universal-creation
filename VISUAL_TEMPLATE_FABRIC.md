# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. The retained kernel is `visual_template_core.py`; explicit extension packs add game/product, creative/narrative, AXM-system, shared-game, key-art and card/deck knowledge before the facade validates one composed v1 catalog. Sticker Fabric remains the immutable/versioned local registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v6 candidate census

- **86 reusable visual/state primitives**
- **14 coherent style systems**
- **124 responsive screen archetypes**
- **12 whole-product archetypes**
- **136 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major game/editor/comic/AXM/key-art/card family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Product foundations accumulated so far

### Games

- `game.racing.performance` — compact racing shell.
- `game.racing.full` — professional 19-screen racing product.
- `game.coop.action` — reusable co-op action shell.
- `game.rts.command` — persistent-world RTS command shell.
- `game.system.shell` — optional genre-neutral product plumbing.
- `game.shared.core` — inventory, progression, missions/maps/objectives, upgrades, lore, revive/boss/spectator state, session summaries and challenges.

Optional online/account surfaces remain capabilities, not requirements for local/offline products.

### Creative/editor

`editor.creative.core` provides twelve coordinated source-first editing surfaces spanning assets, layers, timeline, graph, inspector, animation, effects, cutscenes, materials, audio and review/export.

### Comics / visual narrative

`comic.narrative.core` provides ten editable story surfaces. Page geometry, panels, source art, dialogue, bubble body/tail, captions, references, reading order, branching beats and motion timing remain separate semantic state.

### AXM system / monolith shell

`axm.system.shell` provides twelve AXM-native surfaces for registry, capabilities, portable packages, state, evidence, workflow, specialists, workfloor, snapshots, settings and recovery. Human-facing views use progressive detail while source/version/evidence and recovery consequences remain inspectable.

### Editable key art / poster / cover composition

`visual.keyart.core` provides ten source-first composition surfaces for project setup, composition, subject staging, typography, lighting/effects, atmosphere, crop variants, alternate compositions, review and export. Subject source, depth, masks, type, credits, lighting passes, crop-safe frames, exact variants and export targets remain separate editable state.

### Editable cards / decks / collectibles

`visual.cards.core` provides eleven source-first card and deck surfaces:

- project / set hub;
- card face editor;
- card back editor;
- artwork editor;
- text / statistics editor;
- ability / rules editor;
- rarity / style editor;
- finish / foil editor;
- deck builder;
- print / sheet layout;
- review / export.

Its `visual.cards.collectible` style is a replaceable starting language. The important contract is editability and exact state:

- `card-frame` preserves face/back geometry;
- `artwork-window` keeps source art and crop separate;
- `stat-block` preserves label/value pairs;
- `ability-row` retains exact rules text;
- `rarity-badge` cannot rely on color alone;
- `cost-symbol` keeps resource type and value explicit;
- `card-state` exposes ownership/deck/playability state;
- `deck-slot` points to an exact card reference;
- `foil-pass` cannot replace base artwork;
- `print-safe-frame` cannot rewrite source layout.

Digital and physical outputs derive from richer card source state. Print trim/bleed/safe guides and foil/effect layers remain output/editing aids rather than canonical replacements.

## Registry and identity

Every built-in screen/product can be wrapped as an ordinary immutable Sticker definition:

```python
from axm_stickers import Registry
from axm_uc.visual_templates import install_builtins

with Registry('stickers.sqlite') as registry:
    pins = install_builtins(registry)
```

Definitions use exact id/version/digest identity. There is no floating `latest`, silent upgrade or automatic canon. Screen Sticker slots accept exact pins only and validate declared socket/tag requirements.

## CLI

```sh
axm-visual-templates catalog
axm-visual-templates show visual.cards.core
axm-visual-templates show visual.keyart.core
axm-visual-templates show game.shared.core
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
axm-visual-templates show axm.system.shell
axm-visual-templates render visual.cards.core creations/cards --width 1920 --height 1080
```

A product preview contains one structural SVG per screen plus exact `product.json` and local HTML gallery. Preview/export is derived inspection output, not authoritative source.

## Evidence gate

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v6 candidate gate requires:

- exact census: 14 styles / 86 primitives / 124 screens / 12 products;
- all 124 screens inside six representative viewport shapes;
- exact product screen order and flow across those viewports;
- parseable galleries for all prior proof products plus editable cards/decks;
- all 136 screen/product definitions install through the existing immutable Sticker Registry;
- face/back geometry, artwork/crop separation, exact rules text, non-color rarity cues, explicit costs/card state, exact deck references, non-authoritative foil and non-mutating print guides remain present;
- prior source boundaries from key art, comics, gameplay and AXM state remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural knowledge and editability/state vocabulary only. It does **not** prove target-engine rendering, card-game balance, rules correctness, illustration quality, typography quality, foil rendering, print production/color management, gameplay feel, authoring ergonomics or aesthetic acceptance.

Templates must be connected to actual runtime/project state by the consuming product. Unknown or unavailable state stays visibly unknown rather than being invented. Richer editable source remains authoritative over lossy previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

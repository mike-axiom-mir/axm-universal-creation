# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. The retained kernel is `visual_template_core.py`; explicit extension packs add game/product, creative/narrative, AXM-system, shared-game and key-art knowledge before the facade validates one composed v1 catalog. Sticker Fabric remains the immutable/versioned local registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v5 candidate census

- **76 reusable visual/state primitives**
- **13 coherent style systems**
- **113 responsive screen archetypes**
- **11 whole-product archetypes**
- **124 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major game/editor/comic/AXM/key-art family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

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

`visual.keyart.core` provides ten source-first composition surfaces:

- project hub;
- composition editor;
- hero subject staging;
- title / typography editor;
- lighting / effects editor;
- background / atmosphere editor;
- crop / format variants;
- exact composition variant board;
- review / comparison;
- export matrix.

Its `visual.keyart.cinematic` style supplies a high-impact starting visual language while keeping structure replaceable.

The key-art pack deliberately preserves edit handles:

- `hero-subject` retains source, mask, crop/depth and transform state;
- `depth-layer` keeps foreground/midground/background ordering explicit;
- `focal-mask` guides attention without replacing source art;
- `title-lockup` keeps text and layout separate;
- `credit-block` retains exact credits/legal/byline content;
- `lighting-pass` remains a derived contribution instead of source authority;
- `crop-safe-frame` cannot rewrite source geometry;
- `variant-card` pins alternate composition identity;
- `export-target` exposes dimensions/crop/quality/file expectations.

`math_hooks` on composition and crop screens expose focal/safe-area ranges for later mathematical derivation without replacing template identity.

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
axm-visual-templates show visual.keyart.core
axm-visual-templates show game.shared.core
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
axm-visual-templates show axm.system.shell
axm-visual-templates render visual.keyart.core creations/keyart --width 1920 --height 1080
```

A product preview contains one structural SVG per screen plus exact `product.json` and local HTML gallery. Preview/export is derived inspection output, not authoritative source.

## Evidence gate

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v5 candidate gate requires:

- exact census: 13 styles / 76 primitives / 113 screens / 11 products;
- all 113 screens inside six representative viewport shapes;
- exact product screen order and flow across those viewports;
- parseable galleries for all prior proof products plus editable key art;
- all 124 screen/product definitions install through the existing immutable Sticker Registry;
- subject source/transform, depth ordering, focal masks, title separation, non-authoritative effects, crop-safe source preservation, exact variant identity and explicit export-target requirements remain present;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural knowledge and editability/state vocabulary only. It does **not** prove target-engine rendering, illustration quality, typography quality, lighting quality, print production, store-platform compliance, gameplay feel, authoring ergonomics or aesthetic acceptance.

Templates must be connected to actual runtime/project state by the consuming product. Unknown or unavailable state stays visibly unknown rather than being invented. Richer editable source remains authoritative over lossy previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

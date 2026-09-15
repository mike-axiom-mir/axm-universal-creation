# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. The retained kernel is `visual_template_core.py`; explicit extension packs add game/product, creative/narrative, AXM-system, shared-game, key-art, card/deck and cinematic knowledge before the facade validates one composed v1 catalog. Sticker Fabric remains the immutable/versioned local registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v7 candidate census

- **96 reusable visual/state primitives**
- **15 coherent style systems**
- **134 responsive screen archetypes**
- **13 whole-product archetypes**
- **147 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major game/editor/comic/AXM/key-art/card/cinematic family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

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

`visual.cards.core` provides eleven source-first surfaces for face/back design, artwork, exact text/stats/rules, rarity/style, foil/finish, deck construction, print-sheet layout and review/export. Artwork/crop, rules text, costs, card/deck state, finish layers and print guides remain distinct source/derived state.

### Editable cinematic titles / credits / overlays

`visual.cinematic.core` provides ten source-first cinematic identity and timed-overlay surfaces:

- project / sequence hub;
- title card editor;
- chapter / intertitle editor;
- lower-third editor;
- subtitle / caption editor;
- credits editor;
- timed overlay timeline;
- transition editor;
- aspect / safe-area variants;
- review / export.

Its `visual.cinematic.motion` style is replaceable. The structural contract is exact content and timing:

- `title-card` keeps text, layout and timing separate;
- `lower-third` exposes content, anchor and duration;
- `subtitle-cue` preserves exact text plus start/end timing;
- `credit-line` preserves exact content and order;
- `time-cue` requires explicit start/end;
- `safe-zone` cannot rewrite source layout;
- `transition-cue` stays derived between exact source states;
- `chapter-marker` carries exact label and timeline position;
- `overlay-track` keeps overlaps/conflicts visible;
- `logo-lockup` keeps source identity and transform separate.

Landscape, portrait, square and vertical variants may adapt layout without silently changing exact words, timing or richer source composition.

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
axm-visual-templates show visual.cinematic.core
axm-visual-templates show visual.cards.core
axm-visual-templates show visual.keyart.core
axm-visual-templates show game.shared.core
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
axm-visual-templates show axm.system.shell
axm-visual-templates render visual.cinematic.core creations/cinematic --width 1920 --height 1080
```

A product preview contains one structural SVG per screen plus exact `product.json` and local HTML gallery. Preview/export is derived inspection output, not authoritative source.

## Evidence gate

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v7 candidate gate requires:

- exact census: 15 styles / 96 primitives / 134 screens / 13 products;
- all 134 screens inside six representative viewport shapes;
- exact product screen order and flow across those viewports;
- parseable galleries for all prior proof products plus cinematic titles/overlays;
- all 147 screen/product definitions install through the existing immutable Sticker Registry;
- exact title/lower-third/subtitle/credit content and timing contracts remain present;
- overlay conflicts remain visible, safe areas cannot rewrite source layout, and transitions cannot replace source states;
- prior source boundaries from cards, key art, comics, gameplay and AXM state remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural knowledge and editability/state vocabulary only. It does **not** prove target-engine rendering, typography quality, subtitle reading speed, credit correctness, transition/motion quality, video encoding, platform compliance, gameplay feel, authoring ergonomics or aesthetic acceptance.

Templates must be connected to actual runtime/project state by the consuming product. Unknown or unavailable state stays visibly unknown rather than being invented. Richer editable source remains authoritative over lossy previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. The retained kernel is `visual_template_core.py`; explicit extension packs add game/product, creative/narrative, AXM-system, shared-game, key-art, card/deck, cinematic and broadcast/video-overlay knowledge before the facade validates one composed v1 catalog. Sticker Fabric remains the immutable/versioned local registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v8 candidate census

- **106 reusable visual/state primitives**
- **16 coherent style systems**
- **144 responsive screen archetypes**
- **14 whole-product archetypes**
- **158 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major game/editor/comic/AXM/key-art/card/cinematic/broadcast family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

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

`visual.cinematic.core` provides ten source-first cinematic identity and timed-overlay surfaces. Exact text, layout, timing, credit order, safe areas and transitions remain independent editable state; transitions stay derived between exact source states.

### Editable video / program / stream overlays

`visual.broadcast.core` provides ten source-first presentation surfaces:

- project / scene-set hub;
- scene layout editor;
- source router and health view;
- camera/source frame editor;
- score/status field editor;
- alert / notification editor;
- chat / event-feed editor;
- scene set and switching editor;
- format / safe-area variants;
- review / output.

Its `visual.broadcast.modular` style is replaceable. The important contract is that convincing presentation never substitutes for source truth:

- `source-window` keeps exact source identity visible;
- `camera-slot` keeps source identity separate from crop/framing;
- `status-field` carries value, source and freshness;
- `alert-cue` forbids showing unobserved success;
- `chat-panel` keeps delivery/offline/error state explicit;
- `scene-state` preserves exact preview/live scene identity;
- `overlay-zone` keeps overlap conflicts visible;
- `identity-panel` keeps source asset and transform separate;
- `transition-state` requires exact from/to scene identities;
- `output-monitor` requires observed output-target state.

Landscape, portrait, square and vertical variants may adapt composition while preserving exact source bindings and current scene state.

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
axm-visual-templates show visual.broadcast.core
axm-visual-templates show visual.cinematic.core
axm-visual-templates show visual.cards.core
axm-visual-templates show visual.keyart.core
axm-visual-templates show game.shared.core
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
axm-visual-templates show axm.system.shell
axm-visual-templates render visual.broadcast.core creations/broadcast --width 1920 --height 1080
```

A product preview contains one structural SVG per screen plus exact `product.json` and local HTML gallery. Preview/export is derived inspection output, not authoritative source.

## Evidence gate

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v8 candidate gate requires:

- exact census: 16 styles / 106 primitives / 144 screens / 14 products;
- all 144 screens inside six representative viewport shapes;
- exact product screen order and flow across those viewports;
- parseable galleries for all prior proof products plus video/stream overlays;
- all 158 screen/product definitions install through the existing immutable Sticker Registry;
- exact source identity, crop/source separation, status freshness, delivery state, scene identity and output-state contracts remain present;
- alerts cannot imply unobserved success, overlay conflicts remain visible and transitions keep exact from/to scene identity;
- prior source boundaries from cinematic, cards, key art, comics, gameplay and AXM state remain intact;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural knowledge and editability/state vocabulary only. It does **not** prove live capture, score correctness, chat/message delivery, encoder or output health, network latency, streaming-platform integration, privacy compliance, target-engine rendering, gameplay feel, authoring ergonomics or aesthetic acceptance.

Templates must be connected to actual runtime/project state by the consuming product. Unknown or unavailable state stays visibly unknown rather than being invented. A convincing preview is never evidence that a live source exists. Richer editable source remains authoritative over lossy previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

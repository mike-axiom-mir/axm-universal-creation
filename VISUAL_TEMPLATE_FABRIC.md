# Visual Template / Archetype Fabric

Universal Creation contains one deterministic library of **known visual archetypes** between low-level format scaffolds and finished products. Templates are editable structural starting points, not finished art and not automatic canon.

The public module remains `axm_uc.visual_templates`. The retained kernel is `visual_template_core.py`; explicit extension packs add game/product, creative/narrative, AXM-system and shared-game knowledge before the facade validates one composed v1 catalog. Sticker Fabric remains the immutable/versioned local registry bridge. Mathematical work can enrich declared ratios/ranges through `math_hooks` without replacing template identity.

## Current v4 candidate census

- **67 reusable visual/state primitives**
- **12 coherent style systems**
- **103 responsive screen archetypes**
- **10 whole-product archetypes**
- **113 exact screen/product definitions** when explicitly installed into Sticker Registry

Every major game/editor/comic/AXM family provides compact, standard and wide normalized layouts. Unknown requested variants fail rather than silently falling back.

## Product foundations accumulated so far

### Games

- `game.racing.performance` — compact six-screen racing shell.
- `game.racing.full` — 19-screen professional racing product including selection, tuning, livery, loading, countdown, primary/split HUDs, recovery, replay, progression, settings and accessibility.
- `game.coop.action` — reusable co-op action shell.
- `game.rts.command` — persistent-world RTS command shell.
- `game.system.shell` — 18 optional genre-neutral product surfaces such as profiles, party/seats, matchmaking/server browsing, controls, graphics/audio, saves, achievements, tutorial, photo mode, recovery, chat, privacy/consent and language.
- `game.shared.core` — 12 reusable gameplay-system surfaces for inventory, progression, mission/map/objectives, upgrades, lore, revive/boss/spectator state, session summaries and challenges.

Optional online/account surfaces remain capabilities, not requirements for local/offline products.

### Creative/editor

`editor.creative.core` provides twelve coordinated editing surfaces: project hub, assets, layers, timeline, node graph, inspector, animation, effects, cutscenes, materials, audio and review/export. Rich editable source stays authoritative over previews and exports.

### Comics / visual narrative

`comic.narrative.core` provides ten editable story surfaces: project library, page editor, panel editor, dialogue/lettering editor, character sheet, scene graph, storyboard, motion timeline, reader preview and export. Page geometry, panels, source art, dialogue, bubble body/tail, captions, references, reading order, branching beats and motion timing remain separate semantic state.

### AXM system / monolith shell

`axm.system.shell` provides twelve AXM-native surfaces: home, registry, capability browser, cartridge loader, machine state, evidence review, workflow, specialists, workfloor, snapshots, settings and recovery. The `axm.machine.glass` visual language is a starting style, not canonical AXM identity. Human-facing views use progressive detail while source/version/evidence and recovery consequences remain inspectable.

## Shared gameplay-system pack

`game.shared.core` closes common near-term gaps without rebuilding product plumbing that already exists elsewhere.

Its screens are:

- `game.shared.inventory`
- `game.shared.skill-tree`
- `game.shared.mission-briefing`
- `game.shared.world-map`
- `game.shared.objective-log`
- `game.shared.upgrade-shop`
- `game.shared.codex`
- `game.shared.revive-overlay`
- `game.shared.boss-encounter-hud`
- `game.shared.spectator`
- `game.shared.end-session-summary`
- `game.shared.challenge-board`

The pack adds state-aware primitives instead of only rectangles:

- `inventory-slot` — quantity/ownership/equipped/compatibility state;
- `skill-node` — prerequisites, cost and unlock state;
- `objective-row` — objective lifecycle and progress;
- `shop-offer` — cost plus resulting ownership state;
- `codex-entry` — discovered versus unknown knowledge;
- `revive-state` — actor/time/revival lifecycle;
- `boss-phase` — phase/vulnerability state with non-color cues;
- `spectator-seat` — viewed target/control context;
- `challenge-card` — progress, expiry and reward;
- `session-stat` — metric plus personal/team scope.

The style `game.shared.adventure` is deliberately neutral enough to be replaced by a specific game's art direction while retaining these semantic contracts.

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
axm-visual-templates show game.shared.core
axm-visual-templates show editor.creative.core
axm-visual-templates show comic.narrative.core
axm-visual-templates show axm.system.shell
axm-visual-templates render game.shared.core creations/game-shared --width 1920 --height 1080
```

A product preview contains one structural SVG per screen plus exact `product.json` and local HTML gallery. Preview is derived inspection output, not authoritative source.

## Evidence gate

Run:

```sh
python -m unittest discover -s tests -p 'test_visual_templates.py' -v
python tools/visual_template_proof.py /new/output/path
```

The v4 candidate gate requires:

- exact census: 12 styles / 67 primitives / 103 screens / 10 products;
- all 103 screens inside six representative viewport shapes;
- exact product screen order and flow across those viewports;
- parseable galleries for racing, co-op, RTS, product systems, shared gameplay, creative editor, editable comics and AXM system shell;
- all 113 screen/product definitions install through the existing immutable Sticker Registry;
- explicit state contracts for inventory ownership, skill prerequisites/costs, unknown codex content, revive actor/time, boss phases and challenge progress/rewards;
- copy safety, strict variant rejection, invalid-geometry rejection and exact Sticker slot binding remain intact.

## Truth boundary

Current evidence proves deterministic structural knowledge and state vocabulary only. It does **not** prove target-engine rendering, gameplay feel, economy balance, progression fairness, encounter timing, network behavior, save reliability, authoring ergonomics, drawing quality, package mounting, recovery success, accessibility compliance or aesthetic acceptance.

Templates must be connected to actual runtime/project state by the consuming product. Unknown or unavailable state stays visibly unknown rather than being invented. Richer editable source remains authoritative over lossy previews/exports. Templates may be mutated, combined, replaced or ignored when better evidence and product intent support another solution.

The goal is to stop creation from beginning at zero while preserving agency, exact source truth, deep editability and room for better solutions.

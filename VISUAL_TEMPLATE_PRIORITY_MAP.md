# AXM Visual Template Expansion Priority Map

Status: post-v1 growth plan after merged PR #94.

The visual-template fabric should grow where Universal Creation is most likely to reuse the knowledge soon. The order below is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Priority 1 — Creative editor core

Product target: `editor.creative.core`

Purpose: give AXM reusable professional editing surfaces so generated work remains editable instead of collapsing into flat final outputs.

Planned screen IDs:

- `editor.creative.project-hub`
- `editor.creative.asset-browser`
- `editor.creative.layer-editor`
- `editor.creative.timeline`
- `editor.creative.node-graph`
- `editor.creative.inspector`
- `editor.creative.animation`
- `editor.creative.effects`
- `editor.creative.cutscene`
- `editor.creative.material`
- `editor.creative.audio`
- `editor.creative.review-export`

Reusable primitive targets:

- `layer-row`
- `timeline-track`
- `keyframe`
- `node-card`
- `socket-port`
- `inspector-field`
- `asset-tile`

Primary style target: `creative.workbench`.

## Priority 2 — Editable comics and visual narrative

Product target: `comic.narrative.core`

Purpose: move beyond a flat comic-image generator into an editable visual-story system where page geometry, panels, source art, dialogue, captions, characters, sequencing and motion remain independently controllable.

Planned screen IDs:

- `comic.narrative.library`
- `comic.narrative.page-editor`
- `comic.narrative.panel-editor`
- `comic.narrative.dialogue-editor`
- `comic.narrative.character-sheet`
- `comic.narrative.scene-graph`
- `comic.narrative.storyboard`
- `comic.narrative.motion-timeline`
- `comic.narrative.reader-preview`
- `comic.narrative.export`

Reusable primitive targets:

- `panel-frame`
- `panel-gutter`
- `speech-bubble`
- `caption-box`
- `storyboard-card`
- `reading-order-marker`
- `character-reference-card`
- `story-beat-link`

Primary style target: `narrative.ink`.

## Priority 3 — AXM software / monolith shell

Product target: `axm.system.shell`

Purpose: give AXM-native software coherent reusable surfaces rather than repeatedly inventing one-off dashboards.

Planned screen IDs:

- `axm.system.home`
- `axm.system.registry`
- `axm.system.capability-browser`
- `axm.system.cartridge-loader`
- `axm.system.machine-state`
- `axm.system.evidence-review`
- `axm.system.workflow`
- `axm.system.specialists`
- `axm.system.workfloor`
- `axm.system.snapshots`
- `axm.system.settings`
- `axm.system.recovery`

Design rule: deep machine state may be complex, but the human-facing shell should expose progressive detail rather than forcing internal complexity onto ordinary use.

## Priority 4 — Remaining near-term game gaps

These extend the already merged 57-screen game foundation only where real reusable gaps remain.

Planned IDs:

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

These should inherit the existing game-system shell where possible rather than duplicating profile/settings/network/accessibility surfaces.

## Priority 5 — Later visual families

Grow only after the editor/comic/AXM shells prove useful:

- poster / key-art composition systems;
- card/deck editors;
- cinematic title/credit systems;
- music visualizers and album-art editors;
- video overlay / stream-layout systems;
- procedural diagram / infographic editors;
- world-map / lore-atlas editors;
- interactive visual novel surfaces;
- 3D showroom / gallery presentation templates.

## Cross-cutting rules

Every new family should preserve the existing visual-template contract:

1. normalized responsive geometry with explicit compact/standard/wide behavior where relevant;
2. exact identity/version/digest through the existing Sticker Registry bridge;
3. no floating `latest` references or silent upgrades;
4. richer editable source remains authoritative over preview/export derivatives;
5. selection, focus, ownership, errors and destructive consequences do not depend on color alone;
6. `math_hooks` remain available for the mathematics lane to improve ratios/ranges without silently replacing template identity;
7. templates are known foundations, never automatic canon.

## Immediate build order

1. implement `editor.creative.core`;
2. implement `comic.narrative.core`;
3. prove both across the existing representative viewport set;
4. integrate both into the immutable registry and proof pack;
5. then begin `axm.system.shell`;
6. add game-gap templates only when they are not already represented by the merged v1 catalog.

# AXM Visual Template Expansion Priority Map

Status: v3 growth lane after verified v1 + v2 merges.

The visual-template fabric should grow where Universal Creation is most likely to reuse the knowledge soon. The order below is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Priority 1 — Creative editor core — MERGED

Product: `editor.creative.core`

Twelve coordinated professional editing surfaces are now part of the catalog: project hub, asset browser, layer editor, timeline, node graph, inspector, animation, effects, cutscene, material, audio and review/export. Style: `creative.workbench`.

## Priority 2 — Editable comics and visual narrative — MERGED

Product: `comic.narrative.core`

Ten editable visual-story surfaces are now part of the catalog: library, page editor, panel editor, dialogue editor, character sheet, scene graph, storyboard, motion timeline, reader preview and export. Style: `narrative.ink`.

The structural contract keeps page/panel/dialogue/scene/motion state distinct and preserves editable source above flattened previews.

## Priority 3 — AXM software / monolith shell — IMPLEMENTED IN THIS LANE

Product: `axm.system.shell`

Implemented screens:

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

New reusable primitives:

- `truth-state`
- `capability-card`
- `registry-entry`
- `evidence-chip`
- `state-diff`
- `cartridge-card`
- `specialist-card`
- `workfloor-lane`
- `snapshot-entry`
- `recovery-choice`

Style: `axm.machine.glass`.

Design rule: deep machine state may be complex, but the human-facing shell exposes summary first and progressively reveals detail. Source/version/evidence state and recovery consequences stay explicit.

## Priority 4 — Remaining near-term game gaps — NEXT

These extend the merged game foundation only where real reusable gaps remain.

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
6. `math_hooks` remain available for the mathematics lane to improve ratios/ranges without replacing template identity;
7. templates are known foundations, never automatic canon.

## Immediate build order

1. finish exact-head verification for `axm.system.shell`;
2. merge v3 only when template + repository checks pass;
3. start remaining near-term game gaps from fresh main;
4. only then expand into later visual families.

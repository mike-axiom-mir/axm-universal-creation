# AXM Visual Template Expansion Priority Map

Status: v4 growth lane after verified v1 + v2 + v3 merges.

The visual-template fabric should grow where Universal Creation is most likely to reuse the knowledge soon. The order below is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Priority 1 — Creative editor core — MERGED

Product: `editor.creative.core` — project hub, assets, layers, timeline, graph, inspector, animation, effects, cutscenes, materials, audio and review/export.

## Priority 2 — Editable comics and visual narrative — MERGED

Product: `comic.narrative.core` — library, page/panel/dialogue editing, characters, scene graph, storyboard, motion timeline, reader preview and export.

## Priority 3 — AXM software / monolith shell — MERGED

Product: `axm.system.shell` — home, registry, capabilities, cartridge loader, state, evidence, workflow, specialists, workfloor, snapshots, settings and recovery.

## Priority 4 — Near-term shared gameplay gaps — IMPLEMENTED IN THIS LANE

Product: `game.shared.core`

Implemented IDs:

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

New state-aware primitives:

- `inventory-slot`
- `skill-node`
- `objective-row`
- `shop-offer`
- `codex-entry`
- `revive-state`
- `boss-phase`
- `spectator-seat`
- `challenge-card`
- `session-stat`

Style: `game.shared.adventure`.

These inherit existing product plumbing where possible rather than duplicating profile/settings/network/accessibility surfaces.

## Priority 5 — High-value visual/creation families — NEXT

Potential next packs, ordered by likely reuse:

1. **Key art / poster / cover composition** — hero subject, title hierarchy, focal lighting, credits, variants and crop-safe outputs.
2. **Card/deck editor** — card faces/backs, rarity/state, deck building, stat/ability layouts and print/digital variants.
3. **Cinematic title / credits / trailer overlay system** — title cards, lower thirds, chapter cards, credits, subtitles and transition-safe zones.
4. **Video / stream overlay editor** — gameplay frame, cameras, alerts, chat, score, sponsor-free identity areas and responsive scene sets.
5. **Infographic / diagram editor** — nodes, relationships, legends, annotations, evidence/source panels and export layouts.
6. **World-map / lore-atlas editor** — regions, routes, layers, points of interest, time/state overlays and narrative references.
7. **Interactive visual-novel surfaces** — dialogue, choices, character staging, backgrounds, history/log, saves and branching state.
8. **3D showroom / gallery presentation** — hero object, comparison, annotations, material/variant selection and orbit/detail views.
9. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states and export crops.

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

1. finish exact-head verification for `game.shared.core`;
2. merge v4 only when template + repository checks pass;
3. start the highest-value visual/creation family from fresh main;
4. prefer reusable editors over one-off flat output templates.

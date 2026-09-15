# AXM Visual Template Expansion Priority Map

Status: v6 growth lane after verified v1–v5 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Priority 1 — Creative editor core — MERGED

`editor.creative.core` — assets, layers, timeline, graphs, inspector, animation, effects, cutscenes, materials, audio and review/export.

## Priority 2 — Editable comics and visual narrative — MERGED

`comic.narrative.core` — page/panel/dialogue editing, characters, scene graph, storyboard, motion timeline, reader preview and export.

## Priority 3 — AXM software / monolith shell — MERGED

`axm.system.shell` — registry, capabilities, cartridge loader, machine state, evidence, workflow, specialists, workfloor, snapshots and recovery.

## Priority 4 — Shared gameplay systems — MERGED

`game.shared.core` — inventory, progression, missions/maps/objectives, upgrades, codex, revive/boss/spectator state, session summaries and challenges.

## Priority 5A — Editable key art / poster / cover composition — MERGED

`visual.keyart.core` — source-first composition, subject staging, typography, lighting/effects, atmosphere, crop variants, exact alternate compositions, review and export.

## Priority 5B — Card / deck editor — IMPLEMENTED IN THIS LANE

Product: `visual.cards.core`

Implemented screens:

- `visual.cards.project-hub`
- `visual.cards.face-editor`
- `visual.cards.back-editor`
- `visual.cards.artwork-editor`
- `visual.cards.text-stats`
- `visual.cards.ability-layout`
- `visual.cards.rarity-style`
- `visual.cards.effects-finish`
- `visual.cards.deck-builder`
- `visual.cards.print-sheet`
- `visual.cards.review-export`

New primitives:

- `card-frame`
- `artwork-window`
- `stat-block`
- `ability-row`
- `rarity-badge`
- `cost-symbol`
- `card-state`
- `deck-slot`
- `foil-pass`
- `print-safe-frame`

Style: `visual.cards.collectible`.

The source-first boundary is explicit: face/back remain distinct, source art and crop remain separate, rules text stays exact, rarity is not color-only, deck membership uses exact card references, foil cannot replace base art and print guides cannot mutate source layout.

## Priority 5C — Next high-value visual/creation families

1. **Cinematic title / credits / trailer overlay system** — title cards, lower thirds, chapter cards, credits, subtitles and transition-safe zones.
2. **Video / stream overlay editor** — gameplay frame, cameras, alerts, chat, score and responsive scene sets.
3. **Infographic / diagram editor** — nodes, relationships, legends, annotations, evidence/source panels and export layouts.
4. **World-map / lore-atlas editor** — regions, routes, layers, points of interest, time/state overlays and narrative references.
5. **Interactive visual-novel surfaces** — dialogue, choices, character staging, backgrounds, history/log, saves and branching state.
6. **3D showroom / gallery presentation** — hero object, comparison, annotations, material/variant selection and orbit/detail views.
7. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states and export crops.

## Cross-cutting rules

Every new family should preserve the existing visual-template contract:

1. normalized responsive geometry with explicit compact/standard/wide behavior where relevant;
2. exact identity/version/digest through the existing Sticker Registry bridge;
3. no floating `latest` references or silent upgrades;
4. richer editable source remains authoritative over preview/export derivatives;
5. selection, focus, ownership, errors and consequences do not depend on color alone;
6. `math_hooks` remain available for mathematical ratio/range growth without replacing template identity;
7. templates are known foundations, never automatic canon.

## Immediate build order

1. exact-head verify `visual.cards.core`;
2. merge v6 only when template + repository checks pass;
3. begin cinematic title/credits/trailer overlays from fresh main;
4. keep prioritizing reusable editors over flat one-off output templates.

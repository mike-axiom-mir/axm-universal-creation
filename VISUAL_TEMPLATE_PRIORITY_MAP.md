# AXM Visual Template Expansion Priority Map

Status: v5 growth lane after verified v1–v4 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Priority 1 — Creative editor core — MERGED

`editor.creative.core` — assets, layers, timeline, graphs, inspector, animation, effects, cutscenes, materials, audio and review/export.

## Priority 2 — Editable comics and visual narrative — MERGED

`comic.narrative.core` — page/panel/dialogue editing, characters, scene graph, storyboard, motion timeline, reader preview and export.

## Priority 3 — AXM software / monolith shell — MERGED

`axm.system.shell` — registry, capabilities, cartridge loader, machine state, evidence, workflow, specialists, workfloor, snapshots and recovery.

## Priority 4 — Shared gameplay systems — MERGED

`game.shared.core` — inventory, progression, missions/maps/objectives, upgrades, codex, revive/boss/spectator state, session summaries and challenges.

## Priority 5A — Editable key art / poster / cover composition — IMPLEMENTED IN THIS LANE

Product: `visual.keyart.core`

Implemented screens:

- `visual.keyart.project-hub`
- `visual.keyart.composition-editor`
- `visual.keyart.subject-stage`
- `visual.keyart.type-editor`
- `visual.keyart.lighting-effects`
- `visual.keyart.background-atmosphere`
- `visual.keyart.crop-variants`
- `visual.keyart.variant-board`
- `visual.keyart.review-compare`
- `visual.keyart.export`

New primitives:

- `hero-subject`
- `depth-layer`
- `focal-mask`
- `title-lockup`
- `credit-block`
- `lighting-pass`
- `crop-safe-frame`
- `variant-card`
- `export-target`

Style: `visual.keyart.cinematic`.

The source-first rule is explicit: crop/output frames do not mutate source geometry, effects do not become source authority, text and layout remain separable, and alternate compositions have exact variant identity.

## Priority 5B — Next high-value visual/creation families

1. **Card/deck editor** — card faces/backs, rarity/state, deck building, stat/ability layouts and print/digital variants.
2. **Cinematic title / credits / trailer overlay system** — title cards, lower thirds, chapter cards, credits, subtitles and transition-safe zones.
3. **Video / stream overlay editor** — gameplay frame, cameras, alerts, chat, score and responsive scene sets.
4. **Infographic / diagram editor** — nodes, relationships, legends, annotations, evidence/source panels and export layouts.
5. **World-map / lore-atlas editor** — regions, routes, layers, points of interest, time/state overlays and narrative references.
6. **Interactive visual-novel surfaces** — dialogue, choices, character staging, backgrounds, history/log, saves and branching state.
7. **3D showroom / gallery presentation** — hero object, comparison, annotations, material/variant selection and orbit/detail views.
8. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states and export crops.

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

1. exact-head verify `visual.keyart.core`;
2. merge v5 only when template + repository checks pass;
3. begin the card/deck editor from fresh main;
4. keep prioritizing reusable editors over flat one-off output templates.

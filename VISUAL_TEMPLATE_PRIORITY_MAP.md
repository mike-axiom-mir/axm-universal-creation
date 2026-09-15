# AXM Visual Template Expansion Priority Map

Status: v7 growth lane after verified v1–v6 merges.

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

## Priority 5B — Card / deck editor — MERGED

`visual.cards.core` — card face/back, source artwork, exact text/stats/rules, rarity, effects/foil, deck construction, print sheets and review/export.

## Priority 5C — Cinematic title / credits / overlay editor — IMPLEMENTED IN THIS LANE

Product: `visual.cinematic.core`

Implemented screens:

- `visual.cinematic.project-hub`
- `visual.cinematic.title-editor`
- `visual.cinematic.chapter-editor`
- `visual.cinematic.lower-third`
- `visual.cinematic.subtitle-editor`
- `visual.cinematic.credits-editor`
- `visual.cinematic.overlay-timeline`
- `visual.cinematic.transition-editor`
- `visual.cinematic.aspect-variants`
- `visual.cinematic.review-export`

New primitives:

- `title-card`
- `lower-third`
- `subtitle-cue`
- `credit-line`
- `time-cue`
- `safe-zone`
- `transition-cue`
- `chapter-marker`
- `overlay-track`
- `logo-lockup`

Style: `visual.cinematic.motion`.

Exact text, layout, timing, order, safe-area adaptation and transition state remain separately editable. Safe/output variants cannot rewrite richer source layout and transitions remain derived between exact source states.

## Priority 5D — Next high-value visual/creation families

1. **Video / stream overlay editor** — gameplay/program frame, cameras, alerts, chat, score/status and responsive scene sets.
2. **Infographic / diagram editor** — nodes, relationships, legends, annotations, evidence/source panels and export layouts.
3. **World-map / lore-atlas editor** — regions, routes, layers, points of interest, time/state overlays and narrative references.
4. **Interactive visual-novel surfaces** — dialogue, choices, character staging, backgrounds, history/log, saves and branching state.
5. **3D showroom / gallery presentation** — hero object, comparison, annotations, material/variant selection and orbit/detail views.
6. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states and export crops.

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

1. exact-head verify `visual.cinematic.core`;
2. merge v7 only when template + repository checks pass;
3. begin video / stream overlay editing from fresh main;
4. keep prioritizing reusable editors over flat one-off output templates.

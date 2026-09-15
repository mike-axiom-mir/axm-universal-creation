# AXM Visual Template Expansion Priority Map

Status: v21 growth lane after verified v1–v20 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Merged foundations

- creative editor, editable comics and AXM system shell;
- racing/co-op/RTS/shared game systems;
- key art, cards/decks, cinematic and broadcast overlays;
- evidence-aware diagrams and world-map/lore-atlas editing;
- branching visual novel, 3D showroom, music and presentation/explainer systems;
- character / creature reference sheets;
- vehicle / weapon / equipment configurator;
- source-bound UI motion / transition systems;
- brand / identity system editor;
- environment / level reference boards;
- VFX / particle reference-authoring.

## Quest / mission flow reference systems — IMPLEMENTED IN THIS LANE

Product: `visual.mission.core`

Implemented screens:

- `visual.mission.project-hub`
- `visual.mission.objectives`
- `visual.mission.conditions`
- `visual.mission.branch-flow`
- `visual.mission.world-bindings`
- `visual.mission.rewards-outcomes`
- `visual.mission.failure-retry`
- `visual.mission.runtime-state`
- `visual.mission.variants`
- `visual.mission.review-export`

New primitives:

- `mission-source`
- `objective-state`
- `mission-condition`
- `mission-edge`
- `mission-world-reference`
- `mission-reward-reference`
- `mission-failure-recovery`
- `mission-runtime-flag`
- `mission-variant`
- `mission-export-target`

Style: `visual.mission.flow`.

The central rule is runtime/flow truth: graph lines do not prove reachability, objective presentation does not prove completion, map proximity does not create a mission binding, reward presentation does not prove delivery, and failure/retry/recovery consequences remain explicit source state.

## Next high-value visual/creation families

1. **HUD theme / skin systems** — source-bound component families, layout constraints, readability state, platform/input variants and per-game identity application.
2. **Lighting / post-process look systems** — source-bound exposure, tone, fog, grading, bloom and accessibility/performance variants without baking presentation into world state.
3. **Camera / shot reference systems** — exact camera rigs, targets, framing, lens/FOV, shot transitions and gameplay/cinematic ownership without treating preview framing as world state.
4. **Inventory / item-reference systems** — item identity, rarity/affordance presentation, equipment slots, stats, comparison, provenance and platform/input variants without turning iconography into gameplay truth.

## Cross-cutting rules

Every family preserves the existing visual-template contract:

1. normalized responsive geometry with explicit compact/standard/wide behavior where relevant;
2. exact identity/version/digest through the Sticker Registry bridge;
3. no floating `latest` references or silent upgrades;
4. richer editable source remains authoritative over preview/export derivatives;
5. meaning, selection, ownership, errors and consequences do not depend on color alone;
6. `math_hooks` remain available for mathematical ratio/range growth without replacing template identity;
7. templates are known foundations, never automatic canon.

## Immediate build order

1. exact-head verify `visual.mission.core`;
2. merge v21 only when template + repository checks pass;
3. begin HUD theme / skin systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

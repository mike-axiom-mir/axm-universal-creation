# AXM Visual Template Expansion Priority Map

Status: v20 growth lane after verified v1–v19 merges.

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
- environment / level reference boards.

## VFX / particle reference-authoring — IMPLEMENTED IN THIS LANE

Product: `visual.vfx.core`

Implemented screens:

- `visual.vfx.project-hub`
- `visual.vfx.effect-stage`
- `visual.vfx.emitter-editor`
- `visual.vfx.spawn-region`
- `visual.vfx.curves-timing`
- `visual.vfx.modules`
- `visual.vfx.layers-composite`
- `visual.vfx.interaction-hooks`
- `visual.vfx.reduced-performance`
- `visual.vfx.review-export`

New primitives:

- `vfx-source`
- `emitter-state`
- `spawn-region`
- `emission-curve`
- `particle-module`
- `vfx-layer`
- `vfx-interaction-hook`
- `vfx-timing-event`
- `reduced-effect-rule`
- `vfx-export-target`

Style: `visual.vfx.effect`.

The central rule is runtime truth: effects can communicate or decorate exact events but never prove those events occurred. Collision, damage, interaction and state-change semantics require explicit source-bound hooks; reduced-effect variants preserve required semantic feedback.

## Next high-value visual/creation families

1. **Quest / mission flow reference systems** — objective identity, prerequisites, branches, state transitions, rewards, failure/retry and world/map references for game production.
2. **HUD theme / skin systems** — source-bound component families, layout constraints, readability state, platform/input variants and per-game identity application.
3. **Lighting / post-process look systems** — source-bound exposure, tone, fog, grading, bloom and accessibility/performance variants without baking presentation into world state.
4. **Camera / shot reference systems** — exact camera rigs, targets, framing, lens/FOV, shot transitions and gameplay/cinematic ownership without treating preview framing as world state.

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

1. exact-head verify `visual.vfx.core`;
2. merge v20 only when template + repository checks pass;
3. begin quest / mission flow reference systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

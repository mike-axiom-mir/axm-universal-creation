# AXM Visual Template Expansion Priority Map

Status: v17 growth lane after verified v1–v16 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Merged foundations

- creative editor, editable comics and AXM system shell;
- racing/co-op/RTS/shared game systems;
- key art, cards/decks, cinematic and broadcast overlays;
- evidence-aware diagrams and world-map/lore-atlas editing;
- branching visual novel, 3D showroom, music and presentation/explainer systems;
- character / creature reference sheets;
- vehicle / weapon / equipment configurator.

## UI motion / transition archetypes — IMPLEMENTED IN THIS LANE

Product: `visual.motion.core`

Implemented screens:

- `visual.motion.project-hub`
- `visual.motion.transition-editor`
- `visual.motion.focus-navigation`
- `visual.motion.spatial-continuity`
- `visual.motion.timing-curves`
- `visual.motion.interruption-recovery`
- `visual.motion.progress-loading`
- `visual.motion.reduced-motion`
- `visual.motion.trigger-matrix`
- `visual.motion.review-export`

New primitives:

- `motion-state`
- `transition-edge-state`
- `timing-curve`
- `focus-motion-path`
- `spatial-anchor-transition`
- `interruption-recovery`
- `progress-motion-state`
- `reduced-motion-rule`
- `motion-trigger`
- `motion-export-target`

Style: `visual.motion.system`.

The central rule is state truth: motion explains exact transitions but never creates them. Animation end is not task completion, screen position is not semantic focus order, visual resemblance is not shared-element identity, and reduced-motion variants must preserve the same semantic destination.

## Next high-value visual/creation families

1. **Brand / identity system editor** — exact logos, typography, icon families, spacing rules, usage variants and provenance-backed export packs.
2. **Environment / level reference boards** — modular location identity, scale, materials, props, lighting references, traversal annotations and source provenance for game-world production.
3. **VFX / particle reference and authoring surfaces** — emitter/state identity, timing curves, spawn regions, layering, collision/interaction hooks and reduced-effect variants.
4. **Quest / mission flow reference systems** — objective identity, prerequisites, branches, state transitions, rewards, failure/retry and world/map references for game production.

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

1. exact-head verify `visual.motion.core`;
2. merge v17 only when template + repository checks pass;
3. begin brand / identity system editing from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

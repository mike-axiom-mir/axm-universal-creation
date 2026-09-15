# AXM Visual Template Expansion Priority Map

Status: v19 growth lane after verified v1–v18 merges.

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
- brand / identity system editor.

## Environment / level reference boards — IMPLEMENTED IN THIS LANE

Product: `visual.environment.core`

Implemented screens:

- `visual.environment.project-hub`
- `visual.environment.identity-board`
- `visual.environment.zones-layout`
- `visual.environment.scale-measurements`
- `visual.environment.modular-kit`
- `visual.environment.materials`
- `visual.environment.lighting-weather`
- `visual.environment.traversal-annotations`
- `visual.environment.variants`
- `visual.environment.review-export`

New primitives:

- `environment-source`
- `environment-zone`
- `environment-measurement`
- `modular-environment-piece`
- `environment-prop`
- `environment-material`
- `environment-lighting-state`
- `traversal-reference`
- `environment-variant`
- `environment-export-target`

Style: `visual.environment.reference`.

The central rule is environment truth: reference boards guide production but do not become authoritative level geometry. Scale requires explicit measurements/source state, prop proximity is not gameplay linkage, and traversal/lighting/biome references remain exact source-bound annotations or variants.

## Next high-value visual/creation families

1. **VFX / particle reference and authoring surfaces** — emitter/state identity, timing curves, spawn regions, layering, collision/interaction hooks and reduced-effect variants.
2. **Quest / mission flow reference systems** — objective identity, prerequisites, branches, state transitions, rewards, failure/retry and world/map references for game production.
3. **HUD theme / skin systems** — source-bound component families, layout constraints, readability state, platform/input variants and per-game identity application.
4. **Lighting / post-process look systems** — source-bound exposure, tone, fog, grading, bloom and accessibility/performance variants without baking presentation into world state.

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

1. exact-head verify `visual.environment.core`;
2. merge v19 only when template + repository checks pass;
3. begin VFX / particle reference-authoring from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

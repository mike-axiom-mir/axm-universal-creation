# AXM Visual Template Expansion Priority Map

Status: v16 growth lane after verified v1–v15 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Merged foundations

- creative editor, editable comics and AXM system shell;
- racing/co-op/RTS/shared game systems;
- key art / poster / cover editor;
- card / deck editor;
- cinematic title / credits / overlay editor;
- video / program / stream overlay editor;
- evidence-aware infographic / diagram editor;
- world-map / lore-atlas editor;
- interactive visual-novel / branching narrative editor;
- 3D showroom / gallery presentation;
- music visualizer / album-art editor;
- presentation / explainer page systems;
- character / creature reference-sheet editor.

## Vehicle / weapon / equipment configurator — IMPLEMENTED IN THIS LANE

Product: `visual.configurator.core`

Implemented screens:

- `visual.configurator.project-hub`
- `visual.configurator.object-stage`
- `visual.configurator.socket-editor`
- `visual.configurator.exploded-view`
- `visual.configurator.stat-editor`
- `visual.configurator.variant-material`
- `visual.configurator.compatibility`
- `visual.configurator.comparison`
- `visual.configurator.loadout-presets`
- `visual.configurator.review-export`

New primitives:

- `configurable-source`
- `attachment-socket`
- `component-part`
- `compatibility-rule`
- `config-stat-field`
- `configuration-state`
- `exploded-view-state`
- `config-material-variant`
- `config-annotation`
- `configurator-export-target`

Style: `visual.configurator.precision`.

The central rule is configuration truth: exact source object, sockets, attached components, compatibility rules, stats, variants and saved configuration identity remain separate editable state. Exploded/detail/comparison views are derived presentation and visual fit never implies compatibility.

## Next high-value visual/creation families

1. **UI motion / transition archetypes** — reusable state transitions, focus motion, spatial continuity, interruption/recovery and reduced-motion variants across software/game products.
2. **Brand / identity system editor** — exact logos, typography, icon families, spacing rules, usage variants and provenance-backed export packs.
3. **Environment / level reference boards** — modular location identity, scale, materials, props, lighting references, traversal annotations and source provenance for game-world production.
4. **VFX / particle reference and authoring surfaces** — emitter/state identity, timing curves, spawn regions, layering, collision/interaction hooks and reduced-effect variants.

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

1. exact-head verify `visual.configurator.core`;
2. merge v16 only when template + repository checks pass;
3. begin UI motion / transition archetypes from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

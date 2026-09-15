# AXM Visual Template Expansion Priority Map

Status: v15 growth lane after verified v1–v14 merges.

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
- presentation / explainer page systems.

## Character / creature reference-sheet editor — IMPLEMENTED IN THIS LANE

Product: `visual.character.core`

Implemented screens:

- `visual.character.project-hub`
- `visual.character.turnaround`
- `visual.character.proportions`
- `visual.character.expressions`
- `visual.character.poses`
- `visual.character.materials`
- `visual.character.callouts`
- `visual.character.scale-variants`
- `visual.character.reference-board`
- `visual.character.review-export`

New primitives:

- `character-source`
- `turnaround-view`
- `proportion-guide`
- `expression-state`
- `pose-reference`
- `character-material`
- `character-callout`
- `scale-reference`
- `character-variant`
- `reference-export-target`

Style: `visual.character.reference`.

The central rule is character/reference truth: canonical identity, views, proportions, expressions, poses, materials, callouts, scale and variants remain distinct editable state. Approximate/derived measurements stay distinct from exact values, and inspiration/reference material never becomes canonical source merely because it is visually nearby.

## Next high-value visual/creation families

1. **Vehicle / weapon configuration presentation** — attachment sockets, exact configuration identity, stat comparison, exploded/detail views and source-bound garage/loadout presentation.
2. **UI motion / transition archetypes** — reusable state transitions, focus motion, spatial continuity and reduced-motion variants across software/game products.
3. **Brand / identity system editor** — exact logos, typography, icon families, spacing rules, usage variants and provenance-backed export packs.
4. **Environment / level reference boards** — modular location identity, scale, materials, props, lighting references, traversal annotations and source provenance for game-world production.

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

1. exact-head verify `visual.character.core`;
2. merge v15 only when template + repository checks pass;
3. begin vehicle / weapon configuration presentation from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

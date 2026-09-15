# AXM Visual Template Expansion Priority Map

Status: v12 growth lane after verified v1–v11 merges.

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
- interactive visual-novel / branching narrative editor.

## 3D showroom / gallery presentation — IMPLEMENTED IN THIS LANE

Product: `visual.showroom.core`

Implemented screens:

- `visual.showroom.project-hub`
- `visual.showroom.object-stage`
- `visual.showroom.orbit-camera`
- `visual.showroom.material-editor`
- `visual.showroom.variant-editor`
- `visual.showroom.annotation-editor`
- `visual.showroom.comparison`
- `visual.showroom.detail-view`
- `visual.showroom.turntable`
- `visual.showroom.review-export`

New primitives:

- `showroom-object`
- `orbit-rig`
- `camera-preset`
- `material-slot`
- `variant-option`
- `object-annotation`
- `comparison-object`
- `turntable-state`
- `measurement-callout`
- `showroom-export-target`

Style: `visual.showroom.studio`.

The central rule is object/source truth: exact asset/version, camera target, part/material binding, variant identity/availability, annotation target, comparison references and measurement value/unit/source remain inspectable. Camera/orbit/turntable presentation cannot silently rewrite source-object state.

## Next high-value visual/creation families

1. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states, lyric-free timing/marker state and export crops.
2. **Presentation / explainer page systems** — reusable storytelling pages assembled from diagram, key-art, atlas and editor foundations.
3. **Character / creature reference-sheet editor** — turnaround views, expressions, materials, proportions, callouts and source/reference state for future games/comics.
4. **Vehicle / weapon configuration presentation** — attachment sockets, stat comparison, exploded/detail presentation and exact source/configuration identity for game garages/loadouts.

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

1. exact-head verify `visual.showroom.core`;
2. merge v12 only when template + repository checks pass;
3. begin music visualizer / album-art editing from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

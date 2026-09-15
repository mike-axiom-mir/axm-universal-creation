# AXM Visual Template Expansion Priority Map

Status: v11 growth lane after verified v1–v10 merges.

The visual-template fabric grows where Universal Creation is likely to reuse the knowledge soon. This is a build priority, not canon: templates remain editable foundations and may be replaced when evidence supports a better structure.

## Merged foundations

- creative editor, editable comics and AXM system shell;
- racing/co-op/RTS/shared game systems;
- key art / poster / cover editor;
- card / deck editor;
- cinematic title / credits / overlay editor;
- video / program / stream overlay editor;
- evidence-aware infographic / diagram editor;
- world-map / lore-atlas editor.

## Interactive visual-novel / branching narrative — IMPLEMENTED IN THIS LANE

Product: `visual.novel.core`

Implemented screens:

- `visual.novel.project-hub`
- `visual.novel.scene-editor`
- `visual.novel.character-stage`
- `visual.novel.dialogue-editor`
- `visual.novel.choice-editor`
- `visual.novel.branch-graph`
- `visual.novel.state-inspector`
- `visual.novel.history-log`
- `visual.novel.save-checkpoint`
- `visual.novel.review-export`

New primitives:

- `scene-background`
- `character-stage`
- `dialogue-block`
- `choice-option`
- `branch-node`
- `story-flag`
- `history-entry`
- `save-checkpoint`
- `scene-transition`
- `novel-export-target`

Style: `visual.novel.story`.

The central rule is branching-state truth: exact scenes, character identity/pose/expression, dialogue, choice targets/conditions, node edges, runtime flags, history and save/checkpoint state remain independently editable and inspectable. Presentation cannot silently manufacture a reachable branch or character/runtime state.

## Next high-value visual/creation families

1. **3D showroom / gallery presentation** — hero object, comparison, annotations, material/variant selection, turntable/orbit and detail views.
2. **Music visualizer / album-art editor** — cover systems, track identity, waveform/beat-driven visual states and export crops.
3. **Presentation / explainer page systems** — reusable storytelling pages assembled from diagram, key-art, atlas and editor foundations.
4. **Character / creature reference-sheet editor** — turnaround views, expressions, materials, proportions, callouts and source/reference state for future games/comics.

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

1. exact-head verify `visual.novel.core`;
2. merge v11 only when template + repository checks pass;
3. begin 3D showroom / gallery presentation from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

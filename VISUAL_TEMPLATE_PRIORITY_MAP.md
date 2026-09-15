# AXM Visual Template Expansion Priority Map

Status: v13 growth lane after verified v1–v12 merges.

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
- 3D showroom / gallery presentation.

## Music visualizer / album-art editor — IMPLEMENTED IN THIS LANE

Product: `visual.music.core`

Implemented screens:

- `visual.music.project-hub`
- `visual.music.cover-editor`
- `visual.music.track-identity`
- `visual.music.analysis-waveform`
- `visual.music.marker-timing`
- `visual.music.reactive-editor`
- `visual.music.tracklist-sequence`
- `visual.music.crop-variants`
- `visual.music.playback-preview`
- `visual.music.review-export`

New primitives:

- `music-track-source`
- `music-analysis`
- `beat-marker`
- `waveform-source`
- `cover-composition`
- `reactive-visual-layer`
- `music-marker-cue`
- `album-variant`
- `track-list-entry`
- `music-export-target`

Style: `visual.music.resonant`.

The central rule is audio/source truth: exact track identity/source/digest/duration stays authoritative. Waveform, analysis, beat markers and reactive state must be observed or explicitly derived and attributed. Album art remains editable source layers; no lyrics are inferred or manufactured by this pack.

## Next high-value visual/creation families

1. **Presentation / explainer page systems** — reusable storytelling pages assembled from diagram, key-art, atlas, showroom and editor foundations.
2. **Character / creature reference-sheet editor** — turnaround views, expressions, materials, proportions, callouts and source/reference state for future games/comics.
3. **Vehicle / weapon configuration presentation** — attachment sockets, stat comparison, exploded/detail presentation and exact source/configuration identity for game garages/loadouts.
4. **UI motion / transition archetypes** — reusable state transitions, focus motion, spatial continuity and reduced-motion variants across software/game products.

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

1. exact-head verify `visual.music.core`;
2. merge v13 only when template + repository checks pass;
3. begin presentation / explainer page systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

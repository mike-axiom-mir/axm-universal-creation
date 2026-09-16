# AXM Visual Template Expansion Priority Map

Status: v24 growth lane after verified v1–v23 merges.

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
- VFX / particle reference-authoring;
- quest / mission flow systems;
- HUD theme / skin systems;
- lighting / post-process look systems.

## Camera / shot reference systems — IMPLEMENTED IN THIS LANE

Product: `visual.camera.core`

Implemented screens:

- `visual.camera.project-hub`
- `visual.camera.rig-editor`
- `visual.camera.target-framing`
- `visual.camera.lens-fov`
- `visual.camera.constraints`
- `visual.camera.transitions`
- `visual.camera.runtime-bindings`
- `visual.camera.platform-variants`
- `visual.camera.compare-preview`
- `visual.camera.review-export`

New primitives:

- `camera-source`
- `camera-rig`
- `camera-target`
- `lens-state`
- `framing-guide`
- `camera-transition`
- `camera-constraint`
- `camera-runtime-binding`
- `camera-platform-variant`
- `camera-export-target`

Style: `visual.camera.system`.

The central rule is camera/world-state truth: preview framing never moves world objects, cinematic appearance does not imply gameplay ownership, lens values retain exact source/units, and target/runtime bindings require explicit source state.

## Next high-value visual/creation families

1. **Inventory / item-reference systems** — item identity, rarity/affordance presentation, equipment slots, stats, comparison, provenance and platform/input variants without turning iconography into gameplay truth.
2. **Menu / shell theme systems** — source-bound navigation/component families, focus/state visibility, controller/touch/keyboard variants and branding hooks across complete game/application shells.
3. **Animation / rig reference systems** — exact skeleton/rig identity, clips, state transitions, timing/root-motion/event hooks and retargeting/source state without treating preview motion as runtime truth.
4. **Vehicle cockpit / instrument systems** — exact telemetry bindings, gauges, warning channels, camera/seat variants and platform readability without making visual instruments authoritative over simulation state.

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

1. exact-head verify `visual.camera.core`;
2. merge v24 only when template + repository checks pass;
3. begin inventory / item-reference systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

# AXM Visual Template Expansion Priority Map

Status: v23 growth lane after verified v1–v22 merges.

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
- HUD theme / skin systems.

## Lighting / post-process look systems — IMPLEMENTED IN THIS LANE

Product: `visual.look.core`

Implemented screens:

- `visual.look.project-hub`
- `visual.look.exposure-tone`
- `visual.look.color-grade`
- `visual.look.fog-atmosphere`
- `visual.look.bloom-glare`
- `visual.look.layer-stack`
- `visual.look.scene-bindings`
- `visual.look.platform-performance`
- `visual.look.compare-preview`
- `visual.look.review-export`

New primitives:

- `look-source`
- `exposure-state`
- `tone-map-state`
- `color-grade-state`
- `fog-atmosphere-state`
- `bloom-glare-state`
- `postprocess-layer`
- `scene-look-binding`
- `look-platform-variant`
- `look-export-target`

Style: `visual.look.system`.

The central rule is look/world-state truth: a beautiful preview does not redefine world lighting, color transforms do not replace source materials/lights/geometry, scene application requires exact bindings, and performance/accessibility variants preserve required visibility and state legibility.

## Next high-value visual/creation families

1. **Camera / shot reference systems** — exact camera rigs, targets, framing, lens/FOV, shot transitions and gameplay/cinematic ownership without treating preview framing as world state.
2. **Inventory / item-reference systems** — item identity, rarity/affordance presentation, equipment slots, stats, comparison, provenance and platform/input variants without turning iconography into gameplay truth.
3. **Menu / shell theme systems** — source-bound navigation/component families, focus/state visibility, controller/touch/keyboard variants and branding hooks across complete game/application shells.
4. **Animation / rig reference systems** — exact skeleton/rig identity, clips, state transitions, timing/root-motion/event hooks and retargeting/source state without treating preview motion as runtime truth.

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

1. exact-head verify `visual.look.core`;
2. merge v23 only when template + repository checks pass;
3. begin camera / shot reference systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

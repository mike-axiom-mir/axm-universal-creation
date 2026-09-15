# AXM Visual Template Expansion Priority Map

Status: v22 growth lane after verified v1–v21 merges.

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
- quest / mission flow systems.

## HUD theme / skin systems — IMPLEMENTED IN THIS LANE

Product: `visual.hud.core`

Implemented screens:

- `visual.hud.project-hub`
- `visual.hud.components`
- `visual.hud.layout`
- `visual.hud.data-bindings`
- `visual.hud.readability`
- `visual.hud.alerts-feedback`
- `visual.hud.platform-input`
- `visual.hud.theme-skin`
- `visual.hud.compare-preview`
- `visual.hud.review-export`

New primitives:

- `hud-source`
- `hud-component`
- `hud-layout-anchor`
- `hud-data-binding`
- `hud-readability-rule`
- `hud-safe-region`
- `hud-alert-state`
- `hud-platform-variant`
- `hud-theme-variant`
- `hud-export-target`

Style: `visual.hud.system`.

The central rule is HUD/game-state truth: visual placement does not create a data binding, meter appearance does not prove the underlying value, icon/color alone cannot carry critical meaning, skins do not rewrite gameplay state, and platform variants preserve required semantic feedback/readability.

## Next high-value visual/creation families

1. **Lighting / post-process look systems** — source-bound exposure, tone, fog, grading, bloom and accessibility/performance variants without baking presentation into world state.
2. **Camera / shot reference systems** — exact camera rigs, targets, framing, lens/FOV, shot transitions and gameplay/cinematic ownership without treating preview framing as world state.
3. **Inventory / item-reference systems** — item identity, rarity/affordance presentation, equipment slots, stats, comparison, provenance and platform/input variants without turning iconography into gameplay truth.
4. **Menu / shell theme systems** — source-bound navigation/component families, focus/state visibility, controller/touch/keyboard variants and branding hooks across complete game/application shells.

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

1. exact-head verify `visual.hud.core`;
2. merge v22 only when template + repository checks pass;
3. begin lighting / post-process look systems from fresh main;
4. keep prioritizing reusable source-first editors over flat one-off outputs.

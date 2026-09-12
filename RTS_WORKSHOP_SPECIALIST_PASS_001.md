# RTS Workshop — Profession Fabric Specialist Pass 001

This lane applies the first live Profession Fabric findings to the real improvised workshop source.

## Origin

Profession Fabric Live Job 001 applied four bounded professional methods to the exact workshop artifact:

- Art Director
- 3D Artist
- Technical Artist
- Software QA / Playtest

Durable Profession Fabric record: `mike-axiom-mir/axm-profession-fabric` PR #33.
Universal Creation handoff: issue #51.

This is one machine cognition applying several professional methods. It is not evidence of four independent specialist intelligences.

## Source change in this lane

The Art Director pass identified a remaining identity problem rather than a detail problem. Existing source already contains small personality seeds such as the tea engine, mechanic mug, reclaimed car-door cupboard, hubcap stool, reused wheel hoist and mismatched repair straps.

This pass therefore adds three deliberately large, editable found-object anchors:

1. `front salvage grin` — a front-facing yellow/red smile emblem intended to survive RTS distance;
2. `roof vane salvage wheel` — a crooked wheel-and-scrap wind-vane crown that breaks the roof silhouette;
3. `rear trophy spare wheel` — an asymmetric rear scrap trophy rack so the back has its own identity.

The goal is not to add more micro-detail. The goal is to make the workshop read as an inhabited, playful salvage faction asset from farther away and from more than the hero angle.

## What this lane can establish without Blender

Repository CI can establish that:

- the Python source parses;
- the three anchor constructors remain present;
- `workshop_life()` still invokes all three anchors;
- the rest of the Python/unit-test suite has not regressed.

Those are structural/software facts only.

## Visual acceptance remains blocked

This environment does not have Blender. Therefore this lane does **not** claim that the new anchors:

- improve the asset visually;
- preserve the accepted hero composition;
- avoid geometry intersections;
- remain readable at the intended RTS camera distance;
- improve the rear/detail views;
- preserve the current 3D quality bar.

Fresh Blender build, GLB re-import and visual inspection are still required before an Art Director or 3D Artist acceptance claim.

## Technical-art / QA gates remain separate

The source change does not resolve or claim:

- collision correctness;
- navigation/pathfinding integration;
- target-RTS or target-engine import;
- target-device FPS/performance;
- LOD1 perceptual equivalence;
- material/texture budget acceptance;
- proof that all 18 double-sided material states are required;
- complete game-readiness.

Those remain separate evidence lanes from Profession Fabric Live Job 001.

## Merge rule

Do not merge this lane as a visual improvement merely because CI is green.

Green CI proves source/test continuity. Visual acceptance requires fresh generated evidence from the actual workshop pipeline and inspection of that evidence. If the new anchors hurt composition or readability, repair or revert them rather than redefining the goal.

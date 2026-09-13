# Game runtime realization

`axm_uc.game_runtime_realization` selects the cheapest measured LOD that is
acceptable for each caller-owned game view. It is deterministic, offline and
renderer-neutral. The planner preserves the complete source and request plus
their SHA-256 identities; it does not alter the canonical asset.

## Evidence contract

Each LOD supplies measured triangle count, maximum surface deviation, surviving
story features, contact/socket frames and render observations for named views.
Each view supplies distance, vertical field of view, viewport height, projected
error budget, maximum RGBA RMSE and minimum silhouette intersection-over-union.

A LOD is eligible only when all four gates pass:

1. every contact and socket stays within caller-owned position/angle tolerance;
2. maximum surface deviation projects below the pixel-error budget;
3. every feature large enough to be readable at that view is present; and
4. an exact-view render observation passes both image and silhouette limits.

Missing evidence fails closed. Among eligible representations, the planner
chooses the lowest triangle count. It never assumes that fewer triangles are
better, or that a geometric bound proves visual equivalence.

```sh
axm-assets game-realization-catalog
axm-assets game-realization-plan source.json request.json out/realization
```

The transactional publisher writes the exact source, exact request and final
plan to a new directory and refuses overwrite.

## Real export proof

`tools/blender/game_runtime_realization_roundtrip.py` builds three actual GLBs
of the original animated AXM Clockwork Smacker: 58,928, 28,284 and 10,586
triangles. Blender 4.3 then imports each GLB in a fresh scene, measures final
imported surfaces and triangle counts, checks four attachment/contact frames,
counts feature-bearing triangles, and renders 2.8 m, 9 m and 22 m game views.

With a 42-degree vertical field of view, 512-pixel viewport, 2-pixel geometric
budget, 0.01 RGBA RMSE limit and 0.995 silhouette-IoU floor, the plan selects
LOD0, LOD1 and LOD2 respectively. Geometry-only selection initially chose LOD2
for every view; the near-view render RMSE of 0.03875 and gameplay RMSE of
0.01266 exposed that false confidence and caused the exact-view render gate.

The two imported wheel-contact markers remain within 0.000945 m of their mesh
surfaces. Tool and companion sockets retain exact frames relative to LOD0.
Every named story material survives every tier in this proof.

## Truth boundary

This proves deterministic selection from supplied measurements, fresh-import
structure, representative still comparison, contact-marker proximity and
triangle/file reductions for this asset and camera policy. It does not prove a
continuous collision patch, animation contact through the clip, target-engine
playback, frame-time improvement, dynamic camera policy or user-perceived art
quality. A new engine, camera, scale, mesh or collision representation requires
new evidence.

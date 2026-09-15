# Creative Precision Fabric — executable mesh wave 5

Wave 5 gives UC's existing 3D creation body the same kind of deterministic fine-control layer added to raster, material, audio and timeline work.

It reuses the existing Spatial Studio primitive geometry (`cube`, `sphere`, `cylinder`, `cone`, `plane`, `torus`) rather than creating a second 3D foundation. A new bounded `axm.precision-mesh/v1` body makes the resulting triangle geometry directly editable through small operations.

## Public capability growth

The existing non-mesh Creative Hands registry remains **197 hands** with stable identities.

A separate 42-hand precision-mesh registry is aggregated through the same public `PlatformHands.creativeHands` service:

| mesh family | executable hands |
| --- | ---: |
| primitives | 6 |
| transforms | 8 |
| deforms | 8 |
| topology / repair | 9 |
| UV | 6 |
| analysis | 5 |
| **mesh total** | **42** |

Public aggregate after this wave:

- **239 executable creative hands**
- **246 callable creative recipes**

This modular split avoids turning one registry module into an ever-growing monolith while preserving one host-facing API.

## Primitive hands

- cube
- sphere
- cylinder
- cone
- plane
- torus

These call the already installed Spatial Studio geometry builders. Detail is bounded to 3..64 and the precision body caps mesh size at 200,000 vertices / 400,000 triangles.

## Transform hands

- translate
- non-uniform or uniform scale
- rotate X / Y / Z
- mirror X / Y / Z

Mirrors also repair triangle winding so orientation does not silently invert merely because a negative spatial transform was applied.

## Deform hands

- inflate along vertex normals
- Y-axis twist
- Y-dependent taper
- bounded bend
- flatten X / Y / Z
- seeded normal-direction noise displacement

Noise displacement is deterministic for the same mesh, seed and amount.

## Topology / repair hands

- recalculate vertex normals
- flip winding
- center origin
- normalize overall scale
- remove degenerate triangles
- compact unused vertices
- epsilon weld coincident vertices
- merge multiple precision meshes
- one-level midpoint triangle subdivision

Subdivision checks its projected triangle count before expansion. Mesh creation separately enforces the global vertex and triangle ceilings.

`weld` may intentionally convert split-face vertices into shared vertices and therefore may smooth formerly hard normal seams after normal recalculation. It is a geometry weld, not a preservation promise for authored split normals.

## UV hands

- planar X
- planar Y
- planar Z
- spherical projection
- cylindrical Y projection
- normalize existing UV extents to 0..1

These are deterministic projection tools. They are **not** seam-aware unwrap, island packing, texel-density optimization or distortion minimization. Those remain future mesh/UV work.

## Analysis hands

- bounds
- surface area
- signed / absolute volume
- vertex centroid
- indexed topology statistics

Topology statistics count adjacency in the indexed mesh. Split vertices on geometrically touching surfaces remain split until explicitly welded; the analysis does not silently infer geometric identity.

Signed/absolute volume is a mathematical triangle-soup calculation. A physical solid-volume claim additionally requires a closed, consistently wound manifold mesh; this hand does not infer that authority by itself.

## Public routing

`PlatformHands.creativeHands` now aggregates the original Creative Hands and the precision-mesh registry. Hosts continue to use the same functions:

- `list()`
- `get(id)`
- `invoke(id, args)`
- `audit()`
- `recipeRegistry()`
- `invokeRecipe(id, args)`

Mesh recipes use ids such as `mesh-primitive.sphere`, `mesh-transform.rotate-y`, `mesh-topology.weld` and `mesh-analysis.surface-area`.

## Verification

`creative-mesh-hands-selftest.js` verifies:

- exact 42 mesh-hand family census;
- exact public 239-hand / 246-recipe census;
- all six installed primitive routes;
- translations, non-uniform scale, all axis rotations and mirrors;
- all deform classes including seeded determinism;
- winding, centering, scale normalization, compaction, welding, merge, subdivision, degenerate removal and normal recalculation;
- all six UV hands with bounded UV results;
- area, volume, centroid, topology and bounds analyses;
- public recipe invocation through the same host-facing service;
- fail-closed primitive detail bounds.

The JavaScript proof is called by `tests/test_creative_precision_fabric.py` inside the normal full repository suite. Passing tests prove the declared deterministic operations, not high-end DCC parity or visual-quality acceptance.

Next useful mesh depth includes real face/edge selections, extrusion/inset/bevel, general mesh booleans, seam-aware unwrap and packing, remeshing/retopology, sculpt brushes and richer subdivision/smoothing contracts.

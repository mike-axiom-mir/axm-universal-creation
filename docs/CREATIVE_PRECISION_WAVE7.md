# Creative Precision Fabric — advanced mesh wave 7

Wave 7 continues the same rule used by the earlier creative-precision waves:

`influence -> smallest reusable primitive -> deterministic executor -> hand -> public routing -> exact proof`

It does not add a Blender/Maya-style application and does not copy DCC implementation or UI. It extends UC's existing `axm.precision-mesh/v1` body with bounded sculpt, UV editing, topology inspection and structural modifier operations.

## Public capability growth

Existing modular registries remain intact:

- core creative: 197 hands;
- precision mesh: 42 hands;
- face/edge/vertex mesh edit: 40 hands.

Wave 7 adds a separate **35-hand advanced mesh registry**:

| family | hands |
| --- | ---: |
| mesh sculpt | 8 |
| mesh UV edit | 11 |
| topology inspection | 9 |
| structural modifiers | 7 |
| **wave total** | **35** |

Public `PlatformHands.creativeHands` aggregate becomes:

- **314 executable creative hands**
- **321 callable creative recipes**

Older hand IDs and their owning registries do not change.

## Sculpt hands

- grab
- inflate
- deflate
- smooth
- pinch
- flatten
- twist
- seeded noise

Each sculpt operation uses a center/radius falloff field in the mesh's current coordinate space. Radius, strength, falloff power and vertex count are bounded. Output normals are recalculated after position changes.

These are deterministic position-domain sculpt brushes. They are **not** dynamic topology, multiresolution sculpting, voxel remeshing, cloth brushes, collision-aware sculpting or high-end DCC brush parity.

## UV edit hands

- translate
- scale
- rotate
- flip U
- flip V
- wrap into 0..1
- clamp into 0..1
- normalize selected UV extents
- selected planar X projection
- selected planar Y projection
- selected planar Z projection

UV edits consume the same digest-bound mesh selections introduced in Wave 6. A selection created for an older mesh cannot silently edit a newer mesh state.

UV storage is still per indexed vertex. Independent UV seams require split vertices/topology; this wave does not pretend one shared vertex can carry multiple corner UV values. It does **not** provide seam-aware unwrap, island detection/packing, texel-density solving or distortion minimization.

## Topology inspection hands

- boundary edge components
- face connected components
- face neighbors
- vertex neighbors
- edge incidence histogram
- indexed edge-manifold audit
- degenerate-face audit
- Euler characteristic
- shared-edge orientation audit

The `boundary-loops` hand reports connected boundary-edge components and whether each component has degree-two closed-loop topology. It does not promise an ordered cyclic traversal suitable for every downstream algorithm.

`manifold-audit` is an **indexed edge-manifold** check. A closed edge-manifold result is not proof against geometric self-intersection, duplicate overlapping shells, zero-volume regions or invalid physical solids.

Euler and adjacency results describe the indexed topology exactly; coincident-but-split positional vertices remain distinct until explicitly welded.

## Structural modifier hands

- solidify
- linear array
- radial array
- snap to grid
- snap near an axis-aligned plane
- axis shear
- fit exact bounds

Array operations reject projected vertex/triangle overflow before duplicating meshes. `fit-bounds` requires non-zero source extent on all three axes instead of inventing missing volume for flat input.

`solidify` duplicates vertices along stored/recalculated vertex normals, reverses the outer copy, and closes indexed boundary edges with side walls. It is deterministic and useful, but it does **not** guarantee mathematically constant shell thickness around sharp corners, concavities or self-intersections. Closed inputs produce nested offset shells without boundary side walls.

Snap operations may create coincident vertices or degenerate triangles; they do not silently weld or repair topology. Array copies are merged into one indexed body but overlapping copies are not automatically boolean-unioned or welded.

## Bounds

The underlying precision-mesh ceilings remain authoritative:

- 200,000 vertices;
- 400,000 triangles.

Additional Wave 7 bounds include:

- sculpt execution limited to 100,000 vertices per call;
- sculpt radius/strength/falloff bounds;
- radial and linear arrays limited to 128 copies and preflighted against mesh ceilings;
- UV transform magnitudes bounded;
- full face/vertex neighbor maps bounded to 100,000 elements;
- fit-bounds fails on zero source extent.

## Public routing

The existing modular public service now aggregates four registries through the same API:

- `list()`
- `get(id)`
- `invoke(id, args)`
- `audit()`
- `recipeRegistry()`
- `invokeRecipe(id, args)`

Example IDs:

- `creative.mesh-sculpt.grab`
- `creative.mesh-uv-edit.rotate`
- `creative.mesh-topology-inspect.manifold-audit`
- `creative.mesh-modifier.solidify`

Recipe IDs omit the `creative.` prefix, for example `mesh-modifier.solidify`.

## Verification

`creative-mesh-advanced-hands-selftest.js` proves:

- exact 35-hand family census;
- exact public 314-hand / 321-recipe census;
- execution of all eight sculpt classes;
- seeded sculpt determinism;
- all eleven UV edit routes;
- open-plane boundary/manifold/Euler/adjacency diagnostics;
- closed welded-cube manifold inspection;
- disconnected-component detection;
- solidify triangle/vertex growth;
- linear/radial array growth;
- grid/plane snapping;
- shear and exact fit-bounds;
- flat-input fit-bounds rejection;
- preflight rejection of an over-budget array;
- public recipe invocation.

The proof is bound into `tests/test_creative_precision_fabric.py` and therefore the normal repository suite. Passing proves the declared deterministic contracts, not visual-quality acceptance or general DCC parity.

## Next useful depth

High-value gaps after this wave include connected-region inset, real edge bevel/chamfer, loop/ring traversal, UV seam marking and island packing, mesh booleans, self-intersection tests, remeshing/retopology, richer sculpt masking/symmetry and higher-quality subdivision/surface contracts.

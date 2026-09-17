# Mesh Topology Inspector v0

`axm_uc.mesh_topology.inspect_mesh_topology()` is a bounded deterministic structural diagnostic for triangle meshes.

It exists to close specific 3D-production evidence gaps: a mesh can have finite vertices, in-range indices, non-degenerate triangles and locally matching normals while still contain open seams, more than two faces on one edge, inconsistent shared-edge winding, triangles that collapse when duplicate seam vertices are welded, source-array vertices that are no longer referenced by any triangle, or an exact source index whose incident triangles split into disconnected edge-connected fans.

## Input

- `positions`: up to 131,072 finite XYZ source vertices.
- `indices`: a flat triangle index list, up to 131,072 triangles.
- `weld_tolerance`: finite positive positional tolerance, default `1e-6` in caller units.

The inspector never edits source geometry. It measures exact source-array liveness and exact source-index vertex-fan connectivity from the validated source index stream before any welding. It then clusters first-seen positional representatives only for edge-topology measurement. Clustering is deliberately non-transitive so intermediate vertices cannot bridge a seam wider than the requested tolerance.

## Reported evidence

The report includes:

- source vertex count;
- referenced and unreferenced source-vertex counts;
- `all_source_vertices_referenced` as a read-only liveness fact;
- bounded deterministic source-index examples for unreferenced vertices;
- exact source indices whose incident non-collapsed-by-index triangles form more than one edge-connected fan;
- count of source vertices for which a fan was observed;
- disconnected source-index fan count and maximum fan-component count;
- `all_referenced_source_vertex_fans_connected` as a fail-closed read-only fan-completeness fact;
- seam-clustered vertex count and reduction;
- triangle and valid-triangle counts;
- triangles that collapse after seam clustering;
- unique welded-edge count;
- boundary-edge count;
- edges with more than two incident triangles;
- shared two-face edges whose directions agree instead of oppose;
- edge-connected triangle-component count;
- bounded deterministic examples for repair;
- one conservative edge-status family:
  - `CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE`
  - `OPEN_EDGE_MANIFOLD_CANDIDATE`
  - `INVALID_EDGE_TOPOLOGY`

The word **candidate** matters. Edge incidence, source-index fans and orientation are not a full manifold or geometry proof.

Source-vertex liveness and source-index vertex-fan connectivity are intentionally separate from the existing status values. An unreferenced source vertex or a disconnected exact-source fan does **not** silently change a historical edge-topology status. Callers that require stronger structure must explicitly gate on the corresponding fields and bind that stronger claim to the observer version they actually ran.

## Source-index vertex-fan meaning

For every exact source index referenced by at least one source-index-noncollapsed triangle, the inspector asks whether all of those incident triangles form one connected fan when adjacency is allowed only through a source edge containing that same source index.

This catches the classic bow-tie case where two otherwise closed surface components touch at only one shared source vertex. Every edge can still have two incident faces, yet the shared source index has two disconnected incident-triangle fans.

The fan observer deliberately runs before positional welding. That keeps intentional split source vertices used for hard-normal, UV or material seams distinct and avoids pretending that coincident source entries have one proven shared neighborhood. Unreferenced source vertices remain a separate liveness fact. Exact-index-collapsed source triangles are excluded from fan construction; because their referenced indices are then not fully observed, `all_referenced_source_vertex_fans_connected` fails closed while the existing collapsed-triangle gate independently makes the edge topology invalid.

Therefore `all_referenced_source_vertex_fans_connected=true` means only that every referenced exact source index was observed through at least one non-collapsed-by-index source triangle and has one incident triangle fan under this contract. It does **not** establish seam-welded geometric vertex-manifoldness.

## Bounded-work contract

Issue #186 exists specifically because an earlier intermediate expansion of PR #184 was rejected during integration review: that version expanded every incident face against every neighbor on a high-incidence source edge and could become quadratic under UC's existing 131,072-triangle ceiling.

The retained fan observer instead builds source face/edge incidence once. For each exact source vertex it unions the faces incident to each source edge containing that vertex by one anchor-to-rest pass. A source edge with `k` incident faces therefore contributes linear `k` union work at each endpoint rather than `k²` pair expansion. The implementation keeps the existing global vertex/triangle ceilings and exposes `fan_work_bounded_by_source_face_edge_incidence=true` in its truth boundary.

A regression fixture exercises 1,024 triangles on one source edge: edge topology correctly reports that edge as non-manifold while the two shared endpoint fans remain one connected component. This is structural regression evidence for the bounded incidence algorithm, not a general performance benchmark.

## Truth boundary

This v0 check does **not** establish:

- permission to delete, compact, weld or otherwise mutate an unreferenced source vertex;
- permission to split, merge or repair a disconnected source-index fan;
- source/lineage semantics for why a vertex is unreferenced or fan-disconnected;
- seam-welded geometric vertex-manifoldness;
- freedom from self-intersection;
- UV quality;
- normals/tangents beyond shared-edge winding;
- rig/deformation quality;
- collision or physics suitability;
- LOD quality;
- target-engine compatibility;
- rendered or artistic quality.

A closed oriented edge-manifold candidate can still fail any of those later gates. Likewise, an unreferenced source vertex or disconnected source-index fan is an observed structural fact, not automatic authorization to repair it.

## Structural fixtures

The regression suite applies the inspector to Universal Creation's existing box, pyramid and cylinder generators. Those fixtures intentionally duplicate positions across hard-normal faces/caps, so they exercise the positional seam-clustering path instead of only testing already-index-welded toy meshes. The duplicated source vertices remain correctly classified as referenced, and each referenced exact source index retains one connected incident fan because both source observations happen before positional welding.

Additional fixtures hold open boundaries separate from invalid topology and reproduce non-manifold shared edges, same-direction shared-edge winding, tolerance-caused triangle collapse, disconnected edge components, malformed inputs, a closed edge-topology candidate with an unreferenced source vertex, deterministic bounded reporting of multiple unused source indices, one exact-index-collapsed triangle that fails fan completeness closed, a 1,024-face high-incidence source edge, and two individually closed tetrahedra that share only one exact source vertex. That last fixture keeps the historical closed-oriented edge status while exposing one source index with two disconnected incident-triangle fans, proving the new observer adds information without silently rewriting old status semantics.

## Provenance of the reusable fan pattern

Two independent AXM product domains reached the same structural need before this reusable placement:

- Animal Geometry retained an Animal-local indexed vertex-fan diagnostic for its connected forelimb candidate and a bow-tie negative control at exact historical tested commit `002f6754f7d367b114352883565c6e28a4f07ac8`.
- Character Geometry independently used a local indexed vertex-fan preflight while rebuilding review-006 connected shoulder topology at exact head `8ad006f91ebb9934d5df98702e4410c74a1e68ea`.

Neither inspected donor revision exposes a repository license file, so UC does **not** copy either implementation. The shared structural contract is independently implemented here from the observed requirement and re-tested against UC's own fixtures. Product PASS states do not transfer.

PR #184 remains the liveness-only parent. Its integration review explicitly rejected widening that PR with the earlier unbounded fan helper. Issue #186 and the successor fan lane preserve that decision instead of silently rewriting it.

## Integration boundary

This remains a reusable read-only Python geometry primitive. It does not declare a new live Machine capability, add a generic prune/split/weld repair transform, or silently change the acceptance semantics of `procedural_3d.verify_glb()` or any existing asset pipeline. That avoids upgrading old `VALIDATED_DETERMINISTIC_GLB_ASSET` or edge-manifold-candidate receipts to stronger source-liveness or source-fan claims without an explicit rebind.

Existing product and UC receipts remain truthful for the exact observer identity they ran. A consumer that needs source-array liveness or source-index fan connectivity must pin a successor UC identity, rerun its own evidence, and separately retain authority for any mutation or adoption decision.

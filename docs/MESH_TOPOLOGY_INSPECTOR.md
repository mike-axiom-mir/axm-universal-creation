# Mesh Topology Inspector v0

`axm_uc.mesh_topology.inspect_mesh_topology()` is a bounded deterministic structural diagnostic for triangle meshes.

It exists to close a specific 3D-production evidence gap: a mesh can have finite vertices, in-range indices, non-degenerate triangles and locally matching normals while still contain open seams, more than two faces on one edge, inconsistent shared-edge winding, triangles that collapse when duplicate seam vertices are welded, or source-array vertices that are no longer referenced by any triangle.

## Input

- `positions`: up to 131,072 finite XYZ source vertices.
- `indices`: a flat triangle index list, up to 131,072 triangles.
- `weld_tolerance`: finite positive positional tolerance, default `1e-6` in caller units.

The inspector never edits source geometry. It measures exact source-array liveness from the validated source index stream before any welding. It then clusters first-seen positional representatives only for edge-topology measurement. Clustering is deliberately non-transitive so intermediate vertices cannot bridge a seam wider than the requested tolerance.

## Reported evidence

The report includes:

- source vertex count;
- referenced and unreferenced source-vertex counts;
- `all_source_vertices_referenced` as a read-only liveness fact;
- bounded deterministic source-index examples for unreferenced vertices;
- seam-clustered vertex count and reduction;
- triangle and valid-triangle counts;
- triangles that collapse after seam clustering;
- unique welded-edge count;
- boundary-edge count;
- edges with more than two incident triangles;
- shared two-face edges whose directions agree instead of oppose;
- edge-connected triangle-component count;
- bounded deterministic examples for repair;
- one conservative status:
  - `CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE`
  - `OPEN_EDGE_MANIFOLD_CANDIDATE`
  - `INVALID_EDGE_TOPOLOGY`

The word **candidate** matters. Edge incidence and orientation are not a full manifold or geometry proof.

Source-vertex liveness is intentionally separate from the existing status values. An unreferenced source vertex does **not** silently change a historical edge-topology status. Callers that require every source-array entry to participate in the triangle stream must explicitly gate on `all_source_vertices_referenced` and bind that stronger claim to the observer version they actually ran.

## Truth boundary

This v0 check does **not** establish:

- permission to delete, compact, weld or otherwise mutate an unreferenced source vertex;
- source/lineage semantics for why a vertex is unreferenced;
- vertex-neighborhood manifoldness;
- freedom from self-intersection;
- UV quality;
- normals/tangents beyond shared-edge winding;
- rig/deformation quality;
- collision or physics suitability;
- LOD quality;
- target-engine compatibility;
- rendered or artistic quality.

A closed oriented edge-manifold candidate can still fail any of those later gates. Likewise, an unreferenced source vertex is an observed liveness fact, not automatic authorization to prune it.

## Initial structural fixtures

The regression suite applies the inspector to Universal Creation's existing box, pyramid and cylinder generators. Those fixtures intentionally duplicate positions across hard-normal faces/caps, so they exercise the positional seam-clustering path instead of only testing already-index-welded toy meshes. The duplicated source vertices remain correctly classified as referenced because liveness is measured before positional welding.

Additional fixtures hold open boundaries separate from invalid topology and reproduce non-manifold shared edges, same-direction shared-edge winding, tolerance-caused triangle collapse, disconnected components, malformed inputs, a closed edge-topology candidate with an unreferenced source vertex, and deterministic bounded reporting of multiple unused source indices.

## Integration boundary

This pass remains a reusable read-only Python geometry primitive. It does not declare a new live Machine capability, add a generic prune transform, or silently change the acceptance semantics of `procedural_3d.verify_glb()` or any existing asset pipeline. That avoids upgrading old `VALIDATED_DETERMINISTIC_GLB_ASSET` or edge-manifold-candidate receipts to stronger source-liveness claims without an explicit rebind.

Existing product and UC receipts remain truthful for the exact observer identity they ran. A consumer that needs source-array liveness must pin a successor UC identity, rerun its own evidence, and separately retain authority for any mutation or adoption decision.

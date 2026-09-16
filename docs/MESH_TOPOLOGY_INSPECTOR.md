# Mesh Topology Inspector v0

`axm_uc.mesh_topology.inspect_mesh_topology()` is a bounded deterministic structural diagnostic for triangle meshes.

It exists to close a specific 3D-production evidence gap: a mesh can have finite vertices, in-range indices, non-degenerate triangles and locally matching normals while still contain open seams, more than two faces on one edge, inconsistent shared-edge winding, or triangles that collapse when duplicate seam vertices are welded.

## Input

- `positions`: up to 131,072 finite XYZ source vertices.
- `indices`: a flat triangle index list, up to 131,072 triangles.
- `weld_tolerance`: finite positive positional tolerance, default `1e-6` in caller units.

The inspector never edits source geometry. It clusters first-seen positional representatives only for measurement. Clustering is deliberately non-transitive so intermediate vertices cannot bridge a seam wider than the requested tolerance.

## Reported evidence

The report includes:

- source and seam-clustered vertex counts;
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

## Truth boundary

This v0 check does **not** establish:

- vertex-neighborhood manifoldness;
- freedom from self-intersection;
- UV quality;
- normals/tangents beyond shared-edge winding;
- rig/deformation quality;
- collision or physics suitability;
- LOD quality;
- target-engine compatibility;
- rendered or artistic quality.

A closed oriented edge-manifold candidate can still fail any of those later gates.

## Initial structural fixtures

The regression suite applies the inspector to Universal Creation's existing box, pyramid and cylinder generators. Those fixtures intentionally duplicate positions across hard-normal faces/caps, so they exercise the positional seam-clustering path instead of only testing already-index-welded toy meshes.

Additional fixtures hold open boundaries separate from invalid topology and reproduce non-manifold shared edges, same-direction shared-edge winding, tolerance-caused triangle collapse, disconnected components and malformed inputs.

## Integration boundary

This first pass is a reusable Python geometry primitive only. It does not declare a new live Machine capability and does not silently change the acceptance semantics of `procedural_3d.verify_glb()` or any existing asset pipeline. That avoids upgrading old `VALIDATED_DETERMINISTIC_GLB_ASSET` receipts to stronger topology claims without an explicit contract.

If repeated design-repo evidence shows the report is useful, the Technical Art / UC integration lane can bind it into an explicit machine/export acceptance contract later. Existing receipts must remain scoped to the checks they actually ran.

# Static Asset Budget Evidence v0.1

`axm_uc.static_asset_budget.inspect_static_asset_budget()` adds a bounded, renderer-neutral resource-budget gate for actual static GLB artifacts.

## Why this exists

The Workshop / Profession Fabric review of the current improvised workshop found that UC could already inspect real geometry, UVs, normals, embedded images, topology, hard-surface frames, and clearance/contact, but still lacked a reusable way to say:

> this exact asset is over or under **this project's declared resource budget**.

That missing distinction matters. A high triangle count, many material batches, large textures, or widespread double-sided materials are not automatically wrong. The target context must provide the limits.

## Contract

Schema: `axm.static-asset-budget/v0.1`

A contract must declare at least one explicit non-negative maximum:

- `max_triangles`
- `max_vertices`
- `max_primitives`
- `max_material_batches`
- `max_unique_materials`
- `max_embedded_images`
- `max_compressed_image_bytes`
- `max_estimated_rgba8_mip_bytes`
- `max_double_sided_materials`
- `max_double_sided_batches`

No default quality budget is invented by UC.

## What is measured

For the actual instantiated **default scene**:

- triangle count;
- vertex count;
- primitive count;
- mesh-instance count;
- material-batch count;
- unique material count, including the core default material when used;
- unique referenced core textures;
- unique referenced embedded PNG/JPEG images;
- compressed embedded image bytes;
- deterministic estimated uncompressed RGBA8 mip-chain bytes from actual image dimensions;
- unique double-sided materials;
- instantiated double-sided material batches.

A reused mesh contributes once per default-scene node instance to triangle, vertex, primitive, and material-batch counts. Unique materials/images remain deduplicated identities.

## PASS / FAIL / HOLD

- `PASS`: every requested budget maximum is met by the supported measured subset.
- `FAIL`: at least one explicit maximum is exceeded, or the artifact is structurally invalid for the supported subset.
- `HOLD`: the evidence would require guessing through unsupported deformation, encodings, external media, or resource-affecting material extensions.

External images are never fetched.

## Important truth boundary

This evidence does **not** prove or estimate:

- FPS or frame-time;
- target-engine import correctness;
- draw-call timing;
- real GPU memory after engine compression/streaming;
- collision or navigation correctness;
- LOD visual/perceptual equivalence;
- gameplay readability;
- aesthetic or Art Director acceptance;
- whether a double-sided material is actually unnecessary;
- whether any specific optimization should be performed.

The RGBA8 mip value is an explicit deterministic uncompressed estimate, not a GPU-memory claim.

The intended workflow is:

`target/project defines budget -> UC measures actual artifact -> PASS/FAIL/HOLD -> specialists decide what, if anything, should change`

This keeps optimization pressure grounded in an explicit target instead of letting UC silently invent a universal score.

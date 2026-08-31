# AXM Engine-Ready 3D Forge

The 3D forge is a retained machine capability. Blender is its rendering and
interchange runtime; request compilation, faction builders, export policy,
inspection, evidence, and learning remain inside AXM Universal Creation.

## Outputs

Each accepted run creates:

- editable `.blend` source;
- separate GLB files for LOD0, LOD1, and LOD2;
- a separate `UCX_`-named collision GLB;
- multi-angle PNG render proofs;
- an asset manifest and a decoded-GLB forge receipt.

The GLB inspector parses the container and JSON chunk directly. It reports real
node, mesh, primitive, triangle, material, image, and texture counts; it does not
infer them from filenames or Blender logs.

## Runtime bootstrap

The catalog pins Blender 5.2.1 LTS for Windows x64:

- URL: `https://mirror.blender.org/release/Blender5.2/blender-5.2.1-windows-x64.zip`
- SHA-256: `0e631dad7d0cad6d5d18abdd2e2550f6c0213215334eda00ddbd3d22b96ecb2c`

Set `AXM_BLENDER` to the verified executable or pass `--blender`. The runtime is
replaceable; the machine's contracts do not depend on a manually edited Blender
session.

## Commands

```text
axm-assets 3d-catalog
axm-assets 3d-plan request.json
axm-assets 3d-forge request.json output/asset --blender path/to/blender
axm-assets inspect-glb output/asset/asset_LOD0.glb
```

Example request:

```json
{
  "asset_id": "axiom-bastion-frame",
  "seed": 41027,
  "quality": "hero",
  "render_resolution": 768,
  "angles_degrees": [32, 122, 212, 302]
}
```

## Quality admission

Structural success is not an AAA-quality claim. An asset is not accepted merely
because Blender exported it or the GLB parses. Review must cover:

1. faction identity and silhouette at RTS distance;
2. large, medium, and small form hierarchy;
3. believable load paths, articulation, weapon and shield integration;
4. PBR material response and surface breakup;
5. front, side, and rear topology rather than a detailed facade;
6. LOD preservation, grounded pivot, scale, and collision coverage;
7. rendered comparison with the approved target.

Failed render comparisons remain evidence for the exact asset context. They do
not become global style rules, and a generated mesh is not admitted because a
neural or procedural backend produced it.

## Backend evidence

- Blender 5.2.1 LTS: admitted as the deterministic modeling, render, and export runtime.
- TripoSR CPU proposal path: executable on the tested non-CUDA host, but rejected
  for the Axiom hard-surface hero because its multi-angle render collapsed the
  weapon, shield, limbs, and rear structure into a connected surface blob.

The rejected result is not an engine-ready asset. Its Windows short-path and CPU
marching-cubes findings may inform a future bounded proposal backend.

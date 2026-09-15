# Offline game pose runtime

`GamePoseAsset` evaluates actual GLB animation into local transforms, world
matrices, attachment positions and optionally skinned vertex positions. Python
3.11+ and its standard library are sufficient. No AI, graphics library, browser
or game engine is needed for this operation.

```python
from axm_uc.game_pose_runtime import load_game_pose_glb

asset = load_game_pose_glb("AXM_Parcel_Imp_LOD0.glb")
description = asset.describe()
pose = asset.sample("Package_Launch", 0.3, vertices=True)
socket = next(n["index"] for n in description["nodes"]
              if n["name"] == "Socket.Package")
position = asset.point(pose, socket)
```

CLI uses the same implementation:

```sh
axm-assets pose-runtime-catalog
axm-assets pose-sample character.glb pose-request.json new-output-directory
```

Example request:

```json
{
  "clip": "Delivery_Dash",
  "time_s": 0.2,
  "loop": false,
  "blend": {
    "clip": "Idle_Parcel_Panic",
    "time_s": 0.6,
    "loop": true,
    "weight": 0.4
  },
  "vertices": false
}
```

The blend weight is the target contribution: zero is the specified source pose;
one is the target pose. Translation/scale mix linearly and rotations follow the
shortest quaternion arc. Each sample starts from the original rest pose, so a
channel absent from a clip cannot leak from an earlier clip. The caller chooses
both clocks and the blend weight; no hidden wall clock or transition policy is
introduced. With no clip, sampling returns the rest pose.

Non-looping samples clamp to the clip's end; looping samples wrap, with exactly
one duration returning to time zero. Individual tracks clamp before their first
key and after their last key. The evaluator supports LINEAR and STEP tracks.
`start_s` records the first authored key; `duration_s` is the last timestamp in
the unchanged GLB time domain. An initial gap holds the first value and is not
silently subtracted. Reference importers must align their frame range to that
authored interval when comparing poses.

## Portable coordinates and root ownership

The GLB's coordinate system is retained (normally glTF Y-up, metres). Outputs
use **row-major matrices multiplying column vectors**. GLB matrix accessors are
column-major and are transposed once on intake. Hierarchies compose parent ×
local. A socket point is transformed by its node's complete world matrix.

`skin_world_matrices` are joint-world × inverse-bind matrices. Weighted vertex
positions are already in scene space. The mesh node's transform must not be
applied again. These matrices can also be given to another implementation;
they are not a renderer-specific resource.

Authored root movement is already in the pose. The previous animation-state
runtime's `world_translation_m` is a separate trajectory estimate. **Do not add
it to this pose blindly:** that would apply movement twice. Its linear
distance-over-duration estimate also need not match the asset's authored
acceleration. A future binding should choose an explicit motion owner and use
the actual root curve when extracting/applying movement. This pass does not
silently remove a root track or fabricate that binding.

## Supported input and bounded failures

Intake supports embedded GLB 2.0 buffers, static affine node matrices or TRS,
named animation clips, float transform channels, strided accessors, float or
normalized unsigned-byte/unsigned-short weights, and four influences per vertex.
Near-unit quantized weight sums are normalized explicitly; malformed, negative,
zero-total and substantially non-unit weights are rejected.

External buffers, sparse/compressed geometry, morphs, animation extensions,
CUBICSPLINE and additional skin-influence sets are rejected when relevant to
pose evaluation. The asset's materials and textures are retained in the original
file; this evaluator does not interpret their appearance. Non-pose required
material/texture extensions are allowed. All document nodes are evaluated,
including nodes outside the selected scene; this is an asset pose API, not a
scene-visibility selector.

Input is limited to 64 MiB, JSON to 4 MiB, nodes to 2,048, decoded accessor
scalars to four million, and instantiated vertices to 250,000. Cycles, multiple
parents, duplicate animation targets/names, nonfinite data, missing references,
misaligned/out-of-range accessors and unsupported transform encodings fail.

The publisher stages `asset.json`, `request.json` and `pose.json` and refuses
existing destinations. On a write failure, temporary output is cleaned. It
does not copy, simplify or rewrite the source GLB. Its SHA-256 binds the output
to the exact supplied bytes. This is a file identity, not artistic acceptance.

## Evidence

`tests/test_game_pose_runtime.py` uses analytical GLB fixtures with an offset
rig, a different mesh-node transform, inverse bind matrices, mixed weights and
an articulated hinge. Expected positions are independent geometric results.
Cases cover quaternion sign equivalence, blend endpoints/midpoints, striding,
integer weights, static matrices, loop boundaries and rejected inputs.

`tools/blender/game_pose_runtime_roundtrip.py` is an additional reference gate:
it independently re-imports both GLBs rebuilt by the existing Parcel Imp source,
evaluates three clips at six authored keyframes each, and compares all 16 joint
origins and the complete deformed vertex point sets. A fresh Blender process is
the reference; the production sampler uses no Blender code. Both directional
nearest-point errors must remain under 0.00002 metres. Vertex order/topology is
not inferred from this point-set comparison. Between-key SLERP and crossfades
have analytical unit coverage; native crossfade playback is not claimed.

The `Offline game pose evidence` Actions artifact carries the rebuilt GLBs,
editable Blender source and `pose-runtime-comparison.json`. Its actual job result
determines whether the real-asset reference passed. It must not be inferred from
the unit tests or from this document.

No shading, deformed normals/tangents, physics, constraints/IK, automatic
transition blending, continuous visual playback or device performance is
claimed. The new capability is portable pose execution and its geometric
evidence, with the original styles and richer editable source intact.

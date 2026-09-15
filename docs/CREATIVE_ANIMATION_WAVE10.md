# Creative Animation Wave 10 — canonical rigging and animation body

Wave 10 gives Universal Creation an editable deterministic rig/animation body over the same public Creative Hands and Creative Flow surfaces introduced in earlier waves.

It reuses the existing `advanced-3d.js` deformation and two-bone IK math where applicable rather than creating a second skinning solver.

## Public capability growth

Existing public body after Wave 9:

- 340 executable creative hands
- 347 callable creative recipes

Wave 10 adds **48 executable hands**:

| family | hands |
| --- | ---: |
| rig-skeleton | 9 |
| rig-pose | 11 |
| rig-skin | 8 |
| animation-blendshape | 6 |
| animation-clip | 13 |
| rig-ik | 1 |
| **total** | **48** |

Public aggregate after Wave 10:

- **388 executable creative hands**
- **395 callable creative recipes**

## Skeleton state

`axm.precision-skeleton/v1` stores up to 512 explicitly named bones with:

- parent relationship or root status;
- local rest translation;
- normalized quaternion rest rotation;
- non-zero local rest scale;
- optional metadata.

The skeleton constructor rejects duplicate IDs, missing parents, self-parenting and parent cycles. Multiple roots are allowed and remain explicit.

Executable skeleton hands:

- create;
- add bone;
- remove a leaf bone;
- rename a bone while repairing child parent references;
- reparent;
- set rest transform;
- calculate world rest matrices;
- inspect an ancestor chain;
- validate finite world state.

This is an editable hierarchy contract, not an automatic humanoid/creature rig generator.

## Pose state

`axm.precision-pose/v1` binds one exact skeleton digest and stores a complete local TRS transform for every bone.

Pose hands support:

- create rest pose;
- set absolute local transform;
- translate a bone;
- rotate by Euler delta;
- rotate by quaternion delta;
- scale;
- reset one bone to rest;
- copy one local bone transform to another;
- blend two poses;
- calculate world matrices;
- clamp local translation to explicit bounds.

Quaternion pose blending uses normalized shortest-hemisphere linear interpolation. It is deterministic **NLERP**, not SLERP/SQUAD or a claim of animator-authored arc quality.

## Skin state and deformation

`axm.precision-skin/v1` binds an exact precision mesh and exact skeleton. It stores:

- one to eight bone influences per vertex;
- explicit non-negative weights;
- inverse bind matrices derived from rest-world transforms.

Skin hands support:

- create explicit weights;
- normalize weights;
- prune low weights and renormalize;
- limit influences;
- set one vertex's influences;
- nearest-rest-bone rigid binding;
- validate normalization;
- deform a precision mesh from an exact pose.

Actual deformation reuses the existing deterministic advanced-3D linear skinning kernel. The hand converts named bones to joint indices and applies `poseWorld * inverseBind` matrices before returning a new precision mesh with recalculated normals.

### Skinning truth boundary

This is linear blend skinning. It does **not** claim:

- dual-quaternion skinning;
- heat-map or geodesic auto-weighting;
- muscle/fat/tissue simulation;
- corrective volume preservation;
- automatic joint-collision repair;
- production-quality deformation judgment.

`nearest-bind` is intentionally a simple deterministic foundation. It assigns each vertex wholly to the nearest rest-pose bone origin; it is not represented as professional automatic weighting.

## Blendshapes

`axm.precision-blendshape-set/v1` binds an exact mesh and stores named per-position delta arrays.

Hands support:

- create a blendshape set;
- add shape;
- remove shape;
- replace shape deltas;
- scale one shape;
- apply explicit named weights to produce a new precision mesh.

Blendshape weights can also be supplied to the skin-deform hand so morph deltas are applied before skinning by the reused advanced-3D kernel.

Unknown public blendshape weight names fail closed instead of being silently ignored.

This is position-delta morphing. Normal/tangent delta authoring, in-betweens, driver graphs and corrective-pose systems remain future work.

## Animation clips and keyframes

`axm.precision-animation-clip/v1` binds one exact skeleton and supports up to 2,048 tracks. Tracks target one bone plus one property:

- translation;
- rotation quaternion;
- scale.

Each track has one interpolation policy:

- `hold`;
- `linear`;
- `smoothstep`.

Executable clip hands:

- create;
- add/remove track;
- set/delete key;
- shift key times within a clip;
- uniformly scale clip time;
- trim with sampled boundary keys;
- reverse;
- repeat/loop;
- concatenate two clips on the same skeleton;
- sample an exact pose at a requested time;
- bake bounded pose samples at a requested FPS.

Quaternion track interpolation uses the same deterministic shortest-hemisphere normalized linear interpolation described above.

Baking produces retained **pose states**, not rendered frames or visual-quality evidence.

### Clip truth boundary

Wave 10 clips do not yet provide:

- animation events/markers;
- blendshape-weight tracks;
- bezier/F-curve tangent handles;
- layered/NLA animation stacks;
- generalized constraint graphs;
- motion-warping;
- root-motion extraction contracts;
- motion-capture cleanup;
- physical secondary motion;
- perceptual animation-quality judgment.

Those remain valid future capabilities.

## Two-bone IK

`creative.rig-ik.two-bone-solve` exposes the already-installed analytic two-bone kernel through the public hands body. Inputs are root point, target point and two positive segment lengths; output includes reachability, distance, shoulder angle and elbow angle.

It is **solve evidence**, not a generalized rig mutation. Wave 10 does not silently invent a pole vector, rest orientation or bone-axis convention and therefore does not claim to write the solved angles into an arbitrary skeleton pose automatically.

A future pose-IK layer can add explicit chain-axis/pole/rest-orientation contracts on top of this evidence.

## Creative Flow integration

No special animation planner is added.

The 48-hand registry joins `creative-hands-service`, so Wave 8 Creative Flow automatically sees the new families.

The Wave 10 proof executes this real cross-organ graph:

`skeleton -> animation clip -> sampled pose`

in parallel with:

`mesh -> nearest skin bind`

then:

`sampled pose + mesh + skin -> skinned deformation -> mesh bounds`

All state references are resolved through the existing deterministic flow contract and the resulting steps emit normal Creative Flow receipts.

## Explicit non-claims / next animation depth

Still missing or intentionally incomplete:

- automatic rig generation / bone placement;
- generalized IK with pole vectors, joint limits and pose application;
- FK/IK switching state;
- constraint graphs (aim, parent, copy, distance, spline etc.);
- animation layers and nonlinear clip blending;
- robust skeleton-to-skeleton retargeting;
- humanoid semantic mapping;
- motion capture import/cleanup;
- root-motion extraction/application contracts;
- animation events;
- blendshape animation tracks/drivers;
- spring/secondary-motion rig solvers;
- dual-quaternion or corrective skinning;
- rendered animation acceptance or aesthetic quality judgment.

These are the next useful animation families, not capabilities Wave 10 pretends are already present.

## Verification

`creative-animation-hands-selftest.js` verifies:

- exact 48-hand family census;
- exact public **388-hand / 395-recipe** census;
- hierarchy edits, cycle-safe rebuilds, rest/world matrices and chains;
- every pose operation;
- explicit skin creation, normalization, pruning, influence limiting, vertex editing, nearest binding and actual mesh deformation;
- blendshape CRUD, scaling, mesh application and morph+skin composition;
- all 13 clip/keyframe operations;
- pose sampling and bounded baking;
- analytic two-bone IK evidence;
- a real Creative Flow graph crossing skeleton, clip, pose, mesh, skin and mesh-analysis families.

The selftest is bound into `tests/test_creative_precision_fabric.py`, so exact PR-head repository CI must pass before merge.

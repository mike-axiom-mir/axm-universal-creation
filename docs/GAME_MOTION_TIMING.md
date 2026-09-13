# Game motion timing

`axm_uc.game_motion_timing` deterministically turns explicit local rest/action
transforms into fully sampled animation tracks. It adds readable temporal
phrasing without inventing a rig, changing geometry/material identity, or
depending on an AI or paid service.

Four profiles are available:

| Profile | Character |
| --- | --- |
| `restrained-product` | Deliberate, small overshoot, suitable for product/mechanical motion |
| `weighty-salvage` | Long wind-up, late acceleration, heavy impact and restrained rebound |
| `snappy-comic` | Early impact, large anticipation and comic counter-overshoot |
| `springy-adventure` | Fast action with the broadest settle oscillation |

Every profile authors seven quantized phase events: rest, anticipation,
impact, recoil, counter, settle and complete. Action timing is eased into the
impact, while every exported sample is ordinary `LINEAR` data so the authored
curve survives a portable GLB bake without requiring a custom interpolator.
Quaternion channels use normalized shortest-hemisphere interpolation.

## Request

```json
{
  "name": "Hammer_Slam",
  "fps": 30,
  "duration": 1.2,
  "loop": true,
  "channels": [
    {
      "target": "Hammer",
      "path": "rotation",
      "rest": [0, 0, 0, 1],
      "action": [0, 0, -0.70710678, 0.70710678],
      "anticipation_scale": 0.8,
      "contact_at_impact": true
    }
  ]
}
```

Rotation arrays use glTF order `[x, y, z, w]`. Translation and scale arrays
have three values. The composer bounds FPS, duration, track count and values;
rejects duplicate channels, non-normalized quaternions and scale inversion;
and never mutates the request.

```sh
axm-assets motion-timing-catalog
axm-assets motion-compose motion-request.json out/slam --profile weighty-salvage
```

Publication is transactional and refuses an existing destination. It retains
`source.json`, a portable `motion-clip.json`, and `motion-receipt.json` with the
source digest, exact impact checks, measured action acceleration, quaternion
normalization and loop-seam evidence.

## Blender round trip

`tools/blender/game_motion_timing_roundtrip.py` builds the original AXM
Clockwork Smacker: a squat salvage inspection bot with asymmetrical machinery,
a clock face, crowned duck, layered hammer, quality bell and comic inspection
tag. The proof uses one six-bone rigid mechanical rig and the same explicit
rest/action endpoints for every timing profile.

The build exports LOD0 and LOD1 GLBs plus editable Blender source. A separate
fresh process imports both GLBs, selects every named action, checks its frame
range, measures the world-space loop seam and measures the `ImpactMarker` to
`ImpactTarget` gap. Representative anticipation, impact, recoil and settle
frames are rendered from the imported LOD0, not the unexported authoring scene.

The proof does not establish target-engine playback, controller/state-machine
integration, audio synchronization, soft deformation, IK surface solving,
frame-time performance or complete perceptual animation acceptance. The bell
contact is an authored marker relationship, not a general contact solver.


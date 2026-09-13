# Game secondary motion

`axm_uc.game_secondary_motion` derives portable follow-through tracks from an
existing `axm.game-motion-timing/v0.1` composition. It is deterministic,
offline, bounded and renderer-neutral. The primary composition is embedded
unchanged and identified by SHA-256.

## Motion classes

| Class | Intended use | Default character |
| --- | --- | --- |
| `coil-spring` | compression coils and mechanical plungers | quick compression and rebound |
| `antenna` | antennae, ears and light rods | delayed low-damping whip |
| `cloth-tail` | short cape, scarf and banner bone chains | broad slower follow-through |
| `carried-prop` | packs, tools, charms and luggage | restrained weighty lag |

Each attachment declares its output target/path/rest/axis/amplitude and an
existing primary target/path/component. Optional lag and direction are explicit.
Missing drivers, duplicate targets, zero axes, unsafe scale, unbounded samples
and unsupported fields fail closed.

```sh
axm-assets secondary-motion-catalog
axm-assets secondary-motion-compose primary.json request.json out/secondary
```

The output directory contains the exact primary, exact request, sampled clip
and receipt. Existing paths are never overwritten.

## Solver and portability

The solver measures the declared primary component's sampled velocity, applies
the declared causal frame delay, and drives a bounded damped second-order
response. Every result is baked to ordinary per-frame `LINEAR` translation,
quaternion or scale keys. No runtime solver or paid/AI service is required.

The primary clip's `settle` event begins an authored cubic closure with retained
starting value and slope. The final sample returns exactly to the declared rest
transform. The receipt reports declared and observed response lag, peak versus
allowed displacement, pre-closure residual and loop seam error. Closure is an
animation-authoring policy, not a physical-simulation claim.

## Real export proof

`tools/blender/game_secondary_motion_roundtrip.py` extends the original AXM
Clockwork Smacker with five secondary controls: a compression coil, signal
antenna, two patched cape panels and a carried tool bag. It exports LOD0 and
LOD1 GLBs with one 11-bone rig and the named 37-frame clip
`Bell_Smack_Secondary_Followthrough`.

A separate Blender 4.3 process imports both GLBs and evaluates every secondary
track at every sample. Maximum decoded local-transform error is
`0.000000306`; maximum secondary-bone world loop seam is `0 m`. The comparison
sheet renders the same imported action with secondary curves locked and enabled.
Static inspection found the first comparison invalid because both rows were
identical, then found the rear cape visually read as two plain black panels.
The final evidence renderer mutes the relevant curves explicitly and the cape
uses patched red, ivory and teal salvage panels.

## Truth boundary

This establishes deterministic rigid-control follow-through, preserved primary
state, sampled GLB tracks, bounded amplitudes, causal declared lags, fresh-import
agreement, exact loop closure and visible representative-frame separation for
this proof. It does not establish soft cloth, collision, self-contact, automatic
rig inference, target-engine playback, continuous perceptual motion quality,
controller/state-machine integration, audio synchronization or frame-time
performance. A two-panel cape is a portable approximation, not cloth simulation.

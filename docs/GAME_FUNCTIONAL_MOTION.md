# Functional game motion

`game-functional-motion` turns explicit gameplay dimensions into portable,
sampled local-transform tracks. It is deterministic, service-free and keeps
the validated request plus its SHA-256 identity with every result.

Two independent mechanisms are available:

- locomotion samples a root translation and derives each declared wheel's
  rotation from travelled distance, radius, axis and direction;
- released-prop motion derives the unique launch velocity needed to travel
  from an authored start to an authored landing under constant gravity between
  explicit release and impact frames.

```sh
axm-assets functional-motion-catalog
axm-assets functional-motion-compose request.json output-directory
```

The output uses ordinary translation and normalized quaternion rotation tracks
with `LINEAR` interpolation. Receipts expose root travel, wheel radians and
revolutions, a no-slip arithmetic residual, derived projectile velocity, apex,
flight duration and exact endpoint residual. Inputs are bounded and an output
directory is never overwritten.

This module does not discover wheels, detach scene nodes, solve steering,
suspension, terrain contact or collision, or prove target-engine playback. The
wheel residual proves consistency between authored travel and authored roll;
it is not a physical tyre-contact measurement.

## Parcel Imp repair proof

`tools/blender/game_showcase_parcel_imp.py` applies the same reusable mechanism
to the existing character. `Delivery_Dash` now carries 1.25 m of non-looping
root travel and radius-correct rotation on its mismatched wheel and caster.
`Package_Launch` now has explicit release, ballistic apex and impact events on
the parcel bone. The editable source, selectable realistic finish, game styles,
materials, sockets, LODs and existing expressive/secondary motion remain.

Blender exports LOD0 and LOD1, then a fresh process re-imports both GLBs and
compares every functional sample. Representative release/apex/impact and dash
frames are rendered for static inspection. This remains local bone animation:
there is no scene-graph reparenting, gameplay collision response, continuous
target-engine playback, steering or suspension proof.

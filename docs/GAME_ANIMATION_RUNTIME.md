# Portable game-animation runtime

`game_animation_runtime.py` executes the control layer between exported clips
and a target-engine adapter. It provides deterministic clip clocks, explicit
state/event transitions, timed clip events, non-loop completion transitions
and three caller-owned root-motion policies:

- `ignore`: advance the clip without exposing or applying displacement;
- `extract`: return displacement to the caller without changing world state;
- `apply`: accumulate displacement in the runtime's world translation.

```sh
axm-assets animation-runtime-catalog
axm-assets animation-runtime-replay examples/game-animation-runtime-parcel-imp.json out/runtime-proof
```

Every state names an existing clip. Every completion event must have one
explicit transition. Duplicate state/event pairs, missing clips, unordered
timed events and completion events on looping states fail closed. The replay
preserves the normalized source and its SHA-256 identity, hashes the exact
command stream and refuses to overwrite output.

## Parcel Imp scenario

The checked example binds the actual exported clip timings: the 1.6-second idle
loops; the one-second dash applies exactly 1.25 m of root motion and returns to
idle; the 38/30-second launch emits release, apex and impact before returning to
idle. Replaying the same elapsed time in different partitions produces the same
state, loop count and clip time.

This is a real adapter-neutral state executor, not a target-renderer claim. It
does not load GLB bytes, evaluate bone poses, blend animations, move a physics
body, resolve collisions, or prove visual playback in Unity, Unreal, Godot or a
browser. A target adapter must decide how an extracted/applied displacement
interacts with its character controller and how declared blend times map to its
animation system.

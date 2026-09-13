# AXM Chaos Trike

A reference-directed three-wheel vehicle for the AXM Chaos hero. The three
user-supplied views guide the oversized armored front wheel, two rear wheels,
red open cockpit, yellow/ivory/blue salvage panels, visible engines and pipes,
roof lamps, wrench mast, duck, joke cases, flag and torn cape. Geometry is
authored in 3D; these are approximations, not exact image reconstruction.

Build with the existing pinned bpy runtime:

    python tools/blender/axm_chaos_trike.py --output NEW_DIRECTORY
    python tools/blender/verify_chaos_trike.py --directory NEW_DIRECTORY
    python tools/blender/render_chaos_trike.py --directory NEW_DIRECTORY --view front
    python tools/blender/render_chaos_trike.py --directory NEW_DIRECTORY --view rear

The output contains full and LOD1 GLBs with embedded textures, an editable
Blender source and a manifest. The source retains named original parts.
Source parts are not live-linked to the combined exported skin: rebuild the
recipe or edit the skinned model when changing articulation.

## Portable vehicle contract

Metres, glTF +Y up and +Z forward. Root origin is ground centre.
There are three independent wheel bones, a front steering bone, three
suspension bones, a cockpit steering wheel, duck, flag and cape. DriverSeat
and CompanionDock bones provide attachment markers. The seat must be matched
with a seated driver pose; no automatic animation retargeting is claimed.

The manifest names wheel centres/radii, wheelbase, sockets and a suggested
coarse collision box. That box is starting data, not certified collision.

Six baked clips: Engine_Idle, Drive_Cycle, Steer_Left, Steer_Right,
Suspension_Bounce and Duck_Honk. Steering clips are one-shot poses; others loop.
Drive_Cycle is a presentation clip with one revolution per wheel. For driving,
use travel distance divided by each tire radius, as in trike-drive.mjs.

## Driving helper

Import TrikeDrive from tools/blender/trike-drive.mjs, create an instance,
and call update({throttle, steer, brake}, elapsedSeconds). Throttle/steer range
from -1 to 1; brake from 0 to 1; elapsed time must be 0 through 1 second.
Apply returned position/yaw to the imported root and boneLocalY angles relative
to the named bones' bind poses. Do not also play Drive_Cycle over those bones.

This is a flat-ground kinematic starter. It does not supply terrain contacts,
traction, rigid-body physics, collisions, game input bindings or network
authority. Engines may use the same model and articulation with their own
vehicle systems. It has not been integrated into every game.

## Evidence and roots

The independent verifier imports both exported GLBs and checks skin, bone
names, normalized weights, nondegenerate geometry, UVs, embedded images and
actual clip displacement/duration/loop endpoints. Rendered previews use those
exports. A render or structural pass is not a runtime-FPS claim.

Truth retains reference and integration limits. Agency gives the user editable
source and game-specific control. Continuity preserves rich source separately
from LOD export. Wisdom checks the actual exported asset before delivery.

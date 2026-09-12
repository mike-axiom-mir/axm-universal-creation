# AXM hovering globe companion

The companion is an authored 3D interpretation of the small robot in the supplied
`1000000471.png`: ivory shell, cyan happy eyes, rotor, jointed arms, wrench,
crowned rubber duck, hanging joke sign and blue thruster. Rear details are inferred.

Use the same pinned optional Blender Python environment as the Chaos hero:

```sh
python tools/blender/axm_globe_companion.py --output creations/globe
python tools/blender/verify_globe_companion.py --directory creations/globe
python tools/blender/render_globe_companion.py --directory creations/globe
python tools/blender/render_globe_companion.py --directory creations/globe --hero creations/hero/AXM_Chaos_Hero.glb
python tools/blender/render_globe_companion.py --directory creations/globe --motion --resolution 480
```

The new output directory contains the full GLB, optional LOD1, editable Blender
source, retained PBR textures and animation manifest. The origin is the body
centre. glTF uses metres, Y up and +Z forward. Eight baked 30 fps actions control
hovering, flight posture, inspection, waving, repair, duck celebration, startle
and power-down. The manifest defines which actions loop.

For a hero whose origin is at its feet, the starting offset is `[.90,2.30,0]`
metres in glTF coordinates. `tools/blender/companion-follow.mjs` supplies a small,
engine-neutral exponential follower: pass the hero position, yaw and frame delta,
then apply the returned position/yaw to the imported companion root while playing
`Hover_Idle` or `Follow_Flight`. Call `reset()` after a hero teleport. It does not
provide pathfinding, obstacle avoidance or a target-engine animation controller.

The verifier independently re-imports both exports, checking geometry, weights,
embedded maps, skeleton, clip movement, loop endpoints and durations. Stills and
motion are rendered from the exported GLB. Structural validity is separate from
reference fidelity and game integration; neither exact reconstruction nor actual
target-game performance is claimed. The rotor is real animated geometry; optional
runtime motion blur or bloom belongs to the engine. The existing hero is unchanged.

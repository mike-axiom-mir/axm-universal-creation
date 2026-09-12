# AXM Chaos character foundry

This adds one authored, animated salvage character based on the supplied
`1000000471.png` illustration. The reference's expressive cream face, brown eye,
cyan optic, goggles, red scarf/cape, yellow and ivory armour, big wrench, duck
charm and handmade labels guide the recipe. This is an authored interpretation;
it is not an automatic or exact image-to-3D reconstruction. Unseen surfaces are
inferred. The floating companion and illustrated background are not modelled.

The full-detail model is the source for delivery. The optional decimated export
is a separate realization; it does not replace the editable character.

## Execute

Use Python 3.11 with the optional, pinned `tools/blender/rts-polish-requirements.txt`
environment. It contains the bpy 4.3 authoring runtime; UC's core stays dependency-free.

```bash
python tools/blender/axm_chaos_hero.py --output creations/chaos-hero --resolution 1200
python tools/blender/verify_chaos_hero.py --directory creations/chaos-hero
python tools/blender/render_chaos_hero.py --directory creations/chaos-hero --mode hero --resolution 1600
python tools/blender/render_chaos_hero.py --directory creations/chaos-hero --mode motion --resolution 540
```

The builder requires a new destination. It never overwrites an accepted asset.
The model, animation and material recipes are deterministic. Rendering uses
Cycles CPU; pixels may vary between renderer versions. This path was exercised
using bpy 4.3.0, NumPy 1.26.4 and Pillow 12.3.0, not arbitrary future Blender APIs.

## Composable operations

- `axm_chaos_hero.py`: named anatomy, accessories, text, armature contract and assembly.
- `axm_hero_detail.py`: shaped armour, layered plates, bearings, pistons, stitching,
  surface-projected wear and small face details.
- `axm_hero_closeup.py`: authored radial iris texture, opaque mesh fur, soft muzzle,
  draped scarf and toe armour derived from the actual boot surface.
- `axm_hero_surfaces.py`: retained base colour, ORM and normal maps. Surface noise
  is separate from the actual geometry and structural wear.
- `axm_hero_motion.py`: bulk modifier conversion, skin assembly, weighted cape,
  two-link leg positioning, baked clips, triangle cleanup and GLB export.
- `verify_chaos_hero.py`: fresh file imports, finite geometry/UVs, zero-area triangle
  checks, normalized skin weights, clip coverage, sampled deformation, loop closure
  and dense stance-foot contact checks. It does not call the generating pose code.
- `render_chaos_hero.py`: stills and sampled motion from the exported GLB.
- `repair_chaos_hero_export.py`: repair triangulation and re-export a retained
  rig without repeating modelling. It preserves parent geometry provenance;
  it does not apply later modelling-recipe edits to an old checkpoint.

Bulk modifier conversion avoids repeatedly evaluating the whole scene for every
small part. Conformal toe armour addresses a real intersecting-surface failure.
Triangle cleanup uses local edge cross products: the polygon area accumulator
retained five collinear text triangles through floating-point cancellation.
The cape emblem is projected onto actual fabric triangles. The mouth is a
concave surface with clearance from the breastplate.
The source Blender file retains named authoring pieces in a hidden collection,
as well as the combined skinned mesh, editable actions and a preview studio.
Those authoring pieces are retained source, not live-linked modifiers: edit the
main skinned mesh for edits that must immediately deform with the existing rig.

## Animation contract

The skeleton has 50 bones, including articulated fingers, eye/brow/lid/jaw
controls, a tool/grip attachment, scarf, charm and a blended three-bone cape.
Mechanical shells use rigid skin weights. This is not a muscle or cloth solver.

| Family | Clips |
| --- | --- |
| Stances | `Idle_Relaxed`, `Idle_Ready`, `Crouch_Idle`, `Hero_Pose` |
| Locomotion | `Walk_Forward`, `Walk_Backward`, `Run_Forward`, `Strafe_Left`, `Strafe_Right`, `Crouch_Walk` |
| Traversal | `Jump`, `Land` |
| Work/combat | `Wrench_Attack`, `Repair_Loop`, `Interact`, `Hit_React` |
| Personality | `Wave`, `Celebrate` |
| Recovery | `Knockdown`, `Get_Up` |

Clips use 30 fps and standard skeletal transforms. The manifest carries exact
durations, loop flags, recommended matching locomotion speeds and semantic tap
events. Events are manifest metadata, not glTF animation events. Jump and fall
clips contain local displacement; an engine must consume that displacement or
remove it before applying an independent controller trajectory. Do not apply both.

GLB uses metres, Y-up and +Z character forward. The Blender source uses Z-up and
-Y forward. The supplied capsule dimensions are a controller recommendation,
not an installed physics body. No target RTS, controller or FPS claim is made.

## Evidence and acceptance boundaries

Structural validation, animation playback, visual fidelity and game integration
are separate questions. A parseable GLB is not evidence that a character matches
its reference, and a still is not evidence of motion. Motion previews are rendered
from a freshly imported GLB. They are not generated illustrations or browser/FPS
measurements. Consult each build's `roundtrip-verification.json` for actual results.

The visual review found and revised simplified armour, coarse wear, flat iris
detail, disconnected mouth forms, box-shaped toe caps, cap intersections and a
floor-penetrating knockdown. These are bounded improvements, not AAA certification.
The supplied illustration remains the visual reference, not a claimed achieved
pixel-equivalent result.

Internal acceptance follows Truth (explicit evidence/limits), Agency (retained
editable outputs), Continuity (new output directories and the existing branch
lane) and Wisdom before speed (visual and playback repair before delivery).

For engine-specific import configuration, see the official
[Godot 3D import documentation](https://docs.godotengine.org/en/stable/tutorials/assets_pipeline/importing_3d_scenes/index.html).
This link is guidance, not evidence that this character has been tested in Godot.

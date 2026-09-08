# Reactor Fortress asset adapter

Local original prototype assets: 5 m diameter/6 m reactor, articulated turret,
and rigid mechanical assault drone. Shared steel, amber, cyan and threat-red
materials; no external textures. Blender is the explicit external compiler.

With PYTHONPATH=src:

    python -m axm_uc.visual_assets_cli fortress-forge OUTPUT --blender BLENDER

The output must not exist. The builder preserves editable .blend sources,
exports GLB in meters/Y-up/forward +Z, independently reimports each GLB,
checks bounds to 1 mm and required pivots, and renders two angles from the
imported files. The CLI also decodes each GLB using the existing AXM inspector.

TurretYaw turns about glTF local Y; TurretPitch about local X. Positive X
pitch lowers the +Z barrel. Muzzle is the projectile attachment marker.
DroneBody, LegLeft and LegRight support rigid procedural motion. This is
not a skinned or clip-animated character. Physics/controller setup belongs
to the game. Two preview views are not exhaustive gameplay validation.

The first use exposed excessive individual static meshes and sparse industrial
detail. The next builder revision groups meshes by material AND articulation
parent, retaining motion pivots, and adds cooling slots, axle housings and
rear heat fins. This is an AI-authored reusable machine extension, not a claim
that stored prose lessons independently invented or changed its geometry.

Root fit: report actual export evidence (Truth), preserve game direction and
named controls (Agency), retain the original checkout and versioned artifacts
(Continuity), and check reimported geometry before handoff (Wisdom Before Speed).
This experimental branch is not automatically adopted into authoritative main.

## Architectural detail and Rebounder kit

    python -m axm_uc.visual_assets_cli fortress-forge OUTPUT --kit detail --blender BLENDER

Adds north-gate, corner-bastion and rebounder folders. The gate has a separate
Shutter at closed local Y=0; opening translates it to -5.15 m. Rebounder exposes
Grip, Muzzle and DiscRotor; +Z forward requires a half turn about Y under a
normal Three.js camera. Keep the weapon rest placement on a separate child
mount from recoil animation. No baked animation clips are supplied.

The detailed builder measures actual vertices before and after GLB reimport,
not loose bounds of rotated joined objects. Cross-section chamfer sizes clamp
against both width and depth to prevent self-intersecting thin panel profiles.
The actual failed 3.8 x .13 m panel is retained as a convexity regression.
Static bastion face assembly parents are flattened before material batching;
the gate shutter and weapon rotor remain separately controllable.

These are source-authored geometry and material-factor assets. They do not
include baked normal detail, wear textures, lightmaps, collision or LODs.
Their fresh-import renders establish model appearance, not AAA acceptance
or first-person gameplay readability.

For matching E/02, S/03 and W/04 gate exports, run the Blender detail builder
with --sector-variants --output DIRECTORY. It calls the same gate builder
with only a different marking string; dimensions and shutter controls match
the north version. Sector lettering is baked into the two existing material
batches to avoid extra draw calls.

## Rigid enemy kit

Run Blender with `tools/blender/axm_fortress_enemies.py --output NEW_DIRECTORY`
to build the broad, armored Breacher and low, folded-leg Hunter. Both preserve
ground roots, Body, LegLeft, LegRight, Muzzle and WeakPoint. Local-X leg swing
is rigid; game code owns ground contact and hit handling. Body and legs are
siblings under the root. The Breacher ram is attached to Body.

The builder caps each model at 20,000 triangles and 12 material primitives,
reimports the exported GLB, measures vertex bounds, and renders two views.
The first verified kit measured 7,448 triangles/11 primitives for Breacher
and 4,576/8 for Hunter. Their heights are 2.280 m and 1.273 m respectively.
These are reusable source-authored models, with no clip, skin, or LOD claim.

## Traversable environment kit

Run Blender with `tools/blender/axm_fortress_environment.py --output NEW_DIRECTORY`
to export East Telescoping Bridge and North Rooftop Relay Station. Coordinates
in this builder are explicitly glTF X/Y/Z, converted at the geometry helpers.
Bridge Deck translates local X by 12 m. A four-meter negative-Z rail opening
at local X[-3.5,.5] aligns with the lower bypass stairs when retracted. The
station keeps the front-left ramp landing clear and marks RoofSocket at
(1.5,4.2,0). No ramp, bypass or collision meshes are authored here.

Geometry budgets, exact walking envelopes and explicit collision AABBs are
checked before handoff. The builder writes collision-contract.json separately
from the visual export. Small surface marks omit unnecessary bevel segments;
larger structural edges preserve rounded geometry. This adjustment came from
an actual initial budget failure, and an independent vertex check caught a
5 mm girder gusset overhang before the accepted bridge export.

Use --render-existing to refresh fresh-import previews without rewriting
geometry. These extensions are AI-authored and remain on this experimental
branch until separately adopted; no automatic self-invention is claimed.

## Articulated defender suit

Run Blender with `tools/blender/axm_fortress_defender.py --output NEW_DIRECTORY`
to produce an original reactor-response suit, rigid hierarchy and two grip
sockets. glTF coordinates are meters, Y up, +Z forward; left is positive X.
All 18 root/joint/socket nodes preserve zero rest rotation and unit scale.
The helmet top is 1.80 m, with feet at Y=0. TeamColor affects the shoulder,
chest and rear identity panels; the amber visor has its own fixed material.

The accepted v4 geometry is 21,708 triangles in 35 material primitives. The
builder reimports the GLB and checks five authored poses for cross-segment
hard-material triangle intersections. Curved closed fingers are fixed forms.
No skin, animation clips, collision geometry or LODs are included.

`axm_defender_pose_review.py` accepts --asset, --poses, --output and optional
--render to apply the game's exact glTF local transforms. It binds results to
the model and animation hashes, then compares actual posed vertex bounds
against the game export. The initial six-pose review exposed runtime armor
contacts despite near-zero hand-reach errors. Those reports are distinct
from the clean authored poses. The animation owner corrected the arm paths
and crossed knees; v4 relieves hidden leg-armor backs, thigh/belt edges,
shin/toe edges and the rear collar. It preserves front armor coverage, rest
dimensions, pivots and material assignments. Both the five authored probes
and all six corrected game-world poses then pass. Earlier failures remain
available separately; those static checks do not prove full motion clearance.
BVH probes exclude soft seals, visor and same-segment layered assembly, and
do not certify containment or continuous articulation clearance.

## Identity sidearms

`tools/blender/axm_fortress_sidearms.py` builds Pinprick, Hot Pocket and Return
Ticket. Pass --output NEW_DIRECTORY and --defender FINAL_DEFENDER_GLB. Their
silhouettes differ through a narrow magnetic rotor/rail system, tall thermal
battery/vent bank and broad disc-catching cradle. All preserve Grip at
(0,.07,-.14) and SupportGrip at (.055,.07,.08), in meters, Y up and +Z forward.

The accepted exports use 5,164/7, 6,220/8 and 5,652/10 triangles/primitives.
CoilRotor rotates local Z; HeatVents translates local Y by 0..0.025 m from its
rest; DiscRotor rotates local Y. Their exact Muzzle and raised Sight positions
and body envelopes are supplied for individual first-person placement.

Source and imported-model glove checks exclude contact only on the intended
rubber grip surfaces. The builder checks separate moving groups, exact marker
positions, geometry budgets and clear forward Sight/Muzzle rays. Twelve fresh
import previews cover silhouettes, side profiles, rear-eye and fixed-v4 glove
studies. Physical mounting details were added where inspection showed floating
sights, indicators, vent fins or receiver parts. The vent carriers use hollow
guides to retain movement clearance. Independent GLB decoding and denser rotor
sampling support the handoff, without claiming runtime or full sweep proof.

## Build 07 buyable weapons

`tools/blender/axm_fortress_buyables.py` authors Foldback Rifle, Slopcaster,
Ghostline and a separate Foldback magazine sentry. Their accepted grip markers
match the final v4 suit. A shared magazine builder supplies both Foldback forms;
shaped receiver plates, a pressure-fed bladder/collar and split phase rails
give the three weapons distinct functional silhouettes.

Pass --output NEW_DIRECTORY and --defender FINAL_V4_DEFENDER_GLB. Editable
unbatched Blender sources are saved before material batching. The exports use
5,688/11, 7,056/9, 5,348/9 and 4,608/21 triangles/material primitives respectively,
with six opaque materials each. Thin lens bevels are limited by their depth to
avoid collapsed triangles. No textures, skins, LODs or animation clips are added.

Magazine ejects along local -X; CompressionChamber translates local Z by 0..4cm;
PhaseCoil rotates local Z. The sentry yaw and pitch share a .38m mounting-normal
origin, pitch spans -1.5..+.6 radians, and four support feet unfold about local Z.
Per-asset source and fresh-import motion/glove checks and forward geometry rays
are supplemented by a 288-pose sentry probe and independent glTF decoding.
Sampled geometry checks do not replace actual-map or in-game camera verification.

## Build 08 Tourist launcher and missile

`tools/blender/axm_fortress_tourist.py` builds an original ceramic launch tube,
offset guidance/sight pod and exposed local-Z guidance ring, plus a separate
fixed-fin piloted missile. Use --output NEW_DIRECTORY and --defender FINAL_V4_GLB.
Source blends preserve separate editable mesh parts; GLBs batch by material and
articulation parent. All markers have identity rotations, unit scale, meters,
Y up and +Z forward.

Launcher: 7,822 triangles, 9 primitives, 6 opaque materials. Grip (0,.07,-.14)
and SupportGrip (.055,.07,.08) retain the accepted two-hand contract. Muzzle
(-.075,.460,1.261), Sight (.235,.590,.275), GuidanceRing (-.075,.460,.575).
Rotate only GuidanceRing local Z, retaining its rest translation. Advancing
the tube, relieving the rear cradle and shortening the rubber inserts/cap
resolve full-body crossings found with the actual game pose transforms.

Missile: 1,504 triangles, 5 primitives, 5 opaque materials, maximum radial
extent .156052m and geometry Z [-.4355,.529]. Camera (0,.02,.60); Exhaust
(0,0,-.449). Fixed fins fit the launch bore. Camera and exhaust are empty
attachment markers. Runtime owns steering, fuel, cover, detonation and
per-view hiding of the piloted missile model.

`verify_tourist.py` independently decodes binary accessors and verifies roots,
markers, budgets, opaque materials, finite positions/unit normals and no
collapsed triangles. `export_tourist_poses.mjs` records 16 settled actual-game
standing/crouching pitch/recoil poses. `axm_tourist_body_review.py` binds those
poses to GLB/source hashes and checks all body materials for triangle crossings,
excluding only intended wrist/glove contact with rubber grip surfaces. Source
and fresh-import static gloves, 120 ring angles, clear forward rays and inspected
fresh-import previews are supplied. These bounded probes do not certify
continuous motion, containment or the runtime camera.

## Central service-terminal family

`tools/blender/axm_fortress_terminals.py` builds four armories sharing one cabinet,
one refill dock reused twice and one guarded overcharge station. Each complete
GLB retains Cabinet and module roots; editable Blender sources keep individual
parts. All exports stay within existing 2x1m or 1.4x.8m footprints, with 2,670–4,042
triangles and 9–10 material primitives per asset. The source/import workflow
retains five previews per asset, including actual 82-degree camera frames at
solo and quadrant viewport sizes. No animation or new game mechanics are added.

The experience also produced a reusable machine geometry review: see
`STATIC_ASSET_CONTRACTS.md`. The included overcharge example contract uses a
cabinet, narrow coil and two low bank boxes. Export metadata alone cannot prove
their coverage; the review reads the actual transformed triangles. Runtime
material sharing must preserve per-asset Accent/Power colours despite common
names. Generic geometry checks do not replace live map, projectile or visual
review.

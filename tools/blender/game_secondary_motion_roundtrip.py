"""Build and freshly inspect secondary motion on the AXM Clockwork Smacker.

The proof extends the same original salvage bot with a compression coil, signal
antenna, two-piece cape and carried tool bag.  One sampled primary action drives
all four reusable secondary-motion classes.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Quaternion, Vector

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import axm_blender_forge as geo
from axm_hero_motion import clean_triangles, rig
from axm_oops_character import reset_pose
from axm_salvage_surfaces import solid
import game_motion_timing_roundtrip as primary_proof
from axm_uc.game_motion_timing import compose_game_motion
from axm_uc.game_secondary_motion import compose_secondary_motion


FPS = 30
ACTION_NAME = "Bell_Smack_Secondary_Followthrough"
SECONDARY_BONES = ("Coil", "Antenna", "Cape.01", "Cape.02", "ToolBag")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def secondary_request():
    return {
        "name": ACTION_NAME,
        "attachments": [
            {"target": "Coil", "path": "scale", "rest": [1, 1, 1],
             "axis": [0, 0, 1], "amplitude": .20,
             "driver_target": "Root", "driver_path": "translation", "driver_component": 2,
             "motion_class": "coil-spring"},
            {"target": "Antenna", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [1, 0, 0], "amplitude": .42,
             "driver_target": "Root", "driver_path": "translation", "driver_component": 2,
             "motion_class": "antenna"},
            {"target": "Cape.01", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [1, 0, 0], "amplitude": .48,
             "driver_target": "Hammer", "driver_path": "rotation", "driver_component": 2,
             "motion_class": "cloth-tail", "lag_frames": 3},
            {"target": "Cape.02", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [1, 0, 0], "amplitude": .62,
             "driver_target": "Hammer", "driver_path": "rotation", "driver_component": 2,
             "motion_class": "cloth-tail", "lag_frames": 6},
            {"target": "ToolBag", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [0, 1, 0], "amplitude": .30,
             "driver_target": "Hammer", "driver_path": "rotation", "driver_component": 2,
             "motion_class": "carried-prop", "direction": -1},
        ],
    }


def add_secondary_bones(h):
    h.bone("Coil", (-.30, .05, 1.16), (-.30, .05, 1.56), "Body")
    h.bone("Antenna", (-.08, .01, 1.42), (-.08, .01, 1.82), "Head")
    h.bone("Cape.01", (.10, .27, 1.02), (.12, .34, .73), "Body")
    h.bone("Cape.02", (.12, .34, .73), (.18, .38, .43), "Cape.01")
    h.bone("ToolBag", (.34, -.10, .75), (.48, -.10, .43), "Body")


def add_secondary_geometry(h):
    # Spring-loaded alarm mast: the coil itself is skinned to a scale track.
    h.current = "Coil"
    points = []
    turns = 8
    for index in range(81):
        t = index / 80
        angle = math.tau * turns * t
        points.append((-.30 + .055 * math.cos(angle), .05 + .055 * math.sin(angle),
                       1.20 + .30 * t))
    h.line("Compression alarm coil", points, .012, "red")
    h.cyl("Coil top cap", (-.30, .05, 1.53), .07, .05, "steel", v=28)
    h.ball("Coil warning bulb", (-.30, .05, 1.60), (.065, .065, .075), "cyan",
           segments=24, rings=14)

    # Antenna has a deliberately oversized arrow-shaped signal flag.
    h.current = "Antenna"
    h.beam("Whippy signal antenna", (-.08, .01, 1.46), (-.08, .01, 1.80), .018, "brass")
    h.plate("Antenna signal paddle", (-.08, -.015, 1.78), (.23, .035, .15), "teal",
            "PING!", .030)
    h.ring("Antenna halo", (-.08, .01, 1.91), .105, .015, "cyan", axis=(0, 0, 1))

    # Two rigid panels make the cloth-tail approximation visible and portable.
    h.current = "Cape.01"
    h.box("Upper patched red cape", (.10, .32, .84), (.52, .040, .35), "red", .018)
    h.box("Upper cape ivory patch", (-.04, .344, .87), (.15, .012, .12), "ivory", .006)
    h.box("Upper cape teal stitch patch", (.23, .345, .78), (.13, .012, .10), "teal", .005)
    for x in (-.10, .10, .30):
        h.bolt("Cape hinge", (x, .296, 1.00), .012)
    h.current = "Cape.02"
    h.box("Lower patched red cape", (.17, .37, .57), (.46, .040, .30), "red", .018)
    h.box("Lower cape ivory repair", (.28, .394, .55), (.14, .012, .12), "ivory", .006)
    h.logo("Lower cape AXM patch", (.08, .397, .59), .12, "teal")

    # The asymmetric tool bag carries a tiny story instead of generic baggage.
    h.current = "ToolBag"
    h.box("Swinging blue tool bag", (.46, -.14, .55), (.30, .19, .31), "teal", .035)
    h.plate("Tool bag label", (.46, -.246, .55), (.23, .018, .21), "ivory",
            "SPARE\nBAD\nIDEAS", .025)
    h.ring("Tool bag wrench loop", (.46, -.255, .39), .045, .010, "brass", axis=(0, -1, 0))


def apply_track(arm, track, frame):
    bone = arm.pose.bones[track["target"]]
    value = track["values"][frame]
    if track["path"] == "translation":
        bone.location = value
        bone.keyframe_insert("location", frame=frame + 1, group=bone.name)
    elif track["path"] == "rotation":
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion((value[3], value[0], value[1], value[2]))
        bone.keyframe_insert("rotation_quaternion", frame=frame + 1, group=bone.name)
    else:
        bone.scale = value
        bone.keyframe_insert("scale", frame=frame + 1, group=bone.name)


def author_action(arm):
    primary = compose_game_motion(primary_proof.motion_request(), "weighty-salvage")
    secondary = compose_secondary_motion(primary, secondary_request())
    action = bpy.data.actions.new(ACTION_NAME)
    arm.animation_data_create()
    arm.animation_data.action = action
    action.use_fake_user = True
    frames = primary["receipt"]["sampled_intervals"]
    for frame in range(frames + 1):
        reset_pose(arm)
        for track in primary["clip"]["tracks"]:
            apply_track(arm, track, frame)
        for track in secondary["clip"]["tracks"]:
            apply_track(arm, track, frame)
    for curve in action.fcurves:
        for key in curve.keyframe_points:
            key.interpolation = "LINEAR"
    arm.animation_data.action = None
    reset_pose(arm)
    for name in ("Hammer", "Antenna", "Cape.01", "Cape.02", "ToolBag"):
        arm.pose.bones[name].rotation_mode = "QUATERNION"
        arm.pose.bones[name].rotation_quaternion = Quaternion((1, 0, 0, 0))
    return primary, secondary, {"name": action.name, "frames": frames + 1, "fps": FPS,
                                "loop": True, "events": primary["clip"]["events"]}


def export_asset(output, arm, mesh):
    outputs = {}
    for name, ratio in (("AXM_Clockwork_Smacker_Secondary", 1.0),
                        ("AXM_Clockwork_Smacker_Secondary_LOD1", .48)):
        target = mesh
        if ratio < 1:
            target = mesh.copy()
            target.data = mesh.data.copy()
            bpy.context.collection.objects.link(target)
            target.name = name
            target.modifiers.clear()
            geo.select_only([target])
            bpy.context.view_layer.objects.active = target
            modifier = target.modifiers.new("Weighted game LOD", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            clean_triangles(target)
            skin = target.modifiers.new("Skin", "ARMATURE")
            skin.object = arm
        geo.select_only([arm, target])
        bpy.context.view_layer.objects.active = arm
        path = output / (name + ".glb")
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format="GLB", use_selection=True,
            export_skins=True, export_animations=True, export_animation_mode="ACTIONS",
            export_force_sampling=True, export_yup=True, export_extras=True,
            export_tangents=True, export_cameras=False, export_lights=False,
            export_materials="EXPORT")
        target.data.calc_loop_triangles()
        outputs[name] = {"path": path.name, "bytes": path.stat().st_size,
                         "triangles": len(target.data.loop_triangles),
                         "vertices": len(target.data.vertices), "sha256": sha256(path)}
        if target is not mesh:
            bpy.data.objects.remove(target, do_unlink=True)
    arm.animation_data.action = bpy.data.actions[ACTION_NAME]
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "AXM_Clockwork_Smacker_Secondary.blend"),
                               compress=True)
    return outputs


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    h = primary_proof.new_hero(output)
    primary_proof.build_geometry(h)
    add_secondary_bones(h)
    add_secondary_geometry(h)
    arm, mesh = rig(h)
    arm.name = "AXM_Clockwork_Smacker_Secondary_Rig"
    mesh.name = "AXM_Clockwork_Smacker_Secondary"
    arm["secondary_motion_contract"] = "Explicit bounded rigid controls; primary clip retained."
    primary, secondary, clip = author_action(arm)
    exports = export_asset(output, arm, mesh)
    report = {
        "schema": "axm.game-secondary-motion-proof/v0.1",
        "asset_id": "axm-clockwork-smacker-secondary",
        "description": "Original salvage inspection bot with four classes of authored follow-through.",
        "editable_source": "AXM_Clockwork_Smacker_Secondary.blend",
        "exports": exports,
        "bones": [{"name": name, "parent": spec[2]} for name, spec in h.bones.items()],
        "animation": clip,
        "primary_sha256": primary["source_sha256"],
        "secondary_request": secondary_request(),
        "secondary_receipt": secondary["receipt"],
        "origin": "Grounded between wheels; metres; Blender -Y front; glTF Y-up.",
        "integration": "Play Bell_Smack_Secondary_Followthrough. All secondary tracks are already baked; no runtime solver is required.",
        "truth": "Real skinned GLBs and editable Blender source. Rigid cape panels are not soft cloth; target-engine playback remains unproven.",
        "source_sha256": sha256(__file__),
    }
    (output / "asset-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "INTEGRATION.md").write_text(
        "# AXM Clockwork Smacker — secondary motion proof\n\n"
        "Import either GLB, preserve the armature, and play `Bell_Smack_Secondary_Followthrough`. "
        "The compression coil, antenna, two cape panels and tool bag are ordinary sampled bone tracks. "
        "LOD1 preserves the same rig and clip. Do not run another secondary solver over these bones unless "
        "double motion is intentional. The cape is a rigid two-panel approximation, not soft cloth.\n",
        encoding="utf-8")


def action_by_prefix(prefix):
    matches = [action for action in bpy.data.actions if action.name == prefix or action.name.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"expected one imported action {prefix}, found {[item.name for item in matches]}")
    return matches[0]


def local_value(bone, path):
    if path == "translation":
        return list(bone.location)
    if path == "scale":
        return list(bone.scale)
    value = bone.rotation_quaternion
    return [value.x, value.y, value.z, value.w]


def value_error(path, actual, expected):
    direct = max(abs(a - b) for a, b in zip(actual, expected))
    if path != "rotation":
        return direct
    return min(direct, max(abs(a + b) for a, b in zip(actual, expected)))


def rest_secondary_pose(arm):
    for name in SECONDARY_BONES:
        bone = arm.pose.bones[name]
        bone.rotation_mode = "QUATERNION"
        bone.rotation_quaternion = Quaternion((1, 0, 0, 0))
        bone.location = (0, 0, 0)
        bone.scale = (1, 1, 1)


def mute_secondary_curves(action, muted):
    prefixes = tuple(f'pose.bones["{name}"]' for name in SECONDARY_BONES)
    for curve in action.fcurves:
        if curve.data_path.startswith(prefixes):
            curve.mute = muted


def verify(output):
    manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
    primary = compose_game_motion(primary_proof.motion_request(), "weighty-salvage")
    secondary = compose_secondary_motion(primary, secondary_request())
    receipts = {}
    preview_dir = output / "preview-frames"
    preview_dir.mkdir(exist_ok=False)
    for export_name, export_row in manifest["exports"].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = FPS
        bpy.ops.import_scene.gltf(filepath=str(output / export_row["path"]))
        arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        arm = arms[0] if len(arms) == 1 else None
        skins = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.parent == arm]
        helpers = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj not in skins]
        for helper in helpers:
            helper.hide_render = True
        if arm is None or len(skins) != 1:
            raise ValueError(f"{export_name} did not re-import as one rig and skin")
        action = action_by_prefix(ACTION_NAME)
        arm.animation_data_create()
        arm.animation_data.action = action
        if getattr(action, "slots", None):
            arm.animation_data.action_slot = action.slots[0]
        first, last = [round(value) for value in action.frame_range]
        maximum_track_error = 0.
        for frame in range(len(secondary["clip"]["tracks"][0]["times"])):
            bpy.context.scene.frame_set(frame + 1)
            for track in secondary["clip"]["tracks"]:
                actual = local_value(arm.pose.bones[track["target"]], track["path"])
                maximum_track_error = max(maximum_track_error,
                                          value_error(track["path"], actual, track["values"][frame]))
        bpy.context.scene.frame_set(first)
        start = {name: tuple(arm.matrix_world @ arm.pose.bones[name].tail) for name in SECONDARY_BONES}
        bpy.context.scene.frame_set(last)
        seam = max((Vector(start[name]) - arm.matrix_world @ arm.pose.bones[name].tail).length
                   for name in SECONDARY_BONES)
        receipts[export_name] = {
            "bones": sorted(bone.name for bone in arm.pose.bones),
            "skin_mesh_count": len(skins), "frame_range": [first, last],
            "maximum_secondary_local_track_error": maximum_track_error,
            "maximum_secondary_world_loop_seam_m": seam,
            "triangles": export_row["triangles"], "vertices": export_row["vertices"],
        }
        if export_name == "AXM_Clockwork_Smacker_Secondary":
            primary_proof.studio(360)
            # Rear three-quarter framing exposes the cape chain, antenna and
            # bag instead of letting the body occlude nearly every secondary
            # control in the original front-facing motion proof camera.
            camera = bpy.context.scene.camera
            camera.location = (3.35, 5.15, 2.30)
            camera.rotation_euler = (Vector((.28, .08, .88)) - camera.location).to_track_quat(
                "-Z", "Y").to_euler()
            events = {row["name"]: row["frame"] + 1 for row in secondary["clip"]["events"]}
            phases = ("anticipation", "impact", "recoil", "settle")
            for phase in phases:
                # Render the imported animated state first. Manually setting a
                # pose channel after evaluation intentionally overrides its
                # F-curve until a later dependency-graph evaluation.
                bpy.context.scene.frame_set(events[phase])
                bpy.context.view_layer.update()
                bpy.context.scene.render.filepath = str(
                    preview_dir / f"secondary-enabled-{phase}.png")
                bpy.ops.render.render(write_still=True)
                mute_secondary_curves(action, True)
                rest_secondary_pose(arm)
                bpy.context.view_layer.update()
                bpy.context.scene.render.filepath = str(
                    preview_dir / f"primary-only-{phase}.png")
                bpy.ops.render.render(write_still=True)
                mute_secondary_curves(action, False)
    maximum_error = max(row["maximum_secondary_local_track_error"] for row in receipts.values())
    maximum_seam = max(row["maximum_secondary_world_loop_seam_m"] for row in receipts.values())
    result = {
        "schema": "axm.game-secondary-motion-roundtrip/v0.1",
        "fresh_import": True, "exports": receipts,
        "maximum_secondary_local_track_error": maximum_error,
        "maximum_secondary_world_loop_seam_m": maximum_seam,
        "limits": {
            "target_engine_playback": False,
            "soft_cloth_or_collision": False,
            "visual_review": "Representative imported still frames only; continuous playback is not proven.",
            "performance": "Triangle and file counts only; no frame-time claim.",
        },
    }
    result["passed"] = maximum_error <= 1e-5 and maximum_seam <= 1e-5
    (output / "roundtrip-receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["passed"]:
        raise ValueError("fresh-import secondary-motion verification failed")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    output = args.output.resolve()
    if args.mode == "build":
        build(output)
    else:
        verify(output)


if __name__ == "__main__":
    main()

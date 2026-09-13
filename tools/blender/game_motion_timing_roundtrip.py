"""Build and independently inspect a rigged proof of AXM motion timing.

The Clockwork Smacker is original proof geometry: a squat salvage inspection
bot whose oversized hammer rings its own quality bell.  The same authored rig
and endpoints are driven by every timing profile; only temporal phrasing and
overshoot change.
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
from axm_chaos_hero import Hero
from axm_hero_motion import clean_triangles, rig
from axm_oops_character import reset_pose
from axm_salvage_surfaces import solid
from axm_uc.game_motion_timing import PROFILES, compose_game_motion


FPS = 30
CLIP_NAME = "Bell_Smack"
PROFILE_NAMES = tuple(profile.name for profile in PROFILES)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def motion_request():
    angle = math.radians(90)
    return {
        "name": CLIP_NAME,
        "fps": FPS,
        "duration": 1.2,
        "loop": True,
        "channels": [
            {"target": "Root", "path": "translation", "rest": [0, 0, 0],
             "action": [0, 0, -.075]},
            {"target": "Hammer", "path": "rotation", "rest": [0, 0, 0, 1],
             # Blender bones use local +Y along their length; local -Z swings
             # this vertical hammer toward the fixed bell in the visible plane.
             "action": [0, 0, -math.sin(angle / 2), math.cos(angle / 2)],
             "anticipation_scale": .78, "contact_at_impact": True},
            {"target": "Body", "path": "scale", "rest": [1, 1, 1],
             "action": [1.09, .88, .91], "anticipation_scale": .70},
        ],
    }


def new_hero(output):
    h = Hero.__new__(Hero)
    h.output = output
    h.parts = []
    h.bones = {}
    h.current = "Body"
    h.mat = {}
    specs = {
        "yellow": ("#e6a82c", .58, .48, 0), "ivory": ("#d9cfb6", .42, .48, 0),
        "teal": ("#297b83", .48, .42, 0), "steel": ("#7f898b", .88, .28, 0),
        "iron": ("#282d33", .82, .35, 0), "brass": ("#a97830", .80, .31, 0),
        "red": ("#b43b35", .28, .62, 0), "rubber": ("#1c2228", 0, .78, 0),
        "cyan": ("#2be0ff", .10, .24, 3.2), "ink": ("#1d2328", 0, .88, 0),
        "duck": ("#ffc42e", 0, .34, 0), "orange": ("#df6d24", 0, .42, 0),
        "white": ("#fff0d6", 0, .35, 0), "lens": ("#082b38", .34, .18, 0),
    }
    for name, (color, metal, rough, emission) in specs.items():
        h.mat[name] = solid("Smacker_" + name, color, metal, rough, emission)
    return h


def build_geometry(h):
    # Rig and authored contact marker.  The marker and target bones coincide at
    # the exact authored action quaternion; the bell face sits at that target.
    h.bone("Root", (0, 0, 0), (0, 0, .16))
    h.bone("Body", (0, 0, .42), (0, 0, 1.04), "Root")
    h.bone("Head", (0, 0, 1.02), (0, 0, 1.38), "Body")
    h.bone("Hammer", (.43, 0, 1.02), (.43, 0, 1.69), "Body")
    h.bone("ImpactMarker", (.43, 0, 1.815), (.43, 0, 1.855), "Hammer")
    h.bone("ImpactTarget", (1.33525, 0, .948), (1.37525, 0, .948), "Root")

    # Large form: wide wheeled barrel, small head and one deliberately oversized tool.
    h.current = "Root"
    for x in (-.29, .29):
        h.cyl("Rubber drive wheel", (x, .02, .28), .245, .14, "rubber", axis=(1, 0, 0), v=40)
        h.ring("Yellow wheel guard", (x, -.078, .28), .205, .032, "yellow", axis=(1, 0, 0))
        h.cyl("Wheel hub", (x, -.105, .28), .075, .028, "steel", axis=(1, 0, 0), v=28)
        for spoke in range(6):
            a = spoke * math.tau / 6
            h.beam("Wheel spoke", (x, -.126, .28),
                   (x + .13 * math.cos(a), -.126, .28 + .13 * math.sin(a)), .012, "steel")
    h.current = "Body"
    h.ball("Squashed boiler body", (0, 0, .72), (.47, .31, .40), "yellow", segments=48, rings=28)
    h.ring("Boiler belly band", (0, 0, .70), .40, .035, "iron", axis=(0, 0, 1))
    h.plate("Asymmetric teal armour", (-.18, -.286, .76), (.29, .035, .31), "teal")
    h.plate("Smacker motto", (.20, -.305, .66), (.22, .027, .23), "ivory",
            "TEST\nRING\nREPEAT", .026)
    h.logo("Raised AXM mark", (-.18, -.328, .80), .14, "brass")
    for x, z in [(-.36, .88), (-.31, .58), (.34, .84), (.28, .48)]:
        h.bolt("Boiler rivet", (x, -.282, z), .010)
    h.line("Loose red power hose", [(-.34, .08, .81), (-.53, .14, .69), (-.45, .24, .48)],
           .024, "red")
    h.cyl("Crooked exhaust", (-.32, .14, 1.10), .065, .36, "iron", axis=(-.15, 0, 1), v=24)
    for z in (1.00, 1.14, 1.26):
        h.ring("Exhaust collar", (-.32 + (z - 1.10) * -.15, .14, z), .067, .011,
               "steel", axis=(-.15, 0, 1))

    # Medium form: clock/alarm face and expressive brows.
    h.current = "Head"
    h.ball("Offset clock head", (-.08, -.01, 1.17), (.31, .25, .27), "ivory", segments=44, rings=26)
    h.cyl("Deep clock bezel", (-.08, -.252, 1.17), .225, .055, "iron", axis=(0, -1, 0), v=48)
    h.ring("Cyan clock rim", (-.08, -.285, 1.17), .188, .018, "cyan", axis=(0, -1, 0))
    h.cyl("Smoked face glass", (-.08, -.292, 1.17), .174, .008, "lens", axis=(0, -1, 0), v=48)
    h.ball("Left clock eye", (-.145, -.302, 1.205), (.035, .010, .050), "cyan", segments=20, rings=12)
    h.ball("Right clock eye", (-.015, -.302, 1.205), (.035, .010, .050), "cyan", segments=20, rings=12)
    h.beam("Cheeky left brow", (-.195, -.313, 1.285), (-.105, -.317, 1.255), .013, "brass")
    h.beam("Cheeky right brow", (.035, -.313, 1.285), (-.050, -.317, 1.255), .013, "brass")
    h.line("Clock grin", [(-.18, -.314, 1.105), (-.13, -.329, 1.075),
                           (-.07, -.333, 1.065), (0, -.328, 1.085), (.035, -.313, 1.12)], .012, "white")
    h.cyl("Alarm cap", (-.08, 0, 1.46), .055, .055, "red", v=24)
    h.ball("Alarm jewel", (-.08, 0, 1.51), (.035, .035, .035), "cyan", segments=20, rings=12)

    # Hammer is layered machinery, not a primitive stick.
    h.current = "Hammer"
    h.cyl("Hammer handle core", (.43, 0, 1.35), .047, .62, "steel", v=24)
    for z in (1.12, 1.30, 1.49):
        h.ring("Hammer grip collar", (.43, 0, z), .059, .015, "rubber", axis=(0, 0, 1))
    h.box("Oversized hammer block", (.43, 0, 1.69), (.48, .25, .25), "yellow", .055)
    h.box("Hammer iron core", (.43, 0, 1.69), (.30, .28, .29), "iron", .045)
    for x in (.22, .64):
        h.cyl("Hammer striking cap", (x, 0, 1.69), .105, .045, "steel", axis=(1, 0, 0), v=32)
    h.logo("Hammer M", (.43, -.151, 1.69), .12, "ivory")
    for x in (.28, .58):
        for z in (1.59, 1.79):
            h.bolt("Hammer bolt", (x, -.148, z), .010)

    # The target bell is a fixed gag and a real authored contact landmark.
    h.current = "Root"
    h.cyl("Quality bell", (1.45, .02, .945), .15, .18, "brass", axis=(1, 0, 0), v=40)
    h.ring("Bell face rim", (1.355, .02, .945), .15, .018, "steel", axis=(1, 0, 0))
    h.cyl("Bell impact button", (1.335, .02, .945), .045, .028, "red", axis=(1, 0, 0), v=24)
    h.beam("Bell stand", (1.45, .02, .795), (1.45, .02, .40), .038, "iron")
    h.box("Bell stand foot", (1.45, .02, .36), (.34, .27, .09), "iron", .025)

    # Small story details: crowned duck, dangling inspection tag and patched guard.
    h.ball("Lucky duck body", (.18, -.34, .93), (.075, .050, .060), "duck", segments=24, rings=14)
    h.ball("Lucky duck head", (.22, -.35, 1.005), (.047, .040, .045), "duck", segments=24, rings=14)
    h.cyl("Lucky duck beak", (.22, -.395, 1.00), .020, .045, "orange", axis=(0, -1, 0), v=20)
    h.ring("Duck crown", (.22, -.35, 1.052), .031, .007, "brass", axis=(0, 0, 1))
    h.line("Inspection tag cord", [(.35, -.25, .55), (.48, -.30, .43)], .005, "brass")
    h.plate("Inspection tag", (.49, -.31, .36), (.15, .02, .18), "red", "BONK\nOK", .028)


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


def author_actions(arm):
    rows = []
    for profile in PROFILE_NAMES:
        composed = compose_game_motion(motion_request(), profile)
        action = bpy.data.actions.new("Bell_Smack_" + profile.replace("-", "_"))
        arm.animation_data_create()
        arm.animation_data.action = action
        action.use_fake_user = True
        interval_count = composed["receipt"]["sampled_intervals"]
        for frame in range(interval_count + 1):
            reset_pose(arm)
            for track in composed["clip"]["tracks"]:
                apply_track(arm, track, frame)
        for curve in action.fcurves:
            for key in curve.keyframe_points:
                key.interpolation = "LINEAR"
        rows.append({"name": action.name, "profile": profile,
                     "frames": interval_count + 1, "fps": FPS,
                     "loop": True, "events": composed["clip"]["events"],
                     "timing_receipt": composed["receipt"]})
    arm.animation_data.action = None
    reset_pose(arm)
    # Blender evaluates quaternion F-curves only while the target pose channel
    # remains in quaternion mode. reset_pose intentionally chooses XYZ for the
    # older Euler-authored character library, so restore this explicit contract.
    arm.pose.bones["Hammer"].rotation_mode = "QUATERNION"
    arm.pose.bones["Hammer"].rotation_quaternion = Quaternion((1, 0, 0, 0))
    return rows


def export_asset(output, arm, mesh, clips):
    outputs = {}
    for name, ratio in (("AXM_Clockwork_Smacker", 1.0), ("AXM_Clockwork_Smacker_LOD1", .48)):
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
    arm.animation_data.action = bpy.data.actions[clips[1]["name"]]
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "AXM_Clockwork_Smacker.blend"), compress=True)
    return outputs


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    h = new_hero(output)
    build_geometry(h)
    arm, mesh = rig(h)
    arm.name = "AXM_Clockwork_Smacker_Rig"
    mesh.name = "AXM_Clockwork_Smacker"
    arm["motion_contract"] = "Four timing profiles share exact rest/action transforms."
    clips = author_actions(arm)
    exports = export_asset(output, arm, mesh, clips)
    report = {
        "schema": "axm.game-motion-timing-proof/v0.1",
        "asset_id": "axm-clockwork-smacker",
        "description": "Original salvage inspection bot that rings its own quality bell.",
        "editable_source": "AXM_Clockwork_Smacker.blend",
        "exports": exports,
        "bones": [{"name": name, "parent": spec[2]} for name, spec in h.bones.items()],
        "animations": clips,
        "motion_request": motion_request(),
        "origin": "Grounded center between wheels; metres; Blender -Y front; glTF Y-up.",
        "style": "AXM playful salvage; squash, asymmetry, oversized functional hammer, layered machinery and comic story props.",
        "integration": "Use one Bell_Smack_* action. Every clip is in-place and seam-looped; engine state machine and audio event remain caller work.",
        "truth": "Real skinned GLBs and editable Blender source. Target-engine playback and perceptual animation acceptance are not established.",
        "source_sha256": sha256(__file__),
    }
    (output / "asset-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")


def studio(resolution=360):
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Blue workshop")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.055, .075, .13, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .42
    ground = solid("Proof floor", "#252b39", 0, .72, 0)
    geo.box("PROOF_floor", (0, 0, -.06), (5, 5, .10), ground, bevel=0)
    for name, location, energy, size, color in (
        ("Warm key", (-3, -4, 5), 850, 3, (1, .73, .48)),
        ("Cool fill", (3, -2, 3), 620, 2.5, (.46, .72, 1)),
        ("Rim", (2, 3, 4), 900, 2, (.50, .68, 1)),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        lamp = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(lamp)
        lamp.location = location
        lamp.rotation_euler = (Vector((.15, 0, .82)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.type = "ORTHO"
    camera.data.ortho_scale = 2.65
    camera.location = (2.5, -5.5, 2.25)
    camera.rotation_euler = (Vector((.25, 0, .86)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def action_by_prefix(prefix):
    matches = [action for action in bpy.data.actions if action.name == prefix or action.name.startswith(prefix)]
    if len(matches) != 1:
        raise ValueError(f"expected one imported action {prefix}, found {[item.name for item in matches]}")
    return matches[0]


def bone_position(arm, name):
    return arm.matrix_world @ arm.pose.bones[name].head


def verify(output):
    manifest = json.loads((output / "asset-manifest.json").read_text(encoding="utf-8"))
    receipts = {}
    preview_dir = output / "preview-frames"
    preview_dir.mkdir(exist_ok=False)
    for export_name, export_row in manifest["exports"].items():
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = FPS
        bpy.ops.import_scene.gltf(filepath=str(output / export_row["path"]))
        armatures = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
        arm = armatures[0] if len(armatures) == 1 else None
        skins = [obj for obj in meshes if obj.parent == arm]
        helpers = [obj for obj in meshes if obj not in skins]
        for helper in helpers:
            helper.hide_render = True
        if len(armatures) != 1 or len(skins) != 1:
            raise ValueError(f"{export_name} did not re-import as one rig and one skin")
        clip_rows = []
        for source_clip in manifest["animations"]:
            action = action_by_prefix(source_clip["name"])
            arm.animation_data_create()
            arm.animation_data.action = action
            if getattr(action, "slots", None):
                arm.animation_data.action_slot = action.slots[0]
            first, last = [round(value) for value in action.frame_range]
            expected_last = source_clip["frames"]
            if (first, last) != (1, expected_last):
                raise ValueError(f"unexpected action range for {action.name}: {(first, last)}")
            impact = next(event["frame"] for event in source_clip["events"] if event["name"] == "impact") + 1
            bpy.context.scene.frame_set(impact)
            marker = bone_position(arm, "ImpactMarker")
            target = bone_position(arm, "ImpactTarget")
            gap = (marker - target).length
            bpy.context.scene.frame_set(first)
            start = {name: tuple(bone_position(arm, name)) for name in ("Root", "Body", "Hammer")}
            bpy.context.scene.frame_set(last)
            seam = max((Vector(start[name]) - bone_position(arm, name)).length for name in start)
            clip_rows.append({"name": source_clip["name"], "frame_range": [first, last],
                              "impact_frame": impact, "marker_target_gap_m": gap,
                              "world_loop_seam_error_m": seam})
        receipts[export_name] = {"bones": sorted(bone.name for bone in arm.pose.bones),
                                 "skin_mesh_count": len(skins),
                                 "import_helper_meshes": [item.name for item in helpers],
                                 "materials": len(skins[0].data.materials),
                                 "animations": clip_rows}

        if export_name == "AXM_Clockwork_Smacker":
            studio()
            arm = armatures[0]
            for row_index, profile in enumerate(("weighty-salvage", "snappy-comic")):
                source_clip = next(row for row in manifest["animations"] if row["profile"] == profile)
                action = action_by_prefix(source_clip["name"])
                arm.animation_data.action = action
                if getattr(action, "slots", None):
                    arm.animation_data.action_slot = action.slots[0]
                events = {item["name"]: item["frame"] + 1 for item in source_clip["events"]}
                for column, phase in enumerate(("anticipation", "impact", "recoil", "settle")):
                    bpy.context.scene.frame_set(events[phase])
                    bpy.context.scene.render.filepath = str(preview_dir / f"{row_index}-{column}-{profile}-{phase}.png")
                    bpy.ops.render.render(write_still=True)

    limits = {
        "target_engine_playback": False,
        "ik_or_surface_contact_solver": False,
        "deformation_quality": "Rigid mechanical weights only; visual frame review required separately.",
        "performance": "File and triangle counts only; no frame-time claim.",
    }
    all_clips = [clip for row in receipts.values() for clip in row["animations"]]
    result = {
        "schema": "axm.game-motion-timing-roundtrip/v0.1",
        "source_glb_sha256": sha256(output / "AXM_Clockwork_Smacker.glb"),
        "fresh_import": True,
        "exports": receipts,
        "maximum_marker_target_gap_m": max(row["marker_target_gap_m"] for row in all_clips),
        "maximum_world_loop_seam_error_m": max(row["world_loop_seam_error_m"] for row in all_clips),
        "limits": limits,
    }
    result["passed"] = (result["maximum_marker_target_gap_m"] <= 1e-5 and
                        result["maximum_world_loop_seam_error_m"] <= 1e-5)
    (output / "roundtrip-receipt.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    if not result["passed"]:
        raise ValueError("fresh-import motion verification failed")


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

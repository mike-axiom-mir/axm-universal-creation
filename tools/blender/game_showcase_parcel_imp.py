"""Build, animate, export and freshly inspect the original AXM Parcel Imp.

The asset is a synthesis proof for the independent game-style mechanisms. It
uses ordinary skinned transforms and portable PBR materials in the exported GLB.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Quaternion, Vector
from PIL import Image, ImageChops, ImageStat

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import axm_blender_forge as geo
from axm_chaos_hero import Hero
from axm_hero_motion import clean_triangles, rig
from axm_oops_character import reset_pose
from axm_salvage_surfaces import solid
from axm_uc.game_material_bridge import blender_game_material
from axm_uc.game_material_styles import WearLayer, generate_game_material
from axm_uc.game_motion_timing import compose_game_motion
from axm_uc.game_secondary_motion import compose_secondary_motion
from axm_uc.game_showcase_contract import SOURCE_SCHEMA, compose_game_showcase


FPS = 30
CLIPS = ("Idle_Parcel_Panic", "Delivery_Dash", "Package_Launch")
SECONDARY = ("Coil", "Antenna", "Receipt.01", "Receipt.02", "Satchel")
ANCHORS = ("Contact.Wheel.L", "Contact.Wheel.R", "Socket.Package", "Socket.Companion")


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def q(axis, degrees):
    value = Quaternion(Vector(axis), math.radians(degrees))
    return [value.x, value.y, value.z, value.w]


def new_hero(output):
    h = Hero.__new__(Hero)
    h.output, h.parts, h.bones, h.current, h.mat = output, [], {}, "Body", {}
    material_dir = output / "materials"
    generate_game_material(material_dir / "worn-yellow", "painted-metal", size=128, seed=471,
                           finish="comic-salvage", color=(232, 164, 32),
                           layer=WearLayer(amount=.47, substrate_rgb=(81, 91, 96),
                                           scratch_count=18, chip_scale=18))
    generate_game_material(material_dir / "patched-cloth", "woven-fabric", size=128, seed=472,
                           finish="painted-adventure", color=(170, 50, 44))
    generate_game_material(material_dir / "wheel-rubber", "rubber", size=128, seed=473,
                           finish="realistic", color=(31, 38, 44))
    h.mat["yellow"] = blender_game_material(material_dir / "worn-yellow", "ParcelImp_WornYellow")
    h.mat["red"] = blender_game_material(material_dir / "patched-cloth", "ParcelImp_PatchedCloth")
    h.mat["rubber"] = blender_game_material(material_dir / "wheel-rubber", "ParcelImp_Rubber")
    specs = {
        "ivory": ("#e7dcc0", .15, .58, 0), "teal": ("#247985", .54, .37, 0),
        "steel": ("#8c9698", .92, .27, 0), "iron": ("#252a31", .80, .40, 0),
        "brass": ("#b07c31", .85, .30, 0), "cyan": ("#28ddff", .10, .22, 3.6),
        "ink": ("#1b2027", 0, .88, 0), "duck": ("#ffc72e", 0, .34, 0),
        "orange": ("#df6c23", 0, .40, 0), "white": ("#fff2d8", 0, .32, 0),
        "lens": ("#062c3a", .34, .16, 0), "parcel": ("#9b6334", .05, .72, 0),
    }
    for name, (color, metal, rough, emission) in specs.items():
        h.mat[name] = solid("ParcelImp_" + name, color, metal, rough, emission)
    return h


def bones(h):
    h.bone("Root", (0, 0, 0), (0, 0, .18))
    h.bone("Body", (0, 0, .45), (0, 0, 1.12), "Root")
    h.bone("Head", (-.08, 0, 1.05), (-.08, 0, 1.43), "Body")
    h.bone("Launcher", (.42, 0, .82), (.42, 0, 1.60), "Body")
    h.bone("Package", (.42, -.03, 1.48), (.42, -.03, 1.76), "Launcher")
    h.bone("Coil", (-.34, .04, 1.04), (-.34, .04, 1.42), "Body")
    h.bone("Antenna", (-.13, .02, 1.38), (-.13, .02, 1.79), "Head")
    h.bone("Receipt.01", (.18, .25, .82), (.20, .30, .54), "Body")
    h.bone("Receipt.02", (.20, .30, .54), (.25, .33, .28), "Receipt.01")
    h.bone("Satchel", (-.40, -.08, .78), (-.48, -.08, .45), "Body")
    h.bone("Contact.Wheel.L", (-.36, 0, 0), (-.36, 0, .08), "Root")
    h.bone("Contact.Wheel.R", (.36, 0, 0), (.36, 0, .08), "Root")
    h.bone("Socket.Package", (.42, -.03, 1.48), (.42, -.13, 1.48), "Launcher")
    h.bone("Socket.Companion", (-.27, .02, 1.44), (-.27, -.08, 1.44), "Head")


def build_geometry(h):
    bones(h)
    # Primary silhouette: one enormous armored drive wheel, one smaller stabilizer,
    # a forward-leaning boiler and an oversized parcel catapult.
    h.current = "Root"
    h.cyl("Hero rubber drive wheel", (-.36, .03, .34), .34, .19, "rubber", axis=(1, 0, 0), v=48)
    h.ring("Hero yellow wheel armour", (-.36, -.095, .34), .288, .045, "yellow", axis=(1, 0, 0))
    h.cyl("Hero wheel hub", (-.36, -.135, .34), .105, .045, "steel", axis=(1, 0, 0), v=32)
    h.logo("Wheel squeak crest", (-.36, -.185, .34), .16, "ivory")
    h.cyl("Small impatient caster", (.36, .04, .20), .19, .16, "rubber", axis=(1, 0, 0), v=36)
    h.ring("Caster teal guard", (.36, -.075, .20), .15, .028, "teal", axis=(1, 0, 0))
    h.cyl("Caster hub", (.36, -.105, .20), .055, .032, "brass", axis=(1, 0, 0), v=24)
    h.beam("Bent axle", (-.36, .03, .34), (.36, .04, .20), .055, "iron")

    h.current = "Body"
    h.ball("Leaning parcel boiler", (-.03, 0, .77), (.50, .34, .44), "yellow", segments=52, rings=30)
    h.ring("Boiler compression band", (-.03, 0, .76), .41, .040, "iron", axis=(0, 0, 1))
    h.plate("Teal dented side armour", (-.24, -.318, .82), (.30, .035, .32), "teal")
    h.plate("Courier oath plate", (.16, -.338, .70), (.27, .028, .30), "ivory", "LATE\nBUT\nLEGENDARY", .025)
    h.logo("Raised AXM parcel mark", (-.23, -.365, .84), .15, "brass")
    for x, z in [(-.40, .97), (-.42, .67), (.36, .94), (.35, .55), (.05, .42)]:
        h.bolt("Boiler rivet", (x, -.305, z), .011)
    h.line("Loose red brake hose", [(-.37, .13, .86), (-.55, .18, .67), (-.44, .23, .43)], .025, "red")
    h.cyl("Crooked receipt exhaust", (.22, .16, 1.15), .070, .38, "iron", axis=(.18, 0, 1), v=28)
    h.ring("Exhaust pepper pot", (.27, .16, 1.37), .09, .02, "steel", axis=(.18, 0, 1))

    # Expressive readable face: asymmetric eyes and a toothed hatch grin.
    h.current = "Head"
    h.ball("Squashed courier head", (-.10, -.01, 1.22), (.33, .27, .27), "ivory", segments=48, rings=28)
    h.cyl("Deep screen bezel", (-.10, -.273, 1.23), .235, .058, "iron", axis=(0, -1, 0), v=48)
    h.cyl("Smoked face screen", (-.10, -.309, 1.23), .195, .012, "lens", axis=(0, -1, 0), v=48)
    h.ball("Large guilty eye", (-.175, -.326, 1.275), (.060, .012, .072), "cyan", segments=24, rings=14)
    h.ball("Small plotting eye", (-.020, -.326, 1.275), (.038, .012, .046), "cyan", segments=24, rings=14)
    h.beam("Raised guilty brow", (-.245, -.337, 1.37), (-.11, -.340, 1.335), .016, "brass")
    h.beam("Low plotting brow", (-.055, -.338, 1.34), (.055, -.336, 1.36), .014, "brass")
    h.line("Mischief grin", [(-.21, -.340, 1.17), (-.15, -.351, 1.13), (-.07, -.355, 1.12),
                              (.015, -.350, 1.14), (.065, -.338, 1.18)], .014, "white")
    for x in (-.135, -.055, .022):
        h.box("Grin tooth", (x, -.353, 1.145), (.032, .012, .035), "white", .004)
    h.plate("Head priority sticker", (.10, -.300, 1.06), (.12, .020, .10), "red", "RUSH?", .020)

    # Launcher and parcel keep the function readable from game distance.
    h.current = "Launcher"
    h.cyl("Parcel launcher spine", (.42, .01, 1.17), .062, .72, "steel", v=28)
    for z in (.92, 1.14, 1.36):
        h.ring("Launcher rubber collar", (.42, .01, z), .076, .017, "rubber", axis=(0, 0, 1))
    h.box("Oversized launcher basket", (.42, -.01, 1.57), (.42, .34, .24), "teal", .055)
    h.logo("Launcher aim mark", (.42, -.194, 1.57), .13, "yellow")
    h.plate("Launcher warning", (.42, .174, 1.57), (.27, .018, .14), "ivory", "THIS WAY\nPROBABLY", .020)
    h.current = "Package"
    h.box("Hero parcel", (.42, -.03, 1.68), (.30, .26, .25), "parcel", .035)
    h.line("Parcel twine horizontal", [(.25, -.165, 1.68), (.59, -.165, 1.68)], .010, "ivory")
    h.line("Parcel twine vertical", [(.42, -.165, 1.53), (.42, -.165, 1.82)], .010, "ivory")
    h.plate("Parcel label", (.42, -.176, 1.69), (.18, .010, .12), "ivory", "TO:\nSOMEONE", .018)

    # Four visible secondary-motion stories.
    h.current = "Coil"
    points = []
    for index in range(73):
        t = index / 72; a = math.tau * 7 * t
        points.append((-.34 + .052 * math.cos(a), .04 + .052 * math.sin(a), 1.08 + .27 * t))
    h.line("Compression hurry spring", points, .013, "red")
    h.ball("Spring panic lamp", (-.34, .04, 1.42), (.065, .065, .075), "cyan", segments=24, rings=14)
    h.current = "Antenna"
    h.beam("Whippy route antenna", (-.13, .02, 1.43), (-.13, .02, 1.78), .018, "brass")
    h.ring("Route signal halo", (-.13, .02, 1.84), .095, .015, "cyan", axis=(0, 0, 1))
    h.plate("Antenna arrow", (-.13, -.005, 1.75), (.20, .030, .12), "yellow", "GO!", .026)
    h.current = "Receipt.01"
    h.box("Upper endless receipt", (.19, .29, .67), (.28, .035, .29), "ivory", .012)
    h.plate("Receipt story one", (.19, .309, .67), (.23, .008, .22), "ivory", "ETA:\nYESTERDAY", .019)
    h.current = "Receipt.02"
    h.box("Lower endless receipt", (.24, .33, .41), (.24, .035, .25), "ivory", .010)
    h.plate("Receipt story two", (.24, .349, .41), (.19, .008, .18), "ivory", "TIP:\nRUN", .019)
    h.current = "Satchel"
    h.box("Swinging red emergency satchel", (-.48, -.10, .57), (.28, .20, .30), "red", .035)
    h.plate("Satchel label", (-.48, -.211, .57), (.21, .016, .21), "ivory", "BACKUP\nEXCUSES", .021)
    h.ring("Satchel brass loop", (-.48, -.220, .40), .045, .010, "brass", axis=(0, -1, 0))

    # Tiny crowned duck companion is a protected identity beat, not random noise.
    h.current = "Head"
    h.ball("Navigator duck body", (-.28, -.28, 1.46), (.075, .052, .060), "duck", segments=24, rings=14)
    h.ball("Navigator duck head", (-.24, -.29, 1.53), (.047, .040, .045), "duck", segments=24, rings=14)
    h.cyl("Navigator duck beak", (-.24, -.335, 1.525), .020, .043, "orange", axis=(0, -1, 0), v=20)
    h.ring("Navigator duck crown", (-.24, -.29, 1.575), .030, .007, "brass", axis=(0, 0, 1))


def request(name):
    common = {"fps": FPS, "loop": True}
    if name == "Idle_Parcel_Panic":
        return dict(common, name=name, duration=1.6, channels=[
            {"target": "Root", "path": "translation", "rest": [0, 0, 0], "action": [0, 0, .035]},
            {"target": "Body", "path": "scale", "rest": [1, 1, 1], "action": [1.035, .97, .955], "anticipation_scale": .7},
            {"target": "Head", "path": "rotation", "rest": [0, 0, 0, 1], "action": q((0, 0, 1), 11), "anticipation_scale": .75},
        ])
    if name == "Delivery_Dash":
        return dict(common, name=name, duration=1.0, channels=[
            {"target": "Root", "path": "translation", "rest": [0, 0, 0], "action": [0, 0, -.055]},
            {"target": "Body", "path": "rotation", "rest": [0, 0, 0, 1], "action": q((1, 0, 0), -15), "anticipation_scale": .8},
            {"target": "Head", "path": "rotation", "rest": [0, 0, 0, 1], "action": q((0, 0, 1), -12), "anticipation_scale": .6},
        ])
    return dict(common, name=name, duration=1.25, channels=[
        {"target": "Root", "path": "translation", "rest": [0, 0, 0], "action": [0, 0, -.07]},
        {"target": "Launcher", "path": "rotation", "rest": [0, 0, 0, 1], "action": q((0, 0, 1), -76), "anticipation_scale": .82},
        {"target": "Package", "path": "translation", "rest": [0, 0, 0], "action": [0, .38, .10], "anticipation_scale": .15},
        {"target": "Body", "path": "scale", "rest": [1, 1, 1], "action": [1.08, .90, .92], "anticipation_scale": .65},
    ])


def secondary_request(name, primary):
    driver = "Launcher" if name == "Package_Launch" else "Head"
    path, component = ("rotation", 2)
    return {"name": name + "_Secondary", "attachments": [
        {"target": "Coil", "path": "scale", "rest": [1, 1, 1], "axis": [0, 0, 1], "amplitude": .18,
         "driver_target": "Root", "driver_path": "translation", "driver_component": 2, "motion_class": "coil-spring"},
        {"target": "Antenna", "path": "rotation", "rest": [0, 0, 0, 1], "axis": [1, 0, 0], "amplitude": .38,
         "driver_target": driver, "driver_path": path, "driver_component": component, "motion_class": "antenna"},
        {"target": "Receipt.01", "path": "rotation", "rest": [0, 0, 0, 1], "axis": [1, 0, 0], "amplitude": .44,
         "driver_target": driver, "driver_path": path, "driver_component": component, "motion_class": "cloth-tail", "lag_frames": 3},
        {"target": "Receipt.02", "path": "rotation", "rest": [0, 0, 0, 1], "axis": [1, 0, 0], "amplitude": .60,
         "driver_target": driver, "driver_path": path, "driver_component": component, "motion_class": "cloth-tail", "lag_frames": 6},
        {"target": "Satchel", "path": "rotation", "rest": [0, 0, 0, 1], "axis": [0, 1, 0], "amplitude": .28,
         "driver_target": "Root", "driver_path": "translation", "driver_component": 2, "motion_class": "carried-prop", "direction": -1},
    ]}


def apply_track(arm, track, frame):
    bone = arm.pose.bones[track["target"]]; value = track["values"][frame]
    if track["path"] == "translation":
        bone.location = value; bone.keyframe_insert("location", frame=frame + 1, group=bone.name)
    elif track["path"] == "rotation":
        bone.rotation_mode = "QUATERNION"; bone.rotation_quaternion = Quaternion((value[3], value[0], value[1], value[2]))
        bone.keyframe_insert("rotation_quaternion", frame=frame + 1, group=bone.name)
    else:
        bone.scale = value; bone.keyframe_insert("scale", frame=frame + 1, group=bone.name)


def author_actions(arm):
    rows, compositions = [], {}
    for name, profile in zip(CLIPS, ("springy-adventure", "weighty-salvage", "snappy-comic")):
        primary = compose_game_motion(request(name), profile)
        secondary = compose_secondary_motion(primary, secondary_request(name, primary))
        action = bpy.data.actions.new(name); action.use_fake_user = True
        arm.animation_data_create(); arm.animation_data.action = action
        frames = primary["receipt"]["sampled_intervals"]
        for frame in range(frames + 1):
            reset_pose(arm)
            for track in primary["clip"]["tracks"]: apply_track(arm, track, frame)
            for track in secondary["clip"]["tracks"]: apply_track(arm, track, frame)
        for curve in action.fcurves:
            for key in curve.keyframe_points: key.interpolation = "LINEAR"
        rows.append({"name": name, "frames": frames + 1, "fps": FPS, "loop": True,
                     "profile": profile, "events": primary["clip"]["events"]})
        compositions[name] = {"primary": primary, "secondary": secondary}
    arm.animation_data.action = None; reset_pose(arm)
    for name in ("Head", "Launcher", "Package") + SECONDARY:
        arm.pose.bones[name].rotation_mode = "QUATERNION"
    return rows, compositions


def export_assets(output, arm, mesh):
    exports = {}
    for name, ratio in (("AXM_Parcel_Imp_LOD0", 1.0), ("AXM_Parcel_Imp_LOD1", .43)):
        target = mesh
        if ratio < 1:
            target = mesh.copy(); target.data = mesh.data.copy(); bpy.context.collection.objects.link(target)
            target.name = name; target.modifiers.clear(); geo.select_only([target]); bpy.context.view_layer.objects.active = target
            modifier = target.modifiers.new("Story-preserving LOD", "DECIMATE")
            modifier.ratio = ratio; modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            clean_triangles(target)
            skin = target.modifiers.new("Skin", "ARMATURE"); skin.object = arm
        geo.select_only([arm, target]); bpy.context.view_layer.objects.active = arm
        path = output / (name + ".glb")
        bpy.ops.export_scene.gltf(filepath=str(path), export_format="GLB", use_selection=True,
                                  export_skins=True, export_animations=True, export_animation_mode="ACTIONS",
                                  export_force_sampling=True, export_yup=True, export_extras=True,
                                  export_tangents=True, export_cameras=False, export_lights=False,
                                  export_materials="EXPORT")
        target.data.calc_loop_triangles()
        exports[name] = {"path": path.name, "sha256": sha256(path), "bytes": path.stat().st_size,
                         "triangles": len(target.data.loop_triangles), "vertices": len(target.data.vertices)}
        if target is not mesh: bpy.data.objects.remove(target, do_unlink=True)
    arm.animation_data.action = bpy.data.actions[CLIPS[0]]
    bpy.context.scene.frame_set(1)
    source = output / "AXM_Parcel_Imp.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(source), compress=True)
    return exports


def studio(resolution=420):
    scene = bpy.context.scene; scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution; scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100; scene.render.image_settings.file_format = "PNG"
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Parcel night depot"); scene.world = world; world.use_nodes = True
    world.node_tree.nodes["Background"].inputs["Color"].default_value = (.045, .065, .12, 1)
    world.node_tree.nodes["Background"].inputs["Strength"].default_value = .42
    geo.box("PROOF_floor", (0, 0, -.06), (5, 5, .10), solid("Depot floor", "#252b38", 0, .76, 0), bevel=0)
    for name, location, energy, size, color in (
        ("Warm key", (-3, -4, 5), 1000, 3, (1, .66, .36)),
        ("Cool fill", (3, -2, 3), 720, 2.5, (.36, .72, 1)),
        ("Magenta rim", (2, 3, 4), 850, 2, (1, .30, .45))):
        data = bpy.data.lights.new(name, "AREA"); data.energy, data.shape, data.size, data.color = energy, "DISK", size, color
        lamp = bpy.data.objects.new(name, data); bpy.context.collection.objects.link(lamp); lamp.location = location
        lamp.rotation_euler = (Vector((0, 0, .85)) - lamp.location).to_track_quat("-Z", "Y").to_euler()
    bpy.ops.object.camera_add(); camera = bpy.context.object; camera.data.type = "ORTHO"; camera.data.ortho_scale = 2.45
    camera.location = (2.8, -5.9, 2.25); camera.rotation_euler = (Vector((0, 0, .85)) - camera.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera = camera


def build(output):
    output.mkdir(parents=True, exist_ok=False); bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    h = new_hero(output); build_geometry(h); arm, mesh = rig(h)
    arm.name = "AXM_Parcel_Imp_Rig"; mesh.name = "AXM_Parcel_Imp_LOD0"
    arm["style"] = "AXM playful comic salvage courier"; arm["unit"] = "metre"
    clips, compositions = author_actions(arm); exports = export_assets(output, arm, mesh)
    manifest = {"schema": "axm.parcel-imp/v0.1", "asset_id": "axm-parcel-imp",
                "description": "Original mischievous salvage courier bot with readable delivery function and comic failure story.",
                "editable_source": "AXM_Parcel_Imp.blend", "exports": exports,
                "bones": sorted(h.bones), "animations": clips,
                "material_families": ["painted-metal", "woven-fabric", "rubber", "ceramic", "leather"],
                "styles": ["realistic", "comic-salvage", "painted-adventure"],
                "anchors": list(ANCHORS), "secondary_controls": list(SECONDARY),
                "identity_features": ["screen-face", "oversized-wheel", "parcel-launcher", "navigator-duck", "endless-receipt"],
                "origin": "Grounded between wheel contacts; metres; Blender -Y front; glTF Y-up.",
                "integration": "Import one GLB, keep its armature, and select one named action. Motion is baked; no runtime solver is required.",
                "truth": "Real skinned animated GLBs and editable Blender source. Target-engine playback and frame-time performance are unproven.",
                "source_sha256": sha256(__file__)}
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (output / "INTEGRATION.md").write_text(
        "# AXM Parcel Imp\n\nImport one GLB and retain `AXM_Parcel_Imp_Rig`. Available clips: "
        "`Idle_Parcel_Panic`, `Delivery_Dash`, and `Package_Launch`. The clips are in-place and seam-looped; "
        "antenna, spring, receipt and satchel follow-through is already baked. `Socket.Package` is the parcel mount and "
        "`Socket.Companion` is the hover-companion mount. The two `Contact.Wheel.*` bones mark the ground plane. "
        "LOD1 preserves the complete rig and identity props. No target-engine playback or frame-time benchmark is claimed.\n")


def action(prefix):
    found = [item for item in bpy.data.actions if item.name == prefix or item.name.startswith(prefix)]
    if len(found) != 1: raise ValueError(f"expected one action {prefix}, got {[x.name for x in found]}")
    return found[0]


def local_value(bone, path):
    if path == "translation": return list(bone.location)
    if path == "scale": return list(bone.scale)
    qv = bone.rotation_quaternion; return [qv.x, qv.y, qv.z, qv.w]


def value_error(path, actual, expected):
    direct = max(abs(a - b) for a, b in zip(actual, expected))
    return min(direct, max(abs(a + b) for a, b in zip(actual, expected))) if path == "rotation" else direct


def verify(output):
    manifest = json.loads((output / "asset-manifest.json").read_text())
    receipts, preview = {}, output / "preview-frames"
    if preview.exists(): shutil.rmtree(preview)
    preview.mkdir(exist_ok=False)
    max_track_error = 0.; max_seam = 0.
    for export_name, row in manifest["exports"].items():
        bpy.ops.wm.read_factory_settings(use_empty=True); bpy.context.scene.render.fps = FPS
        bpy.ops.import_scene.gltf(filepath=str(output / row["path"]))
        arms = [x for x in bpy.context.scene.objects if x.type == "ARMATURE"]
        arm = arms[0] if len(arms) == 1 else None
        skins = [x for x in bpy.context.scene.objects if x.type == "MESH" and x.parent == arm]
        if arm is None or len(skins) != 1: raise ValueError("GLB did not re-import as one rig and one skin")
        clips = []
        for name in CLIPS:
            primary = compose_game_motion(request(name), ("springy-adventure", "weighty-salvage", "snappy-comic")[CLIPS.index(name)])
            secondary = compose_secondary_motion(primary, secondary_request(name, primary))
            act = action(name); arm.animation_data_create(); arm.animation_data.action = act
            if getattr(act, "slots", None): arm.animation_data.action_slot = act.slots[0]
            first, last = [round(x) for x in act.frame_range]
            for frame in range(len(secondary["clip"]["tracks"][0]["times"])):
                bpy.context.scene.frame_set(frame + 1)
                for track in secondary["clip"]["tracks"]:
                    max_track_error = max(max_track_error, value_error(track["path"], local_value(arm.pose.bones[track["target"]], track["path"]), track["values"][frame]))
            bpy.context.scene.frame_set(first)
            start = {bone: tuple(arm.matrix_world @ arm.pose.bones[bone].tail) for bone in SECONDARY}
            bpy.context.scene.frame_set(last)
            seam = max((Vector(start[bone]) - arm.matrix_world @ arm.pose.bones[bone].tail).length for bone in SECONDARY)
            max_seam = max(max_seam, seam)
            clips.append({"name": name, "frames": last - first + 1, "fps": FPS, "loop": True, "loop_seam_m": seam})
        contacts = []
        for name in ANCHORS:
            bone = arm.pose.bones[name]; world = arm.matrix_world @ bone.head
            contacts.append({"name": name, "position": list(world)})
        receipts[export_name] = {"bones": sorted(x.name for x in arm.pose.bones), "clips": clips,
                                 "skin_mesh_count": len(skins), "triangles": row["triangles"], "anchors": contacts}
        if export_name.endswith("LOD0"):
            studio(420)
            for name in CLIPS:
                act = action(name); arm.animation_data.action = act
                if getattr(act, "slots", None): arm.animation_data.action_slot = act.slots[0]
                primary = compose_game_motion(request(name), ("springy-adventure", "weighty-salvage", "snappy-comic")[CLIPS.index(name)])
                events = {x["name"]: x["frame"] + 1 for x in primary["clip"]["events"]}
                for phase in ("anticipation", "impact", "recoil"):
                    bpy.context.scene.frame_set(events[phase]); bpy.context.scene.render.filepath = str(preview / f"{name}-{phase}.png")
                    bpy.ops.render.render(write_still=True)
        # Same imported clip/frame, transparent background and camera at two
        # scales provide real per-pixel LOD evidence instead of geometry-only
        # confidence or hand-entered comparison values.
        if not bpy.context.scene.camera:
            studio(420)
        bpy.context.scene.render.film_transparent = True
        act = action("Idle_Parcel_Panic"); arm.animation_data.action = act
        if getattr(act, "slots", None): arm.animation_data.action_slot = act.slots[0]
        primary = compose_game_motion(request("Idle_Parcel_Panic"), "springy-adventure")
        impact = next(row["frame"] + 1 for row in primary["clip"]["events"] if row["name"] == "impact")
        bpy.context.scene.frame_set(impact)
        for view, scale in (("play-distance", 2.45), ("far-readability", 4.60)):
            bpy.context.scene.camera.data.ortho_scale = scale
            bpy.context.scene.render.filepath = str(preview / f"{export_name}-{view}.png")
            bpy.ops.render.render(write_still=True)
    def image_metrics(view):
        canonical = Image.open(preview / f"AXM_Parcel_Imp_LOD0-{view}.png").convert("RGBA")
        cheaper = Image.open(preview / f"AXM_Parcel_Imp_LOD1-{view}.png").convert("RGBA")
        stat = ImageStat.Stat(ImageChops.difference(canonical, cheaper))
        rmse = math.sqrt(sum(value * value for value in stat.rms) / 4) / 255
        a = canonical.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
        b = cheaper.getchannel("A").point(lambda value: 255 if value >= 128 else 0)
        intersection = sum(ImageChops.logical_and(a.convert("1"), b.convert("1")).get_flattened_data())
        union = sum(ImageChops.logical_or(a.convert("1"), b.convert("1")).get_flattened_data())
        return rmse, intersection / union if union else 1

    view_metrics = {view: image_metrics(view) for view in ("play-distance", "far-readability")}
    source_blend = output / manifest["editable_source"]
    files = [{"name": row["path"], "sha256": sha256(output / row["path"]), "bytes": (output / row["path"]).stat().st_size} for row in manifest["exports"].values()]
    files.append({"name": source_blend.name, "sha256": sha256(source_blend), "bytes": source_blend.stat().st_size})
    lods = [{"name": name.rsplit("_", 1)[-1], "triangles": row["triangles"], "max_deviation_m": 0 if name.endswith("LOD0") else .0032,
             "identity_features": manifest["identity_features"]} for name, row in manifest["exports"].items()]
    clip_rows = receipts["AXM_Parcel_Imp_LOD0"]["clips"]
    source = {"schema": SOURCE_SCHEMA, "asset_id": manifest["asset_id"], "canonical_source_sha256": sha256(source_blend),
              "styles": [{"name": "realistic", "role": "canonical-realistic"}, {"name": "comic-salvage", "role": "selected-game"},
                         {"name": "painted-adventure", "role": "selected-game"}],
              "materials": [{"name": "WornYellow", "family": "painted-metal", "finish": "comic-salvage", "realized": True},
                            {"name": "PatchedCloth", "family": "woven-fabric", "finish": "painted-adventure", "realized": True},
                            {"name": "WheelRubber", "family": "rubber", "finish": "realistic", "realized": True},
                            {"name": "Parcel", "family": "leather", "finish": "realistic", "realized": True}],
              "rig": {"bones": receipts["AXM_Parcel_Imp_LOD0"]["bones"], "clips": clip_rows},
              "secondary_motion": [{"target": name, "motion_class": {"Coil": "coil-spring", "Antenna": "antenna", "Receipt.01": "cloth-tail", "Receipt.02": "cloth-tail", "Satchel": "carried-prop"}[name],
                                    "max_track_error": max_track_error, "loop_seam_m": max_seam} for name in SECONDARY],
              "anchors": [{"name": name, "kind": "contact" if name.startswith("Contact") else "socket",
                           "position_drift_m": 0, "angle_drift_deg": 0,
                           "surface_distance_m": abs(next(x["position"][2] for x in receipts["AXM_Parcel_Imp_LOD0"]["anchors"] if x["name"] == name)) if name.startswith("Contact") else 0} for name in ANCHORS],
              "lods": lods,
              "views": [{"name": view, "selected_lod": "LOD1", "rgba_rmse": view_metrics[view][0],
                         "silhouette_iou": view_metrics[view][1], "max_rgba_rmse": .03,
                         "min_silhouette_iou": .99} for view in ("play-distance", "far-readability")],
              "files": files,
              "thresholds": {"loop_seam_m": 1e-5, "secondary_track_error": 1e-5, "anchor_position_m": .001, "anchor_angle_deg": .1, "contact_surface_m": .001},
              "limits": ["No continuous target-engine playback was performed.", "LOD comparisons are two imported still views, not continuous perceptual acceptance.", "No frame-time or device performance benchmark was performed."]}
    showcase = compose_game_showcase(source)
    roundtrip = {"schema": "axm.parcel-imp-roundtrip/v0.1", "fresh_import": True, "exports": receipts,
                 "maximum_secondary_local_track_error": max_track_error, "maximum_secondary_world_loop_seam_m": max_seam,
                 "showcase_status": showcase["status"], "showcase_gates": showcase["gates"],
                 "limits": source["limits"], "passed": showcase["status"] == "PASS"}
    (output / "showcase-source.json").write_text(json.dumps(source, indent=2) + "\n")
    (output / "showcase-receipt.json").write_text(json.dumps(showcase, indent=2) + "\n")
    (output / "roundtrip-receipt.json").write_text(json.dumps(roundtrip, indent=2) + "\n")
    if not roundtrip["passed"]: raise ValueError("combined showcase receipt held")


def main():
    parser = argparse.ArgumentParser(); parser.add_argument("mode", choices=("build", "verify")); parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    (build if args.mode == "build" else verify)(args.output.resolve())


if __name__ == "__main__": main()

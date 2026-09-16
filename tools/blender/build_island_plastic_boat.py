"""Build the first real game asset for the island side-scroller: Tiny Plastic Boat.

Run through Blender, after UC has normalized the rigid presentation motion:
  blender --background --factory-startup --python this_file.py -- request.json vehicle-motion.json output_dir

The output is actual authored geometry and an animated GLB, not a rendered-image substitute.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import shutil
import sys

import bpy
from mathutils import Vector


def args_after_dash():
    argv = sys.argv
    if "--" not in argv:
        raise SystemExit("expected -- request.json vehicle-motion.json output_dir")
    values = argv[argv.index("--") + 1:]
    if len(values) != 3:
        raise SystemExit("expected request.json vehicle-motion.json output_dir")
    return Path(values[0]), Path(values[1]), Path(values[2])


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def reset_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for datablocks in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        pass


def mat(name, rgba, metallic=0.0, roughness=0.45):
    material = bpy.data.materials.new(name)
    material.diffuse_color = tuple(rgba)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = tuple(rgba)
        bsdf.inputs["Metallic"].default_value = metallic
        bsdf.inputs["Roughness"].default_value = roughness
    return material


def apply_mod(obj, name):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=name)


def rounded_box(name, location, dimensions, material, bevel=0.10, segments=3):
    bpy.ops.mesh.primitive_cube_add(size=1, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    mod = obj.modifiers.new("RoundedPlastic", "BEVEL")
    mod.width = min(bevel, min(dimensions) * 0.45)
    mod.segments = segments
    apply_mod(obj, mod.name)
    obj.data.materials.append(material)
    return obj


def cylinder(name, location, radius, depth, material, rotation=(0, 0, 0), vertices=20):
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def sphere(name, location, scale, material, segments=24, rings=12):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def torus(name, location, major, minor, material, rotation=(0, 0, 0)):
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=32, minor_segments=10, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.data.materials.append(material)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    return obj


def canopy(name, z, material):
    verts = [(0, 0, z + 0.28)]
    rx, ry = 1.35, 0.92
    for i in range(8):
        a = math.tau * i / 8
        verts.append((math.cos(a) * rx, math.sin(a) * ry, z))
    faces = []
    for i in range(8):
        faces.append((0, 1 + i, 1 + ((i + 1) % 8)))
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    return obj


def sail(name, material, dark):
    verts = [(-0.73, 0.02, 1.05), (0.73, 0.02, 1.05), (0.60, 0.02, 2.05), (-0.60, 0.02, 2.05)]
    mesh = bpy.data.meshes.new(name + "Mesh")
    mesh.from_pydata(verts, [], [(0, 1, 2, 3)])
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.data.materials.append(material)
    # Geometry smiley, so it survives without a texture dependency.
    for x in (-0.25, 0.25):
        eye = sphere(name + "_SmileEye", (x, -0.015, 1.68), (0.055, 0.025, 0.055), dark, 16, 8)
        eye.rotation_euler[0] = math.radians(90)
    for x, z in ((-0.28, 1.43), (0.0, 1.36), (0.28, 1.43)):
        dot = sphere(name + "_SmileMouth", (x, -0.015, z), (0.045, 0.022, 0.045), dark, 12, 6)
        dot.rotation_euler[0] = math.radians(90)
    return obj


def parent_to(obj, root):
    obj.parent = root
    return obj


def socket(name, location, root):
    obj = bpy.data.objects.new(name, None)
    bpy.context.collection.objects.link(obj)
    obj.empty_display_type = "ARROWS"
    obj.empty_display_size = 0.18
    obj.location = location
    obj["axm_socket"] = True
    obj.parent = root
    return obj


def build_model(request):
    palette = request["palette"]
    yellow = mat("PlasticYellow", palette["plastic_yellow"], 0.02, 0.32)
    blue = mat("PlasticBlue", palette["plastic_blue"], 0.05, 0.34)
    red = mat("SalvageRed", palette["salvage_red"], 0.03, 0.40)
    rope = mat("Rope", palette["rope"], 0.0, 0.78)
    cloth = mat("PatchworkCloth", palette["cloth"], 0.0, 0.68)
    dark = mat("DarkMetal", palette["dark_metal"], 0.65, 0.28)
    white = mat("LifeRingWhite", (0.92, 0.89, 0.79, 1), 0.0, 0.45)
    orange = mat("DuckBeak", (0.95, 0.25, 0.03, 1), 0.0, 0.45)

    root = bpy.data.objects.new("AXM_TinyPlasticBoat_ROOT", None)
    bpy.context.collection.objects.link(root)
    root["axm_asset_id"] = request["asset_id"]
    root["axm_game_role"] = request["game_role"]

    meshes = []
    # Inflatable/plastic survival base.
    meshes += [
        parent_to(rounded_box("Pontoon_Left", (0, -0.62, 0.42), (3.05, 0.46, 0.52), yellow, 0.20, 5), root),
        parent_to(rounded_box("Pontoon_Right", (0, 0.62, 0.42), (3.05, 0.46, 0.52), yellow, 0.20, 5), root),
        parent_to(rounded_box("Deck", (0, 0, 0.52), (2.65, 0.95, 0.22), blue, 0.09, 3), root),
        parent_to(rounded_box("BowBumper", (1.48, 0, 0.47), (0.24, 1.34, 0.36), red, 0.11, 3), root),
        parent_to(rounded_box("CargoCrate", (-0.72, 0.0, 0.88), (0.62, 0.72, 0.55), blue, 0.06, 2), root),
    ]
    # Salvage frame and canopy.
    for x in (-0.93, 0.93):
        for y in (-0.55, 0.55):
            meshes.append(parent_to(cylinder("FramePost", (x, y, 1.35), 0.045, 1.58, rope, vertices=12), root))
    for y in (-0.55, 0.55):
        meshes.append(parent_to(cylinder("FrameTop", (0, y, 2.08), 0.045, 1.92, rope, rotation=(0, math.radians(90), 0), vertices=12), root))
    meshes.append(parent_to(canopy("PatchworkCanopy", 2.08, red), root))
    mast = parent_to(cylinder("Mast", (0.0, 0.0, 1.36), 0.055, 2.15, rope, vertices=14), root)
    meshes.append(mast)
    meshes.append(parent_to(sail("SmileySail", cloth, dark), root))

    # Life ring, rubber duck and tiny salvage details.
    meshes.append(parent_to(torus("LifeRing", (-1.32, -0.73, 0.73), 0.28, 0.075, red, rotation=(math.radians(90), 0, 0)), root))
    duck_body = parent_to(sphere("RubberDuckBody", (0.76, -0.12, 0.88), (0.19, 0.14, 0.13), yellow, 20, 10), root)
    duck_head = parent_to(sphere("RubberDuckHead", (0.86, -0.12, 1.06), (0.115, 0.105, 0.11), yellow, 18, 9), root)
    meshes += [duck_body, duck_head]
    bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.065, radius2=0.0, depth=0.15, location=(0.99, -0.12, 1.05), rotation=(0, math.radians(90), 0))
    beak = bpy.context.object
    beak.name = "RubberDuckBeak"
    beak.data.materials.append(orange)
    meshes.append(parent_to(beak, root))

    # Five stable game attachment nodes.
    socket_map = {
        "Socket_Player1": (-0.25, -0.27, 0.78),
        "Socket_Player2": (-0.25, 0.27, 0.78),
        "Socket_WeaponMount": (1.0, 0.0, 0.92),
        "Socket_UpgradeFront": (1.45, 0.0, 0.60),
        "Socket_UpgradeRear": (-1.45, 0.0, 0.60),
    }
    sockets = [socket(name, socket_map[name], root) for name in request["required_game_sockets"]]

    # Coarse collision stays separate from the visual GLBs.
    collision = rounded_box("COLLISION_TinyPlasticBoat", (0, 0, 0.58), (3.05, 1.42, 0.70), dark, 0.04, 1)
    collision.display_type = "WIRE"
    collision.hide_render = True
    collision["axm_collision"] = True

    return root, meshes, sockets, collision


def bind_uc_motion(root, motion):
    samples = motion["source"]["samples"]
    fps = 24
    action = bpy.data.actions.new("Boat_UC_RigidMotion")
    root.animation_data_create()
    root.animation_data.action = action
    root.rotation_mode = "XYZ"
    for sample in samples:
        frame = 1 + round(sample["time_s"] * fps)
        root.location = (sample["impact_offset_m"][0], sample["impact_offset_m"][2], sample["body_heave_m"] + sample["impact_offset_m"][1])
        root.rotation_euler = (
            sample["body_roll_rad"] + sample["impact_rotation_rad"][2],
            sample["body_pitch_rad"] + sample["impact_rotation_rad"][0],
            sample["impact_rotation_rad"][1],
        )
        root.keyframe_insert(data_path="location", frame=frame)
        root.keyframe_insert(data_path="rotation_euler", frame=frame)
    for fcurve in action.fcurves:
        for point in fcurve.keyframe_points:
            point.interpolation = "BEZIER"
    return action, fps, 1 + round(samples[-1]["time_s"] * fps)


def triangles(objects):
    total = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        total += len(obj.data.loop_triangles)
    return total


def select_only(objects):
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_glb(path, objects):
    select_only(objects)
    kwargs = dict(filepath=str(path), export_format="GLB", use_selection=True, export_animations=True)
    try:
        bpy.ops.export_scene.gltf(**kwargs, export_force_sampling=True, export_extras=True)
    except TypeError:
        bpy.ops.export_scene.gltf(**kwargs)


def decimate(objects, ratio):
    for obj in objects:
        if obj.type != "MESH" or len(obj.data.polygons) < 20:
            continue
        mod = obj.modifiers.new("AXM_LOD_DECIMATE", "DECIMATE")
        mod.ratio = ratio
        try:
            apply_mod(obj, mod.name)
        except Exception:
            obj.modifiers.remove(mod)


def look_at(camera, target):
    direction = Vector(target) - camera.location
    camera.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()


def setup_preview_scene(root):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except Exception:
        try:
            scene.render.engine = "BLENDER_EEVEE"
        except Exception:
            pass
    scene.render.resolution_x = 720
    scene.render.resolution_y = 405
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = False
    scene.world.color = (0.055, 0.12, 0.18)

    bpy.ops.object.camera_add(location=(5.4, -6.8, 3.6))
    cam = bpy.context.object
    cam.name = "ProofCamera"
    cam.data.lens = 52
    scene.camera = cam
    look_at(cam, (0, 0, 0.95))

    for name, loc, energy, size in (
        ("Key", (4.5, -3.5, 6.0), 1100, 4.0),
        ("Fill", (-4.0, -2.0, 3.0), 600, 3.0),
        ("Rim", (0.0, 4.0, 5.5), 900, 2.5),
    ):
        data = bpy.data.lights.new(name, type="AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = loc
        look_at(obj, (0, 0, 0.8))

    water = mat("ProofWater", (0.03, 0.30, 0.42, 1), 0.0, 0.20)
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, 0.05))
    plane = bpy.context.object
    plane.name = "PREVIEW_ONLY_Water"
    plane.data.materials.append(water)
    return scene, cam, plane


def render_proofs(out, scene, cam, frame_end):
    proofs = []
    angles = [25, 115, 205, 295]
    scene.frame_set(1)
    for angle in angles:
        r = 7.4
        a = math.radians(angle)
        cam.location = (math.cos(a) * r, math.sin(a) * r, 3.4)
        look_at(cam, (0, 0, 0.95))
        path = out / f"proof_{angle:03d}.png"
        scene.render.filepath = str(path)
        scene.render.image_settings.file_format = "PNG"
        bpy.ops.render.render(write_still=True)
        proofs.append(path.name)

    # Short actual motion proof from the same animated root that is exported.
    cam.location = (5.5, -7.2, 3.4)
    look_at(cam, (0, 0, 0.95))
    scene.frame_start = 1
    scene.frame_end = frame_end
    scene.render.fps = 24
    scene.render.filepath = str(out / "TinyPlasticBoat_motion.mp4")
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "MEDIUM"
    bpy.ops.render.render(animation=True)
    return proofs


def main():
    request_path, motion_path, out = args_after_dash()
    request = json.loads(request_path.read_text(encoding="utf-8"))
    motion = json.loads(motion_path.read_text(encoding="utf-8"))
    if request.get("schema") != "axm.game-asset-island-boat-request/v0.1":
        raise ValueError("unexpected island boat request schema")
    if motion.get("schema") != "axm.rigid-vehicle-motion/v0.1":
        raise ValueError("expected UC rigid vehicle motion output")
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)

    reset_scene()
    root, meshes, sockets, collision = build_model(request)
    action, fps, frame_end = bind_uc_motion(root, motion)
    scene, cam, preview_water = setup_preview_scene(root)

    # Save editable full-detail source before destructive LOD simplification.
    blend_path = out / "TinyPlasticBoat.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))
    proof_names = render_proofs(out, scene, cam, frame_end)

    asset_nodes = [root, *meshes, *sockets]
    lods = {}
    lod0 = out / "TinyPlasticBoat_Animated_LOD0.glb"
    export_glb(lod0, asset_nodes)
    lods["lod0"] = {"file": lod0.name, "triangles": triangles(meshes)}
    shutil.copyfile(lod0, out / "TinyPlasticBoat_LOD0.glb")

    decimate(meshes, 0.58)
    lod1 = out / "TinyPlasticBoat_LOD1.glb"
    export_glb(lod1, asset_nodes)
    lods["lod1"] = {"file": lod1.name, "triangles": triangles(meshes)}

    decimate(meshes, 0.52)
    lod2 = out / "TinyPlasticBoat_LOD2.glb"
    export_glb(lod2, asset_nodes)
    lods["lod2"] = {"file": lod2.name, "triangles": triangles(meshes)}

    collision_path = out / "TinyPlasticBoat_COLLISION.glb"
    export_glb(collision_path, [collision])

    # Copy exact normalized motion evidence beside the asset.
    shutil.copyfile(motion_path, out / "uc-rigid-motion.json")
    shutil.copyfile(request_path, out / "asset-request.json")

    expected = [
        "TinyPlasticBoat.blend",
        "TinyPlasticBoat_Animated_LOD0.glb",
        "TinyPlasticBoat_LOD0.glb",
        "TinyPlasticBoat_LOD1.glb",
        "TinyPlasticBoat_LOD2.glb",
        "TinyPlasticBoat_COLLISION.glb",
        "TinyPlasticBoat_motion.mp4",
        "uc-rigid-motion.json",
        "asset-request.json",
        *proof_names,
    ]
    records = {}
    for name in expected:
        path = out / name
        if not path.is_file() or path.stat().st_size == 0:
            raise RuntimeError(f"missing or empty output: {name}")
        records[name] = {"bytes": path.stat().st_size, "sha256": sha256(path)}

    manifest = {
        "schema": "axm.game-asset-delivery/v0.1",
        "asset_id": request["asset_id"],
        "status": "EXPORTED_ANIMATED_3D_ASSET_VISUAL_REVIEW_REQUIRED",
        "source_request": request,
        "uc_motion": {
            "schema": motion["schema"],
            "source_sha256": motion["source_sha256"],
            "receipt": motion["receipt"],
            "use": "Normalized UC body-heave/pitch/roll fields drive the exported Blender root animation. The compiler's wheel/corner traces are deliberately unused for this non-wheeled boat."
        },
        "animation": {
            "clip": action.name,
            "fps": fps,
            "frames": [1, frame_end],
            "loop_endpoints_match": True
        },
        "game_nodes": [obj.name for obj in sockets],
        "lods": lods,
        "collision": collision_path.name,
        "proofs": proof_names + ["TinyPlasticBoat_motion.mp4"],
        "files": records,
        "truth": {
            "actual_geometry": True,
            "actual_glb": True,
            "actual_exported_animation": True,
            "editable_blender_source": True,
            "engine_controller_integration_proven": False,
            "buoyancy_simulation_proven": False,
            "final_visual_acceptance": False,
            "note": request["truth_boundary"]
        }
    }
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"status": manifest["status"], "output": str(out), "lods": lods, "animation": manifest["animation"]}, indent=2))


if __name__ == "__main__":
    main()

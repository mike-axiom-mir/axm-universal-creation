"""Fresh-import cinematic and motion evidence for the Future UC machine pack."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random

import bpy
from mathutils import Vector

from verify_chaos_hero import action_set, find_action


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def emission(name: str, color: tuple[float, float, float], strength: float):
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    bsdf = material.node_tree.nodes.get("Principled BSDF")
    bsdf.inputs["Base Color"].default_value = (*color, 1)
    bsdf.inputs["Roughness"].default_value = .42
    bsdf.inputs["Emission Color"].default_value = (*color, 1)
    bsdf.inputs["Emission Strength"].default_value = strength
    return material


def studio(width: int, height: int):
    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE"
    scene.eevee.taa_render_samples = 16 if width <= 640 else 32
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = 30
    scene.view_settings.look = "AgX - Medium High Contrast"
    if not scene.world:
        scene.world = bpy.data.worlds.new("UC deep-space workshop")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.0025, .006, .018, 1)
    background.inputs["Strength"].default_value = .12

    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    nodes.clear()
    layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = .55
    glare.size = 7
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])

    # Preview-only cosmic depth; these objects are never exported as game assets.
    star_material = emission("PREVIEW star light", (.42, .68, 1.0), 7)
    warm_star = emission("PREVIEW warm star", (1.0, .58, .22), 5)
    rng = random.Random(91024)
    for index in range(110):
        angle = rng.uniform(0, math.tau)
        elevation = rng.uniform(-.08, .68)
        radius = rng.uniform(22, 35)
        location = (math.cos(angle) * radius, math.sin(angle) * radius, elevation * radius + 3)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rng.uniform(.018, .065), location=location)
        star = bpy.context.object
        star.name = f"PREVIEW_star_{index:03d}"
        star.data.materials.append(warm_star if index % 17 == 0 else star_material)
    planet_material = emission("PREVIEW distant planet", (.07, .18, .34), .22)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, location=(9, 10, 12), scale=(3.2, 3.2, 3.2))
    planet = bpy.context.object
    planet.name = "PREVIEW_distant_planet"
    planet.data.materials.append(planet_material)
    ring_material = emission("PREVIEW planet ring", (.55, .66, .78), .55)
    bpy.ops.mesh.primitive_torus_add(major_radius=4.2, minor_radius=.11, major_segments=96, minor_segments=10, location=(9, 10, 12), rotation=(.55, .22, -.18))
    bpy.context.object.data.materials.append(ring_material)

    for name, location, energy, size, color in [
        ("Warm creation key", (-8, -10, 13), 1750, 7.0, (1.0, .64, .34)),
        ("Cool machine fill", (10, -7, 9), 1450, 6.0, (.35, .72, 1.0)),
        ("Rear rim", (1, 9, 11), 1850, 5.5, (.42, .60, 1.0)),
        ("Island softbox", (-10, 2, 5), 850, 5.0, (.60, .72, 1.0)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0, 0, 1.4)) - light.location).to_track_quat("-Z", "Y").to_euler()
    for name, location, energy, color in [
        ("Core photon bounce", (0, 0, 3.0), 540, (.15, .72, 1.0)),
        ("Lower forge warmth", (0, -1, .4), 360, (1.0, .38, .10)),
    ]:
        data = bpy.data.lights.new(name, "POINT")
        data.energy = energy
        data.color = color
        data.shadow_soft_size = 2.2
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "PREVIEW_camera"
    camera.data.lens = 52
    camera.data.sensor_width = 36
    scene.camera = camera
    return camera


def aim(camera, location, target, lens=52, dof=False):
    camera.location = location
    camera.data.lens = lens
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.dof.use_dof = dof
    if dof:
        camera.data.dof.focus_object = None
        camera.data.dof.focus_distance = (Vector(target) - camera.location).length
        camera.data.dof.aperture_fstop = 4.0


def imported_asset(root: Path, filename: str):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(root / filename))
    new = [obj for obj in bpy.context.scene.objects if obj not in before]
    arm = next(obj for obj in new if obj.type == "ARMATURE")
    return new, arm


def render_stills(root: Path, width: int, height: int, only_shot: str | None = None) -> list[dict]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Future_UC_Creation_Machine_LOD0.glb")
    camera = studio(width, height)
    scene = bpy.context.scene
    states = [
        ("hero-oblique.png", "Forge_Idle", 58, (12.5, -16.8, 10.2), (0, 0, 1.10), 52, False, "primary hero silhouette"),
        ("core-closeup.png", "Forge_Build_Pulse", 61, (6.1, -8.2, 5.8), (0, 0, 2.55), 68, True, "core, rings, gantry and material detail"),
        ("process-ring.png", "Forge_Idle", 132, (1.0, -15.2, 13.8), (0, 0, .85), 52, False, "eight-pylon radial readability"),
        ("environment-rear.png", "Forge_Idle", 186, (-12.8, 15.5, 8.4), (0, 0, .70), 56, False, "rear, islands, underside and transit"),
        ("dormant-state.png", "Dormant_To_Awake", 0, (11.7, -16.0, 9.1), (0, 0, 1.0), 54, False, "dormant state"),
        ("awake-state.png", "Dormant_To_Awake", 90, (11.7, -16.0, 9.1), (0, 0, 1.0), 54, False, "awake state"),
        ("reactor-detail.png", "Forge_Build_Pulse", 42, (4.2, -6.4, 3.1), (0, 0, 1.18), 70, True, "reactor heatshields, umbilicals and diagnostics"),
        ("pylon-detail.png", "Forge_Build_Pulse", 68, (3.7, -7.7, 2.7), (0, -4.15, .92), 74, True, "pylon joints, focus prongs, console and conduit isolators"),
        ("island-workshop-detail.png", "Forge_Idle", 132, (8.2, -7.5, 3.9), (5.45, -3.50, .83), 72, True, "inhabited island workshops, load ribs and underside services"),
        ("cloud-bus-detail.png", "Forge_Idle", 186, (-9.2, -5.9, 5.7), (-5.65, -1.10, 3.35), 72, True, "transit pressure bands, utility rails, pods and sensor hardware"),
    ]
    evidence = []
    for filename, clip, frame, location, target, lens, dof, purpose in states:
        if only_shot and filename != only_shot:
            continue
        action_set(arm, find_action(clip))
        scene.frame_set(frame)
        aim(camera, location, target, lens, dof)
        path = root / filename
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        evidence.append({"path": filename, "sha256": sha256(path), "clip": clip, "frame": frame, "purpose": purpose, "viewport_px": [width, height]})
        print("FUTURE_UC_RENDER", filename, flush=True)
    return evidence


def render_lod2(root: Path, width: int, height: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Future_UC_Creation_Machine_LOD2.glb")
    camera = studio(width, height)
    action_set(arm, find_action("Forge_Idle"))
    bpy.context.scene.frame_set(58)
    aim(camera, (16.8, -23.0, 14.0), (0, 0, .8), 58)
    path = root / "lod2-environment-distance.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"path": path.name, "sha256": sha256(path), "clip": "Forge_Idle", "frame": 58, "purpose": "LOD2 environment-distance silhouette", "viewport_px": [width, height]}


def render_motion(root: Path, width: int, height: int, count: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Future_UC_Creation_Machine_LOD1.glb")
    camera = studio(width, height)
    scene = bpy.context.scene
    action = find_action("Forge_Build_Pulse")
    action_set(arm, action)
    aim(camera, (13.2, -17.2, 9.7), (0, 0, 1.05), 54)
    folder = root / "motion-frames"
    folder.mkdir(exist_ok=True)
    first, last = action.frame_range
    rows = []
    for index in range(count):
        fraction = index / count
        frame = first + (last - first) * fraction
        scene.frame_set(int(frame), subframe=frame - int(frame))
        path = folder / f"{index:04d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        rows.append({"path": f"motion-frames/{path.name}", "source_frame": frame, "sha256": sha256(path)})
        print("FUTURE_UC_MOTION_FRAME", index + 1, count, flush=True)
    receipt = {
        "clip": "Forge_Build_Pulse",
        "source_lod": "Future_UC_Creation_Machine_LOD1.glb",
        "sampled_frames": count,
        "playback_fps": 12,
        "viewport_px": [width, height],
        "frames": rows,
    }
    (root / "motion-render.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    return receipt


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--width", type=int, default=960)
    parser.add_argument("--height", type=int, default=720)
    parser.add_argument("--motion", action="store_true")
    parser.add_argument("--motion-frames", type=int, default=36)
    parser.add_argument("--only-shot", choices=[
        "hero-oblique.png", "core-closeup.png", "process-ring.png", "environment-rear.png",
        "dormant-state.png", "awake-state.png", "reactor-detail.png", "pylon-detail.png",
        "island-workshop-detail.png", "cloud-bus-detail.png",
    ])
    args = parser.parse_args()
    root = args.directory.resolve()
    if args.motion:
        render_motion(root, args.width, args.height, args.motion_frames)
        return
    stills = render_stills(root, args.width, args.height, args.only_shot)
    lod2 = render_lod2(root, args.width, args.height) if not args.only_shot else None
    receipt = {
        "schema": "axm.uc.future-creation-machine-render-evidence/v1",
        "source": "freshly imported exported GLBs",
        "render_engine": "Blender Eevee with compositor glow",
        "stills": stills + ([lod2] if lod2 else []),
        "limits": "These images prove only the captured camera, animation and LOD states; they do not prove every engine or viewpoint.",
    }
    (root / "render-evidence.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

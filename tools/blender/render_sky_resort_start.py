"""Fresh-import still and motion evidence for the opening-world diorama."""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import random
import sys

import bpy
from mathutils import Vector

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

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
    try:
        scene.eevee.taa_render_samples = 4 if width <= 500 else 8 if width <= 720 else 16
    except Exception:
        pass
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.film_transparent = False
    scene.render.fps = 30
    scene.view_settings.look = "AgX - Medium High Contrast"
    if not scene.world:
        scene.world = bpy.data.worlds.new("PREVIEW tropical sky")
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.018, .055, .105, 1)
    background.inputs["Strength"].default_value = .42

    scene.use_nodes = True
    nodes = scene.node_tree.nodes
    links = scene.node_tree.links
    nodes.clear()
    layers = nodes.new("CompositorNodeRLayers")
    glare = nodes.new("CompositorNodeGlare")
    glare.glare_type = "FOG_GLOW"
    glare.quality = "HIGH"
    glare.threshold = .72
    glare.size = 7
    composite = nodes.new("CompositorNodeComposite")
    links.new(layers.outputs["Image"], glare.inputs["Image"])
    links.new(glare.outputs["Image"], composite.inputs["Image"])

    # Preview-only distant sky islands and stars give the miniature a world context.
    cool = emission("PREVIEW cool horizon", (.18, .46, .72), .4)
    warm = emission("PREVIEW warm horizon", (1.0, .52, .20), .75)
    rng = random.Random(22091)
    for index in range(46):
        angle = rng.uniform(0, math.tau)
        radius = rng.uniform(18, 31)
        z = rng.uniform(1.0, 17.0)
        bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1, radius=rng.uniform(.018, .055),
                                              location=polar(radius, angle, z))
        bpy.context.object.data.materials.append(warm if index % 11 == 0 else cool)
    for index, angle in enumerate((.72, 2.65, 4.80)):
        location = polar(17 + index * 3, angle, 6.2 + index * 1.4)
        bpy.ops.mesh.primitive_cone_add(vertices=10, radius1=.48 + index * .08, radius2=.18,
                                        depth=1.55, location=location)
        shard = bpy.context.object
        shard.name = f"PREVIEW distant island {index:02d}"
        shard.data.materials.append(cool)

    for name, location, energy, size, color in [
        ("Sunset key", (-10, -14, 15), 1900, 7.0, (1.0, .66, .36)),
        ("Sky fill", (11, -6, 13), 1550, 8.0, (.34, .68, 1.0)),
        ("Water rim", (1, 10, 12), 2100, 6.5, (.42, .78, 1.0)),
        ("Lower island fill", (-8, 3, 4), 1450, 5.5, (.40, .66, .86)),
    ]:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.shape = "DISK"
        data.size = size
        data.color = color
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        light.rotation_euler = (Vector((0, 0, 5.1)) - light.location).to_track_quat("-Z", "Y").to_euler()
    for name, location, energy, color, radius in [
        ("Crater photon source", (0, 0, 3.05), 750, (.12, .72, 1.0), 1.4),
        ("Shield bounce", (0, -1, 8.2), 560, (.18, .80, 1.0), 2.6),
        ("Sanctuary warmth", (0, -.4, 9.4), 410, (1.0, .53, .18), 1.5),
    ]:
        data = bpy.data.lights.new(name, "POINT")
        data.energy = energy
        data.color = color
        data.shadow_soft_size = radius
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.name = "PREVIEW_camera"
    camera.data.sensor_width = 36
    scene.camera = camera
    return camera


def polar(radius: float, angle: float, z: float) -> tuple[float, float, float]:
    return (radius * math.cos(angle), radius * math.sin(angle), z)


def aim(camera, location, target, lens=55, dof=False):
    camera.location = location
    camera.data.lens = lens
    camera.rotation_euler = (Vector(target) - camera.location).to_track_quat("-Z", "Y").to_euler()
    camera.data.dof.use_dof = dof
    if dof:
        camera.data.dof.focus_object = None
        camera.data.dof.focus_distance = (Vector(target) - camera.location).length
        camera.data.dof.aperture_fstop = 4.6


def imported_asset(root: Path, filename: str):
    before = set(bpy.context.scene.objects)
    bpy.ops.import_scene.gltf(filepath=str(root / filename))
    new = [obj for obj in bpy.context.scene.objects if obj not in before]
    arm = next(obj for obj in new if obj.type == "ARMATURE")
    return new, arm


def render_stills(root: Path, width: int, height: int, only_shot: str | None = None) -> list[dict]:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Inverted_Water_Sanctuary_LOD0.glb")
    camera = studio(width, height)
    scene = bpy.context.scene
    states = [
        ("hero-oblique.png", "Sanctuary_Idle", 64, (18.2, -24.0, 9.0), (0, 0, 5.1), 58, False,
         "primary lower-island, reverse-water and upper-boundary silhouette"),
        ("water-spine.png", "Watershield_Pulse", 58, (7.6, -10.2, 7.0), (0, 0, 5.1), 72, True,
         "reverse-water ribbon volume, foam and crater connection"),
        ("sanctuary-crown.png", "Sanctuary_Idle", 118, (8.8, -11.6, 11.6), (0, 0, 8.6), 68, True,
         "upper lagoon, pavilions, vegetation and sanctuary detail"),
        ("water-boundary.png", "Watershield_Pulse", 96, (10.6, -13.8, 9.0), (0, 0, 8.0), 68, False,
         "thick circulating water torus and complete protected perimeter"),
        ("arrival-gate.png", "Sanctuary_Idle", 154, (3.3, -8.9, 9.2), (0, -4.0, 8.85), 78, True,
         "direct portal arrival, light guides and replacement-ready bus socket"),
        ("lower-island.png", "Sanctuary_Idle", 188, (8.9, -11.7, 5.4), (0, 0, 1.45), 70, True,
         "lower ruins, palms, shore, springs and layered volcano"),
        ("rear-underside.png", "Sanctuary_Idle", 206, (-13.1, 14.9, 9.4), (0, 0, 5.6), 60, False,
         "rear authorship, hanging geology, cascades and water volume"),
        ("dormant-state.png", "Arrival_Awakening", 0, (14.0, -18.1, 10.5), (0, 0, 5.0), 56, False,
         "dormant opening-world state"),
        ("awake-state.png", "Arrival_Awakening", 120, (14.0, -18.1, 10.5), (0, 0, 5.0), 56, False,
         "fully awakened opening-world state"),
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
        evidence.append({"path": filename, "sha256": sha256(path), "clip": clip,
                         "frame": frame, "purpose": purpose, "viewport_px": [width, height]})
        print("SKY_RESORT_RENDER", filename, flush=True)
    return evidence


def render_lod2(root: Path, width: int, height: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Inverted_Water_Sanctuary_LOD2.glb")
    camera = studio(width, height)
    action_set(arm, find_action("Sanctuary_Idle"))
    bpy.context.scene.frame_set(64)
    aim(camera, (19.0, -24.4, 13.0), (0, 0, 5.0), 62)
    path = root / "lod2-distance.png"
    bpy.context.scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return {"path": path.name, "sha256": sha256(path), "clip": "Sanctuary_Idle", "frame": 64,
            "purpose": "LOD2 decorative/environment-distance silhouette", "viewport_px": [width, height]}


def render_motion(root: Path, width: int, height: int, count: int) -> dict:
    bpy.ops.wm.read_factory_settings(use_empty=True)
    _, arm = imported_asset(root, "Inverted_Water_Sanctuary_LOD1.glb")
    camera = studio(width, height)
    scene = bpy.context.scene
    action = find_action("Watershield_Pulse")
    action_set(arm, action)
    aim(camera, (14.2, -18.2, 10.7), (0, 0, 5.05), 56)
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
        rows.append({"path": f"motion-frames/{path.name}", "source_frame": frame,
                     "sha256": sha256(path)})
        print("SKY_RESORT_MOTION_FRAME", index + 1, count, flush=True)
    duration_seconds = (last - first) / scene.render.fps
    playback_fps = count / duration_seconds
    receipt = {"clip": "Watershield_Pulse", "source_lod": "Inverted_Water_Sanctuary_LOD1.glb",
               "sampled_frames": count, "clip_duration_seconds": duration_seconds,
               "playback_fps": playback_fps, "viewport_px": [width, height],
               "frames": rows}
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
        "hero-oblique.png", "water-spine.png", "sanctuary-crown.png", "water-boundary.png",
        "arrival-gate.png", "lower-island.png", "rear-underside.png", "dormant-state.png",
        "awake-state.png",
    ])
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    root = args.directory.resolve()
    if args.motion:
        render_motion(root, args.width, args.height, args.motion_frames)
        return
    stills = render_stills(root, args.width, args.height, args.only_shot)
    lod2 = render_lod2(root, args.width, args.height) if not args.only_shot else None
    receipt = {
        "schema": "axm.uc.inverted-water-sanctuary-render-evidence/v1",
        "source": "freshly imported exported GLBs",
        "render_engine": "Blender Eevee with compositor glow",
        "stills": stills + ([lod2] if lod2 else []),
        "limits": "These images prove only the captured camera, animation and LOD states; they do not prove every engine or viewpoint.",
    }
    (root / "render-evidence.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()

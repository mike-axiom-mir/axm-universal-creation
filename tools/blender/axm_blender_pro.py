from __future__ import annotations

"""Reusable high-quality Blender helpers for AXM Universal Creation.

This module is intentionally additive. Existing forge scripts can adopt these
helpers progressively instead of being rewritten. It centralizes the pieces
that had drifted across many bpy scripts: render profiles, color management,
world setup, camera aim, light rigs, PBR materials, deterministic seeds, and
pre-render scene validation.
"""

import json
import math
from pathlib import Path
from typing import Any

import bpy
from mathutils import Vector


NATIVE_SCENE_SCHEMA = "axm.native-visual-scene/v0.1"


RENDER_PROFILES: dict[str, dict[str, Any]] = {
    "preview": {
        "engine": "BLENDER_EEVEE_NEXT",
        "resolution": 640,
        "samples": 32,
        "denoise": False,
        "bounces": 3,
    },
    "lookdev": {
        "engine": "BLENDER_EEVEE_NEXT",
        "resolution": 960,
        "samples": 64,
        "denoise": False,
        "bounces": 4,
    },
    "hero": {
        "engine": "CYCLES",
        "resolution": 1280,
        "samples": 96,
        "denoise": True,
        "bounces": 7,
    },
    "proof": {
        "engine": "CYCLES",
        "resolution": 900,
        "samples": 64,
        "denoise": True,
        "bounces": 6,
    },
}


def configure_render(
    profile: str = "hero",
    *,
    resolution: int | None = None,
    transparent: bool = False,
    seed: int = 42,
) -> dict[str, Any]:
    key = str(profile).strip().casefold()
    if key not in RENDER_PROFILES:
        raise ValueError(f"unknown render profile: {profile}")
    spec = dict(RENDER_PROFILES[key])
    if resolution is not None:
        spec["resolution"] = max(128, min(8192, int(resolution)))

    scene = bpy.context.scene
    scene.render.engine = spec["engine"]
    scene.render.resolution_x = spec["resolution"]
    scene.render.resolution_y = spec["resolution"]
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = bool(transparent)

    if spec["engine"] == "CYCLES":
        scene.cycles.samples = spec["samples"]
        scene.cycles.use_denoising = spec["denoise"]
        scene.cycles.seed = int(seed)
        scene.cycles.max_bounces = spec["bounces"]
        scene.cycles.diffuse_bounces = min(4, spec["bounces"])
        scene.cycles.glossy_bounces = min(4, spec["bounces"])

    try:
        scene.view_settings.look = "AgX - Medium High Contrast"
    except (TypeError, ValueError):
        # Keep the helper usable across Blender versions whose AgX labels differ.
        pass
    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0
    return {"profile": key, **spec, "transparent": bool(transparent), "seed": int(seed)}


def configure_world(
    color: tuple[float, float, float] = (0.012, 0.018, 0.032),
    *,
    strength: float = 0.24,
) -> bpy.types.World:
    world = bpy.context.scene.world or bpy.data.worlds.new("AXM_World")
    bpy.context.scene.world = world
    world.use_nodes = True
    nodes = world.node_tree.nodes
    background = nodes.get("Background")
    if background is None:
        background = nodes.new("ShaderNodeBackground")
    background.inputs["Color"].default_value = (*color, 1.0)
    background.inputs["Strength"].default_value = max(0.0, float(strength))
    return world


def aim_at(obj: bpy.types.Object, target: tuple[float, float, float] | Vector) -> None:
    vector = Vector(target) - obj.location
    if vector.length <= 1e-8:
        raise ValueError("camera/light cannot aim at its own location")
    obj.rotation_euler = vector.to_track_quat("-Z", "Y").to_euler()


def make_camera(
    *,
    name: str = "AXM_HeroCamera",
    location: tuple[float, float, float] = (7.5, 5.0, 9.0),
    target: tuple[float, float, float] = (0.0, 1.4, 0.0),
    lens_mm: float = 58.0,
) -> bpy.types.Object:
    data = bpy.data.cameras.new(f"{name}_Data")
    camera = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(camera)
    camera.location = location
    data.lens = float(lens_mm)
    data.sensor_width = 36.0
    aim_at(camera, target)
    bpy.context.scene.camera = camera
    return camera


def _area_light(
    name: str,
    location: tuple[float, float, float],
    target: tuple[float, float, float],
    *,
    energy: float,
    color: tuple[float, float, float],
    size: float,
) -> bpy.types.Object:
    data = bpy.data.lights.new(f"{name}_Data", type="AREA")
    data.energy = float(energy)
    data.color = color
    data.shape = "DISK"
    data.size = float(size)
    light = bpy.data.objects.new(name, data)
    bpy.context.collection.objects.link(light)
    light.location = location
    aim_at(light, target)
    return light


def three_point_lighting(
    *,
    target: tuple[float, float, float] = (0.0, 1.4, 0.0),
    scale: float = 1.0,
) -> list[bpy.types.Object]:
    s = max(0.1, float(scale))
    return [
        _area_light(
            "AXM_Key", (4.8 * s, 7.2 * s, 5.5 * s), target,
            energy=1050 * s, color=(1.0, 0.78, 0.62), size=4.2 * s,
        ),
        _area_light(
            "AXM_Fill", (-5.5 * s, 4.0 * s, 2.8 * s), target,
            energy=620 * s, color=(0.38, 0.58, 1.0), size=5.0 * s,
        ),
        _area_light(
            "AXM_Rim", (0.6 * s, 5.8 * s, -5.8 * s), target,
            energy=880 * s, color=(0.35, 0.92, 1.0), size=3.4 * s,
        ),
    ]


def pbr_material(
    name: str,
    *,
    base_color: tuple[float, float, float, float] = (0.35, 0.4, 0.46, 1.0),
    metallic: float = 0.0,
    roughness: float = 0.45,
    emission: tuple[float, float, float] = (0.0, 0.0, 0.0),
    emission_strength: float = 0.0,
) -> bpy.types.Material:
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    node = material.node_tree.nodes.get("Principled BSDF")
    if node is None:
        raise RuntimeError("Principled BSDF node unavailable")
    node.inputs["Base Color"].default_value = base_color
    node.inputs["Metallic"].default_value = max(0.0, min(1.0, float(metallic)))
    node.inputs["Roughness"].default_value = max(0.04, min(1.0, float(roughness)))
    emission_socket = node.inputs.get("Emission Color") or node.inputs.get("Emission")
    if emission_socket is not None:
        emission_socket.default_value = (*emission, 1.0)
    strength_socket = node.inputs.get("Emission Strength")
    if strength_socket is not None:
        strength_socket.default_value = max(0.0, float(emission_strength))
    return material


def _clear_native_scene_objects() -> None:
    for obj in list(bpy.context.scene.objects):
        if obj.get("axm_native_scene"):
            bpy.data.objects.remove(obj, do_unlink=True)


def _native_primitive(entry: dict[str, Any]) -> bpy.types.Object:
    primitive = entry["primitive"]
    if primitive == "box":
        bpy.ops.mesh.primitive_cube_add(size=1.0)
    elif primitive == "sphere":
        bpy.ops.mesh.primitive_uv_sphere_add(segments=48, ring_count=24, radius=0.5)
    elif primitive == "cylinder":
        bpy.ops.mesh.primitive_cylinder_add(vertices=48, radius=0.5, depth=1.0)
    elif primitive == "plane":
        bpy.ops.mesh.primitive_plane_add(size=1.0)
    else:
        raise ValueError(f"unsupported native primitive: {primitive}")
    obj = bpy.context.active_object
    obj.name = f"AXM_NV_{entry['id']}"
    obj.location = entry["position"]
    obj.rotation_euler = tuple(math.radians(float(value)) for value in entry["rotation_degrees"])
    obj.scale = entry["scale"]
    obj["axm_native_scene"] = True
    obj["axm_native_id"] = entry["id"]
    material_spec = entry["material"]
    material = pbr_material(
        f"AXM_NV_MAT_{entry['id']}",
        base_color=tuple(material_spec["base_color"]),
        metallic=material_spec["metallic"],
        roughness=material_spec["roughness"],
        emission=tuple(material_spec["emissive"]),
        emission_strength=material_spec["emissive_strength"],
    )
    obj.data.materials.append(material)
    return obj


def apply_native_scene(scene_data: dict[str, Any], *, clear_previous: bool = True) -> dict[str, Any]:
    """Realize the AXM native visual scene contract inside Blender.

    The coded WebGL runtime and Blender therefore share camera, object,
    material, light, and world state. This bridge deliberately does not claim
    equivalent pixels or equivalent visual quality between renderers.
    """
    if not isinstance(scene_data, dict) or scene_data.get("schema") != NATIVE_SCENE_SCHEMA:
        raise ValueError(f"scene_data must use {NATIVE_SCENE_SCHEMA}")
    if clear_previous:
        _clear_native_scene_objects()

    world = configure_world(
        tuple(scene_data["background"][:3]),
        strength=max(0.0, float(scene_data["ambient"]["intensity"])),
    )
    world["axm_native_scene"] = True
    created: list[str] = []
    for entry in scene_data.get("objects", []):
        if not entry.get("visible", True):
            continue
        created.append(_native_primitive(entry).name)

    camera_spec = scene_data["camera"]
    camera = make_camera(
        name="AXM_NV_Camera",
        location=tuple(camera_spec["position"]),
        target=tuple(camera_spec["target"]),
        lens_mm=50.0,
    )
    camera.data.angle = math.radians(float(camera_spec["fov_degrees"]))
    camera.data.clip_start = float(camera_spec["near"])
    camera.data.clip_end = float(camera_spec["far"])
    camera["axm_native_scene"] = True

    light_names: list[str] = []
    for entry in scene_data.get("lights", []):
        kind = entry["kind"]
        data = bpy.data.lights.new(
            f"AXM_NV_{entry['id']}_Data",
            type="POINT" if kind == "point" else "SUN",
        )
        data.color = tuple(entry["color"])
        data.energy = max(0.0, float(entry["intensity"])) * (120.0 if kind == "point" else 1.6)
        if kind == "point":
            data.shadow_soft_size = max(0.05, min(float(entry.get("range", 25.0)) * 0.025, 4.0))
        light = bpy.data.objects.new(f"AXM_NV_{entry['id']}", data)
        bpy.context.collection.objects.link(light)
        light["axm_native_scene"] = True
        if kind == "point":
            light.location = entry["position"]
        else:
            direction = Vector(entry["direction"])
            if direction.length <= 1e-8:
                raise ValueError(f"native directional light {entry['id']} has zero direction")
            light.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
        light_names.append(light.name)

    return {
        "schema": "axm.native-visual-to-blender/v0.1",
        "source_scene_sha256": scene_data.get("scene_sha256"),
        "created_objects": created,
        "camera": camera.name,
        "lights": light_names,
        "truth": {
            "shared_scene_contract_realized": True,
            "renderer_pixel_parity_claimed": False,
            "visual_acceptance_requires_rendered_review": True,
        },
    }


def validate_scene(*, require_camera: bool = True, require_mesh: bool = True) -> dict[str, Any]:
    scene = bpy.context.scene
    meshes = [obj for obj in scene.objects if obj.type == "MESH"]
    cameras = [obj for obj in scene.objects if obj.type == "CAMERA"]
    lights = [obj for obj in scene.objects if obj.type == "LIGHT"]
    materials = {slot.material.name for obj in meshes for slot in obj.material_slots if slot.material}
    issues: list[str] = []
    if require_camera and scene.camera is None:
        issues.append("scene has no active camera")
    if require_mesh and not meshes:
        issues.append("scene has no mesh objects")
    for obj in meshes:
        if any(abs(component) < 1e-8 for component in obj.scale):
            issues.append(f"{obj.name}: zero scale component")
        if obj.data and len(obj.data.polygons) == 0:
            issues.append(f"{obj.name}: mesh has no polygons")
    for material in bpy.data.materials:
        if material.users and not material.use_nodes:
            issues.append(f"{material.name}: material is not node based")
    return {
        "schema": "axm.blender-scene-validation/v0.1",
        "status": "PASS" if not issues else "FAIL",
        "counts": {
            "meshes": len(meshes),
            "cameras": len(cameras),
            "lights": len(lights),
            "materials": len(materials),
        },
        "issues": issues,
        "truth": {"visual_quality_judged": False, "structural_scene_checks_only": True},
    }


def proof_angles(count: int = 4, *, offset_degrees: float = 32.0) -> list[float]:
    count = int(count)
    if count < 1 or count > 36:
        raise ValueError("proof angle count must be between 1 and 36")
    step = 360.0 / count
    return [round((float(offset_degrees) + step * index) % 360.0, 6) for index in range(count)]


def write_scene_receipt(
    path: str | Path,
    *,
    render_profile: dict[str, Any] | None = None,
) -> dict[str, Any]:
    validation = validate_scene()
    receipt = {
        "schema": "axm.blender-pro-scene-receipt/v0.1",
        "validation": validation,
        "render_profile": render_profile,
        "proof_angles": proof_angles(4),
        "truth": {
            "bpy_scene_executed": True,
            "visual_acceptance_requires_rendered_review": True,
            "receipt_is_not_a_quality_claim": True,
        },
    }
    Path(path).write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return receipt


def main(argv: list[str] | None = None) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Realize an AXM native visual scene in Blender")
    parser.add_argument("--native-scene", type=Path, required=True, help="Compiled AXM native scene JSON")
    parser.add_argument("--output-blend", type=Path, required=True, help="Destination .blend file")
    parser.add_argument("--receipt", type=Path, required=True, help="Destination Blender scene receipt JSON")
    parser.add_argument("--profile", choices=sorted(RENDER_PROFILES), default="hero")
    parser.add_argument("--resolution", type=int)
    parser.add_argument("--transparent", action="store_true")
    args = parser.parse_args(argv)

    scene_data = json.loads(args.native_scene.read_text(encoding="utf-8"))
    bridge = apply_native_scene(scene_data)
    profile = configure_render(
        args.profile,
        resolution=args.resolution,
        transparent=args.transparent,
    )
    validation = validate_scene()
    if validation["status"] != "PASS":
        raise RuntimeError(f"native scene failed Blender structural validation: {validation['issues']}")
    args.output_blend.parent.mkdir(parents=True, exist_ok=True)
    args.receipt.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    receipt = write_scene_receipt(args.receipt, render_profile=profile)
    receipt["native_scene_bridge"] = bridge
    args.receipt.write_text(json.dumps(receipt, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

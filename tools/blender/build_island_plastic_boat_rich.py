"""Rich-material realization wrapper for the proven Tiny Plastic Boat builder.

The underlying geometry, animation, LOD, socket and collision exporter remains
unchanged. This wrapper adds UC-generated portable PBR material bundles, smart UVs
and a surface receipt before delegating to the proven exporter.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import bpy

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.rich_game_materials import generate_rich_game_material
from axm_uc.rich_game_material_bridge import blender_rich_game_material


def _load_base_builder():
    path = Path(__file__).with_name("build_island_plastic_boat.py")
    spec = importlib.util.spec_from_file_location("axm_island_boat_base", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


BASE = _load_base_builder()


def _rgba_to_rgb(value):
    return tuple(max(0, min(255, round(float(channel) * 255))) for channel in value[:3])


def _smart_uv(obj):
    if obj.type != "MESH":
        return
    bpy.ops.object.select_all(action="DESELECT")
    obj.hide_set(False)
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    try:
        bpy.ops.uv.smart_project(
            angle_limit=1.15192,
            island_margin=.018,
            area_weight=.5,
            correct_aspect=True,
            scale_to_bounds=True,
        )
    finally:
        bpy.ops.object.mode_set(mode="OBJECT")
    if obj.data.uv_layers:
        obj.data.uv_layers.active.name = "AXM_GameMaterialUV"


def _replace_material(obj, material):
    if obj.type != "MESH":
        return
    obj.data.materials.clear()
    obj.data.materials.append(material)


def _profile_specs(request):
    palette = request["palette"]
    configured = request.get("material_profiles", {})
    defaults = {
        "pontoon": {"profile": "sun-faded-plastic", "color": "plastic_yellow"},
        "deck": {"profile": "scratched-fiberglass", "color": "plastic_blue"},
        "bumper": {"profile": "weathered-rubber", "color": "salvage_red"},
        "frame": {"profile": "weathered-aluminum", "color": "dark_metal"},
        "canopy": {"profile": "canvas", "color": "salvage_red"},
        "sail": {"profile": "sailcloth", "color": "cloth"},
        "life_ring": {"profile": "sun-faded-plastic", "color": "salvage_red"},
        "duck": {"profile": "molded-plastic", "color": "plastic_yellow"},
        "duck_beak": {"profile": "molded-plastic", "rgb": [242, 86, 18]},
    }
    specs = {}
    for role, fallback in defaults.items():
        source = dict(fallback)
        source.update(configured.get(role, {}))
        profile = source["profile"]
        if "rgb" in source:
            rgb = tuple(source["rgb"])
        else:
            rgb = _rgba_to_rgb(palette[source["color"]])
        specs[role] = {"profile": profile, "rgb": rgb}
    return specs


def _build_rich_materials(out, request):
    root = out / "materials"
    root.mkdir(exist_ok=False)
    specs = _profile_specs(request)
    materials = {}
    records = {}
    for index, (role, spec) in enumerate(specs.items()):
        folder = root / role
        manifest = generate_rich_game_material(
            folder,
            spec["profile"],
            size=int(request.get("material_texture_size", 256)),
            seed=int(request.get("material_seed", 9137)) + index * 101,
            color=tuple(spec["rgb"]),
        )
        material = blender_rich_game_material(folder, "UC_BOAT_" + role.upper())
        materials[role] = material
        records[role] = {
            "profile": spec["profile"],
            "rgb": list(spec["rgb"]),
            "bundle": str(Path("materials") / role),
            "maps": sorted(manifest["maps"]),
        }
    return materials, records


def _rich_build_model(request):
    root, meshes, sockets, collision = BASE_BUILD_MODEL(request)
    materials, records = _build_rich_materials(OUTPUT, request)

    for obj in meshes:
        _smart_uv(obj)
        name = obj.name
        role = None
        if name.startswith("Pontoon_"):
            role = "pontoon"
        elif name in ("Deck", "CargoCrate"):
            role = "deck"
        elif name == "BowBumper":
            role = "bumper"
        elif name.startswith("FramePost") or name.startswith("FrameTop") or name == "Mast":
            role = "frame"
        elif name == "PatchworkCanopy":
            role = "canopy"
        elif name == "SmileySail":
            role = "sail"
        elif name == "LifeRing":
            role = "life_ring"
        elif name in ("RubberDuckBody", "RubberDuckHead"):
            role = "duck"
        elif name == "RubberDuckBeak":
            role = "duck_beak"
        if role:
            _replace_material(obj, materials[role])

    _smart_uv(collision)
    OUTPUT_SURFACE_RECORDS.clear()
    OUTPUT_SURFACE_RECORDS.update(records)
    return root, meshes, sockets, collision


def _update_delivery_manifest(out):
    path = out / "manifest.json"
    manifest = json.loads(path.read_text(encoding="utf-8"))
    manifest["surface_system"] = {
        "schema": "axm.rich-game-material-realization/v0.1",
        "texture_size": int(REQUEST.get("material_texture_size", 256)),
        "uv_layout": "per-mesh smart-projected game UVs with 0.018 island margin",
        "materials": OUTPUT_SURFACE_RECORDS,
        "portable_maps": ["base_color", "normal", "orm"],
        "truth": (
            "UC-authored packed PBR textures are connected to exported glTF materials. "
            "Procedural wear/stains are UV-space authoring fields, not mesh-derived physical evidence."
        ),
    }
    manifest["truth"]["actual_portable_pbr_textures"] = True
    manifest["truth"]["final_visual_acceptance"] = False
    path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    request_path, _motion_path, OUTPUT = BASE.args_after_dash()
    REQUEST = json.loads(request_path.read_text(encoding="utf-8"))
    OUTPUT_SURFACE_RECORDS = {}
    BASE_BUILD_MODEL = BASE.build_model
    BASE.build_model = _rich_build_model
    BASE.main()
    _update_delivery_manifest(OUTPUT)

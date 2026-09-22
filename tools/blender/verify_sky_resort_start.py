"""Independent GLB, animation, LOD, collision and constraint verification."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import struct
import sys

import bpy
import numpy as np

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from verify_chaos_hero import action_set, find_action, positions, reset


def document(path: Path) -> dict:
    raw = path.read_bytes()
    if len(raw) < 20 or struct.unpack_from("<III", raw) != (0x46546C67, 2, len(raw)):
        raise ValueError(f"Malformed GLB header: {path}")
    size, kind = struct.unpack_from("<II", raw, 12)
    if kind != 0x4E4F534A:
        raise ValueError(f"Missing JSON chunk: {path}")
    return json.loads(raw[20:20 + size])


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_asset(path: Path, manifest: dict) -> dict:
    doc = document(path)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(path))
    arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
    skins = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and
             any(mod.type == "ARMATURE" for mod in obj.modifiers)]
    if len(arms) != 1 or len(skins) != 1:
        raise ValueError(f"Expected one armature and one skinned mesh in {path.name}; got {len(arms)} and {len(skins)}")
    arm, mesh = arms[0], skins[0]
    reset(arm)
    rest = positions(mesh)
    mesh.data.calc_loop_triangles()
    triangles = np.array([triangle.vertices[:] for triangle in mesh.data.loop_triangles], dtype=np.int64)
    area2 = np.linalg.norm(np.cross(rest[triangles[:, 1]] - rest[triangles[:, 0]],
                                    rest[triangles[:, 2]] - rest[triangles[:, 0]]), axis=1)
    degenerate = int((area2 < 1e-12).sum())
    uv = np.array([loop.uv[:] for loop in mesh.data.uv_layers.active.data])
    expected_bones = {row["name"] for row in manifest["bones"]}
    bad_weights = sum(not vertex.groups or abs(sum(group.weight for group in vertex.groups) - 1) > 1e-4
                      for vertex in mesh.data.vertices)
    required = {
        "Root", "LowerIsland", "VolcanoCore", "UpperIsland", "Cascades", "Sanctuary",
        "ArrivalGate", "Socket_Bus_Arrival", "CloudBank",
        "WaterSpiral.A", "WaterSpiral.B", "WaterSpiral.C",
        "WaterShield.A", "WaterShield.B", "WaterShield.C",
    }
    node_names = {node.get("name", "") for node in doc.get("nodes", [])}
    materials = {material.get("name", ""): material for material in doc.get("materials", [])}
    world_water = manifest.get("water_profile") == "world-study"
    world_water_names = {
        "Sanctuary_Rising_Water_Translucent",
        "Sanctuary_Water_Light_Translucent",
        "Sanctuary_Upcurrent_Glint",
    }
    flow_bones = {
        f"WaterFlow.{suffix}.{packet_index}"
        for suffix in ("A", "B", "C")
        for packet_index in range(6)
    }
    world_materials = [materials.get(name, {}) for name in world_water_names]
    forbidden = ("stair", "bridge", "causeway")
    gates = {
        "one_skin": len(doc.get("skins", [])) == 1,
        "skeleton_matches_manifest": set(arm.data.bones.keys()) == expected_bones,
        "required_asset_bones": required.issubset(set(arm.data.bones.keys())),
        "arrival_socket_exported": "Socket_Bus_Arrival" in node_names,
        "forbidden_crossings_absent": not any(token in name.lower() for name in node_names for token in forbidden),
        "no_degenerate_triangles": degenerate == 0,
        "normalized_weights": bad_weights == 0,
        "finite_rest_vertices": bool(np.isfinite(rest).all()),
        "finite_uvs": bool(len(uv) and np.isfinite(uv).all()),
        "all_textures_embedded": bool(doc.get("images")) and all("bufferView" in image for image in doc.get("images", [])),
        "all_primitives_skinned": all(
            "JOINTS_0" in primitive["attributes"] and "WEIGHTS_0" in primitive["attributes"]
            for gltf_mesh in doc.get("meshes", []) for primitive in gltf_mesh["primitives"]
        ),
        "material_family_present": len(doc.get("materials", [])) >= 16,
        "detailed_geometry_present": len(mesh.data.loop_triangles) >= 85000,
        "world_water_materials_present": (
            world_water_names.issubset(materials) if world_water else True
        ),
        "world_water_alpha_blend": (
            all(material.get("alphaMode") == "BLEND" for material in world_materials)
            if world_water else True
        ),
        "world_water_transmission": (
            all(material.get("extensions", {}).get("KHR_materials_transmission", {})
                .get("transmissionFactor", 0) >= .20 for material in world_materials)
            if world_water else True
        ),
        "world_water_ior": (
            all("KHR_materials_ior" in material.get("extensions", {})
                for material in world_materials) if world_water else True
        ),
        "world_water_clearcoat": (
            all("KHR_materials_clearcoat" in material.get("extensions", {})
                for material in world_materials) if world_water else True
        ),
        "world_flow_bones_present": (
            flow_bones.issubset(node_names) and flow_bones.issubset(set(arm.data.bones.keys()))
            if world_water else True
        ),
    }
    clips = []
    for expected in manifest["animations"]:
        action = find_action(expected["name"])
        action_set(arm, action)
        first, last = map(float, action.frame_range)
        samples = []
        for fraction in (0, .125, .25, .375, .5, .625, .75, .875, 1):
            frame = first + (last - first) * fraction
            bpy.context.scene.frame_set(int(frame), subframe=frame - int(frame))
            samples.append(positions(mesh))
        motion = max(float(np.linalg.norm(sample - samples[0], axis=1).max()) for sample in samples[1:])
        endpoint = float(np.linalg.norm(samples[-1] - samples[0], axis=1).max())
        clips.append({
            "name": expected["name"],
            "duration_s": (last - first) / 30,
            "sampled_motion_m": motion,
            "endpoint_delta_m": endpoint,
            "moves_skin": motion > .01,
            "loop_closed": endpoint < .002 if expected["loop"] else None,
            "finite_samples": all(bool(np.isfinite(sample).all()) for sample in samples),
        })
        print("SKY_RESORT_CLIP", path.name, expected["name"], round(motion, 5),
              round(endpoint, 6), flush=True)
    gates.update({
        "all_clips_present": len(clips) == len(manifest["animations"]),
        "all_clips_move_skin": all(clip["moves_skin"] for clip in clips),
        "loop_endpoints_close": all(clip["loop_closed"] is not False for clip in clips),
        "clip_durations_match": all(abs(clip["duration_s"] - expected["seconds"]) < .04
                                    for clip, expected in zip(clips, manifest["animations"])),
        "finite_animation_samples": all(clip["finite_samples"] for clip in clips),
    })
    return {
        "path": path.name,
        "sha256": digest(path),
        "pass": all(gates.values()),
        "gates": gates,
        "counts": {"bones": len(arm.data.bones), "vertices": len(rest),
                   "triangles": len(mesh.data.loop_triangles), "materials": len(doc.get("materials", [])),
                   "embedded_images": len(doc.get("images", [])), "animations": len(doc.get("animations", []))},
        "bounds_m": {"min": rest.min(axis=0).tolist(), "max": rest.max(axis=0).tolist()},
        "degenerate_triangles": degenerate,
        "bad_weight_vertices": bad_weights,
        "clips": clips,
    }


def inspect_collision(path: Path) -> dict:
    doc = document(path)
    names = [node.get("name", "") for node in doc.get("nodes", [])]
    mesh_nodes = [node for node in doc.get("nodes", []) if "mesh" in node]
    expected = {"UCX_DISPLAY_PLINTH", "UCX_LOWER_ISLAND", "UCX_VOLCANO", "UCX_UPPER_ISLAND",
                "UCX_SANCTUARY", "UCX_ARRIVAL_PAD"}
    gates = {
        "decoded": bool(doc.get("meshes")),
        "expected_object_count": len(mesh_nodes) == len(expected),
        "all_mesh_nodes_ucx_named": all(node.get("name", "").startswith("UCX_") for node in mesh_nodes),
        "expected_collisions_present": expected.issubset(set(names)),
    }
    return {"path": path.name, "sha256": digest(path), "pass": all(gates.values()),
            "gates": gates, "mesh_nodes": names}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--directory", type=Path, required=True)
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    args = parser.parse_args(argv)
    root = args.directory.resolve()
    manifest = json.loads((root / "asset-manifest.json").read_text(encoding="utf-8"))
    parts = json.loads((root / "parts-index.json").read_text(encoding="utf-8"))
    recipe = json.loads((root / "assembly-recipe.json").read_text(encoding="utf-8"))
    assets = [inspect_asset(root / row["path"], manifest) for row in manifest["exports"].values()]
    triangles = [asset["counts"]["triangles"] for asset in assets]
    collision = inspect_collision(root / manifest["collision"]["path"])
    categories = {row["category"] for row in parts["parts"]}
    names = [row["name"].lower() for row in parts["parts"]]
    forbidden = ("stair", "bridge", "causeway")
    required_categories = {
        "lower_island", "volcano", "water_vortex", "water_foam", "upper_island",
        "sanctuary_architecture", "water_shield", "waterfall", "arrival_gate", "arrival_socket",
        "vegetation", "ruins",
    }
    part_gates = {
        "detailed_part_count": len(parts["parts"]) >= 850,
        "all_parts_categorized": all(row["category"] for row in parts["parts"]),
        "all_parts_controlled": all(row["controlling_bone"] for row in parts["parts"]),
        "semantic_families": required_categories.issubset(categories),
        "forbidden_crossing_parts_absent": not any(token in name for name in names for token in forbidden),
        "strict_lod_descent": triangles[0] > triangles[1] > triangles[2] > 0,
        "lod2_reduction": triangles[2] / triangles[0] < .30,
        "replacement_contract_present": recipe["replacement_contract"]["socket"] == "Socket_Bus_Arrival",
        "separate_vehicle_declared": manifest["integration_socket"]["vehicle_included"] is False,
        "world_flow_tracer_parts": (
            "water_flow_tracer" in categories
            if manifest.get("water_profile") == "world-study" else True
        ),
    }
    result = {
        "schema": "axm.uc.inverted-water-sanctuary-verification/v1",
        "pass": all(asset["pass"] for asset in assets) and collision["pass"] and all(part_gates.values()),
        "assets": assets,
        "collision": collision,
        "creator_parts": {"count": len(parts["parts"]), "categories": sorted(categories),
                          "gates": part_gates},
        "limits": [
            "Fresh Blender import, decoded GLB structure, numerical skin playback, LOD, collision and explicit crossing constraints only.",
            "Visual quality requires inspection of the fresh-import renders.",
            "Target-engine gameplay, performance, navigation and final transit integration are not tested here.",
        ],
    }
    (root / "verification.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print("SKY_RESORT_START_VERIFIED", result["pass"], flush=True)
    if not result["pass"]:
        raise SystemExit("Opening-world diorama verification requires repair; inspect verification.json")


if __name__ == "__main__":
    main()

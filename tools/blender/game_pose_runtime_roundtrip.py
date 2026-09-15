"""Independent Blender/UC pose comparison on rebuilt Parcel Imp exports.

Run in a fresh process after game_showcase_parcel_imp.py build. No browser,
renderer service or engine installation is used by the production evaluator.
Blender is solely the independent reference for this integration check.
"""
import argparse
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.kdtree import KDTree

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.game_pose_runtime import load_game_pose_glb


def blender_point(p):
    return Vector((p[0], -p[2], p[1]))


def tree(points):
    result = KDTree(len(points))
    for i, p in enumerate(points):
        result.insert(p, i)
    result.balance()
    return result


def compare(asset_path):
    asset = load_game_pose_glb(asset_path)
    description = asset.describe()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = 30
    bpy.ops.import_scene.gltf(filepath=str(asset_path), merge_vertices=False)
    armatures = [o for o in bpy.context.scene.objects if o.type == "ARMATURE"]
    assert len(armatures) == 1, "requires the original single Parcel Imp rig"
    arm = armatures[0]
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    joint_ids = sorted({j for skin in description["skins"] for j in skin["joints"]})
    assert len(joint_ids) == 16, "Parcel Imp joint identity changed"
    rows = []
    for clip in description["clips"]:
        actions = [a for a in bpy.data.actions if a.name == clip["name"] or a.name.startswith(clip["name"] + "_")]
        assert len(actions) == 1, (clip["name"], [a.name for a in bpy.data.actions])
        arm.animation_data_create(); arm.animation_data.action = actions[0]
        # Import uses Blender frames from seconds and can put its first key at 0.
        # Read this mapping rather than assuming an authored frame-one offset.
        start, end = actions[0].frame_range
        assert abs((end - start) / 30 - clip["duration_s"]) < 1e-5
        for fraction in (0., .137, .3, .5, .731, 1.):
            # Compare authored 30 Hz keys. Blender quaternion component F-curves
            # need not implement glTF SLERP between keys; the latter is covered
            # independently by the analytical shortest-arc tests.
            time = min(round(clip["duration_s"] * 30 * fraction) / 30, clip["duration_s"])
            frame = start + time * 30
            bpy.context.scene.frame_set(math.floor(frame), subframe=frame - math.floor(frame))
            pose = asset.sample(clip["name"], time, vertices=True)
            joint_error = 0.
            for j in joint_ids:
                name = description["nodes"][j]["name"]
                actual = blender_point(asset.point(pose, j))
                expected = arm.matrix_world @ arm.pose.bones[name].head
                joint_error = max(joint_error, (actual - expected).length)
            actual_points = [blender_point(p) for mesh in pose["meshes"] for p in mesh["positions"]]
            expected_points = []
            graph = bpy.context.evaluated_depsgraph_get()
            for mesh in meshes:
                evaluated = mesh.evaluated_get(graph)
                expected_points.extend(evaluated.matrix_world @ v.co for v in evaluated.data.vertices)
            assert actual_points and expected_points
            # Importers may reorder/split vertices. Bidirectional nearest-point
            # error checks the complete deformed surface point sets, not indices.
            actual_tree, expected_tree = tree(actual_points), tree(expected_points)
            vertex_error = max(max(expected_tree.find(p)[2] for p in actual_points),
                               max(actual_tree.find(p)[2] for p in expected_points))
            assert joint_error < 2e-5, (asset_path.name, clip["name"], time, "joint", joint_error)
            assert vertex_error < 2e-5, (asset_path.name, clip["name"], time, "skin", vertex_error)
            rows.append({"clip": clip["name"], "time_s": time, "joint_error_m": joint_error,
                         "bidirectional_vertex_error_m": vertex_error,
                         "uc_vertices": len(actual_points), "blender_vertices": len(expected_points)})
    return {"asset": asset_path.name, "source_sha256": asset.source_sha256,
            "joint_count": len(joint_ids), "samples": rows}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    results = [compare(path) for path in sorted(args.directory.glob("AXM_Parcel_Imp_LOD*.glb"))]
    assert len(results) == 2
    receipt = {"schema": "axm.game-pose-blender-comparison/v0.1", "passed": True,
               "reference": "fresh Blender " + bpy.app.version_string + " GLB import and evaluated skin",
               "evaluator": "Python standard library only", "exports": results,
               "maximum_joint_error_m": max(row["joint_error_m"] for result in results for row in result["samples"]),
               "maximum_vertex_error_m": max(row["bidirectional_vertex_error_m"] for result in results for row in result["samples"]),
               "limits": ["Sampled positions only; no shading, normals, continuous playback or performance claim.",
                          "Vertex comparison is bidirectional nearest-point error, not a vertex-order or topology proof.",
                          "Crossfades have analytical unit coverage, not native Blender transition playback coverage."]}
    (args.directory / "pose-runtime-comparison.json").write_text(json.dumps(receipt, indent=2) + "\n")
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()

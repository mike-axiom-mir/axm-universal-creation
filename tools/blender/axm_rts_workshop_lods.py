"""Derive deeper runtime LODs from the verified workshop LOD1 GLB.

This is deliberately a post-stage: the authored hero and existing LOD1 remain
unchanged.  The ladder is sequential so each cheaper tier descends from the
already simplified previous tier instead of re-authoring the workshop.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import bpy

from axm_blender_forge import export_glb, select_only


SOURCE_NAME = "improvised-workshop-lod1.glb"
LOD_STAGES = (
    {
        "role": "near-tactical",
        "filename": "improvised-workshop-tactical.glb",
        "ratio": 0.45,
        "target_triangles": [20_000, 40_000],
    },
    {
        "role": "ordinary-rts",
        "filename": "improvised-workshop-rts.glb",
        "ratio": 0.30,
        "target_triangles": [4_000, 12_000],
    },
    {
        "role": "far-rts",
        "filename": "improvised-workshop-far.glb",
        "ratio": 0.10,
        "target_triangles": [500, 2_000],
    },
)


def triangle_count(objects):
    return sum(sum(max(0, len(poly.vertices) - 2) for poly in obj.data.polygons) for obj in objects)


def clear_scene():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for block in list(bpy.data.objects):
        if block.users == 0:
            bpy.data.objects.remove(block)


def apply_decimation(objects, ratio):
    for obj in objects:
        if obj.type != "MESH" or len(obj.data.polygons) <= 4:
            continue
        modifier = obj.modifiers.new("AXM runtime LOD reduction", "DECIMATE")
        modifier.ratio = ratio
        select_only([obj])
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_apply(modifier=modifier.name)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    root = args.root.resolve()
    source = root / SOURCE_NAME
    if not source.is_file():
        raise SystemExit(f"Missing verified source LOD: {source}")

    clear_scene()
    bpy.ops.import_scene.gltf(filepath=str(source))
    objects = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not objects:
        raise SystemExit("LOD1 import produced no mesh objects")

    stages = []
    previous_triangles = triangle_count(objects)
    for stage in LOD_STAGES:
        before = previous_triangles
        apply_decimation(objects, stage["ratio"])
        after = triangle_count(objects)
        if not 0 < after < before:
            raise RuntimeError(
                f"{stage['role']} did not reduce geometry: before={before}, after={after}"
            )
        output = root / stage["filename"]
        export_glb(output, objects)
        stages.append(
            {
                **stage,
                "input_triangles_in_blender": before,
                "output_triangles_in_blender": after,
                "observed_ratio_in_blender": after / before,
            }
        )
        previous_triangles = after

    report = {
        "schema": "axm.rts-workshop-lod-ladder-build/v0.1",
        "source": SOURCE_NAME,
        "source_triangles_in_blender": triangle_count(objects) if not stages else stages[0]["input_triangles_in_blender"],
        "stages": stages,
        "scope": (
            "Sequential Blender decimation from the existing verified LOD1. "
            "Triangle bands are targets for later independent GLB verification, not visual-equivalence claims."
        ),
    }
    (root / "lod-ladder-build.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2), flush=True)


if __name__ == "__main__":
    main()

"""Build and freshly verify contact/socket-safe game-view realizations.

Extends the original animated Clockwork Smacker proof with explicit attachment
frames and rolling contacts, three real geometry tiers and measured game-view
renders.  The deterministic runtime planner consumes the resulting evidence.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

import bpy
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "src"))

import axm_blender_forge as geo
from axm_hero_motion import clean_triangles, rig
from axm_salvage_surfaces import solid
import game_motion_timing_roundtrip as primary_proof
import game_secondary_motion_roundtrip as secondary_proof
from axm_uc.game_runtime_realization import SOURCE_SCHEMA, compose_game_runtime_realization


FPS = 30
ACTION_NAME = secondary_proof.ACTION_NAME
LOD_SPECS = (("LOD0", 1.0), ("LOD1", .48), ("LOD2", .18))
ANCHOR_BONES = {
    "wheel-contact-left": "Contact_Wheel.L",
    "wheel-contact-right": "Contact_Wheel.R",
    "tool-socket": "Socket_Tool",
    "companion-socket": "Socket_Companion",
}
FEATURE_MATERIALS = {
    "clock-signal": ("Feature_ClockSignal",),
    "lucky-duck": ("Feature_LuckyDuck",),
    "patched-cape": ("Feature_CapeRed", "Feature_CapeIvory"),
    "tool-bag": ("Feature_SecondaryTeal",),
}
VIEWS = (
    {"name": "near-hero", "distance_m": 2.8, "vertical_fov_deg": 42,
     "viewport_height_px": 512, "error_budget_px": 2.0,
     "max_rgba_rmse": .01, "min_silhouette_iou": .995},
    {"name": "gameplay", "distance_m": 9.0, "vertical_fov_deg": 42,
     "viewport_height_px": 512, "error_budget_px": 2.0,
     "max_rgba_rmse": .01, "min_silhouette_iou": .995},
    {"name": "far-gameplay", "distance_m": 22.0, "vertical_fov_deg": 42,
     "viewport_height_px": 512, "error_budget_px": 2.0,
     "max_rgba_rmse": .01, "min_silhouette_iou": .995},
)


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def add_realization_bones(hero):
    # Two points across each wheel width define a rolling contact line. The
    # bone frame supplies the authored surface normal and tangent orientation.
    hero.bone("Contact_Wheel.L", (-.29, .02, .035), (-.19, .02, .035), "Root")
    hero.bone("Contact_Wheel.R", (.29, .02, .035), (.39, .02, .035), "Root")
    hero.bone("Socket_Tool", (.39, -.20, .72), (.39, -.35, .72), "Body")
    hero.bone("Socket_Companion", (-.34, .04, 1.22), (-.34, .04, 1.42), "Body")


def feature_surfaces(hero):
    hero.mat["cyan"] = solid("Feature_ClockSignal", "#2be0ff", .10, .24, 3.2)
    hero.mat["duck"] = solid("Feature_LuckyDuck", "#ffc42e", 0, .34, 0)


def secondary_feature_surfaces(hero):
    hero.mat["red"] = solid("Feature_CapeRed", "#b43b35", .28, .62, 0)
    hero.mat["ivory"] = solid("Feature_CapeIvory", "#d9cfb6", .42, .48, 0)
    hero.mat["teal"] = solid("Feature_SecondaryTeal", "#297b83", .48, .42, 0)


def bvh(mesh):
    return BVHTree.FromPolygons([tuple(vertex.co) for vertex in mesh.vertices],
                                [tuple(poly.vertices) for poly in mesh.polygons], all_triangles=False)


def maximum_surface_deviation(source_mesh, target_mesh, sample_limit=12000):
    if source_mesh == target_mesh:
        return 0.0
    tree = bvh(target_mesh)
    stride = max(1, math.ceil(len(source_mesh.vertices) / sample_limit))
    maximum = 0.0
    for index in range(0, len(source_mesh.vertices), stride):
        vertex = source_mesh.vertices[index]
        nearest = tree.find_nearest(vertex.co)
        if nearest[0] is None:
            raise ValueError("LOD surface query failed")
        maximum = max(maximum, (vertex.co - nearest[0]).length)
    return maximum


def export_lods(output, arm, source_mesh):
    exports = {}
    for lod, ratio in LOD_SPECS:
        target = source_mesh
        if ratio < 1:
            target = source_mesh.copy()
            target.data = source_mesh.data.copy()
            bpy.context.collection.objects.link(target)
            target.name = f"AXM_Clockwork_Smacker_{lod}"
            target.modifiers.clear()
            geo.select_only([target])
            bpy.context.view_layer.objects.active = target
            modifier = target.modifiers.new("Measured game LOD", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
            repaired = target.data.validate(verbose=False, clean_customdata=False)
            print("LOD_MESH_VALIDATION", lod, "repaired", repaired, flush=True)
            clean_triangles(target)
            skin = target.modifiers.new("Skin", "ARMATURE")
            skin.object = arm
        deviation = maximum_surface_deviation(source_mesh.data, target.data)
        geo.select_only([arm, target])
        bpy.context.view_layer.objects.active = arm
        path = output / f"AXM_Clockwork_Smacker_Realization_{lod}.glb"
        bpy.ops.export_scene.gltf(
            filepath=str(path), export_format="GLB", use_selection=True,
            export_skins=True, export_animations=True, export_animation_mode="ACTIONS",
            export_force_sampling=True, export_yup=True, export_extras=True,
            export_tangents=True, export_cameras=False, export_lights=False,
            export_materials="EXPORT")
        target.data.calc_loop_triangles()
        exports[lod] = {"file": path.name, "bytes": path.stat().st_size,
                        "triangles": len(target.data.loop_triangles),
                        "vertices": len(target.data.vertices), "max_deviation_m": deviation,
                        "sha256": sha256(path)}
        if target is not source_mesh:
            bpy.data.objects.remove(target, do_unlink=True)
    arm.animation_data.action = bpy.data.actions[ACTION_NAME]
    bpy.context.scene.frame_set(1)
    blend = output / "AXM_Clockwork_Smacker_Realization.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend), compress=True)
    return exports, blend


def build(output):
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.context.scene.render.fps = FPS
    hero = primary_proof.new_hero(output)
    feature_surfaces(hero)
    primary_proof.build_geometry(hero)
    secondary_proof.add_secondary_bones(hero)
    add_realization_bones(hero)
    secondary_feature_surfaces(hero)
    secondary_proof.add_secondary_geometry(hero)
    arm, mesh = rig(hero)
    arm.name = "AXM_Clockwork_Smacker_Realization_Rig"
    mesh.name = "AXM_Clockwork_Smacker_Realization"
    primary, secondary, animation = secondary_proof.author_action(arm)
    exports, blend = export_lods(output, arm, mesh)
    report = {
        "schema": "axm.game-runtime-realization-build/v0.1",
        "asset_id": "axm-clockwork-smacker-realization",
        "editable_source": blend.name, "editable_source_sha256": sha256(blend),
        "exports": exports, "animation": animation,
        "anchors": [{"name": name, "bone": bone,
                     "kind": "contact" if name.startswith("wheel-contact") else "socket"}
                    for name, bone in ANCHOR_BONES.items()],
        "feature_materials": FEATURE_MATERIALS,
        "views": VIEWS,
        "truth": "Authored three-tier proof awaiting fresh-import anchor, surface and render checks.",
        "source_sha256": sha256(__file__),
    }
    (output / "build-manifest.json").write_text(json.dumps(report, indent=2) + "\n")


def action_by_prefix(prefix):
    found = [action for action in bpy.data.actions if action.name == prefix or action.name.startswith(prefix)]
    if len(found) != 1:
        raise ValueError(f"expected one action {prefix}, found {[item.name for item in found]}")
    return found[0]


def bone_frame(arm, name, kind):
    bone = arm.pose.bones[name]
    matrix = arm.matrix_world @ bone.matrix
    position = arm.matrix_world @ bone.head
    forward = (matrix.to_3x3() @ Vector((0, 1, 0))).normalized()
    # Contacts use +Z as the authored outward/up normal; sockets retain a full
    # frame with the same orthogonal +Z direction.
    up = (matrix.to_3x3() @ Vector((0, 0, 1))).normalized()
    return {"name": next(label for label, bone_name in ANCHOR_BONES.items() if bone_name == name),
            "kind": kind, "position": list(position), "forward": list(forward), "up": list(up)}


def closest_surface_distance(mesh, point_world):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    evaluated = mesh.evaluated_get(depsgraph)
    local = evaluated.matrix_world.inverted() @ point_world
    hit, location, normal, _ = evaluated.closest_point_on_mesh(local, distance=.10, depsgraph=depsgraph)
    if not hit:
        return None
    world = evaluated.matrix_world @ location
    return (world - point_world).length


def feature_counts(mesh):
    names = [slot.material.name if slot.material else "" for slot in mesh.material_slots]
    counts = {name: 0 for name in names}
    mesh.data.calc_loop_triangles()
    for triangle in mesh.data.loop_triangles:
        if triangle.material_index < len(names):
            counts[names[triangle.material_index]] += 1
    result = {"hero-shape": len(mesh.data.loop_triangles)}
    for feature, materials in FEATURE_MATERIALS.items():
        result[feature] = sum(counts.get(name, 0) for name in materials)
    return result


def imported_surface_deviation(canonical_points, mesh):
    tree = bvh(mesh.data)
    maximum = 0.0
    for point in canonical_points:
        nearest = tree.find_nearest(point)
        if nearest[0] is None:
            raise ValueError("imported LOD surface query failed")
        maximum = max(maximum, (point - nearest[0]).length)
    return maximum


def studio(distance):
    primary_proof.studio(512)
    scene = bpy.context.scene
    scene.render.film_transparent = True
    camera = scene.camera
    camera.data.type = "PERSP"
    camera.data.lens_unit = "FOV"
    camera.data.angle = math.radians(42)
    direction = Vector((2.6, -5.4, 2.05)).normalized()
    target = Vector((.24, 0, .90))
    camera.location = target + direction * distance
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def render_view(output, lod, distance):
    studio(distance)
    scene = bpy.context.scene
    path = output / "game-view-renders" / f"{lod}-{distance:.1f}m.png"
    scene.render.filepath = str(path)
    bpy.ops.render.render(write_still=True)
    return path


def pixel_comparison(reference_path, candidate_path):
    a = Image.open(reference_path).convert("RGBA")
    b = Image.open(candidate_path).convert("RGBA")
    pa, pb = list(a.getdata()), list(b.getdata())
    mse = sum(sum((x - y) ** 2 for x, y in zip(ca, cb)) for ca, cb in zip(pa, pb)) / (len(pa) * 4 * 255 * 255)
    alpha_a = [value[3] > 8 for value in pa]
    alpha_b = [value[3] > 8 for value in pb]
    intersection = sum(x and y for x, y in zip(alpha_a, alpha_b))
    union = sum(x or y for x, y in zip(alpha_a, alpha_b))
    return {"rgba_rmse": math.sqrt(mse), "silhouette_iou": intersection / union if union else 1.0}


def verify(output):
    build_report = json.loads((output / "build-manifest.json").read_text())
    render_dir = output / "game-view-renders"
    render_dir.mkdir(exist_ok=False)
    lod_rows = []
    renders = {}
    canonical_points = None
    for lod, _ in LOD_SPECS:
        row = build_report["exports"][lod]
        bpy.ops.wm.read_factory_settings(use_empty=True)
        bpy.context.scene.render.fps = FPS
        bpy.ops.import_scene.gltf(filepath=str(output / row["file"]))
        arms = [obj for obj in bpy.context.scene.objects if obj.type == "ARMATURE"]
        arm = arms[0] if len(arms) == 1 else None
        skins = [obj for obj in bpy.context.scene.objects if obj.type == "MESH" and obj.parent == arm]
        if arm is None or len(skins) != 1:
            raise ValueError(f"{lod} did not re-import as one armature and skin")
        mesh = skins[0]
        mesh.data.calc_loop_triangles()
        if canonical_points is None:
            canonical_points = [vertex.co.copy() for vertex in mesh.data.vertices]
        measured_deviation = imported_surface_deviation(canonical_points, mesh)
        arm.animation_data_create()
        arm.animation_data.action = action_by_prefix(ACTION_NAME)
        if getattr(arm.animation_data.action, "slots", None):
            arm.animation_data.action_slot = arm.animation_data.action.slots[0]
        bpy.context.scene.frame_set(1)
        anchors = []
        surface = {}
        for label, bone_name in ANCHOR_BONES.items():
            kind = "contact" if label.startswith("wheel-contact") else "socket"
            anchors.append(bone_frame(arm, bone_name, kind))
            if kind == "contact":
                surface[label] = closest_surface_distance(mesh, arm.matrix_world @ arm.pose.bones[bone_name].head)
        features = feature_counts(mesh)
        present = [name for name, count in features.items() if count > 0]
        lod_rows.append({"name": lod, "triangles": len(mesh.data.loop_triangles),
                         "max_deviation_m": measured_deviation,
                         "features": present, "anchors": anchors,
                         "feature_triangles": features, "contact_surface_distance_m": surface,
                         "build_reported_triangles": row["triangles"],
                         "build_reported_max_deviation_m": row["max_deviation_m"]})
        for view in VIEWS:
            renders[(lod, view["name"])] = render_view(output, lod, view["distance_m"])

    comparisons = {}
    for view in VIEWS:
        reference = renders[("LOD0", view["name"])]
        comparisons[view["name"]] = {
            lod: pixel_comparison(reference, renders[(lod, view["name"])]) for lod, _ in LOD_SPECS
        }
    for row in lod_rows:
        row["render_observations"] = [
            {"view": view["name"], **comparisons[view["name"]][row["name"]]}
            for view in VIEWS
        ]

    source = {
        "schema": SOURCE_SCHEMA, "asset_id": build_report["asset_id"], "canonical_lod": "LOD0",
        "source_sha256": build_report["editable_source_sha256"],
        "features": [
            {"name": "hero-shape", "hierarchy": "primary", "world_size_m": 1.85, "min_pixels": 5},
            {"name": "clock-signal", "hierarchy": "secondary", "world_size_m": .38, "min_pixels": 10},
            {"name": "patched-cape", "hierarchy": "secondary", "world_size_m": .55, "min_pixels": 8},
            {"name": "lucky-duck", "hierarchy": "detail", "world_size_m": .15, "min_pixels": 9},
            {"name": "tool-bag", "hierarchy": "detail", "world_size_m": .31, "min_pixels": 8},
        ],
        "lods": [{key: row[key] for key in ("name", "triangles", "max_deviation_m", "features",
                                                   "anchors", "render_observations")}
                 for row in lod_rows],
    }
    request = {"views": list(VIEWS), "anchor_position_tolerance_m": 1e-5,
               "anchor_angle_tolerance_deg": .01}
    plan = compose_game_runtime_realization(source, request)
    max_surface = max(value for row in lod_rows for value in row["contact_surface_distance_m"].values()
                      if value is not None)
    result = {
        "schema": "axm.game-runtime-realization-roundtrip/v0.1", "fresh_import": True,
        "source": source, "request": request, "plan": plan, "lod_evidence": lod_rows,
        "render_comparisons": comparisons, "maximum_contact_surface_distance_m": max_surface,
        "limits": {
            "contact": "Two authored wheel markers checked against imported mesh surfaces; not a continuous collision patch.",
            "readability": "Pixel comparison and representative stills only; no target-game camera or user test.",
            "performance": "Triangle/file reductions only; no frame-time measurement.",
            "engine_playback": False,
        },
    }
    result["passed"] = (plan["status"] == "PASS" and max_surface <= .002 and
                        all(all(anchor["passed"] for anchor in rows)
                            for rows in plan["anchor_receipts"].values()))
    (output / "roundtrip-receipt.json").write_text(json.dumps(result, indent=2) + "\n")
    (output / "realization-source.json").write_text(json.dumps(source, indent=2) + "\n")
    (output / "realization-request.json").write_text(json.dumps(request, indent=2) + "\n")
    (output / "realization-plan.json").write_text(json.dumps(plan, indent=2) + "\n")
    (output / "INTEGRATION.md").write_text(
        "# AXM Clockwork Smacker — game realization proof\n\n"
        "Import one GLB and play `Bell_Smack_Secondary_Followthrough`. Use `realization-plan.json` "
        "as evidence for the supplied 42-degree/512px camera policy, not as a universal distance table. "
        "`Socket_Tool` and `Socket_Companion` are attachment frames. `Contact_Wheel.L/R` mark rolling "
        "contacts checked against the imported surface at rest. Re-evaluate for another camera, altered "
        "mesh, collision shape, scale or target engine.\n")
    if not result["passed"]:
        raise ValueError("fresh-import game realization verification failed")


def sheet(output):
    receipt = json.loads((output / "roundtrip-receipt.json").read_text())
    cell, header = 512, 120
    canvas = Image.new("RGB", (cell * 3, header + cell * 3), (19, 23, 34))
    draw = ImageDraw.Draw(canvas)
    font = ImageFont.load_default(size=28)
    small = ImageFont.load_default(size=22)
    draw.text((24, 18), "AXM GAME-VIEW REALIZATION - ACTUAL GLB LODS", fill=(243, 231, 201), font=font)
    selected = {row["view"]: row["selected_lod"] for row in receipt["plan"]["decisions"]}
    for column, view in enumerate(VIEWS):
        title = f"{view['name']}  {view['distance_m']:g}m\nselected {selected[view['name']]}"
        draw.multiline_text((column * cell + 18, 62), title, fill=(57, 226, 242), font=small, spacing=2)
    for row_index, (lod, _) in enumerate(LOD_SPECS):
        for column, view in enumerate(VIEWS):
            image = Image.open(output / "game-view-renders" / f"{lod}-{view['distance_m']:.1f}m.png").convert("RGBA")
            tile = Image.new("RGBA", image.size, (19, 23, 34, 255))
            tile.alpha_composite(image)
            canvas.paste(tile.convert("RGB"), (column * cell, header + row_index * cell))
            draw.text((column * cell + 16, header + row_index * cell + 14), lod,
                      fill=(255, 196, 55), font=small)
    canvas.save(output / "game-runtime-realization.png")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("build", "verify", "sheet"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else None)
    output = args.output.resolve()
    if args.mode == "build":
        build(output)
    elif args.mode == "verify":
        verify(output)
    else:
        sheet(output)


if __name__ == "__main__":
    main()

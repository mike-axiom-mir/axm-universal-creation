"""Build and independently re-import one expressive-form comparison GLB.

This is a geometry/control specimen, not a finished animated game asset.  It
keeps the neutral source next to a comic-salvage derivation and checks actual
fresh-import vertex bounds plus protected wheel/contact and tool socket anchors.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.game_form_styles import apply_game_form
from axm_uc.rts_mesh import SalvageMesh


def courier_mesh():
    mesh = SalvageMesh()
    with mesh.part("body", (0, 0, 0)):
        mesh.roundbox("toolbox-body", (0, 1.28, 0), (1.75, 1.42, 1.18), "paint", .18)
        mesh.roundbox("belly-frame", (0, 1.12, .62), (1.20, .66, .12), "iron", .06)
    with mesh.part("head", (0, 2.05, .18)):
        mesh.ellipsoid("face-shell", (0, 2.08, .18), (1.25, .94, .98), "ivory")
        mesh.ellipsoid("optic", (-.24, 2.14, .64), (.40, .40, .12), "cyan")
        mesh.ellipsoid("wink", (.27, 2.12, .65), (.30, .15, .10), "rubber")
    mesh.wheel("wheel_left", (-.91, .56, 0), .56, .34)
    mesh.wheel("wheel_right", (.91, .56, 0), .56, .34)
    with mesh.part("wrench_arm", (-.80, 1.63, .08)):
        mesh.beam("upper-arm", (-.80, 1.63, .08), (-1.22, 2.03, .05), .17, .15, "iron")
        mesh.beam("wrench-handle", (-1.22, 2.03, .05), (-1.54, 2.55, .04), .12, .10, "signal")
        mesh.ring("open-wrench-jaw", (-1.55, 2.66, .04), .25, .07, "signal", axis="z", ratio=.72)
    with mesh.part("armor", (.64, 1.48, .53)):
        mesh.roundbox("offset-shoulder", (.70, 1.61, .52), (.72, .58, .15), "signal", .08)
        mesh.panel("story-panel", (.46, 1.22, .66), .58, .44, "red")
    with mesh.part("antenna", (.40, 2.46, .12)):
        mesh.pipe("antenna-stalk", [(.40, 2.44, .12), (.49, 2.93, .10)], .035, "iron", 7)
        mesh.ellipsoid("antenna-beacon", (.50, 3.01, .10), (.20, .20, .20), "red", 9, 5)
    with mesh.part("badge", (0, 1.12, .70)):
        mesh.smile((0, 1.12, .70), .24)
    return mesh.surface_spec("mischief-courier-form-specimen")


def part_specs():
    return {
        "body": {"role": "body", "hierarchy": "large",
                 "anchors": {"chassis-floor": [0, .50, 0]}, "anchor_falloff": .20},
        "head": {"role": "functional", "hierarchy": "large",
                 "anchors": {"neck-socket": [0, 1.72, .18]}, "anchor_falloff": .18},
        "wheel_left": {"role": "functional", "hierarchy": "medium",
                       "anchors": {"ground-left": [-.91, 0, 0], "axle-left": [-.91, .56, 0]},
                       "anchor_falloff": .22},
        "wheel_right": {"role": "functional", "hierarchy": "medium",
                        "anchors": {"ground-right": [.91, 0, 0], "axle-right": [.91, .56, 0]},
                        "anchor_falloff": .22},
        "wrench_arm": {"role": "functional", "hierarchy": "large",
                       "anchors": {"shoulder-socket": [-.80, 1.63, .08]}, "anchor_falloff": .17},
        "armor": {"role": "armor", "hierarchy": "medium",
                  "anchors": {"armor-mount": [.64, 1.48, .53]}, "anchor_falloff": .14},
        "antenna": {"role": "detail", "hierarchy": "small",
                    "anchors": {"antenna-socket": [.40, 2.46, .12]}, "anchor_falloff": .17},
        "badge": {"role": "detail", "hierarchy": "small", "anchors": {}, "strength": .55},
    }


def map_point(point):
    # UC surface coordinates are Y-up/+Z-forward; Blender is Z-up/-Y-forward.
    return point[0], -point[2], point[1]


def material_from_primitive(bpy, primitive, cache):
    data = primitive["material"]
    key = (data["color"], data["metallic"], data["roughness"])
    if key in cache:
        return cache[key]
    material = bpy.data.materials.new("Form_" + data["color"][1:7])
    material.use_nodes = True
    color = tuple(int(data["color"][i:i + 2], 16) / 255 for i in (1, 3, 5))
    shader = material.node_tree.nodes.get("Principled BSDF")
    shader.inputs["Base Color"].default_value = (*color, 1)
    shader.inputs["Metallic"].default_value = data["metallic"]
    shader.inputs["Roughness"].default_value = data["roughness"]
    cache[key] = material
    return material


def add_variant(bpy, variant, mesh, x_offset, cache):
    root = bpy.data.objects.new(variant, None)
    bpy.context.scene.collection.objects.link(root)
    root.location.x = x_offset
    root["axm_variant"] = variant
    objects = [root]
    for index, primitive in enumerate(mesh["primitives"]):
        vertices = [map_point(point) for point in primitive["positions"]]
        faces = [primitive["indices"][i:i + 3] for i in range(0, len(primitive["indices"]), 3)]
        data = bpy.data.meshes.new(f"{variant}_{index:02d}")
        data.from_pydata(vertices, [], faces)
        data.materials.append(material_from_primitive(bpy, primitive, cache))
        obj = bpy.data.objects.new(f"{variant}__{index:02d}__{primitive['id']}", data)
        bpy.context.scene.collection.objects.link(obj)
        obj.parent = root
        obj["axm_variant"] = variant
        obj["axm_component"] = primitive["id"].split("__", 1)[0]
        objects.append(obj)
    return root, objects


def add_text(bpy, text, location, size=.20):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body, curve.align_x, curve.align_y = text, "CENTER", "CENTER"
    curve.size, curve.extrude, curve.bevel_depth = size, .008, .003
    obj = bpy.data.objects.new(text, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.pi / 2, 0, 0)
    material = bpy.data.materials.get("Proof captions")
    if material is None:
        material = bpy.data.materials.new("Proof captions")
        material.diffuse_color = (.72, .78, .86, 1)
    obj.data.materials.append(material)


def scene_setup(bpy, output):
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = 1500, 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Form proof world")
    world.color = (.018, .024, .035)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=20, location=(0, 0, -.012))
    floor = bpy.context.object
    floor.name = "PROOF_ONLY_FLOOR"
    floor_material = bpy.data.materials.new("Proof floor")
    floor_material.diffuse_color = (.045, .055, .072, 1)
    floor_material.metallic, floor_material.roughness = .55, .30
    floor.data.materials.append(floor_material)
    bpy.ops.object.camera_add(location=(0, -13.5, 4.4))
    camera = bpy.context.object
    camera.rotation_euler = ((Vector((0, 0, 1.35)) - camera.location).to_track_quat("-Z", "Y").to_euler())
    camera.data.lens = 54
    scene.camera = camera
    for location, power, size, color in [((-4, -4, 7), 1150, 4.2, (1.0, .72, .48)),
                                          ((4, -2, 5), 900, 3.2, (.42, .72, 1.0)),
                                          ((0, 3, 6), 850, 4.0, (.70, .82, 1.0))]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy, light.data.shape, light.data.size, light.data.color = power, "DISK", size, color
        light.rotation_euler = ((Vector((0, 0, 1.2)) - light.location).to_track_quat("-Z", "Y").to_euler())
    add_text(bpy, "CANONICAL SOURCE", (-2.55, -.30, 3.52), .20)
    add_text(bpy, "COMIC-SALVAGE FORM", (2.55, -.30, 3.52), .20)


def object_bounds(obj):
    points = [obj.matrix_world @ vertex.co for vertex in obj.data.vertices]
    return [[min(point[i] for point in points) for i in range(3)],
            [max(point[i] for point in points) for i in range(3)]]


def expected_bounds(mesh, x_offset):
    rows = {}
    for index, primitive in enumerate(mesh["primitives"]):
        points = [(point[0] + x_offset, -point[2], point[1]) for point in primitive["positions"]]
        rows[f"{index:02d}__{primitive['id']}"] = [
            [min(point[i] for point in points) for i in range(3)],
            [max(point[i] for point in points) for i in range(3)],
        ]
    return rows


def build(output):
    import bpy
    output.mkdir(parents=True, exist_ok=False)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    source = courier_mesh()
    derived = apply_game_form(source, part_specs(), "comic-salvage", 471)
    (output / "form-package.json").write_text(json.dumps(derived, indent=2) + "\n")
    cache = {}
    _, source_objects = add_variant(bpy, "SOURCE", source, -2.55, cache)
    _, form_objects = add_variant(bpy, "FORM", derived["realization"], 2.55, cache)
    bpy.ops.object.select_all(action="DESELECT")
    for obj in source_objects + form_objects:
        obj.select_set(True)
    bpy.context.view_layer.objects.active = form_objects[0]
    glb = output / "expressive-form-proof.glb"
    bpy.ops.export_scene.gltf(filepath=str(glb), export_format="GLB", use_selection=True,
                              export_extras=True, export_image_format="AUTO")
    scene_setup(bpy, output / "source.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "expressive-form-proof.blend"))
    bpy.ops.render.render(write_still=True)
    (output / "expected-bounds.json").write_text(json.dumps({
        "SOURCE": expected_bounds(source, -2.55),
        "FORM": expected_bounds(derived["realization"], 2.55),
    }, indent=2) + "\n")


def verify(output):
    from PIL import Image
    import bpy
    package = json.loads((output / "form-package.json").read_text())
    expected = json.loads((output / "expected-bounds.json").read_text())
    bpy.ops.wm.open_mainfile(filepath=str(output / "expressive-form-proof.blend"))
    self_contained = len([obj for obj in bpy.data.objects if obj.get("axm_variant")]) > 2
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(output / "expressive-form-proof.glb"))
    checked = 0
    maximum_error = 0
    for obj in bpy.data.objects:
        if obj.type != "MESH" or not obj.get("axm_variant"):
            continue
        variant = obj["axm_variant"]
        suffix = obj.name.split("__", 1)[1]
        target = expected[variant][suffix]
        actual = object_bounds(obj)
        error = max(abs(actual[a][i] - target[a][i]) for a in range(2) for i in range(3))
        maximum_error = max(maximum_error, error)
        assert error < 2e-5, (obj.name, error)
        checked += 1
    assert checked == sum(len(rows) for rows in expected.values()), checked
    anchors = package["anchor_receipt"]
    assert anchors and all(row["preserved"] and row["drift"] == 0 for row in anchors)
    scene_setup(bpy, output / "reimport.png")
    bpy.ops.render.render(write_still=True)
    source = Image.open(output / "source.png").convert("RGB").tobytes()
    restored = Image.open(output / "reimport.png").convert("RGB").tobytes()
    mae = sum(abs(a - b) for a, b in zip(source, restored)) / len(source)
    assert mae < 2, mae
    glb = output / "expressive-form-proof.glb"
    report = {
        "schema": "axm.game-form-roundtrip/v0.1",
        "blender": bpy.app.version_string,
        "glb_sha256": hashlib.sha256(glb.read_bytes()).hexdigest(),
        "fresh_import_mesh_bounds_checked": checked,
        "maximum_bound_error_m": maximum_error,
        "declared_anchors_preserved": len(anchors),
        "editable_source_contains_both_variants": self_contained,
        "source_reimport_render_mae": mae,
        "limits": (
            "Static two-variant geometry specimen. No rig, animation, collision, LOD, target-engine, "
            "game-distance or perceptual style acceptance. Anchor coordinates pass; full contact surfaces do not."
        ),
    }
    (output / "verification.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("build", "verify"))
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    (build if args.mode == "build" else verify)(args.output.resolve())

"""Build and independently inspect one three-style portable GLB comparison.

The proof uses the same expressive salvage courier geometry for every column.
Only render realization changes. It checks decoded GLB attributes and Blender
fresh import, then renders a visible comparison. It does not claim target-engine
colour management or dynamic shader parity.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.game_form_styles import apply_game_form
from axm_uc.game_render_styles import apply_game_render_style
from axm_uc.procedural_3d import build_glb, verify_glb
from axm_uc.rts_mesh import SalvageMesh


STYLES = ("realistic-pbr", "graphic-toon-baked", "painted-adventure-baked")
OFFSETS = {"realistic-pbr": -3.5, "graphic-toon-baked": 0.0, "painted-adventure-baked": 3.5}
LABELS = {"realistic-pbr": "REALISTIC PBR", "graphic-toon-baked": "GRAPHIC TOON",
          "painted-adventure-baked": "PAINTED ADVENTURE"}


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
    return mesh.surface_spec("mischief-courier-render-specimen")


def form_parts():
    return {
        "body": {"role": "body", "hierarchy": "large", "anchors": {}, "anchor_falloff": .2},
        "head": {"role": "functional", "hierarchy": "large", "anchors": {}, "anchor_falloff": .18},
        "wheel_left": {"role": "functional", "hierarchy": "medium", "anchors": {}, "anchor_falloff": .22},
        "wheel_right": {"role": "functional", "hierarchy": "medium", "anchors": {}, "anchor_falloff": .22},
        "wrench_arm": {"role": "functional", "hierarchy": "large", "anchors": {}, "anchor_falloff": .17},
        "armor": {"role": "armor", "hierarchy": "medium", "anchors": {}, "anchor_falloff": .14},
        "antenna": {"role": "detail", "hierarchy": "small", "anchors": {}, "anchor_falloff": .17},
        "badge": {"role": "detail", "hierarchy": "small", "anchors": {}, "strength": .55},
    }


def glb_chunks(path):
    body = path.read_bytes()
    magic, version, length = struct.unpack_from("<4sII", body)
    assert (magic, version, length) == (b"glTF", 2, len(body))
    json_length, kind = struct.unpack_from("<II", body, 12)
    assert kind == 0x4E4F534A
    document = json.loads(body[20:20 + json_length])
    offset = 20 + json_length
    binary_length, kind = struct.unpack_from("<II", body, offset)
    assert kind == 0x004E4942
    return body, document, body[offset + 8:offset + 8 + binary_length]


def accessor(document, binary, ref):
    item = document["accessors"][ref]
    view = document["bufferViews"][item["bufferView"]]
    widths = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}
    formats = {5123: "H", 5126: "f"}
    width, code = widths[item["type"]], formats[item["componentType"]]
    decoder = struct.Struct("<" + code * width)
    start = view.get("byteOffset", 0) + item.get("byteOffset", 0)
    stride = view.get("byteStride", decoder.size)
    return [decoder.unpack_from(binary, start + index * stride) for index in range(item["count"])]


def add_text(bpy, text, location, size=.18):
    curve = bpy.data.curves.new(text, "FONT")
    curve.body, curve.align_x, curve.align_y = text, "CENTER", "CENTER"
    curve.size, curve.extrude, curve.bevel_depth = size, .008, .003
    obj = bpy.data.objects.new(text, curve)
    bpy.context.scene.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = (math.pi / 2, 0, 0)
    material = bpy.data.materials.get("Proof captions") or bpy.data.materials.new("Proof captions")
    material.diffuse_color = (.72, .80, .90, 1)
    obj.data.materials.append(material)


def scene_setup(bpy, output):
    from mathutils import Vector
    scene = bpy.context.scene
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x, scene.render.resolution_y = 1700, 900
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.filepath = str(output)
    scene.view_settings.look = "AgX - Medium High Contrast"
    world = bpy.data.worlds.new("Render style proof world")
    world.color = (.018, .024, .036)
    scene.world = world
    bpy.ops.mesh.primitive_plane_add(size=24, location=(0, 0, -.012))
    floor = bpy.context.object
    floor.name = "PROOF_ONLY_FLOOR"
    floor_material = bpy.data.materials.new("Proof floor")
    floor_material.diffuse_color = (.038, .050, .070, 1)
    floor_material.metallic, floor_material.roughness = .45, .32
    floor.data.materials.append(floor_material)
    bpy.ops.object.camera_add(location=(0, -18.8, 4.9))
    camera = bpy.context.object
    camera.rotation_euler = ((Vector((0, 0, 1.45)) - camera.location).to_track_quat("-Z", "Y").to_euler())
    camera.data.lens = 56
    scene.camera = camera
    for location, power, size, color in [((-5, -4, 7), 1200, 4.5, (1.0, .70, .46)),
                                          ((5, -2, 5), 900, 3.5, (.40, .70, 1.0)),
                                          ((0, 3, 7), 800, 4.0, (.72, .82, 1.0))]:
        bpy.ops.object.light_add(type="AREA", location=location)
        light = bpy.context.object
        light.data.energy, light.data.shape, light.data.size, light.data.color = power, "DISK", size, color
        light.rotation_euler = ((Vector((0, 0, 1.3)) - light.location).to_track_quat("-Z", "Y").to_euler())
    for style in STYLES:
        add_text(bpy, LABELS[style], (OFFSETS[style], -.34, 3.62), .17)


def import_variants(bpy, output):
    imported = {}
    for style in STYLES:
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=str(output / f"{style}.glb"))
        fresh = [obj for obj in bpy.data.objects if obj not in before]
        root = bpy.data.objects.new("STYLE__" + style, None)
        bpy.context.scene.collection.objects.link(root)
        root.location.x = OFFSETS[style]
        root["axm_render_style"] = style
        for obj in fresh:
            if obj.parent is None:
                obj.parent = root
            if obj.type == "MESH":
                obj["axm_render_style"] = style
        imported[style] = [obj for obj in fresh if obj.type == "MESH"]
    return imported


def build(output):
    import bpy
    output.mkdir(parents=True, exist_ok=False)
    neutral = courier_mesh()
    formed = apply_game_form(neutral, form_parts(), "comic-salvage", 471)["realization"]
    packages = {}
    for style in STYLES:
        package = apply_game_render_style(formed, style, 471)
        built = build_glb(package["realization"])
        assert verify_glb(built["body"])["unlit_materials"] == (0 if style == "realistic-pbr" else len(formed["primitives"]))
        (output / f"{style}.glb").write_bytes(built["body"])
        packages[style] = package
    (output / "render-style-packages.json").write_text(json.dumps(packages, indent=2) + "\n")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    import_variants(bpy, output)
    text = bpy.data.texts.new("AXM_RENDER_STYLE_PACKAGES.json")
    text.write(json.dumps(packages, indent=2))
    scene_setup(bpy, output / "source.png")
    bpy.ops.wm.save_as_mainfile(filepath=str(output / "game-render-style-proof.blend"))
    bpy.ops.render.render(write_still=True)


def verify(output):
    from PIL import Image
    import bpy
    packages = json.loads((output / "render-style-packages.json").read_text())
    rows, max_color_error = [], 0.0
    reference_geometry = None
    for style in STYLES:
        body, document, binary = glb_chunks(output / f"{style}.glb")
        expected = packages[style]["realization"]
        actual_geometry = []
        unlit = style != "realistic-pbr"
        assert ("KHR_materials_unlit" in document.get("extensionsRequired", [])) == unlit
        for index, (mesh, primitive) in enumerate(zip(document["meshes"], expected["primitives"])):
            encoded = mesh["primitives"][0]
            positions = accessor(document, binary, encoded["attributes"]["POSITION"])
            normals = accessor(document, binary, encoded["attributes"]["NORMAL"])
            colours = accessor(document, binary, encoded["attributes"]["COLOR_0"])
            actual_geometry.append((positions, normals, tuple(accessor(document, binary, encoded["indices"]))))
            max_color_error = max(max_color_error, *(abs(colours[row][axis] - primitive["colors"][row][axis])
                                                      for row in range(len(colours)) for axis in range(4)))
            material = document["materials"][encoded["material"]]
            assert (material.get("extensions") == {"KHR_materials_unlit": {}}) == unlit
        if reference_geometry is None:
            reference_geometry = actual_geometry
        else:
            assert actual_geometry == reference_geometry
        rows.append({"style": style, "sha256": hashlib.sha256(body).hexdigest(),
                     "primitives": len(document["meshes"]), "unlit": unlit})
    assert max_color_error < 1e-6, max_color_error
    bpy.ops.wm.open_mainfile(filepath=str(output / "game-render-style-proof.blend"))
    assert "AXM_RENDER_STYLE_PACKAGES.json" in bpy.data.texts
    saved_variant_count = sum(obj.get("axm_render_style") in STYLES for obj in bpy.data.objects if obj.type == "MESH")
    bpy.ops.wm.read_factory_settings(use_empty=True)
    imported = import_variants(bpy, output)
    assert all(imported[style] for style in STYLES)
    # Blender's glTF importer must actually realize the two extension materials
    # differently from the lit PBR column, not merely retain JSON metadata.
    imported_unlit = {}
    for style, objects in imported.items():
        material_nodes = [node.type for obj in objects for material in obj.data.materials if material and material.use_nodes
                          for node in material.node_tree.nodes]
        imported_unlit[style] = "EMISSION" in material_nodes
    assert not imported_unlit["realistic-pbr"]
    assert imported_unlit["graphic-toon-baked"] and imported_unlit["painted-adventure-baked"]
    scene_setup(bpy, output / "reimport.png")
    bpy.ops.render.render(write_still=True)
    source = Image.open(output / "source.png").convert("RGB").tobytes()
    restored = Image.open(output / "reimport.png").convert("RGB").tobytes()
    mae = sum(abs(a - b) for a, b in zip(source, restored)) / len(source)
    assert mae < 2, mae
    report = {
        "schema": "axm.game-render-style-roundtrip/v0.1",
        "blender": bpy.app.version_string,
        "styles": rows,
        "same_decoded_geometry_across_styles": True,
        "maximum_vertex_color_float_error": max_color_error,
        "blender_fresh_import_unlit_realization": imported_unlit,
        "editable_source_variant_meshes": saved_variant_count,
        "source_reimport_render_mae": mae,
        "limits": (
            "Static fixed-light render-style specimen. No target-engine colour-management, dynamic light-band, "
            "outline, camera rim, screen-space grain, animation, performance or game-distance acceptance."
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

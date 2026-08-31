from __future__ import annotations

import argparse
import hashlib
import json
import math
import sys
from pathlib import Path

import bpy
from mathutils import Vector


def arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--height", type=float, default=5.8)
    parser.add_argument("--resolution", type=int, default=768)
    return parser.parse_args(argv)


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def point(obj: bpy.types.Object, target=(0, 0, 2.6)) -> None:
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z", "Y").to_euler()


def main() -> None:
    args = arguments()
    source = Path(args.input).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    bpy.ops.import_scene.gltf(filepath=str(source))
    meshes = [obj for obj in bpy.context.scene.objects if obj.type == "MESH"]
    if not meshes:
        raise RuntimeError("GLB contains no mesh objects")

    points = [obj.matrix_world @ Vector(corner) for obj in meshes for corner in obj.bound_box]
    minimum = Vector((min(p.x for p in points), min(p.y for p in points), min(p.z for p in points)))
    maximum = Vector((max(p.x for p in points), max(p.y for p in points), max(p.z for p in points)))
    source_height = max(maximum.z - minimum.z, 1e-6)
    scale = args.height / source_height
    center = (minimum + maximum) / 2
    for obj in meshes:
        obj.location -= center
        obj.location.z += source_height / 2
        obj.scale *= scale

    for obj in meshes:
        if obj.material_slots:
            continue
        mat = bpy.data.materials.new("AXM_Reconstruction_VertexColor")
        mat.use_nodes = True
        bsdf = mat.node_tree.nodes.get("Principled BSDF")
        bsdf.inputs["Metallic"].default_value = .72
        bsdf.inputs["Roughness"].default_value = .32
        if obj.data.color_attributes:
            attribute = mat.node_tree.nodes.new("ShaderNodeVertexColor")
            attribute.layer_name = obj.data.color_attributes[0].name
            mat.node_tree.links.new(attribute.outputs["Color"], bsdf.inputs["Base Color"])
        else:
            bsdf.inputs["Base Color"].default_value = (.18, .22, .25, 1)
        obj.data.materials.append(mat)

    scene = bpy.context.scene
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = args.resolution
    scene.render.resolution_y = args.resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = False
    scene.world.use_nodes = True
    background = scene.world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.004, .008, .016, 1)
    background.inputs["Strength"].default_value = .25

    floor_mat = bpy.data.materials.new("AXM_RenderFloor")
    floor_mat.diffuse_color = (.012, .018, .026, 1)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -.01))
    floor = bpy.context.object
    floor.data.materials.append(floor_mat)

    bpy.ops.object.camera_add()
    camera = bpy.context.object
    camera.data.lens = 62
    scene.camera = camera
    for name, location, color, energy, size in (
        ("KEY", (5.5, -5.5, 8.5), (.62, .82, 1.0), 1500, 5.5),
        ("RIM", (-5.5, 1.5, 6.5), (.08, .70, 1.0), 1200, 4.0),
        ("FILL", (2.5, 4.5, 4.0), (1.0, .35, .12), 800, 3.5),
    ):
        data = bpy.data.lights.new(name, "AREA")
        data.energy, data.color, data.shape, data.size = energy, color, "DISK", size
        light = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(light)
        light.location = location
        point(light)

    proofs = []
    for angle in (32, 122, 212, 302):
        radians = math.radians(angle)
        camera.location = (math.sin(radians) * 10.2, -math.cos(radians) * 10.2, 5.2)
        point(camera)
        path = output / f"reconstruction_view_{angle:03d}.png"
        scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        proofs.append({"angle_degrees": angle, "path": path.name, "sha256": digest(path), "bytes": path.stat().st_size})

    blend = output / "reconstruction-review.blend"
    bpy.ops.wm.save_as_mainfile(filepath=str(blend))
    manifest = {
        "schema": "axm.3d-reconstruction-review/v0.1",
        "source": {"path": str(source), "sha256": digest(source), "bytes": source.stat().st_size},
        "mesh_objects": len(meshes),
        "normalized_height_meters": args.height,
        "render_proofs": proofs,
        "blend": {"path": blend.name, "sha256": digest(blend), "bytes": blend.stat().st_size},
    }
    (output / "reconstruction-review.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()

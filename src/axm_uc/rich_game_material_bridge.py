"""UC rich game-material bundles -> packed Blender/glTF Principled materials.

Blender is imported lazily so the profile generator remains usable in headless
non-Blender workflows. Bundle hashes are checked before Blender decodes images.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import struct
import tempfile

from .game_material_bridge import _validate_png_payload
from .rich_game_materials import PROFILE_BY_NAME


MAP_CHANNELS = {
    "base_color": 3,
    "normal": 3,
    "orm": 3,
    "ao": 1,
    "roughness": 1,
    "metallic": 1,
    "height": 1,
}
REQUIRED = set(MAP_CHANNELS)
GLTF_OUTPUT_GROUP = "glTF Material Output"


def load_rich_material_bundle(folder):
    root = Path(folder).resolve(strict=True)
    manifest_path = root / "rich-game-material.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 65536:
        raise ValueError("invalid rich material manifest path/size")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("schema") != "axm.rich-game-material/v0.1":
        raise ValueError("unsupported rich material schema")
    if manifest.get("profile") not in PROFILE_BY_NAME:
        raise ValueError("unknown rich material profile")
    size = manifest.get("size")
    if type(size) is not int or not 16 <= size <= 1024:
        raise ValueError("invalid rich material size")
    if manifest.get("orm_channels") != ["occlusion", "roughness", "metallic"]:
        raise ValueError("unsupported ORM channels")
    if manifest.get("normal_convention") != "tangent +Y":
        raise ValueError("rich materials require tangent +Y normals")
    maps = manifest.get("maps")
    if not isinstance(maps, dict) or set(maps) != REQUIRED:
        raise ValueError("rich material maps are incomplete")

    payloads = {}
    for name, channels in MAP_CHANNELS.items():
        record = maps[name]
        filename = record.get("file")
        if filename != name + ".png":
            raise ValueError("unexpected rich material map filename")
        path = root / filename
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 16 * 1024 * 1024:
            raise ValueError("invalid rich material map path/size")
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise ValueError("rich material map digest mismatch: " + name)
        if record.get("channels") != channels:
            raise ValueError("rich material channel mismatch: " + name)
        expected_space = "sRGB" if name == "base_color" else "linear-data"
        if record.get("color_space") != expected_space:
            raise ValueError("rich material color-space mismatch: " + name)
        header = struct.pack(">IIBBBBB", size, size, 8, 2 if channels == 3 else 0, 0, 0, 0)
        if len(data) < 45 or data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR" or data[16:29] != header:
            raise ValueError("invalid rich material PNG header: " + name)
        _validate_png_payload(data, size, channels)
        payloads[name] = data
    return {
        "manifest": manifest,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
        "pngs": payloads,
    }


def _get_gltf_material_output_group(bpy):
    """Return the one canonical glTF exporter helper group for every material.

    Blender's exporter recognizes the exact ``glTF Material Output`` node-group
    contract. Creating a fresh group per material makes Blender suffix later names
    (``.001``, ``.002`` ...), which causes AO/occlusion to disappear from those
    exported materials. Reusing one shared group keeps every material on the same
    exporter-recognized contract.
    """
    group = bpy.data.node_groups.get(GLTF_OUTPUT_GROUP)
    created = False
    if group is None:
        group = bpy.data.node_groups.new(GLTF_OUTPUT_GROUP, "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        group.nodes.new("NodeGroupInput")
        created = True
    return group, created


def blender_rich_game_material(folder, name=None):
    bundle = load_rich_material_bundle(folder)
    import bpy

    manifest = bundle["manifest"]
    label = name or f"UC_RICH_{manifest['profile']}"
    images = []
    material = None
    group = None
    created_group = False
    try:
        material = bpy.data.materials.new(label)
        material.use_nodes = True
        nodes, links = material.node_tree.nodes, material.node_tree.links
        nodes.clear()

        output = nodes.new("ShaderNodeOutputMaterial")
        output.location = (620, 80)
        shader = nodes.new("ShaderNodeBsdfPrincipled")
        shader.location = (320, 80)
        links.new(shader.outputs["BSDF"], output.inputs["Surface"])

        textures = {}
        with tempfile.TemporaryDirectory(prefix="axm-rich-material-") as temp:
            for index, key in enumerate(("base_color", "orm", "normal")):
                path = Path(temp) / (key + ".png")
                path.write_bytes(bundle["pngs"][key])
                image = bpy.data.images.load(str(path), check_existing=False)
                images.append(image)
                image.name = label + "_" + key
                image.colorspace_settings.name = "sRGB" if key == "base_color" else "Non-Color"
                if tuple(image.size) != (manifest["size"], manifest["size"]):
                    raise ValueError("Blender decoded unexpected rich material size")
                image.pack()
                tex = nodes.new("ShaderNodeTexImage")
                tex.image = image
                tex.label = key
                tex.location = (-600, 240 - index * 280)
                textures[key] = tex

        links.new(textures["base_color"].outputs["Color"], shader.inputs["Base Color"])
        split = nodes.new("ShaderNodeSeparateColor")
        split.mode = "RGB"
        split.location = (-260, -80)
        links.new(textures["orm"].outputs["Color"], split.inputs["Color"])
        links.new(split.outputs["Green"], shader.inputs["Roughness"])
        links.new(split.outputs["Blue"], shader.inputs["Metallic"])

        group, created_group = _get_gltf_material_output_group(bpy)
        ao = nodes.new("ShaderNodeGroup")
        ao.node_tree = group
        ao.location = (0, -300)
        links.new(split.outputs["Red"], ao.inputs["Occlusion"])

        normal = nodes.new("ShaderNodeNormalMap")
        normal.space = "TANGENT"
        normal.inputs["Strength"].default_value = 1.0
        normal.location = (-30, -120)
        links.new(textures["normal"].outputs["Color"], normal.inputs["Color"])
        links.new(normal.outputs["Normal"], shader.inputs["Normal"])

        material["axm_rich_material_manifest_sha256"] = bundle["manifest_sha256"]
        material["axm_rich_material_profile"] = manifest["profile"]
        material["axm_normal_convention"] = "tangent +Y"
        return material
    except Exception:
        if material is not None:
            bpy.data.materials.remove(material)
        for image in images:
            if image.name in bpy.data.images:
                bpy.data.images.remove(image)
        if created_group and group is not None and group.name in bpy.data.node_groups:
            bpy.data.node_groups.remove(group)
        raise

"""Verified UC material bundles -> optional Blender/glTF PBR realization.

Bundle validation needs only the standard library. Blender is imported lazily;
existing hero/product materials are not replaced. Height stays authoring data.
"""
from __future__ import annotations

from array import array
import hashlib
import json
from pathlib import Path
import re
import struct
import tempfile
import zlib

from .game_material_styles import FAMILIES, FINISHES

LEGACY_NORMAL = "inherited donor for painted-metal/woven-fabric; tangent +Y for other families"
MAP_CHANNELS = {"base_color": 3, "normal": 3, "orm": 3, "ao": 1,
                "roughness": 1, "height": 1, "metallic": 1, "thickness": 1,
                "wear_mask": 1, "protection_mask": 1, "exposed_mask": 1, "coat_height": 1}
REQUIRED_MAPS = {"base_color", "normal", "orm", "ao", "roughness", "height"}


def _validate_png_payload(data, size, channels):
    """Bound the complete UC PNG stream before passing it to Blender's decoder."""
    cursor, kinds, compressed = 8, [], bytearray()
    while cursor + 12 <= len(data):
        length = struct.unpack_from('>I', data, cursor)[0]
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 8 + length
        if end + 4 > len(data) or kind not in (b'IHDR', b'IDAT', b'IEND'):
            raise ValueError('unsupported/truncated UC PNG chunk')
        payload = data[cursor + 8:end]
        if zlib.crc32(kind + payload) & 0xffffffff != struct.unpack_from('>I', data, end)[0]:
            raise ValueError('PNG CRC mismatch')
        kinds.append(kind)
        if kind == b'IDAT':
            compressed.extend(payload)
        if kind == b'IEND' and length:
            raise ValueError('invalid PNG end')
        cursor = end + 4
    if cursor != len(data) or len(kinds) < 3 or kinds[0] != b'IHDR' or kinds[-1] != b'IEND' or any(k != b'IDAT' for k in kinds[1:-1]):
        raise ValueError('invalid UC PNG chunk sequence')
    expected = size * (size * channels + 1)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, expected + 1)
    if len(raw) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError('invalid or oversized PNG scanlines')
    if any(raw[row * (size * channels + 1)] > 4 for row in range(size)):
        raise ValueError('invalid PNG scanline filter')


def load_material_bundle(folder):
    """Return verified metadata and immutable PNG bytes; never execute source data.

    Deliberately accepts only the bounded UC v0.1 format, not arbitrary downloaded
    textures. A hash checks integrity, not authorship, safety or artistic quality.
    """
    root = Path(folder).resolve(strict=True)
    manifest_path = root / "game-material.json"
    if manifest_path.is_symlink() or manifest_path.stat().st_size > 65536:
        raise ValueError("invalid material manifest path/size")
    manifest_bytes = manifest_path.read_bytes()
    manifest = json.loads(manifest_bytes)
    if not isinstance(manifest, dict) or manifest.get("schema") != "axm.game-material/v0.1":
        raise ValueError("unsupported material schema")
    family, finish = manifest.get("family"), manifest.get("finish")
    if family not in FAMILIES or finish not in [f.name for f in FINISHES]:
        raise ValueError("unknown material family/finish")
    size = manifest.get("size")
    if type(size) is not int or not 16 <= size <= 512:
        raise ValueError("invalid material size")
    if manifest.get("orm_channels") != ["occlusion", "roughness", "metallic"]:
        raise ValueError("unsupported ORM channels")
    convention = manifest.get("normal_convention")
    if convention == LEGACY_NORMAL:
        convention = "tangent -Y" if family in ("painted-metal", "woven-fabric") else "tangent +Y"
    if convention not in ("tangent +Y", "tangent -Y"):
        raise ValueError("normal orientation must be explicit or known UC legacy")
    maps = manifest.get("maps")
    if not isinstance(maps, dict) or not REQUIRED_MAPS <= maps.keys() or maps.keys() - MAP_CHANNELS.keys():
        raise ValueError("unsupported/missing material maps")
    payloads, filenames = {}, set()
    for name, record in maps.items():
        if not isinstance(record, dict):
            raise ValueError("invalid map record")
        filename = record.get("file")
        if not isinstance(filename, str) or not re.fullmatch(r"[A-Za-z0-9_-]+\.png", filename):
            raise ValueError("map must be a plain PNG filename")
        path = root / filename
        if filename in filenames or path.is_symlink() or path.stat().st_size > 4 * 1024 * 1024:
            raise ValueError("duplicate, linked or oversized map")
        filenames.add(filename)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != record.get("sha256"):
            raise ValueError("map digest mismatch: " + name)
        channels = MAP_CHANNELS[name]
        color_space = "sRGB" if name == "base_color" else "linear-data"
        if record.get("channels") != channels or record.get("color_space") != color_space:
            raise ValueError("map channel/color-space mismatch: " + name)
        header = struct.pack(">IIBBBBB", size, size, 8, 2 if channels == 3 else 0, 0, 0, 0)
        if len(data) < 45 or data[:16] != b"\x89PNG\r\n\x1a\n\x00\x00\x00\x0dIHDR" or data[16:29] != header:
            raise ValueError("invalid PNG dimensions/encoding: " + name)
        _validate_png_payload(data, size, channels)
        payloads[name] = data
    return {"manifest": manifest, "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
            "normal_convention": convention, "pngs": payloads}


def blender_game_material(folder, name=None):
    """Create a packed, editable Principled material, tested with Blender 4.3.

    AO is an explicit glTF export socket, not multiplied into base color. Blender
    preview lighting and target-engine AO can differ. This is not a cel shader.
    Image transformations affect only packed derivatives, never source files.
    """
    bundle = load_material_bundle(folder)
    import bpy

    manifest = bundle["manifest"]
    label = name or f"UC_{manifest['family']}_{manifest['finish']}"
    images, material, group = [], None, None
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
        # Decode verified snapshots, not paths that can change after validation.
        with tempfile.TemporaryDirectory(prefix="axm-material-") as temp:
            for index, key in enumerate(("base_color", "orm", "normal")):
                path = Path(temp) / (key + ".png")
                path.write_bytes(bundle["pngs"][key])
                image = bpy.data.images.load(str(path), check_existing=False)
                images.append(image)
                image.name = label + "_" + key
                image.colorspace_settings.name = "sRGB" if key == "base_color" else "Non-Color"
                if tuple(image.size) != (manifest["size"], manifest["size"]):
                    raise ValueError("Blender could not decode the declared map size")
                if key == "normal" and bundle["normal_convention"] == "tangent -Y":
                    pixels = array("f", [0.0]) * len(image.pixels)
                    image.pixels.foreach_get(pixels)
                    for offset in range(1, len(pixels), 4):
                        pixels[offset] = 1.0 - pixels[offset]
                    converted = bpy.data.images.new(label + "_normal_plusY", width=manifest["size"],
                                                    height=manifest["size"], alpha=False)
                    images.append(converted)
                    converted.colorspace_settings.name = "Non-Color"
                    converted.pixels.foreach_set(pixels)
                    converted.update()
                    images.remove(image)
                    bpy.data.images.remove(image)
                    image = converted
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
        # Canonical Blender glTF exporter socket; no baked-in/double AO.
        group = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
        group.interface.new_socket(name="Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        group.nodes.new("NodeGroupInput")
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
        material["axm_material_manifest_sha256"] = bundle["manifest_sha256"]
        material["axm_material_family"] = manifest["family"]
        material["axm_material_finish"] = manifest["finish"]
        material["axm_source_normal_convention"] = bundle["normal_convention"]
        material["axm_realized_normal_convention"] = "tangent +Y"
        return material
    except Exception:
        if material is not None:
            bpy.data.materials.remove(material)
        for image in images:
            bpy.data.images.remove(image)
        if group is not None:
            bpy.data.node_groups.remove(group)
        raise

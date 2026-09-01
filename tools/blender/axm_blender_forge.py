from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
import struct
import sys
import zlib
from pathlib import Path

import bpy
from mathutils import Vector


def write_rgba_png(path: Path, width: int, height: int, rgba: bytes) -> None:
    """Write an 8-bit RGBA PNG without relying on Blender's image save state."""
    if len(rgba) != width * height * 4:
        raise ValueError("RGBA byte count does not match texture dimensions")

    def chunk(kind: bytes, payload: bytes) -> bytes:
        return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)

    stride = width * 4
    scanlines = b"".join(b"\x00" + rgba[y * stride:(y + 1) * stride] for y in range(height))
    path.write_bytes(
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(scanlines, 9))
        + chunk(b"IEND", b"")
    )


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True)
    parser.add_argument("--output", required=True)
    return parser.parse_args(argv)


def clear_scene() -> None:
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete(use_global=False)
    for data in (bpy.data.meshes, bpy.data.curves, bpy.data.materials, bpy.data.cameras, bpy.data.lights):
        for block in list(data):
            if block.users == 0:
                data.remove(block)


def material(name: str, color: tuple[float, float, float, float], *, metallic: float = 0.0,
             roughness: float = 0.45, emission: tuple[float, float, float, float] | None = None,
             emission_strength: float = 0.0, texture_dir: Path | None = None,
             texture_size: int = 512, source_maps: dict[str, Path] | None = None) -> bpy.types.Material:
    mat = bpy.data.materials.new(name)
    mat.diffuse_color = color
    mat.use_nodes = True
    node = mat.node_tree.nodes.get("Principled BSDF")
    node.inputs["Base Color"].default_value = color
    node.inputs["Metallic"].default_value = metallic
    node.inputs["Roughness"].default_value = roughness
    embedded_maps: dict[str, bpy.types.Node] = {}
    if source_maps:
        required = {"basecolor", "roughness", "metallic", "normal"}
        missing = sorted(required - set(source_maps))
        if missing:
            raise ValueError(f"{name} source map set is missing: {', '.join(missing)}")
        for role in ("basecolor", "roughness", "metallic", "normal"):
            source = Path(source_maps[role]).resolve()
            if not source.is_file():
                raise FileNotFoundError(f"missing authored PBR source map: {source}")
            image = bpy.data.images.load(str(source), check_existing=False)
            image.name = f"{name}_{role.title()}"
            image.colorspace_settings.name = "sRGB" if role == "basecolor" else "Non-Color"
            image.pack()
            texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
            texture.name = f"{name}_Authored{role.title()}"
            texture.image = image
            texture.extension = "REPEAT"
            if role == "basecolor":
                mat.node_tree.links.new(texture.outputs["Color"], node.inputs["Base Color"])
            else:
                embedded_maps[role] = texture
    elif texture_dir is not None:
        # A retained, deterministic material compiler. The generated texture is
        # intentionally subtle: it gives the GLB a real embedded PBR image path
        # while the shader's micro-normal/roughness machinery stays procedural.
        texture_dir.mkdir(parents=True, exist_ok=True)
        size = max(256, min(2048, int(texture_size)))
        pixels = bytearray()
        roughness_pixels = bytearray()
        metallic_pixels = bytearray()
        normal_pixels = bytearray()
        salt = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
        # Blender's image pixels are encoded values once tagged sRGB. Convert
        # the authored linear palette before writing or mid-value metals become
        # almost black after color management.
        encoded_color = tuple(pow(max(0.0, min(1.0, channel)), 1.0 / 2.2) for channel in color[:3])
        for y in range(size):
            for x in range(size):
                grain = (
                    math.sin(x * .071 + salt % 37)
                    + math.sin(y * .053 + salt % 53)
                    + math.sin((x + y) * .019 + salt % 71)
                ) * .0022
                seam = -.075 if (x + salt) % 173 in (0, 1) or (y + salt // 7) % 211 == 0 else 0.0
                wear = .045 if ((x * 37 + y * 19 + salt) % 997) < 3 else 0.0
                pixels.extend(int(round(max(0.0, min(1.0, value)) * 255)) for value in (
                    encoded_color[0] + grain + seam + wear,
                    encoded_color[1] + grain + seam + wear,
                    encoded_color[2] + grain + seam + wear,
                    color[3],
                ))
                rough_value = max(.04, min(.98, roughness + grain * 1.4 - wear * .45 - seam * .35))
                metal_value = max(0.0, min(1.0, metallic - wear * 1.4 + seam * .2))
                nx = max(0, min(255, int(128 + math.sin((x + salt % 31) * .11) * 2 + seam * 42)))
                ny = max(0, min(255, int(128 + math.cos((y + salt % 43) * .09) * 2 + seam * 36)))
                nz = 250
                rough_byte = int(round(rough_value * 255))
                metal_byte = int(round(metal_value * 255))
                roughness_pixels.extend((rough_byte, rough_byte, rough_byte, 255))
                metallic_pixels.extend((metal_byte, metal_byte, metal_byte, 255))
                normal_pixels.extend((nx, ny, nz, 255))
        texture_path = texture_dir / f"{name}_basecolor.png"
        write_rgba_png(texture_path, size, size, bytes(pixels))
        image = bpy.data.images.load(str(texture_path), check_existing=False)
        image.name = f"{name}_BaseColor"
        image.colorspace_settings.name = "sRGB"
        image.pack()
        texture = mat.node_tree.nodes.new("ShaderNodeTexImage")
        texture.name = f"{name}_EmbeddedBaseColor"
        texture.image = image
        mat.node_tree.links.new(texture.outputs["Color"], node.inputs["Base Color"])
        for role, suffix, payload in (
            ("roughness", "roughness", roughness_pixels),
            ("metallic", "metallic", metallic_pixels),
            ("normal", "normal", normal_pixels),
        ):
            map_path = texture_dir / f"{name}_{suffix}.png"
            write_rgba_png(map_path, size, size, bytes(payload))
            map_image = bpy.data.images.load(str(map_path), check_existing=False)
            map_image.name = f"{name}_{suffix.title()}"
            map_image.colorspace_settings.name = "Non-Color"
            map_image.pack()
            map_node = mat.node_tree.nodes.new("ShaderNodeTexImage")
            map_node.name = f"{name}_Embedded{suffix.title()}"
            map_node.image = map_image
            embedded_maps[role] = map_node
    if not emission:
        noise = mat.node_tree.nodes.new("ShaderNodeTexNoise")
        noise.inputs["Scale"].default_value = 18.0 if metallic > .5 else 9.0
        noise.inputs["Detail"].default_value = 5.0
        noise.inputs["Roughness"].default_value = .72
        color_ramp = mat.node_tree.nodes.new("ShaderNodeValToRGB")
        darker = tuple(max(0.0, channel * .72) for channel in color[:3]) + (1.0,)
        lighter = tuple(min(1.0, channel * 1.08 + .015) for channel in color[:3]) + (1.0,)
        color_ramp.color_ramp.elements[0].position = .20
        color_ramp.color_ramp.elements[0].color = darker
        color_ramp.color_ramp.elements[1].position = .82
        color_ramp.color_ramp.elements[1].color = lighter
        rough_map = mat.node_tree.nodes.new("ShaderNodeMapRange")
        rough_map.inputs["From Min"].default_value = 0.0
        rough_map.inputs["From Max"].default_value = 1.0
        rough_map.inputs["To Min"].default_value = max(.04, roughness - .09)
        rough_map.inputs["To Max"].default_value = min(1.0, roughness + .11)
        bump = mat.node_tree.nodes.new("ShaderNodeBump")
        bump.inputs["Strength"].default_value = .055 if metallic > .5 else .035
        bump.inputs["Distance"].default_value = .018
        mat.node_tree.links.new(noise.outputs["Fac"], color_ramp.inputs["Fac"])
        if texture_dir is None:
            mat.node_tree.links.new(color_ramp.outputs["Color"], node.inputs["Base Color"])
        mat.node_tree.links.new(noise.outputs["Fac"], rough_map.inputs["Value"])
        mat.node_tree.links.new(rough_map.outputs["Result"], node.inputs["Roughness"])
        mat.node_tree.links.new(noise.outputs["Fac"], bump.inputs["Height"])
        mat.node_tree.links.new(bump.outputs["Normal"], node.inputs["Normal"])
    if embedded_maps:
        mat.node_tree.links.new(embedded_maps["roughness"].outputs["Color"], node.inputs["Roughness"])
        mat.node_tree.links.new(embedded_maps["metallic"].outputs["Color"], node.inputs["Metallic"])
        normal_map = mat.node_tree.nodes.new("ShaderNodeNormalMap")
        normal_map.inputs["Strength"].default_value = .10
        mat.node_tree.links.new(embedded_maps["normal"].outputs["Color"], normal_map.inputs["Color"])
        mat.node_tree.links.new(normal_map.outputs["Normal"], node.inputs["Normal"])
    if emission:
        socket = node.inputs.get("Emission Color") or node.inputs.get("Emission")
        if socket:
            socket.default_value = emission
        strength = node.inputs.get("Emission Strength")
        if strength:
            strength.default_value = emission_strength
    return mat


def wedge(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
          mat: bpy.types.Material, *, front_scale: tuple[float, float] = (.78, .82),
          rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = .045) -> bpy.types.Object:
    hx, hy, hz = (value / 2 for value in dimensions)
    fx, fz = front_scale
    cut_x = min(hx * .32, hz * .42)
    cut_z = min(hz * .32, hx * .42)

    def ring(y: float, sx: float, sz: float) -> list[tuple[float, float, float]]:
        x, z, cx, cz = hx * sx, hz * sz, cut_x * sx, cut_z * sz
        return [
            (-x + cx, y, -z), (x - cx, y, -z), (x, y, -z + cz), (x, y, z - cz),
            (x - cx, y, z), (-x + cx, y, z), (-x, y, z - cz), (-x, y, -z + cz),
        ]

    vertices = ring(hy, 1.0, 1.0) + ring(-hy, fx, fz)
    faces = [tuple(reversed(range(8))), tuple(range(8, 16))]
    faces += [(i, (i + 1) % 8, 8 + (i + 1) % 8, 8 + i) for i in range(8)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel * .62, segments=3, smooth=False)


def sculpted_shell(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                   mat: bpy.types.Material, *, front_scale: tuple[float, float] = (.66, .72),
                   rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = .04) -> bpy.types.Object:
    """Three-ring chamfered shell with a controlled mid-volume crown.

    Unlike a primitive or two-ring wedge this gives hero armor a deliberate
    compound profile while remaining deterministic and UV-unwrappable.
    """
    hx, hy, hz = (value / 2 for value in dimensions)
    cut_x = min(hx * .28, hz * .36)
    cut_z = min(hz * .28, hx * .36)

    def ring(y: float, sx: float, sz: float) -> list[tuple[float, float, float]]:
        x, z, cx, cz = hx * sx, hz * sz, cut_x * sx, cut_z * sz
        return [
            (-x + cx, y, -z), (x - cx, y, -z), (x, y, -z + cz), (x, y, z - cz),
            (x - cx, y, z), (-x + cx, y, z), (-x, y, z - cz), (-x, y, -z + cz),
        ]

    fx, fz = front_scale
    vertices = ring(hy, .90, .92) + ring(0, 1.0, 1.03) + ring(-hy, fx, fz)
    faces = [tuple(reversed(range(8))), tuple(range(16, 24))]
    for base in (0, 8):
        faces += [(base + i, base + (i + 1) % 8, base + 8 + (i + 1) % 8, base + 8 + i) for i in range(8)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel * .58, segments=4, smooth=False)


def articulated_cowl(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                     mat: bpy.types.Material, *, lower_scale: float = .62, upper_scale: float = .78,
                     cant: float = 0.0, rotation: tuple[float, float, float] = (0, 0, 0),
                     bevel: float = .035) -> bpy.types.Object:
    """A tapered four-ring cowl that terminates before adjacent joint axes.

    The decagonal outline makes the limb or torso mass read as one articulated
    armor volume.  Sparse service hardware can sit on top without a grid of
    rectangular tiles becoming the primary anatomy again.
    """
    hx, hy, hz = (value / 2 for value in dimensions)
    lower = max(.32, min(.92, lower_scale))
    upper = max(.42, min(1.08, upper_scale))
    outline = [
        (-hx * lower, -hz), (hx * lower, -hz),
        (hx * (lower + .16), -hz * .70), (hx, -hz * .12),
        (hx * .90, hz * .54), (hx * upper, hz),
        (-hx * upper, hz), (-hx * .90, hz * .54),
        (-hx, -hz * .12), (-hx * (lower + .16), -hz * .70),
    ]

    def ring(y: float, sx: float, sz: float, bias: float) -> list[tuple[float, float, float]]:
        return [(x * sx + bias * (z / max(hz, 1e-6)), y, z * sz) for x, z in outline]

    vertices = (
        ring(-hy, .76, .90, cant * hx * .12)
        + ring(-hy * .30, 1.0, 1.0, cant * hx * .04)
        + ring(hy * .34, .90, .95, -cant * hx * .03)
        + ring(hy, .62, .78, -cant * hx * .10)
    )
    count = len(outline)
    faces = [tuple(reversed(range(count))), tuple(range(count * 3, count * 4))]
    for layer in range(3):
        base = layer * count
        faces += [(base + i, base + (i + 1) % count,
                   base + count + (i + 1) % count, base + count + i) for i in range(count)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=5, smooth=False)


def descending_v_shell(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                       mat: bpy.types.Material, *, notch: float = .30,
                       rotation: tuple[float, float, float] = (0, 0, 0),
                       bevel: float = .022) -> bpy.types.Object:
    """Closed overlapping torso plate with a concave collar and descending V keel."""
    hx, hy, hz = (value / 2 for value in dimensions)
    notch_depth = max(.12, min(.46, notch))
    outline = [
        (-hx, hz), (0, hz * (1.0 - notch_depth)), (hx, hz),
        (hx * .86, hz * .08), (0, -hz), (-hx * .86, hz * .08),
    ]

    def ring(y: float, sx: float, sz: float) -> list[tuple[float, float, float]]:
        return [(x * sx, y, z * sz) for x, z in outline]

    vertices = ring(-hy, .92, .94) + ring(-hy * .22, 1.0, 1.02) + ring(hy, .74, .82)
    count = len(outline)
    faces = [tuple(reversed(range(count))), tuple(range(count * 2, count * 3))]
    for layer in range(2):
        base = layer * count
        faces += [(base + i, base + (i + 1) % count,
                   base + count + (i + 1) % count, base + count + i) for i in range(count)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=5, smooth=False)


def petal_plate(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0),
                bevel: float = .026) -> bpy.types.Object:
    """Pointed three-ring biomorphic armor plate used by the Mir grammar."""
    hx, hy, hz = (value / 2 for value in dimensions)
    outline = [(0, -hz), (hx * .68, -hz * .48), (hx, hz * .08),
               (hx * .55, hz * .67), (0, hz), (-hx * .55, hz * .67),
               (-hx, hz * .08), (-hx * .68, -hz * .48)]

    def ring(y: float, scale_x: float, scale_z: float) -> list[tuple[float, float, float]]:
        return [(x * scale_x, y, z * scale_z) for x, z in outline]

    vertices = ring(hy, .90, .92) + ring(0, 1.0, 1.02) + ring(-hy, .82, .88)
    faces = [tuple(reversed(range(8))), tuple(range(16, 24))]
    for base in (0, 8):
        faces += [(base + i, base + (i + 1) % 8, base + 8 + (i + 1) % 8, base + 8 + i) for i in range(8)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=5, smooth=False)


def sacred_blade_plate(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                       mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0),
                       sweep: float = 0.0, bevel: float = .018) -> bpy.types.Object:
    """Thin hooked Mir shell with a sharp root and crown instead of a toy-like lozenge.

    The asymmetric five-ring profile supplies a readable blade edge, a raised
    ceramic crown, and a recessed mounting surface.  It is deliberately a
    reusable grammar primitive: hero limbs, collar, shield and weapons can all
    share the same manufactured petal language without sharing identical forms.
    """
    hx, hy, hz = (value / 2 for value in dimensions)
    # Preserve one faction grammar while varying anatomical roots, crowns and
    # shoulders. The object name makes this deterministic across rebuilds.
    signature = int(hashlib.sha256(name.encode("utf-8")).hexdigest()[:8], 16)
    crown = .94 + ((signature >> 4) % 13) / 100.0
    root = .91 + ((signature >> 9) % 11) / 100.0
    shoulder = .93 + ((signature >> 14) % 15) / 100.0
    outline = [
        (0, -hz * root), (hx * .58, -hz * .64), (hx * shoulder, -hz * .06),
        (hx * .82, hz * .46), (hx * .20 + sweep * hx, hz * crown),
        (-hx * .24 + sweep * hx, hz * .78), (-hx * .72, hz * .28),
        (-hx * .88 * shoulder, -hz * .24), (-hx * .46, -hz * .72),
    ]

    def ring(y: float, sx: float, sz: float, x_bias: float = 0.0) -> list[tuple[float, float, float]]:
        return [(x * sx + x_bias, y, z * sz) for x, z in outline]

    vertices = (
        ring(hy, .76, .86, sweep * hx * .05)
        + ring(hy * .35, .94, .98)
        + ring(0, 1.0, 1.03)
        + ring(-hy * .42, .90, .96)
        + ring(-hy, .66, .78, -sweep * hx * .06)
    )
    count = len(outline)
    faces = [tuple(reversed(range(count))), tuple(range(count * 4, count * 5))]
    for layer in range(4):
        base = layer * count
        faces += [(base + i, base + (i + 1) % count,
                   base + count + (i + 1) % count, base + count + i) for i in range(count)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=5, smooth=False)


def tapered_chassis(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
                    mat: bpy.types.Material, *, lower_scale: float = .70, front_scale: float = .82,
                    rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = .05) -> bpy.types.Object:
    """A vertically tapered load-bearing volume for torso/pelvis silhouettes."""
    hx, hy, hz = (value / 2 for value in dimensions)
    vertices = [
        (-hx * lower_scale, -hy * front_scale, -hz), (hx * lower_scale, -hy * front_scale, -hz),
        (hx, -hy * front_scale, hz), (-hx, -hy * front_scale, hz),
        (-hx * lower_scale, hy, -hz), (hx * lower_scale, hy, -hz),
        (hx, hy, hz), (-hx, hy, hz),
    ]
    faces = [(0, 1, 2, 3), (4, 7, 6, 5), (0, 4, 5, 1), (1, 5, 6, 2),
             (2, 6, 7, 3), (3, 7, 4, 0)]
    mesh = bpy.data.meshes.new(f"{name}_Mesh")
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    obj.location = location
    obj.rotation_euler = rotation
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=4, smooth=False)


def assign(obj: bpy.types.Object, mat: bpy.types.Material) -> bpy.types.Object:
    if obj.type == "MESH":
        obj.data.materials.append(mat)
    return obj


def finish_mesh(obj: bpy.types.Object, *, bevel: float = 0.0, segments: int = 3, smooth: bool = True) -> bpy.types.Object:
    if obj.type == "MESH" and smooth:
        for polygon in obj.data.polygons:
            polygon.use_smooth = True
    if bevel > 0:
        modifier = obj.modifiers.new("AXM_Bevel", "BEVEL")
        modifier.width = bevel
        modifier.segments = segments
        modifier.limit_method = "ANGLE"
    return obj


def box(name: str, location: tuple[float, float, float], dimensions: tuple[float, float, float],
        mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), bevel: float = 0.06,
        segments: int = 3) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cube_add(location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    obj.dimensions = dimensions
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel * .66, segments=segments, smooth=False)


def sphere(name: str, location: tuple[float, float, float], scale: tuple[float, float, float],
           mat: bpy.types.Material, *, segments: int = 40, rings: int = 24) -> bpy.types.Object:
    bpy.ops.mesh.primitive_uv_sphere_add(segments=segments, ring_count=rings, location=location)
    obj = bpy.context.object
    obj.name = name
    obj.scale = scale
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    assign(obj, mat)
    return finish_mesh(obj, smooth=True)


def cylinder(name: str, location: tuple[float, float, float], radius: float, depth: float,
             mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), vertices: int = 32,
             bevel: float = 0.035) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cylinder_add(vertices=vertices, radius=radius, depth=depth, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=3)


def cone(name: str, location: tuple[float, float, float], radius1: float, radius2: float, depth: float,
         mat: bpy.types.Material, *, rotation: tuple[float, float, float] = (0, 0, 0), vertices: int = 32,
         bevel: float = 0.025) -> bpy.types.Object:
    bpy.ops.mesh.primitive_cone_add(vertices=vertices, radius1=radius1, radius2=radius2, depth=depth,
                                    location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, bevel=bevel, segments=3)


def torus(name: str, location: tuple[float, float, float], major: float, minor: float, mat: bpy.types.Material,
          *, rotation: tuple[float, float, float] = (0, 0, 0), major_segments: int = 48,
          minor_segments: int = 12) -> bpy.types.Object:
    bpy.ops.mesh.primitive_torus_add(major_radius=major, minor_radius=minor, major_segments=major_segments,
                                     minor_segments=minor_segments, location=location, rotation=rotation)
    obj = bpy.context.object
    obj.name = name
    assign(obj, mat)
    return finish_mesh(obj, smooth=True)


def beam(name: str, start: tuple[float, float, float], end: tuple[float, float, float], radius: float,
         mat: bpy.types.Material, *, vertices: int = 24) -> bpy.types.Object:
    a, b = Vector(start), Vector(end)
    delta = b - a
    obj = cylinder(name, tuple((a + b) / 2), radius, delta.length, mat, vertices=vertices)
    obj.rotation_mode = "QUATERNION"
    obj.rotation_quaternion = delta.to_track_quat("Z", "Y")
    return obj


def cable(name: str, points: list[tuple[float, float, float]], radius: float, mat: bpy.types.Material) -> bpy.types.Object:
    curve = bpy.data.curves.new(name, "CURVE")
    curve.dimensions = "3D"
    curve.resolution_u = 2
    curve.bevel_depth = radius
    curve.bevel_resolution = 3
    spline = curve.splines.new("BEZIER")
    spline.bezier_points.add(len(points) - 1)
    for point, value in zip(spline.bezier_points, points):
        point.co = value
        point.handle_left_type = "AUTO"
        point.handle_right_type = "AUTO"
    obj = bpy.data.objects.new(name, curve)
    bpy.context.collection.objects.link(obj)
    curve.materials.append(mat)
    return obj


def add_axiom_details(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    gunmetal, pale, cyan, amber, dark = mats["gunmetal"], mats["pale"], mats["cyan"], mats["amber"], mats["dark"]
    # Grounded digitigrade legs with layered armor and visible mechanical articulation.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        hip = (side * 0.82, 0.0, 2.45)
        knee = (side * 1.02, 0.10, 1.48)
        ankle = (side * 0.86, -0.10, 0.55)
        objects += [sphere(f"AX_{prefix}_HIP_JOINT", hip, (.30, .30, .30), dark)]
        objects += [beam(f"AX_{prefix}_THIGH_CORE", hip, knee, .25, gunmetal)]
        objects += [box(f"AX_{prefix}_THIGH_ARMOR", (side * .94, -.03, 1.98), (.55, .52, .90), pale,
                        rotation=(0, side * .18, side * .10), bevel=.09)]
        objects += [sphere(f"AX_{prefix}_KNEE", knee, (.32, .32, .32), gunmetal)]
        objects += [torus(f"AX_{prefix}_KNEE_RING", knee, .31, .055, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"AX_{prefix}_SHIN_CORE", knee, ankle, .21, dark)]
        objects += [box(f"AX_{prefix}_SHIN_ARMOR", (side * .94, -.03, .99), (.52, .60, .78), gunmetal,
                        rotation=(0, side * -.10, side * -.05), bevel=.08)]
        objects += [box(f"AX_{prefix}_FOOT", (side * .84, -.18, .20), (.72, 1.05, .32), dark,
                        rotation=(0, 0, side * .02), bevel=.08)]
        objects += [box(f"AX_{prefix}_TOE_PLATE", (side * .84, -.60, .25), (.65, .42, .18), pale, bevel=.05)]
        for i in range(3):
            objects += [cylinder(f"AX_{prefix}_ANKLE_PISTON_{i}", (side * (.70 + i * .14), -.02, .60), .045,
                                 .72, pale, rotation=(0, side * .12, 0), vertices=16, bevel=.015)]

    # Pelvis, reactor torso, armored breastplate and command sensor head.
    objects += [box("AX_PELVIS", (0, 0, 2.62), (1.85, .95, .66), gunmetal, bevel=.13)]
    objects += [box("AX_PELVIS_FRONT", (0, -.47, 2.65), (1.18, .18, .40), pale, bevel=.05)]
    objects += [sphere("AX_REACTOR_CORE", (0, -.13, 3.42), (.62, .45, .70), cyan, segments=48, rings=32)]
    objects += [torus("AX_REACTOR_CAGE", (0, -.19, 3.42), .73, .075, pale, rotation=(math.pi / 2, 0, 0))]
    objects += [box("AX_TORSO_MAIN", (0, .05, 3.58), (2.30, 1.08, 1.58), gunmetal, bevel=.16)]
    objects += [box("AX_CHEST_PLATE", (0, -.53, 3.68), (1.62, .17, .96), pale,
                    rotation=(math.radians(7), 0, 0), bevel=.08)]
    objects += [box("AX_CHEST_CENTER", (0, -.67, 3.65), (.22, .09, .76), cyan, bevel=.025)]
    objects += [box("AX_NECK", (0, 0, 4.53), (.56, .52, .30), dark, bevel=.07)]
    objects += [box("AX_HEAD", (0, -.03, 4.86), (.88, .74, .55), pale, bevel=.11)]
    objects += [box("AX_VISOR", (0, -.43, 4.90), (.60, .065, .14), cyan, bevel=.025)]
    objects += [cylinder("AX_SENSOR_MAST", (0, .03, 5.35), .07, .68, gunmetal, vertices=20)]
    objects += [sphere("AX_SENSOR_ORB", (0, .03, 5.68), (.14, .14, .14), amber, segments=28, rings=18)]

    # Shoulder architecture and arms.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        shoulder = (side * 1.48, 0, 4.04)
        elbow = (side * 1.68, .02, 3.10)
        wrist = (side * 1.52, -.08, 2.42)
        objects += [sphere(f"AX_{prefix}_SHOULDER_JOINT", shoulder, (.40, .40, .40), dark)]
        objects += [box(f"AX_{prefix}_PAULDRON", (side * 1.58, -.02, 4.18), (.86, 1.02, .68), pale,
                        rotation=(0, side * .12, side * .10), bevel=.13)]
        objects += [box(f"AX_{prefix}_PAULDRON_STRIPE", (side * 1.60, -.55, 4.18), (.42, .06, .18), amber, bevel=.02)]
        objects += [beam(f"AX_{prefix}_UPPER_ARM", shoulder, elbow, .25, gunmetal)]
        objects += [sphere(f"AX_{prefix}_ELBOW", elbow, (.27, .27, .27), dark)]
        objects += [torus(f"AX_{prefix}_ELBOW_RING", elbow, .26, .045, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"AX_{prefix}_FOREARM", elbow, wrist, .23, gunmetal)]
        objects += [box(f"AX_{prefix}_FOREARM_ARMOR", (side * 1.62, -.05, 2.76), (.55, .66, .66), pale, bevel=.08)]
        objects += [box(f"AX_{prefix}_HAND", wrist, (.38, .46, .30), dark, bevel=.06)]

    # Rail cannon mounted on the right arm, shield/projector on the left.
    objects += [box("AX_RAIL_BODY", (2.05, -.34, 2.82), (.72, 1.65, .54), gunmetal,
                    rotation=(0, 0, 0), bevel=.08)]
    for x in (1.88, 2.22):
        objects += [beam(f"AX_RAIL_{x:.2f}", (x, -.72, 2.84), (x, -2.05, 2.84), .075, pale, vertices=20)]
    objects += [box("AX_RAIL_EMITTER", (2.05, -2.10, 2.84), (.58, .18, .36), cyan, bevel=.04)]
    objects += [cylinder("AX_SHIELD_DISC", (-2.05, -.52, 2.86), .62, .14, pale,
                         rotation=(math.pi / 2, 0, 0), vertices=48, bevel=.06)]
    objects += [torus("AX_SHIELD_RING", (-2.05, -.61, 2.86), .48, .055, cyan,
                      rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("AX_SHIELD_CORE", (-2.05, -.69, 2.86), (.16, .09, .16), amber)]

    # Rear heat vanes, thrusters, vents, bolts, and animated-looking cable language.
    for side in (-1, 1):
        for i in range(3):
            x = side * (.50 + i * .22)
            objects += [box(f"AX_HEAT_VANE_{side}_{i}", (x, .69 + i * .035, 3.70), (.10, .44, .92), dark,
                            rotation=(side * -.12, 0, side * .12), bevel=.025)]
        objects += [cylinder(f"AX_THRUSTER_{side}", (side * .79, .74, 3.18), .25, .62, gunmetal,
                             rotation=(math.pi / 2, 0, 0), vertices=32)]
        objects += [cone(f"AX_THRUSTER_GLOW_{side}", (side * .79, 1.08, 3.18), .18, .08, .18, cyan,
                         rotation=(math.pi / 2, 0, 0), vertices=32)]
        cable_obj = cable(f"AX_CABLE_{side}", [(side * .72, .55, 3.95), (side * 1.10, .77, 3.55),
                                                (side * 1.42, .48, 3.08)], .035, amber)
        objects.append(cable_obj)
    for row in range(4):
        for col in range(5):
            x = (col - 2) * .29
            z = 3.25 + row * .24
            objects += [cylinder(f"AX_CHEST_BOLT_{row}_{col}", (x, -.655, z), .026, .045, dark,
                                 rotation=(math.pi / 2, 0, 0), vertices=12, bevel=.008)]
    for i in range(8):
        x = rng.uniform(-.82, .82)
        objects += [box(f"AX_MICRO_PANEL_{i}", (x, -.682, rng.uniform(3.28, 4.08)),
                        (rng.uniform(.08, .18), .025, rng.uniform(.04, .10)), amber if i % 3 == 0 else dark,
                        bevel=.008, segments=2)]

    # Hero-detail pass: interlocking armor replaces the primitive read with a
    # large/medium/small hierarchy while retaining the deterministic chassis.
    objects += [wedge("AX_HERO_ABDOMEN", (0, -.56, 3.02), (1.30, .30, .64), gunmetal,
                      front_scale=(.72, .68), rotation=(math.radians(-7), 0, 0), bevel=.055)]
    objects += [wedge("AX_HERO_CHEST_L", (-.57, -.70, 3.78), (1.03, .28, 1.10), pale,
                      front_scale=(.76, .86), rotation=(math.radians(5), math.radians(-5), math.radians(-4)), bevel=.06)]
    objects += [wedge("AX_HERO_CHEST_R", (.57, -.70, 3.78), (1.03, .28, 1.10), pale,
                      front_scale=(.76, .86), rotation=(math.radians(5), math.radians(5), math.radians(4)), bevel=.06)]
    objects += [wedge("AX_HERO_REACTOR_WINDOW", (0, -.88, 3.61), (.49, .12, .90), cyan,
                      front_scale=(.72, .82), bevel=.025)]
    objects += [box("AX_HERO_REACTOR_TOP", (0, -.91, 4.10), (.56, .10, .09), amber, bevel=.018)]
    objects += [box("AX_HERO_REACTOR_BOTTOM", (0, -.91, 3.12), (.46, .10, .09), dark, bevel=.018)]
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        objects += [wedge(f"AX_HERO_TORSO_FLANK_{prefix}", (side * 1.06, -.47, 3.68), (.58, .55, 1.30), gunmetal,
                          front_scale=(.62, .76), rotation=(0, side * math.radians(8), side * math.radians(5)), bevel=.055)]
        objects += [wedge(f"AX_HERO_COLLAR_{prefix}", (side * .62, -.38, 4.43), (.91, .45, .34), pale,
                          front_scale=(.74, .66), rotation=(0, side * math.radians(10), side * math.radians(7)), bevel=.045)]
        for slot in range(4):
            objects += [box(f"AX_HERO_VENT_{prefix}_{slot}", (side * 1.18, -.785, 3.40 + slot * .20),
                            (.16, .055, .10), dark, rotation=(0, 0, side * math.radians(5)), bevel=.012)]

        # Angular shoulder carapace with nested armor and a recessed service bay.
        objects += [wedge(f"AX_HERO_SHOULDER_OUTER_{prefix}", (side * 1.70, -.10, 4.24), (.96, 1.18, .86), gunmetal,
                          front_scale=(.68, .74), rotation=(0, side * math.radians(9), side * math.radians(7)), bevel=.07)]
        objects += [wedge(f"AX_HERO_SHOULDER_CAP_{prefix}", (side * 1.72, -.68, 4.26), (.72, .18, .58), pale,
                          front_scale=(.72, .80), rotation=(0, side * math.radians(6), side * math.radians(7)), bevel=.045)]
        objects += [box(f"AX_HERO_SHOULDER_LIGHT_{prefix}", (side * 1.72, -.80, 4.27), (.29, .045, .065), amber, bevel=.012)]
        for slot in range(3):
            objects += [box(f"AX_HERO_SHOULDER_SLOT_{prefix}_{slot}",
                            (side * (1.46 + slot * .12), -.81, 4.03), (.065, .038, .23), dark, bevel=.008)]

        # Layered arm armor, exposed actuator pistons and guarded elbow.
        objects += [wedge(f"AX_HERO_BICEP_{prefix}", (side * 1.58, -.12, 3.58), (.62, .66, .82), gunmetal,
                          front_scale=(.70, .70), rotation=(0, side * math.radians(5), side * math.radians(4)), bevel=.055)]
        objects += [box(f"AX_HERO_BICEP_FACE_{prefix}", (side * 1.59, -.49, 3.58), (.34, .075, .46), pale, bevel=.035)]
        objects += [wedge(f"AX_HERO_FOREARM_COWL_{prefix}", (side * 1.60, -.14, 2.77), (.66, .78, .78), gunmetal,
                          front_scale=(.72, .74), rotation=(0, side * math.radians(4), side * math.radians(3)), bevel=.055)]
        objects += [box(f"AX_HERO_FOREARM_RAIL_{prefix}", (side * 1.78, -.52, 2.77), (.12, .12, .50), pale, bevel=.022)]
        for piston in (-1, 1):
            objects += [beam(f"AX_HERO_ARM_PISTON_{prefix}_{piston}",
                             (side * (1.37 + piston * .07), -.32, 3.35),
                             (side * (1.44 + piston * .07), -.36, 2.95), .035, amber, vertices=16)]

        # Thigh/shin shells and three-part armored feet.
        objects += [wedge(f"AX_HERO_THIGH_FRONT_{prefix}", (side * .95, -.38, 1.98), (.66, .34, 1.02), pale,
                          front_scale=(.68, .82), rotation=(0, side * math.radians(5), side * math.radians(3)), bevel=.052)]
        objects += [wedge(f"AX_HERO_THIGH_SIDE_{prefix}", (side * 1.25, -.02, 1.96), (.24, .58, .80), gunmetal,
                          front_scale=(.62, .76), rotation=(0, side * math.radians(6), 0), bevel=.038)]
        objects += [wedge(f"AX_HERO_KNEE_GUARD_{prefix}", (side * 1.02, -.46, 1.46), (.58, .24, .52), gunmetal,
                          front_scale=(.66, .72), bevel=.045)]
        objects += [box(f"AX_HERO_KNEE_LIGHT_{prefix}", (side * 1.02, -.60, 1.47), (.22, .045, .08), cyan, bevel=.014)]
        objects += [wedge(f"AX_HERO_SHIN_FRONT_{prefix}", (side * .91, -.39, .86), (.60, .30, .88), pale,
                          front_scale=(.62, .78), rotation=(0, side * math.radians(-4), side * math.radians(-2)), bevel=.05)]
        objects += [box(f"AX_HERO_SHIN_CHANNEL_{prefix}", (side * .91, -.56, .86), (.16, .055, .52), dark, bevel=.018)]
        objects += [box(f"AX_HERO_ANKLE_COWL_{prefix}", (side * .84, -.15, .42), (.58, .56, .34), gunmetal, bevel=.06)]
        for toe in (-1, 0, 1):
            objects += [wedge(f"AX_HERO_TOE_{prefix}_{toe}", (side * (.84 + toe * .19), -.69, .17),
                              (.17, .58, .18), pale if toe == 0 else gunmetal,
                              front_scale=(.62, .58), rotation=(0, 0, side * toe * math.radians(3)), bevel=.035)]

    # A compact command sensor cluster prevents the head from reading as a toy face.
    objects += [wedge("AX_HERO_HEAD_FACE", (0, -.44, 4.88), (.70, .18, .36), dark,
                      front_scale=(.72, .70), bevel=.04)]
    for eye in (-1, 1):
        objects += [sphere(f"AX_HERO_OPTIC_{eye}", (eye * .17, -.55, 4.91), (.075, .045, .075), cyan,
                           segments=24, rings=16)]
        objects += [box(f"AX_HERO_OPTIC_GUARD_{eye}", (eye * .17, -.51, 5.05), (.22, .10, .05), pale, bevel=.012)]
    objects += [box("AX_HERO_HEAD_BROW", (0, -.51, 5.12), (.62, .10, .10), gunmetal, bevel=.022)]
    for side in (-1, 1):
        objects += [cylinder(f"AX_HERO_HEAD_DISC_{side}", (side * .48, -.04, 4.88), .18, .12, gunmetal,
                             rotation=(0, math.pi / 2, 0), vertices=32)]
        objects += [torus(f"AX_HERO_HEAD_DISC_RING_{side}", (side * .55, -.04, 4.88), .14, .025, amber,
                          rotation=(0, math.pi / 2, 0), major_segments=32, minor_segments=8)]

    # Rail cannon receives functional coil, cooling, housing and sight details.
    for stage in range(5):
        y = -.86 - stage * .28
        objects += [box(f"AX_HERO_RAIL_HOUSING_{stage}", (2.05, y, 2.84),
                        (.72 - stage * .035, .20, .46 - stage * .025), gunmetal if stage % 2 else pale, bevel=.035)]
        objects += [torus(f"AX_HERO_RAIL_COIL_{stage}", (2.05, y - .09, 2.84), .24 - stage * .01, .028, cyan,
                          rotation=(math.pi / 2, 0, 0), major_segments=32, minor_segments=8)]
    for side in (-1, 1):
        objects += [box(f"AX_HERO_RAIL_SIDE_{side}", (2.05 + side * .32, -1.30, 2.84), (.08, 1.50, .54), dark, bevel=.025)]
    objects += [box("AX_HERO_RAIL_SIGHT", (2.05, -1.36, 3.24), (.22, .48, .18), amber, bevel=.025)]

    # Shield projector gets visible stacked emitter architecture.
    for radius, depth, mat in ((.66, .10, gunmetal), (.53, .075, pale), (.39, .05, cyan)):
        objects += [torus(f"AX_HERO_SHIELD_LAYER_{radius}", (-2.05, -.65 - depth, 2.86), radius, depth, mat,
                          rotation=(math.pi / 2, 0, 0), major_segments=64, minor_segments=12)]
    for i in range(8):
        angle = i * math.tau / 8
        objects += [box(f"AX_HERO_SHIELD_NODE_{i}", (-2.05 + math.cos(angle) * .52, -.80,
                                                      2.86 + math.sin(angle) * .52),
                        (.10, .06, .16), amber if i % 2 else dark, rotation=(0, 0, angle), bevel=.018)]


def add_axiom_hero_v3(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    """Layered military walker derived from the Axiom faction grammar.

    This builder deliberately avoids the legacy box-body topology. Every major
    mass is assembled from tapered load-bearing volumes and nested armor shells.
    """
    gm, pale, cyan, amber, dark = (mats[k] for k in ("gunmetal", "pale", "cyan", "amber", "dark"))

    # Feet and legs: wide armored stance, separate toes, visible ankle/knee mechanics.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        x = side * .96
        for toe in (-1, 0, 1):
            objects.append(wedge(f"AX3_{p}_TOE_{toe}", (x + toe * .18, -.50, .15), (.18, .80, .22),
                                 pale if toe == 0 else gm, front_scale=(.58, .52),
                                 rotation=(0, 0, toe * math.radians(3)), bevel=.026))
        objects.append(wedge(f"AX3_{p}_HEEL", (x, .13, .20), (.72, .68, .32), dark,
                             front_scale=(.72, .64), rotation=(math.radians(-3), 0, 0), bevel=.045))
        ankle = (x, -.02, .48)
        knee = (side * .80, -.02, 1.60)
        hip = (side * .70, .02, 2.68)
        objects.append(sphere(f"AX3_{p}_ANKLE", ankle, (.24, .24, .24), dark, segments=32, rings=20))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_ANKLE_PISTON_{piston}",
                                (x + piston * .16, -.06, .36), (x + piston * .13, -.04, .78), .035, amber, vertices=16))
        objects.append(beam(f"AX3_{p}_SHIN_CORE", ankle, knee, .19, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_SHIN_MAIN", (side * .78, -.10, 1.03), (.39, .40, .65), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_SHIN_FRONT", (side * .78, -.50, 1.06), (.49, .19, .98), pale,
                             front_scale=(.66, .70), rotation=(0, side * math.radians(-3), 0), bevel=.036))
        objects.append(box(f"AX3_{p}_SHIN_CHANNEL", (side * .78, -.615, 1.02), (.12, .035, .60), dark, bevel=.01))
        objects.append(box(f"AX3_{p}_SHIN_LIGHT", (side * .78, -.64, .76), (.075, .025, .15), cyan, bevel=.008))
        objects.append(sphere(f"AX3_{p}_KNEE_MECH", knee, (.34, .34, .34), dark, segments=36, rings=22))
        objects.append(cylinder(f"AX3_{p}_KNEE_AXLE", knee, .26, .82, gm, rotation=(0, math.pi / 2, 0), vertices=36))
        objects.append(wedge(f"AX3_{p}_KNEE_GUARD", (side * .80, -.40, 1.62), (.64, .30, .62), pale,
                             front_scale=(.58, .62), rotation=(math.radians(-4), 0, 0), bevel=.043))
        objects.append(box(f"AX3_{p}_KNEE_MARK", (side * .80, -.58, 1.65), (.20, .035, .075), amber, bevel=.01))
        objects.append(beam(f"AX3_{p}_THIGH_CORE", knee, hip, .24, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_THIGH_MAIN", (side * .74, -.02, 2.18), (.47, .45, .64), gm,
                              segments=48, rings=30))
        objects.append(wedge(f"AX3_{p}_THIGH_FRONT", (side * .74, -.48, 2.20), (.56, .18, .84), pale,
                             front_scale=(.68, .74), rotation=(0, side * math.radians(4), 0), bevel=.038))
        objects.append(wedge(f"AX3_{p}_THIGH_OUTER", (side * 1.12, .02, 2.22), (.22, .62, .76), dark,
                             front_scale=(.62, .68), rotation=(0, side * math.radians(8), 0), bevel=.032))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_KNEE_PISTON_{piston}",
                                (side * (.56 + piston * .07), -.18, 1.74),
                                (side * (.60 + piston * .07), -.15, 2.42), .038, pale, vertices=18))

    # Pelvis, waist bearing and segmented armored abdomen.
    objects.append(sphere("AX3_PELVIS_CORE", (0, .02, 2.72), (1.00, .58, .40), dark,
                          segments=52, rings=32))
    objects.append(wedge("AX3_PELVIS_FRONT", (0, -.58, 2.74), (1.36, .20, .47), gm,
                         front_scale=(.62, .60), bevel=.035))
    objects.append(box("AX3_PELVIS_SIGNAL", (0, -.70, 2.78), (.38, .035, .08), amber, bevel=.012))
    objects.append(torus("AX3_WAIST_BEARING", (0, 0, 3.05), .60, .10, gm, major_segments=64, minor_segments=16))
    objects.append(cylinder("AX3_WAIST_CORE", (0, 0, 3.05), .46, .35, dark, vertices=48))
    for level, (z, width) in enumerate(((3.16, 1.22), (3.35, 1.44), (3.54, 1.68))):
        objects.append(wedge(f"AX3_AB_SEGMENT_{level}", (0, -.16, z), (width, .78, .27), gm,
                             front_scale=(.72, .64), rotation=(math.radians(-4 + level * 2), 0, 0), bevel=.035))
        objects.append(box(f"AX3_AB_SEAM_{level}", (0, -.58, z), (width * .60, .035, .035), dark, bevel=.006))

    # Deep torso volume, separated pectoral armor, collar and exposed cyan reactor.
    objects.append(sphere("AX3_TORSO_CORE", (0, .04, 4.02), (1.42, .76, .94), dark,
                          segments=64, rings=40))
    objects.append(wedge("AX3_CHEST_LEFT", (-.62, -.69, 4.04), (1.23, .24, 1.18), gm,
                         front_scale=(.64, .74), rotation=(math.radians(4), math.radians(-5), math.radians(-3)), bevel=.055))
    objects.append(wedge("AX3_CHEST_RIGHT", (.62, -.69, 4.04), (1.23, .24, 1.18), gm,
                         front_scale=(.64, .74), rotation=(math.radians(4), math.radians(5), math.radians(3)), bevel=.055))
    objects.append(wedge("AX3_CHEST_PLATE_LEFT", (-.65, -.85, 4.04), (.92, .11, .84), pale,
                         front_scale=(.70, .76), rotation=(math.radians(4), math.radians(-5), math.radians(-3)), bevel=.032))
    objects.append(wedge("AX3_CHEST_PLATE_RIGHT", (.65, -.85, 4.04), (.92, .11, .84), pale,
                         front_scale=(.70, .76), rotation=(math.radians(4), math.radians(5), math.radians(3)), bevel=.032))
    objects.append(wedge("AX3_REACTOR", (0, -.92, 3.98), (.54, .14, .92), cyan,
                         front_scale=(.68, .72), bevel=.022))
    for side in (-1, 1):
        objects.append(box(f"AX3_REACTOR_RAIL_{side}", (side * .34, -.92, 3.98), (.09, .08, 1.00), amber, bevel=.015))
        objects.append(wedge(f"AX3_COLLAR_{side}", (side * .70, -.42, 4.73), (1.15, .66, .35), pale,
                             front_scale=(.66, .62), rotation=(math.radians(2), side * math.radians(7), side * math.radians(6)), bevel=.04))
        objects.append(wedge(f"AX3_TORSO_SIDE_{side}", (side * 1.33, -.05, 3.98), (.44, 1.05, 1.20), gm,
                             front_scale=(.58, .72), rotation=(0, side * math.radians(8), 0), bevel=.045))
        for vent in range(5):
            objects.append(box(f"AX3_CHEST_VENT_{side}_{vent}", (side * 1.32, -.61, 3.67 + vent * .17),
                               (.13, .045, .09), dark, rotation=(0, 0, side * math.radians(5)), bevel=.009))

    # Small command head with guarded optics and rear antennae.
    objects.append(cylinder("AX3_NECK", (0, 0, 4.90), .28, .34, dark, vertices=36))
    objects.append(sphere("AX3_HEAD_CORE", (0, -.02, 5.16), (.46, .38, .30), gm,
                          segments=40, rings=24))
    objects.append(wedge("AX3_HEAD_FACE", (0, -.43, 5.16), (.65, .16, .30), dark,
                         front_scale=(.66, .62), bevel=.028))
    for eye in (-1, 1):
        objects.append(sphere(f"AX3_OPTIC_{eye}", (eye * .17, -.535, 5.18), (.075, .045, .075), cyan,
                              segments=24, rings=16))
        objects.append(box(f"AX3_OPTIC_BROW_{eye}", (eye * .17, -.50, 5.32), (.25, .08, .055), pale, bevel=.012))
    objects.append(box("AX3_HEAD_LOWER_SENSOR", (0, -.52, 5.00), (.28, .045, .055), amber, bevel=.009))
    for side in (-1, 1):
        objects.append(cylinder(f"AX3_HEAD_COMMS_{side}", (side * .46, -.02, 5.15), .16, .12, pale,
                                rotation=(0, math.pi / 2, 0), vertices=32))
    objects.append(cylinder("AX3_ANTENNA", (0, .08, 5.70), .045, .88, dark, vertices=16, bevel=.01))
    objects.append(sphere("AX3_ANTENNA_LIGHT", (0, .08, 6.14), (.075, .075, .075), amber, segments=24, rings=16))

    # Shoulders and arms: thick frame, recessed joint mechanics, layered pauldrons.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        shoulder = (side * 1.65, -.02, 4.45)
        elbow = (side * 1.78, -.06, 3.44)
        wrist = (side * 1.72, -.16, 2.70)
        objects.append(beam(f"AX3_{p}_CLAVICLE", (side * 1.05, 0, 4.48), shoulder, .22, dark, vertices=28))
        objects.append(sphere(f"AX3_{p}_SHOULDER_JOINT", shoulder, (.42, .42, .42), dark, segments=40, rings=24))
        objects.append(wedge(f"AX3_{p}_PAULDRON_MAIN", (side * 1.82, -.06, 4.58), (1.04, 1.14, .92), gm,
                             front_scale=(.62, .68), rotation=(0, side * math.radians(9), side * math.radians(6)), bevel=.065))
        objects.append(wedge(f"AX3_{p}_PAULDRON_FACE", (side * 1.84, -.68, 4.58), (.78, .18, .64), pale,
                             front_scale=(.64, .70), rotation=(0, side * math.radians(7), side * math.radians(6)), bevel=.04))
        objects.append(box(f"AX3_{p}_PAULDRON_SIGNAL", (side * 1.84, -.79, 4.59), (.28, .035, .07), amber, bevel=.01))
        objects.append(beam(f"AX3_{p}_UPPER_ARM_CORE", shoulder, elbow, .22, dark, vertices=32))
        objects.append(sphere(f"AX3_{p}_BICEP", (side * 1.75, -.04, 3.92), (.40, .39, .50), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_BICEP_FACE", (side * 1.75, -.45, 3.92), (.46, .13, .58), pale,
                             front_scale=(.65, .72), bevel=.03))
        objects.append(cylinder(f"AX3_{p}_ELBOW_AXLE", elbow, .26, .74, gm, rotation=(0, math.pi / 2, 0), vertices=36))
        objects.append(torus(f"AX3_{p}_ELBOW_RING", elbow, .27, .045, cyan,
                            rotation=(math.pi / 2, 0, 0), major_segments=40, minor_segments=10))
        objects.append(beam(f"AX3_{p}_FOREARM_CORE", elbow, wrist, .20, dark, vertices=28))
        objects.append(sphere(f"AX3_{p}_FOREARM", (side * 1.74, -.08, 3.03), (.40, .43, .50), gm,
                              segments=44, rings=28))
        objects.append(wedge(f"AX3_{p}_FOREARM_FACE", (side * 1.74, -.52, 3.03), (.48, .14, .58), pale,
                             front_scale=(.64, .68), bevel=.032))
        for piston in (-1, 1):
            objects.append(beam(f"AX3_{p}_ARM_PISTON_{piston}",
                                (side * (1.53 + piston * .06), -.18, 3.60),
                                (side * (1.56 + piston * .06), -.20, 3.18), .035, amber, vertices=16))
        objects.append(wedge(f"AX3_{p}_HAND", wrist, (.52, .54, .34), dark, front_scale=(.62, .62), bevel=.04))

    # Left-side integrated rail cannon: long, tapered and mechanically layered.
    gun_x = -1.78
    objects.append(wedge("AX3_RAIL_CORE", (gun_x, -.30, 1.72), (.62, .84, 3.10), dark,
                         front_scale=(.64, .82), rotation=(math.radians(4), 0, 0), bevel=.055))
    objects.append(wedge("AX3_RAIL_ARMOR", (gun_x, -.76, 1.82), (.48, .16, 2.68), gm,
                         front_scale=(.62, .78), rotation=(math.radians(4), 0, 0), bevel=.035))
    for rail in (-1, 1):
        objects.append(box(f"AX3_RAIL_TRACK_{rail}", (gun_x + rail * .22, -.82, 1.70), (.07, .08, 2.78), pale, bevel=.018))
    for coil in range(7):
        z = .72 + coil * .33
        objects.append(box(f"AX3_RAIL_COIL_{coil}", (gun_x, -.905, z), (.24, .035, .13), cyan, bevel=.01))
    objects.append(wedge("AX3_RAIL_MUZZLE", (gun_x, -.34, .22), (.68, .92, .42), gm,
                         front_scale=(.58, .55), rotation=(math.radians(4), 0, 0), bevel=.045))
    objects.append(box("AX3_RAIL_SIGHT", (gun_x, -.80, 3.28), (.24, .22, .36), amber, bevel=.028))

    # Right forearm energy shield: elongated hexagonal silhouette and emitter stack.
    shield_x = 2.15
    objects.append(wedge("AX3_SHIELD_FRAME", (shield_x, -.66, 3.06), (.82, .22, 1.88), gm,
                         front_scale=(.62, .72), rotation=(0, 0, 0), bevel=.055))
    objects.append(wedge("AX3_SHIELD_ARMOR", (shield_x, -.81, 3.06), (.64, .10, 1.56), pale,
                         front_scale=(.60, .70), bevel=.035))
    objects.append(wedge("AX3_SHIELD_ENERGY", (shield_x, -.90, 3.06), (.45, .055, 1.30), cyan,
                         front_scale=(.58, .68), bevel=.022))
    for notch in (-1, 1):
        objects.append(box(f"AX3_SHIELD_RAIL_{notch}", (shield_x + notch * .30, -.84, 3.06),
                           (.055, .08, 1.52), amber, bevel=.012))

    # Rear power plant, vent stacks and cables provide a readable back view.
    for side in (-1, 1):
        objects.append(wedge(f"AX3_BACK_REACTOR_{side}", (side * .72, .72, 4.04), (.72, .42, 1.08), gm,
                             front_scale=(.62, .72), rotation=(math.radians(-5), side * math.radians(4), 0), bevel=.045))
        objects.append(cylinder(f"AX3_BACK_THRUSTER_{side}", (side * .72, .98, 3.82), .22, .44, dark,
                                rotation=(math.pi / 2, 0, 0), vertices=36))
        objects.append(cone(f"AX3_BACK_GLOW_{side}", (side * .72, 1.23, 3.82), .16, .06, .20, cyan,
                            rotation=(math.pi / 2, 0, 0), vertices=32))
        for vent in range(4):
            objects.append(box(f"AX3_BACK_VENT_{side}_{vent}", (side * (.48 + vent * .13), .87, 4.43),
                               (.075, .18, .48), dark, rotation=(side * math.radians(-4), 0, side * math.radians(3)), bevel=.012))
        objects.append(cable(f"AX3_POWER_CABLE_{side}", [
            (side * .58, .61, 4.52), (side * 1.10, .80, 4.10), (side * 1.46, .50, 3.45)
        ], .035, amber))

    # Small-form pass: panel fasteners and edge light blocks on major masses.
    for row in range(5):
        for column in range(6):
            x = (column - 2.5) * .30
            z = 3.72 + row * .18
            if abs(x) < .32:
                continue
            objects.append(cylinder(f"AX3_CHEST_FASTENER_{row}_{column}", (x, -.925, z), .019, .035, dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.005))
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        # Secondary armor tiles break broad surfaces into maintainable modules.
        for tile in range(3):
            objects.append(wedge(f"AX3_{p}_PAULDRON_TILE_{tile}",
                                 (side * (1.57 + tile * .13), -.795, 4.42 + (tile % 2) * .16),
                                 (.11, .035, .22), pale if tile == 1 else gm,
                                 front_scale=(.62, .66), rotation=(0, 0, side * math.radians(5)), bevel=.012))
            objects.append(cylinder(f"AX3_{p}_PAULDRON_BOLT_{tile}",
                                    (side * (1.57 + tile * .13), -.825, 4.30), .016, .025, dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.004))
        for tile in range(4):
            objects.append(wedge(f"AX3_{p}_THIGH_TILE_{tile}",
                                 (side * (.64 + (tile % 2) * .20), -.585, 1.92 + (tile // 2) * .36),
                                 (.17, .038, .24), gm if tile % 2 else pale,
                                 front_scale=(.60, .64), rotation=(0, 0, side * math.radians(2)), bevel=.012))
            objects.append(wedge(f"AX3_{p}_SHIN_TILE_{tile}",
                                 (side * (.67 + (tile % 2) * .20), -.625, .79 + (tile // 2) * .30),
                                 (.15, .038, .20), gm if tile % 2 else pale,
                                 front_scale=(.58, .62), rotation=(0, 0, side * math.radians(-2)), bevel=.010))
        for channel in (-1, 1):
            objects.append(beam(f"AX3_{p}_LEG_HYDRAULIC_{channel}",
                                (side * (.53 + channel * .055), .12, .72),
                                (side * (.58 + channel * .055), .15, 1.42), .027, amber, vertices=14))
            objects.append(beam(f"AX3_{p}_ARM_HYDRAULIC_{channel}",
                                (side * (1.50 + channel * .055), .18, 3.02),
                                (side * (1.54 + channel * .055), .20, 3.72), .027, pale, vertices=14))
    for i in range(12):
        side = -1 if i % 2 == 0 else 1
        objects.append(box(f"AX3_EDGE_LIGHT_{i}", (side * rng.uniform(.42, 1.28), -.90, rng.uniform(3.64, 4.52)),
                           (.055, .025, .10), cyan if i % 3 else amber, bevel=.008))


def add_axiom_hero_v4(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    """Authored hard-surface rebuild driven by the rejected v6/v7 evidence.

    Large spheres and monolithic slabs are deliberately absent. Every major
    silhouette mass exposes a dark load-bearing frame, offset armor shells,
    constrained hinge axes, and negative space.
    """
    gm, pale, cyan, amber, dark = (mats[k] for k in ("gunmetal", "pale", "cyan", "amber", "dark"))

    def hinge(name: str, center: tuple[float, float, float], width: float, radius: float) -> None:
        objects.append(cylinder(f"{name}_AXLE", center, radius, width, dark,
                                rotation=(0, math.pi / 2, 0), vertices=24, bevel=.022))
        for side in (-1, 1):
            cap = (center[0] + side * width * .52, center[1], center[2])
            objects.append(cylinder(f"{name}_CAP_{side}", cap, radius * .78, .075, gm,
                                    rotation=(0, math.pi / 2, 0), vertices=20, bevel=.018))

    def limb_shell(name: str, center: tuple[float, float, float], dims: tuple[float, float, float], side: int) -> None:
        x, y, z = center
        dx, dy, dz = dims
        objects.append(wedge(f"{name}_FRAME", center, (dx * .62, dy * .72, dz), dark,
                             front_scale=(.66, .72), rotation=(0, side * math.radians(3), 0), bevel=.028))
        objects.append(articulated_cowl(f"{name}_PRIMARY_COWL", (x, y - dy * .39, z + dz * .02),
                                       (dx * .94, dy * .30, dz * .84), pale,
                                       lower_scale=.54, upper_scale=.72, cant=side * .18,
                                       rotation=(math.radians(3), side * math.radians(5),
                                                 side * math.radians(2)), bevel=.030))
        objects.append(articulated_cowl(f"{name}_OUTER_COWL", (x + side * dx * .39, y + dy * .02, z + dz * .04),
                                       (dx * .34, dy * .66, dz * .68), gm,
                                       lower_scale=.46, upper_scale=.64, cant=side * .30,
                                       rotation=(0, side * math.radians(10), side * math.radians(4)), bevel=.024))
        objects.append(beam(f"{name}_SERVICE_SPINE", (x - side * dx * .20, y - dy * .48, z - dz * .20),
                            (x - side * dx * .20, y - dy * .48, z + dz * .18), .018, dark, vertices=12))

    # Grounded feet and legs: separated frame, shell, hinge and actuator layers.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        x = side * .82
        stance_y = -.17 if side < 0 else .13
        objects.append(wedge(f"AX4_{p}_HEEL_FRAME", (x, stance_y + .13, .18), (.84, .70, .32), dark,
                             front_scale=(.62, .58), bevel=.035))
        objects.append(wedge(f"AX4_{p}_SOLE", (x, stance_y - .16, .13), (.84, .82, .20), dark,
                             front_scale=(.70, .62), bevel=.026))
        for toe in (-1, 1):
            objects.append(sculpted_shell(f"AX4_{p}_TOE_{toe}",
                                         (x + toe * .18, stance_y - .49, .19),
                                         (.33, .74, .27), pale if toe < 0 else gm,
                                         front_scale=(.46, .52), rotation=(0, 0, toe * math.radians(3)), bevel=.022))
        objects.append(sculpted_shell(f"AX4_{p}_FOOT_COWL", (x, stance_y - .20, .29), (.62, .50, .24), gm,
                                     front_scale=(.50, .56), bevel=.024))
        ankle = (x, stance_y, .48)
        knee = (side * .98, stance_y * .42, 1.56)
        hip = (side * .80, .02, 2.60)
        hinge(f"AX4_{p}_ANKLE", ankle, .55, .17)
        hinge(f"AX4_{p}_KNEE", knee, .72, .25)
        hinge(f"AX4_{p}_HIP", hip, .66, .26)
        objects.append(beam(f"AX4_{p}_SHIN_SPINE", ankle, knee, .12, dark, vertices=20))
        objects.append(beam(f"AX4_{p}_THIGH_SPINE", knee, hip, .14, dark, vertices=20))
        limb_shell(f"AX4_{p}_SHIN", (side * 1.00, (ankle[1] + knee[1]) * .5, 1.02), (.66, .70, .92), side)
        limb_shell(f"AX4_{p}_THIGH", (side * .89, (knee[1] + hip[1]) * .5, 2.08), (.74, .76, .86), side)
        objects.append(sculpted_shell(f"AX4_{p}_KNEE_GUARD", (side * .98, knee[1] - .37, 1.57), (.62, .22, .54), pale,
                             front_scale=(.48, .52), bevel=.028))
        for channel in (-1, 1):
            objects.append(beam(f"AX4_{p}_SHIN_ACTUATOR_{channel}",
                                (x + channel * .12, .20, .59), (side * .89 + channel * .10, .18, 1.38),
                                .025, amber if channel < 0 else pale, vertices=14))
            objects.append(beam(f"AX4_{p}_THIGH_ACTUATOR_{channel}",
                                (side * .63 + channel * .09, .18, 1.72),
                                (side * .66 + channel * .09, .16, 2.43), .029, pale, vertices=14))
        for brace in (-1, 1):
            objects.append(beam(f"AX4_{p}_ANKLE_BRACE_{brace}",
                                (x + brace * .20, stance_y + .05, .24),
                                (x + brace * .19, stance_y + .02, .53), .032, gm, vertices=14))

    # Pelvis and torso use overlapping, offset shells over a narrower frame.
    objects.append(tapered_chassis("AX4_PELVIS_FRAME", (0, .03, 2.70), (1.72, .80, .52), dark,
                                   lower_scale=.72, front_scale=.78, bevel=.040))
    for side in (-1, 1):
        objects.append(sculpted_shell(f"AX4_PELVIS_SHELL_{side}", (side * .52, -.43, 2.73), (.74, .16, .44), gm,
                             front_scale=(.54, .60), rotation=(0, side * math.radians(5), side * math.radians(4)), bevel=.030))
        objects.append(articulated_cowl(f"AX4_HIP_COWL_{side}", (side * .92, -.12, 2.54), (.42, .54, .58), pale,
                                       lower_scale=.48, upper_scale=.70, cant=side * .22,
                                       rotation=(math.radians(-5), side * math.radians(9),
                                                 side * math.radians(7)), bevel=.026))
    objects.append(wedge("AX4_PELVIS_KEEL", (0, -.53, 2.65), (.34, .17, .52), pale,
                         front_scale=(.48, .58), bevel=.022))
    objects.append(cylinder("AX4_WAIST_BEARING", (0, .01, 3.04), .50, .24, dark, vertices=48, bevel=.025))
    objects.append(torus("AX4_WAIST_TRACK", (0, .01, 3.04), .51, .055, gm, major_segments=48, minor_segments=10))
    for level, (z, width) in enumerate(((3.20, 1.12), (3.39, 1.36), (3.58, 1.62))):
        objects.append(wedge(f"AX4_AB_FRAME_{level}", (0, -.02, z), (width, .64, .24), dark,
                             front_scale=(.62, .62), bevel=.026))
        objects.append(wedge(f"AX4_AB_SHELL_{level}", (0, -.38, z), (width * .76, .10, .17), gm,
                             front_scale=(.56, .56), bevel=.016))

    # A compact central thorax plus separated shoulder yokes replaces the old
    # single deep cuboid. Side and rear views now expose negative space and load
    # paths instead of one box defining the complete upper body.
    objects.append(sculpted_shell("AX4_TORSO_CORE", (0, .02, 4.08), (1.38, .70, 1.18), dark,
                                  front_scale=(.54, .68), rotation=(0, 0, math.radians(-1.5)), bevel=.052))
    objects.append(beam("AX4_TORSO_SPINE", (0, .34, 3.56), (0, .38, 4.66), .095, gm, vertices=24))
    for side in (-1, 1):
        objects.append(sculpted_shell(f"AX4_SHOULDER_YOKE_{side}", (side * .91, .01, 4.34), (.76, .68, .76), dark,
                                     front_scale=(.48, .62), rotation=(0, side * math.radians(8), side * math.radians(5)), bevel=.040))
        objects.append(beam(f"AX4_YOKE_BRACE_{side}", (side * .42, .18, 4.30),
                            (side * 1.30, .16, 4.43), .085, gm, vertices=20))
        objects.append(articulated_cowl(f"AX4_CHEST_LOAD_COWL_{side}", (side * .55, -.28, 4.07),
                                       (1.02, .62, 1.10), gm, lower_scale=.58, upper_scale=.84,
                                       cant=side * .20,
                                       rotation=(math.radians(3), side * math.radians(11),
                                                 side * math.radians(5)), bevel=.046))
        objects.append(articulated_cowl(f"AX4_CHEST_PRIMARY_COWL_{side}", (side * .62, -.64, 4.08),
                                       (.82, .24, .82), pale, lower_scale=.50, upper_scale=.76,
                                       cant=side * .26,
                                       rotation=(math.radians(3), side * math.radians(13),
                                                 side * math.radians(5)), bevel=.032))
        objects.append(sculpted_shell(f"AX4_CHEST_INNER_{side}", (side * .27, -.54, 4.03), (.38, .30, .94), dark,
                             front_scale=(.42, .60), rotation=(math.radians(2), side * math.radians(16), side * math.radians(3)), bevel=.026))
        objects.append(wedge(f"AX4_COLLAR_{side}", (side * .61, -.10, 4.75), (.94, .58, .28), gm,
                             front_scale=(.54, .54), rotation=(0, side * math.radians(5), side * math.radians(6)), bevel=.032))
        objects.append(wedge(f"AX4_FLANK_SHELL_{side}", (side * 1.18, .01, 3.98), (.28, .62, .78), dark,
                             front_scale=(.45, .60), rotation=(0, side * math.radians(8), 0), bevel=.030))
        for vent in range(4):
            objects.append(box(f"AX4_FLANK_VENT_{side}_{vent}", (side * 1.24, -.42, 3.72 + vent * .18),
                               (.10, .035, .08), amber if vent == 0 else dark, bevel=.007))
    for side in (-1, 1):
        objects.append(beam(f"AX4_REACTOR_CAGE_UPPER_{side}", (side * .13, -.78, 4.34),
                            (side * .46, -.68, 4.55), .042, gm, vertices=16))
        objects.append(beam(f"AX4_REACTOR_CAGE_LOWER_{side}", (side * .13, -.78, 3.72),
                            (side * .48, -.68, 3.57), .042, gm, vertices=16))
    objects.append(sculpted_shell("AX4_REACTOR_FRAME", (0, -.72, 4.03), (.62, .30, .94), gm,
                                  front_scale=(.44, .58), bevel=.028))
    objects.append(sculpted_shell("AX4_REACTOR_CORE", (0, -.91, 4.03), (.34, .10, .64), cyan,
                                  front_scale=(.38, .50), bevel=.016))

    # Compact sensor head: one guarded visor avoids the v7 googly-eye read.
    objects.append(cylinder("AX4_NECK", (0, .00, 4.93), .25, .28, dark, vertices=28, bevel=.02))
    objects.append(sculpted_shell("AX4_HEAD_FRAME", (0, -.02, 5.20), (.70, .62, .42), dark,
                         front_scale=(.54, .58), bevel=.035))
    objects.append(sculpted_shell("AX4_HEAD_COWL", (0, -.16, 5.30), (.76, .42, .24), gm,
                         front_scale=(.50, .54), bevel=.025))
    objects.append(box("AX4_VISOR", (0, -.37, 5.18), (.42, .045, .075), cyan, bevel=.015))
    objects.append(box("AX4_VISOR_BROW", (0, -.40, 5.31), (.58, .055, .055), pale, bevel=.010))
    objects.append(cylinder("AX4_COMMS_MAST", (.23, .04, 5.67), .026, .74, dark, vertices=12, bevel=.006))
    objects.append(box("AX4_MAST_TIP", (.23, .04, 6.04), (.08, .08, .12), amber, bevel=.012))

    # Arms and layered shoulder assemblies with visible gaps between plates.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        shoulder, elbow, wrist = (side * 1.65, .00, 4.40), (side * 1.82, -.02, 3.48), (side * 1.78, -.10, 2.78)
        objects.append(beam(f"AX4_{p}_CLAVICLE", (side * 1.00, .02, 4.42), shoulder, .15, dark, vertices=20))
        hinge(f"AX4_{p}_SHOULDER", shoulder, .58, .25)
        hinge(f"AX4_{p}_ELBOW", elbow, .58, .21)
        objects.append(articulated_cowl(f"AX4_{p}_SHOULDER_COWL", (side * 1.66, -.08, 4.43),
                                       (.88, .78, .76), gm, lower_scale=.54, upper_scale=.82,
                                       cant=side * .28,
                                       rotation=(0, side * math.radians(10), side * math.radians(7)),
                                       bevel=.036))
        for layer, (ox, oy, oz, sx) in enumerate(((.10, .00, .12, 1.0), (.24, .05, .02, .78), (.36, .10, -.08, .58))):
            objects.append(sculpted_shell(f"AX4_{p}_PAULDRON_{layer}",
                                 (side * (1.52 + ox), -.22 + oy, 4.48 + oz),
                                 (.72 * sx, .70, .34), pale if layer == 1 else gm,
                                 front_scale=(.44, .54), rotation=(0, side * math.radians(8 + layer * 3), side * math.radians(6)), bevel=.026))
        objects.append(beam(f"AX4_{p}_SHOULDER_ACTUATOR_TOP", (side * 1.08, .12, 4.60),
                            (side * 1.55, .18, 4.56), .040, pale, vertices=16))
        objects.append(beam(f"AX4_{p}_SHOULDER_ACTUATOR_LOW", (side * 1.12, .15, 4.29),
                            (side * 1.50, .20, 4.20), .034, amber, vertices=14))
        objects.append(cable(f"AX4_{p}_SHOULDER_CABLE", [
            (side * 1.06, .30, 4.50), (side * 1.36, .46, 4.36), (side * 1.56, .31, 4.06)
        ], .025, cyan))
        objects.append(beam(f"AX4_{p}_UPPER_ARM_SPINE", shoulder, elbow, .12, dark, vertices=20))
        objects.append(beam(f"AX4_{p}_FOREARM_SPINE", elbow, wrist, .11, dark, vertices=20))
        limb_shell(f"AX4_{p}_BICEP", (side * 1.74, -.01, 3.93), (.72, .70, .84), side)
        limb_shell(f"AX4_{p}_FOREARM", (side * 1.80, -.06, 3.08), (.72, .72, .84), side)
        objects.append(sculpted_shell(f"AX4_{p}_PALM", wrist, (.52, .46, .38), dark,
                                     front_scale=(.48, .56), bevel=.026))
        for finger in range(3):
            fx = side * (1.65 + finger * .09)
            objects.append(beam(f"AX4_{p}_FINGER_{finger}", (fx, -.21, 2.70),
                                (fx + side * .025, -.27, 2.43 - finger * .025),
                                .035, pale if finger == 1 else gm, vertices=14))

    # Shoulder-mounted railgun: frame, separated rails, barrel and open coil cage.
    gx, gz = -1.52, 4.58
    objects.append(wedge("AX4_RAIL_FRAME", (gx, -.43, gz), (.58, 1.72, .50), dark,
                         front_scale=(.50, .58), rotation=(0, 0, math.radians(-2)), bevel=.038))
    for rail in (-1, 1):
        objects.append(box(f"AX4_RAIL_LONGERON_{rail}", (gx + rail * .25, -.96, gz),
                           (.075, 1.82, .11), pale, bevel=.018))
    objects.append(wedge("AX4_RAIL_TOP_SHELL", (gx, -.43, gz + .34), (.50, 1.44, .22), gm,
                         front_scale=(.42, .52), bevel=.025))
    objects.append(cylinder("AX4_RAIL_RECOIL_TUBE", (gx, .54, gz), .14, .68, dark,
                            rotation=(math.pi / 2, 0, 0), vertices=24, bevel=.018))
    for side in (-1, 1):
        objects.append(beam(f"AX4_RAIL_RECOIL_PISTON_{side}", (gx + side * .19, .56, gz - .10),
                            (gx + side * .19, .08, gz - .10), .030, amber, vertices=14))
    objects.append(cylinder("AX4_RAIL_BARREL", (gx, -1.30, gz), .105, 1.42, gm,
                            rotation=(math.pi / 2, 0, 0), vertices=28, bevel=.018))
    for cage in range(5):
        y = -.32 - cage * .24
        # Angular field cage around the barrel. The rejected v8 luminous hoops
        # read as arcade geometry; these separated structural ribs retain gaps.
        for side in (-1, 1):
            objects.append(box(f"AX4_RAIL_CAGE_SIDE_{cage}_{side}", (gx + side * .205, y, gz),
                               (.045, .055, .34), pale if cage % 2 else gm, bevel=.010))
        objects.append(box(f"AX4_RAIL_CAGE_TOP_{cage}", (gx, y, gz + .17),
                           (.44, .055, .045), gm, bevel=.010))
        objects.append(box(f"AX4_RAIL_CAGE_BOTTOM_{cage}", (gx, y, gz - .17),
                           (.44, .055, .045), dark, bevel=.010))
        objects.append(box(f"AX4_RAIL_FIELD_CORE_{cage}", (gx, y - .035, gz),
                           (.085, .045, .085), cyan, bevel=.014))
    objects.append(cone("AX4_RAIL_MUZZLE_SHROUD", (gx, -2.05, gz), .24, .19, .28, gm,
                        rotation=(math.pi / 2, 0, 0), vertices=12, bevel=.020))
    objects.append(cylinder("AX4_RAIL_MUZZLE_BORE", (gx, -2.20, gz), .115, .12, dark,
                            rotation=(math.pi / 2, 0, 0), vertices=20, bevel=.012))
    for side in (-1, 1):
        objects.append(wedge(f"AX4_RAIL_FLASH_HIDER_{side}", (gx + side * .19, -2.17, gz),
                             (.08, .30, .22), pale, front_scale=(.42, .48), bevel=.010))
    for side in (-1, 1):
        objects.append(beam(f"AX4_RAIL_MOUNT_{side}", (side * .10 + gx, .15, gz - .08),
                            (side * .12 - .85, .18, 4.40), .055, dark, vertices=16))

    # Forearm shield with a true frame and negative space around the energy lens.
    sx, sy, sz = 2.05, -.53, 3.23
    top, bottom = sz + .82, sz - .82
    points = [(sx, sy, top), (sx + .42, sy, sz + .52), (sx + .42, sy, sz - .52),
              (sx, sy, bottom), (sx - .42, sy, sz - .52), (sx - .42, sy, sz + .52)]
    for i in range(len(points)):
        objects.append(beam(f"AX4_SHIELD_FRAME_{i}", points[i], points[(i + 1) % len(points)], .055, gm, vertices=16))
    objects.append(wedge("AX4_SHIELD_BACKING", (sx, sy - .02, sz), (.58, .045, 1.18), dark,
                         front_scale=(.48, .62), bevel=.018))
    for cell in range(3):
        objects.append(sculpted_shell(f"AX4_SHIELD_CELL_{cell}",
                                     (sx, sy - .065, sz - .38 + cell * .38),
                                     (.42, .035, .29), cyan,
                                     front_scale=(.50, .55), bevel=.012))
    for z in (sz - .58, sz + .58):
        objects.append(box(f"AX4_SHIELD_EMITTER_{z}", (sx, sy - .08, z), (.22, .08, .10), amber, bevel=.012))
    objects.append(beam("AX4_SHIELD_MOUNT", (1.57, -.04, 3.13), (sx - .30, sy + .10, sz), .09, dark, vertices=20))

    # Rear power plant is split around a visible spine and leaves air between
    # the thorax, service modules and shoulder yokes.
    objects.append(sculpted_shell("AX4_BACK_REACTOR_CAGE", (0, .48, 4.02), (.46, .28, .82), dark,
                                  front_scale=(.48, .62), rotation=(math.pi, 0, 0), bevel=.026))
    objects.append(beam("AX4_BACK_REACTOR_SPINE", (0, .64, 3.62), (0, .68, 4.48), .070, pale, vertices=18))
    for side in (-1, 1):
        objects.append(wedge(f"AX4_BACK_FRAME_{side}", (side * .69, .52, 4.10), (.48, .28, .76), dark,
                             front_scale=(.48, .60), bevel=.030))
        objects.append(sculpted_shell(f"AX4_BACK_SHELL_{side}", (side * .69, .72, 4.13), (.44, .22, .64), pale,
                                      front_scale=(.40, .52), rotation=(math.pi, side * math.radians(7), 0), bevel=.026))
        objects.append(cylinder(f"AX4_THRUSTER_{side}", (side * .69, .87, 3.91), .15, .26, dark,
                                rotation=(math.pi / 2, 0, 0), vertices=24, bevel=.018))
        objects.append(torus(f"AX4_THRUSTER_GLOW_{side}", (side * .69, 1.01, 3.91), .13, .026, cyan,
                             rotation=(math.pi / 2, 0, 0), major_segments=24, minor_segments=8))
        for vent in range(4):
            objects.append(box(f"AX4_BACK_VENT_{side}_{vent}", (side * (.43 + vent * .12), .91, 4.48),
                               (.07, .14, .34), pale if vent == 0 else dark, bevel=.008))
        objects.append(cable(f"AX4_POWER_CABLE_{side}", [(side * .42, .55, 4.43),
                                                          (side * .72, .72, 4.16),
                                                          (side * .88, .62, 3.88)], .018, dark))
        for terminal, position in enumerate(((side * .42, .55, 4.43), (side * .88, .62, 3.88))):
            objects.append(cylinder(f"AX4_POWER_TERMINAL_{side}_{terminal}", position, .065, .08, gm,
                                    rotation=(math.pi / 2, 0, 0), vertices=16, bevel=.010))
        for fin in range(5):
            objects.append(box(f"AX4_HEAT_EXCHANGER_{side}_{fin}",
                               (side * (.39 + fin * .115), 1.00, 4.17 + (fin % 2) * .06),
                               (.055, .18, .52), pale if fin == 2 else gm,
                               rotation=(side * math.radians(-3), 0, side * math.radians(2)), bevel=.007))
        objects.append(cable(f"AX4_COOLANT_LOOP_{side}", [
            (side * .38, .78, 4.49), (side * .69, .96, 4.40),
            (side * .78, .94, 4.08), (side * .58, .78, 3.91),
        ], .012, cyan))
        for terminal, position in enumerate(((side * .38, .78, 4.49), (side * .58, .78, 3.91))):
            objects.append(cylinder(f"AX4_COOLANT_TERMINAL_{side}_{terminal}", position, .038, .055, gm,
                                    rotation=(math.pi / 2, 0, 0), vertices=14, bevel=.007))

    # Small-form cadence along chest and limbs.
    for row in range(4):
        for side in (-1, 1):
            objects.append(cylinder(f"AX4_CHEST_FASTENER_{side}_{row}",
                                    (side * (.48 + row * .12), -.765, 3.82 + row * .16),
                                    .015, .025, dark, rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.004))
    for i in range(10):
        side = -1 if i % 2 == 0 else 1
        objects.append(box(f"AX4_EDGE_MARK_{i}", (side * rng.uniform(.50, 1.24), -.77, rng.uniform(3.72, 4.62)),
                           (.045, .022, .085), cyan if i % 3 else amber, bevel=.006))

    # Axiom split-chevron faction glyph, built as geometry so it survives LOD0
    # export and does not depend on a one-view decal projection.
    glyph_y = -.825
    for side in (-1, 1):
        objects.append(beam(f"AX4_GLYPH_UP_{side}", (side * .10, glyph_y, 4.13),
                            (side * .25, glyph_y, 4.34), .018, cyan, vertices=10))
        objects.append(beam(f"AX4_GLYPH_DOWN_{side}", (side * .10, glyph_y, 4.13),
                            (side * .25, glyph_y, 3.92), .018, pale, vertices=10))

    # Sparse secondary hardware stays subordinate to the articulated cowls.
    # The rejected v24 grid of repeated tiles is intentionally absent.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        objects.append(articulated_cowl(f"AX4_{p}_CHEST_ACCESS_COWL",
                                       (side * .72, -.765, 3.92), (.30, .055, .36), gm,
                                       lower_scale=.50, upper_scale=.68, cant=side * .20,
                                       rotation=(0, 0, side * math.radians(5)), bevel=.009))
        objects.append(cylinder(f"AX4_{p}_CHEST_ACCESS_BOLT", (side * .72, -.805, 3.78),
                                .014, .022, amber, rotation=(math.pi / 2, 0, 0),
                                vertices=10, bevel=.003))
        for section, x0, z0 in (("THIGH", .73, 2.04), ("SHIN", .84, 1.00),
                                ("BICEP", 1.74, 3.92), ("FOREARM", 1.80, 3.08)):
            objects.append(beam(f"AX4_{p}_{section}_COWL_SEAM",
                                (side * x0, -.43, z0 - .13),
                                (side * (x0 + .025), -.43, z0 + .14),
                                .012, dark, vertices=10))
            objects.append(cylinder(f"AX4_{p}_{section}_SERVICE_PORT",
                                    (side * (x0 - .10), -.445, z0), .011, .018,
                                    pale if section in {"THIGH", "FOREARM"} else amber,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.003))
        objects.append(beam(f"AX4_{p}_PAULDRON_EDGE",
                            (side * 1.48, -.62, 4.34), (side * 1.85, -.62, 4.61),
                            .018, pale, vertices=12))

    for side in (-1, 1):
        for row in range(4):
            objects.append(box(f"AX4_CHEST_TRIM_{side}_{row}",
                               (side * (.31 + row * .18), -.775, 4.42 - row * .12),
                               (.13, .022, .022), pale if row < 2 else dark,
                               rotation=(0, 0, side * math.radians(4)), bevel=.004))
    for panel in range(5):
        y = -.42 - panel * .38
        objects.append(wedge(f"AX4_RAIL_SIDE_PANEL_{panel}", (gx - .31, y, gz + .02),
                             (.11, .24, .28), gm if panel % 2 else pale,
                             front_scale=(.42, .50), rotation=(0, 0, math.radians(-2)), bevel=.012))
        objects.append(cylinder(f"AX4_RAIL_PANEL_BOLT_{panel}", (gx - .375, y - .08, gz + .02),
                                .012, .025, amber, rotation=(0, math.pi / 2, 0), vertices=10, bevel=.003))
    for index, z in enumerate((3.78, 3.96, 4.14, 4.32)):
        objects.append(box(f"AX4_CENTER_VENT_{index}", (0, -.795, z), (.19, .025, .055), dark, bevel=.007))
    for side in (-1, 1):
        for index in range(3):
            objects.append(cylinder(f"AX4_TORSO_SERVICE_PORT_{side}_{index}",
                                    (side * (.34 + index * .11), -.812, 3.72),
                                    .014, .022, amber if index == 0 else dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.003))


def add_mir_hero_v3(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    """Sacred-biotech guardian rebuilt from the rejected ellipsoid prototype."""
    ivory, brass, rose, cyan, magenta, dark = (mats[k] for k in ("ivory", "brass", "rose", "cyan", "magenta", "dark"))

    def joint(name: str, center: tuple[float, float, float], width: float, radius: float) -> None:
        objects.append(cylinder(f"{name}_BEARING", center, radius * .72, width * .72, dark,
                                rotation=(0, math.pi / 2, 0), vertices=32, bevel=.022))
        for side in (-1, 1):
            objects.append(cylinder(f"{name}_ROSE_CAP_{side}",
                                    (center[0] + side * width * .37, center[1], center[2]),
                                    radius * .50, .034, rose,
                                    rotation=(0, math.pi / 2, 0), vertices=28, bevel=.018))
        objects.append(torus(f"{name}_RESONANCE_RING", center, radius * .58, .018, brass,
                            rotation=(math.pi / 2, 0, 0), major_segments=28, minor_segments=8))

    def limb_petals(name: str, center: tuple[float, float, float], side: int,
                    length: float, width: float) -> None:
        x, y, z = center
        objects.append(beam(f"{name}_TENDON", (x, y + .10, z - length * .48),
                            (x, y + .06, z + length * .48), width * .20, dark, vertices=24))
        objects.append(sacred_blade_plate(f"{name}_LOAD_SHELL", (x, y + .03, z),
                                          (width * .84, .42, length * .96), dark,
                                          rotation=(0, side * math.radians(6), side * math.radians(3)),
                                          sweep=side * .12, bevel=.026))
        objects.append(sacred_blade_plate(f"{name}_FRONT_PETAL", (x, y - .18, z),
                                          (width, .22, length * 1.08), ivory,
                                          rotation=(math.radians(3), side * math.radians(5), side * math.radians(4)),
                                          sweep=side * .18, bevel=.022))
        objects.append(sacred_blade_plate(f"{name}_OUTER_PETAL", (x + side * width * .30, y + .00, z + .06),
                                          (width * .46, .32, length * .88), rose,
                                          rotation=(0, side * math.radians(17), side * math.radians(8)),
                                          sweep=side * .32, bevel=.018))
        objects.append(sacred_blade_plate(f"{name}_INNER_PETAL", (x - side * width * .22, y - .12, z - .08),
                                          (width * .34, .10, length * .76), brass,
                                          rotation=(0, side * math.radians(-8), side * math.radians(-4)),
                                          sweep=-side * .18, bevel=.014))
        objects.append(box(f"{name}_LIGHT", (x, y - .275, z - length * .12),
                           (.032, .018, length * .16), cyan, bevel=.006))
        for mark in (-1, 0, 1):
            objects.append(box(f"{name}_EDGE_GUARD_{mark}",
                               (x + side * width * .13, y - .288, z + mark * length * .22),
                               (.020, .014, length * .13), brass if mark == 0 else dark,
                               rotation=(0, side * math.radians(4), side * math.radians(5)), bevel=.003))
            objects.append(cylinder(f"{name}_FASTENER_{mark}",
                                    (x - side * width * .16, y - .295, z + mark * length * .22),
                                    .009, .012, dark, rotation=(math.pi / 2, 0, 0),
                                    vertices=10, bevel=.002))

    # Slender planted legs with overlapping petals and exposed tendon paths.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        stance_y = -.24 if side < 0 else .14
        ankle = (side * .64, stance_y, .42)
        knee = (side * .72, stance_y * .35, 1.44)
        hip = (side * .52, .03, 2.53)
        # Compact armored hoof: one load-bearing body encloses the ankle root;
        # short split toe caps and a braced heel articulate without rail forms.
        objects.append(sculpted_shell(f"M2_{p}_HOOF_BODY", (side * .64, stance_y - .10, .20),
                                      (.52, .56, .30), dark, front_scale=(.50, .54), bevel=.024))
        objects.append(sacred_blade_plate(f"M2_{p}_HOOF_INSTEP", (side * .64, stance_y - .22, .30),
                                          (.38, .18, .42), ivory,
                                          rotation=(math.radians(18), side * math.radians(5), 0),
                                          sweep=side * .10, bevel=.016))
        for toe in (-1, 1):
            toe_x = side * .64 + toe * .105
            objects.append(sculpted_shell(f"M2_{p}_TOE_CAP_{toe}",
                                          (toe_x, stance_y - .39, .13),
                                          (.19, .34, .16), ivory if toe < 0 else rose,
                                          front_scale=(.42, .46),
                                          rotation=(math.radians(5), 0, toe * math.radians(4)),
                                          bevel=.013))
            objects.append(beam(f"M2_{p}_TOE_BRACE_{toe}",
                                (toe_x, stance_y - .14, .18),
                                (toe_x, stance_y - .34, .14), .018, brass, vertices=12))
        objects.append(sculpted_shell(f"M2_{p}_HEEL_BODY", (side * .64, stance_y + .16, .16),
                                      (.36, .34, .24), dark, front_scale=(.56, .52), bevel=.017))
        objects.append(sacred_blade_plate(f"M2_{p}_HEEL_COWL", (side * .64, stance_y + .27, .25),
                                          (.24, .13, .30), rose,
                                          rotation=(math.radians(-28), 0, 0),
                                          sweep=-side * .08, bevel=.012))
        joint(f"M2_{p}_ANKLE", ankle, .46, .15)
        joint(f"M2_{p}_KNEE", knee, .58, .23)
        joint(f"M2_{p}_HIP", hip, .64, .25)
        limb_petals(f"M2_{p}_SHIN", (side * .68, (ankle[1] + knee[1]) * .5, .92), side, .96, .46)
        limb_petals(f"M2_{p}_THIGH", (side * .62, (knee[1] + hip[1]) * .5, 1.98), side, 1.02, .56)
        for channel in (-1, 1):
            objects.append(beam(f"M2_{p}_LEG_ACTUATOR_{channel}",
                                (side * (.50 + channel * .07), .16, .64),
                                (side * (.55 + channel * .07), .14, 1.30), .024,
                                brass if channel < 0 else rose, vertices=14))

    # Pelvis, narrow waist and layered chest altar.
    objects.append(sculpted_shell("M2_PELVIS_CORE", (0, .03, 2.58), (.70, .56, .58), dark,
                                  front_scale=(.42, .58), bevel=.026))
    for side in (-1, 1):
        objects.append(beam(f"M2_PELVIS_YOKE_{side}", (0, .02, 2.64),
                            (side * .61, .01, 2.60), .070, dark, vertices=20))
        objects.append(torus(f"M2_PELVIS_YOKE_RING_{side}", (side * .47, .01, 2.60),
                             .14, .024, brass, rotation=(math.pi / 2, 0, 0),
                             major_segments=28, minor_segments=8))
    for side in (-1, 1):
        objects.append(sacred_blade_plate(f"M2_HIP_PETAL_{side}", (side * .52, -.24, 2.59), (.66, .14, .88), ivory,
                                          rotation=(math.radians(-4), side * math.radians(14), side * math.radians(10)),
                                          sweep=side * .28, bevel=.020))
        objects.append(sacred_blade_plate(f"M2_HIP_INLAY_{side}", (side * .47, -.34, 2.53), (.26, .055, .54), rose,
                                          rotation=(0, side * math.radians(8), side * math.radians(8)),
                                          sweep=side * .18, bevel=.011))
        objects.append(sacred_blade_plate(f"M2_REAR_HIP_PETAL_{side}", (side * .45, .31, 2.58), (.60, .24, .84), ivory,
                                          rotation=(math.pi, side * math.radians(11), side * math.radians(8)),
                                          sweep=-side * .22, bevel=.017))
    objects.append(sacred_blade_plate("M2_PELVIS_KEEL", (0, -.34, 2.39), (.42, .12, .88), ivory,
                                      rotation=(0, 0, math.pi), sweep=.05, bevel=.018))
    objects.append(cylinder("M2_WAIST_CORE", (0, .02, 2.95), .42, .28, dark, vertices=48, bevel=.025))
    objects.append(torus("M2_WAIST_HALO", (0, .02, 2.95), .42, .038, brass, major_segments=48, minor_segments=10))
    objects.append(beam("M2_TORSO_CORE_SPINE", (0, .08, 3.16), (0, .08, 4.48), .105, dark, vertices=28))
    for side in (-1, 1):
        objects.append(sacred_blade_plate(f"M2_TORSO_LOAD_SHELL_{side}", (side * .33, .02, 3.82),
                                          (.64, .62, 1.42), dark,
                                          rotation=(0, side * math.radians(12), side * math.radians(4)),
                                          sweep=side * .18, bevel=.034))
        objects.append(sacred_blade_plate(f"M2_TORSO_ROOT_ARMOR_{side}", (side * .38, -.31, 3.86),
                                          (.50, .24, 1.18), ivory,
                                          rotation=(math.radians(2), side * math.radians(15), side * math.radians(7)),
                                          sweep=side * .24, bevel=.022))
    for station, z in enumerate((3.34, 3.70, 4.06, 4.38)):
        objects.append(torus(f"M2_TORSO_SPINE_RING_{station}", (0, .08, z),
                             .16 - station * .012, .022, brass,
                             rotation=(math.pi / 2, 0, 0), major_segments=28, minor_segments=8))
    for side in (-1, 1):
        objects.append(beam(f"M2_TORSO_SIDE_TENDON_{side}", (side * .18, .15, 3.20),
                            (side * .38, .14, 4.35), .048, dark, vertices=18))
    for side in (-1, 1):
        objects.append(beam(f"M2_TORSO_YOKE_{side}", (0, .05, 3.18),
                            (side * .83, .04, 4.34), .072, dark, vertices=20))
        objects.append(beam(f"M2_TORSO_YOKE_INLAY_{side}", (side * .06, -.08, 3.24),
                            (side * .75, -.09, 4.28), .026, brass, vertices=16))
        # Volumetric rib arcs run from the front sternum around the side to the
        # rear spine. Major petals attach to the outer sockets below instead of
        # floating as parallel plates around a tubular centerline.
        for rib, z in enumerate((3.38, 3.68, 3.98, 4.28)):
            reach = .48 + rib * .07
            objects.append(cable(f"M2_RIB_CAGE_{side}_{rib}", [
                (side * .08, -.25, z),
                (side * reach, -.14, z + .09),
                (side * (reach + .10), .16, z + .06),
                (side * .26, .42, z - .02),
            ], .050 - rib * .004, dark if rib % 2 else brass))
            objects.append(cylinder(f"M2_RIB_SOCKET_{side}_{rib}",
                                    (side * (reach + .09), -.02, z + .07), .070, .12,
                                    brass, rotation=(math.pi / 2, 0, 0), vertices=18, bevel=.010))
    # A visible load-bearing spine and rib roots keep the petals from reading as
    # stickers on a box. The collar blades carry the shoulder mass instead.
    objects.append(beam("M2_FRONT_SPINE", (0, -.28, 3.10), (0, -.31, 4.52), .075, brass, vertices=24))
    for side in (-1, 1):
        objects.append(sacred_blade_plate(f"M2_COLLAR_BLADE_{side}",
                                          (side * .54, -.18, 4.27), (.68, .28, .94), ivory,
                                          rotation=(math.radians(-3), side * math.radians(19), side * math.radians(19)),
                                          sweep=side * .34, bevel=.024))
        objects.append(sacred_blade_plate(f"M2_COLLAR_INLAY_{side}",
                                          (side * .46, -.36, 4.17), (.30, .09, .66), rose,
                                          rotation=(0, side * math.radians(15), side * math.radians(18)),
                                          sweep=side * .24, bevel=.014))
    for layer, z in enumerate((3.12, 3.35, 3.58)):
        objects.append(sacred_blade_plate(f"M2_ABDOMEN_BLADE_{layer}", (0, -.36 - layer * .02, z),
                                          (.58 + layer * .08, .12, .64), ivory if layer != 1 else rose,
                                          rotation=(0, 0, math.pi if layer == 0 else 0),
                                          sweep=(-.10 + layer * .10), bevel=.016))

    # Six overlapping chest petals define the sacred-machine silhouette.
    chest_specs = [
        (-.50, 4.10, -.20, .72, 1.12, .31), (.50, 4.10, .20, .72, 1.12, .31),
        (-.29, 3.72, -.12, .58, .96, .26), (.29, 3.72, .12, .58, .96, .26),
        (-.16, 4.42, -.15, .44, .82, .22), (.16, 4.42, .15, .44, .82, .22),
    ]
    for index, (x, z, tilt, width, height, depth) in enumerate(chest_specs):
        objects.append(sacred_blade_plate(f"M2_CHEST_PETAL_{index}", (x, -.27 - index * .010, z),
                                          (width, depth, height), ivory if index < 4 else rose,
                                          rotation=(math.radians(2), tilt, math.radians(x * 10)),
                                          sweep=(-.26 if x < 0 else .26), bevel=.024))
    objects.append(sacred_blade_plate("M2_STERNUM_FRAME", (0, -.48, 3.90), (.42, .12, 1.22), brass,
                                      sweep=.08, bevel=.018))
    objects.append(sacred_blade_plate("M2_STERNUM_CORE", (0, -.57, 3.96), (.20, .045, .60), magenta,
                                      sweep=.05, bevel=.010))
    # Four closed plates overlap from collar to waist. Their concave upper edge
    # and pointed lower keel create one descending V-shell torso instead of
    # disconnected petals orbiting an exposed tubular centerline.
    v_shells = (
        ("UPPER", 4.26, .92, .70, .17, ivory, .34),
        ("MID_UPPER", 3.94, .80, .66, .15, rose, .31),
        ("MID_LOWER", 3.64, .68, .60, .14, ivory, .28),
        ("LOWER", 3.36, .56, .54, .13, ivory, .24),
    )
    for layer, (label, z, width, height, depth, material, notch) in enumerate(v_shells):
        objects.append(descending_v_shell(f"M2_TORSO_V_SHELL_{label}",
                                          (0, -.61 - layer * .018, z),
                                          (width, depth, height), material,
                                          notch=notch,
                                          rotation=(math.radians(2 - layer), 0, 0),
                                          bevel=.018))
        objects.append(box(f"M2_TORSO_V_INLAY_{label}",
                           (0, -.715 - layer * .018, z - height * .18),
                           (.035, .018, height * .20),
                           magenta if layer == 1 else brass, bevel=.005))
    for side in (-1, 1):
        for rib in range(4):
            z = 3.48 + rib * .24
            objects.append(beam(f"M2_RIB_{side}_{rib}", (side * .08, -.25, z),
                                (side * (.54 + rib * .07), -.18, z + .12), .028, brass, vertices=16))
    # Terminated seams and service hardware make the armor manufactured rather
    # than relying on glow strips for tertiary detail.
    for side in (-1, 1):
        for row in range(5):
            x = side * (.24 + row * .075)
            z = 3.56 + row * .17
            objects.append(box(f"M2_CHEST_EDGE_GUARD_{side}_{row}", (x, -.475, z),
                               (.025, .018, .13), brass if row % 2 else dark,
                               rotation=(0, side * math.radians(5), side * math.radians(7)), bevel=.004))
            objects.append(cylinder(f"M2_CHEST_RIVET_{side}_{row}", (x + side * .08, -.49, z - .07),
                                    .010, .014, dark, rotation=(math.pi / 2, 0, 0),
                                    vertices=10, bevel=.002))

    # Rear sanctuary engine: layered petals over a visible spine and core.
    objects.append(beam("M2_BACK_SPINE", (0, .46, 3.18), (0, .50, 4.52), .11, dark, vertices=24))
    objects.append(petal_plate("M2_BACK_CORE_FRAME", (0, .56, 3.92), (.58, .16, 1.06), brass,
                               rotation=(math.pi, 0, 0), bevel=.026))
    objects.append(petal_plate("M2_BACK_CORE", (0, .66, 3.94), (.28, .07, .58), magenta,
                               rotation=(math.pi, 0, 0), bevel=.016))
    for side in (-1, 1):
        for layer in range(3):
            x = side * (.34 + layer * .20)
            z = 3.58 + layer * .28
            objects.append(sacred_blade_plate(f"M2_BACK_PETAL_{side}_{layer}", (x, .43 + layer * .018, z),
                                              (.54 - layer * .04, .13, .94 - layer * .05),
                                              ivory if layer != 1 else rose,
                                              rotation=(math.pi, side * math.radians(9 + layer * 5), side * math.radians(8)),
                                              sweep=-side * .30, bevel=.019))
            objects.append(cylinder(f"M2_BACK_FASTENER_{side}_{layer}",
                                    (x, .665, z - .14), .014, .022, dark,
                                    rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.003))
        objects.append(cable(f"M2_BACK_CONDUIT_{side}", [
            (side * .18, .68, 4.38), (side * .55, .75, 4.18),
            (side * .76, .72, 3.76), (side * .48, .66, 3.36),
        ], .020, cyan if side < 0 else magenta))

    # Elongated head and articulated crown, no oval mascot shell.
    objects.append(cylinder("M2_NECK", (0, .02, 4.71), .16, .34, dark, vertices=32, bevel=.018))
    objects.append(sculpted_shell("M2_HEAD_FRAME", (0, -.01, 5.04), (.44, .40, .70), dark,
                                  front_scale=(.34, .52), bevel=.026))
    objects.append(sacred_blade_plate("M2_FACE_PLATE", (0, -.27, 5.04), (.38, .16, .80), ivory,
                                      rotation=(math.radians(2), 0, 0), sweep=.06, bevel=.018))
    objects.append(sacred_blade_plate("M2_FACE_INLAY", (0, -.36, 5.04), (.14, .040, .48), magenta,
                                      sweep=.04, bevel=.009))
    objects.append(box("M2_FACE_SLIT", (0, -.39, 5.16), (.035, .018, .24), cyan, bevel=.006))
    for crown in range(7):
        angle = math.radians(-72 + crown * 24)
        x = math.sin(angle) * .40
        z = 5.31 + math.cos(angle) * .36
        objects.append(sacred_blade_plate(f"M2_CROWN_PETAL_{crown}", (x, .01, z), (.15, .13, .56),
                                          rose if crown % 2 else ivory,
                                          rotation=(0, -angle, angle * .22), sweep=math.sin(angle) * .32,
                                          bevel=.012))
    for side in (-1, 1):
        objects.append(sacred_blade_plate(f"M2_TEMPLE_COWL_{side}", (side * .27, -.01, 5.08), (.26, .26, .72), ivory,
                                          rotation=(0, side * math.radians(24), side * math.radians(9)),
                                          sweep=side * .32, bevel=.016))
        objects.append(box(f"M2_TEMPLE_OPTIC_{side}", (side * .40, -.22, 5.12), (.045, .035, .14), cyan, bevel=.008))
    objects.append(sacred_blade_plate("M2_REAR_HEAD_COWL", (0, .22, 5.06), (.38, .13, .78), rose,
                                      rotation=(math.pi, 0, 0), sweep=-.08, bevel=.016))

    # Shoulder blossoms and articulated arms.
    for side in (-1, 1):
        p = "L" if side < 0 else "R"
        shoulder = (side * .98, .00, 4.18)
        elbow = (side * 1.20, -.03, 3.36)
        wrist = (side * 1.28, -.16, 2.56)
        joint(f"M2_{p}_SHOULDER", shoulder, .46, .21)
        joint(f"M2_{p}_ELBOW", elbow, .42, .17)
        objects.append(sacred_blade_plate(f"M2_{p}_SHOULDER_COWL", (side * 1.00, .01, 4.18),
                                          (.64, .48, .62), dark,
                                          rotation=(0, side * math.radians(14), side * math.radians(8)),
                                          sweep=side * .20, bevel=.030))
        for layer in range(2):
            objects.append(sacred_blade_plate(f"M2_{p}_SHOULDER_PETAL_{layer}",
                                              (side * (1.03 + layer * .10), -.15 + layer * .055, 4.25 + (1 - layer) * .08),
                                              (.44 - layer * .05, .30, .66 - layer * .05),
                                              ivory if layer == 0 else rose,
                                              rotation=(0, side * math.radians(18 + layer * 7), side * math.radians(14 + layer * 2)),
                                              sweep=side * (.30 + layer * .06), bevel=.021))
        objects.append(beam(f"M2_{p}_UPPER_TENDON", shoulder, elbow, .105, dark, vertices=24))
        objects.append(beam(f"M2_{p}_FOREARM_TENDON", elbow, wrist, .090, dark, vertices=24))
        limb_petals(f"M2_{p}_BICEP", ((shoulder[0] + elbow[0]) * .5, -.01, 3.77), side, .88, .50)
        limb_petals(f"M2_{p}_FOREARM", ((elbow[0] + wrist[0]) * .5, -.10, 2.96), side, .84, .48)
        objects.append(sculpted_shell(f"M2_{p}_HAND", wrist, (.34, .32, .28), dark,
                                      front_scale=(.50, .56), bevel=.022))
        for finger in range(3):
            objects.append(beam(f"M2_{p}_FINGER_{finger}",
                                (wrist[0] + side * (-.07 + finger * .07), -.28, wrist[2] - .06),
                                (wrist[0] + side * (-.07 + finger * .07), -.40, wrist[2] - .24 - finger * .025),
                                .025, brass, vertices=12))

    # Left-hand resonance spear with nested blade petals and recessed cores.
    spear_x = -1.78
    objects.append(beam("M2_SPEAR_SHAFT", (spear_x, -.35, .28), (spear_x, -.35, 4.78), .055, brass, vertices=24))
    objects.append(cylinder("M2_SPEAR_GRIP", (spear_x, -.35, 2.55), .085, .72, dark, vertices=20, bevel=.015))
    for layer in range(4):
        objects.append(sacred_blade_plate(f"M2_SPEAR_BLADE_{layer}",
                                          (spear_x, -.35 + layer * .018, 4.76 + layer * .19),
                                          (.58 - layer * .09, .13, 1.48 - layer * .12),
                                          ivory if layer % 2 == 0 else rose,
                                          rotation=(0, 0, 0), sweep=(-.18 + layer * .10), bevel=.016))
    objects.append(sacred_blade_plate("M2_SPEAR_CORE", (spear_x, -.45, 4.86), (.16, .035, .74), magenta,
                                      sweep=.06, bevel=.008))
    objects.append(torus("M2_SPEAR_EMITTER", (spear_x, -.38, 4.40), .24, .035, cyan,
                         rotation=(math.pi / 2, 0, 0), major_segments=32, minor_segments=8))

    # Right forearm flower shield: every petal is attached to the brass frame.
    shield_x, shield_y, shield_z = 1.94, -.54, 3.12
    objects.append(torus("M2_SHIELD_OUTER", (shield_x, shield_y, shield_z), .78, .075, brass,
                         rotation=(math.pi / 2, 0, 0), major_segments=72, minor_segments=14))
    objects.append(torus("M2_SHIELD_INNER", (shield_x, shield_y - .04, shield_z), .44, .045, rose,
                         rotation=(math.pi / 2, 0, 0), major_segments=56, minor_segments=10))
    for petal in range(12):
        angle = petal * math.tau / 12
        x = shield_x + math.cos(angle) * .61
        z = shield_z + math.sin(angle) * .61
        objects.append(sacred_blade_plate(f"M2_SHIELD_PETAL_{petal}", (x, shield_y - .08, z),
                                          (.31, .10, .68), ivory if petal % 3 else rose,
                                          rotation=(0, math.pi / 2 - angle, 0),
                                          sweep=.28 if petal % 2 else -.20, bevel=.013))
        objects.append(beam(f"M2_SHIELD_SPOKE_{petal}", (shield_x, shield_y, shield_z),
                            (shield_x + math.cos(angle) * .48, shield_y, shield_z + math.sin(angle) * .48),
                            .022, brass, vertices=12))
    objects.append(cylinder("M2_SHIELD_CORE_FRAME", (shield_x, shield_y - .10, shield_z), .27, .16, dark,
                            rotation=(math.pi / 2, 0, 0), vertices=36, bevel=.020))
    objects.append(sphere("M2_SHIELD_CORE", (shield_x, shield_y - .20, shield_z), (.18, .07, .18), magenta,
                          segments=36, rings=20))
    objects.append(torus("M2_SHIELD_CORE_HALO", (shield_x, shield_y - .24, shield_z), .22, .025, cyan,
                         rotation=(math.pi / 2, 0, 0), major_segments=36, minor_segments=8))
    for index in range(6):
        angle = index * math.tau / 6
        objects.append(box(f"M2_SHIELD_CORE_GLYPH_{index}",
                           (shield_x + math.cos(angle) * .31, shield_y - .23, shield_z + math.sin(angle) * .31),
                           (.035, .025, .10), rose if index % 2 else brass,
                           rotation=(0, angle, angle), bevel=.006))
    objects.append(beam("M2_SHIELD_MOUNT", (1.45, -.06, 2.92), (shield_x - .28, shield_y + .08, shield_z),
                        .075, dark, vertices=20))

    # Anchored back halo and emitter crown.
    halo_points = []
    for step in range(13):
        angle = math.radians(-55 + step * 17)
        halo_points.append((math.sin(angle) * 1.12, .54, 4.27 + math.cos(angle) * .98))
    objects.append(cable("M2_BACK_HALO_FRAME", halo_points, .038, brass))
    for side in (-1, 1):
        objects.append(beam(f"M2_HALO_BRACE_UPPER_{side}", (side * .48, .46, 4.38),
                            (side * .83, .54, 4.91), .045, dark, vertices=18))
        objects.append(beam(f"M2_HALO_BRACE_LOWER_{side}", (side * .55, .44, 3.86),
                            (side * 1.02, .54, 4.27), .040, brass, vertices=18))
    for index in (1, 4, 7, 10):
        x, y, z = halo_points[index]
        objects.append(sacred_blade_plate(f"M2_HALO_EMITTER_{index}", (x, y, z), (.24, .16, .66),
                                          ivory if index % 4 else rose,
                                          rotation=(0, -math.radians(-55 + index * 17), 0),
                                          sweep=(-.22 + index * .035), bevel=.012))
        objects.append(sphere(f"M2_HALO_LIGHT_{index}", (x, y - .12, z), (.055, .04, .055), cyan,
                              segments=20, rings=12))

    # Small-form service seams, fasteners and energy conduits.
    for side in (-1, 1):
        for row in range(5):
            objects.append(cylinder(f"M2_CHEST_FASTENER_{side}_{row}",
                                    (side * (.27 + row * .105), -.705, 3.52 + row * .18),
                                    .012, .020, dark, rotation=(math.pi / 2, 0, 0), vertices=10, bevel=.003))
        objects.append(cable(f"M2_TORSO_CONDUIT_{side}", [
            (side * .20, -.58, 4.32), (side * .60, -.66, 4.12),
            (side * .74, -.62, 3.70), (side * .48, -.58, 3.35),
        ], .018, cyan if side < 0 else magenta))
    for index in range(12):
        side = -1 if index % 2 == 0 else 1
        objects.append(box(f"M2_EDGE_GLYPH_{index}",
                           (side * rng.uniform(.30, .92), -.72, rng.uniform(3.38, 4.42)),
                           (.035, .018, .075), cyan if index % 3 else magenta, bevel=.005))


def add_mir_details(objects: list[bpy.types.Object], mats: dict[str, bpy.types.Material], rng: random.Random) -> None:
    ivory, brass, rose, cyan, magenta, dark = (mats[k] for k in ("ivory", "brass", "rose", "cyan", "magenta", "dark"))
    # Slender biomechanical legs with nested ceramic shells.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        hip = (side * .62, 0, 2.30)
        knee = (side * .77, -.05, 1.36)
        ankle = (side * .62, -.12, .43)
        objects += [sphere(f"MIR_{prefix}_HIP", hip, (.27, .27, .27), brass)]
        objects += [beam(f"MIR_{prefix}_THIGH", hip, knee, .18, dark)]
        objects += [sphere(f"MIR_{prefix}_THIGH_SHELL", (side * .70, -.01, 1.84), (.32, .28, .58), ivory)]
        objects[-1].rotation_euler[1] = side * .12
        objects += [torus(f"MIR_{prefix}_KNEE_HALO", knee, .29, .045, cyan, rotation=(math.pi / 2, 0, 0))]
        objects += [sphere(f"MIR_{prefix}_KNEE", knee, (.19, .19, .19), rose)]
        objects += [beam(f"MIR_{prefix}_SHIN", knee, ankle, .15, brass)]
        objects += [sphere(f"MIR_{prefix}_SHIN_SHELL", (side * .68, -.08, .88), (.25, .23, .50), ivory)]
        objects += [box(f"MIR_{prefix}_FOOT", (side * .61, -.28, .15), (.48, .74, .22), dark, bevel=.11)]
        objects += [sphere(f"MIR_{prefix}_TOE_PEARL", (side * .61, -.61, .18), (.18, .24, .12), cyan)]

    # Pelvis, living core, rib cage, head and petal crown.
    objects += [sphere("MIR_PELVIS", (0, 0, 2.48), (.93, .58, .48), ivory, segments=48, rings=30)]
    objects += [torus("MIR_PELVIS_RING", (0, -.08, 2.49), .70, .065, brass, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_LIVING_CORE", (0, -.24, 3.42), (.55, .40, .68), magenta, segments=48, rings=32)]
    objects += [sphere("MIR_TORSO", (0, .02, 3.57), (1.08, .62, 1.17), ivory, segments=56, rings=36)]
    for side in (-1, 1):
        for i in range(4):
            z = 3.10 + i * .31
            objects += [beam(f"MIR_RIB_{side}_{i}", (side * .12, -.50, z), (side * (.72 + i * .045), -.35, z + .12),
                             .065, brass, vertices=20)]
    objects += [torus("MIR_CHEST_HALO", (0, -.58, 3.62), .54, .055, cyan, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_NECK", (0, 0, 4.63), (.30, .28, .35), brass)]
    objects += [sphere("MIR_HEAD", (0, -.05, 4.98), (.48, .40, .58), ivory, segments=48, rings=32)]
    objects += [sphere("MIR_FACE_LIGHT", (0, -.42, 5.00), (.20, .07, .27), cyan, segments=36, rings=20)]
    for i in range(7):
        angle = math.radians(-70 + i * (140 / 6))
        x = math.sin(angle) * .58
        z = 5.19 + math.cos(angle) * .58
        petal = sphere(f"MIR_CROWN_PETAL_{i}", (x, .06, z), (.14, .09, .44), rose, segments=32, rings=20)
        petal.rotation_euler[1] = -angle
        objects.append(petal)

    # Petal shoulders and articulated arms.
    for side in (-1, 1):
        prefix = "L" if side < 0 else "R"
        shoulder = (side * 1.18, 0, 4.05)
        elbow = (side * 1.46, -.02, 3.18)
        wrist = (side * 1.32, -.14, 2.48)
        objects += [sphere(f"MIR_{prefix}_SHOULDER_CORE", shoulder, (.30, .30, .30), brass)]
        for i, offset in enumerate((-.22, 0, .22)):
            petal = sphere(f"MIR_{prefix}_SHOULDER_PETAL_{i}",
                           (side * (1.32 + abs(offset) * .35), offset, 4.16 + abs(offset) * .20),
                           (.23, .48, .56), ivory, segments=40, rings=24)
            petal.rotation_euler[1] = side * (.38 + offset * .22)
            petal.rotation_euler[2] = side * offset
            objects.append(petal)
        objects += [beam(f"MIR_{prefix}_UPPER_ARM", shoulder, elbow, .17, brass)]
        objects += [sphere(f"MIR_{prefix}_ELBOW", elbow, (.23, .23, .23), rose)]
        objects += [torus(f"MIR_{prefix}_ELBOW_HALO", elbow, .29, .035, magenta, rotation=(math.pi / 2, 0, 0))]
        objects += [beam(f"MIR_{prefix}_FOREARM", elbow, wrist, .15, dark)]
        shell = sphere(f"MIR_{prefix}_FOREARM_SHELL", (side * 1.40, -.08, 2.83), (.24, .29, .48), ivory)
        shell.rotation_euler[1] = side * .10
        objects.append(shell)
        objects += [sphere(f"MIR_{prefix}_HAND", wrist, (.23, .20, .20), brass)]

    # Sanctuary spear and petal shield.
    objects += [beam("MIR_SPEAR_SHAFT", (1.58, -.30, .45), (1.58, -.30, 4.25), .075, brass, vertices=24)]
    objects += [cone("MIR_SPEAR_TIP", (1.58, -.30, 4.57), .20, .015, .70, ivory, vertices=32)]
    objects += [sphere("MIR_SPEAR_CORE", (1.58, -.34, 3.75), (.18, .13, .25), magenta)]
    for i in range(5):
        angle = i * math.tau / 5
        petal = sphere(f"MIR_SPEAR_PETAL_{i}", (1.58 + math.cos(angle) * .30, -.30, 3.75 + math.sin(angle) * .30),
                       (.10, .055, .28), cyan if i % 2 else rose, segments=28, rings=18)
        petal.rotation_euler[1] = angle
        objects.append(petal)
    objects += [torus("MIR_SHIELD_OUTER", (-1.77, -.52, 2.96), .73, .075, brass, rotation=(math.pi / 2, 0, 0), major_segments=64)]
    objects += [torus("MIR_SHIELD_INNER", (-1.77, -.58, 2.96), .48, .045, cyan, rotation=(math.pi / 2, 0, 0))]
    objects += [sphere("MIR_SHIELD_CORE", (-1.77, -.63, 2.96), (.18, .08, .18), magenta)]
    for i in range(8):
        angle = i * math.tau / 8
        x = -1.77 + math.cos(angle) * .57
        z = 2.96 + math.sin(angle) * .57
        petal = sphere(f"MIR_SHIELD_PETAL_{i}", (x, -.55, z), (.12, .06, .32), ivory, segments=28, rings=18)
        petal.rotation_euler[1] = angle
        objects.append(petal)

    # Flowing energy filaments make the faction's organic motion language visible.
    for side in (-1, 1):
        for i in range(3):
            y = .34 + i * .08
            objects.append(cable(f"MIR_FILAMENT_{side}_{i}", [
                (side * .45, y, 4.18 - i * .09),
                (side * (.88 + i * .08), y + .28, 3.58 - i * .12),
                (side * (.74 + i * .10), y + .48, 2.92 - i * .16),
            ], .025 + i * .005, cyan if i % 2 == 0 else magenta))
    for i in range(10):
        angle = i * math.tau / 10
        objects += [sphere(f"MIR_ORBITAL_PEARL_{i}", (math.cos(angle) * 1.14, .20, 3.58 + math.sin(angle) * 1.02),
                           (.055, .055, .055), cyan if i % 2 else magenta, segments=20, rings=12)]


def apply_modifiers_and_convert(objects: list[bpy.types.Object]) -> list[bpy.types.Object]:
    result: list[bpy.types.Object] = []
    for obj in list(objects):
        if obj.type == "CURVE":
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.convert(target="MESH")
            obj.select_set(False)
        if obj.type != "MESH":
            continue
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        for modifier in list(obj.modifiers):
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            except RuntimeError:
                pass
        if not obj.data.uv_layers:
            # Custom from_pydata armor shells do not inherit primitive UVs.
            # Generate deterministic UV islands so embedded PBR images map to
            # real surfaces instead of silently sampling an undefined origin.
            bpy.context.view_layer.objects.active = obj
            obj.select_set(True)
            bpy.ops.object.mode_set(mode="EDIT")
            bpy.ops.mesh.select_all(action="SELECT")
            bpy.ops.uv.smart_project(angle_limit=math.radians(66), island_margin=.025)
            bpy.ops.object.mode_set(mode="OBJECT")
        # Preserve a roughly world-consistent material scale. Small service
        # parts sample a compact portion of the seamless atlas while torso and
        # limb armor can traverse multiple panels instead of every object
        # stretching one full texture over its complete surface.
        if obj.data.uv_layers:
            extent = max(float(value) for value in obj.dimensions)
            tile_scale = max(.16, min(2.8, extent / .72))
            salt = int(hashlib.sha256(obj.name.encode("utf-8")).hexdigest()[:8], 16)
            offset_u = ((salt & 0xffff) / 0xffff) * .71
            offset_v = (((salt >> 16) & 0xffff) / 0xffff) * .71
            for item in obj.data.uv_layers.active.data:
                item.uv.x = item.uv.x * tile_scale + offset_u
                item.uv.y = item.uv.y * tile_scale + offset_v
        obj.select_set(False)
        result.append(obj)
    return result


def apply_loadout(objects: list[bpy.types.Object], asset_id: str, loadout: str) -> list[bpy.types.Object]:
    """Keep identity review separate from optional gameplay equipment.

    Equipment is still authored by the retained faction builder and can be
    exported with ``loadout=equipped``. Reference mode removes it before LOD,
    proof and source export so the character silhouette can be judged against
    the approved unarmed turnaround without weapon/shield occlusion.
    """
    if loadout == "equipped":
        return objects
    prefixes = (
        ("AX4_RAIL_", "AX4_SHIELD_", "AX4_EDGE_MARK_", "AX4_SHOULDER_CABLE_")
        if asset_id.startswith("axiom")
        else ("M2_SPEAR_", "M2_SHIELD_", "M2_TORSO_CONDUIT_", "M2_EDGE_GLYPH_")
    )
    kept: list[bpy.types.Object] = []
    for obj in objects:
        if obj.name.startswith(prefixes):
            bpy.data.objects.remove(obj, do_unlink=True)
        else:
            kept.append(obj)
    return kept


def select_only(objects: list[bpy.types.Object]) -> None:
    bpy.ops.object.select_all(action="DESELECT")
    for obj in objects:
        obj.hide_set(False)
        obj.hide_render = False
        obj.select_set(True)
    if objects:
        bpy.context.view_layer.objects.active = objects[0]


def export_glb(path: Path, objects: list[bpy.types.Object]) -> None:
    select_only(objects)
    bpy.ops.export_scene.gltf(
        filepath=str(path), export_format="GLB", use_selection=True, export_apply=True,
        export_materials="EXPORT", export_yup=True, export_cameras=False, export_lights=False,
    )


def duplicate_lod(objects: list[bpy.types.Object], ratio: float, suffix: str) -> list[bpy.types.Object]:
    duplicates = []
    for source in objects:
        duplicate = source.copy()
        duplicate.data = source.data.copy()
        duplicate.name = f"{source.name}_{suffix.upper()}"
        bpy.context.collection.objects.link(duplicate)
        if ratio < .999 and len(duplicate.data.polygons) > 80:
            modifier = duplicate.modifiers.new(f"AXM_{suffix}_Decimate", "DECIMATE")
            modifier.ratio = ratio
            modifier.use_collapse_triangulate = True
            bpy.context.view_layer.objects.active = duplicate
            duplicate.select_set(True)
            try:
                bpy.ops.object.modifier_apply(modifier=modifier.name)
            finally:
                duplicate.select_set(False)
        duplicates.append(duplicate)
    return duplicates


def remove_objects(objects: list[bpy.types.Object]) -> None:
    for obj in objects:
        bpy.data.objects.remove(obj, do_unlink=True)


def mesh_stats(objects: list[bpy.types.Object]) -> dict[str, int]:
    vertices = sum(len(obj.data.vertices) for obj in objects if obj.type == "MESH")
    triangles = 0
    for obj in objects:
        if obj.type != "MESH":
            continue
        obj.data.calc_loop_triangles()
        triangles += len(obj.data.loop_triangles)
    return {"objects": len(objects), "vertices": vertices, "triangles": triangles}


def collisions(asset_id: str, mats: dict[str, bpy.types.Material], loadout: str) -> list[bpy.types.Object]:
    collision = mats["collision"]
    if asset_id.startswith("axiom"):
        result = [
            box("UCX_AXIOM_TORSO", (0, 0, 3.55), (2.45, 1.18, 1.75), collision, bevel=0),
            box("UCX_AXIOM_PELVIS", (0, 0, 2.55), (1.95, 1.05, .75), collision, bevel=0),
            box("UCX_AXIOM_LEFT_LEG", (-.92, 0, 1.25), (.72, .74, 2.35), collision, bevel=0),
            box("UCX_AXIOM_RIGHT_LEG", (.92, 0, 1.25), (.72, .74, 2.35), collision, bevel=0),
        ]
        if loadout == "equipped":
            result.append(box("UCX_AXIOM_WEAPON", (-1.52, -.75, 4.58), (.78, 2.10, .62), collision, bevel=0))
        return result
    result = [
        box("UCX_MIR_TORSO", (0, 0, 3.55), (2.30, 1.25, 2.20), collision, bevel=0),
        box("UCX_MIR_PELVIS", (0, 0, 2.48), (1.75, 1.12, .75), collision, bevel=0),
        box("UCX_MIR_LEFT_LEG", (-.68, 0, 1.20), (.58, .62, 2.25), collision, bevel=0),
        box("UCX_MIR_RIGHT_LEG", (.68, 0, 1.20), (.58, .62, 2.25), collision, bevel=0),
    ]
    if loadout == "equipped":
        result.append(box("UCX_MIR_SPEAR", (-1.78, -.35, 2.50), (.40, .40, 4.50), collision, bevel=0))
    return result


def setup_render(resolution: int, transparent: bool) -> tuple[bpy.types.Object, bpy.types.Object]:
    scene = bpy.context.scene
    # Blender 5.2 exposes Eevee under BLENDER_EEVEE; older 4.x builds used
    # BLENDER_EEVEE_NEXT. Prefer the runtime's actual enum, not a version guess.
    try:
        scene.render.engine = "BLENDER_EEVEE"
    except TypeError:
        scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = resolution
    scene.render.resolution_y = resolution
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    scene.render.image_settings.color_mode = "RGBA"
    scene.render.film_transparent = transparent
    scene.render.image_settings.color_depth = "8"
    scene.render.image_settings.compression = 32
    scene.view_settings.exposure = .20
    scene.world.color = (.004, .007, .013)
    world = scene.world
    world.use_nodes = True
    background = world.node_tree.nodes.get("Background")
    background.inputs["Color"].default_value = (.004, .008, .018, 1)
    background.inputs["Strength"].default_value = .36

    ground_mat = material("ENV_Ground", (.012, .019, .030, 1), metallic=.22, roughness=.30)
    bpy.ops.mesh.primitive_plane_add(size=30, location=(0, 0, -.01))
    ground = bpy.context.object
    ground.name = "RENDER_GROUND"
    assign(ground, ground_mat)

    bpy.ops.object.camera_add(location=(9, -11, 6.8))
    camera = bpy.context.object
    camera.name = "RENDER_CAMERA"
    camera.data.lens = 70
    scene.camera = camera

    light_specs = [
        ("KEY", (5.5, -5.5, 8.5), (0.72, 0.86, 1.0), 1850, 5.5),
        ("RIM", (-5.5, 1.5, 6.5), (0.16, 0.76, 1.0), 1250, 4.0),
        ("FILL", (2.5, 4.5, 4.0), (1.0, 0.48, 0.22), 850, 3.5),
        ("TOP", (0, 0, 10.5), (0.68, 0.76, 1.0), 800, 3.0),
    ]
    for name, location, color, energy, size in light_specs:
        data = bpy.data.lights.new(name, "AREA")
        data.energy = energy
        data.color = color
        data.shape = "DISK"
        data.size = size
        obj = bpy.data.objects.new(name, data)
        bpy.context.collection.objects.link(obj)
        obj.location = location
        obj.rotation_euler = (0, 0, 0)
        obj.rotation_euler = ((Vector((0, 0, 3.0)) - obj.location).to_track_quat("-Z", "Y").to_euler())
    return camera, ground


def point_camera(camera: bpy.types.Object, degrees: float, *, radius: float = 12.4, height: float = 5.4) -> None:
    angle = math.radians(degrees)
    camera.location = (math.sin(angle) * radius, -math.cos(angle) * radius, height)
    target = Vector((0, 0, 2.65))
    camera.rotation_euler = (target - camera.location).to_track_quat("-Z", "Y").to_euler()


def sha(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def main() -> None:
    args = parse_args()
    request_path = Path(args.request).resolve()
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=True)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    asset_id = request["asset_id"]
    rng = random.Random(int(request.get("seed", 0)))
    clear_scene()

    texture_size = int(request.get("technical_requirements", {}).get("texture_resolution", 1024))
    texture_root = output / "textures"
    authored_root = Path(__file__).resolve().parents[2] / "assets" / "materials"

    def authored(prefix: str) -> dict[str, Path]:
        return {role: authored_root / f"{prefix}_{role}.png"
                for role in ("basecolor", "roughness", "metallic", "normal")}

    mats = {
        "dark": material("AXM_DarkMechanism", (.018, .024, .032, 1), metallic=.76, roughness=.36,
                         texture_dir=texture_root, texture_size=texture_size,
                         source_maps=authored("axiom-dark-frame-aaa") if asset_id.startswith("axiom") else None),
        "collision": material("AXM_CollisionDebug", (.80, .02, .02, .35), metallic=0, roughness=1),
    }
    if asset_id.startswith("axiom"):
        mats.update({
            "gunmetal": material("AX_Gunmetal", (.075, .105, .135, 1), metallic=.95, roughness=.27,
                                  texture_dir=texture_root, texture_size=texture_size,
                                  source_maps=authored("axiom-dark-gunmetal-aaa")),
            "pale": material("AX_PaleCeramicArmor", (.46, .52, .55, 1), metallic=.66, roughness=.25,
                              texture_dir=texture_root, texture_size=texture_size,
                              source_maps=authored("axiom-pale-ceramic-aaa")),
            "cyan": material("AX_ElectricCyan", (.006, .12, .18, 1), metallic=.20, roughness=.20,
                             emission=(.00, .48, .72, 1), emission_strength=3.2,
                             texture_dir=texture_root, texture_size=texture_size),
            "amber": material("AX_SignalAmber", (.22, .055, .004, 1), metallic=.20, roughness=.25,
                              emission=(.72, .11, .008, 1), emission_strength=2.5,
                              texture_dir=texture_root, texture_size=texture_size),
        })
    else:
        mats.update({
            "ivory": material("MIR_IvoryCeramic", (.63, .56, .46, 1), metallic=.05, roughness=.38,
                              texture_dir=texture_root, texture_size=texture_size,
                              source_maps=authored("mir-aged-ivory-aaa")),
            "brass": material("MIR_Brass", (.34, .15, .035, 1), metallic=.94, roughness=.30,
                              texture_dir=texture_root, texture_size=texture_size),
            "rose": material("MIR_RoseGold", (.36, .11, .09, 1), metallic=.86, roughness=.33,
                             texture_dir=texture_root, texture_size=texture_size),
            "cyan": material("MIR_ResonanceCyan", (.006, .10, .12, 1), metallic=.12, roughness=.22,
                             emission=(.00, .44, .60, 1), emission_strength=2.2,
                             texture_dir=texture_root, texture_size=texture_size),
            "magenta": material("MIR_ResonanceMagenta", (.19, .006, .10, 1), metallic=.12, roughness=.22,
                                emission=(.74, .010, .30, 1), emission_strength=2.8,
                                texture_dir=texture_root, texture_size=texture_size),
        })
    objects: list[bpy.types.Object] = []
    if asset_id == "axiom-bastion-frame":
        add_axiom_hero_v4(objects, mats, rng)
    elif asset_id == "mir-sanctuary-keeper":
        add_mir_hero_v3(objects, mats, rng)
    else:
        raise ValueError(f"unsupported asset_id: {asset_id}")
    loadout = str(request.get("loadout", "reference"))
    objects = apply_loadout(objects, asset_id, loadout)
    objects = apply_modifiers_and_convert(objects)

    exports: dict[str, dict] = {}
    lod0_path = output / f"{asset_id}_LOD0.glb"
    export_glb(lod0_path, objects)
    exports["lod0"] = {"path": lod0_path.name, **mesh_stats(objects), "sha256": sha(lod0_path), "bytes": lod0_path.stat().st_size}

    for lod_name, ratio in (("lod1", .48), ("lod2", .18)):
        duplicated = duplicate_lod(objects, ratio, lod_name)
        path = output / f"{asset_id}_{lod_name.upper()}.glb"
        export_glb(path, duplicated)
        exports[lod_name] = {"path": path.name, **mesh_stats(duplicated), "sha256": sha(path), "bytes": path.stat().st_size}
        remove_objects(duplicated)

    collision_objects = collisions(asset_id, mats, loadout)
    collision_path = output / f"{asset_id}_COLLISION.glb"
    export_glb(collision_path, collision_objects)
    exports["collision"] = {"path": collision_path.name, **mesh_stats(collision_objects), "sha256": sha(collision_path), "bytes": collision_path.stat().st_size}
    for obj in collision_objects:
        obj.hide_render = True
        obj.hide_set(True)

    camera, ground = setup_render(request["render"]["resolution"], request["render"]["transparent"])
    render_proofs = []
    for angle in request["render"]["angles_degrees"]:
        point_camera(camera, float(angle))
        path = output / f"{asset_id}_view_{int(angle):03d}.png"
        bpy.context.scene.render.filepath = str(path)
        bpy.ops.render.render(write_still=True)
        render_proofs.append({"angle_degrees": angle, "path": path.name, "sha256": sha(path), "bytes": path.stat().st_size})

    blend_path = output / f"{asset_id}.blend"
    select_only(objects)
    bpy.ops.wm.save_as_mainfile(filepath=str(blend_path))

    manifest = {
        "schema": "axm.3d-asset-manifest/v0.1",
        "truth_status": "GEOMETRY_EXPORTED_AND_MULTI_ANGLE_RENDERED",
        "asset_id": asset_id,
        "faction": request["faction"],
        "archetype": request["archetype"],
        "loadout": loadout,
        "meters_per_unit": 1.0,
        "source": {"path": blend_path.name, "sha256": sha(blend_path), "bytes": blend_path.stat().st_size},
        "exports": exports,
        "materials": sorted({slot.material.name for obj in objects for slot in obj.material_slots if slot.material}),
        "pbr_texture_resolution": texture_size,
        "render_proofs": render_proofs,
        "quality_claim": "Rendered vertical-slice evidence; final AAA acceptance remains a visual review decision.",
    }
    (output / "asset-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"status": "AXM_3D_FORGE_COMPLETE", "asset_id": asset_id, "output": str(output), "exports": exports}, indent=2))


if __name__ == "__main__":
    main()


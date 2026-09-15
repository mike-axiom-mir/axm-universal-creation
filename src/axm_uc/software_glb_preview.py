"""Deterministic software preview of actual embedded GLB geometry.

This is a bounded inspection renderer, not a target-engine or PBR-equivalence
claim. It uses the existing offline pose evaluator and emits PNG without a GPU,
browser, external service, NumPy or Pillow.
"""
from __future__ import annotations

import hashlib
import math
import struct
from pathlib import Path

from .atomic import atomic_write_bytes
from .fabric_noise import png_bytes
from .game_pose_runtime import GamePoseAsset, _parse


MAX_SIDE = 1024
MAX_PIXELS = 1_048_576
MAX_TRIANGLES = 100_000
MAX_RASTER_VISITS = 36_000_000


def software_glb_preview_catalog():
    return {
        "schema": "axm.software-glb-preview-catalog/v0.1",
        "input": "embedded GLB 2.0 accepted by the offline pose runtime",
        "output": "deterministic RGB PNG plus geometry-bound receipt",
        "features": ["animation sampling", "orthographic framing", "backface culling",
                     "depth buffer", "two-light flat shading", "2x supersampling"],
        "dependencies": [],
        "limits": {"maximum_side": MAX_SIDE, "maximum_pixels": MAX_PIXELS,
                   "maximum_triangles": MAX_TRIANGLES, "maximum_raster_visits": MAX_RASTER_VISITS},
        "truth": (
            "Observes decoded geometry, material factors, vertex colours and one sampled pose. "
            "It does not prove PBR parity, textures, transparency, target-engine import, continuous "
            "animation, artistic quality or performance."
        ),
    }


def _number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} through {high}")
    return value


def _integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} through {high}")
    return value


def _unit(value):
    length = math.sqrt(sum(item * item for item in value))
    if length <= 1e-12:
        raise ValueError("camera basis collapsed")
    return tuple(item / length for item in value)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _sub(a, b):
    return tuple(a[i] - b[i] for i in range(3))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _accessor(document, binary, reference):
    accessors, views = document.get("accessors", []), document.get("bufferViews", [])
    if type(reference) is not int or not 0 <= reference < len(accessors):
        raise ValueError("invalid preview accessor reference")
    accessor = accessors[reference]
    view_ref = accessor.get("bufferView")
    if type(view_ref) is not int or not 0 <= view_ref < len(views):
        raise ValueError("preview accessor requires one embedded buffer view")
    view = views[view_ref]
    component = accessor.get("componentType")
    kind = accessor.get("type")
    formats = {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4), 5126: ("f", 4)}
    widths = {"SCALAR": 1, "VEC3": 3, "VEC4": 4}
    if component not in formats or kind not in widths or accessor.get("sparse"):
        raise ValueError("unsupported preview accessor encoding")
    code, size = formats[component]
    width = widths[kind]
    count = accessor.get("count")
    if type(count) is not int or not 1 <= count <= 1_000_000:
        raise ValueError("invalid preview accessor count")
    base = view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
    stride = view.get("byteStride", width * size)
    if (type(base) is not int or type(stride) is not int or base < 0 or stride < width * size
            or base + (count - 1) * stride + width * size > len(binary)):
        raise ValueError("preview accessor exceeds embedded buffer")
    fmt = "<" + code * width
    return [struct.unpack_from(fmt, binary, base + index * stride) for index in range(count)]


def _scene_triangles(body, clip, time_s, loop):
    asset = GamePoseAsset(body)
    description = asset.describe()
    if clip is not None and clip not in {row["name"] for row in description["clips"]}:
        raise ValueError(f"unknown preview clip: {clip}")
    document, binary = _parse(body)
    pose = asset.sample(clip, time_s, loop=loop, vertices=True)
    triangles = []
    for mesh in pose["meshes"]:
        node = document["nodes"][mesh["node"]]
        primitive = document["meshes"][node["mesh"]]["primitives"][mesh["primitive"]]
        indices = [row[0] for row in _accessor(document, binary, primitive.get("indices"))]
        if len(indices) % 3 or max(indices) >= len(mesh["positions"]):
            raise ValueError("preview triangle indices are invalid")
        material_ref = primitive.get("material")
        if type(material_ref) is not int or not 0 <= material_ref < len(document.get("materials", [])):
            raise ValueError("preview requires a material on every primitive")
        material = document["materials"][material_ref]
        factor = material.get("pbrMetallicRoughness", {}).get("baseColorFactor", [1, 1, 1, 1])
        if not isinstance(factor, list) or len(factor) != 4:
            raise ValueError("invalid preview material factor")
        emissive = material.get("emissiveFactor", [0, 0, 0])
        if not isinstance(emissive, list) or len(emissive) != 3:
            raise ValueError("invalid preview emissive factor")
        colors = None
        if "COLOR_0" in primitive.get("attributes", {}):
            colors = _accessor(document, binary, primitive["attributes"]["COLOR_0"])
            if len(colors) != len(mesh["positions"]):
                raise ValueError("preview vertex color count mismatch")
        for offset in range(0, len(indices), 3):
            face = indices[offset:offset + 3]
            points = [tuple(mesh["positions"][index]) for index in face]
            tint = [1.0, 1.0, 1.0]
            if colors is not None:
                tint = [sum(colors[index][channel] for index in face) / 3 for channel in range(3)]
            base = [max(0.0, min(1.0, factor[channel] * tint[channel])) for channel in range(3)]
            triangles.append((points, base, [max(0.0, min(1.0, value)) for value in emissive]))
            if len(triangles) > MAX_TRIANGLES:
                raise ValueError("preview triangle budget exceeded")
    if not triangles:
        raise ValueError("preview asset contains no triangles")
    return triangles, asset.source_sha256


def render_glb_preview(body, *, width=640, height=420, yaw=.72, elevation=.38,
                       clip=None, time_s=0.0, loop=False, supersample=2):
    width = _integer(width, "width", 64, MAX_SIDE)
    height = _integer(height, "height", 64, MAX_SIDE)
    supersample = _integer(supersample, "supersample", 1, 2)
    if width * height > MAX_PIXELS:
        raise ValueError("preview pixel budget exceeded")
    yaw = _number(yaw, "yaw", -math.tau * 4, math.tau * 4)
    elevation = _number(elevation, "elevation", -1.45, 1.45)
    time_s = _number(time_s, "time_s", 0, 3600)
    if type(loop) is not bool:
        raise ValueError("loop must be boolean")
    triangles, source_sha256 = _scene_triangles(body, clip, time_s, loop)
    right = _unit((math.cos(yaw), 0.0, -math.sin(yaw)))
    up = _unit((-math.sin(yaw) * math.sin(elevation), math.cos(elevation),
                -math.cos(yaw) * math.sin(elevation)))
    forward = _unit(_cross(right, up))
    projected = []
    minimum = [math.inf, math.inf]
    maximum = [-math.inf, -math.inf]
    world_min = [math.inf, math.inf, math.inf]
    world_max = [-math.inf, -math.inf, -math.inf]
    for points, base, emissive in triangles:
        rows = []
        for point in points:
            rows.append([_dot(point, right), _dot(point, up), _dot(point, forward)])
            for axis in range(3):
                world_min[axis] = min(world_min[axis], point[axis])
                world_max[axis] = max(world_max[axis], point[axis])
        for row in rows:
            for axis in range(2):
                minimum[axis] = min(minimum[axis], row[axis])
                maximum[axis] = max(maximum[axis], row[axis])
        projected.append((rows, points, base, emissive))
    render_width, render_height = width * supersample, height * supersample
    span_x = max(.1, maximum[0] - minimum[0])
    span_y = max(.1, maximum[1] - minimum[1])
    scale = min((render_width - 48 * supersample) / span_x,
                (render_height - 42 * supersample) / span_y)
    center = [(minimum[axis] + maximum[axis]) / 2 for axis in range(2)]
    pixels = bytearray(render_width * render_height * 3)
    depth = [-math.inf] * (render_width * render_height)
    # A neutral horizon gradient provides figure/ground separation without altering the GLB.
    for y in range(render_height):
        fraction = y / max(1, render_height - 1)
        sky = fraction < .67
        if sky:
            t = fraction / .67
            color = (round(15 + 18 * t), round(28 + 23 * t), round(40 + 22 * t))
        else:
            t = (fraction - .67) / .33
            color = (round(31 - 9 * t), round(37 - 10 * t), round(40 - 10 * t))
        row = bytes(color) * render_width
        start = y * render_width * 3
        pixels[start:start + len(row)] = row
    key = _unit((-.45, .9, .7))
    rim = _unit((.8, .4, -.5))
    visits = 0
    visible_triangles = 0
    for rows, points, base, emissive in projected:
        screen = [
            ((row[0] - center[0]) * scale + render_width / 2,
             render_height / 2 - (row[1] - center[1]) * scale,
             row[2]) for row in rows
        ]
        normal = _cross(_sub(points[1], points[0]), _sub(points[2], points[0]))
        length = math.sqrt(_dot(normal, normal))
        if length <= 1e-12:
            continue
        normal = tuple(value / length for value in normal)
        if _dot(normal, forward) <= 0:
            continue
        min_x = max(0, math.floor(min(point[0] for point in screen)))
        max_x = min(render_width - 1, math.ceil(max(point[0] for point in screen)))
        min_y = max(0, math.floor(min(point[1] for point in screen)))
        max_y = min(render_height - 1, math.ceil(max(point[1] for point in screen)))
        if min_x > max_x or min_y > max_y:
            continue
        visits += (max_x - min_x + 1) * (max_y - min_y + 1)
        if visits > MAX_RASTER_VISITS:
            raise ValueError("preview raster work budget exceeded")
        a, b, c = screen
        denominator = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
        if abs(denominator) < 1e-12:
            continue
        light = .28 + .64 * max(0.0, _dot(normal, key)) + .19 * max(0.0, _dot(normal, rim))
        linear = [max(0.0, min(1.0, base[channel] * light + emissive[channel] * .6))
                  for channel in range(3)]
        color = [round((value ** (1 / 2.2)) * 255) for value in linear]
        wrote = False
        for y in range(min_y, max_y + 1):
            py = y + .5
            for x in range(min_x, max_x + 1):
                px = x + .5
                u = ((b[1] - c[1]) * (px - c[0]) + (c[0] - b[0]) * (py - c[1])) / denominator
                v = ((c[1] - a[1]) * (px - c[0]) + (a[0] - c[0]) * (py - c[1])) / denominator
                w = 1.0 - u - v
                if u < 0 or v < 0 or w < 0:
                    continue
                z = u * a[2] + v * b[2] + w * c[2]
                at = y * render_width + x
                if z <= depth[at]:
                    continue
                depth[at] = z
                offset = at * 3
                pixels[offset:offset + 3] = bytes(color)
                wrote = True
        visible_triangles += int(wrote)
    if not visible_triangles:
        raise ValueError("preview produced no visible model triangles")
    if supersample == 2:
        down = bytearray(width * height * 3)
        for y in range(height):
            for x in range(width):
                sources = [((y * 2 + dy) * render_width + x * 2 + dx) * 3
                           for dy in (0, 1) for dx in (0, 1)]
                target = (y * width + x) * 3
                for channel in range(3):
                    down[target + channel] = round(sum(pixels[source + channel] for source in sources) / 4)
        pixels = down
    body_png = png_bytes(width, height, 3, bytes(pixels))
    return {
        "body": body_png,
        "receipt": {
            "schema": "axm.software-glb-preview/v0.1",
            "source_sha256": source_sha256,
            "png_sha256": hashlib.sha256(body_png).hexdigest(),
            "width": width, "height": height, "supersample": supersample,
            "yaw": yaw, "elevation": elevation, "clip": clip, "time_s": time_s, "loop": loop,
            "triangles": len(triangles), "visible_triangles": visible_triangles,
            "raster_visits": visits,
            "bounds": {"min": world_min, "max": world_max},
            "truth": software_glb_preview_catalog()["truth"],
        },
    }


def publish_glb_preview(asset, output, **options):
    source = Path(asset)
    target = Path(output)
    if target.suffix.casefold() != ".png":
        raise ValueError("software GLB preview output must end in .png")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing preview: {target}")
    result = render_glb_preview(source.read_bytes(), **options)
    target.parent.mkdir(parents=True, exist_ok=True)
    atomic_write_bytes(target, result["body"])
    if target.read_bytes() != result["body"]:
        target.unlink(missing_ok=True)
        raise ValueError("published preview bytes changed after write")
    return result["receipt"]

"""Measure static GLB UV scale and bound texture resolution for look-development evidence.

This module is intentionally renderer-neutral and standard-library only. It reads
actual embedded GLB geometry/UV bytes and core embedded PNG/JPEG image dimensions.
It does not unwrap, rescale, repair, render, or decide that a texel density is good.
Unsupported deformation, external media, alternate UV sets, compressed accessors,
or texture transforms HOLD instead of being guessed through.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

from .asset_geometry import (
    GeometryIssue,
    IDENTITY,
    MAX_BYTES,
    _GLB,
    _at,
    _integer,
    _local,
    _multiply,
    _point,
)

EVIDENCE_SCHEMA = "axm.material-uv-evidence/v0.1"
MAX_UV_ELEMENTS = 2_000_000
MAX_TRIANGLES = 1_000_000
MAX_PRIMITIVES = 4096
MAX_IMAGE_BYTES = 64 * 1024 * 1024
MIN_TWICE_AREA = 1e-12
CORE_SLOTS = (
    ("base-color", "pbr", "baseColorTexture"),
    ("metallic-roughness", "pbr", "metallicRoughnessTexture"),
    ("normal", "material", "normalTexture"),
    ("occlusion", "material", "occlusionTexture"),
    ("emissive", "material", "emissiveTexture"),
)


def _uv_accessor(glb: _GLB, index: int) -> list[tuple[float, float]]:
    """Decode an unnormalized FLOAT VEC2 accessor from the embedded GLB buffer."""
    a = _at(glb.doc.get("accessors"), index, "accessor")
    if "sparse" in a or a.get("extensions"):
        raise GeometryIssue("UNSUPPORTED_UV_ACCESSOR", "sparse/extended UV accessors are not measured", hold=True)
    if a.get("type") != "VEC2" or a.get("componentType") != 5126 or a.get("normalized", False):
        raise GeometryIssue("UNSUPPORTED_UV_ACCESSOR", "UV evidence requires unnormalized FLOAT VEC2", hold=True)
    count = _integer(a.get("count"), "UV accessor count", 1)
    if count > MAX_UV_ELEMENTS:
        raise GeometryIssue("RESOURCE_LIMIT", "UV accessor exceeds element limit", hold=True)
    view = _at(glb.doc.get("bufferViews"), a.get("bufferView"), "bufferView")
    if view.get("extensions"):
        raise GeometryIssue("UNSUPPORTED_BUFFER_VIEW", "compressed/extended UV buffer views need their decoder", hold=True)
    if view.get("buffer") != 0:
        raise GeometryIssue("INVALID_REFERENCE", "UV bufferView must reference embedded buffer 0")
    start = _integer(view.get("byteOffset", 0), "UV bufferView byteOffset")
    length = _integer(view.get("byteLength"), "UV bufferView byteLength", 1)
    relative = _integer(a.get("byteOffset", 0), "UV accessor byteOffset")
    stride = _integer(view.get("byteStride", 8), "UV byteStride", 8)
    if (start + length > glb.length or relative + (count - 1) * stride + 8 > length
            or (start + relative) % 4 or stride % 4 or stride > 252):
        raise GeometryIssue("INVALID_ACCESSOR_RANGE", "UV accessor alignment/stride/range exceeds its buffer view")
    decoder = struct.Struct("<2f")
    values = [decoder.unpack_from(glb.binary, start + relative + i * stride) for i in range(count)]
    if any(not all(math.isfinite(v) for v in row) for row in values):
        raise GeometryIssue("NONFINITE_UV", "TEXCOORD_0 contains NaN or infinity")
    return values


def _view_bytes(glb: _GLB, ref: Any, kind: str) -> bytes:
    view = _at(glb.doc.get("bufferViews"), ref, kind)
    if view.get("extensions"):
        raise GeometryIssue("UNSUPPORTED_BUFFER_VIEW", f"extended {kind} is not decoded", hold=True)
    if view.get("buffer") != 0:
        raise GeometryIssue("INVALID_REFERENCE", f"{kind} must reference embedded buffer 0")
    start = _integer(view.get("byteOffset", 0), f"{kind} byteOffset")
    length = _integer(view.get("byteLength"), f"{kind} byteLength", 1)
    if length > MAX_IMAGE_BYTES or start + length > glb.length:
        raise GeometryIssue("RESOURCE_LIMIT", f"{kind} is oversized or outside the embedded buffer", hold=True)
    return glb.binary[start:start + length]


def _png_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 33 or data[:8] != b"\x89PNG\r\n\x1a\n" or data[12:16] != b"IHDR":
        raise GeometryIssue("INVALID_IMAGE", "embedded PNG lacks a valid IHDR header", hold=True)
    if struct.unpack_from(">I", data, 8)[0] != 13:
        raise GeometryIssue("INVALID_IMAGE", "embedded PNG IHDR length is invalid", hold=True)
    payload = data[16:29]
    import zlib
    if zlib.crc32(b"IHDR" + payload) & 0xffffffff != struct.unpack_from(">I", data, 29)[0]:
        raise GeometryIssue("INVALID_IMAGE", "embedded PNG IHDR CRC is invalid", hold=True)
    width, height = struct.unpack_from(">II", payload)
    if not 1 <= width <= 32768 or not 1 <= height <= 32768:
        raise GeometryIssue("RESOURCE_LIMIT", "embedded PNG dimensions exceed review bounds", hold=True)
    return width, height


def _jpeg_dimensions(data: bytes) -> tuple[int, int]:
    if len(data) < 4 or data[:2] != b"\xff\xd8":
        raise GeometryIssue("INVALID_IMAGE", "embedded JPEG lacks SOI marker", hold=True)
    cursor = 2
    sof = {0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF}
    while cursor < len(data):
        while cursor < len(data) and data[cursor] != 0xFF:
            cursor += 1
        while cursor < len(data) and data[cursor] == 0xFF:
            cursor += 1
        if cursor >= len(data):
            break
        marker = data[cursor]
        cursor += 1
        if marker in {0xD8, 0xD9, 0x01} or 0xD0 <= marker <= 0xD7:
            continue
        if cursor + 2 > len(data):
            break
        length = struct.unpack_from(">H", data, cursor)[0]
        if length < 2 or cursor + length > len(data):
            break
        if marker in sof:
            if length < 7:
                break
            height, width = struct.unpack_from(">HH", data, cursor + 3)
            if not 1 <= width <= 32768 or not 1 <= height <= 32768:
                raise GeometryIssue("RESOURCE_LIMIT", "embedded JPEG dimensions exceed review bounds", hold=True)
            return width, height
        cursor += length
    raise GeometryIssue("INVALID_IMAGE", "embedded JPEG dimensions could not be resolved", hold=True)


def _image_record(glb: _GLB, index: Any) -> dict[str, Any]:
    image = _at(glb.doc.get("images"), index, "image")
    if image.get("extensions") or "uri" in image or "bufferView" not in image:
        raise GeometryIssue("EXTERNAL_OR_EXTENDED_IMAGE", "UV evidence measures only core embedded GLB images; nothing is fetched", hold=True)
    mime = image.get("mimeType")
    payload = _view_bytes(glb, image["bufferView"], "image bufferView")
    if mime == "image/png":
        width, height = _png_dimensions(payload)
    elif mime == "image/jpeg":
        width, height = _jpeg_dimensions(payload)
    else:
        raise GeometryIssue("UNSUPPORTED_IMAGE", "UV evidence supports core embedded PNG/JPEG images", hold=True)
    return {"image_index": int(index), "mime_type": mime, "width": width, "height": height,
            "sha256": hashlib.sha256(payload).hexdigest(), "byte_length": len(payload)}


def _texture_binding(glb: _GLB, slot: str, info: Any) -> dict[str, Any]:
    if not isinstance(info, dict):
        raise GeometryIssue("INVALID_TEXTURE_INFO", f"{slot} texture info must be an object")
    if info.get("extensions"):
        raise GeometryIssue("TEXTURE_TRANSFORM_UNMEASURED", f"{slot} texture extensions can alter UV scale", hold=True)
    if info.get("texCoord", 0) != 0:
        raise GeometryIssue("ALTERNATE_UV_SET_UNMEASURED", f"{slot} uses TEXCOORD_{info.get('texCoord')}", hold=True)
    texture_index = _integer(info.get("index"), f"{slot} texture index")
    texture = _at(glb.doc.get("textures"), texture_index, "texture")
    if texture.get("extensions") or "source" not in texture:
        raise GeometryIssue("UNSUPPORTED_TEXTURE", f"{slot} texture source is extended or missing", hold=True)
    image = _image_record(glb, texture["source"])
    wrap_s = wrap_t = 10497
    if "sampler" in texture:
        sampler = _at(glb.doc.get("samplers"), texture["sampler"], "sampler")
        if sampler.get("extensions"):
            raise GeometryIssue("UNSUPPORTED_SAMPLER", f"{slot} sampler uses extensions", hold=True)
        wrap_s, wrap_t = sampler.get("wrapS", 10497), sampler.get("wrapT", 10497)
        if wrap_s not in {33071, 33648, 10497} or wrap_t not in {33071, 33648, 10497}:
            raise GeometryIssue("UNSUPPORTED_SAMPLER", f"{slot} sampler wrap mode is invalid", hold=True)
    return {"slot": slot, "texture_index": texture_index, **image, "wrap_s": wrap_s, "wrap_t": wrap_t}


def _material_bindings(glb: _GLB, material: dict[str, Any]) -> list[dict[str, Any]]:
    pbr = material.get("pbrMetallicRoughness", {})
    if not isinstance(pbr, dict):
        raise GeometryIssue("INVALID_MATERIAL", "pbrMetallicRoughness must be an object")
    rows = []
    for slot, owner, key in CORE_SLOTS:
        source = pbr if owner == "pbr" else material
        if key in source:
            rows.append(_texture_binding(glb, slot, source[key]))
    return rows


def _twice_area_3d(a: list[float], b: list[float], c: list[float]) -> float:
    u = [b[i] - a[i] for i in range(3)]
    v = [c[i] - a[i] for i in range(3)]
    cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
    return math.sqrt(sum(x*x for x in cross))


def _twice_area_uv(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return abs((b[0]-a[0])*(c[1]-a[1]) - (b[1]-a[1])*(c[0]-a[0]))


def _weighted_percentile(rows: list[tuple[float, float]], q: float) -> float:
    ordered = sorted(rows)
    total = sum(weight for _, weight in ordered)
    target, seen = total * q, 0.0
    for value, weight in ordered:
        seen += weight
        if seen >= target:
            return value
    return ordered[-1][0]


def _density_summary(base_rows: list[tuple[float, float]], width: int, height: int) -> dict[str, float]:
    scale = math.sqrt(width * height)
    rows = [(ratio * scale, weight) for ratio, weight in base_rows]
    total = sum(weight for _, weight in rows)
    geometric = math.exp(sum(weight * math.log(value) for value, weight in rows) / total)
    p10, p50, p90 = (_weighted_percentile(rows, q) for q in (.1, .5, .9))
    return {"weighted_geometric_mean": geometric, "p10": p10, "p50": p50, "p90": p90,
            "p90_p10_ratio": p90 / p10 if p10 else float("inf")}


def _uv_world_jacobian(
    world_points: list[list[float]], uv_points: list[tuple[float, float]]
) -> tuple[float, float, float, float]:
    """Return the local world-plane -> UV Jacobian for one non-degenerate triangle."""
    a, b, c = world_points
    e1 = [b[i] - a[i] for i in range(3)]
    e2 = [c[i] - a[i] for i in range(3)]
    e1_len = math.sqrt(sum(v * v for v in e1))
    if not math.isfinite(e1_len) or e1_len <= 0:
        raise ArithmeticError("first world edge is not a finite nonzero vector")
    xhat = [v / e1_len for v in e1]
    x2 = sum(e2[i] * xhat[i] for i in range(3))
    orthogonal = [e2[i] - x2 * xhat[i] for i in range(3)]
    y2 = math.sqrt(sum(v * v for v in orthogonal))
    if not math.isfinite(y2) or y2 <= 0:
        raise ArithmeticError("world triangle basis is singular")
    du1 = uv_points[1][0] - uv_points[0][0]
    dv1 = uv_points[1][1] - uv_points[0][1]
    du2 = uv_points[2][0] - uv_points[0][0]
    dv2 = uv_points[2][1] - uv_points[0][1]
    j00 = du1 / e1_len
    j01 = (du2 - du1 * x2 / e1_len) / y2
    j10 = dv1 / e1_len
    j11 = (dv2 - dv1 * x2 / e1_len) / y2
    if not all(math.isfinite(v) for v in (j00, j01, j10, j11)):
        raise ArithmeticError("world-to-UV Jacobian is non-finite")
    return j00, j01, j10, j11


def _singular_values_2x2(a: float, b: float, c: float, d: float) -> tuple[float, float]:
    """Return finite nonnegative singular values in ascending order."""
    scale = max(abs(a), abs(b), abs(c), abs(d))
    if not math.isfinite(scale) or scale <= 0:
        raise ArithmeticError("texel Jacobian has no finite scale")
    na, nb, nc, nd = a / scale, b / scale, c / scale, d / scale
    sumsq = na * na + nb * nb + nc * nc + nd * nd
    det = na * nd - nb * nc
    disc = max(0.0, sumsq * sumsq - 4.0 * det * det)
    smax_n = math.sqrt(max(0.0, (sumsq + math.sqrt(disc)) * 0.5))
    if smax_n <= 0:
        raise ArithmeticError("texel Jacobian is singular")
    smin_n = abs(det) / smax_n
    smax = scale * smax_n
    smin = scale * smin_n
    if not all(math.isfinite(v) and v > 0 for v in (smin, smax)):
        raise ArithmeticError("directional texel density is non-finite or singular")
    return (min(smin, smax), max(smin, smax))


def _directional_accumulator() -> dict[str, Any]:
    return {
        "measured_triangles": 0,
        "skipped_triangles": 0,
        "world_area_m2": 0.0,
        "weighted_log_min": 0.0,
        "weighted_log_max": 0.0,
        "weighted_log_anisotropy": 0.0,
        "min_texels_per_m": float("inf"),
        "max_texels_per_m": 0.0,
        "max_anisotropy_ratio": 0.0,
    }


def _accumulate_directional(
    accumulator: dict[str, Any],
    uv_jacobian: tuple[float, float, float, float],
    width: int,
    height: int,
    weight: float,
) -> None:
    j00, j01, j10, j11 = uv_jacobian
    smin, smax = _singular_values_2x2(
        j00 * width, j01 * width, j10 * height, j11 * height
    )
    ratio = smax / smin
    accumulator["measured_triangles"] += 1
    accumulator["world_area_m2"] += weight
    accumulator["weighted_log_min"] += weight * math.log(smin)
    accumulator["weighted_log_max"] += weight * math.log(smax)
    accumulator["weighted_log_anisotropy"] += weight * math.log(ratio)
    accumulator["min_texels_per_m"] = min(accumulator["min_texels_per_m"], smin)
    accumulator["max_texels_per_m"] = max(accumulator["max_texels_per_m"], smax)
    accumulator["max_anisotropy_ratio"] = max(accumulator["max_anisotropy_ratio"], ratio)


def _directional_summary(accumulator: dict[str, Any]) -> dict[str, Any] | None:
    weight = accumulator["world_area_m2"]
    if not accumulator["measured_triangles"] or weight <= 0:
        return None
    return {
        "measured_triangles": accumulator["measured_triangles"],
        "skipped_triangles": accumulator["skipped_triangles"],
        "complete": accumulator["skipped_triangles"] == 0,
        "weighted_geometric_mean_min": math.exp(accumulator["weighted_log_min"] / weight),
        "weighted_geometric_mean_max": math.exp(accumulator["weighted_log_max"] / weight),
        "weighted_geometric_mean_anisotropy_ratio": math.exp(
            accumulator["weighted_log_anisotropy"] / weight
        ),
        "min_texels_per_m": accumulator["min_texels_per_m"],
        "max_texels_per_m": accumulator["max_texels_per_m"],
        "max_anisotropy_ratio": accumulator["max_anisotropy_ratio"],
    }


def inspect_material_uv_density(path: str | Path) -> dict[str, Any]:
    """Measure actual static GLB triangle UV scale against embedded texture sizes.

    `MEASURED` means the report contains direct byte-derived measurements. It is
    deliberately not PASS/FAIL aesthetic acceptance. A target texel density or
    anisotropy threshold is a project/art-direction decision and is not invented here.
    """
    target = Path(path).resolve()
    result: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "status": "HOLD",
        "artifact_sha256": None,
        "measurements": {"primitive_count": 0, "textured_primitive_count": 0,
                         "measured_binding_count": 0, "collapsed_uv_triangles": 0,
                         "directional_binding_count": 0,
                         "directional_skipped_triangles": 0},
        "primitives": [],
        "findings": [],
        "scope": "Actual default-scene static GLB POSITION/TEXCOORD_0/indices/transforms plus core embedded PNG/JPEG dimensions. Reports scalar area-equivalent texel density and local principal directional density/anisotropy where finite. No unwrap, rescale, anisotropy threshold, texture decode, shader/render, seam quality, style acceptance, engine import, deformation, performance, or automatic repair proof.",
    }

    def finding(code: str, **details: Any) -> None:
        if len(result["findings"]) < 64:
            result["findings"].append({"code": code, **details})

    try:
        raw = target.read_bytes()
        if len(raw) > MAX_BYTES:
            raise GeometryIssue("RESOURCE_LIMIT", "GLB exceeds 128MiB limit", hold=True)
        result["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        glb = _GLB(raw)
        doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")
        stack = [(i, IDENTITY) for i in reversed(roots)]
        seen: set[int] = set()
        triangle_total = 0
        while stack:
            node_index, parent = stack.pop()
            node = _at(doc.get("nodes"), node_index, "node")
            if node_index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(node_index)
            if len(seen) > 10000:
                raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds node limit", hold=True)
            world = _multiply(parent, _local(node))
            children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend((child, world) for child in reversed(children))
            if "mesh" not in node:
                continue
            mesh_index = _integer(node["mesh"], "mesh index")
            mesh = _at(doc.get("meshes"), mesh_index, "mesh")
            primitives = mesh.get("primitives", [])
            if not isinstance(primitives, list):
                raise GeometryIssue("INVALID_MESH", "mesh primitives must be an array")
            for primitive_index, primitive in enumerate(primitives):
                result["measurements"]["primitive_count"] += 1
                if result["measurements"]["primitive_count"] > MAX_PRIMITIVES:
                    raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds primitive limit", hold=True)
                if not isinstance(primitive, dict) or primitive.get("mode", 4) != 4 or primitive.get("targets"):
                    finding("UNSUPPORTED_PRIMITIVE", node=node.get("name"), mesh=mesh_index, primitive=primitive_index)
                    continue
                attributes = primitive.get("attributes", {})
                if not isinstance(attributes, dict) or "POSITION" not in attributes:
                    raise GeometryIssue("INVALID_PRIMITIVE", "triangle primitive is missing POSITION")
                if "TEXCOORD_0" not in attributes:
                    finding("MISSING_TEXCOORD_0", node=node.get("name"), mesh=mesh_index, primitive=primitive_index)
                    continue
                if "material" not in primitive:
                    finding("MISSING_MATERIAL", node=node.get("name"), mesh=mesh_index, primitive=primitive_index)
                    continue
                material_index = _integer(primitive["material"], "material index")
                material = _at(doc.get("materials"), material_index, "material")
                binding_rows: list[dict[str, Any]] = []
                for slot, owner, key in CORE_SLOTS:
                    source = material.get("pbrMetallicRoughness", {}) if owner == "pbr" else material
                    if not isinstance(source, dict) or key not in source:
                        continue
                    try:
                        binding_rows.append(_texture_binding(glb, slot, source[key]))
                    except GeometryIssue as exc:
                        finding(exc.code, node=node.get("name"), mesh=mesh_index, primitive=primitive_index,
                                material=material.get("name"), slot=slot, message=str(exc))
                if not binding_rows:
                    finding("NO_MEASURABLE_TEXTURE", node=node.get("name"), mesh=mesh_index,
                            primitive=primitive_index, material=material.get("name"))
                    continue
                result["measurements"]["textured_primitive_count"] += 1
                positions = glb.accessor(attributes["POSITION"], True)
                uvs = _uv_accessor(glb, attributes["TEXCOORD_0"])
                if len(positions) != len(uvs):
                    raise GeometryIssue("ATTRIBUTE_COUNT_MISMATCH", "POSITION and TEXCOORD_0 counts differ")
                if "indices" in primitive:
                    flat = [row[0] for row in glb.accessor(primitive["indices"], False)]
                else:
                    flat = list(range(len(positions)))
                if len(flat) % 3 or any(i < 0 or i >= len(positions) for i in flat):
                    raise GeometryIssue("INVALID_TRIANGLES", "triangle index data is invalid")
                triangle_total += len(flat) // 3
                if triangle_total > MAX_TRIANGLES:
                    raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds triangle review limit", hold=True)
                base_rows: list[tuple[float, float]] = []
                directional = [_directional_accumulator() for _ in binding_rows]
                world_area = uv_area = 0.0
                collapsed = 0
                uv_min = [float("inf"), float("inf")]
                uv_max = [float("-inf"), float("-inf")]
                for triangle in range(0, len(flat), 3):
                    ids = flat[triangle:triangle+3]
                    wp = [_point(world, positions[i]) for i in ids]
                    uv = [uvs[i] for i in ids]
                    for row in uv:
                        uv_min[0] = min(uv_min[0], row[0]); uv_min[1] = min(uv_min[1], row[1])
                        uv_max[0] = max(uv_max[0], row[0]); uv_max[1] = max(uv_max[1], row[1])
                    wa2 = _twice_area_3d(*wp)
                    if wa2 <= MIN_TWICE_AREA:
                        finding("DEGENERATE_WORLD_TRIANGLE", node=node.get("name"), mesh=mesh_index,
                                primitive=primitive_index, triangle=triangle // 3)
                        continue
                    ua2 = _twice_area_uv(*uv)
                    world_area += wa2 * .5
                    uv_area += ua2 * .5
                    if ua2 <= MIN_TWICE_AREA:
                        collapsed += 1
                        continue
                    weight = wa2 * .5
                    base_rows.append((math.sqrt(ua2 / wa2), weight))
                    try:
                        uv_jacobian = _uv_world_jacobian(wp, uv)
                    except ArithmeticError as exc:
                        for accumulator in directional:
                            accumulator["skipped_triangles"] += 1
                        result["measurements"]["directional_skipped_triangles"] += len(binding_rows)
                        finding("DIRECTIONAL_UV_UNMEASURABLE", node=node.get("name"), mesh=mesh_index,
                                primitive=primitive_index, triangle=triangle // 3, message=str(exc))
                        continue
                    for binding_index, binding in enumerate(binding_rows):
                        try:
                            _accumulate_directional(
                                directional[binding_index], uv_jacobian,
                                binding["width"], binding["height"], weight,
                            )
                        except (ArithmeticError, OverflowError, ValueError) as exc:
                            directional[binding_index]["skipped_triangles"] += 1
                            result["measurements"]["directional_skipped_triangles"] += 1
                            finding("DIRECTIONAL_UV_UNMEASURABLE", node=node.get("name"),
                                    mesh=mesh_index, primitive=primitive_index,
                                    triangle=triangle // 3, slot=binding["slot"], message=str(exc))
                result["measurements"]["collapsed_uv_triangles"] += collapsed
                if collapsed:
                    finding("UV_COLLAPSE", node=node.get("name"), mesh=mesh_index, primitive=primitive_index,
                            triangles=collapsed)
                if not base_rows:
                    finding("NO_MEASURABLE_UV_AREA", node=node.get("name"), mesh=mesh_index, primitive=primitive_index)
                    continue
                binding_reports = []
                for binding_index, binding in enumerate(binding_rows):
                    summary = _density_summary(base_rows, binding["width"], binding["height"])
                    row = {**binding, "texels_per_m": summary}
                    directional_summary = _directional_summary(directional[binding_index])
                    if directional_summary is not None:
                        row["directional_texels_per_m"] = directional_summary
                        result["measurements"]["directional_binding_count"] += 1
                    binding_reports.append(row)
                    result["measurements"]["measured_binding_count"] += 1
                    if (binding["wrap_s"] == 33071 and (uv_min[0] < 0 or uv_max[0] > 1)
                            or binding["wrap_t"] == 33071 and (uv_min[1] < 0 or uv_max[1] > 1)):
                        finding("UV_OUTSIDE_CLAMP", node=node.get("name"), mesh=mesh_index, primitive=primitive_index,
                                slot=binding["slot"], uv_bounds={"min": uv_min, "max": uv_max})
                result["primitives"].append({
                    "node": node.get("name"), "mesh": mesh_index, "primitive": primitive_index,
                    "material_index": material_index, "material": material.get("name"),
                    "triangles": len(flat) // 3, "measured_triangles": len(base_rows),
                    "collapsed_uv_triangles": collapsed, "world_area_m2": world_area, "uv_area": uv_area,
                    "uv_bounds": {"min": uv_min, "max": uv_max}, "bindings": binding_reports,
                })
        if result["measurements"]["measured_binding_count"]:
            result["status"] = "MEASURED"
        else:
            finding("NO_MEASURABLE_BINDINGS")
    except GeometryIssue as exc:
        finding(exc.code, message=str(exc))
        result["status"] = "HOLD" if exc.hold else "FAIL"
    except (OSError, ValueError, TypeError, KeyError, IndexError, struct.error, json.JSONDecodeError) as exc:
        finding("INVALID_INPUT", message=str(exc))
        result["status"] = "FAIL"
    return result

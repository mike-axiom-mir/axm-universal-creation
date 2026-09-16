"""Deterministic offline connected-chart UV unwrap and material atlas bake.

This remains a bounded native UC route from supplied surface geometry without UVs
to an embedded textured GLB. It groups edge-connected triangles only when their
geometric face normals remain within an explicit seam angle. Hard edges,
disconnected topology and uncertain adjacency therefore stay separated.

It deliberately does not claim global seam optimization, density-optimal packing,
high-to-low transfer, cage baking, AO/curvature synthesis, MikkTSpace parity or
artistic acceptance.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path

from .atomic import atomic_write_json
from .fabric_noise import png_bytes
from .game_material_bridge import load_material_bundle
from .native_textures import SLOTS, decode_png, texture_set_from_bundle
from .procedural_3d import build_glb

SCHEMA = "axm.auto-unwrap-bake/v1"
METHOD = "connected-planar-chart-grid-v2"
_EPS = 1e-9


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _options(raw):
    raw = {} if raw is None else raw
    allowed = {"atlas_size", "padding_px", "seam_angle_degrees"}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError("unwrap_bake accepts only atlas_size, padding_px and seam_angle_degrees")
    atlas = raw.get("atlas_size", 256)
    padding = raw.get("padding_px", 4)
    seam_angle = raw.get("seam_angle_degrees", 35.0)
    if type(atlas) is not int or not 32 <= atlas <= 2048:
        raise ValueError("atlas_size must be an integer from 32..2048")
    if type(padding) is not int or not 1 <= padding <= 64:
        raise ValueError("padding_px must be an integer from 1..64")
    if type(seam_angle) not in (int, float) or not math.isfinite(seam_angle) or not 0 <= seam_angle <= 89:
        raise ValueError("seam_angle_degrees must be finite from 0..89")
    return {"atlas_size": atlas, "padding_px": padding, "seam_angle_degrees": float(seam_angle)}


def _sample(pixels, width, height, u, v):
    x = min(width - 1, max(0, round(u * (width - 1))))
    y = min(height - 1, max(0, round(v * (height - 1))))
    offset = (y * width + x) * 3
    return pixels[offset:offset + 3]


def _material_pixels(bundle):
    converted = texture_set_from_bundle(bundle, wrap="clamp")
    decoded = {}
    for slot in SLOTS:
        decoded[slot] = decode_png(base64.b64decode(converted[slot], validate=True))
    return decoded


def _grid(chart_count, atlas, padding):
    columns = math.ceil(math.sqrt(chart_count))
    rows = math.ceil(chart_count / columns)
    cell_w, cell_h = atlas // columns, atlas // rows
    if cell_w < 2 * padding + 3 or cell_h < 2 * padding + 3:
        raise ValueError("atlas is too small for chart count and requested padding")
    return columns, rows, cell_w, cell_h


def _sub(a, b):
    return [a[i] - b[i] for i in range(3)]


def _cross(a, b):
    return [a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0]]


def _unit(value):
    length = math.sqrt(sum(component * component for component in value))
    if not math.isfinite(length) or length <= _EPS:
        raise ValueError("automatic unwrap rejects degenerate triangles")
    return [component / length for component in value]


def _face_normal(positions, triangle):
    a, b, c = (positions[index] for index in triangle)
    return _unit(_cross(_sub(b, a), _sub(c, a)))


def _connected_charts(positions, indices, seam_angle_degrees):
    triangles = [indices[offset:offset + 3] for offset in range(0, len(indices), 3)]
    normals = [_face_normal(positions, triangle) for triangle in triangles]
    edges = {}
    for triangle_id, triangle in enumerate(triangles):
        for a, b in ((triangle[0], triangle[1]), (triangle[1], triangle[2]), (triangle[2], triangle[0])):
            edges.setdefault(tuple(sorted((a, b))), []).append(triangle_id)

    neighbors = {triangle_id: set() for triangle_id in range(len(triangles))}
    nonmanifold_edges = 0
    for linked in edges.values():
        if len(linked) == 2:
            a, b = linked
            neighbors[a].add(b)
            neighbors[b].add(a)
        elif len(linked) > 2:
            # Ambiguous topology is not silently merged across.
            nonmanifold_edges += 1

    threshold = math.cos(math.radians(seam_angle_degrees))
    assigned = set()
    charts = []
    for seed in range(len(triangles)):
        if seed in assigned:
            continue
        seed_normal = normals[seed]
        chart = []
        queue = [seed]
        assigned.add(seed)
        while queue:
            current = queue.pop(0)
            chart.append(current)
            for candidate in sorted(neighbors[current]):
                if candidate in assigned:
                    continue
                pair_dot = sum(normals[current][axis] * normals[candidate][axis] for axis in range(3))
                seed_dot = sum(seed_normal[axis] * normals[candidate][axis] for axis in range(3))
                if pair_dot + 1e-12 >= threshold and seed_dot + 1e-12 >= threshold:
                    assigned.add(candidate)
                    queue.append(candidate)
        charts.append(sorted(chart))
    return triangles, normals, charts, nonmanifold_edges


def _projection_axis(normal):
    # Drop the axis most aligned with the face normal. The remaining two axes
    # form a deterministic planar projection for the bounded connected chart.
    return max(range(3), key=lambda axis: (abs(normal[axis]), -axis))


def _project(position, dropped_axis):
    axes = [axis for axis in range(3) if axis != dropped_axis]
    return position[axes[0]], position[axes[1]]


def _chart_projection(positions, triangles, chart, seed_normal):
    dropped = _projection_axis(seed_normal)
    vertices = []
    seen = set()
    for triangle_id in chart:
        for source_index in triangles[triangle_id]:
            if source_index not in seen:
                seen.add(source_index)
                vertices.append(source_index)
    projected = {source_index: _project(positions[source_index], dropped) for source_index in vertices}
    min_u = min(value[0] for value in projected.values())
    max_u = max(value[0] for value in projected.values())
    min_v = min(value[1] for value in projected.values())
    max_v = max(value[1] for value in projected.values())
    if max_u - min_u <= _EPS or max_v - min_v <= _EPS:
        raise ValueError("automatic unwrap chart projection collapsed")
    return dropped, vertices, projected, (min_u, min_v, max_u, max_v)


def _bake_group(group, bundle, options):
    if "texcoords" in group or "textures" in group:
        raise ValueError("automatic unwrap refuses geometry that already carries UVs or textures")
    positions, normals, indices = group.get("positions"), group.get("normals"), group.get("indices")
    if not isinstance(positions, list) or not isinstance(normals, list) or len(normals) != len(positions):
        raise ValueError("automatic unwrap requires explicit positions and matching normals")
    if not isinstance(indices, list) or not indices or len(indices) % 3:
        raise ValueError("automatic unwrap requires indexed triangles")
    if any(type(index) is not int or not 0 <= index < len(positions) for index in indices):
        raise ValueError("automatic unwrap index is out of range")
    if "colors" in group and (not isinstance(group["colors"], list) or len(group["colors"]) != len(positions)):
        raise ValueError("automatic unwrap color count must match positions")

    triangle_count = len(indices) // 3
    seam_angle = options["seam_angle_degrees"]
    triangles, face_normals, charts, nonmanifold_edges = _connected_charts(
        positions, indices, seam_angle
    )
    atlas, padding = options["atlas_size"], options["padding_px"]
    columns, rows, cell_w, cell_h = _grid(len(charts), atlas, padding)
    source = _material_pixels(bundle)
    atlases = {slot: bytearray(atlas * atlas * 3) for slot in SLOTS}
    out_positions, out_normals, out_indices, texcoords = [], [], [], []
    out_colors = [] if "colors" in group else None
    chart_receipts = []

    for chart_id, chart in enumerate(charts):
        column, row = chart_id % columns, chart_id // columns
        x0, y0 = column * cell_w, row * cell_h
        x1, y1 = x0 + cell_w - 1, y0 + cell_h - 1
        inner_x0, inner_y0 = x0 + padding, y0 + padding
        inner_x1, inner_y1 = x1 - padding, y1 - padding

        # The entire cell receives source material data. Pixels outside the inner
        # rectangle clamp to its edge, making the requested gutter real data.
        for py in range(y0, y1 + 1):
            v = (min(inner_y1, max(inner_y0, py)) - inner_y0) / max(1, inner_y1 - inner_y0)
            for px in range(x0, x1 + 1):
                u = (min(inner_x1, max(inner_x0, px)) - inner_x0) / max(1, inner_x1 - inner_x0)
                dest = (py * atlas + px) * 3
                for slot, (width, height, pixels) in source.items():
                    atlases[slot][dest:dest + 3] = _sample(pixels, width, height, u, v)

        seed_normal = face_normals[chart[0]]
        dropped, source_vertices, projected, bounds = _chart_projection(
            positions, triangles, chart, seed_normal
        )
        min_u, min_v, max_u, max_v = bounds
        vertex_map = {}

        def output_vertex(source_index):
            if source_index in vertex_map:
                return vertex_map[source_index]
            normalized_u = (projected[source_index][0] - min_u) / (max_u - min_u)
            normalized_v = (projected[source_index][1] - min_v) / (max_v - min_v)
            px = inner_x0 + normalized_u * (inner_x1 - inner_x0)
            py = inner_y0 + normalized_v * (inner_y1 - inner_y0)
            uv = [(px + .5) / atlas, 1 - (py + .5) / atlas]
            output_index = len(out_positions)
            vertex_map[source_index] = output_index
            out_positions.append(copy.deepcopy(positions[source_index]))
            out_normals.append(copy.deepcopy(normals[source_index]))
            texcoords.append(uv)
            if out_colors is not None:
                out_colors.append(copy.deepcopy(group["colors"][source_index]))
            return output_index

        for triangle_id in chart:
            out_indices.extend(output_vertex(source_index) for source_index in triangles[triangle_id])

        chart_receipts.append({
            "chart": chart_id,
            "triangles": chart,
            "triangle_count": len(chart),
            "source_vertex_count": len(source_vertices),
            "projection_drop_axis": dropped,
            "cell": [x0, y0, x1, y1],
            "inner": [inner_x0, inner_y0, inner_x1, inner_y1],
        })

    encoded = {slot: png_bytes(atlas, atlas, 3, bytes(pixels)) for slot, pixels in atlases.items()}
    baked = copy.deepcopy(group)
    baked["positions"], baked["normals"], baked["indices"] = out_positions, out_normals, out_indices
    baked["texcoords"] = texcoords
    if out_colors is not None:
        baked["colors"] = out_colors
    baked["textures"] = {
        **{slot: base64.b64encode(data).decode("ascii") for slot, data in encoded.items()},
        "normal_convention": "tangent +Y",
        "wrap": "clamp",
    }
    receipt = {
        "group": group["id"],
        "method": METHOD,
        "triangle_count": triangle_count,
        "chart_count": len(charts),
        "source_vertices": len(positions),
        "baked_vertices": len(out_positions),
        "saved_vertex_duplicates_vs_triangle_fallback": triangle_count * 3 - len(out_positions),
        "atlas_size": atlas,
        "padding_px": padding,
        "seam_angle_degrees": seam_angle,
        "columns": columns,
        "rows": rows,
        "nonmanifold_edges_left_as_seams": nonmanifold_edges,
        "overlap_free_by_construction": True,
        "charts": chart_receipts,
        "material_manifest_sha256": bundle["manifest_sha256"],
        "atlas_sha256": {slot: hashlib.sha256(data).hexdigest() for slot, data in encoded.items()},
    }
    return baked, encoded, receipt


def prepare(specification, materials, options=None, *, resolve_material):
    options = _options(options)
    spec = copy.deepcopy(specification)
    if not isinstance(spec, dict) or spec.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("automatic unwrap requires axm.surface-3d/v0.1 geometry")
    groups = spec.get("primitives")
    if not isinstance(groups, list) or not groups:
        raise ValueError("automatic unwrap requires at least one surface group")
    if not isinstance(materials, dict) or set(materials) != {group.get("id") for group in groups}:
        raise ValueError("automatic unwrap materials must map every surface group exactly once")

    receipts, external = [], {}
    for index, group in enumerate(groups):
        binding = materials[group["id"]]
        if not isinstance(binding, dict) or set(binding) - {"path", "wrap"} or "path" not in binding:
            raise ValueError("automatic unwrap material binding requires path and optional wrap")
        if binding.get("wrap", "clamp") != "clamp":
            raise ValueError("baked atlases use clamp wrapping; repeat is a source-material concern")
        bundle = load_material_bundle(resolve_material(binding["path"]))
        baked, images, receipt = _bake_group(group, bundle, options)
        groups[index] = baked
        external[group["id"]] = images
        receipts.append(receipt)

    built = build_glb(spec)
    total_triangles = sum(row["triangle_count"] for row in receipts)
    total_charts = sum(row["chart_count"] for row in receipts)
    receipt = {
        "schema": SCHEMA,
        "method": METHOD,
        "status": "PASS",
        "source_specification_sha256": hashlib.sha256(_canonical(specification)).hexdigest(),
        "output_specification_sha256": built["specification_sha256"],
        "asset_sha256": hashlib.sha256(built["body"]).hexdigest(),
        "options": options,
        "groups": receipts,
        "measurements": {
            "triangle_count": total_triangles,
            "chart_count": total_charts,
            "triangles_per_chart": total_triangles / total_charts,
        },
        "checks": [
            {"type": "edge-connected-angle-bounded-chart-grouping", "passed": True},
            {"type": "nonoverlapping-chart-cells", "passed": True},
            {"type": "explicit-atlas-padding", "passed": True},
            {"type": "embedded-baked-textures", "passed": True},
        ],
        "visual_quality": "NOT_TESTED",
        "professional_acceptance": "NOT_TESTED",
        "limitations": [
            "Connected charts reduce unnecessary seams on locally planar topology; they do not solve global seam aesthetics or density-optimal packing.",
            "Nonmanifold edges, disconnected topology and faces beyond seam_angle_degrees remain separate by construction.",
            "Bake transfers the supplied material bundle into chart-local planar space; it does not perform high-to-low, cage, AO, curvature or thickness baking.",
            "Tangent-space output uses UC's current triangle-derived tangent path; MikkTSpace/target-engine parity remains unverified.",
            "Technical PASS does not accept aesthetics, material realism, seam placement or final release.",
        ],
    }
    return {"specification": spec, "body": built["body"], "atlases": external, "receipt": receipt}


def build_directory(target, specification, materials, options, *, resolve_material):
    target = Path(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError("automatic unwrap/bake refuses to overwrite: " + str(target))
    result = prepare(specification, materials, options, resolve_material=resolve_material)
    staging = Path(tempfile.mkdtemp(prefix=target.name + ".staging-", dir=target.parent))
    try:
        (staging / "atlases").mkdir()
        (staging / "asset.glb").write_bytes(result["body"])
        for group, slots in result["atlases"].items():
            for slot, payload in slots.items():
                (staging / "atlases" / f"{group}-{slot}.png").write_bytes(payload)
        atomic_write_json(staging / "receipt.json", result["receipt"])
        os.replace(staging, target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return result["receipt"]


def verify_directory(target, specification, materials, options, *, resolve_material):
    target = Path(target)
    result = prepare(specification, materials, options, resolve_material=resolve_material)
    stored = json.loads((target / "receipt.json").read_text(encoding="utf-8"))
    checks = [
        {"type": "fresh-unwrap-bake-receipt", "passed": stored == result["receipt"]},
        {"type": "fresh-exact-baked-glb", "passed": (target / "asset.glb").read_bytes() == result["body"]},
    ]
    for group, slots in result["atlases"].items():
        for slot, payload in slots.items():
            path = target / "atlases" / f"{group}-{slot}.png"
            checks.append({
                "type": f"fresh-atlas:{group}:{slot}",
                "passed": path.is_file() and path.read_bytes() == payload,
            })
    return {
        "status": "PASS" if all(row["passed"] for row in checks) else "FAIL",
        "checks": checks,
        "receipt": result["receipt"],
        "visual_quality": "NOT_TESTED",
        "professional_acceptance": "NOT_TESTED",
    }

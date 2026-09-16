"""Deterministic offline triangle-chart UV unwrap and material atlas bake.

This is the smallest native UC path from supplied surface geometry without UVs to
an embedded textured GLB. It deliberately does not claim smart seam selection,
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
METHOD = "triangle-chart-grid-v1"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _options(raw):
    raw = {} if raw is None else raw
    allowed = {"atlas_size", "padding_px"}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise ValueError("unwrap_bake accepts only atlas_size and padding_px")
    atlas = raw.get("atlas_size", 256)
    padding = raw.get("padding_px", 4)
    if type(atlas) is not int or not 32 <= atlas <= 2048:
        raise ValueError("atlas_size must be an integer from 32..2048")
    if type(padding) is not int or not 1 <= padding <= 64:
        raise ValueError("padding_px must be an integer from 1..64")
    return {"atlas_size": atlas, "padding_px": padding}


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


def _grid(triangle_count, atlas, padding):
    columns = math.ceil(math.sqrt(triangle_count))
    rows = math.ceil(triangle_count / columns)
    cell_w, cell_h = atlas // columns, atlas // rows
    if cell_w < 2 * padding + 3 or cell_h < 2 * padding + 3:
        raise ValueError("atlas is too small for triangle count and requested padding")
    return columns, rows, cell_w, cell_h


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
    triangle_count = len(indices) // 3
    atlas, padding = options["atlas_size"], options["padding_px"]
    columns, rows, cell_w, cell_h = _grid(triangle_count, atlas, padding)
    source = _material_pixels(bundle)
    atlases = {slot: bytearray(atlas * atlas * 3) for slot in SLOTS}
    out_positions, out_normals, out_indices, texcoords = [], [], [], []
    out_colors = [] if "colors" in group else None
    chart_receipts = []

    for triangle in range(triangle_count):
        column, row = triangle % columns, triangle // columns
        x0, y0 = column * cell_w, row * cell_h
        x1, y1 = x0 + cell_w - 1, y0 + cell_h - 1
        inner_x0, inner_y0 = x0 + padding, y0 + padding
        inner_x1, inner_y1 = x1 - padding, y1 - padding
        # Fill the full cell. Values outside the inner UV island are clamped edge
        # dilation, giving each chart a real gutter instead of black gaps.
        for py in range(y0, y1 + 1):
            v = (min(inner_y1, max(inner_y0, py)) - inner_y0) / max(1, inner_y1 - inner_y0)
            for px in range(x0, x1 + 1):
                u = (min(inner_x1, max(inner_x0, px)) - inner_x0) / max(1, inner_x1 - inner_x0)
                dest = (py * atlas + px) * 3
                for slot, (width, height, pixels) in source.items():
                    atlases[slot][dest:dest + 3] = _sample(pixels, width, height, u, v)
        source_indices = indices[triangle * 3:triangle * 3 + 3]
        base = len(out_positions)
        for source_index in source_indices:
            out_positions.append(copy.deepcopy(positions[source_index]))
            out_normals.append(copy.deepcopy(normals[source_index]))
            if out_colors is not None:
                out_colors.append(copy.deepcopy(group["colors"][source_index]))
        out_indices.extend([base, base + 1, base + 2])
        # Pixel-center inset. Each face becomes its own chart, so overlap is
        # impossible by construction and arbitrary source topology needs no seams.
        uv_left = (inner_x0 + .5) / atlas
        uv_right = (inner_x1 + .5) / atlas
        uv_top = 1 - (inner_y0 + .5) / atlas
        uv_bottom = 1 - (inner_y1 + .5) / atlas
        texcoords.extend([[uv_left, uv_bottom], [uv_right, uv_bottom], [uv_left, uv_top]])
        chart_receipts.append({"triangle": triangle, "cell": [x0, y0, x1, y1],
                               "inner": [inner_x0, inner_y0, inner_x1, inner_y1]})

    encoded = {slot: png_bytes(atlas, atlas, 3, bytes(pixels)) for slot, pixels in atlases.items()}
    baked = copy.deepcopy(group)
    baked["positions"], baked["normals"], baked["indices"] = out_positions, out_normals, out_indices
    baked["texcoords"] = texcoords
    if out_colors is not None:
        baked["colors"] = out_colors
    baked["textures"] = {**{slot: base64.b64encode(data).decode("ascii") for slot, data in encoded.items()},
                         "normal_convention": "tangent +Y", "wrap": "clamp"}
    receipt = {"group": group["id"], "method": METHOD, "triangle_count": triangle_count,
               "source_vertices": len(positions), "baked_vertices": len(out_positions),
               "atlas_size": atlas, "padding_px": padding, "columns": columns, "rows": rows,
               "overlap_free_by_construction": True, "charts": chart_receipts,
               "material_manifest_sha256": bundle["manifest_sha256"],
               "atlas_sha256": {slot: hashlib.sha256(data).hexdigest() for slot, data in encoded.items()}}
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
    receipt = {"schema": SCHEMA, "method": METHOD, "status": "PASS",
               "source_specification_sha256": hashlib.sha256(_canonical(specification)).hexdigest(),
               "output_specification_sha256": built["specification_sha256"],
               "asset_sha256": hashlib.sha256(built["body"]).hexdigest(),
               "options": options, "groups": receipts,
               "checks": [{"type": "unique-triangle-charts", "passed": True},
                          {"type": "explicit-atlas-padding", "passed": True},
                          {"type": "embedded-baked-textures", "passed": True}],
               "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED",
               "limitations": [
                   "Triangle-per-chart is a deterministic fallback, not smart seam selection or density-optimal packing.",
                   "Bake transfers the supplied material bundle into chart-local 0..1 space; it does not perform high-to-low, cage, AO, curvature or thickness baking.",
                   "Tangent-space output uses UC's current triangle-derived tangent path; MikkTSpace/target-engine parity remains unverified.",
                   "Technical PASS does not accept aesthetics, material realism, seam placement or final release."
               ]}
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
    checks = [{"type": "fresh-unwrap-bake-receipt", "passed": stored == result["receipt"]},
              {"type": "fresh-exact-baked-glb", "passed": (target / "asset.glb").read_bytes() == result["body"]}]
    for group, slots in result["atlases"].items():
        for slot, payload in slots.items():
            path = target / "atlases" / f"{group}-{slot}.png"
            checks.append({"type": f"fresh-atlas:{group}:{slot}", "passed": path.is_file() and path.read_bytes() == payload})
    return {"status": "PASS" if all(row["passed"] for row in checks) else "FAIL", "checks": checks,
            "receipt": result["receipt"], "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED"}

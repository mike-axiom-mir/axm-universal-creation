"""Bounded static GLB resource-budget evidence.

This module measures the instantiated default-scene resource surface of a core
embedded GLB against an explicit caller-supplied budget. It is deliberately not
an FPS, engine-import, collision, navigation, LOD-equivalence, or visual-quality
claim. Unsupported encodings/deformation HOLD rather than being guessed through.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .asset_geometry import GeometryIssue, MAX_BYTES, _GLB, _at, _integer
from .material_uv_evidence import _material_bindings

BUDGET_SCHEMA = "axm.static-asset-budget/v0.1"
EVIDENCE_SCHEMA = "axm.static-asset-budget-evidence/v0.1"
MAX_NODES = 10_000
MAX_PRIMITIVES = 4096
_ALLOWED_MATERIAL_EXTENSIONS = {"KHR_materials_emissive_strength", "KHR_materials_unlit"}
_LIMIT_FIELDS = (
    "max_triangles",
    "max_vertices",
    "max_primitives",
    "max_material_batches",
    "max_unique_materials",
    "max_embedded_images",
    "max_compressed_image_bytes",
    "max_estimated_rgba8_mip_bytes",
    "max_double_sided_materials",
    "max_double_sided_batches",
)


def validate_static_asset_budget(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != BUDGET_SCHEMA:
        raise ValueError("invalid static asset budget schema")
    unknown = set(value) - ({"schema"} | set(_LIMIT_FIELDS))
    if unknown:
        raise ValueError(f"unknown static asset budget field(s): {sorted(unknown)}")
    if not any(name in value for name in _LIMIT_FIELDS):
        raise ValueError("static asset budget must declare at least one maximum")
    for name in _LIMIT_FIELDS:
        if name in value and (type(value[name]) is not int or value[name] < 0):
            raise ValueError(f"{name} must be an integer >= 0")
    return json.loads(json.dumps(value, sort_keys=True, allow_nan=False))


def _rgba8_mip_bytes(width: int, height: int) -> int:
    total = 0
    w, h = width, height
    while True:
        total += w * h * 4
        if w == 1 and h == 1:
            return total
        w, h = max(1, w // 2), max(1, h // 2)


def inspect_static_asset_budget(path: str | Path, budget: Any) -> dict[str, Any]:
    """Measure one static GLB and compare it with an explicit resource budget.

    Triangle/vertex/primitive/material-batch counts are instantiated default-scene
    counts: a reused mesh contributes once per node instance. Unique material and
    embedded-image counts are deduplicated identities referenced by those batches.
    Expanded RGBA8 mip bytes are a deterministic uncompressed estimate based on
    embedded image dimensions, not a prediction of engine memory or compression.
    """
    spec = validate_static_asset_budget(budget)
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    target = Path(path).resolve()
    result: dict[str, Any] = {
        "schema": EVIDENCE_SCHEMA,
        "status": "HOLD",
        "artifact_sha256": None,
        "budget_sha256": hashlib.sha256(encoded).hexdigest(),
        "budget": spec,
        "measurements": {},
        "referenced_images": [],
        "findings": [],
        "finding_count": 0,
        "finding_counts": {},
        "scope": (
            "Actual instantiated default-scene static core GLB triangle/vertex/primitive/material usage and "
            "core embedded PNG/JPEG byte/dimension evidence. No FPS, target-engine import, draw-call timing, "
            "GPU compression/memory, collision/navigation, LOD perceptual equivalence, gameplay readability, "
            "aesthetic acceptance, or automatic optimization proof."
        ),
    }

    def finding(code: str, **details: Any) -> None:
        result["finding_count"] += 1
        result["finding_counts"][code] = result["finding_counts"].get(code, 0) + 1
        if len(result["findings"]) < 64:
            result["findings"].append({"code": code, **details})

    try:
        raw = target.read_bytes()
        if len(raw) > MAX_BYTES:
            raise GeometryIssue("RESOURCE_LIMIT", "GLB exceeds 128MiB inspection limit", hold=True)
        result["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        glb = _GLB(raw)
        doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")

        stack = list(reversed(roots))
        seen: set[int] = set()
        used_materials: set[int | None] = set()
        material_batches: list[int | None] = []
        triangles = vertices = primitives = mesh_instances = 0

        while stack:
            node_index = _integer(stack.pop(), "node index")
            node = _at(doc.get("nodes"), node_index, "node")
            if node_index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(node_index)
            if len(seen) > MAX_NODES:
                raise GeometryIssue("RESOURCE_LIMIT", "default scene exceeds node limit", hold=True)
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_NODE", "skinned, weighted or extended nodes need separate budget evidence", hold=True)
            children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend(reversed(children))
            if "mesh" not in node:
                continue

            mesh_instances += 1
            mesh = _at(doc.get("meshes"), node["mesh"], "mesh")
            if mesh.get("weights") or mesh.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_MESH", "weighted or extended meshes need separate budget evidence", hold=True)
            rows = mesh.get("primitives", [])
            if not isinstance(rows, list) or not rows:
                raise GeometryIssue("INVALID_MESH", "mesh primitives must be a non-empty array")
            for primitive in rows:
                primitives += 1
                if primitives > MAX_PRIMITIVES:
                    raise GeometryIssue("RESOURCE_LIMIT", "instantiated primitive count exceeds inspection limit", hold=True)
                if not isinstance(primitive, dict) or primitive.get("mode", 4) != 4:
                    raise GeometryIssue("UNSUPPORTED_PRIMITIVE", "budget evidence supports TRIANGLES primitives only", hold=True)
                if primitive.get("targets") or primitive.get("extensions"):
                    raise GeometryIssue("UNSUPPORTED_PRIMITIVE", "morph/extended primitives need separate budget evidence", hold=True)
                attributes = primitive.get("attributes")
                if not isinstance(attributes, dict) or "POSITION" not in attributes:
                    raise GeometryIssue("INVALID_PRIMITIVE", "TRIANGLES primitive requires POSITION")
                positions = glb.accessor(_integer(attributes["POSITION"], "POSITION accessor index"), True)
                vertex_count = len(positions)
                vertices += vertex_count
                if "indices" in primitive:
                    indices = glb.accessor(_integer(primitive["indices"], "index accessor index"), False)
                    if len(indices) % 3:
                        raise GeometryIssue("INVALID_TRIANGLES", "index accessor count must be divisible by three")
                    if any(index[0] >= vertex_count for index in indices):
                        raise GeometryIssue("INVALID_INDEX", "triangle index exceeds POSITION accessor")
                    triangles += len(indices) // 3
                else:
                    if vertex_count % 3:
                        raise GeometryIssue("INVALID_TRIANGLES", "non-indexed TRIANGLES POSITION count must be divisible by three")
                    triangles += vertex_count // 3

                material_index: int | None = None
                if "material" in primitive:
                    material_index = _integer(primitive["material"], "material index")
                    _at(doc.get("materials"), material_index, "material")
                used_materials.add(material_index)
                material_batches.append(material_index)

        if not primitives:
            raise GeometryIssue("EMPTY_GEOMETRY", "default scene contains no TRIANGLES primitives")

        double_sided_materials: set[int] = set()
        image_records: dict[int, dict[str, Any]] = {}
        texture_indices: set[int] = set()
        for material_index in sorted(index for index in used_materials if index is not None):
            material = _at(doc.get("materials"), material_index, "material")
            if type(material.get("doubleSided", False)) is not bool:
                raise GeometryIssue("INVALID_MATERIAL", "doubleSided must be boolean")
            if material.get("doubleSided", False):
                double_sided_materials.add(material_index)
            extensions = material.get("extensions", {})
            if not isinstance(extensions, dict) or set(extensions) - _ALLOWED_MATERIAL_EXTENSIONS:
                raise GeometryIssue("UNSUPPORTED_MATERIAL_EXTENSION", "material extension may change resource bindings", hold=True)
            for record in _material_bindings(glb, material):
                texture_indices.add(record["texture_index"])
                image_index = record["image_index"]
                compact = {
                    "image_index": image_index,
                    "mime_type": record["mime_type"],
                    "width": record["width"],
                    "height": record["height"],
                    "sha256": record["sha256"],
                    "byte_length": record["byte_length"],
                }
                previous = image_records.get(image_index)
                if previous is not None and previous != compact:
                    raise GeometryIssue("INCONSISTENT_IMAGE", "one image index resolved to inconsistent evidence")
                image_records[image_index] = compact

        double_sided_batches = sum(1 for index in material_batches if index in double_sided_materials)
        compressed_image_bytes = sum(row["byte_length"] for row in image_records.values())
        estimated_rgba8_mip_bytes = sum(
            _rgba8_mip_bytes(row["width"], row["height"]) for row in image_records.values()
        )
        measurements = {
            "node_count": len(seen),
            "mesh_instance_count": mesh_instances,
            "triangle_count": triangles,
            "vertex_count": vertices,
            "primitive_count": primitives,
            "material_batch_count": len(material_batches),
            "unique_material_count": len(used_materials),
            "unique_texture_count": len(texture_indices),
            "embedded_image_count": len(image_records),
            "compressed_image_bytes": compressed_image_bytes,
            "estimated_rgba8_mip_bytes": estimated_rgba8_mip_bytes,
            "double_sided_material_count": len(double_sided_materials),
            "double_sided_batch_count": double_sided_batches,
        }
        result["measurements"] = measurements
        result["referenced_images"] = [image_records[index] for index in sorted(image_records)]

        mapping = {
            "max_triangles": "triangle_count",
            "max_vertices": "vertex_count",
            "max_primitives": "primitive_count",
            "max_material_batches": "material_batch_count",
            "max_unique_materials": "unique_material_count",
            "max_embedded_images": "embedded_image_count",
            "max_compressed_image_bytes": "compressed_image_bytes",
            "max_estimated_rgba8_mip_bytes": "estimated_rgba8_mip_bytes",
            "max_double_sided_materials": "double_sided_material_count",
            "max_double_sided_batches": "double_sided_batch_count",
        }
        for limit_name, metric_name in mapping.items():
            if limit_name in spec and measurements[metric_name] > spec[limit_name]:
                finding("BUDGET_EXCEEDED", limit=limit_name, metric=metric_name,
                        actual=measurements[metric_name], maximum=spec[limit_name])
        result["status"] = "FAIL" if result["finding_counts"].get("BUDGET_EXCEEDED") else "PASS"
        return result
    except GeometryIssue as exc:
        finding(exc.code, message=str(exc))
        result["status"] = "HOLD" if exc.hold else "FAIL"
        return result
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        finding("INVALID_ARTIFACT", message=str(exc))
        result["status"] = "FAIL"
        return result

from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

from axm_stickers.assembly import ASSEMBLY, expand
from axm_stickers.core import Registry, resolve
from axm_stickers.placement import attachment_matrix, identity, inverse_rigid, multiply, rigid

from .asset_geometry import (
    GeometryIssue,
    IDENTITY as GLTF_IDENTITY,
    MAX_TRIANGLES,
    MIN_TWICE_AREA_M2,
    _GLB,
    _at,
    _local,
    _multiply as gltf_multiply,
    _point as gltf_point,
)
from .design_workshop import validate_sketch
from .design_workshop_construction import _exact_definition, _pin, compare_sticker_assembly
from .game_pose_runtime import GamePoseAsset, _parse
from .sticker_adapter import GLB
from .sticker_multiplier import _machine_body, _resolve_registry_path

GEOMETRY_REPORT_SCHEMA = "axm.sticker-geometry-calipers/v0.1"
ASSEMBLY_GEOMETRY_SCHEMA = "axm.sticker-assembly-geometry-calipers/v0.1"
WORKSHOP_GEOMETRY_SCHEMA = "axm.design-sticker-geometry-report/v0.1"
MAX_TRANSFORMED_POINTS = 2_000_000

CALIPER_OPERATIONS = {
    "inspect-geometry-calipers",
    "measure-sticker-geometry",
    "measure-sticker-assembly-parts",
    "compare-sticker-geometry",
}


class StickerGeometryCaliperError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class _MeasureIssue(RuntimeError):
    def __init__(self, status: str, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _q(value: float) -> float:
    result = round(float(value), 12)
    return 0.0 if result == -0.0 else result


def _flat_point(matrix: list[float], point: tuple[float, float, float] | list[float]) -> list[float]:
    return [sum(matrix[row * 4 + column] * point[column] for column in range(3)) + matrix[row * 4 + 3]
            for row in range(3)]


def _encode_geometry_view(document: dict[str, Any], binary: bytes) -> bytes:
    clean = copy.deepcopy(document)
    clean.pop("animations", None)
    # game_pose_runtime._parse has already restricted required extensions to
    # non-pose material/texture extensions. They do not alter POSITION bytes or
    # node transforms, so the geometry-only view need not implement them.
    clean.pop("extensionsRequired", None)
    encoded = json.dumps(clean, separators=(",", ":"), allow_nan=False).encode("utf-8")
    encoded += b" " * (-len(encoded) % 4)
    payload = bytes(binary) + b"\0" * (-len(binary) % 4)
    body = struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(payload))
    body += struct.pack("<II", len(encoded), 0x4E4F534A) + encoded
    body += struct.pack("<II", len(payload), 0x004E4942) + payload
    return body


def _source_geometry(registry: Registry, definition: dict[str, Any], placed: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    if definition["adapter"] != GLB:
        raise _MeasureIssue("HOLD", "UNSUPPORTED_ADAPTER", "geometry calipers currently require rigid GLB assembly leaves")
    try:
        recipe = resolve(definition, placed)
    except (TypeError, ValueError) as exc:
        raise _MeasureIssue("FAIL", "INVALID_INSTANCE", str(exc)) from exc
    if recipe != {"model": "model"} or "model" not in definition.get("assets", {}):
        raise _MeasureIssue("HOLD", "UNSUPPORTED_RECIPE", "geometry calipers require the ordinary rigid GLB model recipe")
    reference = definition["assets"]["model"]
    if reference in cache:
        return cache[reference]
    try:
        raw = registry.asset(reference)
        pose_asset = GamePoseAsset(raw)
        description = pose_asset.describe()
        document, binary = _parse(raw)
        if document.get("skins"):
            raise _MeasureIssue("HOLD", "SKINNED_GEOMETRY", "sticker assembly leaves with skins are outside rigid caliper v0.1")
        animation_count = len(document.get("animations", [])) if isinstance(document.get("animations", []), list) else 0
        required = list(document.get("extensionsRequired", [])) if isinstance(document.get("extensionsRequired", []), list) else []
        glb = _GLB(_encode_geometry_view(document, binary))
        doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")
        stack = [(node, GLTF_IDENTITY) for node in reversed(roots)]
        seen: set[int] = set()
        points: list[list[float]] = []
        triangles = 0
        primitives = 0
        degenerate = 0
        while stack:
            node_index, parent = stack.pop()
            node = _at(doc.get("nodes"), node_index, "node")
            if node_index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(node_index)
            if len(seen) > 10000:
                raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds node limit", hold=True)
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_NODE", "skinned, weighted or extended nodes require another observer", hold=True)
            world = gltf_multiply(parent, _local(node))
            children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend((child, world) for child in reversed(children))
            if "mesh" not in node:
                continue
            mesh = _at(doc.get("meshes"), node["mesh"], "mesh")
            if mesh.get("weights"):
                raise GeometryIssue("DEFORMATION_NOT_REVIEWED", "morph weights are outside rigid geometry calipers", hold=True)
            primitive_rows = mesh.get("primitives", [])
            if not isinstance(primitive_rows, list):
                raise GeometryIssue("INVALID_STRUCTURE", "mesh primitives must be an array")
            for primitive in primitive_rows:
                if primitive.get("mode", 4) != 4 or primitive.get("targets") or primitive.get("extensions"):
                    raise GeometryIssue("UNSUPPORTED_PRIMITIVE", "geometry calipers require ordinary TRIANGLES primitives", hold=True)
                attributes = primitive.get("attributes", {})
                if not isinstance(attributes, dict):
                    raise GeometryIssue("INVALID_STRUCTURE", "primitive attributes must be an object")
                positions = glb.accessor(attributes.get("POSITION"), True)
                indices = ([row[0] for row in glb.accessor(primitive["indices"], False)]
                           if "indices" in primitive else list(range(len(positions))))
                if len(indices) % 3 or any(index >= len(positions) for index in indices):
                    raise GeometryIssue("INVALID_TRIANGLES", "incomplete triangle or out-of-range vertex index")
                triangles += len(indices) // 3
                primitives += 1
                if triangles > MAX_TRIANGLES:
                    raise GeometryIssue("RESOURCE_LIMIT", "triangle measurement exceeds bounded work limit", hold=True)
                transformed = [gltf_point(world, position) for position in positions]
                referenced = sorted(set(indices))
                if len(points) + len(referenced) > MAX_TRANSFORMED_POINTS:
                    raise GeometryIssue("RESOURCE_LIMIT", "source vertex measurement exceeds bounded work limit", hold=True)
                points.extend(transformed[index] for index in referenced)
                for offset in range(0, len(indices), 3):
                    tri = [transformed[index] for index in indices[offset:offset + 3]]
                    u = [tri[1][axis] - tri[0][axis] for axis in range(3)]
                    v = [tri[2][axis] - tri[0][axis] for axis in range(3)]
                    cross = [u[1] * v[2] - u[2] * v[1],
                             u[2] * v[0] - u[0] * v[2],
                             u[0] * v[1] - u[1] * v[0]]
                    if math.hypot(*cross) <= MIN_TWICE_AREA_M2:
                        degenerate += 1
        if not points or triangles == 0:
            raise GeometryIssue("EMPTY_GEOMETRY", "default scene has no rendered triangles")
        row = {
            "asset": reference,
            "source_sha256": hashlib.sha256(raw).hexdigest(),
            "points": points,
            "triangles": triangles,
            "primitives": primitives,
            "nodes": len(seen),
            "degenerate_triangles": degenerate,
            "animation_clips_ignored": animation_count,
            "nonpose_required_extensions_ignored": required,
            "pose_runtime_vertices": description["vertices"],
            "status": "FAIL" if degenerate else "PASS",
        }
        cache[reference] = row
        return row
    except _MeasureIssue:
        raise
    except GeometryIssue as exc:
        raise _MeasureIssue("HOLD" if exc.hold else "FAIL", exc.code, str(exc)) from exc
    except (TypeError, ValueError, KeyError, IndexError, AttributeError, struct.error, OverflowError, RecursionError) as exc:
        raise _MeasureIssue("FAIL", "INVALID_GEOMETRY", str(exc)) from exc


def _new_accumulator(part_id: str) -> dict[str, Any]:
    return {
        "id": part_id,
        "bounds": None,
        "source_assets": set(),
        "leaf_instances": 0,
        "triangles": 0,
        "primitives": 0,
        "referenced_points": 0,
        "animation_clips_ignored": 0,
        "selected_source_clips": set(),
        "issues": [],
    }


def _add_point(row: dict[str, Any], point: list[float]) -> None:
    if row["bounds"] is None:
        row["bounds"] = {"min": list(point), "max": list(point)}
    else:
        row["bounds"]["min"] = [min(a, b) for a, b in zip(row["bounds"]["min"], point)]
        row["bounds"]["max"] = [max(a, b) for a, b in zip(row["bounds"]["max"], point)]


def _finish_accumulator(row: dict[str, Any]) -> dict[str, Any]:
    issues = list(row["issues"])
    status = ("FAIL" if any(issue["status"] == "FAIL" for issue in issues)
              else "HOLD" if issues or row["bounds"] is None
              else "PASS")
    result: dict[str, Any] = {
        "id": row["id"],
        "status": status,
        "units": "m",
        "measurement_frame": "sticker socket coordinates at authored/default rest pose",
        "source_assets": sorted(row["source_assets"]),
        "leaf_instances": row["leaf_instances"],
        "triangles": row["triangles"],
        "primitives": row["primitives"],
        "referenced_points": row["referenced_points"],
        "animation_clips_ignored": row["animation_clips_ignored"],
        "selected_source_clips": sorted(row["selected_source_clips"]),
        "issues": issues,
    }
    if row["bounds"] is not None:
        minimum = [_q(value) for value in row["bounds"]["min"]]
        maximum = [_q(value) for value in row["bounds"]["max"]]
        result["bounds_m"] = {"min": minimum, "max": maximum}
        result["size_m"] = [_q(hi - lo) for lo, hi in zip(minimum, maximum)]
    return result


def _measure_definition(registry: Registry, definition: dict[str, Any], *, direct_parts: bool) -> dict[str, Any]:
    try:
        records = expand(registry, definition)
    except (TypeError, ValueError) as exc:
        raise StickerGeometryCaliperError("sticker geometry cannot be expanded exactly") from exc
    if direct_parts and definition["adapter"] != ASSEMBLY:
        raise StickerGeometryCaliperError("direct part geometry requires an assembly sticker")
    accumulators: dict[str, dict[str, Any]] = {}
    reference_frames: dict[str, list[float]] = {}
    if direct_parts:
        children = definition.get("recipe", {}).get("children")
        if not isinstance(children, list):
            raise StickerGeometryCaliperError("assembly does not expose direct children")
        for child in children:
            part_id = child["instance"]["id"]
            accumulators[part_id] = _new_accumulator(part_id)
    else:
        accumulators["root"] = _new_accumulator("root")

    holder_world: dict[int, list[float]] = {}
    socket_world: dict[int, list[float]] = {}
    source_cache: dict[str, Any] = {}
    transformed_visits = 0
    for index, record in enumerate(records):
        parent = record["parent"]
        parent_holder = identity() if parent is None else holder_world[parent]
        try:
            target_frame = list(rigid(record["target"]["frame"]))
            socket = multiply(parent_holder, target_frame)
            local_holder = attachment_matrix(
                record["definition"],
                record["instance"],
                {"space": "3d", "socket": record["target"]["socket"], "frame": identity()},
            )
        except (TypeError, ValueError, KeyError) as exc:
            raise StickerGeometryCaliperError("assembly contains an invalid 3D placement while measuring geometry", {"path": record.get("path")}) from exc
        socket_world[index] = socket
        holder_world[index] = multiply(socket, local_holder)
        path = str(record["path"])
        segments = path.split("/")
        if direct_parts and len(segments) == 2:
            reference_frames[segments[1]] = socket
        if not direct_parts and index == 0:
            reference_frames["root"] = socket
        if record["definition"]["adapter"] == ASSEMBLY:
            continue
        key = segments[1] if direct_parts and len(segments) >= 2 else "root"
        if key not in accumulators or key not in reference_frames:
            continue
        row = accumulators[key]
        row["leaf_instances"] += 1
        if record.get("clip") is not None:
            row["selected_source_clips"].add(str(record["clip"]))
        try:
            source = _source_geometry(registry, record["definition"], record["instance"], source_cache)
            row["source_assets"].add(source["asset"])
            row["triangles"] += source["triangles"]
            row["primitives"] += source["primitives"]
            row["animation_clips_ignored"] += source["animation_clips_ignored"]
            if source["status"] != "PASS":
                row["issues"].append({"status": source["status"], "code": "SOURCE_GEOMETRY_INTEGRITY",
                                      "path": path, "degenerate_triangles": source["degenerate_triangles"]})
            inverse_reference = inverse_rigid(reference_frames[key])
            transformed_visits += len(source["points"])
            if transformed_visits > MAX_TRANSFORMED_POINTS:
                raise _MeasureIssue("HOLD", "RESOURCE_LIMIT", "assembly geometry measurement exceeds transformed-point limit")
            for point in source["points"]:
                outer = _flat_point(holder_world[index], point)
                local = _flat_point(inverse_reference, outer)
                _add_point(row, local)
                row["referenced_points"] += 1
        except _MeasureIssue as exc:
            row["issues"].append({"status": exc.status, "code": exc.code, "path": path, "message": str(exc)})

    finished = [_finish_accumulator(row) for row in accumulators.values()]
    status = ("FAIL" if any(row["status"] == "FAIL" for row in finished)
              else "HOLD" if any(row["status"] == "HOLD" for row in finished)
              else "PASS")
    return {
        "status": status,
        "parts": finished,
        "transformed_point_visits": transformed_visits,
        "unique_source_assets": len(source_cache),
    }


def measure_sticker_geometry(registry: Registry, sticker_pin_raw: Any) -> dict[str, Any]:
    pin = _pin(sticker_pin_raw, "sticker")
    definition = _exact_definition(registry, pin)
    measured = _measure_definition(registry, definition, direct_parts=False)
    root = measured["parts"][0]
    report = {
        "schema": GEOMETRY_REPORT_SCHEMA,
        "truth_status": "ACTUAL_INDEXED_TRIANGLE_GEOMETRY_BOUNDS_AT_AUTHORED_DEFAULT_POSE",
        "status": root["status"],
        "sticker": pin,
        "measurement": root,
        "transformed_point_visits": measured["transformed_point_visits"],
        "unique_source_assets": measured["unique_source_assets"],
        "limitations": [
            "bounds come from actual triangle-referenced POSITION vertices and exact node/assembly transforms, not accessor min/max metadata",
            "measurement is the authored/default rest pose; animation tracks and selected clips are not swept into a motion envelope",
            "bounds and dimensions do not prove mesh contact, collision clearance, strength, manufacturability, physics, aesthetics, or engine acceptance",
        ],
    }
    report["report_digest"] = _digest(report)
    return report


def measure_sticker_assembly_parts(registry: Registry, assembly_pin_raw: Any) -> dict[str, Any]:
    pin = _pin(assembly_pin_raw, "assembly")
    definition = _exact_definition(registry, pin)
    if definition["adapter"] != ASSEMBLY:
        raise StickerGeometryCaliperError("measure-sticker-assembly-parts requires an assembly sticker")
    measured = _measure_definition(registry, definition, direct_parts=True)
    report = {
        "schema": ASSEMBLY_GEOMETRY_SCHEMA,
        "truth_status": "ACTUAL_DIRECT_PART_GEOMETRY_BOUNDS_IN_EACH_STICKER_SOCKET_FRAME",
        "status": measured["status"],
        "assembly": pin,
        "units": "m",
        "parts": measured["parts"],
        "transformed_point_visits": measured["transformed_point_visits"],
        "unique_source_assets": measured["unique_source_assets"],
        "limitations": [
            "nested assemblies and multiplied wrappers are flattened through exact stored transforms before each direct part is measured",
            "dimensions are measured in each direct child's socket frame so rotating the part in the parent does not swap its local caliper axes",
            "measurement is rest/default pose only and does not prove a swept animation envelope, collision clearance, fit, physics, or visual quality",
        ],
    }
    report["report_digest"] = _digest(report)
    return report


def _size_evidence(geometry: dict[str, Any] | None, target: list[float], tolerance: float, *, units_ok: bool) -> dict[str, Any]:
    if not units_ok:
        return {"status": "HOLD", "reason": "geometry is measured in metres and the sketch units are not exactly 'm'; no conversion is guessed"}
    if geometry is None:
        return {"status": "HOLD", "reason": "no complete geometry measurement exists for this sketch part"}
    if geometry["status"] != "PASS" or "size_m" not in geometry:
        return {"status": "HOLD", "reason": "source geometry measurement is not complete PASS evidence",
                "geometry_status": geometry["status"], "issues": copy.deepcopy(geometry.get("issues", []))}
    measured = geometry["size_m"]
    residuals = [abs(measured[index] - target[index]) for index in range(3)]
    residual = max(residuals)
    return {"status": "PASS" if residual <= tolerance else "FAIL",
            "measured": list(measured), "target": list(target), "residual": _q(residual),
            "axis_residuals": [_q(value) for value in residuals], "tolerance": tolerance,
            "bounds_m": copy.deepcopy(geometry["bounds_m"]), "measurement_pose": "authored/default rest pose"}


def compare_sticker_geometry(registry: Registry, sketch_raw: Any, assembly_pin_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    structural = compare_sticker_assembly(registry, sketch, assembly_pin_raw)
    geometry = measure_sticker_assembly_parts(registry, structural["assembly"])
    geometry_by_part = {row["id"]: row for row in geometry["parts"]}
    sketch_by_part = {row["id"]: row for row in sketch["parts"]}
    units_ok = sketch["units"] == "m"

    parts = copy.deepcopy(structural["parts"])
    for row in parts:
        planned = sketch_by_part[row["id"]]
        evidence = _size_evidence(geometry_by_part.get(row["id"]), planned["size"], sketch["tolerances"]["size"], units_ok=units_ok)
        row["geometry_status"] = geometry_by_part.get(row["id"], {}).get("status", "HOLD")
        row["size_status"] = evidence["status"]
        row["size_evidence"] = evidence
        statuses = [row["placement_status"], row["geometry_status"], row["size_status"]]
        row["status"] = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
        row.pop("size_reason", None)

    gauge_specs = {row["id"]: row for row in sketch["gauges"]}
    gauges = copy.deepcopy(structural["gauges"])
    for row in gauges:
        if row["type"] != "size":
            continue
        spec = gauge_specs[row["id"]]
        evidence = _size_evidence(geometry_by_part.get(spec["part"]), spec["target"], spec["tolerance"], units_ok=units_ok)
        row.clear()
        row.update({"id": spec["id"], "type": "size", **evidence})

    statuses = [row["status"] for row in parts] + [row["status"] for row in gauges]
    status = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    report = {
        "schema": WORKSHOP_GEOMETRY_SCHEMA,
        "truth_status": "EXACT_SKETCH_VS_STICKER_PLACEMENT_AND_ACTUAL_TRIANGLE_GEOMETRY",
        "status": status,
        "passed": status == "PASS",
        "placement_status": structural["placement_status"],
        "geometry_status": geometry["status"],
        "assembly": copy.deepcopy(structural["assembly"]),
        "sketch_digest": sketch["sketch_digest"],
        "sketch_units": sketch["units"],
        "geometry_units": "m",
        "placement_report_digest": structural["report_digest"],
        "geometry_report_digest": geometry["report_digest"],
        "parts": parts,
        "extra_parts": copy.deepcopy(structural["extra_parts"]),
        "gauges": gauges,
        "geometry": geometry,
        "unobserved": ["animated motion envelope", "mesh contact/collision clearance", "physics", "strength/manufacturability", "aesthetics", "target-engine behavior"],
        "limitations": [
            "geometry dimensions are actual triangle-referenced rest-pose bounds measured in each part's socket frame",
            "only sketches declaring units exactly 'm' are compared numerically; no implicit unit conversion is performed",
            "a dimension PASS does not prove parts fit together, avoid collision, move safely, or look good",
            "size mismatch is evidence only; this caliper wave does not silently scale or rewrite source geometry",
        ],
    }
    report["report_digest"] = _digest(report)
    return report


def caliper_summary() -> dict[str, Any]:
    return {
        "schemas": [GEOMETRY_REPORT_SCHEMA, ASSEMBLY_GEOMETRY_SCHEMA, WORKSHOP_GEOMETRY_SCHEMA],
        "operations": sorted(CALIPER_OPERATIONS),
        "measurement": "actual indexed TRIANGLES POSITION vertices through exact node, assembly, anchor, offset and scale transforms",
        "pose": "authored/default rest pose only",
        "units": "metres",
        "truth_boundary": "numeric bounds/extents only; no fit, collision, physics, aesthetics or engine-quality claim",
    }


def operate_sticker_geometry_calipers(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-geometry-calipers":
        return {"truth_status": "DECLARED_STICKER_GEOMETRY_CALIPERS_V0_1", **caliper_summary()}
    database = inputs.get("database")
    if not isinstance(database, str) or not database.strip():
        raise StickerGeometryCaliperError("geometry calipers require a sticker database path")
    path = _resolve_registry_path(root, database)
    if _machine_body(root, path):
        raise StickerGeometryCaliperError("geometry caliper database must be an ordinary creation path or external path")
    with Registry(path) as registry:
        if operation == "measure-sticker-geometry":
            return measure_sticker_geometry(registry, inputs.get("sticker"))
        if operation == "measure-sticker-assembly-parts":
            return measure_sticker_assembly_parts(registry, inputs.get("assembly"))
        if operation == "compare-sticker-geometry":
            return compare_sticker_geometry(registry, inputs.get("sketch"), inputs.get("assembly"))
    raise StickerGeometryCaliperError("geometry caliper operation is unsupported", {"operation": operation})

from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from .mesh_fabrication_chain import (
    FABRICATION_LINEAGE_SCHEMA,
    MAX_CHAIN_CUTS,
    _cut as _normalize_notch,
    _digest,
    _lineage_digest,
    _load_parent_lineage as _load_v04_parent_lineage,
    _normalize_digest,
    _notch_rectangle,
    _publish_receipt,
    _read_json_object,
    _restore_bytes,
)
from .mesh_general_hole_chain import (
    GENERAL_HOLE_LINEAGE_SCHEMA,
    _active_interval,
    _clean_boundary,
    _eval_edge,
    _hole_polygon,
    _load_v06_parent_lineage,
    _vertical_intersections,
)
from .mesh_hole_fabrication_chain import (
    HOLE_LINEAGE_SCHEMA,
    _hole as _normalize_hole,
    _resolve_hole,
    _root_from_source,
)
from .mesh_precision_cutter import (
    SOURCE_TOLERANCE,
    MeshPrecisionCutterError,
    _read_source_primitive,
    _signed_volume,
)
from .mesh_topology import MeshTopologyError, inspect_mesh_topology
from .oriented_mesh_precision_cutter import (
    _axis_vector,
    _canonical_normal_to_world,
    _canonical_to_world,
    _match_frame_axis,
)
from .precision_cutter import _append_face, _surface_specification
from .procedural_3d import Procedural3DError, build_glb, publish_glb

MIXED_FABRICATION_SCHEMA = "axm.mesh-mixed-fabrication-chain/v0.7"
MIXED_LINEAGE_SCHEMA = "axm.mesh-mixed-fabrication-lineage/v0.7"
SWEEP_TOLERANCE = 1e-10


def mixed_fabrication_summary() -> dict[str, Any]:
    return {
        "schema": MIXED_FABRICATION_SCHEMA,
        "lineage_schema": MIXED_LINEAGE_SCHEMA,
        "truth_status": "LIVE_HASH_LINKED_SAME_AXIS_MIXED_FABRICATION",
        "operations": ["round-through-hole", "box-notch"],
        "maximum_operations": MAX_CHAIN_CUTS,
        "legacy_lineage_upgrade": [
            FABRICATION_LINEAGE_SCHEMA,
            HOLE_LINEAGE_SCHEMA,
            GENERAL_HOLE_LINEAGE_SCHEMA,
        ],
        "same_axis_mixed_holes_and_notches": True,
        "cross_axis_chain": False,
        "full_arbitrary_mesh_csg": False,
    }


def _normalize_operation(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError(f"operations[{index}] must be an object")
    operation = str(raw.get("operation", "")).strip().casefold()
    if operation == "round-through-hole":
        return _normalize_hole(raw, index)
    if operation == "box-notch":
        return _normalize_notch(raw, index)
    raise MeshPrecisionCutterError(
        "v0.7 mixed fabrication supports round-through-hole and box-notch operations only",
        {"index": index, "operation": operation},
    )


def prepare_mixed_fabrication(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("v0.7 mixed fabrication specification must be an object")
    required = {"schema", "name", "axis_vector", "operations"}
    if set(raw) != required:
        raise MeshPrecisionCutterError(
            "v0.7 mixed fabrication fields do not match the bounded grammar",
            {
                "missing": sorted(required - set(raw)),
                "unexpected": sorted(set(raw) - required),
            },
        )
    if raw["schema"] != MIXED_FABRICATION_SCHEMA:
        raise MeshPrecisionCutterError("unsupported mixed fabrication schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise MeshPrecisionCutterError("name must contain 1..120 characters")
    operations = raw["operations"]
    if not isinstance(operations, list) or not 1 <= len(operations) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"operations must contain 1 through {MAX_CHAIN_CUTS} new fabrication operations"
        )
    normalized = [_normalize_operation(value, index) for index, value in enumerate(operations)]
    ids = [value["id"] for value in normalized]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("new mixed fabrication operation ids must be unique")
    return {
        "schema": MIXED_FABRICATION_SCHEMA,
        "name": name.strip(),
        "axis_vector": list(_axis_vector(raw["axis_vector"])),
        "operations": normalized,
    }


def _resolved_operation(body: dict[str, Any], legacy_digest: str | None = None) -> dict[str, Any]:
    normalized = dict(body)
    normalized.pop("resolved_hole_sha256", None)
    normalized.pop("resolved_cut_sha256", None)
    normalized.pop("resolved_operation_sha256", None)
    if legacy_digest is not None:
        normalized["legacy_resolved_sha256"] = legacy_digest
    normalized["resolved_operation_sha256"] = _digest(normalized)
    return normalized


def _convert_legacy_notch(row: dict[str, Any]) -> dict[str, Any]:
    return _resolved_operation(row, str(row.get("resolved_cut_sha256", "")))


def _convert_legacy_hole(row: dict[str, Any]) -> dict[str, Any]:
    return _resolved_operation(row, str(row.get("resolved_hole_sha256", "")))


def _resolve_operation(
    operation: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> dict[str, Any]:
    if operation["operation"] == "round-through-hole":
        return _resolved_operation(_resolve_hole(operation, frame=frame, order=order))
    return _resolved_operation(_notch_rectangle(operation, frame=frame, order=order))


def _notch_polygon(operation: dict[str, Any]) -> list[tuple[float, float]]:
    x0, z0, x1, z1 = (float(value) for value in operation["rectangle"])
    return [(x0, z0), (x1, z0), (x1, z1), (x0, z1)]


def _operation_polygon(operation: dict[str, Any]) -> list[tuple[float, float]]:
    return _hole_polygon(operation) if operation["operation"] == "round-through-hole" else _notch_polygon(operation)


def _orientation(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _on_segment(
    a: tuple[float, float],
    b: tuple[float, float],
    p: tuple[float, float],
    tolerance: float,
) -> bool:
    if abs(_orientation(a, b, p)) > tolerance:
        return False
    return (
        min(a[0], b[0]) - tolerance <= p[0] <= max(a[0], b[0]) + tolerance
        and min(a[1], b[1]) - tolerance <= p[1] <= max(a[1], b[1]) + tolerance
    )


def _segments_conflict(
    a0: tuple[float, float],
    a1: tuple[float, float],
    b0: tuple[float, float],
    b1: tuple[float, float],
    tolerance: float,
) -> bool:
    o1 = _orientation(a0, a1, b0)
    o2 = _orientation(a0, a1, b1)
    o3 = _orientation(b0, b1, a0)
    o4 = _orientation(b0, b1, a1)
    if (
        ((o1 > tolerance and o2 < -tolerance) or (o1 < -tolerance and o2 > tolerance))
        and ((o3 > tolerance and o4 < -tolerance) or (o3 < -tolerance and o4 > tolerance))
    ):
        return True
    return any(
        (
            abs(o1) <= tolerance and _on_segment(a0, a1, b0, tolerance),
            abs(o2) <= tolerance and _on_segment(a0, a1, b1, tolerance),
            abs(o3) <= tolerance and _on_segment(b0, b1, a0, tolerance),
            abs(o4) <= tolerance and _on_segment(b0, b1, a1, tolerance),
        )
    )


def _point_in_polygon(point: tuple[float, float], polygon: list[tuple[float, float]], tolerance: float) -> bool:
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        if _on_segment(first, second, point, tolerance):
            return True
    x, z = point
    inside = False
    for index, first in enumerate(polygon):
        second = polygon[(index + 1) % len(polygon)]
        x0, z0 = first
        x1, z1 = second
        if (z0 > z) != (z1 > z):
            cross_x = x0 + (z - z0) * (x1 - x0) / (z1 - z0)
            if cross_x > x:
                inside = not inside
    return inside


def _polygons_conflict(
    first: list[tuple[float, float]],
    second: list[tuple[float, float]],
    tolerance: float,
) -> bool:
    for index, a0 in enumerate(first):
        a1 = first[(index + 1) % len(first)]
        for offset, b0 in enumerate(second):
            b1 = second[(offset + 1) % len(second)]
            if _segments_conflict(a0, a1, b0, b1, tolerance):
                return True
    return _point_in_polygon(first[0], second, tolerance) or _point_in_polygon(second[0], first, tolerance)


def _validate_operations(
    operations: list[dict[str, Any]],
    frame: dict[str, Any],
) -> list[list[tuple[float, float]]]:
    if not 1 <= len(operations) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cumulative mixed fabrication must contain 1 through {MAX_CHAIN_CUTS} operations"
        )
    ids = [row["id"] for row in operations]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("cumulative mixed fabrication ids must remain unique")
    polygons = [_operation_polygon(row) for row in operations]
    tolerance = max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    for index, first in enumerate(polygons):
        for offset in range(index + 1, len(polygons)):
            if _polygons_conflict(first, polygons[offset], tolerance):
                raise MeshPrecisionCutterError(
                    "v0.7 refuses overlapping or touching mixed cut volumes",
                    {
                        "first_operation": operations[index]["id"],
                        "second_operation": operations[offset]["id"],
                    },
                )
    return polygons


def _seam_events(
    polygons: list[list[tuple[float, float]]],
    x: float,
    half_depth: float,
) -> list[float]:
    values = {-half_depth, half_depth}
    for polygon in polygons:
        values.update(round(z, 12) for z, _edges in _vertical_intersections(polygon, x))
    return sorted(float(value) for value in values)


def _blocked_on_outer_boundary(
    operations: list[dict[str, Any]],
    *,
    x: float,
    z: float,
    half_width: float,
    half_depth: float,
    tolerance: float,
) -> bool:
    for operation in operations:
        if operation["operation"] != "box-notch":
            continue
        x0, z0, x1, z1 = (float(value) for value in operation["rectangle"])
        side = operation["side"]
        if side == "v-min" and abs(z + half_depth) <= tolerance and x0 - tolerance <= x <= x1 + tolerance:
            return True
        if side == "v-max" and abs(z - half_depth) <= tolerance and x0 - tolerance <= x <= x1 + tolerance:
            return True
        if side == "u-min" and abs(x + half_width) <= tolerance and z0 - tolerance <= z <= z1 + tolerance:
            return True
        if side == "u-max" and abs(x - half_width) <= tolerance and z0 - tolerance <= z <= z1 + tolerance:
            return True
    return False


def _edge_is_open_notch_boundary(
    operation: dict[str, Any],
    first: tuple[float, float],
    second: tuple[float, float],
    *,
    half_width: float,
    half_depth: float,
    tolerance: float,
) -> bool:
    if operation["operation"] != "box-notch":
        return False
    side = operation["side"]
    if side == "v-min":
        return abs(first[1] + half_depth) <= tolerance and abs(second[1] + half_depth) <= tolerance
    if side == "v-max":
        return abs(first[1] - half_depth) <= tolerance and abs(second[1] - half_depth) <= tolerance
    if side == "u-min":
        return abs(first[0] + half_width) <= tolerance and abs(second[0] + half_width) <= tolerance
    return abs(first[0] - half_width) <= tolerance and abs(second[0] - half_width) <= tolerance


def _build_mixed_cross_section_surface(
    width: float,
    depth: float,
    thickness: float,
    operations: list[dict[str, Any]],
    polygons: list[list[tuple[float, float]]],
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int], dict[str, Any]]:
    half_width, half_depth = width / 2.0, depth / 2.0
    tolerance = max(SWEEP_TOLERANCE, SOURCE_TOLERANCE)
    x_events = {-half_width, half_width}
    for polygon in polygons:
        x_events.update(round(point[0], 12) for point in polygon)
    xs = sorted(float(value) for value in x_events)
    seams = {x: _seam_events(polygons, x, half_depth) for x in xs}
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    top, bottom = thickness / 2.0, -thickness / 2.0
    free_region_count = 0

    for left, right in zip(xs, xs[1:]):
        if right - left <= SWEEP_TOLERANCE:
            continue
        midpoint = (left + right) / 2.0
        blocked: list[tuple[float, float, int, int, int]] = []
        for polygon_index, polygon in enumerate(polygons):
            interval = _active_interval(polygon, midpoint)
            if interval is None:
                continue
            low, high, lower_edge, upper_edge = interval
            blocked.append((low, high, polygon_index, lower_edge, upper_edge))
        blocked.sort(key=lambda row: (row[0], row[1], row[2]))
        for first, second in zip(blocked, blocked[1:]):
            if first[1] >= second[0] - tolerance:
                raise MeshPrecisionCutterError(
                    "v0.7 sweep observed overlapping or touching cut polygons",
                    {"x": midpoint},
                )

        bands: list[tuple[tuple[int, int] | None, tuple[int, int] | None]] = []
        previous_upper: tuple[int, int] | None = None
        for _low, _high, polygon_index, lower_edge, upper_edge in blocked:
            bands.append((previous_upper, (polygon_index, lower_edge)))
            previous_upper = (polygon_index, upper_edge)
        bands.append((previous_upper, None))

        for lower_ref, upper_ref in bands:
            if lower_ref is None:
                lower_left = lower_right = -half_depth
            else:
                polygon_index, edge = lower_ref
                lower_left = _eval_edge(polygons[polygon_index], edge, left)
                lower_right = _eval_edge(polygons[polygon_index], edge, right)
            if upper_ref is None:
                upper_left = upper_right = half_depth
            else:
                polygon_index, edge = upper_ref
                upper_left = _eval_edge(polygons[polygon_index], edge, left)
                upper_right = _eval_edge(polygons[polygon_index], edge, right)
            if (lower_left + lower_right) / 2.0 >= (upper_left + upper_right) / 2.0 - SWEEP_TOLERANCE:
                continue
            right_events = [z for z in seams[right] if lower_right + SWEEP_TOLERANCE < z < upper_right - SWEEP_TOLERANCE]
            left_events = [z for z in seams[left] if lower_left + SWEEP_TOLERANCE < z < upper_left - SWEEP_TOLERANCE]
            boundary = _clean_boundary(
                [(left, lower_left), (right, lower_right)]
                + [(right, z) for z in right_events]
                + [(right, upper_right), (left, upper_left)]
                + [(left, z) for z in reversed(left_events)]
            )
            center_x = sum(point[0] for point in boundary) / len(boundary)
            center_z = sum(point[1] for point in boundary) / len(boundary)
            for index, first in enumerate(boundary):
                second = boundary[(index + 1) % len(boundary)]
                if math.dist(first, second) <= SWEEP_TOLERANCE:
                    continue
                _append_face(positions, normals, indices, [(center_x, top, center_z), (first[0], top, first[1]), (second[0], top, second[1])], (0.0, 1.0, 0.0))
                _append_face(positions, normals, indices, [(center_x, bottom, center_z), (first[0], bottom, first[1]), (second[0], bottom, second[1])], (0.0, -1.0, 0.0))
            free_region_count += 1

    for z, normal in ((-half_depth, (0.0, 0.0, -1.0)), (half_depth, (0.0, 0.0, 1.0))):
        for left, right in zip(xs, xs[1:]):
            midpoint = (left + right) / 2.0
            if _blocked_on_outer_boundary(operations, x=midpoint, z=z, half_width=half_width, half_depth=half_depth, tolerance=tolerance):
                continue
            _append_face(positions, normals, indices, [(left, bottom, z), (left, top, z), (right, top, z), (right, bottom, z)], normal)

    for x, normal in ((-half_width, (-1.0, 0.0, 0.0)), (half_width, (1.0, 0.0, 0.0))):
        seam = seams[x]
        for low, high in zip(seam, seam[1:]):
            midpoint = (low + high) / 2.0
            if _blocked_on_outer_boundary(operations, x=x, z=midpoint, half_width=half_width, half_depth=half_depth, tolerance=tolerance):
                continue
            _append_face(positions, normals, indices, [(x, bottom, low), (x, top, low), (x, top, high), (x, bottom, high)], normal)

    for operation, polygon in zip(operations, polygons):
        center_x = sum(point[0] for point in polygon) / len(polygon)
        center_z = sum(point[1] for point in polygon) / len(polygon)
        for edge, first in enumerate(polygon):
            second = polygon[(edge + 1) % len(polygon)]
            if _edge_is_open_notch_boundary(operation, first, second, half_width=half_width, half_depth=half_depth, tolerance=tolerance):
                continue
            edge_points = [first]
            x0, z0 = first
            x1, z1 = second
            if abs(x1 - x0) > SWEEP_TOLERANCE:
                low, high = sorted((x0, x1))
                for x in xs:
                    if low + SWEEP_TOLERANCE < x < high - SWEEP_TOLERANCE:
                        edge_points.append((x, _eval_edge(polygon, edge, x)))
                edge_points.sort(key=lambda point: (point[0] - x0) / (x1 - x0))
            edge_points.append(second)
            dx, dz = x1 - x0, z1 - z0
            length = math.hypot(dx, dz)
            if length <= SWEEP_TOLERANCE:
                raise MeshPrecisionCutterError("v0.7 cut polygon contains a collapsed edge")
            normal = (-dz / length, 0.0, dx / length)
            midpoint = ((x0 + x1) / 2.0, (z0 + z1) / 2.0)
            if normal[0] * (center_x - midpoint[0]) + normal[2] * (center_z - midpoint[1]) < 0.0:
                normal = (-normal[0], 0.0, -normal[2])
            for start, end in zip(edge_points, edge_points[1:]):
                _append_face(positions, normals, indices, [(start[0], bottom, start[1]), (end[0], bottom, end[1]), (end[0], top, end[1]), (start[0], top, start[1])], normal)

    return positions, normals, indices, {
        "sweep_x_events": len(xs),
        "sweep_strips": len(xs) - 1,
        "free_regions": free_region_count,
    }


def _removed_area(operation: dict[str, Any]) -> float:
    return float(operation["polygonized_removed_area"] if operation["operation"] == "round-through-hole" else operation["removed_area"])


def _compile_state(
    *,
    name: str,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    material: dict[str, Any],
    operations: list[dict[str, Any]],
) -> dict[str, Any]:
    polygons = _validate_operations(operations, frame)
    width = float(frame["extents"][order[0]])
    thickness = float(frame["extents"][order[1]])
    depth = float(frame["extents"][order[2]])
    canonical_positions, canonical_normals, indices, sweep = _build_mixed_cross_section_surface(width, depth, thickness, operations, polygons)
    positions = [_canonical_to_world(point, frame, order) for point in canonical_positions]
    normals = [_canonical_normal_to_world(normal, frame, order) for normal in canonical_normals]
    try:
        topology = inspect_mesh_topology(positions, indices, weld_tolerance=SOURCE_TOLERANCE)
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE" or topology["triangle_component_count"] != 1:
        raise MeshPrecisionCutterError(
            "v0.7 mixed fabrication output did not remain one closed oriented component",
            {"topology": topology},
        )
    source_volume = float(frame["box_volume"])
    output_volume = _signed_volume(positions, indices)
    removed_area = sum(_removed_area(operation) for operation in operations)
    expected_volume = source_volume - removed_area * thickness
    volume_tolerance = max(source_volume * 1e-5, 1e-8)
    if output_volume <= 0.0 or abs(output_volume - expected_volume) > volume_tolerance:
        raise MeshPrecisionCutterError(
            "v0.7 closed-mesh volume does not match the mixed removed-area receipt",
            {"observed_output_volume": output_volume, "expected_output_volume": expected_volume, "tolerance": volume_tolerance},
        )
    surface = _surface_specification(name, positions, normals, indices, material)
    glb = build_glb(surface)
    return {
        "surface_specification": surface,
        "glb_sha256": hashlib.sha256(glb["body"]).hexdigest(),
        "specification_sha256": glb["specification_sha256"],
        "topology": topology,
        "geometry": {"vertices": len(positions), "triangles": len(indices) // 3, **sweep},
        "metrics": {
            "source_volume": source_volume,
            "output_volume": output_volume,
            "removed_volume": source_volume - output_volume,
            "mixed_removed_area": removed_area,
            "fabrication_thickness": thickness,
            "hole_count": sum(operation["operation"] == "round-through-hole" for operation in operations),
            "notch_count": sum(operation["operation"] == "box-notch" for operation in operations),
        },
    }


def _steps_for_operations(root_sha256: str, operations: list[dict[str, Any]]) -> list[dict[str, Any]]:
    steps: list[dict[str, Any]] = []
    parent_state = root_sha256
    for operation in operations:
        body = {
            "step": len(steps) + 1,
            "operation_id": operation["id"],
            "operation": operation["operation"],
            "operation_sha256": operation["resolved_operation_sha256"],
            "parent_state_sha256": parent_state,
        }
        body["state_sha256"] = _digest(body)
        parent_state = body["state_sha256"]
        steps.append(body)
    return steps


def _verify_v07_lineage(lineage: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]], dict[str, Any]]:
    if lineage.get("schema") != MIXED_LINEAGE_SCHEMA:
        raise MeshPrecisionCutterError("unsupported v0.7 mixed lineage receipt schema")
    observed = _lineage_digest(lineage)
    if lineage.get("lineage_sha256") != observed:
        raise MeshPrecisionCutterError("v0.7 lineage self-digest does not match its contents")
    root, axis = lineage.get("root"), lineage.get("axis")
    operations, steps, output = lineage.get("operations"), lineage.get("steps"), lineage.get("output")
    if not isinstance(root, dict) or not isinstance(axis, dict) or not isinstance(operations, list) or not isinstance(steps, list) or not isinstance(output, dict):
        raise MeshPrecisionCutterError("v0.7 lineage state has invalid structural types")
    root_sha = root.get("root_sha256")
    if root_sha != _digest({key: value for key, value in root.items() if key != "root_sha256"}):
        raise MeshPrecisionCutterError("v0.7 lineage root digest is invalid")
    if len(operations) != len(steps) or not operations:
        raise MeshPrecisionCutterError("v0.7 lineage operation/step history is inconsistent")
    for operation in operations:
        claimed = operation.get("resolved_operation_sha256")
        if claimed != _digest({key: value for key, value in operation.items() if key != "resolved_operation_sha256"}):
            raise MeshPrecisionCutterError(f"v0.7 operation digest is invalid: {operation.get('id')}")
    if steps != _steps_for_operations(root_sha, operations):
        raise MeshPrecisionCutterError("v0.7 lineage step hash chain is invalid")
    if lineage.get("cumulative_recipe_sha256") != _digest(operations):
        raise MeshPrecisionCutterError("v0.7 cumulative recipe digest is invalid")
    return root, axis, operations, output


def _legacy_parent(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    probe = _read_json_object(lineage_path)
    schema = probe.get("schema")
    axis_probe = {"axis_vector": specification["axis_vector"]}
    if schema == FABRICATION_LINEAGE_SCHEMA:
        base = _load_v04_parent_lineage(source_path, lineage_path, axis_probe, expected_lineage_sha256)
        operations = [_convert_legacy_notch(row) for row in base["resolved_cuts"]]
    elif schema in {HOLE_LINEAGE_SCHEMA, GENERAL_HOLE_LINEAGE_SCHEMA}:
        base = _load_v06_parent_lineage(source_path, lineage_path, axis_probe, expected_lineage_sha256)
        operations = [_convert_legacy_hole(row) for row in base["resolved_holes"]]
    else:
        raise MeshPrecisionCutterError("unsupported legacy lineage schema for v0.7 upgrade")
    parent_digest = _lineage_digest(probe)
    return {
        "root": base["root"],
        "frame": base["frame"],
        "order": base["order"],
        "cut_axis": base["cut_axis"],
        "alignment": base["alignment"],
        "operations": operations,
        "parent_lineage_sha256": parent_digest,
        "migration": {
            "from_schema": schema,
            "parent_lineage_sha256": parent_digest,
            "imported_operation_count": len(operations),
            "prior_output_exactly_recompiled_by_legacy_engine": True,
        },
    }


def _v07_parent(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    lineage = _read_json_object(lineage_path)
    root, axis, operations, output = _verify_v07_lineage(lineage)
    observed_lineage_sha = _lineage_digest(lineage)
    expected = _normalize_digest(expected_lineage_sha256, "expected_lineage_sha256")
    if expected is not None and expected != observed_lineage_sha:
        raise MeshPrecisionCutterError(
            "v0.7 lineage digest does not match expected_lineage_sha256",
            {"expected": expected, "observed": observed_lineage_sha},
        )
    current_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if current_sha != output.get("sha256"):
        raise MeshPrecisionCutterError(
            "resume source GLB does not match the v0.7 lineage output digest",
            {"expected": output.get("sha256"), "observed": current_sha},
        )
    current = _read_source_primitive(source_path)
    if current["source_sha256"] != current_sha:
        raise MeshPrecisionCutterError("resume source digest changed during v0.7 inspection")
    if current["material"] != root.get("material"):
        raise MeshPrecisionCutterError("resume source material no longer matches v0.7 root")
    frame = root.get("frame")
    if not isinstance(frame, dict) or frame.get("frame_sha256") != _digest({key: value for key, value in frame.items() if key != "frame_sha256"}):
        raise MeshPrecisionCutterError("v0.7 lineage frame digest is invalid")
    order_raw = axis.get("canonical_order")
    cut_axis = axis.get("frame_axis_index")
    if not isinstance(order_raw, list) or sorted(order_raw) != [0, 1, 2] or any(type(value) is not int for value in order_raw) or type(cut_axis) is not int or not 0 <= cut_axis <= 2:
        raise MeshPrecisionCutterError("v0.7 lineage axis state is invalid")
    order = tuple(order_raw)
    requested_axis, _direction_sign, alignment = _match_frame_axis(tuple(specification["axis_vector"]), frame)
    if requested_axis != cut_axis:
        raise MeshPrecisionCutterError(
            "v0.7 resume operations must remain on the lineage fabrication axis",
            {"lineage_axis": cut_axis, "requested_axis": requested_axis},
        )
    prior_name = output.get("name")
    if not isinstance(prior_name, str) or not prior_name:
        raise MeshPrecisionCutterError("v0.7 lineage output name is invalid")
    rebuilt = _compile_state(name=prior_name, frame=frame, order=order, material=root["material"], operations=operations)
    if rebuilt["glb_sha256"] != current_sha:
        raise MeshPrecisionCutterError(
            "v0.7 lineage does not deterministically rebuild the supplied prior GLB",
            {"recompiled": rebuilt["glb_sha256"], "observed": current_sha},
        )
    if output.get("specification_sha256") != rebuilt["specification_sha256"]:
        raise MeshPrecisionCutterError("v0.7 output specification digest does not match deterministic rebuild")
    return {
        "root": root,
        "frame": frame,
        "order": order,
        "cut_axis": cut_axis,
        "alignment": alignment,
        "operations": [dict(row) for row in operations],
        "parent_lineage_sha256": observed_lineage_sha,
        "migration": None,
    }


def _load_parent(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    probe = _read_json_object(lineage_path)
    if probe.get("schema") == MIXED_LINEAGE_SCHEMA:
        return _v07_parent(source_path, lineage_path, specification, expected_lineage_sha256)
    return _legacy_parent(source_path, lineage_path, specification, expected_lineage_sha256)


def _fresh_base(
    source_path: Path,
    specification: dict[str, Any],
    expected_source_sha256: str | None,
) -> dict[str, Any]:
    base = _root_from_source(source_path, specification, expected_source_sha256)
    return {
        "root": base["root"],
        "frame": base["frame"],
        "order": base["order"],
        "cut_axis": base["cut_axis"],
        "alignment": base["alignment"],
        "operations": [],
        "parent_lineage_sha256": None,
        "migration": None,
    }


def _resolve_new_operations(
    specification: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {row["id"] for row in existing}
    result: list[dict[str, Any]] = []
    for operation in specification["operations"]:
        if operation["id"] in existing_ids or any(row["id"] == operation["id"] for row in result):
            raise MeshPrecisionCutterError(f"mixed fabrication operation id already exists: {operation['id']}")
        result.append(_resolve_operation(operation, frame=frame, order=order))
    cumulative = existing + result
    if len(cumulative) > MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(f"cumulative mixed fabrication exceeds {MAX_CHAIN_CUTS} operations")
    _validate_operations(cumulative, frame)
    return result


def _build_lineage(
    *,
    specification: dict[str, Any],
    base: dict[str, Any],
    operations: list[dict[str, Any]],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    steps = _steps_for_operations(base["root"]["root_sha256"], operations)
    lineage = {
        "schema": MIXED_LINEAGE_SCHEMA,
        "root": base["root"],
        "axis": {
            "frame_axis_index": base["cut_axis"],
            "canonical_order": list(base["order"]),
            "axis_alignment": base["alignment"],
            "axis_vector_last_request": list(specification["axis_vector"]),
        },
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "migration": base["migration"],
        "operations": operations,
        "steps": steps,
        "cumulative_recipe_sha256": _digest(operations),
        "output": {
            "name": specification["name"],
            "sha256": compiled["glb_sha256"],
            "specification_sha256": compiled["specification_sha256"],
            "geometry": compiled["geometry"],
            "topology": compiled["topology"],
            "metrics": compiled["metrics"],
        },
        "truth_boundary": {
            "same_axis_mixed_holes_and_notches": True,
            "legacy_lineage_upgrade_requires_exact_legacy_recompile": True,
            "v07_resume_requires_exact_v07_recompile": True,
            "nonoverlap_and_nontouch_required": True,
            "cross_axis_chain": "NOT_SUPPORTED",
            "general_arbitrary_mesh_csg": False,
            "self_intersection": "NOT_PROVEN_BEYOND_EXPLICIT_NONOVERLAP_AND_MANIFOLD_EDGE_GATE",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "physical_manufacturing_behavior": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }
    lineage["lineage_sha256"] = _lineage_digest(lineage)
    return lineage


def build_mixed_fabrication(
    source_path: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    spec = prepare_mixed_fabrication(specification)
    if lineage_path is None:
        base = _fresh_base(source_path, spec, expected_source_sha256)
    else:
        if expected_source_sha256 is not None:
            expected = _normalize_digest(expected_source_sha256, "expected_source_sha256")
            observed = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if expected != observed:
                raise MeshPrecisionCutterError(
                    "resume source GLB digest does not match expected_source_sha256",
                    {"expected": expected, "observed": observed},
                )
        base = _load_parent(source_path, Path(lineage_path).resolve(), spec, expected_lineage_sha256)
    new_operations = _resolve_new_operations(spec, frame=base["frame"], order=base["order"], existing=base["operations"])
    cumulative = base["operations"] + new_operations
    compiled = _compile_state(name=spec["name"], frame=base["frame"], order=base["order"], material=base["root"]["material"], operations=cumulative)
    lineage = _build_lineage(specification=spec, base=base, operations=cumulative, compiled=compiled)
    return {
        "schema": MIXED_FABRICATION_SCHEMA,
        "specification": spec,
        "request_sha256": _digest({
            "schema": MIXED_FABRICATION_SCHEMA,
            "parent_lineage_sha256": base["parent_lineage_sha256"],
            "root_sha256": base["root"]["root_sha256"],
            "new_operations": new_operations,
        }),
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "migration": base["migration"],
        "resolved_new_operations": new_operations,
        "cumulative_operation_count": len(cumulative),
        "surface_specification": compiled["surface_specification"],
        "predicted_glb_sha256": compiled["glb_sha256"],
        "output_topology": compiled["topology"],
        "geometry": compiled["geometry"],
        "metrics": compiled["metrics"],
        "lineage": lineage,
        "truth_boundary": lineage["truth_boundary"],
    }


def publish_mixed_fabrication(
    source_path: Path,
    target: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    receipt_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    target = Path(target).resolve()
    if source_path == target:
        raise MeshPrecisionCutterError("v0.7 mixed fabrication requires distinct source_path and output path")
    parent_lineage = Path(lineage_path).resolve() if lineage_path is not None else None
    receipt = Path(receipt_path).resolve() if receipt_path is not None else target.with_suffix(target.suffix + ".mixed-fabrication.json")
    if receipt in {source_path, target}:
        raise MeshPrecisionCutterError("v0.7 mixed fabrication receipt must be distinct from source and output")
    if parent_lineage is not None and receipt == parent_lineage:
        raise MeshPrecisionCutterError("v0.7 continuation must publish a new receipt instead of overwriting its parent")
    if receipt.exists() and not replace:
        raise MeshPrecisionCutterError("v0.7 mixed fabrication receipt already exists; set replace=true to replace it")

    built = build_mixed_fabrication(
        source_path,
        specification,
        lineage_path=parent_lineage,
        expected_source_sha256=expected_source_sha256,
        expected_lineage_sha256=expected_lineage_sha256,
    )
    source_before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    previous_target = target.read_bytes() if target.exists() else None
    previous_receipt = receipt.read_bytes() if receipt.exists() else None
    try:
        publication = publish_glb(target, built["surface_specification"], replace=replace)
        if publication["sha256"] != built["predicted_glb_sha256"]:
            raise MeshPrecisionCutterError("published GLB digest differs from deterministic v0.7 precompile")
        receipt_bytes = _publish_receipt(receipt, built["lineage"], replace=replace)
    except (Procedural3DError, MeshPrecisionCutterError) as exc:
        _restore_bytes(target, previous_target)
        _restore_bytes(receipt, previous_receipt)
        if isinstance(exc, MeshPrecisionCutterError):
            raise
        raise MeshPrecisionCutterError(str(exc), getattr(exc, "details", {})) from exc

    source_after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_unchanged = source_before == source_after
    return {
        "truth_status": "VALIDATED_HASH_LINKED_MIXED_FABRICATION_CHAIN" if source_unchanged else "HOLD_SOURCE_CHANGED_DURING_MIXED_FABRICATION",
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "receipt_path": str(receipt),
        "receipt_bytes": receipt_bytes,
        "lineage_sha256": built["lineage"]["lineage_sha256"],
        "parent_lineage_sha256": built["parent_lineage_sha256"],
        "migration": built["migration"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "resolved_new_operations": built["resolved_new_operations"],
        "cumulative_operation_count": built["cumulative_operation_count"],
        "geometry": built["geometry"],
        "metrics": built["metrics"],
        "output_topology": built["output_topology"],
        "glb_validation": publication["post_publish_validation"],
        "source_unchanged_after_publication": source_unchanged,
        "observed_source_sha256_after_publication": source_after,
        "truth_boundary": built["truth_boundary"],
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

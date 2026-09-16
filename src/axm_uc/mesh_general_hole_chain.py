from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .mesh_fabrication_chain import (
    MAX_CHAIN_CUTS,
    _digest,
    _lineage_digest,
    _normalize_digest,
    _publish_receipt,
    _read_json_object,
    _restore_bytes,
)
from .mesh_hole_fabrication_chain import (
    HOLE_CHAIN_SCHEMA,
    HOLE_LINEAGE_SCHEMA,
    _load_parent_lineage as _load_v05_parent_lineage,
    _resolve_hole,
    _root_from_source,
    _steps_for_append,
    _validate_holes,
    prepare_hole_chain,
)
from .mesh_precision_cutter import (
    EPSILON,
    SOURCE_TOLERANCE,
    MeshPrecisionCutterError,
    _read_source_primitive,
    _signed_volume,
)
from .mesh_topology import MeshTopologyError, inspect_mesh_topology
from .oriented_mesh_precision_cutter import (
    _canonical_normal_to_world,
    _canonical_to_world,
    _match_frame_axis,
)
from .precision_cutter import _append_face, _surface_specification
from .procedural_3d import Procedural3DError, build_glb, publish_glb

GENERAL_HOLE_CHAIN_SCHEMA = "axm.mesh-hole-fabrication-chain/v0.6"
GENERAL_HOLE_LINEAGE_SCHEMA = "axm.mesh-hole-fabrication-lineage/v0.6"
SWEEP_COORD_TOLERANCE = 1e-10


def general_hole_chain_summary() -> dict[str, Any]:
    return {
        "schema": GENERAL_HOLE_CHAIN_SCHEMA,
        "lineage_schema": GENERAL_HOLE_LINEAGE_SCHEMA,
        "truth_status": "LIVE_HASH_LINKED_GENERAL_SAME_AXIS_HOLE_SWEEP",
        "operation": "round-through-hole-chain",
        "maximum_holes": MAX_CHAIN_CUTS,
        "source_scope": "one proven rigid rectangular-prism root frame with arbitrary non-overlapping same-axis round-hole polygons",
        "sweep_contract": "deterministic vertical cross-section decomposition at every resolved polygon vertex x-coordinate",
        "v05_lineage_upgrade_supported": True,
        "projection_separability_required": False,
        "notch_and_hole_mixing": False,
        "cross_axis_chain": False,
        "full_arbitrary_mesh_csg": False,
    }


def prepare_general_hole_chain(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("v0.6 hole-chain specification must be an object")
    adapted = dict(raw)
    if adapted.get("schema") != GENERAL_HOLE_CHAIN_SCHEMA:
        raise MeshPrecisionCutterError("unsupported v0.6 hole fabrication-chain schema")
    adapted["schema"] = HOLE_CHAIN_SCHEMA
    normalized = prepare_hole_chain(adapted)
    normalized["schema"] = GENERAL_HOLE_CHAIN_SCHEMA
    return normalized


def _hole_polygon(hole: dict[str, Any]) -> list[tuple[float, float]]:
    cx, _cy, cz = (float(value) for value in hole["center_canonical"])
    radius = float(hole["effective_radius"])
    segments = int(hole["segments"])
    return [
        (
            cx + radius * math.cos(2.0 * math.pi * index / segments),
            cz + radius * math.sin(2.0 * math.pi * index / segments),
        )
        for index in range(segments)
    ]


def _polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(
        0.5
        * sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
    )


def _eval_edge(
    polygon: list[tuple[float, float]], edge: int, x: float
) -> float:
    x0, z0 = polygon[edge]
    x1, z1 = polygon[(edge + 1) % len(polygon)]
    if abs(x1 - x0) <= SWEEP_COORD_TOLERANCE:
        return (z0 + z1) / 2.0
    amount = (x - x0) / (x1 - x0)
    return z0 + amount * (z1 - z0)


def _vertical_intersections(
    polygon: list[tuple[float, float]], x: float
) -> list[tuple[float, list[int]]]:
    observed: list[tuple[float, int]] = []
    for edge, first in enumerate(polygon):
        second = polygon[(edge + 1) % len(polygon)]
        x0, z0 = first
        x1, z1 = second
        if abs(x1 - x0) <= SWEEP_COORD_TOLERANCE:
            if abs(x - x0) <= SWEEP_COORD_TOLERANCE:
                observed.extend(((z0, edge), (z1, edge)))
            continue
        low, high = sorted((x0, x1))
        if x < low - SWEEP_COORD_TOLERANCE or x > high + SWEEP_COORD_TOLERANCE:
            continue
        amount = (x - x0) / (x1 - x0)
        if not -SWEEP_COORD_TOLERANCE <= amount <= 1.0 + SWEEP_COORD_TOLERANCE:
            continue
        observed.append((z0 + amount * (z1 - z0), edge))
    result: list[tuple[float, list[int]]] = []
    for z, edge in sorted(observed):
        if not result or abs(z - result[-1][0]) > SWEEP_COORD_TOLERANCE * 10.0:
            result.append((float(z), [edge]))
        elif edge not in result[-1][1]:
            result[-1][1].append(edge)
    return result


def _active_interval(
    polygon: list[tuple[float, float]], midpoint_x: float
) -> tuple[float, float, int, int] | None:
    intersections = _vertical_intersections(polygon, midpoint_x)
    if not intersections:
        return None
    if len(intersections) != 2:
        raise MeshPrecisionCutterError(
            "v0.6 resolved hole polygon produced an ambiguous vertical sweep interval",
            {"x": midpoint_x, "intersection_count": len(intersections)},
        )
    lower, upper = intersections
    if upper[0] - lower[0] <= SWEEP_COORD_TOLERANCE:
        return None
    return (lower[0], upper[0], lower[1][0], upper[1][0])


def _seam_events(
    polygons: list[list[tuple[float, float]]], x: float, half_depth: float
) -> list[float]:
    values = {-half_depth, half_depth}
    for polygon in polygons:
        values.update(round(z, 12) for z, _edges in _vertical_intersections(polygon, x))
    return sorted(float(value) for value in values)


def _clean_boundary(points: list[tuple[float, float]]) -> list[tuple[float, float]]:
    result: list[tuple[float, float]] = []
    for point in points:
        normalized = (float(point[0]), float(point[1]))
        if not result or math.dist(result[-1], normalized) > SWEEP_COORD_TOLERANCE:
            result.append(normalized)
    if len(result) > 1 and math.dist(result[0], result[-1]) <= SWEEP_COORD_TOLERANCE:
        result.pop()
    if len(result) < 3:
        raise MeshPrecisionCutterError("v0.6 sweep produced a collapsed free-region boundary")
    return result


def _build_cross_section_surface(
    width: float,
    depth: float,
    thickness: float,
    polygons: list[list[tuple[float, float]]],
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int], dict[str, Any]]:
    half_width, half_depth = width / 2.0, depth / 2.0
    x_events = {-half_width, half_width}
    for polygon in polygons:
        x_events.update(round(point[0], 12) for point in polygon)
    xs = sorted(float(value) for value in x_events)
    if len(xs) < 2:
        raise MeshPrecisionCutterError("v0.6 sweep has no usable cross-section strips")
    seams = {x: _seam_events(polygons, x, half_depth) for x in xs}
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    top, bottom = thickness / 2.0, -thickness / 2.0
    free_region_count = 0

    for left, right in zip(xs, xs[1:]):
        if right - left <= SWEEP_COORD_TOLERANCE:
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
            if first[1] >= second[0] - SWEEP_COORD_TOLERANCE:
                raise MeshPrecisionCutterError(
                    "v0.6 vertical sweep observed overlapping resolved hole polygons",
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
            if (
                (lower_left + lower_right) / 2.0
                >= (upper_left + upper_right) / 2.0 - SWEEP_COORD_TOLERANCE
            ):
                continue
            right_events = [
                z
                for z in seams[right]
                if lower_right + SWEEP_COORD_TOLERANCE < z < upper_right - SWEEP_COORD_TOLERANCE
            ]
            left_events = [
                z
                for z in seams[left]
                if lower_left + SWEEP_COORD_TOLERANCE < z < upper_left - SWEEP_COORD_TOLERANCE
            ]
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
                if math.dist(first, second) <= SWEEP_COORD_TOLERANCE:
                    continue
                _append_face(
                    positions,
                    normals,
                    indices,
                    [
                        (center_x, top, center_z),
                        (first[0], top, first[1]),
                        (second[0], top, second[1]),
                    ],
                    (0.0, 1.0, 0.0),
                )
                _append_face(
                    positions,
                    normals,
                    indices,
                    [
                        (center_x, bottom, center_z),
                        (first[0], bottom, first[1]),
                        (second[0], bottom, second[1]),
                    ],
                    (0.0, -1.0, 0.0),
                )
            free_region_count += 1

    for z, normal in ((-half_depth, (0.0, 0.0, -1.0)), (half_depth, (0.0, 0.0, 1.0))):
        for left, right in zip(xs, xs[1:]):
            _append_face(
                positions,
                normals,
                indices,
                [
                    (left, bottom, z),
                    (left, top, z),
                    (right, top, z),
                    (right, bottom, z),
                ],
                normal,
            )
    for x, normal in ((-half_width, (-1.0, 0.0, 0.0)), (half_width, (1.0, 0.0, 0.0))):
        seam = seams[x]
        for low, high in zip(seam, seam[1:]):
            _append_face(
                positions,
                normals,
                indices,
                [
                    (x, bottom, low),
                    (x, top, low),
                    (x, top, high),
                    (x, bottom, high),
                ],
                normal,
            )

    for polygon in polygons:
        center_x = sum(point[0] for point in polygon) / len(polygon)
        center_z = sum(point[1] for point in polygon) / len(polygon)
        for edge, first in enumerate(polygon):
            second = polygon[(edge + 1) % len(polygon)]
            edge_points = [first]
            x0, z0 = first
            x1, z1 = second
            if abs(x1 - x0) > SWEEP_COORD_TOLERANCE:
                low, high = sorted((x0, x1))
                for x in xs:
                    if low + SWEEP_COORD_TOLERANCE < x < high - SWEEP_COORD_TOLERANCE:
                        edge_points.append((x, _eval_edge(polygon, edge, x)))
                edge_points.sort(key=lambda point: (point[0] - x0) / (x1 - x0))
            edge_points.append(second)
            dx, dz = x1 - x0, z1 - z0
            length = math.hypot(dx, dz)
            if length <= SWEEP_COORD_TOLERANCE:
                raise MeshPrecisionCutterError("v0.6 hole polygon contains a collapsed edge")
            normal = (-dz / length, 0.0, dx / length)
            midpoint = ((x0 + x1) / 2.0, (z0 + z1) / 2.0)
            if normal[0] * (center_x - midpoint[0]) + normal[2] * (center_z - midpoint[1]) < 0.0:
                normal = (-normal[0], 0.0, -normal[2])
            for start, end in zip(edge_points, edge_points[1:]):
                _append_face(
                    positions,
                    normals,
                    indices,
                    [
                        (start[0], bottom, start[1]),
                        (end[0], bottom, end[1]),
                        (end[0], top, end[1]),
                        (start[0], top, start[1]),
                    ],
                    normal,
                )
    return positions, normals, indices, {
        "sweep_x_events": len(xs),
        "sweep_strips": len(xs) - 1,
        "free_regions": free_region_count,
    }


def _compile_state(
    *,
    name: str,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    material: dict[str, Any],
    holes: list[dict[str, Any]],
) -> dict[str, Any]:
    _validate_holes(holes, frame)
    width = float(frame["extents"][order[0]])
    thickness = float(frame["extents"][order[1]])
    depth = float(frame["extents"][order[2]])
    polygons = [_hole_polygon(hole) for hole in holes]
    for hole, polygon in zip(holes, polygons):
        observed_area = _polygon_area(polygon)
        if abs(observed_area - float(hole["polygonized_removed_area"])) > max(
            1e-9, observed_area * 1e-8
        ):
            raise MeshPrecisionCutterError(
                "v0.6 reconstructed hole polygon does not match its resolved area receipt",
                {"hole_id": hole["id"]},
            )
    canonical_positions, canonical_normals, indices, sweep = _build_cross_section_surface(
        width, depth, thickness, polygons
    )
    positions = [
        _canonical_to_world(point, frame, order) for point in canonical_positions
    ]
    normals = [
        _canonical_normal_to_world(normal, frame, order)
        for normal in canonical_normals
    ]
    try:
        topology = inspect_mesh_topology(
            positions, indices, weld_tolerance=SOURCE_TOLERANCE
        )
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if (
        topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        or topology["triangle_component_count"] != 1
    ):
        raise MeshPrecisionCutterError(
            "v0.6 hole sweep did not remain one closed oriented component",
            {"topology": topology},
        )
    source_volume = float(frame["box_volume"])
    output_volume = _signed_volume(positions, indices)
    removed_area = sum(float(hole["polygonized_removed_area"]) for hole in holes)
    expected_volume = source_volume - removed_area * thickness
    tolerance = max(source_volume * 1e-5, 1e-8)
    if output_volume <= 0.0 or abs(output_volume - expected_volume) > tolerance:
        raise MeshPrecisionCutterError(
            "v0.6 closed-mesh volume does not match the cumulative polygonized hole receipt",
            {
                "observed_output_volume": output_volume,
                "expected_output_volume": expected_volume,
                "tolerance": tolerance,
            },
        )
    surface = _surface_specification(name, positions, normals, indices, material)
    glb = build_glb(surface)
    return {
        "surface_specification": surface,
        "glb_sha256": hashlib.sha256(glb["body"]).hexdigest(),
        "specification_sha256": glb["specification_sha256"],
        "topology": topology,
        "geometry": {
            "vertices": len(positions),
            "triangles": len(indices) // 3,
            **sweep,
        },
        "metrics": {
            "source_volume": source_volume,
            "output_volume": output_volume,
            "removed_volume": source_volume - output_volume,
            "polygonized_removed_area": removed_area,
            "fabrication_thickness": thickness,
        },
    }


def _verify_lineage_steps(
    root_sha256: str,
    holes: list[dict[str, Any]],
    steps: list[dict[str, Any]],
) -> None:
    if len(holes) != len(steps) or not holes:
        raise MeshPrecisionCutterError("v0.6 lineage hole/step history is inconsistent")
    parent_state = root_sha256
    for index, (hole, step) in enumerate(zip(holes, steps), start=1):
        if not isinstance(hole, dict) or not isinstance(step, dict):
            raise MeshPrecisionCutterError("v0.6 lineage entries must be objects")
        hole_sha = hole.get("resolved_hole_sha256")
        if hole_sha != _digest(
            {key: value for key, value in hole.items() if key != "resolved_hole_sha256"}
        ):
            raise MeshPrecisionCutterError(f"v0.6 hole digest is invalid at step {index}")
        body = {
            "step": index,
            "hole_id": hole.get("id"),
            "hole_sha256": hole_sha,
            "parent_state_sha256": parent_state,
        }
        state_sha = _digest(body)
        if (
            step.get("step") != index
            or step.get("hole_id") != hole.get("id")
            or step.get("hole_sha256") != hole_sha
            or step.get("parent_state_sha256") != parent_state
            or step.get("state_sha256") != state_sha
        ):
            raise MeshPrecisionCutterError(
                f"v0.6 lineage step hash chain is invalid at step {index}"
            )
        parent_state = state_sha


def _load_v06_parent_lineage(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    lineage = _read_json_object(lineage_path)
    if lineage.get("schema") == HOLE_LINEAGE_SCHEMA:
        return _load_v05_parent_lineage(
            source_path,
            lineage_path,
            specification,
            expected_lineage_sha256,
        )
    if lineage.get("schema") != GENERAL_HOLE_LINEAGE_SCHEMA:
        raise MeshPrecisionCutterError("unsupported v0.6 hole lineage receipt schema")
    observed_lineage_sha = _lineage_digest(lineage)
    if lineage.get("lineage_sha256") != observed_lineage_sha:
        raise MeshPrecisionCutterError("v0.6 lineage self-digest does not match its contents")
    expected = _normalize_digest(expected_lineage_sha256, "expected_lineage_sha256")
    if expected is not None and expected != observed_lineage_sha:
        raise MeshPrecisionCutterError(
            "v0.6 lineage digest does not match expected_lineage_sha256",
            {"expected": expected, "observed": observed_lineage_sha},
        )
    root, axis = lineage.get("root"), lineage.get("axis")
    holes, steps, output = lineage.get("holes"), lineage.get("steps"), lineage.get("output")
    if not all(
        (
            isinstance(root, dict),
            isinstance(axis, dict),
            isinstance(holes, list),
            isinstance(steps, list),
            isinstance(output, dict),
        )
    ):
        raise MeshPrecisionCutterError("v0.6 lineage state has invalid structural types")
    root_sha = root.get("root_sha256")
    if root_sha != _digest({key: value for key, value in root.items() if key != "root_sha256"}):
        raise MeshPrecisionCutterError("v0.6 lineage root digest is invalid")
    _verify_lineage_steps(root_sha, holes, steps)
    if lineage.get("cumulative_recipe_sha256") != _digest(holes):
        raise MeshPrecisionCutterError("v0.6 cumulative recipe digest is invalid")
    if len(holes) >= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError("v0.6 lineage already reached the hole limit")
    current_sha = hashlib.sha256(source_path.read_bytes()).hexdigest()
    if current_sha != output.get("sha256"):
        raise MeshPrecisionCutterError(
            "resume source GLB does not match the v0.6 lineage final output digest",
            {"expected": output.get("sha256"), "observed": current_sha},
        )
    current = _read_source_primitive(source_path)
    if current["source_sha256"] != current_sha:
        raise MeshPrecisionCutterError("resume source digest changed during v0.6 inspection")
    if current["material"] != root.get("material"):
        raise MeshPrecisionCutterError("resume source material no longer matches v0.6 root")
    frame = root.get("frame")
    if not isinstance(frame, dict) or frame.get("frame_sha256") != _digest(
        {key: value for key, value in frame.items() if key != "frame_sha256"}
    ):
        raise MeshPrecisionCutterError("v0.6 lineage frame digest is invalid")
    order_raw = axis.get("canonical_order")
    cut_axis = axis.get("frame_axis_index")
    if (
        not isinstance(order_raw, list)
        or sorted(order_raw) != [0, 1, 2]
        or any(type(value) is not int for value in order_raw)
        or type(cut_axis) is not int
        or not 0 <= cut_axis <= 2
    ):
        raise MeshPrecisionCutterError("v0.6 lineage axis state is invalid")
    order = tuple(order_raw)
    requested_axis, direction_sign, alignment = _match_frame_axis(
        tuple(specification["axis_vector"]), frame
    )
    if requested_axis != cut_axis:
        raise MeshPrecisionCutterError(
            "v0.6 resume holes must remain on the lineage fabrication axis",
            {"lineage_axis": cut_axis, "requested_axis": requested_axis},
        )
    prior_name = output.get("name")
    if not isinstance(prior_name, str) or not prior_name:
        raise MeshPrecisionCutterError("v0.6 lineage output name is invalid")
    rebuilt = _compile_state(
        name=prior_name,
        frame=frame,
        order=order,
        material=root["material"],
        holes=holes,
    )
    if rebuilt["glb_sha256"] != current_sha:
        raise MeshPrecisionCutterError(
            "v0.6 lineage does not deterministically rebuild the supplied prior GLB",
            {"recompiled": rebuilt["glb_sha256"], "observed": current_sha},
        )
    if output.get("specification_sha256") != rebuilt["specification_sha256"]:
        raise MeshPrecisionCutterError(
            "v0.6 output specification digest does not match deterministic rebuild"
        )
    return {
        "root": root,
        "frame": frame,
        "order": order,
        "cut_axis": cut_axis,
        "direction_sign": direction_sign,
        "alignment": alignment,
        "resolved_holes": [dict(value) for value in holes],
        "steps": [dict(value) for value in steps],
        "parent_lineage_sha256": observed_lineage_sha,
        "upgraded_from_v05": False,
    }


def _resolve_new_holes(
    specification: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {hole["id"] for hole in existing}
    result: list[dict[str, Any]] = []
    for hole in specification["holes"]:
        if hole["id"] in existing_ids or any(item["id"] == hole["id"] for item in result):
            raise MeshPrecisionCutterError(f"hole id already exists in lineage: {hole['id']}")
        result.append(_resolve_hole(hole, frame=frame, order=order))
    cumulative = existing + result
    if len(cumulative) > MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(f"cumulative hole chain exceeds {MAX_CHAIN_CUTS} holes")
    _validate_holes(cumulative, frame)
    return result


def _build_lineage(
    specification: dict[str, Any],
    base: dict[str, Any],
    holes: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    lineage = {
        "schema": GENERAL_HOLE_LINEAGE_SCHEMA,
        "root": base["root"],
        "axis": {
            "frame_axis_index": base["cut_axis"],
            "canonical_order": list(base["order"]),
            "axis_alignment": base["alignment"],
            "axis_vector_last_request": list(specification["axis_vector"]),
        },
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "holes": holes,
        "steps": steps,
        "cumulative_recipe_sha256": _digest(holes),
        "output": {
            "name": specification["name"],
            "sha256": compiled["glb_sha256"],
            "specification_sha256": compiled["specification_sha256"],
            "geometry": compiled["geometry"],
            "topology": compiled["topology"],
            "metrics": compiled["metrics"],
        },
        "truth_boundary": {
            "previous_output_recompiled_before_resume": base["parent_lineage_sha256"] is not None,
            "v05_lineage_upgrade_supported": True,
            "hash_linked_append_only_steps": True,
            "projection_separability_required": False,
            "same_axis_arbitrary_nonoverlapping_round_hole_layouts": True,
            "collinear_hole_wall_tessellation_may_refine_when_new_sweep_events_are_added": True,
            "resolved_physical_hole_polygon_and_area_remain_bound_to_each_hole_digest": True,
            "notch_and_hole_mixing": "NOT_SUPPORTED",
            "cross_axis_chain": "NOT_SUPPORTED",
            "full_arbitrary_mesh_csg": False,
            "cryptographic_authorship_signature": "NOT_PROVIDED",
            "self_intersection": "NOT_PROVEN_BEYOND_EXPLICIT_NONOVERLAP_AND_MANIFOLD_EDGE_GATE",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }
    lineage["lineage_sha256"] = _lineage_digest(lineage)
    return lineage


def build_general_hole_chain(
    source_path: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    spec = prepare_general_hole_chain(specification)
    if lineage_path is None:
        base = _root_from_source(source_path, spec, expected_source_sha256)
        base["upgraded_from_v05"] = False
    else:
        if expected_source_sha256 is not None:
            expected = _normalize_digest(expected_source_sha256, "expected_source_sha256")
            observed = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if expected != observed:
                raise MeshPrecisionCutterError(
                    "resume source GLB digest does not match expected_source_sha256",
                    {"expected": expected, "observed": observed},
                )
        parent_path = Path(lineage_path).resolve()
        parent_probe = _read_json_object(parent_path)
        was_v05 = parent_probe.get("schema") == HOLE_LINEAGE_SCHEMA
        base = _load_v06_parent_lineage(
            source_path,
            parent_path,
            spec,
            expected_lineage_sha256,
        )
        base["upgraded_from_v05"] = was_v05
    new_holes = _resolve_new_holes(
        spec,
        frame=base["frame"],
        order=base["order"],
        existing=base["resolved_holes"],
    )
    cumulative = base["resolved_holes"] + new_holes
    steps = _steps_for_append(
        base["root"]["root_sha256"], base["steps"], new_holes
    )
    compiled = _compile_state(
        name=spec["name"],
        frame=base["frame"],
        order=base["order"],
        material=base["root"]["material"],
        holes=cumulative,
    )
    lineage = _build_lineage(spec, base, cumulative, steps, compiled)
    return {
        "schema": GENERAL_HOLE_CHAIN_SCHEMA,
        "specification": spec,
        "request_sha256": _digest(
            {
                "schema": GENERAL_HOLE_CHAIN_SCHEMA,
                "parent_lineage_sha256": base["parent_lineage_sha256"],
                "root_sha256": base["root"]["root_sha256"],
                "new_holes": new_holes,
            }
        ),
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "upgraded_from_v05": base.get("upgraded_from_v05", False),
        "resolved_new_holes": new_holes,
        "cumulative_hole_count": len(cumulative),
        "surface_specification": compiled["surface_specification"],
        "predicted_glb_sha256": compiled["glb_sha256"],
        "output_topology": compiled["topology"],
        "geometry": compiled["geometry"],
        "metrics": compiled["metrics"],
        "lineage": lineage,
        "truth_boundary": lineage["truth_boundary"],
    }


def publish_general_hole_chain(
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
        raise MeshPrecisionCutterError("v0.6 hole chain requires distinct source and output paths")
    parent_lineage = Path(lineage_path).resolve() if lineage_path is not None else None
    receipt = (
        Path(receipt_path).resolve()
        if receipt_path is not None
        else target.with_suffix(target.suffix + ".hole-sweep.json")
    )
    if receipt in {source_path, target}:
        raise MeshPrecisionCutterError("v0.6 receipt must be distinct from source and output")
    if parent_lineage is not None and receipt == parent_lineage:
        raise MeshPrecisionCutterError("v0.6 resume must publish a new receipt")
    if receipt.exists() and not replace:
        raise MeshPrecisionCutterError("v0.6 receipt already exists; set replace=true to replace it")
    built = build_general_hole_chain(
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
            raise MeshPrecisionCutterError(
                "published GLB digest differs from the deterministically precompiled v0.6 output"
            )
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
        "truth_status": (
            "VALIDATED_HASH_LINKED_GENERAL_SAME_AXIS_HOLE_SWEEP"
            if source_unchanged
            else "HOLD_SOURCE_CHANGED_DURING_V06_PUBLICATION"
        ),
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "receipt_path": str(receipt),
        "receipt_bytes": receipt_bytes,
        "lineage_sha256": built["lineage"]["lineage_sha256"],
        "parent_lineage_sha256": built["parent_lineage_sha256"],
        "upgraded_from_v05": built["upgraded_from_v05"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "resolved_new_holes": built["resolved_new_holes"],
        "cumulative_hole_count": built["cumulative_hole_count"],
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

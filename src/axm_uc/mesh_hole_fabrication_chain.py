from __future__ import annotations

import hashlib
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
from .mesh_precision_cutter import (
    EPSILON,
    SOURCE_TOLERANCE,
    MeshPrecisionCutterError,
    _read_source_primitive,
    _signed_volume,
)
from .mesh_topology import MeshTopologyError, inspect_mesh_topology
from .oriented_mesh_precision_cutter import (
    _axis_vector,
    _canonical_axis_order,
    _canonical_normal_to_world,
    _canonical_point_from_world,
    _canonical_to_world,
    _match_frame_axis,
    _recognize_oriented_box,
    _vec3,
)
from .precision_cutter import (
    ANGLE_EPSILON,
    MAX_HOLE_SEGMENTS,
    _append_face,
    _canonical,
    _deduplicate_angles,
    _number,
    _ray_to_rectangle,
    _surface_specification,
)
from .procedural_3d import Procedural3DError, build_glb, publish_glb

HOLE_CHAIN_SCHEMA = "axm.mesh-hole-fabrication-chain/v0.5"
HOLE_LINEAGE_SCHEMA = "axm.mesh-hole-fabrication-lineage/v0.5"


def hole_chain_summary() -> dict[str, Any]:
    return {
        "schema": HOLE_CHAIN_SCHEMA,
        "lineage_schema": HOLE_LINEAGE_SCHEMA,
        "truth_status": "LIVE_HASH_LINKED_MULTI_HOLE_FABRICATION",
        "operation": "round-through-hole-chain",
        "maximum_holes": MAX_CHAIN_CUTS,
        "source_scope": "one proven rigid rectangular-prism source frame, then exact hash-bound cumulative outputs",
        "resume_contract": "deterministically recompile the complete prior hole set and require exact previous GLB digest match before append",
        "rotated_translated_source_supported": True,
        "projection_separable_multi_hole_layouts": True,
        "notch_and_hole_mixing": False,
        "cross_axis_chain": False,
        "full_arbitrary_mesh_csg": False,
    }


def _hole(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError(f"holes[{index}] must be an object")
    required = {"id", "center", "radius", "segments"}
    optional = {"kerf"}
    missing = required - set(raw)
    extra = set(raw) - required - optional
    if missing or extra:
        raise MeshPrecisionCutterError(
            f"holes[{index}] fields do not match the v0.5 grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    hole_id = raw["id"]
    if not isinstance(hole_id, str) or not 1 <= len(hole_id.strip()) <= 80:
        raise MeshPrecisionCutterError(f"holes[{index}].id must contain 1..80 characters")
    segments = raw["segments"]
    if type(segments) is not int or not 8 <= segments <= MAX_HOLE_SEGMENTS:
        raise MeshPrecisionCutterError(
            f"holes[{index}].segments must be an integer from 8 through {MAX_HOLE_SEGMENTS}"
        )
    return {
        "id": hole_id.strip(),
        "operation": "round-through-hole",
        "center": list(_vec3(raw["center"], f"holes[{index}].center")),
        "radius": _number(raw["radius"], f"holes[{index}].radius", 0.0001, 100000.0),
        "segments": segments,
        "kerf": _number(raw.get("kerf", 0.0), f"holes[{index}].kerf", 0.0, 1000.0),
    }


def prepare_hole_chain(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("v0.5 hole-chain specification must be an object")
    required = {"schema", "name", "axis_vector", "holes"}
    if set(raw) != required:
        raise MeshPrecisionCutterError(
            "v0.5 hole-chain fields do not match the bounded grammar",
            {
                "missing": sorted(required - set(raw)),
                "unexpected": sorted(set(raw) - required),
            },
        )
    if raw["schema"] != HOLE_CHAIN_SCHEMA:
        raise MeshPrecisionCutterError("unsupported hole fabrication-chain schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise MeshPrecisionCutterError("name must contain 1..120 characters")
    holes = raw["holes"]
    if not isinstance(holes, list) or not 1 <= len(holes) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"holes must contain 1 through {MAX_CHAIN_CUTS} new round-through holes"
        )
    normalized = [_hole(value, index) for index, value in enumerate(holes)]
    ids = [value["id"] for value in normalized]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("new hole-chain ids must be unique")
    return {
        "schema": HOLE_CHAIN_SCHEMA,
        "name": name.strip(),
        "axis_vector": list(_axis_vector(raw["axis_vector"])),
        "holes": normalized,
    }


def _polygon_area(points: list[tuple[float, float]]) -> float:
    return abs(
        0.5
        * sum(
            points[index][0] * points[(index + 1) % len(points)][1]
            - points[(index + 1) % len(points)][0] * points[index][1]
            for index in range(len(points))
        )
    )


def _resolve_hole(
    hole: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> dict[str, Any]:
    width = float(frame["extents"][order[0]])
    thickness = float(frame["extents"][order[1]])
    depth = float(frame["extents"][order[2]])
    half_width, half_thickness, half_depth = width / 2.0, thickness / 2.0, depth / 2.0
    center = _canonical_point_from_world(tuple(hole["center"]), frame, order)
    tolerance = max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    if abs(center[1]) > half_thickness + tolerance:
        raise MeshPrecisionCutterError(
            f"hole {hole['id']} center lies outside the stock thickness"
        )
    effective_radius = float(hole["radius"]) + float(hole["kerf"]) / 2.0
    available = min(half_width - abs(center[0]), half_depth - abs(center[2]))
    if effective_radius <= 0.0 or effective_radius >= available - tolerance:
        raise MeshPrecisionCutterError(
            f"hole {hole['id']} must stay strictly inside the stock cross-section"
        )
    segment_angles = [
        2.0 * math.pi * index / int(hole["segments"])
        for index in range(int(hole["segments"]))
    ]
    polygon = [
        (
            center[0] + effective_radius * math.cos(angle),
            center[2] + effective_radius * math.sin(angle),
        )
        for angle in segment_angles
    ]
    result = {
        "id": hole["id"],
        "operation": "round-through-hole",
        "center_world": list(hole["center"]),
        "center_canonical": [float(value) for value in center],
        "requested_radius": float(hole["radius"]),
        "effective_radius": effective_radius,
        "segments": int(hole["segments"]),
        "kerf": float(hole["kerf"]),
        "polygonized_removed_area": _polygon_area(polygon),
        "analytic_requested_removed_area": math.pi * float(hole["radius"]) ** 2,
        "analytic_effective_removed_area": math.pi * effective_radius**2,
        "resolved_hole_sha256": "",
    }
    result["resolved_hole_sha256"] = _digest(
        {key: value for key, value in result.items() if key != "resolved_hole_sha256"}
    )
    return result


def _validate_holes(
    holes: list[dict[str, Any]], frame: dict[str, Any]
) -> None:
    if not 1 <= len(holes) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cumulative hole chain must contain 1 through {MAX_CHAIN_CUTS} holes"
        )
    ids = [hole["id"] for hole in holes]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("cumulative hole-chain ids must remain unique")
    tolerance = max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    for index, first in enumerate(holes):
        ax, _ay, az = first["center_canonical"]
        ar = float(first["effective_radius"])
        for second in holes[index + 1 :]:
            bx, _by, bz = second["center_canonical"]
            br = float(second["effective_radius"])
            distance = math.hypot(float(ax) - float(bx), float(az) - float(bz))
            if distance <= ar + br + tolerance:
                raise MeshPrecisionCutterError(
                    "v0.5 refuses overlapping or touching cumulative round holes",
                    {"first_hole": first["id"], "second_hole": second["id"]},
                )


def _projection_is_separable(
    holes: list[dict[str, Any]], coordinate: int, tolerance: float
) -> bool:
    intervals = sorted(
        (
            float(hole["center_canonical"][coordinate]) - float(hole["effective_radius"]),
            float(hole["center_canonical"][coordinate]) + float(hole["effective_radius"]),
        )
        for hole in holes
    )
    return all(
        first[1] < second[0] - tolerance
        for first, second in zip(intervals, intervals[1:])
    )


def _choose_partition_axis(holes: list[dict[str, Any]], frame: dict[str, Any]) -> str:
    tolerance = max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    if len(holes) == 1 or _projection_is_separable(holes, 0, tolerance):
        return "u"
    if _projection_is_separable(holes, 2, tolerance):
        return "v"
    raise MeshPrecisionCutterError(
        "v0.5 multi-hole layout must be separable along canonical u or v so deterministic slab seams can be proven",
        {
            "hole_ids": [hole["id"] for hole in holes],
            "general_polygon_with_holes_triangulation": "NOT_YET_SUPPORTED",
        },
    )


def _slab_hole_geometry(
    stock_size: tuple[float, float],
    center: tuple[float, float],
    radius: float,
    segments: int,
    thickness: float,
    extra_boundary_points: list[tuple[float, float]] | None = None,
) -> tuple[
    list[tuple[float, float, float]],
    list[tuple[float, float, float]],
    list[int],
    list[tuple[float, float]],
    list[tuple[float, float]],
]:
    width, depth = stock_size
    half_width, half_depth = width / 2.0, depth / 2.0
    cx, cz = center
    available = min(half_width - abs(cx), half_depth - abs(cz))
    if radius <= 0.0 or radius >= available - EPSILON:
        raise MeshPrecisionCutterError(
            "round hole must stay strictly inside its deterministic slab"
        )
    tau = 2.0 * math.pi
    base_angles = [tau * index / segments for index in range(segments)]
    event_points = [
        (-half_width, -half_depth),
        (-half_width, half_depth),
        (half_width, -half_depth),
        (half_width, half_depth),
    ]
    event_points.extend(extra_boundary_points or [])
    event_angles = [
        math.atan2(point[1] - cz, point[0] - cx) % tau for point in event_points
    ]
    inner = [
        (cx + radius * math.cos(angle), cz + radius * math.sin(angle))
        for angle in base_angles
    ]
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    outer_points: list[tuple[float, float]] = []
    top, bottom = thickness / 2.0, -thickness / 2.0

    for index, start in enumerate(base_angles):
        end = base_angles[index + 1] if index + 1 < segments else tau
        events = [start]
        for value in event_angles:
            candidate = value
            if index == segments - 1 and candidate < start:
                candidate += tau
            if start + ANGLE_EPSILON < candidate < end - ANGLE_EPSILON:
                events.append(candidate)
        events.append(end)
        events = _deduplicate_angles(events)
        if index == segments - 1:
            normalized: list[float] = []
            for value in events:
                adjusted = value
                if adjusted < start - ANGLE_EPSILON:
                    adjusted += tau
                if not normalized or adjusted - normalized[-1] > ANGLE_EPSILON:
                    normalized.append(adjusted)
            events = normalized
        events = sorted(events)
        outer = [
            _ray_to_rectangle(center, angle % tau, half_width, half_depth)
            for angle in events
        ]
        outer_points.extend(outer)
        current_inner = inner[index]
        next_inner = inner[(index + 1) % segments]
        for outer_index in range(len(outer) - 1):
            first_outer, second_outer = outer[outer_index], outer[outer_index + 1]
            _append_face(
                positions,
                normals,
                indices,
                [
                    (current_inner[0], top, current_inner[1]),
                    (first_outer[0], top, first_outer[1]),
                    (second_outer[0], top, second_outer[1]),
                ],
                (0.0, 1.0, 0.0),
            )
            _append_face(
                positions,
                normals,
                indices,
                [
                    (current_inner[0], bottom, current_inner[1]),
                    (first_outer[0], bottom, first_outer[1]),
                    (second_outer[0], bottom, second_outer[1]),
                ],
                (0.0, -1.0, 0.0),
            )
            dx = second_outer[0] - first_outer[0]
            dz = second_outer[1] - first_outer[1]
            length = math.hypot(dx, dz)
            if length > EPSILON:
                outer_normal = (dz / length, 0.0, -dx / length)
                _append_face(
                    positions,
                    normals,
                    indices,
                    [
                        (first_outer[0], bottom, first_outer[1]),
                        (first_outer[0], top, first_outer[1]),
                        (second_outer[0], top, second_outer[1]),
                        (second_outer[0], bottom, second_outer[1]),
                    ],
                    outer_normal,
                )
        last_outer = outer[-1]
        _append_face(
            positions,
            normals,
            indices,
            [
                (current_inner[0], top, current_inner[1]),
                (last_outer[0], top, last_outer[1]),
                (next_inner[0], top, next_inner[1]),
            ],
            (0.0, 1.0, 0.0),
        )
        _append_face(
            positions,
            normals,
            indices,
            [
                (current_inner[0], bottom, current_inner[1]),
                (last_outer[0], bottom, last_outer[1]),
                (next_inner[0], bottom, next_inner[1]),
            ],
            (0.0, -1.0, 0.0),
        )
        middle_angle = (start + end) / 2.0
        inner_normal = (-math.cos(middle_angle), 0.0, -math.sin(middle_angle))
        _append_face(
            positions,
            normals,
            indices,
            [
                (current_inner[0], bottom, current_inner[1]),
                (next_inner[0], bottom, next_inner[1]),
                (next_inner[0], top, next_inner[1]),
                (current_inner[0], top, current_inner[1]),
            ],
            inner_normal,
        )
    return positions, normals, indices, inner, outer_points


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
    partition = _choose_partition_axis(holes, frame)
    if partition == "u":
        minimum, maximum = -width / 2.0, width / 2.0
        full_other = depth
        partition_coordinate = lambda hole: float(hole["center_canonical"][0])
        other_coordinate = lambda hole: float(hole["center_canonical"][2])

        def local_point_to_canonical(point: tuple[float, float, float], slab_center: float) -> tuple[float, float, float]:
            return (point[0] + slab_center, point[1], point[2])

        def local_normal_to_canonical(normal: tuple[float, float, float]) -> tuple[float, float, float]:
            return normal

    else:
        minimum, maximum = -depth / 2.0, depth / 2.0
        full_other = width
        partition_coordinate = lambda hole: float(hole["center_canonical"][2])
        other_coordinate = lambda hole: -float(hole["center_canonical"][0])

        def local_point_to_canonical(point: tuple[float, float, float], slab_center: float) -> tuple[float, float, float]:
            return (-point[2], point[1], slab_center + point[0])

        def local_normal_to_canonical(normal: tuple[float, float, float]) -> tuple[float, float, float]:
            return (-normal[2], normal[1], normal[0])

    ordered_holes = sorted(holes, key=lambda hole: (partition_coordinate(hole), hole["id"]))
    intervals = [
        (
            partition_coordinate(hole) - float(hole["effective_radius"]),
            partition_coordinate(hole) + float(hole["effective_radius"]),
        )
        for hole in ordered_holes
    ]
    tolerance = max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    if any(
        first[1] >= second[0] - tolerance
        for first, second in zip(intervals, intervals[1:])
    ):
        raise MeshPrecisionCutterError(
            "chosen v0.5 slab partition axis is not strictly separable"
        )
    slab_bounds = [minimum]
    slab_bounds.extend(
        (first[1] + second[0]) / 2.0
        for first, second in zip(intervals, intervals[1:])
    )
    slab_bounds.append(maximum)

    initial: list[dict[str, Any]] = []
    for index, hole in enumerate(ordered_holes):
        low, high = slab_bounds[index], slab_bounds[index + 1]
        slab_width = high - low
        slab_center = (low + high) / 2.0
        geometry = _slab_hole_geometry(
            (slab_width, full_other),
            (
                partition_coordinate(hole) - slab_center,
                other_coordinate(hole),
            ),
            float(hole["effective_radius"]),
            int(hole["segments"]),
            thickness,
        )
        initial.append(
            {
                "slab_width": slab_width,
                "slab_center": slab_center,
                "geometry": geometry,
            }
        )

    seam_values: list[list[float]] = []
    for index in range(len(ordered_holes) - 1):
        values = {-full_other / 2.0, full_other / 2.0}
        left = initial[index]
        right = initial[index + 1]
        left_half = float(left["slab_width"]) / 2.0
        right_half = float(right["slab_width"]) / 2.0
        for x, z in left["geometry"][4]:
            if abs(float(x) - left_half) <= tolerance * 4.0:
                values.add(round(float(z), 12))
        for x, z in right["geometry"][4]:
            if abs(float(x) + right_half) <= tolerance * 4.0:
                values.add(round(float(z), 12))
        seam_values.append(sorted(values))

    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []

    def append_triangle(
        triangle_points: list[tuple[float, float, float]],
        triangle_normals: list[tuple[float, float, float]],
    ) -> None:
        start = len(positions)
        positions.extend(triangle_points)
        normals.extend(triangle_normals)
        indices.extend((start, start + 1, start + 2))

    for index, hole in enumerate(ordered_holes):
        low, high = slab_bounds[index], slab_bounds[index + 1]
        slab_width = high - low
        slab_center = (low + high) / 2.0
        extra: list[tuple[float, float]] = []
        if index > 0:
            extra.extend((-slab_width / 2.0, value) for value in seam_values[index - 1])
        if index + 1 < len(ordered_holes):
            extra.extend((slab_width / 2.0, value) for value in seam_values[index])
        local_positions, local_normals, local_indices, inner, _outer = _slab_hole_geometry(
            (slab_width, full_other),
            (
                partition_coordinate(hole) - slab_center,
                other_coordinate(hole),
            ),
            float(hole["effective_radius"]),
            int(hole["segments"]),
            thickness,
            extra,
        )
        observed_area = _polygon_area(inner)
        if abs(observed_area - float(hole["polygonized_removed_area"])) > max(1e-9, observed_area * 1e-8):
            raise MeshPrecisionCutterError(
                "slab seam refinement changed a previously resolved hole boundary",
                {"hole_id": hole["id"]},
            )
        for offset in range(0, len(local_indices), 3):
            refs = local_indices[offset : offset + 3]
            triangle_points = [local_positions[ref] for ref in refs]
            triangle_normals = [local_normals[ref] for ref in refs]
            normal = triangle_normals[0]
            include = True
            if abs(float(normal[1])) < 0.5:
                x_values = [float(point[0]) for point in triangle_points]
                if all(
                    abs(value + slab_width / 2.0) <= tolerance * 4.0
                    for value in x_values
                ):
                    include = index == 0
                elif all(
                    abs(value - slab_width / 2.0) <= tolerance * 4.0
                    for value in x_values
                ):
                    include = index + 1 == len(ordered_holes)
            if not include:
                continue
            canonical_points = [
                local_point_to_canonical(point, slab_center)
                for point in triangle_points
            ]
            canonical_normals = [
                local_normal_to_canonical(normal_row)
                for normal_row in triangle_normals
            ]
            world_points = [
                _canonical_to_world(point, frame, order)
                for point in canonical_points
            ]
            world_normals = [
                _canonical_normal_to_world(normal_row, frame, order)
                for normal_row in canonical_normals
            ]
            append_triangle(world_points, world_normals)

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
            "v0.5 cumulative hole output did not remain one closed oriented component",
            {"topology": topology},
        )
    volume = _signed_volume(positions, indices)
    source_volume = float(frame["box_volume"])
    polygonized_area = sum(float(hole["polygonized_removed_area"]) for hole in holes)
    expected_volume = source_volume - polygonized_area * thickness
    volume_tolerance = max(source_volume * 1e-5, 1e-8)
    if volume <= 0.0 or abs(volume - expected_volume) > volume_tolerance:
        raise MeshPrecisionCutterError(
            "closed-mesh volume does not match the cumulative round-hole receipt",
            {
                "observed_output_volume": volume,
                "expected_output_volume": expected_volume,
                "tolerance": volume_tolerance,
            },
        )
    surface = _surface_specification(name, positions, normals, indices, material)
    glb = build_glb(surface)
    body = glb["body"]
    return {
        "surface_specification": surface,
        "glb_body": body,
        "glb_sha256": hashlib.sha256(body).hexdigest(),
        "specification_sha256": glb["specification_sha256"],
        "topology": topology,
        "partition_axis": partition,
        "geometry": {
            "vertices": len(positions),
            "triangles": len(indices) // 3,
            "slabs": len(holes),
            "seams": max(0, len(holes) - 1),
        },
        "metrics": {
            "source_volume": source_volume,
            "output_volume": volume,
            "removed_volume": source_volume - volume,
            "polygonized_removed_area": polygonized_area,
            "fabrication_thickness": thickness,
        },
    }


def _root_from_source(
    source_path: Path,
    specification: dict[str, Any],
    expected_source_sha256: str | None,
) -> dict[str, Any]:
    expected = _normalize_digest(expected_source_sha256, "expected_source_sha256")
    source = _read_source_primitive(source_path)
    if expected is not None and source["source_sha256"] != expected:
        raise MeshPrecisionCutterError(
            "source GLB digest does not match expected_source_sha256",
            {"expected": expected, "observed": source["source_sha256"]},
        )
    frame = _recognize_oriented_box(source)
    cut_axis, direction_sign, alignment = _match_frame_axis(
        tuple(specification["axis_vector"]), frame
    )
    order = _canonical_axis_order(cut_axis)
    root = {
        "source_sha256": source["source_sha256"],
        "source_bytes": source["source_bytes"],
        "material_mode": source["material_mode"],
        "material": source["material"],
        "source_topology": source["topology"],
        "frame": frame,
    }
    root["root_sha256"] = _digest(root)
    return {
        "root": root,
        "frame": frame,
        "order": order,
        "cut_axis": cut_axis,
        "direction_sign": direction_sign,
        "alignment": alignment,
        "resolved_holes": [],
        "steps": [],
        "parent_lineage_sha256": None,
    }


def _load_parent_lineage(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    if not lineage_path.is_file() or lineage_path.is_symlink():
        raise MeshPrecisionCutterError("lineage_path must be an existing ordinary JSON receipt")
    lineage = _read_json_object(lineage_path)
    if lineage.get("schema") != HOLE_LINEAGE_SCHEMA:
        raise MeshPrecisionCutterError("unsupported v0.5 hole lineage receipt schema")
    observed_lineage_digest = _lineage_digest(lineage)
    if lineage.get("lineage_sha256") != observed_lineage_digest:
        raise MeshPrecisionCutterError("hole lineage self-digest does not match its contents")
    expected = _normalize_digest(expected_lineage_sha256, "expected_lineage_sha256")
    if expected is not None and expected != observed_lineage_digest:
        raise MeshPrecisionCutterError(
            "hole lineage digest does not match expected_lineage_sha256",
            {"expected": expected, "observed": observed_lineage_digest},
        )
    required = {"root", "axis", "holes", "steps", "output"}
    if not required <= set(lineage):
        raise MeshPrecisionCutterError("hole lineage receipt is missing required state")
    root, axis = lineage["root"], lineage["axis"]
    holes, steps, output = lineage["holes"], lineage["steps"], lineage["output"]
    if (
        not isinstance(root, dict)
        or not isinstance(axis, dict)
        or not isinstance(holes, list)
        or not isinstance(steps, list)
        or not isinstance(output, dict)
        or len(holes) != len(steps)
        or not holes
    ):
        raise MeshPrecisionCutterError("hole lineage state has invalid structural types")
    claimed_root_sha = root.get("root_sha256")
    if claimed_root_sha != _digest(
        {key: value for key, value in root.items() if key != "root_sha256"}
    ):
        raise MeshPrecisionCutterError("hole lineage root digest is invalid")
    parent_state = claimed_root_sha
    for index, (hole, step) in enumerate(zip(holes, steps), start=1):
        if not isinstance(hole, dict) or not isinstance(step, dict):
            raise MeshPrecisionCutterError("hole lineage entries must be objects")
        claimed_hole_sha = hole.get("resolved_hole_sha256")
        if claimed_hole_sha != _digest(
            {key: value for key, value in hole.items() if key != "resolved_hole_sha256"}
        ):
            raise MeshPrecisionCutterError(
                f"hole lineage digest is invalid at step {index}"
            )
        state = {
            "step": index,
            "hole_id": hole.get("id"),
            "hole_sha256": claimed_hole_sha,
            "parent_state_sha256": parent_state,
        }
        expected_state = _digest(state)
        if (
            step.get("step") != index
            or step.get("hole_id") != hole.get("id")
            or step.get("hole_sha256") != claimed_hole_sha
            or step.get("parent_state_sha256") != parent_state
            or step.get("state_sha256") != expected_state
        ):
            raise MeshPrecisionCutterError(
                f"hole lineage step hash chain is invalid at step {index}"
            )
        parent_state = expected_state
    if lineage.get("cumulative_recipe_sha256") != _digest(holes):
        raise MeshPrecisionCutterError("hole lineage cumulative recipe digest is invalid")
    if len(holes) >= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError("hole lineage already reached the v0.5 limit")

    raw = source_path.read_bytes()
    current_sha = hashlib.sha256(raw).hexdigest()
    if current_sha != output.get("sha256"):
        raise MeshPrecisionCutterError(
            "resume source GLB does not match the hole lineage final output digest",
            {"expected": output.get("sha256"), "observed": current_sha},
        )
    current_source = _read_source_primitive(source_path)
    if current_source["source_sha256"] != current_sha:
        raise MeshPrecisionCutterError("resume source digest changed during inspection")
    if current_source["material"] != root.get("material"):
        raise MeshPrecisionCutterError("resume source material no longer matches lineage root material")
    frame = root.get("frame")
    if not isinstance(frame, dict):
        raise MeshPrecisionCutterError("hole lineage root frame is invalid")
    frame_body = {key: value for key, value in frame.items() if key != "frame_sha256"}
    if frame.get("frame_sha256") != _digest(frame_body):
        raise MeshPrecisionCutterError("hole lineage root frame digest is invalid")
    order_raw = axis.get("canonical_order")
    cut_axis = axis.get("frame_axis_index")
    if (
        not isinstance(order_raw, list)
        or sorted(order_raw) != [0, 1, 2]
        or any(type(value) is not int for value in order_raw)
        or type(cut_axis) is not int
        or not 0 <= cut_axis <= 2
    ):
        raise MeshPrecisionCutterError("hole lineage axis state is invalid")
    order = tuple(order_raw)
    new_axis, direction_sign, alignment = _match_frame_axis(
        tuple(specification["axis_vector"]), frame
    )
    if new_axis != cut_axis:
        raise MeshPrecisionCutterError(
            "v0.5 resume holes must remain on the lineage fabrication axis",
            {"lineage_axis": cut_axis, "requested_axis": new_axis},
        )
    prior_name = output.get("name")
    if not isinstance(prior_name, str) or not prior_name:
        raise MeshPrecisionCutterError("hole lineage output name is invalid")
    prior_compiled = _compile_state(
        name=prior_name,
        frame=frame,
        order=order,
        material=root["material"],
        holes=holes,
    )
    if prior_compiled["glb_sha256"] != current_sha:
        raise MeshPrecisionCutterError(
            "resume hole lineage does not deterministically rebuild the supplied prior GLB",
            {"recompiled": prior_compiled["glb_sha256"], "observed": current_sha},
        )
    if output.get("specification_sha256") != prior_compiled["specification_sha256"]:
        raise MeshPrecisionCutterError(
            "hole lineage output specification digest does not match deterministic rebuild"
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
        "parent_lineage_sha256": observed_lineage_digest,
    }


def _resolve_new_holes(
    specification: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {hole["id"] for hole in existing}
    resolved: list[dict[str, Any]] = []
    for hole in specification["holes"]:
        if hole["id"] in existing_ids or any(row["id"] == hole["id"] for row in resolved):
            raise MeshPrecisionCutterError(
                f"hole id already exists in lineage: {hole['id']}"
            )
        resolved.append(_resolve_hole(hole, frame=frame, order=order))
    cumulative = existing + resolved
    if len(cumulative) > MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cumulative hole chain exceeds {MAX_CHAIN_CUTS} holes"
        )
    _validate_holes(cumulative, frame)
    _choose_partition_axis(cumulative, frame)
    return resolved


def _steps_for_append(
    *,
    root_sha256: str,
    previous_steps: list[dict[str, Any]],
    new_holes: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    steps = [dict(value) for value in previous_steps]
    parent_state = steps[-1]["state_sha256"] if steps else root_sha256
    for hole in new_holes:
        state = {
            "step": len(steps) + 1,
            "hole_id": hole["id"],
            "hole_sha256": hole["resolved_hole_sha256"],
            "parent_state_sha256": parent_state,
        }
        state["state_sha256"] = _digest(state)
        parent_state = state["state_sha256"]
        steps.append(state)
    return steps


def _build_lineage(
    *,
    specification: dict[str, Any],
    base: dict[str, Any],
    cumulative_holes: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    lineage = {
        "schema": HOLE_LINEAGE_SCHEMA,
        "root": base["root"],
        "axis": {
            "frame_axis_index": base["cut_axis"],
            "canonical_order": list(base["order"]),
            "axis_alignment": base["alignment"],
            "axis_vector_last_request": list(specification["axis_vector"]),
        },
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "holes": cumulative_holes,
        "steps": steps,
        "cumulative_recipe_sha256": _digest(cumulative_holes),
        "output": {
            "name": specification["name"],
            "sha256": compiled["glb_sha256"],
            "specification_sha256": compiled["specification_sha256"],
            "partition_axis": compiled["partition_axis"],
            "geometry": compiled["geometry"],
            "topology": compiled["topology"],
            "metrics": compiled["metrics"],
        },
        "truth_boundary": {
            "previous_output_recompiled_before_resume": base["parent_lineage_sha256"] is not None,
            "hash_linked_append_only_steps": True,
            "inner_hole_boundaries_stable_when_new_holes_are_appended": True,
            "rotated_translated_source_supported": True,
            "multi_hole_projection_separable_slab_compilation": True,
            "notch_and_hole_mixing": "NOT_SUPPORTED",
            "cross_axis_chain": "NOT_SUPPORTED",
            "general_polygon_with_holes_triangulation": "NOT_YET_SUPPORTED",
            "full_arbitrary_mesh_csg": False,
            "cryptographic_authorship_signature": "NOT_PROVIDED",
            "self_intersection": "NOT_PROVEN",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }
    lineage["lineage_sha256"] = _lineage_digest(lineage)
    return lineage


def build_hole_fabrication_chain(
    source_path: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    spec = prepare_hole_chain(specification)
    if lineage_path is None:
        base = _root_from_source(source_path, spec, expected_source_sha256)
    else:
        if expected_source_sha256 is not None:
            expected = _normalize_digest(expected_source_sha256, "expected_source_sha256")
            observed = hashlib.sha256(source_path.read_bytes()).hexdigest()
            if expected != observed:
                raise MeshPrecisionCutterError(
                    "resume source GLB digest does not match expected_source_sha256",
                    {"expected": expected, "observed": observed},
                )
        base = _load_parent_lineage(
            source_path,
            Path(lineage_path).resolve(),
            spec,
            expected_lineage_sha256,
        )
    resolved_new = _resolve_new_holes(
        spec,
        frame=base["frame"],
        order=base["order"],
        existing=base["resolved_holes"],
    )
    cumulative = base["resolved_holes"] + resolved_new
    steps = _steps_for_append(
        root_sha256=base["root"]["root_sha256"],
        previous_steps=base["steps"],
        new_holes=resolved_new,
    )
    compiled = _compile_state(
        name=spec["name"],
        frame=base["frame"],
        order=base["order"],
        material=base["root"]["material"],
        holes=cumulative,
    )
    lineage = _build_lineage(
        specification=spec,
        base=base,
        cumulative_holes=cumulative,
        steps=steps,
        compiled=compiled,
    )
    return {
        "schema": HOLE_CHAIN_SCHEMA,
        "specification": spec,
        "request_sha256": _digest(
            {
                "schema": HOLE_CHAIN_SCHEMA,
                "parent_lineage_sha256": base["parent_lineage_sha256"],
                "root_sha256": base["root"]["root_sha256"],
                "new_holes": resolved_new,
            }
        ),
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "resolved_new_holes": resolved_new,
        "cumulative_hole_count": len(cumulative),
        "surface_specification": compiled["surface_specification"],
        "predicted_glb_sha256": compiled["glb_sha256"],
        "output_topology": compiled["topology"],
        "partition_axis": compiled["partition_axis"],
        "geometry": compiled["geometry"],
        "metrics": compiled["metrics"],
        "lineage": lineage,
        "truth_boundary": lineage["truth_boundary"],
    }


def publish_hole_fabrication_chain(
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
        raise MeshPrecisionCutterError(
            "hole fabrication chain requires distinct source_path and output path"
        )
    parent_lineage = Path(lineage_path).resolve() if lineage_path is not None else None
    receipt = (
        Path(receipt_path).resolve()
        if receipt_path is not None
        else target.with_suffix(target.suffix + ".hole-fabrication.json")
    )
    if receipt in {source_path, target}:
        raise MeshPrecisionCutterError(
            "hole fabrication receipt must be distinct from source and output paths"
        )
    if parent_lineage is not None and receipt == parent_lineage:
        raise MeshPrecisionCutterError(
            "resume must publish a new hole lineage receipt instead of overwriting its parent"
        )
    if receipt.exists() and not replace:
        raise MeshPrecisionCutterError(
            "hole fabrication receipt already exists; set replace=true to replace it"
        )
    built = build_hole_fabrication_chain(
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
        publication = publish_glb(
            target, built["surface_specification"], replace=replace
        )
        if publication["sha256"] != built["predicted_glb_sha256"]:
            raise MeshPrecisionCutterError(
                "published GLB digest differs from the deterministically precompiled hole-chain output"
            )
        receipt_bytes = _publish_receipt(
            receipt, built["lineage"], replace=replace
        )
    except (Procedural3DError, MeshPrecisionCutterError) as exc:
        _restore_bytes(target, previous_target)
        _restore_bytes(receipt, previous_receipt)
        if isinstance(exc, MeshPrecisionCutterError):
            raise
        raise MeshPrecisionCutterError(
            str(exc), getattr(exc, "details", {})
        ) from exc
    source_after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_unchanged = source_before == source_after
    return {
        "truth_status": (
            "VALIDATED_HASH_LINKED_MULTI_HOLE_FABRICATION_CHAIN"
            if source_unchanged
            else "HOLD_SOURCE_CHANGED_DURING_HOLE_CHAIN_PUBLICATION"
        ),
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "receipt_path": str(receipt),
        "receipt_bytes": receipt_bytes,
        "lineage_sha256": built["lineage"]["lineage_sha256"],
        "parent_lineage_sha256": built["parent_lineage_sha256"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "resolved_new_holes": built["resolved_new_holes"],
        "cumulative_hole_count": built["cumulative_hole_count"],
        "partition_axis": built["partition_axis"],
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

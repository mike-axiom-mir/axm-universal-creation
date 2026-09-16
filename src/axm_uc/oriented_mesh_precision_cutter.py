from __future__ import annotations

import hashlib
import itertools
import math
from pathlib import Path
from typing import Any

from .mesh_precision_cutter import (
    EPSILON,
    SOURCE_TOLERANCE,
    MeshPrecisionCutterError,
    _normalize_expected_digest,
    _notched_profile,
    _read_source_primitive,
    _signed_volume,
)
from .mesh_topology import MeshTopologyError, _weld_vertices, inspect_mesh_topology
from .precision_cutter import (
    MAX_HOLE_SEGMENTS,
    _canonical,
    _extrude_profile,
    _number,
    _round_hole_geometry,
    _surface_specification,
)
from .procedural_3d import Procedural3DError, publish_glb

ORIENTED_MESH_CUTTER_SCHEMA = "axm.mesh-precision-cutter/v0.3"
FRAME_DOT_TOLERANCE = 1e-6


def oriented_mesh_cutter_summary() -> dict[str, Any]:
    return {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "truth_status": "LIVE_BOUNDED_ORIENTED_EXISTING_MESH_SUBTRACTION",
        "operations": ["round-through-hole", "box-notch"],
        "source_scope": "one rigid static closed rectangular-prism GLB primitive in arbitrary rigid world orientation",
        "axis_contract": "explicit world-space axis_vector aligned with one proven source-frame axis",
        "full_arbitrary_mesh_csg": False,
        "arbitrary_angle_cut_axis": False,
        "multi_component_cutting": False,
    }


def _vec3(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise MeshPrecisionCutterError(f"{label} must contain exactly three numbers")
    return tuple(
        _number(item, f"{label}[{index}]", -100000.0, 100000.0)
        for index, item in enumerate(value)
    )


def _dot(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return sum(a[index] * b[index] for index in range(3))


def _sub(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[index] - b[index] for index in range(3))


def _add(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(a[index] + b[index] for index in range(3))


def _scale(vector: tuple[float, float, float], amount: float) -> tuple[float, float, float]:
    return tuple(value * amount for value in vector)


def _length(vector: tuple[float, float, float]) -> float:
    return math.sqrt(_dot(vector, vector))


def _cross(a: tuple[float, float, float], b: tuple[float, float, float]) -> tuple[float, float, float]:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _unit(vector: tuple[float, float, float], label: str) -> tuple[float, float, float]:
    length = _length(vector)
    if not math.isfinite(length) or length <= EPSILON:
        raise MeshPrecisionCutterError(f"{label} must have non-zero finite length")
    return tuple(value / length for value in vector)


def _point_distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return _length(_sub(a, b))


def _canonical_direction(vector: tuple[float, float, float]) -> tuple[float, float, float]:
    direction = _unit(vector, "source frame edge")
    dominant = max(range(3), key=lambda index: (abs(direction[index]), -index))
    if direction[dominant] < 0:
        direction = tuple(-value for value in direction)
    return direction


def _generated_corner_set(
    origin: tuple[float, float, float],
    edges: tuple[tuple[float, float, float], ...],
) -> list[tuple[float, float, float]]:
    result: list[tuple[float, float, float]] = []
    for bits in itertools.product((0, 1), repeat=3):
        point = origin
        for bit, edge in zip(bits, edges):
            if bit:
                point = _add(point, edge)
        result.append(point)
    return result


def _same_point_sets(
    generated: list[tuple[float, float, float]],
    observed: tuple[tuple[float, float, float], ...],
    tolerance: float,
) -> bool:
    unmatched = list(observed)
    for point in generated:
        candidates = [
            (_point_distance(point, candidate), index)
            for index, candidate in enumerate(unmatched)
            if _point_distance(point, candidate) <= tolerance
        ]
        if not candidates:
            return False
        _distance, selected = min(candidates)
        unmatched.pop(selected)
    return not unmatched


def _recognize_oriented_box(source: dict[str, Any]) -> dict[str, Any]:
    positions = tuple(tuple(map(float, point)) for point in source["positions"])
    welded, _mapping = _weld_vertices(positions, SOURCE_TOLERANCE)
    if len(welded) != 8:
        raise MeshPrecisionCutterError(
            "v0.3 source recognition requires exactly eight seam-welded rectangular-prism corners",
            {"welded_vertex_count": len(welded)},
        )
    diagonal = max(
        _point_distance(first, second)
        for first, second in itertools.combinations(welded, 2)
    )
    tolerance = max(SOURCE_TOLERANCE, diagonal * 1e-7)
    origin = min(welded)
    deltas = tuple(
        _sub(point, origin)
        for point in welded
        if _point_distance(point, origin) > tolerance
    )
    candidate_frames: list[tuple[tuple[float, float, float], ...]] = []
    for edges in itertools.combinations(deltas, 3):
        lengths = [_length(edge) for edge in edges]
        if min(lengths) <= tolerance:
            continue
        if any(
            abs(_dot(edges[first], edges[second]))
            > tolerance * max(1.0, lengths[first] * lengths[second])
            for first in range(3)
            for second in range(first + 1, 3)
        ):
            continue
        if not _same_point_sets(
            _generated_corner_set(origin, edges), welded, tolerance * 4.0
        ):
            continue
        axes = [_canonical_direction(edge) for edge in edges]
        axes.sort(
            key=lambda direction: (
                -abs(direction[0]),
                -abs(direction[1]),
                -abs(direction[2]),
                round(direction[0], 12),
                round(direction[1], 12),
                round(direction[2], 12),
            )
        )
        if _dot(_cross(axes[0], axes[1]), axes[2]) < 0:
            axes[2] = tuple(-value for value in axes[2])
        candidate_frames.append(tuple(axes))
    if not candidate_frames:
        raise MeshPrecisionCutterError(
            "source is not a proven rectangular prism in an orthogonal world frame"
        )
    axes = min(
        candidate_frames,
        key=lambda frame: tuple(round(value, 12) for axis in frame for value in axis),
    )
    if any(
        abs(_dot(axes[first], axes[second])) > FRAME_DOT_TOLERANCE
        for first in range(3)
        for second in range(first + 1, 3)
    ):
        raise MeshPrecisionCutterError("recognized source frame is not orthogonal")
    determinant = _dot(_cross(axes[0], axes[1]), axes[2])
    if determinant < 1.0 - 1e-6:
        raise MeshPrecisionCutterError(
            "recognized source frame is not a right-handed orthonormal basis"
        )

    center = tuple(
        sum(point[index] for point in welded) / 8.0 for index in range(3)
    )
    local_corners = [
        tuple(_dot(_sub(point, center), axis) for axis in axes)
        for point in welded
    ]
    half_extents = [
        max(abs(point[axis]) for point in local_corners) for axis in range(3)
    ]
    if any(value <= tolerance for value in half_extents):
        raise MeshPrecisionCutterError("recognized source frame contains a collapsed extent")
    corner_signs: set[tuple[int, int, int]] = set()
    for local in local_corners:
        signs: list[int] = []
        for axis, value in enumerate(local):
            if abs(abs(value) - half_extents[axis]) > tolerance * 4.0:
                raise MeshPrecisionCutterError(
                    "source corner does not lie on the recognized oriented-box boundary"
                )
            signs.append(1 if value > 0 else -1)
        corner_signs.add(tuple(signs))
    if len(corner_signs) != 8:
        raise MeshPrecisionCutterError(
            "recognized source frame does not expose all eight box corners"
        )

    faces: set[tuple[int, int]] = set()
    for offset in range(0, len(source["indices"]), 3):
        triangle = [
            source["positions"][source["indices"][offset + index]]
            for index in range(3)
        ]
        matches: list[tuple[int, int]] = []
        for axis in range(3):
            values = [
                _dot(_sub(tuple(point), center), axes[axis]) for point in triangle
            ]
            if all(
                abs(value + half_extents[axis]) <= tolerance * 4.0
                for value in values
            ):
                matches.append((axis, -1))
            if all(
                abs(value - half_extents[axis]) <= tolerance * 4.0
                for value in values
            ):
                matches.append((axis, 1))
        if len(matches) != 1:
            raise MeshPrecisionCutterError(
                "source triangles must lie on exactly one recognized oriented-box face"
            )
        faces.add(matches[0])
    if faces != {(axis, sign) for axis in range(3) for sign in (-1, 1)}:
        raise MeshPrecisionCutterError(
            "source does not contain all six recognized oriented-box faces"
        )

    extents = [2.0 * value for value in half_extents]
    expected_volume = extents[0] * extents[1] * extents[2]
    signed_volume = _signed_volume(source["positions"], source["indices"])
    volume_tolerance = max(expected_volume * 1e-5, tolerance**3 * 100.0)
    if signed_volume <= 0 or abs(signed_volume - expected_volume) > volume_tolerance:
        raise MeshPrecisionCutterError(
            "source orientation or enclosed volume does not match the recognized oriented box",
            {
                "signed_volume": signed_volume,
                "expected_volume": expected_volume,
                "tolerance": volume_tolerance,
            },
        )
    frame = {
        "center": [float(value) for value in center],
        "axes": [[float(value) for value in axis] for axis in axes],
        "extents": extents,
        "half_extents": half_extents,
        "determinant": determinant,
        "signed_volume": signed_volume,
        "box_volume": expected_volume,
        "tolerance": tolerance,
        "all_six_faces_observed": True,
        "all_eight_corners_observed": True,
    }
    frame["frame_sha256"] = hashlib.sha256(_canonical(frame)).hexdigest()
    return frame


def _axis_vector(value: Any) -> tuple[float, float, float]:
    return _unit(_vec3(value, "axis_vector"), "axis_vector")


def _match_frame_axis(
    direction: tuple[float, float, float], frame: dict[str, Any]
) -> tuple[int, int, float]:
    axes = [tuple(row) for row in frame["axes"]]
    dots = [_dot(direction, axis) for axis in axes]
    index = max(range(3), key=lambda item: abs(dots[item]))
    alignment = abs(dots[index])
    if alignment < 1.0 - 1e-6:
        raise MeshPrecisionCutterError(
            "axis_vector must align with one proven source-frame axis in v0.3",
            {"alignment": alignment, "source_axes": frame["axes"]},
        )
    if max(abs(value) for position, value in enumerate(dots) if position != index) > 1e-5:
        raise MeshPrecisionCutterError(
            "axis_vector is ambiguous across the recognized source frame"
        )
    return index, 1 if dots[index] >= 0 else -1, alignment


def _canonical_axis_order(cut_axis: int) -> tuple[int, int, int]:
    if cut_axis == 0:
        return (2, 0, 1)
    if cut_axis == 1:
        return (0, 1, 2)
    return (1, 2, 0)


def _world_to_frame(
    point: tuple[float, float, float], frame: dict[str, Any]
) -> tuple[float, float, float]:
    center = tuple(frame["center"])
    delta = _sub(point, center)
    return tuple(_dot(delta, tuple(axis)) for axis in frame["axes"])


def _canonical_point_from_world(
    point: tuple[float, float, float],
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> tuple[float, float, float]:
    local = _world_to_frame(point, frame)
    return tuple(local[index] for index in order)


def _canonical_to_world(
    point: tuple[float, float, float],
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> tuple[float, float, float]:
    world = tuple(frame["center"])
    for canonical_axis, frame_axis in enumerate(order):
        world = _add(
            world,
            _scale(tuple(frame["axes"][frame_axis]), point[canonical_axis]),
        )
    return world


def _canonical_normal_to_world(
    normal: tuple[float, float, float],
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> tuple[float, float, float]:
    world = (0.0, 0.0, 0.0)
    for canonical_axis, frame_axis in enumerate(order):
        world = _add(
            world,
            _scale(tuple(frame["axes"][frame_axis]), normal[canonical_axis]),
        )
    return _unit(world, "calculated output normal")


def prepare_oriented_mesh_cut(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("v0.3 mesh cutter specification must be an object")
    required = {"schema", "name", "operation", "axis_vector", "center"}
    optional = {"radius", "segments", "kerf", "side", "span", "depth"}
    missing = required - set(raw)
    extra = set(raw) - required - optional
    if missing or extra:
        raise MeshPrecisionCutterError(
            "v0.3 mesh cutter fields do not match the bounded grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    if raw["schema"] != ORIENTED_MESH_CUTTER_SCHEMA:
        raise MeshPrecisionCutterError("unsupported oriented mesh cutter schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise MeshPrecisionCutterError("name must contain 1..120 characters")
    operation = str(raw["operation"]).strip().casefold()
    if operation not in {"round-through-hole", "box-notch"}:
        raise MeshPrecisionCutterError(
            "unsupported v0.3 oriented cutter operation",
            {"supported": ["box-notch", "round-through-hole"]},
        )
    result: dict[str, Any] = {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "name": name.strip(),
        "operation": operation,
        "axis_vector": list(_axis_vector(raw["axis_vector"])),
        "center": list(_vec3(raw["center"], "center")),
        "kerf": _number(raw.get("kerf", 0.0), "kerf", 0.0, 1000.0),
    }
    if operation == "round-through-hole":
        if not {"radius", "segments"} <= set(raw) or any(
            key in raw for key in ("side", "span", "depth")
        ):
            raise MeshPrecisionCutterError(
                "v0.3 round-through-hole requires radius and segments only"
            )
        segments = raw["segments"]
        if type(segments) is not int or not 8 <= segments <= MAX_HOLE_SEGMENTS:
            raise MeshPrecisionCutterError(
                f"segments must be an integer from 8 through {MAX_HOLE_SEGMENTS}"
            )
        result.update(
            {
                "radius": _number(raw["radius"], "radius", 0.0001, 100000.0),
                "segments": segments,
            }
        )
        return result
    if not {"side", "span", "depth"} <= set(raw) or any(
        key in raw for key in ("radius", "segments")
    ):
        raise MeshPrecisionCutterError(
            "v0.3 box-notch requires side, span, and depth only"
        )
    side = str(raw["side"]).strip().casefold()
    if side not in {"u-min", "u-max", "v-min", "v-max"}:
        raise MeshPrecisionCutterError(
            "side must be one of u-min, u-max, v-min, v-max"
        )
    result.update(
        {
            "side": side,
            "span": _number(raw["span"], "span", 0.0001, 100000.0),
            "depth": _number(raw["depth"], "depth", 0.0001, 100000.0),
        }
    )
    return result


def build_oriented_source_mesh_cut(
    source_path: Path,
    specification: Any,
    *,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    spec = prepare_oriented_mesh_cut(specification)
    expected_digest = _normalize_expected_digest(expected_source_sha256)
    source = _read_source_primitive(source_path)
    if expected_digest is not None and source["source_sha256"] != expected_digest:
        raise MeshPrecisionCutterError(
            "source GLB digest does not match expected_source_sha256",
            {"expected": expected_digest, "observed": source["source_sha256"]},
        )
    frame = _recognize_oriented_box(source)
    cut_axis, direction_sign, alignment = _match_frame_axis(
        tuple(spec["axis_vector"]), frame
    )
    order = _canonical_axis_order(cut_axis)
    width, thickness, depth = (
        frame["extents"][order[0]],
        frame["extents"][order[1]],
        frame["extents"][order[2]],
    )
    canonical_center = _canonical_point_from_world(
        tuple(spec["center"]), frame, order
    )
    if abs(canonical_center[1]) > thickness / 2.0 + frame["tolerance"]:
        raise MeshPrecisionCutterError(
            "cut center lies outside the source extent along axis_vector"
        )

    if spec["operation"] == "round-through-hole":
        effective_radius = spec["radius"] + spec["kerf"] / 2.0
        canonical_positions, canonical_normals, indices, inner, _outer = _round_hole_geometry(
            (width, depth),
            (canonical_center[0], canonical_center[2]),
            effective_radius,
            spec["segments"],
            thickness,
        )
        polygon_removed_area = abs(
            0.5
            * sum(
                inner[index][0] * inner[(index + 1) % len(inner)][1]
                - inner[(index + 1) % len(inner)][0] * inner[index][1]
                for index in range(len(inner))
            )
        )
        operation_metrics: dict[str, Any] = {
            "requested_radius": spec["radius"],
            "effective_radius": effective_radius,
            "kerf": spec["kerf"],
            "segments": spec["segments"],
            "polygonized_removed_area": polygon_removed_area,
            "analytic_requested_removed_area": math.pi * spec["radius"] ** 2,
            "analytic_effective_removed_area": math.pi * effective_radius**2,
            "removed_volume": polygon_removed_area * thickness,
        }
    else:
        span_center = (
            canonical_center[2]
            if spec["side"].startswith("u-")
            else canonical_center[0]
        )
        profile, operation_metrics = _notched_profile(
            width,
            depth,
            side=spec["side"],
            span_center=span_center,
            requested_span=spec["span"],
            requested_depth=spec["depth"],
            kerf=spec["kerf"],
        )
        canonical_positions, canonical_normals, indices, top_triangles = _extrude_profile(
            profile, thickness
        )
        operation_metrics["top_surface_triangles"] = top_triangles
        operation_metrics["removed_volume"] = (
            operation_metrics["removed_area"] * thickness
        )

    positions = [
        _canonical_to_world(point, frame, order) for point in canonical_positions
    ]
    normals = [
        _canonical_normal_to_world(normal, frame, order)
        for normal in canonical_normals
    ]
    try:
        output_topology = inspect_mesh_topology(
            positions, indices, weld_tolerance=SOURCE_TOLERANCE
        )
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if (
        output_topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        or output_topology["triangle_component_count"] != 1
    ):
        raise MeshPrecisionCutterError(
            "v0.3 calculated cut output did not remain one closed oriented component",
            {"topology": output_topology},
        )
    output_volume = _signed_volume(positions, indices)
    if output_volume <= 0 or output_volume >= frame["box_volume"] - EPSILON:
        raise MeshPrecisionCutterError(
            "v0.3 subtractive output volume is not strictly smaller than the measured source volume",
            {"source_volume": frame["box_volume"], "output_volume": output_volume},
        )
    surface = _surface_specification(
        spec["name"], positions, normals, indices, source["material"]
    )
    request_identity = {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "source_sha256": source["source_sha256"],
        "source_frame_sha256": frame["frame_sha256"],
        "specification": spec,
    }
    return {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "operation": spec["operation"],
        "specification": spec,
        "request_sha256": hashlib.sha256(_canonical(request_identity)).hexdigest(),
        "source": {
            "sha256": source["source_sha256"],
            "bytes": source["source_bytes"],
            "node_name": source["node_name"],
            "mesh_name": source["mesh_name"],
            "material_mode": source["material_mode"],
            "material": source["material"],
            "topology": source["topology"],
            "recognition": frame,
        },
        "surface_specification": surface,
        "metrics": {
            "source_volume": frame["box_volume"],
            "output_volume": output_volume,
            "removed_volume_by_closed_mesh": frame["box_volume"] - output_volume,
            "matched_source_axis_index": cut_axis,
            "axis_vector_sign": direction_sign,
            "axis_alignment": alignment,
            "canonical_frame_order": list(order),
            **operation_metrics,
        },
        "output_topology": output_topology,
        "geometry": {"vertices": len(positions), "triangles": len(indices) // 3},
        "truth_boundary": {
            "source_bytes_observed": True,
            "source_topology_checked": True,
            "source_oriented_rectangular_prism_proven_within_v0_3_contract": True,
            "rotated_translated_source_supported": True,
            "axis_vector_bound_to_proven_source_frame": True,
            "source_file_mutated": False,
            "output_closed_edge_manifold_candidate_checked": True,
            "full_arbitrary_mesh_csg": False,
            "arbitrary_angle_relative_to_source_frame": "NOT_SUPPORTED",
            "multi_component_source": "NOT_SUPPORTED",
            "output_to_next_arbitrary_cut_chaining": "NOT_YET_SUPPORTED",
            "uv_texture_tangent_or_vertex_color_preservation": "NOT_SUPPORTED_AND_REJECTED",
            "self_intersection": "NOT_PROVEN",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }


def publish_oriented_source_mesh_cut(
    source_path: Path,
    target: Path,
    specification: Any,
    *,
    expected_source_sha256: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    target = Path(target).resolve()
    if source_path == target:
        raise MeshPrecisionCutterError(
            "v0.3 existing-mesh cutter requires distinct source_path and output path"
        )
    built = build_oriented_source_mesh_cut(
        source_path,
        specification,
        expected_source_sha256=expected_source_sha256,
    )
    try:
        publication = publish_glb(
            target,
            built["surface_specification"],
            replace=replace,
        )
    except Procedural3DError as exc:
        raise MeshPrecisionCutterError(
            str(exc), getattr(exc, "details", {})
        ) from exc
    observed_source_after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_unchanged = observed_source_after == built["source"]["sha256"]
    return {
        "operation": built["operation"],
        "truth_status": (
            "VALIDATED_ORIENTED_EXISTING_MESH_PRECISION_CUT"
            if source_unchanged
            else "HOLD_SOURCE_CHANGED_DURING_PUBLICATION"
        ),
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "source": {
            **built["source"],
            "unchanged_after_publication": source_unchanged,
            "observed_sha256_after_publication": observed_source_after,
        },
        "metrics": built["metrics"],
        "geometry": built["geometry"],
        "source_topology": built["source"]["topology"],
        "output_topology": built["output_topology"],
        "glb_validation": publication["post_publish_validation"],
        "truth_boundary": built["truth_boundary"],
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

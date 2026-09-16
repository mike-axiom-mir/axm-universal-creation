from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .procedural_3d import Procedural3DError, publish_glb

CUTTER_SCHEMA = "axm.precision-cutter/v0.1"
SURFACE_SCHEMA = "axm.surface-3d/v0.1"
MAX_PROFILE_POINTS = 256
MAX_HOLE_SEGMENTS = 128
EPSILON = 1e-9
ANGLE_EPSILON = 1e-10


class PrecisionCutterError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def precision_cutter_summary() -> dict[str, Any]:
    return {
        "schema": CUTTER_SCHEMA,
        "truth_status": "LIVE_BOUNDED_DETERMINISTIC_SUBTRACTIVE_GEOMETRY",
        "operations": ["profile-cut", "round-through-hole", "round-socket"],
        "coordinate_system": "X-Z cut plane with Y thickness",
        "maximum_profile_points": MAX_PROFILE_POINTS,
        "maximum_hole_segments": MAX_HOLE_SEGMENTS,
        "full_arbitrary_mesh_csg": False,
        "visual_quality_observed": False,
    }


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise PrecisionCutterError("precision cutter state must be finite JSON") from exc


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise PrecisionCutterError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise PrecisionCutterError(f"{label} must be from {minimum} through {maximum}")
    return result


def _vec2(
    value: Any,
    label: str,
    minimum: float = -100000.0,
    maximum: float = 100000.0,
) -> tuple[float, float]:
    if not isinstance(value, list) or len(value) != 2:
        raise PrecisionCutterError(f"{label} must contain exactly two numbers")
    return (
        _number(value[0], f"{label}[0]", minimum, maximum),
        _number(value[1], f"{label}[1]", minimum, maximum),
    )


def _material(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise PrecisionCutterError("material must be an object")
    allowed = {"color", "metallic", "roughness", "emissive", "unlit"}
    missing = {"color", "metallic", "roughness"} - set(value)
    extra = set(value) - allowed
    if missing or extra:
        raise PrecisionCutterError(
            "material fields do not match the bounded cutter grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    color = value["color"]
    if not isinstance(color, str) or len(color) not in {7, 9} or not color.startswith("#"):
        raise PrecisionCutterError("material.color must be #RRGGBB or #RRGGBBAA")
    try:
        int(color[1:], 16)
    except ValueError as exc:
        raise PrecisionCutterError("material.color must be hexadecimal") from exc
    result: dict[str, Any] = {
        "color": color.upper(),
        "metallic": _number(value["metallic"], "material.metallic", 0.0, 1.0),
        "roughness": _number(value["roughness"], "material.roughness", 0.0, 1.0),
    }
    if "emissive" in value:
        emissive = value["emissive"]
        if not isinstance(emissive, str) or len(emissive) not in {7, 9} or not emissive.startswith("#"):
            raise PrecisionCutterError("material.emissive must be #RRGGBB or #RRGGBBAA")
        try:
            int(emissive[1:], 16)
        except ValueError as exc:
            raise PrecisionCutterError("material.emissive must be hexadecimal") from exc
        result["emissive"] = emissive.upper()
    if "unlit" in value:
        if type(value["unlit"]) is not bool:
            raise PrecisionCutterError("material.unlit must be boolean")
        if value["unlit"]:
            result["unlit"] = True
    return result


def _signed_area(profile: list[tuple[float, float]]) -> float:
    return 0.5 * sum(
        profile[index][0] * profile[(index + 1) % len(profile)][1]
        - profile[(index + 1) % len(profile)][0] * profile[index][1]
        for index in range(len(profile))
    )


def _cross2(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _orientation(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> int:
    value = _cross2(a, b, c)
    return 1 if value > EPSILON else -1 if value < -EPSILON else 0


def _on_segment(
    a: tuple[float, float],
    b: tuple[float, float],
    point: tuple[float, float],
) -> bool:
    return (
        min(a[0], b[0]) - EPSILON <= point[0] <= max(a[0], b[0]) + EPSILON
        and min(a[1], b[1]) - EPSILON <= point[1] <= max(a[1], b[1]) + EPSILON
        and abs(_cross2(a, b, point)) <= EPSILON
    )


def _segments_intersect(
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
    d: tuple[float, float],
) -> bool:
    o1, o2, o3, o4 = (
        _orientation(a, b, c),
        _orientation(a, b, d),
        _orientation(c, d, a),
        _orientation(c, d, b),
    )
    if o1 != o2 and o3 != o4 and 0 not in {o1, o2, o3, o4}:
        return True
    return any(
        orientation == 0 and _on_segment(x, y, point)
        for orientation, x, y, point in (
            (o1, a, b, c),
            (o2, a, b, d),
            (o3, c, d, a),
            (o4, c, d, b),
        )
    )


def _normalize_profile(raw: Any) -> list[tuple[float, float]]:
    if not isinstance(raw, list) or not 3 <= len(raw) <= MAX_PROFILE_POINTS:
        raise PrecisionCutterError(f"profile must contain 3 through {MAX_PROFILE_POINTS} points")
    profile = [_vec2(row, f"profile[{index}]") for index, row in enumerate(raw)]
    if len(set(profile)) != len(profile):
        raise PrecisionCutterError("profile points must be unique")
    count = len(profile)
    for index in range(count):
        a, b = profile[index], profile[(index + 1) % count]
        if math.dist(a, b) <= EPSILON:
            raise PrecisionCutterError("profile edges must have non-zero length")
        for other in range(index + 1, count):
            if other in {index, (index + 1) % count} or (other + 1) % count in {index, (index + 1) % count}:
                continue
            c, d = profile[other], profile[(other + 1) % count]
            if _segments_intersect(a, b, c, d):
                raise PrecisionCutterError("profile must be a simple non-self-intersecting polygon")
    area = _signed_area(profile)
    if abs(area) <= EPSILON:
        raise PrecisionCutterError("profile area must be non-zero")
    if area < 0:
        profile.reverse()
    return profile


def _point_in_triangle(
    point: tuple[float, float],
    a: tuple[float, float],
    b: tuple[float, float],
    c: tuple[float, float],
) -> bool:
    first = _cross2(a, b, point)
    second = _cross2(b, c, point)
    third = _cross2(c, a, point)
    return first >= -EPSILON and second >= -EPSILON and third >= -EPSILON


def _triangulate(profile: list[tuple[float, float]]) -> list[tuple[int, int, int]]:
    remaining = list(range(len(profile)))
    triangles: list[tuple[int, int, int]] = []
    budget = len(profile) * len(profile) * 2
    while len(remaining) > 3 and budget > 0:
        budget -= 1
        clipped = False
        for position, current in enumerate(remaining):
            previous = remaining[position - 1]
            nxt = remaining[(position + 1) % len(remaining)]
            a, b, c = profile[previous], profile[current], profile[nxt]
            if _cross2(a, b, c) <= EPSILON:
                continue
            if any(
                _point_in_triangle(profile[index], a, b, c)
                for index in remaining
                if index not in {previous, current, nxt}
            ):
                continue
            triangles.append((previous, current, nxt))
            del remaining[position]
            clipped = True
            break
        if not clipped:
            raise PrecisionCutterError("profile triangulation could not find a valid ear")
    if len(remaining) != 3:
        raise PrecisionCutterError("profile triangulation exceeded its bounded work budget")
    triangles.append((remaining[0], remaining[1], remaining[2]))
    return triangles


def _triangle_normal(
    a: tuple[float, float, float],
    b: tuple[float, float, float],
    c: tuple[float, float, float],
) -> tuple[float, float, float]:
    u = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    v = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    )
    length = math.sqrt(sum(value * value for value in cross))
    if length <= EPSILON:
        raise PrecisionCutterError("cutter produced a degenerate face")
    return tuple(value / length for value in cross)


def _append_face(
    positions: list[tuple[float, float, float]],
    normals: list[tuple[float, float, float]],
    indices: list[int],
    points: list[tuple[float, float, float]],
    normal: tuple[float, float, float],
) -> None:
    start = len(positions)
    normalized = [tuple(map(float, point)) for point in points]
    if len(normalized) == 3:
        observed = _triangle_normal(normalized[0], normalized[1], normalized[2])
        order = [0, 1, 2]
        if sum(observed[index] * normal[index] for index in range(3)) < 0:
            order = [0, 2, 1]
        positions.extend(normalized)
        normals.extend([normal] * 3)
        indices.extend(start + index for index in order)
        return
    if len(normalized) != 4:
        raise PrecisionCutterError("internal cutter face must contain three or four points")
    observed = _triangle_normal(normalized[0], normalized[1], normalized[2])
    order = (
        [0, 1, 2, 0, 2, 3]
        if sum(observed[index] * normal[index] for index in range(3)) > 0
        else [0, 2, 1, 0, 3, 2]
    )
    positions.extend(normalized)
    normals.extend([normal] * 4)
    indices.extend(start + index for index in order)


def _extrude_profile(
    profile: list[tuple[float, float]],
    thickness: float,
) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int], int]:
    triangles = _triangulate(profile)
    top = thickness / 2.0
    bottom = -top
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    for a, b, c in triangles:
        pa, pb, pc = profile[a], profile[b], profile[c]
        _append_face(
            positions,
            normals,
            indices,
            [(pa[0], top, pa[1]), (pb[0], top, pb[1]), (pc[0], top, pc[1])],
            (0.0, 1.0, 0.0),
        )
        _append_face(
            positions,
            normals,
            indices,
            [(pa[0], bottom, pa[1]), (pb[0], bottom, pb[1]), (pc[0], bottom, pc[1])],
            (0.0, -1.0, 0.0),
        )
    for index, p0 in enumerate(profile):
        p1 = profile[(index + 1) % len(profile)]
        dx = p1[0] - p0[0]
        dz = p1[1] - p0[1]
        length = math.hypot(dx, dz)
        normal = (dz / length, 0.0, -dx / length)
        _append_face(
            positions,
            normals,
            indices,
            [
                (p0[0], bottom, p0[1]),
                (p0[0], top, p0[1]),
                (p1[0], top, p1[1]),
                (p1[0], bottom, p1[1]),
            ],
            normal,
        )
    return positions, normals, indices, len(triangles)


def _ray_to_rectangle(
    center: tuple[float, float],
    angle: float,
    half_width: float,
    half_depth: float,
) -> tuple[float, float]:
    cx, cz = center
    dx, dz = math.cos(angle), math.sin(angle)
    candidates: list[float] = []
    if abs(dx) > EPSILON:
        candidates.extend(((-half_width - cx) / dx, (half_width - cx) / dx))
    if abs(dz) > EPSILON:
        candidates.extend(((-half_depth - cz) / dz, (half_depth - cz) / dz))
    valid: list[tuple[float, float, float]] = []
    for distance in candidates:
        if distance <= EPSILON:
            continue
        x = cx + distance * dx
        z = cz + distance * dz
        if (
            -half_width - 1e-8 <= x <= half_width + 1e-8
            and -half_depth - 1e-8 <= z <= half_depth + 1e-8
        ):
            valid.append((distance, x, z))
    if not valid:
        raise PrecisionCutterError("hole ray did not intersect stock boundary")
    _distance, x, z = min(valid)
    return (x, z)


def _deduplicate_angles(values: list[float]) -> list[float]:
    """Collapse numerically equivalent radial events, including the 0/tau seam.

    Rectangle-corner angles can be mathematically identical to a requested radial
    segment while differing by a few floating-point ulps. Treating them as two
    events creates a zero-area ring face, so identity is tolerance based here.
    """

    tau = 2.0 * math.pi
    ordered = sorted(value % tau for value in values)
    unique: list[float] = []
    for value in ordered:
        if not unique or value - unique[-1] > ANGLE_EPSILON:
            unique.append(value)
    if len(unique) > 1 and unique[0] + tau - unique[-1] <= ANGLE_EPSILON:
        unique.pop()
    return unique


def _round_hole_geometry(
    stock_size: tuple[float, float],
    center: tuple[float, float],
    radius: float,
    segments: int,
    thickness: float,
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
    if radius <= 0 or radius >= available - EPSILON:
        raise PrecisionCutterError("round cutout must stay strictly inside the rectangular stock")

    angles = [2.0 * math.pi * index / segments for index in range(segments)]
    angles.extend(
        math.atan2(corner_z - cz, corner_x - cx)
        for corner_x, corner_z in (
            (-half_width, -half_depth),
            (-half_width, half_depth),
            (half_width, -half_depth),
            (half_width, half_depth),
        )
    )
    ordered = _deduplicate_angles(angles)
    if len(ordered) < segments:
        raise PrecisionCutterError("round cut radial event normalization lost required resolution")

    inner = [(cx + radius * math.cos(angle), cz + radius * math.sin(angle)) for angle in ordered]
    outer = [_ray_to_rectangle(center, angle, half_width, half_depth) for angle in ordered]
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    top = thickness / 2.0
    bottom = -top
    count = len(ordered)

    for index in range(count):
        nxt = (index + 1) % count
        _append_face(
            positions,
            normals,
            indices,
            [
                (outer[index][0], top, outer[index][1]),
                (outer[nxt][0], top, outer[nxt][1]),
                (inner[nxt][0], top, inner[nxt][1]),
                (inner[index][0], top, inner[index][1]),
            ],
            (0.0, 1.0, 0.0),
        )
        _append_face(
            positions,
            normals,
            indices,
            [
                (outer[index][0], bottom, outer[index][1]),
                (outer[nxt][0], bottom, outer[nxt][1]),
                (inner[nxt][0], bottom, inner[nxt][1]),
                (inner[index][0], bottom, inner[index][1]),
            ],
            (0.0, -1.0, 0.0),
        )

        outer_dx = outer[nxt][0] - outer[index][0]
        outer_dz = outer[nxt][1] - outer[index][1]
        outer_length = math.hypot(outer_dx, outer_dz)
        if outer_length > EPSILON:
            outer_normal = (outer_dz / outer_length, 0.0, -outer_dx / outer_length)
            _append_face(
                positions,
                normals,
                indices,
                [
                    (outer[index][0], bottom, outer[index][1]),
                    (outer[index][0], top, outer[index][1]),
                    (outer[nxt][0], top, outer[nxt][1]),
                    (outer[nxt][0], bottom, outer[nxt][1]),
                ],
                outer_normal,
            )

        middle_angle = math.atan2(
            (inner[index][1] + inner[nxt][1]) / 2.0 - cz,
            (inner[index][0] + inner[nxt][0]) / 2.0 - cx,
        )
        inner_normal = (-math.cos(middle_angle), 0.0, -math.sin(middle_angle))
        _append_face(
            positions,
            normals,
            indices,
            [
                (inner[index][0], bottom, inner[index][1]),
                (inner[nxt][0], bottom, inner[nxt][1]),
                (inner[nxt][0], top, inner[nxt][1]),
                (inner[index][0], top, inner[index][1]),
            ],
            inner_normal,
        )

    return positions, normals, indices, inner, outer


def _surface_specification(
    name: str,
    positions: list[tuple[float, float, float]],
    normals: list[tuple[float, float, float]],
    indices: list[int],
    material: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": SURFACE_SCHEMA,
        "name": name,
        "primitives": [
            {
                "id": "precision-cut-result",
                "positions": [[float(value) for value in row] for row in positions],
                "normals": [[float(value) for value in row] for row in normals],
                "indices": list(indices),
                "material": material,
            }
        ],
    }


def prepare_cut(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PrecisionCutterError("precision cutter specification must be an object")
    required = {"schema", "name", "operation", "thickness", "material"}
    optional = {"profile", "stock_size", "hole", "socket", "kerf"}
    missing = required - set(raw)
    extra = set(raw) - required - optional
    if missing or extra:
        raise PrecisionCutterError(
            "precision cutter fields do not match the bounded grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    if raw["schema"] != CUTTER_SCHEMA:
        raise PrecisionCutterError("unsupported precision cutter schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise PrecisionCutterError("name must contain 1..120 characters")
    operation = str(raw["operation"]).strip().casefold()
    supported = {"profile-cut", "round-through-hole", "round-socket"}
    if operation not in supported:
        raise PrecisionCutterError(
            "unsupported precision cutter operation",
            {"supported": sorted(supported)},
        )

    thickness = _number(raw["thickness"], "thickness", 0.0001, 10000.0)
    kerf = _number(raw.get("kerf", 0.0), "kerf", 0.0, 1000.0)
    material = _material(raw["material"])
    normalized: dict[str, Any] = {
        "schema": CUTTER_SCHEMA,
        "name": name.strip(),
        "operation": operation,
        "thickness": thickness,
        "kerf": kerf,
        "material": material,
    }

    if operation == "profile-cut":
        if "profile" not in raw or any(key in raw for key in ("stock_size", "hole", "socket")):
            raise PrecisionCutterError("profile-cut requires only profile geometry")
        normalized["profile"] = [list(point) for point in _normalize_profile(raw["profile"])]
        return normalized

    if "stock_size" not in raw:
        raise PrecisionCutterError(f"{operation} requires stock_size")
    normalized["stock_size"] = list(_vec2(raw["stock_size"], "stock_size", 0.0001, 100000.0))
    key = "hole" if operation == "round-through-hole" else "socket"
    if (
        key not in raw
        or (operation == "round-through-hole" and "socket" in raw)
        or (operation == "round-socket" and "hole" in raw)
        or "profile" in raw
    ):
        raise PrecisionCutterError(f"{operation} requires exactly one {key} definition")
    definition = raw[key]
    if not isinstance(definition, dict):
        raise PrecisionCutterError(f"{key} must be an object")
    required_fields = {"center", "segments"} | (
        {"radius"} if key == "hole" else {"source_radius", "clearance"}
    )
    if set(definition) != required_fields:
        raise PrecisionCutterError(f"{key} fields do not match the bounded grammar")
    segments = definition["segments"]
    if type(segments) is not int or not 8 <= segments <= MAX_HOLE_SEGMENTS:
        raise PrecisionCutterError(
            f"{key}.segments must be an integer from 8 through {MAX_HOLE_SEGMENTS}"
        )
    center = _vec2(definition["center"], f"{key}.center")
    if key == "hole":
        radius = _number(definition["radius"], "hole.radius", 0.0001, 100000.0)
        normalized[key] = {"center": list(center), "radius": radius, "segments": segments}
    else:
        source_radius = _number(
            definition["source_radius"],
            "socket.source_radius",
            0.0001,
            100000.0,
        )
        clearance = _number(definition["clearance"], "socket.clearance", 0.0, 1000.0)
        normalized[key] = {
            "center": list(center),
            "source_radius": source_radius,
            "clearance": clearance,
            "segments": segments,
        }
    return normalized


def build_cut(raw: Any) -> dict[str, Any]:
    specification = prepare_cut(raw)
    operation = specification["operation"]
    material = specification["material"]
    thickness = specification["thickness"]

    if operation == "profile-cut":
        profile = [tuple(row) for row in specification["profile"]]
        positions, normals, indices, top_triangles = _extrude_profile(profile, thickness)
        area = abs(_signed_area(profile))
        metrics: dict[str, Any] = {
            "profile_area": area,
            "solid_volume": area * thickness,
            "profile_points": len(profile),
            "top_surface_triangles": top_triangles,
            "kerf_applied": False,
        }
    else:
        stock = tuple(specification["stock_size"])
        definition = (
            specification["hole"]
            if operation == "round-through-hole"
            else specification["socket"]
        )
        if operation == "round-through-hole":
            requested_radius = definition["radius"]
            source_radius = None
            clearance = None
        else:
            source_radius = definition["source_radius"]
            clearance = definition["clearance"]
            requested_radius = source_radius + clearance

        effective_radius = requested_radius + specification["kerf"] / 2.0
        positions, normals, indices, inner, _outer = _round_hole_geometry(
            stock,
            tuple(definition["center"]),
            effective_radius,
            definition["segments"],
            thickness,
        )
        polygon_removed = abs(_signed_area(inner))
        stock_area = stock[0] * stock[1]
        metrics = {
            "stock_area": stock_area,
            "analytic_requested_removed_area": math.pi * requested_radius * requested_radius,
            "analytic_effective_removed_area": math.pi * effective_radius * effective_radius,
            "polygonized_removed_area": polygon_removed,
            "remaining_polygonized_area": stock_area - polygon_removed,
            "requested_radius": requested_radius,
            "effective_radius": effective_radius,
            "kerf": specification["kerf"],
            "ring_vertices": len(inner),
        }
        if source_radius is not None:
            metrics.update(
                {
                    "source_radius": source_radius,
                    "requested_radial_clearance": clearance,
                    "geometric_radial_clearance": effective_radius - source_radius,
                }
            )

    surface = _surface_specification(
        specification["name"],
        positions,
        normals,
        indices,
        material,
    )
    return {
        "schema": CUTTER_SCHEMA,
        "operation": operation,
        "specification": specification,
        "specification_sha256": hashlib.sha256(_canonical(specification)).hexdigest(),
        "surface_specification": surface,
        "metrics": metrics,
        "triangles": len(indices) // 3,
        "vertices": len(positions),
        "truth_boundary": {
            "geometry_generated": True,
            "cut_is_exact_within_declared_polygonization": True,
            "full_arbitrary_mesh_csg": False,
            "structural_strength": "NOT_TESTED",
            "visual_quality": "NOT_TESTED",
            "uv_continuity": "NOT_TESTED",
            "physical_laser_process": "NOT_SIMULATED",
        },
    }


def publish_precision_cut(
    target: Path,
    specification: Any,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    built = build_cut(specification)
    try:
        publication = publish_glb(
            target,
            built["surface_specification"],
            replace=replace,
        )
    except Procedural3DError as exc:
        raise PrecisionCutterError(str(exc), getattr(exc, "details", {})) from exc
    return {
        "operation": built["operation"],
        "truth_status": "VALIDATED_DETERMINISTIC_PRECISION_CUT",
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "specification": built["specification"],
        "specification_sha256": built["specification_sha256"],
        "metrics": built["metrics"],
        "geometry": {"vertices": built["vertices"], "triangles": built["triangles"]},
        "glb_validation": publication["post_publish_validation"],
        "truth_boundary": built["truth_boundary"],
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

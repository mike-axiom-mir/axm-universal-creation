"""Bounded read-only nonadjacent triangle self-intersection evidence.

Animal and Character independently demonstrated the need for this neutral kind
of indexed-mesh diagnostic. Their repositories are treated as requirement and
method precedent only; this UC implementation is independently written and
re-tested here.

The observer deliberately stays separate from :mod:`axm_uc.mesh_topology`.
Topology incidence and geometric pair testing have different work bounds and
truth boundaries. This module never repairs, welds, splits, prunes, adopts, or
otherwise mutates geometry.
"""
from __future__ import annotations

import math
from typing import Any, Iterable, Sequence

MAX_VERTICES = 131_072
MAX_TRIANGLES = 131_072
DEFAULT_MAX_TRIANGLE_PAIR_CHECKS = 250_000
HARD_MAX_TRIANGLE_PAIR_CHECKS = 2_000_000
MAX_EXAMPLES = 16

Point = tuple[float, float, float]
Triangle = tuple[Point, Point, Point]
Box = tuple[Point, Point]

DONOR_PROVENANCE = (
    {
        "repository": "mike-axiom-mir/axm-animal-design",
        "commit": "feb4b24cd36bcc879173138d240754f71db34834",
        "path": "src/axm_animal_design/self_intersection.py",
        "reuse": "requirement/geometric-method precedent only; source not copied",
    },
    {
        "repository": "mike-axiom-mir/axm-character-design",
        "commit": "eae6d296867ecaa40e8f5c3f1fe37d8e3019541e",
        "path": "src/axm_character_design/self_intersection.py",
        "reuse": "independent second receiving-domain evidence; result not inherited",
    },
)


class MeshSelfIntersectionError(ValueError):
    """Raised when input cannot support the observer contract."""


def _finite_number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MeshSelfIntersectionError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result):
        raise MeshSelfIntersectionError(f"{label} must be a finite number")
    return result


def _read_point(value: Sequence[float], label: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise MeshSelfIntersectionError(f"{label} must contain exactly three finite coordinates")
    return tuple(_finite_number(component, f"{label}[{axis}]") for axis, component in enumerate(value))


def _minus(left: Point, right: Point) -> Point:
    return (left[0] - right[0], left[1] - right[1], left[2] - right[2])


def _plus_scaled(origin: Point, direction: Point, scale: float) -> Point:
    return (
        origin[0] + direction[0] * scale,
        origin[1] + direction[1] * scale,
        origin[2] + direction[2] * scale,
    )


def _dot(left: Point, right: Point) -> float:
    return left[0] * right[0] + left[1] * right[1] + left[2] * right[2]


def _cross(left: Point, right: Point) -> Point:
    return (
        left[1] * right[2] - left[2] * right[1],
        left[2] * right[0] - left[0] * right[2],
        left[0] * right[1] - left[1] * right[0],
    )


def _magnitude(vector: Point) -> float:
    return math.hypot(vector[0], vector[1], vector[2])


def _triangle_normal(triangle: Triangle) -> Point:
    return _cross(_minus(triangle[1], triangle[0]), _minus(triangle[2], triangle[0]))


def _box_for(triangle: Triangle) -> Box:
    return (
        tuple(min(vertex[axis] for vertex in triangle) for axis in range(3)),
        tuple(max(vertex[axis] for vertex in triangle) for axis in range(3)),
    )


def _boxes_overlap(first: Box, second: Box, epsilon: float) -> bool:
    first_low, first_high = first
    second_low, second_high = second
    for axis in range(3):
        if first_high[axis] + epsilon < second_low[axis]:
            return False
        if second_high[axis] + epsilon < first_low[axis]:
            return False
    return True


def _point_inside_triangle(point: Point, triangle: Triangle, epsilon: float) -> bool:
    """Barycentric containment for a point already known to lie on the plane."""
    a, b, c = triangle
    edge0 = _minus(b, a)
    edge1 = _minus(c, a)
    relative = _minus(point, a)
    d00 = _dot(edge0, edge0)
    d01 = _dot(edge0, edge1)
    d11 = _dot(edge1, edge1)
    d20 = _dot(relative, edge0)
    d21 = _dot(relative, edge1)
    denominator = d00 * d11 - d01 * d01
    if denominator <= 0 or not math.isfinite(denominator):
        raise MeshSelfIntersectionError("self-intersection inspection requires non-degenerate triangles")
    v = (d11 * d20 - d01 * d21) / denominator
    w = (d00 * d21 - d01 * d20) / denominator
    u = 1.0 - v - w
    return u >= -epsilon and v >= -epsilon and w >= -epsilon


def _segment_hits_triangle(start: Point, end: Point, triangle: Triangle, normal: Point, epsilon: float) -> bool:
    direction = _minus(end, start)
    denominator = _dot(normal, direction)
    if abs(denominator) <= epsilon:
        return False
    plane_offset = _dot(normal, _minus(triangle[0], start))
    parameter = plane_offset / denominator
    if parameter < -epsilon or parameter > 1.0 + epsilon:
        return False
    point = _plus_scaled(start, direction, parameter)
    return _point_inside_triangle(point, triangle, epsilon)


def _project(point: Point, omitted_axis: int) -> tuple[float, float]:
    values = [point[axis] for axis in range(3) if axis != omitted_axis]
    return values[0], values[1]


def _orientation(a, b, c) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _point_on_2d_segment(point, start, end, epsilon: float) -> bool:
    if abs(_orientation(start, end, point)) > epsilon:
        return False
    return (
        min(start[0], end[0]) - epsilon <= point[0] <= max(start[0], end[0]) + epsilon
        and min(start[1], end[1]) - epsilon <= point[1] <= max(start[1], end[1]) + epsilon
    )


def _segments_overlap_2d(a0, a1, b0, b1, epsilon: float) -> bool:
    oa = _orientation(a0, a1, b0)
    ob = _orientation(a0, a1, b1)
    oc = _orientation(b0, b1, a0)
    od = _orientation(b0, b1, a1)
    proper = (
        ((oa > epsilon and ob < -epsilon) or (oa < -epsilon and ob > epsilon))
        and ((oc > epsilon and od < -epsilon) or (oc < -epsilon and od > epsilon))
    )
    if proper:
        return True
    return (
        (abs(oa) <= epsilon and _point_on_2d_segment(b0, a0, a1, epsilon))
        or (abs(ob) <= epsilon and _point_on_2d_segment(b1, a0, a1, epsilon))
        or (abs(oc) <= epsilon and _point_on_2d_segment(a0, b0, b1, epsilon))
        or (abs(od) <= epsilon and _point_on_2d_segment(a1, b0, b1, epsilon))
    )


def _point_in_triangle_2d(point, triangle, epsilon: float) -> bool:
    signs = (
        _orientation(triangle[0], triangle[1], point),
        _orientation(triangle[1], triangle[2], point),
        _orientation(triangle[2], triangle[0], point),
    )
    has_positive = any(value > epsilon for value in signs)
    has_negative = any(value < -epsilon for value in signs)
    return not (has_positive and has_negative)


def _coplanar_overlap(first: Triangle, second: Triangle, normal: Point, epsilon: float) -> bool:
    omitted_axis = max(range(3), key=lambda axis: abs(normal[axis]))
    first_2d = tuple(_project(vertex, omitted_axis) for vertex in first)
    second_2d = tuple(_project(vertex, omitted_axis) for vertex in second)
    for first_edge in range(3):
        a0 = first_2d[first_edge]
        a1 = first_2d[(first_edge + 1) % 3]
        for second_edge in range(3):
            b0 = second_2d[second_edge]
            b1 = second_2d[(second_edge + 1) % 3]
            if _segments_overlap_2d(a0, a1, b0, b1, epsilon):
                return True
    return (
        _point_in_triangle_2d(first_2d[0], second_2d, epsilon)
        or _point_in_triangle_2d(second_2d[0], first_2d, epsilon)
    )


def _triangles_overlap(first: Triangle, second: Triangle, epsilon: float) -> bool:
    first_normal = _triangle_normal(first)
    second_normal = _triangle_normal(second)
    first_normal_length = _magnitude(first_normal)
    second_normal_length = _magnitude(second_normal)
    if first_normal_length <= epsilon or second_normal_length <= epsilon:
        raise MeshSelfIntersectionError("self-intersection inspection requires non-degenerate triangles")

    normal_cross_length = _magnitude(_cross(first_normal, second_normal))
    parallel_threshold = epsilon * first_normal_length * second_normal_length
    if normal_cross_length <= parallel_threshold:
        plane_distance = abs(_dot(first_normal, _minus(second[0], first[0]))) / first_normal_length
        if plane_distance > epsilon:
            return False
        return _coplanar_overlap(first, second, first_normal, epsilon)

    for edge in range(3):
        if _segment_hits_triangle(
            first[edge], first[(edge + 1) % 3], second, second_normal, epsilon
        ):
            return True
        if _segment_hits_triangle(
            second[edge], second[(edge + 1) % 3], first, first_normal, epsilon
        ):
            return True
    return False


def _truth_boundary(complete: bool) -> dict[str, bool]:
    return {
        "nonadjacent_triangle_self_intersection_checked": complete,
        "topological_neighbor_contacts_excluded": True,
        "adjacent_foldover_or_contact_checked": False,
        "continuous_deformation_checked": False,
        "collision_or_gameplay_checked": False,
        "visual_quality_checked": False,
        "repair_or_adoption_authorized": False,
    }


def inspect_triangle_self_intersections(
    positions: Iterable[Sequence[float]],
    indices: Iterable[int],
    *,
    epsilon: float = 1e-9,
    max_examples: int = MAX_EXAMPLES,
    max_triangle_pair_checks: int = DEFAULT_MAX_TRIANGLE_PAIR_CHECKS,
) -> dict[str, Any]:
    """Inspect nonadjacent triangle pairs under an explicit pair-work ceiling.

    AABB rejection reduces expensive geometric predicates but not the number of
    unordered source-triangle pairs visited. Therefore the observer computes the
    exact all-pairs iteration count first and returns a HOLD without a partial
    result when the requested budget is insufficient.
    """
    try:
        vertices = tuple(_read_point(value, f"positions[{index}]") for index, value in enumerate(positions))
    except TypeError as exc:
        raise MeshSelfIntersectionError("positions must be an iterable of 3D points") from exc
    if not vertices:
        raise MeshSelfIntersectionError("positions must contain at least one vertex")
    if len(vertices) > MAX_VERTICES:
        raise MeshSelfIntersectionError(f"mesh exceeds {MAX_VERTICES} vertices")

    try:
        raw_indices = tuple(indices)
    except TypeError as exc:
        raise MeshSelfIntersectionError("indices must be an iterable of triangle indices") from exc
    if not raw_indices or len(raw_indices) % 3:
        raise MeshSelfIntersectionError("indices must contain one or more complete triangles")
    if any(type(index) is not int for index in raw_indices):
        raise MeshSelfIntersectionError("triangle indices must be integers")
    if any(index < 0 or index >= len(vertices) for index in raw_indices):
        raise MeshSelfIntersectionError("triangle index is out of range")

    triangle_count = len(raw_indices) // 3
    if triangle_count > MAX_TRIANGLES:
        raise MeshSelfIntersectionError(f"mesh exceeds {MAX_TRIANGLES} triangles")

    epsilon = _finite_number(epsilon, "epsilon")
    if epsilon <= 0:
        raise MeshSelfIntersectionError("epsilon must be > 0")
    if type(max_examples) is not int or not 0 <= max_examples <= MAX_EXAMPLES:
        raise MeshSelfIntersectionError(f"max_examples must be an integer between 0 and {MAX_EXAMPLES}")
    if type(max_triangle_pair_checks) is not int or max_triangle_pair_checks <= 0:
        raise MeshSelfIntersectionError("max_triangle_pair_checks must be a positive integer")
    if max_triangle_pair_checks > HARD_MAX_TRIANGLE_PAIR_CHECKS:
        raise MeshSelfIntersectionError(
            f"max_triangle_pair_checks exceeds hard ceiling {HARD_MAX_TRIANGLE_PAIR_CHECKS}"
        )

    required_pair_checks = triangle_count * (triangle_count - 1) // 2
    if required_pair_checks > max_triangle_pair_checks:
        return {
            "status": "HOLD_TRIANGLE_PAIR_BUDGET_EXCEEDED",
            "inspection_complete": False,
            "vertex_count": len(vertices),
            "triangle_count": triangle_count,
            "epsilon": epsilon,
            "max_triangle_pair_checks": max_triangle_pair_checks,
            "triangle_pair_checks_required": required_pair_checks,
            "triangle_pair_checks_performed": 0,
            "skipped_topological_neighbor_pairs": None,
            "broad_phase_candidate_pairs": None,
            "self_intersection_pair_count": None,
            "examples": [],
            "truth_boundary": _truth_boundary(False),
            "limitations": [
                "The quadratic pair scan was not started because the explicit work budget would be exceeded.",
                "No scanned prefix is relabelled as a complete mesh result.",
                "Triangle degeneracy is not geometrically evaluated on a budget HOLD; only point/index stream validity and bounds are established.",
            ],
        }

    source_faces: list[tuple[int, int, int]] = []
    triangles: list[Triangle] = []
    boxes: list[Box] = []
    for triangle_index in range(triangle_count):
        face = tuple(raw_indices[triangle_index * 3: triangle_index * 3 + 3])
        if len(set(face)) != 3:
            raise MeshSelfIntersectionError(f"triangle {triangle_index} is collapsed by index")
        triangle = tuple(vertices[index] for index in face)
        if _magnitude(_triangle_normal(triangle)) <= epsilon:
            raise MeshSelfIntersectionError(f"triangle {triangle_index} is geometrically degenerate")
        source_faces.append(face)
        triangles.append(triangle)
        boxes.append(_box_for(triangle))

    checked_pairs = 0
    skipped_neighbors = 0
    broad_phase_pairs = 0
    intersection_count = 0
    examples: list[dict[str, int]] = []

    for left in range(triangle_count):
        left_indices = set(source_faces[left])
        for right in range(left + 1, triangle_count):
            checked_pairs += 1
            if left_indices.intersection(source_faces[right]):
                skipped_neighbors += 1
                continue
            if not _boxes_overlap(boxes[left], boxes[right], epsilon):
                continue
            broad_phase_pairs += 1
            if _triangles_overlap(triangles[left], triangles[right], epsilon):
                intersection_count += 1
                if len(examples) < max_examples:
                    examples.append({"triangle_a": left, "triangle_b": right})

    if checked_pairs != required_pair_checks:
        raise AssertionError("bounded self-intersection pair accounting drifted")

    status = (
        "PASS_NO_NONADJACENT_SELF_INTERSECTIONS"
        if intersection_count == 0
        else "SELF_INTERSECTIONS_DETECTED"
    )
    return {
        "status": status,
        "inspection_complete": True,
        "vertex_count": len(vertices),
        "triangle_count": triangle_count,
        "epsilon": epsilon,
        "max_triangle_pair_checks": max_triangle_pair_checks,
        "triangle_pair_checks_required": required_pair_checks,
        "triangle_pair_checks_performed": checked_pairs,
        "skipped_topological_neighbor_pairs": skipped_neighbors,
        "broad_phase_candidate_pairs": broad_phase_pairs,
        "self_intersection_pair_count": intersection_count,
        "examples": examples,
        "truth_boundary": _truth_boundary(True),
        "limitations": [
            "Pairs sharing an exact source vertex index are excluded; adjacent fold-over/contact is not classified.",
            "Predicates use finite Python float arithmetic and epsilon thresholds, not exact computational geometry.",
            "A complete report is geometric evidence only; it does not authorize repair, mesh adoption, collision suitability, visual acceptance, or production release.",
        ],
    }

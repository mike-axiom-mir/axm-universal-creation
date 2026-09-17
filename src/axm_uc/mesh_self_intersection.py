"""Bounded read-only nonadjacent triangle self-intersection evidence.

This module extracts neutral indexed-triangle geometry machinery independently
proved in AXM Animal and AXM Character receiving domains. It deliberately stays
separate from :mod:`axm_uc.mesh_topology`: edge/fan topology and geometric
self-intersection have different work bounds and different truth boundaries.

The observer never repairs, welds, splits, prunes, or adopts mesh geometry. It
excludes triangle pairs that share an exact source vertex index, so adjacent
fold-over/contact semantics remain outside this contract.
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

DONOR_PROVENANCE = (
    {
        "repository": "mike-axiom-mir/axm-animal-design",
        "commit": "feb4b24cd36bcc879173138d240754f71db34834",
        "path": "src/axm_animal_design/self_intersection.py",
        "role": "first receiving-domain geometric-method precedent",
    },
    {
        "repository": "mike-axiom-mir/axm-character-design",
        "commit": "eae6d296867ecaa40e8f5c3f1fe37d8e3019541e",
        "path": "src/axm_character_design/self_intersection.py",
        "role": "independent second receiving-domain re-test of the same neutral method",
    },
)


class MeshSelfIntersectionError(ValueError):
    """Raised when the observer input contract is invalid."""


def _num(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise MeshSelfIntersectionError(f"{label} must be a finite number")
    converted = float(value)
    if not math.isfinite(converted):
        raise MeshSelfIntersectionError(f"{label} must be a finite number")
    return converted


def _point(value: Sequence[float], label: str) -> Point:
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise MeshSelfIntersectionError(f"{label} must contain exactly three finite coordinates")
    return tuple(_num(item, f"{label}[{index}]") for index, item in enumerate(value))


def _sub(first: Point, second: Point) -> Point:
    return tuple(first[index] - second[index] for index in range(3))


def _dot(first: Point, second: Point) -> float:
    return sum(first[index] * second[index] for index in range(3))


def _cross(first: Point, second: Point) -> Point:
    return (
        first[1] * second[2] - first[2] * second[1],
        first[2] * second[0] - first[0] * second[2],
        first[0] * second[1] - first[1] * second[0],
    )


def _length(value: Point) -> float:
    return math.sqrt(_dot(value, value))


def _aabb(triangle: Triangle) -> tuple[Point, Point]:
    return (
        tuple(min(point[axis] for point in triangle) for axis in range(3)),
        tuple(max(point[axis] for point in triangle) for axis in range(3)),
    )


def _aabb_overlap(first, second, epsilon: float) -> bool:
    first_min, first_max = first
    second_min, second_max = second
    return all(
        first_max[axis] + epsilon >= second_min[axis]
        and second_max[axis] + epsilon >= first_min[axis]
        for axis in range(3)
    )


def _segment_triangle_intersection(start: Point, end: Point, triangle: Triangle, epsilon: float) -> bool:
    a, b, c = triangle
    direction = _sub(end, start)
    edge1 = _sub(b, a)
    edge2 = _sub(c, a)
    h = _cross(direction, edge2)
    determinant = _dot(edge1, h)
    if abs(determinant) <= epsilon:
        return False
    inverse = 1.0 / determinant
    s = _sub(start, a)
    u = inverse * _dot(s, h)
    if u < -epsilon or u > 1.0 + epsilon:
        return False
    q = _cross(s, edge1)
    v = inverse * _dot(direction, q)
    if v < -epsilon or u + v > 1.0 + epsilon:
        return False
    t = inverse * _dot(edge2, q)
    return -epsilon <= t <= 1.0 + epsilon


def _orient2(first, second, third) -> float:
    return (
        (second[0] - first[0]) * (third[1] - first[1])
        - (second[1] - first[1]) * (third[0] - first[0])
    )


def _on_segment2(start, end, point, epsilon: float) -> bool:
    return (
        min(start[0], end[0]) - epsilon <= point[0] <= max(start[0], end[0]) + epsilon
        and min(start[1], end[1]) - epsilon <= point[1] <= max(start[1], end[1]) + epsilon
        and abs(_orient2(start, end, point)) <= epsilon
    )


def _segments_intersect2(first_start, first_end, second_start, second_end, epsilon: float) -> bool:
    o1 = _orient2(first_start, first_end, second_start)
    o2 = _orient2(first_start, first_end, second_end)
    o3 = _orient2(second_start, second_end, first_start)
    o4 = _orient2(second_start, second_end, first_end)
    if ((o1 > epsilon and o2 < -epsilon) or (o1 < -epsilon and o2 > epsilon)) and (
        (o3 > epsilon and o4 < -epsilon) or (o3 < -epsilon and o4 > epsilon)
    ):
        return True
    return (
        (abs(o1) <= epsilon and _on_segment2(first_start, first_end, second_start, epsilon))
        or (abs(o2) <= epsilon and _on_segment2(first_start, first_end, second_end, epsilon))
        or (abs(o3) <= epsilon and _on_segment2(second_start, second_end, first_start, epsilon))
        or (abs(o4) <= epsilon and _on_segment2(second_start, second_end, first_end, epsilon))
    )


def _point_in_triangle2(point, triangle, epsilon: float) -> bool:
    a, b, c = triangle
    o1 = _orient2(a, b, point)
    o2 = _orient2(b, c, point)
    o3 = _orient2(c, a, point)
    has_positive = any(value > epsilon for value in (o1, o2, o3))
    has_negative = any(value < -epsilon for value in (o1, o2, o3))
    return not (has_positive and has_negative)


def _project2(point: Point, drop_axis: int):
    return tuple(point[axis] for axis in range(3) if axis != drop_axis)


def _coplanar_triangles_intersect(first: Triangle, second: Triangle, normal: Point, epsilon: float) -> bool:
    drop_axis = max(range(3), key=lambda axis: abs(normal[axis]))
    first_2d = tuple(_project2(point, drop_axis) for point in first)
    second_2d = tuple(_project2(point, drop_axis) for point in second)
    for index in range(3):
        first_start, first_end = first_2d[index], first_2d[(index + 1) % 3]
        for other in range(3):
            second_start, second_end = second_2d[other], second_2d[(other + 1) % 3]
            if _segments_intersect2(first_start, first_end, second_start, second_end, epsilon):
                return True
    return (
        _point_in_triangle2(first_2d[0], second_2d, epsilon)
        or _point_in_triangle2(second_2d[0], first_2d, epsilon)
    )


def _triangles_intersect(first: Triangle, second: Triangle, epsilon: float) -> bool:
    first_normal = _cross(_sub(first[1], first[0]), _sub(first[2], first[0]))
    second_normal = _cross(_sub(second[1], second[0]), _sub(second[2], second[0]))
    first_length = _length(first_normal)
    second_length = _length(second_normal)
    if first_length <= epsilon or second_length <= epsilon:
        raise MeshSelfIntersectionError("self-intersection inspection requires non-degenerate triangles")

    normal_cross = _length(_cross(first_normal, second_normal))
    plane_distance = abs(_dot(first_normal, _sub(second[0], first[0]))) / first_length
    if normal_cross <= epsilon * first_length * second_length and plane_distance <= epsilon:
        return _coplanar_triangles_intersect(first, second, first_normal, epsilon)

    for index in range(3):
        if _segment_triangle_intersection(first[index], first[(index + 1) % 3], second, epsilon):
            return True
        if _segment_triangle_intersection(second[index], second[(index + 1) % 3], first, epsilon):
            return True
    return False


def _truth_boundary(*, complete: bool) -> dict[str, bool]:
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
    """Inspect nonadjacent triangle pairs under an explicit bounded-work contract.

    The observer performs an all-pairs source-triangle scan with AABB rejection.
    Because even broad-phase rejection requires visiting each unordered pair, the
    complete scan is attempted only when ``n * (n - 1) / 2`` is within the caller's
    bounded pair budget. Otherwise a HOLD report is returned without a partial
    geometric claim.
    """
    try:
        vertices = tuple(_point(value, f"positions[{index}]") for index, value in enumerate(positions))
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

    epsilon = _num(epsilon, "epsilon")
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
            "truth_boundary": _truth_boundary(complete=False),
            "limitations": [
                "The observer did not start the quadratic pair scan because the explicit pair budget would be exceeded.",
                "No partial prefix is reported as a complete self-intersection result.",
                "Triangle degeneracy is not geometrically evaluated on a budget HOLD; only point/index stream validity and bounds are established.",
            ],
        }

    triangle_indices: list[tuple[int, int, int]] = []
    triangles: list[Triangle] = []
    boxes = []
    for triangle_index in range(triangle_count):
        face = tuple(raw_indices[triangle_index * 3: triangle_index * 3 + 3])
        if len(set(face)) != 3:
            raise MeshSelfIntersectionError(f"triangle {triangle_index} is collapsed by index")
        triangle = tuple(vertices[index] for index in face)
        area2 = _length(_cross(_sub(triangle[1], triangle[0]), _sub(triangle[2], triangle[0])))
        if area2 <= epsilon:
            raise MeshSelfIntersectionError(f"triangle {triangle_index} is geometrically degenerate")
        triangle_indices.append(face)
        triangles.append(triangle)
        boxes.append(_aabb(triangle))

    checked_pairs = 0
    skipped_topological_neighbors = 0
    broad_phase_pairs = 0
    intersection_count = 0
    examples: list[dict[str, int]] = []

    for left in range(triangle_count):
        left_vertices = set(triangle_indices[left])
        for right in range(left + 1, triangle_count):
            checked_pairs += 1
            if left_vertices.intersection(triangle_indices[right]):
                skipped_topological_neighbors += 1
                continue
            if not _aabb_overlap(boxes[left], boxes[right], epsilon):
                continue
            broad_phase_pairs += 1
            if _triangles_intersect(triangles[left], triangles[right], epsilon):
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
        "skipped_topological_neighbor_pairs": skipped_topological_neighbors,
        "broad_phase_candidate_pairs": broad_phase_pairs,
        "self_intersection_pair_count": intersection_count,
        "examples": examples,
        "truth_boundary": _truth_boundary(complete=True),
        "limitations": [
            "Pairs sharing an exact source vertex index are excluded; adjacent fold-over/contact is not classified.",
            "The geometric predicates use finite Python float arithmetic and epsilon thresholds, not exact computational geometry.",
            "The observer does not mutate geometry or authorize repair, adoption, collision suitability, visual acceptance, or production release.",
        ],
    }

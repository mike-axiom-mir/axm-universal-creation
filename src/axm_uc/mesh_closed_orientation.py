"""Read-only closed-component orientability and signed-orientation evidence.

This module is deliberately an observation helper for ``mesh_topology``.  It
solves face-parity constraints on already validated seam-welded triangle
components and reports algebraic signed volume in the caller-declared input
frame.  It never rewrites source indices, chooses a renderer front-face rule,
or authorizes source repair/adoption.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict, deque
from typing import Any, Mapping, Sequence

Point = tuple[float, float, float]
Edge = tuple[int, int]
Face = tuple[int, int, int]


def _sha256_lines(lines: Sequence[str]) -> str:
    digest = hashlib.sha256()
    for line in lines:
        digest.update(line.encode("utf-8"))
        digest.update(b"\n")
    return digest.hexdigest()


def _signed_volume(
    triangle_indices: Sequence[int],
    valid_faces: Mapping[int, Face],
    vertices: Sequence[Point],
    parity: Mapping[int, int] | None = None,
) -> float:
    """Return algebraic volume using the numeric XYZ right-hand cross product."""
    accumulator = 0.0
    for triangle_index in triangle_indices:
        a, b, c = valid_faces[triangle_index]
        if parity is not None and parity.get(triangle_index, 0):
            b, c = c, b
        p0, p1, p2 = vertices[a], vertices[b], vertices[c]
        cross = (
            p1[1] * p2[2] - p1[2] * p2[1],
            p1[2] * p2[0] - p1[0] * p2[2],
            p1[0] * p2[1] - p1[1] * p2[0],
        )
        accumulator += p0[0] * cross[0] + p0[1] * cross[1] + p0[2] * cross[2]
    return accumulator / 6.0


def _volume_state(value: float | None, epsilon: float) -> str:
    if value is None:
        return "NOT_EVALUATED"
    if abs(value) <= epsilon:
        return "NEAR_ZERO"
    return "POSITIVE" if value > 0.0 else "NEGATIVE"


def _build_components(
    valid_triangles: Sequence[int],
    edge_faces: Mapping[Edge, Sequence[tuple[int, int]]],
) -> tuple[list[list[int]], dict[int, int], list[list[tuple[Edge, Sequence[tuple[int, int]]]]]]:
    """Build deterministic edge-connected triangle components in linear incidence work."""
    parent = {triangle: triangle for triangle in valid_triangles}

    def find(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union(first: int, second: int) -> None:
        root_first, root_second = find(first), find(second)
        if root_first == root_second:
            return
        if root_first < root_second:
            parent[root_second] = root_first
        else:
            parent[root_first] = root_second

    for incidents in edge_faces.values():
        faces = sorted({triangle for triangle, _direction in incidents})
        if len(faces) > 1:
            anchor = faces[0]
            for other in faces[1:]:
                union(anchor, other)

    by_root: dict[int, list[int]] = defaultdict(list)
    for triangle in valid_triangles:
        by_root[find(triangle)].append(triangle)

    roots = sorted(by_root, key=lambda root: min(by_root[root]))
    components = [sorted(by_root[root]) for root in roots]
    component_index_by_triangle = {
        triangle: component_index
        for component_index, triangles in enumerate(components)
        for triangle in triangles
    }
    component_edges: list[list[tuple[Edge, Sequence[tuple[int, int]]]]] = [
        [] for _component in components
    ]
    for edge, incidents in edge_faces.items():
        if not incidents:
            continue
        component_index = component_index_by_triangle[incidents[0][0]]
        component_edges[component_index].append((edge, incidents))
    for edges in component_edges:
        edges.sort(key=lambda item: item[0])

    return components, component_index_by_triangle, component_edges


def _solve_parity(
    triangles: Sequence[int],
    edges: Sequence[tuple[Edge, Sequence[tuple[int, int]]]],
) -> tuple[bool, dict[int, int], int]:
    """Solve deterministic XOR face-flip constraints without mutating the mesh."""
    adjacency: dict[int, list[tuple[int, int, Edge]]] = defaultdict(list)
    constraint_edges = 0
    for edge, incidents in edges:
        if len(incidents) != 2:
            continue
        (first_triangle, first_direction), (second_triangle, second_direction) = incidents
        required_xor = 1 if first_direction == second_direction else 0
        adjacency[first_triangle].append((second_triangle, required_xor, edge))
        adjacency[second_triangle].append((first_triangle, required_xor, edge))
        constraint_edges += 1

    parity: dict[int, int] = {}
    for seed in triangles:
        if seed in parity:
            continue
        parity[seed] = 0
        queue: deque[int] = deque([seed])
        while queue:
            triangle = queue.popleft()
            for neighbor, required_xor, edge in sorted(
                adjacency[triangle], key=lambda item: (item[0], item[2])
            ):
                expected = parity[triangle] ^ required_xor
                if neighbor in parity:
                    if parity[neighbor] != expected:
                        return False, {}, constraint_edges
                    continue
                parity[neighbor] = expected
                queue.append(neighbor)

    return True, parity, constraint_edges


def inspect_closed_component_orientation(
    *,
    raw_indices: Sequence[int],
    welded_vertices: Sequence[Point],
    valid_faces: Mapping[int, Face],
    edge_faces: Mapping[Edge, Sequence[tuple[int, int]]],
    valid_triangles: Sequence[int],
    collapsed_triangles: Sequence[int],
    triangle_budget: int,
    volume_epsilon: float,
    frame_label: str,
    handedness: str,
    max_examples: int,
) -> dict[str, Any]:
    """Inspect closed seam-welded components without changing source geometry.

    The parity solution keeps the lowest triangle index in each component unflipped.
    That makes the solution deterministic but deliberately does *not* normalize its
    global sign.  The complementary solution is equally orientable and would invert
    algebraic signed volume.
    """
    components, _component_index_by_triangle, component_edges = _build_components(
        valid_triangles, edge_faces
    )

    reports: list[dict[str, Any]] = []
    orientable_count = 0
    non_orientable_count = 0
    not_evaluated_count = 0

    for component_index, triangles in enumerate(components):
        edges = component_edges[component_index]
        boundary_edges = [edge for edge, incidents in edges if len(incidents) == 1]
        nonmanifold_edges = [edge for edge, incidents in edges if len(incidents) > 2]
        orientation_conflicts = [
            edge
            for edge, incidents in edges
            if len(incidents) == 2 and incidents[0][1] == incidents[1][1]
        ]

        if nonmanifold_edges:
            closure_state = "NON_MANIFOLD"
        elif boundary_edges:
            closure_state = "OPEN"
        else:
            closure_state = "CLOSED"

        if closure_state == "CLOSED":
            current_shared_edge_orientation_state = (
                "CONSISTENT" if not orientation_conflicts else "CONFLICTING"
            )
        else:
            current_shared_edge_orientation_state = "NOT_EVALUATED"

        component_digest = _sha256_lines(
            [
                f"{triangle}:{raw_indices[triangle * 3]},{raw_indices[triangle * 3 + 1]},{raw_indices[triangle * 3 + 2]}"
                for triangle in triangles
            ]
        )

        report: dict[str, Any] = {
            "component_index": component_index,
            "triangle_index_min": min(triangles),
            "triangle_index_max": max(triangles),
            "triangle_count": len(triangles),
            "triangle_identity_sha256": component_digest,
            "edge_count": len(edges),
            "boundary_edge_count": len(boundary_edges),
            "nonmanifold_edge_count": len(nonmanifold_edges),
            "current_orientation_conflict_edge_count": len(orientation_conflicts),
            "closure_state": closure_state,
            "current_shared_edge_orientation_state": current_shared_edge_orientation_state,
            "orientability_state": "NOT_EVALUATED",
            "not_evaluated_reason": None,
            "orientation_constraint_edge_count": 0,
            "parity_solution_sha256": None,
            "diagnostic_face_flip_count": None,
            "diagnostic_face_flip_examples": [],
            "current_signed_volume": None,
            "current_signed_volume_state": "NOT_EVALUATED",
            "coherent_candidate_signed_volume": None,
            "coherent_candidate_signed_volume_state": "NOT_EVALUATED",
            "global_sign_normalized": False,
        }

        if collapsed_triangles:
            report["not_evaluated_reason"] = "COLLAPSED_TRIANGLES_PRESENT"
            not_evaluated_count += 1
            reports.append(report)
            continue
        if len(triangles) > triangle_budget:
            report["not_evaluated_reason"] = "TRIANGLE_WORK_BUDGET_EXCEEDED"
            not_evaluated_count += 1
            reports.append(report)
            continue
        if closure_state == "OPEN":
            report["not_evaluated_reason"] = "OPEN_COMPONENT"
            not_evaluated_count += 1
            reports.append(report)
            continue
        if closure_state == "NON_MANIFOLD":
            report["not_evaluated_reason"] = "NON_MANIFOLD_COMPONENT"
            not_evaluated_count += 1
            reports.append(report)
            continue

        orientable, parity, constraint_edges = _solve_parity(triangles, edges)
        report["orientation_constraint_edge_count"] = constraint_edges
        if not orientable:
            report["orientability_state"] = "NON_ORIENTABLE"
            non_orientable_count += 1
            reports.append(report)
            continue

        report["orientability_state"] = "ORIENTABLE"
        orientable_count += 1
        flip_triangles = [triangle for triangle in triangles if parity[triangle]]
        report["parity_solution_sha256"] = _sha256_lines(
            [f"{triangle}:{parity[triangle]}" for triangle in triangles]
        )
        report["diagnostic_face_flip_count"] = len(flip_triangles)
        report["diagnostic_face_flip_examples"] = flip_triangles[:max_examples]

        candidate_signed_volume = _signed_volume(
            triangles, valid_faces, welded_vertices, parity
        )
        report["coherent_candidate_signed_volume"] = candidate_signed_volume
        report["coherent_candidate_signed_volume_state"] = _volume_state(
            candidate_signed_volume, volume_epsilon
        )

        if current_shared_edge_orientation_state == "CONSISTENT":
            current_signed_volume = _signed_volume(
                triangles, valid_faces, welded_vertices, None
            )
            report["current_signed_volume"] = current_signed_volume
            report["current_signed_volume_state"] = _volume_state(
                current_signed_volume, volume_epsilon
            )

        reports.append(report)

    return {
        "schema": "axm.mesh-closed-component-orientation/v0.1",
        "inspection_complete": not collapsed_triangles and not_evaluated_count == 0,
        "global_not_evaluated_reason": (
            "COLLAPSED_TRIANGLES_PRESENT" if collapsed_triangles else None
        ),
        "component_count": len(reports),
        "orientable_component_count": orientable_count,
        "non_orientable_component_count": non_orientable_count,
        "not_evaluated_component_count": not_evaluated_count,
        "triangle_budget_per_component": triangle_budget,
        "volume_epsilon": volume_epsilon,
        "coordinate_frame": {
            "label": frame_label,
            "handedness": handedness,
            "signed_volume_convention": "sum(dot(p0,cross(p1,p2)))/6_on_seam_welded_numeric_XYZ",
            "handedness_changing_transform_can_flip_sign": True,
        },
        "components": reports,
        "truth_boundary": {
            "read_only_observer": True,
            "source_geometry_rewritten": False,
            "source_winding_repaired": False,
            "source_repair_authorized": False,
            "parity_solution_diagnostic_only": True,
            "lowest_triangle_seed_kept_unflipped": True,
            "global_parity_complement_not_normalized": True,
            "positive_signed_volume_called_outward": False,
            "signed_volume_uses_seam_welded_representatives": True,
            "renderer_front_face_or_culling_checked": False,
            "normals_or_tangents_rewritten": False,
            "self_intersection_checked": False,
            "physical_volume_certified": False,
            "collision_suitability_checked": False,
            "visual_quality_checked": False,
            "product_adoption_authorized": False,
        },
    }

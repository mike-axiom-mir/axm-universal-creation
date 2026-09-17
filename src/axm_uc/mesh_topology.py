"""Deterministic structural topology evidence for bounded triangle meshes.

This module diagnoses source-vertex liveness plus seam-welded edge topology. It
does not prove freedom from self-intersection, vertex-manifoldness, deformation
quality, collision suitability, or visual quality, and it never authorizes source
vertex deletion.
"""
from __future__ import annotations

import math
from collections import defaultdict
from typing import Any, Iterable, Sequence

MAX_VERTICES = 131_072
MAX_TRIANGLES = 131_072
MAX_EXAMPLES = 16

Point = tuple[float, float, float]
Edge = tuple[int, int]


class MeshTopologyError(ValueError):
    pass


def _point(value: Sequence[float], label: str) -> Point:
    if (
        not isinstance(value, (list, tuple))
        or len(value) != 3
        or any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in value)
    ):
        raise MeshTopologyError(f"{label} must contain exactly three finite coordinates")
    point = tuple(float(item) for item in value)
    if not all(math.isfinite(item) for item in point):
        raise MeshTopologyError(f"{label} must contain exactly three finite coordinates")
    return point


def _indices(raw: Iterable[int]) -> tuple[int, ...]:
    try:
        indices = tuple(raw)
    except TypeError as exc:
        raise MeshTopologyError("indices must be an iterable of triangle indices") from exc
    if not indices or len(indices) % 3:
        raise MeshTopologyError("indices must contain one or more complete triangles")
    if len(indices) // 3 > MAX_TRIANGLES:
        raise MeshTopologyError(f"mesh exceeds {MAX_TRIANGLES} triangles")
    if any(type(index) is not int for index in indices):
        raise MeshTopologyError("triangle indices must be integers")
    return indices


def _weld_vertices(vertices: tuple[Point, ...], tolerance: float) -> tuple[tuple[Point, ...], tuple[int, ...]]:
    """Cluster source vertices around first-seen representatives within tolerance.

    Representative clustering is deliberately non-transitive: a chain of vertices
    cannot bridge a seam wider than the requested tolerance through intermediate
    points. Source order makes the clustering deterministic without editing source
    coordinates.
    """
    grid: dict[tuple[int, int, int], list[int]] = defaultdict(list)
    welded: list[Point] = []
    source_to_welded: list[int] = []
    tolerance2 = tolerance * tolerance

    for point in vertices:
        cell = tuple(math.floor(axis / tolerance) for axis in point)
        candidates: list[tuple[float, int]] = []
        for dx in (-1, 0, 1):
            for dy in (-1, 0, 1):
                for dz in (-1, 0, 1):
                    for candidate in grid.get((cell[0] + dx, cell[1] + dy, cell[2] + dz), ()):
                        reference = welded[candidate]
                        distance2 = sum((point[axis] - reference[axis]) ** 2 for axis in range(3))
                        if distance2 <= tolerance2:
                            candidates.append((distance2, candidate))
        if candidates:
            _distance2, selected = min(candidates, key=lambda item: (item[0], item[1]))
            source_to_welded.append(selected)
            continue

        selected = len(welded)
        welded.append(point)
        source_to_welded.append(selected)
        grid[cell].append(selected)

    return tuple(welded), tuple(source_to_welded)


def inspect_mesh_topology(
    positions: Iterable[Sequence[float]],
    indices: Iterable[int],
    *,
    weld_tolerance: float = 1e-6,
) -> dict[str, Any]:
    """Return source-liveness and seam-welded edge-topology evidence.

    ``indices`` is a flat triangle index list. Source-array liveness is measured
    from the validated source index stream before any positional welding. Coincident
    source vertices are then clustered by Euclidean distance before edge incidence
    is measured, which lets hard-normal/material seams be diagnosed as one geometric
    surface without rewriting the source mesh.
    """
    if isinstance(weld_tolerance, bool) or not isinstance(weld_tolerance, (int, float)):
        raise MeshTopologyError("weld_tolerance must be a finite positive number")
    tolerance = float(weld_tolerance)
    if not math.isfinite(tolerance) or tolerance <= 0:
        raise MeshTopologyError("weld_tolerance must be a finite positive number")

    try:
        vertices = tuple(_point(value, f"positions[{index}]") for index, value in enumerate(positions))
    except TypeError as exc:
        raise MeshTopologyError("positions must be an iterable of 3D points") from exc
    if not vertices:
        raise MeshTopologyError("mesh must contain at least one vertex")
    if len(vertices) > MAX_VERTICES:
        raise MeshTopologyError(f"mesh exceeds {MAX_VERTICES} vertices")

    raw_indices = _indices(indices)
    if any(index < 0 or index >= len(vertices) for index in raw_indices):
        raise MeshTopologyError("triangle index is out of range")

    referenced_source_vertices = set(raw_indices)
    unreferenced_source_vertices = tuple(
        index for index in range(len(vertices)) if index not in referenced_source_vertices
    )

    welded_vertices, source_to_welded = _weld_vertices(vertices, tolerance)

    edge_faces: dict[Edge, list[tuple[int, int]]] = defaultdict(list)
    collapsed_triangles: list[int] = []
    valid_triangles: list[int] = []

    for triangle_index in range(len(raw_indices) // 3):
        source_face = raw_indices[triangle_index * 3: triangle_index * 3 + 3]
        face = tuple(source_to_welded[index] for index in source_face)
        if len(set(face)) != 3:
            collapsed_triangles.append(triangle_index)
            continue

        a, b, c = face
        pa, pb, pc = (welded_vertices[index] for index in face)
        u = tuple(pb[axis] - pa[axis] for axis in range(3))
        v = tuple(pc[axis] - pa[axis] for axis in range(3))
        cross = (
            u[1] * v[2] - u[2] * v[1],
            u[2] * v[0] - u[0] * v[2],
            u[0] * v[1] - u[1] * v[0],
        )
        if sum(value * value for value in cross) <= tolerance ** 4:
            collapsed_triangles.append(triangle_index)
            continue

        valid_triangles.append(triangle_index)
        for start, end in ((a, b), (b, c), (c, a)):
            edge = (start, end) if start < end else (end, start)
            direction = 1 if (start, end) == edge else -1
            edge_faces[edge].append((triangle_index, direction))

    boundary_edges: list[Edge] = []
    nonmanifold_edges: list[Edge] = []
    orientation_conflicts: list[Edge] = []
    for edge, incidents in edge_faces.items():
        if len(incidents) == 1:
            boundary_edges.append(edge)
        elif len(incidents) > 2:
            nonmanifold_edges.append(edge)
        elif incidents[0][1] == incidents[1][1]:
            orientation_conflicts.append(edge)

    boundary_edges.sort()
    nonmanifold_edges.sort()
    orientation_conflicts.sort()

    parent = {triangle: triangle for triangle in valid_triangles}

    def find_triangle(item: int) -> int:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    def union_triangles(first: int, second: int) -> None:
        root_first, root_second = find_triangle(first), find_triangle(second)
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
                union_triangles(anchor, other)

    component_count = len({find_triangle(triangle) for triangle in valid_triangles}) if valid_triangles else 0

    if collapsed_triangles or nonmanifold_edges or orientation_conflicts:
        status = "INVALID_EDGE_TOPOLOGY"
    elif boundary_edges:
        status = "OPEN_EDGE_MANIFOLD_CANDIDATE"
    else:
        status = "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"

    return {
        "status": status,
        "source_vertex_count": len(vertices),
        "referenced_source_vertex_count": len(referenced_source_vertices),
        "unreferenced_source_vertex_count": len(unreferenced_source_vertices),
        "all_source_vertices_referenced": not unreferenced_source_vertices,
        "welded_vertex_count": len(welded_vertices),
        "welded_vertex_reduction": len(vertices) - len(welded_vertices),
        "triangle_count": len(raw_indices) // 3,
        "valid_triangle_count": len(valid_triangles),
        "collapsed_triangle_count": len(collapsed_triangles),
        "edge_count": len(edge_faces),
        "boundary_edge_count": len(boundary_edges),
        "nonmanifold_edge_count": len(nonmanifold_edges),
        "orientation_conflict_edge_count": len(orientation_conflicts),
        "triangle_component_count": component_count,
        "closed_by_edge_incidence": not boundary_edges and not nonmanifold_edges and not collapsed_triangles,
        "orientation_consistent_by_shared_edge": not orientation_conflicts,
        "weld_tolerance": tolerance,
        "examples": {
            "unreferenced_source_vertices": list(unreferenced_source_vertices[:MAX_EXAMPLES]),
            "collapsed_triangles": collapsed_triangles[:MAX_EXAMPLES],
            "boundary_edges": [list(edge) for edge in boundary_edges[:MAX_EXAMPLES]],
            "nonmanifold_edges": [list(edge) for edge in nonmanifold_edges[:MAX_EXAMPLES]],
            "orientation_conflict_edges": [list(edge) for edge in orientation_conflicts[:MAX_EXAMPLES]],
        },
        "truth_boundary": {
            "source_vertex_liveness_checked": True,
            "source_vertex_pruning_performed": False,
            "seam_clustered_by_position": True,
            "source_geometry_rewritten": False,
            "edge_incidence_checked": True,
            "shared_edge_orientation_checked": True,
            "vertex_manifoldness_checked": False,
            "self_intersection_checked": False,
            "deformation_quality_checked": False,
            "collision_suitability_checked": False,
            "visual_quality_checked": False,
        },
    }

"""Bounded point classification for an already welded, closed triangle surface.

Ray intersections use one fixed origin and Python float arithmetic. They never
advance a float32 BVH origin by a tiny distance that can re-hit the same face.
This is a discrete geometric query, not a swept collision or rig acceptance test.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Iterable, Literal, Sequence

Point = tuple[float, float, float]
Classification = Literal["inside", "outside", "boundary", "hold"]


def _point(value: Sequence[float]) -> Point:
    if len(value) != 3 or any(isinstance(v, bool) for v in value):
        raise ValueError("Expected three finite coordinates")
    result = tuple(float(v) for v in value)
    if not all(math.isfinite(v) for v in result):
        raise ValueError("Expected three finite coordinates")
    return result


def _sub(a: Point, b: Point) -> Point:
    return tuple(a[i] - b[i] for i in range(3))


def _dot(a: Point, b: Point) -> float:
    return sum(a[i] * b[i] for i in range(3))


def _cross(a: Point, b: Point) -> Point:
    return (a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0])


class ClosedTriangleSurface:
    """Classify points; callers supply a non-self-intersecting closed surface.

    Topology is checked after the caller's seam weld. Every undirected edge
    must have two incident triangles. Self-intersection is not established by
    that check and remains a caller precondition. Ambiguous parity returns
    ``hold`` instead of choosing the majority of disagreeing rays.
    """

    def __init__(self, vertices: Iterable[Sequence[float]], triangles: Iterable[Sequence[int]], *, tolerance_m: float = 1e-7):
        if isinstance(tolerance_m, bool) or not math.isfinite(tolerance_m) or tolerance_m <= 0:
            raise ValueError("Tolerance must be finite and positive")
        self.tolerance_m = tolerance_m
        self.vertices = tuple(_point(v) for v in vertices)
        faces = tuple(tuple(f) for f in triangles)
        if not self.vertices or not faces:
            raise ValueError("A closed triangle surface cannot be empty")
        edges: Counter = Counter()
        self._faces = []
        for f in faces:
            if len(f) != 3 or len(set(f)) != 3 or any(type(i) is not int or not 0 <= i < len(self.vertices) for i in f):
                raise ValueError("Expected valid non-repeated triangle indices")
            a, b, c = (self.vertices[i] for i in f)
            e1, e2 = _sub(b, a), _sub(c, a)
            normal = _cross(e1, e2)
            area2 = math.sqrt(_dot(normal, normal))
            if not math.isfinite(area2) or area2 <= tolerance_m*tolerance_m:
                raise ValueError("Degenerate triangle at the requested tolerance")
            self._faces.append((a, e1, e2, normal, area2))
            edges.update(tuple(sorted((f[i], f[(i+1) % 3]))) for i in range(3))
        if any(count != 2 for count in edges.values()):
            raise ValueError("Surface must be welded and closed: two triangles per edge")
        self.bounds = tuple((min(v[i] for v in self.vertices), max(v[i] for v in self.vertices)) for i in range(3))

    def classify(self, point: Sequence[float]) -> Classification:
        p, eps = _point(point), self.tolerance_m
        if any(p[i] < lo-eps or p[i] > hi+eps for i, (lo, hi) in enumerate(self.bounds)):
            return "outside"
        # Barycentric coordinates of the point projected onto each face plane.
        for a, e1, e2, normal, area2 in self._faces:
            delta = _sub(p, a)
            if abs(_dot(delta, normal)) > eps*area2:
                continue
            d00, d01, d11 = _dot(e1, e1), _dot(e1, e2), _dot(e2, e2)
            denominator = _dot(normal, normal)
            u = (d11*_dot(delta, e1)-d01*_dot(delta, e2))/denominator
            v = (d00*_dot(delta, e2)-d01*_dot(delta, e1))/denominator
            bary_eps = eps/max(math.sqrt(max(d00, d11)), eps)
            if u >= -bary_eps and v >= -bary_eps and u+v <= 1+bary_eps:
                return "boundary"
        parities = []
        for raw in ((.931, .277, .239), (.137, .971, .197), (.193, .217, .957)):
            length = math.sqrt(_dot(raw, raw))
            direction = tuple(v/length for v in raw)
            hits = []
            for a, e1, e2, normal, area2 in self._faces:
                h = _cross(direction, e2)
                determinant = _dot(e1, h)
                if abs(determinant) <= area2*1e-12:
                    continue
                delta = _sub(p, a)
                u = _dot(delta, h)/determinant
                if u < -1e-10 or u > 1+1e-10:
                    continue
                q = _cross(delta, e1)
                v = _dot(direction, q)/determinant
                if v < -1e-10 or u+v > 1+1e-10:
                    continue
                distance = _dot(e2, q)/determinant
                if distance > eps:
                    hits.append(distance)
            hits.sort()
            distinct = []
            for distance in hits:
                if distinct:
                    gap = distance-distinct[-1]
                    roundoff = min(eps, max(1e-12, 8*math.ulp(distance)))
                    if gap <= roundoff:
                        continue
                    if gap <= eps:
                        return "hold"  # Separate surfaces closer than the declared resolution.
                distinct.append(distance)
            parities.append(len(distinct) % 2)
        if len(set(parities)) != 1:
            return "hold"
        return "inside" if parities[0] else "outside"

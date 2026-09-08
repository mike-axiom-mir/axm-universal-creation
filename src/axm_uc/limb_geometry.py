"""Read-only two-bone entry ranges; no target projection or collision acceptance.

The elbow locus follows the two exact segment lengths and the supplied shoulder
and wrist. Its projection onto an entry axis exposes requests that no pole angle
can satisfy, instead of silently clamping an impossible bend request.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Literal, Sequence

Point = tuple[float, float, float]


def _finite(value: float, name: str) -> float:
    if isinstance(value, (bool, str, bytes)):
        raise ValueError(f"{name} must be a finite number")
    try:
        result = float(value)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError(f"{name} must be a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{name} must be a finite number")
    return result


def _point(value: Sequence[float], name: str) -> Point:
    try:
        values = tuple(value)
    except TypeError as exc:
        raise ValueError(f"{name} must contain three coordinates") from exc
    if len(values) != 3:
        raise ValueError(f"{name} must contain three coordinates")
    return tuple(_finite(v, name) for v in values)


def _unit(value: Point) -> Point:
    scale = max(abs(v) for v in value)
    if scale == 0:
        raise ValueError("Entry axis must be nonzero")
    scaled = tuple(v/scale for v in value)
    length = math.hypot(*scaled)
    return tuple(v/length for v in scaled)


@dataclass(frozen=True)
class TwoBoneEntryRange:
    status: Literal["reachable", "unreachable", "hold"]
    reason: str
    locus: Literal["circle", "point", "sphere"] | None = None
    center: Point | None = None
    radius_m: float | None = None
    circle_axis: Point | None = None
    minimum_entry_m: float | None = None
    maximum_entry_m: float | None = None

    def classify_minimum(self, required_m: float, *, tolerance_m: float = 1e-9) -> str:
        """Classify only the requested axial entry, never mesh clearance.

        ``boundary`` retains numerical uncertainty near the requested threshold.
        The tolerance does not enlarge the elbow locus or modify either target.
        """
        required = _finite(required_m, "Required entry")
        tolerance = _finite(tolerance_m, "Tolerance")
        if tolerance <= 0:
            raise ValueError("Tolerance must be positive")
        if self.status != "reachable":
            return self.status
        margin = self.maximum_entry_m - required
        if abs(margin) <= tolerance:
            return "boundary"
        return "possible" if margin > 0 else "impossible"


def two_bone_entry_range(
    shoulder: Sequence[float],
    wrist: Sequence[float],
    upper_length_m: float,
    forearm_length_m: float,
    entry_axis: Sequence[float],
) -> TwoBoneEntryRange:
    """Range of ``dot(elbow - wrist, unit(entry_axis))`` in one coordinate frame.

    Segment lengths must be positive. All inputs must be finite, in the same
    frame and metric. Unreachable wrists remain unreachable; coincident equal-
    length endpoints have a sphere of elbows, not an arbitrarily chosen circle.
    The model imposes no joint limits, obstacles, twist or anatomical rules.
    """
    start, end = _point(shoulder, "Shoulder"), _point(wrist, "Wrist")
    upper = _finite(upper_length_m, "Upper length")
    forearm = _finite(forearm_length_m, "Forearm length")
    if upper <= 0 or forearm <= 0:
        raise ValueError("Segment lengths must be positive")
    entry = _unit(_point(entry_axis, "Entry axis"))
    delta = tuple(end[i]-start[i] for i in range(3))
    distance = math.hypot(*delta)
    if not math.isfinite(distance):
        return TwoBoneEntryRange("hold", "Endpoint difference exceeds numeric range")
    # Normalize before squared-length arithmetic to avoid overflow and underflow.
    scale = max(upper, forearm, distance)
    u, f, d = upper/scale, forearm/scale, distance/scale
    if d > u+f or d < abs(u-f):
        return TwoBoneEntryRange("unreachable", "Wrist lies outside both-segment reach")
    if distance == 0:
        return TwoBoneEntryRange("reachable", "Coincident equal-length endpoints",
                                 "sphere", start, upper, None, -upper, upper)
    if d == 0:
        return TwoBoneEntryRange("hold", "Endpoint separation is below numeric resolution")
    axis = tuple(v/distance for v in delta)
    relative_difference = (u-f)/d
    along_scaled = .5*(d+relative_difference*(u+f))
    # Factor and cancel Heron's two small factors before multiplication. A
    # nearly coincident equal-length chain still has an almost full-radius
    # elbow circle, even when the squared endpoint separation underflows.
    radius_scaled = (.5*math.sqrt(u+f+d)*math.sqrt(max(0.0, u+f-d))
                     *math.sqrt(max(0.0, 1+relative_difference))
                     *math.sqrt(max(0.0, 1-relative_difference)))
    along, radius = along_scaled*scale, radius_scaled*scale
    center = tuple(start[i]+along*axis[i] for i in range(3))
    if not all(math.isfinite(v) for v in (*center, radius, along)):
        return TwoBoneEntryRange("hold", "Elbow locus exceeds numeric range")
    axial_cosine = max(-1.0, min(1.0, math.fsum(axis[i]*entry[i] for i in range(3))))
    # Use relative coordinates here so a large world translation does not
    # subtract two nearly equal absolute elbow/wrist coordinates.
    midpoint = (along-distance)*axial_cosine
    span = radius*math.sqrt(max(0.0, (1-axial_cosine)*(1+axial_cosine)))
    return TwoBoneEntryRange("reachable", "Exact two-segment elbow locus",
                             "point" if radius == 0 else "circle", center, radius,
                             axis, midpoint-span, midpoint+span)

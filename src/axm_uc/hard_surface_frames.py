"""Evidence for rigid hard-surface attachment frames in actual static GLB artifacts.

This is deliberately narrower than fit/contact or runtime acceptance. It checks
that named rigid marker nodes exist at declared positions with declared local
+Z forward / +Y up orientation, and that their world basis is not mirrored.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .asset_geometry import (
    GeometryIssue,
    IDENTITY,
    MAX_BYTES,
    _GLB,
    _at,
    _local,
    _multiply,
    _point,
    _vector,
)

FRAME_PLAN_SCHEMA = "axm.hard-surface-frame-plan/v0.1"
FRAME_REVIEW_SCHEMA = "axm.hard-surface-frame-review/v0.1"


def _unit(vector: list[float], name: str) -> list[float]:
    length = math.sqrt(sum(v * v for v in vector))
    if not math.isfinite(length) or length <= 1e-12:
        raise ValueError(f"{name} must have non-zero finite length")
    return [v / length for v in vector]


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b))


def _cross(a: list[float], b: list[float]) -> list[float]:
    return [
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    ]


def _angle_deg(a: list[float], b: list[float]) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, _dot(_unit(a, "a"), _unit(b, "b"))))))


def validate_frame_plan(plan: Any) -> dict[str, Any]:
    fields = {"schema", "position_tolerance_m", "angle_tolerance_deg", "frames"}
    if not isinstance(plan, dict) or set(plan) - fields or plan.get("schema") != FRAME_PLAN_SCHEMA:
        raise ValueError("invalid hard-surface frame plan schema or unknown field")
    pos_tol = plan.get("position_tolerance_m", 0.0001)
    ang_tol = plan.get("angle_tolerance_deg", 0.25)
    if type(pos_tol) not in (int, float) or not math.isfinite(pos_tol) or not 0 <= pos_tol <= 0.05:
        raise ValueError("position_tolerance_m must be finite between 0 and 0.05")
    if type(ang_tol) not in (int, float) or not math.isfinite(ang_tol) or not 0 <= ang_tol <= 45:
        raise ValueError("angle_tolerance_deg must be finite between 0 and 45")
    frames = plan.get("frames")
    if not isinstance(frames, dict) or not frames or len(frames) > 256:
        raise ValueError("frames must contain 1..256 named frame contracts")
    for name, spec in frames.items():
        if not isinstance(name, str) or not name or not isinstance(spec, dict):
            raise ValueError("frame names must be non-empty strings with object contracts")
        allowed = {"position", "forward", "up", "require_right_handed"}
        if set(spec) - allowed or not _vector(spec.get("position")) or not _vector(spec.get("forward")) or not _vector(spec.get("up")):
            raise ValueError(f"frame {name!r} requires finite position/forward/up XYZ vectors")
        if "require_right_handed" in spec and type(spec["require_right_handed"]) is not bool:
            raise ValueError("require_right_handed must be boolean")
        forward = _unit(spec["forward"], f"{name} forward")
        up = _unit(spec["up"], f"{name} up")
        if abs(_dot(forward, up)) > 1e-6:
            raise ValueError(f"frame {name!r} forward and up must be orthogonal")
    return json.loads(json.dumps(plan, allow_nan=False))


def _basis(world: list[list[float]]) -> dict[str, Any]:
    right = _unit([world[0][0], world[1][0], world[2][0]], "right basis")
    up = _unit([world[0][1], world[1][1], world[2][1]], "up basis")
    forward = _unit([world[0][2], world[1][2], world[2][2]], "forward basis")
    orthogonality_error = max(abs(_dot(right, up)), abs(_dot(right, forward)), abs(_dot(up, forward)))
    handedness = _dot(_cross(right, up), forward)
    return {
        "right": right,
        "up": up,
        "forward": forward,
        "orthogonality_error": orthogonality_error,
        "handedness": handedness,
    }


def review_hard_surface_frames(path: str | Path, plan: Any) -> dict[str, Any]:
    spec = validate_frame_plan(plan)
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    result: dict[str, Any] = {
        "schema": FRAME_REVIEW_SCHEMA,
        "status": "HOLD",
        "artifact_sha256": None,
        "plan_sha256": hashlib.sha256(encoded).hexdigest(),
        "plan": spec,
        "measurements": {"frames": {}},
        "findings": [],
        "finding_count": 0,
        "scope": (
            "Actual named rigid node world frames in one static default-scene GLB. "
            "No mesh mating, clearance/contact, strength, manufacturability, animation envelope, "
            "materials, renderer/engine acceptance, gameplay, or aesthetic proof."
        ),
    }

    def finding(code: str, **details: Any) -> None:
        result["finding_count"] += 1
        if len(result["findings"]) < 64:
            result["findings"].append({"code": code, **details})

    try:
        target = Path(path).resolve()
        with target.open("rb") as stream:
            raw = stream.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise GeometryIssue("RESOURCE_LIMIT", "GLB exceeds 128MiB limit", hold=True)
        result["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        glb = _GLB(raw)
        doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")

        stack = [(index, IDENTITY) for index in reversed(roots)]
        seen: set[int] = set()
        named: dict[str, list[list[list[float]]]] = {}
        while stack:
            index, parent = stack.pop()
            node = _at(doc.get("nodes"), index, "node")
            if index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(index)
            if len(seen) > 10000:
                raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds node limit", hold=True)
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_NODE", "skinned, weighted or extended marker nodes need separate review", hold=True)
            world = _multiply(parent, _local(node))
            if node.get("name"):
                named.setdefault(node["name"], []).append(world)
            children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend((child, world) for child in reversed(children))

        pos_tol = spec.get("position_tolerance_m", 0.0001)
        ang_tol = spec.get("angle_tolerance_deg", 0.25)
        for name, expected in spec["frames"].items():
            matches = named.get(name, [])
            if len(matches) != 1:
                finding("FRAME_IDENTITY", name=name, matches=len(matches))
                continue
            world = matches[0]
            actual_position = _point(world, (0, 0, 0))
            basis = _basis(world)
            position_error = math.dist(actual_position, expected["position"])
            forward_error = _angle_deg(basis["forward"], expected["forward"])
            up_error = _angle_deg(basis["up"], expected["up"])
            frame_measurement = {
                "actual_position": actual_position,
                "position_error_m": position_error,
                "actual_forward": basis["forward"],
                "forward_error_deg": forward_error,
                "actual_up": basis["up"],
                "up_error_deg": up_error,
                "actual_right": basis["right"],
                "orthogonality_error": basis["orthogonality_error"],
                "handedness": basis["handedness"],
            }
            result["measurements"]["frames"][name] = frame_measurement
            if position_error > pos_tol:
                finding("FRAME_POSITION", name=name, actual=actual_position, expected=expected["position"], error_m=position_error)
            if forward_error > ang_tol:
                finding("FRAME_FORWARD", name=name, actual=basis["forward"], expected=expected["forward"], error_deg=forward_error)
            if up_error > ang_tol:
                finding("FRAME_UP", name=name, actual=basis["up"], expected=expected["up"], error_deg=up_error)
            if basis["orthogonality_error"] > 1e-6:
                finding("FRAME_NONORTHOGONAL", name=name, error=basis["orthogonality_error"])
            if expected.get("require_right_handed", True) and basis["handedness"] <= 0:
                finding("FRAME_MIRRORED", name=name, handedness=basis["handedness"])

        result["status"] = "FAIL" if result["finding_count"] else "PASS"
    except GeometryIssue as exc:
        finding(exc.code, message=str(exc))
        result["status"] = "HOLD" if exc.hold else "FAIL"
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, OverflowError) as exc:
        finding("INVALID_INPUT", message=str(exc))
        result["status"] = "FAIL"
    return result

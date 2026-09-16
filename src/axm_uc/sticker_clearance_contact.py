from __future__ import annotations

import copy
import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

from axm_stickers.assembly import ASSEMBLY, expand
from axm_stickers.core import Registry, resolve
from axm_stickers.placement import attachment_matrix, identity, multiply, rigid

from .asset_geometry import GeometryIssue, IDENTITY as GLTF_IDENTITY, MAX_TRIANGLES, _GLB, _at, _local, _multiply as gltf_multiply, _point as gltf_point
from .design_workshop import validate_sketch
from .design_workshop_construction import _exact_definition, _pin
from .game_pose_runtime import GamePoseAsset, _parse
from .sticker_adapter import GLB
from .sticker_geometry_calipers import _encode_geometry_view, _flat_point
from .sticker_multiplier import _machine_body, _resolve_registry_path
from .triangle_queries import ClosedTriangleSurface

PAIR_SCHEMA = "axm.sticker-clearance-contact/v0.1"
ASSEMBLY_SCHEMA = "axm.sticker-assembly-clearance-contact/v0.1"
PLAN_SCHEMA = "axm.design-clearance-plan/v0.1"
WORKSHOP_SCHEMA = "axm.design-clearance-report/v0.1"
MAX_DIRECT_PARTS = 64
MAX_PAIR_REQUESTS = 256
MAX_PAIR_TRIANGLE_PRODUCT = 500_000
MAX_TOTAL_PAIR_TRIANGLE_PRODUCT = 2_000_000
MAX_SOURCE_TRIANGLES = 100_000
MAX_CLASSIFY_SAMPLES = 4096
DEFAULT_TOLERANCE_M = 1e-6

CLEARANCE_OPERATIONS = {
    "inspect-clearance-contact",
    "measure-sticker-clearance-pair",
    "measure-sticker-assembly-clearances",
    "validate-clearance-plan",
    "compare-sketch-clearance",
}


class StickerClearanceContactError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class _ClearanceIssue(RuntimeError):
    def __init__(self, status: str, code: str, message: str):
        super().__init__(message)
        self.status = status
        self.code = code


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _q(value: float) -> float:
    value = round(float(value), 12)
    return 0.0 if value == -0.0 else value


def _number(value: Any, label: str, *, minimum: float = 0.0, maximum: float = 1e3) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise StickerClearanceContactError(f"{label} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise StickerClearanceContactError(f"{label} must be within {minimum}..{maximum}")
    return result


def _vsub(a: list[float] | tuple[float, float, float], b: list[float] | tuple[float, float, float]) -> tuple[float, float, float]:
    return tuple(float(a[i]) - float(b[i]) for i in range(3))


def _vadd(a, b):
    return tuple(float(a[i]) + float(b[i]) for i in range(3))


def _vmul(a, s: float):
    return tuple(float(a[i]) * s for i in range(3))


def _dot(a, b) -> float:
    return sum(float(a[i]) * float(b[i]) for i in range(3))


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])


def _norm2(a) -> float:
    return _dot(a, a)


def _dist2(a, b) -> float:
    return _norm2(_vsub(a, b))


def _bounds_for_triangles(triangles: list[list[list[float]]]) -> dict[str, list[float]]:
    points = [point for triangle in triangles for point in triangle]
    if not points:
        raise _ClearanceIssue("HOLD", "EMPTY_GEOMETRY", "part has no measured triangles")
    return {"min": [min(point[i] for point in points) for i in range(3)],
            "max": [max(point[i] for point in points) for i in range(3)]}


def _aabb_distance(a: dict[str, list[float]], b: dict[str, list[float]]) -> float:
    gaps = []
    for axis in range(3):
        if a["max"][axis] < b["min"][axis]:
            gaps.append(b["min"][axis] - a["max"][axis])
        elif b["max"][axis] < a["min"][axis]:
            gaps.append(a["min"][axis] - b["max"][axis])
        else:
            gaps.append(0.0)
    return math.sqrt(sum(value * value for value in gaps))


def _aabb_overlap_depths(a: dict[str, list[float]], b: dict[str, list[float]]) -> list[float]:
    return [min(a["max"][axis], b["max"][axis]) - max(a["min"][axis], b["min"][axis]) for axis in range(3)]


def _closest_point_triangle(point, triangle):
    # Real-Time Collision Detection, Christer Ericson, closest point on triangle.
    a, b, c = (tuple(row) for row in triangle)
    ab, ac, ap = _vsub(b, a), _vsub(c, a), _vsub(point, a)
    d1, d2 = _dot(ab, ap), _dot(ac, ap)
    if d1 <= 0 and d2 <= 0:
        return a
    bp = _vsub(point, b); d3, d4 = _dot(ab, bp), _dot(ac, bp)
    if d3 >= 0 and d4 <= d3:
        return b
    vc = d1 * d4 - d3 * d2
    if vc <= 0 and d1 >= 0 and d3 <= 0:
        v = d1 / (d1 - d3)
        return _vadd(a, _vmul(ab, v))
    cp = _vsub(point, c); d5, d6 = _dot(ab, cp), _dot(ac, cp)
    if d6 >= 0 and d5 <= d6:
        return c
    vb = d5 * d2 - d1 * d6
    if vb <= 0 and d2 >= 0 and d6 <= 0:
        w = d2 / (d2 - d6)
        return _vadd(a, _vmul(ac, w))
    va = d3 * d6 - d5 * d4
    if va <= 0 and (d4 - d3) >= 0 and (d5 - d6) >= 0:
        bc = _vsub(c, b); w = (d4 - d3) / ((d4 - d3) + (d5 - d6))
        return _vadd(b, _vmul(bc, w))
    denominator = va + vb + vc
    if denominator == 0:
        return a
    v, w = vb / denominator, vc / denominator
    return _vadd(a, _vadd(_vmul(ab, v), _vmul(ac, w)))


def _closest_segment_segment(p1, q1, p2, q2):
    d1, d2, r = _vsub(q1, p1), _vsub(q2, p2), _vsub(p1, p2)
    a, e, f = _dot(d1, d1), _dot(d2, d2), _dot(d2, r)
    eps = 1e-24
    if a <= eps and e <= eps:
        return tuple(p1), tuple(p2)
    if a <= eps:
        s, t = 0.0, max(0.0, min(1.0, f / e))
    else:
        c = _dot(d1, r)
        if e <= eps:
            t, s = 0.0, max(0.0, min(1.0, -c / a))
        else:
            b = _dot(d1, d2); denom = a * e - b * b
            s = max(0.0, min(1.0, (b * f - c * e) / denom)) if abs(denom) > eps else 0.0
            t = (b * s + f) / e
            if t < 0.0:
                t, s = 0.0, max(0.0, min(1.0, -c / a))
            elif t > 1.0:
                t, s = 1.0, max(0.0, min(1.0, (b - c) / a))
    return _vadd(p1, _vmul(d1, s)), _vadd(p2, _vmul(d2, t))


def _segment_triangle_hit(p0, p1, triangle, tolerance: float):
    a, b, c = (tuple(row) for row in triangle)
    direction = _vsub(p1, p0)
    edge1, edge2 = _vsub(b, a), _vsub(c, a)
    h = _cross(direction, edge2); det = _dot(edge1, h)
    scale = max(math.sqrt(_norm2(edge1) * _norm2(edge2) * max(_norm2(direction), 1e-30)), 1e-30)
    if abs(det) <= max(1e-14 * scale, tolerance * 1e-9):
        return None
    inv = 1.0 / det; s = _vsub(p0, a); u = inv * _dot(s, h)
    eps = max(1e-10, tolerance * 1e-4)
    if u < -eps or u > 1.0 + eps:
        return None
    q = _cross(s, edge1); v = inv * _dot(direction, q)
    if v < -eps or u + v > 1.0 + eps:
        return None
    t = inv * _dot(edge2, q)
    if t < -eps or t > 1.0 + eps:
        return None
    t = max(0.0, min(1.0, t))
    return _vadd(p0, _vmul(direction, t))


def _triangle_distance(first, second, tolerance: float):
    edges = ((0, 1), (1, 2), (2, 0))
    for i, j in edges:
        hit = _segment_triangle_hit(first[i], first[j], second, tolerance)
        if hit is not None:
            return 0.0, hit, hit
    for i, j in edges:
        hit = _segment_triangle_hit(second[i], second[j], first, tolerance)
        if hit is not None:
            return 0.0, hit, hit
    best = (math.inf, None, None)
    for point in first:
        other = _closest_point_triangle(point, second); d2 = _dist2(point, other)
        if d2 < best[0]: best = (d2, tuple(point), other)
    for point in second:
        other = _closest_point_triangle(point, first); d2 = _dist2(point, other)
        if d2 < best[0]: best = (d2, other, tuple(point))
    for ia, ja in edges:
        for ib, jb in edges:
            pa, pb = _closest_segment_segment(first[ia], first[ja], second[ib], second[jb]); d2 = _dist2(pa, pb)
            if d2 < best[0]: best = (d2, pa, pb)
    return math.sqrt(max(0.0, best[0])), best[1], best[2]


def _source_triangles(registry: Registry, definition: dict[str, Any], placed: dict[str, Any], cache: dict[str, Any]) -> dict[str, Any]:
    if definition["adapter"] != GLB:
        raise _ClearanceIssue("HOLD", "UNSUPPORTED_ADAPTER", "clearance/contact currently requires rigid GLB assembly leaves")
    try:
        recipe = resolve(definition, placed)
    except (TypeError, ValueError) as exc:
        raise _ClearanceIssue("FAIL", "INVALID_INSTANCE", str(exc)) from exc
    if recipe != {"model": "model"} or "model" not in definition.get("assets", {}):
        raise _ClearanceIssue("HOLD", "UNSUPPORTED_RECIPE", "clearance/contact requires the ordinary rigid GLB model recipe")
    reference = definition["assets"]["model"]
    if reference in cache:
        return cache[reference]
    try:
        raw = registry.asset(reference); GamePoseAsset(raw); document, binary = _parse(raw)
        if document.get("skins"):
            raise _ClearanceIssue("HOLD", "SKINNED_GEOMETRY", "skinned leaves are outside rest-pose rigid clearance v0.1")
        animation_count = len(document.get("animations", [])) if isinstance(document.get("animations", []), list) else 0
        glb = _GLB(_encode_geometry_view(document, binary)); doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene"); roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")
        stack = [(node, GLTF_IDENTITY) for node in reversed(roots)]; seen = set(); triangles = []
        while stack:
            node_index, parent = stack.pop(); node = _at(doc.get("nodes"), node_index, "node")
            if node_index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(node_index)
            if len(seen) > 10000:
                raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds node limit", hold=True)
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_NODE", "skinned, weighted or extended nodes require another observer", hold=True)
            world = gltf_multiply(parent, _local(node)); children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend((child, world) for child in reversed(children))
            if "mesh" not in node: continue
            mesh = _at(doc.get("meshes"), node["mesh"], "mesh")
            for primitive in mesh.get("primitives", []):
                if primitive.get("mode", 4) != 4 or primitive.get("targets") or primitive.get("extensions"):
                    raise GeometryIssue("UNSUPPORTED_PRIMITIVE", "clearance/contact requires ordinary TRIANGLES primitives", hold=True)
                attributes = primitive.get("attributes", {})
                positions = glb.accessor(attributes.get("POSITION"), True)
                indices = ([row[0] for row in glb.accessor(primitive["indices"], False)] if "indices" in primitive else list(range(len(positions))))
                if len(indices) % 3 or any(index >= len(positions) for index in indices):
                    raise GeometryIssue("INVALID_TRIANGLES", "incomplete triangle or out-of-range vertex index")
                transformed = [gltf_point(world, position) for position in positions]
                for offset in range(0, len(indices), 3):
                    tri = [transformed[index] for index in indices[offset:offset + 3]]
                    u, v = _vsub(tri[1], tri[0]), _vsub(tri[2], tri[0])
                    if math.sqrt(_norm2(_cross(u, v))) <= 1e-12:
                        raise _ClearanceIssue("HOLD", "DEGENERATE_TRIANGLE", "source contains a degenerate triangle at clearance resolution")
                    triangles.append(tri)
                    if len(triangles) > min(MAX_TRIANGLES, MAX_SOURCE_TRIANGLES):
                        raise _ClearanceIssue("HOLD", "RESOURCE_LIMIT", "source exceeds clearance triangle limit")
        if not triangles:
            raise _ClearanceIssue("HOLD", "EMPTY_GEOMETRY", "source has no rendered triangles")
        row = {"asset": reference, "triangles": triangles, "animation_clips_ignored": animation_count}
        cache[reference] = row
        return row
    except _ClearanceIssue:
        raise
    except GeometryIssue as exc:
        raise _ClearanceIssue("HOLD" if exc.hold else "FAIL", exc.code, str(exc)) from exc
    except (TypeError, ValueError, KeyError, IndexError, AttributeError, struct.error, OverflowError, RecursionError) as exc:
        raise _ClearanceIssue("FAIL", "INVALID_GEOMETRY", str(exc)) from exc


def _assembly_parts(registry: Registry, assembly_pin_raw: Any) -> tuple[dict[str, Any], dict[str, dict[str, Any]]]:
    pin = _pin(assembly_pin_raw, "assembly"); definition = _exact_definition(registry, pin)
    if definition["adapter"] != ASSEMBLY:
        raise StickerClearanceContactError("clearance/contact requires an exact 3D assembly sticker")
    try:
        records = expand(registry, definition)
    except (TypeError, ValueError) as exc:
        raise StickerClearanceContactError("assembly cannot be expanded exactly") from exc
    children = definition.get("recipe", {}).get("children")
    if not isinstance(children, list) or not 2 <= len(children) <= MAX_DIRECT_PARTS:
        raise StickerClearanceContactError(f"assembly clearance requires 2..{MAX_DIRECT_PARTS} direct parts")
    parts = {child["instance"]["id"]: {"id": child["instance"]["id"], "triangles": [], "source_assets": set(),
                                                "animation_clips_ignored": 0, "selected_source_clips": set(), "issues": []}
             for child in children}
    holder_world: dict[int, list[float]] = {}; cache: dict[str, Any] = {}; triangle_visits = 0
    for index, record in enumerate(records):
        parent = record["parent"]; parent_holder = identity() if parent is None else holder_world[parent]
        try:
            socket = multiply(parent_holder, list(rigid(record["target"]["frame"])))
            local_holder = attachment_matrix(record["definition"], record["instance"],
                                             {"space": "3d", "socket": record["target"]["socket"], "frame": identity()})
        except (TypeError, ValueError, KeyError) as exc:
            raise StickerClearanceContactError("assembly contains an invalid 3D placement", {"path": record.get("path")}) from exc
        holder_world[index] = multiply(socket, local_holder)
        segments = str(record["path"]).split("/")
        if record["definition"]["adapter"] == ASSEMBLY or len(segments) < 2:
            continue
        key = segments[1]
        if key not in parts: continue
        row = parts[key]
        if record.get("clip") is not None: row["selected_source_clips"].add(str(record["clip"]))
        try:
            source = _source_triangles(registry, record["definition"], record["instance"], cache)
            row["source_assets"].add(source["asset"]); row["animation_clips_ignored"] += source["animation_clips_ignored"]
            for triangle in source["triangles"]:
                row["triangles"].append([_flat_point(holder_world[index], point) for point in triangle]); triangle_visits += 1
                if triangle_visits > MAX_SOURCE_TRIANGLES:
                    raise _ClearanceIssue("HOLD", "RESOURCE_LIMIT", "assembly exceeds clearance transformed-triangle limit")
        except _ClearanceIssue as exc:
            row["issues"].append({"status": exc.status, "code": exc.code, "path": record["path"], "message": str(exc)})
    finished = {}
    for key, row in parts.items():
        row["source_assets"] = sorted(row["source_assets"]); row["selected_source_clips"] = sorted(row["selected_source_clips"])
        row["status"] = ("FAIL" if any(issue["status"] == "FAIL" for issue in row["issues"])
                         else "HOLD" if row["issues"] or not row["triangles"] else "PASS")
        if row["triangles"]: row["bounds_m"] = _bounds_for_triangles(row["triangles"])
        finished[key] = row
    return pin, finished


def _weld_surface(triangles: list[list[list[float]]], tolerance: float):
    scale = 1.0 / max(tolerance, 1e-9); vertices = []; lookup = {}; faces = []
    for triangle in triangles:
        face = []
        for point in triangle:
            key = tuple(round(float(value) * scale) for value in point)
            if key not in lookup:
                lookup[key] = len(vertices); vertices.append(tuple(float(value) for value in point))
            face.append(lookup[key])
        faces.append(tuple(face))
    return ClosedTriangleSurface(vertices, faces, tolerance_m=max(tolerance, 1e-7)), vertices


def _inside_witness(source: dict[str, Any], target: dict[str, Any], tolerance: float):
    try:
        surface, _ = _weld_surface(target["triangles"], tolerance)
    except ValueError as exc:
        return None, {"status": "HOLD", "reason": f"target is not proven as a welded closed non-self-intersecting surface: {exc}"}
    samples = []
    for triangle in source["triangles"]:
        samples.extend(tuple(point) for point in triangle)
        samples.append(tuple(sum(point[axis] for point in triangle) / 3.0 for axis in range(3)))
        if len(samples) >= MAX_CLASSIFY_SAMPLES: break
    seen = set()
    for sample in samples[:MAX_CLASSIFY_SAMPLES]:
        key = tuple(round(value, 12) for value in sample)
        if key in seen: continue
        seen.add(key)
        result = surface.classify(sample)
        if result == "inside":
            return list(sample), {"status": "PASS", "classification": "inside"}
        if result == "hold":
            return None, {"status": "HOLD", "reason": "closed-surface point classification reached tolerance ambiguity"}
    return None, {"status": "PASS", "classification": "no sampled inside witness"}


def _measure_pair(parts: dict[str, dict[str, Any]], part_a: str, part_b: str, tolerance: float) -> dict[str, Any]:
    if part_a == part_b or part_a not in parts or part_b not in parts:
        raise StickerClearanceContactError("clearance pair requires two distinct existing direct part ids")
    a, b = parts[part_a], parts[part_b]
    if a["status"] != "PASS" or b["status"] != "PASS":
        return {"status": "HOLD", "relation": "UNMEASURED", "part_a": part_a, "part_b": part_b,
                "reason": "both parts require complete rigid triangle geometry", "part_statuses": {part_a: a["status"], part_b: b["status"]}}
    product = len(a["triangles"]) * len(b["triangles"])
    if product > MAX_PAIR_TRIANGLE_PRODUCT:
        return {"status": "HOLD", "relation": "UNMEASURED", "part_a": part_a, "part_b": part_b,
                "reason": "triangle-pair narrow phase exceeds bounded work limit", "triangle_pair_product": product}
    broad_distance = _aabb_distance(a["bounds_m"], b["bounds_m"]); depths = _aabb_overlap_depths(a["bounds_m"], b["bounds_m"])
    best_distance = math.inf; best_a = best_b = None; tested = 0; pruned = 0
    for ta in a["triangles"]:
        ba = _bounds_for_triangles([ta])
        for tb in b["triangles"]:
            lower = _aabb_distance(ba, _bounds_for_triangles([tb]))
            if lower > best_distance:
                pruned += 1; continue
            tested += 1
            distance, ca, cb = _triangle_distance(ta, tb, tolerance)
            if distance < best_distance:
                best_distance, best_a, best_b = distance, ca, cb
                if best_distance <= tolerance: best_distance = 0.0
    if best_a is None or best_b is None:
        return {"status": "HOLD", "relation": "UNMEASURED", "part_a": part_a, "part_b": part_b, "reason": "narrow phase produced no witness"}

    witness_a, classify_a = _inside_witness(a, b, tolerance)
    witness_b, classify_b = _inside_witness(b, a, tolerance)
    inside = ({"inside_part": part_a, "container_part": part_b, "point": witness_a} if witness_a is not None else
              {"inside_part": part_b, "container_part": part_a, "point": witness_b} if witness_b is not None else None)
    if inside is not None:
        relation = "PENETRATING"; clearance = 0.0; certainty = "PASS"
    elif best_distance > tolerance:
        relation = "SEPARATED"; clearance = best_distance; certainty = "PASS"
    else:
        tangent_bounds = all(value >= -tolerance for value in depths) and any(abs(value) <= tolerance for value in depths)
        classifications_complete = classify_a["status"] == classify_b["status"] == "PASS"
        if tangent_bounds and classifications_complete:
            relation = "TOUCHING"; clearance = 0.0; certainty = "PASS"
        else:
            relation = "CONTACT_OR_INTERSECTION"; clearance = 0.0; certainty = "HOLD"
    return {
        "status": certainty,
        "relation": relation,
        "part_a": part_a,
        "part_b": part_b,
        "units": "m",
        "clearance_m": _q(clearance),
        "surface_distance_m": _q(best_distance),
        "closest_point_a_m": [_q(v) for v in best_a],
        "closest_point_b_m": [_q(v) for v in best_b],
        "penetration_witness": inside,
        "broad_phase": {"aabb_distance_lower_bound_m": _q(broad_distance),
                         "aabb_overlap": all(value >= -tolerance for value in depths),
                         "axis_overlap_depths_m": [_q(value) for value in depths]},
        "narrow_phase": {"triangle_pair_product": product, "triangle_pairs_tested": tested, "triangle_pairs_pruned": pruned},
        "inside_classification": {part_a: classify_a, part_b: classify_b},
        "tolerance_m": tolerance,
    }


def measure_sticker_clearance_pair(registry: Registry, assembly_pin_raw: Any, part_a: str, part_b: str, *, tolerance_m: float = DEFAULT_TOLERANCE_M) -> dict[str, Any]:
    tolerance = _number(tolerance_m, "tolerance_m", minimum=1e-9, maximum=0.01)
    pin, parts = _assembly_parts(registry, assembly_pin_raw)
    pair = _measure_pair(parts, str(part_a), str(part_b), tolerance)
    report = {"schema": PAIR_SCHEMA, "truth_status": "ACTUAL_REST_POSE_TRIANGLE_CLEARANCE_CONTACT_EVIDENCE",
              "assembly": pin, "pair": pair,
              "limitations": [
                  "surface distance is exact only within the supported rigid TRIANGLES subset and bounded pair work",
                  "PENETRATING requires an actual closed-surface inside witness; unresolved zero-distance intersections remain CONTACT_OR_INTERSECTION",
                  "TOUCHING is reserved for zero-distance evidence with tangent broad-phase bounds and no sampled inside witness",
                  "rest/default pose only; no swept animation, physics, strength, manufacturability or aesthetic claim",
              ]}
    report["report_digest"] = _digest(report); return report


def _pair_requests(parts: dict[str, Any], raw: Any) -> list[tuple[str, str]]:
    ids = list(parts)
    if raw is None:
        if len(ids) > MAX_DIRECT_PARTS:
            raise StickerClearanceContactError("too many direct parts for all-pairs scan")
        return [(ids[i], ids[j]) for i in range(len(ids)) for j in range(i + 1, len(ids))]
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_PAIR_REQUESTS:
        raise StickerClearanceContactError(f"pairs must contain 1..{MAX_PAIR_REQUESTS} entries")
    result = []; seen = set()
    for row in raw:
        if not isinstance(row, list) or len(row) != 2 or any(not isinstance(value, str) for value in row):
            raise StickerClearanceContactError("each pair must be [part_a, part_b]")
        a, b = row; key = tuple(sorted((a, b)))
        if a == b or a not in parts or b not in parts or key in seen:
            raise StickerClearanceContactError("pairs must be unique distinct existing direct parts")
        seen.add(key); result.append((a, b))
    return result


def measure_sticker_assembly_clearances(registry: Registry, assembly_pin_raw: Any, *, pairs: Any = None, tolerance_m: float = DEFAULT_TOLERANCE_M) -> dict[str, Any]:
    tolerance = _number(tolerance_m, "tolerance_m", minimum=1e-9, maximum=0.01)
    pin, parts = _assembly_parts(registry, assembly_pin_raw); requests = _pair_requests(parts, pairs)
    total_product = sum(len(parts[a]["triangles"]) * len(parts[b]["triangles"]) for a, b in requests)
    if total_product > MAX_TOTAL_PAIR_TRIANGLE_PRODUCT:
        raise StickerClearanceContactError("requested assembly clearance scan exceeds total bounded triangle-pair work")
    results = [_measure_pair(parts, a, b, tolerance) for a, b in requests]
    status = "FAIL" if any(row["status"] == "FAIL" for row in results) else "HOLD" if any(row["status"] == "HOLD" for row in results) else "PASS"
    report = {"schema": ASSEMBLY_SCHEMA, "truth_status": "BOUNDED_ACTUAL_REST_POSE_ASSEMBLY_CLEARANCE_CONTACT_SCAN",
              "status": status, "assembly": pin, "pair_count": len(results), "pairs": results,
              "part_geometry": [{"id": key, "status": value["status"], "triangles": len(value["triangles"]),
                                  "source_assets": value["source_assets"], "bounds_m": copy.deepcopy(value.get("bounds_m")),
                                  "animation_clips_ignored": value["animation_clips_ignored"]} for key, value in parts.items()],
              "triangle_pair_product": total_product,
              "limitations": ["all-pairs scanning is bounded; callers can request an explicit subset", "rest/default pose only; no swept animation or physics"]}
    report["report_digest"] = _digest(report); return report


def validate_clearance_plan(raw: Any, sketch_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw); required = {"schema", "sketch_digest", "requirements"}; allowed = required | {"plan_digest"}
    if not isinstance(raw, dict) or required - set(raw) or set(raw) - allowed or raw.get("schema") != PLAN_SCHEMA:
        raise StickerClearanceContactError("clearance plan has missing/unsupported fields or schema")
    if raw["sketch_digest"] != sketch["sketch_digest"]:
        raise StickerClearanceContactError("clearance plan does not match exact sketch digest")
    requirements = raw["requirements"]
    if not isinstance(requirements, list) or not 1 <= len(requirements) <= MAX_PAIR_REQUESTS:
        raise StickerClearanceContactError(f"clearance plan requires 1..{MAX_PAIR_REQUESTS} requirements")
    part_ids = {row["id"] for row in sketch["parts"]}; result = []; seen = set()
    for index, row in enumerate(requirements):
        if not isinstance(row, dict) or not {"id", "a", "b", "kind"} <= set(row):
            raise StickerClearanceContactError(f"requirements[{index}] is incomplete")
        kind = row["kind"]
        expected = ({"id", "a", "b", "kind", "minimum_m", "tolerance_m"} if kind == "minimum-clearance" else
                    {"id", "a", "b", "kind", "tolerance_m"} if kind in {"contact", "no-penetration"} else set())
        if not expected or set(row) != expected:
            raise StickerClearanceContactError(f"requirements[{index}] has unsupported kind or fields")
        if not all(isinstance(row[key], str) and row[key] for key in ("id", "a", "b")) or row["a"] == row["b"]:
            raise StickerClearanceContactError("clearance requirement ids/parts must be nonempty and pair parts distinct")
        if row["a"] not in part_ids or row["b"] not in part_ids or row["id"] in seen:
            raise StickerClearanceContactError("clearance requirement references unknown part or duplicate id")
        seen.add(row["id"]); normalized = {"id": row["id"], "a": row["a"], "b": row["b"], "kind": kind,
                                             "tolerance_m": _number(row["tolerance_m"], "requirement tolerance_m", minimum=1e-9, maximum=0.01)}
        if kind == "minimum-clearance":
            normalized["minimum_m"] = _number(row["minimum_m"], "minimum_m", minimum=0.0, maximum=1000.0)
        result.append(normalized)
    normalized = {"schema": PLAN_SCHEMA, "sketch_digest": sketch["sketch_digest"], "requirements": result}
    plan_digest = _digest(normalized)
    if "plan_digest" in raw and raw["plan_digest"] != plan_digest:
        raise StickerClearanceContactError("persisted clearance plan digest does not match normalized body")
    normalized["plan_digest"] = plan_digest; return normalized


def compare_sketch_clearance(registry: Registry, sketch_raw: Any, assembly_pin_raw: Any, plan_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw); plan = validate_clearance_plan(plan_raw, sketch)
    pin, parts = _assembly_parts(registry, assembly_pin_raw); results = []
    for req in plan["requirements"]:
        pair = _measure_pair(parts, req["a"], req["b"], req["tolerance_m"])
        if pair["status"] == "HOLD":
            status = "HOLD"; reason = "pair relation is not resolved strongly enough for this requirement"
        elif req["kind"] == "minimum-clearance":
            if pair["relation"] == "PENETRATING": status = "FAIL"
            else: status = "PASS" if pair["clearance_m"] + req["tolerance_m"] >= req["minimum_m"] else "FAIL"
            reason = "actual rest-pose clearance compared with explicit minimum"
        elif req["kind"] == "contact":
            status = "PASS" if pair["relation"] == "TOUCHING" else "FAIL" if pair["relation"] in {"SEPARATED", "PENETRATING"} else "HOLD"
            reason = "contact requires measured touching without a penetration witness"
        else:
            status = "FAIL" if pair["relation"] == "PENETRATING" else "PASS" if pair["relation"] in {"SEPARATED", "TOUCHING"} else "HOLD"
            reason = "no-penetration requires resolved separated/touching evidence"
        results.append({"id": req["id"], "kind": req["kind"], "status": status, "reason": reason,
                        "requirement": copy.deepcopy(req), "pair": pair})
    statuses = [row["status"] for row in results]; status = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    report = {"schema": WORKSHOP_SCHEMA, "truth_status": "EXACT_SKETCH_BOUND_CLEARANCE_REQUIREMENTS_VS_ACTUAL_REST_POSE_TRIANGLE_GEOMETRY",
              "status": status, "passed": status == "PASS", "assembly": pin, "sketch_digest": sketch["sketch_digest"],
              "plan_digest": plan["plan_digest"], "requirements": results,
              "limitations": ["plan is a companion contract bound to the exact sketch rather than silently extending the sketch schema",
                              "PENETRATING requires an inside witness; unresolved surface intersections hold instead of being guessed",
                              "rest/default pose only; no swept motion, physical response, strength, manufacturability, aesthetics or engine acceptance"]}
    report["report_digest"] = _digest(report); return report


def clearance_summary() -> dict[str, Any]:
    return {"schemas": [PAIR_SCHEMA, ASSEMBLY_SCHEMA, PLAN_SCHEMA, WORKSHOP_SCHEMA], "operations": sorted(CLEARANCE_OPERATIONS),
            "broad_phase": "actual transformed triangle AABBs", "narrow_phase": "triangle-to-triangle minimum distance plus closed-surface inside witness",
            "relations": ["SEPARATED", "TOUCHING", "PENETRATING", "CONTACT_OR_INTERSECTION", "UNMEASURED"],
            "pose": "authored/default rest pose only", "units": "metres",
            "truth_boundary": "numeric geometry/contact evidence only; no swept collision, physics, strength, manufacturability, aesthetic or engine-quality claim"}


def operate_sticker_clearance_contact(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-clearance-contact":
        return {"truth_status": "DECLARED_STICKER_CLEARANCE_CONTACT_V0_1", **clearance_summary()}
    database = inputs.get("database")
    if not isinstance(database, str) or not database.strip():
        raise StickerClearanceContactError("clearance/contact requires a sticker database path")
    path = _resolve_registry_path(root, database)
    if _machine_body(root, path):
        raise StickerClearanceContactError("clearance/contact database must be an ordinary creation path or external path")
    with Registry(path) as registry:
        if operation == "measure-sticker-clearance-pair":
            return measure_sticker_clearance_pair(registry, inputs.get("assembly"), inputs.get("part_a"), inputs.get("part_b"), tolerance_m=inputs.get("tolerance_m", DEFAULT_TOLERANCE_M))
        if operation == "measure-sticker-assembly-clearances":
            return measure_sticker_assembly_clearances(registry, inputs.get("assembly"), pairs=inputs.get("pairs"), tolerance_m=inputs.get("tolerance_m", DEFAULT_TOLERANCE_M))
        if operation == "validate-clearance-plan":
            return {"truth_status": "DETERMINISTIC_CLEARANCE_PLAN_VALIDATION", "plan": validate_clearance_plan(inputs.get("plan"), inputs.get("sketch"))}
        if operation == "compare-sketch-clearance":
            return compare_sketch_clearance(registry, inputs.get("sketch"), inputs.get("assembly"), inputs.get("plan"))
    raise StickerClearanceContactError("clearance/contact operation is unsupported", {"operation": operation})

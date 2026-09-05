"""Read actual static GLB triangles against an explicit spatial contract.

Standard-library only. No renderer, external buffer fetch, physics or admission.
Supported subset follows https://registry.khronos.org/glTF/specs/2.0/glTF-2.0.html
Unsupported deformation/encoding yields HOLD, never a partial PASS.
"""
from __future__ import annotations

import hashlib
import json
import math
import struct
from pathlib import Path
from typing import Any

CONTRACT_SCHEMA = "axm.static-asset-contract/v0.1"
REVIEW_SCHEMA = "axm.static-asset-review/v0.1"
MAX_BYTES = 128 * 1024 * 1024
MAX_ELEMENTS = 2_000_000
MAX_TRIANGLES = 1_000_000
MAX_COVERAGE_PAIRS = 5_000_000
IDENTITY = [[float(i == j) for j in range(4)] for i in range(4)]


class GeometryIssue(ValueError):
    def __init__(self, code: str, message: str, *, hold: bool = False):
        super().__init__(message)
        self.code, self.hold = code, hold


def _number(value: Any) -> bool:
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _vector(value: Any, length: int = 3) -> bool:
    return isinstance(value, list) and len(value) == length and all(_number(x) for x in value)


def _box(value: Any) -> bool:
    return (isinstance(value, dict) and set(value) <= {"min", "max", "name"}
            and _vector(value.get("min")) and _vector(value.get("max"))
            and all(a <= b for a, b in zip(value["min"], value["max"]))
            and ("name" not in value or isinstance(value["name"], str)))


def validate_static_contract(contract: Any) -> dict[str, Any]:
    fields = {"schema", "bounds", "floor_y", "tolerance_m", "max_triangles", "max_primitives",
              "markers", "collision_boxes", "require_root_identity"}
    if not isinstance(contract, dict) or set(contract) - fields or contract.get("schema") != CONTRACT_SCHEMA:
        raise ValueError("invalid static asset contract schema or unknown field")
    tolerance = contract.get("tolerance_m", 0.00001)
    if not _number(tolerance) or not 0 <= tolerance <= .01:
        raise ValueError("tolerance_m must be finite and between 0 and .01 metres")
    if "bounds" in contract and not _box(contract["bounds"]):
        raise ValueError("bounds requires finite ordered min/max XYZ vectors")
    if "floor_y" in contract and not _number(contract["floor_y"]):
        raise ValueError("floor_y must be finite")
    for key in ("max_triangles", "max_primitives"):
        if key in contract and (type(contract[key]) is not int or contract[key] < 1):
            raise ValueError(f"{key} must be a positive integer")
    if "require_root_identity" in contract and type(contract["require_root_identity"]) is not bool:
        raise ValueError("require_root_identity must be boolean")
    markers = contract.get("markers", {})
    if (not isinstance(markers, dict) or len(markers) > 256
            or any(not isinstance(k, str) or not k or not _vector(v) for k, v in markers.items())):
        raise ValueError("markers requires at most 256 named finite XYZ vectors")
    boxes = contract.get("collision_boxes", [])
    if not isinstance(boxes, list) or len(boxes) > 256 or any(not _box(b) for b in boxes):
        raise ValueError("collision_boxes requires at most 256 finite ordered boxes")
    if "collision_boxes" in contract and not boxes:
        raise ValueError("an explicit collision_boxes list must not be empty")
    return json.loads(json.dumps(contract, allow_nan=False))


def _integer(value: Any, name: str, minimum: int = 0) -> int:
    if type(value) is not int or value < minimum:
        raise GeometryIssue("INVALID_STRUCTURE", f"{name} must be an integer >= {minimum}")
    return value


def _at(rows: Any, index: Any, kind: str) -> dict[str, Any]:
    i = _integer(index, kind + " index")
    if not isinstance(rows, list) or i >= len(rows) or not isinstance(rows[i], dict):
        raise GeometryIssue("INVALID_REFERENCE", f"invalid {kind} reference {i}")
    return rows[i]


def _multiply(a: list, b: list) -> list:
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)] for i in range(4)]


def _local(node: dict) -> list:
    if "matrix" in node:
        if any(key in node for key in ("translation", "rotation", "scale")) or not _vector(node["matrix"], 16):
            raise GeometryIssue("INVALID_TRANSFORM", "matrix must be finite and cannot coexist with TRS")
        m = [[node["matrix"][j * 4 + i] for j in range(4)] for i in range(4)]
        if m[3] != [0, 0, 0, 1]:
            raise GeometryIssue("INVALID_TRANSFORM", "node matrix must be affine")
        return m
    t, q, s = node.get("translation", [0, 0, 0]), node.get("rotation", [0, 0, 0, 1]), node.get("scale", [1, 1, 1])
    if not _vector(t) or not _vector(q, 4) or not _vector(s) or abs(sum(x*x for x in q) - 1) > .00001:
        raise GeometryIssue("INVALID_TRANSFORM", "TRS must be finite with a unit quaternion")
    x, y, z, w = q
    r = [[1-2*(y*y+z*z), 2*(x*y-z*w), 2*(x*z+y*w)],
         [2*(x*y+z*w), 1-2*(x*x+z*z), 2*(y*z-x*w)],
         [2*(x*z-y*w), 2*(y*z+x*w), 1-2*(x*x+y*y)]]
    return [[r[i][j]*s[j] for j in range(3)] + [t[i]] for i in range(3)] + [[0, 0, 0, 1]]


def _point(matrix: list, point: tuple) -> list:
    p = [sum(matrix[i][j]*point[j] for j in range(3)) + matrix[i][3] for i in range(3)]
    if not all(_number(v) for v in p):
        raise GeometryIssue("NONFINITE_GEOMETRY", "transformed position is not finite")
    return p


class _GLB:
    def __init__(self, raw: bytes):
        if len(raw) < 20 or struct.unpack_from("<4sII", raw) != (b"glTF", 2, len(raw)):
            raise GeometryIssue("INVALID_GLB", "expected a complete GLB v2 container")
        chunks, offset = [], 12
        while offset < len(raw):
            if offset + 8 > len(raw):
                raise GeometryIssue("INVALID_GLB", "truncated chunk header")
            size, kind = struct.unpack_from("<I4s", raw, offset)
            if size % 4 or offset + 8 + size > len(raw):
                raise GeometryIssue("INVALID_GLB", "unaligned or truncated chunk")
            chunks.append((kind, raw[offset+8:offset+8+size])); offset += 8 + size
        if [kind for kind, _ in chunks] != [b"JSON", b"BIN\0"]:
            raise GeometryIssue("UNSUPPORTED_CONTAINER", "requires one JSON chunk followed by one BIN chunk", hold=True)
        self.doc = json.loads(chunks[0][1].decode("utf-8"))
        if not isinstance(self.doc, dict) or self.doc.get("asset", {}).get("version") != "2.0":
            raise GeometryIssue("INVALID_GLB", "requires glTF asset version 2.0")
        self.binary = chunks[1][1]
        buffers = self.doc.get("buffers", [])
        if len(buffers) != 1 or "uri" in buffers[0]:
            raise GeometryIssue("EXTERNAL_BUFFER", "only one embedded buffer is supported; nothing is fetched", hold=True)
        length = _integer(buffers[0].get("byteLength"), "buffer byteLength", 1)
        if not length <= len(self.binary) <= length + 3:
            raise GeometryIssue("INVALID_BUFFER", "BIN length does not match declared buffer")
        self.length = length
        self.decoded_elements = 0
        # Required geometry extensions may alter the meaning of decoded positions.
        allowed = {"KHR_materials_emissive_strength", "KHR_materials_unlit"}
        if set(self.doc.get("extensionsRequired", [])) - allowed:
            raise GeometryIssue("UNSUPPORTED_EXTENSION", "required extension is outside the reviewed subset", hold=True)
        if self.doc.get("animations") or self.doc.get("skins"):
            raise GeometryIssue("DEFORMATION_NOT_REVIEWED", "animation and skin poses need a separate runtime review", hold=True)

    def accessor(self, index: int, position: bool) -> list:
        a = _at(self.doc.get("accessors"), index, "accessor")
        if "sparse" in a or a.get("extensions"):
            raise GeometryIssue("UNSUPPORTED_ACCESSOR", "sparse/extended accessors are not decoded", hold=True)
        formats = {5126: ("f", 4)} if position else {5121: ("B", 1), 5123: ("H", 2), 5125: ("I", 4)}
        expected = "VEC3" if position else "SCALAR"
        if a.get("type") != expected or a.get("componentType") not in formats or a.get("normalized", False):
            raise GeometryIssue("UNSUPPORTED_ACCESSOR", f"requires unnormalized {expected} with supported components", hold=True)
        count = _integer(a.get("count"), "accessor count", 1)
        self.decoded_elements += count
        if count > MAX_ELEMENTS or self.decoded_elements > MAX_ELEMENTS * 2:
            raise GeometryIssue("RESOURCE_LIMIT", "accessor exceeds element limit", hold=True)
        view = _at(self.doc.get("bufferViews"), a.get("bufferView"), "bufferView")
        if view.get("extensions"):
            raise GeometryIssue("UNSUPPORTED_BUFFER_VIEW", "compressed/extended buffer views need their decoder", hold=True)
        if view.get("buffer") != 0:
            raise GeometryIssue("INVALID_REFERENCE", "bufferView must reference embedded buffer 0")
        start = _integer(view.get("byteOffset", 0), "bufferView byteOffset")
        length = _integer(view.get("byteLength"), "bufferView byteLength", 1)
        relative = _integer(a.get("byteOffset", 0), "accessor byteOffset")
        fmt, component = formats[a["componentType"]]; width = 3 if position else 1; packed = width*component
        stride = _integer(view.get("byteStride", packed), "byteStride", packed)
        if (start + length > self.length or relative + (count-1)*stride + packed > length
                or (start+relative) % component or stride % component
                or ("byteStride" in view and (not position or stride % 4 or stride > 252))):
            raise GeometryIssue("INVALID_ACCESSOR_RANGE", "accessor alignment/stride/range exceeds its buffer view")
        decoder = struct.Struct("<" + fmt*width)
        values = [decoder.unpack_from(self.binary, start+relative+i*stride) for i in range(count)]
        if position and any(not all(math.isfinite(v) for v in row) for row in values):
            raise GeometryIssue("NONFINITE_GEOMETRY", "POSITION contains NaN or infinity")
        return values


def _inside(point: list, box: dict, tolerance: float) -> bool:
    return all(lo-tolerance <= p <= hi+tolerance for p, lo, hi in zip(point, box["min"], box["max"]))


def review_static_glb(path: str | Path, contract: Any) -> dict[str, Any]:
    """Review default-scene rigid triangles in world metres; never mutate inputs.

    Collision proof is sufficient/conservative: each whole triangle must fit one
    box. A triangle spanning adjacent boxes can remain unproven even if their
    union covers it. Bounds come from positions, never accessor min/max claims.
    """
    spec = validate_static_contract(contract)
    encoded = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    target = Path(path).resolve()
    result = {"schema": REVIEW_SCHEMA, "status": "HOLD", "artifact_sha256": None,
              "contract_sha256": hashlib.sha256(encoded).hexdigest(), "contract": spec,
              "measurements": {}, "findings": [], "finding_count": 0, "finding_counts": {},
              "scope": "Actual default-scene static GLB positions/indices/transforms. No renderer import, visual-quality, topology, animation, self-collision, gameplay, or automatic adoption proof."}
    def finding(code: str, **details: Any) -> None:
        result["finding_count"] += 1
        result["finding_counts"][code] = result["finding_counts"].get(code, 0) + 1
        if len(result["findings"]) < 32:
            result["findings"].append({"code": code, **details})
    try:
        with target.open("rb") as stream:
            raw = stream.read(MAX_BYTES+1)
        if len(raw) > MAX_BYTES:
            raise GeometryIssue("RESOURCE_LIMIT", "GLB exceeds 128MiB limit", hold=True)
        result["artifact_sha256"] = hashlib.sha256(raw).hexdigest()
        glb = _GLB(raw); doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise GeometryIssue("EMPTY_SCENE", "default scene has no roots")
        stack = [(i, IDENTITY, True) for i in reversed(roots)]
        seen, named, bounds, total, primitives = set(), {}, None, 0, 0
        tolerance = spec.get("tolerance_m", .00001); boxes = spec.get("collision_boxes", [])
        uncovered, degenerate, outside, pairs = 0, 0, 0, 0
        while stack:
            index, parent, is_root = stack.pop(); node = _at(doc.get("nodes"), index, "node")
            if index in seen:
                raise GeometryIssue("INVALID_NODE_GRAPH", "cycle or multiple-parent/default-root reference")
            seen.add(index)
            if len(seen) > 10000:
                raise GeometryIssue("RESOURCE_LIMIT", "scene exceeds node limit", hold=True)
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise GeometryIssue("UNSUPPORTED_NODE", "skinned, weighted or extended nodes require separate review", hold=True)
            local = _local(node); world = _multiply(parent, local)
            if is_root and spec.get("require_root_identity") and any(abs(local[i][j]-IDENTITY[i][j]) > tolerance for i in range(4) for j in range(4)):
                finding("ROOT_TRANSFORM", node=index, name=node.get("name"))
            if node.get("name"):
                named.setdefault(node["name"], []).append(_point(world, (0, 0, 0)))
            children = node.get("children", [])
            if not isinstance(children, list):
                raise GeometryIssue("INVALID_NODE_GRAPH", "node children must be an array")
            stack.extend((child, world, False) for child in reversed(children))
            if "mesh" not in node:
                continue
            mesh = _at(doc.get("meshes"), node["mesh"], "mesh")
            if mesh.get("weights"):
                raise GeometryIssue("DEFORMATION_NOT_REVIEWED", "morph weights are outside static review", hold=True)
            for primitive_index, primitive in enumerate(mesh.get("primitives", [])):
                if primitive.get("mode", 4) != 4 or primitive.get("targets") or primitive.get("extensions"):
                    raise GeometryIssue("UNSUPPORTED_PRIMITIVE", "requires ordinary rigid TRIANGLES primitives", hold=True)
                positions = glb.accessor(primitive.get("attributes", {}).get("POSITION"), True)
                indices = ([v[0] for v in glb.accessor(primitive["indices"], False)] if "indices" in primitive else list(range(len(positions))))
                if len(indices) % 3 or any(v >= len(positions) for v in indices):
                    raise GeometryIssue("INVALID_TRIANGLES", "incomplete triangle or out-of-range vertex index")
                total += len(indices)//3; primitives += 1; pairs += len(indices)//3*len(boxes)
                if total > MAX_TRIANGLES or pairs > MAX_COVERAGE_PAIRS:
                    raise GeometryIssue("RESOURCE_LIMIT", "triangle/box proof exceeds bounded work limit", hold=True)
                points = [_point(world, p) for p in positions]
                for offset in range(0, len(indices), 3):
                    tri = [points[i] for i in indices[offset:offset+3]]
                    context = {"node": index, "name": node.get("name"), "primitive": primitive_index, "triangle": offset//3}
                    for point in tri:
                        if bounds is None:
                            bounds = {"min": point.copy(), "max": point.copy()}
                        else:
                            bounds["min"] = [min(a,b) for a,b in zip(bounds["min"], point)]
                            bounds["max"] = [max(a,b) for a,b in zip(bounds["max"], point)]
                    u, v = ([tri[j][i]-tri[0][i] for i in range(3)] for j in (1,2))
                    cross = [u[1]*v[2]-u[2]*v[1], u[2]*v[0]-u[0]*v[2], u[0]*v[1]-u[1]*v[0]]
                    if not all(math.isfinite(x) for x in cross):
                        raise GeometryIssue("NONFINITE_GEOMETRY", "triangle arithmetic overflow")
                    if math.hypot(*cross) <= 1e-12:
                        degenerate += 1; finding("DEGENERATE_TRIANGLE", **context)
                    if "bounds" in spec and not all(_inside(p, spec["bounds"], tolerance) for p in tri):
                        outside += 1; finding("OUTSIDE_ENVELOPE", **context)
                    if boxes and not any(all(_inside(p, b, tolerance) for p in tri) for b in boxes):
                        uncovered += 1; finding("COLLISION_COVERAGE_UNPROVEN", **context)
        if bounds is None or total == 0:
            raise GeometryIssue("EMPTY_GEOMETRY", "default scene has no rendered triangles")
        if "floor_y" in spec and abs(bounds["min"][1]-spec["floor_y"]) > tolerance:
            finding("FLOOR_CONTACT", actual_min_y=bounds["min"][1], expected_y=spec["floor_y"])
        for key, actual in (("max_triangles", total), ("max_primitives", primitives)):
            if key in spec and actual > spec[key]:
                finding("BUDGET_EXCEEDED", field=key, actual=actual, maximum=spec[key])
        markers = {}
        for name, expected in spec.get("markers", {}).items():
            matches = named.get(name, [])
            if len(matches) != 1:
                finding("MARKER_IDENTITY", name=name, matches=len(matches)); continue
            error = math.dist(matches[0], expected); markers[name] = {"actual": matches[0], "error_m": error}
            if error > tolerance:
                finding("MARKER_POSITION", name=name, actual=matches[0], expected=expected, error_m=error)
        result["measurements"] = {"bounds": bounds, "triangles": total, "primitives": primitives,
                                  "nodes": len(seen), "markers": markers, "degenerate_triangles": degenerate,
                                  "outside_envelope_triangles": outside,
                                  "collision_triangles_tested": total if boxes else 0, "collision_triangles_unproven": uncovered}
        result["status"] = "FAIL" if result["finding_count"] else "PASS"
    except GeometryIssue as exc:
        finding(exc.code, message=str(exc)); result["status"] = "HOLD" if exc.hold else "FAIL"
    except (OSError, ValueError, TypeError, KeyError, IndexError, AttributeError, struct.error, OverflowError, RecursionError) as exc:
        finding("INVALID_INPUT", message=str(exc)); result["status"] = "FAIL"
    return result

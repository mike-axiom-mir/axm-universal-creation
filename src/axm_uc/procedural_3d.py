from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any

from .atomic import atomic_write_bytes


GLB_MAGIC = b"glTF"
GLB_VERSION = 2
JSON_CHUNK = 0x4E4F534A
BIN_CHUNK = 0x004E4942
SPEC_SCHEMA = "axm.procedural-3d/v0.1"
MAX_PRIMITIVES = 128
MAX_CYLINDER_SEGMENTS = 64
MAX_REPLACED_FILE_BYTES = 64 * 1024 * 1024
_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")


class Procedural3DError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def procedural_3d_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_BOUNDED_DETERMINISTIC_GLB_GENERATION",
        "schema": SPEC_SCHEMA,
        "container": "glTF 2.0 binary GLB",
        "primitive_grammar": ["box", "pyramid", "cylinder"],
        "maximum_primitives": MAX_PRIMITIVES,
        "maximum_cylinder_segments": MAX_CYLINDER_SEGMENTS,
        "materials": "base-color metallic-roughness only",
        "container_and_buffer_ranges_reverified_after_publish": True,
        "rendered_appearance_or_host_compatibility_proven": False,
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
        raise Procedural3DError("3D specification must be finite JSON data") from exc


def _object(raw: Any, label: str, *, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise Procedural3DError(f"{label} must be an object")
    optional = optional or set()
    missing = sorted(required - set(raw))
    unexpected = sorted(set(raw) - required - optional)
    if missing or unexpected:
        raise Procedural3DError(
            f"{label} fields do not match the bounded grammar",
            {"label": label, "missing_fields": missing, "unexpected_fields": unexpected},
        )
    return raw


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise Procedural3DError(f"{label} must be a finite number")
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        raise Procedural3DError(f"{label} must be from {minimum} through {maximum}")
    return result


def _vector3(value: Any, label: str, minimum: float, maximum: float) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise Procedural3DError(f"{label} must contain exactly three numbers")
    return [_number(item, f"{label}[{index}]", minimum, maximum) for index, item in enumerate(value)]


def _color(value: Any, label: str) -> tuple[str, list[float]]:
    if not isinstance(value, str) or len(value) not in {7, 9} or not value.startswith("#"):
        raise Procedural3DError(f"{label} must be #RRGGBB or #RRGGBBAA")
    try:
        channels = [int(value[index:index + 2], 16) for index in range(1, len(value), 2)]
    except ValueError as exc:
        raise Procedural3DError(f"{label} must be #RRGGBB or #RRGGBBAA") from exc
    if len(channels) == 3:
        channels.append(255)
    return value.upper(), [channel / 255.0 for channel in channels]


def _normalize_spec(raw: Any) -> dict[str, Any]:
    spec = _object(raw, "specification", required={"schema", "name", "primitives"})
    if spec["schema"] != SPEC_SCHEMA:
        raise Procedural3DError("unsupported 3D specification schema", {"expected": SPEC_SCHEMA})
    if not isinstance(spec["name"], str) or not spec["name"].strip() or len(spec["name"].strip()) > 120:
        raise Procedural3DError("specification.name must be non-empty text up to 120 characters")
    raw_primitives = spec["primitives"]
    if not isinstance(raw_primitives, list) or not 1 <= len(raw_primitives) <= MAX_PRIMITIVES:
        raise Procedural3DError(f"specification.primitives must contain 1 through {MAX_PRIMITIVES} entries")
    seen: set[str] = set()
    primitives: list[dict[str, Any]] = []
    for index, raw_primitive in enumerate(raw_primitives):
        label = f"specification.primitives[{index}]"
        primitive = _object(
            raw_primitive,
            label,
            required={"id", "type", "size", "translation", "material"},
            optional={"segments"},
        )
        primitive_id = primitive["id"]
        if not isinstance(primitive_id, str) or not _ID_RE.fullmatch(primitive_id):
            raise Procedural3DError(f"{label}.id must be a bounded portable identifier")
        if primitive_id in seen:
            raise Procedural3DError("primitive IDs must be unique", {"duplicate_id": primitive_id})
        seen.add(primitive_id)
        kind = primitive["type"]
        if kind not in {"box", "pyramid", "cylinder"}:
            raise Procedural3DError(f"{label}.type must be box, pyramid, or cylinder")
        if kind != "cylinder" and "segments" in primitive:
            raise Procedural3DError(f"{label}.segments is allowed only for cylinders")
        segments = primitive.get("segments", 16)
        if isinstance(segments, bool) or not isinstance(segments, int) or not 3 <= segments <= MAX_CYLINDER_SEGMENTS:
            raise Procedural3DError(
                f"{label}.segments must be an integer from 3 through {MAX_CYLINDER_SEGMENTS}"
            )
        material = _object(
            primitive["material"],
            f"{label}.material",
            required={"color", "metallic", "roughness"},
        )
        color, _rgba = _color(material["color"], f"{label}.material.color")
        primitives.append(
            {
                "id": primitive_id,
                "type": kind,
                "size": _vector3(primitive["size"], f"{label}.size", 0.001, 10_000.0),
                "translation": _vector3(
                    primitive["translation"], f"{label}.translation", -100_000.0, 100_000.0
                ),
                "segments": segments if kind == "cylinder" else None,
                "material": {
                    "color": color,
                    "metallic": _number(material["metallic"], f"{label}.material.metallic", 0.0, 1.0),
                    "roughness": _number(material["roughness"], f"{label}.material.roughness", 0.0, 1.0),
                },
            }
        )
    return {"schema": SPEC_SCHEMA, "name": spec["name"].strip(), "primitives": primitives}


def _quad(
    positions: list[tuple[float, float, float]],
    normals: list[tuple[float, float, float]],
    indices: list[int],
    corners: tuple[tuple[float, float, float], ...],
    normal: tuple[float, float, float],
) -> None:
    start = len(positions)
    positions.extend(corners)
    normals.extend([normal] * 4)
    indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])


def _box_geometry() -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int]]:
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    _quad(positions, normals, indices, ((-.5, -.5, .5), (.5, -.5, .5), (.5, .5, .5), (-.5, .5, .5)), (0., 0., 1.))
    _quad(positions, normals, indices, ((.5, -.5, -.5), (-.5, -.5, -.5), (-.5, .5, -.5), (.5, .5, -.5)), (0., 0., -1.))
    _quad(positions, normals, indices, ((.5, -.5, .5), (.5, -.5, -.5), (.5, .5, -.5), (.5, .5, .5)), (1., 0., 0.))
    _quad(positions, normals, indices, ((-.5, -.5, -.5), (-.5, -.5, .5), (-.5, .5, .5), (-.5, .5, -.5)), (-1., 0., 0.))
    _quad(positions, normals, indices, ((-.5, .5, .5), (.5, .5, .5), (.5, .5, -.5), (-.5, .5, -.5)), (0., 1., 0.))
    _quad(positions, normals, indices, ((-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5), (-.5, -.5, .5)), (0., -1., 0.))
    return positions, normals, indices


def _normal(a: tuple[float, float, float], b: tuple[float, float, float], c: tuple[float, float, float]) -> tuple[float, float, float]:
    ab = (b[0] - a[0], b[1] - a[1], b[2] - a[2])
    ac = (c[0] - a[0], c[1] - a[1], c[2] - a[2])
    cross = (
        ab[1] * ac[2] - ab[2] * ac[1],
        ab[2] * ac[0] - ab[0] * ac[2],
        ab[0] * ac[1] - ab[1] * ac[0],
    )
    length = math.sqrt(sum(component * component for component in cross))
    return tuple(component / length for component in cross)


def _pyramid_geometry() -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int]]:
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    _quad(positions, normals, indices, ((-.5, -.5, -.5), (.5, -.5, -.5), (.5, -.5, .5), (-.5, -.5, .5)), (0., -1., 0.))
    sides = [
        ((-.5, -.5, .5), (.5, -.5, .5), (0., .5, 0.)),
        ((.5, -.5, -.5), (-.5, -.5, -.5), (0., .5, 0.)),
        ((.5, -.5, .5), (.5, -.5, -.5), (0., .5, 0.)),
        ((-.5, -.5, -.5), (-.5, -.5, .5), (0., .5, 0.)),
    ]
    for side in sides:
        start = len(positions)
        positions.extend(side)
        normals.extend([_normal(*side)] * 3)
        indices.extend([start, start + 1, start + 2])
    return positions, normals, indices


def _cylinder_geometry(segments: int) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int]]:
    positions: list[tuple[float, float, float]] = []
    normals: list[tuple[float, float, float]] = []
    indices: list[int] = []
    for index in range(segments):
        a0 = 2.0 * math.pi * index / segments
        a1 = 2.0 * math.pi * (index + 1) / segments
        p0 = (math.cos(a0) * .5, -.5, math.sin(a0) * .5)
        p1 = (math.cos(a1) * .5, -.5, math.sin(a1) * .5)
        p2 = (p1[0], .5, p1[2])
        p3 = (p0[0], .5, p0[2])
        start = len(positions)
        positions.extend([p0, p1, p2, p3])
        normals.extend([
            (math.cos(a0), 0., math.sin(a0)),
            (math.cos(a1), 0., math.sin(a1)),
            (math.cos(a1), 0., math.sin(a1)),
            (math.cos(a0), 0., math.sin(a0)),
        ])
        indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])
        top = len(positions)
        positions.extend([(0., .5, 0.), p3, p2])
        normals.extend([(0., 1., 0.)] * 3)
        indices.extend([top, top + 1, top + 2])
        bottom = len(positions)
        positions.extend([(0., -.5, 0.), p1, p0])
        normals.extend([(0., -1., 0.)] * 3)
        indices.extend([bottom, bottom + 1, bottom + 2])
    return positions, normals, indices


def _geometry(kind: str, segments: int | None) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]], list[int]]:
    if kind == "box":
        return _box_geometry()
    if kind == "pyramid":
        return _pyramid_geometry()
    return _cylinder_geometry(int(segments or 16))


def build_glb(raw: Any) -> dict[str, Any]:
    spec = _normalize_spec(raw)
    spec_digest = hashlib.sha256(_canonical(spec)).hexdigest()
    binary = bytearray()
    buffer_views: list[dict[str, Any]] = []
    accessors: list[dict[str, Any]] = []
    meshes: list[dict[str, Any]] = []
    materials: list[dict[str, Any]] = []
    nodes: list[dict[str, Any]] = []

    def append_buffer(data: bytes, *, target: int) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(data)
        index = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data), "target": target})
        return index

    for primitive in spec["primitives"]:
        positions, normals, indices = _geometry(primitive["type"], primitive["segments"])
        position_data = b"".join(struct.pack("<fff", *position) for position in positions)
        normal_data = b"".join(struct.pack("<fff", *normal) for normal in normals)
        index_data = b"".join(struct.pack("<H", index) for index in indices)
        position_view = append_buffer(position_data, target=34962)
        normal_view = append_buffer(normal_data, target=34962)
        index_view = append_buffer(index_data, target=34963)
        position_accessor = len(accessors)
        accessors.append({
            "bufferView": position_view,
            "componentType": 5126,
            "count": len(positions),
            "type": "VEC3",
            "min": [min(row[axis] for row in positions) for axis in range(3)],
            "max": [max(row[axis] for row in positions) for axis in range(3)],
        })
        normal_accessor = len(accessors)
        accessors.append({"bufferView": normal_view, "componentType": 5126, "count": len(normals), "type": "VEC3"})
        index_accessor = len(accessors)
        accessors.append({
            "bufferView": index_view,
            "componentType": 5123,
            "count": len(indices),
            "type": "SCALAR",
            "min": [min(indices)],
            "max": [max(indices)],
        })
        _color_text, rgba = _color(primitive["material"]["color"], "material.color")
        material_index = len(materials)
        materials.append({
            "name": f"{primitive['id']}-material",
            "pbrMetallicRoughness": {
                "baseColorFactor": rgba,
                "metallicFactor": primitive["material"]["metallic"],
                "roughnessFactor": primitive["material"]["roughness"],
            },
        })
        mesh_index = len(meshes)
        meshes.append({
            "name": primitive["id"],
            "primitives": [{
                "attributes": {"POSITION": position_accessor, "NORMAL": normal_accessor},
                "indices": index_accessor,
                "material": material_index,
                "mode": 4,
            }],
        })
        nodes.append({
            "name": primitive["id"],
            "mesh": mesh_index,
            "translation": primitive["translation"],
            "scale": primitive["size"],
        })

    buffer_length = len(binary)
    document = {
        "asset": {"version": "2.0", "generator": "AXM Universal Creation deterministic GLB v0.1"},
        "scene": 0,
        "scenes": [{"name": spec["name"], "nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": buffer_length}],
        "extras": {
            "axmSpecificationSchema": SPEC_SCHEMA,
            "axmSpecificationSha256": spec_digest,
            "axmPrimitiveCount": len(spec["primitives"]),
        },
    }
    json_bytes = _canonical(document)
    json_padded = json_bytes + b" " * ((-len(json_bytes)) % 4)
    binary_padded = bytes(binary) + b"\x00" * ((-len(binary)) % 4)
    total = 12 + 8 + len(json_padded) + 8 + len(binary_padded)
    body = (
        struct.pack("<4sII", GLB_MAGIC, GLB_VERSION, total)
        + struct.pack("<II", len(json_padded), JSON_CHUNK)
        + json_padded
        + struct.pack("<II", len(binary_padded), BIN_CHUNK)
        + binary_padded
    )
    return {"specification": spec, "specification_sha256": spec_digest, "document": document, "body": body}


def verify_glb(body: bytes, *, expected_spec_digest: str | None = None) -> dict[str, Any]:
    if len(body) < 28:
        raise Procedural3DError("generated GLB is truncated")
    magic, version, declared_length = struct.unpack("<4sII", body[:12])
    if magic != GLB_MAGIC or version != GLB_VERSION or declared_length != len(body):
        raise Procedural3DError("generated GLB header is invalid")
    offset = 12
    chunks: list[tuple[int, bytes]] = []
    while offset < len(body):
        if offset + 8 > len(body):
            raise Procedural3DError("generated GLB chunk header is truncated")
        length, kind = struct.unpack("<II", body[offset:offset + 8])
        offset += 8
        if length % 4 or offset + length > len(body):
            raise Procedural3DError("generated GLB chunk range is invalid")
        chunks.append((kind, body[offset:offset + length]))
        offset += length
    if offset != len(body) or len(chunks) != 2 or [kind for kind, _ in chunks] != [JSON_CHUNK, BIN_CHUNK]:
        raise Procedural3DError("generated GLB must contain one JSON chunk followed by one BIN chunk")
    try:
        document = json.loads(chunks[0][1].rstrip(b" ").decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise Procedural3DError("generated GLB JSON chunk is invalid") from exc
    if document.get("asset", {}).get("version") != "2.0":
        raise Procedural3DError("generated GLB JSON does not declare glTF 2.0")
    buffers = document.get("buffers")
    if not isinstance(buffers, list) or len(buffers) != 1 or not isinstance(buffers[0].get("byteLength"), int):
        raise Procedural3DError("generated GLB buffer declaration is invalid")
    declared_buffer = buffers[0]["byteLength"]
    bin_bytes = chunks[1][1]
    if declared_buffer < 0 or declared_buffer > len(bin_bytes) or len(bin_bytes) - declared_buffer > 3:
        raise Procedural3DError("generated GLB BIN chunk length is invalid")
    views = document.get("bufferViews")
    accessors = document.get("accessors")
    meshes = document.get("meshes")
    nodes = document.get("nodes")
    materials = document.get("materials")
    if not all(isinstance(value, list) for value in (views, accessors, meshes, nodes, materials)):
        raise Procedural3DError("generated GLB structural collections are invalid")
    for index, view in enumerate(views):
        if not isinstance(view, dict) or view.get("buffer") != 0:
            raise Procedural3DError("generated GLB bufferView is invalid", {"index": index})
        start = view.get("byteOffset", 0)
        length = view.get("byteLength")
        if not isinstance(start, int) or not isinstance(length, int) or start < 0 or length <= 0 or start + length > declared_buffer:
            raise Procedural3DError("generated GLB bufferView exceeds the declared buffer", {"index": index})
    for index, accessor in enumerate(accessors):
        if not isinstance(accessor, dict) or not isinstance(accessor.get("bufferView"), int):
            raise Procedural3DError("generated GLB accessor is invalid", {"index": index})
        if not 0 <= accessor["bufferView"] < len(views) or accessor.get("componentType") not in {5123, 5126}:
            raise Procedural3DError("generated GLB accessor reference or component type is invalid", {"index": index})
        if not isinstance(accessor.get("count"), int) or accessor["count"] <= 0 or accessor.get("type") not in {"SCALAR", "VEC3"}:
            raise Procedural3DError("generated GLB accessor shape is invalid", {"index": index})
    for index, mesh in enumerate(meshes):
        primitives = mesh.get("primitives") if isinstance(mesh, dict) else None
        if not isinstance(primitives, list) or len(primitives) != 1:
            raise Procedural3DError("generated GLB mesh must contain one bounded primitive", {"index": index})
        primitive = primitives[0]
        attributes = primitive.get("attributes", {})
        refs = [attributes.get("POSITION"), attributes.get("NORMAL"), primitive.get("indices")]
        if any(not isinstance(ref, int) or not 0 <= ref < len(accessors) for ref in refs):
            raise Procedural3DError("generated GLB mesh accessor reference is invalid", {"index": index})
        material = primitive.get("material")
        if not isinstance(material, int) or not 0 <= material < len(materials) or primitive.get("mode") != 4:
            raise Procedural3DError("generated GLB mesh material or draw mode is invalid", {"index": index})
    if len(nodes) != len(meshes) or len(materials) != len(meshes):
        raise Procedural3DError("generated GLB primitive, node, mesh, and material counts diverge")
    for index, node in enumerate(nodes):
        if not isinstance(node, dict) or node.get("mesh") != index:
            raise Procedural3DError("generated GLB node-to-mesh mapping is invalid", {"index": index})
        if not all(isinstance(node.get(field), list) and len(node[field]) == 3 for field in ("translation", "scale")):
            raise Procedural3DError("generated GLB node transform is invalid", {"index": index})
    extras = document.get("extras", {})
    digest = extras.get("axmSpecificationSha256") if isinstance(extras, dict) else None
    if expected_spec_digest is not None and digest != expected_spec_digest:
        raise Procedural3DError("generated GLB specification digest does not match the requested body")
    return {
        "format": "glb",
        "passed": True,
        "version": version,
        "chunks": ["JSON", "BIN"],
        "buffer_bytes": declared_buffer,
        "buffer_views": len(views),
        "accessors": len(accessors),
        "primitives": len(meshes),
        "nodes": len(nodes),
        "materials": len(materials),
        "triangles": sum(accessors[mesh["primitives"][0]["indices"]]["count"] // 3 for mesh in meshes),
        "specification_sha256": digest,
    }


def publish_glb(target: Path, specification: Any, *, replace: bool = False) -> dict[str, Any]:
    target = Path(target).resolve()
    if target.suffix.casefold() != ".glb":
        raise Procedural3DError("procedural 3D output path must end in .glb")
    if target.exists() and target.is_dir():
        raise Procedural3DError("procedural 3D output path is an existing directory")
    if target.exists() and not replace:
        raise Procedural3DError("procedural 3D output already exists and replace is false")
    previous = target.read_bytes() if target.exists() else None
    if previous is not None and len(previous) > MAX_REPLACED_FILE_BYTES:
        raise Procedural3DError("existing 3D asset exceeds the bounded rollback size")
    built = build_glb(specification)
    verification = verify_glb(built["body"], expected_spec_digest=built["specification_sha256"])
    try:
        atomic_write_bytes(target, built["body"])
        published = target.read_bytes()
        if published != built["body"]:
            raise Procedural3DError("published GLB bytes differ from the generated body")
        post_publish = verify_glb(published, expected_spec_digest=built["specification_sha256"])
    except Exception:
        if previous is None:
            if target.exists():
                target.unlink()
        else:
            atomic_write_bytes(target, previous)
        raise
    digest = hashlib.sha256(built["body"]).hexdigest()
    return {
        "operation": "glb",
        "truth_status": "VALIDATED_DETERMINISTIC_GLB_ASSET",
        "path": str(target),
        "bytes": len(built["body"]),
        "sha256": digest,
        "specification": built["specification"],
        "specification_sha256": built["specification_sha256"],
        "pre_publish_validation": verification,
        "post_publish_validation": post_publish,
        "published": True,
        "replaced": previous is not None,
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

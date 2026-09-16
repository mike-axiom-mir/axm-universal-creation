from __future__ import annotations

import hashlib
import math
from pathlib import Path
from typing import Any

from .asset_geometry import GeometryIssue, IDENTITY, _GLB, _at, _local, _multiply, _point
from .mesh_topology import MeshTopologyError, inspect_mesh_topology
from .precision_cutter import (
    MAX_HOLE_SEGMENTS,
    _canonical,
    _extrude_profile,
    _normalize_profile,
    _number,
    _round_hole_geometry,
    _surface_specification,
)
from .procedural_3d import Procedural3DError, publish_glb

MESH_CUTTER_SCHEMA = "axm.mesh-precision-cutter/v0.2"
MAX_SOURCE_BYTES = 64 * 1024 * 1024
MAX_SOURCE_TRIANGLES = 131_072
SOURCE_TOLERANCE = 1e-6
EPSILON = 1e-9
_SUPPORTED_AXES = {"x", "y", "z"}
_SUPPORTED_SIDES = {"u-min", "u-max", "v-min", "v-max"}


class MeshPrecisionCutterError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def mesh_precision_cutter_summary() -> dict[str, Any]:
    return {
        "schema": MESH_CUTTER_SCHEMA,
        "truth_status": "LIVE_BOUNDED_EXISTING_MESH_SUBTRACTIVE_GEOMETRY",
        "operations": ["round-through-hole", "box-notch"],
        "source_scope": "one rigid static closed axis-aligned rectangular-prism GLB primitive",
        "principal_cut_axes": sorted(_SUPPORTED_AXES),
        "full_arbitrary_mesh_csg": False,
        "source_mesh_is_observed_before_cut": True,
        "source_topology_is_checked_before_cut": True,
        "output_topology_is_checked_before_publish": True,
    }


def _vec3(value: Any, label: str) -> tuple[float, float, float]:
    if not isinstance(value, list) or len(value) != 3:
        raise MeshPrecisionCutterError(f"{label} must contain exactly three numbers")
    return tuple(
        _number(item, f"{label}[{index}]", -100000.0, 100000.0)
        for index, item in enumerate(value)
    )


def _normalize_expected_digest(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise MeshPrecisionCutterError("expected_source_sha256 must be lowercase SHA-256 text")
    text = value.strip()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise MeshPrecisionCutterError(
            "expected_source_sha256 must be 64 lowercase hexadecimal characters"
        )
    return text


def prepare_mesh_cut(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("mesh cutter specification must be an object")
    required = {"schema", "name", "operation", "axis", "center"}
    optional = {"radius", "segments", "kerf", "side", "span", "depth"}
    missing = required - set(raw)
    extra = set(raw) - required - optional
    if missing or extra:
        raise MeshPrecisionCutterError(
            "mesh cutter fields do not match the bounded grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    if raw["schema"] != MESH_CUTTER_SCHEMA:
        raise MeshPrecisionCutterError("unsupported mesh precision cutter schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise MeshPrecisionCutterError("name must contain 1..120 characters")
    operation = str(raw["operation"]).strip().casefold()
    if operation not in {"round-through-hole", "box-notch"}:
        raise MeshPrecisionCutterError(
            "unsupported existing-mesh cutter operation",
            {"supported": ["box-notch", "round-through-hole"]},
        )
    axis = str(raw["axis"]).strip().casefold()
    if axis not in _SUPPORTED_AXES:
        raise MeshPrecisionCutterError("axis must be x, y, or z")
    center = _vec3(raw["center"], "center")
    kerf = _number(raw.get("kerf", 0.0), "kerf", 0.0, 1000.0)
    normalized: dict[str, Any] = {
        "schema": MESH_CUTTER_SCHEMA,
        "name": name.strip(),
        "operation": operation,
        "axis": axis,
        "center": list(center),
        "kerf": kerf,
    }
    if operation == "round-through-hole":
        if not {"radius", "segments"} <= set(raw) or any(
            key in raw for key in ("side", "span", "depth")
        ):
            raise MeshPrecisionCutterError("round-through-hole requires radius and segments only")
        radius = _number(raw["radius"], "radius", 0.0001, 100000.0)
        segments = raw["segments"]
        if type(segments) is not int or not 8 <= segments <= MAX_HOLE_SEGMENTS:
            raise MeshPrecisionCutterError(
                f"segments must be an integer from 8 through {MAX_HOLE_SEGMENTS}"
            )
        normalized.update({"radius": radius, "segments": segments})
        return normalized

    if not {"side", "span", "depth"} <= set(raw) or any(
        key in raw for key in ("radius", "segments")
    ):
        raise MeshPrecisionCutterError("box-notch requires side, span, and depth only")
    side = str(raw["side"]).strip().casefold()
    if side not in _SUPPORTED_SIDES:
        raise MeshPrecisionCutterError("side must be one of u-min, u-max, v-min, v-max")
    normalized.update(
        {
            "side": side,
            "span": _number(raw["span"], "span", 0.0001, 100000.0),
            "depth": _number(raw["depth"], "depth", 0.0001, 100000.0),
        }
    )
    return normalized


def _hex_channel(value: float, label: str) -> int:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or not 0.0 <= value <= 1.0
    ):
        raise MeshPrecisionCutterError(f"{label} must contain finite values from 0 through 1")
    channel = round(float(value) * 255.0)
    if abs(float(value) - channel / 255.0) > 1e-6:
        raise MeshPrecisionCutterError(
            f"{label} is outside v0.2 exact 8-bit material preservation"
        )
    return channel


def _hex_color(values: Any, label: str, *, alpha: bool) -> str:
    width = 4 if alpha else 3
    if not isinstance(values, list) or len(values) != width:
        raise MeshPrecisionCutterError(f"{label} must contain exactly {width} channels")
    channels = [_hex_channel(value, label) for value in values]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _material_from_primitive(
    doc: dict[str, Any], primitive: dict[str, Any]
) -> tuple[dict[str, Any], str]:
    if "material" not in primitive:
        return {"color": "#FFFFFFFF", "metallic": 1.0, "roughness": 1.0}, "glTF-default"
    material = _at(doc.get("materials"), primitive["material"], "material")
    if any(key in material for key in ("normalTexture", "occlusionTexture", "emissiveTexture")):
        raise MeshPrecisionCutterError(
            "textured source materials are outside v0.2 preservation scope"
        )
    if material.get("alphaMode", "OPAQUE") != "OPAQUE" or material.get("doubleSided", False) is True:
        raise MeshPrecisionCutterError(
            "transparent or double-sided source materials are outside v0.2 scope"
        )
    extensions = material.get("extensions", {})
    if not isinstance(extensions, dict) or set(extensions) - {"KHR_materials_unlit"}:
        raise MeshPrecisionCutterError(
            "source material extensions are outside v0.2 preservation scope"
        )
    if "KHR_materials_unlit" in extensions and extensions["KHR_materials_unlit"] != {}:
        raise MeshPrecisionCutterError("KHR_materials_unlit source declaration is malformed")
    pbr = material.get("pbrMetallicRoughness", {})
    if not isinstance(pbr, dict) or any(
        key in pbr for key in ("baseColorTexture", "metallicRoughnessTexture")
    ):
        raise MeshPrecisionCutterError(
            "textured PBR source materials are outside v0.2 preservation scope"
        )
    color = _hex_color(
        pbr.get("baseColorFactor", [1.0, 1.0, 1.0, 1.0]),
        "baseColorFactor",
        alpha=True,
    )
    metallic = _number(pbr.get("metallicFactor", 1.0), "metallicFactor", 0.0, 1.0)
    roughness = _number(pbr.get("roughnessFactor", 1.0), "roughnessFactor", 0.0, 1.0)
    result: dict[str, Any] = {
        "color": color,
        "metallic": metallic,
        "roughness": roughness,
    }
    emissive = material.get("emissiveFactor", [0.0, 0.0, 0.0])
    emissive_hex = _hex_color(emissive, "emissiveFactor", alpha=False)
    if emissive_hex != "#000000":
        result["emissive"] = emissive_hex
    if "KHR_materials_unlit" in extensions:
        result["unlit"] = True
    return result, "exact-supported-PBR"


def _signed_volume(
    positions: list[tuple[float, float, float]], indices: list[int]
) -> float:
    volume = 0.0
    for offset in range(0, len(indices), 3):
        a, b, c = (positions[indices[offset + index]] for index in range(3))
        cross = (
            b[1] * c[2] - b[2] * c[1],
            b[2] * c[0] - b[0] * c[2],
            b[0] * c[1] - b[1] * c[0],
        )
        volume += (
            a[0] * cross[0] + a[1] * cross[1] + a[2] * cross[2]
        ) / 6.0
    return volume


def _read_source_primitive(source: Path) -> dict[str, Any]:
    source = Path(source).resolve()
    if source.suffix.casefold() != ".glb":
        raise MeshPrecisionCutterError("source_path must end in .glb")
    if not source.is_file() or source.is_symlink():
        raise MeshPrecisionCutterError("source_path must be an existing ordinary GLB file")
    raw = source.read_bytes()
    if len(raw) > MAX_SOURCE_BYTES:
        raise MeshPrecisionCutterError("source GLB exceeds the 64MiB v0.2 cutter limit")
    digest = hashlib.sha256(raw).hexdigest()
    try:
        glb = _GLB(raw)
        doc = glb.doc
        scene = _at(doc.get("scenes"), doc.get("scene", 0), "scene")
        roots = scene.get("nodes", [])
        if not isinstance(roots, list) or not roots:
            raise MeshPrecisionCutterError(
                "source default scene must contain at least one root node"
            )
        stack = [(index, IDENTITY) for index in reversed(roots)]
        seen: set[int] = set()
        candidates: list[dict[str, Any]] = []
        while stack:
            index, parent = stack.pop()
            node = _at(doc.get("nodes"), index, "node")
            if index in seen:
                raise MeshPrecisionCutterError(
                    "source node graph must not contain cycles or multiple parents"
                )
            seen.add(index)
            if len(seen) > 4096:
                raise MeshPrecisionCutterError("source node graph exceeds the v0.2 node limit")
            if "skin" in node or node.get("weights") or node.get("extensions"):
                raise MeshPrecisionCutterError(
                    "skinned, weighted, or extended source nodes are outside v0.2 scope"
                )
            world = _multiply(parent, _local(node))
            children = node.get("children", [])
            if not isinstance(children, list):
                raise MeshPrecisionCutterError("source node children must be an array")
            stack.extend((child, world) for child in reversed(children))
            if "mesh" not in node:
                continue
            mesh = _at(doc.get("meshes"), node["mesh"], "mesh")
            if mesh.get("weights"):
                raise MeshPrecisionCutterError(
                    "morph-weighted source meshes are outside v0.2 scope"
                )
            primitives = mesh.get("primitives", [])
            if not isinstance(primitives, list) or not primitives:
                raise MeshPrecisionCutterError(
                    "source mesh must contain ordinary triangle primitives"
                )
            for primitive in primitives:
                if (
                    primitive.get("mode", 4) != 4
                    or primitive.get("targets")
                    or primitive.get("extensions")
                ):
                    raise MeshPrecisionCutterError(
                        "source requires ordinary rigid TRIANGLES primitives"
                    )
                attributes = primitive.get("attributes", {})
                if not isinstance(attributes, dict) or "POSITION" not in attributes:
                    raise MeshPrecisionCutterError(
                        "source primitive requires POSITION geometry"
                    )
                if set(attributes) - {"POSITION", "NORMAL"}:
                    raise MeshPrecisionCutterError(
                        "v0.2 refuses to silently discard UVs, colors, tangents, joints, or other vertex attributes"
                    )
                positions = [
                    tuple(_point(world, row))
                    for row in glb.accessor(attributes["POSITION"], True)
                ]
                indices = (
                    [row[0] for row in glb.accessor(primitive["indices"], False)]
                    if "indices" in primitive
                    else list(range(len(positions)))
                )
                if (
                    not indices
                    or len(indices) % 3
                    or any(
                        type(value) is not int or not 0 <= value < len(positions)
                        for value in indices
                    )
                ):
                    raise MeshPrecisionCutterError(
                        "source primitive contains invalid triangle indices"
                    )
                if len(indices) // 3 > MAX_SOURCE_TRIANGLES:
                    raise MeshPrecisionCutterError(
                        "source primitive exceeds the v0.2 triangle limit"
                    )
                material, material_mode = _material_from_primitive(doc, primitive)
                candidates.append(
                    {
                        "positions": positions,
                        "indices": indices,
                        "material": material,
                        "material_mode": material_mode,
                        "node_name": node.get("name"),
                        "mesh_name": mesh.get("name"),
                    }
                )
    except GeometryIssue as exc:
        raise MeshPrecisionCutterError(
            f"source GLB is outside the reviewed static subset: {exc}",
            {"code": exc.code, "hold": exc.hold},
        ) from exc

    if len(candidates) != 1:
        raise MeshPrecisionCutterError(
            "v0.2 source cutting requires exactly one mesh primitive in the default scene",
            {"observed_primitives": len(candidates)},
        )
    candidate = candidates[0]
    try:
        topology = inspect_mesh_topology(
            candidate["positions"],
            candidate["indices"],
            weld_tolerance=SOURCE_TOLERANCE,
        )
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if (
        topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        or topology["triangle_component_count"] != 1
    ):
        raise MeshPrecisionCutterError(
            "source mesh must be one closed consistently oriented component",
            {"topology": topology},
        )
    candidate.update(
        {
            "source_sha256": digest,
            "source_bytes": len(raw),
            "topology": topology,
        }
    )
    return candidate


def _recognize_axis_aligned_box(source: dict[str, Any]) -> dict[str, Any]:
    positions = source["positions"]
    indices = source["indices"]
    bounds = [
        (
            min(point[axis] for point in positions),
            max(point[axis] for point in positions),
        )
        for axis in range(3)
    ]
    extents = [high - low for low, high in bounds]
    diagonal = math.sqrt(sum(value * value for value in extents))
    tolerance = max(SOURCE_TOLERANCE, diagonal * 1e-7)
    if any(value <= tolerance for value in extents):
        raise MeshPrecisionCutterError(
            "source rectangular prism must have positive extent on every axis"
        )

    corners: set[tuple[int, int, int]] = set()
    for point in positions:
        corner: list[int] = []
        for axis, value in enumerate(point):
            low, high = bounds[axis]
            if abs(value - low) <= tolerance:
                corner.append(0)
            elif abs(value - high) <= tolerance:
                corner.append(1)
            else:
                raise MeshPrecisionCutterError(
                    "v0.2 source surgery currently requires an axis-aligned rectangular prism"
                )
        corners.add(tuple(corner))
    if len(corners) != 8:
        raise MeshPrecisionCutterError(
            "source prism must expose all eight measured AABB corners",
            {"corner_count": len(corners)},
        )

    faces: set[tuple[int, int]] = set()
    for offset in range(0, len(indices), 3):
        triangle = [positions[indices[offset + index]] for index in range(3)]
        matches: list[tuple[int, int]] = []
        for axis in range(3):
            low, high = bounds[axis]
            if all(abs(point[axis] - low) <= tolerance for point in triangle):
                matches.append((axis, 0))
            if all(abs(point[axis] - high) <= tolerance for point in triangle):
                matches.append((axis, 1))
        if len(matches) != 1:
            raise MeshPrecisionCutterError(
                "source triangles must lie on exactly one measured rectangular-prism face"
            )
        faces.add(matches[0])
    if faces != {(axis, side) for axis in range(3) for side in (0, 1)}:
        raise MeshPrecisionCutterError(
            "source prism does not contain all six measured boundary faces"
        )

    signed_volume = _signed_volume(positions, indices)
    expected_volume = extents[0] * extents[1] * extents[2]
    volume_tolerance = max(expected_volume * 1e-5, tolerance**3 * 100.0)
    if signed_volume <= 0 or abs(signed_volume - expected_volume) > volume_tolerance:
        raise MeshPrecisionCutterError(
            "source prism orientation or enclosed volume does not match its measured box",
            {
                "signed_volume": signed_volume,
                "expected_volume": expected_volume,
                "tolerance": volume_tolerance,
            },
        )

    center = [(low + high) / 2.0 for low, high in bounds]
    return {
        "bounds": {
            "min": [row[0] for row in bounds],
            "max": [row[1] for row in bounds],
        },
        "center": center,
        "extents": extents,
        "signed_volume": signed_volume,
        "box_volume": expected_volume,
        "tolerance": tolerance,
        "all_six_faces_observed": True,
    }


def _to_canonical(
    point: tuple[float, float, float] | list[float],
    center: list[float],
    axis: str,
) -> tuple[float, float, float]:
    dx, dy, dz = (float(point[index]) - center[index] for index in range(3))
    if axis == "y":
        return (dx, dy, dz)
    if axis == "x":
        return (dz, dx, dy)
    return (dy, dz, dx)


def _from_canonical(
    point: tuple[float, float, float], center: list[float], axis: str
) -> tuple[float, float, float]:
    x, y, z = point
    if axis == "y":
        delta = (x, y, z)
    elif axis == "x":
        delta = (y, z, x)
    else:
        delta = (z, x, y)
    return tuple(center[index] + delta[index] for index in range(3))


def _normal_from_canonical(
    normal: tuple[float, float, float], axis: str
) -> tuple[float, float, float]:
    x, y, z = normal
    if axis == "y":
        return (x, y, z)
    if axis == "x":
        return (y, z, x)
    return (z, x, y)


def _canonical_extents(extents: list[float], axis: str) -> tuple[float, float, float]:
    x, y, z = extents
    if axis == "y":
        return (x, y, z)
    if axis == "x":
        return (z, x, y)
    return (y, z, x)


def _notched_profile(
    width: float,
    depth: float,
    *,
    side: str,
    span_center: float,
    requested_span: float,
    requested_depth: float,
    kerf: float,
) -> tuple[list[tuple[float, float]], dict[str, float]]:
    half_width, half_depth = width / 2.0, depth / 2.0
    half_span = requested_span / 2.0 + kerf / 2.0
    effective_depth = requested_depth + kerf / 2.0
    if side.startswith("u-"):
        available_span = depth
        perpendicular = width
    else:
        available_span = width
        perpendicular = depth
    if half_span <= 0 or 2.0 * half_span >= available_span - EPSILON:
        raise MeshPrecisionCutterError(
            "box-notch span must stay strictly inside the selected source edge"
        )
    if effective_depth <= 0 or effective_depth >= perpendicular - EPSILON:
        raise MeshPrecisionCutterError(
            "box-notch depth must leave source material behind"
        )
    span_half_extent = available_span / 2.0
    a, b = span_center - half_span, span_center + half_span
    if a <= -span_half_extent + EPSILON or b >= span_half_extent - EPSILON:
        raise MeshPrecisionCutterError(
            "box-notch center/span would reach a source corner"
        )

    if side == "v-min":
        profile = [
            (-half_width, -half_depth),
            (a, -half_depth),
            (a, -half_depth + effective_depth),
            (b, -half_depth + effective_depth),
            (b, -half_depth),
            (half_width, -half_depth),
            (half_width, half_depth),
            (-half_width, half_depth),
        ]
    elif side == "v-max":
        profile = [
            (-half_width, -half_depth),
            (half_width, -half_depth),
            (half_width, half_depth),
            (b, half_depth),
            (b, half_depth - effective_depth),
            (a, half_depth - effective_depth),
            (a, half_depth),
            (-half_width, half_depth),
        ]
    elif side == "u-max":
        profile = [
            (-half_width, -half_depth),
            (half_width, -half_depth),
            (half_width, a),
            (half_width - effective_depth, a),
            (half_width - effective_depth, b),
            (half_width, b),
            (half_width, half_depth),
            (-half_width, half_depth),
        ]
    else:
        profile = [
            (-half_width, -half_depth),
            (half_width, -half_depth),
            (half_width, half_depth),
            (-half_width, half_depth),
            (-half_width, b),
            (-half_width + effective_depth, b),
            (-half_width + effective_depth, a),
            (-half_width, a),
        ]
    normalized = _normalize_profile([[point[0], point[1]] for point in profile])
    effective_span = 2.0 * half_span
    return normalized, {
        "requested_span": requested_span,
        "effective_span": effective_span,
        "requested_depth": requested_depth,
        "effective_depth": effective_depth,
        "kerf": kerf,
        "removed_area": effective_span * effective_depth,
    }


def build_source_mesh_cut(
    source_path: Path,
    specification: Any,
    *,
    expected_source_sha256: str | None = None,
) -> dict[str, Any]:
    spec = prepare_mesh_cut(specification)
    expected_digest = _normalize_expected_digest(expected_source_sha256)
    source = _read_source_primitive(source_path)
    if expected_digest is not None and source["source_sha256"] != expected_digest:
        raise MeshPrecisionCutterError(
            "source GLB digest does not match expected_source_sha256",
            {"expected": expected_digest, "observed": source["source_sha256"]},
        )
    box = _recognize_axis_aligned_box(source)
    axis = spec["axis"]
    width, thickness, depth = _canonical_extents(box["extents"], axis)
    canonical_center = _to_canonical(tuple(spec["center"]), box["center"], axis)
    if abs(canonical_center[1]) > thickness / 2.0 + box["tolerance"]:
        raise MeshPrecisionCutterError(
            "cut center lies outside the source extent along the selected axis"
        )

    if spec["operation"] == "round-through-hole":
        effective_radius = spec["radius"] + spec["kerf"] / 2.0
        canonical_positions, canonical_normals, indices, inner, _outer = _round_hole_geometry(
            (width, depth),
            (canonical_center[0], canonical_center[2]),
            effective_radius,
            spec["segments"],
            thickness,
        )
        polygon_removed_area = abs(
            0.5
            * sum(
                inner[index][0] * inner[(index + 1) % len(inner)][1]
                - inner[(index + 1) % len(inner)][0] * inner[index][1]
                for index in range(len(inner))
            )
        )
        operation_metrics: dict[str, Any] = {
            "requested_radius": spec["radius"],
            "effective_radius": effective_radius,
            "kerf": spec["kerf"],
            "segments": spec["segments"],
            "polygonized_removed_area": polygon_removed_area,
            "analytic_requested_removed_area": math.pi * spec["radius"] ** 2,
            "analytic_effective_removed_area": math.pi * effective_radius**2,
            "removed_volume": polygon_removed_area * thickness,
        }
    else:
        span_center = (
            canonical_center[2]
            if spec["side"].startswith("u-")
            else canonical_center[0]
        )
        profile, operation_metrics = _notched_profile(
            width,
            depth,
            side=spec["side"],
            span_center=span_center,
            requested_span=spec["span"],
            requested_depth=spec["depth"],
            kerf=spec["kerf"],
        )
        canonical_positions, canonical_normals, indices, top_triangles = _extrude_profile(
            profile, thickness
        )
        operation_metrics["top_surface_triangles"] = top_triangles
        operation_metrics["removed_volume"] = operation_metrics["removed_area"] * thickness

    positions = [
        _from_canonical(point, box["center"], axis) for point in canonical_positions
    ]
    normals = [_normal_from_canonical(normal, axis) for normal in canonical_normals]
    try:
        output_topology = inspect_mesh_topology(
            positions, indices, weld_tolerance=SOURCE_TOLERANCE
        )
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if (
        output_topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        or output_topology["triangle_component_count"] != 1
    ):
        raise MeshPrecisionCutterError(
            "calculated cut output did not remain one closed oriented component",
            {"topology": output_topology},
        )

    output_volume = _signed_volume(positions, indices)
    if output_volume <= 0 or output_volume >= box["box_volume"] - EPSILON:
        raise MeshPrecisionCutterError(
            "calculated subtractive output volume is not strictly smaller than the measured source volume",
            {"source_volume": box["box_volume"], "output_volume": output_volume},
        )

    surface = _surface_specification(
        spec["name"],
        positions,
        normals,
        indices,
        source["material"],
    )
    request_identity = {
        "schema": MESH_CUTTER_SCHEMA,
        "source_sha256": source["source_sha256"],
        "specification": spec,
    }
    return {
        "schema": MESH_CUTTER_SCHEMA,
        "operation": spec["operation"],
        "specification": spec,
        "request_sha256": hashlib.sha256(_canonical(request_identity)).hexdigest(),
        "source": {
            "sha256": source["source_sha256"],
            "bytes": source["source_bytes"],
            "node_name": source["node_name"],
            "mesh_name": source["mesh_name"],
            "material_mode": source["material_mode"],
            "material": source["material"],
            "topology": source["topology"],
            "recognition": box,
        },
        "surface_specification": surface,
        "metrics": {
            "cut_axis": axis,
            "source_volume": box["box_volume"],
            "output_volume": output_volume,
            "removed_volume_by_closed_mesh": box["box_volume"] - output_volume,
            **operation_metrics,
        },
        "output_topology": output_topology,
        "geometry": {"vertices": len(positions), "triangles": len(indices) // 3},
        "truth_boundary": {
            "source_bytes_observed": True,
            "source_topology_checked": True,
            "source_axis_aligned_rectangular_prism_proven_within_v0_2_contract": True,
            "existing_source_geometry_used_to_derive_cut": True,
            "source_file_mutated": False,
            "output_closed_edge_manifold_candidate_checked": True,
            "full_arbitrary_mesh_csg": False,
            "arbitrary_rotated_or_multi_primitive_source": "NOT_SUPPORTED",
            "uv_texture_tangent_or_vertex_color_preservation": "NOT_SUPPORTED_AND_REJECTED",
            "self_intersection": "NOT_PROVEN",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }


def publish_source_mesh_cut(
    source_path: Path,
    target: Path,
    specification: Any,
    *,
    expected_source_sha256: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    target = Path(target).resolve()
    if source_path == target:
        raise MeshPrecisionCutterError(
            "existing-mesh cutter requires distinct source_path and output path"
        )
    built = build_source_mesh_cut(
        source_path,
        specification,
        expected_source_sha256=expected_source_sha256,
    )
    try:
        publication = publish_glb(
            target,
            built["surface_specification"],
            replace=replace,
        )
    except Procedural3DError as exc:
        raise MeshPrecisionCutterError(
            str(exc), getattr(exc, "details", {})
        ) from exc
    observed_source_after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_unchanged = observed_source_after == built["source"]["sha256"]
    return {
        "operation": built["operation"],
        "truth_status": (
            "VALIDATED_EXISTING_MESH_PRECISION_CUT"
            if source_unchanged
            else "HOLD_SOURCE_CHANGED_DURING_PUBLICATION"
        ),
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "source": {
            **built["source"],
            "unchanged_after_publication": source_unchanged,
            "observed_sha256_after_publication": observed_source_after,
        },
        "metrics": built["metrics"],
        "geometry": built["geometry"],
        "source_topology": built["source"]["topology"],
        "output_topology": built["output_topology"],
        "glb_validation": publication["post_publish_validation"],
        "truth_boundary": built["truth_boundary"],
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

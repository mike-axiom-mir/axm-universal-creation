"""Deterministic, renderer-neutral 3D form derivation for game silhouettes.

The input ``axm.surface-3d/v0.1`` mesh stays embedded and unchanged beside the
derived realization.  Controls operate on named components, never material
groups, so every material slice of one part receives the same deformation.
Protected anchors fade deformation to exactly zero at declared contacts/sockets.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import random
from dataclasses import asdict, dataclass
from pathlib import Path

from .atomic import atomic_write_json


FORM_SCHEMA = "axm.game-form-derivation/v0.1"
ROLES = ("body", "armor", "functional", "detail")
HIERARCHY = ("large", "medium", "small")


@dataclass(frozen=True)
class FormStyle:
    name: str
    vertical_scale: float
    taper: float
    functional_scale: float
    armor_scale: float
    asymmetry: float
    large_scale: float
    medium_scale: float
    small_scale: float


FORM_STYLES = (
    FormStyle("realistic", 1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 1.0, 1.0),
    FormStyle("comic-salvage", .86, .12, 1.32, 1.12, .085, 1.08, 1.0, .84),
    FormStyle("heroic-toon", 1.06, .17, 1.24, 1.18, .045, 1.12, 1.0, .80),
    FormStyle("storybook-chunky", .76, -.06, 1.38, 1.10, .065, 1.16, 1.0, .72),
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _vec3(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must have three coordinates")
    return tuple(_number(item, f"{label}[{index}]") for index, item in enumerate(value))


def _style(name):
    for style in FORM_STYLES:
        if style.name == name:
            return style
    raise ValueError(f"unknown game form style: {name}")


def game_form_catalog():
    return {
        "schema": "axm.game-form-styles/v0.1",
        "styles": [asdict(style) for style in FORM_STYLES],
        "roles": list(ROLES),
        "hierarchy": list(HIERARCHY),
        "preserves_canonical_source": True,
        "truth": (
            "Deterministic geometric derivation with explicit part roles and protected anchors. "
            "It does not infer good art direction, rig safety, deformation quality or engine fitness."
        ),
    }


def _component(primitive):
    identifier = primitive.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("every primitive needs a non-empty id")
    return identifier.split("__", 1)[0]


def _validated_mesh(mesh):
    if not isinstance(mesh, dict) or mesh.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("mesh must use axm.surface-3d/v0.1")
    primitives = mesh.get("primitives")
    if not isinstance(primitives, list) or not primitives or len(primitives) > 512:
        raise ValueError("mesh needs 1..512 primitives")
    components = {}
    for primitive in primitives:
        if not isinstance(primitive, dict):
            raise ValueError("primitive must be an object")
        component = _component(primitive)
        positions = primitive.get("positions")
        indices = primitive.get("indices")
        if not isinstance(positions, list) or not positions or len(positions) > 1_000_000:
            raise ValueError(f"{component} positions are missing or over limit")
        checked = [_vec3(position, f"{component}.position") for position in positions]
        normals, colors, material = primitive.get("normals"), primitive.get("colors"), primitive.get("material")
        if not isinstance(normals, list) or len(normals) != len(positions):
            raise ValueError(f"{component} needs one normal per position")
        for normal in normals:
            _vec3(normal, f"{component}.normal")
        if not isinstance(colors, list) or len(colors) != len(positions):
            raise ValueError(f"{component} needs one color per position")
        if not isinstance(material, dict):
            raise ValueError(f"{component} material is missing")
        if (not isinstance(indices, list) or not indices or len(indices) % 3 or
                any(isinstance(i, bool) or not isinstance(i, int) or not 0 <= i < len(positions) for i in indices)):
            raise ValueError(f"{component} indices must be bounded triangles")
        components.setdefault(component, []).extend(checked)
    return components


def _part_specs(raw, components):
    if not isinstance(raw, dict) or set(raw) != set(components):
        missing, unexpected = sorted(set(components) - set(raw)), sorted(set(raw) - set(components))
        raise ValueError(f"part specs must exactly cover components; missing={missing}, unexpected={unexpected}")
    result = {}
    for component, value in raw.items():
        if not isinstance(value, dict):
            raise ValueError(f"part {component} must be an object")
        unexpected = set(value) - {"role", "hierarchy", "strength", "anchors", "anchor_falloff"}
        if unexpected:
            raise ValueError(f"part {component} has unsupported fields: {sorted(unexpected)}")
        role, hierarchy = value.get("role", "detail"), value.get("hierarchy", "medium")
        if role not in ROLES or hierarchy not in HIERARCHY:
            raise ValueError(f"part {component} has unknown role or hierarchy")
        anchors = value.get("anchors", {})
        if not isinstance(anchors, dict) or len(anchors) > 32:
            raise ValueError(f"part {component}.anchors must be an object with at most 32 entries")
        checked_anchors = {}
        for name, point in anchors.items():
            if not isinstance(name, str) or not name or len(name) > 100:
                raise ValueError("anchor names must be short non-empty text")
            checked_anchors[name] = _vec3(point, f"anchor {name}")
        result[component] = {
            "role": role,
            "hierarchy": hierarchy,
            "strength": _number(value.get("strength", 1), f"part {component}.strength", 0, 1),
            "anchors": checked_anchors,
            "anchor_falloff": _number(value.get("anchor_falloff", .18),
                                       f"part {component}.anchor_falloff", 0, 1),
        }
    return result


def _bounds(points):
    return tuple(min(p[i] for p in points) for i in range(3)), tuple(max(p[i] for p in points) for i in range(3))


def _seeded_sign(seed, component):
    value = int(hashlib.sha256(f"{seed}:{component}".encode()).hexdigest()[:16], 16)
    return -1 if value & 1 else 1


def _raw_transform(point, bounds, spec, style, sign):
    low, high = bounds
    center = tuple((low[i] + high[i]) * .5 for i in range(3))
    x, y, z = point
    strength = spec["strength"]
    hierarchy = getattr(style, spec["hierarchy"] + "_scale")
    hierarchy = 1 + (hierarchy - 1) * strength
    role = spec["role"]
    role_scale = (style.functional_scale if role == "functional" else
                  style.armor_scale if role == "armor" else 1)
    role_scale = 1 + (role_scale - 1) * strength
    vertical = 1 + (style.vertical_scale - 1) * strength
    span_y = max(high[1] - low[1], 1e-9)
    height_t = max(0, min(1, (y - low[1]) / span_y))
    taper = 1 + style.taper * (height_t * 2 - 1) * strength
    horizontal = hierarchy * role_scale * taper
    vertical_total = vertical * (role_scale if role == "functional" else hierarchy)
    dx, dy, dz = (x - center[0]) * horizontal, (y - center[1]) * vertical_total, (z - center[2]) * horizontal
    angle = style.asymmetry * .7 * sign * strength
    ca, sa = math.cos(angle), math.sin(angle)
    dx, dz = dx * ca - dz * sa, dx * sa + dz * ca
    # Height-dependent shear gives intentional imbalance rather than a color cue.
    dx += style.asymmetry * sign * (y - center[1]) * strength
    return center[0] + dx, center[1] + dy, center[2] + dz


def _transform(point, bounds, spec, style, sign):
    raw = _raw_transform(point, bounds, spec, style, sign)
    delta = tuple(raw[i] - point[i] for i in range(3))
    anchors = spec["anchors"]
    if anchors and any(delta):
        low, high = bounds
        diagonal = math.sqrt(sum((high[i] - low[i]) ** 2 for i in range(3)))
        radius = diagonal * spec["anchor_falloff"]
        distance = min(math.dist(point, anchor) for anchor in anchors.values())
        weight = 1 if radius <= 1e-12 else min(1, distance / radius)
        delta = tuple(value * weight for value in delta)
    return tuple(round(point[i] + delta[i], 9) for i in range(3))


def _normals(positions, indices):
    accum = [[0., 0., 0.] for _ in positions]
    for offset in range(0, len(indices), 3):
        ia, ib, ic = indices[offset:offset + 3]
        a, b, c = positions[ia], positions[ib], positions[ic]
        ab, ac = tuple(b[i] - a[i] for i in range(3)), tuple(c[i] - a[i] for i in range(3))
        normal = (ab[1] * ac[2] - ab[2] * ac[1], ab[2] * ac[0] - ab[0] * ac[2],
                  ab[0] * ac[1] - ab[1] * ac[0])
        length = math.sqrt(sum(value * value for value in normal))
        if length <= 1e-12:
            raise ValueError("form derivation produced a degenerate triangle")
        for index in (ia, ib, ic):
            for axis in range(3):
                accum[index][axis] += normal[axis] / length
    result = []
    for normal in accum:
        length = math.sqrt(sum(value * value for value in normal))
        if length <= 1e-12:
            raise ValueError("form derivation produced an unreferenced vertex")
        result.append([round(value / length, 9) for value in normal])
    return result


def apply_game_form(mesh, part_specs, style="comic-salvage", seed=1):
    """Return canonical source plus a derived realization and anchor receipt."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_147_483_647:
        raise ValueError("seed must be an integer from 0 to 2147483647")
    profile = _style(style)
    components = _validated_mesh(mesh)
    specs = _part_specs(part_specs, components)
    bounds = {name: _bounds(points) for name, points in components.items()}
    realization = copy.deepcopy(mesh)
    anchor_rows = []
    for primitive in realization["primitives"]:
        component = _component(primitive)
        spec, sign = specs[component], _seeded_sign(seed, component)
        source_positions = [tuple(point) for point in primitive["positions"]]
        if style == "realistic" or spec["strength"] == 0:
            positions = [list(point) for point in source_positions]
        else:
            positions = [list(_transform(point, bounds[component], spec, profile, sign))
                         for point in source_positions]
            primitive["normals"] = _normals(positions, primitive["indices"])
        primitive["positions"] = positions
    for component, spec in specs.items():
        sign = _seeded_sign(seed, component)
        for name, point in spec["anchors"].items():
            after = point if style == "realistic" else _transform(point, bounds[component], spec, profile, sign)
            drift = math.dist(point, after)
            anchor_rows.append({"component": component, "name": name, "before": list(point),
                                "after": list(after), "drift": drift, "preserved": drift <= 1e-9})
    source = copy.deepcopy(mesh)
    return {
        "schema": FORM_SCHEMA,
        "style": asdict(profile),
        "seed": seed,
        "source_sha256": _digest(source),
        "source": source,
        "realization": realization,
        "parts": copy.deepcopy(part_specs),
        "anchor_receipt": anchor_rows,
        "gates": {"canonical-source-embedded": True,
                  "all-declared-anchors-preserved": all(row["preserved"] for row in anchor_rows)},
        "truth": (
            "A deterministic geometry derivation, not perceptual style acceptance. Protected anchor "
            "coordinates are preserved; rig deformation, collisions and target-engine behavior remain unproven."
        ),
    }


def publish_game_form(path, mesh, part_specs, style="comic-salvage", seed=1):
    """Publish source, realization and receipt without overwriting an existing path."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing form package: {target}")
    result = apply_game_form(mesh, part_specs, style, seed)
    target.mkdir(parents=True)
    try:
        atomic_write_json(target / "source.json", result["source"])
        atomic_write_json(target / "realization.json", result["realization"])
        manifest = {key: value for key, value in result.items() if key not in ("source", "realization")}
        atomic_write_json(target / "form-manifest.json", manifest)
    except Exception:
        for child in target.iterdir():
            child.unlink()
        target.rmdir()
        raise
    return {"path": str(target), "style": style, "source_sha256": result["source_sha256"],
            "anchors": result["anchor_receipt"], "gates": result["gates"],
            "files": ["source.json", "realization.json", "form-manifest.json"]}

"""Deterministic vehicle colour, finish, marking and wear realization.

The canonical surface mesh remains caller-owned.  This module realizes explicit
art-direction choices into ordinary surface materials and vertex colours, and can
append bounded panel-conforming marking geometry.  It does not infer taste,
damage history, UVs, texture projection, or target-engine shader behavior.
"""
from __future__ import annotations

import copy
import fnmatch
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from .atomic import atomic_write_bytes, atomic_write_json
from .procedural_3d import build_glb


REQUEST_SCHEMA = "axm.vehicle-art-direction-request/v0.1"
RESULT_SCHEMA = "axm.vehicle-art-direction/v0.1"
SLOTS = (
    "primary", "secondary", "trim", "structure", "metal_dark",
    "metal_bright", "rubber", "glass", "warning", "light_primary",
    "light_brake", "dirt", "damage",
)
PALETTES = {
    "industrial-teal": {
        "primary": "#28777BFF", "secondary": "#17464BFF", "trim": "#D19A35FF",
        "structure": "#252E32FF", "metal_dark": "#465156FF", "metal_bright": "#B8C0BAFF",
        "rubber": "#161D21FF", "glass": "#6BAEB2FF", "warning": "#E2A52CFF",
        "light_primary": "#25E6ECFF", "light_brake": "#E34A3DFF",
        "dirt": "#3B332AFF", "damage": "#B5A38AFF",
    },
    "interceptor-black-red": {
        "primary": "#171C21FF", "secondary": "#421B1EFF", "trim": "#D53A32FF",
        "structure": "#11161AFF", "metal_dark": "#343A40FF", "metal_bright": "#AAB0B4FF",
        "rubber": "#101519FF", "glass": "#596D7AFF", "warning": "#F07B32FF",
        "light_primary": "#EAF8FFFF", "light_brake": "#FF302FFF",
        "dirt": "#302A25FF", "damage": "#C1B29EFF",
    },
    "weathered-steel-orange": {
        "primary": "#76513AFF", "secondary": "#41484AFF", "trim": "#E1782EFF",
        "structure": "#292E2EFF", "metal_dark": "#4B5150FF", "metal_bright": "#B8B5A8FF",
        "rubber": "#1B2021FF", "glass": "#72969AFF", "warning": "#F3A12EFF",
        "light_primary": "#8DECF2FF", "light_brake": "#D94A35FF",
        "dirt": "#443426FF", "damage": "#B8AA92FF",
    },
    "ivory-gold-prototype": {
        "primary": "#D8D2C1FF", "secondary": "#5C6265FF", "trim": "#B9974CFF",
        "structure": "#252A2EFF", "metal_dark": "#4D555AFF", "metal_bright": "#D0D2CBFF",
        "rubber": "#20272BFF", "glass": "#7DB7BDFF", "warning": "#D5A33DFF",
        "light_primary": "#73F5F2FF", "light_brake": "#E45443FF",
        "dirt": "#554D40FF", "damage": "#B3A687FF",
    },
    "rally-blue-yellow": {
        "primary": "#245F9BFF", "secondary": "#163754FF", "trim": "#F0C42EFF",
        "structure": "#20272BFF", "metal_dark": "#414A50FF", "metal_bright": "#B8C1C7FF",
        "rubber": "#151B1FFF", "glass": "#75A8B7FF", "warning": "#FFD133FF",
        "light_primary": "#C3F8FFFF", "light_brake": "#E8493FFF",
        "dirt": "#40382EFF", "damage": "#B6AA95FF",
    },
}
FINISHES = {
    "factory": {"roughness_scale": 1.0, "roughness_bias": 0.0, "metallic_scale": 1.0},
    "matte": {"roughness_scale": .55, "roughness_bias": .46, "metallic_scale": .82},
    "satin": {"roughness_scale": .58, "roughness_bias": .22, "metallic_scale": .94},
    "gloss": {"roughness_scale": .25, "roughness_bias": .08, "metallic_scale": 1.0},
    "bare-metal": {"roughness_scale": .35, "roughness_bias": .20, "metallic_scale": 1.0},
    "damaged": {"roughness_scale": .52, "roughness_bias": .42, "metallic_scale": .88},
}
MARKING_STYLES = ("panel", "stripe", "chevron")
DEFAULT_BINDINGS = {
    "paint": "primary", "canvas": "secondary", "iron": "structure",
    "tin": "metal_bright", "rubber": "rubber", "glass": "glass",
    "windshield": "glass", "signal": "warning", "red": "light_brake",
    "cyan": "light_primary", "glow": "warning", "collision": "structure",
}
_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")
_PATTERN = re.compile(r"^[A-Za-z0-9*?_.\-/]{1,96}$")


def _canonical(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _object(value, label, required=(), optional=()):
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be an object")
    missing = sorted(set(required) - set(value))
    extra = sorted(set(value) - set(required) - set(optional))
    if missing or extra:
        raise ValueError(f"{label} fields invalid; missing={missing}, unexpected={extra}")
    return value


def _number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} through {high}")
    return value


def _integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} through {high}")
    return value


def _color(value, label):
    if not isinstance(value, str) or len(value) not in (7, 9) or not value.startswith("#"):
        raise ValueError(f"{label} must be #RRGGBB or #RRGGBBAA")
    try:
        bytes.fromhex(value[1:])
    except ValueError as exc:
        raise ValueError(f"{label} must be #RRGGBB or #RRGGBBAA") from exc
    return (value + "FF" if len(value) == 7 else value).upper()


def _rgba(value):
    color = _color(value, "color")
    return tuple(int(color[index:index + 2], 16) / 255 for index in (1, 3, 5, 7))


def _vector(value, label, low=-100_000, high=100_000):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three numbers")
    return tuple(_number(item, f"{label}[{index}]", low, high) for index, item in enumerate(value))


def _unit(value, label):
    vector = _vector(value, label, -1, 1)
    length = math.sqrt(sum(item * item for item in vector))
    if length <= 1e-9:
        raise ValueError(f"{label} must not be zero")
    return tuple(item / length for item in vector)


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _normalize_marking(raw, index):
    label = f"markings[{index}]"
    row = _object(raw, label,
                  required=("id", "style", "slot", "center", "right", "up", "size"),
                  optional=("offset", "bands"))
    if not isinstance(row["id"], str) or not _ID.fullmatch(row["id"]):
        raise ValueError(f"{label}.id must be a portable identifier")
    if row["style"] not in MARKING_STYLES:
        raise ValueError(f"{label}.style must be one of {MARKING_STYLES}")
    if row["slot"] not in SLOTS:
        raise ValueError(f"{label}.slot is unknown")
    right, up = _unit(row["right"], f"{label}.right"), _unit(row["up"], f"{label}.up")
    if abs(sum(right[i] * up[i] for i in range(3))) > .05:
        raise ValueError(f"{label}.right and up must be perpendicular")
    size = row["size"]
    if not isinstance(size, (list, tuple)) or len(size) != 2:
        raise ValueError(f"{label}.size must contain width and height")
    return {
        "id": row["id"], "style": row["style"], "slot": row["slot"],
        "center": list(_vector(row["center"], f"{label}.center")),
        "right": [round(item, 9) for item in right], "up": [round(item, 9) for item in up],
        "size": [_number(size[0], f"{label}.size[0]", .01, 100),
                 _number(size[1], f"{label}.size[1]", .01, 100)],
        "offset": _number(row.get("offset", .002), f"{label}.offset", -.1, .1),
        "bands": _integer(row.get("bands", 1), f"{label}.bands", 1, 12),
    }


def _normalize_upgrade(raw, index):
    label = f"upgrades[{index}]"
    row = _object(raw, label, required=("id", "level", "maximum", "targets", "slots"),
                  optional=("finishes",))
    if not isinstance(row["id"], str) or not _ID.fullmatch(row["id"]):
        raise ValueError(f"{label}.id must be a portable identifier")
    maximum = _integer(row["maximum"], f"{label}.maximum", 1, 12)
    level = _integer(row["level"], f"{label}.level", 0, maximum)
    targets = row["targets"]
    if not isinstance(targets, list) or not 1 <= len(targets) <= 8:
        raise ValueError(f"{label}.targets must contain 1 through 8 patterns")
    if any(not isinstance(item, str) or not _PATTERN.fullmatch(item) for item in targets):
        raise ValueError(f"{label}.targets contains an invalid pattern")
    slots = row["slots"]
    if not isinstance(slots, list) or len(slots) != maximum + 1 or any(item not in SLOTS for item in slots):
        raise ValueError(f"{label}.slots must contain one known slot for every level")
    finishes = row.get("finishes", [None] * (maximum + 1))
    if (not isinstance(finishes, list) or len(finishes) != maximum + 1
            or any(item is not None and item not in FINISHES for item in finishes)):
        raise ValueError(f"{label}.finishes must align with levels and name known finishes")
    return {"id": row["id"], "level": level, "maximum": maximum,
            "targets": list(targets), "slots": list(slots), "finishes": list(finishes)}


def vehicle_art_direction_catalog():
    return {
        "schema": "axm.vehicle-art-direction-catalog/v0.1",
        "request_schema": REQUEST_SCHEMA,
        "palettes": copy.deepcopy(PALETTES), "slots": list(SLOTS),
        "finishes": copy.deepcopy(FINISHES), "marking_styles": list(MARKING_STYLES),
        "weather_channels": ["dirt", "wear", "scratches", "edge_damage"],
        "custom_slot_colors": True, "upgrade_level_variants": True,
        "output": "canonical source, styled surface, compact receipt and actual GLB",
        "truth": (
            "This is deterministic object-space material, vertex-colour and marking realization. "
            "Weather is an authored visual proposal, not inferred physical history. Gloss and metal "
            "are core metallic-roughness approximations; texture projection, clearcoat, target-engine "
            "shaders, reflections and artistic approval remain outside this receipt."
        ),
    }


def compile_vehicle_art_direction(raw):
    request = _object(raw, "request", required=("schema", "palette"),
                      optional=("seed", "custom_slots", "finish", "material_bindings",
                                "weathering", "markings", "upgrades"))
    if request["schema"] != REQUEST_SCHEMA:
        raise ValueError(f"request.schema must be {REQUEST_SCHEMA}")
    preset = request["palette"]
    if preset not in PALETTES:
        raise ValueError(f"unknown vehicle palette: {preset}")
    seed = _integer(request.get("seed", 1), "seed", 0, 2_147_483_647)
    finish = request.get("finish", "satin")
    if finish not in FINISHES:
        raise ValueError(f"unknown vehicle finish: {finish}")
    palette = copy.deepcopy(PALETTES[preset])
    custom = request.get("custom_slots", {})
    if not isinstance(custom, dict) or len(custom) > len(SLOTS):
        raise ValueError("custom_slots must be a bounded slot-to-colour object")
    for slot, color in custom.items():
        if slot not in SLOTS:
            raise ValueError(f"unknown custom colour slot: {slot}")
        palette[slot] = _color(color, f"custom_slots.{slot}")
    bindings = dict(DEFAULT_BINDINGS)
    custom_bindings = request.get("material_bindings", {})
    if not isinstance(custom_bindings, dict) or len(custom_bindings) > 64:
        raise ValueError("material_bindings must be a bounded object")
    for source, slot in custom_bindings.items():
        if not isinstance(source, str) or not _ID.fullmatch(source) or slot not in SLOTS:
            raise ValueError("material_bindings must map portable names to known slots")
        bindings[source] = slot
    weather = request.get("weathering", {})
    if not isinstance(weather, dict) or set(weather) - {"dirt", "wear", "scratches", "edge_damage"}:
        raise ValueError("weathering contains unknown channels")
    weather = {name: _number(weather.get(name, 0), f"weathering.{name}", 0, 1)
               for name in ("dirt", "wear", "scratches", "edge_damage")}
    if finish == "damaged":
        weather["wear"] = max(weather["wear"], .42)
        weather["scratches"] = max(weather["scratches"], .28)
        weather["edge_damage"] = max(weather["edge_damage"], .36)
    markings = request.get("markings", [])
    if not isinstance(markings, list) or len(markings) > 24:
        raise ValueError("markings must contain at most 24 layers")
    markings = [_normalize_marking(row, index) for index, row in enumerate(markings)]
    if len({row["id"] for row in markings}) != len(markings):
        raise ValueError("marking IDs must be unique")
    upgrades = request.get("upgrades", [])
    if not isinstance(upgrades, list) or len(upgrades) > 16:
        raise ValueError("upgrades must contain at most 16 tracks")
    upgrades = [_normalize_upgrade(row, index) for index, row in enumerate(upgrades)]
    if len({row["id"] for row in upgrades}) != len(upgrades):
        raise ValueError("upgrade IDs must be unique")
    return {
        "schema": RESULT_SCHEMA, "request_schema": REQUEST_SCHEMA, "palette_preset": preset,
        "palette": palette, "custom_slots": sorted(custom), "finish": finish,
        "finish_profile": copy.deepcopy(FINISHES[finish]), "seed": seed,
        "material_bindings": bindings, "weathering": weather,
        "markings": markings, "upgrades": upgrades,
        "upgrade_variants": {
            row["id"]: [
                {"level": level, "slot": row["slots"][level],
                 "finish": row["finishes"][level] or finish, "active": level == row["level"]}
                for level in range(row["maximum"] + 1)
            ] for row in upgrades
        },
        "request_sha256": _digest(raw),
    }


def _point(center, right, up, normal, u, v, offset):
    return [round(center[i] + right[i] * u + up[i] * v + normal[i] * offset, 9)
            for i in range(3)]


def _strip(a, b, width):
    dx, dy = b[0] - a[0], b[1] - a[1]
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length * width / 2, dx / length * width / 2
    return [(a[0] - px, a[1] - py), (b[0] - px, b[1] - py),
            (b[0] + px, b[1] + py), (a[0] + px, a[1] + py)]


def _marking_primitives(markings):
    output = []
    for row in markings:
        center, right, up = row["center"], row["right"], row["up"]
        normal = _unit(_cross(right, up), f"marking {row['id']} basis")
        width, height = row["size"]
        quads = []
        if row["style"] == "panel":
            quads.append([(-width / 2, -height / 2), (width / 2, -height / 2),
                          (width / 2, height / 2), (-width / 2, height / 2)])
        elif row["style"] == "stripe":
            band_width = width / (row["bands"] * 2 - 1)
            for index in range(row["bands"]):
                x0 = -width / 2 + index * band_width * 2
                quads.append([(x0, -height / 2), (x0 + band_width, -height / 2),
                              (x0 + band_width, height / 2), (x0, height / 2)])
        else:
            stroke = min(width, height) * .16
            for index in range(row["bands"]):
                inset = index * stroke * 1.65
                y0, y1 = -height / 2 + inset, height / 2 - inset
                if y1 <= y0:
                    break
                quads.append(_strip((-width / 2, y1), (0, y0), stroke))
                quads.append(_strip((0, y0), (width / 2, y1), stroke))
        positions, normals, indices = [], [], []
        for quad in quads:
            start = len(positions)
            positions.extend(_point(center, right, up, normal, u, v, row["offset"])
                             for u, v in quad)
            normals.extend([list(normal)] * 4)
            indices.extend([start, start + 1, start + 2, start, start + 2, start + 3])
        output.append({
            "id": f"marking-{row['id']}__{row['slot']}", "positions": positions,
            "normals": normals, "indices": indices, "colors": [[1, 1, 1, 1]] * len(positions),
            "material": {"color": "#FFFFFFFF", "metallic": .1, "roughness": .55},
        })
    return output


def _mix(a, b, amount):
    return tuple(a[i] * (1 - amount) + b[i] * amount for i in range(3))


def _noise(position, seed, salt):
    value = math.sin(position[0] * 91.713 + position[1] * 47.271
                     + position[2] * 73.117 + seed * .131 + salt * 17.17) * 43758.5453
    return value - math.floor(value)


def _base_slot(primitive, bindings):
    key = primitive["id"].rsplit("__", 1)[-1]
    if key in SLOTS:
        return key
    return bindings.get(key, "secondary")


def _upgrade_for(primitive_id, upgrades):
    matches = [row for row in upgrades if any(fnmatch.fnmatchcase(primitive_id, pattern)
                                               for pattern in row["targets"])]
    if len(matches) > 1:
        raise ValueError(f"primitive matches multiple upgrade tracks: {primitive_id}")
    return matches[0] if matches else None


def _styled_material(source, slot, finish_name, weather):
    profile = FINISHES[finish_name]
    metallic = float(source.get("metallic", 0)) * profile["metallic_scale"]
    roughness = float(source.get("roughness", 1)) * profile["roughness_scale"] + profile["roughness_bias"]
    if slot in ("metal_dark", "metal_bright", "structure"):
        metallic = max(metallic, .68 if slot != "structure" else .5)
    elif slot == "rubber":
        metallic, roughness = 0.0, max(roughness, .82)
    elif slot == "glass":
        metallic, roughness = .08, min(roughness, .18)
    elif slot in ("light_primary", "light_brake"):
        metallic, roughness = .05, min(roughness, .24)
    roughness += weather["dirt"] * .12 + weather["wear"] * .06
    return {"color": "#FFFFFFFF", "metallic": round(max(0, min(1, metallic)), 6),
            "roughness": round(max(.02, min(1, roughness)), 6)}


def apply_vehicle_art_direction(mesh, request, *, include_markings=True):
    """Return source plus a styled realization without mutating either input."""
    if not isinstance(mesh, dict) or mesh.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("vehicle art direction requires an axm.surface-3d/v0.1 mesh")
    if not isinstance(mesh.get("primitives"), list) or not mesh["primitives"]:
        raise ValueError("vehicle surface requires primitives")
    compiled = compile_vehicle_art_direction(request)
    source, result = copy.deepcopy(mesh), copy.deepcopy(mesh)
    if include_markings:
        result["primitives"].extend(_marking_primitives(compiled["markings"]))
    changed, affected_vertices, upgrade_hits = 0, 0, {}
    substrate = _rgba(compiled["palette"]["damage"])
    dirt_color = _rgba(compiled["palette"]["dirt"])
    for primitive in result["primitives"]:
        for key in ("id", "positions", "normals", "indices", "material"):
            if key not in primitive:
                raise ValueError(f"vehicle primitive missing {key}")
        slot = _base_slot(primitive, compiled["material_bindings"])
        finish = compiled["finish"]
        upgrade = _upgrade_for(primitive["id"], compiled["upgrades"])
        if upgrade:
            level = upgrade["level"]
            slot = upgrade["slots"][level]
            finish = upgrade["finishes"][level] or finish
            upgrade_hits[upgrade["id"]] = upgrade_hits.get(upgrade["id"], 0) + 1
        color = _rgba(compiled["palette"][slot])
        if finish == "bare-metal" and slot in ("primary", "secondary", "trim"):
            color = (*_mix(color[:3], _rgba(compiled["palette"]["metal_bright"])[:3], .68), color[3])
        positions = primitive["positions"]
        colors = primitive.get("colors", [[1, 1, 1, 1] for _ in positions])
        if len(colors) != len(positions):
            raise ValueError("vehicle primitive color count must match positions")
        low = [min(point[axis] for point in positions) for axis in range(3)]
        high = [max(point[axis] for point in positions) for axis in range(3)]
        span = [max(1e-9, high[axis] - low[axis]) for axis in range(3)]
        styled = []
        weather = compiled["weathering"]
        for index, (position, tint) in enumerate(zip(positions, colors)):
            if not isinstance(tint, (list, tuple)) or len(tint) != 4:
                raise ValueError("vehicle vertex colours must be RGBA")
            rgb = tuple(max(0, min(1, color[channel] * float(tint[channel]))) for channel in range(3))
            normalized = [(position[axis] - low[axis]) / span[axis] for axis in range(3)]
            boundary = sorted(max(value, 1 - value) for value in normalized)[-2]
            noise = _noise(position, compiled["seed"], index % 17)
            ground = 1 - normalized[1]
            dirt = weather["dirt"] * max(0, ground - .12) * (.45 + .55 * noise)
            wear = weather["wear"] * max(0, noise - .42) * .32
            scratch_line = abs(math.sin(position[0] * 31.7 + position[1] * 11.3
                                        - position[2] * 23.9 + compiled["seed"] * .17))
            scratch = weather["scratches"] * max(0, scratch_line - .965) * 9
            edge = weather["edge_damage"] * max(0, boundary - .84) * 2.6
            rgb = _mix(rgb, dirt_color[:3], min(.72, dirt))
            rgb = _mix(rgb, substrate[:3], min(.82, wear + scratch + edge))
            styled.append([*[round(max(0, min(1, value)), 9) for value in rgb],
                           round(max(0, min(1, color[3] * float(tint[3]))), 9)])
        primitive["colors"] = styled
        material = _styled_material(primitive["material"], slot, finish, weather)
        if slot in ("light_primary", "light_brake"):
            material["emissive"] = compiled["palette"][slot]
        primitive["material"] = material
        changed += 1
        affected_vertices += len(styled)
    return {
        "schema": RESULT_SCHEMA, "source": source, "realization": result,
        "compiled": compiled,
        "receipt": {
            "source_sha256": _digest(source), "realization_sha256": _digest(result),
            "request_sha256": compiled["request_sha256"], "palette": compiled["palette_preset"],
            "custom_slots": compiled["custom_slots"], "finish": compiled["finish"],
            "material_count": changed, "affected_vertices": affected_vertices,
            "marking_layers": len(compiled["markings"]) if include_markings else 0,
            "marking_primitives": len(compiled["markings"]) if include_markings else 0,
            "weathering": compiled["weathering"], "upgrade_hits": upgrade_hits,
            "geometry_preserved": all(
                left[key] == right[key]
                for left, right in zip(source["primitives"], result["primitives"])
                for key in ("positions", "normals", "indices")
            ),
            "canonical_source_embedded": True,
            "truth": vehicle_art_direction_catalog()["truth"],
        },
    }


def publish_vehicle_art_direction(path, mesh, request):
    """Atomically publish source, realization, receipt and actual styled GLB."""
    target = Path(path).resolve()
    if target.exists():
        raise FileExistsError(f"vehicle art direction output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    package = apply_vehicle_art_direction(mesh, request)
    built = build_glb(package["realization"])
    with tempfile.TemporaryDirectory(prefix=".axm-vehicle-style-", dir=target.parent) as temporary:
        stage = Path(temporary) / "publication"
        stage.mkdir()
        atomic_write_json(stage / "source.json", package["source"])
        atomic_write_json(stage / "realization.json", package["realization"])
        manifest = {"schema": RESULT_SCHEMA, "compiled": package["compiled"],
                    "receipt": package["receipt"],
                    "glb_sha256": hashlib.sha256(built["body"]).hexdigest(),
                    "glb_specification_sha256": built["specification_sha256"]}
        atomic_write_json(stage / "art-direction.json", manifest)
        atomic_write_bytes(stage / "asset.glb", built["body"])
        os.replace(stage, target)
    return {**manifest, "path": str(target),
            "files": sorted(item.name for item in target.iterdir())}

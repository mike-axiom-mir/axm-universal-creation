"""Portable baked game-lighting styles for renderer-neutral surface meshes.

Stylized realizations fold source material and vertex colour into final linear
vertex colours and opt into glTF KHR_materials_unlit.  This preserves the baked
look across conforming viewers without pretending that dynamic bands, outlines,
rim lights, or paint strokes exist in glTF core.  The canonical PBR source stays
embedded and unchanged beside every realization.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import tempfile

from .atomic import atomic_write_bytes, atomic_write_json
from .procedural_3d import build_glb


RENDER_STYLE_SCHEMA = "axm.game-render-style/v0.1"


@dataclass(frozen=True)
class RenderStyle:
    name: str
    mode: str
    bands: int
    brush_strength: float
    shadow_tint: tuple[float, float, float]
    highlight_tint: tuple[float, float, float]
    portable: str


RENDER_STYLES = (
    RenderStyle("realistic-pbr", "dynamic-pbr", 0, 0.0, (0, 0, 0), (0, 0, 0),
                "unchanged canonical surface"),
    RenderStyle("graphic-toon-baked", "unlit-baked", 3, 0.0, (.03, .10, .22), (1.0, .70, .22),
                "KHR_materials_unlit plus final linear vertex colours"),
    RenderStyle("painted-adventure-baked", "unlit-baked", 6, .30, (.20, .18, .38), (1.0, .58, .25),
                "KHR_materials_unlit plus position-coherent brushed vertex colours"),
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _profile(name):
    for style in RENDER_STYLES:
        if style.name == name:
            return style
    raise ValueError(f"unknown game render style: {name}")


def _number(value, label, low=-100000.0, high=100000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _vector(value, label, width, low=-100000.0, high=100000.0):
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise ValueError(f"{label} must contain {width} numbers")
    return tuple(_number(item, f"{label}[{index}]", low, high) for index, item in enumerate(value))


def _unit(value):
    length = math.sqrt(sum(item * item for item in value))
    if length <= 1e-12:
        raise ValueError("light direction must not be zero")
    return tuple(item / length for item in value)


def _rgba(value):
    if not isinstance(value, str) or len(value) not in (7, 9) or not value.startswith("#"):
        raise ValueError("material color must be #RRGGBB or #RRGGBBAA")
    try:
        channels = [int(value[index:index + 2], 16) / 255 for index in range(1, len(value), 2)]
    except ValueError as exc:
        raise ValueError("material color must be hexadecimal") from exc
    if len(channels) == 3:
        channels.append(1.0)
    return channels


def _validate(mesh):
    if not isinstance(mesh, dict) or mesh.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("mesh must use axm.surface-3d/v0.1")
    primitives = mesh.get("primitives")
    if not isinstance(primitives, list) or not 1 <= len(primitives) <= 128:
        raise ValueError("mesh must contain 1..128 primitives")
    for primitive in primitives:
        if not isinstance(primitive, dict) or not isinstance(primitive.get("id"), str):
            raise ValueError("every primitive needs a text id")
        positions, normals, colors = (primitive.get(key) for key in ("positions", "normals", "colors"))
        if not isinstance(positions, list) or not positions or len(positions) > 65535:
            raise ValueError("primitive positions are missing or over limit")
        if not isinstance(normals, list) or len(normals) != len(positions):
            raise ValueError("primitive needs one normal per position")
        if not isinstance(colors, list) or len(colors) != len(positions):
            raise ValueError("primitive needs one linear RGBA colour per position")
        for index, (position, normal, color) in enumerate(zip(positions, normals, colors)):
            _vector(position, f"position {index}", 3)
            _unit(_vector(normal, f"normal {index}", 3, -1, 1))
            _vector(color, f"colour {index}", 4, 0, 1)
        material = primitive.get("material")
        if not isinstance(material, dict) or set(material) - {"color", "metallic", "roughness", "unlit"}:
            raise ValueError("surface material fields are invalid")
        _rgba(material.get("color"))
        _number(material.get("metallic"), "metallic", 0, 1)
        _number(material.get("roughness"), "roughness", 0, 1)
        if "unlit" in material and type(material["unlit"]) is not bool:
            raise ValueError("material unlit flag must be boolean")
    # Reuse the native generator as the final topology/index grammar gate.
    build_glb(mesh)


def game_render_style_catalog():
    return {
        "schema": "axm.game-render-style-catalog/v0.1",
        "styles": [asdict(style) for style in RENDER_STYLES],
        "canonical_source_preserved": True,
        "portable_dynamic_features": [],
        "target_engine_adapter_features": [
            "camera-responsive outlines", "dynamic light-band direction",
            "screen-space paper grain", "camera rim lighting", "animated brush crawl",
        ],
        "truth": (
            "Baked unlit styles preserve their fixed authored lighting in conforming GLB viewers. "
            "They do not prove target-engine colour management or dynamic toon/painterly shaders."
        ),
    }


def _mix(a, b, amount):
    return tuple(a[i] * (1 - amount) + b[i] * amount for i in range(3))


def _quantize(value, bands):
    return round(max(0, min(1, value)) * (bands - 1)) / (bands - 1)


def _tone(base, normal, position, style, light, seed, primitive_index):
    normal = _unit(normal)
    ndotl = sum(normal[i] * light[i] for i in range(3))
    diffuse = max(0, min(1, (ndotl + .18) / 1.18))
    band = _quantize(diffuse, style.bands)
    if style.name == "graphic-toon-baked":
        value = .27 + band * .88
        tint = _mix(style.shadow_tint, style.highlight_tint, band)
        tint_amount = .15 if band < .5 else .07
    else:
        phase = (seed * .61803398875 + primitive_index * 1.41421356237) % math.tau
        # Object-space diagonal strokes remain coherent across shared positions;
        # this is fixed paint rhythm, not a screen-space shader claim.
        stroke = math.sin(position[0] * 11.3 + position[1] * 17.1 - position[2] * 7.7 + phase)
        cross = math.sin(position[0] * 4.1 - position[1] * 8.3 + position[2] * 13.7 - phase)
        brush_signal = stroke * .72 + cross * .28
        brush = brush_signal * style.brush_strength
        painted_band = _quantize(diffuse + brush, style.bands)
        value = .32 + painted_band * .78
        tint = _mix(style.shadow_tint, style.highlight_tint, painted_band)
        # Chromatic pigment variation makes the fixed object-space strokes
        # legible after GLB export without inventing a screen-space effect.
        stroke_tint = (1.0, .50, .18) if brush_signal >= 0 else (.18, .34, .72)
        tint = _mix(tint, stroke_tint, .18 * abs(brush_signal))
        tint_amount = .19 if painted_band < .5 else .12
    shaded = tuple(max(0, min(1, channel * value)) for channel in base)
    return _mix(shaded, tint, tint_amount)


def apply_game_render_style(mesh, style="graphic-toon-baked", seed=1,
                            light_direction=(-.45, .82, .35)):
    """Return exact canonical source plus one portable render realization."""
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2_147_483_647:
        raise ValueError("seed must be an integer from 0 to 2147483647")
    profile = _profile(style)
    light = _unit(_vector(light_direction, "light_direction", 3, -1, 1))
    _validate(mesh)
    source = copy.deepcopy(mesh)
    realization = copy.deepcopy(mesh)
    if profile.mode == "unlit-baked":
        for primitive_index, primitive in enumerate(realization["primitives"]):
            factor = _rgba(primitive["material"]["color"])
            output = []
            for position, normal, color in zip(primitive["positions"], primitive["normals"], primitive["colors"]):
                base = tuple(factor[i] * color[i] for i in range(3))
                rgb = _tone(base, normal, position, profile, light, seed, primitive_index)
                output.append([*[round(value, 9) for value in rgb], round(factor[3] * color[3], 9)])
            primitive["colors"] = output
            primitive["material"] = {"color": "#FFFFFFFF", "metallic": 0.0,
                                     "roughness": 1.0, "unlit": True}
    return {
        "schema": RENDER_STYLE_SCHEMA,
        "source": source,
        "source_sha256": _digest(source),
        "realization": realization,
        "style": asdict(profile),
        "seed": seed,
        "light_direction": [round(value, 9) for value in light],
        "gates": {
            "canonical-source-embedded": source == mesh,
            "geometry-unchanged": all(
                left[key] == right[key]
                for left, right in zip(source["primitives"], realization["primitives"])
                for key in ("positions", "normals", "indices")
            ),
            "portable-unlit-bake": profile.mode == "unlit-baked",
        },
        "engine_adapter_required_for": game_render_style_catalog()["target_engine_adapter_features"],
        "truth": (
            "The GLB bake fixes authored light direction and paint rhythm in vertex colours. "
            "Dynamic outlines, lights, rims and screen-space effects require a target-engine adapter."
        ),
    }


def publish_game_render_style(path, mesh, style="graphic-toon-baked", seed=1,
                              light_direction=(-.45, .82, .35)):
    """Atomically publish source, realization, manifest, and actual GLB."""
    target = Path(path).resolve()
    if target.exists():
        raise FileExistsError(f"game render style output already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    package = apply_game_render_style(mesh, style, seed, light_direction)
    built = build_glb(package["realization"])
    with tempfile.TemporaryDirectory(prefix=".axm-game-render-", dir=target.parent) as temporary:
        stage = Path(temporary) / "publication"
        stage.mkdir()
        atomic_write_json(stage / "source.json", package["source"])
        atomic_write_json(stage / "realization.json", package["realization"])
        manifest = {key: value for key, value in package.items() if key not in ("source", "realization")}
        manifest["glb_sha256"] = hashlib.sha256(built["body"]).hexdigest()
        manifest["glb_specification_sha256"] = built["specification_sha256"]
        atomic_write_json(stage / "render-style.json", manifest)
        atomic_write_bytes(stage / "asset.glb", built["body"])
        os.replace(stage, target)
    return {**manifest, "path": str(target), "files": sorted(item.name for item in target.iterdir())}

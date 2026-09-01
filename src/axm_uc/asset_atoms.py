from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from pathlib import Path
from typing import Any, Callable

from .project import ProjectError, build_project


ASSET_ATOM_SCHEMA = "axm.asset-atom-package/v0.1"
ASSET_INSTANCE_SCHEMA = "axm.asset-instance/v0.1"
ATOM_KINDS = {
    "shape",
    "part",
    "texture",
    "material",
    "palette",
    "gradient",
    "mask",
    "overlay",
    "shader",
    "animation",
    "state",
    "behavior",
    "lod",
    "collision",
    "socket",
    "metadata",
}
MAX_ATOMS = 512
MAX_LIST = 128
MAX_TEXT = 2000
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?")
SHA256_RE = re.compile(r"(sha256:)?[0-9a-f]{64}")
TEXTURE_CHANNELS = {
    "base-color",
    "normal",
    "roughness",
    "metallic",
    "ambient-occlusion",
    "height",
    "displacement",
    "emissive",
    "opacity",
    "color-mask",
    "decal",
    "microdetail",
}
MATERIAL_SCALARS = {
    "metallic",
    "roughness",
    "opacity",
    "emission",
    "normal-strength",
    "height-scale",
    "displacement-scale",
    "ambient-occlusion-strength",
    "transmission",
    "ior",
    "subsurface",
    "anisotropy",
    "clearcoat",
}
MATERIAL_COLORS = {"base-color", "emissive-color", "specular-color"}


class AssetAtomError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _object(raw: Any, label: str, allowed: set[str], required: set[str] = frozenset()) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise AssetAtomError(f"{label} must be an object")
    unexpected = sorted(set(raw) - allowed)
    missing = sorted(required - set(raw))
    if unexpected:
        raise AssetAtomError(f"{label} has unsupported fields", {"label": label, "unexpected_fields": unexpected})
    if missing:
        raise AssetAtomError(f"{label} is missing required fields", {"label": label, "missing_fields": missing})
    return raw


def _text(value: Any, label: str, maximum: int = MAX_TEXT) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AssetAtomError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise AssetAtomError(f"{label} exceeds its {maximum}-character bound")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 128)
    if ID_RE.fullmatch(result) is None:
        raise AssetAtomError(f"{label} is invalid", {"label": label, "value": result})
    return result


def _number(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise AssetAtomError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise AssetAtomError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise AssetAtomError(f"{label} must be <= {maximum}")
    return result


def _integer(value: Any, label: str, minimum: int = 0, maximum: int = 1_000_000) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise AssetAtomError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _boolean(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise AssetAtomError(f"{label} must be boolean")
    return value


def _color(value: Any, label: str) -> str:
    result = _text(value, label, 9)
    if HEX_RE.fullmatch(result) is None:
        raise AssetAtomError(f"{label} must be #RRGGBB or #RRGGBBAA")
    return result.upper()


def _names(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_LIST or (not value and not allow_empty):
        qualifier = "1..128" if not allow_empty else "0..128"
        raise AssetAtomError(f"{label} must contain {qualifier} unique identifiers")
    result: list[str] = []
    for index, item in enumerate(value):
        name = _identifier(item, f"{label}[{index}]")
        if name in result:
            raise AssetAtomError(f"{label} entries must be unique", {"duplicate": name})
        result.append(name)
    return result


def _texts(value: Any, label: str, *, allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or len(value) > MAX_LIST or (not value and not allow_empty):
        qualifier = "1..128" if not allow_empty else "0..128"
        raise AssetAtomError(f"{label} must contain {qualifier} text entries")
    result: list[str] = []
    for index, item in enumerate(value):
        text = _text(item, f"{label}[{index}]", 400)
        if text in result:
            raise AssetAtomError(f"{label} entries must be unique", {"duplicate": text})
        result.append(text)
    return result


def _vector(value: Any, label: str, length: int, *, minimum: float | None = None) -> list[float]:
    if not isinstance(value, list) or len(value) != length:
        raise AssetAtomError(f"{label} must contain exactly {length} numbers")
    return [_number(item, f"{label}[{index}]", minimum) for index, item in enumerate(value)]


def _json_value(value: Any, label: str) -> Any:
    try:
        encoded = _canonical_bytes(value)
    except (TypeError, ValueError) as exc:
        raise AssetAtomError(f"{label} must be deterministic JSON data") from exc
    if len(encoded) > 65536:
        raise AssetAtomError(f"{label} exceeds its 65536-byte bound")
    return copy.deepcopy(value)


def _resource(raw: Any, label: str) -> dict[str, Any]:
    raw = _object(
        raw,
        label,
        {"uri", "mime_type", "digest", "color_space"},
        {"uri", "mime_type"},
    )
    result = {
        "uri": _text(raw["uri"], f"{label}.uri", 1000),
        "mime_type": _text(raw["mime_type"], f"{label}.mime_type", 120).casefold(),
    }
    if "digest" in raw:
        digest = _text(raw["digest"], f"{label}.digest", 71).casefold()
        if SHA256_RE.fullmatch(digest) is None:
            raise AssetAtomError(f"{label}.digest must be a SHA-256 value")
        result["digest"] = digest if digest.startswith("sha256:") else f"sha256:{digest}"
    if "color_space" in raw:
        color_space = _text(raw["color_space"], f"{label}.color_space", 40).casefold()
        if color_space not in {"srgb", "linear", "normal-data", "scalar-data", "not-applicable"}:
            raise AssetAtomError(f"{label}.color_space is unsupported", {"color_space": color_space})
        result["color_space"] = color_space
    return result


def _transform(raw: Any, label: str) -> dict[str, list[float]]:
    raw = {} if raw is None else _object(raw, label, {"position", "rotation_euler", "scale"})
    return {
        "position": _vector(raw.get("position", [0, 0, 0]), f"{label}.position", 3),
        "rotation_euler": _vector(raw.get("rotation_euler", [0, 0, 0]), f"{label}.rotation_euler", 3),
        "scale": _vector(raw.get("scale", [1, 1, 1]), f"{label}.scale", 3, minimum=0.000001),
    }


def _dimensions(raw: Any, label: str) -> dict[str, Any]:
    raw = _object(raw, label, {"width", "height", "depth", "unit"}, {"width", "height", "depth", "unit"})
    return {
        "width": _number(raw["width"], f"{label}.width", 0),
        "height": _number(raw["height"], f"{label}.height", 0),
        "depth": _number(raw["depth"], f"{label}.depth", 0),
        "unit": _text(raw["unit"], f"{label}.unit", 32).casefold(),
    }


def _shape_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"dimension", "representation", "primitive", "source", "bounds"}, {"dimension", "representation", "bounds"})
    dimension = _text(raw["dimension"], f"{label}.dimension", 8).casefold()
    representation = _text(raw["representation"], f"{label}.representation", 40).casefold()
    if dimension not in {"2d", "3d"}:
        raise AssetAtomError(f"{label}.dimension must be 2d or 3d")
    if representation not in {"primitive", "vector", "mesh", "sprite", "impostor"}:
        raise AssetAtomError(f"{label}.representation is unsupported", {"representation": representation})
    result: dict[str, Any] = {
        "dimension": dimension,
        "representation": representation,
        "bounds": _dimensions(raw["bounds"], f"{label}.bounds"),
    }
    if representation == "primitive":
        primitive = _text(raw.get("primitive"), f"{label}.primitive", 40).casefold()
        if primitive not in {"box", "sphere", "cylinder", "capsule", "plane", "circle", "rect", "polygon"}:
            raise AssetAtomError(f"{label}.primitive is unsupported", {"primitive": primitive})
        result["primitive"] = primitive
        if "source" in raw:
            raise AssetAtomError(f"{label}.source is not allowed for a primitive representation")
    else:
        if "primitive" in raw:
            raise AssetAtomError(f"{label}.primitive is only allowed for a primitive representation")
        result["source"] = _resource(raw.get("source"), f"{label}.source")
    return result, []


def _texture_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"channel", "resource", "uv_set", "tiling", "offset", "strength"}, {"channel", "resource"})
    channel = _text(raw["channel"], f"{label}.channel", 40).casefold().replace("_", "-")
    if channel not in TEXTURE_CHANNELS:
        raise AssetAtomError(f"{label}.channel is unsupported", {"channel": channel})
    return {
        "channel": channel,
        "resource": _resource(raw["resource"], f"{label}.resource"),
        "uv_set": _integer(raw.get("uv_set", 0), f"{label}.uv_set", 0, 7),
        "tiling": _vector(raw.get("tiling", [1, 1]), f"{label}.tiling", 2, minimum=0.000001),
        "offset": _vector(raw.get("offset", [0, 0]), f"{label}.offset", 2),
        "strength": _number(raw.get("strength", 1), f"{label}.strength", 0, 16),
    }, []


def _palette_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"colors"}, {"colors"})
    colors = raw["colors"]
    if not isinstance(colors, dict) or not 1 <= len(colors) <= 64:
        raise AssetAtomError(f"{label}.colors must map 1..64 roles to colors")
    normalized: dict[str, str] = {}
    for role, color in colors.items():
        normalized[_identifier(role, f"{label}.colors role")] = _color(color, f"{label}.colors.{role}")
    return {"colors": normalized}, []


def _gradient_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"kind", "space", "angle", "palette", "stops"}, {"kind", "space", "stops"})
    kind = _text(raw["kind"], f"{label}.kind", 40).casefold()
    space = _text(raw["space"], f"{label}.space", 40).casefold()
    if kind not in {"linear", "radial", "ramp"} or space not in {"srgb", "linear", "oklab"}:
        raise AssetAtomError(f"{label} has an unsupported gradient kind or color space")
    palette = _identifier(raw["palette"], f"{label}.palette") if "palette" in raw else None
    stops = raw["stops"]
    if not isinstance(stops, list) or not 2 <= len(stops) <= 16:
        raise AssetAtomError(f"{label}.stops must contain 2..16 entries")
    normalized_stops: list[dict[str, Any]] = []
    previous = -1.0
    for index, stop in enumerate(stops):
        stop = _object(stop, f"{label}.stops[{index}]", {"position", "color", "palette_role"}, {"position"})
        if ("color" in stop) == ("palette_role" in stop):
            raise AssetAtomError(f"{label}.stops[{index}] must declare exactly one of color or palette_role")
        position = _number(stop["position"], f"{label}.stops[{index}].position", 0, 1)
        if position <= previous:
            raise AssetAtomError(f"{label}.stops positions must be strictly increasing")
        previous = position
        row: dict[str, Any] = {"position": position}
        if "color" in stop:
            row["color"] = _color(stop["color"], f"{label}.stops[{index}].color")
        else:
            if palette is None:
                raise AssetAtomError(f"{label}.palette is required when a stop uses palette_role")
            row["palette_role"] = _identifier(stop["palette_role"], f"{label}.stops[{index}].palette_role")
        normalized_stops.append(row)
    result: dict[str, Any] = {"kind": kind, "space": space, "angle": _number(raw.get("angle", 0), f"{label}.angle", -360, 360), "stops": normalized_stops}
    if palette is not None:
        result["palette"] = palette
    return result, [palette] if palette else []


def _mask_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"source", "component", "meaning", "invert", "threshold"}, {"source", "component", "meaning"})
    component = _text(raw["component"], f"{label}.component", 20).casefold()
    if component not in {"r", "g", "b", "a", "luminance"}:
        raise AssetAtomError(f"{label}.component is unsupported", {"component": component})
    source = _identifier(raw["source"], f"{label}.source")
    return {
        "source": source,
        "component": component,
        "meaning": _text(raw["meaning"], f"{label}.meaning", 120),
        "invert": _boolean(raw.get("invert", False), f"{label}.invert"),
        "threshold": _number(raw.get("threshold", 0.5), f"{label}.threshold", 0, 1),
    }, [source]


def _overlay_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"source", "mask", "blend_mode", "opacity", "order", "states"}, {"source", "blend_mode"})
    source = _identifier(raw["source"], f"{label}.source")
    mask = _identifier(raw["mask"], f"{label}.mask") if "mask" in raw else None
    blend = _text(raw["blend_mode"], f"{label}.blend_mode", 40).casefold()
    if blend not in {"normal", "multiply", "screen", "overlay", "add", "subtract", "soft-light", "hard-light"}:
        raise AssetAtomError(f"{label}.blend_mode is unsupported", {"blend_mode": blend})
    result: dict[str, Any] = {
        "source": source,
        "blend_mode": blend,
        "opacity": _number(raw.get("opacity", 1), f"{label}.opacity", 0, 1),
        "order": _integer(raw.get("order", 0), f"{label}.order", 0, 10000),
        "states": _names(raw.get("states", []), f"{label}.states"),
    }
    refs = [source]
    if mask is not None:
        result["mask"] = mask
        refs.append(mask)
    return result, refs


def _shader_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(
        raw,
        label,
        {"model", "parameters", "animated_parameters", "runtime_source"},
        {"model"},
    )
    model = _text(raw["model"], f"{label}.model", 80).casefold()
    supported = {
        "pbr-metallic-roughness",
        "unlit",
        "glass",
        "hologram",
        "water",
        "energy-shield",
        "iridescent",
        "toon",
        "camouflage",
        "scan-lines",
        "custom-descriptor",
    }
    if model not in supported:
        raise AssetAtomError(f"{label}.model is unsupported", {"model": model})
    parameters = raw.get("parameters", {})
    if not isinstance(parameters, dict) or len(parameters) > 64:
        raise AssetAtomError(f"{label}.parameters must be an object with at most 64 entries")
    normalized_parameters: dict[str, Any] = {}
    for key, value in parameters.items():
        normalized_parameters[_identifier(key, f"{label}.parameters key")] = _json_value(
            value, f"{label}.parameters.{key}"
        )
    animated = _names(raw.get("animated_parameters", []), f"{label}.animated_parameters")
    unknown = sorted(set(animated) - set(normalized_parameters))
    if unknown:
        raise AssetAtomError(
            f"{label}.animated_parameters must name declared parameters",
            {"unknown_parameters": unknown},
        )
    result: dict[str, Any] = {
        "model": model,
        "parameters": normalized_parameters,
        "animated_parameters": animated,
    }
    if "runtime_source" in raw:
        result["runtime_source"] = _resource(raw["runtime_source"], f"{label}.runtime_source")
    return result, []


def _material_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(
        raw,
        label,
        {"scalars", "colors", "texture_bindings", "shader", "palette", "gradient", "masks", "overlays"},
    )
    scalars = raw.get("scalars", {})
    if not isinstance(scalars, dict) or len(scalars) > 32:
        raise AssetAtomError(f"{label}.scalars must be an object with at most 32 entries")
    normalized_scalars: dict[str, float] = {}
    for key, value in scalars.items():
        name = _text(key, f"{label}.scalars key", 64).casefold().replace("_", "-")
        if name not in MATERIAL_SCALARS:
            raise AssetAtomError(f"{label}.scalars has an unsupported channel", {"channel": name})
        maximum = 4 if name == "ior" else 16 if name in {"emission", "height-scale", "displacement-scale"} else 1
        minimum = 1 if name == "ior" else 0
        normalized_scalars[name] = _number(value, f"{label}.scalars.{key}", minimum, maximum)

    colors = raw.get("colors", {})
    if not isinstance(colors, dict) or len(colors) > len(MATERIAL_COLORS):
        raise AssetAtomError(f"{label}.colors must be a bounded object")
    normalized_colors: dict[str, str] = {}
    for key, value in colors.items():
        name = _text(key, f"{label}.colors key", 64).casefold().replace("_", "-")
        if name not in MATERIAL_COLORS:
            raise AssetAtomError(f"{label}.colors has an unsupported channel", {"channel": name})
        normalized_colors[name] = _color(value, f"{label}.colors.{key}")

    bindings = raw.get("texture_bindings", {})
    if not isinstance(bindings, dict) or len(bindings) > len(TEXTURE_CHANNELS):
        raise AssetAtomError(f"{label}.texture_bindings must be a bounded channel-to-atom object")
    normalized_bindings: dict[str, str] = {}
    for channel, ref in bindings.items():
        channel_name = _text(channel, f"{label}.texture_bindings key", 64).casefold().replace("_", "-")
        if channel_name not in TEXTURE_CHANNELS:
            raise AssetAtomError(
                f"{label}.texture_bindings has an unsupported channel", {"channel": channel_name}
            )
        normalized_bindings[channel_name] = _identifier(ref, f"{label}.texture_bindings.{channel}")

    result: dict[str, Any] = {
        "scalars": normalized_scalars,
        "colors": normalized_colors,
        "texture_bindings": normalized_bindings,
        "masks": _names(raw.get("masks", []), f"{label}.masks"),
        "overlays": _names(raw.get("overlays", []), f"{label}.overlays"),
    }
    refs = [*normalized_bindings.values(), *result["masks"], *result["overlays"]]
    for field in ("shader", "palette", "gradient"):
        if field in raw:
            ref = _identifier(raw[field], f"{label}.{field}")
            result[field] = ref
            refs.append(ref)
    return result, refs


def _collision_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"shape", "dimensions", "source_shape", "layers", "is_trigger"}, {"shape", "dimensions"})
    shape = _text(raw["shape"], f"{label}.shape", 40).casefold()
    if shape not in {"box", "sphere", "capsule", "convex-hull", "mesh-reference"}:
        raise AssetAtomError(f"{label}.shape is unsupported", {"shape": shape})
    source_shape = _identifier(raw["source_shape"], f"{label}.source_shape") if "source_shape" in raw else None
    if shape == "mesh-reference" and source_shape is None:
        raise AssetAtomError(f"{label}.source_shape is required for mesh-reference collision")
    result: dict[str, Any] = {
        "shape": shape,
        "dimensions": _dimensions(raw["dimensions"], f"{label}.dimensions"),
        "layers": _names(raw.get("layers", ["default"]), f"{label}.layers", allow_empty=False),
        "is_trigger": _boolean(raw.get("is_trigger", False), f"{label}.is_trigger"),
    }
    if source_shape is not None:
        result["source_shape"] = source_shape
    return result, [source_shape] if source_shape else []


def _part_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"role", "shape", "material", "children", "collision", "transform", "tags"}, {"role", "shape"})
    shape = _identifier(raw["shape"], f"{label}.shape")
    children = _names(raw.get("children", []), f"{label}.children")
    result: dict[str, Any] = {
        "role": _text(raw["role"], f"{label}.role", 120),
        "shape": shape,
        "children": children,
        "transform": _transform(raw.get("transform"), f"{label}.transform"),
        "tags": _names(raw.get("tags", []), f"{label}.tags"),
    }
    refs = [shape, *children]
    for field in ("material", "collision"):
        if field in raw:
            ref = _identifier(raw[field], f"{label}.{field}")
            result[field] = ref
            refs.append(ref)
    return result, refs


def _socket_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"owner", "name", "transform", "accepts", "required"}, {"owner", "name", "accepts"})
    owner = _identifier(raw["owner"], f"{label}.owner")
    return {
        "owner": owner,
        "name": _identifier(raw["name"], f"{label}.name"),
        "transform": _transform(raw.get("transform"), f"{label}.transform"),
        "accepts": _names(raw["accepts"], f"{label}.accepts", allow_empty=False),
        "required": _boolean(raw.get("required", False), f"{label}.required"),
    }, [owner]


def _lod_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"metric", "representations"}, {"metric", "representations"})
    metric = _text(raw["metric"], f"{label}.metric", 40).casefold()
    if metric != "distance":
        raise AssetAtomError(f"{label}.metric must be distance in v0.1")
    rows = raw["representations"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 16:
        raise AssetAtomError(f"{label}.representations must contain 1..16 entries")
    normalized: list[dict[str, Any]] = []
    refs: list[str] = []
    expected_min = 0.0
    for index, row in enumerate(rows):
        row = _object(
            row,
            f"{label}.representations[{index}]",
            {"id", "min_distance", "max_distance", "atom"},
            {"id", "min_distance", "max_distance", "atom"},
        )
        minimum = _number(row["min_distance"], f"{label}.representations[{index}].min_distance", 0)
        if minimum != expected_min:
            raise AssetAtomError(
                f"{label}.representations must provide exact continuous coverage",
                {"index": index, "expected_min_distance": expected_min, "actual_min_distance": minimum},
            )
        maximum_raw = row["max_distance"]
        if maximum_raw is None:
            if index != len(rows) - 1:
                raise AssetAtomError(f"{label}.representations only the final max_distance may be null")
            maximum = None
        else:
            maximum = _number(maximum_raw, f"{label}.representations[{index}].max_distance", minimum)
            if maximum <= minimum:
                raise AssetAtomError(f"{label}.representations max_distance must exceed min_distance")
            expected_min = maximum
        atom = _identifier(row["atom"], f"{label}.representations[{index}].atom")
        normalized.append({
            "id": _identifier(row["id"], f"{label}.representations[{index}].id"),
            "min_distance": minimum,
            "max_distance": maximum,
            "atom": atom,
        })
        refs.append(atom)
    if normalized[-1]["max_distance"] is not None:
        raise AssetAtomError(f"{label}.representations final max_distance must be null")
    ids = [row["id"] for row in normalized]
    if len(ids) != len(set(ids)):
        raise AssetAtomError(f"{label}.representations ids must be unique")
    return {"metric": metric, "representations": normalized}, refs


def _animation_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"name", "duration_seconds", "loop", "tracks"}, {"name", "duration_seconds", "tracks"})
    duration = _number(raw["duration_seconds"], f"{label}.duration_seconds", 0.000001, 86400)
    tracks = raw["tracks"]
    if not isinstance(tracks, list) or not 1 <= len(tracks) <= MAX_LIST:
        raise AssetAtomError(f"{label}.tracks must contain 1..{MAX_LIST} entries")
    normalized_tracks: list[dict[str, Any]] = []
    refs: list[str] = []
    for track_index, track in enumerate(tracks):
        track_label = f"{label}.tracks[{track_index}]"
        track = _object(track, track_label, {"target", "property", "interpolation", "keyframes"}, {"target", "property", "interpolation", "keyframes"})
        interpolation = _text(track["interpolation"], f"{track_label}.interpolation", 20).casefold()
        if interpolation not in {"step", "linear", "cubic"}:
            raise AssetAtomError(f"{track_label}.interpolation is unsupported")
        keyframes = track["keyframes"]
        if not isinstance(keyframes, list) or not 1 <= len(keyframes) <= 256:
            raise AssetAtomError(f"{track_label}.keyframes must contain 1..256 entries")
        normalized_keyframes: list[dict[str, Any]] = []
        previous = -1.0
        for key_index, keyframe in enumerate(keyframes):
            key_label = f"{track_label}.keyframes[{key_index}]"
            keyframe = _object(keyframe, key_label, {"time", "value"}, {"time", "value"})
            time = _number(keyframe["time"], f"{key_label}.time", 0, duration)
            if time <= previous:
                raise AssetAtomError(f"{track_label}.keyframe times must be strictly increasing")
            previous = time
            normalized_keyframes.append({"time": time, "value": _json_value(keyframe["value"], f"{key_label}.value")})
        target = _identifier(track["target"], f"{track_label}.target")
        normalized_tracks.append({
            "target": target,
            "property": _text(track["property"], f"{track_label}.property", 120),
            "interpolation": interpolation,
            "keyframes": normalized_keyframes,
        })
        refs.append(target)
    return {
        "name": _text(raw["name"], f"{label}.name", 120),
        "duration_seconds": duration,
        "loop": _boolean(raw.get("loop", False), f"{label}.loop"),
        "tracks": normalized_tracks,
    }, refs


def _state_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(raw, label, {"name", "activates", "deactivates", "overrides"}, {"name"})
    activates = _names(raw.get("activates", []), f"{label}.activates")
    deactivates = _names(raw.get("deactivates", []), f"{label}.deactivates")
    overlap = sorted(set(activates) & set(deactivates))
    if overlap:
        raise AssetAtomError(f"{label} cannot activate and deactivate the same atoms", {"atoms": overlap})
    overrides = raw.get("overrides", {})
    if not isinstance(overrides, dict) or len(overrides) > MAX_LIST:
        raise AssetAtomError(f"{label}.overrides must map at most {MAX_LIST} atom ids to objects")
    normalized_overrides: dict[str, Any] = {}
    for ref, value in overrides.items():
        atom_id = _identifier(ref, f"{label}.overrides key")
        if not isinstance(value, dict):
            raise AssetAtomError(f"{label}.overrides.{atom_id} must be an object")
        normalized_overrides[atom_id] = _json_value(value, f"{label}.overrides.{atom_id}")
    refs = [*activates, *deactivates, *normalized_overrides]
    return {
        "name": _text(raw["name"], f"{label}.name", 120),
        "activates": activates,
        "deactivates": deactivates,
        "overrides": normalized_overrides,
    }, refs


def _behavior_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(
        raw,
        label,
        {"name", "target", "trigger", "animation", "from_state", "to_state", "conditions"},
        {"name", "target", "trigger"},
    )
    target = _identifier(raw["target"], f"{label}.target")
    result: dict[str, Any] = {
        "name": _text(raw["name"], f"{label}.name", 120),
        "target": target,
        "trigger": _identifier(raw["trigger"], f"{label}.trigger"),
        "conditions": _json_value(raw.get("conditions", {}), f"{label}.conditions"),
    }
    if not isinstance(result["conditions"], dict):
        raise AssetAtomError(f"{label}.conditions must be an object")
    refs = [target]
    for field in ("animation", "from_state", "to_state"):
        if field in raw:
            ref = _identifier(raw[field], f"{label}.{field}")
            result[field] = ref
            refs.append(ref)
    return result, refs


def _metadata_payload(raw: Any, label: str) -> tuple[dict[str, Any], list[str]]:
    raw = _object(
        raw,
        label,
        {"name", "category", "dimensions", "era", "factions", "cost", "rarity", "tech_requirements", "tags"},
        {"name", "category", "dimensions"},
    )
    result: dict[str, Any] = {
        "name": _text(raw["name"], f"{label}.name", 160),
        "category": _identifier(raw["category"], f"{label}.category"),
        "dimensions": _dimensions(raw["dimensions"], f"{label}.dimensions"),
        "factions": _names(raw.get("factions", []), f"{label}.factions"),
        "tech_requirements": _names(raw.get("tech_requirements", []), f"{label}.tech_requirements"),
        "tags": _names(raw.get("tags", []), f"{label}.tags"),
    }
    for field in ("era", "rarity"):
        if field in raw:
            result[field] = _text(raw[field], f"{label}.{field}", 80)
    if "cost" in raw:
        cost = _object(raw["cost"], f"{label}.cost", {"amount", "currency"}, {"amount", "currency"})
        result["cost"] = {
            "amount": _number(cost["amount"], f"{label}.cost.amount", 0),
            "currency": _identifier(cost["currency"], f"{label}.cost.currency"),
        }
    return result, []


PayloadValidator = Callable[[Any, str], tuple[dict[str, Any], list[str]]]
PAYLOAD_VALIDATORS: dict[str, PayloadValidator] = {
    "shape": _shape_payload,
    "part": _part_payload,
    "texture": _texture_payload,
    "material": _material_payload,
    "palette": _palette_payload,
    "gradient": _gradient_payload,
    "mask": _mask_payload,
    "overlay": _overlay_payload,
    "shader": _shader_payload,
    "animation": _animation_payload,
    "state": _state_payload,
    "behavior": _behavior_payload,
    "lod": _lod_payload,
    "collision": _collision_payload,
    "socket": _socket_payload,
    "metadata": _metadata_payload,
}


def _expect_kind(atoms: dict[str, dict[str, Any]], owner: str, ref: str, allowed: set[str], field: str) -> None:
    target = atoms.get(ref)
    if target is None:
        raise AssetAtomError("asset atom reference does not resolve", {"atom": owner, "field": field, "reference": ref})
    if target["kind"] not in allowed:
        raise AssetAtomError(
            "asset atom reference has the wrong kind",
            {"atom": owner, "field": field, "reference": ref, "expected_kinds": sorted(allowed), "actual_kind": target["kind"]},
        )


def _validate_reference_kinds(atoms: dict[str, dict[str, Any]]) -> None:
    for atom_id, atom in atoms.items():
        kind = atom["kind"]
        payload = atom["payload"]
        if kind == "gradient" and "palette" in payload:
            _expect_kind(atoms, atom_id, payload["palette"], {"palette"}, "palette")
            palette_roles = set(atoms[payload["palette"]]["payload"]["colors"])
            unknown_roles = sorted(
                {stop["palette_role"] for stop in payload["stops"] if "palette_role" in stop} - palette_roles
            )
            if unknown_roles:
                raise AssetAtomError("gradient references unknown palette roles", {"atom": atom_id, "unknown_roles": unknown_roles})
        elif kind == "mask":
            _expect_kind(atoms, atom_id, payload["source"], {"texture"}, "source")
        elif kind == "overlay":
            _expect_kind(atoms, atom_id, payload["source"], {"texture", "gradient", "material"}, "source")
            if "mask" in payload:
                _expect_kind(atoms, atom_id, payload["mask"], {"mask"}, "mask")
        elif kind == "material":
            for channel, ref in payload["texture_bindings"].items():
                _expect_kind(atoms, atom_id, ref, {"texture"}, f"texture_bindings.{channel}")
                actual_channel = atoms[ref]["payload"]["channel"]
                if actual_channel != channel:
                    raise AssetAtomError(
                        "material texture binding channel does not match the texture atom channel",
                        {"atom": atom_id, "binding_channel": channel, "texture": ref, "texture_channel": actual_channel},
                    )
            for field, expected in (("shader", {"shader"}), ("palette", {"palette"}), ("gradient", {"gradient"})):
                if field in payload:
                    _expect_kind(atoms, atom_id, payload[field], expected, field)
            for ref in payload["masks"]:
                _expect_kind(atoms, atom_id, ref, {"mask"}, "masks")
            for ref in payload["overlays"]:
                _expect_kind(atoms, atom_id, ref, {"overlay"}, "overlays")
        elif kind == "part":
            _expect_kind(atoms, atom_id, payload["shape"], {"shape"}, "shape")
            for ref in payload["children"]:
                _expect_kind(atoms, atom_id, ref, {"part"}, "children")
            if "material" in payload:
                _expect_kind(atoms, atom_id, payload["material"], {"material"}, "material")
            if "collision" in payload:
                _expect_kind(atoms, atom_id, payload["collision"], {"collision"}, "collision")
        elif kind == "socket":
            _expect_kind(atoms, atom_id, payload["owner"], {"part"}, "owner")
        elif kind == "collision" and "source_shape" in payload:
            _expect_kind(atoms, atom_id, payload["source_shape"], {"shape"}, "source_shape")
        elif kind == "lod":
            for index, row in enumerate(payload["representations"]):
                _expect_kind(atoms, atom_id, row["atom"], {"part", "shape"}, f"representations[{index}].atom")
        elif kind == "animation":
            for index, track in enumerate(payload["tracks"]):
                _expect_kind(atoms, atom_id, track["target"], {"part", "socket", "material", "shader"}, f"tracks[{index}].target")
        elif kind == "behavior":
            _expect_kind(atoms, atom_id, payload["target"], {"part", "socket"}, "target")
            if "animation" in payload:
                _expect_kind(atoms, atom_id, payload["animation"], {"animation"}, "animation")
            for field in ("from_state", "to_state"):
                if field in payload:
                    _expect_kind(atoms, atom_id, payload[field], {"state"}, field)


def _dependency_order(atoms: dict[str, dict[str, Any]]) -> list[str]:
    visiting: list[str] = []
    visited: set[str] = set()
    order: list[str] = []

    def visit(atom_id: str) -> None:
        if atom_id in visited:
            return
        if atom_id in visiting:
            start = visiting.index(atom_id)
            raise AssetAtomError("asset atom dependency cycle detected", {"cycle": [*visiting[start:], atom_id]})
        visiting.append(atom_id)
        for dependency in sorted(atoms[atom_id]["uses"]):
            visit(dependency)
        visiting.pop()
        visited.add(atom_id)
        order.append(atom_id)

    for atom_id in sorted(atoms):
        visit(atom_id)
    return order


def _provenance(raw: Any, label: str) -> dict[str, Any]:
    raw = _object(raw, label, {"kind", "basis", "creator", "source_uri", "license"}, {"kind", "basis", "creator"})
    result = {
        "kind": _identifier(raw["kind"], f"{label}.kind"),
        "basis": _text(raw["basis"], f"{label}.basis", 1000),
        "creator": _text(raw["creator"], f"{label}.creator", 200),
    }
    for field in ("source_uri", "license"):
        if field in raw:
            result[field] = _text(raw[field], f"{label}.{field}", 1000 if field == "source_uri" else 120)
    return result


def validate_asset_package(raw: Any) -> dict[str, Any]:
    raw = _object(
        raw,
        "asset package",
        {"schema", "id", "version", "asset_class", "root_atoms", "atoms", "provenance", "limitations"},
        {"schema", "id", "version", "asset_class", "root_atoms", "atoms", "provenance", "limitations"},
    )
    if raw["schema"] != ASSET_ATOM_SCHEMA:
        raise AssetAtomError(
            "asset package schema is unsupported",
            {"expected": ASSET_ATOM_SCHEMA, "actual": raw["schema"]},
        )
    package_id = _identifier(raw["id"], "asset package.id")
    version = _text(raw["version"], "asset package.version", 64)
    if VERSION_RE.fullmatch(version) is None:
        raise AssetAtomError("asset package.version is invalid", {"version": version})
    root_atoms = _names(raw["root_atoms"], "asset package.root_atoms", allow_empty=False)
    atoms_raw = raw["atoms"]
    if not isinstance(atoms_raw, list) or not 1 <= len(atoms_raw) <= MAX_ATOMS:
        raise AssetAtomError(f"asset package.atoms must contain 1..{MAX_ATOMS} entries")

    atoms: dict[str, dict[str, Any]] = {}
    for index, atom_raw in enumerate(atoms_raw):
        atom_label = f"asset package.atoms[{index}]"
        atom_raw = _object(atom_raw, atom_label, {"id", "kind", "purpose", "uses", "payload"}, {"id", "kind", "purpose", "uses", "payload"})
        atom_id = _identifier(atom_raw["id"], f"{atom_label}.id")
        if atom_id in atoms:
            raise AssetAtomError("asset atom ids must be unique", {"duplicate": atom_id})
        kind = _text(atom_raw["kind"], f"{atom_label}.kind", 40).casefold()
        validator = PAYLOAD_VALIDATORS.get(kind)
        if validator is None:
            raise AssetAtomError(f"{atom_label}.kind is unsupported", {"kind": kind, "supported_kinds": sorted(ATOM_KINDS)})
        payload, inferred_refs = validator(atom_raw["payload"], f"{atom_label}.payload")
        declared_refs = _names(atom_raw["uses"], f"{atom_label}.uses")
        inferred_set = set(inferred_refs)
        if set(declared_refs) != inferred_set:
            raise AssetAtomError(
                "asset atom uses must exactly match payload references",
                {
                    "atom": atom_id,
                    "missing_from_uses": sorted(inferred_set - set(declared_refs)),
                    "unexpected_in_uses": sorted(set(declared_refs) - inferred_set),
                },
            )
        atoms[atom_id] = {
            "id": atom_id,
            "kind": kind,
            "purpose": _text(atom_raw["purpose"], f"{atom_label}.purpose", 400),
            "uses": sorted(declared_refs),
            "payload": payload,
        }

    missing_roots = sorted(set(root_atoms) - set(atoms))
    if missing_roots:
        raise AssetAtomError("asset package root atoms do not resolve", {"missing_root_atoms": missing_roots})
    unresolved = sorted({ref for atom in atoms.values() for ref in atom["uses"] if ref not in atoms})
    if unresolved:
        raise AssetAtomError("asset package contains unresolved atom references", {"unresolved_references": unresolved})
    _validate_reference_kinds(atoms)
    dependency_order = _dependency_order(atoms)
    limitations = _texts(raw["limitations"], "asset package.limitations", allow_empty=False)

    normalized = {
        "schema": ASSET_ATOM_SCHEMA,
        "id": package_id,
        "version": version,
        "asset_class": _identifier(raw["asset_class"], "asset package.asset_class"),
        "root_atoms": root_atoms,
        "atoms": [atoms[atom_id] for atom_id in sorted(atoms)],
        "provenance": _provenance(raw["provenance"], "asset package.provenance"),
        "limitations": limitations,
    }
    normalized["validation"] = {
        "truth_status": "DETERMINISTIC_ASSET_ATOM_PACKAGE_VALIDATION",
        "atom_count": len(atoms),
        "atom_kinds": sorted({atom["kind"] for atom in atoms.values()}),
        "dependency_order": dependency_order,
        "all_references_resolved": True,
        "acyclic": True,
    }
    return normalized


def _without_validation(package: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in package.items() if key != "validation"}


def _resource_evidence(atoms: dict[str, dict[str, Any]]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    for atom_id in sorted(atoms):
        atom = atoms[atom_id]
        resource: dict[str, Any] | None = None
        if atom["kind"] == "shape" and "source" in atom["payload"]:
            resource = atom["payload"]["source"]
        elif atom["kind"] == "texture":
            resource = atom["payload"]["resource"]
        elif atom["kind"] == "shader" and "runtime_source" in atom["payload"]:
            resource = atom["payload"]["runtime_source"]
        if resource is not None:
            rows.append({
                "atom": atom_id,
                "uri": resource["uri"],
                "declared_digest": resource.get("digest"),
                "bytes_fetched_or_verified": False,
            })
    return {
        "truth_status": "DECLARED_RESOURCE_REFERENCES_NOT_FETCHED",
        "resource_count": len(rows),
        "declared_digest_count": sum(row["declared_digest"] is not None for row in rows),
        "resources": rows,
    }


def _select_atom(atoms: dict[str, dict[str, Any]], atom_id: Any, kind: str, label: str) -> str | None:
    if atom_id is None:
        return None
    selected = _identifier(atom_id, label)
    atom = atoms.get(selected)
    if atom is None or atom["kind"] != kind:
        raise AssetAtomError(
            f"{label} must name an existing {kind} atom",
            {"selection": selected, "actual_kind": atom["kind"] if atom else None},
        )
    return selected


def _resolve_palette_overrides(atoms: dict[str, dict[str, Any]], raw: Any) -> dict[str, dict[str, str]]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict) or len(raw) > 64:
        raise AssetAtomError("palette_overrides must be an object keyed by palette atom id")
    resolved: dict[str, dict[str, str]] = {
        atom_id: copy.deepcopy(atom["payload"]["colors"])
        for atom_id, atom in atoms.items()
        if atom["kind"] == "palette"
    }
    for raw_palette_id, raw_roles in raw.items():
        palette_id = _identifier(raw_palette_id, "palette_overrides key")
        if palette_id not in resolved:
            raise AssetAtomError("palette override names no palette atom", {"palette": palette_id})
        if not isinstance(raw_roles, dict) or not raw_roles:
            raise AssetAtomError("palette override roles must be a non-empty object", {"palette": palette_id})
        unknown_roles = sorted(set(raw_roles) - set(resolved[palette_id]))
        if unknown_roles:
            raise AssetAtomError("palette override names unknown roles", {"palette": palette_id, "unknown_roles": unknown_roles})
        for role, color in raw_roles.items():
            resolved[palette_id][role] = _color(color, f"palette_overrides.{palette_id}.{role}")
    return resolved


def compile_asset_package(
    raw: Any,
    *,
    observation_distance: Any = 0,
    state: Any = None,
    animation: Any = None,
    palette_overrides: Any = None,
) -> dict[str, Any]:
    package = validate_asset_package(raw)
    package_body = _without_validation(package)
    atoms = {atom["id"]: atom for atom in package["atoms"]}
    distance = _number(observation_distance, "observation_distance", 0)
    state_id = _select_atom(atoms, state, "state", "state")
    animation_id = _select_atom(atoms, animation, "animation", "animation")
    resolved_palettes = _resolve_palette_overrides(atoms, palette_overrides)

    selected_lods: dict[str, dict[str, Any]] = {}
    for atom_id in sorted(atoms):
        atom = atoms[atom_id]
        if atom["kind"] != "lod":
            continue
        selected = next(
            (
                row
                for row in atom["payload"]["representations"]
                if distance >= row["min_distance"]
                and (row["max_distance"] is None or distance < row["max_distance"])
            ),
            None,
        )
        if selected is None:
            raise AssetAtomError("validated LOD unexpectedly has no distance match", {"lod": atom_id, "distance": distance})
        selected_lods[atom_id] = copy.deepcopy(selected)

    selected_state = copy.deepcopy(atoms[state_id]) if state_id else None
    selected_animation = copy.deepcopy(atoms[animation_id]) if animation_id else None
    sockets = [copy.deepcopy(atom) for atom in package["atoms"] if atom["kind"] == "socket"]
    package_digest = _digest(package_body)
    instance_body: dict[str, Any] = {
        "schema": ASSET_INSTANCE_SCHEMA,
        "package_ref": f"{package['id']}@{package['version']}",
        "package_digest": package_digest,
        "selection": {
            "observation_distance": distance,
            "state": state_id,
            "animation": animation_id,
        },
        "dependency_order": package["validation"]["dependency_order"],
        "selected_lods": selected_lods,
        "resolved_palettes": resolved_palettes,
        "selected_state": selected_state,
        "selected_animation": selected_animation,
        "sockets": sockets,
        "resource_evidence": _resource_evidence(atoms),
        "limitations": [
            "this compiler validates and resolves renderer-neutral descriptors; it does not render meshes or sprites",
            "shader instructions and animation clips are described but not executed",
            "collision shapes are described but no physics simulation is run",
            "external resource bytes are not fetched or verified by this compiler",
        ],
    }
    instance = {**instance_body, "instance_digest": _digest(instance_body)}
    return {
        "truth_status": "DETERMINISTIC_ASSET_INSTANCE_COMPILED",
        "package": package_body,
        "package_validation": package["validation"],
        "package_digest": package_digest,
        "instance": instance,
    }


def materialize_asset_package(
    target: Path,
    raw: Any,
    *,
    observation_distance: Any = 0,
    state: Any = None,
    animation: Any = None,
    palette_overrides: Any = None,
    replace: bool = False,
) -> dict[str, Any]:
    compilation = compile_asset_package(
        raw,
        observation_distance=observation_distance,
        state=state,
        animation=animation,
        palette_overrides=palette_overrides,
    )
    files = {
        "asset.package.json": json.dumps(compilation["package"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
        "asset.instance.json": json.dumps(compilation["instance"], indent=2, ensure_ascii=False, sort_keys=True) + "\n",
    }
    project = build_project(
        target=target,
        files=files,
        project_type="generic",
        checks=[
            {"type": "file-set", "files": sorted(files), "mode": "exact"},
            {"type": "json-valid", "path": "asset.package.json"},
            {"type": "json-valid", "path": "asset.instance.json"},
        ],
        replace=replace,
        publish_mode="validated",
    )
    return {
        "truth_status": "VALIDATED_ASSET_DESCRIPTOR_PROJECT",
        "package_ref": compilation["instance"]["package_ref"],
        "package_digest": compilation["package_digest"],
        "instance_digest": compilation["instance"]["instance_digest"],
        "compilation": compilation,
        **project,
    }


class AssetPackageLibrary:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.directory = self.root / "asset-packages"
        self._packages: dict[str, dict[str, Any]] = {}
        self._sources: dict[str, str] = {}
        if not self.directory.exists():
            return
        if not self.directory.is_dir() or self.directory.is_symlink():
            raise AssetAtomError("asset-packages must be a real directory inside the machine body")
        for path in sorted(self.directory.glob("*.json")):
            if path.is_symlink():
                raise AssetAtomError("asset package files may not be symlinks", {"path": str(path)})
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                package = validate_asset_package(raw)
            except (OSError, UnicodeError, json.JSONDecodeError, AssetAtomError) as exc:
                details = getattr(exc, "details", {})
                raise AssetAtomError(f"invalid installed asset package: {path.name}: {exc}", {"path": str(path), **details}) from exc
            ref = f"{package['id']}@{package['version']}"
            if ref in self._packages:
                raise AssetAtomError("duplicate installed asset package reference", {"ref": ref, "paths": [self._sources[ref], str(path)]})
            self._packages[ref] = package
            self._sources[ref] = str(path)

    def resolve(self, ref: Any) -> dict[str, Any]:
        exact_ref = _text(ref, "asset package ref", 200)
        package = self._packages.get(exact_ref)
        if package is None:
            raise AssetAtomError("asset package ref is not installed", {"ref": exact_ref, "available_refs": sorted(self._packages)})
        return _without_validation(package)

    def inspect(self, ref: Any) -> dict[str, Any]:
        exact_ref = _text(ref, "asset package ref", 200)
        package = self._packages.get(exact_ref)
        if package is None:
            raise AssetAtomError("asset package ref is not installed", {"ref": exact_ref, "available_refs": sorted(self._packages)})
        return {**copy.deepcopy(package), "ref": exact_ref, "source": self._sources[exact_ref]}

    def list(self, *, asset_class: str | None = None, atom_kind: str | None = None) -> list[dict[str, Any]]:
        normalized_class = _identifier(asset_class, "asset_class") if asset_class is not None else None
        normalized_kind = _text(atom_kind, "atom_kind", 40).casefold() if atom_kind is not None else None
        if normalized_kind is not None and normalized_kind not in ATOM_KINDS:
            raise AssetAtomError("atom_kind is unsupported", {"atom_kind": normalized_kind})
        rows: list[dict[str, Any]] = []
        for ref in sorted(self._packages):
            package = self._packages[ref]
            kinds = package["validation"]["atom_kinds"]
            if normalized_class is not None and package["asset_class"] != normalized_class:
                continue
            if normalized_kind is not None and normalized_kind not in kinds:
                continue
            rows.append({
                "ref": ref,
                "id": package["id"],
                "version": package["version"],
                "asset_class": package["asset_class"],
                "root_atoms": package["root_atoms"],
                "atom_count": package["validation"]["atom_count"],
                "atom_kinds": kinds,
                "source": self._sources[ref],
            })
        return rows

    def summary(self) -> dict[str, Any]:
        kind_counts = {kind: 0 for kind in sorted(ATOM_KINDS)}
        total_atoms = 0
        for package in self._packages.values():
            total_atoms += package["validation"]["atom_count"]
            for atom in package["atoms"]:
                kind_counts[atom["kind"]] += 1
        return {
            "truth_status": "EXACT_LOCAL_ASSET_PACKAGE_LIBRARY",
            "schema": ASSET_ATOM_SCHEMA,
            "package_count": len(self._packages),
            "atom_count": total_atoms,
            "refs": sorted(self._packages),
            "atom_kind_counts": kind_counts,
            "runtime_execution_proven": False,
        }


def asset_atom_schema_summary() -> dict[str, Any]:
    return {
        "truth_status": "DECLARED_CLOSED_ASSET_ATOM_SCHEMA",
        "package_schema": ASSET_ATOM_SCHEMA,
        "instance_schema": ASSET_INSTANCE_SCHEMA,
        "atom_kinds": sorted(ATOM_KINDS),
        "atom_kind_count": len(ATOM_KINDS),
        "reference_rule": "each atom uses list must exactly equal its payload's direct atom references",
        "selection": ["distance-bounded LOD", "exact state", "exact animation", "palette role overrides"],
        "runtime_boundary": "descriptor validation and deterministic selection only; no rendering, shader execution, animation runtime, physics, or external byte fetch",
    }

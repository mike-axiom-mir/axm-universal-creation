from __future__ import annotations

import hashlib
import json
import math
import struct
import zlib
from typing import Any, Sequence


SCHEMA = "axm.procedural-visual-assets/v0.1"
MAX_SIZE = 2048
DEFAULT_SIZE = 256

TEXTURES = (
    "noise", "smooth-noise", "grain", "checker", "stripes", "diagonal-stripes",
    "dots", "grid", "brick", "tile", "wood", "marble", "stone", "concrete",
    "brushed-metal", "hammered-metal", "fabric", "carbon-fiber", "leather", "paper",
    "terrain", "camouflage", "circuit", "sci-fi-panel", "hex", "terrazzo", "scales",
)
GRADIENTS = (
    "linear", "radial", "conic", "diamond", "reflected", "stepped",
    "sunset", "aurora", "neon", "metallic", "heatmap", "holographic",
)
MATERIALS = (
    "wood", "stone", "concrete", "iron", "steel", "copper", "gold", "plastic",
    "rubber", "glass", "fabric", "leather", "ceramic", "emissive", "sci-fi",
)
FIXTURES = (
    "button", "knob", "slider", "toggle", "panel", "vent", "grille", "handle",
    "hinge", "bracket", "bolt", "rivet", "screw", "washer", "gear", "pipe",
    "elbow", "window", "light", "gauge", "badge", "screen", "port",
)
OBJ_FIXTURES = (
    "button", "knob", "panel", "vent", "handle", "hinge", "bracket", "bolt",
    "rivet", "screw", "washer", "gear", "pipe", "elbow", "light", "port",
)
DECALS = (
    "arrow", "chevron", "warning", "hazard-stripes", "target", "crosshair",
    "panel-lines", "serial-label", "circuit-trace", "scratch", "crack", "drip",
)
PALETTES = (
    "analogous", "complementary", "split-complementary", "triadic", "tetradic",
    "monochrome", "warm", "cool", "earth", "neon",
)

DEFAULT_GRADIENT_STOPS: dict[str, tuple[str, ...]] = {
    "linear": ("#101820", "#4A90E2", "#F2F7FF"),
    "radial": ("#FFFFFF", "#6AA9FF", "#111827"),
    "conic": ("#FF3366", "#FFCC33", "#33D17A", "#3388FF", "#AA55FF", "#FF3366"),
    "diamond": ("#F8FAFC", "#94A3B8", "#0F172A"),
    "reflected": ("#0B1020", "#56D8FF", "#FFFFFF", "#56D8FF", "#0B1020"),
    "stepped": ("#111827", "#1D4ED8", "#06B6D4", "#F8FAFC"),
    "sunset": ("#25134D", "#9C3B8F", "#F56A63", "#FFB347", "#FFE0A3"),
    "aurora": ("#071A2B", "#075E54", "#28D7A1", "#74F7FF", "#A77CFF"),
    "neon": ("#090014", "#FF2BD6", "#9D4EDD", "#00E5FF", "#15FFB1"),
    "metallic": ("#111318", "#727983", "#F3F5F7", "#8D949C", "#23272E"),
    "heatmap": ("#050B2C", "#1565C0", "#00BCD4", "#FFEB3B", "#FF5722", "#7F0000"),
    "holographic": ("#FF8BD7", "#8FE9FF", "#C3FFB0", "#FFF2A8", "#C5A5FF", "#FF8BD7"),
}

MATERIAL_SPECS: dict[str, dict[str, Any]] = {
    "wood": {"pattern": "wood", "colors": ("#2C160C", "#7A421F", "#D39A59"), "roughness": .66, "metallic": .0},
    "stone": {"pattern": "stone", "colors": ("#242629", "#74777C", "#C7CACD"), "roughness": .82, "metallic": .0},
    "concrete": {"pattern": "concrete", "colors": ("#303438", "#777B7D", "#B7BAB8"), "roughness": .9, "metallic": .0},
    "iron": {"pattern": "hammered-metal", "colors": ("#17191B", "#535A60", "#979FA5"), "roughness": .48, "metallic": .92},
    "steel": {"pattern": "brushed-metal", "colors": ("#2D3338", "#89939C", "#E4E9ED"), "roughness": .3, "metallic": .96},
    "copper": {"pattern": "brushed-metal", "colors": ("#3B160D", "#B55B34", "#F0A36F"), "roughness": .34, "metallic": .91},
    "gold": {"pattern": "brushed-metal", "colors": ("#4E3300", "#C99B21", "#FFE28A"), "roughness": .24, "metallic": 1.0},
    "plastic": {"pattern": "smooth-noise", "colors": ("#111827", "#2563EB", "#8EC5FF"), "roughness": .42, "metallic": .0},
    "rubber": {"pattern": "grain", "colors": ("#08090A", "#1C1F22", "#33373B"), "roughness": .94, "metallic": .0},
    "glass": {"pattern": "smooth-noise", "colors": ("#8BE3FF", "#D9F8FF", "#FFFFFF"), "roughness": .08, "metallic": .0, "opacity": .22},
    "fabric": {"pattern": "fabric", "colors": ("#291B35", "#6F4B8B", "#C6A7DF"), "roughness": .92, "metallic": .0},
    "leather": {"pattern": "leather", "colors": ("#1F0E08", "#6E321B", "#A9673F"), "roughness": .72, "metallic": .0},
    "ceramic": {"pattern": "tile", "colors": ("#A7B0B8", "#E8EEF2", "#FFFFFF"), "roughness": .18, "metallic": .0},
    "emissive": {"pattern": "circuit", "colors": ("#04121C", "#063B4B", "#1FFFE0"), "roughness": .25, "metallic": .18, "emission": 1.0},
    "sci-fi": {"pattern": "sci-fi-panel", "colors": ("#0B1016", "#26313A", "#8BA0AD"), "roughness": .38, "metallic": .78, "emission": .35},
}


def catalog() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "truth_status": "EXECUTABLE_GENERATOR_CATALOG",
        "dependencies": [],
        "deterministic": True,
        "outputs": {
            "texture": {"formats": ["png"], "kinds": list(TEXTURES)},
            "gradient": {"formats": ["png"], "kinds": list(GRADIENTS)},
            "material": {"formats": ["png", "json"], "kinds": list(MATERIALS), "channels": ["albedo", "roughness", "metallic", "height", "normal", "ao", "emissive", "opacity"]},
            "fixture": {"formats": ["svg", "obj"], "kinds": list(FIXTURES), "obj_kinds": list(OBJ_FIXTURES)},
            "decal": {"formats": ["svg"], "kinds": list(DECALS)},
            "palette": {"formats": ["json", "svg"], "kinds": list(PALETTES)},
            "kit": {"formats": ["directory", "json-manifest"], "profiles": ["starter", "full"]},
        },
    }


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return lo if value < lo else hi if value > hi else value


def _byte(value: float) -> int:
    return int(round(_clamp(value) * 255.0))


def _hex_rgb(value: str) -> tuple[int, int, int]:
    text = str(value).strip().lstrip("#")
    if len(text) == 3:
        text = "".join(ch * 2 for ch in text)
    if len(text) != 6 or any(ch not in "0123456789abcdefABCDEF" for ch in text):
        raise ValueError(f"invalid RGB color: {value!r}")
    return tuple(int(text[i:i + 2], 16) for i in (0, 2, 4))


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#" + "".join(f"{max(0, min(255, int(v))):02X}" for v in rgb)


def _mix(a: tuple[int, int, int], b: tuple[int, int, int], t: float) -> tuple[int, int, int]:
    t = _clamp(t)
    return tuple(int(round(a[i] + (b[i] - a[i]) * t)) for i in range(3))


def _sample_stops(stops: Sequence[tuple[int, int, int]], t: float) -> tuple[int, int, int]:
    if not stops:
        return (0, 0, 0)
    if len(stops) == 1:
        return stops[0]
    t = _clamp(t)
    scaled = t * (len(stops) - 1)
    index = min(len(stops) - 2, int(scaled))
    return _mix(stops[index], stops[index + 1], scaled - index)


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)


def png_bytes(width: int, height: int, rows: Sequence[Sequence[Any]], mode: str = "RGB") -> bytes:
    if mode not in {"L", "RGB", "RGBA"}:
        raise ValueError("mode must be L, RGB, or RGBA")
    channels = {"L": 1, "RGB": 3, "RGBA": 4}[mode]
    color_type = {"L": 0, "RGB": 2, "RGBA": 6}[mode]
    raw = bytearray()
    if len(rows) != height:
        raise ValueError("row count does not match height")
    for row in rows:
        if len(row) != width:
            raise ValueError("column count does not match width")
        raw.append(0)
        for pixel in row:
            values = (pixel,) if channels == 1 else tuple(pixel)
            if len(values) != channels:
                raise ValueError("pixel channel count mismatch")
            raw.extend(max(0, min(255, int(v))) for v in values)
    header = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + _chunk(b"IEND", b"")


def _hash2(seed: int, x: int, y: int) -> float:
    n = (int(seed) ^ (x * 374761393) ^ (y * 668265263)) & 0xFFFFFFFF
    n = ((n ^ (n >> 13)) * 1274126177) & 0xFFFFFFFF
    n ^= n >> 16
    return (n & 0xFFFFFFFF) / 4294967295.0


def _fade(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)


def _value_noise(seed: int, x: float, y: float) -> float:
    x0 = math.floor(x)
    y0 = math.floor(y)
    tx = _fade(x - x0)
    ty = _fade(y - y0)
    a = _hash2(seed, x0, y0)
    b = _hash2(seed, x0 + 1, y0)
    c = _hash2(seed, x0, y0 + 1)
    d = _hash2(seed, x0 + 1, y0 + 1)
    ab = a + (b - a) * tx
    cd = c + (d - c) * tx
    return ab + (cd - ab) * ty


def _fbm(seed: int, x: float, y: float, octaves: int = 5) -> float:
    value = 0.0
    amplitude = 0.5
    frequency = 1.0
    total = 0.0
    for octave in range(max(1, octaves)):
        value += _value_noise(seed + octave * 977, x * frequency, y * frequency) * amplitude
        total += amplitude
        amplitude *= 0.5
        frequency *= 2.0
    return value / total if total else 0.0


def _distance_to_hex_edge(x: float, y: float, scale: float) -> float:
    qx = (x / scale) * 1.154700538
    qy = y / scale
    row = round(qy)
    col = round(qx - 0.5 * (row & 1))
    cx = (col + 0.5 * (row & 1)) / 1.154700538 * scale
    cy = row * scale
    dx = abs(x - cx) / scale
    dy = abs(y - cy) / scale
    return max(dx * 0.8660254 + dy * 0.5, dy)

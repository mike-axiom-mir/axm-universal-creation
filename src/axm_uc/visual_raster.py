from __future__ import annotations

import colorsys
import math
import random
from typing import Any, Sequence

from .visual_base import (
    DEFAULT_GRADIENT_STOPS, MATERIAL_SPECS, TEXTURES, GRADIENTS,
    _byte, _clamp, _fbm, _hash2, _hex_rgb, _rgb_hex, _sample_stops, _value_noise,
    _distance_to_hex_edge,
)

def texture_field(kind: str, width: int, height: int, seed: int = 0, scale: float = 1.0) -> list[list[float]]:
    kind = str(kind).strip().casefold()
    if kind not in TEXTURES:
        raise KeyError(f"unknown texture kind: {kind}")
    scale = max(0.05, float(scale))
    inv = 1.0 / max(1, min(width, height))
    rows: list[list[float]] = []
    for y in range(height):
        row: list[float] = []
        v = y / max(1, height - 1)
        for x in range(width):
            u = x / max(1, width - 1)
            sx = x * inv * 8.0 / scale
            sy = y * inv * 8.0 / scale
            n = _fbm(seed, sx, sy, 5)
            if kind == "noise":
                value = _hash2(seed, x, y)
            elif kind == "smooth-noise":
                value = n
            elif kind == "grain":
                value = _clamp(0.48 + (_hash2(seed, x, y) - 0.5) * 0.36 + (n - 0.5) * 0.24)
            elif kind == "checker":
                cell = max(2, int(min(width, height) / (8 * scale)))
                value = 0.22 if ((x // cell) + (y // cell)) % 2 == 0 else 0.82
            elif kind == "stripes":
                value = 0.18 if int(u * 12 / scale) % 2 == 0 else 0.82
            elif kind == "diagonal-stripes":
                value = 0.18 if int((u + v) * 10 / scale) % 2 == 0 else 0.84
            elif kind == "dots":
                cell = max(6, int(min(width, height) / (8 * scale)))
                dx = (x % cell) - cell / 2
                dy = (y % cell) - cell / 2
                value = 0.86 if dx * dx + dy * dy < (cell * 0.22) ** 2 else 0.18
            elif kind == "grid":
                cell = max(4, int(min(width, height) / (10 * scale)))
                line = max(1, cell // 12)
                value = 0.88 if x % cell < line or y % cell < line else 0.2
            elif kind == "brick":
                bw = max(8, int(width / (6 * scale)))
                bh = max(5, int(height / (12 * scale)))
                row_i = y // bh
                xx = (x + (bw // 2 if row_i % 2 else 0)) % bw
                mortar = min(xx, bw - xx, y % bh, bh - (y % bh))
                value = 0.08 if mortar < max(1, min(bw, bh) // 10) else _clamp(0.54 + (n - 0.5) * 0.32)
            elif kind == "tile":
                cell = max(8, int(min(width, height) / (6 * scale)))
                grout = min(x % cell, y % cell, cell - (x % cell), cell - (y % cell))
                value = 0.1 if grout < max(1, cell // 18) else _clamp(0.65 + (n - 0.5) * 0.18)
            elif kind == "wood":
                warp = (n - 0.5) * 2.4
                rings = math.sin((sx + warp) * math.pi * 2.2)
                value = _clamp(0.5 + rings * 0.23 + (n - 0.5) * 0.24)
            elif kind == "marble":
                vein = math.sin((sx * 1.4 + sy * 0.35 + n * 4.0) * math.pi)
                value = _clamp(0.62 + vein * 0.22 + (n - 0.5) * 0.18)
            elif kind == "stone":
                value = _clamp(0.38 + n * 0.5 + abs(n - 0.52) * 0.16)
            elif kind == "concrete":
                speck = 0.18 if _hash2(seed + 13, x, y) > 0.965 else 0.0
                value = _clamp(0.5 + (n - 0.5) * 0.34 - speck)
            elif kind == "brushed-metal":
                streak = _value_noise(seed + 71, x * 0.055 / scale, y * 0.8 / scale)
                fine = _hash2(seed + 31, x, y)
                value = _clamp(0.5 + (streak - 0.5) * 0.44 + (fine - 0.5) * 0.1)
            elif kind == "hammered-metal":
                value = _clamp(0.44 + n * 0.38 + math.sin(n * 28.0) * 0.12)
            elif kind == "fabric":
                wx = 0.5 + 0.5 * math.sin(x * math.pi / max(2.0, 2.8 * scale))
                wy = 0.5 + 0.5 * math.sin(y * math.pi / max(2.0, 2.8 * scale))
                value = _clamp(0.25 + wx * 0.32 + wy * 0.32 + (n - 0.5) * 0.12)
            elif kind == "carbon-fiber":
                cell = max(4, int(8 * scale))
                a = ((x + y) // cell) % 2
                b = ((x - y) // cell) % 2
                value = 0.72 if a == b else 0.26
            elif kind == "leather":
                pores = 0.2 if _hash2(seed + 99, x // 2, y // 2) > 0.92 else 0.0
                value = _clamp(0.48 + (n - 0.5) * 0.4 - pores)
            elif kind == "paper":
                fibers = math.sin((x * 0.25 + _value_noise(seed, 0, y * 0.07) * 8.0)) * 0.04
                value = _clamp(0.72 + (n - 0.5) * 0.16 + fibers)
            elif kind == "terrain":
                value = _clamp(n ** 1.35)
            elif kind == "camouflage":
                value = round(_clamp(n) * 4.0) / 4.0
            elif kind == "circuit":
                cell = max(8, int(min(width, height) / (12 * scale)))
                cx, cy = x // cell, y // cell
                gate = _hash2(seed, cx, cy)
                trace = (x % cell < max(1, cell // 10)) or (y % cell < max(1, cell // 10))
                pad = (x % cell - cell // 2) ** 2 + (y % cell - cell // 2) ** 2 < (cell * 0.18) ** 2
                value = 0.92 if (trace and gate > 0.34) or (pad and gate > 0.18) else 0.12 + n * 0.18
            elif kind == "sci-fi-panel":
                cell = max(12, int(min(width, height) / (6 * scale)))
                border = min(x % cell, y % cell, cell - (x % cell), cell - (y % cell))
                notch = ((x + y) // max(3, cell // 5)) % 5 == 0
                value = 0.08 if border < max(1, cell // 22) else _clamp(0.36 + n * 0.32 + (0.16 if notch else 0.0))
            elif kind == "hex":
                d = _distance_to_hex_edge(float(x), float(y), max(5.0, min(width, height) / (10.0 * scale)))
                value = 0.12 if d > 0.78 else _clamp(0.56 + (n - 0.5) * 0.2)
            elif kind == "terrazzo":
                speck = _hash2(seed + 333, x, y)
                value = _clamp(0.62 + (n - 0.5) * 0.15 + (0.3 if speck > 0.975 else -0.22 if speck < 0.018 else 0.0))
            elif kind == "scales":
                cell = max(8, int(min(width, height) / (10 * scale)))
                yy = y % cell
                xx = (x + (cell // 2 if (y // cell) % 2 else 0)) % cell
                radius = cell * 0.55
                dist = math.sqrt((xx - cell / 2) ** 2 + (yy - cell / 2) ** 2)
                value = _clamp(0.2 + (1.0 - min(1.0, abs(dist - radius) / max(1.0, cell * .22))) * 0.6)
            else:
                raise AssertionError(kind)
            row.append(value)
        rows.append(row)
    return rows


def colorize(field: Sequence[Sequence[float]], colors: Sequence[str]) -> list[list[tuple[int, int, int]]]:
    stops = [_hex_rgb(c) for c in colors]
    return [[_sample_stops(stops, value) for value in row] for row in field]


def gradient_rows(kind: str, width: int, height: int, colors: Sequence[str] | None = None, angle: float = 35.0) -> list[list[tuple[int, int, int]]]:
    kind = str(kind).strip().casefold()
    if kind not in GRADIENTS:
        raise KeyError(f"unknown gradient kind: {kind}")
    stops = [_hex_rgb(c) for c in (colors or DEFAULT_GRADIENT_STOPS[kind])]
    theta = math.radians(float(angle))
    cx, cy = 0.5, 0.5
    rows: list[list[tuple[int, int, int]]] = []
    for y in range(height):
        v = y / max(1, height - 1)
        row: list[tuple[int, int, int]] = []
        for x in range(width):
            u = x / max(1, width - 1)
            dx, dy = u - cx, v - cy
            if kind in {"linear", "sunset", "aurora", "neon", "metallic", "heatmap", "holographic"}:
                t = (dx * math.cos(theta) + dy * math.sin(theta)) + 0.5
                if kind == "holographic":
                    t = (t + math.sin((u + v) * math.pi * 4) * 0.08) % 1.0
            elif kind == "radial":
                t = math.sqrt(dx * dx + dy * dy) / math.sqrt(0.5)
            elif kind == "conic":
                t = (math.atan2(dy, dx) / (math.pi * 2.0) + 1.0) % 1.0
            elif kind == "diamond":
                t = min(1.0, (abs(dx) + abs(dy)) * 1.4)
            elif kind == "reflected":
                projection = dx * math.cos(theta) + dy * math.sin(theta)
                t = min(1.0, abs(projection) * 2.0)
            elif kind == "stepped":
                projection = _clamp((dx * math.cos(theta) + dy * math.sin(theta)) + 0.5)
                t = math.floor(projection * len(stops)) / max(1, len(stops) - 1)
            else:
                raise AssertionError(kind)
            row.append(_sample_stops(stops, t))
        rows.append(row)
    return rows


def _height_to_normal(field: Sequence[Sequence[float]], strength: float = 2.0) -> list[list[tuple[int, int, int]]]:
    h = len(field)
    w = len(field[0]) if h else 0
    rows: list[list[tuple[int, int, int]]] = []
    for y in range(h):
        row: list[tuple[int, int, int]] = []
        ym, yp = max(0, y - 1), min(h - 1, y + 1)
        for x in range(w):
            xm, xp = max(0, x - 1), min(w - 1, x + 1)
            dx = (field[y][xp] - field[y][xm]) * strength
            dy = (field[yp][x] - field[ym][x]) * strength
            nx, ny, nz = -dx, -dy, 1.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            row.append((_byte(nx / length * .5 + .5), _byte(ny / length * .5 + .5), _byte(nz / length * .5 + .5)))
        rows.append(row)
    return rows


def _scalar_rows(field: Sequence[Sequence[float]], transform=lambda x: x) -> list[list[int]]:
    return [[_byte(float(transform(v))) for v in row] for row in field]


def _material_maps(kind: str, size: int, seed: int, scale: float) -> dict[str, tuple[str, list[list[Any]]]]:
    spec = MATERIAL_SPECS[kind]
    field = texture_field(spec["pattern"], size, size, seed=seed, scale=scale)
    albedo = colorize(field, spec["colors"])
    base_rough = float(spec.get("roughness", .5))
    base_metal = float(spec.get("metallic", 0.0))
    opacity = float(spec.get("opacity", 1.0))
    emission = float(spec.get("emission", 0.0))
    rough = _scalar_rows(field, lambda v: _clamp(base_rough + (v - .5) * .24))
    metallic = _scalar_rows(field, lambda v: _clamp(base_metal + (v - .5) * .08))
    height = _scalar_rows(field)
    normal = _height_to_normal(field, strength=2.8)
    ao = _scalar_rows(field, lambda v: _clamp(.72 + v * .28))
    emissive = colorize(field, ("#000000", spec["colors"][-1])) if emission > 0 else [[(0, 0, 0) for _ in range(size)] for _ in range(size)]
    if emission > 0:
        emissive = [[tuple(int(channel * min(1.0, emission)) for channel in pixel) for pixel in row] for row in emissive]
    opacity_rows = [[_byte(opacity) for _ in range(size)] for _ in range(size)]
    return {
        "albedo": ("RGB", albedo),
        "roughness": ("L", rough),
        "metallic": ("L", metallic),
        "height": ("L", height),
        "normal": ("RGB", normal),
        "ao": ("L", ao),
        "emissive": ("RGB", emissive),
        "opacity": ("L", opacity_rows),
    }


def _palette(kind: str, seed: int = 0, count: int = 7) -> list[str]:
    rng = random.Random(seed)
    count = max(2, min(16, int(count)))
    base = rng.random()
    if kind == "analogous":
        hues = [base + (i - (count - 1) / 2) * .035 for i in range(count)]
        sats = [.62] * count
        vals = [.88 - .22 * abs(i - (count - 1) / 2) / max(1, count) for i in range(count)]
    elif kind == "complementary":
        hues = [base if i < math.ceil(count / 2) else base + .5 for i in range(count)]
        sats = [.65 + (i % 3) * .08 for i in range(count)]
        vals = [.48 + (i / max(1, count - 1)) * .48 for i in range(count)]
    elif kind == "split-complementary":
        anchors = [base, base + .42, base + .58]
        hues = [anchors[i % 3] + ((i // 3) - 1) * .018 for i in range(count)]
        sats, vals = [.7] * count, [.86] * count
    elif kind == "triadic":
        hues = [base + (i % 3) / 3 for i in range(count)]
        sats = [.72] * count
        vals = [.62 + .34 * ((i // 3 + 1) / (count // 3 + 2)) for i in range(count)]
    elif kind == "tetradic":
        hues = [base + (i % 4) * .25 for i in range(count)]
        sats, vals = [.68] * count, [.84] * count
    elif kind == "monochrome":
        hues = [base] * count
        sats = [.32 + i / max(1, count - 1) * .5 for i in range(count)]
        vals = [.25 + i / max(1, count - 1) * .7 for i in range(count)]
    elif kind == "warm":
        hues = [(.96 + i / max(1, count - 1) * .18) % 1.0 for i in range(count)]
        sats, vals = [.72] * count, [.9] * count
    elif kind == "cool":
        hues = [.48 + i / max(1, count - 1) * .26 for i in range(count)]
        sats, vals = [.64] * count, [.85] * count
    elif kind == "earth":
        predefined = ["#2E241C", "#5A3E2B", "#7C5A3A", "#9A7B4F", "#6C7A4A", "#3E5C4A", "#C4AE84", "#DED1B0"]
        return [predefined[i * (len(predefined)-1) // max(1, count-1)] for i in range(count)]
    elif kind == "neon":
        hues = [(base + i * 0.16) % 1.0 for i in range(count)]
        sats, vals = [.92] * count, [1.0] * count
    else:
        raise KeyError(kind)
    result = []
    for h, s, v in zip(hues, sats, vals):
        r, g, b = colorsys.hsv_to_rgb(h % 1.0, _clamp(s), _clamp(v))
        result.append(_rgb_hex((_byte(r), _byte(g), _byte(b))))
    return result


def _palette_svg(colors: Sequence[str]) -> str:
    width = 120 * len(colors)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} 180" width="{width}" height="180">']
    for i, color in enumerate(colors):
        parts += [f'<rect x="{i*120}" width="120" height="180" fill="{color}"/>', f'<text x="{i*120+60}" y="158" font-family="monospace" font-size="18" text-anchor="middle" fill="#000000" stroke="#FFFFFF" stroke-width="3" paint-order="stroke">{color}</text>']
    parts.append('</svg>')
    return "".join(parts)

from __future__ import annotations

import math
from typing import Any

from .visual_base import _byte, _clamp, _hash2, _hex_rgb, _sample_stops
from .visual_surface import surface_field

PIGMENTS = (
    "painted-metal", "bare-metal", "oxidized-copper", "worn-plastic", "polished-plastic",
    "cloth-dye", "leather-stain", "ceramic-glaze", "stone-mineral", "neon-coat",
    "rubberized-coat", "military-paint", "weathered-wall-paint", "enchanted-pigment",
    "reactor-coat", "biotech-pigment", "vehicle-enamel", "industrial-powdercoat",
)

SMART_MASKS = (
    "edge-wear", "cavity-dirt", "rust", "dust", "moisture", "crack", "peel",
    "scorch", "moss", "snow", "streak", "sun-fade",
)

PIGMENT_SPECS: dict[str, dict[str, Any]] = {
    "painted-metal": {"surface": "spaceship-hull", "colors": ("#17202A", "#42637A", "#8EBCD0"), "roughness": .42, "metallic": .55, "wear": .55, "rust": .22},
    "bare-metal": {"surface": "galvanized-steel", "colors": ("#31383D", "#8B969D", "#E0E5E8"), "roughness": .3, "metallic": .97, "wear": .25},
    "oxidized-copper": {"surface": "oxidized-copper", "colors": ("#3C1F16", "#9B5638", "#4C9D84", "#9BD7C3"), "roughness": .5, "metallic": .78, "rust": .62, "moisture": .32},
    "worn-plastic": {"surface": "painted-wall", "colors": ("#11151D", "#315A8D", "#83B7EF"), "roughness": .65, "metallic": .0, "wear": .72, "peel": .3},
    "polished-plastic": {"surface": "porcelain", "colors": ("#0B1220", "#1E73D8", "#A7D6FF"), "roughness": .18, "metallic": .0, "wear": .15},
    "cloth-dye": {"surface": "nanofiber-weave", "colors": ("#25132E", "#733E89", "#C28BD6"), "roughness": .9, "metallic": .0, "dirt": .35},
    "leather-stain": {"surface": "mud", "colors": ("#241008", "#6D2F18", "#A85A32"), "roughness": .72, "metallic": .0, "wear": .48, "moisture": .25},
    "ceramic-glaze": {"surface": "porcelain", "colors": ("#7D8D94", "#D8E5E9", "#FFFFFF"), "roughness": .12, "metallic": .0, "crack": .24},
    "stone-mineral": {"surface": "granite", "colors": ("#30343A", "#767E87", "#B2B9B8"), "roughness": .84, "metallic": .02, "moss": .28},
    "neon-coat": {"surface": "cyber-grid", "colors": ("#0A0714", "#5E1FB0", "#F02DCF", "#6FF9FF"), "roughness": .25, "metallic": .22, "emission": .9},
    "rubberized-coat": {"surface": "rubber-tread", "colors": ("#050607", "#181A1D", "#34383D"), "roughness": .95, "metallic": .0, "dust": .36},
    "military-paint": {"surface": "mech-armor", "colors": ("#171C15", "#3E5033", "#71805E"), "roughness": .62, "metallic": .3, "wear": .64, "dirt": .48, "rust": .28},
    "weathered-wall-paint": {"surface": "stucco", "colors": ("#4D5556", "#8EA4A0", "#CED6CC"), "roughness": .88, "metallic": .0, "peel": .65, "dirt": .42, "moss": .22},
    "enchanted-pigment": {"surface": "ornamental", "colors": ("#1B1024", "#67449A", "#D69AF7", "#FFF2BA"), "roughness": .34, "metallic": .18, "emission": .55},
    "reactor-coat": {"surface": "reactor-skin", "colors": ("#06100E", "#0A5E45", "#18CE8A", "#A6FFBE"), "roughness": .28, "metallic": .42, "emission": .8, "scorch": .34},
    "biotech-pigment": {"surface": "biotech-membrane", "colors": ("#210C1E", "#6B2852", "#C34D82", "#F3A2C2"), "roughness": .48, "metallic": .05, "moisture": .62, "emission": .15},
    "vehicle-enamel": {"surface": "painted-wall", "colors": ("#16161B", "#8E1725", "#EF3C4E", "#FFC2C9"), "roughness": .2, "metallic": .35, "wear": .4, "dirt": .26},
    "industrial-powdercoat": {"surface": "mech-armor", "colors": ("#16191B", "#5E6569", "#B6BFC3"), "roughness": .48, "metallic": .46, "wear": .32, "dust": .24},
}


def _neighbor(field: list[list[float]], x: int, y: int) -> tuple[float, float, float, float]:
    h = len(field)
    w = len(field[0]) if h else 0
    return (
        field[y][max(0, x - 1)], field[y][min(w - 1, x + 1)],
        field[max(0, y - 1)][x], field[min(h - 1, y + 1)][x],
    )


def smart_masks(kind: str, size: int, seed: int, scale: float = 1.0, *, age: float = .5, damage: float = .35, moisture: float = .25) -> dict[str, list[list[float]]]:
    spec = PIGMENT_SPECS[kind]
    base = surface_field(spec["surface"], size, size, seed=seed, scale=scale)
    age = _clamp(age)
    damage = _clamp(damage)
    moisture = _clamp(moisture)
    result = {name: [] for name in SMART_MASKS}
    for y in range(size):
        rows = {name: [] for name in SMART_MASKS}
        v = y / max(1, size - 1)
        for x in range(size):
            u = x / max(1, size - 1)
            center = base[y][x]
            left, right, up, down = _neighbor(base, x, y)
            gradient = min(1.0, (abs(right - left) + abs(down - up)) * 3.4)
            cavity = _clamp(1.0 - center)
            coarse = _hash2(seed + 2001, x // 3, y // 3)
            fine = _hash2(seed + 2027, x, y)
            streak_phase = _hash2(seed + 2101, x // max(1, size // 16), 0)
            edge_wear = _clamp(gradient * (0.35 + age * .85) + (fine > .985) * .25)
            cavity_dirt = _clamp(cavity * (.2 + age * .65) + (coarse > .86) * .2)
            rust = _clamp((edge_wear * .5 + cavity_dirt * .55 + moisture * .3) * float(spec.get("rust", .12)) * (0.5 + age))
            dust = _clamp((.25 + (1.0 - v) * .35 + (coarse - .5) * .35) * float(spec.get("dust", spec.get("dirt", .18))) * (0.5 + age))
            wet = _clamp((v * .35 + cavity * .45 + (coarse > .78) * .3) * (moisture + float(spec.get("moisture", .0))))
            crack = _clamp((1.0 if abs(center - .5) < .025 + damage * .018 else 0.0) * (damage + float(spec.get("crack", .0))))
            peel = _clamp((edge_wear * .7 + (coarse > .91) * .4) * (damage + float(spec.get("peel", .0))))
            scorch = _clamp((1.0 if _hash2(seed + 2303, x // 5, y // 5) > .93 else 0.0) * (damage + float(spec.get("scorch", .0))) * center)
            moss = _clamp((cavity * .5 + wet * .7 + (coarse > .82) * .25) * (moisture + float(spec.get("moss", .0))))
            snow = _clamp(((1.0 - v) * .4 + max(0.0, up - center) * 2.5) * (0.1 + moisture * .25))
            streak = _clamp((1.0 if abs((u + streak_phase) % .16 - .08) < .012 else 0.0) * wet * (0.5 + age))
            sun_fade = _clamp((1.0 - v) * (.25 + age * .55) * (0.75 + .25 * math.sin(u * math.pi)))
            vals = {"edge-wear": edge_wear, "cavity-dirt": cavity_dirt, "rust": rust, "dust": dust, "moisture": wet, "crack": crack, "peel": peel, "scorch": scorch, "moss": moss, "snow": snow, "streak": streak, "sun-fade": sun_fade}
            for name in SMART_MASKS:
                rows[name].append(vals[name])
        for name in SMART_MASKS:
            result[name].append(rows[name])
    return result


def _normal_from_height(field: list[list[float]], strength: float = 2.5) -> list[list[tuple[int, int, int]]]:
    h = len(field)
    w = len(field[0]) if h else 0
    out: list[list[tuple[int, int, int]]] = []
    for y in range(h):
        row = []
        for x in range(w):
            l, r, u, d = _neighbor(field, x, y)
            nx, ny, nz = -(r - l) * strength, -(d - u) * strength, 1.0
            length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
            row.append((_byte(nx / length * .5 + .5), _byte(ny / length * .5 + .5), _byte(nz / length * .5 + .5)))
        out.append(row)
    return out


def pigment_maps(kind: str, size: int, seed: int = 0, scale: float = 1.0, *, age: float = .5, damage: float = .35, moisture: float = .25) -> tuple[dict[str, tuple[str, list]], dict[str, Any]]:
    kind = str(kind).strip().casefold()
    if kind not in PIGMENT_SPECS:
        raise KeyError(f"unknown pigment kind: {kind}")
    spec = PIGMENT_SPECS[kind]
    field = surface_field(spec["surface"], size, size, seed=seed, scale=scale)
    masks = smart_masks(kind, size, seed, scale, age=age, damage=damage, moisture=moisture)
    palette = [_hex_rgb(c) for c in spec["colors"]]
    albedo: list[list[tuple[int, int, int]]] = []
    roughness: list[list[int]] = []
    metallic: list[list[int]] = []
    ao: list[list[int]] = []
    emissive: list[list[tuple[int, int, int]]] = []
    opacity: list[list[int]] = []
    height_rows: list[list[int]] = []
    emission = float(spec.get("emission", 0.0))
    base_rough = float(spec.get("roughness", .5))
    base_metal = float(spec.get("metallic", 0.0))
    for y in range(size):
        arow, rrow, mrow, aorow, erow, orow, hrow = [], [], [], [], [], [], []
        for x in range(size):
            value = field[y][x]
            wear = masks["edge-wear"][y][x]
            dirt = masks["cavity-dirt"][y][x]
            fade = masks["sun-fade"][y][x]
            rust = masks["rust"][y][x]
            t = _clamp(value * .82 + wear * .13 - dirt * .14 + fade * .08)
            color = _sample_stops(palette, t)
            if rust > .05:
                rust_color = (142, 69, 35)
                mix = min(.72, rust)
                color = tuple(int(color[i] * (1 - mix) + rust_color[i] * mix) for i in range(3))
            arow.append(color)
            rrow.append(_byte(_clamp(base_rough + dirt * .2 + masks["dust"][y][x] * .18 - wear * .12)))
            mrow.append(_byte(_clamp(base_metal * (1.0 - rust * .55))))
            aorow.append(_byte(_clamp(.68 + value * .27 - dirt * .18)))
            glow = _clamp(emission * (value * .55 + .45) * (1.0 - masks["scorch"][y][x] * .7))
            erow.append(tuple(int(c * glow) for c in color))
            orow.append(_byte(float(spec.get("opacity", 1.0))))
            hrow.append(_byte(_clamp(value - masks["crack"][y][x] * .35 - masks["peel"][y][x] * .15)))
        albedo.append(arow); roughness.append(rrow); metallic.append(mrow); ao.append(aorow); emissive.append(erow); opacity.append(orow); height_rows.append(hrow)
    normal = _normal_from_height(field)
    maps: dict[str, tuple[str, list]] = {"albedo": ("RGB", albedo), "roughness": ("L", roughness), "metallic": ("L", metallic), "height": ("L", height_rows), "normal": ("RGB", normal), "ao": ("L", ao), "emissive": ("RGB", emissive), "opacity": ("L", opacity)}
    for name in SMART_MASKS:
        maps[f"mask-{name}"] = ("L", [[_byte(v) for v in row] for row in masks[name]])
    metadata = {"surface": spec["surface"], "colors": list(spec["colors"]), "age": _clamp(age), "damage": _clamp(damage), "moisture": _clamp(moisture), "smart_masks": list(SMART_MASKS), "roughness": base_rough, "metallic": base_metal, "emission": emission}
    return maps, metadata

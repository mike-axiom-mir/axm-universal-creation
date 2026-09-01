from __future__ import annotations

import math
from typing import Sequence

from .visual_base import _clamp, _fbm, _hash2, _hex_rgb, _sample_stops

SURFACES = (
    "bark", "moss", "lichen", "mud", "sand", "snow", "ice", "lava-crust",
    "obsidian", "granite", "slate", "limestone", "clay", "cracked-earth", "wet-soil",
    "grass-patch", "leaf-litter", "roof-tile", "plaster", "stucco", "asphalt",
    "painted-wall", "wallpaper", "porcelain", "frosted-glass", "dirty-glass",
    "rusted-steel", "oxidized-copper", "galvanized-steel", "rubber-tread",
    "foam", "insulation", "spaceship-hull", "mech-armor", "energy-panel",
    "hologram-grid", "reactor-skin", "shield-field", "cyber-grid", "nanofiber-weave",
    "warning-panel", "data-lattice", "alien-alloy", "biotech-membrane", "chain-link",
    "quilt", "zigzag", "labyrinth", "ornamental", "wave-pattern", "spiral-pattern",
)

SURFACE_PALETTES: dict[str, tuple[str, ...]] = {
    "bark": ("#140C08", "#4D2B18", "#8B5A32", "#C08A5A"),
    "moss": ("#102313", "#2E5C2B", "#6C913E", "#B3C96D"),
    "lichen": ("#273229", "#657A55", "#A8B579", "#D7D3A0"),
    "mud": ("#1A100B", "#493123", "#76563C", "#A6825E"),
    "sand": ("#5B472A", "#B08A52", "#E4C98E", "#F4E3B6"),
    "snow": ("#A7BDCE", "#DCEAF3", "#F7FBFF"),
    "ice": ("#2B5870", "#68AFCB", "#CFF5FF", "#F7FEFF"),
    "lava-crust": ("#060607", "#2B2020", "#781F12", "#FF6A18"),
    "obsidian": ("#030409", "#101629", "#2D3154", "#7476A4"),
    "granite": ("#25282B", "#666A6E", "#A4A7A8", "#D2D0C9"),
    "slate": ("#182027", "#354653", "#687A86", "#9AA8B0"),
    "limestone": ("#6D6756", "#AAA188", "#D7CEAE", "#EEE6CA"),
    "clay": ("#4F241A", "#98452D", "#C96F4A", "#E7A37A"),
    "cracked-earth": ("#24150D", "#6E4329", "#A66B42", "#D5A66E"),
    "wet-soil": ("#090A07", "#202719", "#455434", "#75805A"),
    "grass-patch": ("#0D2514", "#295B28", "#5C8A3A", "#A2BC61"),
    "leaf-litter": ("#211409", "#593019", "#8B5C29", "#C19245"),
    "roof-tile": ("#3A1615", "#7A2B26", "#B34F3C", "#D77B59"),
    "plaster": ("#74716A", "#B8B3A7", "#E2DDD0", "#F6F2E7"),
    "stucco": ("#5E5B55", "#A29C91", "#D3CEC2", "#EEEAE0"),
    "asphalt": ("#0B0D0F", "#24282B", "#4A4D4E", "#6A6966"),
    "painted-wall": ("#10131A", "#334766", "#5F86B8", "#B7D4ED"),
    "wallpaper": ("#2C1738", "#6A3C79", "#B06EAF", "#E5B1D7"),
    "porcelain": ("#8D9AA5", "#D7E0E7", "#F9FCFF"),
    "frosted-glass": ("#46768B", "#90C6D6", "#DDF7FC", "#FFFFFF"),
    "dirty-glass": ("#263A3C", "#5F817A", "#A7B9A9", "#DAE6D8"),
    "rusted-steel": ("#17191A", "#4A3026", "#91452A", "#CF7546"),
    "oxidized-copper": ("#2D1A14", "#8B5134", "#4B947C", "#8BCAB3"),
    "galvanized-steel": ("#3D464C", "#7C8A91", "#BEC8CC", "#EEF2F3"),
    "rubber-tread": ("#050607", "#151719", "#303337"),
    "foam": ("#5D6366", "#AAB1B3", "#E8EDED"),
    "insulation": ("#7F5A21", "#D89A35", "#F6CD71"),
    "spaceship-hull": ("#0B1016", "#27313B", "#6F7B86", "#B8C3CC"),
    "mech-armor": ("#101319", "#313946", "#626D7E", "#A4AEBB"),
    "energy-panel": ("#03141C", "#064F63", "#10B8C9", "#7CFFF4"),
    "hologram-grid": ("#080B1A", "#3C1E72", "#D33BD1", "#73F8FF"),
    "reactor-skin": ("#05080A", "#0E3B31", "#18B77A", "#A9FFB9"),
    "shield-field": ("#081126", "#174A92", "#45BCEB", "#D1F8FF"),
    "cyber-grid": ("#080811", "#28194F", "#7A2ED6", "#18E8FF"),
    "nanofiber-weave": ("#101214", "#343B42", "#7A858F", "#D4DCE2"),
    "warning-panel": ("#111111", "#493C05", "#D49E00", "#FFD54A"),
    "data-lattice": ("#041016", "#0B4553", "#149CB0", "#70FFF2"),
    "alien-alloy": ("#13121A", "#45345D", "#8C68A2", "#D8B9E6"),
    "biotech-membrane": ("#130B15", "#4E1E43", "#9B3E6A", "#E883A8"),
    "chain-link": ("#14171A", "#4F565D", "#A0A7AD"),
    "quilt": ("#2B1A39", "#6C4E91", "#BFA5D8"),
    "zigzag": ("#141A25", "#3B62A6", "#C6DCFF"),
    "labyrinth": ("#0C0F15", "#2F3B55", "#879BC0"),
    "ornamental": ("#24150F", "#765025", "#D0A550", "#F0DB98"),
    "wave-pattern": ("#071624", "#1F5F82", "#73C5D9"),
    "spiral-pattern": ("#170F25", "#663A8C", "#D49BEA"),
}


def _cell_edge(x: float, y: float, cell: float) -> float:
    xx = x % cell
    yy = y % cell
    return min(xx, yy, cell - xx, cell - yy) / max(1.0, cell)


def surface_field(kind: str, width: int, height: int, seed: int = 0, scale: float = 1.0) -> list[list[float]]:
    kind = str(kind).strip().casefold()
    if kind not in SURFACES:
        raise KeyError(f"unknown surface kind: {kind}")
    scale = max(0.05, float(scale))
    small = max(1, min(width, height))
    rows: list[list[float]] = []
    for y in range(height):
        row: list[float] = []
        v = y / max(1, height - 1)
        for x in range(width):
            u = x / max(1, width - 1)
            sx = x / small * 9.0 / scale
            sy = y / small * 9.0 / scale
            n = _fbm(seed, sx, sy, 5)
            fine = _fbm(seed + 911, sx * 3.1, sy * 3.1, 3)
            grain = _hash2(seed + 73, x, y)
            if kind in {"bark", "nanofiber-weave", "insulation"}:
                bands = abs(math.sin((sx + (n - .5) * 2.2) * math.pi * (2.2 if kind == "bark" else 4.5)))
                value = _clamp(.18 + bands * .55 + fine * .25)
            elif kind in {"moss", "lichen", "grass-patch", "leaf-litter", "biotech-membrane"}:
                blobs = _clamp((n - .32) * 1.7)
                speck = 0.18 if grain > .94 else 0.0
                value = _clamp(.18 + blobs * .68 + fine * .14 + speck)
            elif kind in {"mud", "wet-soil", "clay", "plaster", "stucco", "foam"}:
                pore = -0.22 if grain > (.965 if kind != "foam" else .90) else 0.0
                value = _clamp(.4 + (n - .5) * .5 + (fine - .5) * .18 + pore)
            elif kind in {"sand", "snow", "granite", "limestone", "asphalt", "galvanized-steel"}:
                speck = (grain - .5) * (.35 if kind in {"sand", "asphalt"} else .22)
                value = _clamp(.5 + (n - .5) * .28 + speck)
            elif kind in {"ice", "frosted-glass", "dirty-glass", "obsidian"}:
                streak = math.sin((sx * .5 + sy * 1.6 + n * 3.0) * math.pi)
                dirt = -.2 if kind == "dirty-glass" and grain > .93 else 0.0
                value = _clamp(.6 + streak * .12 + (n - .5) * .24 + dirt)
            elif kind in {"lava-crust", "cracked-earth", "rusted-steel", "oxidized-copper"}:
                ridge = abs(n - .5)
                crack = 1.0 if ridge < (.035 if kind != "rusted-steel" else .045) else 0.0
                oxidation = _clamp((fine - .45) * 1.8)
                value = _clamp(.32 + n * .38 + oxidation * .24 - crack * .5)
            elif kind in {"slate", "roof-tile", "porcelain"}:
                cell = max(6.0, small / (8.0 * scale))
                edge = _cell_edge(float(x), float(y), cell)
                value = _clamp((.12 if edge < .08 else .62) + (n - .5) * .22)
            elif kind in {"painted-wall", "wallpaper", "quilt", "ornamental"}:
                motif = .5 + .5 * math.sin((u * 12 / scale + math.sin(v * math.pi * 4)) * math.pi)
                if kind == "quilt":
                    motif = 1.0 - min(1.0, abs((x % max(4, int(small / 8))) - small / 16) / max(1.0, small / 16))
                elif kind == "ornamental":
                    motif = .5 + .5 * math.sin((u + v) * math.pi * 10) * math.cos((u - v) * math.pi * 8)
                value = _clamp(.35 + motif * .45 + (n - .5) * .16)
            elif kind in {"rubber-tread", "chain-link", "zigzag", "labyrinth", "wave-pattern", "spiral-pattern"}:
                if kind == "rubber-tread":
                    motif = .9 if int((u + v) * 18 / scale) % 2 == 0 else .18
                elif kind == "chain-link":
                    a = abs(math.sin((u + v) * math.pi * 10 / scale))
                    b = abs(math.sin((u - v) * math.pi * 10 / scale))
                    motif = 1.0 if min(a, b) < .13 else .18
                elif kind == "zigzag":
                    motif = .5 + .5 * math.sin((u * 12 + abs((v * 8) % 2 - 1) * 3) * math.pi / scale)
                elif kind == "labyrinth":
                    motif = .9 if (int(u * 16 / scale) ^ int(v * 16 / scale)) % 3 == 0 else .18
                elif kind == "wave-pattern":
                    motif = .5 + .5 * math.sin((u * 10 + math.sin(v * math.pi * 6) * .7) * math.pi / scale)
                else:
                    dx, dy = u - .5, v - .5
                    angle = math.atan2(dy, dx)
                    radius = math.sqrt(dx * dx + dy * dy)
                    motif = .5 + .5 * math.sin((radius * 16 + angle * 2.3) * math.pi / scale)
                value = _clamp(.2 + motif * .65 + (n - .5) * .12)
            else:
                cell = max(8, int(small / (7 * scale)))
                border = min(x % cell, y % cell, cell - (x % cell), cell - (y % cell))
                phase = _hash2(seed + sum(ord(c) for c in kind), x // cell, y // cell)
                grid = .08 if border < max(1, cell // 18) else .0
                pulse = .24 if ((x + y + int(phase * cell)) % max(5, cell // 3)) < 2 else 0.0
                value = _clamp(.27 + n * .42 + pulse - grid)
            row.append(value)
        rows.append(row)
    return rows


def surface_rows(kind: str, width: int, height: int, seed: int = 0, scale: float = 1.0, colors: Sequence[str] | None = None) -> list[list[tuple[int, int, int]]]:
    field = surface_field(kind, width, height, seed=seed, scale=scale)
    palette = [_hex_rgb(c) for c in (colors or SURFACE_PALETTES[kind])]
    return [[_sample_stops(palette, value) for value in row] for row in field]

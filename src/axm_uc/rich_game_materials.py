"""Expanded deterministic game-material profiles for UC 3D builders.

This module is additive to ``game_material_styles``. It turns role-oriented game
surface names (molded plastic, sun-faded plastic, fiberglass, rope, sailcloth,
oxidized metal, driftwood, foam, etc.) into portable PBR map fields and PNG
bundles without requiring a renderer, Pillow, NumPy, internet, or stock textures.

Truth boundary: these are authored procedural game materials, not scanned or
physically measured substances. UV-space wear/stains are not mesh-derived.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .fabric_noise import fbm, png_bytes


@dataclass(frozen=True)
class RichMaterialProfile:
    name: str
    default_rgb: tuple[int, int, int]
    roughness: float
    metallic: float
    broad_scale: float
    grain_scale: float
    color_variation: float
    roughness_variation: float
    normal_strength: float
    pattern: str
    description: str


PROFILES = (
    RichMaterialProfile("molded-plastic", (232, 151, 37), .38, .00, 3.2, 52, .10, .12, .035,
                        "molded", "Injection/molded game plastic with cloudy color and micro-orange-peel."),
    RichMaterialProfile("sun-faded-plastic", (235, 148, 35), .57, .00, 2.5, 47, .22, .17, .028,
                        "sunfade", "UV-faded plastic with pale directional fade and salt freckles."),
    RichMaterialProfile("wet-plastic", (34, 120, 150), .18, .00, 4.2, 70, .08, .08, .024,
                        "wet", "Darkened plastic with lower roughness and broken water-film variation."),
    RichMaterialProfile("painted-fiberglass", (42, 119, 145), .34, .00, 3.6, 86, .13, .11, .038,
                        "fiberglass", "Painted fiberglass/gelcoat with subtle fiber and cloudy resin variation."),
    RichMaterialProfile("scratched-fiberglass", (38, 110, 137), .48, .00, 4.0, 92, .18, .17, .052,
                        "scratched-fiberglass", "Weathered gelcoat with scratches, pale scuffs and exposed fiber hints."),
    RichMaterialProfile("canvas", (196, 169, 116), .78, .00, 2.4, 38, .15, .12, .060,
                        "canvas", "Coarse woven canvas with irregular dye and raised crossing threads."),
    RichMaterialProfile("sailcloth", (222, 207, 167), .68, .00, 2.0, 46, .12, .10, .045,
                        "sailcloth", "Tighter sail weave with sun bleaching, stains and soft thread relief."),
    RichMaterialProfile("dry-rope", (126, 88, 49), .86, .00, 2.0, 28, .18, .08, .075,
                        "rope", "Dry twisted rope with diagonal strand relief and uneven fibers."),
    RichMaterialProfile("wet-rope", (82, 58, 35), .55, .00, 2.2, 30, .14, .12, .065,
                        "wet-rope", "Dark damp rope with strand relief and patchy wetness."),
    RichMaterialProfile("powdercoat-metal", (157, 58, 43), .46, 1.00, 3.0, 78, .08, .13, .035,
                        "powdercoat", "Paint/powder-coated metal with fine stipple and subtle coat wear."),
    RichMaterialProfile("anodized-aluminum", (73, 88, 98), .27, 1.00, 4.0, 110, .07, .10, .018,
                        "brushed-metal", "Fine brushed/anodized aluminum with anisotropic-looking line variation."),
    RichMaterialProfile("weathered-aluminum", (146, 151, 147), .52, 1.00, 3.3, 76, .15, .18, .034,
                        "weathered-metal", "Salt-weathered aluminum with cloudy oxidation and directional scuffs."),
    RichMaterialProfile("oxidized-steel", (102, 75, 57), .68, .72, 2.9, 54, .30, .20, .060,
                        "oxidized-steel", "Steel with patchy oxide, pitting and partially retained metallic response."),
    RichMaterialProfile("varnished-wood", (132, 81, 38), .34, .00, 2.0, 34, .18, .12, .050,
                        "wood", "Warm sealed wood with lengthwise grain and glossy low spots."),
    RichMaterialProfile("driftwood", (148, 132, 108), .82, .00, 2.0, 30, .24, .10, .072,
                        "driftwood", "Bleached rough wood with long grain, salt whitening and cracks."),
    RichMaterialProfile("eva-foam", (60, 76, 82), .82, .00, 3.8, 64, .10, .08, .030,
                        "foam", "Soft closed-cell foam with tiny pores and compressed mottling."),
    RichMaterialProfile("weathered-rubber", (39, 46, 49), .80, .00, 3.1, 72, .14, .10, .044,
                        "rubber", "Aged rubber with bloom, micro grain and pale abrasion."),
    RichMaterialProfile("salt-crusted-surface", (173, 170, 151), .88, .00, 2.6, 58, .26, .12, .070,
                        "salt", "Generic salt-crusted coating used as a secondary island/ocean material."),
)
PROFILE_BY_NAME = {profile.name: profile for profile in PROFILES}


def rich_game_material_catalog() -> dict:
    return {
        "schema": "axm.rich-game-material-catalog/v0.1",
        "profiles": [asdict(profile) for profile in PROFILES],
        "map_channels": ["base_color", "normal", "orm", "ao", "roughness", "metallic", "height"],
        "dependencies": [],
        "truth": (
            "Deterministic authored UV-space game materials. Not scans, measured BRDFs, "
            "mesh-derived curvature wear, or automatic visual acceptance."
        ),
    }


def _u8(value: float) -> int:
    return max(0, min(255, round(value * 255)))


def _check(size: int, seed: int) -> None:
    if type(size) is not int or not 16 <= size <= 1024:
        raise ValueError("size must be an integer from 16 to 1024")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("seed must be an integer from 0 to 2147483647")


def _normal_from_height(height: list[float], size: int, strength: float) -> bytes:
    out = bytearray()
    for y in range(size):
        for x in range(size):
            xl, xr = max(0, x - 1), min(size - 1, x + 1)
            yd, yu = max(0, y - 1), min(size - 1, y + 1)
            dx = height[y * size + xr] - height[y * size + xl]
            dy = height[yu * size + x] - height[yd * size + x]
            nx, ny = -dx * size * strength, dy * size * strength
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + 1.0)
            out.extend((_u8(nx * inv * .5 + .5), _u8(ny * inv * .5 + .5), _u8(inv * .5 + .5)))
    return bytes(out)


def _strand(u: float, v: float, density: float, twist: float) -> float:
    return .5 + .5 * math.sin((u * density + v * twist) * math.tau)


def _cross_weave(u: float, v: float, density: float) -> float:
    a = .5 + .5 * math.sin(u * density * math.tau)
    b = .5 + .5 * math.sin(v * density * math.tau)
    return (a * b) ** .75


def _crack_field(u: float, v: float, seed: int) -> float:
    warp = (fbm(u * 5.1, v * 5.1, seed + 3001, 3) - .5) * .18
    band_a = abs(math.sin((u * 7.0 + v * 1.3 + warp) * math.pi))
    band_b = abs(math.sin((v * 8.5 - u * 1.1 - warp) * math.pi))
    return max(0.0, .11 - min(band_a, band_b)) / .11


def _surface(profile: RichMaterialProfile, u: float, v: float, seed: int):
    broad = fbm(u * profile.broad_scale, v * profile.broad_scale, seed + 101, 4)
    grain = fbm(u * profile.grain_scale, v * profile.grain_scale, seed + 907, 3)
    micro = fbm(u * profile.grain_scale * 2.8, v * profile.grain_scale * 2.8, seed + 1901, 2)
    p = profile.pattern
    color_delta = (broad - .5) * 2
    rough_delta = (grain - .5) * 2
    h = .5 + (grain - .5) * .018
    metal_factor = 1.0
    tint = (1.0, 1.0, 1.0)

    if p == "molded":
        h += (micro - .5) * .010 + math.sin((u * 2.2 + broad * .4) * math.tau) * .002
    elif p == "sunfade":
        fade = max(0.0, min(1.0, .15 + .85 * v + (broad - .5) * .22))
        salt = max(0.0, (grain - .68) * 3.0)
        tint = tuple(1.0 + fade * c for c in (.18, .15, .10))
        color_delta -= fade * .22
        rough_delta += fade * .28 + salt * .20
        h += salt * .012
    elif p == "wet":
        wet = max(0.0, min(1.0, .55 + (broad - .5) * 1.1))
        color_delta -= wet * .16
        rough_delta -= wet * .52
        h += (micro - .5) * .005
    elif p in ("fiberglass", "scratched-fiberglass"):
        fiber = _cross_weave(u + broad * .015, v, 72)
        h += (fiber - .5) * .009
        rough_delta += (fiber - .5) * .14
        if p == "scratched-fiberglass":
            scratch = max(0.0, (_strand(u + broad * .02, v, 56, 5) - .86) / .14)
            scuff = max(0.0, (.42 - grain) * 2.2)
            color_delta += scuff * .15 + scratch * .22
            rough_delta += scuff * .28
            h -= scratch * .035
    elif p in ("canvas", "sailcloth"):
        density = 44 if p == "canvas" else 58
        weave = _cross_weave(u, v, density)
        stain = max(0.0, (.40 - broad) * 2.0)
        h += (weave - .5) * (.038 if p == "canvas" else .025)
        color_delta -= stain * .14
        rough_delta += (weave - .5) * .18 + stain * .08
        if p == "sailcloth":
            sun = max(0.0, v - .35)
            color_delta += sun * .10
    elif p in ("rope", "wet-rope"):
        strands = _strand(u, v, 23, 7.5)
        secondary = _strand(u + .17, v, 46, -3.2)
        h += (strands - .5) * .055 + (secondary - .5) * .018
        color_delta += (strands - .5) * .20
        if p == "wet-rope":
            wet = max(0.0, min(1.0, .5 + (broad - .5) * 1.3))
            color_delta -= wet * .22
            rough_delta -= wet * .32
    elif p == "powdercoat":
        h += (micro - .5) * .018
        rough_delta += (micro - .5) * .22
    elif p == "brushed-metal":
        brush = .5 + .5 * math.sin((u * 190 + broad * 1.2) * math.tau)
        h += (brush - .5) * .003
        color_delta += (brush - .5) * .05
        rough_delta += (brush - .5) * .12
    elif p == "weathered-metal":
        brush = .5 + .5 * math.sin((u * 118 + broad * 1.8) * math.tau)
        oxide = max(0.0, (.44 - grain) * 2.4)
        h += (brush - .5) * .005 + oxide * .010
        color_delta += oxide * .19
        rough_delta += oxide * .32
        metal_factor -= oxide * .22
    elif p == "oxidized-steel":
        oxide = max(0.0, (broad * .72 + grain * .28 - .48) * 2.0)
        pits = max(0.0, (.37 - micro) * 2.7)
        tint = (1.0 + oxide * .22, 1.0 - oxide * .12, 1.0 - oxide * .23)
        color_delta -= pits * .16
        rough_delta += oxide * .38 + pits * .25
        h -= pits * .030
        metal_factor = max(.08, 1.0 - oxide * .80)
    elif p in ("wood", "driftwood"):
        warp = (broad - .5) * 1.7
        rings = .5 + .5 * math.sin((u * 24 + warp) * math.tau)
        knot = math.exp(-(((u - .37) ** 2) + ((v - .59) * .42) ** 2) * 58)
        h += (rings - .5) * .030 + knot * .012
        color_delta += (rings - .5) * .27 - knot * .08
        rough_delta += (grain - .5) * .10
        if p == "driftwood":
            cracks = _crack_field(u, v, seed)
            h -= cracks * .055
            color_delta += .13 - cracks * .20
            rough_delta += .22 + cracks * .18
    elif p == "foam":
        pores = max(0.0, (.43 - micro) * 2.5)
        h -= pores * .014
        color_delta -= pores * .07
        rough_delta += pores * .12
    elif p == "rubber":
        abrasion = max(0.0, (.40 - broad) * 2.1)
        bloom = max(0.0, (grain - .66) * 2.8)
        h += (micro - .5) * .015 - abrasion * .008
        color_delta += bloom * .13 + abrasion * .09
        rough_delta += abrasion * .18
    elif p == "salt":
        crust = max(0.0, (grain - .58) * 2.4)
        streak = max(0.0, (.44 - fbm(u * 8, v * 2.2, seed + 8121, 3)) * 2.3)
        h += crust * .040 + streak * .014
        color_delta += crust * .30 + streak * .10
        rough_delta += crust * .16

    return color_delta, rough_delta, h, metal_factor, tint


def rich_game_material_fields(profile_name: str, size: int = 256, seed: int = 1,
                              color: tuple[int, int, int] | None = None) -> dict:
    _check(size, seed)
    if profile_name not in PROFILE_BY_NAME:
        raise ValueError(f"unknown rich material profile: {profile_name}")
    profile = PROFILE_BY_NAME[profile_name]
    rgb = profile.default_rgb if color is None else tuple(color)
    if len(rgb) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in rgb):
        raise ValueError("color requires three integer sRGB bytes")

    base = bytearray()
    roughness = bytearray()
    metallic = bytearray()
    height: list[float] = []
    ao = bytearray()
    for y in range(size):
        v = (y + .5) / size
        for x in range(size):
            u = (x + .5) / size
            color_delta, rough_delta, h, metal_factor, tint = _surface(profile, u, v, seed)
            scale = max(.35, 1.0 + color_delta * profile.color_variation)
            for channel, component in enumerate(rgb):
                base.append(max(0, min(255, round(component * scale * tint[channel]))))
            roughness.append(_u8(max(.03, min(.98, profile.roughness + rough_delta * profile.roughness_variation))))
            metallic.append(_u8(max(0.0, min(1.0, profile.metallic * metal_factor))))
            height.append(max(0.0, min(1.0, h)))
            ao.append(_u8(max(.72, min(1.0, .97 + (h - .5) * 1.6))))

    normal = _normal_from_height(height, size, profile.normal_strength)
    orm = bytes(channel for i in range(size * size)
                for channel in (ao[i], roughness[i], metallic[i]))
    return {
        "base_color": (3, bytes(base)),
        "roughness": (1, bytes(roughness)),
        "metallic": (1, bytes(metallic)),
        "height": (1, bytes(_u8(value) for value in height)),
        "normal": (3, normal),
        "ao": (1, bytes(ao)),
        "orm": (3, orm),
    }


def generate_rich_game_material(path, profile_name: str, size: int = 256, seed: int = 1,
                                color: tuple[int, int, int] | None = None) -> dict:
    """Write one immutable rich material bundle and return its manifest."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    profile = PROFILE_BY_NAME.get(profile_name)
    if profile is None:
        raise ValueError(f"unknown rich material profile: {profile_name}")
    fields = rich_game_material_fields(profile_name, size, seed, color)
    maps = {}
    for name, (channels, pixels) in fields.items():
        payload = png_bytes(size, size, channels, pixels)
        filename = name + ".png"
        (target / filename).write_bytes(payload)
        maps[name] = {
            "file": filename,
            "channels": channels,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "color_space": "sRGB" if name == "base_color" else "linear-data",
        }
    manifest = {
        "schema": "axm.rich-game-material/v0.1",
        "profile": profile_name,
        "profile_spec": asdict(profile),
        "size": size,
        "seed": seed,
        "color": list(profile.default_rgb if color is None else color),
        "maps": maps,
        "orm_channels": ["occlusion", "roughness", "metallic"],
        "normal_convention": "tangent +Y",
        "truth": (
            "Deterministic authored UV-space game material. Not a scan or measured BRDF. "
            "Wear, stains, fibers and oxidation are procedural surface fields rather than mesh-derived evidence."
        ),
    }
    manifest_bytes = (json.dumps(manifest, indent=2, sort_keys=True) + "\n").encode()
    (target / "rich-game-material.json").write_bytes(manifest_bytes)
    return manifest

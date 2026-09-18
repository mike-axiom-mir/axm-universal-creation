"""Deterministic layered game-material composition for UC.

This module sits above :mod:`axm_uc.rich_game_materials`. A rich material remains
an independently reusable base surface; optional authored layers add readable
island/game wear such as salt, dirt, wetness, scuffs, paint chips, rust, algae,
sun bleaching and simple decal stripes.

Truth boundary: masks are authored in UV space. They are not curvature, contact,
world-space accumulation, physically measured weathering or automatic aesthetic
acceptance. Builders may later replace/supply masks derived from real mesh evidence.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .fabric_noise import fbm, png_bytes
from .rich_game_materials import PROFILE_BY_NAME, rich_game_material_fields


@dataclass(frozen=True)
class LayerType:
    name: str
    default_amount: float
    default_scale: float
    description: str
    changes: tuple[str, ...]


LAYER_TYPES = (
    LayerType("salt", .25, 7.0, "Pale broken salt crust/freckles for ocean-exposed assets.",
              ("base_color", "roughness", "height", "metallic")),
    LayerType("dirt", .20, 4.0, "Irregular warm dirt and grime accumulation.",
              ("base_color", "roughness", "height")),
    LayerType("wetness", .18, 3.0, "Patchy darkened low-roughness water film.",
              ("base_color", "roughness")),
    LayerType("scuff", .22, 18.0, "Directional abrasion and scratch breakup.",
              ("base_color", "roughness", "height")),
    LayerType("paint-chip", .16, 11.0, "Clustered paint loss exposing a darker substrate.",
              ("base_color", "roughness", "metallic", "height")),
    LayerType("rust", .18, 6.0, "Clustered orange-brown oxidation for ferrous surfaces.",
              ("base_color", "roughness", "metallic", "height")),
    LayerType("sun-bleach", .22, 2.0, "Directional UV bleaching with broad noisy breakup.",
              ("base_color", "roughness")),
    LayerType("algae", .16, 4.5, "Green-brown damp growth band for waterline-style breakup.",
              ("base_color", "roughness", "height")),
    LayerType("decal-stripe", .35, 5.0, "Simple authored diagonal stripe/decal mask.",
              ("base_color", "roughness", "height")),
)
LAYER_BY_NAME = {layer.name: layer for layer in LAYER_TYPES}


def layered_game_material_catalog() -> dict:
    return {
        "schema": "axm.layered-game-material-catalog/v0.1",
        "layer_types": [asdict(layer) for layer in LAYER_TYPES],
        "base_profiles": sorted(PROFILE_BY_NAME),
        "truth": (
            "Layers are deterministic authored UV-space masks. They are not mesh-curvature, "
            "contact, gravity, simulation, scanned weathering or visual acceptance evidence."
        ),
    }


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _u8(value: float) -> int:
    return max(0, min(255, round(_clamp01(value) * 255)))


def _mix(a: float, b: float, t: float) -> float:
    return a + (b - a) * _clamp01(t)


def _validate_layer(raw: dict, index: int) -> dict:
    if not isinstance(raw, dict):
        raise ValueError(f"layer {index} must be an object")
    kind = raw.get("type")
    if kind not in LAYER_BY_NAME:
        raise ValueError(f"layer {index} has unknown type: {kind}")
    spec = LAYER_BY_NAME[kind]
    amount = raw.get("amount", spec.default_amount)
    scale = raw.get("scale", spec.default_scale)
    if not isinstance(amount, (int, float)) or not 0.0 <= float(amount) <= 1.0:
        raise ValueError(f"layer {index} amount must be from 0 to 1")
    if not isinstance(scale, (int, float)) or not 0.25 <= float(scale) <= 256.0:
        raise ValueError(f"layer {index} scale must be from .25 to 256")
    color = raw.get("color")
    if color is not None:
        if (not isinstance(color, list) or len(color) != 3 or
                any(type(c) is not int or not 0 <= c <= 255 for c in color)):
            raise ValueError(f"layer {index} color requires three sRGB bytes")
        color = tuple(color)
    return {
        "type": kind,
        "amount": float(amount),
        "scale": float(scale),
        "color": color,
        "seed_offset": int(raw.get("seed_offset", index * 1009 + 37)),
    }


def _mask(kind: str, u: float, v: float, seed: int, scale: float) -> float:
    broad = fbm(u * scale, v * scale, seed + 101, 4)
    fine = fbm(u * scale * 3.7, v * scale * 3.7, seed + 701, 3)
    if kind == "salt":
        crust = max(0.0, (fine - .56) * 2.4)
        patch = max(0.0, (broad - .47) * 1.55)
        return _clamp01(crust * .72 + patch * .48)
    if kind == "dirt":
        streak = .5 + .5 * math.sin((u * .65 + v * 2.1 + broad * .35) * math.tau)
        return _clamp01(max(0.0, (.58 - broad) * 1.85) * .75 + streak * .18)
    if kind == "wetness":
        return _clamp01((broad - .34) * 1.45 + max(0.0, fine - .60) * .30)
    if kind == "scuff":
        lines = .5 + .5 * math.sin((u * scale * 2.7 + v * scale * .31 + broad * .7) * math.tau)
        scratches = max(0.0, (lines - .84) / .16)
        rubbed = max(0.0, (.43 - fine) * 1.7)
        return _clamp01(scratches * .82 + rubbed * .38)
    if kind == "paint-chip":
        cells = max(0.0, (broad * .65 + fine * .35 - .61) * 2.7)
        rim = max(0.0, (fine - .69) * 2.0)
        return _clamp01(cells + rim * .18)
    if kind == "rust":
        cluster = max(0.0, (broad - .48) * 1.8)
        pits = max(0.0, (.39 - fine) * 2.2)
        return _clamp01(cluster * .85 + pits * .32)
    if kind == "sun-bleach":
        directional = _clamp01(.12 + v * .92)
        return _clamp01(directional * (.72 + (broad - .5) * .55))
    if kind == "algae":
        waterline = _clamp01((.72 - v) * 2.0)
        growth = _clamp01((broad - .36) * 1.55)
        return _clamp01(waterline * growth + max(0.0, fine - .72) * .15)
    if kind == "decal-stripe":
        phase = (u * scale + v * scale * .34 + (broad - .5) * .08) % 1.0
        edge = .16
        if phase < .36:
            return 1.0
        if phase < .36 + edge:
            return 1.0 - (phase - .36) / edge
        return 0.0
    raise ValueError(kind)


def _normal_from_height(height_bytes: bytes, size: int, strength: float = .10) -> bytes:
    values = [value / 255.0 for value in height_bytes]
    out = bytearray()
    for y in range(size):
        for x in range(size):
            xl, xr = max(0, x - 1), min(size - 1, x + 1)
            yd, yu = max(0, y - 1), min(size - 1, y + 1)
            dx = values[y * size + xr] - values[y * size + xl]
            dy = values[yu * size + x] - values[yd * size + x]
            nx, ny = -dx * size * strength, dy * size * strength
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + 1.0)
            out.extend((_u8(nx * inv * .5 + .5), _u8(ny * inv * .5 + .5), _u8(inv * .5 + .5)))
    return bytes(out)


def layered_game_material_fields(base_profile: str, layers: list[dict], size: int = 256,
                                 seed: int = 1, color: tuple[int, int, int] | None = None) -> tuple[dict, list[dict]]:
    if base_profile not in PROFILE_BY_NAME:
        raise ValueError(f"unknown rich material profile: {base_profile}")
    if not isinstance(layers, list) or len(layers) > 16:
        raise ValueError("layers must be a list of at most 16 entries")
    normalized = [_validate_layer(raw, index) for index, raw in enumerate(layers)]
    fields = rich_game_material_fields(base_profile, size=size, seed=seed, color=color)

    base = bytearray(fields["base_color"][1])
    rough = bytearray(fields["roughness"][1])
    metal = bytearray(fields["metallic"][1])
    height = bytearray(fields["height"][1])
    ao = bytearray(fields["ao"][1])
    masks: list[dict] = []

    for index, layer in enumerate(normalized):
        kind = layer["type"]
        amount = layer["amount"]
        scale = layer["scale"]
        layer_seed = seed + layer["seed_offset"]
        mask_bytes = bytearray()
        chosen = layer["color"]
        for y in range(size):
            v = (y + .5) / size
            for x in range(size):
                u = (x + .5) / size
                raw_mask = _mask(kind, u, v, layer_seed, scale)
                alpha = _clamp01(raw_mask * amount)
                mask_bytes.append(_u8(raw_mask))
                i = y * size + x
                j = i * 3
                r, g, b = base[j], base[j + 1], base[j + 2]
                rv, mv, hv, av = rough[i] / 255.0, metal[i] / 255.0, height[i] / 255.0, ao[i] / 255.0

                if kind == "salt":
                    target = chosen or (232, 229, 207)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .90, alpha)
                    mv = _mix(mv, 0.0, alpha * .65)
                    hv = _clamp01(hv + alpha * .08)
                elif kind == "dirt":
                    target = chosen or (86, 65, 42)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .84, alpha)
                    hv = _clamp01(hv + alpha * .025)
                elif kind == "wetness":
                    r, g, b = (r * (1.0 - alpha * .24), g * (1.0 - alpha * .24), b * (1.0 - alpha * .24))
                    rv = _mix(rv, .10, alpha * .92)
                elif kind == "scuff":
                    target = chosen or (210, 207, 194)
                    r, g, b = (_mix(r, target[0], alpha * .72), _mix(g, target[1], alpha * .72), _mix(b, target[2], alpha * .72))
                    rv = _mix(rv, .73, alpha)
                    hv = _clamp01(hv - alpha * .055)
                elif kind == "paint-chip":
                    target = chosen or (58, 63, 65)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .48, alpha)
                    mv = _mix(mv, .58, alpha * .65)
                    hv = _clamp01(hv - alpha * .045)
                elif kind == "rust":
                    target = chosen or (137, 69, 31)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .90, alpha)
                    mv = _mix(mv, .05, alpha)
                    hv = _clamp01(hv + alpha * .045)
                    av = _mix(av, .84, alpha * .55)
                elif kind == "sun-bleach":
                    target = chosen or (242, 234, 210)
                    r, g, b = (_mix(r, target[0], alpha * .55), _mix(g, target[1], alpha * .55), _mix(b, target[2], alpha * .55))
                    rv = _mix(rv, .72, alpha * .55)
                elif kind == "algae":
                    target = chosen or (63, 86, 46)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .78, alpha)
                    hv = _clamp01(hv + alpha * .038)
                elif kind == "decal-stripe":
                    target = chosen or (232, 78, 48)
                    r, g, b = (_mix(r, target[0], alpha), _mix(g, target[1], alpha), _mix(b, target[2], alpha))
                    rv = _mix(rv, .40, alpha)
                    hv = _clamp01(hv + alpha * .010)

                base[j:j + 3] = bytes((max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b)))))
                rough[i] = _u8(rv)
                metal[i] = _u8(mv)
                height[i] = _u8(hv)
                ao[i] = _u8(av)

        masks.append({"index": index, "type": kind, "pixels": bytes(mask_bytes), "recipe": layer})

    normal = _normal_from_height(bytes(height), size)
    orm = bytes(channel for i in range(size * size) for channel in (ao[i], rough[i], metal[i]))
    return {
        "base_color": (3, bytes(base)),
        "roughness": (1, bytes(rough)),
        "metallic": (1, bytes(metal)),
        "height": (1, bytes(height)),
        "normal": (3, normal),
        "ao": (1, bytes(ao)),
        "orm": (3, orm),
    }, masks


def generate_layered_game_material(path, base_profile: str, layers: list[dict], size: int = 256,
                                   seed: int = 1, color: tuple[int, int, int] | None = None) -> dict:
    """Write one immutable layered PBR material bundle and return its manifest."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    fields, masks = layered_game_material_fields(base_profile, layers, size=size, seed=seed, color=color)

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

    layer_dir = target / "layer_masks"
    layer_dir.mkdir()
    layer_records = []
    for record in masks:
        payload = png_bytes(size, size, 1, record["pixels"])
        filename = f"{record['index']:02d}_{record['type']}.png"
        (layer_dir / filename).write_bytes(payload)
        layer_records.append({
            "index": record["index"],
            "type": record["type"],
            "recipe": record["recipe"],
            "file": str(Path("layer_masks") / filename),
            "sha256": hashlib.sha256(payload).hexdigest(),
        })

    manifest = {
        "schema": "axm.layered-game-material/v0.1",
        "base_profile": base_profile,
        "size": size,
        "seed": seed,
        "color": list(PROFILE_BY_NAME[base_profile].default_rgb if color is None else color),
        "layers": layer_records,
        "maps": maps,
        "orm_channels": ["occlusion", "roughness", "metallic"],
        "normal_convention": "tangent +Y",
        "truth": (
            "Final PBR maps contain deterministic authored UV-space layer composition. "
            "Layer masks are preserved as evidence, but are not mesh-curvature/contact/simulation evidence."
        ),
    }
    (target / "layered-game-material.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest

"""Portable material fields and opt-in game finishes; no renderer or AI required.

Finishes operate on surface maps, not silhouettes, lighting or animation.
Existing metal/fabric donors and the Blender hero surfaces remain unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path

from .donor_metal import PaintedMetalSpec, painted_metal_fields
from .fabric_material import FabricSpec, fabric_fields
from .fabric_noise import fbm, png_bytes
from .mixed_project import build_mixed_project


@dataclass(frozen=True)
class Finish:
    name: str
    value_bands: int
    band_mix: float
    normal_detail: float
    roughness_floor: float
    brush_strength: float = 0.0


FINISHES = (
    Finish("realistic", 0, 0.0, 1.0, 0.0),
    Finish("comic-salvage", 5, 0.65, 0.60, 0.44),
    Finish("painted-adventure", 7, 0.35, 0.38, 0.66, 0.12),
    Finish("graphic-toon", 3, 1.0, 0.0, 0.78),
)
FAMILIES = ("painted-metal", "woven-fabric", "rubber", "leather", "ceramic", "carved-wood")
DEFAULT_COLORS = {
    "painted-metal": (229, 173, 50), "woven-fabric": (184, 60, 53),
    "rubber": (37, 43, 48), "leather": (100, 66, 51),
    "ceramic": (225, 214, 186), "carved-wood": (157, 100, 48),
}


def _u8(value):
    return max(0, min(255, round(value * 255)))


def _inputs(size, seed):
    if type(size) is not int or not 16 <= size <= 512:
        raise ValueError("size must be an integer from 16 to 512")
    if type(seed) is not int or not 0 <= seed <= 2147483647:
        raise ValueError("seed must be an integer from 0 to 2147483647")


def _finish(name):
    for profile in FINISHES:
        if profile.name == name:
            return profile
    raise ValueError(f"unknown finish: {name}")


def _normal_from_height(height, size, strength):
    # Images are top-to-bottom; positive tangent Y is increasing UV V (up).
    result = bytearray()
    for y in range(size):
        for x in range(size):
            dx = height[y * size + min(x + 1, size - 1)] - height[y * size + max(x - 1, 0)]
            dy = height[min(y + 1, size - 1) * size + x] - height[max(y - 1, 0) * size + x]
            nx, ny = -dx * size * strength, dy * size * strength
            inv = 1 / math.sqrt(nx * nx + ny * ny + 1)
            result.extend((_u8(nx * inv * .5 + .5), _u8(ny * inv * .5 + .5), _u8(inv * .5 + .5)))
    return bytes(result)


def _authored_fields(family, size, seed, color):
    base, rough, height = bytearray(), bytearray(), []
    for y in range(size):
        v = (y + .5) / size
        for x in range(size):
            u = (x + .5) / size
            broad = fbm(u * 5, v * 5, seed, 3)
            grain = fbm(u * 46, v * 46, seed + 101, 3)
            if family == "rubber":
                shade, r, h = .93 + grain * .08, .72 + grain * .15, .5 + grain * .008
            elif family == "leather":
                pore = max(0, (.48 - grain) * 3)
                shade, r, h = .88 + broad * .16 - pore * .15, .58 + grain * .19, .5 + grain * .012 - pore * .016
            elif family == "ceramic":
                speck = max(0, (grain - .68) * 4)
                shade, r, h = .97 + broad * .04 - speck * .09, .18 + grain * .10, .5 + grain * .001
            else:
                # Bent longitudinal grain; knots alter the field rather than color alone.
                dx, dy = u - .37, (v - .58) * .45
                knot = math.exp(-(dx * dx + dy * dy) * 55)
                rings = .5 + .5 * math.sin((u * 26 + broad * 1.8 + knot * 2.3) * math.tau)
                shade, r, h = .72 + rings * .25 + broad * .10, .65 + grain * .17, .5 + rings * .013
            base.extend(max(0, min(255, round(c * shade))) for c in color)
            rough.append(_u8(r))
            height.append(h)
    ao, metallic = bytes([255]) * (size * size), bytes(size * size)
    orm = bytes(c for r in rough for c in (255, r, 0))
    return {"base_color": (3, bytes(base)), "roughness": (1, bytes(rough)),
            "height": (1, bytes(_u8(h) for h in height)),
            "normal": (3, _normal_from_height(height, size, .14)),
            "ao": (1, ao), "metallic": (1, metallic), "orm": (3, orm)}


def _validate_fields(fields, size):
    required = {"base_color": 3, "roughness": 1, "normal": 3, "ao": 1, "orm": 3}
    if not isinstance(fields, dict) or not required.keys() <= fields.keys():
        raise ValueError("fields require base_color, roughness, normal, ao and orm")
    for name, value in fields.items():
        if not isinstance(value, (list, tuple)) or len(value) != 2:
            raise ValueError(f"invalid field: {name}")
        channels, data = value
        if type(channels) is not int or channels not in (1, 3, 4) or not isinstance(data, bytes) or len(data) != size * size * channels:
            raise ValueError(f"invalid field bytes: {name}")
        expected = required.get(name, 1 if name in ("metallic", "height", "thickness") else channels)
        if channels != expected:
            raise ValueError(f"invalid channel count: {name}")
    orm = fields["orm"][1]
    if orm[0::3] != fields["ao"][1] or orm[1::3] != fields["roughness"][1]:
        raise ValueError("ORM must match the separate AO and roughness fields")
    if "metallic" in fields and orm[2::3] != fields["metallic"][1]:
        raise ValueError("ORM must match the separate metallic field")


def apply_finish(fields, size, finish="realistic", seed=1):
    """Return new map fields. Realistic is byte-for-byte identity, not a restyle.

    AO and conductivity are invariant. Graphic finishes quantize albedo value,
    reduce tangent detail and broaden roughness; they do NOT implement cel light.
    """
    _inputs(size, seed)
    profile = _finish(finish)
    _validate_fields(fields, size)
    result = dict(fields)
    if finish == "realistic":
        return result
    base, normal = bytearray(), bytearray()
    source = fields["base_color"][1]
    source_normal = fields["normal"][1]
    for i in range(size * size):
        rgb = source[i * 3:i * 3 + 3]
        value = max(rgb) / 255
        # Quantize HSV value; use interval centres so dark materials stay legible.
        band = min(profile.value_bands - 1, int(value * profile.value_bands))
        target = (band + .5) / profile.value_bands
        value_out = value * (1 - profile.band_mix) + target * profile.band_mix
        if profile.brush_strength:
            u, v = (i % size + .5) / size, (i // size + .5) / size
            brush = fbm(u * 22, v * 5, seed + 4701, 2)
            value_out *= 1 + (brush - .5) * profile.brush_strength * 2
        scale = value_out / value if value else 0
        base.extend(max(0, min(255, round(c * scale))) for c in rgb)
        nx, ny, nz = (c / 127.5 - 1 for c in source_normal[i * 3:i * 3 + 3])
        nx *= profile.normal_detail
        ny *= profile.normal_detail
        nz = 1 + (nz - 1) * profile.normal_detail
        length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if length < 1e-6:
            nx, ny, nz, length = 0, 0, 1, 1
        normal.extend(_u8(c / length * .5 + .5) for c in (nx, ny, nz))
    rough = bytes(max(_u8(profile.roughness_floor), r) for r in fields["roughness"][1])
    old_orm = fields["orm"][1]
    orm = bytes(c for i, r in enumerate(rough) for c in (old_orm[i * 3], r, old_orm[i * 3 + 2]))
    result.update(base_color=(3, bytes(base)), roughness=(1, rough), normal=(3, bytes(normal)), orm=(3, orm))
    return result


def game_material_fields(family, size=128, seed=1, finish="realistic", color=None):
    _inputs(size, seed)
    _finish(finish)
    if family not in FAMILIES:
        raise ValueError(f"unknown material family: {family}")
    color = DEFAULT_COLORS[family] if color is None else color
    if not isinstance(color, (tuple, list)) or len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
        raise ValueError("color requires three integer sRGB bytes")
    if family == "painted-metal":
        fields = painted_metal_fields(size, seed, PaintedMetalSpec(paint_rgb=tuple(color)))
    elif family == "woven-fabric":
        fields = fabric_fields(size, seed, FabricSpec(base_rgb=tuple(color)))
    else:
        fields = _authored_fields(family, size, seed, color)
    return apply_finish(fields, size, finish, seed)


def game_material_catalog():
    return {"schema": "axm.game-material-styles/v0.1", "families": list(FAMILIES),
            "finishes": [asdict(f) for f in FINISHES], "dependencies": [],
            "preserves_existing_generators": True,
            "truth": "Executable surface maps only. Not a complete game art style, cel shader, geometry or animation generator."}


def game_material_request(path, family, size=128, seed=1, finish="realistic", color=None):
    fields = game_material_fields(family, size, seed, finish, color)
    binaries, maps = {}, {}
    for name, (channels, pixels) in fields.items():
        data = png_bytes(size, size, channels, pixels)
        digest = hashlib.sha256(data).hexdigest()
        filename = name + ".png"
        binaries[filename] = {"encoding": "base64", "content": base64.b64encode(data).decode(),
                              "sha256": digest, "media_type": "image/png"}
        maps[name] = {"file": filename, "channels": channels, "sha256": digest,
                      "color_space": "sRGB" if name == "base_color" else "linear-data"}
    manifest = {"schema": "axm.game-material/v0.1", "family": family, "finish": finish,
                "size": size, "seed": seed, "color": list(DEFAULT_COLORS[family] if color is None else color),
                "profile": asdict(_finish(finish)), "maps": maps,
                "orm_channels": ["occlusion", "roughness", "metallic"],
                "normal_convention": "inherited donor for painted-metal/woven-fabric; tangent +Y for other families",
                "truth": "Authored procedural fields, not scanned material. No mesh-aware edge wear, seamless tiling, lighting or engine acceptance claimed.",
                "height_usage": "Authoring proxy; finish modifies normals independently. Re-baking normal from height replaces that finish choice."}
    return {"kind": "mixed-media-project", "direction": "generate reusable game material maps",
            "inputs": {"path": str(path), "project_type": "generic",
                       "text_files": {"game-material.json": json.dumps(manifest, indent=2)},
                       "binary_files": binaries,
                       "checks": [{"type": "media-signature", "path": p, "format": "png"} for p in binaries]}}


def generate_game_material(path, family, size=128, seed=1, finish="realistic", color=None):
    request = game_material_request(path, family, size, seed, finish, color)
    inputs = dict(request["inputs"])
    target = Path(inputs.pop("path"))
    return build_mixed_project(target, **inputs)

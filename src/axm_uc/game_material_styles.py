"""Portable material fields and opt-in game finishes; no renderer or AI required.

Finishes operate on surface maps, not silhouettes, lighting or animation.
Existing metal/fabric donors and the Blender hero surfaces remain unchanged.
"""
from __future__ import annotations

import base64
import hashlib
import json
import math
import random
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


@dataclass(frozen=True)
class WearLayer:
    """One removable top-coat layer over a physically distinct substrate."""
    amount: float = 0.38
    substrate_rgb: tuple[int, int, int] = (92, 101, 105)
    substrate_roughness: float = 0.34
    substrate_metallic: float = 1.0
    chip_scale: float = 15.0
    scratch_count: int = 14
    edge_normal_strength: float = 0.014


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


def _unit(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"{name} must be finite from 0 to 1")
    return float(value)


def _wear_layer(layer):
    if not isinstance(layer, WearLayer):
        raise ValueError("layer must be WearLayer")
    for name in ("amount", "substrate_roughness", "substrate_metallic", "edge_normal_strength"):
        _unit(getattr(layer, name), name)
    if (not isinstance(layer.substrate_rgb, (tuple, list)) or len(layer.substrate_rgb) != 3
            or any(type(c) is not int or not 0 <= c <= 255 for c in layer.substrate_rgb)):
        raise ValueError("substrate_rgb requires three integer sRGB bytes")
    if type(layer.chip_scale) not in (int, float) or not math.isfinite(layer.chip_scale) or not 2 <= layer.chip_scale <= 128:
        raise ValueError("chip_scale must be finite from 2 to 128")
    if type(layer.scratch_count) is not int or not 0 <= layer.scratch_count <= 128:
        raise ValueError("scratch_count must be an integer from 0 to 128")
    return layer


def protected_regions_mask(size, rectangles):
    """Rasterize normalized authored rectangles; 255 vetoes all wear exactly."""
    if type(size) is not int or not 16 <= size <= 512:
        raise ValueError("size must be an integer from 16 to 512")
    if not isinstance(rectangles, (tuple, list)) or len(rectangles) > 64:
        raise ValueError("rectangles must be a list of at most 64 regions")
    checked = []
    for rect in rectangles:
        if not isinstance(rect, (tuple, list)) or len(rect) != 4:
            raise ValueError("each protected rectangle needs x0 y0 x1 y1")
        x0, y0, x1, y1 = (_unit(value, "rectangle coordinate") for value in rect)
        if x0 >= x1 or y0 >= y1:
            raise ValueError("protected rectangle must have positive area")
        checked.append((x0, y0, x1, y1))
    return bytes(255 if any(x0 <= (x + .5) / size <= x1 and y0 <= (y + .5) / size <= y1
                            for x0, y0, x1, y1 in checked) else 0
                 for y in range(size) for x in range(size))


def _mask(value, size, name):
    if value is None:
        return bytes(size * size)
    if not isinstance(value, bytes) or len(value) != size * size:
        raise ValueError(f"{name} must be one byte per pixel")
    return value


def _distance_to_segment(px, py, ax, ay, bx, by):
    vx, vy, wx, wy = bx - ax, by - ay, px - ax, py - ay
    length = vx * vx + vy * vy
    if length <= 1e-12:
        return math.hypot(wx, wy)
    t = max(0, min(1, (wx * vx + wy * vy) / length))
    return math.hypot(px - ax - t * vx, py - ay - t * vy)


def procedural_wear_mask(size, seed=1, layer=WearLayer()):
    """Return deterministic UV-space chip/scratch proposal; it is not mesh wear."""
    _inputs(size, seed)
    layer = _wear_layer(layer)
    rng = random.Random(seed ^ 0xA4D6E29)
    scratches = []
    for _ in range(layer.scratch_count):
        ax, ay = rng.random(), rng.random()
        angle, length = rng.uniform(-math.pi, math.pi), rng.uniform(.06, .34)
        scratches.append((ax, ay, ax + math.cos(angle) * length,
                          ay + math.sin(angle) * length, rng.uniform(.002, .009)))
    output = bytearray()
    # Amount moves the chip threshold and scratch opacity; zero stays exact zero.
    threshold = .77 - layer.amount * .22
    for y in range(size):
        v = (y + .5) / size
        for x in range(size):
            u = (x + .5) / size
            broad = fbm(u * 4.7, v * 4.7, seed + 7103, 3)
            chip = fbm(u * layer.chip_scale, v * layer.chip_scale, seed + 7207, 4)
            islands = max(0, (chip * .78 + broad * .22 - threshold) / max(.04, 1 - threshold))
            scratch = max((max(0, 1 - _distance_to_segment(u, v, *line[:4]) / line[4])
                           for line in scratches), default=0)
            damage = max(islands, scratch * (.35 + layer.amount * .65)) * layer.amount
            output.append(_u8(min(1, damage)))
    return bytes(output)


def _srgb_linear(value):
    value /= 255
    return value / 12.92 if value <= .04045 else ((value + .055) / 1.055) ** 2.4


def _linear_srgb(value):
    value = max(0, min(1, value))
    return _u8(value * 12.92 if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055)


def apply_layered_wear(fields, size, seed=1, layer=WearLayer(), protected_mask=None, wear_mask=None,
                       normal_convention="tangent +Y"):
    """Composite paint loss without mutating the canonical top-coat fields.

    A supplied wear mask is an untrusted proposal; callers must record whether it
    was authored, projected or mesh-baked. Protection always wins and is retained.
    Without a supplied mask the candidate is explicitly procedural UV damage.
    """
    _inputs(size, seed)
    _validate_fields(fields, size)
    layer = _wear_layer(layer)
    protected = _mask(protected_mask, size, "protected_mask")
    if normal_convention not in ("tangent +Y", "tangent -Y"):
        raise ValueError("normal_convention must be tangent +Y or tangent -Y")
    candidate = (bytes(round(value * layer.amount) for value in _mask(wear_mask, size, "wear_mask"))
                 if wear_mask is not None else procedural_wear_mask(size, seed, layer))
    exposed = bytes(round(candidate[i] * (255 - protected[i]) / 255) for i in range(size * size))
    paint = bytes(255 - value for value in exposed)
    coat_height = paint
    overlay = _normal_from_height([value / 255 for value in coat_height], size, layer.edge_normal_strength)
    if normal_convention == "tangent -Y":
        overlay = bytes(255 - value if index % 3 == 1 else value for index, value in enumerate(overlay))
    source_base, source_rough, source_normal = fields["base_color"][1], fields["roughness"][1], fields["normal"][1]
    source_metal = fields.get("metallic", (1, fields["orm"][1][2::3]))[1]
    base, rough, metal, normal = bytearray(), bytearray(), bytearray(), bytearray()
    substrate = [_srgb_linear(value) for value in layer.substrate_rgb]
    for i, byte in enumerate(exposed):
        mix = byte / 255
        if byte == 0:
            base.extend(source_base[i * 3:i * 3 + 3])
            rough.append(source_rough[i])
            metal.append(source_metal[i])
            normal.extend(source_normal[i * 3:i * 3 + 3])
            continue
        for channel in range(3):
            top = _srgb_linear(source_base[i * 3 + channel])
            base.append(_linear_srgb(top * (1 - mix) + substrate[channel] * mix))
        rough.append(_u8(source_rough[i] / 255 * (1 - mix) + layer.substrate_roughness * mix))
        metal.append(_u8(source_metal[i] / 255 * (1 - mix) + layer.substrate_metallic * mix))
        source_xyz = [value / 127.5 - 1 for value in source_normal[i * 3:i * 3 + 3]]
        overlay_xyz = [value / 127.5 - 1 for value in overlay[i * 3:i * 3 + 3]]
        nx, ny, nz = source_xyz[0] + overlay_xyz[0], source_xyz[1] + overlay_xyz[1], source_xyz[2]
        length = math.sqrt(nx * nx + ny * ny + nz * nz) or 1
        normal.extend(_u8(value / length * .5 + .5) for value in (nx, ny, nz))
    ao = fields["ao"][1]
    orm = bytes(value for i in range(size * size) for value in (ao[i], rough[i], metal[i]))
    result = dict(fields)
    result.update(base_color=(3, bytes(base)), roughness=(1, bytes(rough)), metallic=(1, bytes(metal)),
                  normal=(3, bytes(normal)), orm=(3, orm), wear_mask=(1, candidate),
                  protection_mask=(1, protected), exposed_mask=(1, exposed), coat_height=(1, coat_height))
    return result


def layered_game_material_fields(family, size=128, seed=1, finish="realistic", color=None,
                                 layer=WearLayer(), protected_mask=None, wear_mask=None, surface_parameters=None):
    """Build top coat, then add an opt-in removable layer with source-family orientation."""
    fields = game_material_fields(family, size, seed, finish, color, surface_parameters)
    convention = "tangent -Y" if family in ("painted-metal", "woven-fabric") else "tangent +Y"
    return apply_layered_wear(fields, size, seed, layer, protected_mask, wear_mask, convention)


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


def _smooth_values(values, size):
    """Small edge-aware separable filter; retain grain/paint-chip boundaries."""
    radius = max(1, size // 64)
    rows, output = [0.0] * len(values), [0.0] * len(values)
    for source, dest, horizontal in ((values, rows, True), (rows, output, False)):
        for y in range(size):
            for x in range(size):
                centre = source[y * size + x]
                total = weight_sum = 0.0
                for delta in range(-radius, radius + 1):
                    xx, yy = (x + delta, y) if horizontal else (x, y + delta)
                    if not (0 <= xx < size and 0 <= yy < size):
                        continue
                    sample = source[yy * size + xx]
                    weight = 1 / (1 + ((sample - centre) / .025) ** 4)
                    total += sample * weight
                    weight_sum += weight
                dest[y * size + x] = total / weight_sum
    return output


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
    values = [max(source[i:i + 3]) / 255 for i in range(0, len(source), 3)]
    smooth_values = _smooth_values(values, size)
    low, high = min(smooth_values), max(smooth_values)
    span = high - low
    for i in range(size * size):
        rgb = source[i * 3:i * 3 + 3]
        value = values[i]
        # Quantize within this field's own range. Absolute 0..1 bands can erase
        # an entire dark wood/rubber signal or turn threshold noise into speckles.
        local = (smooth_values[i] - low) / span if span > 1e-8 else 0
        band = max(0, min(profile.value_bands - 1, round(local * (profile.value_bands - 1))))
        target = low + span * band / (profile.value_bands - 1)
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


def _surface_parameters(family, raw):
    if raw is None:
        return {}
    ranges = {"wear": (0,1), "scratches": (0,128), "grain_scale": (2,256),
              "paint_roughness": (0,1), "metal_roughness": (0,1), "normal_strength": (0,8),
              "height_grain_amplitude": (0,1), "height_broad_amplitude": (0,1),
              "height_scratch_depth": (0,1), "height_pit_depth": (0,1),
              "pit_wear_strength": (0,1), "base_grain_variation": (0,1), "roughness_grain_variation": (0,1)}
    if family != "painted-metal" or not isinstance(raw, dict) or set(raw)-ranges.keys():
        raise ValueError("surface_parameters currently supports named painted-metal controls only")
    for name, value in raw.items():
        low, high = ranges[name]
        if type(value) not in (int,float) or not math.isfinite(value) or not low <= value <= high or (name == "scratches" and type(value) is not int):
            raise ValueError("invalid painted-metal surface parameter: " + name)
    return dict(raw)


def game_material_fields(family, size=128, seed=1, finish="realistic", color=None, surface_parameters=None):
    _inputs(size, seed)
    _finish(finish)
    if family not in FAMILIES:
        raise ValueError(f"unknown material family: {family}")
    controls = _surface_parameters(family, surface_parameters)
    color = DEFAULT_COLORS[family] if color is None else color
    if not isinstance(color, (tuple, list)) or len(color) != 3 or any(type(c) is not int or not 0 <= c <= 255 for c in color):
        raise ValueError("color requires three integer sRGB bytes")
    if family == "painted-metal":
        fields = painted_metal_fields(size, seed, PaintedMetalSpec(paint_rgb=tuple(color), **controls))
    elif family == "woven-fabric":
        fields = fabric_fields(size, seed, FabricSpec(base_rgb=tuple(color)))
    else:
        fields = _authored_fields(family, size, seed, color)
    return apply_finish(fields, size, finish, seed)


def game_material_catalog():
    return {"schema": "axm.game-material-styles/v0.1", "families": list(FAMILIES),
            "finishes": [asdict(f) for f in FINISHES], "dependencies": [],
            "optional_layers": [{"name": "removable-top-coat", "default_parameters": asdict(WearLayer()),
                                 "mask_order": ["wear proposal", "protected-region veto", "actual exposure"],
                                 "wear_sources": ["procedural-uv", "caller-declared authored/projected/mesh-baked"]}],
            "preserves_existing_generators": True,
            "truth": "Executable surface maps only. Not a complete game art style, cel shader, geometry or animation generator."}


def game_material_request(path, family, size=128, seed=1, finish="realistic", color=None,
                          layer=None, protected_mask=None, wear_mask=None,
                          protected_mask_source=None, wear_mask_source=None, surface_parameters=None):
    if layer is None:
        if any(value is not None for value in (protected_mask, wear_mask, protected_mask_source, wear_mask_source)):
            raise ValueError("wear/protection inputs require a WearLayer")
        fields = game_material_fields(family, size, seed, finish, color, surface_parameters)
    else:
        _wear_layer(layer)
        if protected_mask is not None and not protected_mask_source:
            raise ValueError("protected_mask_source is required for supplied protection")
        if wear_mask is not None and not wear_mask_source:
            raise ValueError("wear_mask_source is required for supplied wear")
        for value, name in ((protected_mask_source, "protected_mask_source"),
                            (wear_mask_source, "wear_mask_source")):
            if value is not None and (not isinstance(value, str) or not value.strip() or len(value) > 100):
                raise ValueError(f"{name} must be a short non-empty label")
        fields = layered_game_material_fields(family, size, seed, finish, color, layer,
                                              protected_mask, wear_mask, surface_parameters)
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
                "normal_convention": "tangent -Y" if family in ("painted-metal", "woven-fabric") else "tangent +Y",
                "truth": "Authored procedural fields, not scanned material. No mesh-aware edge wear, seamless tiling, lighting or engine acceptance claimed.",
                "height_usage": "Authoring proxy; finish modifies normals independently. Re-baking normal from height replaces that finish choice."}
    if surface_parameters is not None:
        manifest["surface_parameters"] = _surface_parameters(family, surface_parameters)
    if layer is not None:
        manifest["layers"] = [{"type": "removable-top-coat", "parameters": asdict(layer),
                               "wear_mask_source": wear_mask_source or "procedural-uv",
                               "protected_mask_source": protected_mask_source or "none",
                               "maps": {"proposal": "wear_mask", "protected": "protection_mask",
                                        "actual_exposure": "exposed_mask", "remaining_coat": "coat_height"},
                               "truth": "Procedural UV wear is not mesh-derived. Supplied mask source is caller-declared; protection vetoes exposure."}]
        manifest["truth"] = "Layered procedural material fields, not scans. Wear source is explicit; no automatic mesh-edge derivation, seamless tiling, lighting or engine acceptance claimed."
    return {"kind": "mixed-media-project", "direction": "generate reusable game material maps",
            "inputs": {"path": str(path), "project_type": "generic",
                       "text_files": {"game-material.json": json.dumps(manifest, indent=2)},
                       "binary_files": binaries,
                       "checks": [{"type": "media-signature", "path": p, "format": "png"} for p in binaries]}}


def generate_game_material(path, family, size=128, seed=1, finish="realistic", color=None,
                           layer=None, protected_mask=None, wear_mask=None,
                           protected_mask_source=None, wear_mask_source=None, surface_parameters=None):
    request = game_material_request(path, family, size, seed, finish, color, layer,
                                    protected_mask, wear_mask, protected_mask_source, wear_mask_source, surface_parameters)
    inputs = dict(request["inputs"])
    target = Path(inputs.pop("path"))
    return build_mixed_project(target, **inputs)

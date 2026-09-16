"""Game-art finishing for UC's expanded deterministic rich material profiles.

This module composes two existing UC capabilities instead of inventing a separate
material stack:

1. ``rich_game_materials`` supplies profile-specific PBR fields for plastic,
   fiberglass, cloth, rope, metals, wood, foam and other game surfaces.
2. ``game_material_styles`` supplies optional value-band game finishes and a
   removable wear layer.

The composition stays renderer-independent and dependency-free. Wear remains an
authored/procedural UV proposal unless a caller supplies mesh-derived evidence;
this module never claims curvature, contact or physical abrasion was observed.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .fabric_noise import png_bytes
from .game_material_styles import FINISHES, WearLayer, apply_finish, apply_layered_wear
from .rich_game_materials import PROFILE_BY_NAME, rich_game_material_catalog, rich_game_material_fields


PORTABLE_MAPS = ("base_color", "roughness", "metallic", "height", "normal", "ao", "orm")
FINISH_BY_NAME = {finish.name: finish for finish in FINISHES}


def _unit(value: float, name: str) -> float:
    if type(value) not in (int, float) or not 0 <= float(value) <= 1:
        raise ValueError(f"{name} must be from 0 to 1")
    return float(value)


def _rgb(value, name: str) -> tuple[int, int, int]:
    if not isinstance(value, (tuple, list)) or len(value) != 3:
        raise ValueError(f"{name} requires three integer sRGB bytes")
    result = tuple(value)
    if any(type(channel) is not int or not 0 <= channel <= 255 for channel in result):
        raise ValueError(f"{name} requires three integer sRGB bytes")
    return result


def rich_game_art_catalog() -> dict:
    catalog = dict(rich_game_material_catalog())
    catalog["game_finishes"] = [asdict(finish) for finish in FINISHES]
    catalog["optional_wear_layer"] = {
        "amount": "0..1; zero is exact no-wear",
        "substrate_color": "optional explicit sRGB bytes",
        "substrate_roughness": "optional 0..1",
        "substrate_metallic": "optional 0..1",
        "source": "procedural UV proposal unless caller supplies and declares another source",
    }
    catalog["composition_truth"] = (
        "Rich profile + game finish + optional UV wear. This is not mesh-aware edge wear, "
        "lighting, a cel shader, geometry detail, or automatic visual acceptance."
    )
    return catalog


def rich_game_art_fields(
    profile_name: str,
    size: int = 256,
    seed: int = 1,
    color: tuple[int, int, int] | None = None,
    finish: str = "realistic",
    wear_amount: float = 0.0,
    substrate_color: tuple[int, int, int] | None = None,
    substrate_roughness: float | None = None,
    substrate_metallic: float | None = None,
) -> dict:
    """Return portable PBR maps after optional UC game-art finishing.

    ``realistic`` + zero wear is byte-for-byte the underlying rich material.
    Other finishes use UC's existing value-band/roughness/normal treatment.
    The optional wear layer remains procedural UV damage and is never described as
    measured or mesh-derived unless another caller explicitly provides such evidence.
    """
    if profile_name not in PROFILE_BY_NAME:
        raise ValueError(f"unknown rich material profile: {profile_name}")
    if finish not in FINISH_BY_NAME:
        raise ValueError(f"unknown game finish: {finish}")
    wear_amount = _unit(wear_amount, "wear_amount")
    if color is not None:
        color = _rgb(color, "color")

    profile = PROFILE_BY_NAME[profile_name]
    fields = rich_game_material_fields(profile_name, size, seed, color)
    fields = apply_finish(fields, size, finish, seed)

    if wear_amount > 0:
        source_color = profile.default_rgb if color is None else color
        if substrate_color is None:
            # Conservative same-family underlayer: darker/desaturated rather than
            # silently turning plastic/fabric into exposed metal.
            substrate_color = tuple(max(0, min(255, round(channel * .62 + 20))) for channel in source_color)
        else:
            substrate_color = _rgb(substrate_color, "substrate_color")
        if substrate_roughness is None:
            substrate_roughness = min(.95, max(.18, profile.roughness + .14))
        else:
            substrate_roughness = _unit(substrate_roughness, "substrate_roughness")
        if substrate_metallic is None:
            substrate_metallic = profile.metallic
        else:
            substrate_metallic = _unit(substrate_metallic, "substrate_metallic")
        layer = WearLayer(
            amount=wear_amount,
            substrate_rgb=substrate_color,
            substrate_roughness=substrate_roughness,
            substrate_metallic=substrate_metallic,
            chip_scale=17.0,
            scratch_count=max(6, round(8 + wear_amount * 30)),
            edge_normal_strength=.018,
        )
        fields = apply_layered_wear(
            fields,
            size,
            seed + 17011,
            layer=layer,
            normal_convention="tangent +Y",
        )

    # The existing rich Blender bridge intentionally accepts exactly these maps.
    return {name: fields[name] for name in PORTABLE_MAPS}


def generate_rich_game_art_material(
    path,
    profile_name: str,
    size: int = 256,
    seed: int = 1,
    color: tuple[int, int, int] | None = None,
    finish: str = "realistic",
    wear_amount: float = 0.0,
    substrate_color: tuple[int, int, int] | None = None,
    substrate_roughness: float | None = None,
    substrate_metallic: float | None = None,
) -> dict:
    """Write one immutable rich material bundle with explicit game-art treatment."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(target)
    if profile_name not in PROFILE_BY_NAME:
        raise ValueError(f"unknown rich material profile: {profile_name}")
    if finish not in FINISH_BY_NAME:
        raise ValueError(f"unknown game finish: {finish}")

    profile = PROFILE_BY_NAME[profile_name]
    fields = rich_game_art_fields(
        profile_name,
        size=size,
        seed=seed,
        color=color,
        finish=finish,
        wear_amount=wear_amount,
        substrate_color=substrate_color,
        substrate_roughness=substrate_roughness,
        substrate_metallic=substrate_metallic,
    )
    target.mkdir(parents=True)
    maps = {}
    for name in PORTABLE_MAPS:
        channels, pixels = fields[name]
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
        "color": list(profile.default_rgb if color is None else _rgb(color, "color")),
        "maps": maps,
        "orm_channels": ["occlusion", "roughness", "metallic"],
        "normal_convention": "tangent +Y",
        "game_finish": finish,
        "wear_layer": {
            "amount": float(wear_amount),
            "source": "procedural-uv" if wear_amount > 0 else "none",
            "substrate_color": list(substrate_color) if substrate_color is not None else "derived-same-family",
            "substrate_roughness": substrate_roughness if substrate_roughness is not None else "derived-from-profile",
            "substrate_metallic": substrate_metallic if substrate_metallic is not None else "profile-metallicity",
        },
        "truth": (
            "Deterministic authored rich game material composed with an explicit UC game finish. "
            "Wear is procedural UV-space authoring, not observed mesh-edge/contact wear. "
            "No lighting, geometry-detail or aesthetic acceptance is claimed."
        ),
    }
    (target / "rich-game-material.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest

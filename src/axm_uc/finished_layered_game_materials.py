"""Optional game-art finishing for UC layered rich-material bundles.

This composes existing deterministic capabilities in a single portable artifact:
rich material profile -> explicit UV-space surface layers -> optional UC game finish.
Layer masks remain preserved beside the final PBR maps so finishing does not erase
how the surface was authored.

Truth boundary: layer masks remain authored UV-space proposals, not observed
curvature/contact/simulation evidence. Game finishes alter texture fields only;
they do not implement lighting, outlines, geometry detail or aesthetic acceptance.
"""
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
from pathlib import Path

from .fabric_noise import png_bytes
from .game_material_styles import FINISHES, apply_finish
from .layered_game_materials import layered_game_material_fields
from .rich_game_materials import PROFILE_BY_NAME


FINISH_BY_NAME = {finish.name: finish for finish in FINISHES}


def finished_layered_game_material_fields(
    base_profile: str,
    layers: list[dict],
    size: int = 256,
    seed: int = 1,
    color: tuple[int, int, int] | None = None,
    finish: str = "realistic",
) -> tuple[dict, list[dict]]:
    if finish not in FINISH_BY_NAME:
        raise ValueError(f"unknown game finish: {finish}")
    fields, masks = layered_game_material_fields(
        base_profile, layers, size=size, seed=seed, color=color
    )
    return apply_finish(fields, size, finish, seed), masks


def generate_finished_layered_game_material(
    path,
    base_profile: str,
    layers: list[dict],
    size: int = 256,
    seed: int = 1,
    color: tuple[int, int, int] | None = None,
    finish: str = "realistic",
) -> dict:
    """Write one immutable layered PBR bundle with an explicit game finish."""
    target = Path(path)
    if target.exists():
        raise FileExistsError(target)
    if base_profile not in PROFILE_BY_NAME:
        raise ValueError(f"unknown rich material profile: {base_profile}")
    if finish not in FINISH_BY_NAME:
        raise ValueError(f"unknown game finish: {finish}")

    fields, masks = finished_layered_game_material_fields(
        base_profile, layers, size=size, seed=seed, color=color, finish=finish
    )
    target.mkdir(parents=True)

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

    profile = FINISH_BY_NAME[finish]
    manifest = {
        "schema": "axm.layered-game-material/v0.1",
        "base_profile": base_profile,
        "size": size,
        "seed": seed,
        "color": list(PROFILE_BY_NAME[base_profile].default_rgb if color is None else color),
        "layers": layer_records,
        "game_finish": finish,
        "game_finish_profile": asdict(profile),
        "maps": maps,
        "orm_channels": ["occlusion", "roughness", "metallic"],
        "normal_convention": "tangent +Y",
        "truth": (
            "Final PBR maps contain deterministic authored UV-space layer composition plus an explicit UC game finish. "
            "Layer masks are preserved as evidence but are not mesh-curvature/contact/simulation evidence. "
            "The finish changes map values only; no cel lighting, outlines, geometry detail or aesthetic acceptance is claimed."
        ),
    }
    (target / "layered-game-material.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return manifest

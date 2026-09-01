from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Sequence

from .visual_base import (
    SCHEMA, MAX_SIZE, DEFAULT_SIZE, TEXTURES, GRADIENTS, MATERIALS, FIXTURES, OBJ_FIXTURES,
    DECALS, PALETTES, DEFAULT_GRADIENT_STOPS, MATERIAL_SPECS, catalog, png_bytes,
)
from .visual_raster import texture_field, colorize, gradient_rows, _material_maps, _palette, _palette_svg
from .visual_vector import _fixture_svg, _fixture_obj, _decal_svg


def _ensure_target(path: Path, replace: bool, directory: bool = False) -> None:
    if path.exists() and not replace:
        raise FileExistsError(f"target already exists: {path}; pass replace=True to overwrite")
    if directory:
        path.mkdir(parents=True, exist_ok=True)
    else:
        path.parent.mkdir(parents=True, exist_ok=True)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _receipt(target: Path, category: str, kind: str, seed: int, extra: dict[str, Any] | None = None) -> dict[str, Any]:
    result = {
        "schema": SCHEMA,
        "truth_status": "OBSERVED_GENERATED_ASSET",
        "category": category,
        "kind": kind,
        "seed": int(seed),
        "path": str(target),
        "sha256": _sha256(target),
        "bytes": target.stat().st_size,
    }
    if extra:
        result.update(extra)
    return result


def generate_texture(path: Path | str, kind: str, *, seed: int = 0, size: int = DEFAULT_SIZE, colors: Sequence[str] | None = None, scale: float = 1.0, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    size = int(size)
    if not 1 <= size <= MAX_SIZE:
        raise ValueError(f"size must be 1..{MAX_SIZE}")
    kind = kind.casefold()
    _ensure_target(target, replace)
    field = texture_field(kind, size, size, seed=seed, scale=scale)
    palette = colors or ("#101317", "#6F7A84", "#E2E8EE")
    target.write_bytes(png_bytes(size, size, colorize(field, palette), "RGB"))
    return _receipt(target, "texture", kind, seed, {"size": size, "colors": list(palette), "scale": float(scale)})


def generate_gradient(path: Path | str, kind: str, *, size: int = DEFAULT_SIZE, colors: Sequence[str] | None = None, angle: float = 35.0, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    size = int(size)
    if not 1 <= size <= MAX_SIZE:
        raise ValueError(f"size must be 1..{MAX_SIZE}")
    kind = kind.casefold()
    _ensure_target(target, replace)
    palette = tuple(colors or DEFAULT_GRADIENT_STOPS[kind])
    target.write_bytes(png_bytes(size, size, gradient_rows(kind, size, size, palette, angle), "RGB"))
    return _receipt(target, "gradient", kind, 0, {"size": size, "colors": list(palette), "angle": float(angle)})


def generate_material(path: Path | str, kind: str, *, seed: int = 0, size: int = DEFAULT_SIZE, scale: float = 1.0, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    kind = kind.casefold()
    if kind not in MATERIAL_SPECS:
        raise KeyError(f"unknown material kind: {kind}")
    size = int(size)
    if not 1 <= size <= MAX_SIZE:
        raise ValueError(f"size must be 1..{MAX_SIZE}")
    if target.exists() and any(target.iterdir()) and not replace:
        raise FileExistsError(f"target material directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    maps = _material_maps(kind, size, seed, scale)
    files = []
    for channel, (mode, rows) in maps.items():
        output = target / f"{channel}.png"
        output.write_bytes(png_bytes(size, size, rows, mode))
        files.append({"channel": channel, "path": output.name, "sha256": _sha256(output), "bytes": output.stat().st_size})
    spec = MATERIAL_SPECS[kind]
    manifest = {
        "schema": SCHEMA,
        "category": "material",
        "kind": kind,
        "seed": int(seed),
        "size": size,
        "scale": float(scale),
        "pattern": spec["pattern"],
        "channels": {row["channel"]: row["path"] for row in files},
        "parameters": {k: v for k, v in spec.items() if k not in {"pattern", "colors"}},
        "base_colors": list(spec["colors"]),
    }
    manifest_path = target / "material.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    files.append({"channel": "manifest", "path": manifest_path.name, "sha256": _sha256(manifest_path), "bytes": manifest_path.stat().st_size})
    return {"schema": SCHEMA, "truth_status": "OBSERVED_GENERATED_MATERIAL_PACK", "category": "material", "kind": kind, "seed": int(seed), "path": str(target), "files": files}


def generate_fixture(path: Path | str, kind: str, *, format: str = "svg", seed: int = 0, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    kind = kind.casefold()
    format = format.casefold()
    if kind not in FIXTURES:
        raise KeyError(f"unknown fixture kind: {kind}")
    if format not in {"svg", "obj"}:
        raise ValueError("fixture format must be svg or obj")
    if format == "obj" and kind not in OBJ_FIXTURES:
        raise ValueError(f"fixture {kind!r} does not have an OBJ generator")
    _ensure_target(target, replace)
    text = _fixture_svg(kind, seed) if format == "svg" else _fixture_obj(kind, seed)
    target.write_text(text, encoding="utf-8")
    return _receipt(target, "fixture", kind, seed, {"format": format})


def generate_decal(path: Path | str, kind: str, *, seed: int = 0, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    kind = kind.casefold()
    if kind not in DECALS:
        raise KeyError(f"unknown decal kind: {kind}")
    _ensure_target(target, replace)
    target.write_text(_decal_svg(kind, seed), encoding="utf-8")
    return _receipt(target, "decal", kind, seed, {"format": "svg"})


def generate_palette(path: Path | str, kind: str, *, seed: int = 0, count: int = 7, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    kind = kind.casefold()
    if kind not in PALETTES:
        raise KeyError(f"unknown palette kind: {kind}")
    if target.exists() and any(target.iterdir()) and not replace:
        raise FileExistsError(f"target palette directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    colors = _palette(kind, seed, count)
    json_path = target / "palette.json"
    svg_path = target / "swatches.svg"
    json_path.write_text(json.dumps({"schema": SCHEMA, "category": "palette", "kind": kind, "seed": seed, "colors": colors}, indent=2) + "\n", encoding="utf-8")
    svg_path.write_text(_palette_svg(colors), encoding="utf-8")
    return {"schema": SCHEMA, "truth_status": "OBSERVED_GENERATED_PALETTE", "category": "palette", "kind": kind, "seed": seed, "path": str(target), "colors": colors, "files": [{"path": p.name, "sha256": _sha256(p), "bytes": p.stat().st_size} for p in (json_path, svg_path)]}


def generate_asset(*, category: str, kind: str, path: Path | str, seed: int = 0, size: int = DEFAULT_SIZE, colors: Sequence[str] | None = None, scale: float = 1.0, angle: float = 35.0, format: str | None = None, count: int = 7, replace: bool = False) -> dict[str, Any]:
    category = category.strip().casefold()
    if category == "texture":
        return generate_texture(path, kind, seed=seed, size=size, colors=colors, scale=scale, replace=replace)
    if category == "gradient":
        return generate_gradient(path, kind, size=size, colors=colors, angle=angle, replace=replace)
    if category == "material":
        return generate_material(path, kind, seed=seed, size=size, scale=scale, replace=replace)
    if category == "fixture":
        return generate_fixture(path, kind, format=format or "svg", seed=seed, replace=replace)
    if category == "decal":
        return generate_decal(path, kind, seed=seed, replace=replace)
    if category == "palette":
        return generate_palette(path, kind, seed=seed, count=count, replace=replace)
    raise KeyError(f"unknown visual asset category: {category}")


def generate_kit(path: Path | str, *, profile: str = "starter", seed: int = 0, size: int = 96, replace: bool = False) -> dict[str, Any]:
    target = Path(path)
    profile = profile.casefold()
    if profile not in {"starter", "full"}:
        raise ValueError("kit profile must be starter or full")
    if target.exists() and any(target.iterdir()) and not replace:
        raise FileExistsError(f"target kit directory is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    chosen = {
        "texture": TEXTURES if profile == "full" else ("wood", "stone", "concrete", "brushed-metal", "fabric", "circuit", "sci-fi-panel", "terrain"),
        "gradient": GRADIENTS if profile == "full" else ("linear", "radial", "sunset", "aurora", "neon", "metallic"),
        "material": MATERIALS if profile == "full" else ("wood", "steel", "concrete", "fabric", "glass", "sci-fi"),
        "fixture": FIXTURES if profile == "full" else ("button", "knob", "panel", "vent", "handle", "gear", "window", "light", "port"),
        "decal": DECALS if profile == "full" else ("arrow", "warning", "hazard-stripes", "target", "panel-lines", "circuit-trace"),
        "palette": PALETTES if profile == "full" else ("analogous", "complementary", "earth", "neon"),
    }
    receipts: list[dict[str, Any]] = []
    for index, kind in enumerate(chosen["texture"]): receipts.append(generate_texture(target / "textures" / f"{kind}.png", kind, seed=seed + index * 17, size=size, replace=True))
    for kind in chosen["gradient"]: receipts.append(generate_gradient(target / "gradients" / f"{kind}.png", kind, size=size, replace=True))
    for index, kind in enumerate(chosen["material"]): receipts.append(generate_material(target / "materials" / kind, kind, seed=seed + 1000 + index * 23, size=size, replace=True))
    for index, kind in enumerate(chosen["fixture"]):
        receipts.append(generate_fixture(target / "fixtures" / f"{kind}.svg", kind, seed=seed + 2000 + index, replace=True))
        if kind in OBJ_FIXTURES: receipts.append(generate_fixture(target / "fixtures-3d" / f"{kind}.obj", kind, format="obj", seed=seed + 2000 + index, replace=True))
    for index, kind in enumerate(chosen["decal"]): receipts.append(generate_decal(target / "decals" / f"{kind}.svg", kind, seed=seed + 3000 + index, replace=True))
    for index, kind in enumerate(chosen["palette"]): receipts.append(generate_palette(target / "palettes" / kind, kind, seed=seed + 4000 + index, replace=True))
    files = [{"path": file.relative_to(target).as_posix(), "sha256": _sha256(file), "bytes": file.stat().st_size} for file in sorted(p for p in target.rglob("*") if p.is_file())]
    manifest = {"schema": SCHEMA, "truth_status": "OBSERVED_GENERATED_VISUAL_ASSET_KIT", "profile": profile, "seed": int(seed), "size": int(size), "catalog": catalog()["outputs"], "receipt_count": len(receipts), "files": files}
    manifest_path = target / "visual-assets.manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return {"schema": SCHEMA, "truth_status": manifest["truth_status"], "profile": profile, "seed": int(seed), "path": str(target), "receipt_count": len(receipts), "file_count": len(files) + 1, "manifest": str(manifest_path), "manifest_sha256": _sha256(manifest_path)}


def operate_visual_assets(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "generate")).strip().casefold()
    if operation == "catalog":
        return catalog()
    requested = Path(str(inputs.get("path", ""))).expanduser()
    if not requested.is_absolute():
        requested = (Path(root) / requested).resolve()
    if operation == "kit":
        return generate_kit(requested, profile=str(inputs.get("profile", "starter")), seed=int(inputs.get("seed", 0)), size=int(inputs.get("size", 96)), replace=bool(inputs.get("replace", False)))
    return generate_asset(category=str(inputs["category"]), kind=str(inputs["kind"]), path=requested, seed=int(inputs.get("seed", 0)), size=int(inputs.get("size", DEFAULT_SIZE)), colors=inputs.get("colors") if isinstance(inputs.get("colors"), list) else None, scale=float(inputs.get("scale", 1.0)), angle=float(inputs.get("angle", 35.0)), format=str(inputs["format"]) if "format" in inputs else None, count=int(inputs.get("count", 7)), replace=bool(inputs.get("replace", False)))

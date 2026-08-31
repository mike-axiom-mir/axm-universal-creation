from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_expanded import expansion_catalog, generate_expanded_asset, generate_expansion_kit


def operate_visual_expansion(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    """Path-explicit bridge for the expanded visual forge.

    The caller chooses the output path. This deliberately does not freeze a final
    local filemap before the local installation/layout has been decided.
    """
    operation = str(inputs.get("operation", "generate")).strip().casefold()
    if operation == "catalog":
        return {
            **expansion_catalog(),
            "layout_status": "CALLER_SELECTED_PATH_NO_FINAL_LOCAL_FILEMAP_ASSUMED",
        }
    requested = Path(str(inputs.get("path", ""))).expanduser()
    if not str(requested):
        raise ValueError("visual expansion requires an explicit output path")
    if not requested.is_absolute():
        requested = (Path(root) / requested).resolve()
    if operation == "kit":
        return generate_expansion_kit(
            requested,
            profile=str(inputs.get("profile", "starter")),
            seed=int(inputs.get("seed", 0)),
            size=int(inputs.get("size", 48)),
            replace=bool(inputs.get("replace", False)),
        )
    return generate_expanded_asset(
        category=str(inputs["category"]),
        kind=str(inputs["kind"]),
        path=requested,
        seed=int(inputs.get("seed", 0)),
        size=int(inputs.get("size", 256)),
        scale=float(inputs.get("scale", 1.0)),
        colors=inputs.get("colors") if isinstance(inputs.get("colors"), list) else None,
        age=float(inputs.get("age", .5)),
        damage=float(inputs.get("damage", .35)),
        moisture=float(inputs.get("moisture", .25)),
        frame_size=int(inputs.get("frame_size", 32)),
        frames=int(inputs.get("frames", 4)),
        columns=int(inputs["columns"]) if inputs.get("columns") is not None else None,
        replace=bool(inputs.get("replace", False)),
    )

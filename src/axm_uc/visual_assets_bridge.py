from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_creation_grammar import compile_visual_recipe, grammar_catalog
from .visual_expanded import expansion_catalog, generate_expanded_asset, generate_expansion_kit
from .visual_state_prompt_atlas import compile_visual_state, visual_state_catalog


def operate_visual_expansion(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    """Path-explicit bridge for the expanded visual forge and visual grammars.

    Generation callers choose the output path. Planning operations are read-only
    and do not invent a final local filemap, renderer, or visual-quality claim.
    """
    operation = str(inputs.get("operation", "generate")).strip().casefold()
    if operation == "catalog":
        return {
            **expansion_catalog(),
            "visual_state_atlas": visual_state_catalog(),
            "layout_status": "CALLER_SELECTED_PATH_NO_FINAL_LOCAL_FILEMAP_ASSUMED",
        }
    if operation == "grammar-catalog":
        return grammar_catalog()
    if operation == "state-catalog":
        return visual_state_catalog(include_aliases=bool(inputs.get("include_aliases", False)))
    if operation == "plan":
        request = inputs.get("request")
        if not isinstance(request, dict):
            raise TypeError("visual plan operation requires request object")
        return compile_visual_recipe(request)
    if operation == "state-compile":
        request = inputs.get("request")
        if not isinstance(request, dict):
            raise TypeError("visual state compile operation requires request object")
        return compile_visual_state(request)

    raw_path = str(inputs.get("path", "")).strip()
    if not raw_path:
        raise ValueError("visual expansion requires an explicit output path")
    requested = Path(raw_path).expanduser()
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
    if operation != "generate":
        raise ValueError(f"unknown visual expansion operation: {operation}")
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

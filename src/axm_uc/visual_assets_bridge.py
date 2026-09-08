from __future__ import annotations

from pathlib import Path
from typing import Any

from .visual_creation_grammar import compile_visual_recipe, grammar_catalog
from .visual_expanded import expansion_catalog, generate_expanded_asset, generate_expansion_kit
from .visual_learning import (
    compile_adaptive_visual_recipe,
    inspect_png,
    inspect_visual_learning,
    record_visual_use,
)
from .visual_3d import assess_3d_output, catalog_3d, compile_3d_request, compile_adaptive_3d_request, forge_3d_asset, inspect_glb, record_3d_review
from .asset_geometry import review_static_glb
from .visual_3d_iteration import (
    forge_3d_iteration, inspect_3d_iteration, plan_3d_iteration,
    reject_3d_iteration, review_3d_iteration, start_3d_iteration,
)
from .rigged_characters import character_catalog, forge_rigged_character, inspect_rigged_character


def operate_visual_expansion(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    """Path-explicit bridge for the expanded visual forge and visual grammar.

    Generation callers choose the output path. Planning operations are read-only
    and do not invent a final local filemap, renderer, or visual-quality claim.
    """
    operation = str(inputs.get("operation", "generate")).strip().casefold()
    if operation == "catalog":
        return {
            **expansion_catalog(),
            "layout_status": "CALLER_SELECTED_PATH_NO_FINAL_LOCAL_FILEMAP_ASSUMED",
        }
    if operation == "grammar-catalog":
        return grammar_catalog()
    if operation == "plan":
        request = inputs.get("request")
        if not isinstance(request, dict):
            raise TypeError("visual plan operation requires request object")
        return compile_visual_recipe(request)
    if operation == "plan-adaptive":
        return compile_adaptive_visual_recipe(root, inputs.get("request"))
    if operation == "inspect-png":
        raw_artifact = str(inputs.get("artifact_path", "")).strip()
        if not raw_artifact:
            raise ValueError("inspect-png requires artifact_path")
        artifact = Path(raw_artifact).expanduser()
        if not artifact.is_absolute():
            artifact = (Path(root) / artifact).resolve()
        return inspect_png(artifact)
    if operation == "record-use":
        return record_visual_use(root, inputs.get("observation"))
    if operation == "inspect-learning":
        return inspect_visual_learning(root, context_key=inputs.get("context_key"))
    if operation == "3d-catalog":
        return catalog_3d()
    if operation == "character-catalog":
        return character_catalog()
    if operation in {"character-forge", "character-inspect"}:
        raw_path = inputs.get("path")
        if not isinstance(raw_path, str) or not raw_path.strip():
            raise ValueError(f"{operation} requires an explicit path")
        target = Path(raw_path)
        if not target.is_absolute():
            target = Path(root) / target
        if operation == "character-inspect":
            return inspect_rigged_character(target)
        return forge_rigged_character(root, inputs.get("request"), target, blender=inputs.get("blender"),
                                       timeout_seconds=int(inputs.get("timeout_seconds", 2400)))
    if operation == "3d-plan":
        return compile_3d_request(inputs.get("request"))
    if operation == "3d-plan-adaptive":
        return compile_adaptive_3d_request(root, inputs.get("request"))
    if operation == "3d-review":
        return record_3d_review(root, inputs.get("review"))
    if operation == "3d-iteration-start":
        return start_3d_iteration(root, inputs.get("spec"))
    if operation == "3d-iteration-status":
        return inspect_3d_iteration(root, inputs.get("run_id"))
    if operation == "3d-iteration-next":
        return plan_3d_iteration(root, inputs.get("run_id"))
    if operation == "3d-iteration-forge":
        return forge_3d_iteration(root, inputs.get("run_id"), change_summary=inputs.get("change_summary"),
                                    blender=inputs.get("blender"),
                                    auto_provision_runtime=bool(inputs.get("auto_provision_runtime", True)),
                                    timeout_seconds=int(inputs.get("timeout_seconds", 1800)))
    if operation == "3d-iteration-review":
        return review_3d_iteration(root, inputs.get("run_id"), inputs.get("review"))
    if operation == "3d-iteration-reject":
        return reject_3d_iteration(root, inputs.get("run_id"), inputs.get("reason"))
    if operation == "3d-assess":
        return assess_3d_output(inputs.get("receipt", {}), inputs.get("manifest", {}), inputs.get("visual_review"))
    if operation in {"inspect-glb", "3d-contract-review"}:
        raw_artifact = str(inputs.get("artifact_path", "")).strip()
        if not raw_artifact:
            raise ValueError(f"{operation} requires artifact_path")
        artifact = Path(raw_artifact).expanduser()
        if not artifact.is_absolute():
            artifact = (Path(root) / artifact).resolve()
        return review_static_glb(artifact, inputs.get("contract")) if operation == "3d-contract-review" else inspect_glb(artifact)
    if operation == "3d-forge":
        raw_output = str(inputs.get("path", "")).strip()
        if not raw_output:
            raise ValueError("3d-forge requires explicit path")
        output = Path(raw_output).expanduser()
        if not output.is_absolute():
            output = (Path(root) / output).resolve()
        return forge_3d_asset(
            root,
            inputs.get("request"),
            output,
            blender=inputs.get("blender"),
            timeout_seconds=int(inputs.get("timeout_seconds", 1800)),
            spatial_contract=inputs.get("spatial_contract"),
        )

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

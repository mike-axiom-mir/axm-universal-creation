from __future__ import annotations

import copy
from pathlib import Path
from typing import Any, Callable


def register_standalone_creation_builtins(
    *,
    capability_error: type[RuntimeError],
    resolve_output_path: Callable[[Path, str], Path],
    is_machine_body_path: Callable[[Path, Path], bool],
    grammar_inventory: Callable[[Path], dict[str, Any]],
    project_error: type[RuntimeError],
) -> dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]]:
    """Return bounded adapters for the restored standalone creation engines.

    This module intentionally contains only the compatibility seam needed to expose
    the recovered engines through the current capability registry. It does not
    alter candidate adoption, recovery, CANON, or machine-body authority.
    """

    def local_creation_provider(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .local_provider import LocalProviderError, operate_local_provider

        operation = str(inputs.get("operation", "inspect")).strip().casefold()
        if operation == "create":
            target = resolve_output_path(root, str(inputs.get("path", "")))
            if is_machine_body_path(root, target):
                raise capability_error(
                    "local provider creation cannot rewrite the live machine body; provider output must enter an ordinary creation surface"
                )
        try:
            return operate_local_provider(root, inputs)
        except LocalProviderError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def host_evidence(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .host_evidence import HostEvidenceError, operate_host_evidence

        operation = str(inputs.get("operation", "inspect")).strip().casefold()
        if operation == "bind":
            target = resolve_output_path(root, str(inputs.get("path", "")))
            if is_machine_body_path(root, target):
                raise capability_error("creation host evidence binds to created project bodies, not the live machine body")
        try:
            return operate_host_evidence(root, inputs)
        except HostEvidenceError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def write_mixed_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .mixed_project import build_mixed_project

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("mixed-media project creation cannot rewrite the live machine body")
        if "checks" in inputs and not isinstance(inputs["checks"], list):
            raise capability_error("mixed-project checks must be a list")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("mixed-project replace must be a boolean")
        try:
            result = build_mixed_project(
                target,
                text_files=inputs.get("text_files"),
                binary_files=inputs.get("binary_files"),
                project_type=str(inputs.get("project_type", "generic")),
                checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
                replace=bool(inputs.get("replace", False)),
                publish_mode=str(inputs.get("publish_mode", "validated")),
            )
            result["grammar_inventory"] = grammar_inventory(target)
            return result
        except project_error as exc:
            raise capability_error(str(exc), getattr(exc, "details", {})) from exc

    def portable_creation_bundle(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .portable_bundle import PortableBundleError, operate_portable_bundle

        operation = str(inputs.get("operation", "inspect")).strip().casefold()
        normalized = dict(inputs)
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("portable bundle replace must be a boolean")
        if "path" in inputs:
            normalized["path"] = str(resolve_output_path(root, str(inputs["path"])))
        if operation == "pack":
            source = resolve_output_path(root, str(inputs.get("source", "")))
            output = resolve_output_path(root, str(inputs.get("path", "")))
            if is_machine_body_path(root, source) or is_machine_body_path(root, output):
                raise capability_error("portable bundle packing is limited to ordinary creation surfaces")
            normalized["source"] = str(source)
        if operation == "unpack":
            target = resolve_output_path(root, str(inputs.get("target", "")))
            if is_machine_body_path(root, target):
                raise capability_error("portable bundle unpacking cannot rewrite the live machine body")
            normalized["target"] = str(target)
        try:
            return operate_portable_bundle(normalized)
        except PortableBundleError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def deterministic_state_machine(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        del root
        from .state_machine import StateMachineError, operate_state_machine

        if "stop_on_hold" in inputs and not isinstance(inputs["stop_on_hold"], bool):
            raise capability_error("state-machine stop_on_hold must be a boolean")
        try:
            return operate_state_machine(inputs)
        except StateMachineError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def procedural_media(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .procedural_media import ProceduralMediaError, publish_media_asset

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("procedural media generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("procedural media replace must be a boolean")
        try:
            return publish_media_asset(
                target,
                operation=inputs["operation"],
                specification=inputs["specification"],
                replace=inputs.get("replace", False),
            )
        except ProceduralMediaError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def browser_game(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .browser_game import BrowserGameError, build_browser_game

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("browser-game creation cannot rewrite the live machine body")
        if "checks" in inputs and not isinstance(inputs["checks"], list):
            raise capability_error("browser-game checks must be a list")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("browser-game replace must be a boolean")
        try:
            result = build_browser_game(
                target,
                specification=inputs["specification"],
                checks=inputs.get("checks"),
                replace=inputs.get("replace", False),
            )
            result["grammar_inventory"] = grammar_inventory(target)
            return result
        except BrowserGameError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def creation_growth(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .creation_growth import CreationGrowthError, operate_creation_growth

        normalized = copy.deepcopy(inputs)
        operation = str(inputs.get("operation", "")).strip().casefold()
        if operation == "materialize-and-test":
            target = resolve_output_path(root, str(inputs.get("path", "")))
            if is_machine_body_path(root, target):
                raise capability_error(
                    "creation-growth candidates must stay detached from the live machine body; use creations/ or an external path"
                )
            normalized["path"] = str(target)
        try:
            return operate_creation_growth(root, normalized)
        except CreationGrowthError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def procedural_3d(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .creator_retention import CreatorRetentionError, SOURCE_SCHEMA, publish_retained_glb
        from .procedural_3d import Procedural3DError

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("procedural 3D generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("procedural 3D replace must be a boolean")
        source = {
            "schema": SOURCE_SCHEMA,
            "kind": "procedural-3d-specification",
            "source_authority": True,
            "realization_is_secondary": True,
            "specification": copy.deepcopy(inputs["specification"]),
            "automatic_canon_admission": False,
        }
        try:
            return publish_retained_glb(
                target,
                inputs["specification"],
                source,
                replace=inputs.get("replace", False),
            )
        except (Procedural3DError, CreatorRetentionError) as exc:
            raise capability_error(str(exc), getattr(exc, "details", {})) from exc

    def shape_recipe(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .procedural_3d import Procedural3DError
        from .shape_recipe import ShapeRecipeError, publish_shape_recipe

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("shape recipe generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("shape recipe replace must be a boolean")
        try:
            return publish_shape_recipe(target, inputs["recipe"], replace=inputs.get("replace", False))
        except (ShapeRecipeError, Procedural3DError) as exc:
            raise capability_error(str(exc), exc.details) from exc

    def form_pattern(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .creator_retention import CreatorRetentionError
        from .form_pattern import FormPatternError, publish_form_pattern
        from .procedural_3d import Procedural3DError

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("form-pattern generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("form-pattern replace must be a boolean")
        try:
            return publish_form_pattern(target, inputs["recipe"], replace=inputs.get("replace", False))
        except (FormPatternError, CreatorRetentionError, Procedural3DError) as exc:
            raise capability_error(str(exc), getattr(exc, "details", {})) from exc

    def character_recipe(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .character_recipe import CharacterRecipeError, publish_character_recipe
        from .creator_retention import CreatorRetentionError
        from .procedural_3d import Procedural3DError

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("character-recipe generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("character-recipe replace must be a boolean")
        try:
            return publish_character_recipe(target, inputs["recipe"], replace=inputs.get("replace", False))
        except (CharacterRecipeError, CreatorRetentionError, Procedural3DError) as exc:
            raise capability_error(str(exc), getattr(exc, "details", {})) from exc

    def creation_atlas(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .atlas_pipeline import operate_atlas
        try:
            return operate_atlas(root, inputs)
        except (ValueError, RuntimeError, OSError, KeyError) as exc:
            raise capability_error(str(exc)) from exc

    def construction_search(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .construction_search import publish_search
        target = resolve_output_path(root, str(inputs['path']))
        if is_machine_body_path(root, target):
            raise capability_error('construction search cannot rewrite the live machine body')
        try:
            return publish_search(target, inputs['search'])
        except (ValueError, RuntimeError) as exc:
            raise capability_error(str(exc)) from exc

    def character_controller(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .atomic import atomic_write_json
        from .character_controller import CharacterController
        target = resolve_output_path(root, str(inputs['path']))
        if is_machine_body_path(root, target):
            raise capability_error('character controller cannot rewrite the live machine body')
        if target.exists():
            raise capability_error('controller output already exists')
        try:
            controller = CharacterController(inputs['recipe'])
            evidence = controller.measure(inputs['clip'], inputs['times'], feet=inputs.get('feet'),
                            up_axis=inputs.get('up_axis',2),ground_height_m=inputs.get('ground_height_m',0))
            output = {'recipe':copy.deepcopy(inputs['recipe']), 'evidence':evidence,
                      'poses':[controller.sample(inputs['clip'],t) for t in inputs['times']],
                      'source_authority':True,'automatic_canon_admission':False}
            atomic_write_json(target,output)
            return {'operation':'character-controller','path':str(target),'evidence':evidence}
        except (ValueError, RuntimeError) as exc:
            raise capability_error(str(exc)) from exc

    def material_response(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .material_response import MaterialResponseHold, resolve_material_response

        family = inputs.get("family")
        if not isinstance(family, str) or not family.strip():
            raise capability_error("material response requires a non-empty family")
        if "variant" in inputs and inputs["variant"] is not None and not isinstance(inputs["variant"], str):
            raise capability_error("material response variant must be text when supplied")
        if "overrides" in inputs and inputs["overrides"] is not None and not isinstance(inputs["overrides"], dict):
            raise capability_error("material response overrides must be an object when supplied")
        try:
            return resolve_material_response(
                family.strip(),
                variant=inputs.get("variant"),
                overrides=copy.deepcopy(inputs.get("overrides")),
                base_color=copy.deepcopy(inputs.get("base_color")),
            )
        except MaterialResponseHold as exc:
            raise capability_error(str(exc)) from exc

    def precision_cutter(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .precision_cutter import PrecisionCutterError, publish_precision_cut

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("precision cutting cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("precision cutter replace must be a boolean")

        if "source_path" in inputs:
            from .mesh_precision_cutter import (
                MeshPrecisionCutterError,
                publish_source_mesh_cut,
            )

            source = resolve_output_path(root, str(inputs["source_path"]))
            if is_machine_body_path(root, source):
                raise capability_error(
                    "existing-mesh precision cutting cannot read the protected live machine body as source material"
                )
            if source == target:
                raise capability_error(
                    "existing-mesh precision cutting requires distinct source and output paths"
                )
            specification = inputs["specification"]
            schema = specification.get("schema") if isinstance(specification, dict) else None
            try:
                if schema == "axm.mesh-hole-fabrication-chain/v0.5":
                    from .mesh_hole_fabrication_chain import publish_hole_fabrication_chain

                    lineage = None
                    if "lineage_path" in inputs:
                        lineage = resolve_output_path(root, str(inputs["lineage_path"]))
                        if is_machine_body_path(root, lineage):
                            raise capability_error(
                                "hole-chain lineage must stay on an ordinary creation surface"
                            )
                    if "receipt_path" in inputs:
                        receipt = resolve_output_path(root, str(inputs["receipt_path"]))
                    else:
                        receipt = target.with_suffix(target.suffix + ".hole-fabrication.json")
                    if is_machine_body_path(root, receipt):
                        raise capability_error(
                            "hole-chain receipt cannot rewrite the live machine body"
                        )
                    return publish_hole_fabrication_chain(
                        source,
                        target,
                        specification,
                        lineage_path=lineage,
                        receipt_path=receipt,
                        expected_source_sha256=inputs.get("expected_source_sha256"),
                        expected_lineage_sha256=inputs.get("expected_lineage_sha256"),
                        replace=inputs.get("replace", False),
                    )
                if schema == "axm.mesh-fabrication-chain/v0.4":
                    from .mesh_fabrication_chain import publish_fabrication_chain

                    lineage = None
                    if "lineage_path" in inputs:
                        lineage = resolve_output_path(root, str(inputs["lineage_path"]))
                        if is_machine_body_path(root, lineage):
                            raise capability_error(
                                "fabrication-chain lineage must stay on an ordinary creation surface"
                            )
                    if "receipt_path" in inputs:
                        receipt = resolve_output_path(root, str(inputs["receipt_path"]))
                    else:
                        receipt = target.with_suffix(target.suffix + ".fabrication.json")
                    if is_machine_body_path(root, receipt):
                        raise capability_error(
                            "fabrication-chain receipt cannot rewrite the live machine body"
                        )
                    return publish_fabrication_chain(
                        source,
                        target,
                        specification,
                        lineage_path=lineage,
                        receipt_path=receipt,
                        expected_source_sha256=inputs.get("expected_source_sha256"),
                        expected_lineage_sha256=inputs.get("expected_lineage_sha256"),
                        replace=inputs.get("replace", False),
                    )
                if schema == "axm.mesh-precision-cutter/v0.3":
                    from .oriented_mesh_precision_cutter import publish_oriented_source_mesh_cut

                    return publish_oriented_source_mesh_cut(
                        source,
                        target,
                        specification,
                        expected_source_sha256=inputs.get("expected_source_sha256"),
                        replace=inputs.get("replace", False),
                    )
                return publish_source_mesh_cut(
                    source,
                    target,
                    specification,
                    expected_source_sha256=inputs.get("expected_source_sha256"),
                    replace=inputs.get("replace", False),
                )
            except MeshPrecisionCutterError as exc:
                raise capability_error(str(exc), exc.details) from exc

        try:
            return publish_precision_cut(
                target,
                inputs["specification"],
                replace=inputs.get("replace", False),
            )
        except PrecisionCutterError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def creative_flow(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .creative_flow import CreativeFlowError, run_creative_flow

        try:
            return run_creative_flow(root, inputs)
        except CreativeFlowError as exc:
            raise capability_error(str(exc), exc.details) from exc

    def native_visual_runtime(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .native_visual_engine import catalog_native_visual, compile_scene, demo_scene, write_visual_bundle

        operation = str(inputs.get("operation", "inspect")).strip().casefold()
        if operation == "inspect":
            return catalog_native_visual()
        if operation == "compile":
            if "scene" not in inputs:
                raise capability_error("native visual compile requires scene")
            return compile_scene(inputs["scene"])
        if operation not in {"bundle", "demo"}:
            raise capability_error(
                f"unsupported native visual operation: {operation}",
                {"supported_operations": ["inspect", "compile", "bundle", "demo"]},
            )
        target = resolve_output_path(root, str(inputs.get("path", "")))
        if is_machine_body_path(root, target):
            raise capability_error("native visual bundles cannot rewrite the live machine body")
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool):
            raise capability_error("native visual replace must be a boolean")
        if operation == "bundle" and "scene" not in inputs:
            raise capability_error("native visual bundle requires scene")
        scene = demo_scene() if operation == "demo" else inputs["scene"]
        try:
            return write_visual_bundle(target, scene, replace=replace)
        except (TypeError, ValueError, FileExistsError) as exc:
            raise capability_error(str(exc)) from exc

    def external_visual_tools(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        from .external_visual_tools import ExternalVisualToolError, operate_external_visual_tool

        normalized = dict(inputs)
        operation = str(inputs.get("operation", "catalog")).strip().casefold()
        if operation == "execute":
            if "cwd" not in inputs:
                raise capability_error("external visual tool execution requires an explicit cwd")
            cwd = resolve_output_path(root, str(inputs["cwd"]))
            if is_machine_body_path(root, cwd):
                raise capability_error(
                    "external visual tools cannot execute with the live machine body as their working directory"
                )
            normalized["cwd"] = str(cwd)
        try:
            return operate_external_visual_tool(root, normalized)
        except ExternalVisualToolError as exc:
            raise capability_error(str(exc), exc.details) from exc

    return {
        "builtin:local_creation_provider": local_creation_provider,
        "builtin:host_evidence": host_evidence,
        "builtin:write_mixed_project": write_mixed_project,
        "builtin:portable_creation_bundle": portable_creation_bundle,
        "builtin:deterministic_state_machine": deterministic_state_machine,
        "builtin:procedural_media": procedural_media,
        "builtin:browser_game": browser_game,
        "builtin:creation_growth": creation_growth,
        "builtin:procedural_3d": procedural_3d,
        "builtin:shape_recipe": shape_recipe,
        "builtin:form_pattern": form_pattern,
        "builtin:character_recipe": character_recipe,
        "builtin:construction_search": construction_search,
        "builtin:creation_atlas": creation_atlas,
        "builtin:character_controller": character_controller,
        "builtin:material_response": material_response,
        "builtin:precision_cutter": precision_cutter,
        "builtin:creative_flow": creative_flow,
        "builtin:native_visual_runtime": native_visual_runtime,
        "builtin:external_visual_tools": external_visual_tools,
    }

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
        from .procedural_3d import Procedural3DError, publish_glb

        target = resolve_output_path(root, str(inputs["path"]))
        if is_machine_body_path(root, target):
            raise capability_error("procedural 3D generation cannot rewrite the live machine body")
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise capability_error("procedural 3D replace must be a boolean")
        try:
            return publish_glb(target, inputs["specification"], replace=inputs.get("replace", False))
        except Procedural3DError as exc:
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
    }

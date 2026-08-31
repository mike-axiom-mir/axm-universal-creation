from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from .atomic import atomic_write_json, atomic_write_text
from .grammar import grammar_inventory
from .organ_library import ExecutableOrganError, ExecutableOrganLibrary, resolve_organ_assembly
from .organ_discovery import OrganDiscoveryError, discover_interface_assembly
from .organ_gap import OrganGapError, explore_missing_organ_closure
from .organ_project import assemble_organ_project
from .project import ProjectError, build_project, validate_project
from .registry import Registry
from .repair import patch_project
from .self_workspace import SelfWorkspaceError, operate_self_workspace
from .template import instantiate_project_template


class CapabilityError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _resolve_output_path(root: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def _is_machine_body_path(root: Path, target: Path) -> bool:
    """Return True when ordinary creation is trying to write machine internals.

    Inside the repository only `creations/` and the short-lived `.axm-build/`
    candidate-test area are ordinary write surfaces. Everything else is machine
    body and must use the explicit self-modification path.
    """
    root = root.resolve()
    try:
        rel = target.resolve().relative_to(root)
    except ValueError:
        try:
            root.relative_to(target.resolve())
        except ValueError:
            return False
        return True
    if not rel.parts:
        return True
    return rel.parts[0] not in {"creations", ".axm-build"}


def builtin_write_text(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal creation cannot rewrite the machine body; use candidate adoption/self-modification so root fit remains inspectable")
    text = str(inputs["content"])
    atomic_write_text(target, text)
    return {"path": str(target), "bytes": len(text.encode("utf-8")), "kind": "text"}


def builtin_write_json(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal creation cannot rewrite the machine body; use candidate adoption/self-modification so root fit remains inspectable")
    atomic_write_json(target, inputs["value"])
    return {"path": str(target), "bytes": target.stat().st_size, "kind": "json"}


def builtin_inspect_registry(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    registry = Registry(root)
    return {
        "summary": registry.summary(),
        "records": registry.search(
            query=str(inputs.get("query", "")),
            level=inputs.get("level"),
            limit=int(inputs.get("limit", 20)),
        ),
    }


def builtin_write_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal project creation cannot rewrite the machine body; self-modification remains a separate root-fit path")
    try:
        result = build_project(
            target=target,
            files=inputs["files"],
            project_type=str(inputs.get("project_type", "generic")),
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            replace=bool(inputs.get("replace", False)),
            publish_mode=str(inputs.get("publish_mode", "grounded-draft")),
        )
        result["grammar_inventory"] = grammar_inventory(target)
        return result
    except ProjectError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_instantiate_project_template(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal template creation cannot rewrite the machine body; self-modification remains a separate future growth path")
    try:
        result = instantiate_project_template(
            target=target,
            template=inputs["template"],
            variables=inputs["variables"],
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            replace=bool(inputs.get("replace", False)),
            publish_mode=str(inputs.get("publish_mode", "grounded-draft")),
        )
        result["grammar_inventory"] = grammar_inventory(target)
        return result
    except ProjectError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_self_workspace(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        return operate_self_workspace(root, inputs)
    except SelfWorkspaceError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_assemble_organ_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal organ assembly cannot rewrite the live machine body; use a self-workspace for whole-body experiments")
    try:
        resolved_assembly, resolution = resolve_organ_assembly(root, inputs["assembly"])
        result = assemble_organ_project(
            target=target,
            assembly=resolved_assembly,
            variables=inputs["variables"],
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            replace=bool(inputs.get("replace", False)),
            publish_mode=str(inputs.get("publish_mode", "grounded-draft")),
        )
        result["executable_organ_resolution"] = resolution
        result["grammar_inventory"] = grammar_inventory(target)
        return result
    except (ProjectError, ExecutableOrganError) as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_compose_organ_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError(
            "interface-driven organ composition cannot rewrite the live machine body; use a self-workspace for whole-body experiments"
        )
    try:
        discovery = discover_interface_assembly(root, inputs["organ_goal"])
        if discovery["status"] != "READY_EXACT_INTERFACE_ASSEMBLY":
            raise CapabilityError(
                "interface-driven organ discovery is on HOLD",
                {"organ_discovery": discovery},
            )
        resolved_assembly, resolution = resolve_organ_assembly(root, discovery["assembly"])
        result = assemble_organ_project(
            target=target,
            assembly=resolved_assembly,
            variables=discovery["variables"],
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            replace=bool(inputs.get("replace", False)),
            publish_mode=str(inputs.get("publish_mode", "grounded-draft")),
        )
        result["organ_discovery"] = discovery
        result["executable_organ_resolution"] = resolution
        result["grammar_inventory"] = grammar_inventory(target)
        return result
    except CapabilityError:
        raise
    except (ProjectError, ExecutableOrganError, OrganDiscoveryError) as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_inspect_executable_organs(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    try:
        library = ExecutableOrganLibrary(root)
        if "organ_goal" in inputs:
            return {
                "truth_status": "OBSERVED_INTERFACE_DRIVEN_ORGAN_DISCOVERY",
                "summary": library.summary(),
                "assembly_plan": discover_interface_assembly(root, inputs["organ_goal"]),
            }
        ref = inputs.get("ref")
        if ref is not None:
            return {
                "truth_status": "EXACT_LOCAL_EXECUTABLE_ORGAN_PACKAGE",
                "summary": library.summary(),
                "package": library.inspect(ref),
            }
        return {
            "truth_status": "EXACT_LOCAL_EXECUTABLE_ORGAN_PACKAGES",
            "summary": library.summary(),
            "packages": library.list(
                project_type=str(inputs["project_type"]) if "project_type" in inputs else None,
                provides=str(inputs["provides"]) if "provides" in inputs else None,
            ),
        }
    except (ExecutableOrganError, OrganDiscoveryError) as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_explore_organ_gap(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError(
            "missing-organ closure candidates must stay detached from the live machine body; use creations/ or an external path"
        )
    if "checks" in inputs and not isinstance(inputs["checks"], list):
        raise CapabilityError("missing-organ closure checks must be a list")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("missing-organ closure replace must be a boolean")
    try:
        return explore_missing_organ_closure(
            root=root,
            target=target,
            raw_goal=inputs["organ_goal"],
            raw_proposal=inputs["proposal"],
            checks=inputs.get("checks"),
            replace=inputs.get("replace", False),
        )
    except (OrganGapError, OrganDiscoveryError, ExecutableOrganError) as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_organ_materialization(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .organ_materialization import OrganMaterializationError, operate_organ_materialization
    from .spawn import SpawnError

    operation = str(inputs.get("operation", "")).strip().casefold()
    normalized_inputs = copy.deepcopy(inputs)
    if operation == "materialize-and-test":
        target = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError(
                "organ materialization candidates must stay outside the live machine body; use creations/ or an external path"
            )
        normalized_inputs["path"] = str(target)
    try:
        return operate_organ_materialization(root, normalized_inputs)
    except (OrganMaterializationError, ProjectError, SpawnError) as exc:
        raise CapabilityError(str(exc), getattr(exc, "details", {})) from exc


def builtin_spawn_creation_unit(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .spawn import SpawnError, operate_spawn_unit

    target = _resolve_output_path(root, str(inputs.get("path", "")))
    if _is_machine_body_path(root, target):
        raise CapabilityError(
            "creation-unit candidates must stay outside the live machine body; use creations/ or an external path"
        )
    try:
        return operate_spawn_unit(root, inputs)
    except (ProjectError, SpawnError) as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_evolve_machine(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .evolution import EvolutionError, operate_evolution

    try:
        return operate_evolution(root, inputs)
    except EvolutionError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_simulate_creation(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .simulation import SimulationError, operate_simulation

    try:
        return operate_simulation(root, inputs)
    except SimulationError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_paintgun_specialist(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .paintgun import PaintgunError, operate_paintgun

    target = _resolve_output_path(root, str(inputs.get("path", "")))
    if _is_machine_body_path(root, target):
        raise CapabilityError(
            "paintgun materialization is an ordinary creation and cannot rewrite the live machine body"
        )
    try:
        return operate_paintgun(root, inputs)
    except PaintgunError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_synthesize_creation_gap(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .gap_synthesis import GapSynthesisError, operate_gap_synthesis
    from .spawn import SpawnError

    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "materialize-and-test":
        target = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError(
                "gap-derived candidates must stay outside the live machine body; use creations/ or an external path"
            )
    try:
        return operate_gap_synthesis(root, inputs)
    except (GapSynthesisError, ProjectError, SpawnError) as exc:
        raise CapabilityError(str(exc), getattr(exc, "details", {})) from exc


def builtin_verify_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("verify-project is for created project bodies; use inspect for the machine itself")
    report = validate_project(
        target,
        project_type=str(inputs.get("project_type", "generic")),
        checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
        expected_files=inputs.get("expected_files") if isinstance(inputs.get("expected_files"), dict) else None,
        expected_file_digests=inputs.get("expected_file_digests") if isinstance(inputs.get("expected_file_digests"), dict) else None,
    )
    report["grammar_inventory"] = grammar_inventory(target) if target.is_dir() else {
        "truth_status": "OBSERVED_EXTENSION_GRAMMAR_INVENTORY",
        "counts": {},
        "files": [],
    }
    return report


def builtin_patch_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("normal project repair cannot rewrite the machine body; self-modification remains a separate root-fit path")
    try:
        return patch_project(
            target=target,
            operations=inputs["operations"],
            project_type=str(inputs.get("project_type", "generic")),
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            expected_files=inputs.get("expected_files") if isinstance(inputs.get("expected_files"), dict) else None,
        )
    except ProjectError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_local_creation_provider(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .local_provider import LocalProviderError, operate_local_provider

    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    if operation == "create":
        target = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError(
                "local provider creation cannot rewrite the live machine body; provider output must enter an ordinary creation surface"
            )
    try:
        return operate_local_provider(root, inputs)
    except LocalProviderError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_host_evidence(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .host_evidence import HostEvidenceError, operate_host_evidence

    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    if operation == "bind":
        target = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError("creation host evidence binds to created project bodies, not the live machine body")
    try:
        return operate_host_evidence(root, inputs)
    except HostEvidenceError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_write_mixed_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .mixed_project import build_mixed_project

    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("mixed-media project creation cannot rewrite the live machine body")
    if "checks" in inputs and not isinstance(inputs["checks"], list):
        raise CapabilityError("mixed-project checks must be a list")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("mixed-project replace must be a boolean")
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
    except ProjectError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_portable_creation_bundle(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .portable_bundle import PortableBundleError, operate_portable_bundle

    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    normalized = dict(inputs)
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("portable bundle replace must be a boolean")
    if "path" in inputs:
        normalized["path"] = str(_resolve_output_path(root, str(inputs["path"])))
    if operation == "pack":
        source = _resolve_output_path(root, str(inputs.get("source", "")))
        output = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, source) or _is_machine_body_path(root, output):
            raise CapabilityError("portable bundle packing is limited to ordinary creation surfaces")
        normalized["source"] = str(source)
    if operation == "unpack":
        target = _resolve_output_path(root, str(inputs.get("target", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError("portable bundle unpacking cannot rewrite the live machine body")
        normalized["target"] = str(target)
    try:
        return operate_portable_bundle(normalized)
    except PortableBundleError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_deterministic_state_machine(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    del root
    from .state_machine import StateMachineError, operate_state_machine

    if "stop_on_hold" in inputs and not isinstance(inputs["stop_on_hold"], bool):
        raise CapabilityError("state-machine stop_on_hold must be a boolean")
    try:
        return operate_state_machine(inputs)
    except StateMachineError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_procedural_media(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .procedural_media import ProceduralMediaError, publish_media_asset

    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("procedural media generation cannot rewrite the live machine body")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("procedural media replace must be a boolean")
    try:
        return publish_media_asset(
            target,
            operation=inputs["operation"],
            specification=inputs["specification"],
            replace=inputs.get("replace", False),
        )
    except ProceduralMediaError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_browser_game(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .browser_game import BrowserGameError, build_browser_game

    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("browser-game creation cannot rewrite the live machine body")
    if "checks" in inputs and not isinstance(inputs["checks"], list):
        raise CapabilityError("browser-game checks must be a list")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("browser-game replace must be a boolean")
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
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_creation_growth(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .creation_growth import CreationGrowthError, operate_creation_growth

    normalized = copy.deepcopy(inputs)
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "materialize-and-test":
        target = _resolve_output_path(root, str(inputs.get("path", "")))
        if _is_machine_body_path(root, target):
            raise CapabilityError(
                "creation-growth candidates must stay detached from the live machine body; use creations/ or an external path"
            )
        normalized["path"] = str(target)
    try:
        return operate_creation_growth(root, normalized)
    except CreationGrowthError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_procedural_3d(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .procedural_3d import Procedural3DError, publish_glb

    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("procedural 3D generation cannot rewrite the live machine body")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CapabilityError("procedural 3D replace must be a boolean")
    try:
        return publish_glb(target, inputs["specification"], replace=inputs.get("replace", False))
    except Procedural3DError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


BUILTINS: dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]] = {
    "builtin:write_text": builtin_write_text,
    "builtin:write_json": builtin_write_json,
    "builtin:inspect_registry": builtin_inspect_registry,
    "builtin:write_project": builtin_write_project,
    "builtin:instantiate_project_template": builtin_instantiate_project_template,
    "builtin:self_workspace": builtin_self_workspace,
    "builtin:assemble_organ_project": builtin_assemble_organ_project,
    "builtin:compose_organ_project": builtin_compose_organ_project,
    "builtin:inspect_executable_organs": builtin_inspect_executable_organs,
    "builtin:explore_organ_gap": builtin_explore_organ_gap,
    "builtin:organ_materialization": builtin_organ_materialization,
    "builtin:spawn_creation_unit": builtin_spawn_creation_unit,
    "builtin:evolve_machine": builtin_evolve_machine,
    "builtin:simulate_creation": builtin_simulate_creation,
    "builtin:paintgun_specialist": builtin_paintgun_specialist,
    "builtin:gap_synthesis": builtin_synthesize_creation_gap,
    "builtin:verify_project": builtin_verify_project,
    "builtin:patch_project": builtin_patch_project,
    "builtin:local_creation_provider": builtin_local_creation_provider,
    "builtin:host_evidence": builtin_host_evidence,
    "builtin:write_mixed_project": builtin_write_mixed_project,
    "builtin:portable_creation_bundle": builtin_portable_creation_bundle,
    "builtin:deterministic_state_machine": builtin_deterministic_state_machine,
    "builtin:procedural_media": builtin_procedural_media,
    "builtin:browser_game": builtin_browser_game,
    "builtin:creation_growth": builtin_creation_growth,
    "builtin:procedural_3d": builtin_procedural_3d,
}


_MISSING = object()
_BINDING_TRANSFORMS = {"file-digest-map"}


def _lookup_binding(source: str, request_inputs: dict[str, Any], step_results: dict[str, Any]) -> Any:
    text = str(source).strip()
    if text == "request":
        return request_inputs
    if text.startswith("request."):
        value: Any = request_inputs
        parts = text.split(".")[1:]
    elif text == "steps":
        return step_results
    elif text.startswith("steps."):
        value = step_results
        parts = text.split(".")[1:]
    else:
        return _MISSING
    for part in parts:
        if not isinstance(value, dict) or part not in value:
            return _MISSING
        value = value[part]
    return value


def _transform_binding(name: Any, value: Any) -> Any:
    transform = str(name).strip().casefold()
    if transform not in _BINDING_TRANSFORMS:
        raise CapabilityError(
            f"unsupported composite binding transform: {transform or '<empty>'}",
            {"supported_transforms": sorted(_BINDING_TRANSFORMS)},
        )
    if transform == "file-digest-map":
        if not isinstance(value, list) or not value:
            raise CapabilityError("file-digest-map requires a non-empty file receipt list")
        result: dict[str, str] = {}
        for index, row in enumerate(value):
            if not isinstance(row, dict):
                raise CapabilityError(
                    "file-digest-map receipt rows must be objects",
                    {"index": index},
                )
            path = row.get("path")
            digest = row.get("sha256")
            if not isinstance(path, str) or not path.strip():
                raise CapabilityError(
                    "file-digest-map receipt path must be non-empty text",
                    {"index": index},
                )
            normalized_path = path.strip().replace("\\", "/")
            if normalized_path in result:
                raise CapabilityError(
                    "file-digest-map receipt paths must be unique",
                    {"index": index, "duplicate_path": normalized_path},
                )
            if (
                not isinstance(digest, str)
                or len(digest) != 64
                or any(character not in "0123456789abcdef" for character in digest)
            ):
                raise CapabilityError(
                    "file-digest-map receipt SHA-256 must be 64 lowercase hexadecimal characters",
                    {"index": index, "path": normalized_path},
                )
            result[normalized_path] = digest
        return result
    raise AssertionError("unreachable binding transform")


def _resolve_binding(spec: Any, request_inputs: dict[str, Any], step_results: dict[str, Any]) -> Any:
    if isinstance(spec, dict) and "from" in spec:
        unexpected = sorted(set(spec) - {"from", "default", "transform"})
        if unexpected:
            raise CapabilityError(
                "composite binding reference has unsupported fields",
                {"unexpected_fields": unexpected},
            )
        if not isinstance(spec["from"], str) or not spec["from"].strip():
            raise CapabilityError("composite binding from must be non-empty text")
        value = _lookup_binding(str(spec["from"]), request_inputs, step_results)
        if value is _MISSING:
            if "default" in spec:
                value = copy.deepcopy(spec["default"])
            else:
                raise CapabilityError(f"composite binding could not resolve: {spec['from']}")
        else:
            value = copy.deepcopy(value)
        if "transform" in spec:
            return _transform_binding(spec["transform"], value)
        return value
    if isinstance(spec, dict):
        return {key: _resolve_binding(value, request_inputs, step_results) for key, value in spec.items()}
    if isinstance(spec, list):
        return [_resolve_binding(value, request_inputs, step_results) for value in spec]
    return copy.deepcopy(spec)


class CapabilityStore:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.registry = Registry(root)

    def live(self) -> list[dict[str, Any]]:
        return self.registry.capability_manifests()

    def by_id(self, capability_id: str) -> dict[str, Any] | None:
        return next((c for c in self.live() if c.get("id") == capability_id), None)

    def route(self, creation_kind: str) -> dict[str, Any] | None:
        return next((c for c in self.live() if creation_kind in c.get("handles", [])), None)

    @staticmethod
    def required_inputs(manifest: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
        contract = manifest.get("input_contract", {})
        required = list(contract.get("required", []))
        operation = inputs.get("operation")
        by_operation = contract.get("required_by_operation", {})
        if isinstance(operation, str) and isinstance(by_operation, dict):
            conditional = by_operation.get(operation.strip().casefold(), [])
            if isinstance(conditional, list):
                required.extend(conditional)
        return sorted({str(key) for key in required})

    @staticmethod
    def missing_required_inputs(manifest: dict[str, Any], inputs: dict[str, Any]) -> list[str]:
        required = CapabilityStore.required_inputs(manifest, inputs)
        return sorted(key for key in required if key not in inputs)

    def invoke(self, manifest: dict[str, Any], inputs: dict[str, Any], _seen: set[str] | None = None) -> dict[str, Any]:
        missing = self.missing_required_inputs(manifest, inputs)
        if missing:
            raise CapabilityError(f"missing required inputs: {', '.join(missing)}")
        impl = manifest.get("implementation", {})
        kind = impl.get("kind")
        if kind == "DETERMINISTIC_SOURCE":
            entry = impl.get("entrypoint")
            fn = BUILTINS.get(entry)
            if fn is None:
                raise CapabilityError(f"unknown builtin entrypoint: {entry}")
            return fn(self.root, inputs)
        if kind in {"LOCAL_PROVIDER_BOUNDARY", "EXTERNAL_EVIDENCE_BOUNDARY"}:
            entry = impl.get("entrypoint")
            fn = BUILTINS.get(entry)
            if fn is None:
                raise CapabilityError(f"unknown boundary entrypoint: {entry}")
            return fn(self.root, inputs)
        if kind == "DETERMINISTIC_ALIAS":
            delegate_id = impl.get("delegate")
            seen = set(_seen or set())
            current_id = str(manifest.get("id"))
            if current_id in seen:
                raise CapabilityError("capability alias cycle detected")
            seen.add(current_id)
            delegate = self.by_id(str(delegate_id))
            if delegate is None:
                raise CapabilityError(f"delegate capability is not live: {delegate_id}")
            return self.invoke(delegate, inputs, seen)
        if kind == "DETERMINISTIC_COMPOSITE":
            seen = set(_seen or set())
            current_id = str(manifest.get("id"))
            if current_id in seen:
                raise CapabilityError("capability composite cycle detected")
            seen.add(current_id)
            steps = impl.get("steps")
            if not isinstance(steps, list) or not steps:
                raise CapabilityError("composite capability requires a non-empty steps list")
            step_results: dict[str, Any] = {}
            for step in steps:
                if not isinstance(step, dict):
                    raise CapabilityError("composite step must be an object")
                step_id = str(step.get("id", "")).strip()
                capability_id = str(step.get("capability", "")).strip()
                if not step_id or not capability_id:
                    raise CapabilityError("composite step requires id and capability")
                if step_id in step_results:
                    raise CapabilityError(f"duplicate composite step id: {step_id}")
                delegate = self.by_id(capability_id)
                if delegate is None:
                    raise CapabilityError(f"composite delegate capability is not live: {capability_id}")
                raw_inputs = step.get("inputs", {})
                if not isinstance(raw_inputs, dict):
                    raise CapabilityError(f"composite step inputs must be an object: {step_id}")
                resolved_inputs = _resolve_binding(raw_inputs, inputs, step_results)
                step_results[step_id] = self.invoke(delegate, resolved_inputs, seen)
            output_spec = impl.get("outputs")
            if output_spec is None:
                return {"steps": step_results}
            resolved = _resolve_binding(output_spec, inputs, step_results)
            if not isinstance(resolved, dict):
                return {"value": resolved, "steps": step_results}
            return resolved
        raise CapabilityError(f"unsupported implementation kind: {kind}")

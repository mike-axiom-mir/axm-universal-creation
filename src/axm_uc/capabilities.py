from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any, Callable

from .atomic import atomic_write_json, atomic_write_text
from .grammar import grammar_inventory
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
        return False
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


def builtin_verify_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("verify-project is for created project bodies; use inspect for the machine itself")
    report = validate_project(
        target,
        project_type=str(inputs.get("project_type", "generic")),
        checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
        expected_files=inputs.get("expected_files") if isinstance(inputs.get("expected_files"), dict) else None,
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


BUILTINS: dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]] = {
    "builtin:write_text": builtin_write_text,
    "builtin:write_json": builtin_write_json,
    "builtin:inspect_registry": builtin_inspect_registry,
    "builtin:write_project": builtin_write_project,
    "builtin:instantiate_project_template": builtin_instantiate_project_template,
    "builtin:self_workspace": builtin_self_workspace,
    "builtin:verify_project": builtin_verify_project,
    "builtin:patch_project": builtin_patch_project,
}


_MISSING = object()


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


def _resolve_binding(spec: Any, request_inputs: dict[str, Any], step_results: dict[str, Any]) -> Any:
    if isinstance(spec, dict) and "from" in spec:
        value = _lookup_binding(str(spec["from"]), request_inputs, step_results)
        if value is _MISSING:
            if "default" in spec:
                return copy.deepcopy(spec["default"])
            raise CapabilityError(f"composite binding could not resolve: {spec['from']}")
        return copy.deepcopy(value)
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

    def invoke(self, manifest: dict[str, Any], inputs: dict[str, Any], _seen: set[str] | None = None) -> dict[str, Any]:
        required = manifest.get("input_contract", {}).get("required", [])
        missing = [key for key in required if key not in inputs]
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

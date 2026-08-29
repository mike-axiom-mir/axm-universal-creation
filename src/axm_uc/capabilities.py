from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from .atomic import atomic_write_json, atomic_write_text
from .project import ProjectError, build_project, validate_project
from .registry import Registry


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
    root = root.resolve()
    try:
        rel = target.resolve().relative_to(root)
    except ValueError:
        return False
    if not rel.parts:
        return True
    protected = {
        "src", "state", "reference", "tools", "tests",
        "atoms", "components", "organs", "interfaces",
    }
    if rel.parts[0] in protected:
        return True
    if rel.parts[:2] in (("capabilities", "live"), ("capabilities", "candidates")):
        return True
    if rel.as_posix() in {"machine.contract.json", "pyproject.toml"}:
        return True
    return False


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
        return build_project(
            target=target,
            files=inputs["files"],
            project_type=str(inputs.get("project_type", "generic")),
            checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
            replace=bool(inputs.get("replace", False)),
        )
    except ProjectError as exc:
        raise CapabilityError(str(exc), exc.details) from exc


def builtin_verify_project(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = _resolve_output_path(root, str(inputs["path"]))
    if _is_machine_body_path(root, target):
        raise CapabilityError("verify-project is for created project bodies; use inspect for the machine itself")
    return validate_project(
        target,
        project_type=str(inputs.get("project_type", "generic")),
        checks=inputs.get("checks") if isinstance(inputs.get("checks"), list) else None,
    )


BUILTINS: dict[str, Callable[[Path, dict[str, Any]], dict[str, Any]]] = {
    "builtin:write_text": builtin_write_text,
    "builtin:write_json": builtin_write_json,
    "builtin:inspect_registry": builtin_inspect_registry,
    "builtin:write_project": builtin_write_project,
    "builtin:verify_project": builtin_verify_project,
}


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
        raise CapabilityError(f"unsupported implementation kind: {kind}")

from __future__ import annotations

import os
import shutil
import uuid
from pathlib import Path
from typing import Any

from .grammar import grammar_inventory
from .project import (
    ProjectError,
    _begin_publish,
    _file_manifest,
    _resolve_inside,
    _rollback_publish,
    _safe_relative_path,
    validate_project,
)


OPERATIONS = {"add", "update", "delete", "rename"}


def _normalize_operations(operations: Any) -> list[dict[str, Any]]:
    if not isinstance(operations, list) or not operations:
        raise ProjectError("operations must be a non-empty list")

    normalized: list[dict[str, Any]] = []
    for index, raw in enumerate(operations, start=1):
        if not isinstance(raw, dict):
            raise ProjectError(f"repair operation {index} must be an object")
        kind = str(raw.get("op", "")).strip().casefold()
        if kind not in OPERATIONS:
            raise ProjectError(f"repair operation {index} has unsupported op: {kind or '<missing>'}")

        if kind in {"add", "update", "delete"}:
            rel = _safe_relative_path(str(raw.get("path", ""))).as_posix()
            row: dict[str, Any] = {"op": kind, "path": rel}
            if kind in {"add", "update"}:
                content = raw.get("content")
                if not isinstance(content, str):
                    raise ProjectError(f"repair operation {index} content must be text")
                row["content"] = content
            normalized.append(row)
            continue

        source = _safe_relative_path(str(raw.get("from", ""))).as_posix()
        target = _safe_relative_path(str(raw.get("to", ""))).as_posix()
        if source == target:
            raise ProjectError(f"repair operation {index} rename source and target are identical")
        normalized.append({"op": "rename", "from": source, "to": target})

    return normalized


def _apply_operations(stage: Path, operations: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, str]]:
    observed: list[dict[str, Any]] = []
    expected_changed_text: dict[str, str] = {}

    for operation in operations:
        kind = operation["op"]
        if kind == "add":
            path = _resolve_inside(stage, operation["path"])
            if path.exists():
                raise ProjectError(f"add target already exists: {operation['path']}")
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(operation["content"], encoding="utf-8")
            expected_changed_text[operation["path"]] = operation["content"]
            observed.append({"op": "add", "path": operation["path"], "bytes": path.stat().st_size})
            continue

        if kind == "update":
            path = _resolve_inside(stage, operation["path"])
            if not path.is_file():
                raise ProjectError(f"update target is not an existing file: {operation['path']}")
            before_bytes = path.stat().st_size
            path.write_text(operation["content"], encoding="utf-8")
            expected_changed_text[operation["path"]] = operation["content"]
            observed.append({
                "op": "update",
                "path": operation["path"],
                "before_bytes": before_bytes,
                "after_bytes": path.stat().st_size,
            })
            continue

        if kind == "delete":
            path = _resolve_inside(stage, operation["path"])
            if not path.is_file():
                raise ProjectError(f"delete target is not an existing file: {operation['path']}")
            before_bytes = path.stat().st_size
            path.unlink()
            observed.append({"op": "delete", "path": operation["path"], "before_bytes": before_bytes})
            continue

        source = _resolve_inside(stage, operation["from"])
        target = _resolve_inside(stage, operation["to"])
        if not source.is_file():
            raise ProjectError(f"rename source is not an existing file: {operation['from']}")
        if target.exists():
            raise ProjectError(f"rename target already exists: {operation['to']}")
        target.parent.mkdir(parents=True, exist_ok=True)
        os.replace(source, target)
        observed.append({
            "op": "rename",
            "from": operation["from"],
            "to": operation["to"],
            "bytes": target.stat().st_size,
        })

    return observed, expected_changed_text


def patch_project(
    target: Path,
    operations: Any,
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    expected_files: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Patch an existing project transactionally and publish only verified state."""
    target = Path(target).resolve()
    if not target.is_dir():
        raise ProjectError(f"repair target project does not exist: {target}")

    normalized = _normalize_operations(operations)
    before_files = _file_manifest(target)
    stage = target.with_name(f".{target.name}.axm-repair-{uuid.uuid4().hex}")
    if stage.exists():
        raise ProjectError(f"unexpected repair staging collision: {stage}")
    shutil.copytree(target, stage)

    backup: Path | None = None
    published = False
    try:
        applied, changed_text = _apply_operations(stage, normalized)

        combined_expected: dict[str, Any] | None
        if expected_files is None:
            combined_expected = changed_text if changed_text else None
        else:
            if not isinstance(expected_files, dict):
                raise ProjectError("expected_files must be an object mapping project-relative paths to exact text")
            combined_expected = dict(expected_files)
            for path, text in changed_text.items():
                if path in combined_expected and combined_expected[path] != text:
                    raise ProjectError(f"expected_files contradicts repair content for: {path}")
                combined_expected[path] = text

        pre_validation = validate_project(
            stage,
            project_type=project_type,
            checks=checks,
            expected_files=combined_expected,
        )
        if not pre_validation["passed"]:
            raise ProjectError(
                "project repair validation failed before publish; original body unchanged",
                {"phase": "pre-publish", "validation": pre_validation, "original_unchanged": True},
            )

        backup = _begin_publish(stage, target, replace=True)
        published = True
        post_validation = validate_project(
            target,
            project_type=project_type,
            checks=checks,
            expected_files=combined_expected,
        )
        if not post_validation["passed"]:
            _rollback_publish(target, backup)
            published = False
            raise ProjectError(
                "project repair validation failed after publish; original body restored",
                {"phase": "post-publish", "validation": post_validation, "rolled_back": True},
            )

        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return {
            "path": str(target),
            "project_type": str(project_type or "generic"),
            "published": True,
            "truth_status": "OBSERVED_TRANSACTIONAL_PROJECT_REPAIR",
            "intent": {"operations": normalized},
            "observed": {
                "applied_operations": applied,
                "before_files": before_files,
                "after_files": _file_manifest(target),
            },
            "expected_files": combined_expected or {},
            "validation": post_validation,
            "grammar_inventory": grammar_inventory(target),
            "limitations": [
                "operation success and deterministic validation are observed; semantic intent beyond supplied checks is not inferred",
                "identified grammars without an explicit validator are not claimed syntax-valid",
            ],
        }
    except Exception:
        if published and target.exists():
            _rollback_publish(target, backup)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

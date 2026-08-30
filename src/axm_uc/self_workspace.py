from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from .atomic import atomic_write_json


EXCLUDED_TOP_LEVEL = {
    ".axm-build",
    ".git",
    ".pytest_cache",
    "creations",
    "snapshots",
}
EXCLUDED_ANYWHERE = {"__pycache__", ".pytest_cache"}
MERGE_CHECKS = {
    "source-diff",
    "build",
    "machine-inspect",
    "executable-anatomy",
    "plan-probes",
    "creation-trials",
}


class SelfWorkspaceError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _bounded_timeout(value: Any) -> int:
    try:
        timeout_seconds = int(value)
    except (TypeError, ValueError) as exc:
        raise SelfWorkspaceError("timeout_seconds must be an integer from 1 through 3600") from exc
    if timeout_seconds < 1 or timeout_seconds > 3600:
        raise SelfWorkspaceError("timeout_seconds must be between 1 and 3600")
    return timeout_seconds


def _captured_text(value: str | bytes | None) -> str:
    if value is None:
        return ""
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    return value


def _relative_is_included(relative: PurePosixPath) -> bool:
    if relative.parts and relative.parts[0] in EXCLUDED_TOP_LEVEL:
        return False
    if any(part in EXCLUDED_ANYWHERE for part in relative.parts):
        return False
    return relative.suffix != ".pyc"


def _body_files(root: Path) -> dict[str, Path]:
    files: dict[str, Path] = {}
    for current, dirnames, filenames in os.walk(root, topdown=True, followlinks=False):
        current_path = Path(current)
        kept_directories: list[str] = []
        for name in sorted(dirnames):
            path = current_path / name
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if not _relative_is_included(relative):
                continue
            if path.is_symlink():
                raise SelfWorkspaceError(
                    "self-workspace source contains a symbolic link; link semantics are not implemented",
                    {"path": relative.as_posix()},
                )
            kept_directories.append(name)
        dirnames[:] = kept_directories
        for name in sorted(filenames):
            path = current_path / name
            relative = PurePosixPath(path.relative_to(root).as_posix())
            if not _relative_is_included(relative):
                continue
            if path.is_symlink():
                raise SelfWorkspaceError(
                    "self-workspace source contains a symbolic link; link semantics are not implemented",
                    {"path": relative.as_posix()},
                )
            if path.is_file():
                files[relative.as_posix()] = path
    return files


def _validate_workspace_target(root: Path, target: Path) -> None:
    if target == root:
        raise SelfWorkspaceError("self-workspace target cannot be the live machine body")
    try:
        root.relative_to(target)
    except ValueError:
        pass
    else:
        raise SelfWorkspaceError("self-workspace target cannot contain the live machine body")

    try:
        relative = target.relative_to(root)
    except ValueError:
        return
    if not relative.parts or relative.parts[0] != "creations":
        raise SelfWorkspaceError(
            "a repo-local self-workspace must be placed under creations/ so it stays outside the live machine body"
        )


def _validate_workspace_body(workspace: Path) -> None:
    required = [
        "machine.contract.json",
        "src/axm_uc",
        "tests",
        "tools/build.py",
    ]
    missing = [relative for relative in required if not workspace.joinpath(*PurePosixPath(relative).parts).exists()]
    if missing:
        raise SelfWorkspaceError(
            "path is not a complete AXM self-workspace body",
            {"missing_required_paths": missing},
        )


def _compare_bodies(live_root: Path, workspace: Path) -> dict[str, Any]:
    live = _body_files(live_root)
    candidate = _body_files(workspace)
    live_paths = set(live)
    candidate_paths = set(candidate)
    added = sorted(candidate_paths - live_paths)
    removed = sorted(live_paths - candidate_paths)
    modified = sorted(
        relative
        for relative in live_paths & candidate_paths
        if live[relative].read_bytes() != candidate[relative].read_bytes()
    )
    return {
        "truth_status": "OBSERVED_EXACT_SOURCE_BODY_COMPARISON",
        "changed": bool(added or modified or removed),
        "added": added,
        "modified": modified,
        "removed": removed,
        "change_count": len(added) + len(modified) + len(removed),
        "comparison_uses_content_bytes_not_a_trust_score": True,
    }


def clone_self_workspace(root: Path, target: Path, replace: bool = False) -> dict[str, Any]:
    root = Path(root).resolve()
    target = Path(target).resolve()
    _validate_workspace_target(root, target)
    source_files = _body_files(root)
    if not source_files:
        raise SelfWorkspaceError("live machine body has no source files to clone")
    if target.exists() and not replace:
        raise SelfWorkspaceError("self-workspace target already exists", {"path": str(target)})
    if target.exists() and not target.is_dir():
        raise SelfWorkspaceError("self-workspace target exists and is not a directory", {"path": str(target)})

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(f".{target.name}.axm-self-clone-{uuid.uuid4().hex}")
    backup: Path | None = None
    try:
        stage.mkdir()
        for relative, source in source_files.items():
            destination = stage.joinpath(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)

        cloned_files = _body_files(stage)
        missing = sorted(set(source_files) - set(cloned_files))
        unexpected = sorted(set(cloned_files) - set(source_files))
        changed = sorted(
            relative
            for relative in set(source_files) & set(cloned_files)
            if source_files[relative].read_bytes() != cloned_files[relative].read_bytes()
        )
        if missing or unexpected or changed:
            raise SelfWorkspaceError(
                "self-workspace clone verification failed",
                {
                    "missing": missing,
                    "unexpected": unexpected,
                    "content_mismatches": changed,
                },
            )

        if target.exists():
            backup = target.with_name(f".{target.name}.axm-self-backup-{uuid.uuid4().hex}")
            os.replace(target, backup)
        os.replace(stage, target)
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    total_bytes = sum(path.stat().st_size for path in _body_files(target).values())
    return {
        "operation": "clone",
        "truth_status": "VERIFIED_EDITABLE_SOURCE_BODY_CLONE",
        "path": str(target),
        "source_path": str(root),
        "source_files": len(source_files),
        "source_bytes": total_bytes,
        "exact_copy_verified": True,
        "editable": True,
        "independently_testable": True,
        "live_body_modified": False,
        "excluded_runtime_surfaces": sorted(EXCLUDED_TOP_LEVEL | EXCLUDED_ANYWHERE | {"*.pyc"}),
        "git_history_included": False,
        "os_security_sandbox": False,
        "adoption": "not automatic; inspect and test the candidate body before a separately chosen merge/adoption",
    }


def inspect_self_workspace(root: Path, workspace: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    workspace = Path(workspace).resolve()
    _validate_workspace_target(root, workspace)
    _validate_workspace_body(workspace)
    comparison = _compare_bodies(root, workspace)
    return {
        "operation": "inspect",
        "path": str(workspace),
        "body_status": "EDITABLE_SELF_WORKSPACE_CANDIDATE",
        "live_body_modified": False,
        "comparison": comparison,
        "os_security_sandbox": False,
    }


def test_self_workspace(root: Path, workspace: Path, timeout_seconds: int = 900) -> dict[str, Any]:
    root = Path(root).resolve()
    workspace = Path(workspace).resolve()
    _validate_workspace_target(root, workspace)
    _validate_workspace_body(workspace)
    timeout_seconds = _bounded_timeout(timeout_seconds)

    env = dict(os.environ)
    env["PYTHONPATH"] = str(workspace / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, str(workspace / "tools/build.py")]
    try:
        run = subprocess.run(
            command,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
        timed_out = False
    except subprocess.TimeoutExpired as exc:
        return {
            "operation": "test",
            "truth_status": "OBSERVED_SELF_WORKSPACE_BUILD",
            "path": str(workspace),
            "passed": False,
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
            "stdout": _captured_text(exc.stdout),
            "stderr": _captured_text(exc.stderr),
            "live_body_modified": False,
            "live_body_modified_by_workspace_manager": False,
            "os_security_sandbox": False,
        }

    return {
        "operation": "test",
        "truth_status": "OBSERVED_SELF_WORKSPACE_BUILD",
        "path": str(workspace),
        "passed": run.returncode == 0,
        "returncode": run.returncode,
        "timed_out": timed_out,
        "timeout_seconds": timeout_seconds,
        "command": ["python", "tools/build.py"],
        "stdout": run.stdout,
        "stderr": run.stderr,
        "comparison_after_test": _compare_bodies(root, workspace),
        "live_body_modified": False,
        "live_body_modified_by_workspace_manager": False,
        "os_security_sandbox": False,
        "execution_boundary": "candidate tests run with the current process user's host permissions; this is a source-body clone, not an OS containment boundary",
    }


def _candidate_cli(
    workspace: Path,
    arguments: list[str],
    timeout_seconds: int,
) -> dict[str, Any]:
    env = dict(os.environ)
    env["PYTHONPATH"] = str(workspace / "src")
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    command = [sys.executable, "-m", "axm_uc", "--root", str(workspace), *arguments]
    try:
        run = subprocess.run(
            command,
            cwd=workspace,
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
        )
    except subprocess.TimeoutExpired as exc:
        return {
            "passed": False,
            "timed_out": True,
            "timeout_seconds": timeout_seconds,
            "command": ["python", "-m", "axm_uc", "--root", ".", *arguments],
            "stdout": _captured_text(exc.stdout),
            "stderr": _captured_text(exc.stderr),
        }
    parsed: Any = None
    if run.stdout.strip():
        try:
            parsed = json.loads(run.stdout)
        except json.JSONDecodeError:
            pass
    result: dict[str, Any] = {
        "passed": run.returncode == 0,
        "timed_out": False,
        "returncode": run.returncode,
        "command": ["python", "-m", "axm_uc", "--root", ".", *arguments],
        "stdout": run.stdout,
        "stderr": run.stderr,
    }
    if parsed is not None:
        result["result"] = parsed
    return result


def _candidate_probe_paths(workspace: Path, raw_paths: Any) -> list[Path]:
    if not isinstance(raw_paths, list) or not raw_paths:
        raise SelfWorkspaceError("probe_requests must be a non-empty list for plan-probes or creation-trials")
    paths: list[Path] = []
    for raw in raw_paths:
        if not isinstance(raw, str) or not raw.strip():
            raise SelfWorkspaceError("every probe request path must be non-empty text")
        path = Path(raw).expanduser()
        if not path.is_absolute():
            path = workspace / path
        path = path.resolve()
        try:
            path.relative_to(workspace)
        except ValueError as exc:
            raise SelfWorkspaceError("probe request must stay inside the candidate body", {"path": str(path)}) from exc
        if not path.is_file():
            raise SelfWorkspaceError("probe request file does not exist", {"path": str(path)})
        paths.append(path)
    return paths


def request_merge_check(
    root: Path,
    workspace: Path,
    readiness_statement: Any,
    requested_checks: Any = None,
    probe_requests: Any = None,
    timeout_seconds: int = 900,
    requested_by: Any = "candidate-body",
) -> dict[str, Any]:
    root = Path(root).resolve()
    workspace = Path(workspace).resolve()
    _validate_workspace_target(root, workspace)
    _validate_workspace_body(workspace)
    if not isinstance(readiness_statement, str) or not readiness_statement.strip():
        raise SelfWorkspaceError("request-merge-check requires a non-empty readiness_statement")
    if not isinstance(requested_by, str) or not requested_by.strip():
        raise SelfWorkspaceError("requested_by must be non-empty text")
    timeout_seconds = _bounded_timeout(timeout_seconds)

    raw_checks = requested_checks if requested_checks is not None else ["source-diff", "build"]
    if not isinstance(raw_checks, list) or not raw_checks:
        raise SelfWorkspaceError("requested_checks must be a non-empty list")
    checks: list[str] = []
    for raw in raw_checks:
        check = str(raw).strip().casefold()
        if check not in MERGE_CHECKS:
            raise SelfWorkspaceError(
                "unknown requested merge check",
                {"check": check, "supported_checks": sorted(MERGE_CHECKS)},
            )
        if check not in checks:
            checks.append(check)

    probe_paths: list[Path] = []
    if "plan-probes" in checks or "creation-trials" in checks:
        probe_paths = _candidate_probe_paths(workspace, probe_requests)

    observations: dict[str, Any] = {}
    for check in checks:
        if check == "source-diff":
            observations[check] = _compare_bodies(root, workspace)
        elif check == "build":
            observations[check] = test_self_workspace(root, workspace, timeout_seconds=timeout_seconds)
        elif check == "machine-inspect":
            observations[check] = _candidate_cli(workspace, ["inspect"], timeout_seconds)
        elif check == "executable-anatomy":
            observations[check] = _candidate_cli(workspace, ["executable"], timeout_seconds)
        elif check in {"plan-probes", "creation-trials"}:
            command = "plan" if check == "plan-probes" else "trial"
            observations[check] = [
                {
                    "request": path.relative_to(workspace).as_posix(),
                    "observation": _candidate_cli(workspace, [command, str(path)], timeout_seconds),
                }
                for path in probe_paths
            ]

    current_request = {
        "operation": "request-merge-check",
        "truth_status": "CANDIDATE_CHOSEN_MERGE_CHECK_REQUEST",
        "request_state": "MERGE_CHECK_REQUESTED_NOT_APPROVED",
        "requested_by": requested_by.strip(),
        "path": str(workspace),
        "candidate_path": str(workspace),
        "readiness_statement": readiness_statement.strip(),
        "requested_checks": checks,
        "observations": observations,
        "merge_performed": False,
        "merge_approved": False,
        "live_body_modified": False,
        "readiness_decided_by_workspace_manager": False,
        "score_or_growth_incentive": None,
        "meaning": "the candidate chose to request inspection; observations inform a later explicit adoption choice and do not approve it",
        "available_assessment_options": sorted(MERGE_CHECKS),
        "limitations": [
            "source-body execution is not OS-contained",
            "requested observations only prove what their current implementations measure",
            "whole-body merge/adoption is not implemented by this request operation",
        ],
    }
    request_path = workspace / "creations/self-merge-check/current.json"
    atomic_write_json(request_path, current_request)
    current_request["request_artifact"] = str(request_path)
    return current_request


def operate_self_workspace(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    raw_target = inputs.get("path")
    if not isinstance(raw_target, str) or not raw_target.strip():
        raise SelfWorkspaceError("self-workspace path must be non-empty")
    target = Path(raw_target).expanduser()
    if not target.is_absolute():
        target = Path(root) / target
    if operation == "clone":
        return clone_self_workspace(root, target, replace=bool(inputs.get("replace", False)))
    if operation == "inspect":
        return inspect_self_workspace(root, target)
    if operation == "test":
        return test_self_workspace(root, target, timeout_seconds=inputs.get("timeout_seconds", 900))
    if operation == "request-merge-check":
        return request_merge_check(
            root,
            target,
            readiness_statement=inputs.get("readiness_statement"),
            requested_checks=inputs.get("requested_checks"),
            probe_requests=inputs.get("probe_requests"),
            timeout_seconds=inputs.get("timeout_seconds", 900),
            requested_by=inputs.get("requested_by", "candidate-body"),
        )
    raise SelfWorkspaceError("self-workspace operation must be clone, inspect, test, or request-merge-check")

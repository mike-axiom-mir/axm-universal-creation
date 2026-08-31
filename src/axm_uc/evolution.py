from __future__ import annotations

import datetime as dt
import hashlib
import os
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from .atomic import atomic_write_text
from .organ_library import ExecutableOrganError, ExecutableOrganLibrary
from .root_fit import evaluate_declared_root_fit, evaluate_root_fit_decision
from .snapshot import create_daily_snapshot, restore_snapshot
from .self_workspace import (
    EXCLUDED_ANYWHERE,
    EXCLUDED_TOP_LEVEL,
    SelfWorkspaceError,
    _body_files,
    _validate_workspace_body,
    _validate_workspace_target,
    test_self_workspace,
)
from .spawn import test_spawned_unit


class EvolutionError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise EvolutionError(f"{label} exceeds its {maximum}-character bound")
    return text


def _resolve_path(root: Path, raw: Any, label: str) -> Path:
    path = Path(_required_text(raw, label, maximum=1000)).expanduser()
    if not path.is_absolute():
        path = Path(root) / path
    return path.resolve()


def _adoption_root_fit(raw: Any) -> dict[str, Any]:
    evaluated = evaluate_root_fit_decision(raw)
    if evaluated.get("fit") is not True:
        raise EvolutionError(
            "self-evolution root-fit decision is missing attribution or is not positive",
            {"root_fit_decision": evaluated},
        )
    return evaluated


def _organ_destination(root: Path, unit: dict[str, Any]) -> Path:
    organ_id = str(unit["id"])
    version = str(unit["version"])
    destination = (Path(root).resolve() / "executable-organs" / f"{organ_id}-{version}.json").resolve()
    library_root = (Path(root).resolve() / "executable-organs").resolve()
    try:
        destination.relative_to(library_root)
    except ValueError as exc:
        raise EvolutionError("derived executable-organ destination escaped the live library") from exc
    return destination


def _library_refs(root: Path) -> list[str]:
    try:
        return list(ExecutableOrganLibrary(root).summary().get("package_refs", []))
    except ExecutableOrganError as exc:
        raise EvolutionError(str(exc), exc.details) from exc


def _default_snapshot_path(root: Path, day: dt.date) -> Path:
    return Path(root).resolve().parent / "axm-universal-creation-snapshots" / f"AXM_Universal_Creation_{day.isoformat()}.zip"


def ensure_daily_recovery_snapshot(
    root: Path,
    *,
    today: dt.date | None = None,
    output_dir: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    day = today or dt.date.today()
    target = (
        Path(output_dir).resolve() / f"AXM_Universal_Creation_{day.isoformat()}.zip"
        if output_dir is not None
        else _default_snapshot_path(root, day)
    )
    existed_before = target.is_file()
    result = create_daily_snapshot(
        root,
        output_dir=Path(output_dir).resolve() if output_dir is not None else None,
        replace=False,
        today=day,
    )
    if not Path(result["path"]).is_file():
        raise EvolutionError(
            "daily recovery snapshot was not established before self-evolution",
            {"snapshot": result},
        )
    return {
        "truth_status": "DAILY_RECOVERY_SNAPSHOT_READY",
        "day": day.isoformat(),
        "path": result["path"],
        "created_now": result.get("created") is True,
        "already_existed": existed_before or result.get("created") is False,
        "recovery_meaning": "one complete known-good body for this day; restore quarantines the later current body",
    }


def adopt_organ(
    root: Path,
    candidate: Path,
    reason: Any,
    root_fit: Any,
    *,
    today: dt.date | None = None,
    snapshot_output_dir: Path | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    candidate = Path(candidate).resolve()
    reason_text = _required_text(reason, "reason")
    adoption_fit = _adoption_root_fit(root_fit)

    tested = test_spawned_unit(root, candidate)
    if tested.get("passed") is not True:
        return {
            "operation": "adopt-organ",
            "truth_status": "HOLD_CANDIDATE_TESTS_FAILED",
            "adopted": False,
            "path": str(candidate),
            "test_evidence": tested,
            "live_machine_body_modified": False,
        }

    unit = tested.get("inspection", {}).get("unit", {})
    receipt = tested.get("inspection", {}).get("spawn_receipt", {})
    if unit.get("kind") != "organ":
        return {
            "operation": "adopt-organ",
            "truth_status": "HOLD_ADOPTION_KIND_NOT_SUPPORTED",
            "adopted": False,
            "path": str(candidate),
            "kind": unit.get("kind"),
            "supported_kinds": ["organ"],
            "live_machine_body_modified": False,
        }

    candidate_fit = evaluate_declared_root_fit(unit)
    if candidate_fit.get("fit") is not True:
        return {
            "operation": "adopt-organ",
            "truth_status": "HOLD_CANDIDATE_ROOT_FIT",
            "adopted": False,
            "path": str(candidate),
            "root_fit": candidate_fit,
            "live_machine_body_modified": False,
        }

    unit_ref = str(unit["ref"])
    refs_before = _library_refs(root)
    destination = _organ_destination(root, unit)
    if unit_ref in refs_before or destination.exists():
        return {
            "operation": "adopt-organ",
            "truth_status": "HOLD_EXECUTABLE_ORGAN_REF_COLLISION",
            "adopted": False,
            "unit_ref": unit_ref,
            "destination": str(destination),
            "live_machine_body_modified": False,
        }

    entry_relative = PurePosixPath(str(unit["implementation"]["entrypoint"]))
    entrypoint = candidate.joinpath(*entry_relative.parts)
    try:
        source_text = entrypoint.read_text(encoding="utf-8")
    except (OSError, UnicodeError) as exc:
        raise EvolutionError("could not read tested organ entrypoint", {"path": str(entrypoint)}) from exc
    source_digest = _digest_bytes(source_text.encode("utf-8"))

    observed_payload = next(
        (row for row in unit.get("payload_files", []) if row.get("path") == entry_relative.as_posix()),
        None,
    )
    if not isinstance(observed_payload, dict) or observed_payload.get("digest") != source_digest:
        return {
            "operation": "adopt-organ",
            "truth_status": "HOLD_CANDIDATE_SOURCE_DRIFT",
            "adopted": False,
            "unit_ref": unit_ref,
            "entrypoint": str(entrypoint),
            "expected_digest": observed_payload.get("digest") if isinstance(observed_payload, dict) else None,
            "actual_digest": source_digest,
            "live_machine_body_modified": False,
        }

    recovery = ensure_daily_recovery_snapshot(
        root,
        today=today,
        output_dir=snapshot_output_dir,
    )

    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        atomic_write_text(destination, source_text)
        live_library = ExecutableOrganLibrary(root)
        live_package = live_library.inspect(unit_ref)
        live_digest = _digest_bytes(destination.read_bytes())
        if live_digest != source_digest:
            raise EvolutionError(
                "installed organ bytes differ from the tested candidate",
                {"expected_digest": source_digest, "actual_digest": live_digest},
            )
        if live_package.get("ref") != unit_ref:
            raise EvolutionError("live executable-organ library did not register the adopted ref")
    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    refs_after = _library_refs(root)
    if unit_ref not in refs_after:
        if destination.exists():
            destination.unlink()
        raise EvolutionError("adopted organ was not visible after live-library reload")

    return {
        "operation": "adopt-organ",
        "truth_status": "ADOPTED_LIVE_EXECUTABLE_ORGAN",
        "adopted": True,
        "reason": reason_text,
        "unit_ref": unit_ref,
        "candidate_path": str(candidate),
        "candidate_package_digest": receipt.get("package_digest"),
        "source_digest": source_digest,
        "destination": str(destination),
        "candidate_root_fit": candidate_fit,
        "adoption_root_fit": adoption_fit,
        "recovery_snapshot": recovery,
        "transition": {
            "installed": True,
            "registered": True,
            "promoted_for_composition": True,
            "merged": False,
            "canon_changed": False,
            "permissions_changed": False,
        },
        "live_machine_body_modified": True,
        "continuing_machine": "the adopted organ is now part of the normal executable-organ library and may participate in future interface-driven composition",
        "limitations": [
            "organ package validation is structural evidence and does not by itself prove emitted runtime behavior",
            "this v0 path adds a new exact organ ref; replacement and in-place upgrade semantics remain separate future transitions",
            "whole-machine rollback uses the daily snapshot recovery boundary rather than a per-change event log",
        ],
    }


def _body_digest_map(root: Path) -> dict[str, str]:
    return {
        relative: _digest_bytes(path.read_bytes())
        for relative, path in _body_files(Path(root).resolve()).items()
    }


def adopt_whole_body_candidate(
    root: Path,
    candidate: Path,
    reason: Any,
    root_fit: Any,
    *,
    confirm: Any,
    timeout_seconds: int = 900,
    today: dt.date | None = None,
    snapshot_output_dir: Path | None = None,
) -> dict[str, Any]:
    """Adopt one tested complete source candidate while preserving Git/runtime surfaces.

    This is an explicit continuing-machine transition, not a Git merge. The
    current imported Python process still finishes from its old module image;
    the adopted body becomes authoritative for the next process invocation.
    """
    if confirm is not True:
        raise EvolutionError("adopt-whole-body-candidate requires confirm=true")
    root = Path(root).resolve()
    candidate = Path(candidate).resolve()
    reason_text = _required_text(reason, "reason")
    adoption_fit = _adoption_root_fit(root_fit)
    try:
        _validate_workspace_target(root, candidate)
        _validate_workspace_body(candidate)
        candidate_test = test_self_workspace(root, candidate, timeout_seconds=timeout_seconds)
    except SelfWorkspaceError as exc:
        raise EvolutionError(str(exc), exc.details) from exc
    if candidate_test.get("passed") is not True:
        return {
            "operation": "adopt-whole-body-candidate",
            "truth_status": "HOLD_WHOLE_BODY_CANDIDATE_BUILD_FAILED",
            "adopted": False,
            "candidate_path": str(candidate),
            "candidate_test": candidate_test,
            "live_machine_body_modified": False,
        }

    candidate_manifest = _body_digest_map(candidate)
    live_manifest_before = _body_digest_map(root)
    if candidate_manifest == live_manifest_before:
        return {
            "operation": "adopt-whole-body-candidate",
            "truth_status": "HOLD_WHOLE_BODY_CANDIDATE_HAS_NO_SOURCE_CHANGE",
            "adopted": False,
            "candidate_path": str(candidate),
            "candidate_test": candidate_test,
            "live_machine_body_modified": False,
        }

    stage = root.parent / f".{root.name}.axm-whole-body-stage-{uuid.uuid4().hex}"
    quarantine = root.parent / (
        f"{root.name}.whole-body-quarantine-"
        f"{dt.datetime.now(dt.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')}-{uuid.uuid4().hex[:8]}"
    )
    try:
        stage.mkdir(parents=False, exist_ok=False)
        for relative, source in _body_files(candidate).items():
            destination = stage.joinpath(*PurePosixPath(relative).parts)
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
        staged_manifest = _body_digest_map(stage)
        if staged_manifest != candidate_manifest:
            raise EvolutionError(
                "staged whole-body candidate bytes differ from the tested candidate",
                {"candidate_files": candidate_manifest, "staged_files": staged_manifest},
            )

        recovery = ensure_daily_recovery_snapshot(
            root,
            today=today,
            output_dir=snapshot_output_dir,
        )
        quarantine.mkdir(parents=False, exist_ok=False)
        moved_live: list[str] = []
        installed: list[str] = []
        try:
            for child in sorted(root.iterdir(), key=lambda path: path.name):
                relative = PurePosixPath(child.name)
                if (
                    child.name in EXCLUDED_TOP_LEVEL
                    or child.name in EXCLUDED_ANYWHERE
                    or relative.suffix == ".pyc"
                ):
                    continue
                shutil.move(str(child), str(quarantine / child.name))
                moved_live.append(child.name)
            for child in sorted(stage.iterdir(), key=lambda path: path.name):
                os.replace(child, root / child.name)
                installed.append(child.name)
            installed_manifest = _body_digest_map(root)
            if installed_manifest != candidate_manifest:
                raise EvolutionError(
                    "adopted whole-body bytes differ from the tested candidate",
                    {"candidate_files": candidate_manifest, "installed_files": installed_manifest},
                )
        except Exception:
            for name in installed:
                path = root / name
                if path.is_dir():
                    shutil.rmtree(path)
                elif path.exists():
                    path.unlink()
            for child in sorted(quarantine.iterdir(), key=lambda path: path.name):
                os.replace(child, root / child.name)
            quarantine.rmdir()
            raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

    return {
        "operation": "adopt-whole-body-candidate",
        "truth_status": "ADOPTED_TESTED_WHOLE_MACHINE_SOURCE_BODY",
        "adopted": True,
        "reason": reason_text,
        "candidate_path": str(candidate),
        "candidate_test": candidate_test,
        "adoption_root_fit": adoption_fit,
        "source_files_before": len(live_manifest_before),
        "source_files_after": len(candidate_manifest),
        "replaced_top_level": moved_live,
        "candidate_body_digest": _digest_bytes(
            "\n".join(f"{path}\0{digest}" for path, digest in sorted(candidate_manifest.items())).encode("utf-8")
        ),
        "recovery_snapshot": recovery,
        "transition_quarantine": str(quarantine),
        "preserved_live_surfaces": sorted(EXCLUDED_TOP_LEVEL | EXCLUDED_ANYWHERE | {"*.pyc"}),
        "git_history_preserved_in_place": True,
        "git_merge_performed": False,
        "live_machine_body_modified": True,
        "continuing_machine": "the tested candidate source body is installed for the next machine process invocation",
        "limitations": [
            "candidate build execution uses the current process user's host permissions and is not OS-contained",
            "a passing build proves only the checks implemented by that candidate body",
            "Git history and runtime creation surfaces are preserved rather than replaced by candidate copies",
            "recovery remains the one-per-day whole-machine snapshot; the immediate prior source body is also retained in transition quarantine",
        ],
    }


def inspect_evolution(root: Path, *, today: dt.date | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    day = today or dt.date.today()
    snapshot = _default_snapshot_path(root, day)
    try:
        organs = ExecutableOrganLibrary(root).summary()
    except ExecutableOrganError as exc:
        raise EvolutionError(str(exc), exc.details) from exc
    return {
        "operation": "inspect-evolution",
        "truth_status": "OBSERVED_SELF_EVOLUTION_STATE",
        "daily_recovery": {
            "day": day.isoformat(),
            "path": str(snapshot),
            "exists": snapshot.is_file(),
            "model": "one complete restorable snapshot per day; restore quarantines the later current body",
        },
        "executable_organs": organs,
        "state_transitions": {
            "organ_adoption": "live",
            "candidate_capability_adoption": "already available through UniversalCreationMachine.adopt_candidate",
            "snapshot_create": "live",
            "snapshot_restore": "live with explicit confirm",
            "whole_body_candidate_adoption": "live with candidate re-test, attributed root fit, explicit confirm, daily recovery, and byte verification",
            "git_merge": "not performed by whole-body source adoption",
            "canon_change": "not bundled into organ adoption",
            "permission_change": "not bundled into organ adoption",
        },
        "live_machine_body_modified": False,
    }


def snapshot_machine(
    root: Path,
    *,
    output_dir: Path | None = None,
    replace: bool = False,
    today: dt.date | None = None,
) -> dict[str, Any]:
    if not isinstance(replace, bool):
        raise EvolutionError("replace must be boolean")
    result = create_daily_snapshot(
        Path(root).resolve(),
        output_dir=output_dir,
        replace=replace,
        today=today,
    )
    return {
        "operation": "snapshot-machine",
        "truth_status": "DAILY_MACHINE_SNAPSHOT",
        **result,
        "live_machine_body_modified": False,
    }


def restore_machine_snapshot(
    root: Path,
    snapshot: Path,
    *,
    confirm: Any,
    reason: Any,
) -> dict[str, Any]:
    if confirm is not True:
        raise EvolutionError("restore-machine-snapshot requires confirm=true")
    reason_text = _required_text(reason, "reason")
    try:
        result = restore_snapshot(Path(root).resolve(), Path(snapshot).resolve(), confirm=True)
    except (OSError, ValueError) as exc:
        raise EvolutionError(str(exc)) from exc
    return {
        "operation": "restore-machine-snapshot",
        "truth_status": "RESTORED_KNOWN_GOOD_DAILY_MACHINE_SNAPSHOT",
        "reason": reason_text,
        **result,
        "live_machine_body_modified": True,
        "continuity": "the later current body was quarantined by the existing recovery mechanism instead of being silently discarded",
    }


def evolution_summary() -> dict[str, Any]:
    return {
        "truth_status": "EXPLICIT_SELF_EVOLUTION_WITH_DAILY_RECOVERY",
        "operations": [
            "adopt-organ",
            "adopt-whole-body-candidate",
            "inspect-evolution",
            "snapshot-machine",
            "restore-machine-snapshot",
        ],
        "current_adoptable_creation_unit_kinds": ["organ"],
        "outside_approval_required": False,
        "root_fit_required_before_adoption": True,
        "root_fit_decision_attribution_required": True,
        "root_fit_is_objective_proof": False,
        "root_fit_truth_boundary": "the core validates an attributed positive four-root decision and its explicit bases; it does not independently prove moral or semantic correctness",
        "candidate_test_rechecked_before_adoption": True,
        "whole_body_candidate_adoption_available": True,
        "whole_body_adoption_requires_explicit_confirm": True,
        "whole_body_adoption_preserves_git_and_runtime_surfaces": True,
        "daily_snapshot_ensured_before_organ_mutation": True,
        "silent_overwrite": False,
        "state_transitions_are_capabilities": True,
        "recovery_boundary": "one complete restorable snapshot per day",
        "future_transition_surface": [
            "replace-organ",
            "canon-change",
            "permission-change",
        ],
    }


def operate_evolution(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    if operation == "adopt-organ":
        candidate = _resolve_path(root, inputs.get("path"), "path")
        snapshot_output_dir = None
        if inputs.get("snapshot_output_dir") is not None:
            snapshot_output_dir = _resolve_path(root, inputs.get("snapshot_output_dir"), "snapshot_output_dir")
        return adopt_organ(
            root,
            candidate,
            reason=inputs.get("reason"),
            root_fit=inputs.get("root_fit"),
            snapshot_output_dir=snapshot_output_dir,
        )
    if operation == "adopt-whole-body-candidate":
        candidate = _resolve_path(root, inputs.get("path"), "path")
        snapshot_output_dir = None
        if inputs.get("snapshot_output_dir") is not None:
            snapshot_output_dir = _resolve_path(root, inputs.get("snapshot_output_dir"), "snapshot_output_dir")
        return adopt_whole_body_candidate(
            root,
            candidate,
            reason=inputs.get("reason"),
            root_fit=inputs.get("root_fit"),
            confirm=inputs.get("confirm"),
            timeout_seconds=inputs.get("timeout_seconds", 900),
            snapshot_output_dir=snapshot_output_dir,
        )
    if operation == "inspect-evolution":
        return inspect_evolution(root)
    if operation == "snapshot-machine":
        output_dir = None
        if inputs.get("output_dir") is not None:
            output_dir = _resolve_path(root, inputs.get("output_dir"), "output_dir")
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool):
            raise EvolutionError("replace must be boolean")
        return snapshot_machine(root, output_dir=output_dir, replace=replace)
    if operation == "restore-machine-snapshot":
        snapshot = _resolve_path(root, inputs.get("snapshot"), "snapshot")
        return restore_machine_snapshot(
            root,
            snapshot,
            confirm=inputs.get("confirm"),
            reason=inputs.get("reason"),
        )
    raise EvolutionError(
        "unsupported machine evolution operation",
        {"operation": operation, "supported_operations": evolution_summary()["operations"]},
    )

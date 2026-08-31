from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath
from typing import Any

from .atomic import atomic_write_json, atomic_write_text
from .organ_library import ExecutableOrganError, ExecutableOrganLibrary
from .root_fit import evaluate_declared_root_fit
from .spawn import test_spawned_unit


ADOPTION_SCHEMA = "axm.machine-evolution-organ-adoption/v0.1"
ROLLBACK_SCHEMA = "axm.machine-evolution-organ-rollback/v0.1"
ROLLBACK_WINDOW = timedelta(days=1)
EVOLUTION_DIR = "evolution/adoptions"


class EvolutionError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_value(value: Any) -> str:
    return _digest_bytes(_canonical_bytes(value))


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def _parse_iso(value: Any, label: str) -> datetime:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionError(f"{label} must be a UTC timestamp")
    text = value.strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise EvolutionError(f"{label} is not a valid timestamp", {"value": value}) from exc
    if parsed.tzinfo is None:
        raise EvolutionError(f"{label} must include timezone information", {"value": value})
    return parsed.astimezone(timezone.utc)


def _required_text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise EvolutionError(f"{label} exceeds its {maximum}-character bound")
    return text


def _resolve_candidate(root: Path, raw: Any) -> Path:
    path = Path(_required_text(raw, "path", maximum=1000)).expanduser()
    if not path.is_absolute():
        path = Path(root) / path
    return path.resolve()


def _adoption_dir(root: Path) -> Path:
    return Path(root).resolve() / EVOLUTION_DIR


def _safe_adoption_id(value: Any) -> str:
    text = _required_text(value, "adoption_id", maximum=240)
    if any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-" for ch in text):
        raise EvolutionError("adoption_id contains unsupported characters")
    return text


def _record_path(root: Path, adoption_id: str) -> Path:
    return _adoption_dir(root) / f"{adoption_id}.json"


def _rollback_path(root: Path, adoption_id: str) -> Path:
    return _adoption_dir(root) / f"{adoption_id}.rollback.json"


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise EvolutionError(f"could not read {label}: {exc}", {"path": str(path)}) from exc
    if not isinstance(value, dict):
        raise EvolutionError(f"{label} must be a JSON object", {"path": str(path)})
    return value


def _validate_record_digest(record: dict[str, Any], digest_field: str, label: str) -> None:
    expected = record.get(digest_field)
    if not isinstance(expected, str):
        raise EvolutionError(f"{label} is missing {digest_field}")
    body = {key: value for key, value in record.items() if key != digest_field}
    actual = _digest_value(body)
    if actual != expected:
        raise EvolutionError(
            f"{label} digest does not match its current bytes",
            {"expected": expected, "actual": actual},
        )


def _adoption_root_fit(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EvolutionError("root_fit must be an inspectable four-root decision object")
    evaluated = evaluate_declared_root_fit({"root_fit": raw})
    if evaluated.get("fit") is not True:
        raise EvolutionError("self-evolution root-fit decision is not positive", {"root_fit": evaluated})
    return evaluated


def _organ_destination(root: Path, unit: dict[str, Any]) -> Path:
    organ_id = str(unit["id"])
    version = str(unit["version"])
    name = f"{organ_id}-{version}.json"
    path = (Path(root).resolve() / "executable-organs" / name).resolve()
    try:
        path.relative_to((Path(root).resolve() / "executable-organs").resolve())
    except ValueError as exc:
        raise EvolutionError("derived executable-organ destination escaped the live library") from exc
    return path


def _library_refs(root: Path) -> list[str]:
    try:
        return list(ExecutableOrganLibrary(root).summary().get("package_refs", []))
    except ExecutableOrganError as exc:
        raise EvolutionError(str(exc), exc.details) from exc


def adopt_organ(
    root: Path,
    candidate: Path,
    reason: Any,
    root_fit: Any,
    *,
    now: datetime | None = None,
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

    adopted_at = (now or _utc_now()).astimezone(timezone.utc)
    rollback_until = adopted_at + ROLLBACK_WINDOW
    timestamp_token = adopted_at.strftime("%Y%m%dT%H%M%S%fZ")
    adoption_id = f"{unit['id']}-{unit['version']}-{timestamp_token}-{source_digest.removeprefix('sha256:')[:12]}"
    record_path = _record_path(root, adoption_id)
    rollback_path = _rollback_path(root, adoption_id)
    if record_path.exists() or rollback_path.exists():
        raise EvolutionError("unexpected evolution record collision", {"adoption_id": adoption_id})

    test_evidence_digest = _digest_value(tested)
    record_without_digest = {
        "schema": ADOPTION_SCHEMA,
        "state": "ACTIVE_ROLLBACK_WINDOW",
        "adoption_id": adoption_id,
        "unit_ref": unit_ref,
        "kind": "organ",
        "reason": reason_text,
        "candidate_path": str(candidate),
        "candidate_package_digest": receipt.get("package_digest"),
        "test_evidence_digest": test_evidence_digest,
        "candidate_root_fit": candidate_fit,
        "adoption_root_fit": adoption_fit,
        "source_entrypoint": entry_relative.as_posix(),
        "source_digest": source_digest,
        "installed_source_text": source_text,
        "destination": str(destination),
        "destination_relative": destination.relative_to(root).as_posix(),
        "pre_change": {
            "destination_existed": False,
            "library_refs": refs_before,
        },
        "transition": {
            "installed": True,
            "registered": True,
            "promoted_for_composition": True,
            "merged": False,
            "canon_changed": False,
            "permissions_changed": False,
        },
        "adopted_at": _iso(adopted_at),
        "rollback_until": _iso(rollback_until),
        "rollback_window_seconds": int(ROLLBACK_WINDOW.total_seconds()),
        "rollback_action": "remove this exact newly installed organ only if its live digest still matches the adoption receipt",
        "limitations": [
            "adoption proves the exact tested executable-organ package entered the live organ library",
            "organ package validation is structural evidence and does not by itself prove emitted runtime behavior",
            "this v0 adoption path adds a new exact organ ref; replacement and in-place upgrade semantics are not implemented",
            "rollback is guaranteed only inside the recorded one-day window and only while the adopted file has not drifted",
        ],
    }
    record = {**record_without_digest, "adoption_digest": _digest_value(record_without_digest)}

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
        try:
            candidate_entry = json.loads(source_text)
        except json.JSONDecodeError as exc:
            raise EvolutionError("tested organ entrypoint stopped being valid JSON") from exc
        comparable_live = {key: value for key, value in live_package.items() if key not in {"ref", "source_path"}}
        if comparable_live != candidate_entry:
            raise EvolutionError("live executable-organ library does not resolve the exact adopted package")
        atomic_write_json(record_path, record)
    except Exception:
        if destination.exists():
            destination.unlink()
        raise

    refs_after = _library_refs(root)
    if unit_ref not in refs_after:
        if destination.exists():
            destination.unlink()
        if record_path.exists():
            record_path.unlink()
        raise EvolutionError("adopted organ was not visible after live-library reload")

    return {
        "operation": "adopt-organ",
        "truth_status": "ADOPTED_LIVE_EXECUTABLE_ORGAN_WITH_ROLLBACK",
        "adopted": True,
        "adoption_id": adoption_id,
        "unit_ref": unit_ref,
        "destination": str(destination),
        "adoption_receipt": str(record_path),
        "rollback_until": record["rollback_until"],
        "transition": record["transition"],
        "live_machine_body_modified": True,
        "next_observation": "use the organ through normal interface-driven composition; rollback-adoption remains available for one day",
    }


def _inspect_one(root: Path, adoption_id: str, *, now: datetime | None = None) -> dict[str, Any]:
    record_path = _record_path(root, adoption_id)
    if not record_path.is_file():
        raise EvolutionError("adoption record does not exist", {"adoption_id": adoption_id})
    record = _load_json(record_path, "adoption record")
    if record.get("schema") != ADOPTION_SCHEMA:
        raise EvolutionError("adoption record schema is unsupported", {"schema": record.get("schema")})
    _validate_record_digest(record, "adoption_digest", "adoption record")

    rollback_path = _rollback_path(root, adoption_id)
    rollback: dict[str, Any] | None = None
    if rollback_path.is_file():
        rollback = _load_json(rollback_path, "rollback record")
        if rollback.get("schema") != ROLLBACK_SCHEMA:
            raise EvolutionError("rollback record schema is unsupported", {"schema": rollback.get("schema")})
        _validate_record_digest(rollback, "rollback_digest", "rollback record")

    destination = Path(str(record["destination"])).resolve()
    current_digest = _digest_bytes(destination.read_bytes()) if destination.is_file() else None
    expected_digest = record.get("source_digest")
    live_exact = current_digest == expected_digest
    current = (now or _utc_now()).astimezone(timezone.utc)
    deadline = _parse_iso(record.get("rollback_until"), "rollback_until")
    if rollback is not None:
        state = "ROLLED_BACK"
    elif live_exact and current <= deadline:
        state = "ACTIVE_ROLLBACK_WINDOW"
    elif live_exact:
        state = "ACTIVE_ROLLBACK_WINDOW_EXPIRED"
    elif destination.exists():
        state = "HOLD_LIVE_BODY_DRIFT"
    else:
        state = "HOLD_ADOPTED_BODY_MISSING"

    return {
        "adoption_id": adoption_id,
        "state": state,
        "unit_ref": record.get("unit_ref"),
        "adoption": record,
        "rollback": rollback,
        "destination_exists": destination.is_file(),
        "expected_live_digest": expected_digest,
        "actual_live_digest": current_digest,
        "live_exact": live_exact,
        "rollback_available_now": rollback is None and live_exact and current <= deadline,
        "observed_at": _iso(current),
    }


def inspect_evolution(root: Path, adoption_id: Any = None, *, now: datetime | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    if adoption_id is not None:
        inspected = _inspect_one(root, _safe_adoption_id(adoption_id), now=now)
        return {
            "operation": "inspect-evolution",
            "truth_status": "OBSERVED_MACHINE_EVOLUTION_STATE",
            **inspected,
            "live_machine_body_modified": False,
        }

    folder = _adoption_dir(root)
    ids = []
    if folder.is_dir():
        ids = sorted(
            path.name[:-5]
            for path in folder.glob("*.json")
            if not path.name.endswith(".rollback.json")
        )
    records = [_inspect_one(root, item, now=now) for item in ids]
    return {
        "operation": "inspect-evolution",
        "truth_status": "OBSERVED_MACHINE_EVOLUTION_STATE",
        "count": len(records),
        "adoptions": records,
        "live_machine_body_modified": False,
    }


def rollback_adoption(
    root: Path,
    adoption_id: Any,
    reason: Any,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    adoption_key = _safe_adoption_id(adoption_id)
    reason_text = _required_text(reason, "reason")
    inspected = _inspect_one(root, adoption_key, now=now)
    if inspected["rollback"] is not None:
        return {
            "operation": "rollback-adoption",
            "truth_status": "ALREADY_ROLLED_BACK",
            "rolled_back": False,
            "adoption_id": adoption_key,
            "state": inspected["state"],
            "live_machine_body_modified": False,
        }
    if not inspected["rollback_available_now"]:
        return {
            "operation": "rollback-adoption",
            "truth_status": (
                "HOLD_ROLLBACK_WINDOW_EXPIRED"
                if inspected["state"] == "ACTIVE_ROLLBACK_WINDOW_EXPIRED"
                else "HOLD_ROLLBACK_REQUIRES_EXACT_ADOPTED_BODY"
            ),
            "rolled_back": False,
            "adoption_id": adoption_key,
            "state": inspected["state"],
            "expected_live_digest": inspected["expected_live_digest"],
            "actual_live_digest": inspected["actual_live_digest"],
            "live_machine_body_modified": False,
        }

    record = inspected["adoption"]
    destination = Path(str(record["destination"])).resolve()
    expected_library = (root / "executable-organs").resolve()
    try:
        destination.relative_to(expected_library)
    except ValueError as exc:
        raise EvolutionError("adoption destination no longer belongs to the live executable-organ library") from exc

    source_text = record.get("installed_source_text")
    if not isinstance(source_text, str):
        raise EvolutionError("adoption record does not contain exact installed source for recovery")
    removed_digest = _digest_bytes(destination.read_bytes())
    current = (now or _utc_now()).astimezone(timezone.utc)
    rollback_without_digest = {
        "schema": ROLLBACK_SCHEMA,
        "state": "ROLLED_BACK",
        "adoption_id": adoption_key,
        "unit_ref": record.get("unit_ref"),
        "reason": reason_text,
        "adoption_digest": record.get("adoption_digest"),
        "removed_digest": removed_digest,
        "rolled_back_at": _iso(current),
        "transition": {
            "installed": False,
            "registered": False,
            "promoted_for_composition": False,
            "merged": record.get("transition", {}).get("merged", False),
            "canon_changed": record.get("transition", {}).get("canon_changed", False),
            "permissions_changed": record.get("transition", {}).get("permissions_changed", False),
        },
        "continuity": "the adoption receipt and rollback receipt remain inspectable after the exact live organ file is removed",
    }
    rollback = {**rollback_without_digest, "rollback_digest": _digest_value(rollback_without_digest)}
    rollback_path = _rollback_path(root, adoption_key)

    try:
        destination.unlink()
        if str(record.get("unit_ref")) in _library_refs(root):
            raise EvolutionError("rolled-back organ ref is still visible in the executable-organ library")
        atomic_write_json(rollback_path, rollback)
    except Exception:
        if not destination.exists():
            atomic_write_text(destination, source_text)
        raise

    return {
        "operation": "rollback-adoption",
        "truth_status": "ROLLED_BACK_EXACT_ORGAN_ADOPTION",
        "rolled_back": True,
        "adoption_id": adoption_key,
        "unit_ref": record.get("unit_ref"),
        "rollback_receipt": str(rollback_path),
        "transition": rollback["transition"],
        "live_machine_body_modified": True,
    }


def evolution_summary() -> dict[str, Any]:
    return {
        "truth_status": "EXPLICIT_SELF_EVOLUTION_WITH_BOUNDED_ROLLBACK",
        "operations": ["adopt-organ", "inspect-evolution", "rollback-adoption"],
        "current_adoptable_kinds": ["organ"],
        "rollback_window_seconds": int(ROLLBACK_WINDOW.total_seconds()),
        "outside_approval_required": False,
        "root_fit_required_before_adoption": True,
        "candidate_test_rechecked_before_adoption": True,
        "silent_overwrite": False,
        "state_transitions_are_capabilities": True,
        "future_transition_surface": [
            "register",
            "promote",
            "merge",
            "canon-change",
            "permission-change",
        ],
    }


def operate_evolution(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    if operation == "adopt-organ":
        candidate = _resolve_candidate(root, inputs.get("path"))
        return adopt_organ(
            root,
            candidate,
            reason=inputs.get("reason"),
            root_fit=inputs.get("root_fit"),
        )
    if operation == "inspect-evolution":
        return inspect_evolution(root, inputs.get("adoption_id"))
    if operation == "rollback-adoption":
        return rollback_adoption(
            root,
            adoption_id=inputs.get("adoption_id"),
            reason=inputs.get("reason"),
        )
    raise EvolutionError(
        "unsupported machine evolution operation",
        {"operation": operation, "supported_operations": evolution_summary()["operations"]},
    )

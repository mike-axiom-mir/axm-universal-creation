from __future__ import annotations

import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any


HOST_EVIDENCE_SCHEMA = "axm.creation-host-evidence/v0.1"
HOST_EVIDENCE_RECEIPT_SCHEMA = "axm.creation-host-evidence-receipt/v0.1"
EVIDENCE_KINDS = {
    "runtime-execution",
    "browser-interaction",
    "visual-inspection",
    "gameplay-observation",
    "accessibility-inspection",
    "host-specific",
}
STATUSES = {"PASS", "FAIL", "UNKNOWN", "BLOCKED"}
MAX_PROJECT_FILES = 4096
MAX_PROJECT_BYTES = 256 << 20


class HostEvidenceError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise HostEvidenceError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise HostEvidenceError(f"{label} exceeds its {maximum}-character bound")
    return text


def _sha256(value: Any, label: str) -> str:
    text = _required_text(value, label, 80).casefold()
    if text.startswith("sha256:"):
        text = text[7:]
    if len(text) != 64 or any(character not in "0123456789abcdef" for character in text):
        raise HostEvidenceError(f"{label} must be a SHA-256 digest")
    return text


def _project_manifest(path: Path) -> list[dict[str, Any]]:
    if not path.is_dir():
        raise HostEvidenceError("host evidence subject path is not an existing project directory", {"path": str(path)})
    rows: list[dict[str, Any]] = []
    total = 0
    for file in sorted(path.rglob("*")):
        if file.is_symlink():
            raise HostEvidenceError(
                "host evidence subject project may not contain symbolic links",
                {"path": file.relative_to(path).as_posix()},
            )
        if not file.is_file():
            continue
        if len(rows) >= MAX_PROJECT_FILES:
            raise HostEvidenceError(
                "host evidence subject exceeds the project file bound",
                {"maximum_files": MAX_PROJECT_FILES},
            )
        content = file.read_bytes()
        total += len(content)
        if total > MAX_PROJECT_BYTES:
            raise HostEvidenceError(
                "host evidence subject exceeds the project byte bound",
                {"maximum_bytes": MAX_PROJECT_BYTES},
            )
        rows.append(
            {
                "path": file.relative_to(path).as_posix(),
                "bytes": len(content),
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        )
    if not rows:
        raise HostEvidenceError("host evidence subject project contains no files", {"path": str(path)})
    return rows


def _expected_digests(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict) or not raw:
        raise HostEvidenceError("expected_file_digests must be a non-empty object")
    result: dict[str, str] = {}
    for path, digest in raw.items():
        text = _required_text(path, "expected file path", 1000).replace("\\", "/")
        if text in result:
            raise HostEvidenceError("expected_file_digests contains a duplicate path", {"path": text})
        result[text] = _sha256(digest, f"expected digest for {text}")
    return result


def _timestamp(raw: Any) -> dt.datetime:
    text = _required_text(raw, "evidence.observed_at", 100)
    try:
        value = dt.datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise HostEvidenceError("evidence.observed_at must be an ISO-8601 timestamp") from exc
    if value.tzinfo is None or value.utcoffset() is None:
        raise HostEvidenceError("evidence.observed_at must include an explicit UTC offset")
    return value.astimezone(dt.timezone.utc)


def _claims(raw: Any, overall_status: str) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw:
        raise HostEvidenceError("evidence.claims must be a non-empty list")
    if len(raw) > 100:
        raise HostEvidenceError("evidence.claims exceeds the 100-claim bound")
    claims: list[dict[str, Any]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise HostEvidenceError("host evidence claim must be an object", {"index": index})
        allowed = {"claim", "status", "basis", "evidence_refs"}
        unexpected = sorted(set(item) - allowed)
        if unexpected:
            raise HostEvidenceError(
                "host evidence claim contains unsupported fields",
                {"index": index, "unexpected_fields": unexpected},
            )
        status = str(item.get("status", "")).strip().upper()
        if status not in STATUSES:
            raise HostEvidenceError("host evidence claim status is invalid", {"index": index, "status": status})
        refs = item.get("evidence_refs", [])
        if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
            raise HostEvidenceError("host evidence_refs must be a list of non-empty text", {"index": index})
        claims.append(
            {
                "claim": _required_text(item.get("claim"), f"evidence.claims[{index}].claim"),
                "status": status,
                "basis": _required_text(item.get("basis"), f"evidence.claims[{index}].basis"),
                "evidence_refs": [ref.strip() for ref in refs],
            }
        )
    if overall_status == "PASS" and any(item["status"] != "PASS" for item in claims):
        raise HostEvidenceError("overall PASS is incompatible with non-PASS claim evidence")
    if overall_status == "FAIL" and all(item["status"] != "FAIL" for item in claims):
        raise HostEvidenceError("overall FAIL requires at least one failed claim")
    return claims


def _attachments(raw: Any) -> list[dict[str, str]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise HostEvidenceError("evidence.attachments must be a list")
    result: list[dict[str, str]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) != {"name", "sha256"}:
            raise HostEvidenceError(
                "each evidence attachment requires exactly name and sha256",
                {"index": index},
            )
        result.append(
            {
                "name": _required_text(item["name"], f"evidence.attachments[{index}].name", 1000),
                "sha256": _sha256(item["sha256"], f"evidence.attachments[{index}].sha256"),
            }
        )
    return result


def host_evidence_summary() -> dict[str, Any]:
    return {
        "truth_status": "EXPLICIT_EXTERNAL_HOST_EVIDENCE_BOUNDARY",
        "schema": HOST_EVIDENCE_SCHEMA,
        "receipt_schema": HOST_EVIDENCE_RECEIPT_SCHEMA,
        "evidence_kinds": sorted(EVIDENCE_KINDS),
        "statuses": sorted(STATUSES),
        "binds_to_exact_project_digests": True,
        "checks_freshness": True,
        "external_status_is_independently_judged_by_core": False,
        "evidence_grants_execution_authority": False,
        "automatic_activity_log": False,
        "project_limits": {"files": MAX_PROJECT_FILES, "bytes": MAX_PROJECT_BYTES},
    }


def bind_host_evidence(root: Path, inputs: dict[str, Any], *, now: dt.datetime | None = None) -> dict[str, Any]:
    target = Path(str(inputs.get("path", ""))).expanduser()
    if not target.is_absolute():
        target = Path(root) / target
    target = target.resolve()
    manifest = _project_manifest(target)
    actual = {row["path"]: row["sha256"] for row in manifest}
    expected = _expected_digests(inputs.get("expected_file_digests"))
    if expected != actual:
        raise HostEvidenceError(
            "host evidence does not bind to the current exact project body",
            {
                "expected_file_digests": expected,
                "actual_file_digests": actual,
                "missing_expected_paths": sorted(set(actual) - set(expected)),
                "missing_current_paths": sorted(set(expected) - set(actual)),
                "changed_paths": sorted(path for path in set(actual) & set(expected) if actual[path] != expected[path]),
            },
        )
    evidence = inputs.get("evidence")
    if not isinstance(evidence, dict):
        raise HostEvidenceError("evidence must be an object")
    allowed = {
        "schema",
        "kind",
        "status",
        "observed_by",
        "observed_at",
        "valid_for_seconds",
        "claims",
        "limitations",
        "attachments",
    }
    unexpected = sorted(set(evidence) - allowed)
    if unexpected:
        raise HostEvidenceError("evidence contains unsupported fields", {"unexpected_fields": unexpected})
    if evidence.get("schema") != HOST_EVIDENCE_SCHEMA:
        raise HostEvidenceError(
            "host evidence schema is not supported",
            {"expected": HOST_EVIDENCE_SCHEMA, "received": evidence.get("schema")},
        )
    kind = str(evidence.get("kind", "")).strip().casefold()
    if kind not in EVIDENCE_KINDS:
        raise HostEvidenceError("host evidence kind is not supported", {"kind": kind})
    status = str(evidence.get("status", "")).strip().upper()
    if status not in STATUSES:
        raise HostEvidenceError("host evidence status is invalid", {"status": status})
    observed_at = _timestamp(evidence.get("observed_at"))
    valid_for = evidence.get("valid_for_seconds", 3600)
    if not isinstance(valid_for, int) or isinstance(valid_for, bool) or valid_for < 1 or valid_for > 31_536_000:
        raise HostEvidenceError("evidence.valid_for_seconds must be an integer from 1 through 31536000")
    current = now or dt.datetime.now(dt.timezone.utc)
    current = current.astimezone(dt.timezone.utc)
    expires_at = observed_at + dt.timedelta(seconds=valid_for)
    freshness = "FRESH" if observed_at <= current <= expires_at else "STALE_OR_NOT_YET_VALID"
    limitations = evidence.get("limitations", [])
    if not isinstance(limitations, list) or any(not isinstance(item, str) or not item.strip() for item in limitations):
        raise HostEvidenceError("evidence.limitations must be a list of non-empty text")
    normalized = {
        "schema": HOST_EVIDENCE_SCHEMA,
        "kind": kind,
        "status": status,
        "observed_by": _required_text(evidence.get("observed_by"), "evidence.observed_by", 1000),
        "observed_at": observed_at.isoformat().replace("+00:00", "Z"),
        "valid_for_seconds": valid_for,
        "expires_at": expires_at.isoformat().replace("+00:00", "Z"),
        "freshness": freshness,
        "claims": _claims(evidence.get("claims"), status),
        "limitations": [item.strip() for item in limitations],
        "attachments": _attachments(evidence.get("attachments")),
    }
    effective_status = status if freshness == "FRESH" else "UNKNOWN"
    receipt = {
        "schema": HOST_EVIDENCE_RECEIPT_SCHEMA,
        "truth_status": "EXTERNAL_OBSERVATION_BOUND_TO_EXACT_PROJECT_NOT_INDEPENDENTLY_JUDGED",
        "path": str(target),
        "project_files": manifest,
        "project_digest": _digest(actual),
        "evidence": normalized,
        "effective_status": effective_status,
        "authority": {
            "external_observer_claim_preserved": True,
            "core_independently_reperformed_observation": False,
            "execution_authority_granted": False,
            "machine_body_modified": False,
            "automatic_history_written": False,
        },
    }
    return {**receipt, "receipt_digest": _digest(receipt)}


def operate_host_evidence(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    if operation == "inspect":
        return {"operation": operation, **host_evidence_summary()}
    if operation == "bind":
        return {"operation": operation, **bind_host_evidence(root, inputs)}
    raise HostEvidenceError(
        "unsupported host evidence operation",
        {"operation": operation, "supported_operations": ["inspect", "bind"]},
    )

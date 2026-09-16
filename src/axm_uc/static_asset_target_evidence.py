"""Bind target-context evidence to one exact static GLB without inventing readiness.

This module does not run a game engine, collision solver, navigation bake, visual
review, or performance benchmark. It validates a closed evidence packet, binds
that packet to the exact artifact bytes, and refuses to promote a required lane
when the supplied evidence kind is too weak for the claim.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from .asset_geometry import GeometryIssue, MAX_BYTES, _GLB

PACKET_SCHEMA = "axm.static-asset-target-evidence/v0.1"
REPORT_SCHEMA = "axm.static-asset-target-evidence-report/v0.1"

_ALLOWED_STATUSES = {"PASS", "FAIL", "NOT_TESTED"}
_ALLOWED_EVIDENCE_KINDS = {
    "TESTED",
    "MEASURED",
    "VISUALLY_INSPECTED",
    "SOURCE_INSPECTED",
    "INFERRED",
}
_LANE_EVIDENCE_KINDS = {
    "target_engine_import": {"TESTED"},
    "scale_pivot": {"TESTED", "MEASURED"},
    "material_shader": {"TESTED", "VISUALLY_INSPECTED"},
    "collision": {"TESTED", "MEASURED"},
    "navigation": {"TESTED", "MEASURED"},
    "resource_budget": {"TESTED", "MEASURED"},
    "material_sidedness": {"TESTED", "VISUALLY_INSPECTED"},
    "lod_perceptual_equivalence": {"VISUALLY_INSPECTED"},
    "target_runtime_integration": {"TESTED", "MEASURED"},
    "target_device_performance": {"MEASURED"},
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be non-empty text")
    return value.strip()


def _validate_evidence_item(value: Any, lane: str, index: int) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError(f"{lane}.evidence[{index}] must be an object")
    unknown = set(value) - {"kind", "source", "summary", "details"}
    if unknown:
        raise ValueError(f"unknown {lane}.evidence[{index}] field(s): {sorted(unknown)}")
    kind = value.get("kind")
    if kind not in _ALLOWED_EVIDENCE_KINDS:
        raise ValueError(f"{lane}.evidence[{index}].kind is not supported")
    normalized = {
        "kind": kind,
        "source": _text(value.get("source"), f"{lane}.evidence[{index}].source"),
        "summary": _text(value.get("summary"), f"{lane}.evidence[{index}].summary"),
    }
    if "details" in value:
        if not isinstance(value["details"], dict):
            raise ValueError(f"{lane}.evidence[{index}].details must be an object")
        normalized["details"] = value["details"]
    return normalized


def validate_static_asset_target_evidence(value: Any) -> dict[str, Any]:
    """Validate and normalize a closed target-context evidence packet."""
    if not isinstance(value, dict) or value.get("schema") != PACKET_SCHEMA:
        raise ValueError("invalid static asset target evidence schema")
    unknown = set(value) - {"schema", "artifact_sha256", "target", "required_lanes", "lanes"}
    if unknown:
        raise ValueError(f"unknown static asset target evidence field(s): {sorted(unknown)}")

    artifact_sha256 = value.get("artifact_sha256")
    if not isinstance(artifact_sha256, str) or not _SHA256_RE.fullmatch(artifact_sha256):
        raise ValueError("artifact_sha256 must be a lowercase SHA-256 hex digest")

    target = value.get("target")
    if not isinstance(target, dict):
        raise ValueError("target must be an object")
    unknown_target = set(target) - {"engine", "version", "context"}
    if unknown_target:
        raise ValueError(f"unknown target field(s): {sorted(unknown_target)}")
    normalized_target = {
        "engine": _text(target.get("engine"), "target.engine"),
        "context": _text(target.get("context"), "target.context"),
    }
    if "version" in target:
        normalized_target["version"] = _text(target["version"], "target.version")

    required_lanes = value.get("required_lanes")
    if not isinstance(required_lanes, list) or not required_lanes:
        raise ValueError("required_lanes must be a non-empty array")
    normalized_required: list[str] = []
    for index, lane in enumerate(required_lanes):
        lane = _text(lane, f"required_lanes[{index}]")
        if lane not in _LANE_EVIDENCE_KINDS:
            raise ValueError(f"unknown required lane: {lane}")
        if lane in normalized_required:
            raise ValueError(f"duplicate required lane: {lane}")
        normalized_required.append(lane)

    lanes = value.get("lanes")
    if not isinstance(lanes, dict):
        raise ValueError("lanes must be an object")
    unknown_lanes = set(lanes) - set(_LANE_EVIDENCE_KINDS)
    if unknown_lanes:
        raise ValueError(f"unknown target evidence lane(s): {sorted(unknown_lanes)}")

    normalized_lanes: dict[str, dict[str, Any]] = {}
    for lane, row in lanes.items():
        if not isinstance(row, dict):
            raise ValueError(f"{lane} must be an object")
        unknown_row = set(row) - {"status", "evidence", "notes"}
        if unknown_row:
            raise ValueError(f"unknown {lane} field(s): {sorted(unknown_row)}")
        status = row.get("status")
        if status not in _ALLOWED_STATUSES:
            raise ValueError(f"{lane}.status must be PASS, FAIL or NOT_TESTED")
        evidence = row.get("evidence", [])
        if not isinstance(evidence, list):
            raise ValueError(f"{lane}.evidence must be an array")
        notes = row.get("notes", [])
        if not isinstance(notes, list) or any(not isinstance(note, str) or not note.strip() for note in notes):
            raise ValueError(f"{lane}.notes must be an array of non-empty text")
        normalized_lanes[lane] = {
            "status": status,
            "evidence": [_validate_evidence_item(item, lane, index) for index, item in enumerate(evidence)],
            "notes": [note.strip() for note in notes],
        }

    normalized = {
        "schema": PACKET_SCHEMA,
        "artifact_sha256": artifact_sha256,
        "target": normalized_target,
        "required_lanes": normalized_required,
        "lanes": normalized_lanes,
    }
    # Also guarantees every optional details object is JSON-safe and strips
    # caller-specific Python container subclasses from the returned contract.
    return json.loads(json.dumps(normalized, sort_keys=True, allow_nan=False))


def verify_static_asset_target_evidence(path: str | Path, packet: Any) -> dict[str, Any]:
    """Bind supplied target evidence to exact GLB bytes and evaluate declared gates.

    PASS means only that every caller-declared required lane has a PASS receipt
    containing at least one evidence kind strong enough for that lane, the packet
    is bound to the exact artifact SHA-256, and no supplied lane reports FAIL.
    UC does not independently reproduce the external target observations here.
    """
    spec = validate_static_asset_target_evidence(packet)
    packet_bytes = json.dumps(spec, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    target = Path(path).resolve()
    result: dict[str, Any] = {
        "schema": REPORT_SCHEMA,
        "status": "HOLD",
        "artifact_sha256": None,
        "packet_sha256": hashlib.sha256(packet_bytes).hexdigest(),
        "target": spec["target"],
        "required_lanes": list(spec["required_lanes"]),
        "lane_results": {},
        "findings": [],
        "finding_count": 0,
        "finding_counts": {},
        "scope": (
            "Exact-artifact evidence binding and minimum evidence-kind sufficiency for caller-declared static GLB "
            "target-context gates. This verifier does not itself launch the target engine, import the asset, run "
            "collision/navigation, inspect rendering, measure device performance, or prove game readiness."
        ),
        "nonclaims": [
            "A PASS does not mean UC independently reproduced the referenced external observations.",
            "A PASS does not certify visual quality, gameplay readability, engine compatibility outside the declared target, or production readiness.",
            "NOT_TESTED and missing required lanes remain HOLD rather than being inferred from source structure.",
        ],
    }

    def finding(code: str, **details: Any) -> None:
        result["finding_count"] += 1
        result["finding_counts"][code] = result["finding_counts"].get(code, 0) + 1
        if len(result["findings"]) < 64:
            result["findings"].append({"code": code, **details})

    try:
        raw = target.read_bytes()
        if len(raw) > MAX_BYTES:
            finding("RESOURCE_LIMIT", message="GLB exceeds 128MiB inspection limit")
            result["status"] = "HOLD"
            return result
        artifact_sha256 = hashlib.sha256(raw).hexdigest()
        result["artifact_sha256"] = artifact_sha256
        _GLB(raw)  # Basic container/JSON validation only; not target-engine import evidence.
    except GeometryIssue as exc:
        finding(exc.code, message=str(exc))
        result["status"] = "HOLD" if exc.hold else "FAIL"
        return result
    except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        finding("INVALID_ARTIFACT", message=str(exc))
        result["status"] = "FAIL"
        return result

    if result["artifact_sha256"] != spec["artifact_sha256"]:
        finding(
            "ARTIFACT_SHA_MISMATCH",
            expected=spec["artifact_sha256"],
            actual=result["artifact_sha256"],
        )
        result["status"] = "FAIL"
        return result

    required = set(spec["required_lanes"])
    supplied = spec["lanes"]
    any_fail = False
    any_hold = False

    for lane in sorted(set(supplied) | required):
        row = supplied.get(lane)
        is_required = lane in required
        allowed_kinds = _LANE_EVIDENCE_KINDS[lane]
        if row is None:
            result["lane_results"][lane] = {
                "required": True,
                "status": "HOLD",
                "reason": "MISSING_REQUIRED_LANE",
                "acceptable_evidence_kinds": sorted(allowed_kinds),
            }
            finding("MISSING_REQUIRED_LANE", lane=lane)
            any_hold = True
            continue

        declared_status = row["status"]
        kinds = sorted({item["kind"] for item in row["evidence"]})
        lane_result = {
            "required": is_required,
            "declared_status": declared_status,
            "status": declared_status,
            "evidence_kinds": kinds,
            "acceptable_evidence_kinds": sorted(allowed_kinds),
            "evidence_count": len(row["evidence"]),
            "notes": list(row["notes"]),
        }

        if declared_status == "FAIL":
            lane_result["status"] = "FAIL"
            lane_result["reason"] = "DECLARED_TARGET_FAILURE"
            finding("DECLARED_TARGET_FAILURE", lane=lane)
            any_fail = True
        elif declared_status == "NOT_TESTED":
            lane_result["status"] = "HOLD" if is_required else "NOT_TESTED"
            lane_result["reason"] = "REQUIRED_NOT_TESTED" if is_required else "OPTIONAL_NOT_TESTED"
            if is_required:
                finding("REQUIRED_NOT_TESTED", lane=lane)
                any_hold = True
        elif not row["evidence"]:
            lane_result["status"] = "HOLD"
            lane_result["reason"] = "PASS_WITHOUT_EVIDENCE"
            finding("PASS_WITHOUT_EVIDENCE", lane=lane)
            if is_required:
                any_hold = True
        elif not (set(kinds) & allowed_kinds):
            lane_result["status"] = "HOLD"
            lane_result["reason"] = "INSUFFICIENT_EVIDENCE_KIND"
            finding(
                "INSUFFICIENT_EVIDENCE_KIND",
                lane=lane,
                supplied=kinds,
                acceptable=sorted(allowed_kinds),
            )
            if is_required:
                any_hold = True
        else:
            lane_result["status"] = "PASS"
            lane_result["reason"] = "DECLARED_PASS_WITH_QUALIFYING_EVIDENCE"

        result["lane_results"][lane] = lane_result

    if any_fail:
        result["status"] = "FAIL"
    elif any_hold:
        result["status"] = "HOLD"
    else:
        result["status"] = "PASS"
    return result

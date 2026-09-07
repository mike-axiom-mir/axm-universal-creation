from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any

from .design_observer import (
    DEFAULT_PERCEPTUAL_ASSESSMENTS,
    RENDER_OBSERVATION_SCHEMA,
    record_render_observation,
)


VIEWPORT_EVIDENCE_BUNDLE_SCHEMA = "axm.design-viewport-evidence-bundle/v0.1"
MAX_SOURCE_OBSERVATIONS = 16
MAX_PROJECTED_ARTIFACTS = 32
MAX_PROJECTED_ASSESSMENTS = 32
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
ALLOWED_ARTIFACT_FIELDS = {"kind", "digest", "uri", "mime_type", "bytes"}


class DesignEvidenceBundleError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _digest_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise DesignEvidenceBundleError(f"{label} must be a SHA-256 digest")
    normalized = value.casefold()
    if SHA256_RE.fullmatch(normalized) is None:
        raise DesignEvidenceBundleError(f"{label} must use sha256:<64 hex>")
    return normalized


def _text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignEvidenceBundleError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignEvidenceBundleError(f"{label} exceeds its {maximum}-character bound")
    return result


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise DesignEvidenceBundleError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise DesignEvidenceBundleError(f"{label} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise DesignEvidenceBundleError(f"{label} must be between {minimum} and {maximum}")
    return result


def _viewport(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not {"id", "width", "height"}.issubset(raw) or set(raw) - {
        "id",
        "width",
        "height",
        "device_pixel_ratio",
    }:
        raise DesignEvidenceBundleError(
            "viewport must use id, width, height, and optional device_pixel_ratio"
        )
    result: dict[str, Any] = {
        "id": _text(raw["id"], "viewport.id", 128),
        "width": _integer(raw["width"], "viewport.width", 1, 100_000),
        "height": _integer(raw["height"], "viewport.height", 1, 100_000),
        "device_pixel_ratio": _number(
            raw.get("device_pixel_ratio", 1),
            "viewport.device_pixel_ratio",
            0.1,
            32,
        ),
    }
    return result


def _verified_observation(raw: Any, index: int, plan_digest: str) -> dict[str, Any]:
    label = f"observations[{index}]"
    if not isinstance(raw, dict) or raw.get("schema") != RENDER_OBSERVATION_SCHEMA:
        raise DesignEvidenceBundleError(
            f"{label} must be an axm.design-render-observation/v0.1 body"
        )
    observation = copy.deepcopy(raw)
    supplied_digest = _digest_text(observation.get("observation_digest"), f"{label}.observation_digest")
    actual_digest = _digest({key: value for key, value in observation.items() if key != "observation_digest"})
    if supplied_digest != actual_digest:
        raise DesignEvidenceBundleError(
            f"{label} observation digest does not match its contents",
            {"supplied": supplied_digest, "actual": actual_digest},
        )
    observed_plan = _digest_text(observation.get("plan_digest"), f"{label}.plan_digest")
    if observed_plan != plan_digest:
        raise DesignEvidenceBundleError(
            f"{label} belongs to a different design plan",
            {"expected": plan_digest, "actual": observed_plan},
        )
    observer = observation.get("observer")
    if not isinstance(observer, dict) or not isinstance(observer.get("kind"), str) or not isinstance(observer.get("id"), str):
        raise DesignEvidenceBundleError(f"{label}.observer is invalid")
    captures = observation.get("captures")
    if not isinstance(captures, list):
        raise DesignEvidenceBundleError(f"{label}.captures must be a list")
    return observation


def _capture_for_viewport(observation: dict[str, Any], viewport: dict[str, Any], label: str) -> dict[str, Any]:
    matches = [
        capture
        for capture in observation.get("captures", [])
        if isinstance(capture, dict)
        and isinstance(capture.get("viewport"), dict)
        and capture["viewport"].get("id") == viewport["id"]
    ]
    if len(matches) != 1:
        raise DesignEvidenceBundleError(
            f"{label} must contain exactly one capture for viewport {viewport['id']}",
            {"matches": len(matches)},
        )
    capture = matches[0]
    observed_viewport = capture["viewport"]
    observed_ratio = float(observed_viewport.get("device_pixel_ratio", 1))
    expected = (
        viewport["width"],
        viewport["height"],
        float(viewport["device_pixel_ratio"]),
    )
    actual = (
        observed_viewport.get("width"),
        observed_viewport.get("height"),
        observed_ratio,
    )
    if actual != expected:
        raise DesignEvidenceBundleError(
            f"{label} viewport dimensions do not match the bundle viewport",
            {"expected": expected, "actual": actual},
        )
    return capture


def _value_key(value: Any) -> str:
    try:
        return _canonical(value).decode("utf-8")
    except (TypeError, ValueError) as exc:
        raise DesignEvidenceBundleError("measurement value is not canonical JSON") from exc


def _measurement_resolution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_key: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_key.setdefault(row["measurement"], []).append(row)
    result: dict[str, Any] = {}
    for measurement in sorted(by_key):
        evidence = by_key[measurement]
        unique: dict[str, Any] = {}
        for row in evidence:
            unique.setdefault(_value_key(row["value"]), row["value"])
        values = list(unique.values())
        status = "CONSISTENT" if len(values) == 1 else "CONFLICT"
        result[measurement] = {
            "status": status,
            "source_count": len(evidence),
            "distinct_value_count": len(values),
            "consensus_value": copy.deepcopy(values[0]) if len(values) == 1 else None,
            "evidence": copy.deepcopy(evidence),
        }
    return result


def _assessment_resolution(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_id: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        by_id.setdefault(row["assessment"]["id"], []).append(row)
    result: dict[str, Any] = {}
    for assessment_id in sorted(by_id):
        evidence = by_id[assessment_id]
        statuses = sorted({str(row["assessment"].get("status", "")).upper() for row in evidence})
        valid_statuses = [status for status in statuses if status in {"PASS", "FAIL", "HOLD"}]
        consistent = len(valid_statuses) == 1 and len(valid_statuses) == len(statuses)
        result[assessment_id] = {
            "status": "CONSISTENT" if consistent else "CONFLICT",
            "source_count": len(evidence),
            "distinct_statuses": statuses,
            "consensus_status": valid_statuses[0] if consistent else None,
            "evidence": copy.deepcopy(evidence),
        }
    return result


def consolidate_viewport_evidence(
    plan_digest_raw: Any,
    viewport_raw: Any,
    observations_raw: Any,
) -> dict[str, Any]:
    plan_digest = _digest_text(plan_digest_raw, "plan_digest")
    viewport = _viewport(viewport_raw)
    if not isinstance(observations_raw, list) or not 1 <= len(observations_raw) <= MAX_SOURCE_OBSERVATIONS:
        raise DesignEvidenceBundleError(
            f"observations must contain 1..{MAX_SOURCE_OBSERVATIONS} render-observation receipts"
        )

    sources: list[dict[str, Any]] = []
    artifacts: list[dict[str, Any]] = []
    measurement_rows: list[dict[str, Any]] = []
    assessment_rows: list[dict[str, Any]] = []

    seen_observations: set[str] = set()
    for index, raw in enumerate(observations_raw):
        observation = _verified_observation(raw, index, plan_digest)
        observation_digest = observation["observation_digest"]
        if observation_digest in seen_observations:
            raise DesignEvidenceBundleError(
                "duplicate source observation digest is not allowed",
                {"observation_digest": observation_digest},
            )
        seen_observations.add(observation_digest)
        capture = _capture_for_viewport(observation, viewport, f"observations[{index}]")
        observer = copy.deepcopy(observation["observer"])
        source = {
            "observation_digest": observation_digest,
            "truth_status": observation.get("truth_status"),
            "observer": observer,
            "capture_digest": capture.get("capture_digest"),
        }
        sources.append(source)

        for artifact in capture.get("artifacts", []):
            if not isinstance(artifact, dict) or not isinstance(artifact.get("kind"), str) or not isinstance(artifact.get("digest"), str):
                raise DesignEvidenceBundleError(
                    f"observations[{index}] contains an invalid artifact"
                )
            artifacts.append({
                "source_observation_digest": observation_digest,
                "observer": observer,
                "artifact": copy.deepcopy(artifact),
            })

        measurements = capture.get("measurements")
        if not isinstance(measurements, dict):
            raise DesignEvidenceBundleError(
                f"observations[{index}] capture measurements must be an object"
            )
        for name, value in measurements.items():
            measurement_rows.append({
                "measurement": str(name),
                "value": copy.deepcopy(value),
                "source_observation_digest": observation_digest,
                "observer": observer,
            })

        assessments = capture.get("assessments")
        if not isinstance(assessments, list):
            raise DesignEvidenceBundleError(
                f"observations[{index}] capture assessments must be a list"
            )
        for assessment in assessments:
            if not isinstance(assessment, dict) or not isinstance(assessment.get("id"), str):
                raise DesignEvidenceBundleError(
                    f"observations[{index}] contains an invalid assessment"
                )
            assessment_rows.append({
                "assessment": copy.deepcopy(assessment),
                "source_observation_digest": observation_digest,
                "observer": observer,
            })

    measurement_resolution = _measurement_resolution(measurement_rows)
    assessment_resolution = _assessment_resolution(assessment_rows)
    artifact_kind_counts: dict[str, int] = {}
    for row in artifacts:
        kind = str(row["artifact"].get("kind", "other"))
        artifact_kind_counts[kind] = artifact_kind_counts.get(kind, 0) + 1

    conflicts = {
        "measurements": [name for name, body in measurement_resolution.items() if body["status"] == "CONFLICT"],
        "assessments": [name for name, body in assessment_resolution.items() if body["status"] == "CONFLICT"],
    }
    default_perceptual = {
        assessment_id: assessment_resolution.get(
            assessment_id,
            {
                "status": "UNOBSERVED",
                "source_count": 0,
                "distinct_statuses": [],
                "consensus_status": None,
                "evidence": [],
            },
        )
        for assessment_id in DEFAULT_PERCEPTUAL_ASSESSMENTS
    }

    result = {
        "schema": VIEWPORT_EVIDENCE_BUNDLE_SCHEMA,
        "truth_status": "DETERMINISTIC_PROVENANCE_PRESERVING_VIEWPORT_EVIDENCE_BUNDLE",
        "plan_digest": plan_digest,
        "viewport": viewport,
        "sources": sources,
        "evidence": {
            "artifacts": artifacts,
            "measurements": measurement_rows,
            "assessments": assessment_rows,
        },
        "resolution": {
            "measurements": measurement_resolution,
            "assessments": assessment_resolution,
            "conflicts": conflicts,
        },
        "coverage": {
            "source_observation_count": len(sources),
            "artifact_kind_counts": dict(sorted(artifact_kind_counts.items())),
            "measurement_ids": sorted(measurement_resolution),
            "assessment_ids": sorted(assessment_resolution),
            "default_perceptual_assessments": default_perceptual,
        },
        "claim_boundary": {
            "source_observations_preserved": True,
            "conflicting_measurements_silently_resolved": False,
            "conflicting_assessments_silently_resolved": False,
            "weaker_evidence_promoted_to_stronger_evidence": False,
            "aesthetic_truth_inferred": False,
            "accessibility_conformance_inferred": False,
            "automatic_acceptance": False,
        },
    }
    result["bundle_digest"] = _digest(result)
    return result


def _verified_bundle(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != VIEWPORT_EVIDENCE_BUNDLE_SCHEMA:
        raise DesignEvidenceBundleError(
            "bundle must be an axm.design-viewport-evidence-bundle/v0.1 body"
        )
    bundle = copy.deepcopy(raw)
    supplied = _digest_text(bundle.get("bundle_digest"), "bundle.bundle_digest")
    actual = _digest({key: value for key, value in bundle.items() if key != "bundle_digest"})
    if supplied != actual:
        raise DesignEvidenceBundleError(
            "bundle digest does not match its contents",
            {"supplied": supplied, "actual": actual},
        )
    return bundle


def _projection_artifacts(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for row in bundle.get("evidence", {}).get("artifacts", []):
        artifact = row.get("artifact") if isinstance(row, dict) else None
        if not isinstance(artifact, dict):
            continue
        kind = artifact.get("kind")
        digest = artifact.get("digest")
        if not isinstance(kind, str) or not isinstance(digest, str):
            continue
        key = (kind, digest.casefold())
        if key in seen:
            continue
        seen.add(key)
        projected = {
            field: copy.deepcopy(value)
            for field, value in artifact.items()
            if field in ALLOWED_ARTIFACT_FIELDS
        }
        result.append(projected)
    if len(result) > MAX_PROJECTED_ARTIFACTS:
        raise DesignEvidenceBundleError(
            "consensus projection exceeds render-observation artifact bound",
            {"artifact_count": len(result), "maximum": MAX_PROJECTED_ARTIFACTS},
        )
    return result


def _projection_measurements(bundle: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for measurement, body in bundle.get("resolution", {}).get("measurements", {}).items():
        if isinstance(body, dict) and body.get("status") == "CONSISTENT":
            result[str(measurement)] = copy.deepcopy(body.get("consensus_value"))
    return result


def _projection_assessments(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    result = []
    for assessment_id, body in bundle.get("resolution", {}).get("assessments", {}).items():
        if not isinstance(body, dict) or body.get("status") != "CONSISTENT":
            continue
        evidence = body.get("evidence")
        if not isinstance(evidence, list) or not evidence:
            continue
        source_rows = []
        confidences = []
        for row in evidence:
            assessment = row.get("assessment") if isinstance(row, dict) else None
            if not isinstance(assessment, dict):
                continue
            confidence = assessment.get("confidence")
            if isinstance(confidence, (int, float)) and not isinstance(confidence, bool):
                confidences.append(float(confidence))
            observer = row.get("observer") if isinstance(row, dict) else None
            source_rows.append(
                f"{observer.get('kind','?')}:{observer.get('id','?')}"
                if isinstance(observer, dict)
                else "unknown-observer"
            )
        confidence = min(confidences) if confidences else 0.0
        basis = (
            "Consistent attributed assessment status across bundle sources "
            f"[{', '.join(source_rows)}]; this is a consensus projection, not objective aesthetic truth."
        )
        result.append({
            "id": str(assessment_id),
            "status": body.get("consensus_status"),
            "confidence": max(0.0, min(1.0, confidence)),
            "basis": basis[:1200],
        })
    if len(result) > MAX_PROJECTED_ASSESSMENTS:
        raise DesignEvidenceBundleError(
            "consensus projection exceeds render-observation assessment bound",
            {"assessment_count": len(result), "maximum": MAX_PROJECTED_ASSESSMENTS},
        )
    return result


def project_consensus_render_observation(bundle_raw: Any) -> dict[str, Any]:
    bundle = _verified_bundle(bundle_raw)
    viewport = bundle.get("viewport")
    if not isinstance(viewport, dict):
        raise DesignEvidenceBundleError("bundle viewport is invalid")
    source_digests = [
        str(row.get("observation_digest"))
        for row in bundle.get("sources", [])
        if isinstance(row, dict)
    ]
    projection = record_render_observation(
        bundle["plan_digest"],
        {
            "kind": "other",
            "id": "axm-viewport-evidence-bundle",
            "version": "0.1",
            "basis": (
                "deterministic consensus projection from provenance-preserving viewport bundle; "
                "conflicting measurement or assessment claims are omitted so downstream gates HOLD rather than being silently resolved; "
                + "sources="
                + ",".join(source_digests)
            )[:1000],
        },
        [{
            "viewport": copy.deepcopy(viewport),
            "artifacts": _projection_artifacts(bundle),
            "measurements": _projection_measurements(bundle),
            "assessments": _projection_assessments(bundle),
        }],
    )
    projection["truth_status"] = "DERIVED_CONSENSUS_RENDER_OBSERVATION_FROM_ATTRIBUTED_BUNDLE"
    projection["evidence_boundary"]["source_observations_preserved_in_bundle"] = True
    projection["evidence_boundary"]["conflicting_claims_omitted"] = True
    projection["evidence_boundary"]["aesthetic_consensus_promoted_to_objective_truth"] = False
    projection["source_bundle_digest"] = bundle["bundle_digest"]
    projection["source_observation_digests"] = source_digests
    projection["observation_digest"] = _digest(
        {key: value for key, value in projection.items() if key != "observation_digest"}
    )
    return {
        "truth_status": "CONSENSUS_RENDER_PROJECTION_READY_FOR_EXISTING_JUDGE",
        "bundle_digest": bundle["bundle_digest"],
        "omitted_conflicts": copy.deepcopy(bundle.get("resolution", {}).get("conflicts", {})),
        "observation": projection,
        "claim_boundary": {
            "conflict_resolution_policy_invented": False,
            "projection_is_stronger_than_sources": False,
            "automatic_aesthetic_pass": False,
            "automatic_acceptance": False,
        },
    }


def design_evidence_bundle_summary() -> dict[str, Any]:
    return {
        "schema": VIEWPORT_EVIDENCE_BUNDLE_SCHEMA,
        "operations": [
            "inspect-evidence-bundle",
            "consolidate-viewport-evidence",
            "project-consensus-render-observation",
        ],
        "purpose": "join exact same-plan/same-viewport render evidence without collapsing source provenance or silently resolving contradictions",
        "maximum_source_observations": MAX_SOURCE_OBSERVATIONS,
        "conflict_policy": "retain conflicts in bundle; omit them from consensus projection so existing judge receives missing evidence and can HOLD",
        "default_perceptual_assessments": list(DEFAULT_PERCEPTUAL_ASSESSMENTS),
        "automatic_aesthetic_judgment": False,
        "automatic_acceptance": False,
    }


def operate_design_evidence_bundle(inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-evidence-bundle":
        return {
            "truth_status": "DECLARED_VIEWPORT_EVIDENCE_BUNDLE_V0_1",
            **design_evidence_bundle_summary(),
        }
    if operation == "consolidate-viewport-evidence":
        return consolidate_viewport_evidence(
            inputs.get("plan_digest"),
            inputs.get("viewport"),
            inputs.get("observations"),
        )
    if operation == "project-consensus-render-observation":
        return project_consensus_render_observation(inputs.get("bundle"))
    raise DesignEvidenceBundleError(
        "design evidence bundle operation is unsupported",
        {
            "operation": operation,
            "supported_operations": design_evidence_bundle_summary()["operations"],
        },
    )

from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from typing import Any

from .design_fabric import DESIGN_PLAN_SCHEMA, DesignFabricError, judge_design_plan


RENDER_OBSERVATION_SCHEMA = "axm.design-render-observation/v0.1"
INTEGRATED_JUDGMENT_SCHEMA = "axm.design-integrated-judgment/v0.1"
REPAIR_PLAN_SCHEMA = "axm.design-repair-plan/v0.1"
MAX_CAPTURES = 16
MAX_ARTIFACTS = 32
MAX_ASSESSMENTS = 32
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
SHA256_RE = re.compile(r"(?:sha256:)?[0-9a-f]{64}")
OBSERVER_KINDS = {"human", "browser-tool", "model", "test-fixture", "other"}
ARTIFACT_KINDS = {
    "screenshot",
    "dom-snapshot",
    "accessibility-tree",
    "interaction-log",
    "computed-style",
    "performance-trace",
    "other",
}
DEFAULT_PERCEPTUAL_ASSESSMENTS = (
    "visual-hierarchy",
    "spacing-consistency",
    "component-coherence",
)


class DesignObserverError(RuntimeError):
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


def _text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignObserverError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignObserverError(f"{label} exceeds its {maximum}-character bound")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 128)
    if ID_RE.fullmatch(result) is None:
        raise DesignObserverError(f"{label} is invalid", {"value": result})
    return result


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise DesignObserverError(f"{label} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise DesignObserverError(f"{label} must be between {minimum} and {maximum}")
    return result


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise DesignObserverError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _digest_text(value: Any, label: str) -> str:
    result = _text(value, label, 71).casefold()
    if SHA256_RE.fullmatch(result) is None:
        raise DesignObserverError(f"{label} must be a SHA-256 digest")
    return result if result.startswith("sha256:") else f"sha256:{result}"


def _observer(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not {"kind", "id"}.issubset(raw) or set(raw) - {"kind", "id", "version", "basis"}:
        raise DesignObserverError("observer must use kind, id, optional version, and optional basis")
    kind = _text(raw["kind"], "observer.kind", 40).casefold()
    if kind not in OBSERVER_KINDS:
        raise DesignObserverError("observer.kind is unsupported", {"kind": kind, "supported": sorted(OBSERVER_KINDS)})
    result: dict[str, Any] = {
        "kind": kind,
        "id": _identifier(raw["id"], "observer.id"),
    }
    if "version" in raw:
        result["version"] = _text(raw["version"], "observer.version", 120)
    if "basis" in raw:
        result["basis"] = _text(raw["basis"], "observer.basis", 1000)
    return result


def _artifact(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or not {"kind", "digest"}.issubset(raw) or set(raw) - {"kind", "digest", "uri", "mime_type", "bytes"}:
        raise DesignObserverError(f"{label} must use kind, digest, and optional uri/mime_type/bytes")
    kind = _text(raw["kind"], f"{label}.kind", 60).casefold()
    if kind not in ARTIFACT_KINDS:
        raise DesignObserverError(f"{label}.kind is unsupported", {"kind": kind, "supported": sorted(ARTIFACT_KINDS)})
    result: dict[str, Any] = {
        "kind": kind,
        "digest": _digest_text(raw["digest"], f"{label}.digest"),
        "bytes_verified_or_fetched_by_design_fabric": False,
    }
    if "uri" in raw:
        result["uri"] = _text(raw["uri"], f"{label}.uri", 1000)
    if "mime_type" in raw:
        result["mime_type"] = _text(raw["mime_type"], f"{label}.mime_type", 120).casefold()
    if "bytes" in raw:
        result["bytes"] = _integer(raw["bytes"], f"{label}.bytes", 0, 1_000_000_000)
    return result


def _measurements(raw: Any, label: str) -> dict[str, Any]:
    allowed = {
        "horizontal_overflow",
        "focus_visible",
        "reduced_motion_honored",
        "minimum_text_contrast",
        "interaction_error_count",
    }
    if raw is None:
        return {}
    if not isinstance(raw, dict) or set(raw) - allowed:
        raise DesignObserverError(f"{label} has unsupported measurement fields", {"supported": sorted(allowed)})
    result: dict[str, Any] = {}
    for key in ("horizontal_overflow", "focus_visible", "reduced_motion_honored"):
        if key in raw:
            if not isinstance(raw[key], bool):
                raise DesignObserverError(f"{label}.{key} must be boolean")
            result[key] = raw[key]
    if "minimum_text_contrast" in raw:
        result["minimum_text_contrast"] = _number(raw["minimum_text_contrast"], f"{label}.minimum_text_contrast", 1, 21)
    if "interaction_error_count" in raw:
        result["interaction_error_count"] = _integer(raw["interaction_error_count"], f"{label}.interaction_error_count", 0, 1_000_000)
    return result


def _assessment(raw: Any, label: str) -> dict[str, Any]:
    required = {"id", "status", "confidence", "basis"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise DesignObserverError(f"{label} must use exactly id, status, confidence, and basis")
    status = _text(raw["status"], f"{label}.status", 20).upper()
    if status not in {"PASS", "FAIL", "HOLD"}:
        raise DesignObserverError(f"{label}.status must be PASS, FAIL, or HOLD")
    return {
        "id": _identifier(raw["id"], f"{label}.id"),
        "status": status,
        "confidence": _number(raw["confidence"], f"{label}.confidence", 0, 1),
        "basis": _text(raw["basis"], f"{label}.basis", 1200),
    }


def _capture(raw: Any, index: int) -> dict[str, Any]:
    label = f"captures[{index}]"
    required = {"viewport", "artifacts", "measurements", "assessments"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise DesignObserverError(f"{label} must use exactly viewport, artifacts, measurements, and assessments")
    viewport = raw["viewport"]
    if not isinstance(viewport, dict) or not {"id", "width", "height"}.issubset(viewport) or set(viewport) - {"id", "width", "height", "device_pixel_ratio"}:
        raise DesignObserverError(f"{label}.viewport is invalid")
    normalized_viewport: dict[str, Any] = {
        "id": _identifier(viewport["id"], f"{label}.viewport.id"),
        "width": _integer(viewport["width"], f"{label}.viewport.width", 1, 100_000),
        "height": _integer(viewport["height"], f"{label}.viewport.height", 1, 100_000),
    }
    if "device_pixel_ratio" in viewport:
        normalized_viewport["device_pixel_ratio"] = _number(
            viewport["device_pixel_ratio"],
            f"{label}.viewport.device_pixel_ratio",
            0.1,
            32,
        )

    artifacts = raw["artifacts"]
    if not isinstance(artifacts, list) or len(artifacts) > MAX_ARTIFACTS:
        raise DesignObserverError(f"{label}.artifacts must be a list with at most {MAX_ARTIFACTS} entries")
    normalized_artifacts = [_artifact(item, f"{label}.artifacts[{i}]") for i, item in enumerate(artifacts)]

    assessments = raw["assessments"]
    if not isinstance(assessments, list) or len(assessments) > MAX_ASSESSMENTS:
        raise DesignObserverError(f"{label}.assessments must be a list with at most {MAX_ASSESSMENTS} entries")
    normalized_assessments = [_assessment(item, f"{label}.assessments[{i}]") for i, item in enumerate(assessments)]
    ids = [row["id"] for row in normalized_assessments]
    if len(ids) != len(set(ids)):
        raise DesignObserverError(f"{label}.assessment ids must be unique")

    result = {
        "viewport": normalized_viewport,
        "artifacts": normalized_artifacts,
        "measurements": _measurements(raw["measurements"], f"{label}.measurements"),
        "assessments": normalized_assessments,
    }
    result["capture_digest"] = _digest(result)
    return result


def record_render_observation(plan_digest: Any, observer: Any, captures: Any) -> dict[str, Any]:
    if not isinstance(captures, list) or not 1 <= len(captures) <= MAX_CAPTURES:
        raise DesignObserverError(f"captures must contain 1..{MAX_CAPTURES} entries")
    normalized_captures = [_capture(item, index) for index, item in enumerate(captures)]
    viewport_ids = [row["viewport"]["id"] for row in normalized_captures]
    if len(viewport_ids) != len(set(viewport_ids)):
        raise DesignObserverError("capture viewport ids must be unique")
    result = {
        "schema": RENDER_OBSERVATION_SCHEMA,
        "truth_status": "EXPLICIT_EXTERNAL_RENDER_OBSERVATION_RECEIPT",
        "plan_digest": _digest_text(plan_digest, "plan_digest"),
        "observer": _observer(observer),
        "captures": normalized_captures,
        "evidence_boundary": {
            "artifact_bytes_fetched_or_verified": False,
            "browser_or_screen_control_claimed": False,
            "observer_assessments_promoted_to_objective_truth": False,
            "deterministic_normalization_and_digest": True,
        },
    }
    result["observation_digest"] = _digest(result)
    return result


def _gate(name: str, status: str, evidence: dict[str, Any]) -> dict[str, Any]:
    return {"gate": name, "status": status, "evidence": evidence}


def _measurement_values(observation: dict[str, Any], key: str) -> list[Any]:
    values = []
    for capture in observation["captures"]:
        measurements = capture.get("measurements")
        if isinstance(measurements, dict) and key in measurements:
            values.append(measurements[key])
    return values


def judge_rendered_design(
    plan_raw: Any,
    observation_raw: Any,
    required_assessments: Any = None,
) -> dict[str, Any]:
    if not isinstance(plan_raw, dict) or plan_raw.get("schema") != DESIGN_PLAN_SCHEMA:
        raise DesignObserverError("judge-rendered requires an axm.design-plan/v0.1 plan")
    plan = copy.deepcopy(plan_raw)
    plan_digest = plan.get("plan_digest")
    if not isinstance(plan_digest, str):
        raise DesignObserverError("design plan is missing plan_digest")
    if not isinstance(observation_raw, dict) or observation_raw.get("schema") != RENDER_OBSERVATION_SCHEMA:
        raise DesignObserverError("judge-rendered requires an axm.design-render-observation/v0.1 observation")
    observation = copy.deepcopy(observation_raw)
    if observation.get("plan_digest") != plan_digest:
        raise DesignObserverError(
            "render observation does not belong to this design plan",
            {"plan_digest": plan_digest, "observation_plan_digest": observation.get("plan_digest")},
        )

    try:
        structural = judge_design_plan(plan)
    except DesignFabricError as exc:
        raise DesignObserverError(str(exc), getattr(exc, "details", {})) from exc

    if required_assessments is None:
        required = list(DEFAULT_PERCEPTUAL_ASSESSMENTS)
    else:
        if not isinstance(required_assessments, list) or len(required_assessments) > MAX_ASSESSMENTS:
            raise DesignObserverError("required_assessments must be a bounded list")
        required = []
        for index, value in enumerate(required_assessments):
            item = _identifier(value, f"required_assessments[{index}]")
            if item not in required:
                required.append(item)

    required_viewports = plan.get("viewports") if isinstance(plan.get("viewports"), list) else []
    capture_by_viewport = {row["viewport"]["id"]: row for row in observation["captures"]}
    missing_viewports = [viewport for viewport in required_viewports if viewport not in capture_by_viewport]
    gates = [
        _gate(
            "structural-design-judgment",
            structural["status"],
            {"structural_judgment_digest": structural.get("judgment_digest"), "failed_or_held": structural.get("repair_direction", [])},
        ),
        _gate(
            "viewport-render-coverage",
            "PASS" if not missing_viewports else "HOLD",
            {"required": required_viewports, "observed": sorted(capture_by_viewport), "missing": missing_viewports},
        ),
    ]

    screenshots_by_viewport = {
        viewport: any(artifact.get("kind") == "screenshot" for artifact in capture["artifacts"])
        for viewport, capture in capture_by_viewport.items()
    }
    screenshot_missing = [viewport for viewport in required_viewports if not screenshots_by_viewport.get(viewport, False)]
    gates.append(
        _gate(
            "screenshot-evidence-coverage",
            "PASS" if not screenshot_missing else "HOLD",
            {"required": required_viewports, "missing_screenshot_viewports": screenshot_missing},
        )
    )

    overflow_values = _measurement_values(observation, "horizontal_overflow")
    if any(value is True for value in overflow_values):
        overflow_status = "FAIL"
    elif len(overflow_values) < len(required_viewports):
        overflow_status = "HOLD"
    else:
        overflow_status = "PASS"
    gates.append(_gate("horizontal-overflow", overflow_status, {"observations": overflow_values}))

    selected = plan.get("selected_components") if isinstance(plan.get("selected_components"), list) else []
    interactive_required = bool(plan.get("quality_gates", {}).get("focus_visible_required")) and any(
        isinstance(component, dict) and component.get("interactive") is True for component in selected
    )
    focus_values = _measurement_values(observation, "focus_visible")
    if not interactive_required:
        focus_status = "PASS"
    elif any(value is False for value in focus_values):
        focus_status = "FAIL"
    elif not focus_values:
        focus_status = "HOLD"
    else:
        focus_status = "PASS"
    gates.append(_gate("observed-focus-visibility", focus_status, {"required": interactive_required, "observations": focus_values}))

    reduced_required = bool(plan.get("quality_gates", {}).get("reduced_motion_required"))
    reduced_values = _measurement_values(observation, "reduced_motion_honored")
    if not reduced_required:
        reduced_status = "PASS"
    elif any(value is False for value in reduced_values):
        reduced_status = "FAIL"
    elif not reduced_values:
        reduced_status = "HOLD"
    else:
        reduced_status = "PASS"
    gates.append(_gate("observed-reduced-motion", reduced_status, {"required": reduced_required, "observations": reduced_values}))

    contrast_pairs = plan.get("contrast_pairs") if isinstance(plan.get("contrast_pairs"), list) else []
    contrast_values = _measurement_values(observation, "minimum_text_contrast")
    if not contrast_pairs:
        contrast_status = "HOLD"
        threshold = None
    else:
        threshold = max(float(row.get("minimum", 1)) for row in contrast_pairs if isinstance(row, dict))
        if not contrast_values:
            contrast_status = "HOLD"
        elif min(float(value) for value in contrast_values) < threshold:
            contrast_status = "FAIL"
        else:
            contrast_status = "PASS"
    gates.append(
        _gate(
            "observed-rendered-text-contrast",
            contrast_status,
            {"required_minimum": threshold, "observed_minimums": contrast_values},
        )
    )

    interaction_errors = _measurement_values(observation, "interaction_error_count")
    if any(int(value) > 0 for value in interaction_errors):
        interaction_status = "FAIL"
    elif len(interaction_errors) < len(required_viewports):
        interaction_status = "HOLD"
    else:
        interaction_status = "PASS"
    gates.append(_gate("interaction-error-observation", interaction_status, {"observations": interaction_errors}))

    assessment_rows: dict[str, list[dict[str, Any]]] = {item: [] for item in required}
    for capture in observation["captures"]:
        for assessment in capture.get("assessments", []):
            if assessment.get("id") in assessment_rows:
                assessment_rows[str(assessment["id"])].append(assessment)
    perceptual_evidence = []
    perceptual_statuses = []
    for assessment_id in required:
        rows = assessment_rows[assessment_id]
        statuses = [row["status"] for row in rows]
        if "FAIL" in statuses:
            status = "FAIL"
        elif len(rows) < len(required_viewports) or "HOLD" in statuses:
            status = "HOLD"
        else:
            status = "PASS"
        perceptual_statuses.append(status)
        perceptual_evidence.append({
            "assessment": assessment_id,
            "status": status,
            "observations": rows,
        })
    if "FAIL" in perceptual_statuses:
        perceptual_status = "FAIL"
    elif "HOLD" in perceptual_statuses:
        perceptual_status = "HOLD"
    else:
        perceptual_status = "PASS"
    gates.append(
        _gate(
            "external-perceptual-assessments",
            perceptual_status,
            {"required": required, "assessments": perceptual_evidence},
        )
    )

    statuses = [row["status"] for row in gates]
    status = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    result = {
        "schema": INTEGRATED_JUDGMENT_SCHEMA,
        "truth_status": "DETERMINISTIC_INTEGRATION_OF_EXPLICIT_EXTERNAL_RENDER_EVIDENCE",
        "status": status,
        "passed": status == "PASS",
        "plan_digest": plan_digest,
        "observation_digest": observation.get("observation_digest"),
        "observer": copy.deepcopy(observation.get("observer")),
        "structural_judgment": structural,
        "gates": gates,
        "repair_direction": [row["gate"] for row in gates if row["status"] != "PASS"],
        "truth_boundary": [
            "Design Fabric did not capture the screenshots or artifact bytes itself",
            "external observer assessments remain attributed observations rather than objective aesthetic truth",
            "a PASS means every declared structural and external-evidence gate passed for this exact plan and observation set",
            "a PASS does not prove universal beauty, originality, accessibility, or correctness outside the observed conditions",
        ],
    }
    result["judgment_digest"] = _digest(result)
    return result


_REPAIR_MAP = {
    "structural-design-judgment": ("design-structure", "repair the failed or held structural Design Judge gates before trusting rendered quality"),
    "viewport-render-coverage": ("observer-coverage", "capture every requested viewport and bind each capture to the same design-plan digest"),
    "screenshot-evidence-coverage": ("observer-artifacts", "supply screenshot evidence for each requested viewport"),
    "horizontal-overflow": ("responsive-layout", "inspect width constraints, wrapping, fixed dimensions, and overflow rules at failing viewports"),
    "observed-focus-visibility": ("interaction-states", "repair visible keyboard focus styling and re-observe the interactive state"),
    "observed-reduced-motion": ("motion-policy", "implement or repair reduced-motion behavior and re-observe the runtime state"),
    "observed-rendered-text-contrast": ("color-system", "repair rendered foreground/background pairings or tokens and re-measure contrast"),
    "interaction-error-observation": ("interaction-runtime", "repair observed interaction failures before visual approval"),
    "external-perceptual-assessments": ("visual-composition", "repair externally observed hierarchy, spacing, or component-coherence gaps and request a fresh observation"),
}


def propose_design_repair(judgment_raw: Any) -> dict[str, Any]:
    if not isinstance(judgment_raw, dict) or judgment_raw.get("schema") != INTEGRATED_JUDGMENT_SCHEMA:
        raise DesignObserverError("propose-repair requires an axm.design-integrated-judgment/v0.1 judgment")
    actions = []
    for gate in judgment_raw.get("gates", []):
        if not isinstance(gate, dict) or gate.get("status") == "PASS":
            continue
        gate_name = str(gate.get("gate", ""))
        target, instruction = _REPAIR_MAP.get(
            gate_name,
            ("design-evidence", "inspect the held or failed gate evidence and make the smallest justified repair"),
        )
        actions.append({
            "gate": gate_name,
            "status": gate.get("status"),
            "target": target,
            "instruction": instruction,
            "evidence": copy.deepcopy(gate.get("evidence")),
        })
    status = "NO_REPAIR_NEEDED" if not actions else "REPAIR_PLAN_READY_FROM_OBSERVED_GAPS"
    result = {
        "schema": REPAIR_PLAN_SCHEMA,
        "truth_status": "DETERMINISTIC_REPAIR_DIRECTION_FROM_EXPLICIT_GATE_EVIDENCE",
        "status": status,
        "source_judgment_digest": judgment_raw.get("judgment_digest"),
        "actions": actions,
        "automatic_source_rewrite": False,
        "automatic_acceptance": False,
        "next_gate": "apply an explicit repair through existing creation/repair machinery, then render and observe again",
    }
    result["repair_plan_digest"] = _digest(result)
    return result


def design_observer_summary() -> dict[str, Any]:
    return {
        "render_observation_schema": RENDER_OBSERVATION_SCHEMA,
        "integrated_judgment_schema": INTEGRATED_JUDGMENT_SCHEMA,
        "repair_plan_schema": REPAIR_PLAN_SCHEMA,
        "operations": ["inspect-observer", "record-render-observation", "judge-rendered", "propose-repair"],
        "observer_kinds": sorted(OBSERVER_KINDS),
        "artifact_kinds": sorted(ARTIFACT_KINDS),
        "default_perceptual_assessments": list(DEFAULT_PERCEPTUAL_ASSESSMENTS),
        "browser_capture_performed_by_this_module": False,
        "artifact_bytes_verified_by_this_module": False,
        "automatic_source_rewrite": False,
        "closed_loop": "plan -> external render observation -> integrated judgment -> repair direction -> explicit repair -> re-render",
    }


def operate_design_observer(inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    supported = set(design_observer_summary()["operations"])
    if operation not in supported:
        raise DesignObserverError(
            "design observer operation is unsupported",
            {"operation": operation, "supported_operations": sorted(supported)},
        )
    if operation == "inspect-observer":
        return {"truth_status": "DECLARED_DESIGN_OBSERVER_V0_1", **design_observer_summary()}
    if operation == "record-render-observation":
        return record_render_observation(inputs.get("plan_digest"), inputs.get("observer"), inputs.get("captures"))
    if operation == "judge-rendered":
        return judge_rendered_design(inputs.get("plan"), inputs.get("observation"), inputs.get("required_assessments"))
    if operation == "propose-repair":
        return propose_design_repair(inputs.get("judgment"))
    raise AssertionError("unreachable")

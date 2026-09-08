from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from .design_compare import RENDER_COMPARISON_SCHEMA
from .design_observer import (
    INTEGRATED_JUDGMENT_SCHEMA,
    RENDER_OBSERVATION_SCHEMA,
    REPAIR_PLAN_SCHEMA,
)


REPAIR_CYCLE_SCHEMA = "axm.design-repair-cycle-receipt/v0.1"
SHA256_RE = re.compile(r"sha256:[0-9a-f]{64}")
STATUS_RANK = {"FAIL": 0, "HOLD": 1, "PASS": 2}


class DesignCycleError(RuntimeError):
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
        raise DesignCycleError(f"{label} must be a SHA-256 digest")
    value = value.casefold()
    if SHA256_RE.fullmatch(value) is None:
        raise DesignCycleError(f"{label} must be a sha256:<64 hex> digest")
    return value


def _judgment(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != INTEGRATED_JUDGMENT_SCHEMA:
        raise DesignCycleError(f"{label} must be an axm.design-integrated-judgment/v0.1 body")
    result = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    status = str(result.get("status", "")).upper()
    if status not in STATUS_RANK:
        raise DesignCycleError(f"{label}.status must be PASS, FAIL, or HOLD")
    _digest_text(result.get("judgment_digest"), f"{label}.judgment_digest")
    _digest_text(result.get("plan_digest"), f"{label}.plan_digest")
    _digest_text(result.get("observation_digest"), f"{label}.observation_digest")
    if not isinstance(result.get("gates"), list):
        raise DesignCycleError(f"{label}.gates must be a list")
    return result


def _observation(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != RENDER_OBSERVATION_SCHEMA:
        raise DesignCycleError(f"{label} must be an axm.design-render-observation/v0.1 body")
    result = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    _digest_text(result.get("plan_digest"), f"{label}.plan_digest")
    _digest_text(result.get("observation_digest"), f"{label}.observation_digest")
    return result


def _repair_plan(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != REPAIR_PLAN_SCHEMA:
        raise DesignCycleError("repair_plan must be an axm.design-repair-plan/v0.1 body")
    result = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    _digest_text(result.get("source_judgment_digest"), "repair_plan.source_judgment_digest")
    _digest_text(result.get("repair_plan_digest"), "repair_plan.repair_plan_digest")
    if not isinstance(result.get("actions"), list):
        raise DesignCycleError("repair_plan.actions must be a list")
    return result


def _repair_result(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DesignCycleError("repair_result must be an observed project-repair result")
    result = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    if result.get("truth_status") != "OBSERVED_TRANSACTIONAL_PROJECT_REPAIR":
        raise DesignCycleError(
            "repair_result must come from the transactional project repair boundary",
            {"truth_status": result.get("truth_status")},
        )
    if result.get("published") is not True:
        raise DesignCycleError("repair_result must be published before it can enter a completed repair-cycle receipt")
    validation = result.get("validation")
    if not isinstance(validation, dict) or validation.get("passed") is not True:
        raise DesignCycleError("repair_result validation must have passed")
    observed = result.get("observed")
    if not isinstance(observed, dict) or not isinstance(observed.get("before_files"), list) or not isinstance(observed.get("after_files"), list):
        raise DesignCycleError("repair_result must retain before_files and after_files evidence")
    return result


def _comparison(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != RENDER_COMPARISON_SCHEMA:
        raise DesignCycleError("comparison must be an axm.design-render-comparison/v0.1 body")
    result = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    if result.get("status") not in {"PASS", "HOLD"}:
        raise DesignCycleError("comparison status must be PASS or HOLD")
    _digest_text(result.get("comparison_digest"), "comparison.comparison_digest")
    for side in ("before", "after"):
        body = result.get(side)
        if not isinstance(body, dict):
            raise DesignCycleError(f"comparison.{side} must be an object")
        _digest_text(body.get("plan_digest"), f"comparison.{side}.plan_digest")
        _digest_text(body.get("observation_digest"), f"comparison.{side}.observation_digest")
        _digest_text(body.get("artifact_digest"), f"comparison.{side}.artifact_digest")
    return result


def _gate_status_map(judgment: dict[str, Any]) -> dict[str, str]:
    result: dict[str, str] = {}
    for row in judgment.get("gates", []):
        if not isinstance(row, dict):
            continue
        gate = row.get("gate")
        status = str(row.get("status", "")).upper()
        if isinstance(gate, str) and gate and status in STATUS_RANK:
            result[gate] = status
    return result


def _assert_equal(actual: Any, expected: Any, label: str) -> None:
    if actual != expected:
        raise DesignCycleError(
            f"{label} continuity mismatch",
            {"expected": expected, "actual": actual},
        )


def record_repair_cycle(
    before_judgment_raw: Any,
    repair_plan_raw: Any,
    repair_result_raw: Any,
    before_observation_raw: Any,
    after_observation_raw: Any,
    comparison_raw: Any,
    after_judgment_raw: Any,
) -> dict[str, Any]:
    before_judgment = _judgment(before_judgment_raw, "before_judgment")
    after_judgment = _judgment(after_judgment_raw, "after_judgment")
    repair_plan = _repair_plan(repair_plan_raw)
    repair_result = _repair_result(repair_result_raw)
    before_observation = _observation(before_observation_raw, "before_observation")
    after_observation = _observation(after_observation_raw, "after_observation")
    comparison = _comparison(comparison_raw)

    _assert_equal(
        repair_plan["source_judgment_digest"],
        before_judgment["judgment_digest"],
        "repair plan -> before judgment",
    )
    _assert_equal(
        before_judgment["plan_digest"],
        before_observation["plan_digest"],
        "before judgment -> before observation plan",
    )
    _assert_equal(
        before_judgment["observation_digest"],
        before_observation["observation_digest"],
        "before judgment -> before observation",
    )
    _assert_equal(
        after_judgment["plan_digest"],
        after_observation["plan_digest"],
        "after judgment -> after observation plan",
    )
    _assert_equal(
        after_judgment["observation_digest"],
        after_observation["observation_digest"],
        "after judgment -> after observation",
    )
    _assert_equal(
        comparison["before"]["plan_digest"],
        before_observation["plan_digest"],
        "comparison before -> before observation plan",
    )
    _assert_equal(
        comparison["before"]["observation_digest"],
        before_observation["observation_digest"],
        "comparison before -> before observation",
    )
    _assert_equal(
        comparison["after"]["plan_digest"],
        after_observation["plan_digest"],
        "comparison after -> after observation plan",
    )
    _assert_equal(
        comparison["after"]["observation_digest"],
        after_observation["observation_digest"],
        "comparison after -> after observation",
    )

    before_status = str(before_judgment["status"]).upper()
    after_status = str(after_judgment["status"]).upper()
    before_gates = _gate_status_map(before_judgment)
    after_gates = _gate_status_map(after_judgment)
    gate_transitions = []
    all_gates = sorted(set(before_gates) | set(after_gates))
    for gate in all_gates:
        before = before_gates.get(gate)
        after = after_gates.get(gate)
        if before == after:
            movement = "UNCHANGED"
        elif before is None or after is None:
            movement = "EVIDENCE_SET_CHANGED"
        elif STATUS_RANK[after] > STATUS_RANK[before]:
            movement = "TOWARD_PASS"
        else:
            movement = "AWAY_FROM_PASS"
        gate_transitions.append({
            "gate": gate,
            "before": before,
            "after": after,
            "movement": movement,
        })

    status_movement = (
        "UNCHANGED"
        if before_status == after_status
        else "TOWARD_PASS"
        if STATUS_RANK[after_status] > STATUS_RANK[before_status]
        else "AWAY_FROM_PASS"
    )
    if after_status == "PASS":
        cycle_status = "DECLARED_GATES_PASS_AFTER_REPAIR_NOT_AUTO_ACCEPTED"
    elif status_movement == "TOWARD_PASS":
        cycle_status = "EVIDENCE_PROGRESS_AFTER_REPAIR_CYCLE_REMAINS_OPEN"
    else:
        cycle_status = "REPAIR_CYCLE_REMAINS_OPEN"

    repair_result_digest = _digest(repair_result)
    result = {
        "schema": REPAIR_CYCLE_SCHEMA,
        "truth_status": "DETERMINISTIC_CONTINUITY_RECEIPT_ACROSS_EXPLICIT_REPAIR_CYCLE",
        "status": cycle_status,
        "before": {
            "plan_digest": before_judgment["plan_digest"],
            "observation_digest": before_observation["observation_digest"],
            "judgment_digest": before_judgment["judgment_digest"],
            "judgment_status": before_status,
        },
        "repair": {
            "repair_plan_digest": repair_plan["repair_plan_digest"],
            "repair_result_digest": repair_result_digest,
            "published": True,
            "validation_passed": True,
            "operation_count": len(repair_result.get("intent", {}).get("operations", [])),
            "before_file_count": len(repair_result["observed"]["before_files"]),
            "after_file_count": len(repair_result["observed"]["after_files"]),
        },
        "after": {
            "plan_digest": after_judgment["plan_digest"],
            "observation_digest": after_observation["observation_digest"],
            "judgment_digest": after_judgment["judgment_digest"],
            "judgment_status": after_status,
        },
        "comparison": {
            "comparison_digest": comparison["comparison_digest"],
            "status": comparison["status"],
            "truth_status": comparison.get("truth_status"),
            "changed_fraction": comparison.get("change", {}).get("changed_fraction") if isinstance(comparison.get("change"), dict) else None,
        },
        "status_transition": {
            "before": before_status,
            "after": after_status,
            "movement": status_movement,
        },
        "gate_transitions": gate_transitions,
        "automatic_source_rewrite_by_cycle_recorder": False,
        "automatic_acceptance": False,
        "claim_boundary": {
            "repair_execution_observed": True,
            "gate_status_transition_observed": True,
            "pixel_change_observed_when_comparison_passed": comparison["status"] == "PASS",
            "visual_quality_improvement_proven": False,
            "semantic_correctness_proven": False,
            "human_acceptance_granted": False,
        },
        "next_gate": (
            "human or external authority may accept the exact evidence packet"
            if after_status == "PASS"
            else "derive another bounded repair from remaining FAIL/HOLD evidence and repeat the cycle"
        ),
    }
    result["cycle_digest"] = _digest(result)
    return result


def design_cycle_summary() -> dict[str, Any]:
    return {
        "repair_cycle_schema": REPAIR_CYCLE_SCHEMA,
        "operations": ["inspect-repair-cycle", "record-repair-cycle"],
        "links": [
            "before integrated judgment -> before render observation",
            "before judgment -> repair plan",
            "observed transactional project repair",
            "after render observation -> after integrated judgment",
            "before/after render comparison -> exact observations",
        ],
        "gate_status_transition_measured": True,
        "visual_improvement_inferred": False,
        "semantic_correctness_inferred": False,
        "automatic_source_rewrite": False,
        "automatic_acceptance": False,
    }


def operate_design_cycle(inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-repair-cycle":
        return {"truth_status": "DECLARED_DESIGN_REPAIR_CYCLE_V0_1", **design_cycle_summary()}
    if operation == "record-repair-cycle":
        return record_repair_cycle(
            inputs.get("before_judgment"),
            inputs.get("repair_plan"),
            inputs.get("repair_result"),
            inputs.get("before_observation"),
            inputs.get("after_observation"),
            inputs.get("comparison"),
            inputs.get("after_judgment"),
        )
    raise DesignCycleError(
        "repair cycle operation is unsupported",
        {"operation": operation, "supported_operations": design_cycle_summary()["operations"]},
    )

from __future__ import annotations

import copy
import hashlib
import json
import random
from pathlib import Path
from typing import Any

from .capabilities import CapabilityError, CapabilityStore
from .specialist_pool import build_specialist_pool, prepare_tournament


STEPWISE_PREPARATION_SCHEMA = "axm.stepwise-perspective-preparation/v0.1"
STEPWISE_PLAN_SCHEMA = "axm.stepwise-perspective-plan/v0.1"
STEPWISE_WORKFLOW_SCHEMA = "axm.stepwise-perspective-workflow/v0.1"
STEPWISE_CHECKPOINT_SCHEMA = "axm.stepwise-perspective-checkpoint/v0.1"
MAX_INITIAL_STEPS = 64
MAX_TOTAL_STEPS = 128
MAX_SPLIT_DEPTH = 8
PERSPECTIVE_PANEL_SIZE = 4
SELF_HANDLES = {
    "stepwise-workflow",
    "microstep-workflow",
    "perspective-step-run",
    "instant-staged-workflow",
}
DECISIONS = {"PROCEED", "SPLIT", "REPLAN", "HOLD"}
DECISION_PRIORITY = {"PROCEED": 0, "REPLAN": 1, "SPLIT": 2, "HOLD": 3}


class StepwiseWorkflowError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StepwiseWorkflowError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise StepwiseWorkflowError(f"{label} exceeds {maximum} characters")
    return text


def _text_list(value: Any, label: str, *, minimum: int = 1, maximum: int = 16) -> list[str]:
    if not isinstance(value, list) or len(value) < minimum or len(value) > maximum:
        raise StepwiseWorkflowError(f"{label} must be a list with {minimum}..{maximum} entries")
    result: list[str] = []
    for index, item in enumerate(value):
        result.append(_required_text(item, f"{label}[{index}]", 1000))
    return result


def _workflow_body(raw: dict[str, Any]) -> dict[str, Any]:
    body = copy.deepcopy(raw)
    body.pop("workflow_digest", None)
    return body


def _seal_workflow(raw: dict[str, Any]) -> dict[str, Any]:
    body = _workflow_body(raw)
    body["workflow_digest"] = _digest(body)
    return body


def _verify_workflow(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != STEPWISE_WORKFLOW_SCHEMA:
        raise StepwiseWorkflowError("workflow schema is unsupported")
    supplied = raw.get("workflow_digest")
    actual = _digest(_workflow_body(raw))
    if supplied != actual:
        raise StepwiseWorkflowError("workflow digest mismatch")
    return copy.deepcopy(raw)


def _validate_action(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StepwiseWorkflowError(f"{label} must be an object")
    unexpected = sorted(set(raw) - {"kind", "direction", "inputs"})
    if unexpected:
        raise StepwiseWorkflowError(f"{label} has unsupported fields", {"unexpected_fields": unexpected})
    kind = _required_text(raw.get("kind"), f"{label}.kind", 160)
    if kind in SELF_HANDLES:
        raise StepwiseWorkflowError("a stepwise workflow cannot recursively execute itself as a step")
    inputs = raw.get("inputs", {})
    if not isinstance(inputs, dict):
        raise StepwiseWorkflowError(f"{label}.inputs must be an object")
    result = {"kind": kind, "inputs": copy.deepcopy(inputs)}
    if "direction" in raw:
        result["direction"] = _required_text(raw.get("direction"), f"{label}.direction", 1000)
    return result


def _normalize_step(raw: Any, index: int, *, inherited_depth: int | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StepwiseWorkflowError(f"steps[{index}] must be an object")
    allowed = {
        "id", "purpose", "mode", "action", "expected_evidence", "stop_condition",
        "depends_on", "split_depth", "perspective_focus",
    }
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise StepwiseWorkflowError(f"steps[{index}] has unsupported fields", {"unexpected_fields": unexpected})
    step_id = _required_text(raw.get("id"), f"steps[{index}].id", 120)
    mode = str(raw.get("mode", "action")).strip().casefold()
    if mode not in {"action", "analysis"}:
        raise StepwiseWorkflowError(f"steps[{index}].mode must be action or analysis")
    depth_raw = inherited_depth if inherited_depth is not None else raw.get("split_depth", 0)
    if isinstance(depth_raw, bool) or not isinstance(depth_raw, int) or depth_raw < 0 or depth_raw > MAX_SPLIT_DEPTH:
        raise StepwiseWorkflowError(f"steps[{index}].split_depth must be 0..{MAX_SPLIT_DEPTH}")
    depends = raw.get("depends_on", [])
    if not isinstance(depends, list) or any(not isinstance(item, str) or not item.strip() for item in depends):
        raise StepwiseWorkflowError(f"steps[{index}].depends_on must be a list of step ids")
    step = {
        "id": step_id,
        "purpose": _required_text(raw.get("purpose"), f"steps[{index}].purpose", 1600),
        "mode": mode,
        "expected_evidence": _text_list(raw.get("expected_evidence"), f"steps[{index}].expected_evidence"),
        "stop_condition": _required_text(raw.get("stop_condition"), f"steps[{index}].stop_condition", 1200),
        "depends_on": [item.strip() for item in depends],
        "split_depth": depth_raw,
        "perspective_focus": _required_text(
            raw.get("perspective_focus", raw.get("purpose")),
            f"steps[{index}].perspective_focus",
            1600,
        ),
    }
    if mode == "action":
        if "action" not in raw:
            raise StepwiseWorkflowError(f"steps[{index}] action mode requires action")
        step["action"] = _validate_action(raw["action"], f"steps[{index}].action")
    elif "action" in raw:
        raise StepwiseWorkflowError(f"steps[{index}] analysis mode cannot declare an executable action")
    return step


def validate_step_plan(raw: Any, *, expected_goal: str | None = None, maximum: int = MAX_INITIAL_STEPS) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StepwiseWorkflowError("plan must be an object")
    schema = raw.get("schema", STEPWISE_PLAN_SCHEMA)
    if schema != STEPWISE_PLAN_SCHEMA:
        raise StepwiseWorkflowError("plan schema is unsupported")
    goal = _required_text(raw.get("goal"), "plan.goal")
    if expected_goal is not None and goal != expected_goal:
        raise StepwiseWorkflowError("plan goal does not match prepared workflow goal")
    steps_raw = raw.get("steps")
    if not isinstance(steps_raw, list) or not steps_raw or len(steps_raw) > maximum:
        raise StepwiseWorkflowError(f"plan.steps must contain 1..{maximum} steps")
    steps: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(steps_raw):
        step = _normalize_step(row, index)
        if step["id"] in seen:
            raise StepwiseWorkflowError("plan step ids must be unique", {"duplicate": step["id"]})
        missing_or_future = [dependency for dependency in step["depends_on"] if dependency not in seen]
        if missing_or_future:
            raise StepwiseWorkflowError(
                "step dependencies must refer only to earlier steps",
                {"step_id": step["id"], "invalid_dependencies": missing_or_future},
            )
        seen.add(step["id"])
        steps.append(step)
    plan = {
        "schema": STEPWISE_PLAN_SCHEMA,
        "goal": goal,
        "steps": steps,
        "planning_truth": _required_text(
            raw.get(
                "planning_truth",
                "this is the selected explicit step plan; step size and semantic adequacy remain revisable through perspective checkpoints",
            ),
            "plan.planning_truth",
            1600,
        ),
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def prepare_stepwise_workflow(
    root: Path,
    goal: Any,
    *,
    request: Any = None,
    pool_size: int = 32,
    team_size: int = 4,
    max_teams: int = 64,
    seed: str | None = None,
) -> dict[str, Any]:
    goal_text = _required_text(goal, "goal")
    planning_challenge = (
        "Create the smallest truthful executable step plan for this goal. Split broad work until each step has one clear purpose, "
        "one evidence expectation, and one stop condition. Preserve dependencies and explicit unknowns. Goal: " + goal_text
    )
    tournament = prepare_tournament(
        root,
        planning_challenge,
        pool_size=pool_size,
        team_size=team_size,
        max_teams=max_teams,
        seed=seed,
    )
    structural_context = None
    if isinstance(request, dict) and isinstance(request.get("kind"), str) and request["kind"].strip():
        from .machine import UniversalCreationMachine

        structural_context = UniversalCreationMachine(root).plan(copy.deepcopy(request), per_level=4)
    preparation = {
        "schema": STEPWISE_PREPARATION_SCHEMA,
        "status": "AWAITING_PARALLEL_STEP_PLAN_PROPOSALS",
        "goal": goal_text,
        "goal_digest": _digest({"goal": goal_text}),
        "structural_context": structural_context,
        "planning_tournament": tournament,
        "required_plan_contract": {
            "schema": STEPWISE_PLAN_SCHEMA,
            "maximum_initial_steps": MAX_INITIAL_STEPS,
            "step_modes": ["action", "analysis"],
            "required_step_fields": [
                "id", "purpose", "mode", "expected_evidence", "stop_condition",
            ],
            "action_step_additional_field": "action = {kind, inputs, optional direction}",
            "smallness_rule": "one step should express one bounded action or one bounded analysis question; if a checkpoint still sees multiple independent unknowns, split it",
        },
        "truth_boundary": "the deterministic engine prepares competing planning packets but does not claim a team generated a plan until an executor supplies that team's actual proposal",
    }
    preparation["preparation_digest"] = _digest(preparation)
    return preparation


def start_workflow(goal: Any, plan: Any, *, selection_evidence: Any = "explicitly selected plan") -> dict[str, Any]:
    goal_text = _required_text(goal, "goal")
    normalized = validate_step_plan(plan, expected_goal=goal_text)
    states = {
        step["id"]: {
            "status": "PENDING",
            "pre_analysis": None,
            "result": None,
            "post_analysis": None,
        }
        for step in normalized["steps"]
    }
    workflow = {
        "schema": STEPWISE_WORKFLOW_SCHEMA,
        "status": "AWAITING_PRE_ANALYSIS",
        "goal": goal_text,
        "plan": normalized,
        "cursor": 0,
        "step_states": states,
        "completed_steps": [],
        "retired_steps": [],
        "selection_evidence": _required_text(selection_evidence, "selection_evidence", 2000),
        "timeline": [],
        "chronology_rule": "even an instant run must advance through pre-analysis -> execution/result -> post-analysis for every completed step",
    }
    return _seal_workflow(workflow)


def _current_step(workflow: dict[str, Any]) -> dict[str, Any]:
    cursor = workflow.get("cursor")
    steps = workflow["plan"]["steps"]
    if not isinstance(cursor, int) or cursor < 0 or cursor >= len(steps):
        raise StepwiseWorkflowError("workflow has no current step")
    return steps[cursor]


def _panel_profile(row: dict[str, Any], role: str) -> dict[str, Any]:
    return {
        "panel_role": role,
        "id": row["id"],
        "name": row["name"],
        "temperament": row.get("temperament"),
        "core_question": row.get("core_question"),
        "strength": row.get("strength"),
        "blind_spot": row.get("blind_spot"),
        "evidence_preference": row.get("evidence_preference"),
        "fit": row.get("fit"),
    }


def _perspective_panel(root: Path, challenge: str, *, pool_size: int = 20, seed: str | None = None) -> dict[str, Any]:
    pool_size = max(8, min(int(pool_size), 40))
    pool = build_specialist_pool(root, challenge, pool_size=pool_size)
    profiles = pool["specialists"]
    selected: list[tuple[str, dict[str, Any]]] = []
    selected.append(("historically-best-fit", profiles[0]))
    selected.append(("middle-fit", profiles[len(profiles) // 2]))
    selected.append(("lowest-third-challenger", profiles[-1]))
    used = {row[1]["id"] for row in selected}
    candidates = [row for row in profiles if row["id"] not in used]
    if candidates:
        rng_seed = seed or pool["challenge_digest"]
        rng = random.Random(int(hashlib.sha256(rng_seed.encode("utf-8")).hexdigest(), 16))
        selected.append(("mixed-random-challenger", rng.choice(candidates)))
    unique: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role, row in selected:
        if row["id"] in seen:
            continue
        seen.add(row["id"])
        unique.append(_panel_profile(row, role))
    return {
        "context_key": pool["context_key"],
        "challenge_digest": pool["challenge_digest"],
        "panel": unique[:PERSPECTIVE_PANEL_SIZE],
        "selection_truth": "panel intentionally mixes current best-fit, middle, low-ranked, and deterministic-random challengers so historical winners never become the only eyes",
    }


def prepare_checkpoint(root: Path, raw_workflow: Any, *, pool_size: int = 20, seed: str | None = None) -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    if workflow["status"] == "AWAITING_PRE_ANALYSIS":
        phase = "pre"
    elif workflow["status"] == "AWAITING_POST_ANALYSIS":
        phase = "post"
    else:
        raise StepwiseWorkflowError("workflow is not waiting for a perspective checkpoint", {"status": workflow["status"]})
    step = _current_step(workflow)
    prior = workflow["completed_steps"][-4:]
    challenge = (
        f"{phase}-step analysis for goal '{workflow['goal']}'. Current step '{step['id']}': {step['purpose']}. "
        f"Expected evidence: {', '.join(step['expected_evidence'])}. Stop condition: {step['stop_condition']}. "
        f"Recently completed steps: {', '.join(prior) if prior else 'none'}."
    )
    panel = _perspective_panel(root, challenge, pool_size=pool_size, seed=seed)
    required_questions = (
        [
            "Which assumption could make this step too large or incorrectly ordered?",
            "What evidence should exist before executing it?",
            "Should this step PROCEED, SPLIT, REPLAN, or HOLD?",
        ]
        if phase == "pre"
        else [
            "Does the observed result satisfy the declared evidence and stop condition?",
            "What new gap or contradiction appeared only after this result existed?",
            "Should the workflow PROCEED, SPLIT, REPLAN, or HOLD before the next step?",
        ]
    )
    checkpoint = {
        "schema": STEPWISE_CHECKPOINT_SCHEMA,
        "workflow_digest": workflow["workflow_digest"],
        "step_id": step["id"],
        "phase": phase,
        "context_key": panel["context_key"],
        "perspectives": panel["panel"],
        "required_questions": required_questions,
        "required_response": {
            "analysis": "non-empty analysis text",
            "decision": sorted(DECISIONS),
            "evidence_refs": "one or more explicit evidence/unknown references",
        },
        "execution_claim": "perspective packets are prepared but no perspective analysis is claimed until an executor supplies it",
    }
    checkpoint["checkpoint_digest"] = _digest(checkpoint)
    return checkpoint


def _verify_checkpoint(raw: Any, workflow: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != STEPWISE_CHECKPOINT_SCHEMA:
        raise StepwiseWorkflowError("checkpoint schema is unsupported")
    supplied = raw.get("checkpoint_digest")
    body = copy.deepcopy(raw)
    body.pop("checkpoint_digest", None)
    if supplied != _digest(body):
        raise StepwiseWorkflowError("checkpoint digest mismatch")
    if raw.get("workflow_digest") != workflow.get("workflow_digest"):
        raise StepwiseWorkflowError("checkpoint was prepared for a different workflow state")
    if raw.get("step_id") != _current_step(workflow)["id"]:
        raise StepwiseWorkflowError("checkpoint step does not match current workflow step")
    return copy.deepcopy(raw)


def record_checkpoint_analysis(raw_workflow: Any, raw_checkpoint: Any, analyses: Any) -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    checkpoint = _verify_checkpoint(raw_checkpoint, workflow)
    expected_phase = "pre" if workflow["status"] == "AWAITING_PRE_ANALYSIS" else "post" if workflow["status"] == "AWAITING_POST_ANALYSIS" else None
    if checkpoint["phase"] != expected_phase:
        raise StepwiseWorkflowError("checkpoint phase does not match workflow state")
    if not isinstance(analyses, dict):
        raise StepwiseWorkflowError("analyses must be an object keyed by specialist id")
    expected_ids = [row["id"] for row in checkpoint["perspectives"]]
    if set(analyses) != set(expected_ids):
        raise StepwiseWorkflowError(
            "analyses must contain exactly the prepared perspective panel",
            {"expected": sorted(expected_ids), "received": sorted(analyses)},
        )
    normalized: dict[str, Any] = {}
    decisions: list[str] = []
    for specialist_id in expected_ids:
        row = analyses[specialist_id]
        if not isinstance(row, dict):
            raise StepwiseWorkflowError(f"analysis for {specialist_id} must be an object")
        decision = str(row.get("decision", "")).strip().upper()
        if decision not in DECISIONS:
            raise StepwiseWorkflowError(f"analysis decision for {specialist_id} must be one of {sorted(DECISIONS)}")
        decisions.append(decision)
        normalized[specialist_id] = {
            "analysis": _required_text(row.get("analysis"), f"analyses.{specialist_id}.analysis", 4000),
            "decision": decision,
            "evidence_refs": _text_list(row.get("evidence_refs"), f"analyses.{specialist_id}.evidence_refs", maximum=24),
        }
    aggregate = max(decisions, key=lambda item: DECISION_PRIORITY[item])
    step = _current_step(workflow)
    record = {
        "type": "PERSPECTIVE_CHECKPOINT",
        "phase": checkpoint["phase"],
        "step_id": step["id"],
        "checkpoint_digest": checkpoint["checkpoint_digest"],
        "analyses": normalized,
        "decisions": decisions,
        "aggregate_transition": aggregate,
        "aggregation_truth": "the most conservative supplied transition wins; this is a workflow-control rule, not a claim that the perspectives are objectively correct",
    }
    workflow["timeline"].append(record)
    state = workflow["step_states"][step["id"]]
    if checkpoint["phase"] == "pre":
        state["pre_analysis"] = record
    else:
        state["post_analysis"] = record
    if aggregate == "HOLD":
        workflow["status"] = "HOLD_PERSPECTIVE_CHECKPOINT"
    elif aggregate == "SPLIT":
        workflow["status"] = "SPLIT_REQUIRED"
    elif aggregate == "REPLAN":
        workflow["status"] = "REPLAN_REQUIRED"
    elif checkpoint["phase"] == "pre":
        workflow["status"] = "READY_TO_EXECUTE"
    else:
        state["status"] = "COMPLETE"
        workflow["completed_steps"].append(step["id"])
        workflow["cursor"] += 1
        if workflow["cursor"] >= len(workflow["plan"]["steps"]):
            workflow["status"] = "COMPLETE"
        else:
            workflow["status"] = "AWAITING_PRE_ANALYSIS"
    return _seal_workflow(workflow)


def _record_result(workflow: dict[str, Any], result: Any, evidence: Any, executor: Any) -> dict[str, Any]:
    if workflow["status"] != "READY_TO_EXECUTE":
        raise StepwiseWorkflowError("workflow is not ready to record a step result")
    step = _current_step(workflow)
    evidence_rows = _text_list(evidence, "evidence", maximum=32)
    executor_text = _required_text(executor, "executor", 400)
    try:
        result_digest = _digest(result)
    except (TypeError, ValueError) as exc:
        raise StepwiseWorkflowError("step result must be JSON-serializable") from exc
    record = {
        "type": "STEP_RESULT",
        "step_id": step["id"],
        "executor": executor_text,
        "result": copy.deepcopy(result),
        "result_digest": result_digest,
        "evidence": evidence_rows,
    }
    workflow["step_states"][step["id"]]["result"] = record
    workflow["step_states"][step["id"]]["status"] = "RESULT_RECORDED"
    workflow["timeline"].append(record)
    workflow["status"] = "AWAITING_POST_ANALYSIS"
    return _seal_workflow(workflow)


def record_step_result(raw_workflow: Any, result: Any, evidence: Any, *, executor: Any = "external-executor") -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    return _record_result(workflow, result, evidence, executor)


def execute_current_step(root: Path, raw_workflow: Any) -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    if workflow["status"] != "READY_TO_EXECUTE":
        raise StepwiseWorkflowError("workflow is not ready to execute the current step")
    step = _current_step(workflow)
    if step["mode"] != "action":
        raise StepwiseWorkflowError("analysis-only steps require an external recorded result rather than capability execution")
    action = step["action"]
    store = CapabilityStore(root)
    manifest = store.route(action["kind"])
    if manifest is None:
        workflow["status"] = "HOLD_NO_LIVE_STEP_ROUTE"
        workflow["timeline"].append({
            "type": "STEP_EXECUTION_HOLD",
            "step_id": step["id"],
            "reason": "no live capability routes the declared action kind",
            "action_kind": action["kind"],
        })
        return _seal_workflow(workflow)
    try:
        result = store.invoke(manifest, action.get("inputs", {}))
    except CapabilityError as exc:
        workflow["status"] = "HOLD_STEP_EXECUTION_ERROR"
        workflow["timeline"].append({
            "type": "STEP_EXECUTION_HOLD",
            "step_id": step["id"],
            "reason": str(exc),
            "details": exc.details,
            "capability": manifest.get("id"),
        })
        return _seal_workflow(workflow)
    return _record_result(
        workflow,
        result,
        [f"live capability {manifest.get('id')} returned this exact result", f"result digest {_digest(result)}"],
        f"live-capability:{manifest.get('id')}",
    )


def split_current_step(raw_workflow: Any, substeps: Any, *, reason: Any) -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    if workflow["status"] != "SPLIT_REQUIRED":
        raise StepwiseWorkflowError("current workflow state does not require a split")
    current = _current_step(workflow)
    next_depth = current["split_depth"] + 1
    if next_depth > MAX_SPLIT_DEPTH:
        workflow["status"] = "HOLD_MAX_SPLIT_DEPTH"
        return _seal_workflow(workflow)
    if not isinstance(substeps, list) or len(substeps) < 2:
        raise StepwiseWorkflowError("substeps must contain at least two smaller steps")
    if len(workflow["plan"]["steps"]) - 1 + len(substeps) > MAX_TOTAL_STEPS:
        raise StepwiseWorkflowError(f"split would exceed the {MAX_TOTAL_STEPS}-step total bound")
    normalized: list[dict[str, Any]] = []
    existing_ids = {row["id"] for row in workflow["plan"]["steps"] if row["id"] != current["id"]}
    previous_id: str | None = None
    for index, raw in enumerate(substeps):
        row = copy.deepcopy(raw)
        if not isinstance(row, dict):
            raise StepwiseWorkflowError(f"substeps[{index}] must be an object")
        if index == 0:
            row["depends_on"] = list(current["depends_on"])
        else:
            row["depends_on"] = [previous_id]
        row["split_depth"] = next_depth
        step = _normalize_step(row, index, inherited_depth=next_depth)
        if step["id"] in existing_ids or any(item["id"] == step["id"] for item in normalized):
            raise StepwiseWorkflowError("split step ids must be unique across the workflow", {"duplicate": step["id"]})
        normalized.append(step)
        previous_id = step["id"]
    assert previous_id is not None
    old_id = current["id"]
    cursor = workflow["cursor"]
    replacement_steps = workflow["plan"]["steps"][:cursor] + normalized + workflow["plan"]["steps"][cursor + 1:]
    for row in replacement_steps[cursor + len(normalized):]:
        row["depends_on"] = [previous_id if item == old_id else item for item in row["depends_on"]]
    new_plan = validate_step_plan({
        "schema": STEPWISE_PLAN_SCHEMA,
        "goal": workflow["goal"],
        "steps": replacement_steps,
        "planning_truth": workflow["plan"]["planning_truth"],
    }, expected_goal=workflow["goal"], maximum=MAX_TOTAL_STEPS)
    workflow["retired_steps"].append({
        "step": current,
        "state": workflow["step_states"].get(old_id),
        "reason": _required_text(reason, "reason", 2000),
        "replacement_ids": [row["id"] for row in normalized],
    })
    workflow["plan"] = new_plan
    workflow["step_states"].pop(old_id, None)
    for row in normalized:
        workflow["step_states"][row["id"]] = {"status": "PENDING", "pre_analysis": None, "result": None, "post_analysis": None}
    workflow["timeline"].append({
        "type": "STEP_SPLIT",
        "retired_step_id": old_id,
        "replacement_ids": [row["id"] for row in normalized],
        "split_depth": next_depth,
        "reason": _required_text(reason, "reason", 2000),
    })
    workflow["status"] = "AWAITING_PRE_ANALYSIS"
    return _seal_workflow(workflow)


def replan_remaining(raw_workflow: Any, replacement_steps: Any, *, reason: Any) -> dict[str, Any]:
    workflow = _verify_workflow(raw_workflow)
    if workflow["status"] != "REPLAN_REQUIRED":
        raise StepwiseWorkflowError("current workflow state does not require replanning")
    if not isinstance(replacement_steps, list) or not replacement_steps:
        raise StepwiseWorkflowError("replacement_steps must be a non-empty list")
    completed_prefix = workflow["plan"]["steps"][: workflow["cursor"]]
    new_plan = validate_step_plan({
        "schema": STEPWISE_PLAN_SCHEMA,
        "goal": workflow["goal"],
        "steps": completed_prefix + copy.deepcopy(replacement_steps),
        "planning_truth": f"remaining plan explicitly revised: {_required_text(reason, 'reason', 2000)}",
    }, expected_goal=workflow["goal"], maximum=MAX_TOTAL_STEPS)
    old_remaining = workflow["plan"]["steps"][workflow["cursor"]:]
    workflow["retired_steps"].append({
        "replanned_remaining_steps": old_remaining,
        "reason": _required_text(reason, "reason", 2000),
        "replacement_ids": [row["id"] for row in new_plan["steps"][workflow["cursor"]:]],
    })
    workflow["plan"] = new_plan
    completed = set(workflow["completed_steps"])
    workflow["step_states"] = {
        row["id"]: workflow["step_states"].get(row["id"], {"status": "PENDING", "pre_analysis": None, "result": None, "post_analysis": None})
        for row in new_plan["steps"]
        if row["id"] in completed or new_plan["steps"].index(row) >= workflow["cursor"]
    }
    workflow["timeline"].append({
        "type": "REPLAN_REMAINING",
        "reason": _required_text(reason, "reason", 2000),
        "new_remaining_ids": [row["id"] for row in new_plan["steps"][workflow["cursor"]:]],
    })
    workflow["status"] = "AWAITING_PRE_ANALYSIS"
    return _seal_workflow(workflow)


def run_instant_staged(
    root: Path,
    goal: Any,
    plan: Any,
    step_records: Any,
    *,
    selection_evidence: Any = "instant staged run selected plan",
    perspective_pool_size: int = 20,
    seed: str | None = None,
) -> dict[str, Any]:
    workflow = start_workflow(goal, plan, selection_evidence=selection_evidence)
    if not isinstance(step_records, list):
        raise StepwiseWorkflowError("step_records must be a list in plan order")
    expected_steps = [row["id"] for row in workflow["plan"]["steps"]]
    received_steps = [row.get("step_id") if isinstance(row, dict) else None for row in step_records]
    if received_steps != expected_steps:
        raise StepwiseWorkflowError("step_records must match the exact plan order", {"expected": expected_steps, "received": received_steps})
    for record in step_records:
        step_id = record["step_id"]
        pre = prepare_checkpoint(root, workflow, pool_size=perspective_pool_size, seed=f"{seed or ''}|{step_id}|pre")
        workflow = record_checkpoint_analysis(workflow, pre, record.get("pre_analyses"))
        if workflow["status"] != "READY_TO_EXECUTE":
            return workflow
        current = _current_step(workflow)
        if "result" in record:
            workflow = record_step_result(
                workflow,
                record.get("result"),
                record.get("evidence", ["explicit external result supplied for instant staged run"]),
                executor=record.get("executor", "external-executor"),
            )
        elif current["mode"] == "action":
            workflow = execute_current_step(root, workflow)
        else:
            raise StepwiseWorkflowError(f"analysis-only instant step {step_id} requires an explicit result")
        if workflow["status"] != "AWAITING_POST_ANALYSIS":
            return workflow
        post = prepare_checkpoint(root, workflow, pool_size=perspective_pool_size, seed=f"{seed or ''}|{step_id}|post")
        workflow = record_checkpoint_analysis(workflow, post, record.get("post_analyses"))
        if workflow["status"] not in {"AWAITING_PRE_ANALYSIS", "COMPLETE"}:
            return workflow
    return workflow


def stepwise_summary() -> dict[str, Any]:
    return {
        "truth_status": "EXPLICIT_MICROSTEP_WORKFLOW_WITH_PERSPECTIVE_CHECKPOINTS",
        "chronology": ["pre-analysis", "execution-or-result", "post-analysis", "advance"],
        "maximum_initial_steps": MAX_INITIAL_STEPS,
        "maximum_total_steps_after_splitting": MAX_TOTAL_STEPS,
        "maximum_split_depth": MAX_SPLIT_DEPTH,
        "perspective_panel": ["best-fit", "middle-fit", "lowest-third", "deterministic-random"],
        "instant_runs_preserve_logical_step_order": True,
        "semantic_reasoning_is_not_faked": True,
    }


def operate_stepwise_workflow(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "prepare")).strip().casefold()
    if operation in {"prepare", "prepare-workflow", "plan-tournament"}:
        return prepare_stepwise_workflow(
            root,
            inputs.get("goal"),
            request=inputs.get("request"),
            pool_size=int(inputs.get("pool_size", 32)),
            team_size=int(inputs.get("team_size", 4)),
            max_teams=int(inputs.get("max_teams", 64)),
            seed=inputs.get("seed"),
        )
    if operation in {"start", "start-workflow"}:
        return start_workflow(inputs.get("goal"), inputs.get("plan"), selection_evidence=inputs.get("selection_evidence", "explicitly selected plan"))
    if operation in {"checkpoint", "prepare-checkpoint"}:
        return prepare_checkpoint(root, inputs.get("workflow"), pool_size=int(inputs.get("pool_size", 20)), seed=inputs.get("seed"))
    if operation in {"record-analysis", "record-checkpoint"}:
        return record_checkpoint_analysis(inputs.get("workflow"), inputs.get("checkpoint"), inputs.get("analyses"))
    if operation in {"execute", "execute-step"}:
        return execute_current_step(root, inputs.get("workflow"))
    if operation in {"record-result", "result"}:
        return record_step_result(inputs.get("workflow"), inputs.get("result"), inputs.get("evidence"), executor=inputs.get("executor", "external-executor"))
    if operation in {"split", "split-step"}:
        return split_current_step(inputs.get("workflow"), inputs.get("substeps"), reason=inputs.get("reason"))
    if operation in {"replan", "replan-remaining"}:
        return replan_remaining(inputs.get("workflow"), inputs.get("replacement_steps"), reason=inputs.get("reason"))
    if operation in {"instant", "run-instant", "instant-staged"}:
        return run_instant_staged(
            root,
            inputs.get("goal"),
            inputs.get("plan"),
            inputs.get("step_records"),
            selection_evidence=inputs.get("selection_evidence", "instant staged run selected plan"),
            perspective_pool_size=int(inputs.get("perspective_pool_size", 20)),
            seed=inputs.get("seed"),
        )
    if operation in {"inspect", "summary"}:
        return stepwise_summary()
    raise StepwiseWorkflowError("unsupported stepwise workflow operation")

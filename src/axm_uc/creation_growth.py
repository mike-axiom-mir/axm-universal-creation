from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .gap_synthesis import GapSynthesisError, analyze_creation_gap
from .organ_gap import OrganGapError, explore_missing_organ_closure
from .organ_materialization import (
    OrganMaterializationError,
    census_organs,
    compile_organ_proposal,
)


CREATION_GROWTH_SCHEMA = "axm.creation-organ-growth/v0.1"
SUPPORTED_OPERATIONS = ("analyze", "prepare", "materialize-and-test")


class CreationGrowthError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def creation_growth_summary() -> dict[str, Any]:
    return {
        "truth_status": "BOUNDED_ORGAN_TO_CREATION_GROWTH_BRIDGE",
        "schema": CREATION_GROWTH_SCHEMA,
        "operations": list(SUPPORTED_OPERATIONS),
        "starts_from_creation_gap": True,
        "requires_exact_missing_interface_hold": True,
        "requires_explicit_organ_anatomy_and_package_source": True,
        "uses_415_organ_census": True,
        "compiles_with_organ_materialization_fabric": True,
        "tests_ephemeral_full_creation_closure": True,
        "automatic_source_invention": False,
        "automatic_install_registration_promotion_or_merge": False,
    }


def _digest(value: Any) -> str:
    return hashlib.sha256(
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    ).hexdigest()


def _required_text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise CreationGrowthError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise CreationGrowthError(f"{label} exceeds its {maximum}-character bound")
    return result


def _gap_context(root: Path, request: Any) -> tuple[dict[str, Any], dict[str, Any], str]:
    try:
        analysis = analyze_creation_gap(root, request)
    except GapSynthesisError as exc:
        raise CreationGrowthError(str(exc), exc.details) from exc
    if analysis["status"] != "HOLD_MISSING_ORGAN_INTERFACE":
        raise CreationGrowthError(
            "creation growth requires an observed missing executable-organ interface hold",
            {"gap_status": analysis["status"], "analysis": analysis},
        )
    candidates = analysis.get("composite_candidates", [])
    if len(candidates) != 1 or not isinstance(candidates[0].get("organ_discovery"), dict):
        raise CreationGrowthError("creation gap does not expose one exact organ-discovery hold")
    discovery = candidates[0]["organ_discovery"]
    missing = discovery.get("missing_interfaces")
    if not isinstance(missing, list) or len(missing) != 1 or not isinstance(missing[0], str):
        raise CreationGrowthError(
            "this bounded bridge handles exactly one missing interface at a time",
            {"missing_interfaces": missing},
        )
    return analysis, discovery, missing[0]


def _linked_plan(root: Path, request: Any, anatomy_id: Any, package: Any) -> dict[str, Any]:
    analysis, discovery, missing_interface = _gap_context(root, request)
    selected_id = _required_text(anatomy_id, "anatomy_id", maximum=240)
    try:
        census = census_organs(root, anatomy_id=selected_id, limit=1)
        proposal = compile_organ_proposal(root, selected_id, package)
    except OrganMaterializationError as exc:
        raise CreationGrowthError(str(exc), exc.details) from exc
    provides = proposal["contracts"]["provides"]
    if missing_interface not in provides:
        raise CreationGrowthError(
            "supplied organ package does not provide the exact observed missing interface",
            {"missing_interface": missing_interface, "package_provides": provides},
        )
    plan = {
        "schema": CREATION_GROWTH_SCHEMA,
        "truth_status": "EXPLICIT_ORGAN_LINKED_TO_OBSERVED_CREATION_GAP",
        "request": copy.deepcopy(analysis["request"]),
        "request_digest": analysis["request_digest"],
        "gap_analysis_digest": analysis["analysis_digest"],
        "gap_status": analysis["status"],
        "missing_interface": missing_interface,
        "organ_goal": copy.deepcopy(discovery["goal"]),
        "anatomy_id": selected_id,
        "anatomy_materialization_before": copy.deepcopy(census["organs"][0]["materialization"]),
        "package_ref": f"{proposal['id']}@{proposal['version']}",
        "package_provides": copy.deepcopy(provides),
        "package_requires": copy.deepcopy(proposal["contracts"]["requires"]),
        "proposal": proposal,
        "proposal_digest": _digest(proposal),
        "selection_authority": "CALLER_EXPLICIT",
        "source_invented": False,
        "live_machine_body_modified": False,
        "candidate_installed": False,
        "candidate_registered": False,
        "candidate_promoted": False,
        "candidate_merged": False,
    }
    return {**plan, "plan_digest": _digest(plan)}


def operate_creation_growth(root: Path, inputs: Any) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise CreationGrowthError("creation growth inputs must be an object")
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    if operation not in SUPPORTED_OPERATIONS:
        raise CreationGrowthError(
            "unsupported creation growth operation",
            {"operation": operation, "supported_operations": list(SUPPORTED_OPERATIONS)},
        )
    allowed = {
        "analyze": {"operation", "request"},
        "prepare": {"operation", "request", "anatomy_id", "package"},
        "materialize-and-test": {
            "operation", "request", "anatomy_id", "package", "path", "checks", "replace"
        },
    }[operation]
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise CreationGrowthError(
            "creation growth inputs contain unsupported fields",
            {"operation": operation, "unexpected_fields": unexpected},
        )
    if "request" not in inputs:
        raise CreationGrowthError("creation growth requires request")
    if operation == "analyze":
        analysis, discovery, missing_interface = _gap_context(root, inputs["request"])
        return {
            "operation": "analyze",
            "schema": CREATION_GROWTH_SCHEMA,
            "truth_status": "OBSERVED_CREATION_GAP_READY_FOR_EXPLICIT_ORGAN_SOURCE",
            "analysis": analysis,
            "missing_interface": missing_interface,
            "missing_unit_contracts": copy.deepcopy(discovery["missing_unit_contracts"]),
            "source_invented": False,
            "live_machine_body_modified": False,
            "next_operation": "prepare",
        }
    missing = sorted(field for field in ("anatomy_id", "package") if field not in inputs)
    if missing:
        raise CreationGrowthError("creation growth is missing explicit organ inputs", {"missing_fields": missing})
    plan = _linked_plan(root, inputs["request"], inputs["anatomy_id"], inputs["package"])
    if operation == "prepare":
        return {
            "operation": "prepare",
            **plan,
            "materialized": False,
            "tested": False,
            "next_operation": "materialize-and-test",
        }
    if "path" not in inputs:
        raise CreationGrowthError("materialize-and-test requires a detached candidate path")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise CreationGrowthError("replace must be a boolean")
    if "checks" in inputs and not isinstance(inputs["checks"], list):
        raise CreationGrowthError("checks must be a list")
    target = Path(_required_text(inputs["path"], "path", maximum=1000))
    try:
        closure = explore_missing_organ_closure(
            root=root,
            target=target,
            raw_goal=plan["organ_goal"],
            raw_proposal=plan["proposal"],
            checks=inputs.get("checks"),
            replace=inputs.get("replace", False),
        )
    except (OrganGapError, OrganMaterializationError) as exc:
        raise CreationGrowthError(str(exc), getattr(exc, "details", {})) from exc
    passed = closure.get("passed") is True
    return {
        "operation": "materialize-and-test",
        **plan,
        "status": "TESTED_CREATION_GROWTH_CANDIDATE" if passed else "HELD_CREATION_GROWTH_CANDIDATE",
        "truth_status": (
            "OBSERVED_EXPLICIT_ORGAN_CLOSES_ONE_CREATION_GAP"
            if passed
            else "OBSERVED_EXPLICIT_ORGAN_DID_NOT_CLOSE_CREATION_GAP"
        ),
        "passed": passed,
        "path": str(target.resolve()),
        "closure": closure,
        "materialized": True,
        "tested": True,
        "generic_compose_capability_expansion_observed_in_ephemeral_space": passed,
        "live_route_after_test": None,
        "candidate_installed": False,
        "candidate_registered": False,
        "candidate_promoted": False,
        "candidate_merged": False,
        "live_machine_body_modified": False,
        "next_decision": (
            "inspect the exact detached evidence and separately decide whether to adopt the organ"
            if passed
            else "repair or replace the explicit organ source without changing the live machine"
        ),
        "limitations": [
            "one passing request-shaped closure does not prove universal semantic interface conformance",
            "the candidate remains detached; descriptive anatomy, candidate materialization, installation, registration, promotion, merge, and CANON remain separate states",
            "runtime, browser, visual, accessibility, and host behavior require separate evidence",
        ],
    }

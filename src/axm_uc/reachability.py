from __future__ import annotations

import copy
from typing import Any


REACHABILITY_SCHEMA = "axm.state-direction-reachability/v0.1"
CURRENT_PATH_AVAILABLE = "CURRENT_PATH_AVAILABLE"
PATH_UNKNOWN_CURRENTLY = "PATH_UNKNOWN_CURRENTLY"
BLOCKED_BY_CURRENT_CONSTRAINT = "BLOCKED_BY_CURRENT_CONSTRAINT"


def state_direction_summary() -> dict[str, Any]:
    """Describe the machine's bounded reachability language without claiming universality."""
    return {
        "schema": REACHABILITY_SCHEMA,
        "principle": "do not encode current ignorance as fundamental impossibility",
        "claim_scope": "current machine state, observed evidence, and currently known transition graph",
        "statuses": [
            CURRENT_PATH_AVAILABLE,
            PATH_UNKNOWN_CURRENTLY,
            BLOCKED_BY_CURRENT_CONSTRAINT,
        ],
        "orientation": [
            "preserve the requested direction while a path is unknown",
            "represent the smallest currently observed missing transition or constraint",
            "permit bounded construction or experiment to discover a new valid path",
            "verify any newly constructed path before treating it as capability",
            "never convert a missing path into automatic permission, admission, promotion, merge, or canon",
        ],
        "prompt_relation": {
            "role": "high-level state-direction source",
            "may_compile_into": [
                "explicit constraints",
                "structured target properties",
                "state representations",
                "candidate transition rules",
                "verification criteria",
            ],
            "not_claimed": "natural-language prompt text is literal processor machine code",
        },
    }


def frame_state_direction(
    request: dict[str, Any],
    *,
    route_available: bool,
    current_constraint: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Frame one request as target direction plus current reachability evidence.

    This function deliberately says only what the current machine can justify. A
    missing route means that the current transition graph has no known path; it
    does not prove that no path can ever be constructed.
    """
    if not isinstance(request, dict):
        raise TypeError("request must be an object")

    kind = request.get("kind")
    if not isinstance(kind, str) or not kind.strip():
        raise ValueError("request.kind must be a non-empty string")

    direction_source = "kind"
    direction: Any = kind
    if isinstance(request.get("direction"), str) and request["direction"].strip():
        direction_source = "direction"
        direction = request["direction"].strip()
    elif isinstance(request.get("purpose"), str) and request["purpose"].strip():
        direction_source = "purpose"
        direction = request["purpose"].strip()

    constraints = request.get("constraints")
    if not isinstance(constraints, dict):
        constraints = {}
    inputs = request.get("inputs")
    if not isinstance(inputs, dict):
        inputs = {}

    if route_available:
        status = CURRENT_PATH_AVAILABLE
    elif current_constraint:
        status = BLOCKED_BY_CURRENT_CONSTRAINT
    else:
        status = PATH_UNKNOWN_CURRENTLY

    return {
        "schema": REACHABILITY_SCHEMA,
        "target_direction": {
            "source": direction_source,
            "value": direction,
            "request_kind": kind.strip(),
            "explicit_constraints": copy.deepcopy(constraints),
            "supplied_input_keys": sorted(str(key) for key in inputs),
        },
        "current_reachability": {
            "status": status,
            "claim_scope": "current machine state and currently known transition graph",
            "observed_constraint": copy.deepcopy(current_constraint),
            "does_not_claim": [
                "fundamental impossibility",
                "global unreachability",
                "that the current transition graph is complete",
            ],
        },
        "construction_orientation": {
            "when_path_unknown": [
                "keep the target direction explicit",
                "identify the smallest currently justified missing transition",
                "reuse existing machinery before inventing new machinery",
                "construct or test bounded intermediate machinery when justified",
                "verify the resulting path and preserve the truth boundary",
            ],
            "failure_is_evidence": "friction can identify missing knowledge, representation, resource, constraint handling, or transition machinery without proving impossibility",
        },
        "prompt_relation": state_direction_summary()["prompt_relation"],
        "authority_boundary": {
            "path_discovery_is_permission": False,
            "capability_is_permission": False,
            "automatic_admission": False,
            "automatic_promotion": False,
            "automatic_merge": False,
            "automatic_canon": False,
        },
    }

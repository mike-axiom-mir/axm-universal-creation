from __future__ import annotations

from typing import Any

ROOTS = ("truth", "agency", "continuity", "wisdom-before-speed")


def evaluate_declared_root_fit(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate the candidate's inspectable v0 root-fit declaration.

    This is deliberately not a hidden classifier or score. The declaration and
    its basis remain visible in the candidate manifest.
    """
    declaration = candidate.get("root_fit")
    if not isinstance(declaration, dict):
        return {
            "fit": False,
            "truth_status": "DECLARED_ROOT_FIT_STRUCTURE_INVALID",
            "reason": "missing root_fit declaration",
            "roots": {},
            "independent_semantic_judgment_performed": False,
        }

    checked: dict[str, Any] = {}
    overall = True
    for root in ROOTS:
        item = declaration.get(root)
        valid = (
            isinstance(item, dict)
            and item.get("fit") is True
            and isinstance(item.get("basis"), str)
            and bool(item["basis"].strip())
        )
        checked[root] = {
            "fit": bool(valid),
            "basis": item.get("basis") if isinstance(item, dict) else None,
        }
        overall = overall and valid
    return {
        "fit": overall,
        "truth_status": (
            "POSITIVE_ROOT_FIT_DECLARATION_STRUCTURALLY_VALID"
            if overall
            else "DECLARED_ROOT_FIT_STRUCTURE_INVALID"
        ),
        "reason": (
            "all four roots have a positive inspectable declaration; semantic correctness was not independently judged"
            if overall
            else "one or more roots do not have a positive inspectable declaration"
        ),
        "roots": checked,
        "independent_semantic_judgment_performed": False,
        "meaning": "structure and explicit basis validation only; a positive declaration is not objective proof that the change fits the roots",
    }


def evaluate_root_fit_decision(raw: Any) -> dict[str, Any]:
    """Validate an attributed current-machine root-fit decision envelope.

    The decision remains human/model/rule supplied. This function checks that
    an accountable source and exact four-root basis exist; it does not invent
    or silently upgrade the decision into objective moral proof.
    """
    if not isinstance(raw, dict):
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit decision must be an object",
            "independent_semantic_judgment_performed": False,
        }
    unexpected = sorted(set(raw) - {"decision_source", "decided_by", "evidence_refs", "roots"})
    if unexpected:
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit decision contains unsupported fields",
            "unexpected_fields": unexpected,
            "independent_semantic_judgment_performed": False,
        }
    source = raw.get("decision_source")
    decided_by = raw.get("decided_by")
    roots = raw.get("roots")
    refs = raw.get("evidence_refs", [])
    if not isinstance(source, str) or not source.strip():
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit decision_source must be non-empty text",
            "independent_semantic_judgment_performed": False,
        }
    if not isinstance(decided_by, str) or not decided_by.strip():
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit decided_by must be non-empty text",
            "independent_semantic_judgment_performed": False,
        }
    if not isinstance(refs, list) or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit evidence_refs must be a list of non-empty text",
            "independent_semantic_judgment_performed": False,
        }
    if not isinstance(roots, dict) or set(roots) != set(ROOTS):
        return {
            "fit": False,
            "truth_status": "ROOT_FIT_DECISION_ENVELOPE_INVALID",
            "reason": "root-fit roots must contain exactly Truth, Agency, Continuity, and Wisdom Before Speed",
            "expected_roots": list(ROOTS),
            "received_roots": sorted(roots) if isinstance(roots, dict) else None,
            "independent_semantic_judgment_performed": False,
        }
    evaluated = evaluate_declared_root_fit({"root_fit": roots})
    return {
        **evaluated,
        "truth_status": (
            "ATTRIBUTED_POSITIVE_ROOT_FIT_DECISION_STRUCTURALLY_VALID"
            if evaluated.get("fit") is True
            else "ATTRIBUTED_ROOT_FIT_DECISION_INVALID"
        ),
        "decision_source": source.strip(),
        "decided_by": decided_by.strip(),
        "evidence_refs": [ref.strip() for ref in refs],
        "decision_is_objective_proof": False,
    }

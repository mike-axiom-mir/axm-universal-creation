from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from .core import (
    Candidate,
    Claim,
    CommunicationKind,
    ProposalMap,
    ProposalStatus,
    Ref,
    Relation,
)


def _sorted_unique_refs(refs: Iterable[Ref]) -> tuple[Ref, ...]:
    by_key: dict[str, Ref] = {}
    for ref in refs:
        by_key[ref.key] = ref
    return tuple(by_key[key] for key in sorted(by_key))


def _require_unique_refs(refs: tuple[Ref, ...], name: str) -> tuple[Ref, ...]:
    ordered = _sorted_unique_refs(refs)
    if len(ordered) != len(refs):
        raise ValueError(f"{name} must contain unique references")
    return ordered


@dataclass(frozen=True)
class CriterionObservation:
    """One explicit grounded evaluation of one required success criterion."""

    criterion: Ref
    observation: Ref
    satisfied: bool
    evidence: tuple[Ref, ...]

    def __post_init__(self) -> None:
        if not isinstance(self.satisfied, bool):
            raise ValueError("CriterionObservation.satisfied must be a boolean")
        if not self.evidence:
            raise ValueError("CriterionObservation.evidence must contain at least one reference")
        _require_unique_refs(self.evidence, "CriterionObservation.evidence")


def produce_criterion_outcome(
    *,
    event_id: str,
    source: Ref,
    activity: Ref,
    attempt: Ref,
    attempt_evidence: tuple[Ref, ...],
    criteria_contract: Ref,
    required_criteria: tuple[Ref, ...],
    criteria_evidence: tuple[Ref, ...],
    observations: tuple[CriterionObservation, ...],
    next_operations: tuple[str, ...] = ("inspect", "compare"),
) -> Candidate | None:
    """Evaluate one attempt against one explicit all-required success contract.

    v0.1 supports exactly one aggregation rule: every explicitly required criterion must
    be satisfied for success. One grounded failed criterion is therefore sufficient to
    establish failure relative to that contract, even if other criteria are not yet
    evaluated. Partial all-positive evidence remains silence rather than premature success.

    The producer treats the supplied criteria contract as the evaluation basis. It does
    not authenticate who authored that contract or independently verify that it existed
    before the attempt/evaluation occurred.
    """

    if not event_id.strip():
        raise ValueError("event_id must be non-empty")
    if not required_criteria:
        raise ValueError("required_criteria must contain at least one reference")
    if not attempt_evidence:
        raise ValueError("attempt_evidence must contain at least one reference")
    if not criteria_evidence:
        raise ValueError("criteria_evidence must contain at least one reference")
    if any(not operation.strip() for operation in next_operations):
        raise ValueError("next_operations may not contain empty operations")
    if len(set(next_operations)) != len(next_operations):
        raise ValueError("next_operations must be unique")

    required = _require_unique_refs(required_criteria, "required_criteria")
    attempt_evidence_sorted = _require_unique_refs(attempt_evidence, "attempt_evidence")
    criteria_evidence_sorted = _require_unique_refs(criteria_evidence, "criteria_evidence")

    observation_refs = [item.observation.key for item in observations]
    if len(set(observation_refs)) != len(observation_refs):
        raise ValueError("observations must have unique observation references")
    criterion_refs = [item.criterion.key for item in observations]
    if len(set(criterion_refs)) != len(criterion_refs):
        raise ValueError("observations may evaluate each criterion at most once")

    required_by_key = {ref.key: ref for ref in required}
    for item in observations:
        if item.criterion.key not in required_by_key:
            raise ValueError(
                f"observation references undeclared criterion: {item.criterion.key}"
            )

    observed_by_criterion = {item.criterion.key: item for item in observations}
    failed = tuple(
        item
        for item in sorted(observations, key=lambda value: value.criterion.key)
        if not item.satisfied
    )

    if failed:
        kind = CommunicationKind.FAILURE
        relevant_observations = failed
        failed_criteria = tuple(item.criterion for item in failed)
        claim_predicate = "attempt_fails_explicit_all_required_success_contract"
        claim_value = {
            "aggregation_rule": "all_required",
            "criteria_contract": criteria_contract.key,
            "required_criteria": [ref.key for ref in required],
            "failed_criteria": [ref.key for ref in failed_criteria],
            "global_failure_claimed": False,
            "all_other_criteria_required_for_failure_claim": False,
            "criteria_contract_authenticity_claimed": False,
            "criteria_contract_preexistence_authenticated": False,
        }
    else:
        if len(observed_by_criterion) != len(required):
            return None
        # Every required criterion is represented exactly once and no observation failed.
        kind = CommunicationKind.SUCCESS
        relevant_observations = tuple(
            observed_by_criterion[ref.key]
            for ref in required
        )
        claim_predicate = "attempt_satisfies_explicit_all_required_success_contract"
        claim_value = {
            "aggregation_rule": "all_required",
            "criteria_contract": criteria_contract.key,
            "required_criteria": [ref.key for ref in required],
            "satisfied_criteria": [ref.key for ref in required],
            "global_success_claimed": False,
            "criteria_contract_authenticity_claimed": False,
            "criteria_contract_preexistence_authenticated": False,
        }

    relevant_observations = tuple(
        sorted(relevant_observations, key=lambda value: value.criterion.key)
    )
    observation_evidence = _sorted_unique_refs(
        ref
        for item in relevant_observations
        for ref in item.evidence
    )
    evidence = _sorted_unique_refs(
        (*attempt_evidence_sorted, *criteria_evidence_sorted, *observation_evidence)
    )

    nodes = _sorted_unique_refs(
        (
            attempt,
            criteria_contract,
            *required,
            *(item.observation for item in relevant_observations),
            *evidence,
        )
    )

    relations: list[Relation] = [Relation(attempt, "evaluated_against", criteria_contract)]
    relations.extend(
        Relation(criteria_contract, "requires_success_criterion", criterion)
        for criterion in required
    )
    relations.extend(
        Relation(attempt, "supported_by", ref)
        for ref in attempt_evidence_sorted
    )
    relations.extend(
        Relation(criteria_contract, "supported_by", ref)
        for ref in criteria_evidence_sorted
    )
    for item in relevant_observations:
        relations.append(Relation(item.observation, "outcome_for_attempt", attempt))
        relations.append(
            Relation(
                item.observation,
                "satisfies_criterion" if item.satisfied else "fails_criterion",
                item.criterion,
            )
        )
        relations.extend(
            Relation(item.observation, "supported_by", ref)
            for ref in _sorted_unique_refs(item.evidence)
        )

    if kind is CommunicationKind.SUCCESS:
        truth_note = (
            "The supplied attempt has grounded satisfied observations for every criterion in the supplied all-required "
            "success contract. This establishes success only relative to that contract; it does not claim universal "
            "success, absence of side effects, contract authenticity, or independently verified contract timing."
        )
        selection = "all explicit required criteria grounded satisfied"
    else:
        truth_note = (
            "At least one explicit required criterion in the supplied all-required success contract has a grounded "
            "failed observation. This establishes failure relative to that contract even if other criteria remain "
            "unevaluated; it does not claim universal failure, worthlessness, contract authenticity, or independently "
            "verified contract timing."
        )
        selection = "all grounded failed explicit required criteria sorted by Ref.key"

    return Candidate(
        event_id=event_id,
        kind=kind,
        source=source,
        subjects=(attempt,),
        claim=Claim(
            claim_predicate,
            (attempt, criteria_contract, *(item.criterion for item in relevant_observations)),
            claim_value,
        ),
        evidence=evidence,
        relevance=(activity,),
        next_operations=next_operations,
        proposal_map=ProposalMap(
            nodes=nodes,
            relations=tuple(relations),
            status=ProposalStatus.GROUNDED,
        ),
        metadata={
            "producer": "criterion-outcome/0.1",
            "selection": selection,
            "truth_note": truth_note,
        },
    )

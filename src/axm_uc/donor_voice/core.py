from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from hashlib import sha256
import json
from pathlib import Path
from typing import Any, Mapping


PROTOCOL_VERSION = "0.1"


class CommunicationKind(str, Enum):
    NOTICE = "notice"
    CONFLICT = "conflict"
    ALTERNATIVE = "alternative"
    UNRESOLVED = "unresolved"
    NEED = "need"
    REPEAT = "repeat"
    NOVEL = "novel"
    SUCCESS = "success"
    FAILURE = "failure"
    LOOK = "look"


class ProposalStatus(str, Enum):
    DISCOVERED = "discovered"
    GROUNDED = "grounded"
    UNTESTED = "untested"
    TESTABLE = "testable"
    TESTING = "testing"
    SUPPORTED = "supported"
    CONTRADICTED = "contradicted"
    REJECTED = "rejected"
    ADOPTED = "adopted"


@dataclass(frozen=True, order=True)
class Ref:
    """Open reference into a state-capable world.

    `kind` is deliberately open rather than a closed enum so future capabilities can
    reference object types this experiment did not anticipate.
    """

    kind: str
    id: str

    def __post_init__(self) -> None:
        if not self.kind.strip():
            raise ValueError("Ref.kind must be non-empty")
        if not self.id.strip():
            raise ValueError("Ref.id must be non-empty")

    @property
    def key(self) -> str:
        return f"{self.kind}:{self.id}"


@dataclass(frozen=True)
class Relation:
    source: Ref
    predicate: str
    target: Ref

    def __post_init__(self) -> None:
        if not self.predicate.strip():
            raise ValueError("Relation.predicate must be non-empty")


@dataclass(frozen=True)
class Claim:
    """Machine-readable claim. Human prose is intentionally absent."""

    predicate: str
    arguments: tuple[Ref, ...]
    value: Any = None

    def __post_init__(self) -> None:
        if not self.predicate.strip():
            raise ValueError("Claim.predicate must be non-empty")
        if not self.arguments:
            raise ValueError("Claim.arguments must contain at least one reference")


@dataclass(frozen=True)
class ProposalMap:
    nodes: tuple[Ref, ...] = ()
    relations: tuple[Relation, ...] = ()
    status: ProposalStatus = ProposalStatus.UNTESTED

    def validate(self) -> None:
        node_keys = {node.key for node in self.nodes}
        for relation in self.relations:
            if relation.source.key not in node_keys or relation.target.key not in node_keys:
                raise ValueError("Every relation endpoint must exist in ProposalMap.nodes")


@dataclass(frozen=True)
class Candidate:
    """A grounded candidate presented to the communication gate.

    This object is not itself communication. It becomes communication only if the
    deterministic gate accepts it.
    """

    event_id: str
    kind: CommunicationKind
    source: Ref
    subjects: tuple[Ref, ...]
    claim: Claim
    evidence: tuple[Ref, ...]
    relevance: tuple[Ref, ...]
    next_operations: tuple[str, ...]
    proposal_map: ProposalMap | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.event_id.strip():
            raise ValueError("Candidate.event_id must be non-empty")
        if any(not operation.strip() for operation in self.next_operations):
            raise ValueError("Candidate.next_operations may not contain empty operations")
        if self.proposal_map is not None:
            self.proposal_map.validate()


@dataclass(frozen=True)
class GateContext:
    active_refs: tuple[Ref, ...]
    seen_fingerprints: frozenset[str] = frozenset()


@dataclass(frozen=True)
class GateDecision:
    eligible: bool
    reasons: tuple[str, ...]
    fingerprint: str


@dataclass(frozen=True)
class StateTalkPacket:
    version: str
    event_id: str
    kind: CommunicationKind
    source: Ref
    subjects: tuple[Ref, ...]
    claim: Claim
    evidence: tuple[Ref, ...]
    relevance: tuple[Ref, ...]
    next_operations: tuple[str, ...]
    fingerprint: str
    proposal_map: ProposalMap | None = None
    metadata: Mapping[str, Any] = field(default_factory=dict)


FLOORVOICE = {
    CommunicationKind.NOTICE: "I noticed something.",
    CommunicationKind.CONFLICT: "These do not fit.",
    CommunicationKind.ALTERNATIVE: "There is another way.",
    CommunicationKind.UNRESOLVED: "I cannot resolve this.",
    CommunicationKind.NEED: "I need something.",
    CommunicationKind.REPEAT: "This happened before.",
    CommunicationKind.NOVEL: "This is new.",
    CommunicationKind.SUCCESS: "This worked.",
    CommunicationKind.FAILURE: "This did not work.",
    CommunicationKind.LOOK: "Look here.",
}


def _normalise(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Ref):
        return {"kind": value.kind, "id": value.id}
    if isinstance(value, Relation):
        return {
            "source": _normalise(value.source),
            "predicate": value.predicate,
            "target": _normalise(value.target),
        }
    if isinstance(value, Claim):
        return {
            "predicate": value.predicate,
            "arguments": [_normalise(v) for v in value.arguments],
            "value": _normalise(value.value),
        }
    if isinstance(value, ProposalMap):
        return {
            "nodes": [_normalise(v) for v in value.nodes],
            "relations": [_normalise(v) for v in value.relations],
            "status": value.status.value,
        }
    if isinstance(value, StateTalkPacket):
        return {
            "version": value.version,
            "event_id": value.event_id,
            "kind": value.kind.value,
            "source": _normalise(value.source),
            "subjects": [_normalise(v) for v in value.subjects],
            "claim": _normalise(value.claim),
            "evidence": [_normalise(v) for v in value.evidence],
            "relevance": [_normalise(v) for v in value.relevance],
            "next_operations": list(value.next_operations),
            "fingerprint": value.fingerprint,
            "proposal_map": _normalise(value.proposal_map),
            "metadata": _normalise(dict(value.metadata)),
        }
    if isinstance(value, Candidate):
        return {
            "kind": value.kind.value,
            "source": _normalise(value.source),
            "subjects": [_normalise(v) for v in value.subjects],
            "claim": _normalise(value.claim),
            "evidence": [_normalise(v) for v in value.evidence],
            "relevance": [_normalise(v) for v in value.relevance],
            "next_operations": list(value.next_operations),
            "proposal_map": _normalise(value.proposal_map),
        }
    if isinstance(value, Mapping):
        return {str(k): _normalise(v) for k, v in sorted(value.items(), key=lambda item: str(item[0]))}
    if isinstance(value, (tuple, list)):
        return [_normalise(v) for v in value]
    if isinstance(value, set):
        return sorted(_normalise(v) for v in value)
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def semantic_fingerprint(candidate: Candidate) -> str:
    """Fingerprint semantic content, intentionally excluding event_id and metadata."""

    return sha256(canonical_json(candidate).encode("utf-8")).hexdigest()


def evaluate(candidate: Candidate, context: GateContext) -> GateDecision:
    """Apply deterministic eligibility rules.

    Eligibility currently requires:
    - at least one subject;
    - at least one evidence reference;
    - at least one relevance reference shared with the active collaborative context;
    - at least one explicit next operation;
    - semantic content not previously emitted.

    This is intentionally conservative. The gate does not decide whether a proposal
    is true; it decides whether there is enough grounded structure to surface it.
    """

    fingerprint = semantic_fingerprint(candidate)
    reasons: list[str] = []

    if not candidate.subjects:
        reasons.append("missing_subject")
    if not candidate.evidence:
        reasons.append("missing_evidence")
    active = {ref.key for ref in context.active_refs}
    relevant = {ref.key for ref in candidate.relevance}
    if not active.intersection(relevant):
        reasons.append("not_relevant_to_active_context")
    if not candidate.next_operations:
        reasons.append("no_next_operation")
    if fingerprint in context.seen_fingerprints:
        reasons.append("duplicate_semantic_event")

    return GateDecision(eligible=not reasons, reasons=tuple(reasons), fingerprint=fingerprint)


def emit(candidate: Candidate, decision: GateDecision) -> StateTalkPacket:
    if not decision.eligible:
        raise ValueError(f"Cannot emit an ineligible candidate: {decision.reasons}")
    expected = semantic_fingerprint(candidate)
    if decision.fingerprint != expected:
        raise ValueError("GateDecision fingerprint does not match Candidate")
    return StateTalkPacket(
        version=PROTOCOL_VERSION,
        event_id=candidate.event_id,
        kind=candidate.kind,
        source=candidate.source,
        subjects=candidate.subjects,
        claim=candidate.claim,
        evidence=candidate.evidence,
        relevance=candidate.relevance,
        next_operations=candidate.next_operations,
        fingerprint=decision.fingerprint,
        proposal_map=candidate.proposal_map,
        metadata=dict(candidate.metadata),
    )


def render_floorvoice(packet: StateTalkPacket) -> str:
    """Return a fixed phrase only.

    No claim details, names, values, or generated language enter the phrase. Humans
    must inspect the packet / proposal map for meaning and evidence.
    """

    return FLOORVOICE[packet.kind]


def packet_dict(packet: StateTalkPacket) -> dict[str, Any]:
    return _normalise(packet)


class JsonlEventLog:
    """Append-only local record of emitted events and later observations."""

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def append(self, packet: StateTalkPacket, *, human_phrase: str, observation: Mapping[str, Any] | None = None) -> None:
        record = {
            "packet": packet_dict(packet),
            "human_phrase": human_phrase,
            "observation": dict(observation or {}),
        }
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as handle:
            handle.write(canonical_json(record) + "\n")

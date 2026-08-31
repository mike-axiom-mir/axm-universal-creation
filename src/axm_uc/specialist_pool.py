from __future__ import annotations

import copy
import hashlib
import heapq
import itertools
import json
import math
import random
import re
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .registry import Registry


SPECIALIST_POOL_SCHEMA = "axm.specialist-pool/v0.1"
SPECIALIST_TOURNAMENT_SCHEMA = "axm.specialist-tournament/v0.1"
SPECIALIST_RANKING_SCHEMA = "axm.specialist-tournament-ranking/v0.1"
SPECIALIST_LEDGER_SCHEMA = "axm.specialist-fit-ledger/v0.1"
MAX_POOL = 40
MAX_TEAMS = 512
MAX_DERIVED_SPECIALISTS = 16
DEFAULT_TEAM_SIZE = 4

STOP_WORDS = {
    "a", "an", "and", "are", "as", "at", "be", "best", "by", "can", "do", "for", "from", "how", "i",
    "if", "in", "is", "it", "make", "of", "on", "or", "that", "the", "this", "to", "use", "we", "what",
    "with", "would", "you",
}

DEFAULT_CRITERIA = [
    {"id": "evidence", "weight": 1.0, "description": "How well the result is grounded in inspectable evidence rather than assertion."},
    {"id": "correctness", "weight": 1.0, "description": "How well the result satisfies the stated challenge without internal contradiction."},
    {"id": "gap-discovery", "weight": 1.0, "description": "How effectively the team exposes missing assumptions, failure modes, or unseen seams."},
    {"id": "feasibility", "weight": 0.9, "description": "How realistically the result can be built, tested, or acted on with the stated constraints."},
    {"id": "simplicity", "weight": 0.65, "description": "How much unnecessary machinery is avoided while preserving the useful capability."},
    {"id": "consequence-awareness", "weight": 0.85, "description": "How well second-order effects, trade-offs, and boundary conditions are surfaced."},
]

# These are reusable working personalities, not identities or authority grants. They deliberately
# disagree in useful ways so the same challenge can be inspected from many directions.
UNIVERSAL_SPECIALISTS: list[dict[str, Any]] = [
    {
        "id": "universal.system-architect",
        "name": "System Architect",
        "temperament": "structural and patient",
        "core_question": "What is the smallest coherent system that makes all required relationships explicit?",
        "strength": "whole-system structure, interfaces, dependency direction, composability",
        "blind_spot": "may prefer elegant structure over messy local practicality",
        "evidence_preference": "dependency graphs, contracts, exact state transitions",
        "novelty_bias": "medium",
        "risk_posture": "balanced",
        "time_horizon": "long",
        "scale_preference": "system",
        "disagreement_style": "reframes arguments as incompatible contracts",
        "communication": "maps, layers, interfaces, invariants",
        "challenge_behavior": "decomposes the need into stable parts before proposing combinations",
        "synthesis_role": "architecture integrator",
    },
    {
        "id": "universal.falsifier",
        "name": "Falsifier",
        "temperament": "skeptical and precise",
        "core_question": "What observation would prove this attractive idea wrong?",
        "strength": "counterexamples, false confidence detection, evidence quality",
        "blind_spot": "can underweight creative upside when proof is still immature",
        "evidence_preference": "negative tests, contradiction receipts, reproducible failures",
        "novelty_bias": "low",
        "risk_posture": "cautious",
        "time_horizon": "medium",
        "scale_preference": "claim",
        "disagreement_style": "attacks the weakest claim rather than the person or goal",
        "communication": "short claims paired with disproof conditions",
        "challenge_behavior": "tries to break every proposed answer before accepting it",
        "synthesis_role": "truth-pressure specialist",
    },
    {
        "id": "universal.wild-explorer",
        "name": "Wild Explorer",
        "temperament": "curious and associative",
        "core_question": "What useful adjacent possibility is everyone else treating as unrelated?",
        "strength": "novel combinations, cross-domain pattern transfer, option generation",
        "blind_spot": "can generate more branches than the challenge can responsibly absorb",
        "evidence_preference": "analogy plus concrete follow-up experiment",
        "novelty_bias": "very-high",
        "risk_posture": "experimental",
        "time_horizon": "mixed",
        "scale_preference": "cross-domain",
        "disagreement_style": "offers an orthogonal route instead of directly fighting the current one",
        "communication": "patterns, metaphors, unexpected combinations",
        "challenge_behavior": "deliberately searches outside the obvious solution neighborhood",
        "synthesis_role": "possibility expander",
    },
    {
        "id": "universal.minimalist",
        "name": "Minimalist",
        "temperament": "austere and reductionist",
        "core_question": "What can be deleted while the requested capability still remains true?",
        "strength": "complexity reduction, small kernels, removal of decorative machinery",
        "blind_spot": "may cut redundancy that later proves useful for resilience or creativity",
        "evidence_preference": "before/after behavior with fewer moving parts",
        "novelty_bias": "medium",
        "risk_posture": "conservative",
        "time_horizon": "medium",
        "scale_preference": "primitive",
        "disagreement_style": "asks which exact requirement justifies each extra part",
        "communication": "compact rules and deletion lists",
        "challenge_behavior": "rebuilds proposals from the irreducible core outward",
        "synthesis_role": "complexity compressor",
    },
    {
        "id": "universal.performance-optimizer",
        "name": "Performance Optimizer",
        "temperament": "quantitative and impatient with waste",
        "core_question": "Where is work repeated, serialized, copied, or calculated at the wrong granularity?",
        "strength": "latency, memory, throughput, caching, parallel structure",
        "blind_spot": "can optimize a metric before confirming the metric matters",
        "evidence_preference": "measured resource deltas and reproducible profiles",
        "novelty_bias": "medium",
        "risk_posture": "measured",
        "time_horizon": "short-to-medium",
        "scale_preference": "hot path",
        "disagreement_style": "requests cost evidence for assumptions",
        "communication": "budgets, bottlenecks, asymptotics, measurements",
        "challenge_behavior": "looks for multiplicative efficiency rather than cosmetic speedups",
        "synthesis_role": "resource optimizer",
    },
    {
        "id": "universal.adversarial-tester",
        "name": "Adversarial Tester",
        "temperament": "hostile to fragile assumptions",
        "core_question": "How would a malicious input, unlucky timing, or pathological edge case destroy this?",
        "strength": "edge cases, abuse cases, unsafe transitions, hidden coupling",
        "blind_spot": "can make ordinary use look more hostile than it usually is",
        "evidence_preference": "failing fixtures, fuzz boundaries, mutation tests",
        "novelty_bias": "medium",
        "risk_posture": "defensive",
        "time_horizon": "medium",
        "scale_preference": "boundary",
        "disagreement_style": "constructs an explicit attack case",
        "communication": "failure stories and exact triggering conditions",
        "challenge_behavior": "tries to produce the nastiest legal input the design must survive",
        "synthesis_role": "failure hunter",
    },
    {
        "id": "universal.human-use",
        "name": "Human Use Specialist",
        "temperament": "pragmatic and user-centered",
        "core_question": "What does the person actually need to understand, decide, or do next?",
        "strength": "usability, cognitive load, workflow fit, affordances",
        "blind_spot": "may underweight machine-native elegance that users never directly see",
        "evidence_preference": "task completion, observable friction, explicit user choices",
        "novelty_bias": "medium",
        "risk_posture": "balanced",
        "time_horizon": "immediate",
        "scale_preference": "interaction",
        "disagreement_style": "returns abstract arguments to concrete user actions",
        "communication": "flows, decisions, visible states",
        "challenge_behavior": "walks the solution from the user's first contact to recovery from mistakes",
        "synthesis_role": "human interface translator",
    },
    {
        "id": "universal.maintainer",
        "name": "Maintainer",
        "temperament": "boringly dependable",
        "core_question": "What will become confusing, brittle, or expensive after the hundredth change?",
        "strength": "operability, naming, upgrade paths, debugging, lifecycle clarity",
        "blind_spot": "can resist radical redesigns that make the old maintenance model irrelevant",
        "evidence_preference": "inspectability, migration tests, stable contracts",
        "novelty_bias": "low",
        "risk_posture": "conservative",
        "time_horizon": "long",
        "scale_preference": "lifecycle",
        "disagreement_style": "asks who diagnoses and repairs the thing later",
        "communication": "maintenance scenarios and ownership boundaries",
        "challenge_behavior": "evaluates the future cost of today's cleverness",
        "synthesis_role": "continuity keeper",
    },
    {
        "id": "universal.integrator",
        "name": "Integrator",
        "temperament": "cooperative and interface-obsessed",
        "core_question": "Which existing capabilities already become stronger if connected correctly?",
        "strength": "reuse, interoperability, seam discovery, avoiding duplicate subsystems",
        "blind_spot": "may overvalue reuse when a clean replacement would be simpler",
        "evidence_preference": "exact interfaces, dependency closure, shared state contracts",
        "novelty_bias": "medium-high",
        "risk_posture": "balanced",
        "time_horizon": "medium",
        "scale_preference": "seam",
        "disagreement_style": "searches for a bridge between apparently competing proposals",
        "communication": "connection maps and shared contracts",
        "challenge_behavior": "tries composition before invention",
        "synthesis_role": "capability bridge",
    },
    {
        "id": "universal.empiricist",
        "name": "Empiricist",
        "temperament": "measurement-first",
        "core_question": "What can we observe now instead of debating from intuition?",
        "strength": "experiments, metrics, evidence ladders, uncertainty separation",
        "blind_spot": "may undervalue hypotheses whose useful evidence is expensive or delayed",
        "evidence_preference": "direct observations with provenance and limits",
        "novelty_bias": "medium",
        "risk_posture": "measured",
        "time_horizon": "short",
        "scale_preference": "experiment",
        "disagreement_style": "turns disagreements into discriminating tests",
        "communication": "hypothesis, test, observation, limit",
        "challenge_behavior": "searches for the cheapest observation that changes the decision",
        "synthesis_role": "evidence designer",
    },
    {
        "id": "universal.contrarian",
        "name": "Contrarian",
        "temperament": "deliberately oppositional",
        "core_question": "If the leading assumption is backwards, what becomes possible?",
        "strength": "assumption inversion, consensus escape, neglected alternatives",
        "blind_spot": "opposition can become noise when the obvious answer is simply correct",
        "evidence_preference": "counter-models that explain the same facts differently",
        "novelty_bias": "high",
        "risk_posture": "experimental",
        "time_horizon": "mixed",
        "scale_preference": "premise",
        "disagreement_style": "constructs the strongest coherent opposite position",
        "communication": "inverted premises and alternative worlds",
        "challenge_behavior": "forces at least one serious route that rejects the dominant framing",
        "synthesis_role": "consensus breaker",
    },
    {
        "id": "universal.cross-domain-translator",
        "name": "Cross-Domain Translator",
        "temperament": "analogical but disciplined",
        "core_question": "Which other field already solved a structurally similar problem under different names?",
        "strength": "pattern transfer, terminology translation, reusable abstractions",
        "blind_spot": "analogies can smuggle in mismatched constraints",
        "evidence_preference": "explicit mapping of shared structure and non-shared assumptions",
        "novelty_bias": "high",
        "risk_posture": "balanced",
        "time_horizon": "mixed",
        "scale_preference": "pattern",
        "disagreement_style": "offers a mapped analogy and names where it breaks",
        "communication": "structural correspondences and mismatch tables",
        "challenge_behavior": "searches other domains for proven shapes rather than copied surface solutions",
        "synthesis_role": "pattern bridge",
    },
    {
        "id": "universal.simulationist",
        "name": "Simulationist",
        "temperament": "counterfactual and iterative",
        "core_question": "What can be tried cheaply in a simulated state before reality pays the cost?",
        "strength": "variant search, scenario branching, state transitions, simulation-to-reality",
        "blind_spot": "can trust the simulator farther than its evidence supports",
        "evidence_preference": "simulation predictions paired with reality discrepancy checks",
        "novelty_bias": "high",
        "risk_posture": "experimental",
        "time_horizon": "mixed",
        "scale_preference": "state-space",
        "disagreement_style": "asks competing proposals to survive the same simulated conditions",
        "communication": "world states, branches, stop conditions",
        "challenge_behavior": "explores alternatives before committing one state to reality",
        "synthesis_role": "counterfactual explorer",
    },
    {
        "id": "universal.boundary-keeper",
        "name": "Boundary Keeper",
        "temperament": "literal and contract-focused",
        "core_question": "Which claim, permission, or state transition is being silently smuggled across a boundary?",
        "strength": "authority separation, provenance, state truth, scope control",
        "blind_spot": "can make rapid prototyping feel administratively heavy",
        "evidence_preference": "typed states, explicit authority, exact digests and receipts",
        "novelty_bias": "low-medium",
        "risk_posture": "cautious",
        "time_horizon": "long",
        "scale_preference": "transition",
        "disagreement_style": "separates claims until each can be independently supported",
        "communication": "state names and authority maps",
        "challenge_behavior": "checks that useful freedom does not depend on hidden state confusion",
        "synthesis_role": "truth-boundary auditor",
    },
    {
        "id": "universal.repairer",
        "name": "Repairer",
        "temperament": "constructive and failure-tolerant",
        "core_question": "If this fails, what is the smallest reversible repair that preserves what still works?",
        "strength": "recovery, rollback, bounded patches, fault isolation",
        "blind_spot": "may patch a structure that deserves replacement",
        "evidence_preference": "before/after validation and preserved unaffected state",
        "novelty_bias": "medium",
        "risk_posture": "recovery-oriented",
        "time_horizon": "short-to-medium",
        "scale_preference": "failure seam",
        "disagreement_style": "offers a reversible repair experiment",
        "communication": "failure, patch, re-test, rollback",
        "challenge_behavior": "plans recovery at the same time as success",
        "synthesis_role": "resilience builder",
    },
    {
        "id": "universal.cost-controller",
        "name": "Cost Controller",
        "temperament": "frugal and concrete",
        "core_question": "Which capability buys the most useful outcome per unit of compute, storage, money, and human attention?",
        "strength": "resource trade-offs, cheap substitutes, operational budgets",
        "blind_spot": "can underfund frontier experiments whose upside is intentionally uncertain",
        "evidence_preference": "explicit cost basis and marginal benefit",
        "novelty_bias": "medium",
        "risk_posture": "budget-conscious",
        "time_horizon": "medium",
        "scale_preference": "resource",
        "disagreement_style": "prices the alternatives rather than moralizing about expense",
        "communication": "cost tables and marginal gains",
        "challenge_behavior": "looks for multiplicative capability without multiplicative cost",
        "synthesis_role": "resource steward",
    },
    {
        "id": "universal.visual-composer",
        "name": "Visual Composer",
        "temperament": "spatial and aesthetic",
        "core_question": "How do hierarchy, material, light, motion, proportion, and negative space cooperate as one readable visual state?",
        "strength": "visual hierarchy, spatial composition, material/light relationships",
        "blind_spot": "can privilege perceptual quality over implementation simplicity",
        "evidence_preference": "rendered comparisons tied to explicit visual variables",
        "novelty_bias": "high",
        "risk_posture": "experimental",
        "time_horizon": "immediate",
        "scale_preference": "scene",
        "disagreement_style": "produces alternate compositions instead of arguing only in words",
        "communication": "layers, contrast, rhythm, material, light",
        "challenge_behavior": "treats visuals as interacting systems rather than decoration",
        "synthesis_role": "perceptual integrator",
    },
    {
        "id": "universal.reliability-engineer",
        "name": "Reliability Engineer",
        "temperament": "redundancy-aware and suspicious of single points",
        "core_question": "What happens after partial failure, retry, interruption, duplicate delivery, or stale state?",
        "strength": "idempotence, retries, recovery, degraded operation, consistency",
        "blind_spot": "can overbuild resilience for disposable experiments",
        "evidence_preference": "fault injection and recovery receipts",
        "novelty_bias": "low-medium",
        "risk_posture": "defensive",
        "time_horizon": "long",
        "scale_preference": "runtime",
        "disagreement_style": "asks every proposal for its failure semantics",
        "communication": "fault states and recovery paths",
        "challenge_behavior": "assumes interruptions are normal rather than exceptional",
        "synthesis_role": "runtime stabilizer",
    },
    {
        "id": "universal.accessibility-inclusion",
        "name": "Accessibility and Inclusion Specialist",
        "temperament": "constraint-expanding and concrete",
        "core_question": "Who cannot use this current shape, and which alternative representation keeps the capability available?",
        "strength": "accessibility, alternate modalities, edge-user constraints",
        "blind_spot": "may broaden requirements beyond the intended experiment if scope is not explicit",
        "evidence_preference": "specific user constraints and testable alternate paths",
        "novelty_bias": "medium",
        "risk_posture": "protective",
        "time_horizon": "medium",
        "scale_preference": "access path",
        "disagreement_style": "adds a missing user condition to the test matrix",
        "communication": "barriers, alternatives, equivalent outcomes",
        "challenge_behavior": "searches for capability loss caused by one assumed interaction mode",
        "synthesis_role": "access-path expander",
    },
    {
        "id": "universal.future-stress",
        "name": "Future Stress Tester",
        "temperament": "long-horizon and speculative but bounded",
        "core_question": "Which assumption fails first if scale, capability, users, or time increase by an order of magnitude?",
        "strength": "scaling discontinuities, upgrade seams, future compatibility",
        "blind_spot": "can optimize for futures that never arrive",
        "evidence_preference": "explicit scaling scenarios and threshold conditions",
        "novelty_bias": "high",
        "risk_posture": "exploratory",
        "time_horizon": "long",
        "scale_preference": "trajectory",
        "disagreement_style": "changes one future variable until competing designs diverge",
        "communication": "thresholds, trajectories, failure horizons",
        "challenge_behavior": "tests whether today's architecture traps tomorrow's options",
        "synthesis_role": "future-option keeper",
    },
]

PERSONALITY_PALETTE = [
    ("forensic", "quiet, evidence-dense, suspicious of narrative completion", "looks for provenance gaps before proposing action"),
    ("playful", "associative, high-variance, comfortable with strange combinations", "generates unusual candidates then asks for cheap falsification"),
    ("mechanical", "literal, deterministic, contract-oriented", "reduces the problem to state, interfaces, and allowed transitions"),
    ("ecological", "relationship-first, sensitive to feedback loops", "looks for indirect consequences and mutually dependent capabilities"),
    ("pragmatic", "action-biased but not reckless", "prefers the smallest experiment that changes the decision"),
    ("mathematical", "abstraction-friendly, consistency-seeking", "searches invariants, symmetries, bounds, and combinatorial structure"),
    ("craft", "detail-sensitive, quality-focused, patient", "inspects how small implementation choices accumulate into felt quality"),
    ("contrarian", "independent, resistant to default framing", "constructs a coherent alternative premise before accepting consensus"),
]


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 12000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise ValueError(f"{label} exceeds {maximum} characters")
    return text


def _tokens(text: str) -> set[str]:
    return {
        token for token in re.findall(r"[a-z0-9][a-z0-9_-]{2,}", text.casefold())
        if token not in STOP_WORDS
    }


def _criteria(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return copy.deepcopy(DEFAULT_CRITERIA)
    if not isinstance(raw, list) or not raw:
        raise ValueError("criteria must be a non-empty list")
    result: list[dict[str, Any]] = []
    seen: set[str] = set()
    for index, row in enumerate(raw):
        if isinstance(row, str):
            item = {"id": _required_text(row, f"criteria[{index}]", 80), "weight": 1.0, "description": row.strip()}
        elif isinstance(row, dict):
            item = {
                "id": _required_text(row.get("id"), f"criteria[{index}].id", 80),
                "weight": float(row.get("weight", 1.0)),
                "description": _required_text(row.get("description", row.get("id")), f"criteria[{index}].description", 500),
            }
        else:
            raise ValueError(f"criteria[{index}] must be text or an object")
        if not math.isfinite(item["weight"]) or item["weight"] <= 0 or item["weight"] > 100:
            raise ValueError(f"criteria[{index}].weight must be > 0 and <= 100")
        if item["id"] in seen:
            raise ValueError("criterion ids must be unique")
        seen.add(item["id"])
        result.append(item)
    return result


def _ledger_path(root: Path) -> Path:
    return Path(root) / "state/specialist-fit.json"


def _empty_ledger() -> dict[str, Any]:
    return {"schema": SPECIALIST_LEDGER_SCHEMA, "specialists": {}, "votes": []}


def load_fit_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return _empty_ledger()
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SPECIALIST_LEDGER_SCHEMA:
        raise ValueError("specialist fit ledger schema is unsupported")
    if not isinstance(data.get("specialists"), dict) or not isinstance(data.get("votes"), list):
        raise ValueError("specialist fit ledger body is invalid")
    return data


def _record_view(ledger: dict[str, Any], specialist_id: str, context_key: str) -> dict[str, Any]:
    raw = ledger.get("specialists", {}).get(specialist_id, {})
    global_points = int(raw.get("points", 0))
    appearances = int(raw.get("appearances", 0))
    finalist_appearances = int(raw.get("finalist_appearances", 0))
    ctx = raw.get("contexts", {}).get(context_key, {}) if isinstance(raw.get("contexts"), dict) else {}
    context_points = int(ctx.get("points", 0))
    context_appearances = int(ctx.get("appearances", 0))
    context_finalists = int(ctx.get("finalist_appearances", 0))
    return {
        "context_points": context_points,
        "context_appearances": context_appearances,
        "context_win_rate": (context_points / context_appearances) if context_appearances else None,
        "context_finalist_appearances": context_finalists,
        "global_points": global_points,
        "global_appearances": appearances,
        "global_win_rate": (global_points / appearances) if appearances else None,
        "global_finalist_appearances": finalist_appearances,
        "fit_status": "UNPROVEN" if appearances == 0 else "OBSERVED_VOTE_HISTORY",
    }


def _stable_int(text: str) -> int:
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest(), 16)


def _fit_sort_key(profile: dict[str, Any]) -> tuple[Any, ...]:
    fit = profile["fit"]
    return (
        -fit["context_points"],
        -fit["global_points"],
        -(fit["context_win_rate"] if fit["context_win_rate"] is not None else -1),
        -(fit["global_win_rate"] if fit["global_win_rate"] is not None else -1),
        profile["id"],
    )


def _record_score(record: dict[str, Any], tokens: set[str]) -> int:
    haystack = " ".join(str(record.get(key, "")) for key in ("id", "name", "definition", "domain", "domain_code")).casefold()
    score = sum(3 for token in tokens if token in str(record.get("name", "")).casefold())
    score += sum(2 for token in tokens if token in str(record.get("domain", "")).casefold())
    score += sum(1 for token in tokens if token in haystack)
    return score


def _derived_specialists(registry: Registry, challenge: str, limit: int) -> tuple[list[dict[str, Any]], list[str]]:
    tokens = _tokens(challenge)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for record in registry.master_records():
        score = _record_score(record, tokens)
        if score > 0:
            scored.append((score, str(record.get("id", "")), record))
    scored.sort(key=lambda row: (-row[0], row[1]))
    selected = scored[:limit]
    profiles: list[dict[str, Any]] = []
    domains: list[str] = []
    for score, record_id, record in selected:
        palette_index = _stable_int(record_id) % len(PERSONALITY_PALETTE)
        personality_id, temperament, behavior = PERSONALITY_PALETTE[palette_index]
        domain_code = str(record.get("domain_code", "unknown"))
        domains.append(domain_code)
        profiles.append({
            "id": f"registry.{record_id}",
            "name": f"{record.get('name', record_id)} specialist",
            "kind": "need-derived-registry-specialist",
            "registry_ref": record_id,
            "registry_level": record.get("level"),
            "domain_code": domain_code,
            "domain": record.get("domain"),
            "focus": record.get("definition"),
            "match_score": score,
            "personality_variant": personality_id,
            "temperament": temperament,
            "core_question": f"What does the challenge look like when inspected specifically through {record.get('name', record_id)}?",
            "strength": f"deep focus on {record.get('name', record_id)} and its declared {domain_code} relationships",
            "blind_spot": "domain depth can overfit a challenge whose decisive seam lies elsewhere",
            "evidence_preference": f"evidence directly connected to {record_id} contracts, definitions, or observable behavior",
            "novelty_bias": "context-dependent",
            "risk_posture": "bounded by evidence",
            "time_horizon": "domain-dependent",
            "scale_preference": str(record.get("level", "unknown")),
            "disagreement_style": f"tests whether a competing proposal ignores a {record.get('name', record_id)} constraint",
            "communication": f"{personality_id} framing grounded in {record_id}",
            "challenge_behavior": behavior,
            "synthesis_role": "need-specific perspective",
        })
    return profiles, domains


def build_specialist_pool(root: Path, challenge: str, *, pool_size: int = 32) -> dict[str, Any]:
    if isinstance(pool_size, bool) or not isinstance(pool_size, int) or pool_size < 8 or pool_size > MAX_POOL:
        raise ValueError(f"pool_size must be an integer from 8 to {MAX_POOL}")
    registry = Registry(root)
    derived_limit = min(MAX_DERIVED_SPECIALISTS, max(0, pool_size - len(UNIVERSAL_SPECIALISTS)))
    derived, domains = _derived_specialists(registry, challenge, derived_limit)
    base_profiles = [dict(row, kind="universal-perspective") for row in UNIVERSAL_SPECIALISTS]
    profiles = (base_profiles + derived)[:pool_size]
    top_domains = []
    for domain in domains:
        if domain and domain not in top_domains:
            top_domains.append(domain)
        if len(top_domains) == 3:
            break
    context_key = "|".join(top_domains) if top_domains else "general-unmatched"
    ledger = load_fit_ledger(root)
    for profile in profiles:
        profile["fit"] = _record_view(ledger, profile["id"], context_key)
    profiles.sort(key=_fit_sort_key)
    return {
        "schema": SPECIALIST_POOL_SCHEMA,
        "challenge": challenge,
        "challenge_digest": _digest({"challenge": challenge}),
        "context_key": context_key,
        "pool_size": len(profiles),
        "specialists": profiles,
        "ranking_rule": "context +1 votes first, then global +1 votes; win rates are tie/context evidence, not a global worth score",
        "personality_difference_is_method_not_identity": True,
    }


def _tier_slices(profiles: list[dict[str, Any]]) -> tuple[list[str], list[str], list[str]]:
    ids = [row["id"] for row in profiles]
    third = max(1, math.ceil(len(ids) / 3))
    top = ids[:third]
    low = ids[-third:]
    middle = ids[third:len(ids) - third] or ids[third:third * 2] or ids
    return top, middle, low


def _team_id(challenge_digest: str, members: list[str]) -> str:
    digest = hashlib.sha256((challenge_digest + "|" + "|".join(sorted(members))).encode("utf-8")).hexdigest()[:16]
    return f"team-{digest}"


def _team_metadata(team_type: str, members: list[str], profiles_by_id: dict[str, dict[str, Any]], challenge_digest: str) -> dict[str, Any]:
    profiles = [profiles_by_id[member] for member in members]
    return {
        "team_id": _team_id(challenge_digest, members),
        "team_type": team_type,
        "members": members,
        "personality_diversity": len({row.get("personality_variant", row["id"]) for row in profiles}),
        "domain_diversity": len({row.get("domain_code", "universal") for row in profiles}),
        "historical_context_points": sum(row["fit"]["context_points"] for row in profiles),
        "historical_global_points": sum(row["fit"]["global_points"] for row in profiles),
    }


def build_teams(pool: dict[str, Any], *, team_size: int = DEFAULT_TEAM_SIZE, max_teams: int = 256, seed: str | None = None) -> dict[str, Any]:
    profiles = pool["specialists"]
    if isinstance(team_size, bool) or not isinstance(team_size, int) or team_size < 3 or team_size > 6 or team_size > len(profiles):
        raise ValueError("team_size must be an integer from 3 to 6 and no larger than the pool")
    if isinstance(max_teams, bool) or not isinstance(max_teams, int) or max_teams < 4 or max_teams > MAX_TEAMS:
        raise ValueError(f"max_teams must be an integer from 4 to {MAX_TEAMS}")
    challenge_digest = pool["challenge_digest"]
    profiles_by_id = {row["id"]: row for row in profiles}
    ranked_ids = [row["id"] for row in profiles]
    top, middle, low = _tier_slices(profiles)
    rng_seed = seed or challenge_digest
    rng = random.Random(_stable_int(rng_seed))

    dedicated: list[tuple[str, list[str]]] = []
    dedicated.append(("best-evidence-team", ranked_ids[:team_size]))
    mid_start = max(0, (len(middle) - team_size) // 2)
    middle_team = (middle[mid_start:mid_start + team_size] + ranked_ids)[:team_size]
    dedicated.append(("middle-evidence-team", list(dict.fromkeys(middle_team))[:team_size]))
    low_team = list(reversed(low))[:team_size]
    if len(low_team) < team_size:
        low_team += [row for row in reversed(ranked_ids) if row not in low_team][:team_size - len(low_team)]
    dedicated.append(("lowest-third-challenge-team", low_team))

    mixed: list[str] = []
    for tier in (top, middle, low):
        choices = [item for item in tier if item not in mixed]
        if choices:
            mixed.append(rng.choice(choices))
    remaining = [item for item in ranked_ids if item not in mixed]
    rng.shuffle(remaining)
    mixed += remaining[: max(0, team_size - len(mixed))]
    dedicated.append(("mixed-random-team", mixed[:team_size]))

    teams_by_members: dict[tuple[str, ...], dict[str, Any]] = {}
    for team_type, members in dedicated:
        if len(set(members)) != team_size:
            continue
        key = tuple(sorted(members))
        teams_by_members[key] = _team_metadata(team_type, members, profiles_by_id, challenge_digest)

    total_possible = math.comb(len(ranked_ids), team_size)
    slots = max(0, max_teams - len(teams_by_members))
    if slots:
        combos = itertools.combinations(ranked_ids, team_size)
        selected = heapq.nsmallest(
            slots,
            combos,
            key=lambda combo: hashlib.sha256((rng_seed + "|" + "|".join(sorted(combo))).encode("utf-8")).hexdigest(),
        )
        for combo in selected:
            key = tuple(sorted(combo))
            if key in teams_by_members:
                continue
            teams_by_members[key] = _team_metadata("combination-team", list(combo), profiles_by_id, challenge_digest)
            if len(teams_by_members) >= max_teams:
                break

    teams = sorted(teams_by_members.values(), key=lambda row: row["team_id"])
    return {
        "team_size": team_size,
        "combination_space": total_possible,
        "generated_team_count": len(teams),
        "max_teams": max_teams,
        "deterministic_random_seed": rng_seed,
        "tiers": {"top_third": top, "middle_third": middle, "lowest_third": low},
        "teams": teams,
    }


def _challenge_packet(challenge: str, criteria: list[dict[str, Any]], team: dict[str, Any]) -> dict[str, Any]:
    return {
        "team_id": team["team_id"],
        "team_type": team["team_type"],
        "members": team["members"],
        "challenge": challenge,
        "criteria": criteria,
        "isolation_rule": "solve independently; no other team's submission, ranking, or vote is visible before parallel challenge work is complete",
        "working_protocol": [
            "each specialist inspects the same challenge through its own bounded profile",
            "preserve disagreements and unknowns instead of forcing artificial consensus",
            "reuse evidence and existing capabilities before inventing new machinery",
            "produce one team synthesis only after individual perspective contributions exist",
        ],
        "required_submission": {
            "proposal": "team answer or candidate direction",
            "evidence": "inspectable evidence supporting the proposal",
            "dissent": "important member disagreements that survived synthesis",
            "unknowns": "unresolved gaps and untested assumptions",
            "criterion_notes": "notes mapped to every tournament criterion",
        },
    }


def prepare_tournament(
    root: Path,
    challenge: str,
    *,
    criteria: Any = None,
    pool_size: int = 32,
    team_size: int = DEFAULT_TEAM_SIZE,
    max_teams: int = 256,
    seed: str | None = None,
) -> dict[str, Any]:
    challenge = _required_text(challenge, "challenge")
    normalized_criteria = _criteria(criteria)
    pool = build_specialist_pool(root, challenge, pool_size=pool_size)
    team_body = build_teams(pool, team_size=team_size, max_teams=max_teams, seed=seed)
    tournament = {
        "schema": SPECIALIST_TOURNAMENT_SCHEMA,
        "status": "READY_FOR_PARALLEL_SPECIALIST_CHALLENGE",
        "challenge": challenge,
        "challenge_digest": pool["challenge_digest"],
        "context_key": pool["context_key"],
        "criteria": normalized_criteria,
        "pool": pool,
        "team_generation": team_body,
        "parallel_challenge_packets": [_challenge_packet(challenge, normalized_criteria, team) for team in team_body["teams"]],
        "execution_claim": "team packets are prepared but no specialist reasoning is claimed until a cognition provider, human, or other executor actually returns submissions/evidence",
        "vote_rule": "after complete independent judging, show the best two teams; a separate finalist vote awards +1 contextual/global fit point to every winning team member",
    }
    tournament["tournament_digest"] = _digest(tournament)
    return tournament


def _verify_tournament(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SPECIALIST_TOURNAMENT_SCHEMA:
        raise ValueError("tournament schema is unsupported")
    supplied = raw.get("tournament_digest")
    body = copy.deepcopy(raw)
    body.pop("tournament_digest", None)
    actual = _digest(body)
    if supplied != actual:
        raise ValueError("tournament digest mismatch")
    return raw


def rank_tournament(raw_tournament: Any, judgements: Any) -> dict[str, Any]:
    tournament = _verify_tournament(raw_tournament)
    if not isinstance(judgements, dict):
        raise ValueError("judgements must be an object keyed by team_id")
    teams = {row["team_id"]: row for row in tournament["team_generation"]["teams"]}
    criteria = tournament["criteria"]
    criterion_ids = [row["id"] for row in criteria]
    weights = {row["id"]: float(row["weight"]) for row in criteria}
    rows: list[dict[str, Any]] = []
    unexpected = sorted(set(judgements) - set(teams))
    if unexpected:
        raise ValueError(f"judgements contain unknown teams: {', '.join(unexpected)}")
    for team_id, judgement in judgements.items():
        if not isinstance(judgement, dict):
            raise ValueError(f"judgement for {team_id} must be an object")
        scores = judgement.get("criteria")
        if not isinstance(scores, dict):
            raise ValueError(f"judgement for {team_id} requires criteria")
        missing = [criterion for criterion in criterion_ids if criterion not in scores]
        if missing:
            raise ValueError(f"judgement for {team_id} is missing criteria: {', '.join(missing)}")
        weighted = 0.0
        weight_total = 0.0
        normalized_scores: dict[str, Any] = {}
        for criterion in criterion_ids:
            cell = scores[criterion]
            if not isinstance(cell, dict):
                raise ValueError(f"judgement {team_id}.{criterion} must be an object")
            score = cell.get("score")
            evidence = cell.get("evidence")
            if isinstance(score, bool) or not isinstance(score, (int, float)) or not math.isfinite(float(score)) or score < 0 or score > 100:
                raise ValueError(f"judgement {team_id}.{criterion}.score must be 0..100")
            if not isinstance(evidence, str) or not evidence.strip():
                raise ValueError(f"judgement {team_id}.{criterion}.evidence must be non-empty text")
            weight = weights[criterion]
            weighted += float(score) * weight
            weight_total += weight
            normalized_scores[criterion] = {"score": float(score), "evidence": evidence.strip()}
        rows.append({
            "team_id": team_id,
            "team": teams[team_id],
            "score": weighted / weight_total,
            "criteria": normalized_scores,
            "summary": str(judgement.get("summary", "")).strip(),
        })
    rows.sort(key=lambda row: (-row["score"], row["team_id"]))
    complete = len(rows) == len(teams)
    finalists = rows[:2] if complete and len(rows) >= 2 else []
    ranking = {
        "schema": SPECIALIST_RANKING_SCHEMA,
        "status": "AWAITING_FINALIST_VOTE" if finalists else "PARTIAL_RANKING_NO_FINALIST_VOTE",
        "tournament_digest": tournament["tournament_digest"],
        "context_key": tournament["context_key"],
        "complete_parallel_judging": complete,
        "judged_team_count": len(rows),
        "required_team_count": len(teams),
        "ranking": rows,
        "finalists": finalists,
        "vote_candidates": [row["team_id"] for row in finalists],
        "points_awarded": False,
        "ranking_truth": "scores are exactly the supplied independent judgements under the declared weighted criteria; the tournament engine does not invent missing team performance",
    }
    ranking["ranking_digest"] = _digest(ranking)
    return ranking


def _verify_ranking(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SPECIALIST_RANKING_SCHEMA:
        raise ValueError("ranking schema is unsupported")
    supplied = raw.get("ranking_digest")
    body = copy.deepcopy(raw)
    body.pop("ranking_digest", None)
    if supplied != _digest(body):
        raise ValueError("ranking digest mismatch")
    if raw.get("status") != "AWAITING_FINALIST_VOTE" or len(raw.get("finalists", [])) != 2:
        raise ValueError("ranking is not ready for a finalist vote")
    return raw


def _increment_specialist(ledger: dict[str, Any], specialist_id: str, context_key: str, *, appearance: bool, finalist: bool, win: bool) -> dict[str, Any]:
    specialists = ledger.setdefault("specialists", {})
    row = specialists.setdefault(specialist_id, {"points": 0, "appearances": 0, "finalist_appearances": 0, "contexts": {}})
    if appearance:
        row["appearances"] = int(row.get("appearances", 0)) + 1
    if finalist:
        row["finalist_appearances"] = int(row.get("finalist_appearances", 0)) + 1
    if win:
        row["points"] = int(row.get("points", 0)) + 1
    contexts = row.setdefault("contexts", {})
    ctx = contexts.setdefault(context_key, {"points": 0, "appearances": 0, "finalist_appearances": 0})
    if appearance:
        ctx["appearances"] = int(ctx.get("appearances", 0)) + 1
    if finalist:
        ctx["finalist_appearances"] = int(ctx.get("finalist_appearances", 0)) + 1
    if win:
        ctx["points"] = int(ctx.get("points", 0)) + 1
    return _record_view(ledger, specialist_id, context_key)


def record_finalist_vote(root: Path, raw_ranking: Any, winner_team_id: str) -> dict[str, Any]:
    ranking = _verify_ranking(raw_ranking)
    winner_team_id = _required_text(winner_team_id, "winner_team_id", 120)
    finalist_ids = [row["team_id"] for row in ranking["finalists"]]
    if winner_team_id not in finalist_ids:
        raise ValueError("winner_team_id must be one of the two shown finalists")
    context_key = ranking["context_key"]
    ledger = load_fit_ledger(root)
    vote_digest = _digest({"ranking_digest": ranking["ranking_digest"], "winner_team_id": winner_team_id})
    for vote in ledger["votes"]:
        if vote.get("ranking_digest") == ranking["ranking_digest"]:
            if vote.get("winner_team_id") != winner_team_id:
                raise ValueError("this ranking already has a different recorded finalist vote")
            return {
                "status": "VOTE_ALREADY_RECORDED",
                "vote_digest": vote.get("vote_digest"),
                "winner_team_id": winner_team_id,
                "member_updates": vote.get("member_updates", {}),
                "ledger_path": str(_ledger_path(root)),
            }

    all_participants = {
        member
        for row in ranking["ranking"]
        for member in row["team"]["members"]
    }
    finalist_members = {
        member
        for row in ranking["finalists"]
        for member in row["team"]["members"]
    }
    winner = next(row for row in ranking["finalists"] if row["team_id"] == winner_team_id)
    winner_members = set(winner["team"]["members"])
    member_updates: dict[str, Any] = {}
    for specialist_id in sorted(all_participants):
        member_updates[specialist_id] = _increment_specialist(
            ledger,
            specialist_id,
            context_key,
            appearance=True,
            finalist=specialist_id in finalist_members,
            win=specialist_id in winner_members,
        )
    vote = {
        "vote_digest": vote_digest,
        "ranking_digest": ranking["ranking_digest"],
        "tournament_digest": ranking["tournament_digest"],
        "context_key": context_key,
        "winner_team_id": winner_team_id,
        "winner_members": sorted(winner_members),
        "points_each_winner_member": 1,
        "member_updates": member_updates,
    }
    ledger["votes"].append(vote)
    atomic_write_json(_ledger_path(root), ledger)
    return {
        "status": "FINALIST_VOTE_RECORDED",
        "truth_status": "CONTEXTUAL_SPECIALIST_FIT_UPDATED_FROM_EXPLICIT_FINALIST_VOTE",
        "vote_digest": vote_digest,
        "winner_team_id": winner_team_id,
        "winner_members": sorted(winner_members),
        "points_each_winner_member": 1,
        "member_updates": {member: member_updates[member] for member in sorted(winner_members)},
        "ledger_path": str(_ledger_path(root)),
        "meaning": "+1 is accumulated evidence that this specialist contributed to a winning team for this context; it is not a global intelligence, identity, authority, or growth reward",
    }


def inspect_specialist_fit(root: Path, *, challenge: str | None = None, limit: int = 100) -> dict[str, Any]:
    ledger = load_fit_ledger(root)
    if challenge:
        pool = build_specialist_pool(root, _required_text(challenge, "challenge"), pool_size=min(MAX_POOL, max(8, len(UNIVERSAL_SPECIALISTS))))
        context_key = pool["context_key"]
        rows = [
            {"id": row["id"], "name": row["name"], "fit": row["fit"]}
            for row in pool["specialists"]
        ][: max(1, min(int(limit), 500))]
    else:
        context_key = None
        rows = []
        for specialist_id in sorted(ledger["specialists"]):
            raw = ledger["specialists"][specialist_id]
            rows.append({
                "id": specialist_id,
                "points": int(raw.get("points", 0)),
                "appearances": int(raw.get("appearances", 0)),
                "finalist_appearances": int(raw.get("finalist_appearances", 0)),
                "contexts": raw.get("contexts", {}),
            })
        rows.sort(key=lambda row: (-row["points"], row["id"]))
        rows = rows[: max(1, min(int(limit), 500))]
    return {
        "schema": SPECIALIST_LEDGER_SCHEMA,
        "truth_status": "OBSERVED_EXPLICIT_FINALIST_VOTE_HISTORY",
        "context_key": context_key,
        "specialists": rows,
        "recorded_votes": len(ledger["votes"]),
        "ranking_warning": "historical +1 votes estimate contextual team fit only; low or zero points can mean under-exposure rather than poor capability, so lowest/middle/mixed teams continue to be generated",
    }


def operate_specialist_tournament(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "prepare")).strip().casefold()
    if operation in {"prepare", "prepare-tournament", "build-pool"}:
        return prepare_tournament(
            root,
            inputs.get("challenge"),
            criteria=inputs.get("criteria"),
            pool_size=inputs.get("pool_size", 32),
            team_size=inputs.get("team_size", DEFAULT_TEAM_SIZE),
            max_teams=inputs.get("max_teams", 256),
            seed=inputs.get("seed"),
        )
    if operation in {"rank", "rank-tournament", "select-finalists"}:
        return rank_tournament(inputs.get("tournament"), inputs.get("judgements"))
    if operation in {"vote", "record-vote", "record-finalist-vote"}:
        return record_finalist_vote(root, inputs.get("ranking"), str(inputs.get("winner_team_id", "")))
    if operation in {"inspect-fit", "fit", "history"}:
        return inspect_specialist_fit(root, challenge=inputs.get("challenge"), limit=int(inputs.get("limit", 100)))
    raise ValueError("unsupported specialist tournament operation")

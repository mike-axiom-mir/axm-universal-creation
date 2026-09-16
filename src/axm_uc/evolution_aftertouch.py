from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path
from typing import Any

from .project import ProjectError, validate_project
from .simulation import SimulationError, simulate_until_no_known_improvements
from .specialist_pool import prepare_tournament, rank_tournament


CHAMBER_SCHEMA = "axm.evolution-aftertouch-chamber/v0.1"
CANDIDATE_SCHEMA = "axm.evolution-aftertouch-candidate/v0.1"
SELF_TEST_SCHEMA = "axm.evolution-aftertouch-self-test/v0.1"
ROUND_COUNT = 7
SURVIVOR_COUNT = 2
MAX_TEAMS = 64
VERIFICATION_STATUSES = {"PASS", "HOLD", "FAIL", "NOT_TESTED"}
FINAL_EVIDENCE_LANES = (
    "structural",
    "functional",
    "visual",
    "experience",
    "context",
    "adversarial",
    "polish",
)
ROUND_PHASES = (
    {
        "round": 1,
        "id": "foundation",
        "focus": "structure, function, interfaces, feasibility, and a coherent base that can survive later mutation",
        "simulation_target": 3,
    },
    {
        "round": 2,
        "id": "composition",
        "focus": "shape, layout, hierarchy, spatial arrangement, system composition, and whole-result readability",
        "simulation_target": 3,
    },
    {
        "round": 3,
        "id": "detail",
        "focus": "secondary and tertiary construction, detail density, material or state richness, and removal of generic empty areas",
        "simulation_target": 3,
    },
    {
        "round": 4,
        "id": "experience",
        "focus": "actual use, play, interaction, readability, responsiveness, recovery, and end-to-end flow",
        "simulation_target": 4,
    },
    {
        "round": 5,
        "id": "stress",
        "focus": "adversarial use, edge cases, bad inputs, collisions, load, failure and retry behavior, and regression pressure",
        "simulation_target": 7,
    },
    {
        "round": 6,
        "id": "creative-elevation",
        "focus": "search outside the obvious local optimum while preserving what evidence says already works",
        "simulation_target": 4,
    },
    {
        "round": 7,
        "id": "deep-aftertouch",
        "focus": "structural, functional, visual, experiential, contextual, adversarial, and polish aftertouch followed by re-test",
        "simulation_target": 7,
    },
)


class EvolutionAftertouchError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EvolutionAftertouchError("evolution chamber values must be JSON serializable") from exc


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 8000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise EvolutionAftertouchError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise EvolutionAftertouchError(f"{label} exceeds its {maximum}-character bound")
    return text


def _bounded_int(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < minimum or value > maximum:
        raise EvolutionAftertouchError(f"{label} must be an integer from {minimum} to {maximum}")
    return value


def _phase(round_number: int) -> dict[str, Any]:
    if round_number < 1 or round_number > ROUND_COUNT:
        raise EvolutionAftertouchError("round is outside the seven-round chamber")
    return copy.deepcopy(ROUND_PHASES[round_number - 1])


def _verification_rows(raw: Any) -> list[dict[str, Any]]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise EvolutionAftertouchError("verification must be a list")
    rows: list[dict[str, Any]] = []
    for index, row in enumerate(raw):
        if not isinstance(row, dict):
            raise EvolutionAftertouchError(f"verification[{index}] must be an object")
        lane = _required_text(row.get("lane"), f"verification[{index}].lane", 80).casefold()
        status = str(row.get("status", "")).strip().upper()
        if status not in VERIFICATION_STATUSES:
            raise EvolutionAftertouchError(
                f"verification[{index}].status must be PASS, HOLD, FAIL, or NOT_TESTED"
            )
        evidence = row.get("evidence")
        if status != "NOT_TESTED" and (not isinstance(evidence, str) or not evidence.strip()):
            raise EvolutionAftertouchError(
                f"verification[{index}].evidence must be non-empty text unless status is NOT_TESTED"
            )
        rows.append(
            {
                "lane": lane,
                "status": status,
                "evidence": evidence.strip() if isinstance(evidence, str) else "",
                "source": str(row.get("source", "external-or-existing-uc-evidence")).strip(),
            }
        )
    return rows


def _evidence_list(raw: Any, label: str) -> list[str]:
    if isinstance(raw, str) and raw.strip():
        return [raw.strip()]
    if not isinstance(raw, list) or not raw:
        raise EvolutionAftertouchError(f"{label} must be non-empty text or a non-empty list of text evidence")
    result = []
    for index, value in enumerate(raw):
        result.append(_required_text(value, f"{label}[{index}]", 4000))
    return result


def _candidate_digest(candidate: dict[str, Any]) -> str:
    body = copy.deepcopy(candidate)
    body.pop("candidate_digest", None)
    return _digest(body)


def _chamber_digest(chamber: dict[str, Any]) -> str:
    body = copy.deepcopy(chamber)
    body.pop("chamber_digest", None)
    return _digest(body)


def _verify_chamber(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != CHAMBER_SCHEMA:
        raise EvolutionAftertouchError("chamber schema is unsupported")
    supplied = raw.get("chamber_digest")
    actual = _chamber_digest(raw)
    if supplied != actual:
        raise EvolutionAftertouchError("chamber digest mismatch")
    return copy.deepcopy(raw)


def _parent_summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_digest": candidate["candidate_digest"],
        "origin_team_id": candidate["origin_team_id"],
        "proposal": copy.deepcopy(candidate["proposal"]),
        "evidence": copy.deepcopy(candidate["evidence"]),
        "verification": copy.deepcopy(candidate["verification"]),
        "unknowns": copy.deepcopy(candidate["unknowns"]),
    }


def _round_challenge(challenge: str, phase: dict[str, Any], parents: list[dict[str, Any]]) -> str:
    text = (
        f"{challenge}\n\n"
        f"EVOLUTION ROUND {phase['round']}/7 — {phase['id']}\n"
        f"Focus: {phase['focus']}\n"
        "Create a materially improved candidate, not a commentary about one. Build or specify what can be built, "
        "exercise it through available UC simulation/test/observer surfaces, diagnose evidence, repair what is known, "
        "and re-test before submission. Do not claim tests that were not run."
    )
    if parents:
        text += (
            "\nTwo survivors from the prior round remain alive. Each creative team receives exactly one assigned parent. "
            "Preserve that parent's working evidence while making an actual next variant; do not silently overwrite the other survivor."
        )
    return text


def _creative_packets(
    tournament: dict[str, Any],
    phase: dict[str, Any],
    parents: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    packets = []
    tournament_packets = tournament["parallel_challenge_packets"]
    for index, source in enumerate(tournament_packets):
        parent = parents[index % len(parents)] if parents else None
        packet = copy.deepcopy(source)
        packet.update(
            {
                "round": phase["round"],
                "phase": phase["id"],
                "phase_focus": phase["focus"],
                "simulation_target": phase["simulation_target"],
                "parent_candidate": _parent_summary(parent) if parent else None,
                "parent_candidate_id": parent["candidate_id"] if parent else None,
                "creation_protocol": [
                    "create a concrete candidate variant",
                    "simulate or test through every applicable available UC evidence surface",
                    "observe the actual result rather than inferring success from source alone",
                    "diagnose structural, functional, visual, experience, context and adversarial gaps that are observable now",
                    "repair bounded known gaps without silently rewriting the goal",
                    "re-run the same tests after repair",
                    "submit explicit NOT_TESTED for evidence lanes that cannot currently be exercised",
                ],
                "required_submission": {
                    "proposal": "JSON-serializable concrete candidate/output body",
                    "evidence": "one or more inspectable evidence statements or references",
                    "verification": "list of lane/status/evidence receipts using PASS/HOLD/FAIL/NOT_TESTED",
                    "dissent": "surviving creative-team disagreement, may be empty text/list",
                    "unknowns": "remaining unknowns or untested assumptions, may be empty text/list",
                    "parent_candidate_id": "must equal the packet parent when a parent is assigned",
                },
            }
        )
        packets.append(packet)
    return packets


def _prepare_round(
    root: Path,
    challenge: str,
    round_number: int,
    *,
    parents: list[dict[str, Any]],
    criteria: Any,
    pool_size: int,
    team_size: int,
    max_teams: int,
    seed: str,
) -> dict[str, Any]:
    phase = _phase(round_number)
    tournament = prepare_tournament(
        root,
        _round_challenge(challenge, phase, parents),
        criteria=criteria,
        pool_size=pool_size,
        team_size=team_size,
        max_teams=max_teams,
        seed=f"{seed}:round:{round_number}:{phase['id']}",
    )
    return {
        "round": round_number,
        "phase": phase,
        "status": "AWAITING_PARALLEL_CREATIVE_TEAM_OUTPUTS_AND_INDEPENDENT_JUDGEMENTS",
        "parent_candidates": [_parent_summary(row) for row in parents],
        "tournament": tournament,
        "creative_packets": _creative_packets(tournament, phase, parents),
        "survivors": [],
        "ranking": None,
    }


def prepare_chamber(
    root: Path,
    challenge: Any,
    *,
    criteria: Any = None,
    pool_size: int = 20,
    team_size: int = 4,
    max_teams: int = 8,
    seed: Any = None,
) -> dict[str, Any]:
    challenge = _required_text(challenge, "challenge")
    pool_size = _bounded_int(pool_size, "pool_size", 8, 40)
    team_size = _bounded_int(team_size, "team_size", 3, 6)
    max_teams = _bounded_int(max_teams, "max_teams", 4, MAX_TEAMS)
    seed_text = _required_text(seed, "seed", 500) if seed is not None else _digest({"challenge": challenge})
    first = _prepare_round(
        root,
        challenge,
        1,
        parents=[],
        criteria=criteria,
        pool_size=pool_size,
        team_size=team_size,
        max_teams=max_teams,
        seed=seed_text,
    )
    chamber = {
        "schema": CHAMBER_SCHEMA,
        "status": "ROUND_1_READY",
        "truth_status": "SEVEN_ROUND_CREATIVE_EVOLUTION_PREPARED_NO_TEAM_REASONING_OR_TESTING_FAKED",
        "challenge": challenge,
        "seed": seed_text,
        "current_round": 1,
        "round_count": ROUND_COUNT,
        "survivor_count": SURVIVOR_COUNT,
        "phases": [copy.deepcopy(row) for row in ROUND_PHASES],
        "config": {
            "criteria": copy.deepcopy(criteria),
            "pool_size": pool_size,
            "team_size": team_size,
            "max_teams": max_teams,
        },
        "policy": {
            "parallel_creative_teams": True,
            "exact_survivors_per_completed_round": SURVIVOR_COUNT,
            "final_outputs_retained": SURVIVOR_COUNT,
            "self_test_before_output": True,
            "retest_after_repair": True,
            "front_end_or_render_observation_when_applicable": True,
            "explicit_not_tested_instead_of_fake_pass": True,
            "automatic_acceptance": False,
            "automatic_canon": False,
            "perfect_claimed": False,
        },
        "rounds": [first],
        "survivors": [],
        "finalists": [],
    }
    chamber["chamber_digest"] = _chamber_digest(chamber)
    return chamber


def _normalize_submission(team_id: str, raw: Any, expected_parent_id: str | None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise EvolutionAftertouchError(f"submission for {team_id} must be an object")
    if "proposal" not in raw:
        raise EvolutionAftertouchError(f"submission for {team_id} requires proposal")
    _canonical(raw["proposal"])
    supplied_parent = raw.get("parent_candidate_id")
    if expected_parent_id is None:
        if supplied_parent not in {None, ""}:
            raise EvolutionAftertouchError(f"round-one submission {team_id} cannot claim an invented parent")
        parent_id = None
    else:
        if supplied_parent != expected_parent_id:
            raise EvolutionAftertouchError(
                f"submission for {team_id} must remain bound to its assigned parent",
                {"expected_parent_candidate_id": expected_parent_id, "supplied": supplied_parent},
            )
        parent_id = expected_parent_id
    return {
        "team_id": team_id,
        "parent_candidate_id": parent_id,
        "proposal": copy.deepcopy(raw["proposal"]),
        "evidence": _evidence_list(raw.get("evidence"), f"submission[{team_id}].evidence"),
        "verification": _verification_rows(raw.get("verification")),
        "dissent": copy.deepcopy(raw.get("dissent", [])),
        "unknowns": copy.deepcopy(raw.get("unknowns", [])),
    }


def _finalist_candidate(
    chamber: dict[str, Any],
    current: dict[str, Any],
    ranking_row: dict[str, Any],
    submission: dict[str, Any],
) -> dict[str, Any]:
    round_number = int(current["round"])
    candidate_id = (
        "candidate-"
        + hashlib.sha256(
            (
                chamber["chamber_digest"]
                + f"|{round_number}|"
                + ranking_row["team_id"]
                + "|"
                + _digest(submission["proposal"])
            ).encode("utf-8")
        ).hexdigest()[:20]
    )
    candidate = {
        "schema": CANDIDATE_SCHEMA,
        "candidate_id": candidate_id,
        "round": round_number,
        "phase": current["phase"]["id"],
        "origin_team_id": ranking_row["team_id"],
        "origin_members": copy.deepcopy(ranking_row["team"]["members"]),
        "parent_candidate_id": submission["parent_candidate_id"],
        "proposal": copy.deepcopy(submission["proposal"]),
        "evidence": copy.deepcopy(submission["evidence"]),
        "verification": copy.deepcopy(submission["verification"]),
        "dissent": copy.deepcopy(submission["dissent"]),
        "unknowns": copy.deepcopy(submission["unknowns"]),
        "judged_score": float(ranking_row["score"]),
        "criterion_judgements": copy.deepcopy(ranking_row["criteria"]),
        "accepted": False,
        "canon": False,
    }
    candidate["candidate_digest"] = _candidate_digest(candidate)
    return candidate


def _final_gate(finalists: list[dict[str, Any]]) -> dict[str, Any]:
    finalist_rows = []
    aggregate_statuses = []
    for candidate in finalists:
        by_lane: dict[str, list[dict[str, Any]]] = {}
        for row in candidate.get("verification", []):
            by_lane.setdefault(row["lane"], []).append(row)
        lanes = {}
        for lane in FINAL_EVIDENCE_LANES:
            receipts = by_lane.get(lane, [])
            if not receipts:
                status = "NOT_TESTED"
            elif any(row["status"] == "FAIL" for row in receipts):
                status = "FAIL"
            elif any(row["status"] == "HOLD" for row in receipts):
                status = "HOLD"
            elif any(row["status"] == "NOT_TESTED" for row in receipts):
                status = "NOT_TESTED"
            else:
                status = "PASS"
            lanes[lane] = {"status": status, "receipts": copy.deepcopy(receipts)}
            aggregate_statuses.append(status)
        finalist_rows.append(
            {
                "candidate_id": candidate["candidate_id"],
                "candidate_digest": candidate["candidate_digest"],
                "lanes": lanes,
            }
        )
    if "FAIL" in aggregate_statuses:
        status = "TWO_FINALISTS_RETAINED_FINAL_GATE_FAILED"
        output_ready = False
    elif "HOLD" in aggregate_statuses or "NOT_TESTED" in aggregate_statuses:
        status = "TWO_FINALISTS_RETAINED_WITH_EXPLICIT_TEST_GAPS"
        output_ready = False
    else:
        status = "TWO_FINALISTS_RETAINED_ALL_DECLARED_AFTERTOUCH_GATES_PASS"
        output_ready = True
    return {
        "status": status,
        "output_ready_under_declared_gates": output_ready,
        "required_lanes": list(FINAL_EVIDENCE_LANES),
        "finalists": finalist_rows,
        "truth_boundary": "PASS means the supplied evidence receipts pass the declared lanes; it is not a claim of perfection, universal quality, or human acceptance",
    }


def advance_round(
    root: Path,
    raw_chamber: Any,
    submissions: Any,
    judgements: Any,
) -> dict[str, Any]:
    chamber = _verify_chamber(raw_chamber)
    if chamber.get("status") == "COMPLETE_TWO_FINALISTS_RETAINED":
        raise EvolutionAftertouchError("chamber is already complete")
    round_number = int(chamber["current_round"])
    current = chamber["rounds"][-1]
    if current.get("round") != round_number:
        raise EvolutionAftertouchError("current round continuity mismatch")
    if not isinstance(submissions, dict):
        raise EvolutionAftertouchError("submissions must be an object keyed by team_id")
    packet_by_team = {row["team_id"]: row for row in current["creative_packets"]}
    expected_ids = set(packet_by_team)
    supplied_ids = set(submissions)
    if supplied_ids != expected_ids:
        raise EvolutionAftertouchError(
            "all parallel creative-team submissions are required before two survivors can be selected",
            {"missing": sorted(expected_ids - supplied_ids), "unexpected": sorted(supplied_ids - expected_ids)},
        )
    normalized_submissions = {
        team_id: _normalize_submission(team_id, submissions[team_id], packet_by_team[team_id].get("parent_candidate_id"))
        for team_id in sorted(expected_ids)
    }
    try:
        ranking = rank_tournament(current["tournament"], judgements)
    except (ValueError, TypeError) as exc:
        raise EvolutionAftertouchError(str(exc)) from exc
    if ranking.get("status") != "AWAITING_FINALIST_VOTE" or len(ranking.get("finalists", [])) != SURVIVOR_COUNT:
        raise EvolutionAftertouchError("complete independent judging is required before the chamber may keep two survivors")
    survivors = [
        _finalist_candidate(chamber, current, ranking_row, normalized_submissions[ranking_row["team_id"]])
        for ranking_row in ranking["finalists"]
    ]
    current["status"] = "ROUND_COMPLETE_TWO_SURVIVORS_RETAINED"
    current["ranking"] = ranking
    current["survivors"] = copy.deepcopy(survivors)
    current["submission_receipts"] = normalized_submissions
    chamber["rounds"][-1] = current
    chamber["survivors"] = copy.deepcopy(survivors)

    if round_number == ROUND_COUNT:
        chamber["status"] = "COMPLETE_TWO_FINALISTS_RETAINED"
        chamber["finalists"] = copy.deepcopy(survivors)
        chamber["final_gate"] = _final_gate(survivors)
        chamber["truth_status"] = "SEVEN_EVOLUTION_ROUNDS_COMPLETED_TWO_FINALISTS_RETAINED_WITH_EXPLICIT_EVIDENCE_BOUNDARY"
        chamber["current_round"] = ROUND_COUNT
    else:
        next_round = _prepare_round(
            root,
            chamber["challenge"],
            round_number + 1,
            parents=survivors,
            criteria=chamber["config"]["criteria"],
            pool_size=chamber["config"]["pool_size"],
            team_size=chamber["config"]["team_size"],
            max_teams=chamber["config"]["max_teams"],
            seed=chamber["seed"],
        )
        chamber["rounds"].append(next_round)
        chamber["current_round"] = round_number + 1
        chamber["status"] = f"ROUND_{round_number + 1}_READY"
        chamber["truth_status"] = "PRIOR_ROUND_JUDGED_TWO_SURVIVORS_BOUND_INTO_NEXT_PARALLEL_CREATIVE_ROUND"

    chamber.pop("chamber_digest", None)
    chamber["chamber_digest"] = _chamber_digest(chamber)
    return chamber


def _allowed_creation_target(root: Path, target: Path) -> bool:
    root = root.resolve()
    target = target.resolve()
    try:
        rel = target.relative_to(root)
    except ValueError:
        return True
    return bool(rel.parts) and rel.parts[0] in {"creations", ".axm-build"}


def self_test_candidate(root: Path, raw_candidate: Any) -> dict[str, Any]:
    if not isinstance(raw_candidate, dict):
        raise EvolutionAftertouchError("candidate must be an object")
    artifact = raw_candidate.get("artifact", raw_candidate)
    if not isinstance(artifact, dict):
        raise EvolutionAftertouchError("candidate artifact must be an object")
    kind = str(artifact.get("kind", "generic")).strip().casefold()

    if kind in {"visual-thought", "paintgun-thought", "visual"} and "thought" in artifact:
        try:
            simulation = simulate_until_no_known_improvements(
                artifact.get("thought"),
                defaults=artifact.get("defaults"),
                alternatives=artifact.get("alternatives"),
                palette=artifact.get("palette"),
                criteria=artifact.get("criteria"),
                max_iterations=artifact.get("max_iterations", 32),
            )
        except SimulationError as exc:
            return {
                "schema": SELF_TEST_SCHEMA,
                "adapter": "uc-visual-simulation",
                "status": "FAIL",
                "verification": [{"lane": "visual", "status": "FAIL", "evidence": str(exc), "source": "builtin:simulate_creation"}],
                "details": exc.details,
                "perfect_claimed": False,
            }
        passed = simulation.get("status") == "NO_KNOWN_IMPROVEMENTS" and simulation.get("materialization_ready") is True
        status = "PASS" if passed else "HOLD"
        return {
            "schema": SELF_TEST_SCHEMA,
            "adapter": "uc-visual-simulation",
            "status": status,
            "verification": [
                {
                    "lane": "structural",
                    "status": status,
                    "evidence": f"UC visual simulation ended with {simulation.get('status')}",
                    "source": "builtin:simulate_creation",
                },
                {
                    "lane": "visual",
                    "status": status,
                    "evidence": "renderable cinematic projection exists" if simulation.get("cinematic_projection", {}).get("available") else "cinematic projection unavailable",
                    "source": "builtin:simulate_creation",
                },
            ],
            "simulation": simulation,
            "perfect_claimed": False,
        }

    if kind in {"project", "software", "game"} and "path" in artifact:
        target = Path(str(artifact["path"])).expanduser()
        if not target.is_absolute():
            target = root / target
        target = target.resolve()
        if not _allowed_creation_target(root, target):
            return {
                "schema": SELF_TEST_SCHEMA,
                "adapter": "uc-project-verifier",
                "status": "HOLD",
                "verification": [{
                    "lane": "functional",
                    "status": "HOLD",
                    "evidence": "self-test refused to treat the live UC machine body as an ordinary creation candidate",
                    "source": "builtin:verify_project boundary",
                }],
                "perfect_claimed": False,
            }
        try:
            report = validate_project(
                target,
                project_type=str(artifact.get("project_type", "generic")),
                checks=artifact.get("checks") if isinstance(artifact.get("checks"), list) else None,
                expected_files=artifact.get("expected_files") if isinstance(artifact.get("expected_files"), dict) else None,
                expected_file_digests=artifact.get("expected_file_digests") if isinstance(artifact.get("expected_file_digests"), dict) else None,
            )
        except ProjectError as exc:
            return {
                "schema": SELF_TEST_SCHEMA,
                "adapter": "uc-project-verifier",
                "status": "FAIL",
                "verification": [{"lane": "functional", "status": "FAIL", "evidence": str(exc), "source": "builtin:verify_project"}],
                "details": exc.details,
                "perfect_claimed": False,
            }
        passed = report.get("passed") is True
        status = "PASS" if passed else "FAIL"
        return {
            "schema": SELF_TEST_SCHEMA,
            "adapter": "uc-project-verifier",
            "status": status,
            "verification": [
                {
                    "lane": "structural",
                    "status": status,
                    "evidence": f"project validator passed={passed}",
                    "source": "builtin:verify_project",
                },
                {
                    "lane": "functional",
                    "status": status,
                    "evidence": f"project checks passed={passed}",
                    "source": "builtin:verify_project",
                },
            ],
            "report": report,
            "perfect_claimed": False,
        }

    return {
        "schema": SELF_TEST_SCHEMA,
        "adapter": "none",
        "status": "NOT_TESTED",
        "verification": [
            {
                "lane": "generic",
                "status": "NOT_TESTED",
                "evidence": "",
                "source": "no deterministic self-test adapter registered for this artifact kind",
            }
        ],
        "kind": kind or "generic",
        "perfect_claimed": False,
        "next_gate": "attach an applicable UC simulator, project verifier, render observer, domain test, or external evidence provider before claiming this lane was tested",
    }


def inspect_chamber() -> dict[str, Any]:
    return {
        "schema": CHAMBER_SCHEMA,
        "rounds": [copy.deepcopy(row) for row in ROUND_PHASES],
        "survivors_per_round": SURVIVOR_COUNT,
        "final_outputs": SURVIVOR_COUNT,
        "final_evidence_lanes": list(FINAL_EVIDENCE_LANES),
        "operations": ["inspect", "prepare", "advance-round", "self-test-candidate"],
        "truth_boundary": [
            "creative team packets are prepared deterministically but team reasoning/output is external until supplied",
            "ranking is exactly the existing specialist tournament's supplied independent judgement result",
            "self-test executes only registered deterministic adapters; unsupported media return NOT_TESTED",
            "two finalists are retained after round seven but are never auto-accepted, auto-canonized, or called perfect",
        ],
    }


def operate_evolution_aftertouch(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "prepare")).strip().casefold()
    if operation in {"inspect", "summary"}:
        return {"truth_status": "DECLARED_EVOLUTION_AFTERTOUCH_CHAMBER_V0_1", **inspect_chamber()}
    if operation in {"prepare", "start", "prepare-chamber"}:
        return prepare_chamber(
            root,
            inputs.get("challenge"),
            criteria=inputs.get("criteria"),
            pool_size=inputs.get("pool_size", 20),
            team_size=inputs.get("team_size", 4),
            max_teams=inputs.get("max_teams", 8),
            seed=inputs.get("seed"),
        )
    if operation in {"advance", "advance-round", "judge-round"}:
        return advance_round(root, inputs.get("chamber"), inputs.get("submissions"), inputs.get("judgements"))
    if operation in {"self-test", "self-test-candidate", "test-candidate"}:
        return self_test_candidate(root, inputs.get("candidate"))
    raise EvolutionAftertouchError(
        "evolution-aftertouch operation is unsupported",
        {"operation": operation, "supported_operations": inspect_chamber()["operations"]},
    )

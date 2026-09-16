"""Offline professional stations with evidence-scoped, deterministic practice memory.

Professional reasoning stays an explicit judgment boundary. These stations run
selected UC tools and observe real artifacts; they do not impersonate people.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .adoption_lock import candidate_adoption_lock
from .atomic import atomic_write_json
from .profession_target_evidence import (
    ACTION_KIND as TARGET_EVIDENCE_KIND,
    EVIDENCE_SCOPE,
    LANE_OWNERS,
    assess_target_evidence,
    target_contract,
)
from .stepwise_workflow import validate_step_plan

SCHEMA = "axm.uc-profession-crew.v1"
MAX_RUNS = 256
MAX_STEPS = 32
CATALOG_PATH = Path(__file__).parent / "data/professions/catalog.json"
TEAMS = {
    "software": ["software-architect", "backend-engineer", "software-maintainer", "software-qa-playtest", "integration-release-engineer"],
    "web": ["frontend-engineer", "visual-designer", "software-qa-playtest", "integration-release-engineer"],
    "3d": ["3d-artist", "art-director", "technical-artist", "graphics-engineer", "software-qa-playtest"],
    "animation": ["motion-designer", "technical-artist", "3d-artist", "graphics-engineer", "software-qa-playtest"],
    "game": ["gameplay-engineer", "game-systems-designer", "world-encounter-designer", "technical-artist", "sound-designer", "software-qa-playtest"],
    "audio": ["sound-designer", "software-qa-playtest"],
    "document": ["technical-writer", "visual-designer", "software-qa-playtest"],
}
# Deliberately bounded adapters: an unfamiliar capability must never acquire an
# execution permission or a PASS merely by appearing in the live registry.
PROJECT_KINDS = {"software-project", "python-project", "static-web-project"}
GLB_KINDS = {"procedural-3d-asset", "procedural-glb-asset", "deterministic-3d-model", "glb-scene-asset"}
TEXT_KINDS = {"text-file", "json-file"}
SUPPORTED = PROJECT_KINDS | GLB_KINDS | TEXT_KINDS | {"verify-project", TARGET_EVIDENCE_KIND}


class ProfessionCrewError(ValueError):
    pass


def _hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def _id(value: Any, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,95}", value):
        raise ProfessionCrewError(f"{label} must be a simple identifier (1..96 characters)")
    return value


def _catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def _revision(root: Path) -> str:
    # A changed tool invalidates reuse. This is cache scope, not a new machine
    # authority or mandatory baseline/ledger. All Python providers are included.
    rows = []
    for base in [Path(__file__).parent, root / "capabilities/live"]:
        for path in sorted(base.glob("*.py" if base.name != "live" else "*.json")):
            rows.append([base.name, path.name, hashlib.sha256(path.read_bytes()).hexdigest()])
    return _hash(rows)


def _store_path(root: Path, crew_id: str) -> Path:
    path = root / "state/profession-crews" / (_id(crew_id, "crew_id") + ".json")
    # Never follow an existing link into unrelated state.
    for part in [root / "state", path.parent, path]:
        if part.is_symlink():
            raise ProfessionCrewError("crew state must not use symbolic links")
    return path


def _load(root: Path, crew_id: str) -> dict:
    path = _store_path(root, crew_id)
    if not path.exists():
        return {"schema": SCHEMA, "crew_id": crew_id, "runs": {}, "practice": {}}
    state = json.loads(path.read_text(encoding="utf-8"))
    if state.get("schema") != SCHEMA or state.get("crew_id") != crew_id:
        raise ProfessionCrewError("unsupported or mismatched crew state; preserve it for explicit migration")
    if not isinstance(state.get("runs"), dict) or not isinstance(state.get("practice"), dict):
        raise ProfessionCrewError("invalid crew state")
    return state


def _target(root: Path, value: Any) -> Path:
    from .capabilities import _is_machine_body_path
    if not isinstance(value, str) or not value.strip():
        raise ProfessionCrewError("station action requires an explicit path")
    raw = Path(value).expanduser()
    raw = raw if raw.is_absolute() else root / raw
    for part in [raw, *raw.parents]:
        if part.is_symlink():
            raise ProfessionCrewError("station artifacts must not use symbolic links")
    target = raw.resolve()
    if _is_machine_body_path(root, target):
        raise ProfessionCrewError("profession stations cannot write or assess protected machine state")
    return target


def _project_type(kind: str, inputs: dict) -> str:
    return str(inputs.get("project_type", {"python-project": "python", "static-web-project": "static-web"}.get(kind, "generic")))


def _fingerprint(path: Path) -> str:
    if path.is_symlink():
        raise ProfessionCrewError("artifact is a symbolic link")
    if path.is_file():
        return hashlib.sha256(path.read_bytes()).hexdigest()
    if path.is_dir():
        rows = []
        for file in sorted(path.rglob("*")):
            if file.is_symlink():
                raise ProfessionCrewError("artifact contains a symbolic link")
            if file.is_file():
                rows.append([file.relative_to(path).as_posix(), hashlib.sha256(file.read_bytes()).hexdigest()])
        return _hash(rows)
    raise ProfessionCrewError("artifact is missing")


def _observe(root: Path, action: dict) -> dict:
    """Read artifacts afresh, never promote provider/caller 'passed' fields."""
    from .project import validate_project
    from .procedural_3d import build_glb, verify_glb
    kind, inputs = action["kind"], action["inputs"]
    path = _target(root, inputs.get("path"))
    if kind == TARGET_EVIDENCE_KIND:
        report = assess_target_evidence(path, inputs)
        return {"status": report["status"], "artifact": str(path),
                "artifact_digest": report["artifact_sha256"], "target_evidence": report,
                "evidence_origin": "EXTERNAL_EVIDENCE_PACKET", "limitations": report["nonclaims"],
                "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED"}
    if kind in PROJECT_KINDS | {"verify-project"}:
        report = validate_project(path, project_type=_project_type(kind, inputs), checks=inputs.get("checks"),
                                  expected_files=inputs.get("files", inputs.get("expected_files")), expected_file_digests=inputs.get("expected_file_digests"))
        checks = report["checks"]
        limits = report["limitations"]
    elif kind in GLB_KINDS:
        expected = build_glb(inputs["specification"])["specification_sha256"]
        report = verify_glb(path.read_bytes(), expected_spec_digest=expected)
        checks = [{"type": "glb-geometry", "passed": report["passed"]}]
        limits = ["Geometry/container checks do not prove artistic quality, animation, engine import or rendered appearance."]
    elif kind in TEXT_KINDS:
        if kind == "text-file":
            passed = path.read_text(encoding="utf-8") == str(inputs["content"])
        else:
            passed = _hash(json.loads(path.read_text(encoding="utf-8"))) == _hash(inputs["value"])
        checks = [{"type": "exact-content", "passed": passed}]
        limits = ["Exact content integrity does not prove semantic or professional quality."]
    else:
        return {"status": "NOT_TESTED", "checks": [], "limitations": ["No registered artifact observer."]}
    return {"status": "PASS" if checks and all(c.get("passed") is True for c in checks) else "FAIL",
            "checks": checks, "artifact": str(path), "artifact_digest": _fingerprint(path), "limitations": limits,
            "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED"}


def plan_crew(root: Path, inputs: dict) -> dict:
    from .capabilities import CapabilityStore
    crew_id = _id(inputs.get("crew_id", "default"), "crew_id")
    work_type = inputs.get("work_type")
    if work_type not in TEAMS:
        raise ProfessionCrewError("work_type must be one of: " + ", ".join(TEAMS))
    context = inputs.get("context", {})
    if not isinstance(context, dict):
        raise ProfessionCrewError("context must be an object")
    source = _catalog()
    catalog = {r["id"]: r for r in source["professions"]}
    state = _load(root, crew_id)
    runtime = _revision(root)
    catalog_digest = _hash(source)
    raw_steps = inputs.get("steps")
    if not isinstance(raw_steps, list) or not 1 <= len(raw_steps) <= MAX_STEPS:
        raise ProfessionCrewError(f"steps must contain 1..{MAX_STEPS} explicit stations")
    steps, stations, assignments, handoff_professions = [], [], [], []
    for index, raw in enumerate(raw_steps):
        if not isinstance(raw, dict):
            raise ProfessionCrewError("each station must be an object")
        profession = raw.get("profession_id", TEAMS[work_type][0])
        if profession not in catalog:
            raise ProfessionCrewError(f"unknown profession: {profession}")
        if profession not in TEAMS[work_type] and profession != "developer-tools-engineer":
            raise ProfessionCrewError(f"profession {profession} has no declared fit for {work_type}")
        body = catalog[profession]["body"]
        skills = [s["id"] for s in body["skills"]]
        skill = raw.get("skill_id", skills[0])
        if skill not in skills:
            raise ProfessionCrewError(f"unknown skill for {profession}: {skill}")
        action = copy.deepcopy(raw.get("action"))
        if not isinstance(action, dict) or not isinstance(action.get("inputs", {}), dict):
            raise ProfessionCrewError("station action must contain kind and inputs")
        action.setdefault("inputs", {})
        kind = action.get("kind")
        if kind in PROJECT_KINDS:
            action["inputs"].setdefault("project_type", _project_type(kind, action["inputs"]))
        step_id = _id(raw.get("id", f"step-{index + 1}"), "step id")
        route = CapabilityStore(root).route(kind)
        automatic = kind in SUPPORTED and route is not None
        binding = {"work_type": work_type, "context": context, "profession": profession, "skill": skill,
                   "kind": kind, "project_type": action["inputs"].get("project_type"),
                   "runtime": runtime, "catalog": catalog_digest}
        if kind == TARGET_EVIDENCE_KIND:
            binding["target_contract"] = target_contract(action["inputs"])
            packet = action["inputs"]["packet"]
            lanes = (set(binding["target_contract"]["required_lanes"]) | set(packet["lanes"])
                     | {lane.strip() for lane in packet["required_lanes"]})
            handoff_professions.extend(LANE_OWNERS[lane] for lane in sorted(lanes))
        key = _hash(binding)
        practice = copy.deepcopy(state["practice"].get(key, {}))
        learned_preflight = kind in PROJECT_KINDS and bool(practice.get("failed_cases"))
        if automatic:
            _target(root, action["inputs"].get("path"))
            missing = CapabilityStore.missing_required_inputs(route, action["inputs"])
            if missing:
                raise ProfessionCrewError("missing station inputs: " + ", ".join(missing))
        station = {"id": step_id, "profession_id": profession, "skill_id": skill, "binding": binding,
                   "practice_key": key, "practice": practice, "learned_preflight": learned_preflight,
                   "automatic_execution": automatic, "action": action,
                   "judgment": raw.get("judgment", "NOT_TESTED"),
                   "fit_basis": "explicit work-type ownership table and caller-selected/default body skill; not a competence claim"}
        if kind == TARGET_EVIDENCE_KIND:
            station["evidence_scope"] = EVIDENCE_SCOPE
        if station["judgment"] not in {"NOT_TESTED", "REQUIRED"}:
            raise ProfessionCrewError("judgment must be NOT_TESTED or REQUIRED; machine cannot claim supplied approval")
        stations.append(station)
        assignments.append(profession)
        steps.append({"id": step_id, "purpose": raw.get("purpose", f"Execute the selected {profession} station"),
                      "mode": "action", "action": action, "depends_on": raw.get("depends_on", []),
                      "expected_evidence": ["Exact artifact observation and professional judgment gaps"],
                      "stop_condition": "Failure, unsupported observer or required judgment holds the job"})
    plan = validate_step_plan({"goal": inputs.get("goal"), "steps": steps}, maximum=MAX_STEPS)
    crew = []
    for profession in dict.fromkeys(TEAMS[work_type] + assignments + handoff_professions):
        row = catalog[profession]
        body = row["body"]
        crew.append({"id": profession, "status": body["status"], "scope": body["scope"],
                     "skills": body["skills"], "procedures": body["procedures"],
                     "failure_library": body["failure_library"], "handoffs": body["handoffs"],
                     "workflow_files": row["workflow_files"], "sources": row["sources"],
                     "execution_role": "assigned station" if profession in assignments else "consultation/handoff; not executed"})
    return {"schema": "axm.uc-profession-plan.v1", "crew_id": crew_id, "work_type": work_type,
            "context": context, "runtime_revision": runtime, "catalog_digest": catalog_digest,
            "source": source["origin"], "crew": crew, "stations": stations, "stepwise_plan": plan,
            "status": "PLANNED", "truth_boundary": "Bodies remain EXPERIMENTAL. Consultation cards are not executed specialists. Growth is local practice, not professional rank."}


def _preflight(action: dict) -> dict:
    from .project import build_project
    inputs = copy.deepcopy(action["inputs"])
    with tempfile.TemporaryDirectory(prefix="axm-crew-practice-") as tmp:
        result = build_project(Path(tmp) / "candidate", files=inputs["files"],
                               project_type=inputs.get("project_type", "generic"), checks=inputs.get("checks"),
                               publish_mode="grounded-draft")
        return result["validation"]


def _learn(state: dict, station: dict, observation: dict) -> None:
    # Even malformed packets or provider exceptions are not locally performed
    # target tests. Do not let a declaration teach either success or failure.
    if station["action"]["kind"] == TARGET_EVIDENCE_KIND:
        return
    if observation["status"] not in {"PASS", "FAIL"}:
        return
    # Repeating the same work under different run ids cannot manufacture growth.
    action = copy.deepcopy(station["action"])
    action["inputs"].pop("path", None)
    action["inputs"].pop("replace", None)
    case = _hash({"action": action, "artifact": observation.get("artifact_digest"), "status": observation["status"]})
    row = state["practice"].setdefault(station["practice_key"], {
        "binding": station["binding"], "passed_cases": [], "failed_cases": [], "failure_checks": [],
        "interpretation": "Distinct local observed cases; not a score, incentive, profession promotion or generalized competence."})
    field = "passed_cases" if observation["status"] == "PASS" else "failed_cases"
    if case not in row[field]:
        row[field].append(case)
    for check in observation.get("checks", []):
        if check.get("passed") is False and check.get("type") not in row["failure_checks"]:
            row["failure_checks"].append(check.get("type"))


def run_crew(root: Path, inputs: dict) -> dict:
    from .capabilities import CapabilityStore
    crew_id = _id(inputs.get("crew_id", "default"), "crew_id")
    run_id = _id(inputs.get("run_id"), "run_id")
    path = _store_path(root, crew_id)
    # Reuse UC's OS-managed nonblocking lock with a distinct crew identity.
    with candidate_adoption_lock(path):
        state = _load(root, crew_id)
        identity = _hash({k: v for k, v in inputs.items() if k not in {"operation", "run_id"}})
        prior = state["runs"].get(run_id)
        if prior:
            if prior["request_digest"] != identity:
                raise ProfessionCrewError("run_id already belongs to a different request")
            result = copy.deepcopy(prior)
            result["replayed"] = True
            result["status"] = "HOLD_INTERRUPTED" if result["status"] == "RUNNING" else result["status"]
            result["freshness"] = "RECORDED_RESULT_ONLY; use verify before relying on artifacts"
            return result
        if len(state["runs"]) >= MAX_RUNS:
            raise ProfessionCrewError("crew reached 256 retained jobs; export/preserve state and choose a new crew_id")
        plan = plan_crew(root, inputs)
        record = {"run_id": run_id, "request_digest": identity, "plan": plan, "status": "RUNNING", "observations": [],
                  "professional_acceptance": "NOT_TESTED", "visual_quality": "NOT_TESTED"}
        state["runs"][run_id] = record
        atomic_write_json(path, state)
        for station in plan["stations"]:
            if not station["automatic_execution"] or station["judgment"] == "REQUIRED":
                record["status"] = "HOLD_JUDGMENT" if station["judgment"] == "REQUIRED" else "HOLD_CAPABILITY_GAP"
                record["handoff"] = {"station": station["id"], "profession_id": station["profession_id"],
                                     "reason": "Required judgment or registered execution/observation adapter is unavailable"}
                break
            action = station["action"]
            try:
                if station["learned_preflight"]:
                    preflight = _preflight(action)
                    if preflight["passed"] is not True:
                        record["observations"].append({"station": station["id"], "status": "FAIL", "phase": "learned-preflight",
                                                       "checks": preflight["checks"], "target_written": False})
                        record["status"] = "HOLD_LEARNED_PREFLIGHT"
                        break
                route = CapabilityStore(root).route(action["kind"])
                CapabilityStore(root).invoke(route, action["inputs"])
                observed = _observe(root, action)
            except Exception as exc:
                # A failed tool call is a failure observation, never professional
                # success. Persist it, then stop; do not replay unknown writes.
                observed = {"status": "FAIL", "checks": [{"type": "execution-or-observation", "passed": False}],
                            "error": f"{type(exc).__name__}: {exc}", "side_effects": "inspect target; partial output may exist"}
            observed["station"] = station["id"]
            if action["kind"] == TARGET_EVIDENCE_KIND:
                observed["evidence_origin"] = "EXTERNAL_EVIDENCE_PACKET"
            record["observations"].append(observed)
            _learn(state, station, observed)
            atomic_write_json(path, state)
            if observed["status"] != "PASS":
                record["status"] = "HOLD_TARGET_EVIDENCE" if observed["status"] == "HOLD" else "HOLD_FAILED_CHECK"
                if action["kind"] == TARGET_EVIDENCE_KIND:
                    record["handoff"] = {"station": station["id"], "profession_id": station["profession_id"],
                        "reason": "Supply or correct exact-artifact target evidence; no target test was independently reproduced",
                        "requirements": observed.get("target_evidence", {}).get("handoff_requirements", [
                            {"lane": None, "profession_id": "technical-artist", "reason": "EXECUTION_OR_OBSERVATION_ERROR"}])}
                break
        else:
            record["status"] = "COMPLETE_BOUNDED_CHECKS"
        atomic_write_json(path, state)
        return copy.deepcopy(record)


def verify_run(root: Path, inputs: dict) -> dict:
    state = _load(root, _id(inputs.get("crew_id", "default"), "crew_id"))
    run = state["runs"].get(_id(inputs.get("run_id"), "run_id"))
    if run is None:
        raise ProfessionCrewError("unknown run_id")
    checks = []
    for station, prior in zip(run["plan"]["stations"], run["observations"]):
        if "artifact_digest" not in prior:
            checks.append({"station": station["id"], "status": "NOT_TESTED"})
            continue
        try:
            fresh = _observe(root, station["action"])
            fresh["same_artifact"] = fresh.get("artifact_digest") == prior["artifact_digest"]
            if not fresh["same_artifact"]:
                fresh["status"] = "STALE"
        except Exception as exc:
            fresh = {"status": "STALE", "error": str(exc)}
        checks.append({"station": station["id"], **fresh})
    runtime_matches = run["plan"]["runtime_revision"] == _revision(root)
    catalog_matches = run["plan"]["catalog_digest"] == _hash(_catalog())
    complete = run["status"] == "COMPLETE_BOUNDED_CHECKS" and len(checks) == len(run["plan"]["stations"])
    return {"status": "PASS" if complete and runtime_matches and catalog_matches and all(c["status"] == "PASS" for c in checks) else "NOT_CURRENT_PASS",
            "checks": checks, "runtime_matches": runtime_matches, "catalog_matches": catalog_matches,
            "professional_acceptance": "NOT_TESTED", "visual_quality": "NOT_TESTED"}


def prepare_profession_specialists(root: Path, inputs: dict) -> dict:
    """Give the existing specialist tournament actual professional machinery.

    The universal lenses retain their identities and voting history. The
    profession bodies are their work contracts, not extra votes or new rank.
    """
    from .specialist_pool import _digest, prepare_tournament
    plan = plan_crew(root, inputs)
    tournament = prepare_tournament(root, inputs["goal"], criteria=inputs.get("criteria"),
                                    pool_size=inputs.get("pool_size", 20), team_size=inputs.get("team_size", 4),
                                    max_teams=inputs.get("max_teams", 8), seed=inputs.get("seed"))
    tournament["profession_workflow"] = plan
    for packet in tournament["parallel_challenge_packets"]:
        packet["profession_workflow_digest"] = _hash(plan)
        packet["professional_contracts"] = [{"id": p["id"], "scope": p["scope"], "procedures": p["procedures"],
                                              "handoffs": p["handoffs"], "sources": p["sources"]} for p in plan["crew"]]
        packet["station_practice"] = [{"id": s["id"], "profession_id": s["profession_id"],
                                        "practice": s["practice"], "learned_preflight": s["learned_preflight"]} for s in plan["stations"]]
        packet["required_submission"]["profession_handoffs"] = "Identify station-owned work, exact tool/artifact evidence, unresolved judgment and owning profession. Votes never update crew practice."
    tournament.pop("tournament_digest", None)
    tournament["tournament_digest"] = _digest(tournament)
    return tournament


def operate_profession_crew(root: Path, inputs: dict) -> dict:
    root = Path(root).resolve()
    operation = inputs.get("operation", "inspect")
    if operation == "catalog":
        return {"catalog": _catalog(), "workflows": TEAMS, "execution_adapters": sorted(SUPPORTED)}
    if operation == "plan":
        return plan_crew(root, inputs)
    if operation == "prepare-specialists":
        return prepare_profession_specialists(root, inputs)
    if operation == "run":
        return run_crew(root, inputs)
    if operation == "verify":
        return verify_run(root, inputs)
    if operation == "inspect":
        return _load(root, _id(inputs.get("crew_id", "default"), "crew_id"))
    raise ProfessionCrewError(f"unsupported profession crew operation: {operation}")

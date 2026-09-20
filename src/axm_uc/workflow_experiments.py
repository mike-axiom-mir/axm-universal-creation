"""Bounded before/after iteration, actual outcomes, robust ranking and confirmation."""
from __future__ import annotations

from collections import Counter
import hashlib
import math
from pathlib import Path

from .atomic import atomic_write_json
from .atlas_pipeline import _output, build_intent
from .creation_atlas import digest
from .workflow_discovery import choice_order, compile_candidate, plan
from .workflow_memory import OBSERVATION_SCHEMA, retain


def _diagnose(run, candidate):
    by_id = {n["id"]: n for n in candidate["program"]["nodes"]}
    failed = [c for c in run.get("checks", []) if not c["passed"]]
    step = (run.get("error") or {}).get("step") or (failed[0]["check"]["step"] if failed else None)
    result = run.get("steps", {}).get(step, {})
    evidence = result.get("evidence", {})
    return {"step": step, "operator": by_id.get(step, {}).get("operator"),
            "failed_checks": failed, "error": run.get("error"), "metrics": result.get("metrics", {}),
            "tool_checks": [c for c in evidence.get("checks", []) if not c.get("passed")],
            "not_executed": [n["id"] for n in candidate["program"]["nodes"] if n["id"] not in run.get("steps", {})]}


def _measure(run, candidate, request):
    metrics = {}
    for goal, ref in candidate["program"]["outputs"].items():
        values = run.get("steps", {}).get(ref["node"], {}).get("metrics", {})
        needed = {c["metric"] for c in request["goals"][goal]["checks"]}
        needed.update(o["metric"] for o in request["objectives"] if o["goal"] == goal)
        metrics[goal] = {key: values[key] for key in sorted(needed)
                         if type(values.get(key)) in {int, float} and math.isfinite(values[key])}
        if set(metrics[goal]) != needed:
            return metrics, False
    return metrics, True


def _deficits(metrics, objectives):
    values = []
    for obj in objectives:
        measured = metrics[obj["goal"]][obj["metric"]]
        delta = measured - obj["target"] if obj["direction"] == "minimize" else obj["target"] - measured
        values.append(max(0., delta / obj["scale"]))
    return values


def _rank(cases, request):
    worst = [max(_deficits(c["metrics"], request["objectives"])[i] for c in cases)
             for i in range(len(request["objectives"]))]
    score = sum(d * o["weight"] for d, o in zip(worst, request["objectives"]))
    return {"weighted_worst_deficit": score, "objective_deficits": worst,
            "targets_satisfied": all(d == 0 for d in worst)}


def _prefixes(candidate, request, operators, scenario):
    """Context-sensitive failure reuse, including goal checks on every ancestor."""
    blueprint, intent = compile_candidate(candidate, request, operators, scenario)
    checks = {s["id"]: s["checks"] for s in blueprint["steps"]}
    values, signatures = intent["parameters"], {}
    for node in candidate["program"]["nodes"]:
        # Check step ids are structural but not necessary to prefix identity.
        own_checks = [{k: v for k, v in c.items() if k != "step"} for c in checks[node["id"]]]
        signatures[node["id"]] = digest({"operator": operators[node["operator"]], "checks": own_checks,
            "inputs": {p: {"value": values[r["source"]]["value"]} if "source" in r
                       else {"prefix": signatures[r["node"]]} for p, r in node["inputs"].items()}})
    return signatures


def _case(root, candidate, request, operators, scenario, path):
    blueprint, intent = compile_candidate(candidate, request, operators, scenario)
    try:
        run = build_intent(root, intent, str(path), candidate_blueprint=blueprint)
    except (ValueError, RuntimeError, OSError) as exc:
        # An unreadable/oversized evidence file or other boundary failure cannot
        # terminate the search with an apparently successful partial candidate.
        run = {"status": "HOLD_EVIDENCE_ERROR", "error": {"step": None, "message": str(exc)}}
    metrics, measured = _measure(run, candidate, request)
    passed = run["status"] == "CHECKS_PASSED" and measured
    products = {p: sha for p, sha in run.get("files", {}).items()
                if Path(p).suffix in {".glb", ".png", ".wav", ".js", ".py", ".html", ".css"}}
    report_path = path / "run.json"
    return {"scenario": scenario["id"], "status": "PASS" if passed else "FAIL", "metrics": metrics,
            "run_path": str(path), "run_sha256": hashlib.sha256(report_path.read_bytes()).hexdigest() if report_path.is_file() else None,
            "run_status": run["status"], "product_hashes": products,
            "diagnosis": None if passed else _diagnose(run, candidate),
            "passed_steps": sum(r.get("status") == "PASS" for r in run.get("steps", {}).values())}


def _distance(candidate, anchor, request):
    if anchor is None:
        return (0, 0)
    left = Counter(n["operator"] for n in candidate["program"]["nodes"])
    right = Counter(n["operator"] for n in anchor["program"]["nodes"])
    topology = sum((left - right).values()) + sum((right - left).values())
    a, b = candidate["program"]["choices"], anchor["program"]["choices"]
    changes = sum(a.get(k) != b.get(k) for k in set(a) | set(b))
    return topology, changes


def experiment(root, raw, path, *, memory=None, expected_plan=None):
    fresh = plan(root, raw, memory=memory)
    if expected_plan is not None and expected_plan != fresh["plan_sha256"]:
        return {"status": "HOLD_STALE_PLAN", "fresh_plan": fresh}
    if fresh["status"] != "READY":
        return {"status": fresh["status"], "plan": fresh}
    target = _output(root, path)
    if memory is not None:
        collection = _output(root, memory)
        if target == collection or target in collection.parents or collection in target.parents:
            raise ValueError("experiment output and memory must be separate directories")
    if target.exists():
        raise ValueError("workflow experiment output already exists")
    target.mkdir(parents=True)
    atomic_write_json(target / "plan.json", fresh)
    request, operators = fresh["request"], fresh["operators"]
    limits = request["budget"]
    scenarios = [{"id": "baseline", "inputs": {}}, *request["scenarios"]]
    pending, outcomes, rounds, failures = list(fresh["candidates"]), [], [], {}
    trials, anchor, best, most_progress = 0, None, None, -1
    stop_reason = "candidate_space_exhausted"

    def checkpoint():
        atomic_write_json(target / "progress.json", {"completed_trials": trials, "outcomes": outcomes,
                          "rounds": rounds, "remaining_candidates": len(pending), "resumable": False,
                          "note": "Interrupted work is evidence only. Start a fresh experiment; no partial admission."})

    for round_number in range(1, limits["rounds"] + 1):
        if not pending:
            break
        iteration = {"round": round_number, "mode": "explore" if anchor is None else "refine" if best else "repair",
                     "basis": None if anchor is None else anchor["id"], "attempts": [], "pruned": []}
        # Reject only identical failed dependency closures under identical checks.
        survivors = []
        for candidate in pending:
            cached = None
            for scenario in scenarios:
                for node, fingerprint in _prefixes(candidate, request, operators, scenario).items():
                    if fingerprint in failures:
                        cached = {"candidate": candidate["id"], "scenario": scenario["id"], "step": node,
                                  "because": failures[fingerprint]}
                        break
                if cached:
                    break
            if cached:
                iteration["pruned"].append(cached)
                outcomes.append({"candidate": candidate["id"], "signature": candidate["signature"],
                                 "status": "PRUNED_IDENTICAL_FAILURE", "evidence": cached})
            else:
                survivors.append(candidate)
        pending = sorted(survivors, key=lambda c: (_distance(c, anchor, request), not c["reused_structure"], c["cost"], choice_order(c), c["id"]))
        for _ in range(min(limits["batch_size"], len(pending))):
            if trials >= limits["trials"]:
                stop_reason = "trial_budget"
                break
            candidate = pending.pop(0)
            cases, confirmation, status = [], [], "INCOMPLETE"
            for scenario in scenarios:
                if trials >= limits["trials"]:
                    break
                trial_path = target / "trials" / (f"{trials + 1:04d}-" + scenario["id"])
                observed = _case(root, candidate, request, operators, scenario, trial_path)
                trials += 1
                cases.append(observed)
                if observed["status"] != "PASS":
                    status = "REJECTED"
                    diagnosis = observed["diagnosis"]
                    if diagnosis["step"] and observed["run_status"] == "HOLD_FAILED_CHECK":
                        fingerprint = _prefixes(candidate, request, operators, scenario)[diagnosis["step"]]
                        failures[fingerprint] = {"candidate": candidate["id"], "scenario": scenario["id"],
                                                 "diagnosis": diagnosis, "run_sha256": observed["run_sha256"]}
                    if best is None and observed["passed_steps"] > most_progress:
                        most_progress, anchor = observed["passed_steps"], candidate
                    break
            ranking = None
            if len(cases) == len(scenarios) and all(c["status"] == "PASS" for c in cases):
                ranking = _rank(cases, request)
                # Rebuild the hardest observed cases in new directories. No cached PASS.
                hardest = sorted(cases, key=lambda c: (-sum(d * o["weight"] for d, o in
                                 zip(_deficits(c["metrics"], request["objectives"]), request["objectives"])), c["scenario"]))
                for index in range(limits["confirmation_cases"]):
                    if trials >= limits["trials"]:
                        break
                    prior = hardest[index % len(hardest)]
                    scenario = next(s for s in scenarios if s["id"] == prior["scenario"])
                    observed = _case(root, candidate, request, operators, scenario,
                                     target / "trials" / f"{trials + 1:04d}-confirmation")
                    trials += 1
                    observed["repeatable"] = (observed["status"] == "PASS" and observed["metrics"] == prior["metrics"]
                                               and observed["product_hashes"] == prior["product_hashes"])
                    confirmation.append(observed)
                    if not observed["repeatable"]:
                        status = "CONFIRMATION_FAILED"
                        break
                if len(confirmation) == limits["confirmation_cases"] and all(c["repeatable"] for c in confirmation):
                    status = "CONFIRMED"
            observation = {"schema": OBSERVATION_SCHEMA, "status": status, "candidate": candidate["id"],
                           "signature": candidate["signature"], "pins": fresh["pins"], "intent": request["intent"],
                           "request_sha256": digest(request), "program": candidate["program"],
                           "source_values": {k: request["inputs"][k]["values"][v] for k, v in candidate["program"]["choices"].items()},
                           "validation_scope": {"goals": request["goals"], "objectives": request["objectives"], "scenarios": scenarios},
                           "cases": cases, "confirmation": confirmation, "ranking": ranking,
                           "cost": candidate["cost"], "reused_structure": candidate["reused_structure"],
                           "prior_evidence_current": candidate["prior_evidence_current"],
                           "repeatability_scope": "Declared goal metrics and generated GLB/PNG/WAV/code bytes; not all environments or all inputs.",
                           "automatic_canon_admission": False}
            atomic_write_json(target / "observations" / (candidate["id"] + ".json"), observation)
            retained_id = retain(root, memory, observation, candidate, request, operators)
            outcome = {"candidate": candidate["id"], "signature": candidate["signature"], "status": status,
                       "ranking": ranking, "cost": candidate["cost"], "observation": "observations/" + candidate["id"] + ".json",
                       "retained_observation": retained_id}
            outcomes.append(outcome)
            iteration["attempts"].append({"candidate": candidate["id"], "status": status,
                                          "failed": next((c["diagnosis"] for c in cases if c["status"] != "PASS"), None)})
            if status == "CONFIRMED":
                key = (ranking["weighted_worst_deficit"], candidate["cost"], candidate["id"])
                if best is None or key < best:
                    best, anchor = key, candidate
            checkpoint()
        rounds.append(iteration)
        checkpoint()
        if trials >= limits["trials"]:
            stop_reason = "trial_budget"
            break
    else:
        if pending:
            stop_reason = "round_budget"
    ranked = sorted((o for o in outcomes if o["status"] == "CONFIRMED"),
                    key=lambda o: (o["ranking"]["weighted_worst_deficit"], o["cost"], o["candidate"]))
    frontier = [o["candidate"] for o in ranked if not any(
        all(a <= b for a, b in zip(other["ranking"]["objective_deficits"], o["ranking"]["objective_deficits"]))
        and any(a < b for a, b in zip(other["ranking"]["objective_deficits"], o["ranking"]["objective_deficits"]))
        for other in ranked)]
    report = {"schema": "axm.workflow-experiment-result/v0.1", "status": "VERIFIED_WORKFLOWS" if ranked else "HOLD_NO_CONFIRMED_WORKFLOW",
              "path": str(target), "plan_sha256": fresh["plan_sha256"], "trials": trials, "rounds": rounds,
              "outcomes": outcomes, "ranked": ranked, "pareto_frontier": frontier,
              "selected": ranked[0] if ranked else None, "untried": [c["id"] for c in pending],
              "retained_structures": len({o["signature"] for o in ranked}) if memory else 0,
              "stop_reason": stop_reason, "search": fresh["search"], "automatic_canon_admission": False,
              "boundary": "Bounded experimental evidence, not statistical confidence or global optimality. Every reuse reruns current goals; unavailable physics, aesthetic or target checks stay gaps."}
    report["report_sha256"] = digest(report)
    atomic_write_json(target / "report.json", report)
    return report

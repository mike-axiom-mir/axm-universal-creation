"""Finite, explicit intent and operator contracts for reproducible workflow search."""
from __future__ import annotations

from copy import deepcopy
import json
import math
import re

from .creation_atlas import canonical, digest, local_file, text

REQUEST_SCHEMA = "axm.workflow-experiment/v0.1"
CATALOG_SCHEMA = "axm.workflow-operators/v0.1"
NAME = re.compile(r"[a-z][a-z0-9_-]{0,63}\Z")
LIMITS = {"states": (2000, 20000), "plans": (24, 128), "steps": (10, 16),
          "trials": (24, 256), "rounds": (8, 128), "batch_size": (3, 16), "confirmation_cases": (1, 4)}


def name(value):
    if not isinstance(value, str) or not NAME.fullmatch(value):
        raise ValueError("names require lowercase letters, digits, hyphens or underscores")
    return value


def type_contract(value):
    if (not isinstance(value, dict) or not value.get("kind") or len(value) > 12
            or any(not isinstance(k, str) or not isinstance(v, str) or not v for k, v in value.items())):
        raise ValueError("type requires a kind and explicit string-valued attributes")
    return value


def matches(provided, required):
    return all(provided.get(k) == v for k, v in required.items())


def number(value, label):
    if type(value) not in {int, float} or not math.isfinite(value) or abs(value) > 1e12:
        raise ValueError(label + " must be finite and within +/- 1e12")
    return value


def load_operators(root):
    from pathlib import Path
    operators, source_kinds = {}, set()
    for path in sorted((Path(root) / "atlas/operators").glob("*.json")):
        body = json.loads(local_file(root, path.relative_to(root).as_posix()).read_text())
        if set(body) != {"schema", "source_kinds", "operators"} or body["schema"] != CATALOG_SCHEMA:
            raise ValueError("invalid workflow operator catalog")
        if not isinstance(body["source_kinds"], list):
            raise ValueError("operator source kinds must be a list")
        source_kinds.update(name(k) for k in body["source_kinds"])
        for raw in body["operators"]:
            op = deepcopy(raw)
            required = {"id", "version", "purpose", "capability", "operation", "needs", "provides", "metrics", "cost", "dependencies", "limitations"}
            if set(op) - (required | {"identity_from"}) or not required <= set(op):
                raise ValueError("invalid workflow operator fields")
            identity = name(op["id"])
            if identity in operators or len(operators) >= 64:
                raise ValueError("duplicate operator or catalog exceeds 64 operators")
            for field in ("version", "purpose", "capability", "operation"):
                text(op[field], "operator " + field)
            if not isinstance(op["needs"], dict) or not 1 <= len(op["needs"]) <= 8:
                raise ValueError("operator requires 1..8 input ports")
            for port, contract in op["needs"].items():
                name(port)
                type_contract(contract)
            type_contract(op["provides"])
            if not isinstance(op["metrics"], dict) or len(op["metrics"]) > 32:
                raise ValueError("operator metric contract must be a bounded map")
            for metric, unit in op["metrics"].items():
                name(metric)
                text(unit, "metric unit")
            if not 0 < number(op["cost"], "declared cost") <= 100000:
                raise ValueError("operator cost must be positive and bounded")
            if not isinstance(op["dependencies"], list) or not isinstance(op["limitations"], list):
                raise ValueError("operator dependencies and limitations must be lists")
            if "identity_from" in op and op["identity_from"] not in op["needs"]:
                raise ValueError("identity_from must refer to an input port")
            op["source"] = {"path": path.relative_to(root).as_posix(), "sha256": digest(body)}
            operators[identity] = op
    return operators, source_kinds


def validate_request(raw, source_kinds):
    if not isinstance(raw, dict) or set(raw) - {"schema", "intent", "inputs", "goals", "objectives", "scenarios", "budget", "operators"}:
        raise ValueError("unsupported workflow experiment fields")
    if raw.get("schema") != REQUEST_SCHEMA or len(canonical(raw).encode()) > 2_000_000:
        raise ValueError("workflow request needs its schema and at most 2 MB")
    request = deepcopy(raw)
    text(request.get("intent"), "intent")
    inputs, goals = request.get("inputs"), request.get("goals")
    if not isinstance(inputs, dict) or not 1 <= len(inputs) <= 12:
        raise ValueError("workflow requires 1..12 explicit input sources")
    for identity, source in inputs.items():
        name(identity)
        if not isinstance(source, dict) or set(source) != {"type", "values"}:
            raise ValueError("source needs type and values")
        type_contract(source["type"])
        if source["type"]["kind"] not in source_kinds:
            raise ValueError("no declared source adapter for kind: " + source["type"]["kind"])
        if not isinstance(source["values"], list) or not 1 <= len(source["values"]) <= 8:
            raise ValueError("source requires 1..8 candidate values")
        if any(not isinstance(v, dict) for v in source["values"]):
            raise ValueError("source values are retained JSON construction objects, not unpinned external paths")
    if not isinstance(goals, dict) or not 1 <= len(goals) <= 8:
        raise ValueError("workflow requires 1..8 measured goals")
    for identity, goal in goals.items():
        name(identity)
        if not isinstance(goal, dict) or set(goal) - {"type", "checks", "same_origin_as", "uses_goal"}:
            raise ValueError("goal needs type/checks and optional same_origin_as/uses_goal")
        type_contract(goal.get("type"))
        checks = goal.get("checks")
        if not isinstance(checks, list) or not 1 <= len(checks) <= 16:
            raise ValueError("every goal needs 1..16 observable numeric checks")
        for check in checks:
            if (not isinstance(check, dict) or set(check) - {"metric", "unit", "min", "max"}
                    or not {"metric", "unit"} <= set(check) or not {"min", "max"} & set(check)):
                raise ValueError("goal check requires metric, unit and min/max")
            name(check["metric"])
            text(check["unit"], "check unit")
            for key in ("min", "max"):
                if key in check:
                    number(check[key], key)
            if check.get("min", -math.inf) > check.get("max", math.inf):
                raise ValueError("goal minimum exceeds maximum")
        for relation in ("same_origin_as", "uses_goal"):
            if relation in goal and (goal[relation] not in goals or goal[relation] == identity):
                raise ValueError("goal relation must refer to a different goal")
    ordered, pending = [], set(goals)
    while pending:
        ready = sorted(g for g in pending if all(goals[g].get(r) in {None, *ordered} for r in ("same_origin_as", "uses_goal")))
        if not ready:
            raise ValueError("cyclic goal origin constraints")
        ordered.extend(ready)
        pending.difference_update(ready)
    objectives = request.setdefault("objectives", [])
    if not isinstance(objectives, list) or len(objectives) > 16:
        raise ValueError("at most 16 ranking objectives")
    for obj in objectives:
        if not isinstance(obj, dict) or set(obj) != {"goal", "metric", "unit", "direction", "target", "scale", "weight"}:
            raise ValueError("objective requires goal, metric, unit, direction, target, scale and weight")
        if obj["goal"] not in goals or obj["direction"] not in {"minimize", "maximize"}:
            raise ValueError("unknown objective goal or direction")
        name(obj["metric"])
        text(obj["unit"], "objective unit")
        for key in ("target", "scale", "weight"):
            number(obj[key], key)
        if obj["scale"] < 1e-12 or obj["weight"] <= 0:
            raise ValueError("objective scale must be at least 1e-12 and weight positive")
    for goal_id, goal in goals.items():
        units = {}
        for check in [*goal["checks"], *(o for o in objectives if o["goal"] == goal_id)]:
            prior = units.setdefault(check["metric"], check["unit"])
            if prior != check["unit"]:
                raise ValueError("conflicting units for one goal measurement")
    scenarios = request.setdefault("scenarios", [])
    if not isinstance(scenarios, list) or len(scenarios) > 3:
        raise ValueError("at most three stress scenarios in addition to baseline")
    seen = {"baseline"}
    for scenario in scenarios:
        if not isinstance(scenario, dict) or set(scenario) != {"id", "inputs"}:
            raise ValueError("scenario requires id and input overrides")
        identity = name(scenario["id"])
        if identity in seen or not isinstance(scenario["inputs"], dict) or set(scenario["inputs"]) - set(inputs):
            raise ValueError("duplicate scenario or unknown input override")
        seen.add(identity)
        if any(not isinstance(v, dict) for v in scenario["inputs"].values()):
            raise ValueError("scenario overrides must be JSON construction objects")
    budget = request.setdefault("budget", {})
    if not isinstance(budget, dict) or set(budget) - set(LIMITS):
        raise ValueError("unsupported workflow budget")
    for key, (default, maximum) in LIMITS.items():
        value = budget.setdefault(key, default)
        if type(value) is not int or not 1 <= value <= maximum:
            raise ValueError(f"{key} budget must be 1..{maximum}")
    if "operators" in request and (not isinstance(request["operators"], list) or not request["operators"]
                                  or len(set(request["operators"])) != len(request["operators"])):
        raise ValueError("operator selection must be a nonempty unique list")
    return request, ordered

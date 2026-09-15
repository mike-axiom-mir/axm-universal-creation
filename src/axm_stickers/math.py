"""Deterministic mathematical families for reusable creative parts.

The contract is deliberately small and declarative. It resolves bounded numeric
parameters, named variants, derived values and explicit constraints without
executing arbitrary code or claiming physical/rendered truth.
"""
from __future__ import annotations

import copy
import math
import re
from typing import Any

SCHEMA = "axm.math-family/v1"
RESULT_SCHEMA = "axm.math-result/v1"
TRUTH_STATES = {"exact", "measured", "empirical", "estimated", "creative"}
CONSTANTS = {"pi": math.pi, "tau": math.tau, "e": math.e}
MAX_PARAMETERS = 256
MAX_VARIANTS = 256
MAX_DERIVED = 256
MAX_CONSTRAINTS = 256
MAX_EXPR_DEPTH = 24


def _identifier(value: Any) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}", value):
        raise ValueError("expected portable identifier of 1..80 characters")
    return value


def _finite(value: Any) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError("expected finite number")
    return float(value)


def _truth(value: Any) -> str:
    if value not in TRUTH_STATES:
        raise ValueError("unknown truth state")
    return value


def _unit(value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 40:
        raise ValueError("unit must be bounded nonempty text")
    return value


def _parameter_spec(name: str, spec: Any) -> dict[str, Any]:
    _identifier(name)
    if not isinstance(spec, dict):
        raise ValueError("parameter spec must be an object")
    required = {"unit", "min", "max", "default", "truth"}
    optional = {"uncertainty", "source"}
    if not required <= set(spec) or set(spec) - required - optional:
        raise ValueError("unsupported parameter fields")
    minimum = _finite(spec["min"])
    maximum = _finite(spec["max"])
    default = _finite(spec["default"])
    if minimum > maximum or not minimum <= default <= maximum:
        raise ValueError("parameter default/range invalid")
    _unit(spec["unit"])
    _truth(spec["truth"])
    if "uncertainty" in spec:
        uncertainty = _finite(spec["uncertainty"])
        if uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")
    if "source" in spec and (not isinstance(spec["source"], str) or len(spec["source"]) > 1000):
        raise ValueError("source must be bounded text")
    return copy.deepcopy(spec)


def _eval(expr: Any, values: dict[str, float], *, depth: int = 0) -> float:
    if depth > MAX_EXPR_DEPTH:
        raise ValueError("expression depth exceeded")
    if type(expr) in (int, float):
        return _finite(expr)
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError("expression node must contain exactly one operation")
    key, payload = next(iter(expr.items()))
    if key == "param":
        _identifier(payload)
        if payload not in values:
            raise ValueError(f"unknown parameter: {payload}")
        return values[payload]
    if key == "const":
        if payload not in CONSTANTS:
            raise ValueError("unknown mathematical constant")
        return CONSTANTS[payload]
    if key != "op" or not isinstance(payload, dict):
        raise ValueError("unknown expression node")
    name = payload.get("name")
    args = payload.get("args")
    if set(payload) != {"name", "args"} or not isinstance(args, list) or not 1 <= len(args) <= 32:
        raise ValueError("operation requires bounded args")
    vals = [_eval(item, values, depth=depth + 1) for item in args]
    if name == "add": return _finite(sum(vals))
    if name == "sub":
        if len(vals) != 2: raise ValueError("sub requires two args")
        return _finite(vals[0] - vals[1])
    if name == "mul":
        result = 1.0
        for value in vals: result *= value
        return _finite(result)
    if name == "div":
        if len(vals) != 2 or vals[1] == 0: raise ValueError("div requires two args and nonzero divisor")
        return _finite(vals[0] / vals[1])
    if name == "pow":
        if len(vals) != 2: raise ValueError("pow requires two args")
        return _finite(vals[0] ** vals[1])
    if name == "min": return min(vals)
    if name == "max": return max(vals)
    if name == "abs":
        if len(vals) != 1: raise ValueError("abs requires one arg")
        return abs(vals[0])
    if name == "sqrt":
        if len(vals) != 1 or vals[0] < 0: raise ValueError("sqrt requires one non-negative arg")
        return math.sqrt(vals[0])
    if name in {"sin", "cos", "tan"}:
        if len(vals) != 1: raise ValueError(f"{name} requires one arg")
        return _finite(getattr(math, name)(vals[0]))
    raise ValueError("unsupported mathematical operation")


def _derived_spec(name: str, spec: Any, values: dict[str, float]) -> dict[str, Any]:
    _identifier(name)
    if not isinstance(spec, dict): raise ValueError("derived spec must be an object")
    required = {"unit", "expr", "truth"}; optional = {"source"}
    if not required <= set(spec) or set(spec) - required - optional: raise ValueError("unsupported derived fields")
    _unit(spec["unit"]); _truth(spec["truth"])
    if "source" in spec and (not isinstance(spec["source"], str) or len(spec["source"]) > 1000): raise ValueError("source must be bounded text")
    _eval(spec["expr"], values)
    return copy.deepcopy(spec)


def _constraint(spec: Any, values: dict[str, float]) -> dict[str, Any]:
    if not isinstance(spec, dict): raise ValueError("constraint must be an object")
    required = {"label", "left", "op", "right"}; optional = {"tolerance"}
    if not required <= set(spec) or set(spec) - required - optional: raise ValueError("unsupported constraint fields")
    _identifier(spec["label"]); op = spec["op"]
    if op not in {"lt", "le", "eq", "ge", "gt"}: raise ValueError("unsupported constraint operator")
    tolerance = _finite(spec.get("tolerance", 0.0))
    if tolerance < 0: raise ValueError("constraint tolerance must be non-negative")
    left = _eval(spec["left"], values); right = _eval(spec["right"], values)
    passed = {"lt": left < right - tolerance,"le": left <= right + tolerance,"eq": abs(left - right) <= tolerance,"ge": left + tolerance >= right,"gt": left > right + tolerance}[op]
    return {"label": spec["label"], "op": op, "left": left, "right": right, "tolerance": tolerance, "passed": passed}


def validate_family(family: Any) -> dict[str, Any]:
    if not isinstance(family, dict): raise ValueError("math family must be an object")
    required = {"schema", "id", "parameters", "variants", "derived", "constraints"}
    if set(family) != required or family["schema"] != SCHEMA: raise ValueError("unsupported math family contract")
    _identifier(family["id"])
    parameters, variants, derived, constraints = family["parameters"], family["variants"], family["derived"], family["constraints"]
    if not isinstance(parameters, dict) or not 1 <= len(parameters) <= MAX_PARAMETERS: raise ValueError("family requires 1..256 parameters")
    if not isinstance(variants, dict) or len(variants) > MAX_VARIANTS: raise ValueError("too many variants")
    if not isinstance(derived, dict) or len(derived) > MAX_DERIVED: raise ValueError("too many derived values")
    if not isinstance(constraints, list) or len(constraints) > MAX_CONSTRAINTS: raise ValueError("too many constraints")
    base: dict[str, float] = {}
    for name, spec in parameters.items():
        checked = _parameter_spec(name, spec); base[name] = _finite(checked["default"])
    for name, values in variants.items():
        _identifier(name)
        if not isinstance(values, dict) or set(values) - parameters.keys(): raise ValueError("variant may only override declared parameters")
        for parameter, value in values.items():
            checked = _parameter_spec(parameter, parameters[parameter]); numeric = _finite(value)
            if not _finite(checked["min"]) <= numeric <= _finite(checked["max"]): raise ValueError("variant value exceeds declared range")
    for name, spec in derived.items(): _derived_spec(name, spec, base)
    combined = dict(base)
    for name, spec in derived.items(): combined[name] = _eval(spec["expr"], combined)
    for item in constraints: _constraint(item, combined)
    return copy.deepcopy(family)


def resolve_family(family: Any, *, variant: str | None = None, overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    family = validate_family(family); parameters = family["parameters"]; chosen = {}
    if variant is not None:
        _identifier(variant)
        if variant not in family["variants"]: raise ValueError("unknown math variant")
        chosen.update(family["variants"][variant])
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - parameters.keys(): raise ValueError("overrides may only target declared parameters")
        chosen.update(overrides)
    values: dict[str, float] = {}; parameter_evidence: dict[str, dict[str, Any]] = {}
    for name, spec in parameters.items():
        value = _finite(chosen.get(name, spec["default"])); minimum = _finite(spec["min"]); maximum = _finite(spec["max"])
        if not minimum <= value <= maximum: raise ValueError(f"parameter {name} exceeds declared range")
        values[name] = value
        parameter_evidence[name] = {"value": value,"unit": spec["unit"],"truth": spec["truth"],"uncertainty": float(spec.get("uncertainty", 0.0)),"source": spec.get("source"),"selected_by": "override" if overrides and name in overrides else "variant" if variant and name in family["variants"][variant] else "default"}
    derived_evidence: dict[str, dict[str, Any]] = {}
    for name, spec in family["derived"].items():
        value = _eval(spec["expr"], values); values[name] = value
        derived_evidence[name] = {"value": value,"unit": spec["unit"],"truth": spec["truth"],"source": spec.get("source"),"selected_by": "derived"}
    checks = [_constraint(item, values) for item in family["constraints"]]
    failed = [item["label"] for item in checks if not item["passed"]]
    if failed: raise ValueError("math constraints failed: " + ", ".join(failed))
    return {"schema": RESULT_SCHEMA,"family": family["id"],"variant": variant,"parameters": parameter_evidence,"derived": derived_evidence,"constraints": checks,"truth_boundary": "Numeric derivation and declared constraints were evaluated. Units are labels in v1; dimensional consistency, physical realism, manufacturability, rendered quality and real-world safety are not inferred."}


def value_map(result: Any) -> dict[str, float]:
    if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA: raise ValueError("expected resolved math result")
    values = {}
    for section in ("parameters", "derived"):
        records = result.get(section)
        if not isinstance(records, dict): raise ValueError("malformed resolved math result")
        for name, record in records.items():
            _identifier(name)
            if not isinstance(record, dict) or "value" not in record: raise ValueError("malformed resolved math record")
            values[name] = _finite(record["value"])
    return values

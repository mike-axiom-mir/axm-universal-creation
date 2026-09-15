"""Deterministic dimension-aware mathematical families for reusable creative parts.

The evaluator is declarative and bounded. It resolves numeric parameters, units,
named variants, derived values and explicit constraints without executing
arbitrary code or claiming rendered/physical truth it has not established.
"""
from __future__ import annotations

import copy
from dataclasses import dataclass
from fractions import Fraction
import math
import re
from typing import Any

SCHEMA = "axm.math-family/v1"
RESULT_SCHEMA = "axm.math-result/v1"
TRUTH_STATES = {"exact", "measured", "empirical", "estimated", "creative"}
TRUTH_RANK = {"creative": 0, "estimated": 1, "empirical": 2, "measured": 3, "exact": 4}
CONSTANTS = {"pi": math.pi, "tau": math.tau, "e": math.e}
BASE_DIMENSIONS = (
    "length", "mass", "time", "current", "temperature",
    "amount", "luminous_intensity", "angle", "screen",
)
MAX_PARAMETERS = 256
MAX_VARIANTS = 256
MAX_DERIVED = 256
MAX_CONSTRAINTS = 256
MAX_EXPR_DEPTH = 24


def _dims(**values: int) -> tuple[Fraction, ...]:
    return tuple(Fraction(values.get(name, 0)) for name in BASE_DIMENSIONS)


DIMENSIONLESS = _dims()
LENGTH = _dims(length=1)
MASS = _dims(mass=1)
TIME = _dims(time=1)
ANGLE = _dims(angle=1)
SCREEN = _dims(screen=1)


@dataclass(frozen=True)
class Unit:
    factor: float
    dims: tuple[Fraction, ...]


@dataclass(frozen=True)
class Quantity:
    si: float
    dims: tuple[Fraction, ...]


def _combine_dims(a: tuple[Fraction, ...], b: tuple[Fraction, ...], sign: int = 1) -> tuple[Fraction, ...]:
    return tuple(x + sign * y for x, y in zip(a, b))


def _scale_dims(a: tuple[Fraction, ...], scale: Fraction) -> tuple[Fraction, ...]:
    return tuple(x * scale for x in a)


UNITS = {
    "1": Unit(1.0, DIMENSIONLESS),
    "ratio": Unit(1.0, DIMENSIONLESS),
    "%": Unit(0.01, DIMENSIONLESS),
    "count": Unit(1.0, DIMENSIONLESS),
    "m": Unit(1.0, LENGTH),
    "cm": Unit(0.01, LENGTH),
    "mm": Unit(0.001, LENGTH),
    "km": Unit(1000.0, LENGTH),
    "m2": Unit(1.0, _scale_dims(LENGTH, Fraction(2))),
    "cm2": Unit(0.0001, _scale_dims(LENGTH, Fraction(2))),
    "mm2": Unit(0.000001, _scale_dims(LENGTH, Fraction(2))),
    "m3": Unit(1.0, _scale_dims(LENGTH, Fraction(3))),
    "cm3": Unit(0.000001, _scale_dims(LENGTH, Fraction(3))),
    "mm3": Unit(0.000000001, _scale_dims(LENGTH, Fraction(3))),
    "kg": Unit(1.0, MASS),
    "g": Unit(0.001, MASS),
    "s": Unit(1.0, TIME),
    "ms": Unit(0.001, TIME),
    "min": Unit(60.0, TIME),
    "h": Unit(3600.0, TIME),
    "rad": Unit(1.0, ANGLE),
    "deg": Unit(math.pi / 180.0, ANGLE),
    "rev": Unit(math.tau, ANGLE),
    "Hz": Unit(1.0, _scale_dims(TIME, Fraction(-1))),
    "m/s": Unit(1.0, _combine_dims(LENGTH, TIME, -1)),
    "km/h": Unit(1000.0 / 3600.0, _combine_dims(LENGTH, TIME, -1)),
    "m/s2": Unit(1.0, _combine_dims(LENGTH, _scale_dims(TIME, Fraction(2)), -1)),
    "rad/s": Unit(1.0, _combine_dims(ANGLE, TIME, -1)),
    "deg/s": Unit(math.pi / 180.0, _combine_dims(ANGLE, TIME, -1)),
    "rpm": Unit(math.tau / 60.0, _combine_dims(ANGLE, TIME, -1)),
    "N": Unit(1.0, _combine_dims(_combine_dims(MASS, LENGTH), _scale_dims(TIME, Fraction(2)), -1)),
    "Pa": Unit(1.0, _combine_dims(MASS, _combine_dims(LENGTH, _scale_dims(TIME, Fraction(2))), -1)),
    "J": Unit(1.0, _combine_dims(_combine_dims(MASS, _scale_dims(LENGTH, Fraction(2))), _scale_dims(TIME, Fraction(2)), -1)),
    "W": Unit(1.0, _combine_dims(_combine_dims(MASS, _scale_dims(LENGTH, Fraction(2))), _scale_dims(TIME, Fraction(3)), -1)),
    "px": Unit(1.0, SCREEN),
}


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


def _unit(value: Any) -> Unit:
    if not isinstance(value, str) or value not in UNITS:
        raise ValueError("unknown unit")
    return UNITS[value]


def _dimension_json(dims: tuple[Fraction, ...]) -> dict[str, int | str]:
    result: dict[str, int | str] = {}
    for name, power in zip(BASE_DIMENSIONS, dims):
        if power:
            result[name] = int(power) if power.denominator == 1 else f"{power.numerator}/{power.denominator}"
    return result


def unit_info(name: str) -> dict[str, Any]:
    unit = _unit(name)
    return {"unit": name, "factor_to_base": unit.factor, "dimension": _dimension_json(unit.dims)}


def convert(value: Any, from_unit: str, to_unit: str) -> float:
    numeric = _finite(value)
    source = _unit(from_unit)
    target = _unit(to_unit)
    if source.dims != target.dims:
        raise ValueError("incompatible unit dimensions")
    return _finite(numeric * source.factor / target.factor)


def _quantity(value: Any, unit_name: str) -> Quantity:
    numeric = _finite(value)
    unit = _unit(unit_name)
    return Quantity(_finite(numeric * unit.factor), unit.dims)


def _as_unit(quantity: Quantity, unit_name: str) -> float:
    unit = _unit(unit_name)
    if quantity.dims != unit.dims:
        raise ValueError("derived expression dimension does not match declared unit")
    return _finite(quantity.si / unit.factor)


def _parameter_spec(name: str, spec: Any) -> dict[str, Any]:
    _identifier(name)
    if not isinstance(spec, dict):
        raise ValueError("parameter spec must be an object")
    required = {"unit", "min", "max", "default", "truth"}
    optional = {"uncertainty", "source"}
    if not required <= set(spec) or set(spec) - required - optional:
        raise ValueError("unsupported parameter fields")
    unit = _unit(spec["unit"])
    minimum = _finite(spec["min"])
    maximum = _finite(spec["max"])
    default = _finite(spec["default"])
    if minimum > maximum or not minimum <= default <= maximum:
        raise ValueError("parameter default/range invalid")
    _truth(spec["truth"])
    if "uncertainty" in spec:
        uncertainty = _finite(spec["uncertainty"])
        if uncertainty < 0:
            raise ValueError("uncertainty must be non-negative")
    if "source" in spec and (not isinstance(spec["source"], str) or len(spec["source"]) > 1000):
        raise ValueError("source must be bounded text")
    if not math.isfinite(default * unit.factor):
        raise ValueError("parameter conversion is not finite")
    return copy.deepcopy(spec)


def _expr_dependencies(expr: Any, *, depth: int = 0) -> set[str]:
    if depth > MAX_EXPR_DEPTH:
        raise ValueError("expression depth exceeded")
    if type(expr) in (int, float):
        _finite(expr)
        return set()
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError("expression node must contain exactly one operation")
    key, payload = next(iter(expr.items()))
    if key == "param":
        return {_identifier(payload)}
    if key == "const":
        if payload not in CONSTANTS:
            raise ValueError("unknown mathematical constant")
        return set()
    if key == "quantity":
        if not isinstance(payload, dict) or set(payload) != {"value", "unit"}:
            raise ValueError("quantity requires value and unit")
        _quantity(payload["value"], payload["unit"])
        return set()
    if key != "op" or not isinstance(payload, dict):
        raise ValueError("unknown expression node")
    if set(payload) != {"name", "args"} or not isinstance(payload["args"], list) or not 1 <= len(payload["args"]) <= 32:
        raise ValueError("operation requires bounded args")
    result: set[str] = set()
    for item in payload["args"]:
        result |= _expr_dependencies(item, depth=depth + 1)
    return result


def _eval(expr: Any, values: dict[str, Quantity], *, depth: int = 0) -> Quantity:
    if depth > MAX_EXPR_DEPTH:
        raise ValueError("expression depth exceeded")
    if type(expr) in (int, float):
        return Quantity(_finite(expr), DIMENSIONLESS)
    if not isinstance(expr, dict) or len(expr) != 1:
        raise ValueError("expression node must contain exactly one operation")

    key, payload = next(iter(expr.items()))
    if key == "param":
        name = _identifier(payload)
        if name not in values:
            raise ValueError(f"unknown parameter: {name}")
        return values[name]
    if key == "const":
        if payload not in CONSTANTS:
            raise ValueError("unknown mathematical constant")
        return Quantity(CONSTANTS[payload], DIMENSIONLESS)
    if key == "quantity":
        if not isinstance(payload, dict) or set(payload) != {"value", "unit"}:
            raise ValueError("quantity requires value and unit")
        return _quantity(payload["value"], payload["unit"])
    if key != "op" or not isinstance(payload, dict):
        raise ValueError("unknown expression node")

    name = payload.get("name")
    args = payload.get("args")
    if set(payload) != {"name", "args"} or not isinstance(args, list) or not 1 <= len(args) <= 32:
        raise ValueError("operation requires bounded args")
    vals = [_eval(item, values, depth=depth + 1) for item in args]

    if name in {"add", "sub", "min", "max"}:
        dims = vals[0].dims
        if any(value.dims != dims for value in vals[1:]):
            raise ValueError(f"{name} requires compatible dimensions")
        if name == "add":
            return Quantity(_finite(sum(value.si for value in vals)), dims)
        if name == "sub":
            if len(vals) != 2:
                raise ValueError("sub requires two args")
            return Quantity(_finite(vals[0].si - vals[1].si), dims)
        chosen = min(vals, key=lambda q: q.si) if name == "min" else max(vals, key=lambda q: q.si)
        return chosen

    if name == "mul":
        si = 1.0
        dims = DIMENSIONLESS
        for value in vals:
            si *= value.si
            dims = _combine_dims(dims, value.dims)
        return Quantity(_finite(si), dims)

    if name == "div":
        if len(vals) != 2 or vals[1].si == 0:
            raise ValueError("div requires two args and nonzero divisor")
        return Quantity(_finite(vals[0].si / vals[1].si), _combine_dims(vals[0].dims, vals[1].dims, -1))

    if name == "pow":
        if len(vals) != 2 or vals[1].dims != DIMENSIONLESS:
            raise ValueError("pow requires a dimensionless exponent")
        exponent = vals[1].si
        if vals[0].dims != DIMENSIONLESS:
            rounded = round(exponent)
            if not math.isclose(exponent, rounded, rel_tol=0.0, abs_tol=1e-12):
                raise ValueError("dimensionful pow requires an integer exponent")
            scale = Fraction(int(rounded))
        else:
            scale = Fraction(0)
        return Quantity(_finite(vals[0].si ** exponent),
                        DIMENSIONLESS if vals[0].dims == DIMENSIONLESS else _scale_dims(vals[0].dims, scale))

    if name == "abs":
        if len(vals) != 1:
            raise ValueError("abs requires one arg")
        return Quantity(abs(vals[0].si), vals[0].dims)

    if name == "sqrt":
        if len(vals) != 1 or vals[0].si < 0:
            raise ValueError("sqrt requires one non-negative arg")
        return Quantity(math.sqrt(vals[0].si), _scale_dims(vals[0].dims, Fraction(1, 2)))

    if name in {"sin", "cos", "tan"}:
        if len(vals) != 1 or vals[0].dims != ANGLE:
            raise ValueError(f"{name} requires one angle")
        return Quantity(_finite(getattr(math, name)(vals[0].si)), DIMENSIONLESS)

    if name in {"asin", "acos", "atan"}:
        if len(vals) != 1 or vals[0].dims != DIMENSIONLESS:
            raise ValueError(f"{name} requires one dimensionless arg")
        return Quantity(_finite(getattr(math, name)(vals[0].si)), ANGLE)

    if name == "atan2":
        if len(vals) != 2 or vals[0].dims != vals[1].dims:
            raise ValueError("atan2 requires two compatible dimensions")
        return Quantity(_finite(math.atan2(vals[0].si, vals[1].si)), ANGLE)

    raise ValueError("unsupported mathematical operation")


def _derived_spec(name: str, spec: Any, values: dict[str, Quantity]) -> dict[str, Any]:
    _identifier(name)
    if not isinstance(spec, dict):
        raise ValueError("derived spec must be an object")
    required = {"unit", "expr", "truth"}
    optional = {"source"}
    if not required <= set(spec) or set(spec) - required - optional:
        raise ValueError("unsupported derived fields")
    _unit(spec["unit"])
    _truth(spec["truth"])
    if "source" in spec and (not isinstance(spec["source"], str) or len(spec["source"]) > 1000):
        raise ValueError("source must be bounded text")
    quantity = _eval(spec["expr"], values)
    _as_unit(quantity, spec["unit"])
    return copy.deepcopy(spec)


def _constraint(spec: Any, values: dict[str, Quantity]) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("constraint must be an object")
    required = {"label", "left", "op", "right"}
    optional = {"tolerance", "tolerance_unit"}
    if not required <= set(spec) or set(spec) - required - optional:
        raise ValueError("unsupported constraint fields")
    _identifier(spec["label"])
    op = spec["op"]
    if op not in {"lt", "le", "eq", "ge", "gt"}:
        raise ValueError("unsupported constraint operator")
    left = _eval(spec["left"], values)
    right = _eval(spec["right"], values)
    if left.dims != right.dims:
        raise ValueError("constraint compares incompatible dimensions")

    tolerance = _finite(spec.get("tolerance", 0.0))
    if tolerance < 0:
        raise ValueError("constraint tolerance must be non-negative")
    if tolerance:
        if "tolerance_unit" not in spec:
            if left.dims != DIMENSIONLESS:
                raise ValueError("dimensioned tolerance requires tolerance_unit")
            tolerance_si = tolerance
        else:
            tol = _quantity(tolerance, spec["tolerance_unit"])
            if tol.dims != left.dims:
                raise ValueError("constraint tolerance has incompatible dimension")
            tolerance_si = tol.si
    else:
        if "tolerance_unit" in spec:
            tol = _quantity(0.0, spec["tolerance_unit"])
            if tol.dims != left.dims:
                raise ValueError("constraint tolerance has incompatible dimension")
        tolerance_si = 0.0

    passed = {
        "lt": left.si < right.si - tolerance_si,
        "le": left.si <= right.si + tolerance_si,
        "eq": abs(left.si - right.si) <= tolerance_si,
        "ge": left.si + tolerance_si >= right.si,
        "gt": left.si > right.si + tolerance_si,
    }[op]
    return {
        "label": spec["label"], "op": op, "left_base": left.si, "right_base": right.si,
        "dimension": _dimension_json(left.dims), "tolerance_base": tolerance_si, "passed": passed,
    }


def _combined_truth(states: list[str]) -> str:
    return min(states, key=lambda state: TRUTH_RANK[_truth(state)])


def validate_family(family: Any) -> dict[str, Any]:
    if not isinstance(family, dict):
        raise ValueError("math family must be an object")
    required = {"schema", "id", "parameters", "variants", "derived", "constraints"}
    if set(family) != required or family["schema"] != SCHEMA:
        raise ValueError("unsupported math family contract")
    _identifier(family["id"])

    parameters = family["parameters"]
    variants = family["variants"]
    derived = family["derived"]
    constraints = family["constraints"]
    if not isinstance(parameters, dict) or not 1 <= len(parameters) <= MAX_PARAMETERS:
        raise ValueError("family requires 1..256 parameters")
    if not isinstance(variants, dict) or len(variants) > MAX_VARIANTS:
        raise ValueError("too many variants")
    if not isinstance(derived, dict) or len(derived) > MAX_DERIVED:
        raise ValueError("too many derived values")
    if not isinstance(constraints, list) or len(constraints) > MAX_CONSTRAINTS:
        raise ValueError("too many constraints")
    if set(parameters) & set(derived):
        raise ValueError("parameter and derived names must be distinct")

    base: dict[str, Quantity] = {}
    for name, spec in parameters.items():
        checked = _parameter_spec(name, spec)
        base[name] = _quantity(checked["default"], checked["unit"])

    for name, values in variants.items():
        _identifier(name)
        if not isinstance(values, dict) or set(values) - parameters.keys():
            raise ValueError("variant may only override declared parameters")
        for parameter, value in values.items():
            checked = _parameter_spec(parameter, parameters[parameter])
            numeric = _finite(value)
            if not _finite(checked["min"]) <= numeric <= _finite(checked["max"]):
                raise ValueError("variant value exceeds declared range")

    combined = dict(base)
    for name, spec in derived.items():
        _derived_spec(name, spec, combined)
        combined[name] = _eval(spec["expr"], combined)

    for item in constraints:
        _constraint(item, combined)

    return copy.deepcopy(family)


def resolve_family(
    family: Any,
    *,
    variant: str | None = None,
    overrides: dict[str, Any] | None = None,
) -> dict[str, Any]:
    family = validate_family(family)
    parameters = family["parameters"]
    chosen = {}
    if variant is not None:
        _identifier(variant)
        if variant not in family["variants"]:
            raise ValueError("unknown math variant")
        chosen.update(family["variants"][variant])
    if overrides is not None:
        if not isinstance(overrides, dict) or set(overrides) - parameters.keys():
            raise ValueError("overrides may only target declared parameters")
        chosen.update(overrides)

    values: dict[str, Quantity] = {}
    evidence_truth: dict[str, str] = {}
    parameter_evidence: dict[str, dict[str, Any]] = {}
    for name, spec in parameters.items():
        value = _finite(chosen.get(name, spec["default"]))
        minimum = _finite(spec["min"])
        maximum = _finite(spec["max"])
        if not minimum <= value <= maximum:
            raise ValueError(f"parameter {name} exceeds declared range")
        quantity = _quantity(value, spec["unit"])
        values[name] = quantity
        evidence_truth[name] = spec["truth"]
        uncertainty = float(spec.get("uncertainty", 0.0))
        parameter_evidence[name] = {
            "value": value,
            "unit": spec["unit"],
            "base_value": quantity.si,
            "dimension": _dimension_json(quantity.dims),
            "truth": spec["truth"],
            "uncertainty": uncertainty,
            "base_uncertainty": uncertainty * _unit(spec["unit"]).factor,
            "source": spec.get("source"),
            "selected_by": "override" if overrides and name in overrides else
                           "variant" if variant and name in family["variants"][variant] else
                           "default",
        }

    derived_evidence: dict[str, dict[str, Any]] = {}
    for name, spec in family["derived"].items():
        dependencies = sorted(_expr_dependencies(spec["expr"]))
        missing = [dependency for dependency in dependencies if dependency not in values]
        if missing:
            raise ValueError("derived expression references unavailable values: " + ", ".join(missing))
        quantity = _eval(spec["expr"], values)
        declared = _as_unit(quantity, spec["unit"])
        dep_truths = [evidence_truth[dependency] for dependency in dependencies]
        value_truth = _combined_truth([spec["truth"], *dep_truths]) if dep_truths else spec["truth"]
        values[name] = quantity
        evidence_truth[name] = value_truth
        derived_evidence[name] = {
            "value": declared,
            "unit": spec["unit"],
            "base_value": quantity.si,
            "dimension": _dimension_json(quantity.dims),
            "relation_truth": spec["truth"],
            "truth": value_truth,
            "depends_on": dependencies,
            "source": spec.get("source"),
            "selected_by": "derived",
        }

    checks = [_constraint(item, values) for item in family["constraints"]]
    failed = [item["label"] for item in checks if not item["passed"]]
    if failed:
        raise ValueError("math constraints failed: " + ", ".join(failed))

    return {
        "schema": RESULT_SCHEMA,
        "family": family["id"],
        "variant": variant,
        "parameters": parameter_evidence,
        "derived": derived_evidence,
        "constraints": checks,
        "truth_boundary": (
            "Declared units were converted through the built-in dimension registry and expression "
            "dimensions were checked. Mathematical compatibility is not evidence of physical realism, "
            "manufacturability, rendered quality, ergonomics or real-world safety. Input uncertainty "
            "is retained but derived uncertainty is not yet propagated."
        ),
    }


def value_map(result: Any) -> dict[str, float]:
    if not isinstance(result, dict) or result.get("schema") != RESULT_SCHEMA:
        raise ValueError("expected resolved math result")
    values = {}
    for section in ("parameters", "derived"):
        records = result.get(section)
        if not isinstance(records, dict):
            raise ValueError("malformed resolved math result")
        for name, record in records.items():
            _identifier(name)
            if not isinstance(record, dict) or "value" not in record:
                raise ValueError("malformed resolved math record")
            values[name] = _finite(record["value"])
    return values

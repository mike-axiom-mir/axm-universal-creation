"""Bounded measurement-result records using metrology-aware uncertainty terms."""
from __future__ import annotations

import copy
import math
import re
from typing import Any

from .math import convert, unit_info

SCHEMA = "axm.measurement-result/v1"
UNCERTAINTY_KINDS = {"standard", "combined_standard", "expanded"}
EVALUATIONS = {"type_a", "type_b", "mixed", "not_stated"}
STATISTICS = {"single", "mean", "median", "model_estimate", "other"}
SOURCE_KINDS = {"published", "local_record", "dataset"}


def _text(value: Any, label: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be bounded non-empty text")
    return value


def _finite(value: Any, label: str) -> float:
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    return float(value)


def _date(value: Any, label: str) -> str:
    value = _text(value, label, 10)
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError(f"{label} must be YYYY-MM-DD")
    return value


def _quantity(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"value", "unit"}:
        raise ValueError("measurement quantity requires value and unit")
    _finite(value["value"], "measurement value")
    unit_info(value["unit"])
    return copy.deepcopy(value)


def _uncertainty(value: Any, quantity_unit: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("measurement uncertainty must be an object")
    required = {"kind", "value", "unit", "evaluation"}
    optional = {"coverage_factor", "coverage_probability", "degrees_of_freedom"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("unsupported measurement uncertainty fields")
    if value["kind"] not in UNCERTAINTY_KINDS or value["evaluation"] not in EVALUATIONS:
        raise ValueError("unsupported uncertainty kind/evaluation")
    numeric = _finite(value["value"], "uncertainty value")
    if numeric < 0:
        raise ValueError("uncertainty must be non-negative")
    unit_info(value["unit"])
    convert(1.0, value["unit"], quantity_unit)

    if value["kind"] == "expanded":
        if "coverage_factor" not in value:
            raise ValueError("expanded uncertainty requires coverage_factor")
        factor = _finite(value["coverage_factor"], "coverage factor")
        if factor <= 0:
            raise ValueError("coverage factor must be positive")
        if "coverage_probability" in value:
            probability = _finite(value["coverage_probability"], "coverage probability")
            if not 0 < probability <= 1:
                raise ValueError("coverage probability must be in (0, 1]")
    elif "coverage_factor" in value or "coverage_probability" in value:
        raise ValueError("coverage metadata belongs to expanded uncertainty")

    if "degrees_of_freedom" in value:
        degrees = _finite(value["degrees_of_freedom"], "degrees of freedom")
        if degrees <= 0:
            raise ValueError("degrees of freedom must be positive")
    return copy.deepcopy(value)


def _method(value: Any, evaluation: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("measurement method must be an object")
    required = {"description", "statistic"}
    optional = {"sample_count", "instrument", "procedure"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("unsupported measurement method fields")
    _text(value["description"], "method description")
    if value["statistic"] not in STATISTICS:
        raise ValueError("unsupported measurement statistic")
    if "sample_count" in value:
        sample_count = value["sample_count"]
        if type(sample_count) is not int or sample_count <= 0:
            raise ValueError("sample_count must be a positive integer")
    if evaluation == "type_a" and value.get("sample_count", 0) < 2:
        raise ValueError("Type A evaluation requires a series of observations")
    for key in ("instrument", "procedure"):
        if key in value:
            _text(value[key], f"method {key}")
    return copy.deepcopy(value)


def _scope(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("measurement scope must be an object")
    required = {"kind", "applies_to"}
    optional = {"conditions"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("unsupported measurement scope fields")
    _text(value["kind"], "scope kind", 100)
    _text(value["applies_to"], "scope applies_to")
    if "conditions" in value:
        if not isinstance(value["conditions"], list) or len(value["conditions"]) > 32:
            raise ValueError("scope conditions must be a bounded array")
        for condition in value["conditions"]:
            _text(condition, "scope condition")
    return copy.deepcopy(value)


def _source(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ValueError("measurement source must be an object")
    required = {"kind", "authority", "title", "locator"}
    optional = {"url", "sha256", "retrieved_on"}
    if not required <= set(value) or set(value) - required - optional:
        raise ValueError("unsupported measurement source fields")
    if value["kind"] not in SOURCE_KINDS:
        raise ValueError("unsupported measurement source kind")
    for key in ("authority", "title", "locator"):
        _text(value[key], f"source {key}")
    if "url" not in value and "sha256" not in value:
        raise ValueError("measurement source requires url or sha256")
    if "url" in value and not _text(value["url"], "source url").startswith("https://"):
        raise ValueError("measurement source url must use https")
    if "sha256" in value:
        digest = value["sha256"]
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-fA-F]{64}", digest):
            raise ValueError("measurement source sha256 must be 64 hex characters")
    if "retrieved_on" in value:
        _date(value["retrieved_on"], "source retrieved_on")
    return copy.deepcopy(value)


def validate_measurement_result(record: Any) -> dict[str, Any]:
    if not isinstance(record, dict):
        raise ValueError("measurement result must be an object")
    required = {"schema", "id", "measurand", "quantity", "uncertainty", "method", "scope", "source", "notes"}
    optional = {"observed_at"}
    if not required <= set(record) or set(record) - required - optional or record["schema"] != SCHEMA:
        raise ValueError("unsupported measurement-result contract")
    if not isinstance(record["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", record["id"]):
        raise ValueError("invalid measurement-result id")
    _text(record["measurand"], "measurand")
    quantity = _quantity(record["quantity"])
    uncertainty = _uncertainty(record["uncertainty"], quantity["unit"])
    _method(record["method"], uncertainty["evaluation"])
    _scope(record["scope"])
    _source(record["source"])
    if "observed_at" in record:
        _date(record["observed_at"], "observed_at")
    if not isinstance(record["notes"], list) or len(record["notes"]) > 32:
        raise ValueError("measurement notes must be a bounded array")
    for note in record["notes"]:
        _text(note, "measurement note")
    return copy.deepcopy(record)


def measurement_value(record: Any, to_unit: str | None = None) -> float:
    item = validate_measurement_result(record)
    quantity = item["quantity"]
    if to_unit is None:
        return float(quantity["value"])
    return convert(quantity["value"], quantity["unit"], to_unit)


def standard_uncertainty(record: Any, to_unit: str | None = None) -> float:
    item = validate_measurement_result(record)
    uncertainty = item["uncertainty"]
    value = float(uncertainty["value"])
    if uncertainty["kind"] == "expanded":
        value /= float(uncertainty["coverage_factor"])
    unit = uncertainty["unit"]
    return value if to_unit is None else convert(value, unit, to_unit)


def source_summary(record: Any) -> str:
    item = validate_measurement_result(record)
    source = item["source"]
    locator = source.get("url") or f"sha256:{source['sha256']}"
    summary = (
        f"measurement_result={item['id']} | measurand={item['measurand']} | "
        f"source={source['authority']}: {source['title']} | locator={source['locator']} | record={locator} | "
        f"scope={item['scope']['kind']}:{item['scope']['applies_to']}"
    )
    if len(summary) > 1000:
        raise ValueError("measurement provenance exceeds math source bound")
    return summary

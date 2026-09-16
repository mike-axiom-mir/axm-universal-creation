"""Local source-backed measures kept separate from pure math relations."""
from __future__ import annotations

import copy
import json
import math
import re
from typing import Any

from .math import convert, resolve_family, unit_info, validate_family

SCHEMA = "axm.known-measure/v1"
BASES = {"si_definition", "conventional", "defined_unit"}
TRUTH = {"exact", "measured", "empirical", "estimated"}


def _text(value: Any, label: str, limit: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise ValueError(f"{label} must be bounded non-empty text")
    return value


def validate_measure(record: Any) -> dict[str, Any]:
    required = {"schema", "id", "quantity", "truth", "basis", "scope", "source", "notes"}
    if not isinstance(record, dict) or set(record) != required or record.get("schema") != SCHEMA:
        raise ValueError("unsupported known-measure contract")
    if not isinstance(record["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,119}", record["id"]):
        raise ValueError("invalid known-measure id")
    quantity = record["quantity"]
    if not isinstance(quantity, dict) or set(quantity) != {"value", "unit"}:
        raise ValueError("known-measure quantity requires value and unit")
    if type(quantity["value"]) not in (int, float) or not math.isfinite(quantity["value"]):
        raise ValueError("known-measure value must be finite")
    unit_info(quantity["unit"])
    if record["truth"] not in TRUTH or record["basis"] not in BASES:
        raise ValueError("unsupported known-measure truth/basis")
    if not isinstance(record["scope"], dict) or "kind" not in record["scope"]:
        raise ValueError("known measure requires explicit scope")
    source = record["source"]
    if not isinstance(source, dict) or set(source) != {"authority", "title", "url", "retrieved_on", "locator"}:
        raise ValueError("known measure requires complete source metadata")
    for key in ("authority", "title", "locator"):
        _text(source[key], f"source {key}")
    if not _text(source["url"], "source url").startswith("https://"):
        raise ValueError("source url must use https")
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", _text(source["retrieved_on"], "retrieved_on", 10)):
        raise ValueError("retrieved_on must be YYYY-MM-DD")
    if not isinstance(record["notes"], list) or any(not isinstance(note, str) for note in record["notes"]):
        raise ValueError("notes must be text array")
    return copy.deepcopy(record)


def _record(measure_id: str, value: float, unit: str, basis: str, scope: dict[str, Any],
            authority: str, title: str, url: str, locator: str, notes: list[str]) -> dict[str, Any]:
    return {"schema": SCHEMA, "id": measure_id, "quantity": {"value": value, "unit": unit},
            "truth": "exact", "basis": basis, "scope": scope,
            "source": {"authority": authority, "title": title, "url": url,
                       "retrieved_on": "2026-09-15", "locator": locator}, "notes": notes}


MEASURES = {
    "si.speed_of_light_vacuum": _record(
        "si.speed_of_light_vacuum", 299792458.0, "m/s", "si_definition",
        {"kind": "physical_definition", "applies_to": "speed of light in vacuum"},
        "BIPM", "SI defining constants",
        "https://www.bipm.org/en/measurement-units/si-defining-constants",
        "c = 299 792 458 m s^-1",
        ["Fixed numerical SI value; no uncertainty."],
    ),
    "convention.standard_gravity": _record(
        "convention.standard_gravity", 9.80665, "m/s2", "conventional",
        {"kind": "convention", "applies_to": "standard gravity g_n, not local measured gravity"},
        "CGPM / BIPM", "Declaration 2 of the 3rd CGPM (1901)",
        "https://www.bipm.org/en/committees/cg/cgpm/3-1901/resolution-2",
        "item 3: 980.665 cm/s^2",
        ["Conventional reference value; not a claim about gravity at a location."],
    ),
    "convention.standard_atmosphere": _record(
        "convention.standard_atmosphere", 101325.0, "Pa", "defined_unit",
        {"kind": "defined_reference", "applies_to": "one standard atmosphere"},
        "NIST", "NIST Guide to the SI, Appendix B: Conversion Factors",
        "https://www.nist.gov/pml/special-publication-811/nist-guide-si-appendix-b-conversion-factors",
        "1 atm = 101 325 Pa exactly",
        ["Defined reference pressure; not a claim about current local air pressure."],
    ),
    "convention.astronomical_unit": _record(
        "convention.astronomical_unit", 149597870700.0, "m", "defined_unit",
        {"kind": "defined_reference", "applies_to": "IAU astronomical unit of length"},
        "International Astronomical Union", "IAU 2012 Resolution B2",
        "https://www.iau.org/static/resolutions/IAU2012_English.pdf",
        "astronomical unit = 149 597 870 700 m exactly",
        ["Conventional unit of length; not an instantaneous Sun-Earth distance."],
    ),
}


def known_measure(measure_id: str) -> dict[str, Any]:
    if measure_id not in MEASURES:
        raise ValueError("unknown known measure")
    return validate_measure(MEASURES[measure_id])


def measure_catalog() -> list[dict[str, Any]]:
    return [{"id": item["id"], "value": item["quantity"]["value"], "unit": item["quantity"]["unit"],
             "truth": item["truth"], "basis": item["basis"], "scope": item["scope"]}
            for item in (known_measure(key) for key in sorted(MEASURES))]


def measure_value(measure_id: str, to_unit: str | None = None) -> float:
    item = known_measure(measure_id)
    q = item["quantity"]
    return float(q["value"]) if to_unit is None else convert(q["value"], q["unit"], to_unit)


def resolve_family_with_measures(family: Any, *, variant: str | None = None,
                                 overrides: dict[str, Any] | None = None,
                                 measure_overrides: dict[str, str] | None = None) -> dict[str, Any]:
    family = validate_family(family)
    if measure_overrides is None:
        return resolve_family(family, variant=variant, overrides=overrides)
    if not isinstance(measure_overrides, dict) or len(measure_overrides) > 256:
        raise ValueError("measure_overrides must be a bounded object")
    if set(measure_overrides) - set(family["parameters"]):
        raise ValueError("known measures may only target declared parameters")
    if overrides is not None and set(overrides) & set(measure_overrides):
        raise ValueError("numeric and known-measure overrides cannot target the same parameter")
    numeric = dict(overrides or {})
    used = {}
    for parameter, measure_id in measure_overrides.items():
        item = known_measure(measure_id)
        q = item["quantity"]
        spec = family["parameters"][parameter]
        numeric[parameter] = convert(q["value"], q["unit"], spec["unit"])
        spec["truth"] = item["truth"]
        summary = (f"known_measure={item['id']} | basis={item['basis']} | source={item['source']['authority']}: "
                   f"{item['source']['title']} | locator={item['source']['locator']} | url={item['source']['url']} | "
                   f"scope={json.dumps(item['scope'], sort_keys=True, separators=(',', ':'))}")
        if len(summary) > 1000:
            raise ValueError("known-measure provenance exceeds math source bound")
        spec["source"] = summary
        spec.pop("uncertainty", None)
        used[parameter] = item
    result = resolve_family(family, variant=variant, overrides=numeric)
    for parameter, item in used.items():
        result["parameters"][parameter]["selected_by"] = "known_measure"
        result["parameters"][parameter]["known_measure"] = copy.deepcopy(item)
    result["known_measures"] = {parameter: item["id"] for parameter, item in used.items()}
    result["truth_boundary"] += (
        " Known measures preserve basis, scope and source; a definition or convention is not automatically "
        "evidence that a particular physical object or location has that value."
    )
    return result

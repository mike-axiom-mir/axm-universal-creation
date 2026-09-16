"""Bounded, reusable static-clearance repair using UC's actual triangle tools.

The executable repertoire is fixed and inspectable. A crew can retain a verified
parameterized procedure; neither learned code nor arbitrary commands execute.
Sources remain immutable. Each result is a separate portable assembly bundle.
"""
from __future__ import annotations

import copy
import json
import math
import tempfile
from pathlib import Path

from axm_stickers import Registry
from axm_stickers.assembly import ASSEMBLY, expand, import_library, library_bundle
from axm_stickers.core import digest, identifier, validate
from axm_stickers.placement import identity

from .design_workshop_construction import _exact_definition, _pin
from .sticker_assembly import export_assembly
from .sticker_clearance_contact import (
    MAX_TOTAL_PAIR_TRIANGLE_PRODUCT, _assembly_parts, _measure_pair,
)

ACTION_KIND = "repair-sticker-clearance"
SCHEMA = "axm.profession-clearance-repair/v1"
PROCEDURE_SCHEMA = "axm.clearance-procedure/v1"
TOLERANCE = 1e-6
LIMITS = [
    "Measures only the named rigid parts in static rest pose; other pairs are untested.",
    "A separated final pose does not prove a collision-free movement path, steering, suspension, physics or mount strength.",
    "Source definitions, geometry and materials are preserved; only one permitted child translation changes in a new assembly.",
    "Geometric clearance does not establish artistic quality or professional acceptance.",
]


def _number(value, label, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"{label} must be finite in {low}..{high}")
    return float(value)


def procedure(axis):
    return {"schema": PROCEDURE_SCHEMA, "operator": "separate-bounds", "axis": axis,
            "scope": "STATIC_RIGID_TRANSLATION"}


def validate_request(inputs):
    axis = inputs.get("axis")
    if axis not in {"+x", "-x", "+y", "-y", "+z", "-z"}:
        raise ValueError("axis must be a signed assembly axis")
    moving = identifier(inputs.get("moving"))
    fixed = inputs.get("fixed")
    if (not isinstance(fixed, list) or not 1 <= len(fixed) <= 8
            or any(not isinstance(x, str) for x in fixed)
            or len(set(fixed)) != len(fixed) or moving in fixed):
        raise ValueError("fixed must contain 1..8 unique other part identifiers")
    fixed = sorted(identifier(x) for x in fixed)
    samples = inputs.get("search_steps", 8)
    if type(samples) is not int or not 1 <= samples <= 16:
        raise ValueError("search_steps must be an integer in 1..16")
    retained = inputs.get("procedure")
    if retained is not None and retained != procedure(axis):
        raise ValueError("unsupported or mismatched retained procedure")
    return {"assembly": _pin(inputs.get("assembly")), "moving": moving, "fixed": fixed, "axis": axis,
            "minimum_m": _number(inputs.get("minimum_m"), "minimum_m", 1e-4, 10),
            "max_translation_m": _number(inputs.get("max_translation_m"), "max_translation_m", 1e-4, 10),
            "search_steps": samples, "output_id": identifier(inputs.get("output_id")),
            "procedure": copy.deepcopy(retained)}


def _pin_of(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def _source_parts(registry, request):
    source = _exact_definition(registry, request["assembly"])
    if (source["adapter"] != ASSEMBLY or source["attachment"]["anchor"] != identity()
            or source["parameters"]):
        raise ValueError("repair requires an unparameterized assembly with identity anchor")
    if any(r["motion"] or r["clip"] for r in expand(registry, source)):
        raise ValueError("animated assemblies require a motion-aware repair adapter")
    _, parts = _assembly_parts(registry, request["assembly"])
    selected = [request["moving"], *request["fixed"]]
    if any(x not in parts for x in selected):
        raise ValueError("repair references an unknown direct assembly part")
    if any(parts[x]["animation_clips_ignored"] for x in selected):
        raise ValueError("animated source parts require a motion-aware repair adapter")
    work = sum(len(parts[request["moving"]]["triangles"]) * len(parts[x]["triangles"]) for x in request["fixed"])
    if work > MAX_TOTAL_PAIR_TRIANGLE_PRODUCT:
        raise ValueError("repair exceeds the existing bounded clearance work limit")
    return source, parts


def _assess(parts, request):
    checks = []
    for fixed in request["fixed"]:
        pair = _measure_pair(parts, request["moving"], fixed, TOLERANCE)
        if pair["status"] == "PASS":
            passing = pair["relation"] == "SEPARATED" and pair["clearance_m"] + TOLERANCE >= request["minimum_m"]
            status = "PASS" if passing else "FAIL"
        elif pair["relation"] == "CONTACT_OR_INTERSECTION":
            # The exact kind of contact is ambiguous, but zero surface distance
            # cannot meet a strictly positive minimum. Do not claim penetration.
            status = "FAIL"
        else:
            status = "HOLD"
        checks.append({"fixed": fixed, "status": status, "pair": pair})
    return {"status": "HOLD" if any(x["status"] == "HOLD" for x in checks) else
            "PASS" if all(x["status"] == "PASS" for x in checks) else "FAIL", "requirements": checks}


def _moved_parts(parts, request, distance):
    axis = "xyz".index(request["axis"][1]); sign = 1 if request["axis"][0] == "+" else -1
    moving = copy.deepcopy(parts[request["moving"]])
    for triangle in moving["triangles"]:
        for point in triangle:
            point[axis] += sign * distance
    for side in ("min", "max"):
        moving["bounds_m"][side][axis] += sign * distance
    return {**parts, request["moving"]: moving}


def _procedure_distance(parts, request):
    axis = "xyz".index(request["axis"][1]); bounds = parts[request["moving"]]["bounds_m"]
    if request["axis"][0] == "+":
        overlap = max(parts[x]["bounds_m"]["max"][axis] for x in request["fixed"]) - bounds["min"][axis]
    else:
        overlap = bounds["max"][axis] - min(parts[x]["bounds_m"]["min"][axis] for x in request["fixed"])
    return max(0.0, overlap + request["minimum_m"] + 4 * TOLERANCE)


def _repaired_definition(source, request, distance):
    result = copy.deepcopy(source)
    result["id"] = request["output_id"]
    result["version"] = 1
    axis = "xyz".index(request["axis"][1]); sign = 1 if request["axis"][0] == "+" else -1
    for child in result["recipe"]["children"]:
        if child["instance"]["id"] == request["moving"]:
            child["target"]["frame"][axis * 4 + 3] += sign * distance
    return validate(result)


def run_repair(root: Path, inputs: dict):
    from .profession_crew import _target
    request = validate_request(inputs)
    database = _target(root, inputs.get("database"))
    target = _target(root, inputs.get("path"))
    if not database.is_file():
        raise ValueError("repair requires an existing source registry")
    if target.exists():
        raise FileExistsError("repair output already exists; choose a new destination")
    with Registry(database) as registry:
        source, parts = _source_parts(registry, request)
        bundle = library_bundle(registry, source["id"], source["version"])
        before_glb = export_assembly(registry, source["id"], source["version"])["body"]
    before = _assess(parts, request)
    report = {"schema": SCHEMA, "request": request, "status": "HOLD", "before": before,
              "trials": [], "selection": "RETAINED_PROCEDURE" if request["procedure"] else "BOUNDED_SEARCH",
              "distance_m": None, "procedure": None, "limitations": LIMITS}
    selected = None
    if before["status"] == "PASS":
        selected = 0.0
        report["selection"] = "ALREADY_CLEAR"
    elif before["status"] == "FAIL":
        distances = ([_procedure_distance(parts, request)] if request["procedure"] else
                     [request["max_translation_m"] * i / request["search_steps"] for i in range(1, request["search_steps"] + 1)])
        for distance in distances:
            if not 0 < distance <= request["max_translation_m"]:
                break
            observed = _assess(_moved_parts(parts, request, distance), request)
            report["trials"].append({"distance_m": distance, **observed})
            if observed["status"] == "PASS":
                selected = distance
                break
            if observed["status"] == "HOLD":
                break
        # Cold discovery tests a reusable rule against real triangles before
        # retention; the first successful search offset is not generalized.
        if selected is not None:
            distance = _procedure_distance(parts, request)
            if 0 < distance <= request["max_translation_m"]:
                checked = _assess(_moved_parts(parts, request, distance), request)
                report["procedure_validation"] = checked
                if checked["status"] == "PASS":
                    selected = distance
                    report["procedure"] = procedure(request["axis"])
    if selected is None:
        report["reason"] = "UNMEASURABLE_SOURCE" if before["status"] == "HOLD" else "NO_VERIFIED_REPAIR_WITHIN_BOUND"
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".clearance-repair-", dir=target.parent) as scratch:
        stage = Path(scratch) / "result"; stage.mkdir()
        (stage / "source-library.json").write_text(json.dumps(bundle, sort_keys=True), encoding="utf-8")
        (stage / "before.glb").write_bytes(before_glb)
        if selected is not None:
            with Registry(Path(scratch) / "trial.sqlite") as trial:
                import_library(trial, bundle)
                result = _repaired_definition(source, request, selected)
                trial.register(result)
                after_pin = _pin_of(result)
                _, fresh_parts = _assembly_parts(trial, after_pin)
                after = _assess(fresh_parts, request)
                report.update(status=after["status"], distance_m=selected, after=after, assembly=after_pin)
                (stage / "repaired-library.json").write_text(json.dumps(library_bundle(trial, result["id"], 1), sort_keys=True), encoding="utf-8")
                (stage / "after.glb").write_bytes(export_assembly(trial, result["id"], 1)["body"])
        (stage / "repair.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        if target.exists():
            raise FileExistsError("repair destination appeared during execution")
        stage.rename(target)
    return report


def observe_repair(root: Path, inputs: dict):
    """Reconstruct exact assemblies and repeat checks; stored PASS is not evidence."""
    from .profession_crew import _target
    request = validate_request(inputs)
    target = _target(root, inputs.get("path"))
    for path in target.rglob("*"):
        if path.is_symlink():
            raise ValueError("repair artifacts must not use symbolic links")
    report = json.loads((target / "repair.json").read_text(encoding="utf-8"))
    if report.get("schema") != SCHEMA or report.get("request") != request:
        raise ValueError("repair artifact does not match the requested contract")
    with tempfile.TemporaryDirectory(prefix="uc-clearance-observe-") as scratch, Registry(Path(scratch) / "verify.sqlite") as registry:
        pin = import_library(registry, json.loads((target / "source-library.json").read_text(encoding="utf-8")))
        if pin != request["assembly"]:
            raise ValueError("repair source pin mismatch")
        source, parts = _source_parts(registry, request)
        if (target / "before.glb").read_bytes() != export_assembly(registry, source["id"], source["version"])["body"]:
            raise ValueError("before GLB differs from the pinned source")
        before = _assess(parts, request)
        result = {"status": "HOLD", "before": before, "limitations": LIMITS,
                  "learned_procedure": None, "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED"}
        distance = report.get("distance_m")
        if distance is None:
            return result
        distance = _number(distance, "observed translation", 0, request["max_translation_m"])
        pin = import_library(registry, json.loads((target / "repaired-library.json").read_text(encoding="utf-8")))
        expected = _repaired_definition(source, request, distance)
        if pin != _pin_of(expected):
            raise ValueError("repair changed state outside the permitted translation")
        if (target / "after.glb").read_bytes() != export_assembly(registry, pin["id"], pin["version"])["body"]:
            raise ValueError("after GLB differs from the exact repaired assembly")
        _, fresh_parts = _assembly_parts(registry, pin)
        after = _assess(fresh_parts, request)
        result.update(status=after["status"], after=after, distance_m=distance, assembly=pin)
        if before["status"] == "FAIL" and after["status"] == "PASS":
            predicted = _procedure_distance(parts, request)
            if abs(predicted - distance) <= TOLERANCE and 0 < predicted <= request["max_translation_m"]:
                check = _assess(_moved_parts(parts, request, predicted), request)
                if check["status"] == "PASS":
                    result["learned_procedure"] = procedure(request["axis"])
    return result

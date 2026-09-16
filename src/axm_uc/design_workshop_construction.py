from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from axm_stickers.assembly import ASSEMBLY, expand, save_assembly
from axm_stickers.core import Registry, digest as sticker_digest, identifier, instance, sha, version
from axm_stickers.placement import inverse_rigid, multiply, rigid

from .design_workshop import validate_sketch


BUILD_PLAN_SCHEMA = "axm.design-sticker-build/v0.1"
BUILD_RECEIPT_SCHEMA = "axm.design-sticker-build-receipt/v0.1"
ASSEMBLY_REPORT_SCHEMA = "axm.design-sticker-assembly-report/v0.1"
REPAIR_PLAN_SCHEMA = "axm.design-sticker-repair-plan/v0.1"
MAX_BINDINGS = 256

CONSTRUCTION_OPERATIONS = {
    "inspect-construction-loop",
    "validate-sticker-build",
    "compile-sticker-build",
    "save-sticker-build",
    "compare-sticker-assembly",
    "propose-sticker-repair",
    "save-sticker-repair",
}


class DesignWorkshopConstructionError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignWorkshopConstructionError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignWorkshopConstructionError(f"{label} exceeds its {maximum}-character bound")
    return result


def _pin(raw: Any, label: str = "sticker") -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"id", "version", "digest"}:
        raise DesignWorkshopConstructionError(f"{label} must be an exact sticker pin")
    try:
        pin = {"id": identifier(raw["id"]), "version": version(raw["version"]), "digest": sha(raw["digest"])}
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopConstructionError(f"{label} pin is invalid") from exc
    return pin


def _exact_definition(registry: Registry, pin: dict[str, Any]) -> dict[str, Any]:
    try:
        definition = registry.get(pin["id"], pin["version"])
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopConstructionError("build references an unknown sticker version", {"sticker": pin}) from exc
    observed = sticker_digest(definition)
    if observed != pin["digest"]:
        raise DesignWorkshopConstructionError(
            "build sticker pin digest drifted",
            {"sticker": pin, "observed_digest": observed},
        )
    if definition["attachment"]["space"] != "3d":
        raise DesignWorkshopConstructionError("workshop sticker construction v0.1 accepts 3D source stickers only", {"sticker": pin})
    return definition


def validate_sticker_build_plan(raw: Any, sketch_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    required = {"schema", "sketch_digest", "bindings"}
    allowed = required | {"plan_digest"}
    if not isinstance(raw, dict) or required - set(raw) or set(raw) - allowed:
        raise DesignWorkshopConstructionError("sticker build plan has missing or unsupported fields")
    if raw.get("schema") != BUILD_PLAN_SCHEMA:
        raise DesignWorkshopConstructionError("sticker build plan schema is unsupported")
    if raw.get("sketch_digest") != sketch["sketch_digest"]:
        raise DesignWorkshopConstructionError("sticker build plan does not match the exact sketch digest")
    bindings_raw = raw["bindings"]
    if not isinstance(bindings_raw, list) or not 1 <= len(bindings_raw) <= MAX_BINDINGS:
        raise DesignWorkshopConstructionError(f"sticker build plan requires 1..{MAX_BINDINGS} bindings")
    bindings = []
    seen = set()
    for index, item in enumerate(bindings_raw):
        if not isinstance(item, dict) or set(item) != {"part", "sticker", "overrides", "placement"}:
            raise DesignWorkshopConstructionError(
                f"bindings[{index}] must use part, sticker, overrides, and placement"
            )
        try:
            part = identifier(item["part"])
        except (TypeError, ValueError) as exc:
            raise DesignWorkshopConstructionError(f"bindings[{index}].part is invalid") from exc
        if part in seen:
            raise DesignWorkshopConstructionError("sticker build parts must be bound exactly once", {"duplicate": part})
        seen.add(part)
        if not isinstance(item["overrides"], dict) or not isinstance(item["placement"], dict):
            raise DesignWorkshopConstructionError("sticker build overrides and placement must be objects")
        try:
            _canonical(item["overrides"])
            _canonical(item["placement"])
        except (TypeError, ValueError) as exc:
            raise DesignWorkshopConstructionError("sticker build overrides and placement must be deterministic JSON") from exc
        bindings.append({
            "part": part,
            "sticker": _pin(item["sticker"], f"bindings[{index}].sticker"),
            "overrides": copy.deepcopy(item["overrides"]),
            "placement": copy.deepcopy(item["placement"]),
        })
    sketch_parts = [part["id"] for part in sketch["parts"]]
    if set(seen) != set(sketch_parts):
        raise DesignWorkshopConstructionError(
            "sticker build must bind every sketch part exactly once",
            {"missing": sorted(set(sketch_parts) - seen), "extra": sorted(seen - set(sketch_parts))},
        )
    normalized = {
        "schema": BUILD_PLAN_SCHEMA,
        "sketch_digest": sketch["sketch_digest"],
        "bindings": bindings,
    }
    plan_digest = _digest(normalized)
    if "plan_digest" in raw and raw["plan_digest"] != plan_digest:
        raise DesignWorkshopConstructionError(
            "persisted sticker build plan digest does not match its normalized body",
            {"declared": raw["plan_digest"], "observed": plan_digest},
        )
    normalized["plan_digest"] = plan_digest
    return normalized


def compile_sticker_build(registry: Registry, sketch_raw: Any, plan_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    plan = validate_sticker_build_plan(plan_raw, sketch)
    by_part = {binding["part"]: binding for binding in plan["bindings"]}
    children = []
    receipts = []
    for part in sketch["parts"]:
        binding = by_part[part["id"]]
        definition = _exact_definition(registry, binding["sticker"])
        try:
            placed = instance(
                definition,
                part["id"],
                overrides=binding["overrides"],
                placement=binding["placement"],
            )
            target_frame = rigid(part["frame"])
        except (TypeError, ValueError) as exc:
            raise DesignWorkshopConstructionError(
                "sticker build binding is incompatible with its exact source definition",
                {"part": part["id"], "sticker": binding["sticker"]},
            ) from exc
        target = {
            "space": "3d",
            "socket": definition["attachment"]["socket"],
            "frame": list(target_frame),
        }
        child = {"instance": placed, "target": target, "motion": None, "clip": None}
        children.append(child)
        receipts.append({
            "part": part["id"],
            "sticker": copy.deepcopy(binding["sticker"]),
            "target_frame": list(target_frame),
            "placement": copy.deepcopy(binding["placement"]),
            "overrides": copy.deepcopy(binding["overrides"]),
        })
    result = {
        "schema": BUILD_RECEIPT_SCHEMA,
        "truth_status": "DETERMINISTIC_SKETCH_TO_EXACT_STICKER_ASSEMBLY_PLAN",
        "sketch_digest": sketch["sketch_digest"],
        "plan_digest": plan["plan_digest"],
        "parts": receipts,
        "children": children,
        "limitations": [
            "a sketch frame becomes the declared target socket frame for the bound sticker; geometric center correspondence is not inferred",
            "explicit sticker placement/overrides remain caller-controlled and may offset or scale the source within the sketch target frame",
            "compilation proves exact pins and valid placement contracts, not mesh fit, collision clearance, actual dimensions, physics, aesthetics, or engine acceptance",
        ],
    }
    result["receipt_digest"] = _digest(result)
    return result


def _origin(raw: Any, lineage: str) -> tuple[dict[str, str], dict[str, str]]:
    if not isinstance(raw, dict) or set(raw) != {"author", "license", "source"}:
        raise DesignWorkshopConstructionError("origin must declare author, license, and source")
    original = {key: _text(raw[key], f"origin.{key}") for key in ("author", "license", "source")}
    combined = f"{original['source']} | {lineage}"
    if len(combined) > 2000:
        raise DesignWorkshopConstructionError("derived provenance source exceeds the sticker source bound")
    return {"author": original["author"], "license": original["license"], "source": combined}, original


def save_sticker_build(
    registry: Registry,
    sketch_raw: Any,
    plan_raw: Any,
    *,
    id: str,
    name: str,
    origin: dict[str, Any],
    ver: int = 1,
    socket: str = "mount",
    anchor: Any = None,
    tags: Any = None,
) -> dict[str, Any]:
    compiled = compile_sticker_build(registry, sketch_raw, plan_raw)
    derived_origin, original_origin = _origin(
        origin,
        f"sketch={compiled['sketch_digest']}; build-plan={compiled['plan_digest']}",
    )
    try:
        assembly = save_assembly(
            registry,
            id=id,
            name=name,
            children=compiled["children"],
            origin=derived_origin,
            ver=ver,
            socket=socket,
            anchor=anchor,
            tags=tags,
        )
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopConstructionError("compiled sketch assembly could not be saved", {"id": id, "version": ver}) from exc
    pin = {"id": assembly["id"], "version": assembly["version"], "digest": sticker_digest(assembly)}
    receipt = {
        "schema": BUILD_RECEIPT_SCHEMA,
        "truth_status": "SAVED_IMMUTABLE_STICKER_ASSEMBLY_FROM_EXACT_SKETCH_PLAN",
        "assembly": pin,
        "sketch_digest": compiled["sketch_digest"],
        "plan_digest": compiled["plan_digest"],
        "source_origin": original_origin,
        "part_count": len(compiled["children"]),
        "ordinary_sticker_v1": True,
    }
    receipt["receipt_digest"] = _digest(receipt)
    return {"assembly": assembly, "pin": pin, "receipt": receipt}


def _position(frame: list[float]) -> tuple[float, float, float]:
    return float(frame[3]), float(frame[7]), float(frame[11])


def _distance(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    return math.sqrt(sum((first[index] - second[index]) ** 2 for index in range(3)))


def _axis_vector(frame: list[float], axis: str) -> tuple[float, float, float]:
    column = {"x": 0, "y": 1, "z": 2}[axis]
    return float(frame[column]), float(frame[4 + column]), float(frame[8 + column])


def _angle(first: tuple[float, float, float], second: tuple[float, float, float]) -> float:
    dot = max(-1.0, min(1.0, sum(first[index] * second[index] for index in range(3))))
    return math.degrees(math.acos(dot))


def _rotation_delta_degrees(expected: list[float], observed: list[float]) -> float:
    trace = sum(
        expected[k * 4 + row] * observed[k * 4 + row]
        for row in range(3)
        for k in range(3)
    )
    cosine = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    return math.degrees(math.acos(cosine))


def _frame_gauge_result(gauge: dict[str, Any], observed: dict[str, list[float]]) -> dict[str, Any]:
    kind = gauge["type"]
    if kind == "size":
        return {
            "id": gauge["id"],
            "type": kind,
            "status": "HOLD",
            "reason": "saved assembly placement does not expose actual source geometry dimensions",
        }
    if kind in {"distance", "angle"}:
        needed = [gauge["a"], gauge["b"]]
    elif kind in {"alignment", "spacing"}:
        needed = list(gauge["parts"])
    elif kind == "orientation":
        needed = [gauge["part"]]
    elif kind == "symmetry":
        needed = [value for pair in gauge["pairs"] for value in (pair["a"], pair["b"])]
    else:
        return {"id": gauge["id"], "type": kind, "status": "HOLD", "reason": "unsupported placement-only gauge"}
    missing = sorted(set(needed) - set(observed))
    if missing:
        return {"id": gauge["id"], "type": kind, "status": "HOLD", "missing_parts": missing}
    if kind == "distance":
        measured = _distance(_position(observed[gauge["a"]]), _position(observed[gauge["b"]]))
        residual = abs(measured - gauge["target"])
        tolerance = gauge["tolerance"]
    elif kind == "alignment":
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]
        first = _position(observed[gauge["parts"][0]])
        residual = max(
            math.sqrt(sum((position[index] - first[index]) ** 2 for index in range(3) if index != axis_index))
            for position in (_position(observed[part]) for part in gauge["parts"])
        )
        measured = residual
        tolerance = gauge["tolerance"]
    elif kind == "spacing":
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]
        values = [_position(observed[part])[axis_index] for part in gauge["parts"]]
        gaps = [abs(values[index + 1] - values[index]) for index in range(len(values) - 1)]
        residual = max(abs(value - gauge["target"]) for value in gaps)
        measured = gaps
        tolerance = gauge["tolerance"]
    elif kind == "angle":
        measured = _angle(_axis_vector(observed[gauge["a"]], gauge["a_axis"]), _axis_vector(observed[gauge["b"]], gauge["b_axis"]))
        residual = abs(measured - gauge["target_degrees"])
        tolerance = gauge["tolerance_degrees"]
    elif kind == "orientation":
        world = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}[gauge["world_axis"]]
        measured = _angle(_axis_vector(observed[gauge["part"]], gauge["local_axis"]), world)
        residual = abs(measured - gauge["target_degrees"])
        tolerance = gauge["tolerance_degrees"]
    else:  # symmetry
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]
        values = []
        for pair in gauge["pairs"]:
            first = _position(observed[pair["a"]])
            second = list(_position(observed[pair["b"]]))
            second[axis_index] = 2.0 * gauge["center"] - second[axis_index]
            values.append(_distance(first, tuple(second)))
        residual = max(values)
        measured = values
        tolerance = gauge["tolerance"]
    return {
        "id": gauge["id"],
        "type": kind,
        "status": "PASS" if residual <= tolerance else "FAIL",
        "measured": measured,
        "residual": round(residual, 12),
        "tolerance": tolerance,
    }


def compare_sticker_assembly(registry: Registry, sketch_raw: Any, assembly_pin_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    pin = _pin(assembly_pin_raw, "assembly")
    definition = _exact_definition(registry, pin)
    if definition["adapter"] != ASSEMBLY:
        raise DesignWorkshopConstructionError("compare-sticker-assembly requires an exact 3D assembly sticker")
    try:
        expand(registry, definition)
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopConstructionError("source assembly cannot be expanded exactly") from exc
    children = definition["recipe"].get("children") if isinstance(definition.get("recipe"), dict) else None
    if not isinstance(children, list):
        raise DesignWorkshopConstructionError("source assembly does not expose direct children")
    observed: dict[str, list[float]] = {}
    for child in children:
        child_id = child["instance"]["id"]
        try:
            observed[child_id] = list(rigid(child["target"]["frame"]))
        except (TypeError, ValueError, KeyError) as exc:
            raise DesignWorkshopConstructionError("assembly child target is not a rigid workshop placement", {"part": child_id}) from exc
    planned = {part["id"]: part for part in sketch["parts"]}
    part_results = []
    for part_id, part in planned.items():
        frame = observed.get(part_id)
        if frame is None:
            part_results.append({
                "id": part_id,
                "placement_status": "FAIL",
                "status": "FAIL",
                "reason": "sketch part is missing from the direct assembly children",
                "size_status": "HOLD",
            })
            continue
        position_residual = _distance(_position(part["frame"]), _position(frame))
        orientation_residual = _rotation_delta_degrees(part["frame"], frame)
        failed = []
        if position_residual > sketch["tolerances"]["position"]:
            failed.append("position")
        if orientation_residual > sketch["tolerances"]["orientation_degrees"]:
            failed.append("orientation")
        placement_status = "PASS" if not failed else "FAIL"
        part_results.append({
            "id": part_id,
            "placement_status": placement_status,
            "status": placement_status,
            "position_residual": round(position_residual, 12),
            "orientation_residual_degrees": round(orientation_residual, 12),
            "failed_dimensions": failed,
            "size_status": "HOLD",
            "size_reason": "assembly placement state does not prove source mesh dimensions",
        })
    extra_parts = sorted(set(observed) - set(planned))
    gauge_results = [_frame_gauge_result(gauge, observed) for gauge in sketch["gauges"]]
    placement_fail = bool(extra_parts) or any(row["placement_status"] == "FAIL" for row in part_results) or any(
        row["status"] == "FAIL" for row in gauge_results if row["type"] != "size"
    )
    placement_hold = any(row["status"] == "HOLD" for row in gauge_results if row["type"] != "size")
    placement_status = "FAIL" if placement_fail else "HOLD" if placement_hold else "PASS"
    report = {
        "schema": ASSEMBLY_REPORT_SCHEMA,
        "truth_status": "DETERMINISTIC_STICKER_ASSEMBLY_PLACEMENT_VS_EXACT_SKETCH",
        "status": "FAIL" if placement_status == "FAIL" else "HOLD",
        "placement_status": placement_status,
        "placement_passed": placement_status == "PASS",
        "assembly": pin,
        "sketch_digest": sketch["sketch_digest"],
        "parts": part_results,
        "extra_parts": extra_parts,
        "gauges": gauge_results,
        "unobserved": ["actual source mesh dimensions", "mesh fit", "collision clearance", "physics", "aesthetics", "target-engine behavior"],
        "limitations": [
            "direct child target frames are structural assembly state, not rendered geometry evidence",
            "size stays HOLD because the assembly recipe does not prove the dimensions represented by the sketch blockout",
            "placement PASS proves only agreement of declared target frames and frame-derived gauges within sketch tolerances",
        ],
    }
    report["report_digest"] = _digest(report)
    return report


def propose_sticker_repair(registry: Registry, sketch_raw: Any, assembly_pin_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    report = compare_sticker_assembly(registry, sketch, assembly_pin_raw)
    by_part = {part["id"]: part for part in sketch["parts"]}
    actions = []
    unresolved = []
    for row in report["parts"]:
        if row["placement_status"] != "FAIL":
            continue
        if row.get("reason"):
            unresolved.append({"kind": "missing-part", "part": row["id"], "reason": row["reason"]})
            continue
        actions.append({
            "operation": "set-target-frame",
            "part": row["id"],
            "frame": copy.deepcopy(by_part[row["id"]]["frame"]),
            "basis": sorted(row.get("failed_dimensions", [])),
        })
    for part in report["extra_parts"]:
        unresolved.append({"kind": "extra-part", "part": part, "reason": "removal is not inferred by the placement repair loop"})
    recheck_gauges = [row["id"] for row in report["gauges"] if row["status"] != "PASS"]
    if unresolved:
        status = "HOLD_STRUCTURAL_MISMATCH"
    elif actions:
        status = "READY_BOUNDED_PLACEMENT_REPAIR"
    else:
        status = "NO_PLACEMENT_REPAIR_REQUIRED"
    plan = {
        "schema": REPAIR_PLAN_SCHEMA,
        "truth_status": "DETERMINISTIC_WORKSHOP_PLACEMENT_REPAIR_DIRECTION",
        "status": status,
        "assembly": copy.deepcopy(report["assembly"]),
        "sketch_digest": sketch["sketch_digest"],
        "source_report_digest": report["report_digest"],
        "actions": actions,
        "unresolved": unresolved,
        "recheck_gauges": recheck_gauges,
        "limitations": [
            "only direct child target-frame corrections are automatically grounded",
            "missing/extra parts, size changes, source-geometry edits, collisions, material changes, and aesthetic repairs are not inferred",
            "all repaired frame-derived gauges must be measured again after a new immutable assembly version is saved",
        ],
    }
    plan["repair_digest"] = _digest(plan)
    return plan


def _rebase_motion(motion: Any, old_frame: list[float], new_frame: list[float]) -> Any:
    if motion is None:
        return None
    if not isinstance(motion, list):
        raise DesignWorkshopConstructionError("assembly motion is malformed")
    delta = multiply(new_frame, inverse_rigid(old_frame))
    rebased = copy.deepcopy(motion)
    for index, sample in enumerate(rebased):
        if not isinstance(sample, dict) or set(sample) != {"time", "frame"}:
            raise DesignWorkshopConstructionError("assembly motion sample is malformed")
        sample["frame"] = multiply(delta, rigid(sample["frame"]))
        if index == 0:
            sample["frame"] = list(new_frame)
    return rebased


def save_sticker_repair(
    registry: Registry,
    sketch_raw: Any,
    assembly_pin_raw: Any,
    *,
    id: str,
    name: str,
    origin: dict[str, Any],
    ver: int,
    tags: Any = None,
) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw)
    source_pin = _pin(assembly_pin_raw, "assembly")
    source = _exact_definition(registry, source_pin)
    if source["adapter"] != ASSEMBLY:
        raise DesignWorkshopConstructionError("save-sticker-repair requires an assembly sticker")
    if source.get("parameters"):
        raise DesignWorkshopConstructionError("v0.1 placement repair rejects parameterized source assemblies instead of silently invalidating defaults")
    repair = propose_sticker_repair(registry, sketch, source_pin)
    if repair["status"] == "HOLD_STRUCTURAL_MISMATCH":
        raise DesignWorkshopConstructionError("placement repair is on HOLD because the assembly structure does not match the sketch", {"unresolved": repair["unresolved"]})
    if repair["status"] != "READY_BOUNDED_PLACEMENT_REPAIR":
        raise DesignWorkshopConstructionError("no bounded placement repair is required")
    actions = {row["part"]: row for row in repair["actions"]}
    children = copy.deepcopy(source["recipe"]["children"])
    for child in children:
        part = child["instance"]["id"]
        action = actions.get(part)
        if action is None:
            continue
        old_frame = list(rigid(child["target"]["frame"]))
        new_frame = list(rigid(action["frame"]))
        child["target"]["frame"] = new_frame
        child["motion"] = _rebase_motion(child.get("motion"), old_frame, new_frame)
    derived_origin, original_origin = _origin(
        origin,
        f"repair-of={source_pin['id']}@{source_pin['version']}:{source_pin['digest']}; sketch={sketch['sketch_digest']}; repair={repair['repair_digest']}",
    )
    try:
        assembly = save_assembly(
            registry,
            id=id,
            name=name,
            children=children,
            origin=derived_origin,
            ver=ver,
            socket=source["attachment"]["socket"],
            anchor=source["attachment"]["anchor"],
            tags=source["tags"] if tags is None else tags,
        )
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopConstructionError("repaired immutable assembly version could not be saved") from exc
    pin = {"id": assembly["id"], "version": assembly["version"], "digest": sticker_digest(assembly)}
    verification = compare_sticker_assembly(registry, sketch, pin)
    receipt = {
        "truth_status": "SAVED_IMMUTABLE_PLACEMENT_REPAIR_FROM_EXACT_SKETCH",
        "source_assembly": source_pin,
        "repaired_assembly": pin,
        "sketch_digest": sketch["sketch_digest"],
        "repair_digest": repair["repair_digest"],
        "source_origin": original_origin,
        "action_count": len(repair["actions"]),
        "post_repair_placement_status": verification["placement_status"],
        "post_repair_report_digest": verification["report_digest"],
    }
    receipt["receipt_digest"] = _digest(receipt)
    return {"assembly": assembly, "pin": pin, "repair": repair, "verification": verification, "receipt": receipt}


def construction_loop_summary() -> dict[str, Any]:
    return {
        "build_plan_schema": BUILD_PLAN_SCHEMA,
        "build_receipt_schema": BUILD_RECEIPT_SCHEMA,
        "assembly_report_schema": ASSEMBLY_REPORT_SCHEMA,
        "repair_plan_schema": REPAIR_PLAN_SCHEMA,
        "operations": sorted(CONSTRUCTION_OPERATIONS),
        "loop": "exact sketch -> explicit exact sticker bindings -> ordinary immutable assembly -> structural placement comparison -> bounded frame repair -> new immutable assembly version",
        "truth_boundary": "structural target-frame evidence only; no source sticker choice, actual size, mesh fit, collision, physics, aesthetics, or engine quality is inferred",
    }


def _resolve_database(root: Path, requested: Any) -> Path:
    value = Path(_text(requested, "database", 4000)).expanduser()
    target = (Path(root).resolve() / value).resolve() if not value.is_absolute() else value.resolve()
    machine_root = Path(root).resolve()
    try:
        relative = target.relative_to(machine_root)
    except ValueError:
        return target
    if not relative.parts or relative.parts[0] not in {"creations", ".axm-build"}:
        raise DesignWorkshopConstructionError("workshop construction database cannot live inside the machine body")
    return target


def operate_workshop_construction(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation not in CONSTRUCTION_OPERATIONS:
        raise DesignWorkshopConstructionError("workshop construction operation is unsupported", {"operation": operation, "supported": sorted(CONSTRUCTION_OPERATIONS)})
    if operation == "inspect-construction-loop":
        return {"truth_status": "DECLARED_WORKSHOP_CONSTRUCTION_LOOP_V0_1", **construction_loop_summary()}
    database = _resolve_database(root, inputs.get("database"))
    with Registry(database) as registry:
        if operation == "validate-sticker-build":
            return {"truth_status": "DETERMINISTIC_STICKER_BUILD_PLAN_VALIDATION", "plan": validate_sticker_build_plan(inputs.get("plan"), inputs.get("sketch"))}
        if operation == "compile-sticker-build":
            return compile_sticker_build(registry, inputs.get("sketch"), inputs.get("plan"))
        if operation == "save-sticker-build":
            return save_sticker_build(
                registry,
                inputs.get("sketch"),
                inputs.get("plan"),
                id=inputs.get("id"),
                name=inputs.get("name"),
                origin=inputs.get("origin"),
                ver=inputs.get("ver", 1),
                socket=inputs.get("socket", "mount"),
                anchor=inputs.get("anchor"),
                tags=inputs.get("tags"),
            )
        if operation == "compare-sticker-assembly":
            return compare_sticker_assembly(registry, inputs.get("sketch"), inputs.get("assembly"))
        if operation == "propose-sticker-repair":
            return propose_sticker_repair(registry, inputs.get("sketch"), inputs.get("assembly"))
        if operation == "save-sticker-repair":
            return save_sticker_repair(
                registry,
                inputs.get("sketch"),
                inputs.get("assembly"),
                id=inputs.get("id"),
                name=inputs.get("name"),
                origin=inputs.get("origin"),
                ver=inputs.get("ver"),
                tags=inputs.get("tags"),
            )
    raise AssertionError("unreachable")

from __future__ import annotations

import copy
import hashlib
import itertools
import json
import math
from pathlib import Path
import tempfile
from typing import Any

from axm_stickers.assembly import ASSEMBLY, expand, library_definitions
from axm_stickers.core import SCHEMA, Registry, digest, identifier, instance, text, validate, version
from axm_stickers.placement import identity

from .design_workshop import validate_sketch
from .design_workshop_construction import DesignWorkshopConstructionError, _exact_definition, _pin
from .sticker_clearance_contact import (
    StickerClearanceContactError,
    compare_sketch_clearance,
    validate_clearance_plan,
)
from .sticker_geometry_calipers import StickerGeometryCaliperError, compare_sticker_geometry
from .sticker_multiplier import _machine_body, _resolve_registry_path

PLANNER_SCHEMA = "axm.workshop-bounded-planner/v0.1"
PREVIEW_SCHEMA = "axm.workshop-bounded-planner-preview/v0.1"
RETENTION_SCHEMA = "axm.workshop-bounded-planner-retention/v0.1"
MAX_SLOTS = 32
MAX_CANDIDATES_PER_SLOT = 8
MAX_COMBINATIONS = 256
MAX_QUERY_SCAN = 512

PLANNER_OPERATIONS = {
    "inspect-workshop-planner",
    "preview-workshop-plan",
    "retain-workshop-plan",
}


class WorkshopBoundedPlannerError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _exact_pin(definition: dict[str, Any]) -> dict[str, Any]:
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def _pin_checked(registry: Registry, raw: Any, label: str) -> tuple[dict[str, Any], dict[str, Any]]:
    try:
        pin = _pin(raw, label)
        definition = _exact_definition(registry, pin)
    except (DesignWorkshopConstructionError, TypeError, ValueError) as exc:
        raise WorkshopBoundedPlannerError(f"{label} is not an exact available sticker pin") from exc
    if definition["attachment"]["space"] != "3d":
        raise WorkshopBoundedPlannerError(f"{label} is not a 3D sticker")
    return pin, definition


def _query_spec(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"adapter", "socket", "tag", "limit"}:
        raise WorkshopBoundedPlannerError(f"{label} query must use adapter, socket, tag, and limit")
    result: dict[str, Any] = {}
    for key in ("adapter", "socket", "tag"):
        value = raw[key]
        if value is not None and (not isinstance(value, str) or not value.strip()):
            raise WorkshopBoundedPlannerError(f"{label}.{key} must be null or non-empty text")
        result[key] = value.strip() if isinstance(value, str) else None
    if all(result[key] is None for key in ("adapter", "socket", "tag")):
        raise WorkshopBoundedPlannerError(f"{label} query must constrain at least one registry field")
    limit = raw["limit"]
    if type(limit) is not int or not 1 <= limit <= MAX_CANDIDATES_PER_SLOT:
        raise WorkshopBoundedPlannerError(f"{label}.limit must be 1..{MAX_CANDIDATES_PER_SLOT}")
    result["limit"] = limit
    return result


def _search_pool(registry: Registry, query: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    after = 0
    while True:
        page = registry.search(adapter=query["adapter"], socket=query["socket"], tag=query["tag"], after=after, limit=100)
        rows = page["entries"]
        entries.extend(rows)
        if len(entries) > MAX_QUERY_SCAN:
            raise WorkshopBoundedPlannerError(
                "registry query is too broad for deterministic bounded planning",
                {"maximum_scan": MAX_QUERY_SCAN, "query": copy.deepcopy(query)},
            )
        if len(rows) < 100:
            break
        next_after = page["next_cursor"]
        if type(next_after) is not int or next_after <= after:
            raise WorkshopBoundedPlannerError("registry pagination did not advance")
        after = next_after
    pins: dict[tuple[str, int, str], dict[str, Any]] = {}
    for row in entries:
        attachment = row.get("attachment", {})
        if not isinstance(attachment, dict) or attachment.get("space") != "3d":
            continue
        pin = {"id": row["id"], "version": row["version"], "digest": row["digest"]}
        checked, _ = _pin_checked(registry, pin, "query result")
        pins[(checked["id"], checked["version"], checked["digest"])] = checked
    return [pins[key] for key in sorted(pins)[: query["limit"]]]


def _normalize_request(registry: Registry, sketch_raw: Any, raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    sketch = validate_sketch(sketch_raw)
    required = {"schema", "sketch_digest", "slots", "objective"}
    allowed = required | {"clearance_plan", "incumbent", "planner_digest"}
    if not isinstance(raw, dict) or required - set(raw) or set(raw) - allowed or raw.get("schema") != PLANNER_SCHEMA:
        raise WorkshopBoundedPlannerError("planner request has missing/unsupported fields or schema")
    if raw["sketch_digest"] != sketch["sketch_digest"]:
        raise WorkshopBoundedPlannerError("planner request does not match the exact sketch digest")
    objective = raw["objective"]
    if not isinstance(objective, dict) or objective != {
        "kind": "minimize-size-error",
        "require_all_evidence_pass": True,
        "incumbent_policy": "strict-improvement",
    }:
        raise WorkshopBoundedPlannerError(
            "v0.1 objective must explicitly require all evidence PASS, minimize size error, and retain incumbents without strict improvement"
        )
    slots_raw = raw["slots"]
    if not isinstance(slots_raw, list) or not 1 <= len(slots_raw) <= MAX_SLOTS:
        raise WorkshopBoundedPlannerError(f"planner requires 1..{MAX_SLOTS} slots")
    sketch_ids = [row["id"] for row in sketch["parts"]]
    seen: set[str] = set()
    by_part: dict[str, dict[str, Any]] = {}
    for index, slot in enumerate(slots_raw):
        if not isinstance(slot, dict) or "part" not in slot:
            raise WorkshopBoundedPlannerError(f"slots[{index}] is invalid")
        part = slot["part"]
        if not isinstance(part, str) or part not in sketch_ids or part in seen:
            raise WorkshopBoundedPlannerError("planner slots must reference every sketch part exactly once")
        seen.add(part)
        has_candidates = "candidates" in slot
        has_query = "query" in slot
        if has_candidates == has_query or set(slot) != ({"part", "candidates"} if has_candidates else {"part", "query"}):
            raise WorkshopBoundedPlannerError("each planner slot requires exactly one of candidates or query")
        if has_candidates:
            candidates_raw = slot["candidates"]
            if not isinstance(candidates_raw, list) or not 1 <= len(candidates_raw) <= MAX_CANDIDATES_PER_SLOT:
                raise WorkshopBoundedPlannerError(f"slot candidates must contain 1..{MAX_CANDIDATES_PER_SLOT} exact pins")
            candidates: dict[tuple[str, int, str], dict[str, Any]] = {}
            for candidate_index, candidate in enumerate(candidates_raw):
                pin, _ = _pin_checked(registry, candidate, f"slots[{index}].candidates[{candidate_index}]")
                candidates[(pin["id"], pin["version"], pin["digest"])] = pin
            by_part[part] = {"part": part, "source": "explicit", "candidates": [candidates[key] for key in sorted(candidates)]}
        else:
            query = _query_spec(slot["query"], f"slots[{index}].query")
            by_part[part] = {"part": part, "source": "registry-query", "query": query, "candidates": _search_pool(registry, query)}
    if seen != set(sketch_ids):
        raise WorkshopBoundedPlannerError(
            "planner slots must cover every sketch part exactly once",
            {"missing": sorted(set(sketch_ids) - seen), "extra": sorted(seen - set(sketch_ids))},
        )
    slots = [by_part[part] for part in sketch_ids]
    counts = [len(slot["candidates"]) for slot in slots]
    combination_count = math.prod(counts) if counts else 0
    if combination_count > MAX_COMBINATIONS:
        raise WorkshopBoundedPlannerError(
            "planner candidate Cartesian product exceeds bounded combination budget",
            {"candidate_counts": counts, "combination_count": combination_count, "maximum": MAX_COMBINATIONS},
        )
    clearance_plan = validate_clearance_plan(raw["clearance_plan"], sketch) if "clearance_plan" in raw else None
    incumbent = None
    if "incumbent" in raw:
        incumbent, incumbent_definition = _pin_checked(registry, raw["incumbent"], "incumbent")
        if incumbent_definition["adapter"] != ASSEMBLY:
            raise WorkshopBoundedPlannerError("incumbent must be an exact saved assembly sticker")
    normalized = {
        "schema": PLANNER_SCHEMA,
        "sketch_digest": sketch["sketch_digest"],
        "slots": slots,
        "objective": copy.deepcopy(objective),
        "clearance_plan": clearance_plan,
        "incumbent": incumbent,
        "combination_count": combination_count,
    }
    body = copy.deepcopy(normalized)
    resolved_digest = _digest(body)
    if "planner_digest" in raw and raw["planner_digest"] != resolved_digest:
        raise WorkshopBoundedPlannerError("persisted planner digest does not match the resolved exact candidate body")
    normalized["planner_digest"] = resolved_digest
    return sketch, normalized


def _copy_closure(source: Registry, target: Registry, roots: list[dict[str, Any]]) -> None:
    definitions: dict[str, dict[str, Any]] = {}
    for root in roots:
        for definition in library_definitions(source, root):
            definitions[digest(definition)] = definition
    if not definitions:
        return
    assets: dict[str, bytes] = {}
    for definition in definitions.values():
        for reference in definition["assets"].values():
            if reference not in assets:
                assets[reference] = source.asset(reference)
    target.register_many([definitions[key] for key in sorted(definitions)], assets)


def _children(registry: Registry, sketch: dict[str, Any], selection: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    children = []
    for part in sketch["parts"]:
        pin = selection[part["id"]]
        definition = registry.get(pin["id"], pin["version"])
        if digest(definition) != pin["digest"]:
            raise WorkshopBoundedPlannerError("candidate pin drifted in evaluation registry", {"part": part["id"], "pin": pin})
        placed = instance(definition, part["id"])
        children.append({
            "instance": placed,
            "target": {"space": "3d", "socket": definition["attachment"]["socket"], "frame": copy.deepcopy(part["frame"])},
            "motion": None,
            "clip": None,
        })
    return children


def _assembly_definition(*, id: str, name: str, ver: int, socket: str, tags: list[str], origin: dict[str, str], children: list[dict[str, Any]]) -> dict[str, Any]:
    return validate({
        "schema": SCHEMA,
        "id": id,
        "version": ver,
        "name": name,
        "tags": tags,
        "origin": origin,
        "adapter": ASSEMBLY,
        "attachment": {"space": "3d", "socket": socket, "anchor": identity()},
        "recipe": {"children": copy.deepcopy(children)},
        "assets": {},
        "parameters": {},
    })


def _score(geometry: dict[str, Any]) -> dict[str, float] | None:
    if geometry.get("status") != "PASS":
        return None
    residuals: list[float] = []
    for row in geometry.get("parts", []):
        evidence = row.get("size_evidence", {})
        if evidence.get("status") != "PASS" or not isinstance(evidence.get("axis_residuals"), list):
            return None
        residuals.extend(float(value) for value in evidence["axis_residuals"])
    if not residuals:
        return None
    return {
        "max_axis_size_error_m": round(max(residuals), 12),
        "total_axis_size_error_m": round(sum(residuals), 12),
    }


def _numeric_key(score: dict[str, float]) -> tuple[float, float]:
    return score["max_axis_size_error_m"], score["total_axis_size_error_m"]


def _selection_signature(sketch: dict[str, Any], selection: dict[str, dict[str, Any]]) -> str:
    return _digest([{"part": part["id"], "sticker": selection[part["id"]]} for part in sketch["parts"]])


def _evaluate_existing(registry: Registry, sketch: dict[str, Any], pin: dict[str, Any], clearance_plan: dict[str, Any] | None) -> dict[str, Any]:
    try:
        geometry = compare_sticker_geometry(registry, sketch, pin)
        clearance = compare_sketch_clearance(registry, sketch, pin, clearance_plan) if clearance_plan is not None else None
        score = _score(geometry)
        accepted = geometry["status"] == "PASS" and (clearance is None or clearance["status"] == "PASS") and score is not None
        return {
            "accepted": accepted,
            "geometry_status": geometry["status"],
            "geometry_report_digest": geometry["report_digest"],
            "clearance_status": clearance["status"] if clearance is not None else "NOT_REQUESTED",
            "clearance_report_digest": clearance["report_digest"] if clearance is not None else None,
            "score": score,
            "geometry": geometry,
            "clearance": clearance,
            "reason": "all required evidence PASS" if accepted else "candidate did not satisfy every required evidence gate",
        }
    except (StickerGeometryCaliperError, StickerClearanceContactError, DesignWorkshopConstructionError, TypeError, ValueError) as exc:
        return {
            "accepted": False,
            "geometry_status": "HOLD",
            "geometry_report_digest": None,
            "clearance_status": "HOLD" if clearance_plan is not None else "NOT_REQUESTED",
            "clearance_report_digest": None,
            "score": None,
            "geometry": None,
            "clearance": None,
            "reason": f"evaluation held: {exc}",
        }


def _summary(index: int | None, selection: dict[str, dict[str, Any]] | None, evidence: dict[str, Any], *, kind: str) -> dict[str, Any]:
    return {
        "kind": kind,
        "index": index,
        "selection": copy.deepcopy(selection),
        "accepted": evidence["accepted"],
        "geometry_status": evidence["geometry_status"],
        "geometry_report_digest": evidence["geometry_report_digest"],
        "clearance_status": evidence["clearance_status"],
        "clearance_report_digest": evidence["clearance_report_digest"],
        "score": copy.deepcopy(evidence["score"]),
        "reason": evidence["reason"],
        "selection_signature": _selection_signature_from_map(selection) if selection is not None else None,
    }


def _selection_signature_from_map(selection: dict[str, dict[str, Any]]) -> str:
    return _digest([{"part": key, "sticker": selection[key]} for key in sorted(selection)])


def _run_preview(registry: Registry, sketch_raw: Any, planner_raw: Any) -> tuple[dict[str, Any], dict[str, Any] | None]:
    sketch, planner = _normalize_request(registry, sketch_raw, planner_raw)
    candidate_pins = [pin for slot in planner["slots"] for pin in slot["candidates"]]
    roots = []
    for pin in candidate_pins:
        roots.append(_exact_definition(registry, pin))
    if planner["incumbent"] is not None:
        roots.append(_exact_definition(registry, planner["incumbent"]))

    with tempfile.TemporaryDirectory(prefix="axm-workshop-planner-") as temp:
        with Registry(Path(temp) / "planner.sqlite") as trial:
            _copy_closure(registry, trial, roots)
            incumbent_evidence = None
            incumbent_summary = None
            if planner["incumbent"] is not None:
                incumbent_evidence = _evaluate_existing(trial, sketch, planner["incumbent"], planner["clearance_plan"])
                incumbent_summary = {
                    "kind": "incumbent",
                    "assembly": copy.deepcopy(planner["incumbent"]),
                    "accepted": incumbent_evidence["accepted"],
                    "geometry_status": incumbent_evidence["geometry_status"],
                    "geometry_report_digest": incumbent_evidence["geometry_report_digest"],
                    "clearance_status": incumbent_evidence["clearance_status"],
                    "clearance_report_digest": incumbent_evidence["clearance_report_digest"],
                    "score": copy.deepcopy(incumbent_evidence["score"]),
                    "reason": incumbent_evidence["reason"],
                }

            evaluations: list[dict[str, Any]] = []
            full: list[tuple[dict[str, Any], dict[str, Any], dict[str, dict[str, Any]]]] = []
            pools = [slot["candidates"] for slot in planner["slots"]]
            for index, combination in enumerate(itertools.product(*pools) if pools and all(pools) else []):
                selection = {slot["part"]: copy.deepcopy(pin) for slot, pin in zip(planner["slots"], combination)}
                children = _children(trial, sketch, selection)
                candidate = _assembly_definition(
                    id=f"planner-candidate-{index + 1:03d}",
                    name=f"Planner candidate {index + 1:03d}",
                    ver=1,
                    socket="mount",
                    tags=["planner-candidate"],
                    origin={"author": "AXM workshop planner", "license": "CC0-1.0", "source": f"ephemeral planner evaluation {planner['planner_digest']}"},
                    children=children,
                )
                expand(trial, candidate)
                trial.register(candidate)
                pin = _exact_pin(candidate)
                evidence = _evaluate_existing(trial, sketch, pin, planner["clearance_plan"])
                summary = {
                    "index": index + 1,
                    "selection": copy.deepcopy(selection),
                    "selection_signature": _selection_signature(sketch, selection),
                    "accepted": evidence["accepted"],
                    "geometry_status": evidence["geometry_status"],
                    "geometry_report_digest": evidence["geometry_report_digest"],
                    "clearance_status": evidence["clearance_status"],
                    "clearance_report_digest": evidence["clearance_report_digest"],
                    "score": copy.deepcopy(evidence["score"]),
                    "reason": evidence["reason"],
                }
                evaluations.append(summary)
                full.append((summary, evidence, selection))

            passing = [row for row in full if row[0]["accepted"]]
            passing.sort(key=lambda row: (_numeric_key(row[0]["score"]), row[0]["selection_signature"]))
            best = passing[0] if passing else None
            selected_public = None
            selected_evidence = None
            outcome = "HOLD_NO_PASSING_CANDIDATE"
            if planner["incumbent"] is not None:
                if incumbent_evidence is not None and incumbent_evidence["accepted"]:
                    if best is not None and _numeric_key(best[0]["score"]) < _numeric_key(incumbent_evidence["score"]):
                        selected_public = {"kind": "candidate", **copy.deepcopy(best[0])}
                        selected_evidence = best[1]
                        outcome = "SELECTED_STRICT_NUMERIC_IMPROVEMENT"
                    else:
                        selected_public = {"kind": "incumbent", "assembly": copy.deepcopy(planner["incumbent"]),
                                           "accepted": True, "score": copy.deepcopy(incumbent_evidence["score"])}
                        selected_evidence = incumbent_evidence
                        outcome = "INCUMBENT_RETAINED_NO_STRICT_IMPROVEMENT"
                elif best is not None:
                    selected_public = {"kind": "candidate", **copy.deepcopy(best[0])}
                    selected_evidence = best[1]
                    outcome = "SELECTED_PASSING_RECOVERY_FROM_NONPASS_INCUMBENT"
                else:
                    selected_public = {"kind": "incumbent", "assembly": copy.deepcopy(planner["incumbent"]),
                                       "accepted": False, "score": copy.deepcopy(incumbent_evidence["score"] if incumbent_evidence else None)}
                    selected_evidence = incumbent_evidence
                    outcome = "HOLD_INCUMBENT_RETAINED_NO_PASSING_REPLACEMENT"
            elif best is not None:
                selected_public = {"kind": "candidate", **copy.deepcopy(best[0])}
                selected_evidence = best[1]
                outcome = "SELECTED_BEST_PASSING_CANDIDATE"

            empty_slots = [slot["part"] for slot in planner["slots"] if not slot["candidates"]]
            report = {
                "schema": PREVIEW_SCHEMA,
                "truth_status": "BOUNDED_REGISTRY_SEARCH_ASSEMBLY_MEASURE_REJECT_SELECT_WITH_STRICT_INCUMBENT_PROTECTION",
                "status": "PASS" if selected_public is not None and selected_public.get("accepted") else "HOLD",
                "outcome": outcome,
                "sketch_digest": sketch["sketch_digest"],
                "planner_digest": planner["planner_digest"],
                "resolved_slots": copy.deepcopy(planner["slots"]),
                "combination_count": planner["combination_count"],
                "evaluated_candidates": len(evaluations),
                "empty_slots": empty_slots,
                "incumbent": incumbent_summary,
                "candidates": evaluations,
                "selection": selected_public,
                "selection_evidence": ({
                    "geometry": copy.deepcopy(selected_evidence["geometry"]),
                    "clearance": copy.deepcopy(selected_evidence["clearance"]),
                } if selected_evidence is not None else None),
                "source_registry_mutated": False,
                "objective": copy.deepcopy(planner["objective"]),
                "limitations": [
                    "v0.1 optimizes only actual numeric part-size agreement after every required geometry/clearance gate passes",
                    "clearance requirements are gates, not a hidden preference to maximize or minimize gaps",
                    "registry metadata narrows the candidate pool but does not prove semantic suitability, aesthetics, gameplay quality, or user preference",
                    "visual quality is not inferred from geometry; rendered/user evidence must become a separate future gate",
                    "candidate assemblies exist only in a temporary evaluation registry; preview never writes them into the source registry",
                    "a passing incumbent is retained unless a candidate has a strictly smaller numeric size-error tuple",
                ],
            }
            report["report_digest"] = _digest(report)
            return report, selected_evidence


def preview_workshop_plan(registry: Registry, sketch_raw: Any, planner_raw: Any) -> dict[str, Any]:
    report, _ = _run_preview(registry, sketch_raw, planner_raw)
    return report


def _retention_spec(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"id", "name", "version", "socket", "tags", "origin"}:
        raise WorkshopBoundedPlannerError("retention requires id, name, version, socket, tags, and origin")
    try:
        sticker_id = identifier(raw["id"])
        sticker_name = text(raw["name"], 160)
        sticker_version = version(raw["version"])
        socket = identifier(raw["socket"])
    except ValueError as exc:
        raise WorkshopBoundedPlannerError(str(exc)) from exc
    tags = raw["tags"]
    if not isinstance(tags, list) or len(tags) > 31 or len(tags) != len(set(tags)):
        raise WorkshopBoundedPlannerError("retention tags must be at most 31 unique identifiers")
    try:
        tags = [identifier(tag) for tag in tags]
    except ValueError as exc:
        raise WorkshopBoundedPlannerError(str(exc)) from exc
    origin = raw["origin"]
    if not isinstance(origin, dict) or set(origin) != {"author", "license", "source"}:
        raise WorkshopBoundedPlannerError("retention origin must declare author, license, and source")
    try:
        clean_origin = {key: text(origin[key]) for key in ("author", "license", "source")}
    except ValueError as exc:
        raise WorkshopBoundedPlannerError(str(exc)) from exc
    return {"id": sticker_id, "name": sticker_name, "version": sticker_version, "socket": socket, "tags": tags, "origin": clean_origin}


def retain_workshop_plan(registry: Registry, sketch_raw: Any, planner_raw: Any, retention_raw: Any) -> dict[str, Any]:
    preview, _ = _run_preview(registry, sketch_raw, planner_raw)
    selected = preview.get("selection")
    if not selected or not selected.get("accepted"):
        raise WorkshopBoundedPlannerError("planner has no passing selected construction to retain")
    if selected["kind"] == "incumbent":
        result = {
            "schema": RETENTION_SCHEMA,
            "truth_status": "INCUMBENT_RETAINED_WITHOUT_NEW_REGISTRY_WRITE",
            "status": "PASS",
            "planner_report_digest": preview["report_digest"],
            "assembly": copy.deepcopy(selected["assembly"]),
            "new_registry_entry": False,
            "reason": preview["outcome"],
        }
        result["receipt_digest"] = _digest(result)
        return result

    retention = _retention_spec(retention_raw)
    sketch = validate_sketch(sketch_raw)
    selection = selected["selection"]
    children = _children(registry, sketch, selection)
    lineage = f"{retention['origin']['source']} | AXM workshop planner {preview['planner_digest']} selected {selected['selection_signature']}"
    if len(lineage) > 2000:
        raise WorkshopBoundedPlannerError("retained provenance source exceeds sticker source bound")
    final = _assembly_definition(
        id=retention["id"],
        name=retention["name"],
        ver=retention["version"],
        socket=retention["socket"],
        tags=list(dict.fromkeys(retention["tags"] + ["planner-retained"])),
        origin={"author": retention["origin"]["author"], "license": retention["origin"]["license"], "source": lineage},
        children=children,
    )
    # Dependency closure and all source instances are rechecked against the live registry
    # before the one immutable root definition is committed.
    expand(registry, final)
    registry.register(final)
    pin = _exact_pin(final)
    geometry = compare_sticker_geometry(registry, sketch, pin)
    planner = _normalize_request(registry, sketch, planner_raw)[1]
    clearance = compare_sketch_clearance(registry, sketch, pin, planner["clearance_plan"]) if planner["clearance_plan"] is not None else None
    verification_pass = geometry["status"] == "PASS" and (clearance is None or clearance["status"] == "PASS")
    result = {
        "schema": RETENTION_SCHEMA,
        "truth_status": "NEW_IMMUTABLE_PLANNER_SELECTED_ASSEMBLY_RETAINED_AND_REMEASURED",
        "status": "PASS" if verification_pass else "HOLD",
        "planner_report_digest": preview["report_digest"],
        "planner_digest": preview["planner_digest"],
        "selection_signature": selected["selection_signature"],
        "assembly": pin,
        "new_registry_entry": True,
        "geometry_report_digest": geometry["report_digest"],
        "geometry_status": geometry["status"],
        "clearance_report_digest": clearance["report_digest"] if clearance is not None else None,
        "clearance_status": clearance["status"] if clearance is not None else "NOT_REQUESTED",
        "verification_passed": verification_pass,
        "limitations": [
            "retention preserves the selected construction recipe and exact source pins; it does not promote visual or gameplay quality",
            "a retained immutable version is evidence-bearing state, not CANON authority",
        ],
    }
    result["receipt_digest"] = _digest(result)
    return result


def planner_summary() -> dict[str, Any]:
    return {
        "schemas": [PLANNER_SCHEMA, PREVIEW_SCHEMA, RETENTION_SCHEMA],
        "operations": sorted(PLANNER_OPERATIONS),
        "candidate_sources": ["explicit exact sticker pins", "bounded exact registry tag/socket/adapter queries"],
        "maximum_candidates_per_part": MAX_CANDIDATES_PER_SLOT,
        "maximum_combinations": MAX_COMBINATIONS,
        "objective": "all required evidence must PASS; among passing candidates minimize max then total XYZ size error; passing incumbent wins unless strictly improved",
        "truth_boundary": "construction selection from numeric geometry/clearance evidence only; no hidden aesthetic, semantic, gameplay, physics, or engine-quality judgment",
    }


def operate_workshop_bounded_planner(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-workshop-planner":
        return {"truth_status": "DECLARED_WORKSHOP_BOUNDED_PLANNER_V0_1", **planner_summary()}
    database = inputs.get("database")
    if not isinstance(database, str) or not database.strip():
        raise WorkshopBoundedPlannerError("workshop planner requires a sticker database path")
    path = _resolve_registry_path(root, database)
    if _machine_body(root, path):
        raise WorkshopBoundedPlannerError("workshop planner database must be an ordinary creation path or external path")
    with Registry(path) as registry:
        if operation == "preview-workshop-plan":
            return preview_workshop_plan(registry, inputs.get("sketch"), inputs.get("planner"))
        if operation == "retain-workshop-plan":
            return retain_workshop_plan(registry, inputs.get("sketch"), inputs.get("planner"), inputs.get("retention"))
    raise WorkshopBoundedPlannerError("workshop planner operation is unsupported", {"operation": operation})

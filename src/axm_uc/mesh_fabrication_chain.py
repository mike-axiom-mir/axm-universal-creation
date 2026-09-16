from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile
from pathlib import Path
from typing import Any

from .mesh_precision_cutter import (
    EPSILON,
    SOURCE_TOLERANCE,
    MeshPrecisionCutterError,
    _normalize_expected_digest,
    _read_source_primitive,
    _signed_volume,
)
from .mesh_topology import MeshTopologyError, inspect_mesh_topology
from .oriented_mesh_precision_cutter import (
    _axis_vector,
    _canonical_axis_order,
    _canonical_normal_to_world,
    _canonical_point_from_world,
    _canonical_to_world,
    _match_frame_axis,
    _recognize_oriented_box,
    _vec3,
)
from .precision_cutter import (
    _canonical,
    _extrude_profile,
    _normalize_profile,
    _number,
    _surface_specification,
)
from .procedural_3d import Procedural3DError, build_glb, publish_glb

FABRICATION_CHAIN_SCHEMA = "axm.mesh-fabrication-chain/v0.4"
FABRICATION_LINEAGE_SCHEMA = "axm.mesh-fabrication-lineage/v0.4"
MAX_CHAIN_CUTS = 32
_SUPPORTED_SIDES = {"u-min", "u-max", "v-min", "v-max"}


def fabrication_chain_summary() -> dict[str, Any]:
    return {
        "schema": FABRICATION_CHAIN_SCHEMA,
        "lineage_schema": FABRICATION_LINEAGE_SCHEMA,
        "truth_status": "LIVE_HASH_LINKED_CUMULATIVE_MESH_FABRICATION",
        "operation": "box-notch-chain",
        "maximum_cuts": MAX_CHAIN_CUTS,
        "source_scope": "one proven rigid rectangular-prism source frame, then hash-bound cumulative derived outputs",
        "resume_contract": "recompile prior cumulative recipe and require exact previous GLB digest match before append",
        "rotated_translated_source_supported": True,
        "multiple_nonoverlapping_notches_supported": True,
        "round_hole_chaining": False,
        "full_arbitrary_mesh_csg": False,
    }


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _lineage_digest(lineage: dict[str, Any]) -> str:
    body = {key: value for key, value in lineage.items() if key != "lineage_sha256"}
    return _digest(body)


def _normalize_digest(value: Any, label: str) -> str | None:
    try:
        return _normalize_expected_digest(value)
    except MeshPrecisionCutterError as exc:
        raise MeshPrecisionCutterError(str(exc).replace("expected_source_sha256", label), exc.details) from exc


def _cut(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError(f"cuts[{index}] must be an object")
    required = {"id", "operation", "center", "side", "span", "depth"}
    optional = {"kerf"}
    missing = required - set(raw)
    extra = set(raw) - required - optional
    if missing or extra:
        raise MeshPrecisionCutterError(
            f"cuts[{index}] fields do not match the v0.4 grammar",
            {"missing": sorted(missing), "unexpected": sorted(extra)},
        )
    cut_id = raw["id"]
    if not isinstance(cut_id, str) or not 1 <= len(cut_id.strip()) <= 80:
        raise MeshPrecisionCutterError(f"cuts[{index}].id must contain 1..80 characters")
    operation = str(raw["operation"]).strip().casefold()
    if operation != "box-notch":
        raise MeshPrecisionCutterError(
            "v0.4 cumulative fabrication currently supports box-notch cuts only",
            {"unsupported_operation": operation, "round_hole_chaining": False},
        )
    side = str(raw["side"]).strip().casefold()
    if side not in _SUPPORTED_SIDES:
        raise MeshPrecisionCutterError(
            f"cuts[{index}].side must be one of u-min, u-max, v-min, v-max"
        )
    return {
        "id": cut_id.strip(),
        "operation": "box-notch",
        "center": list(_vec3(raw["center"], f"cuts[{index}].center")),
        "side": side,
        "span": _number(raw["span"], f"cuts[{index}].span", 0.0001, 100000.0),
        "depth": _number(raw["depth"], f"cuts[{index}].depth", 0.0001, 100000.0),
        "kerf": _number(raw.get("kerf", 0.0), f"cuts[{index}].kerf", 0.0, 1000.0),
    }


def prepare_fabrication_chain(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise MeshPrecisionCutterError("v0.4 fabrication-chain specification must be an object")
    required = {"schema", "name", "axis_vector", "cuts"}
    if set(raw) != required:
        raise MeshPrecisionCutterError(
            "v0.4 fabrication-chain fields do not match the bounded grammar",
            {
                "missing": sorted(required - set(raw)),
                "unexpected": sorted(set(raw) - required),
            },
        )
    if raw["schema"] != FABRICATION_CHAIN_SCHEMA:
        raise MeshPrecisionCutterError("unsupported fabrication-chain schema")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise MeshPrecisionCutterError("name must contain 1..120 characters")
    cuts = raw["cuts"]
    if not isinstance(cuts, list) or not 1 <= len(cuts) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cuts must contain 1 through {MAX_CHAIN_CUTS} new box-notch cuts"
        )
    normalized = [_cut(value, index) for index, value in enumerate(cuts)]
    ids = [value["id"] for value in normalized]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("new fabrication-chain cut ids must be unique")
    return {
        "schema": FABRICATION_CHAIN_SCHEMA,
        "name": name.strip(),
        "axis_vector": list(_axis_vector(raw["axis_vector"])),
        "cuts": normalized,
    }


def _notch_rectangle(
    cut: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
) -> dict[str, Any]:
    width = float(frame["extents"][order[0]])
    thickness = float(frame["extents"][order[1]])
    depth = float(frame["extents"][order[2]])
    half_width, half_depth = width / 2.0, depth / 2.0
    center = _canonical_point_from_world(tuple(cut["center"]), frame, order)
    if abs(center[1]) > thickness / 2.0 + float(frame["tolerance"]):
        raise MeshPrecisionCutterError(
            f"cut {cut['id']} center lies outside the source extent along the fabrication axis"
        )
    effective_span = float(cut["span"]) + float(cut["kerf"])
    effective_depth = float(cut["depth"]) + float(cut["kerf"]) / 2.0
    if cut["side"].startswith("u-"):
        span_center = center[2]
        span_half_extent = half_depth
        perpendicular = width
    else:
        span_center = center[0]
        span_half_extent = half_width
        perpendicular = depth
    half_span = effective_span / 2.0
    a, b = span_center - half_span, span_center + half_span
    if (
        half_span <= 0.0
        or a <= -span_half_extent + EPSILON
        or b >= span_half_extent - EPSILON
    ):
        raise MeshPrecisionCutterError(
            f"cut {cut['id']} span must stay strictly inside its selected stock edge"
        )
    if effective_depth <= 0.0 or effective_depth >= perpendicular - EPSILON:
        raise MeshPrecisionCutterError(
            f"cut {cut['id']} depth must leave source material behind"
        )

    if cut["side"] == "v-min":
        rectangle = (a, -half_depth, b, -half_depth + effective_depth)
    elif cut["side"] == "v-max":
        rectangle = (a, half_depth - effective_depth, b, half_depth)
    elif cut["side"] == "u-min":
        rectangle = (-half_width, a, -half_width + effective_depth, b)
    else:
        rectangle = (half_width - effective_depth, a, half_width, b)

    return {
        "id": cut["id"],
        "operation": "box-notch",
        "side": cut["side"],
        "center_world": list(cut["center"]),
        "center_canonical": [float(value) for value in center],
        "requested_span": float(cut["span"]),
        "effective_span": effective_span,
        "requested_depth": float(cut["depth"]),
        "effective_depth": effective_depth,
        "kerf": float(cut["kerf"]),
        "span_center": float(span_center),
        "span_interval": [float(a), float(b)],
        "rectangle": [float(value) for value in rectangle],
        "removed_area": effective_span * effective_depth,
        "resolved_cut_sha256": "",
    }


def _rectangles_conflict(first: dict[str, Any], second: dict[str, Any], tolerance: float) -> bool:
    ax0, az0, ax1, az1 = first["rectangle"]
    bx0, bz0, bx1, bz1 = second["rectangle"]
    separated = (
        ax1 < bx0 - tolerance
        or bx1 < ax0 - tolerance
        or az1 < bz0 - tolerance
        or bz1 < az0 - tolerance
    )
    return not separated


def _validate_resolved_cuts(cuts: list[dict[str, Any]], tolerance: float) -> None:
    if not 1 <= len(cuts) <= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cumulative fabrication chain must contain 1 through {MAX_CHAIN_CUTS} cuts"
        )
    ids = [row["id"] for row in cuts]
    if len(ids) != len(set(ids)):
        raise MeshPrecisionCutterError("cumulative fabrication-chain cut ids must remain unique")
    for index, first in enumerate(cuts):
        for second in cuts[index + 1 :]:
            if _rectangles_conflict(first, second, tolerance):
                raise MeshPrecisionCutterError(
                    "v0.4 refuses overlapping or touching cumulative notch volumes",
                    {"first_cut": first["id"], "second_cut": second["id"]},
                )


def _append_point(profile: list[tuple[float, float]], point: tuple[float, float]) -> None:
    normalized = (float(point[0]), float(point[1]))
    if not profile or math.dist(profile[-1], normalized) > EPSILON:
        profile.append(normalized)


def _profile_from_notches(
    width: float,
    depth: float,
    cuts: list[dict[str, Any]],
) -> list[tuple[float, float]]:
    half_width, half_depth = width / 2.0, depth / 2.0
    grouped = {side: [] for side in _SUPPORTED_SIDES}
    for cut in cuts:
        grouped[cut["side"]].append(cut)

    profile: list[tuple[float, float]] = []
    _append_point(profile, (-half_width, -half_depth))

    for cut in sorted(grouped["v-min"], key=lambda row: row["span_interval"][0]):
        a, b = cut["span_interval"]
        top = -half_depth + cut["effective_depth"]
        _append_point(profile, (a, -half_depth))
        _append_point(profile, (a, top))
        _append_point(profile, (b, top))
        _append_point(profile, (b, -half_depth))
    _append_point(profile, (half_width, -half_depth))

    for cut in sorted(grouped["u-max"], key=lambda row: row["span_interval"][0]):
        a, b = cut["span_interval"]
        left = half_width - cut["effective_depth"]
        _append_point(profile, (half_width, a))
        _append_point(profile, (left, a))
        _append_point(profile, (left, b))
        _append_point(profile, (half_width, b))
    _append_point(profile, (half_width, half_depth))

    for cut in sorted(grouped["v-max"], key=lambda row: row["span_interval"][1], reverse=True):
        a, b = cut["span_interval"]
        bottom = half_depth - cut["effective_depth"]
        _append_point(profile, (b, half_depth))
        _append_point(profile, (b, bottom))
        _append_point(profile, (a, bottom))
        _append_point(profile, (a, half_depth))
    _append_point(profile, (-half_width, half_depth))

    for cut in sorted(grouped["u-min"], key=lambda row: row["span_interval"][1], reverse=True):
        a, b = cut["span_interval"]
        right = -half_width + cut["effective_depth"]
        _append_point(profile, (-half_width, b))
        _append_point(profile, (right, b))
        _append_point(profile, (right, a))
        _append_point(profile, (-half_width, a))

    return _normalize_profile([[x, z] for x, z in profile])


def _compile_state(
    *,
    name: str,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    material: dict[str, Any],
    cuts: list[dict[str, Any]],
) -> dict[str, Any]:
    width = float(frame["extents"][order[0]])
    thickness = float(frame["extents"][order[1]])
    depth = float(frame["extents"][order[2]])
    _validate_resolved_cuts(cuts, max(SOURCE_TOLERANCE, float(frame["tolerance"])))
    profile = _profile_from_notches(width, depth, cuts)
    canonical_positions, canonical_normals, indices, top_triangles = _extrude_profile(
        profile, thickness
    )
    positions = [_canonical_to_world(point, frame, order) for point in canonical_positions]
    normals = [
        _canonical_normal_to_world(normal, frame, order)
        for normal in canonical_normals
    ]
    try:
        topology = inspect_mesh_topology(
            positions, indices, weld_tolerance=SOURCE_TOLERANCE
        )
    except MeshTopologyError as exc:
        raise MeshPrecisionCutterError(str(exc)) from exc
    if (
        topology["status"] != "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE"
        or topology["triangle_component_count"] != 1
    ):
        raise MeshPrecisionCutterError(
            "cumulative fabrication output did not remain one closed oriented component",
            {"topology": topology},
        )
    volume = _signed_volume(positions, indices)
    source_volume = float(frame["box_volume"])
    if volume <= 0.0 or volume >= source_volume - EPSILON:
        raise MeshPrecisionCutterError(
            "cumulative fabrication output volume is not strictly smaller than source stock",
            {"source_volume": source_volume, "output_volume": volume},
        )
    surface = _surface_specification(name, positions, normals, indices, material)
    glb = build_glb(surface)
    body = glb["body"]
    removed_area = sum(float(cut["removed_area"]) for cut in cuts)
    expected_volume = source_volume - removed_area * thickness
    tolerance = max(source_volume * 1e-5, 1e-8)
    if abs(volume - expected_volume) > tolerance:
        raise MeshPrecisionCutterError(
            "closed-mesh volume does not match the non-overlapping cumulative notch receipt",
            {
                "observed_output_volume": volume,
                "expected_output_volume": expected_volume,
                "tolerance": tolerance,
            },
        )
    return {
        "surface_specification": surface,
        "glb_body": body,
        "glb_sha256": hashlib.sha256(body).hexdigest(),
        "specification_sha256": glb["specification_sha256"],
        "topology": topology,
        "geometry": {
            "vertices": len(positions),
            "triangles": len(indices) // 3,
            "top_surface_triangles": top_triangles,
            "profile_points": len(profile),
        },
        "metrics": {
            "source_volume": source_volume,
            "output_volume": volume,
            "removed_volume": source_volume - volume,
            "resolved_removed_area": removed_area,
            "fabrication_thickness": thickness,
        },
    }


def _root_from_source(
    source_path: Path,
    specification: dict[str, Any],
    expected_source_sha256: str | None,
) -> dict[str, Any]:
    expected = _normalize_digest(expected_source_sha256, "expected_source_sha256")
    source = _read_source_primitive(source_path)
    if expected is not None and source["source_sha256"] != expected:
        raise MeshPrecisionCutterError(
            "source GLB digest does not match expected_source_sha256",
            {"expected": expected, "observed": source["source_sha256"]},
        )
    frame = _recognize_oriented_box(source)
    cut_axis, direction_sign, alignment = _match_frame_axis(
        tuple(specification["axis_vector"]), frame
    )
    order = _canonical_axis_order(cut_axis)
    root = {
        "source_sha256": source["source_sha256"],
        "source_bytes": source["source_bytes"],
        "material_mode": source["material_mode"],
        "material": source["material"],
        "source_topology": source["topology"],
        "frame": frame,
    }
    root["root_sha256"] = _digest(root)
    return {
        "root": root,
        "frame": frame,
        "order": order,
        "cut_axis": cut_axis,
        "direction_sign": direction_sign,
        "alignment": alignment,
        "resolved_cuts": [],
        "steps": [],
        "parent_lineage_sha256": None,
    }


def _read_json_object(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
        value = json.loads(raw)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise MeshPrecisionCutterError("fabrication lineage receipt is unreadable JSON") from exc
    if not isinstance(value, dict):
        raise MeshPrecisionCutterError("fabrication lineage receipt must be a JSON object")
    return value


def _load_parent_lineage(
    source_path: Path,
    lineage_path: Path,
    specification: dict[str, Any],
    expected_lineage_sha256: str | None,
) -> dict[str, Any]:
    if not lineage_path.is_file() or lineage_path.is_symlink():
        raise MeshPrecisionCutterError("lineage_path must be an existing ordinary JSON receipt")
    lineage = _read_json_object(lineage_path)
    if lineage.get("schema") != FABRICATION_LINEAGE_SCHEMA:
        raise MeshPrecisionCutterError("unsupported fabrication lineage receipt schema")
    observed_lineage_digest = _lineage_digest(lineage)
    if lineage.get("lineage_sha256") != observed_lineage_digest:
        raise MeshPrecisionCutterError(
            "fabrication lineage self-digest does not match its contents"
        )
    expected = _normalize_digest(
        expected_lineage_sha256, "expected_lineage_sha256"
    )
    if expected is not None and expected != observed_lineage_digest:
        raise MeshPrecisionCutterError(
            "fabrication lineage digest does not match expected_lineage_sha256",
            {"expected": expected, "observed": observed_lineage_digest},
        )
    required = {"root", "axis", "cuts", "steps", "output"}
    if not required <= set(lineage):
        raise MeshPrecisionCutterError("fabrication lineage receipt is missing required state")
    root = lineage["root"]
    axis = lineage["axis"]
    cuts = lineage["cuts"]
    steps = lineage["steps"]
    output = lineage["output"]
    if not isinstance(root, dict) or not isinstance(axis, dict) or not isinstance(cuts, list) or not isinstance(steps, list) or not isinstance(output, dict):
        raise MeshPrecisionCutterError("fabrication lineage state has invalid structural types")
    if len(cuts) != len(steps) or not cuts:
        raise MeshPrecisionCutterError("fabrication lineage cut/step history is inconsistent")
    claimed_root_sha = root.get("root_sha256")
    root_body = {key: value for key, value in root.items() if key != "root_sha256"}
    if claimed_root_sha != _digest(root_body):
        raise MeshPrecisionCutterError("fabrication lineage root digest is invalid")
    parent_state = claimed_root_sha
    for index, (cut, step) in enumerate(zip(cuts, steps), start=1):
        if not isinstance(cut, dict) or not isinstance(step, dict):
            raise MeshPrecisionCutterError("fabrication lineage cut/step entries must be objects")
        claimed_cut_sha = cut.get("resolved_cut_sha256")
        cut_body = {key: value for key, value in cut.items() if key != "resolved_cut_sha256"}
        if claimed_cut_sha != _digest(cut_body):
            raise MeshPrecisionCutterError(
                f"fabrication lineage cut digest is invalid at step {index}"
            )
        expected_step = {
            "step": index,
            "cut_id": cut.get("id"),
            "cut_sha256": claimed_cut_sha,
            "parent_state_sha256": parent_state,
        }
        expected_state_sha = _digest(expected_step)
        if (
            step.get("step") != index
            or step.get("cut_id") != cut.get("id")
            or step.get("cut_sha256") != claimed_cut_sha
            or step.get("parent_state_sha256") != parent_state
            or step.get("state_sha256") != expected_state_sha
        ):
            raise MeshPrecisionCutterError(
                f"fabrication lineage step hash chain is invalid at step {index}"
            )
        parent_state = expected_state_sha
    if lineage.get("cumulative_recipe_sha256") != _digest(cuts):
        raise MeshPrecisionCutterError("fabrication lineage cumulative recipe digest is invalid")
    if len(cuts) >= MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError("fabrication lineage already reached the v0.4 cut limit")

    raw = source_path.read_bytes()
    current_sha = hashlib.sha256(raw).hexdigest()
    if current_sha != output.get("sha256"):
        raise MeshPrecisionCutterError(
            "resume source GLB does not match the lineage final output digest",
            {"expected": output.get("sha256"), "observed": current_sha},
        )
    current_source = _read_source_primitive(source_path)
    if current_source["source_sha256"] != current_sha:
        raise MeshPrecisionCutterError("resume source digest changed during inspection")
    if current_source["material"] != root.get("material"):
        raise MeshPrecisionCutterError("resume source material no longer matches lineage root material")

    frame = root.get("frame")
    if not isinstance(frame, dict) or frame.get("frame_sha256") != _digest(
        {key: value for key, value in frame.items() if key != "frame_sha256"}
    ):
        candidate = dict(frame) if isinstance(frame, dict) else {}
        claimed = candidate.pop("frame_sha256", None)
        if claimed != _digest(candidate):
            raise MeshPrecisionCutterError("lineage root frame digest is invalid")
    order_raw = axis.get("canonical_order")
    if (
        not isinstance(order_raw, list)
        or sorted(order_raw) != [0, 1, 2]
        or any(type(value) is not int for value in order_raw)
    ):
        raise MeshPrecisionCutterError("lineage canonical axis order is invalid")
    order = tuple(order_raw)
    cut_axis = axis.get("frame_axis_index")
    if type(cut_axis) is not int or not 0 <= cut_axis <= 2:
        raise MeshPrecisionCutterError("lineage frame axis index is invalid")
    new_axis, direction_sign, alignment = _match_frame_axis(
        tuple(specification["axis_vector"]), frame
    )
    if new_axis != cut_axis:
        raise MeshPrecisionCutterError(
            "v0.4 resume cuts must remain on the lineage fabrication axis",
            {"lineage_axis": cut_axis, "requested_axis": new_axis},
        )

    prior_name = output.get("name")
    if not isinstance(prior_name, str) or not prior_name:
        raise MeshPrecisionCutterError("lineage output name is invalid")
    prior_compiled = _compile_state(
        name=prior_name,
        frame=frame,
        order=order,
        material=root["material"],
        cuts=cuts,
    )
    if prior_compiled["glb_sha256"] != current_sha:
        raise MeshPrecisionCutterError(
            "resume lineage does not deterministically rebuild the supplied prior GLB",
            {
                "recompiled": prior_compiled["glb_sha256"],
                "observed": current_sha,
            },
        )
    if output.get("specification_sha256") != prior_compiled["specification_sha256"]:
        raise MeshPrecisionCutterError(
            "lineage output specification digest does not match deterministic rebuild"
        )
    return {
        "root": root,
        "frame": frame,
        "order": order,
        "cut_axis": cut_axis,
        "direction_sign": direction_sign,
        "alignment": alignment,
        "resolved_cuts": [dict(value) for value in cuts],
        "steps": [dict(value) for value in steps],
        "parent_lineage_sha256": observed_lineage_digest,
    }


def _resolve_new_cuts(
    specification: dict[str, Any],
    *,
    frame: dict[str, Any],
    order: tuple[int, int, int],
    existing: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    existing_ids = {cut["id"] for cut in existing}
    resolved: list[dict[str, Any]] = []
    for cut in specification["cuts"]:
        if cut["id"] in existing_ids or any(row["id"] == cut["id"] for row in resolved):
            raise MeshPrecisionCutterError(
                f"fabrication cut id already exists in lineage: {cut['id']}"
            )
        row = _notch_rectangle(cut, frame=frame, order=order)
        row["resolved_cut_sha256"] = _digest(
            {key: value for key, value in row.items() if key != "resolved_cut_sha256"}
        )
        resolved.append(row)
    cumulative = existing + resolved
    if len(cumulative) > MAX_CHAIN_CUTS:
        raise MeshPrecisionCutterError(
            f"cumulative fabrication chain exceeds {MAX_CHAIN_CUTS} cuts"
        )
    _validate_resolved_cuts(
        cumulative, max(SOURCE_TOLERANCE, float(frame["tolerance"]))
    )
    return resolved


def _steps_for_append(
    *,
    root_sha256: str,
    previous_steps: list[dict[str, Any]],
    new_cuts: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    steps = [dict(value) for value in previous_steps]
    parent_state = steps[-1]["state_sha256"] if steps else root_sha256
    for cut in new_cuts:
        state = {
            "step": len(steps) + 1,
            "cut_id": cut["id"],
            "cut_sha256": cut["resolved_cut_sha256"],
            "parent_state_sha256": parent_state,
        }
        state["state_sha256"] = _digest(state)
        parent_state = state["state_sha256"]
        steps.append(state)
    return steps


def _build_lineage(
    *,
    specification: dict[str, Any],
    base: dict[str, Any],
    cumulative_cuts: list[dict[str, Any]],
    steps: list[dict[str, Any]],
    compiled: dict[str, Any],
) -> dict[str, Any]:
    lineage = {
        "schema": FABRICATION_LINEAGE_SCHEMA,
        "root": base["root"],
        "axis": {
            "frame_axis_index": base["cut_axis"],
            "canonical_order": list(base["order"]),
            "axis_alignment": base["alignment"],
            "axis_vector_last_request": list(specification["axis_vector"]),
        },
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "cuts": cumulative_cuts,
        "steps": steps,
        "cumulative_recipe_sha256": _digest(cumulative_cuts),
        "output": {
            "name": specification["name"],
            "sha256": compiled["glb_sha256"],
            "specification_sha256": compiled["specification_sha256"],
            "geometry": compiled["geometry"],
            "topology": compiled["topology"],
            "metrics": compiled["metrics"],
        },
        "truth_boundary": {
            "previous_output_recompiled_before_resume": base["parent_lineage_sha256"] is not None,
            "hash_linked_append_only_steps": True,
            "source_frame_reused_without_relaxing_box_recognition": True,
            "multiple_nonoverlapping_notches_same_fabrication_axis": True,
            "round_hole_chaining": "NOT_SUPPORTED",
            "cross_axis_chain": "NOT_SUPPORTED",
            "full_arbitrary_mesh_csg": False,
            "cryptographic_authorship_signature": "NOT_PROVIDED",
            "coordinated_receipt_and_artifact_tamper_without_external_anchor": "NOT_AUTHENTICATED",
            "self_intersection": "NOT_PROVEN",
            "visual_quality": "NOT_TESTED",
            "structural_strength": "NOT_TESTED",
            "host_import_compatibility": "NOT_TESTED",
        },
    }
    lineage["lineage_sha256"] = _lineage_digest(lineage)
    return lineage


def build_fabrication_chain(
    source_path: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    spec = prepare_fabrication_chain(specification)
    if lineage_path is None:
        base = _root_from_source(source_path, spec, expected_source_sha256)
    else:
        if expected_source_sha256 is not None:
            if not source_path.is_file() or source_path.is_symlink():
                raise MeshPrecisionCutterError(
                    "source_path must be an existing ordinary GLB file"
                )
            observed = hashlib.sha256(source_path.read_bytes()).hexdigest()
            expected = _normalize_digest(
                expected_source_sha256, "expected_source_sha256"
            )
            if expected != observed:
                raise MeshPrecisionCutterError(
                    "resume source GLB digest does not match expected_source_sha256",
                    {"expected": expected, "observed": observed},
                )
        base = _load_parent_lineage(
            source_path,
            Path(lineage_path).resolve(),
            spec,
            expected_lineage_sha256,
        )
    resolved_new = _resolve_new_cuts(
        spec,
        frame=base["frame"],
        order=base["order"],
        existing=base["resolved_cuts"],
    )
    cumulative = base["resolved_cuts"] + resolved_new
    steps = _steps_for_append(
        root_sha256=base["root"]["root_sha256"],
        previous_steps=base["steps"],
        new_cuts=resolved_new,
    )
    compiled = _compile_state(
        name=spec["name"],
        frame=base["frame"],
        order=base["order"],
        material=base["root"]["material"],
        cuts=cumulative,
    )
    lineage = _build_lineage(
        specification=spec,
        base=base,
        cumulative_cuts=cumulative,
        steps=steps,
        compiled=compiled,
    )
    return {
        "schema": FABRICATION_CHAIN_SCHEMA,
        "specification": spec,
        "request_sha256": _digest(
            {
                "schema": FABRICATION_CHAIN_SCHEMA,
                "parent_lineage_sha256": base["parent_lineage_sha256"],
                "root_sha256": base["root"]["root_sha256"],
                "new_cuts": resolved_new,
            }
        ),
        "parent_lineage_sha256": base["parent_lineage_sha256"],
        "resolved_new_cuts": resolved_new,
        "cumulative_cut_count": len(cumulative),
        "surface_specification": compiled["surface_specification"],
        "predicted_glb_sha256": compiled["glb_sha256"],
        "output_topology": compiled["topology"],
        "geometry": compiled["geometry"],
        "metrics": compiled["metrics"],
        "lineage": lineage,
        "truth_boundary": lineage["truth_boundary"],
    }


def _restore_bytes(path: Path, previous: bytes | None) -> None:
    try:
        if previous is None:
            path.unlink(missing_ok=True)
            return
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, temporary = tempfile.mkstemp(
            prefix=f".{path.name}.restore-", dir=str(path.parent)
        )
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(previous)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, path)
        finally:
            if os.path.exists(temporary):
                os.unlink(temporary)
    except OSError:
        pass


def _publish_receipt(path: Path, lineage: dict[str, Any], *, replace: bool) -> int:
    if path.exists() and not replace:
        raise MeshPrecisionCutterError(
            "fabrication receipt already exists; set replace=true to replace it"
        )
    path.parent.mkdir(parents=True, exist_ok=True)
    encoded = (
        json.dumps(lineage, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
        + "\n"
    ).encode("utf-8")
    fd, temporary = tempfile.mkstemp(
        prefix=f".{path.name}.tmp-", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(encoded)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    except OSError as exc:
        raise MeshPrecisionCutterError("failed to publish fabrication lineage receipt") from exc
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    return len(encoded)


def publish_fabrication_chain(
    source_path: Path,
    target: Path,
    specification: Any,
    *,
    lineage_path: Path | None = None,
    receipt_path: Path | None = None,
    expected_source_sha256: str | None = None,
    expected_lineage_sha256: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    source_path = Path(source_path).resolve()
    target = Path(target).resolve()
    if source_path == target:
        raise MeshPrecisionCutterError(
            "fabrication chain requires distinct source_path and output path"
        )
    parent_lineage = Path(lineage_path).resolve() if lineage_path is not None else None
    receipt = (
        Path(receipt_path).resolve()
        if receipt_path is not None
        else target.with_suffix(target.suffix + ".fabrication.json")
    )
    if receipt in {source_path, target}:
        raise MeshPrecisionCutterError(
            "fabrication receipt path must be distinct from source and output paths"
        )
    if parent_lineage is not None and receipt == parent_lineage:
        raise MeshPrecisionCutterError(
            "resume must publish a new lineage receipt instead of overwriting its parent"
        )
    if receipt.exists() and not replace:
        raise MeshPrecisionCutterError(
            "fabrication receipt already exists; set replace=true to replace it"
        )

    built = build_fabrication_chain(
        source_path,
        specification,
        lineage_path=parent_lineage,
        expected_source_sha256=expected_source_sha256,
        expected_lineage_sha256=expected_lineage_sha256,
    )
    source_before = hashlib.sha256(source_path.read_bytes()).hexdigest()
    previous_target = target.read_bytes() if target.exists() else None
    previous_receipt = receipt.read_bytes() if receipt.exists() else None
    try:
        publication = publish_glb(
            target, built["surface_specification"], replace=replace
        )
        if publication["sha256"] != built["predicted_glb_sha256"]:
            raise MeshPrecisionCutterError(
                "published GLB digest differs from the deterministically precompiled chain output"
            )
        receipt_bytes = _publish_receipt(
            receipt, built["lineage"], replace=replace
        )
    except (Procedural3DError, MeshPrecisionCutterError) as exc:
        _restore_bytes(target, previous_target)
        _restore_bytes(receipt, previous_receipt)
        if isinstance(exc, MeshPrecisionCutterError):
            raise
        raise MeshPrecisionCutterError(
            str(exc), getattr(exc, "details", {})
        ) from exc

    source_after = hashlib.sha256(source_path.read_bytes()).hexdigest()
    source_unchanged = source_before == source_after
    truth_status = (
        "VALIDATED_HASH_LINKED_FABRICATION_CHAIN"
        if source_unchanged
        else "HOLD_SOURCE_CHANGED_DURING_CHAIN_PUBLICATION"
    )
    return {
        "truth_status": truth_status,
        "path": publication["path"],
        "bytes": publication["bytes"],
        "sha256": publication["sha256"],
        "receipt_path": str(receipt),
        "receipt_bytes": receipt_bytes,
        "lineage_sha256": built["lineage"]["lineage_sha256"],
        "parent_lineage_sha256": built["parent_lineage_sha256"],
        "request_sha256": built["request_sha256"],
        "specification": built["specification"],
        "resolved_new_cuts": built["resolved_new_cuts"],
        "cumulative_cut_count": built["cumulative_cut_count"],
        "geometry": built["geometry"],
        "metrics": built["metrics"],
        "output_topology": built["output_topology"],
        "glb_validation": publication["post_publish_validation"],
        "source_unchanged_after_publication": source_unchanged,
        "observed_source_sha256_after_publication": source_after,
        "truth_boundary": built["truth_boundary"],
        "rendered_appearance_observed": False,
        "host_import_compatibility_observed": False,
    }

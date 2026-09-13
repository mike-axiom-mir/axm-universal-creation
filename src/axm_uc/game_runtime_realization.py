"""Deterministic game-view LOD selection with anchor and readability gates.

The planner consumes measured, caller-owned LOD evidence.  It never invents
geometry quality: a representation is eligible only when its contact/socket
frames remain within tolerance, its projected deviation fits the requested
pixel budget, and every story feature large enough to read is present.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json


SOURCE_SCHEMA = "axm.game-runtime-realization-source/v0.1"
PLAN_SCHEMA = "axm.game-runtime-realization/v0.1"
ANCHOR_KINDS = ("contact", "socket")
HIERARCHY = ("primary", "secondary", "detail")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low=None, high=None):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if low is not None and value < low or high is not None and value > high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def _name(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{label} must contain 1..128 visible characters")
    return value


def _vec3(value, label, *, unit=False):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three numbers")
    result = tuple(_number(item, f"{label}[{index}]", -100000, 100000)
                   for index, item in enumerate(value))
    if unit:
        length = math.sqrt(sum(item * item for item in result))
        if abs(length - 1) > 1e-5:
            raise ValueError(f"{label} must be normalized")
        result = tuple(item / length for item in result)
    return result


def game_runtime_realization_catalog():
    return {
        "schema": "axm.game-runtime-realization-catalog/v0.1",
        "anchor_kinds": list(ANCHOR_KINDS),
        "feature_hierarchy": list(HIERARCHY),
        "selection": "cheapest measured LOD satisfying anchors, projected deviation, visible features and exact-view render limits",
        "canonical_source_preserved": True,
        "truth": (
            "Plans from explicit measured LOD evidence. It does not measure meshes, judge art, "
            "run an engine, prove collision patches or infer camera/player policy."
        ),
    }


def _anchor(raw, label):
    required = {"name", "kind", "position", "forward", "up"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"{label} must contain exactly {sorted(required)}")
    name = _name(raw["name"], f"{label}.name")
    kind = raw["kind"]
    if kind not in ANCHOR_KINDS:
        raise ValueError(f"{label}.kind must be contact or socket")
    forward = _vec3(raw["forward"], f"{label}.forward", unit=True)
    up = _vec3(raw["up"], f"{label}.up", unit=True)
    if abs(sum(a * b for a, b in zip(forward, up))) > 1e-4:
        raise ValueError(f"{label} forward and up must be perpendicular")
    return {"name": name, "kind": kind, "position": list(_vec3(raw["position"], f"{label}.position")),
            "forward": list(forward), "up": list(up)}


def _features(raw):
    if not isinstance(raw, list) or not 1 <= len(raw) <= 128:
        raise ValueError("features must contain 1..128 entries")
    result, names = [], set()
    for index, row in enumerate(raw):
        label = f"features[{index}]"
        required = {"name", "hierarchy", "world_size_m", "min_pixels"}
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError(f"{label} must contain exactly {sorted(required)}")
        name = _name(row["name"], f"{label}.name")
        if name in names:
            raise ValueError(f"duplicate feature: {name}")
        names.add(name)
        hierarchy = row["hierarchy"]
        if hierarchy not in HIERARCHY:
            raise ValueError(f"{label}.hierarchy is unsupported")
        result.append({"name": name, "hierarchy": hierarchy,
                       "world_size_m": _number(row["world_size_m"], f"{label}.world_size_m", .0001, 1000),
                       "min_pixels": _number(row["min_pixels"], f"{label}.min_pixels", .25, 1024)})
    return result, names


def _source(raw):
    required = {"schema", "asset_id", "canonical_lod", "features", "lods", "source_sha256"}
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"source must use {SOURCE_SCHEMA} and contain exactly {sorted(required)}")
    asset_id = _name(raw["asset_id"], "asset_id")
    source_sha = raw["source_sha256"]
    if not isinstance(source_sha, str) or len(source_sha) != 64 or any(c not in "0123456789abcdef" for c in source_sha):
        raise ValueError("source_sha256 must be a lowercase SHA-256")
    features, feature_names = _features(raw["features"])
    lods = raw["lods"]
    if not isinstance(lods, list) or not 1 <= len(lods) <= 16:
        raise ValueError("lods must contain 1..16 entries")
    checked, lod_names, prior_triangles, prior_error = [], set(), None, None
    canonical_anchors = None
    for index, row in enumerate(lods):
        label = f"lods[{index}]"
        required_lod = {"name", "triangles", "max_deviation_m", "features", "anchors", "render_observations"}
        if not isinstance(row, dict) or set(row) != required_lod:
            raise ValueError(f"{label} must contain exactly {sorted(required_lod)}")
        name = _name(row["name"], f"{label}.name")
        if name in lod_names:
            raise ValueError(f"duplicate LOD: {name}")
        lod_names.add(name)
        triangles = _integer(row["triangles"], f"{label}.triangles", 1, 100_000_000)
        deviation = _number(row["max_deviation_m"], f"{label}.max_deviation_m", 0, 1000)
        if prior_triangles is not None and triangles >= prior_triangles:
            raise ValueError("LOD triangle counts must strictly descend")
        if prior_error is not None and deviation < prior_error:
            raise ValueError("LOD maximum deviation must not decrease")
        prior_triangles, prior_error = triangles, deviation
        present = row["features"]
        if not isinstance(present, list) or len(present) > len(feature_names):
            raise ValueError(f"{label}.features must be a bounded list")
        present = [_name(item, f"{label}.features") for item in present]
        if len(set(present)) != len(present) or set(present) - feature_names:
            raise ValueError(f"{label}.features contains duplicates or unknown names")
        anchors = [_anchor(item, f"{label}.anchors[{i}]") for i, item in enumerate(row["anchors"])]
        amap = {(item["name"], item["kind"]): item for item in anchors}
        if len(amap) != len(anchors) or not anchors:
            raise ValueError(f"{label}.anchors must be non-empty and unique by name/kind")
        if canonical_anchors is None:
            canonical_anchors = set(amap)
        elif set(amap) != canonical_anchors:
            raise ValueError("every LOD must report the same anchor identities")
        observations = row["render_observations"]
        if not isinstance(observations, list) or not observations or len(observations) > 64:
            raise ValueError(f"{label}.render_observations must contain 1..64 entries")
        checked_observations, observation_names = [], set()
        for observation_index, observation in enumerate(observations):
            observation_label = f"{label}.render_observations[{observation_index}]"
            fields = {"view", "rgba_rmse", "silhouette_iou"}
            if not isinstance(observation, dict) or set(observation) != fields:
                raise ValueError(f"{observation_label} must contain exactly {sorted(fields)}")
            view = _name(observation["view"], f"{observation_label}.view")
            if view in observation_names:
                raise ValueError(f"duplicate render observation: {name}/{view}")
            observation_names.add(view)
            checked_observations.append({
                "view": view,
                "rgba_rmse": _number(observation["rgba_rmse"], f"{observation_label}.rgba_rmse", 0, 1),
                "silhouette_iou": _number(observation["silhouette_iou"], f"{observation_label}.silhouette_iou", 0, 1),
            })
        checked.append({"name": name, "triangles": triangles, "max_deviation_m": deviation,
                        "features": present, "anchors": anchors,
                        "render_observations": checked_observations})
    canonical_lod = _name(raw["canonical_lod"], "canonical_lod")
    if canonical_lod != checked[0]["name"]:
        raise ValueError("canonical_lod must be the first and richest representation")
    if checked[0]["max_deviation_m"] != 0 or set(checked[0]["features"]) != feature_names:
        raise ValueError("canonical LOD needs zero deviation and every feature")
    return {"schema": SOURCE_SCHEMA, "asset_id": asset_id, "canonical_lod": canonical_lod,
            "features": features, "lods": checked, "source_sha256": source_sha}


def _request(raw):
    required = {"views", "anchor_position_tolerance_m", "anchor_angle_tolerance_deg"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"request must contain exactly {sorted(required)}")
    views = raw["views"]
    if not isinstance(views, list) or not 1 <= len(views) <= 64:
        raise ValueError("views must contain 1..64 entries")
    checked, names = [], set()
    for index, row in enumerate(views):
        label = f"views[{index}]"
        fields = {"name", "distance_m", "vertical_fov_deg", "viewport_height_px", "error_budget_px",
                  "max_rgba_rmse", "min_silhouette_iou"}
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError(f"{label} must contain exactly {sorted(fields)}")
        name = _name(row["name"], f"{label}.name")
        if name in names:
            raise ValueError(f"duplicate view: {name}")
        names.add(name)
        checked.append({"name": name,
                        "distance_m": _number(row["distance_m"], f"{label}.distance_m", .05, 100000),
                        "vertical_fov_deg": _number(row["vertical_fov_deg"], f"{label}.vertical_fov_deg", 5, 175),
                        "viewport_height_px": _integer(row["viewport_height_px"], f"{label}.viewport_height_px", 16, 32768),
                        "error_budget_px": _number(row["error_budget_px"], f"{label}.error_budget_px", .01, 1000),
                        "max_rgba_rmse": _number(row["max_rgba_rmse"], f"{label}.max_rgba_rmse", 0, 1),
                        "min_silhouette_iou": _number(row["min_silhouette_iou"], f"{label}.min_silhouette_iou", 0, 1)})
    return {"views": checked,
            "anchor_position_tolerance_m": _number(raw["anchor_position_tolerance_m"], "anchor_position_tolerance_m", 0, 10),
            "anchor_angle_tolerance_deg": _number(raw["anchor_angle_tolerance_deg"], "anchor_angle_tolerance_deg", 0, 180)}


def _angle(a, b):
    dot = max(-1., min(1., sum(x * y for x, y in zip(a, b))))
    return math.degrees(math.acos(dot))


def _anchor_receipts(source, request):
    canonical = {(a["name"], a["kind"]): a for a in source["lods"][0]["anchors"]}
    result = {}
    for lod in source["lods"]:
        rows = []
        for anchor in lod["anchors"]:
            base = canonical[(anchor["name"], anchor["kind"])]
            position = math.dist(base["position"], anchor["position"])
            angular = max(_angle(base["forward"], anchor["forward"]), _angle(base["up"], anchor["up"]))
            rows.append({"name": anchor["name"], "kind": anchor["kind"],
                         "position_drift_m": position, "angle_drift_deg": angular,
                         "passed": position <= request["anchor_position_tolerance_m"] and
                                   angular <= request["anchor_angle_tolerance_deg"]})
        result[lod["name"]] = rows
    return result


def compose_game_runtime_realization(raw_source, raw_request):
    source, request = _source(raw_source), _request(raw_request)
    anchors = _anchor_receipts(source, request)
    decisions = []
    for view in request["views"]:
        pixels_per_m = view["viewport_height_px"] / (
            2 * view["distance_m"] * math.tan(math.radians(view["vertical_fov_deg"]) / 2))
        feature_pixels = {row["name"]: row["world_size_m"] * pixels_per_m for row in source["features"]}
        required = sorted(row["name"] for row in source["features"]
                          if feature_pixels[row["name"]] >= row["min_pixels"])
        candidates = []
        for lod in source["lods"]:
            anchor_pass = all(row["passed"] for row in anchors[lod["name"]])
            missing = sorted(set(required) - set(lod["features"]))
            error = lod["max_deviation_m"] * pixels_per_m
            observations = {row["view"]: row for row in lod["render_observations"]}
            observed = observations.get(view["name"])
            render_pass = (observed is not None and
                           observed["rgba_rmse"] <= view["max_rgba_rmse"] and
                           observed["silhouette_iou"] >= view["min_silhouette_iou"])
            eligible = anchor_pass and not missing and error <= view["error_budget_px"] and render_pass
            candidates.append({"lod": lod["name"], "triangles": lod["triangles"],
                               "projected_error_px": error, "missing_required_features": missing,
                               "anchors_pass": anchor_pass, "render_observation": copy.deepcopy(observed),
                               "render_pass": render_pass, "eligible": eligible})
        eligible = [row for row in candidates if row["eligible"]]
        decisions.append({"view": view["name"], "pixels_per_m": pixels_per_m,
                          "feature_pixels": feature_pixels, "required_features": required,
                          "selected_lod": min(eligible, key=lambda row: row["triangles"])["lod"] if eligible else None,
                          "status": "PASS" if eligible else "HOLD", "candidates": candidates})
    return {"schema": PLAN_SCHEMA, "status": "PASS" if all(row["status"] == "PASS" for row in decisions) else "HOLD",
            "source_sha256": _digest(raw_source), "request_sha256": _digest(raw_request),
            "source": copy.deepcopy(raw_source), "request": copy.deepcopy(raw_request),
            "anchor_receipts": anchors, "decisions": decisions,
            "truth": "Selection is justified by supplied measurements; mesh measurement and engine playback remain external."}


def publish_game_runtime_realization(path, source, request):
    destination = Path(path)
    if destination.exists():
        raise FileExistsError(f"refusing to overwrite {destination}")
    plan = compose_game_runtime_realization(source, request)
    destination.mkdir(parents=True)
    try:
        atomic_write_json(destination / "source.json", source)
        atomic_write_json(destination / "request.json", request)
        atomic_write_json(destination / "realization-plan.json", plan)
    except Exception:
        for child in destination.iterdir():
            child.unlink()
        destination.rmdir()
        raise
    return plan

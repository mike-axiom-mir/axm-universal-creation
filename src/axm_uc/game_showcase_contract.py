"""Fail-closed acceptance contract for a combined animated game-asset proof.

This module does not create or judge art.  It binds caller-measured geometry,
material, animation, anchor, LOD and visual evidence into one deterministic
receipt so a showcase cannot pass by demonstrating only one layer.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json


SOURCE_SCHEMA = "axm.game-showcase-source/v0.1"
RECEIPT_SCHEMA = "axm.game-showcase/v0.1"
MOTION_CLASSES = ("coil-spring", "antenna", "cloth-tail", "carried-prop")


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _name(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{label} must contain 1..128 visible characters")
    return value


def _number(value, label, low=0, high=1_000_000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _integer(value, label, low=0, high=100_000_000):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def _sha(value, label):
    if not isinstance(value, str) or len(value) != 64 or any(c not in "0123456789abcdef" for c in value):
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def game_showcase_catalog():
    return {
        "schema": "axm.game-showcase-catalog/v0.1",
        "required_layers": ["canonical identity", "selectable styles", "material families", "named animation",
                            "secondary motion", "contact/socket anchors", "LOD ladder", "render comparisons"],
        "canonical_source_preserved": True,
        "truth": (
            "Verifies explicit caller-measured evidence and file digests. It does not judge art, inspect pixels, "
            "run a target engine, measure runtime performance, or make an asset fun."
        ),
    }


def _validate(raw):
    fields = {"schema", "asset_id", "canonical_source_sha256", "styles", "materials", "rig",
              "secondary_motion", "anchors", "lods", "views", "files", "thresholds", "limits"}
    if not isinstance(raw, dict) or set(raw) != fields or raw.get("schema") != SOURCE_SCHEMA:
        raise ValueError(f"source must use {SOURCE_SCHEMA} and contain exactly {sorted(fields)}")
    source = {"schema": SOURCE_SCHEMA, "asset_id": _name(raw["asset_id"], "asset_id"),
              "canonical_source_sha256": _sha(raw["canonical_source_sha256"], "canonical_source_sha256")}

    styles, style_names = [], set()
    if not isinstance(raw["styles"], list) or not 2 <= len(raw["styles"]) <= 16:
        raise ValueError("styles must contain 2..16 entries")
    for index, row in enumerate(raw["styles"]):
        if not isinstance(row, dict) or set(row) != {"name", "role"}:
            raise ValueError(f"styles[{index}] must contain exactly name and role")
        name, role = _name(row["name"], f"styles[{index}].name"), row["role"]
        if name in style_names or role not in ("canonical-realistic", "selected-game"):
            raise ValueError("styles must be unique and use supported roles")
        style_names.add(name); styles.append({"name": name, "role": role})
    if sum(row["role"] == "canonical-realistic" for row in styles) != 1 or not any(row["role"] == "selected-game" for row in styles):
        raise ValueError("styles require exactly one realistic canonical option and a selected game option")
    source["styles"] = styles

    materials, material_names, families = [], set(), set()
    if not isinstance(raw["materials"], list) or not 3 <= len(raw["materials"]) <= 64:
        raise ValueError("materials must contain 3..64 entries")
    for index, row in enumerate(raw["materials"]):
        if not isinstance(row, dict) or set(row) != {"name", "family", "finish", "realized"}:
            raise ValueError(f"materials[{index}] has unsupported fields")
        name = _name(row["name"], f"materials[{index}].name")
        if name in material_names or type(row["realized"]) is not bool:
            raise ValueError("material names must be unique and realized must be boolean")
        material_names.add(name); families.add(_name(row["family"], f"materials[{index}].family"))
        materials.append({"name": name, "family": row["family"], "finish": _name(row["finish"], f"materials[{index}].finish"), "realized": row["realized"]})
    source["materials"] = materials

    rig = raw["rig"]
    if not isinstance(rig, dict) or set(rig) != {"bones", "clips"}:
        raise ValueError("rig must contain exactly bones and clips")
    bones = [_name(item, "rig.bones") for item in rig["bones"]] if isinstance(rig["bones"], list) else []
    if not 4 <= len(bones) <= 512 or len(bones) != len(set(bones)):
        raise ValueError("rig.bones must contain 4..512 unique names")
    clips, clip_names = [], set()
    if not isinstance(rig["clips"], list) or not 2 <= len(rig["clips"]) <= 64:
        raise ValueError("rig.clips must contain 2..64 entries")
    for index, row in enumerate(rig["clips"]):
        required = {"name", "frames", "fps", "loop", "loop_seam_m"}
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError(f"rig.clips[{index}] has unsupported fields")
        name = _name(row["name"], f"rig.clips[{index}].name")
        if name in clip_names or type(row["loop"]) is not bool:
            raise ValueError("clip names must be unique and loop must be boolean")
        clip_names.add(name)
        clips.append({"name": name, "frames": _integer(row["frames"], "clip.frames", 2, 100_000),
                      "fps": _number(row["fps"], "clip.fps", 1, 1000), "loop": row["loop"],
                      "loop_seam_m": _number(row["loop_seam_m"], "clip.loop_seam_m")})
    source["rig"] = {"bones": bones, "clips": clips}

    secondary, secondary_targets = [], set()
    if not isinstance(raw["secondary_motion"], list) or not 2 <= len(raw["secondary_motion"]) <= 64:
        raise ValueError("secondary_motion must contain 2..64 entries")
    for index, row in enumerate(raw["secondary_motion"]):
        if not isinstance(row, dict) or set(row) != {"target", "motion_class", "max_track_error", "loop_seam_m"}:
            raise ValueError(f"secondary_motion[{index}] has unsupported fields")
        target, motion_class = _name(row["target"], "secondary target"), row["motion_class"]
        if target in secondary_targets or motion_class not in MOTION_CLASSES or target not in bones:
            raise ValueError("secondary targets must be unique rig bones with supported classes")
        secondary_targets.add(target)
        secondary.append({"target": target, "motion_class": motion_class,
                          "max_track_error": _number(row["max_track_error"], "secondary.max_track_error"),
                          "loop_seam_m": _number(row["loop_seam_m"], "secondary.loop_seam_m")})
    source["secondary_motion"] = secondary

    anchors, anchor_names, anchor_kinds = [], set(), set()
    if not isinstance(raw["anchors"], list) or not 2 <= len(raw["anchors"]) <= 128:
        raise ValueError("anchors must contain 2..128 entries")
    for index, row in enumerate(raw["anchors"]):
        if not isinstance(row, dict) or set(row) != {"name", "kind", "position_drift_m", "angle_drift_deg", "surface_distance_m"}:
            raise ValueError(f"anchors[{index}] has unsupported fields")
        name, kind = _name(row["name"], "anchor.name"), row["kind"]
        if name in anchor_names or kind not in ("contact", "socket") or name not in bones:
            raise ValueError("anchors must be unique rig bones of contact/socket kind")
        anchor_names.add(name); anchor_kinds.add(kind)
        anchors.append({"name": name, "kind": kind,
                        "position_drift_m": _number(row["position_drift_m"], "anchor.position_drift_m"),
                        "angle_drift_deg": _number(row["angle_drift_deg"], "anchor.angle_drift_deg", 0, 360),
                        "surface_distance_m": _number(row["surface_distance_m"], "anchor.surface_distance_m")})
    if anchor_kinds != {"contact", "socket"}:
        raise ValueError("anchors require both contact and socket evidence")
    source["anchors"] = anchors

    lods, lod_names, prior_triangles = [], set(), None
    if not isinstance(raw["lods"], list) or not 2 <= len(raw["lods"]) <= 16:
        raise ValueError("lods must contain 2..16 entries")
    for index, row in enumerate(raw["lods"]):
        if not isinstance(row, dict) or set(row) != {"name", "triangles", "max_deviation_m", "identity_features"}:
            raise ValueError(f"lods[{index}] has unsupported fields")
        name, triangles = _name(row["name"], "lod.name"), _integer(row["triangles"], "lod.triangles", 1)
        features = [_name(item, "lod.identity_features") for item in row["identity_features"]] if isinstance(row["identity_features"], list) else []
        if name in lod_names or (prior_triangles is not None and triangles >= prior_triangles) or not features or len(features) != len(set(features)):
            raise ValueError("LOD names/features must be unique and triangle counts must strictly descend")
        lod_names.add(name); prior_triangles = triangles
        lods.append({"name": name, "triangles": triangles,
                     "max_deviation_m": _number(row["max_deviation_m"], "lod.max_deviation_m"),
                     "identity_features": features})
    if lods[0]["max_deviation_m"] != 0:
        raise ValueError("first LOD must be canonical with zero deviation")
    source["lods"] = lods

    views, view_names = [], set()
    if not isinstance(raw["views"], list) or not 2 <= len(raw["views"]) <= 64:
        raise ValueError("views must contain 2..64 entries")
    for index, row in enumerate(raw["views"]):
        if not isinstance(row, dict) or set(row) != {"name", "selected_lod", "rgba_rmse", "silhouette_iou", "max_rgba_rmse", "min_silhouette_iou"}:
            raise ValueError(f"views[{index}] has unsupported fields")
        name, lod = _name(row["name"], "view.name"), row["selected_lod"]
        if name in view_names or lod not in lod_names:
            raise ValueError("views must be unique and select a known LOD")
        view_names.add(name)
        views.append({"name": name, "selected_lod": lod,
                      "rgba_rmse": _number(row["rgba_rmse"], "view.rgba_rmse", 0, 1),
                      "silhouette_iou": _number(row["silhouette_iou"], "view.silhouette_iou", 0, 1),
                      "max_rgba_rmse": _number(row["max_rgba_rmse"], "view.max_rgba_rmse", 0, 1),
                      "min_silhouette_iou": _number(row["min_silhouette_iou"], "view.min_silhouette_iou", 0, 1)})
    source["views"] = views

    files, filenames = [], set()
    if not isinstance(raw["files"], list) or not 2 <= len(raw["files"]) <= 128:
        raise ValueError("files must contain 2..128 entries")
    for index, row in enumerate(raw["files"]):
        if not isinstance(row, dict) or set(row) != {"name", "sha256", "bytes"}:
            raise ValueError(f"files[{index}] has unsupported fields")
        name = _name(row["name"], "file.name")
        if name in filenames or name.startswith(("/", "\\")) or ".." in Path(name).parts:
            raise ValueError("file names must be unique safe relative paths")
        filenames.add(name)
        files.append({"name": name, "sha256": _sha(row["sha256"], "file.sha256"),
                      "bytes": _integer(row["bytes"], "file.bytes", 1)})
    source["files"] = files

    threshold_fields = {"loop_seam_m", "secondary_track_error", "anchor_position_m", "anchor_angle_deg", "contact_surface_m"}
    if not isinstance(raw["thresholds"], dict) or set(raw["thresholds"]) != threshold_fields:
        raise ValueError(f"thresholds must contain exactly {sorted(threshold_fields)}")
    source["thresholds"] = {key: _number(value, f"thresholds.{key}") for key, value in raw["thresholds"].items()}
    if not isinstance(raw["limits"], list) or not raw["limits"] or not all(isinstance(x, str) and x.strip() for x in raw["limits"]):
        raise ValueError("limits must contain explicit non-empty truth boundaries")
    source["limits"] = list(raw["limits"])
    return source, families


def compose_game_showcase(raw):
    before = copy.deepcopy(raw)
    source, families = _validate(raw)
    t = source["thresholds"]
    gates = {
        "style_choice": any(row["role"] == "canonical-realistic" for row in source["styles"]) and any(row["role"] == "selected-game" for row in source["styles"]),
        "material_realization": len(families) >= 3 and all(row["realized"] for row in source["materials"]),
        "named_motion": len(source["rig"]["clips"]) >= 2 and all((not row["loop"]) or row["loop_seam_m"] <= t["loop_seam_m"] for row in source["rig"]["clips"]),
        "secondary_motion": len({row["motion_class"] for row in source["secondary_motion"]}) >= 2 and all(row["max_track_error"] <= t["secondary_track_error"] and row["loop_seam_m"] <= t["loop_seam_m"] for row in source["secondary_motion"]),
        "anchors": all(row["position_drift_m"] <= t["anchor_position_m"] and row["angle_drift_deg"] <= t["anchor_angle_deg"] and (row["kind"] != "contact" or row["surface_distance_m"] <= t["contact_surface_m"]) for row in source["anchors"]),
        "lod_ladder": len(source["lods"]) >= 2 and all(set(row["identity_features"]) >= set(source["lods"][-1]["identity_features"]) for row in source["lods"]),
        "render_evidence": all(row["rgba_rmse"] <= row["max_rgba_rmse"] and row["silhouette_iou"] >= row["min_silhouette_iou"] for row in source["views"]),
        "artifact_manifest": any(row["name"].endswith(".glb") for row in source["files"]) and any(row["name"].endswith(".blend") for row in source["files"]),
    }
    if raw != before:
        raise AssertionError("showcase validation mutated caller source")
    return {"schema": RECEIPT_SCHEMA, "status": "PASS" if all(gates.values()) else "HOLD",
            "asset_id": source["asset_id"], "gates": gates, "source_sha256": _digest(source),
            "source": source,
            "truth": "Evidence-completeness receipt only; see source.limits for unverified claims."}


def publish_game_showcase(path, source):
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    receipt = compose_game_showcase(source)
    target.mkdir(parents=True)
    atomic_write_json(target / "showcase-source.json", receipt["source"])
    atomic_write_json(target / "showcase-receipt.json", receipt)
    return receipt

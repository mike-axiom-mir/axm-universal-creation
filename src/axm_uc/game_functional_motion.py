"""Deterministic portable wheel-roll and released-prop motion tracks.

The compositor samples ordinary local transform tracks.  Locomotion derives
wheel angle from travelled distance and declared radius.  A projectile derives
its launch velocity from endpoints, constant gravity and explicit release /
impact frames.  It does not solve terrain, suspension or collisions.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json


FUNCTIONAL_MOTION_SCHEMA = "axm.game-functional-motion/v0.1"


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _name(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{label} must contain 1..128 visible characters")
    return value


def _number(value, label, low=-100_000, high=100_000):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _integer(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def _vec3(value, label):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f"{label} must contain three finite numbers")
    return tuple(_number(item, f"{label}[{index}]") for index, item in enumerate(value))


def _unit(value, label):
    result = _vec3(value, label)
    length = math.sqrt(sum(item * item for item in result))
    if abs(length - 1) > 1e-5:
        raise ValueError(f"{label} must be normalized")
    return tuple(item / length for item in result)


def game_functional_motion_catalog():
    return {
        "schema": "axm.game-functional-motion-catalog/v0.1",
        "capabilities": ["distance-derived wheel roll", "constant-gravity released-prop trajectory"],
        "portable_tracks": ["translation", "normalized quaternion rotation"],
        "canonical_source_preserved": True,
        "truth": (
            "Authors sampled local transform tracks from explicit dimensions and endpoints. "
            "It does not infer wheels, solve suspension or steering, detach scene graphs, "
            "detect collision, or prove target-engine gameplay."
        ),
    }


def _locomotion(raw, frame_count):
    if raw is None:
        return None
    required = {"root_target", "start", "end", "start_frame", "end_frame", "easing"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"locomotion must contain exactly {sorted(required)}")
    start_frame = _integer(raw["start_frame"], "locomotion.start_frame", 0, frame_count - 2)
    end_frame = _integer(raw["end_frame"], "locomotion.end_frame", start_frame + 1, frame_count - 1)
    if raw["easing"] not in ("linear", "smoothstep"):
        raise ValueError("locomotion.easing must be linear or smoothstep")
    start, end = _vec3(raw["start"], "locomotion.start"), _vec3(raw["end"], "locomotion.end")
    if math.dist(start, end) <= 1e-6:
        raise ValueError("locomotion must travel a measurable distance")
    return {"root_target": _name(raw["root_target"], "locomotion.root_target"),
            "start": list(start), "end": list(end), "start_frame": start_frame,
            "end_frame": end_frame, "easing": raw["easing"]}


def _wheels(raw, locomotion):
    if not isinstance(raw, list) or len(raw) > 16:
        raise ValueError("wheels must contain 0..16 entries")
    if (locomotion is None) != (len(raw) == 0):
        raise ValueError("locomotion and at least one wheel must be supplied together")
    rows, names = [], set()
    for index, row in enumerate(raw):
        required = {"target", "radius_m", "axis", "direction"}
        if not isinstance(row, dict) or set(row) != required:
            raise ValueError(f"wheels[{index}] must contain exactly {sorted(required)}")
        target = _name(row["target"], f"wheels[{index}].target")
        if target in names or row["direction"] not in (-1, 1):
            raise ValueError("wheel targets must be unique and direction must be -1 or 1")
        names.add(target)
        rows.append({"target": target, "radius_m": _number(row["radius_m"], "wheel.radius_m", .001, 1000),
                     "axis": list(_unit(row["axis"], "wheel.axis")), "direction": row["direction"]})
    return rows


def _projectile(raw, frame_count):
    if raw is None:
        return None
    required = {"target", "start", "landing", "gravity", "release_frame", "impact_frame"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"projectile must contain exactly {sorted(required)}")
    release = _integer(raw["release_frame"], "projectile.release_frame", 0, frame_count - 2)
    impact = _integer(raw["impact_frame"], "projectile.impact_frame", release + 1, frame_count - 1)
    start, landing, gravity = (_vec3(raw[key], f"projectile.{key}") for key in ("start", "landing", "gravity"))
    if math.sqrt(sum(item * item for item in gravity)) <= 1e-6:
        raise ValueError("projectile.gravity must be nonzero")
    if math.dist(start, landing) <= 1e-6:
        raise ValueError("projectile start and landing must differ")
    return {"target": _name(raw["target"], "projectile.target"), "start": list(start),
            "landing": list(landing), "gravity": list(gravity),
            "release_frame": release, "impact_frame": impact}


def _phase(frame, start, end, easing):
    if frame <= start:
        return 0.
    if frame >= end:
        return 1.
    value = (frame - start) / (end - start)
    return value * value * (3 - 2 * value) if easing == "smoothstep" else value


def _quat(axis, angle):
    half = angle / 2
    return [axis[0] * math.sin(half), axis[1] * math.sin(half),
            axis[2] * math.sin(half), math.cos(half)]


def compose_game_functional_motion(raw):
    before = copy.deepcopy(raw)
    required = {"name", "fps", "frame_count", "locomotion", "wheels", "projectile"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"request must contain exactly {sorted(required)}")
    fps = _number(raw["fps"], "fps", 1, 1000)
    frame_count = _integer(raw["frame_count"], "frame_count", 2, 3601)
    source = {"name": _name(raw["name"], "name"), "fps": fps, "frame_count": frame_count}
    source["locomotion"] = _locomotion(raw["locomotion"], frame_count)
    source["wheels"] = _wheels(raw["wheels"], source["locomotion"])
    source["projectile"] = _projectile(raw["projectile"], frame_count)
    if source["locomotion"] is None and source["projectile"] is None:
        raise ValueError("request must author locomotion, a projectile, or both")
    if raw != before:
        raise AssertionError("functional motion validation mutated caller request")
    times = [frame / fps for frame in range(frame_count)]
    tracks, receipt, events = [], {"wheels": []}, []
    if source["locomotion"]:
        move = source["locomotion"]
        fractions = [_phase(frame, move["start_frame"], move["end_frame"], move["easing"])
                     for frame in range(frame_count)]
        delta = [b - a for a, b in zip(move["start"], move["end"])]
        distance = math.sqrt(sum(item * item for item in delta))
        root_values = [[a + d * fraction for a, d in zip(move["start"], delta)] for fraction in fractions]
        tracks.append({"target": move["root_target"], "path": "translation", "times": times,
                       "values": root_values, "interpolation": "LINEAR"})
        for wheel in source["wheels"]:
            angles = [wheel["direction"] * distance * fraction / wheel["radius_m"] for fraction in fractions]
            tracks.append({"target": wheel["target"], "path": "rotation", "times": times,
                           "values": [_quat(wheel["axis"], angle) for angle in angles], "interpolation": "LINEAR"})
            receipt["wheels"].append({"target": wheel["target"], "radius_m": wheel["radius_m"],
                                      "travel_m": distance, "rotation_radians": angles[-1],
                                      "revolutions": abs(angles[-1]) / math.tau,
                                      "maximum_no_slip_residual_m": max(abs(abs(angle) * wheel["radius_m"] - distance * fraction) for angle, fraction in zip(angles, fractions))})
        receipt["root_distance_m"] = distance
        events.extend([{"name": "travel_start", "frame": move["start_frame"]},
                       {"name": "travel_end", "frame": move["end_frame"]}])
    if source["projectile"]:
        prop = source["projectile"]
        duration = (prop["impact_frame"] - prop["release_frame"]) / fps
        velocity = [(end - start - .5 * gravity * duration * duration) / duration
                    for start, end, gravity in zip(prop["start"], prop["landing"], prop["gravity"])]
        values = []
        for frame in range(frame_count):
            if frame <= prop["release_frame"]:
                values.append(list(prop["start"]))
            elif frame >= prop["impact_frame"]:
                values.append(list(prop["landing"]))
            else:
                t = (frame - prop["release_frame"]) / fps
                values.append([start + speed * t + .5 * gravity * t * t
                               for start, speed, gravity in zip(prop["start"], velocity, prop["gravity"])])
        tracks.append({"target": prop["target"], "path": "translation", "times": times,
                       "values": values, "interpolation": "LINEAR"})
        gravity_length = math.sqrt(sum(item * item for item in prop["gravity"]))
        gravity_axis = [item / gravity_length for item in prop["gravity"]]
        heights = [-sum((value[i] - prop["start"][i]) * gravity_axis[i] for i in range(3)) for value in values]
        apex = max(range(prop["release_frame"], prop["impact_frame"] + 1), key=lambda frame: heights[frame])
        residual = math.dist(values[prop["impact_frame"]], prop["landing"])
        receipt["projectile"] = {"target": prop["target"], "derived_velocity": velocity,
                                 "flight_seconds": duration, "apex_frame": apex,
                                 "apex_height_along_gravity_m": heights[apex],
                                 "impact_residual_m": residual}
        events.extend([{"name": "release", "frame": prop["release_frame"]},
                       {"name": "apex", "frame": apex},
                       {"name": "impact", "frame": prop["impact_frame"]}])
    receipt["maximum_no_slip_residual_m"] = max((row["maximum_no_slip_residual_m"] for row in receipt["wheels"]), default=0.)
    receipt["projectile_impact_residual_m"] = receipt.get("projectile", {}).get("impact_residual_m", 0.)
    return {"schema": FUNCTIONAL_MOTION_SCHEMA, "source_sha256": _digest(source), "source": source,
            "clip": {"name": source["name"], "fps": fps, "frame_count": frame_count,
                     "tracks": tracks, "events": sorted(events, key=lambda row: (row["frame"], row["name"]))},
            "receipt": receipt,
            "truth": "Sampled authored local tracks; no terrain, steering, suspension, detach graph, collision or target-engine playback claim."}


def publish_game_functional_motion(path, request):
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    result = compose_game_functional_motion(request)
    target.mkdir(parents=True)
    atomic_write_json(target / "functional-motion-source.json", result["source"])
    atomic_write_json(target / "functional-motion.json", result)
    return result

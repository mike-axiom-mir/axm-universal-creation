"""Deterministic secondary-motion composition over sampled primary clips.

The solver adds bounded inertial follow-through for explicitly declared rigid
controls.  It does not infer bones, simulate cloth, or mutate the primary clip.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
import os
from dataclasses import asdict, dataclass
from pathlib import Path
import tempfile

from .atomic import atomic_write_json
from .game_motion_timing import MOTION_TIMING_SCHEMA, PATH_WIDTHS


SECONDARY_MOTION_SCHEMA = "axm.game-secondary-motion/v0.1"


@dataclass(frozen=True)
class SecondaryMotionProfile:
    name: str
    response_hz: float
    damping: float
    lag_frames: int
    drive_gain: float
    description: str


PROFILES = (
    SecondaryMotionProfile("coil-spring", 5.4, .30, 1, 1.00,
                           "Fast mechanical compression with a readable rebound."),
    SecondaryMotionProfile("antenna", 4.0, .23, 2, 1.08,
                           "Light delayed whip for rods, ears and aerials."),
    SecondaryMotionProfile("cloth-tail", 2.7, .36, 3, 1.16,
                           "Broad, slower follow-through for short rigid cloth chains."),
    SecondaryMotionProfile("carried-prop", 3.5, .48, 1, .82,
                           "Weighty restrained lag for packs, tools and dangling props."),
)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low, high):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _vector(value, width, label, low=-100000., high=100000.):
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise ValueError(f"{label} must contain {width} values")
    return tuple(_number(item, f"{label}[{index}]", low, high)
                 for index, item in enumerate(value))


def _normalize(value, label):
    value = _vector(value, len(value), label)
    length = math.sqrt(sum(item * item for item in value))
    if length < 1e-9:
        raise ValueError(f"{label} cannot be zero")
    return tuple(item / length for item in value)


def _quaternion(value, label):
    value = _vector(value, 4, label)
    length = math.sqrt(sum(item * item for item in value))
    if abs(length - 1.) > 1e-5:
        raise ValueError(f"{label} must be normalized")
    return tuple(item / length for item in value)


def _profile(name):
    for profile in PROFILES:
        if profile.name == name:
            return profile
    raise ValueError(f"unknown secondary motion class: {name}")


def game_secondary_motion_catalog():
    return {
        "schema": "axm.game-secondary-motion-catalog/v0.1",
        "profiles": [asdict(profile) for profile in PROFILES],
        "paths": copy.deepcopy(PATH_WIDTHS),
        "canonical_primary_preserved": True,
        "portable_sampling": "Per-frame LINEAR local transform tracks.",
        "truth": (
            "Composes bounded rigid-control follow-through from a sampled primary clip. "
            "It does not infer a rig, perform soft-body or cloth simulation, solve collisions, "
            "or prove target-engine animation quality."
        ),
    }


def _validate_primary(primary):
    if not isinstance(primary, dict) or primary.get("schema") != MOTION_TIMING_SCHEMA:
        raise ValueError("primary must be an axm.game-motion-timing/v0.1 composition")
    clip = primary.get("clip")
    if not isinstance(clip, dict) or not isinstance(clip.get("tracks"), list) or not clip["tracks"]:
        raise ValueError("primary clip must contain sampled tracks")
    count = len(clip["tracks"][0].get("times", []))
    if not 13 <= count <= 1201:
        raise ValueError("primary clip must contain 13..1201 samples")
    times = clip["tracks"][0]["times"]
    if not all(isinstance(value, (int, float)) and math.isfinite(value) for value in times):
        raise ValueError("primary times must be finite")
    if not all(b > a for a, b in zip(times, times[1:])):
        raise ValueError("primary times must be strictly increasing")
    for track in clip["tracks"]:
        path = track.get("path")
        if path not in PATH_WIDTHS or track.get("interpolation") != "LINEAR":
            raise ValueError("primary tracks must use supported LINEAR paths")
        if track.get("times") != times or len(track.get("values", [])) != count:
            raise ValueError("primary tracks must share one sample clock")
        for index, value in enumerate(track["values"]):
            _vector(value, PATH_WIDTHS[path], f"primary {track.get('target')}[{index}]")
    events = {row.get("name"): row.get("frame") for row in clip.get("events", [])
              if isinstance(row, dict)}
    if set(events) != {"rest", "anticipation", "impact", "recoil", "counter", "settle", "complete"}:
        raise ValueError("primary clip must expose the complete timing event set")
    if events["complete"] != count - 1 or not 1 <= events["settle"] < events["complete"]:
        raise ValueError("primary settle/complete events are inconsistent")
    return clip, times, events


def _request(raw, primary_tracks):
    if not isinstance(raw, dict) or set(raw) != {"name", "attachments"}:
        raise ValueError("secondary request must contain exactly name and attachments")
    if not isinstance(raw["name"], str) or not raw["name"].strip() or len(raw["name"]) > 96:
        raise ValueError("secondary motion name must contain 1..96 visible characters")
    rows = raw["attachments"]
    if not isinstance(rows, list) or not 1 <= len(rows) <= 64:
        raise ValueError("attachments must contain 1..64 entries")
    known = {(track["target"], track["path"]): track for track in primary_tracks}
    normalized, outputs = [], set()
    required = {"target", "path", "rest", "axis", "amplitude", "driver_target",
                "driver_path", "driver_component", "motion_class"}
    optional = {"lag_frames", "direction"}
    for index, row in enumerate(rows):
        label = f"attachments[{index}]"
        if not isinstance(row, dict) or not required <= set(row) or set(row) - required - optional:
            raise ValueError(f"{label} has missing or unsupported fields")
        target, path = row["target"], row["path"]
        if not isinstance(target, str) or not target.strip() or len(target) > 128 or path not in PATH_WIDTHS:
            raise ValueError(f"{label} has invalid target or path")
        if (target, path) in outputs:
            raise ValueError(f"duplicate secondary target: {target} {path}")
        outputs.add((target, path))
        driver_key = (row["driver_target"], row["driver_path"])
        if driver_key not in known:
            raise ValueError(f"{label} references a missing primary driver")
        component = row["driver_component"]
        if type(component) is not int or not 0 <= component < PATH_WIDTHS[driver_key[1]]:
            raise ValueError(f"{label}.driver_component is invalid")
        profile = _profile(row["motion_class"])
        lag = row.get("lag_frames", profile.lag_frames)
        if type(lag) is not int or not 0 <= lag <= 24:
            raise ValueError(f"{label}.lag_frames must be an integer from 0 to 24")
        direction = row.get("direction", 1)
        if direction not in (-1, 1):
            raise ValueError(f"{label}.direction must be -1 or 1")
        if path == "rotation":
            rest = _quaternion(row["rest"], f"{label}.rest")
            axis = _normalize(_vector(row["axis"], 3, f"{label}.axis"), f"{label}.axis")
            amplitude = _number(row["amplitude"], f"{label}.amplitude", 0.001, math.pi)
        else:
            rest = _vector(row["rest"], 3, f"{label}.rest")
            axis = _normalize(_vector(row["axis"], 3, f"{label}.axis"), f"{label}.axis")
            upper = .8 if path == "scale" else 10.
            amplitude = _number(row["amplitude"], f"{label}.amplitude", 0.001, upper)
            if path == "scale" and min(rest) - amplitude <= 0:
                raise ValueError(f"{label} scale amplitude could invert the transform")
        normalized.append({
            "target": target, "path": path, "rest": list(rest), "axis": list(axis),
            "amplitude": amplitude, "driver_target": driver_key[0],
            "driver_path": driver_key[1], "driver_component": component,
            "motion_class": profile.name, "lag_frames": lag, "direction": direction,
        })
    return {"name": raw["name"], "attachments": normalized}


def _multiply_quaternion(a, b):
    ax, ay, az, aw = a
    bx, by, bz, bw = b
    return (aw * bx + ax * bw + ay * bz - az * by,
            aw * by - ax * bz + ay * bw + az * bx,
            aw * bz + ax * by - ay * bx + az * bw,
            aw * bw - ax * bx - ay * by - az * bz)


def _value(row, displacement):
    if row["path"] == "rotation":
        half = displacement / 2
        turn = (*[item * math.sin(half) for item in row["axis"]], math.cos(half))
        value = _multiply_quaternion(tuple(row["rest"]), turn)
        length = math.sqrt(sum(item * item for item in value))
        return [item / length for item in value]
    value = [base + axis * displacement for base, axis in zip(row["rest"], row["axis"])]
    if row["path"] == "scale" and any(item <= 1e-6 for item in value):
        raise ValueError(f"secondary motion inverted scale for {row['target']}")
    return value


def _simulate(row, driver, times, settle_frame):
    profile = _profile(row["motion_class"])
    component = row["driver_component"]
    scalars = [value[component] for value in driver["values"]]
    # Quaternion tracks may legally switch sign without changing orientation.
    if driver["path"] == "rotation":
        for index in range(1, len(scalars)):
            if sum(a * b for a, b in zip(driver["values"][index - 1], driver["values"][index])) < 0:
                scalars[index] *= -1
    velocity = [0.] + [b - a for a, b in zip(scalars, scalars[1:])]
    maximum = max(abs(value) for value in velocity)
    if maximum <= 1e-12:
        raise ValueError(f"primary driver has no motion: {row['driver_target']} {row['driver_path']}")
    signal = [value / maximum for value in velocity]
    displacement, speed = 0., 0.
    raw = [0.]
    omega = 2 * math.pi * profile.response_hz
    for frame in range(1, len(times)):
        delayed = max(0, frame - row["lag_frames"])
        target = -row["direction"] * row["amplitude"] * profile.drive_gain * signal[delayed]
        target = max(-row["amplitude"], min(row["amplitude"], target))
        dt = times[frame] - times[frame - 1]
        substeps = max(2, math.ceil(dt * omega * 4))
        step = dt / substeps
        for _ in range(substeps):
            acceleration = omega * omega * (target - displacement) - 2 * profile.damping * omega * speed
            speed += acceleration * step
            displacement += speed * step
        displacement = max(-row["amplitude"], min(row["amplitude"], displacement))
        raw.append(displacement)
    preclosure_residual = raw[-1]
    closure_start = max(1, settle_frame)
    start_value = raw[closure_start]
    start_slope = raw[closure_start] - raw[closure_start - 1]
    remaining = len(raw) - 1 - closure_start
    for frame in range(closure_start, len(raw)):
        t = (frame - closure_start) / remaining
        h00 = 2 * t ** 3 - 3 * t ** 2 + 1
        h10 = t ** 3 - 2 * t ** 2 + t
        raw[frame] = h00 * start_value + h10 * remaining * start_slope
    raw[-1] = 0.
    return raw, preclosure_residual


def compose_secondary_motion(primary, raw):
    source_primary, source_request = copy.deepcopy(primary), copy.deepcopy(raw)
    clip, times, events = _validate_primary(primary)
    request = _request(raw, clip["tracks"])
    drivers = {(track["target"], track["path"]): track for track in clip["tracks"]}
    tracks, receipts = [], []
    for row in request["attachments"]:
        driver = drivers[(row["driver_target"], row["driver_path"])]
        scalar, residual = _simulate(row, driver, times, events["settle"])
        values = [_value(row, amount) for amount in scalar]
        seam = max(abs(a - b) for a, b in zip(values[0], values[-1]))
        first_driver = next(index for index, (a, b) in
                            enumerate(zip(driver["values"], driver["values"][1:]), 1)
                            if max(abs(x - y) for x, y in zip(a, b)) > 1e-10)
        moving = [index for index, amount in enumerate(scalar) if abs(amount) > 1e-8]
        first_secondary = moving[0] if moving else len(scalar)
        tracks.append({"target": row["target"], "path": row["path"],
                       "interpolation": "LINEAR", "times": list(times), "values": values})
        receipts.append({
            "target": row["target"], "motion_class": row["motion_class"],
            "declared_lag_frames": row["lag_frames"],
            "observed_response_lag_frames": first_secondary - first_driver,
            "peak_displacement": max(abs(value) for value in scalar),
            "amplitude_limit": row["amplitude"], "preclosure_residual": residual,
            "loop_seam_error": seam,
        })
    maximum_seam = max(row["loop_seam_error"] for row in receipts)
    passed = maximum_seam <= 1e-10 and all(
        row["peak_displacement"] <= row["amplitude_limit"] + 1e-12 for row in receipts)
    return {
        "schema": SECONDARY_MOTION_SCHEMA,
        "primary": source_primary,
        "primary_sha256": _digest(source_primary),
        "source": source_request,
        "source_sha256": _digest(source_request),
        "clip": {"name": request["name"], "fps": clip["fps"],
                 "duration": clip["duration"], "loop": clip["loop"],
                 "tracks": tracks, "events": copy.deepcopy(clip["events"])},
        "receipt": {"tracks": receipts, "closure_start_frame": events["settle"],
                    "maximum_loop_seam_error": maximum_seam, "passed": passed},
        "gates": {
            "primary-byte-equivalent": source_primary == primary,
            "bounded-amplitude": all(row["peak_displacement"] <= row["amplitude_limit"] + 1e-12
                                     for row in receipts),
            "exact-loop-closure": maximum_seam <= 1e-10,
            "target-engine-playback": False,
            "soft-body-cloth-simulation": False,
        },
    }


def publish_secondary_motion(path, primary, request):
    path = Path(path)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {path}")
    result = compose_secondary_motion(primary, request)
    path.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{path.name}-", dir=path.parent))
    try:
        atomic_write_json(staging / "primary.json", result["primary"])
        atomic_write_json(staging / "source.json", result["source"])
        atomic_write_json(staging / "secondary-clip.json", result["clip"])
        atomic_write_json(staging / "secondary-receipt.json", result["receipt"])
        os.replace(staging, path)
    except Exception:
        for child in staging.glob("*"):
            child.unlink()
        staging.rmdir()
        raise
    return {"schema": SECONDARY_MOTION_SCHEMA, "path": str(path),
            "files": sorted(item.name for item in path.iterdir()),
            "primary_sha256": result["primary_sha256"],
            "source_sha256": result["source_sha256"], "receipt": result["receipt"]}

"""Compile explicit vehicle presentation samples into rigid assembly traces.

The compiler does not solve vehicle dynamics. It maps caller-owned distance,
steering, suspension and body motion to ordinary rigid frames that the existing
sticker assembly exporter, a game engine, or a human-authored tool can consume.
"""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import tempfile

from .atomic import atomic_write_json


REQUEST_SCHEMA = "axm.rigid-vehicle-motion-request/v0.1"
RESULT_SCHEMA = "axm.rigid-vehicle-motion/v0.1"
WHEEL_ROLES = ("front-left", "front-right", "rear-left", "rear-right")
MAX_SAMPLES = 240


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low=-100_000.0, high=100_000.0):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} through {high}")
    return value


def _vector(value, width, label, low=-100_000.0, high=100_000.0):
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise ValueError(f"{label} must contain {width} numbers")
    return [_number(item, f"{label}[{index}]", low, high) for index, item in enumerate(value)]


def _matrix(translation, rotation):
    """Row-major rigid matrix, Euler input ordered pitch(X), yaw(Y), roll(Z)."""
    pitch, yaw, roll = rotation
    cx, sx = math.cos(pitch), math.sin(pitch)
    cy, sy = math.cos(yaw), math.sin(yaw)
    cz, sz = math.cos(roll), math.sin(roll)
    # Rz * Ry * Rx; Y-up games can layer body pitch, steering yaw and body roll.
    return [
        cz * cy, cz * sy * sx - sz * cx, cz * sy * cx + sz * sx, translation[0],
        sz * cy, sz * sy * sx + cz * cx, sz * sy * cx - cz * sx, translation[1],
        -sy, cy * sx, cy * cx, translation[2],
        0.0, 0.0, 0.0, 1.0,
    ]


def rigid_vehicle_motion_catalog():
    return {
        "schema": "axm.rigid-vehicle-motion-catalog/v0.1",
        "input": "explicit distance, steering, suspension, body, impact, light and damage samples",
        "output": "renderer-neutral rigid frames for body, four corners and four wheels",
        "assembly_compatible": True,
        "limits": {"samples": MAX_SAMPLES, "wheels": 4, "maximum_wheel_step_radians": math.pi},
        "truth": (
            "Compiles caller-owned presentation samples. It does not infer contact, solve suspension, "
            "simulate tyres, collisions or damage, or change gameplay state."
        ),
    }


def _contract(raw):
    required = {"wheel_radius_m", "wheel_positions_m", "max_steer_rad",
                "max_suspension_m", "max_body_rotation_rad", "max_impact_offset_m"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"contract must contain exactly {sorted(required)}")
    positions = raw["wheel_positions_m"]
    if not isinstance(positions, dict) or set(positions) != set(WHEEL_ROLES):
        raise ValueError("wheel_positions_m must define the four canonical wheel roles")
    return {
        "wheel_radius_m": _number(raw["wheel_radius_m"], "wheel_radius_m", .05, 5.0),
        "wheel_positions_m": {role: _vector(positions[role], 3, role) for role in WHEEL_ROLES},
        "max_steer_rad": _number(raw["max_steer_rad"], "max_steer_rad", 0.01, 1.4),
        "max_suspension_m": _number(raw["max_suspension_m"], "max_suspension_m", .001, 2.0),
        "max_body_rotation_rad": _number(raw["max_body_rotation_rad"], "max_body_rotation_rad", .001, 1.4),
        "max_impact_offset_m": _number(raw["max_impact_offset_m"], "max_impact_offset_m", .001, 2.0),
    }


def _sample(raw, index, contract, previous_time, previous_distance):
    required = {"time_s", "distance_m", "steer", "suspension_m", "body_heave_m",
                "body_pitch_rad", "body_roll_rad", "impact_offset_m",
                "impact_rotation_rad", "damage_stage", "lights"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"samples[{index}] must contain exactly {sorted(required)}")
    time = _number(raw["time_s"], f"samples[{index}].time_s", 0, 3600)
    distance = _number(raw["distance_m"], f"samples[{index}].distance_m", -1_000_000, 1_000_000)
    if index == 0 and time != 0:
        raise ValueError("the first sample must start at time zero")
    if index and time <= previous_time:
        raise ValueError("sample times must strictly increase")
    if index and distance < previous_distance:
        raise ValueError("vehicle distance must not move backwards in this first compiler")
    steer = _number(raw["steer"], f"samples[{index}].steer", -1, 1)
    suspension = _vector(raw["suspension_m"], 4, f"samples[{index}].suspension_m",
                         -contract["max_suspension_m"], contract["max_suspension_m"])
    heave = _number(raw["body_heave_m"], f"samples[{index}].body_heave_m",
                    -contract["max_suspension_m"], contract["max_suspension_m"])
    pitch = _number(raw["body_pitch_rad"], f"samples[{index}].body_pitch_rad",
                    -contract["max_body_rotation_rad"], contract["max_body_rotation_rad"])
    roll = _number(raw["body_roll_rad"], f"samples[{index}].body_roll_rad",
                   -contract["max_body_rotation_rad"], contract["max_body_rotation_rad"])
    impact = _vector(raw["impact_offset_m"], 3, f"samples[{index}].impact_offset_m",
                     -contract["max_impact_offset_m"], contract["max_impact_offset_m"])
    impact_rotation = _vector(
        raw["impact_rotation_rad"], 3, f"samples[{index}].impact_rotation_rad",
        -contract["max_body_rotation_rad"], contract["max_body_rotation_rad"])
    stage = raw["damage_stage"]
    if isinstance(stage, bool) or not isinstance(stage, int) or not 0 <= stage <= 4:
        raise ValueError("damage_stage must be an integer from 0 through 4")
    lights = raw["lights"]
    if (not isinstance(lights, dict) or set(lights) != {"head", "brake", "reverse", "damage"}
            or any(type(value) is not bool for value in lights.values())):
        raise ValueError("lights must contain four boolean presentation states")
    return {
        "time_s": time, "distance_m": distance, "steer": steer,
        "suspension_m": suspension, "body_heave_m": heave,
        "body_pitch_rad": pitch, "body_roll_rad": roll,
        "impact_offset_m": impact, "impact_rotation_rad": impact_rotation,
        "damage_stage": stage, "lights": dict(lights),
    }


def compile_rigid_vehicle_motion(raw):
    before = copy.deepcopy(raw)
    required = {"schema", "name", "contract", "samples"}
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema") != REQUEST_SCHEMA:
        raise ValueError(f"request must use {REQUEST_SCHEMA} and contain exactly {sorted(required)}")
    name = raw["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        raise ValueError("name must contain 1..120 characters")
    contract = _contract(raw["contract"])
    rows = raw["samples"]
    if not isinstance(rows, list) or not 2 <= len(rows) <= MAX_SAMPLES:
        raise ValueError(f"samples must contain 2..{MAX_SAMPLES} entries")
    samples = []
    for index, row in enumerate(rows):
        samples.append(_sample(
            row, index, contract,
            samples[-1]["time_s"] if samples else -1,
            samples[-1]["distance_m"] if samples else -1_000_001,
        ))
    if raw != before:
        raise AssertionError("vehicle motion compilation mutated its caller")

    times = [row["time_s"] for row in samples]
    traces = {"body": []}
    for role in WHEEL_ROLES:
        traces[f"corner-{role}"] = []
        traces[f"wheel-{role}"] = []
    max_wheel_step = 0.0
    previous_angles = None
    origin_distance = samples[0]["distance_m"]
    states = []
    for row in samples:
        time = row["time_s"]
        body_translation = [row["impact_offset_m"][0],
                            row["body_heave_m"] + row["impact_offset_m"][1],
                            row["impact_offset_m"][2]]
        body_rotation = [row["body_pitch_rad"] + row["impact_rotation_rad"][0],
                         row["impact_rotation_rad"][1],
                         row["body_roll_rad"] + row["impact_rotation_rad"][2]]
        traces["body"].append({"time": time, "frame": _matrix(body_translation, body_rotation)})
        angles = []
        for wheel_index, role in enumerate(WHEEL_ROLES):
            base = contract["wheel_positions_m"][role]
            corner_translation = [base[0], base[1] + row["suspension_m"][wheel_index], base[2]]
            steer_angle = row["steer"] * contract["max_steer_rad"] if role.startswith("front") else 0.0
            traces[f"corner-{role}"].append({
                "time": time, "frame": _matrix(corner_translation, [0, steer_angle, 0])})
            # Assembly motion is relative to the declared first pose. Keeping
            # the initial roll at zero also avoids baking a route coordinate
            # into otherwise reusable wheel geometry.
            angle = -(row["distance_m"] - origin_distance) / contract["wheel_radius_m"]
            angles.append(angle)
            traces[f"wheel-{role}"].append({"time": time, "frame": _matrix([0, 0, 0], [angle, 0, 0])})
        if previous_angles is not None:
            max_wheel_step = max(max_wheel_step, *(abs(a - b) for a, b in zip(angles, previous_angles)))
        previous_angles = angles
        states.append({"time": time, "damage_stage": row["damage_stage"], "lights": row["lights"]})
    if max_wheel_step > math.pi + 1e-9:
        raise ValueError("wheel samples alias more than pi radians; provide denser distance samples")
    source = {"schema": REQUEST_SCHEMA, "name": name.strip(), "contract": contract, "samples": samples}
    return {
        "schema": RESULT_SCHEMA,
        "source": source,
        "source_sha256": _digest(source),
        "traces": traces,
        "presentation_states": states,
        "receipt": {
            "duration_s": times[-1],
            "distance_m": samples[-1]["distance_m"] - samples[0]["distance_m"],
            "wheel_rotation_radians": -(samples[-1]["distance_m"] - samples[0]["distance_m"]) / contract["wheel_radius_m"],
            "maximum_wheel_step_radians": max_wheel_step,
            "trace_count": len(traces),
            "sample_count": len(samples),
            "assembly_motion_compatible": True,
        },
        "truth": rigid_vehicle_motion_catalog()["truth"],
    }


def publish_rigid_vehicle_motion(path, request):
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    result = compile_rigid_vehicle_motion(request)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=".axm-vehicle-motion-", dir=target.parent))
    try:
        atomic_write_json(stage / "vehicle-motion-source.json", result["source"])
        atomic_write_json(stage / "vehicle-motion.json", result)
        if target.exists():
            raise FileExistsError(f"refusing to overwrite existing path: {target}")
        stage.rename(target)
        return result
    finally:
        if stage.exists():
            shutil.rmtree(stage)

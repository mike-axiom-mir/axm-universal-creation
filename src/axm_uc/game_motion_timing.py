"""Deterministic animation timing composition for portable game motion.

The composer turns explicit rest/action transforms into fully sampled tracks
with readable anticipation, accelerated action, impact, recoil and settle
phases.  It authors timing only: callers retain rig, mesh and material truth.
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


MOTION_TIMING_SCHEMA = "axm.game-motion-timing/v0.1"
PATH_WIDTHS = {"translation": 3, "rotation": 4, "scale": 3}


@dataclass(frozen=True)
class MotionTimingProfile:
    name: str
    anticipation_time: float
    impact_time: float
    recoil_time: float
    counter_time: float
    settle_time: float
    anticipation: float
    recoil: float
    counter: float
    settle: float
    action_exponent: float


PROFILES = (
    MotionTimingProfile("restrained-product", .20, .50, .62, .74, .88, .08, .86, .04, .015, 1.65),
    MotionTimingProfile("weighty-salvage", .27, .60, .69, .79, .92, .24, .68, -.07, .025, 2.45),
    MotionTimingProfile("snappy-comic", .16, .38, .47, .59, .78, .34, .52, -.16, .055, 2.05),
    MotionTimingProfile("springy-adventure", .21, .43, .54, .67, .86, .20, .58, -.22, .10, 1.85),
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


def _vector(value, width, label):
    if not isinstance(value, (list, tuple)) or len(value) != width:
        raise ValueError(f"{label} must contain {width} values")
    return tuple(_number(item, f"{label}[{index}]", -100000, 100000)
                 for index, item in enumerate(value))


def _normalize_quaternion(value, label):
    value = _vector(value, 4, label)
    length = math.sqrt(sum(item * item for item in value))
    if length < 1e-12:
        raise ValueError(f"{label} cannot be a zero quaternion")
    if abs(length - 1) > 1e-5:
        raise ValueError(f"{label} must be normalized")
    return tuple(item / length for item in value)


def _profile(name):
    for profile in PROFILES:
        if profile.name == name:
            return profile
    raise ValueError(f"unknown motion timing profile: {name}")


def game_motion_timing_catalog():
    return {
        "schema": "axm.game-motion-timing-catalog/v0.1",
        "profiles": [asdict(profile) for profile in PROFILES],
        "paths": copy.deepcopy(PATH_WIDTHS),
        "phases": ["rest", "anticipation", "impact", "recoil", "counter", "settle", "complete"],
        "canonical_source_preserved": True,
        "material_and_geometry_unchanged": True,
        "truth": (
            "Produces sampled local transform tracks and timing receipts. It does not infer a rig, "
            "skin a mesh, solve contacts, export an engine controller or prove motion quality."
        ),
    }


def _request(raw):
    if not isinstance(raw, dict) or set(raw) != {"name", "fps", "duration", "loop", "channels"}:
        raise ValueError("motion request must contain exactly name, fps, duration, loop and channels")
    name = raw["name"]
    if not isinstance(name, str) or not name.strip() or len(name) > 96:
        raise ValueError("motion name must contain 1..96 visible characters")
    if type(raw["fps"]) is not int or not 12 <= raw["fps"] <= 120:
        raise ValueError("fps must be an integer from 12 to 120")
    duration = _number(raw["duration"], "duration", .5, 10)
    if type(raw["loop"]) is not bool:
        raise ValueError("loop must be boolean")
    channels = raw["channels"]
    if not isinstance(channels, list) or not 1 <= len(channels) <= 64:
        raise ValueError("channels must contain 1..64 entries")
    normalized, targets = [], set()
    for index, channel in enumerate(channels):
        label = f"channels[{index}]"
        if not isinstance(channel, dict):
            raise ValueError(f"{label} must be an object")
        allowed = {"target", "path", "rest", "action", "anticipation_scale", "contact_at_impact"}
        if not {"target", "path", "rest", "action"} <= set(channel) or set(channel) - allowed:
            raise ValueError(f"{label} has missing or unsupported fields")
        target, path = channel["target"], channel["path"]
        if not isinstance(target, str) or not target.strip() or len(target) > 128 or path not in PATH_WIDTHS:
            raise ValueError(f"{label} has an invalid target or path")
        key = (target, path)
        if key in targets:
            raise ValueError(f"duplicate channel target: {target} {path}")
        targets.add(key)
        width = PATH_WIDTHS[path]
        if path == "rotation":
            rest = _normalize_quaternion(channel["rest"], f"{label}.rest")
            action = _normalize_quaternion(channel["action"], f"{label}.action")
        else:
            rest = _vector(channel["rest"], width, f"{label}.rest")
            action = _vector(channel["action"], width, f"{label}.action")
            if path == "scale" and (any(item <= 0 for item in rest) or any(item <= 0 for item in action)):
                raise ValueError(f"{label} scale endpoints must be positive")
        anticipation_scale = _number(channel.get("anticipation_scale", 1),
                                     f"{label}.anticipation_scale", 0, 2)
        contact = channel.get("contact_at_impact", False)
        if type(contact) is not bool:
            raise ValueError(f"{label}.contact_at_impact must be boolean")
        normalized.append({"target": target, "path": path, "rest": list(rest), "action": list(action),
                           "anticipation_scale": anticipation_scale, "contact_at_impact": contact})
    frames = round(duration * raw["fps"])
    if frames < 12 or frames > 1200:
        raise ValueError("duration and fps must produce 12..1200 intervals")
    return {"name": name, "fps": raw["fps"], "duration": frames / raw["fps"],
            "loop": raw["loop"], "channels": normalized}, frames


def _phase_frames(profile, end):
    ratios = (profile.anticipation_time, profile.impact_time, profile.recoil_time,
              profile.counter_time, profile.settle_time)
    result, previous = [], 0
    for index, ratio in enumerate(ratios):
        remaining = len(ratios) - index
        frame = round(end * ratio)
        frame = max(previous + 1, min(frame, end - remaining))
        result.append(frame)
        previous = frame
    return (0, *result, end)


def _smoothstep(value):
    return value * value * (3 - 2 * value)


def _ease_out_quad(value):
    return 1 - (1 - value) * (1 - value)


def _weight(frame, phase_frames, profile):
    values = (0., -profile.anticipation, 1., profile.recoil,
              profile.counter, profile.settle, 0.)
    for index, (start, end) in enumerate(zip(phase_frames, phase_frames[1:])):
        if frame <= end:
            t = (frame - start) / (end - start)
            if index == 1:
                t = t ** profile.action_exponent
            elif index == 2:
                t = _ease_out_quad(t)
            else:
                t = _smoothstep(t)
            return values[index] + (values[index + 1] - values[index]) * t
    return 0.


def _slerp(a, b, amount):
    dot = sum(x * y for x, y in zip(a, b))
    if dot < 0:
        b = tuple(-item for item in b)
        dot = -dot
    dot = max(-1., min(1., dot))
    if dot > .9995:
        value = tuple(x + (y - x) * amount for x, y in zip(a, b))
    else:
        angle = math.acos(dot)
        value = tuple((x * math.sin((1 - amount) * angle) + y * math.sin(amount * angle)) /
                      math.sin(angle) for x, y in zip(a, b))
    length = math.sqrt(sum(item * item for item in value))
    return tuple(item / length for item in value)


def _interpolate(channel, amount):
    if amount < 0:
        amount *= channel["anticipation_scale"]
    if channel["path"] == "rotation":
        return _slerp(tuple(channel["rest"]), tuple(channel["action"]), amount)
    value = tuple(a + (b - a) * amount for a, b in zip(channel["rest"], channel["action"]))
    if channel["path"] == "scale" and any(item <= 1e-6 for item in value):
        raise ValueError(f"motion would invert scale for {channel['target']}")
    return value


def _max_delta(a, b):
    return max(abs(x - y) for x, y in zip(a, b))


def _transform_error(path, a, b):
    direct = _max_delta(a, b)
    if path != "rotation":
        return direct
    return min(direct, _max_delta(a, [-item for item in b]))


def compose_game_motion(raw, profile_name="weighty-salvage"):
    source = copy.deepcopy(raw)
    request, end = _request(raw)
    profile = _profile(profile_name)
    frames = _phase_frames(profile, end)
    names = ("rest", "anticipation", "impact", "recoil", "counter", "settle", "complete")
    weights = [_weight(frame, frames, profile) for frame in range(end + 1)]
    tracks, impact_targets = [], []
    impact_frame = frames[2]
    maximum_quaternion_error = 0.
    for channel in request["channels"]:
        values = [list(_interpolate(channel, weight)) for weight in weights]
        if channel["path"] == "rotation":
            maximum_quaternion_error = max(maximum_quaternion_error,
                                           max(abs(sum(v * v for v in value) - 1) for value in values))
        if channel["contact_at_impact"]:
            error = _transform_error(channel["path"], values[impact_frame], channel["action"])
            if error > 1e-9:
                raise ValueError(f"impact contact target drifted: {channel['target']}")
            impact_targets.append({"target": channel["target"], "path": channel["path"],
                                   "maximum_error": error})
        tracks.append({"target": channel["target"], "path": channel["path"],
                       "interpolation": "LINEAR", "times": [frame / request["fps"] for frame in range(end + 1)],
                       "values": values})
    action_steps = [abs(weights[index + 1] - weights[index])
                    for index in range(frames[1], frames[2])]
    split = max(1, len(action_steps) // 2)
    early = max(action_steps[:split], default=0.)
    late = max(action_steps[split:], default=0.)
    if early <= 1e-12:
        raise ValueError("action timing has no measurable early movement")
    acceleration_ratio = late / early
    loop_error = max(_max_delta(track["values"][0], track["values"][-1]) for track in tracks)
    result = {
        "schema": MOTION_TIMING_SCHEMA,
        "source": source,
        "source_sha256": _digest(source),
        "profile": asdict(profile),
        "clip": {"name": request["name"], "fps": request["fps"], "duration": request["duration"],
                 "loop": request["loop"], "tracks": tracks,
                 "events": [{"name": name, "frame": frame, "time": frame / request["fps"]}
                            for name, frame in zip(names, frames)]},
        "receipt": {
            "sampled_intervals": end,
            "strictly_increasing_times": True,
            "impact_frame": impact_frame,
            "impact_targets": impact_targets,
            "action_acceleration_ratio": acceleration_ratio,
            "maximum_loop_seam_error": loop_error,
            "maximum_quaternion_norm_error": maximum_quaternion_error,
            "final_settle_weight": weights[-1],
            "passed": acceleration_ratio > 1 and maximum_quaternion_error <= 1e-10 and
                      (not request["loop"] or loop_error <= 1e-10),
        },
        "gates": {
            "timing-structure-valid": True,
            "accelerated-action-measured": acceleration_ratio > 1,
            "declared-impact-targets-exact": all(row["maximum_error"] <= 1e-9 for row in impact_targets),
            "loop-seam-exact-when-requested": not request["loop"] or loop_error <= 1e-10,
            "rig-export-observed": False,
            "contact-solve-observed": False,
            "target-engine-observed": False,
        },
        "limits": (
            "Local sampled transform tracks only. No rig inference, skin deformation, IK/contact solving, "
            "secondary motion, state machine, target-engine playback or perceptual animation acceptance."
        ),
    }
    if not result["receipt"]["passed"]:
        raise ValueError("composed motion failed its timing receipt")
    return result


def publish_game_motion(path, request, profile_name="weighty-salvage"):
    target = Path(path).resolve()
    if target.exists():
        raise FileExistsError(f"output already exists: {target}")
    result = compose_game_motion(request, profile_name)
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix=f".{target.name}-", dir=target.parent))
    try:
        atomic_write_json(stage / "source.json", result["source"])
        atomic_write_json(stage / "motion-clip.json", result["clip"])
        atomic_write_json(stage / "motion-receipt.json", {key: result[key] for key in
                                                          ("schema", "source_sha256", "profile", "receipt", "gates", "limits")})
        os.replace(stage, target)
    except Exception:
        for child in stage.iterdir():
            child.unlink()
        stage.rmdir()
        raise
    return {"path": str(target), "profile": profile_name, "clip": result["clip"]["name"],
            "files": sorted(item.name for item in target.iterdir()), "receipt": result["receipt"]}

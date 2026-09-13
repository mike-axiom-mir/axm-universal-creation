"""Deterministic clip clocks, transitions, events and root-motion ownership."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json


ANIMATION_RUNTIME_SCHEMA = "axm.game-animation-runtime/v0.1"
MAX_CLIPS = 128
MAX_COMMANDS = 10_000


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value):
    return hashlib.sha256(_canonical(value)).hexdigest()


def _name(value, label):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{label} must contain 1..128 visible characters")
    return value


def _number(value, label, low=0., high=10_000.):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _vec3(value, label):
    if not isinstance(value, list) or len(value) != 3:
        raise ValueError(f"{label} must contain three finite numbers")
    return [_number(item, f"{label}[{index}]", -100_000, 100_000) for index, item in enumerate(value)]


def game_animation_runtime_catalog():
    return {
        "schema": "axm.game-animation-runtime-catalog/v0.1",
        "executes": ["clip clocks", "explicit transitions", "timed events", "completion transitions", "root-motion ownership"],
        "root_motion_modes": ["ignore", "extract", "apply"],
        "canonical_source_preserved": True,
        "truth": (
            "Executes deterministic adapter-neutral animation state. It does not load a GLB, render, blend poses, "
            "solve collision, or prove playback in Unity, Unreal, Godot or a browser renderer."
        ),
    }


def compile_game_animation_runtime(raw):
    before = copy.deepcopy(raw)
    required = {"schema", "id", "initial_state", "clips", "states", "transitions"}
    if not isinstance(raw, dict) or set(raw) != required or raw.get("schema") != ANIMATION_RUNTIME_SCHEMA:
        raise ValueError(f"runtime must use {ANIMATION_RUNTIME_SCHEMA} and contain exactly {sorted(required)}")
    clips, clip_names = [], set()
    if not isinstance(raw["clips"], list) or not 1 <= len(raw["clips"]) <= MAX_CLIPS:
        raise ValueError(f"clips must contain 1..{MAX_CLIPS} entries")
    for index, row in enumerate(raw["clips"]):
        fields = {"name", "duration_s", "loop", "root_motion_m", "events"}
        if not isinstance(row, dict) or set(row) != fields or type(row["loop"]) is not bool:
            raise ValueError(f"clips[{index}] has unsupported fields or loop type")
        name = _name(row["name"], "clip.name")
        if name in clip_names:
            raise ValueError("clip names must be unique")
        duration = _number(row["duration_s"], "clip.duration_s", .01, 600)
        events, prior = [], -1.
        if not isinstance(row["events"], list) or len(row["events"]) > 256:
            raise ValueError("clip.events must contain at most 256 entries")
        for event in row["events"]:
            if not isinstance(event, dict) or set(event) != {"name", "time_s"}:
                raise ValueError("clip events require exactly name and time_s")
            time = _number(event["time_s"], "event.time_s", 0, duration)
            if time <= prior:
                raise ValueError("clip events must have strictly increasing times")
            prior = time
            events.append({"name": _name(event["name"], "event.name"), "time_s": time})
        clip_names.add(name)
        clips.append({"name": name, "duration_s": duration, "loop": row["loop"],
                      "root_motion_m": _vec3(row["root_motion_m"], "clip.root_motion_m"), "events": events})
    states, state_names = [], set()
    if not isinstance(raw["states"], list) or not 1 <= len(raw["states"]) <= 256:
        raise ValueError("states must contain 1..256 entries")
    for index, row in enumerate(raw["states"]):
        fields = {"name", "clip", "speed", "root_motion", "completion_event"}
        if not isinstance(row, dict) or set(row) != fields:
            raise ValueError(f"states[{index}] has unsupported fields")
        name, clip = _name(row["name"], "state.name"), _name(row["clip"], "state.clip")
        if name in state_names or clip not in clip_names:
            raise ValueError("state names must be unique and clips must exist")
        mode = row["root_motion"]
        if mode not in ("ignore", "extract", "apply"):
            raise ValueError("state.root_motion must be ignore, extract or apply")
        complete = row["completion_event"]
        if complete is not None:
            complete = _name(complete, "state.completion_event")
        states.append({"name": name, "clip": clip, "speed": _number(row["speed"], "state.speed", .01, 4),
                       "root_motion": mode, "completion_event": complete})
        state_names.add(name)
    initial = _name(raw["initial_state"], "initial_state")
    if initial not in state_names:
        raise ValueError("initial_state must name a state")
    transitions, pairs = [], set()
    if not isinstance(raw["transitions"], list) or len(raw["transitions"]) > 4096:
        raise ValueError("transitions must contain at most 4096 entries")
    for index, row in enumerate(raw["transitions"]):
        if not isinstance(row, dict) or set(row) != {"from", "event", "to", "blend_s"}:
            raise ValueError(f"transitions[{index}] has unsupported fields")
        source, event, target = (_name(row[key], f"transition.{key}") for key in ("from", "event", "to"))
        if source not in state_names or target not in state_names or (source, event) in pairs:
            raise ValueError("transitions require declared states and unique from/event pairs")
        pairs.add((source, event))
        transitions.append({"from": source, "event": event, "to": target,
                            "blend_s": _number(row["blend_s"], "transition.blend_s", 0, 10)})
    clip_by_name = {row["name"]: row for row in clips}
    for state in states:
        complete = state["completion_event"]
        if clip_by_name[state["clip"]]["loop"] and complete is not None:
            raise ValueError("looping states cannot declare completion events")
        if complete is not None and (state["name"], complete) not in pairs:
            raise ValueError("every completion event must have an explicit transition")
    normalized = {"schema": ANIMATION_RUNTIME_SCHEMA, "id": _name(raw["id"], "id"),
                  "initial_state": initial, "clips": clips, "states": states,
                  "transitions": sorted(transitions, key=lambda row: (row["from"], row["event"], row["to"]))}
    if raw != before:
        raise AssertionError("animation runtime validation mutated caller source")
    return {"schema": "axm.game-animation-runtime-compiled/v0.1", "source": normalized,
            "source_sha256": _digest(normalized), "truth": game_animation_runtime_catalog()["truth"]}


def replay_game_animation_runtime(raw, commands):
    compiled = compile_game_animation_runtime(raw)
    if not isinstance(commands, list) or len(commands) > MAX_COMMANDS:
        raise ValueError(f"commands must contain at most {MAX_COMMANDS} entries")
    source = compiled["source"]
    clips = {row["name"]: row for row in source["clips"]}
    states = {row["name"]: row for row in source["states"]}
    transitions = {(row["from"], row["event"]): row for row in source["transitions"]}
    current, time, cycles = source["initial_state"], 0., 0
    world = [0., 0., 0.]
    transcript = []

    def dispatch(event, automatic=False):
        nonlocal current, time, cycles
        row = transitions.get((current, event))
        if row is None:
            return {"type": "HOLD_NO_DECLARED_TRANSITION", "event": event, "state": current,
                    "automatic": automatic, "applied": False}
        prior = current
        current, time, cycles = row["to"], 0., 0
        return {"type": "TRANSITION", "event": event, "from": prior, "to": current,
                "blend_s": row["blend_s"], "automatic": automatic, "applied": True}

    for index, command in enumerate(commands):
        if not isinstance(command, dict) or len(command) != 1 or next(iter(command)) not in ("event", "dt"):
            raise ValueError("each command must contain exactly event or dt")
        emitted, extracted = [], [0., 0., 0.]
        if "event" in command:
            emitted.append(dispatch(_name(command["event"], "command.event")))
        else:
            remaining = _number(command["dt"], "command.dt", 0, 10)
            guard = 0
            while remaining > 1e-12:
                guard += 1
                if guard > 10_000:
                    raise ValueError("advance exceeded bounded transition work")
                state, clip = states[current], clips[states[current]["clip"]]
                wall_to_end = (clip["duration_s"] - time) / state["speed"]
                wall = min(remaining, wall_to_end)
                start, end = time, time + wall * state["speed"]
                fraction = (end - start) / clip["duration_s"]
                delta = [value * fraction for value in clip["root_motion_m"]]
                if state["root_motion"] == "apply":
                    world = [value + step for value, step in zip(world, delta)]
                elif state["root_motion"] == "extract":
                    extracted = [value + step for value, step in zip(extracted, delta)]
                for event in clip["events"]:
                    if start < event["time_s"] <= end + 1e-12:
                        emitted.append({"type": "CLIP_EVENT", "state": current, "clip": clip["name"],
                                        "event": event["name"], "time_s": event["time_s"]})
                time, remaining = end, remaining - wall
                if abs(time - clip["duration_s"]) <= 1e-10:
                    if clip["loop"]:
                        cycles += 1; time = 0.
                        emitted.append({"type": "LOOP", "state": current, "clip": clip["name"], "cycle": cycles})
                    elif state["completion_event"] is not None:
                        emitted.append(dispatch(state["completion_event"], automatic=True))
                    else:
                        time = clip["duration_s"]; remaining = 0.
                        emitted.append({"type": "HOLD_AT_CLIP_END", "state": current, "clip": clip["name"]})
        transcript.append({"index": index, "command": copy.deepcopy(command), "state": current,
                           "clip": states[current]["clip"], "clip_time_s": time, "cycles": cycles,
                           "world_translation_m": list(world), "extracted_root_motion_m": extracted,
                           "emitted": emitted})
    return {"schema": "axm.game-animation-runtime-replay/v0.1", "compiled": compiled,
            "commands_sha256": _digest(commands), "final_state": current, "final_clip": states[current]["clip"],
            "world_translation_m": world, "transcript": transcript,
            "truth": "Deterministic adapter-neutral clock/state execution; no GLB loading, pose blending, collision, rendering or target-engine playback claim."}


def publish_game_animation_replay(path, runtime, commands):
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    result = replay_game_animation_runtime(runtime, commands)
    target.mkdir(parents=True)
    atomic_write_json(target / "animation-runtime-source.json", result["compiled"]["source"])
    atomic_write_json(target / "animation-runtime-replay.json", result)
    return result

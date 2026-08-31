from __future__ import annotations

import hashlib
import json
from typing import Any


STATE_MACHINE_SCHEMA = "axm.deterministic-state-machine/v0.1"
MAX_STATES = 256
MAX_TRANSITIONS = 4096
MAX_REPLAY_EVENTS = 10000


def state_machine_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_EXPLICIT_DETERMINISTIC_STATE_MACHINE",
        "schema": STATE_MACHINE_SCHEMA,
        "operations": ["compile", "step", "replay"],
        "maximum_states": MAX_STATES,
        "maximum_transitions": MAX_TRANSITIONS,
        "maximum_replay_events": MAX_REPLAY_EVENTS,
        "missing_transition_behavior": "HOLD_NO_DECLARED_TRANSITION",
        "effects_executed": False,
    }


class StateMachineError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise StateMachineError("state machine values must be finite JSON data", {"error": str(exc)}) from exc


def _text(value: Any, label: str, maximum: int = 200) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        raise StateMachineError(f"{label} must be 1..{maximum} characters of text")
    return value.strip()


def compile_state_machine(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise StateMachineError("machine must be an object")
    if set(raw) != {"schema", "id", "states", "initial_state", "transitions"}:
        raise StateMachineError(
            "machine must contain exactly schema, id, states, initial_state, and transitions",
            {"fields": sorted(str(key) for key in raw)},
        )
    if raw.get("schema") != STATE_MACHINE_SCHEMA:
        raise StateMachineError(f"machine schema must be {STATE_MACHINE_SCHEMA}")
    machine_id = _text(raw.get("id"), "machine.id")
    raw_states = raw.get("states")
    if not isinstance(raw_states, list) or not raw_states or len(raw_states) > MAX_STATES:
        raise StateMachineError(f"states must contain 1..{MAX_STATES} entries")
    states = [_text(value, "state", 120) for value in raw_states]
    if len(states) != len(set(states)):
        raise StateMachineError("states must be unique")
    state_set = set(states)
    initial = _text(raw.get("initial_state"), "initial_state", 120)
    if initial not in state_set:
        raise StateMachineError("initial_state must name one declared state")
    raw_transitions = raw.get("transitions")
    if not isinstance(raw_transitions, list) or len(raw_transitions) > MAX_TRANSITIONS:
        raise StateMachineError(f"transitions must be an array with at most {MAX_TRANSITIONS} entries")
    transitions: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for index, row in enumerate(raw_transitions):
        if not isinstance(row, dict) or not set(row).issubset({"from", "event", "to", "effects"}):
            raise StateMachineError("transition fields must be from, event, to, and optional effects", {"index": index})
        if not {"from", "event", "to"}.issubset(row):
            raise StateMachineError("transition requires from, event, and to", {"index": index})
        source = _text(row.get("from"), "transition.from", 120)
        event = _text(row.get("event"), "transition.event", 120)
        target = _text(row.get("to"), "transition.to", 120)
        if source not in state_set or target not in state_set:
            raise StateMachineError("transition states must be declared", {"index": index, "from": source, "to": target})
        key = (source, event)
        if key in seen:
            raise StateMachineError(
                "more than one transition for the same state and event would be nondeterministic",
                {"from": source, "event": event},
            )
        effects = row.get("effects", [])
        if not isinstance(effects, list):
            raise StateMachineError("transition effects must be an array of JSON data", {"index": index})
        effects = json.loads(_canonical(effects).decode("utf-8"))
        transitions.append({"from": source, "event": event, "to": target, "effects": effects})
        seen.add(key)
    transitions.sort(key=lambda row: (row["from"], row["event"], row["to"]))
    normalized = {
        "schema": STATE_MACHINE_SCHEMA,
        "id": machine_id,
        "states": states,
        "initial_state": initial,
        "transitions": transitions,
    }
    outgoing = {state: 0 for state in states}
    for row in transitions:
        outgoing[row["from"]] += 1
    return {
        "truth_status": "COMPILED_EXPLICIT_DETERMINISTIC_STATE_GRAPH",
        "machine": normalized,
        "machine_digest": hashlib.sha256(_canonical(normalized)).hexdigest(),
        "state_count": len(states),
        "transition_count": len(transitions),
        "terminal_states": sorted(state for state, count in outgoing.items() if count == 0),
        "deterministic": True,
        "executable_effects": False,
        "proof_scope": "closed state/event transition selection only; effect entries are returned as data and never executed",
    }


def step_state_machine(compiled: dict[str, Any], state: Any, event: Any) -> dict[str, Any]:
    machine = compiled["machine"]
    current = _text(state, "state", 120)
    signal = _text(event, "event", 120)
    if current not in set(machine["states"]):
        raise StateMachineError("state must name one declared machine state", {"state": current})
    transition = next(
        (row for row in machine["transitions"] if row["from"] == current and row["event"] == signal),
        None,
    )
    if transition is None:
        return {
            "truth_status": "HOLD_NO_DECLARED_TRANSITION",
            "machine_digest": compiled["machine_digest"],
            "from": current,
            "event": signal,
            "to": current,
            "effects": [],
            "applied": False,
            "reason": "no explicit transition exists for this state and event; the machine did not guess",
        }
    return {
        "truth_status": "APPLIED_EXPLICIT_DETERMINISTIC_TRANSITION",
        "machine_digest": compiled["machine_digest"],
        "from": current,
        "event": signal,
        "to": transition["to"],
        "effects": transition["effects"],
        "applied": True,
        "effects_executed": False,
    }


def replay_state_machine(raw: Any, events: Any, *, state: Any = None, stop_on_hold: bool = True) -> dict[str, Any]:
    compiled = compile_state_machine(raw)
    if not isinstance(events, list) or len(events) > MAX_REPLAY_EVENTS:
        raise StateMachineError(f"events must be an array with at most {MAX_REPLAY_EVENTS} entries")
    current = compiled["machine"]["initial_state"] if state is None else _text(state, "state", 120)
    transcript: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        result = step_state_machine(compiled, current, event)
        result["index"] = index
        transcript.append(result)
        current = result["to"]
        if result["applied"] is not True and stop_on_hold:
            break
    applied = sum(1 for row in transcript if row["applied"] is True)
    return {
        "truth_status": "OBSERVED_DETERMINISTIC_STATE_REPLAY",
        "machine": compiled,
        "start_state": compiled["machine"]["initial_state"] if state is None else state,
        "final_state": current,
        "events_supplied": len(events),
        "events_observed": len(transcript),
        "transitions_applied": applied,
        "completed": len(transcript) == len(events) and applied == len(events),
        "stop_on_hold": stop_on_hold,
        "transcript": transcript,
        "effects_executed": False,
    }


def operate_state_machine(inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "compile")).strip().casefold()
    compiled = compile_state_machine(inputs["machine"])
    if operation == "compile":
        return {"operation": "compile", **compiled}
    if operation == "step":
        return {"operation": "step", "machine": compiled, "transition": step_state_machine(compiled, inputs["state"], inputs["event"])}
    if operation == "replay":
        return {
            "operation": "replay",
            **replay_state_machine(
                inputs["machine"],
                inputs["events"],
                state=inputs.get("state"),
                stop_on_hold=bool(inputs.get("stop_on_hold", True)),
            ),
        }
    raise StateMachineError("state-machine operation must be compile, step, or replay")

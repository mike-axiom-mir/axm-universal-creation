from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


def machine() -> dict:
    return {
        "schema": "axm.deterministic-state-machine/v0.1",
        "id": "round",
        "states": ["lobby", "playing", "finished"],
        "initial_state": "lobby",
        "transitions": [
            {"from": "playing", "event": "win", "to": "finished", "effects": [{"type": "award", "points": 1}]},
            {"from": "lobby", "event": "start", "to": "playing", "effects": [{"type": "start-clock"}]},
        ],
    }


class StateMachineRuntimeTests(unittest.TestCase):
    def test_compile_and_replay_are_deterministic_and_effects_stay_inert(self):
        runtime = UniversalCreationMachine(ROOT)
        compile_a = runtime.create({"kind": "deterministic-state-machine", "inputs": {"machine": machine()}})
        reordered = machine()
        reordered["transitions"].reverse()
        compile_b = runtime.create({"kind": "deterministic-state-machine", "inputs": {"machine": reordered}})
        self.assertEqual(compile_a["type"], "CREATION_RESULT", compile_a)
        self.assertEqual(compile_a["result"]["machine_digest"], compile_b["result"]["machine_digest"])

        replay = runtime.create(
            {
                "kind": "game-rule-state-machine",
                "inputs": {"operation": "replay", "machine": machine(), "events": ["start", "win"]},
            }
        )
        self.assertEqual(replay["type"], "CREATION_RESULT", replay)
        observed = replay["result"]
        self.assertEqual(observed["final_state"], "finished")
        self.assertTrue(observed["completed"])
        self.assertFalse(observed["effects_executed"])
        self.assertEqual(observed["transcript"][1]["effects"], [{"points": 1, "type": "award"}])

    def test_unknown_transition_holds_without_guessing_or_changing_state(self):
        result = UniversalCreationMachine(ROOT).create(
            {
                "kind": "workflow-state-machine",
                "inputs": {
                    "operation": "step",
                    "machine": machine(),
                    "state": "lobby",
                    "event": "win",
                },
            }
        )
        transition = result["result"]["transition"]
        self.assertEqual(transition["truth_status"], "HOLD_NO_DECLARED_TRANSITION")
        self.assertEqual(transition["to"], "lobby")
        self.assertFalse(transition["applied"])

    def test_duplicate_state_event_pair_is_rejected_as_nondeterministic(self):
        definition = machine()
        definition["transitions"].append(
            {"from": "lobby", "event": "start", "to": "finished", "effects": []}
        )
        result = UniversalCreationMachine(ROOT).create(
            {"kind": "deterministic-state-machine", "inputs": {"machine": definition}}
        )
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertIn("nondeterministic", result["message"])

    def test_operation_specific_inputs_are_reported_before_invocation(self):
        result = UniversalCreationMachine(ROOT).create(
            {"kind": "game-rule-state-machine", "inputs": {"operation": "step", "machine": machine()}}
        )
        self.assertEqual(result["type"], "CAPABILITY_INPUT_GAP", result)
        self.assertEqual(result["missing_required_inputs"], ["event", "state"])

        invalid_bool = UniversalCreationMachine(ROOT).create(
            {
                "kind": "game-rule-state-machine",
                "inputs": {
                    "operation": "replay",
                    "machine": machine(),
                    "events": [],
                    "stop_on_hold": "false",
                },
            }
        )
        self.assertEqual(invalid_bool["type"], "CREATION_ERROR", invalid_bool)
        self.assertIn("boolean", invalid_bool["message"])


if __name__ == "__main__":
    unittest.main()

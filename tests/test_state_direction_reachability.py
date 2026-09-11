from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.reachability import (
    BLOCKED_BY_CURRENT_CONSTRAINT,
    CURRENT_PATH_AVAILABLE,
    PATH_UNKNOWN_CURRENTLY,
    frame_state_direction,
    state_direction_summary,
)


class StateDirectionReachabilityTests(unittest.TestCase):
    def test_unknown_current_path_is_not_fundamental_impossibility(self):
        request = {
            "kind": "not-a-live-route-state-direction-test",
            "direction": "reach a currently unsupported but explicitly described target state",
            "inputs": {"target": {"shape": "closed-loop", "behavior": "deterministic"}},
        }
        framed = frame_state_direction(request, route_available=False)

        self.assertEqual(framed["current_reachability"]["status"], PATH_UNKNOWN_CURRENTLY)
        self.assertIn("fundamental impossibility", framed["current_reachability"]["does_not_claim"])
        self.assertEqual(framed["target_direction"]["source"], "direction")
        self.assertEqual(framed["target_direction"]["supplied_input_keys"], ["target"])

    def test_known_route_and_observed_constraint_are_distinct_states(self):
        request = {"kind": "example", "inputs": {}}
        available = frame_state_direction(request, route_available=True)
        blocked = frame_state_direction(
            request,
            route_available=False,
            current_constraint={"kind": "bounded-resource", "observed": "fixture-limit"},
        )

        self.assertEqual(available["current_reachability"]["status"], CURRENT_PATH_AVAILABLE)
        self.assertEqual(blocked["current_reachability"]["status"], BLOCKED_BY_CURRENT_CONSTRAINT)
        self.assertEqual(
            blocked["current_reachability"]["observed_constraint"],
            {"kind": "bounded-resource", "observed": "fixture-limit"},
        )

    def test_prompt_is_direction_source_not_literal_machine_code_claim(self):
        summary = state_direction_summary()
        relation = summary["prompt_relation"]

        self.assertEqual(relation["role"], "high-level state-direction source")
        self.assertIn("structured target properties", relation["may_compile_into"])
        self.assertIn("literal processor machine code", relation["not_claimed"])

    def test_framing_is_deterministic_and_has_zero_automatic_authority(self):
        request = {
            "kind": "example",
            "purpose": "preserve the same direction across repeated framing",
            "constraints": {"lossless": True, "maximum": 64},
            "inputs": {"b": 2, "a": 1},
        }
        first = frame_state_direction(request, route_available=False)
        second = frame_state_direction(request, route_available=False)

        self.assertEqual(first, second)
        self.assertEqual(json.dumps(first, sort_keys=True), json.dumps(second, sort_keys=True))
        self.assertFalse(any(first["authority_boundary"].values()))

    def test_existing_capability_gap_already_preserves_current_boundary_language(self):
        machine = UniversalCreationMachine(ROOT)
        gap = machine.create({
            "kind": "not-a-live-route-state-direction-test",
            "direction": "retain this requested direction while its path is unknown",
            "inputs": {},
        })

        self.assertEqual(gap["type"], "CAPABILITY_GAP")
        self.assertEqual(gap["truth_status"], "HYPOTHESIS")
        self.assertIn("smallest_missing_capability_currently_justified", gap)
        self.assertNotIn(
            "impossible",
            gap["smallest_missing_capability_currently_justified"].casefold(),
        )


if __name__ == "__main__":
    unittest.main()

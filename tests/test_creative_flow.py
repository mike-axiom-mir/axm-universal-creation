from __future__ import annotations

import shutil
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


@unittest.skipUnless(shutil.which("node"), "Creative Flow uses the local Platform Hands Node runtime")
class CreativeFlowMachineTests(unittest.TestCase):
    def test_live_capability_routes_multi_hand_flow(self):
        machine = UniversalCreationMachine(ROOT)
        manifest = machine.capabilities.route("creative-flow")
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["id"], "AXM-CAP-CREATIVE-FLOW-SPINE")

        result = machine.create({
            "kind": "creative-flow",
            "direction": "create a wider cube and inspect its exact bounds",
            "inputs": {
                "mode": "execute",
                "goal": "create a wider cube and inspect its exact bounds",
                "state": {"caller": "machine-test"},
                "steps": [
                    {
                        "id": "make",
                        "hand_id": "creative.mesh-primitive.cube",
                        "args": {"spec": {"id": "machine-flow-cube", "detail": 8}},
                        "save_as": "mesh",
                    },
                    {
                        "id": "scale",
                        "selector": {"family": "mesh-transform", "operation": "scale"},
                        "args": {"mesh": {"$state": "mesh"}, "vector": [2, 1, 1]},
                        "save_as": "scaled",
                    },
                    {
                        "id": "bounds",
                        "recipe_id": "mesh-analysis.bounds",
                        "args": {"mesh": {"$state": "scaled"}},
                        "save_as": "bounds",
                    },
                ],
                "expose": {"bounds": {"$state": "bounds"}},
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT")
        self.assertEqual(result["capability"], "AXM-CAP-CREATIVE-FLOW-SPINE")
        flow = result["result"]
        self.assertEqual(flow["status"], "PASS")
        self.assertTrue(flow["candidate_ready"])
        self.assertFalse(flow["source_state_mutated"])
        self.assertEqual(len(flow["receipts"]), 3)
        self.assertEqual(flow["outputs"]["bounds"]["size"], [4, 2, 2])

    def test_prose_goal_discovers_but_does_not_self_authorize_plan(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "creative-flow",
            "direction": "discover relevant creative hands",
            "inputs": {
                "mode": "plan",
                "goal": "sculpt and smooth a mesh surface",
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT")
        flow = result["result"]
        self.assertEqual(flow["status"], "HOLD_PLAN_REQUIRED")
        self.assertTrue(flow["discovery"]["matches"])

    def test_failed_step_does_not_publish_final_candidate_state(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "creative-flow",
            "inputs": {
                "mode": "execute",
                "state": {"caller": "source"},
                "steps": [
                    {
                        "id": "make",
                        "hand_id": "creative.mesh-primitive.cube",
                        "args": {"spec": {"id": "failure-cube", "detail": 8}},
                        "save_as": "mesh",
                    },
                    {
                        "id": "bad-scale",
                        "hand_id": "creative.mesh-transform.scale",
                        "args": {"mesh": {"$state": "mesh"}, "vector": [-1, 1, 1]},
                        "save_as": "scaled",
                    },
                ],
            },
        })
        flow = result["result"]
        self.assertEqual(flow["status"], "HOLD_EXECUTION_FAILED")
        self.assertFalse(flow["candidate_ready"])
        self.assertFalse(flow["source_state_mutated"])
        self.assertNotIn("final_state", flow)
        self.assertEqual(flow["failure"]["step_id"], "bad-scale")


if __name__ == "__main__":
    unittest.main()

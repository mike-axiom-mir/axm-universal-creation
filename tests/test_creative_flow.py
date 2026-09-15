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

    def test_adaptive_quality_plans_and_executes_through_same_machine_route(self):
        machine = UniversalCreationMachine(ROOT)
        goal = "Create an animated armored sci-fi supply crate game asset with editable materials and animation."
        planned = machine.create({
            "kind": "creative-flow",
            "direction": goal,
            "inputs": {
                "mode": "adaptive-plan",
                "goal": goal,
                "quality": 0.9,
                "machine": {"concurrency": 4},
            },
        })["result"]
        self.assertEqual(planned["status"], "READY")
        self.assertEqual(planned["profile_id"], "game-prop.armored-crate/v1")
        self.assertEqual(planned["requested_quality"], 0.9)
        self.assertEqual(planned["realized_quality"], 0.9)
        self.assertEqual(len(planned["execution_request"]["steps"]), 47)
        self.assertEqual(planned["schedule"]["parallel_runtime"], "PLANNED_NOT_EXECUTED")
        self.assertTrue(any(len(group["steps"]) > 1 for group in planned["schedule"]["groups"]))

        executed = machine.create({
            "kind": "creative-flow",
            "direction": goal,
            "inputs": {
                "mode": "adaptive-execute",
                "goal": goal,
                "quality": "game-ready",
                "machine": {"concurrency": 4},
            },
        })["result"]
        self.assertEqual(executed["status"], "PASS")
        self.assertTrue(executed["candidate_ready"])
        self.assertEqual(executed["realized_quality"], 0.45)
        self.assertEqual(len(executed["execution"]["receipts"]), 18)

    def test_maximum_quality_holds_or_explicitly_degrades_instead_of_overclaiming(self):
        goal = "Create a maximum quality animated armored sci-fi supply crate game asset."
        machine = UniversalCreationMachine(ROOT)
        held = machine.create({
            "kind": "creative-flow",
            "direction": goal,
            "inputs": {"mode": "adaptive-plan", "goal": goal, "quality": "maximum"},
        })["result"]
        self.assertEqual(held["status"], "HOLD_CAPABILITY_GAP")
        self.assertTrue(any(row["hand_id"] == "creative.mesh-model-finish.bevel" for row in held["missing_capabilities"]))

        degraded = machine.create({
            "kind": "creative-flow",
            "direction": goal,
            "inputs": {
                "mode": "adaptive-plan",
                "goal": goal,
                "quality": "maximum",
                "machine": {"allow_quality_degrade": True},
            },
        })["result"]
        self.assertEqual(degraded["status"], "READY_DEGRADED")
        self.assertLess(degraded["realized_quality"], 0.92)
        self.assertGreaterEqual(degraded["realized_quality"], 0.85)

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

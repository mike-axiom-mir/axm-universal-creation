from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.directions import SoftwareDirections
from axm_uc.machine import UniversalCreationMachine


class SoftwareDirectionTests(unittest.TestCase):
    def setUp(self):
        self.directions = SoftwareDirections(ROOT)

    def test_catalog_contains_all_donor_direction_profiles_and_axes(self):
        summary = self.directions.summary()
        self.assertEqual(summary["profiles"], 29)
        self.assertEqual(set(summary["axes"]), {"runtime", "execution", "state", "quality", "risk", "verification", "distribution"})
        self.assertEqual(sum(summary["families"].values()), 29)
        self.assertFalse(summary["automatic_selection"])
        self.assertTrue(summary["engineering_quality_and_risk_axes_are_not_axm_roots"])

    def test_rts_suggestions_are_candidates_not_selection(self):
        report = self.directions.suggest({"goals": ["Build a multiplayer RTS game with shared world state"]})
        ids = [row["direction_id"] for row in report["candidates"]]
        self.assertIn("game", ids)
        self.assertIn("collaboration-multiplayer", ids)
        self.assertFalse(report["automatic_selection"])
        self.assertTrue(all(row["candidate_is_selection"] is False for row in report["candidates"]))

    def test_explicit_game_multiplayer_stack_combines_needs_with_sources(self):
        stack = self.directions.compose({
            "direction_ids": ["game", "collaboration-multiplayer"],
            "verification": ["deterministic-replay"],
        })
        self.assertEqual(stack["result"], "DIRECTION_STACK_READY_NO_AUTHORITY")
        capability_ids = {row["id"] for row in stack["expectations"]["capabilities"]}
        self.assertIn("FRAME_LOOP", capability_ids)
        self.assertIn("WORLD_STATE_MODEL", capability_ids)
        self.assertIn("SHARED_STATE_PROTOCOL", capability_ids)
        replay = next(row for row in stack["expectations"]["verifiers"] if row["id"] == "deterministic-replay")
        self.assertIn("game", replay["source_directions"])
        self.assertIn("collaboration-multiplayer", replay["source_directions"])
        self.assertIn("EXPLICIT_AXIS", replay["source_directions"])
        self.assertFalse(stack["direction_is_authority"])
        self.assertFalse(stack["expectations_are_implementation_proof"])

    def test_suggestions_alone_do_not_enrich_anatomy(self):
        machine = UniversalCreationMachine(ROOT)
        plan = machine.plan({
            "kind": "software-project",
            "direction": "Build a multiplayer RTS game",
            "inputs": {"path": "creations/rts"},
        })
        self.assertEqual(plan["software_direction"]["stack"]["result"], "NO_EXPLICIT_DIRECTION_SELECTION")
        self.assertIsNone(plan["explicit_planning_context"])
        ids = [row["direction_id"] for row in plan["software_direction"]["suggestions"]["candidates"]]
        self.assertIn("game", ids)

    def test_explicit_direction_selection_enriches_anatomy_terms(self):
        machine = UniversalCreationMachine(ROOT)
        plan = machine.plan({
            "kind": "software-project",
            "direction": "Build a multiplayer RTS game",
            "software_directions": {
                "direction_ids": ["game", "collaboration-multiplayer"],
                "runtime": ["browser"],
                "distribution": ["local-file"],
            },
            "inputs": {"path": "creations/rts"},
        })
        stack = plan["software_direction"]["stack"]
        self.assertEqual(stack["result"], "DIRECTION_STACK_READY_NO_AUTHORITY")
        self.assertIsNotNone(plan["explicit_planning_context"])
        self.assertIn("frame", plan["request_terms"])
        self.assertIn("shared", plan["request_terms"])
        self.assertIn("protocol", plan["request_terms"])
        self.assertEqual(plan["method"]["extra_context_rule"], "only caller-selected planning context may enrich lexical terms; suggestions alone never do")

    def test_unknown_direction_is_visible_and_does_not_become_context(self):
        stack = self.directions.compose({"direction_ids": ["warp-potato"]})
        self.assertEqual(stack["result"], "UNKNOWN_DIRECTION")
        self.assertEqual(stack["unknown_directions"], ["warp-potato"])
        self.assertIsNone(self.directions.planning_context(stack))


if __name__ == "__main__":
    unittest.main()

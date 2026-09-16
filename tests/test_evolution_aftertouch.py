from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.evolution_aftertouch import (
    FINAL_EVIDENCE_LANES,
    ROUND_COUNT,
    advance_round,
    prepare_chamber,
    self_test_candidate,
)
from axm_uc.machine import UniversalCreationMachine


class EvolutionAftertouchTests(unittest.TestCase):
    @staticmethod
    def _judgements(chamber: dict) -> dict:
        current = chamber["rounds"][-1]
        tournament = current["tournament"]
        result = {}
        teams = tournament["team_generation"]["teams"]
        criteria = tournament["criteria"]
        for index, team in enumerate(teams):
            score = min(100, 50 + index * 5)
            result[team["team_id"]] = {
                "criteria": {
                    criterion["id"]: {
                        "score": score,
                        "evidence": f"independent fixture evidence round {current['round']} team {index}",
                    }
                    for criterion in criteria
                },
                "summary": f"fixture judgement {index}",
            }
        return result

    @staticmethod
    def _submissions(chamber: dict, *, final_all_pass: bool = False) -> dict:
        current = chamber["rounds"][-1]
        rows = {}
        for index, packet in enumerate(current["creative_packets"]):
            verification = []
            if final_all_pass and current["round"] == ROUND_COUNT:
                verification = [
                    {
                        "lane": lane,
                        "status": "PASS",
                        "evidence": f"fixture {lane} evidence {index}",
                        "source": "fixture-evidence-provider",
                    }
                    for lane in FINAL_EVIDENCE_LANES
                ]
            rows[packet["team_id"]] = {
                "parent_candidate_id": packet["parent_candidate_id"],
                "proposal": {
                    "artifact": {"kind": "generic", "round": current["round"], "team": packet["team_id"]},
                    "revision": f"candidate-{current['round']}-{index}",
                },
                "evidence": [f"concrete fixture evidence {current['round']}:{index}"],
                "verification": verification,
                "dissent": [],
                "unknowns": [],
            }
        return rows

    def test_live_machine_routes_seven_round_chamber(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "creative-evolution-chamber",
            "inputs": {
                "operation": "prepare",
                "challenge": "create a deeply polished gamepad asset and verify it before output",
                "pool_size": 8,
                "team_size": 3,
                "max_teams": 4,
                "seed": "aftertouch-route-test",
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        chamber = result["result"]
        self.assertEqual(chamber["round_count"], 7)
        self.assertEqual(chamber["survivor_count"], 2)
        self.assertEqual(len(chamber["rounds"][-1]["creative_packets"]), 4)
        self.assertFalse(chamber["policy"]["automatic_acceptance"])
        self.assertFalse(chamber["policy"]["perfect_claimed"])

    def test_each_completed_round_keeps_two_and_binds_them_into_next_round(self):
        chamber = prepare_chamber(
            ROOT,
            "evolve one creation through multiple creative teams",
            pool_size=8,
            team_size=3,
            max_teams=4,
            seed="two-survivor-test",
        )
        next_state = advance_round(ROOT, chamber, self._submissions(chamber), self._judgements(chamber))
        self.assertEqual(next_state["current_round"], 2)
        self.assertEqual(len(next_state["survivors"]), 2)
        survivor_ids = {row["candidate_id"] for row in next_state["survivors"]}
        packet_parent_ids = {row["parent_candidate_id"] for row in next_state["rounds"][-1]["creative_packets"]}
        self.assertEqual(packet_parent_ids, survivor_ids)
        self.assertEqual(next_state["rounds"][0]["status"], "ROUND_COMPLETE_TWO_SURVIVORS_RETAINED")

    def test_seven_rounds_retain_exactly_two_finalists_with_explicit_test_gaps(self):
        chamber = prepare_chamber(
            ROOT,
            "finish a creation only after repeated simulation observation repair and aftertouch",
            pool_size=8,
            team_size=3,
            max_teams=4,
            seed="seven-round-gap-test",
        )
        for _ in range(ROUND_COUNT):
            chamber = advance_round(ROOT, chamber, self._submissions(chamber), self._judgements(chamber))
        self.assertEqual(chamber["status"], "COMPLETE_TWO_FINALISTS_RETAINED")
        self.assertEqual(len(chamber["finalists"]), 2)
        self.assertEqual(chamber["final_gate"]["status"], "TWO_FINALISTS_RETAINED_WITH_EXPLICIT_TEST_GAPS")
        self.assertFalse(chamber["final_gate"]["output_ready_under_declared_gates"])
        self.assertFalse(chamber["policy"]["automatic_canon"])

    def test_deep_aftertouch_can_finish_with_all_declared_gates_pass_without_claiming_perfection(self):
        chamber = prepare_chamber(
            ROOT,
            "prove the final evidence gate shape",
            pool_size=8,
            team_size=3,
            max_teams=4,
            seed="seven-round-pass-test",
        )
        for _ in range(ROUND_COUNT):
            chamber = advance_round(
                ROOT,
                chamber,
                self._submissions(chamber, final_all_pass=True),
                self._judgements(chamber),
            )
        self.assertEqual(chamber["final_gate"]["status"], "TWO_FINALISTS_RETAINED_ALL_DECLARED_AFTERTOUCH_GATES_PASS")
        self.assertTrue(chamber["final_gate"]["output_ready_under_declared_gates"])
        self.assertFalse(chamber["policy"]["perfect_claimed"])
        self.assertTrue(all(candidate["accepted"] is False for candidate in chamber["finalists"]))

    def test_unsupported_candidate_kind_reports_not_tested_instead_of_inventing_success(self):
        result = self_test_candidate(ROOT, {"artifact": {"kind": "unknown-future-medium", "value": 1}})
        self.assertEqual(result["status"], "NOT_TESTED")
        self.assertEqual(result["verification"][0]["status"], "NOT_TESTED")
        self.assertFalse(result["perfect_claimed"])

    def test_visual_candidate_uses_existing_uc_simulator(self):
        result = self_test_candidate(
            ROOT,
            {
                "artifact": {
                    "kind": "visual-thought",
                    "thought": {
                        "intent": "simple aftertouch fixture",
                        "canvas": {"width": 100, "height": 100, "background": "#000000"},
                        "objects": [
                            {
                                "id": "panel",
                                "shape": {"kind": "rect", "x": 10, "y": 10, "width": 80, "height": 80},
                            }
                        ],
                    },
                    "palette": ["#FFFFFF"],
                    "criteria": {"fit_canvas": True, "minimum_contrast": 4.5},
                }
            },
        )
        self.assertEqual(result["adapter"], "uc-visual-simulation")
        self.assertIn(result["status"], {"PASS", "HOLD"})
        self.assertNotEqual(result["status"], "NOT_TESTED")
        self.assertFalse(result["perfect_claimed"])


if __name__ == "__main__":
    unittest.main()

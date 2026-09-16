from __future__ import annotations

import base64
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.aftertouch_preview import capture_candidate_preview, normalize_preview_policy
from axm_uc.machine import UniversalCreationMachine

PNG_1X1 = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Zr9sAAAAASUVORK5CYII="
)


class AftertouchPreviewTests(unittest.TestCase):
    def _root(self, parent: Path) -> Path:
        root = parent / "machine"
        registry = root / "reference/AXM_Universal_Creation_Map_v0.1/registry"
        registry.mkdir(parents=True)
        for name in ("master_registry.json", "core_build_seed.json"):
            shutil.copy2(
                ROOT / "reference/AXM_Universal_Creation_Map_v0.1/registry" / name,
                registry / name,
            )
        shutil.copytree(ROOT / "capabilities/live", root / "capabilities/live", dirs_exist_ok=True)
        return root

    @staticmethod
    def _judgements(chamber: dict) -> dict:
        current = chamber["rounds"][-1]
        criteria = current["tournament"]["criteria"]
        rows = {}
        for index, team in enumerate(current["tournament"]["team_generation"]["teams"]):
            rows[team["team_id"]] = {
                "criteria": {
                    criterion["id"]: {
                        "score": 60 + index,
                        "evidence": f"preview fixture evidence {index}:{criterion['id']}",
                    }
                    for criterion in criteria
                },
                "summary": f"preview fixture team {index}",
            }
        return rows

    @staticmethod
    def _submissions(chamber: dict, preview_path: Path) -> dict:
        current = chamber["rounds"][-1]
        return {
            packet["team_id"]: {
                "parent_candidate_id": packet["parent_candidate_id"],
                "proposal": {
                    "artifact": {
                        "kind": "3d-asset",
                        "preview_image_path": str(preview_path),
                    },
                    "revision": f"preview-round-{current['round']}-{index}",
                },
                "evidence": [f"candidate evidence {current['round']}:{index}"],
                "verification": [],
                "dissent": [],
                "unknowns": [],
            }
            for index, packet in enumerate(current["creative_packets"])
        }

    def test_default_policy_keeps_internal_machine_preview_and_ai_off(self):
        policy = normalize_preview_policy()
        self.assertEqual(policy["mode"], "internal")
        self.assertTrue(policy["machine_observation"])
        self.assertFalse(policy["ai_review"])
        self.assertEqual(policy["user_feedback_policy"], "never")
        self.assertEqual(normalize_preview_policy(policy), policy)

    def test_caller_preview_image_is_retained_and_bound_for_user_checkpoint(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "machine"
            source = root / "creations/source/preview.png"
            source.parent.mkdir(parents=True)
            source.write_bytes(PNG_1X1)
            candidate = {
                "candidate_id": "candidate-preview",
                "round": 2,
                "proposal": {"artifact": {"kind": "3d-asset", "preview_image_path": str(source)}},
            }
            receipt = capture_candidate_preview(
                root,
                candidate,
                round_number=2,
                policy={"mode": "user-every-round", "ai_review": True, "retain_artifacts": True},
            )
            self.assertEqual(receipt["status"], "CAPTURED")
            self.assertTrue(receipt["user_feedback_required"])
            self.assertTrue(receipt["review_audience"]["machine"])
            self.assertTrue(receipt["review_audience"]["ai"])
            self.assertTrue(receipt["review_audience"]["user"])
            self.assertEqual(len(receipt["artifacts"]), 1)
            retained = Path(receipt["artifacts"][0]["path"])
            self.assertTrue(retained.is_file())
            self.assertEqual(retained.read_bytes(), PNG_1X1)
            self.assertFalse(receipt["perceptual_quality_claimed"])

    def test_machine_prepare_exposes_user_selected_preview_policy(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            machine = UniversalCreationMachine(root)
            result = machine.create({
                "kind": "creative-evolution-chamber",
                "inputs": {
                    "operation": "prepare",
                    "challenge": "evolve a visual candidate with user preview checkpoints",
                    "pool_size": 8,
                    "team_size": 3,
                    "max_teams": 4,
                    "seed": "preview-policy-route",
                    "preview_policy": {
                        "mode": "user-milestones",
                        "milestone_rounds": [1, 4, 7],
                        "ai_review": False,
                        "retain_artifacts": True,
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            chamber = result["result"]
            self.assertEqual(chamber["preview_policy"]["mode"], "user-milestones")
            self.assertEqual(chamber["preview_policy"]["milestone_rounds"], [1, 4, 7])
            self.assertFalse(chamber["preview_policy"]["ai_review"])
            self.assertFalse(chamber["preview_state"]["pending_user_feedback"])

    def test_user_every_round_blocks_next_advance_until_both_preview_reviews_are_recorded(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._root(Path(td))
            preview = root / "creations/source/preview.png"
            preview.parent.mkdir(parents=True)
            preview.write_bytes(PNG_1X1)
            machine = UniversalCreationMachine(root)
            prepared_result = machine.create({
                "kind": "creative-evolution-chamber",
                "inputs": {
                    "operation": "prepare",
                    "challenge": "use intermediate visual checkpoints before further evolution",
                    "pool_size": 8,
                    "team_size": 3,
                    "max_teams": 4,
                    "seed": "preview-user-gate",
                    "preview_policy": {"mode": "user-every-round", "ai_review": False, "retain_artifacts": True},
                },
            })
            chamber = prepared_result["result"]
            advanced_result = machine.create({
                "kind": "creative-evolution-chamber",
                "inputs": {
                    "operation": "advance-round",
                    "chamber": chamber,
                    "submissions": self._submissions(chamber, preview),
                    "judgements": self._judgements(chamber),
                },
            })
            self.assertEqual(advanced_result["type"], "CREATION_RESULT", advanced_result)
            waiting = advanced_result["result"]
            self.assertEqual(waiting["status"], "ROUND_1_PREVIEW_AWAITING_USER_FEEDBACK")
            self.assertTrue(waiting["preview_state"]["pending_user_feedback"])
            self.assertEqual(len(waiting["survivors"]), 2)
            for survivor in waiting["survivors"]:
                checkpoint = survivor["preview_checkpoint"]
                self.assertEqual(checkpoint["status"], "CAPTURED")
                self.assertTrue(Path(checkpoint["artifacts"][0]["path"]).is_file())

            blocked = machine.create({
                "kind": "creative-evolution-chamber",
                "inputs": {
                    "operation": "advance-round",
                    "chamber": waiting,
                    "submissions": self._submissions(waiting, preview),
                    "judgements": self._judgements(waiting),
                },
            })
            self.assertEqual(blocked["type"], "CREATION_ERROR", blocked)
            self.assertIn("preview feedback", blocked["message"])

            feedback = {
                survivor["candidate_id"]: {
                    "reviewer": "user",
                    "observation": "preview checked before continuing",
                    "decision": "continue",
                    "requested_changes": [],
                }
                for survivor in waiting["survivors"]
            }
            reviewed = machine.create({
                "kind": "creative-evolution-chamber",
                "inputs": {
                    "operation": "record-preview-feedback",
                    "chamber": waiting,
                    "feedback": feedback,
                },
            })
            self.assertEqual(reviewed["type"], "CREATION_RESULT", reviewed)
            resumed = reviewed["result"]
            self.assertEqual(resumed["status"], "ROUND_2_READY")
            self.assertFalse(resumed["preview_state"]["pending_user_feedback"])
            contexts = [packet.get("preview_adjustment_context") for packet in resumed["rounds"][-1]["creative_packets"]]
            self.assertTrue(all(isinstance(row, dict) and row.get("review_status") == "CONTINUE" for row in contexts))


if __name__ == "__main__":
    unittest.main()

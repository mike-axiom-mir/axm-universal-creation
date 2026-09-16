from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.aftertouch_media_observers import media_self_test_candidate
from axm_uc.machine import UniversalCreationMachine


class _FakePoseAsset:
    source_sha256 = "f" * 64

    def describe(self):
        return {
            "schema": "axm.game-pose-asset/v0.1",
            "source_sha256": self.source_sha256,
            "nodes": [
                {"index": 0, "name": "Root", "parent": None},
                {"index": 1, "name": "Socket.Weapon", "parent": 0},
            ],
            "clips": [{"name": "Idle", "start_s": 0.0, "duration_s": 1.0, "channels": 1}],
            "skins": [{"joints": [0, 1]}],
            "primitives": 1,
            "vertices": 3,
            "truth": "fixture",
        }

    def sample(self, clip=None, time_s=0.0, *, loop=False, blend=None, vertices=False):
        offset = 0.0 if clip is None else float(time_s % 1.0 if loop else min(time_s, 1.0))
        result = {
            "schema": "axm.game-pose-sample/v0.1",
            "source_sha256": self.source_sha256,
            "clip": clip,
            "time_s": offset,
            "world_matrices": [
                [1, 0, 0, offset, 0, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1],
                [1, 0, 0, 1 + offset, 0, 1, 0, 2, 0, 0, 1, 3, 0, 0, 0, 1],
            ],
        }
        if vertices:
            result["meshes"] = [{"node": 0, "primitive": 0, "positions": [[offset, 0, 0], [1 + offset, 0, 0], [0, 1, 0]]}]
        return result

    def point(self, pose, node, position=(0.0, 0.0, 0.0)):
        matrix = pose["world_matrices"][node]
        return [matrix[3] + position[0], matrix[7] + position[1], matrix[11] + position[2]]


class AftertouchMediaObserverTests(unittest.TestCase):
    @staticmethod
    def _statuses(result: dict) -> dict[str, list[str]]:
        rows: dict[str, list[str]] = {}
        for item in result["verification"]:
            rows.setdefault(item["lane"], []).append(item["status"])
        return rows

    def test_glb_observer_uses_pose_skin_runtime_and_keeps_perceptual_gaps_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            glb = Path(td) / "weapon.glb"
            glb.write_bytes(b"fixture")
            with patch("axm_uc.aftertouch_media_observers.load_game_pose_glb", return_value=_FakePoseAsset()):
                result = media_self_test_candidate(
                    ROOT,
                    {
                        "artifact": {
                            "kind": "3d-asset",
                            "path": str(glb),
                            "animation_expected": True,
                            "required_sockets": ["Socket.Weapon"],
                        }
                    },
                )
        self.assertEqual(result["adapter"], "uc-glb-pose-observer")
        statuses = self._statuses(result)
        self.assertIn("PASS", statuses["structural"])
        self.assertIn("PASS", statuses["functional"])
        self.assertIn("PASS", statuses["context"])
        self.assertIn("PASS", statuses["adversarial"])
        self.assertEqual(statuses["visual"], ["NOT_TESTED"])
        self.assertEqual(statuses["experience"], ["NOT_TESTED"])
        self.assertFalse(result["perfect_claimed"])
        self.assertGreater(result["max_sampled_node_displacement"], 0)

    def test_game_without_browser_does_not_promote_file_validation_to_playability(self):
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "game"
            project.mkdir()
            (project / "index.html").write_text("<button id='sessionButton'>Start</button>", encoding="utf-8")
            with patch("axm_uc.aftertouch_media_observers.validate_project", return_value={"passed": True}):
                result = media_self_test_candidate(ROOT, {"artifact": {"kind": "game", "path": str(project)}})
        self.assertEqual(result["adapter"], "uc-playable-game-observer")
        self.assertEqual(result["status"], "HOLD")
        statuses = self._statuses(result)
        self.assertEqual(statuses["structural"], ["PASS"])
        self.assertEqual(statuses["functional"], ["NOT_TESTED"])
        self.assertEqual(statuses["experience"], ["NOT_TESTED"])

    def test_game_browser_observer_collects_runtime_interaction_reset_and_screenshot_evidence(self):
        def fake_capture(**kwargs):
            output = Path(kwargs["output_value"])
            output.mkdir(parents=True)
            (output / "game.png").write_bytes(b"png")
            (output / "game.runtime.json").write_text(
                json.dumps({"schema": "axm.browser-runtime-probe/v0.1", "runtime_error_count": 0}), encoding="utf-8"
            )
            (output / "game.interaction.json").write_text(
                json.dumps({
                    "schema": "axm.browser-interaction-probe/v0.1",
                    "requested_recipe_count": 2,
                    "completed_recipe_count": 2,
                    "interaction_error_count": 0,
                    "recipes": [
                        {"id": "primary-game-controls", "status": "PASS", "steps": []},
                        {"id": "reset-recovery", "status": "PASS", "steps": []},
                    ],
                }), encoding="utf-8"
            )
            return {
                "observation": {
                    "captures": [{
                        "measurements": {"horizontal_overflow": False, "interaction_error_count": 0},
                        "artifacts": [{"kind": "screenshot", "uri": "game.png", "bytes": 3}],
                    }]
                }
            }

        html = """<!doctype html><html><body>
        <button id='sessionButton'>Start</button><button id='fireButton'>Fire</button>
        <button id='targetButton'>Target</button><button id='reloadButton'>Reload</button>
        <button id='resetButton'>Reset</button></body></html>"""
        with tempfile.TemporaryDirectory() as td:
            project = Path(td) / "game"
            project.mkdir()
            (project / "index.html").write_text(html, encoding="utf-8")
            with patch("axm_uc.aftertouch_media_observers.validate_project", return_value={"passed": True}), patch(
                "axm_uc.aftertouch_media_observers.capture_local_browser", side_effect=fake_capture
            ):
                result = media_self_test_candidate(
                    ROOT,
                    {
                        "artifact": {
                            "kind": "browser-game",
                            "path": str(project),
                            "browser_executable": "fixture-chromium",
                            "allow_synthetic_activation": True,
                        }
                    },
                )
        statuses = self._statuses(result)
        self.assertEqual(statuses["functional"], ["PASS"])
        self.assertEqual(statuses["experience"], ["PASS"])
        self.assertEqual(statuses["context"], ["PASS"])
        self.assertEqual(statuses["adversarial"], ["PASS"])
        self.assertEqual(statuses["visual"], ["HOLD"])
        self.assertEqual(statuses["polish"], ["NOT_TESTED"])
        self.assertEqual(result["status"], "HOLD")
        self.assertFalse(result["perfect_claimed"])

    def test_live_chamber_route_prefers_media_observer_before_generic_fallback(self):
        with tempfile.TemporaryDirectory() as td:
            glb = Path(td) / "asset.glb"
            glb.write_bytes(b"fixture")
            with patch("axm_uc.aftertouch_media_observers.load_game_pose_glb", return_value=_FakePoseAsset()):
                result = UniversalCreationMachine(ROOT).create({
                    "kind": "creative-evolution-chamber",
                    "inputs": {
                        "operation": "self-test-candidate",
                        "candidate": {"artifact": {"kind": "3d-asset", "path": str(glb)}},
                    },
                })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertEqual(result["result"]["adapter"], "uc-glb-pose-observer")

    def test_non_media_kind_returns_none_for_existing_aftertouch_fallback(self):
        self.assertIsNone(media_self_test_candidate(ROOT, {"artifact": {"kind": "software", "path": "/tmp/example"}}))


if __name__ == "__main__":
    unittest.main()

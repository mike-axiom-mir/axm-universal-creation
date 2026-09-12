from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path


import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


def game_spec() -> dict:
    return {
        "schema": "axm.browser-arena/v0.1",
        "id": "command-tower-arena",
        "title": "Command Tower: Hostile Parent",
        "viewport": {"width": 960, "height": 540},
        "theme": {
            "background": "#05090F",
            "ground": "#12383B",
            "panel": "#07151A",
            "accent": "#37E4D5",
            "danger": "#FF365E",
            "text": "#F4F7F8",
        },
        "player": {"x": 480, "y": 450, "size": 18, "color": "#FFC857", "speed": 250, "max_health": 100},
        "tower": {"x": 405, "y": 245, "width": 150, "height": 105, "color": "#19A7A1", "max_health": 300},
        "enemies": [
            {"id": "hostile-parent", "label": "Hostile Parent", "x": 480, "y": 105, "size": 42, "color": "#FF365E", "health": 120, "speed": 24, "damage": 18, "reward": 500},
            {"id": "scout-left", "label": "Left Scout", "x": 180, "y": 170, "size": 28, "color": "#F05D7A", "health": 50, "speed": 34, "damage": 8, "reward": 100},
            {"id": "scout-right", "label": "Right Scout", "x": 780, "y": 170, "size": 28, "color": "#F05D7A", "health": 50, "speed": 34, "damage": 8, "reward": 100},
        ],
        "rules": {
            "projectile_speed": 620,
            "projectile_damage": 25,
            "fire_cooldown_ms": 180,
            "ammo_capacity": 30,
            "reload_ms": 1400,
            "contact_distance": 72,
        },
    }


def request(target: Path, specification: dict | None = None) -> dict:
    return {
        "kind": "offline-browser-game",
        "direction": "create a local tactical arena inspired only by visible reference cues",
        "inputs": {"path": str(target), "specification": specification or game_spec()},
    }


class BrowserGameTests(unittest.TestCase):
    def test_builds_dependency_free_validated_game_source_and_generated_assets(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "arena"
            result = UniversalCreationMachine(ROOT).create(request(target))
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            created = result["result"]
            self.assertEqual(created["truth_status"], "VALIDATED_OFFLINE_BROWSER_GAME_SOURCE_PROJECT")
            self.assertTrue(created["validation"]["passed"], created)
            self.assertFalse(created["browser_execution_observed"])
            self.assertEqual(created["runtime_dependencies"], [])
            self.assertEqual(
                {row["path"] for row in created["files"]},
                {
                    "README.md",
                    "assets/fire.wav",
                    "assets/target.png",
                    "game.js",
                    "game.json",
                    "index.html",
                    "state-machine.json",
                    "style.css",
                },
            )
            self.assertTrue((target / "assets/target.png").read_bytes().startswith(b"\x89PNG\r\n\x1a\n"))
            self.assertEqual((target / "assets/fire.wav").read_bytes()[:4], b"RIFF")
            self.assertNotIn("https://", (target / "index.html").read_text(encoding="utf-8"))
            self.assertNotIn("http://", (target / "game.js").read_text(encoding="utf-8"))
            self.assertIn(game_spec()["theme"]["panel"], (target / "style.css").read_text(encoding="utf-8"))

    def test_two_builds_have_identical_files_and_compiled_state_graph(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            machine = UniversalCreationMachine(ROOT)
            first = machine.create(request(base / "first"))["result"]
            second = machine.create(request(base / "second"))["result"]
            self.assertEqual(first["game_specification_digest"], second["game_specification_digest"])
            self.assertEqual(first["session_machine_digest"], second["session_machine_digest"])
            self.assertEqual(first["files"], second["files"])
            state = json.loads((base / "first/state-machine.json").read_text(encoding="utf-8"))
            self.assertEqual(state["states"], ["ready", "playing", "paused", "won", "lost"])
            self.assertIn(first["session_machine_digest"], (base / "first/game.js").read_text(encoding="utf-8"))

    def test_trial_independently_reverifies_the_complete_game_body(self):
        with tempfile.TemporaryDirectory() as td:
            trial = UniversalCreationMachine(ROOT).trial(request(Path(td) / "trial"))
            self.assertTrue(trial["passed"], trial)
            verification = trial["verification"]["result"]
            digest_check = next(row for row in verification["checks"] if row["type"] == "expected-file-digests")
            self.assertTrue(digest_check["passed"])
            self.assertEqual(len(digest_check["files"]), 8)
            self.assertIn("browser", " ".join(trial["limitations"]))

    def test_invalid_specification_holds_before_replacing_an_existing_creation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "arena"
            target.mkdir()
            sentinel = target / "keep.txt"
            sentinel.write_text("previous body\n", encoding="utf-8")
            invalid = game_spec()
            invalid["enemies"].append(dict(invalid["enemies"][0]))
            bad_request = request(target, invalid)
            bad_request["inputs"]["replace"] = True
            result = UniversalCreationMachine(ROOT).create(bad_request)
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("unique", result["message"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "previous body\n")
            self.assertEqual([path.name for path in target.iterdir()], ["keep.txt"])

    def test_required_inputs_and_optional_types_are_strict(self):
        machine = UniversalCreationMachine(ROOT)
        gap = machine.create({"kind": "browser-game-project", "inputs": {"path": "creations/not-built"}})
        self.assertEqual(gap["type"], "CAPABILITY_INPUT_GAP", gap)
        self.assertEqual(gap["missing_required_inputs"], ["specification"])
        invalid = machine.create(
            {
                "kind": "browser-game-project",
                "inputs": {
                    "path": "creations/not-built",
                    "specification": game_spec(),
                    "checks": "none",
                },
            }
        )
        self.assertEqual(invalid["type"], "CREATION_ERROR", invalid)
        self.assertIn("list", invalid["message"])


if __name__ == "__main__":
    unittest.main()

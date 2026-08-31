from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.paintgun import PAINT_CHANNELS, thought_digest


class SimulationToRealityTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    @staticmethod
    def _rough_thought() -> dict:
        return {
            "intent": "A glossy simulated panel that should become a real local visual artifact only after known improvements are exhausted.",
            "canvas": {"width": 640, "height": 360, "background": "#101010"},
            "objects": [
                {
                    "id": "panel",
                    "shape": {"kind": "rect", "x": -40, "y": 24, "width": 760, "height": 300, "rx": 28},
                    "material": {
                        "name": "experimental-glass-metal",
                        "metallic": 1.4,
                        "roughness": -0.2,
                        "opacity": 1.2,
                        "emission": 0.2
                    },
                    "color": {"fill": "#111111", "stroke": "#111111", "stroke_width": 2}
                }
            ]
        }

    def _simulate(self, thought: dict | None = None) -> dict:
        result = self.machine.create({
            "kind": "simulate-creation",
            "inputs": {
                "thought": thought or self._rough_thought(),
                "palette": ["#111111", "#FFFFFF", "#00E5FF"],
                "criteria": {"fit_canvas": True, "minimum_contrast": 4.5},
                "max_iterations": 8
            }
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        return result["result"]

    def test_simulation_improves_until_no_registered_rule_finds_more(self):
        simulation = self._simulate()
        self.assertEqual(simulation["status"], "NO_KNOWN_IMPROVEMENTS")
        self.assertFalse(simulation["perfect_claimed"])
        self.assertTrue(simulation["materialization_ready"])
        self.assertGreaterEqual(simulation["iterations"], 2)
        panel = simulation["thought"]["objects"][0]
        self.assertEqual(set(PAINT_CHANNELS) - set(panel), set())
        self.assertEqual(panel["shape"]["x"], 0)
        self.assertEqual(panel["shape"]["width"], 640)
        self.assertEqual(panel["material"]["metallic"], 1)
        self.assertEqual(panel["material"]["roughness"], 0)
        self.assertEqual(panel["material"]["opacity"], 1)
        self.assertEqual(panel["color"]["fill"], "#FFFFFF")
        self.assertTrue(simulation["cinematic_projection"]["available"])
        self.assertIn("AXM simulated visual thought", simulation["cinematic_projection"]["svg"])
        first_rules = {
            row["rule"]
            for row in simulation["history"][0]["improvements"]
        }
        self.assertIn("derive-neutral-surface-channels", first_rules)
        self.assertIn("fit-known-shapes-inside-canvas", first_rules)
        self.assertIn("choose-higher-contrast-known-color", first_rules)

    def test_same_thought_reaches_same_digest_and_cinematic_projection(self):
        first = self._simulate()
        second = self._simulate()
        self.assertEqual(first["thought_digest"], second["thought_digest"])
        self.assertEqual(first["thought"], second["thought"])
        self.assertEqual(first["cinematic_projection"], second["cinematic_projection"])
        self.assertEqual(first["history"], second["history"])

    def test_paintgun_pulls_exact_simulated_scene_into_reality(self):
        simulation = self._simulate()
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "materialized-thought"
            result = self.machine.create({
                "kind": "materialize-simulated-thought",
                "inputs": {"path": str(target), "simulation": simulation}
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            materialized = result["result"]
            self.assertTrue(materialized["cinematic_projection_equal_to_materialized_scene"])
            self.assertEqual(materialized["thought_digest"], simulation["thought_digest"])
            self.assertEqual(
                (target / "scene.svg").read_text(encoding="utf-8"),
                simulation["cinematic_projection"]["svg"]
            )
            stored_thought = json.loads((target / "thought.json").read_text(encoding="utf-8"))
            self.assertEqual(stored_thought, simulation["thought"])
            self.assertEqual(thought_digest(stored_thought), simulation["thought_digest"])
            self.assertTrue(materialized["project"]["validation"]["passed"])

    def test_tampered_thought_cannot_cross_simulation_reality_boundary(self):
        simulation = self._simulate()
        tampered = copy.deepcopy(simulation)
        tampered["thought"]["objects"][0]["color"]["fill"] = "#FF0000"
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "must-not-exist"
            result = self.machine.create({
                "kind": "materialize-simulated-thought",
                "inputs": {"path": str(target), "simulation": tampered}
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("digest", result["message"])
            self.assertFalse(target.exists())

    def test_missing_shape_stays_known_gap_instead_of_becoming_fake_completion(self):
        thought = self._rough_thought()
        del thought["objects"][0]["shape"]
        simulation = self._simulate(thought)
        self.assertEqual(simulation["status"], "HOLD_KNOWN_GAPS_NO_AVAILABLE_IMPROVEMENT")
        self.assertFalse(simulation["materialization_ready"])
        self.assertTrue(any(
            gap["channel"] == "shape" and gap["known_improvement_available"] is False
            for gap in simulation["known_gaps"]
        ))
        with tempfile.TemporaryDirectory() as td:
            result = self.machine.create({
                "kind": "materialize-simulated-thought",
                "inputs": {"path": str(Path(td) / "blocked"), "simulation": simulation}
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("NO_KNOWN_IMPROVEMENTS", result["message"])

    def test_paintgun_keeps_material_vocabulary_open_while_channels_remain_explicit(self):
        thought = {
            "intent": "Use a material name the kernel has never seen without collapsing the explicit surface channels.",
            "canvas": {"width": 320, "height": 180, "background": "#000000"},
            "objects": [
                {
                    "id": "orb",
                    "shape": {"kind": "circle", "cx": 160, "cy": 90, "r": 60},
                    "material": {"name": "liquid-starship-ceramic", "metallic": 0.7, "roughness": 0.15, "opacity": 0.92, "emission": 0.8},
                    "color": {"fill": "#7C4DFF", "stroke": "#EDE7F6", "stroke_width": 3},
                    "light": {"color": "#B3E5FC", "intensity": 1.4, "x": 80, "y": 40, "radius": 120},
                    "shade": {"color": "#000000", "dx": 8, "dy": 12, "blur": 18, "opacity": 0.6},
                    "skin": {"kind": "radial-gradient", "colors": ["#FFFFFF", "#7C4DFF", "#1A237E"], "angle": 0}
                }
            ]
        }
        simulation = self._simulate(thought)
        self.assertEqual(simulation["status"], "NO_KNOWN_IMPROVEMENTS")
        self.assertEqual(simulation["thought"]["objects"][0]["material"]["name"], "liquid-starship-ceramic")
        self.assertIn('data-material="liquid-starship-ceramic"', simulation["cinematic_projection"]["svg"])

    def test_malformed_empty_skin_stays_on_typed_hold(self):
        thought = self._rough_thought()
        thought["objects"][0]["color"] = {"fill": "#FFFFFF", "stroke": "#FFFFFF", "stroke_width": 2}
        thought["objects"][0]["skin"] = {"kind": "solid", "colors": [], "angle": 0}
        simulation = self._simulate(thought)
        self.assertEqual(simulation["status"], "HOLD_SIMULATION_STATE_NOT_MATERIALIZABLE")
        self.assertFalse(simulation["materialization_ready"])
        self.assertTrue(any(
            gap["type"] == "paintgun-validation"
            for gap in simulation["known_gaps"]
        ))

    def test_fake_complete_simulation_with_missing_channel_is_rejected_by_specialist(self):
        simulation = self._simulate()
        fake = copy.deepcopy(simulation)
        del fake["thought"]["objects"][0]["light"]
        fake["thought_digest"] = thought_digest(fake["thought"])
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "fake"
            result = self.machine.create({
                "kind": "paintgun-visual-project",
                "inputs": {"path": str(target), "simulation": fake}
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("composition-complete", result["message"])
            self.assertFalse(target.exists())


if __name__ == "__main__":
    unittest.main()

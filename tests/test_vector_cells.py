from __future__ import annotations

import copy
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


def painted(local_id: str, shape: dict, fill: str, *, material: str = "adaptive-metal") -> dict:
    return {
        "id": local_id,
        "shape": shape,
        "material": {"name": material, "metallic": 0.7, "roughness": 0.2, "opacity": 1, "emission": 0.15},
        "color": {"fill": fill, "stroke": "#E0F7FA", "stroke_width": 2},
        "light": {"color": "#80DEEA", "intensity": 0.8, "x": 40, "y": 20, "radius": 100},
        "shade": {"color": "#000000", "dx": 4, "dy": 6, "blur": 10, "opacity": 0.45},
        "skin": {"kind": "linear-gradient", "colors": [fill, "#263238"], "angle": 35},
    }


class VectorCellFabricTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    @staticmethod
    def fabric() -> dict:
        return {
            "intent": "One stable panel cell that merges detail when far away and unfolds its child cells when inspected closely.",
            "canvas": {"width": 360, "height": 180, "background": "#080B10"},
            "cells": [{
                "id": "panel",
                "role": "adaptive-control-panel",
                "transform": {"x": 40, "y": 30, "scale": 1},
                "representations": [
                    {
                        "id": "far-merged",
                        "min_scale": 0,
                        "max_scale": 0.75,
                        "mode": "expression",
                        "objects": [painted("merged", {"kind": "rect", "x": 0, "y": 0, "width": 260, "height": 110, "rx": 20}, "#1565C0")],
                    },
                    {
                        "id": "medium",
                        "min_scale": 0.75,
                        "max_scale": 2,
                        "mode": "expression",
                        "objects": [painted("body", {"kind": "rect", "x": 0, "y": 0, "width": 260, "height": 110, "rx": 18}, "#00838F")],
                    },
                    {
                        "id": "medium-selected",
                        "min_scale": 0.75,
                        "max_scale": 2,
                        "choices": ["selected"],
                        "mode": "expression",
                        "objects": [painted("body", {"kind": "rect", "x": 0, "y": 0, "width": 260, "height": 110, "rx": 18}, "#7C4DFF")],
                    },
                    {"id": "close-split", "min_scale": 2, "mode": "children"},
                ],
                "children": [
                    {
                        "id": "left-module",
                        "role": "detail-cell",
                        "transform": {"x": 10, "y": 12, "scale": 1},
                        "representations": [{
                            "id": "detail",
                            "min_scale": 0,
                            "mode": "expression",
                            "objects": [painted("left", {"kind": "rect", "x": 0, "y": 0, "width": 105, "height": 82, "rx": 12}, "#00ACC1")],
                        }],
                    },
                    {
                        "id": "right-module",
                        "role": "detail-cell",
                        "transform": {"x": 140, "y": 12, "scale": 1},
                        "representations": [{
                            "id": "detail",
                            "min_scale": 0,
                            "mode": "expression",
                            "objects": [painted("right", {"kind": "rect", "x": 0, "y": 0, "width": 105, "height": 82, "rx": 12}, "#26A69A")],
                        }],
                    },
                ],
            }],
        }

    def resolve(self, scale: float, choice: str = "default", fabric: dict | None = None) -> dict:
        result = self.machine.create({
            "kind": "resolve-vector-cells",
            "inputs": {
                "operation": "resolve-vector-cells",
                "fabric": fabric or self.fabric(),
                "observation_scale": scale,
                "choice": choice,
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        return result["result"]

    def test_same_cell_merges_far_and_splits_close(self):
        far = self.resolve(0.5)
        close = self.resolve(3)
        self.assertEqual(far["fabric_digest"], close["fabric_digest"])
        self.assertEqual(far["resolution"][0]["cell_id"], "panel")
        self.assertEqual(close["resolution"][0]["cell_id"], "panel")
        self.assertEqual(far["resolution"][0]["representation_id"], "far-merged")
        self.assertEqual(close["resolution"][0]["representation_id"], "close-split")
        self.assertEqual(far["stats"]["merged_child_cells"], 2)
        self.assertEqual(far["stats"]["resolved_objects"], 1)
        self.assertEqual(close["stats"]["split_child_cells"], 2)
        self.assertEqual(close["stats"]["resolved_objects"], 2)
        self.assertEqual(len(far["thought"]["objects"]), 1)
        self.assertEqual(len(close["thought"]["objects"]), 2)
        self.assertNotEqual(far["thought_digest"], close["thought_digest"])

    def test_choice_changes_expression_without_changing_cell_identity(self):
        normal = self.resolve(1)
        selected = self.resolve(1, "selected")
        self.assertEqual(normal["fabric_digest"], selected["fabric_digest"])
        self.assertEqual(normal["resolution"][0]["cell_id"], selected["resolution"][0]["cell_id"])
        self.assertEqual(normal["resolution"][0]["representation_id"], "medium")
        self.assertEqual(selected["resolution"][0]["representation_id"], "medium-selected")
        self.assertEqual(normal["thought"]["objects"][0]["color"]["fill"], "#00838F")
        self.assertEqual(selected["thought"]["objects"][0]["color"]["fill"], "#7C4DFF")
        self.assertNotEqual(normal["thought_digest"], selected["thought_digest"])

    def test_resolution_is_deterministic_for_same_scale_and_choice(self):
        first = self.resolve(3)
        second = self.resolve(3)
        self.assertEqual(first, second)

    def test_ambiguous_scale_state_holds_instead_of_guessing(self):
        fabric = self.fabric()
        duplicate = copy.deepcopy(fabric["cells"][0]["representations"][0])
        duplicate["id"] = "far-also"
        fabric["cells"][0]["representations"].append(duplicate)
        result = self.machine.create({
            "kind": "resolve-vector-cells",
            "inputs": {"fabric": fabric, "observation_scale": 0.5},
        })
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertIn("exactly one representation", result["message"])

    def test_duplicate_cell_identity_is_rejected(self):
        fabric = self.fabric()
        fabric["cells"][0]["children"][1]["id"] = "left-module"
        result = self.machine.create({
            "kind": "adaptive-vector-scene",
            "inputs": {"fabric": fabric, "observation_scale": 3},
        })
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertIn("globally unique", result["message"])

    def test_resolved_cells_flow_through_simulation_and_paintgun(self):
        vector = self.resolve(3)
        simulated = self.machine.create({
            "kind": "simulate-creation",
            "inputs": {"thought": vector["simulation_input"]["thought"], "max_iterations": 4},
        })
        self.assertEqual(simulated["type"], "CREATION_RESULT", simulated)
        simulation = simulated["result"]
        self.assertEqual(simulation["status"], "NO_KNOWN_IMPROVEMENTS")
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "vector-cell-reality"
            built = self.machine.create({
                "kind": "materialize-simulated-thought",
                "inputs": {"path": str(target), "simulation": simulation},
            })
            self.assertEqual(built["type"], "CREATION_RESULT", built)
            self.assertTrue(built["result"]["cinematic_projection_equal_to_materialized_scene"])
            self.assertEqual(
                (target / "scene.svg").read_text(encoding="utf-8"),
                simulation["cinematic_projection"]["svg"],
            )


if __name__ == "__main__":
    unittest.main()

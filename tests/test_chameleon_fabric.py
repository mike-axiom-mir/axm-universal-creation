from __future__ import annotations

import math
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.chameleon import inspect_calibrations, record_calibration
from axm_uc.machine import UniversalCreationMachine


def painted(local_id: str, shape: dict, fill: str, *, roughness: float = 0.2) -> dict:
    return {
        "id": local_id,
        "shape": shape,
        "material": {"name": "adaptive-surface", "metallic": 0.5, "roughness": roughness, "opacity": 1, "emission": 0.1},
        "color": {"fill": fill, "stroke": fill, "stroke_width": 2},
        "light": {"color": "#FFFFFF", "intensity": 0.4, "x": 20, "y": 20, "radius": 80},
        "shade": {"color": "#000000", "dx": 2, "dy": 3, "blur": 6, "opacity": 0.3},
        "skin": {"kind": "linear-gradient", "colors": [fill, "#202020"], "angle": 20},
    }


def thought(fill: str = "#204060", *, x: float = 10, roughness: float = 0.2, shape_kind: str = "rect") -> dict:
    shape = {"kind": "rect", "x": x, "y": 10, "width": 80, "height": 40, "rx": 8}
    if shape_kind == "circle":
        shape = {"kind": "circle", "cx": x + 40, "cy": 30, "r": 20}
    return {
        "intent": "bounded chameleon fixture",
        "canvas": {"width": 180, "height": 100, "background": "#000000"},
        "camera": {"x": 0, "y": 0, "zoom": 1},
        "objects": [painted("body", shape, fill, roughness=roughness)],
    }


def fabric() -> dict:
    return {
        "intent": "one body with calm and alert states",
        "canvas": {"width": 180, "height": 100, "background": "#000000"},
        "cells": [{
            "id": "body-cell",
            "role": "chameleon-body",
            "representations": [
                {
                    "id": "calm",
                    "min_scale": 0,
                    "mode": "expression",
                    "objects": [painted("body", {"kind": "rect", "x": 10, "y": 10, "width": 80, "height": 40, "rx": 8}, "#204060")],
                },
                {
                    "id": "alert",
                    "min_scale": 0,
                    "choices": ["alert"],
                    "mode": "expression",
                    "objects": [painted("body", {"kind": "rect", "x": 50, "y": 20, "width": 100, "height": 60, "rx": 18}, "#D05020", roughness=0.6)],
                },
            ],
        }],
    }


class ChameleonFabricTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    def _create(self, operation: str, **inputs):
        result = self.machine.create({
            "kind": "chameleon-fabric",
            "inputs": {"operation": operation, **inputs},
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        return result["result"]

    def _simulation(self, raw_thought: dict | None = None) -> dict:
        result = self.machine.create({
            "kind": "simulate-creation",
            "inputs": {"thought": raw_thought or thought(), "max_iterations": 4},
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertEqual(result["result"]["status"], "NO_KNOWN_IMPROVEMENTS", result)
        return result["result"]

    def test_machine_routes_chameleon_fabric(self):
        compiled = self._create(
            "compile-material-graph",
            material_graph={"id": "route-proof", "base_color": "#336699"},
        )
        self.assertEqual(compiled["schema"], "axm.material-graph/v0.1")
        self.assertEqual(compiled["truth_status"], "RICH_MATERIAL_GRAPH_COMPILED_TO_CURRENT_PAINTGUN_APPROXIMATION")

    def test_compatible_shape_morph_interpolates_geometry_color_and_material(self):
        result = self._create(
            "morph-thoughts",
            from_thought=thought("#000000", x=10, roughness=0.2),
            to_thought=thought("#FFFFFF", x=50, roughness=0.6),
            factor=0.5,
        )
        obj = result["thought"]["objects"][0]
        self.assertEqual(result["morph_trace"][0]["mode"], "continuous-channel-and-geometry-interpolation")
        self.assertAlmostEqual(obj["shape"]["x"], 30)
        self.assertEqual(obj["color"]["fill"], "#808080")
        self.assertAlmostEqual(obj["material"]["roughness"], 0.4)

    def test_incompatible_geometry_crossfades_instead_of_claiming_deformation(self):
        result = self._create(
            "continuous-morph",
            from_thought=thought("#204060", shape_kind="rect"),
            to_thought=thought("#D05020", shape_kind="circle"),
            factor=0.25,
        )
        self.assertEqual(result["morph_trace"][0]["mode"], "continuous-crossfade-incompatible-geometry")
        self.assertEqual(len(result["thought"]["objects"]), 2)
        opacities = sorted(obj["material"]["opacity"] for obj in result["thought"]["objects"])
        self.assertEqual(opacities, [0.25, 0.75])

    def test_vector_cell_states_morph_without_losing_fabric_lineage(self):
        result = self._create(
            "morph-vector-cells",
            fabric=fabric(),
            from_state={"observation_scale": 1, "choice": "default"},
            to_state={"observation_scale": 1, "choice": "alert"},
            factor=0.5,
        )
        self.assertEqual(result["from_resolution"][0]["cell_id"], "body-cell")
        self.assertEqual(result["to_resolution"][0]["cell_id"], "body-cell")
        self.assertEqual(result["from_resolution"][0]["representation_id"], "calm")
        self.assertEqual(result["to_resolution"][0]["representation_id"], "alert")
        self.assertEqual(result["thought"]["objects"][0]["id"], "body-cell::body")

    def test_rich_material_graph_retains_unrendered_truth_and_bounded_approximation(self):
        compiled = self._create(
            "compile-material-graph",
            material_graph={
                "id": "adaptive-skin",
                "name": "adaptive translucent scales",
                "base_color": "#336699",
                "secondary_color": "#99CCFF",
                "metallic": 0.25,
                "roughness": 0.7,
                "transmission": 0.6,
                "ior": 1.45,
                "clearcoat": 0.8,
                "anisotropy": 0.4,
                "subsurface": 0.3,
                "normal_strength": 1.5,
                "displacement": 0.4,
                "microstructure": {"kind": "scales", "scale": 8, "strength": 1.2, "seed": 42},
            },
        )
        material = compiled["material"]
        self.assertEqual(material["transmission"], 0.6)
        self.assertEqual(material["ior"], 1.45)
        self.assertEqual(material["anisotropy"], 0.4)
        self.assertEqual(material["subsurface"], 0.3)
        self.assertEqual(compiled["skin"]["kind"], "radial-gradient")
        self.assertTrue(any(row["source"] == "normal_strength" and "metadata-only" in row["rendered_as"] for row in compiled["render_approximation"]))

    def test_rich_material_applies_to_paintgun_thought_and_stays_simulatable(self):
        applied = self._create(
            "apply-material-graph",
            thought=thought(),
            object_id="body",
            material_graph={
                "id": "fibrous",
                "base_color": "#704020",
                "secondary_color": "#D0A060",
                "normal_strength": 1.1,
                "microstructure": {"kind": "fibers", "angle": 55, "strength": 0.8},
            },
        )
        obj = applied["thought"]["objects"][0]
        self.assertEqual(obj["material"]["material_graph_id"], "fibrous")
        self.assertEqual(obj["skin"]["kind"], "linear-gradient")
        simulation = self._simulation(applied["thought"])
        self.assertEqual(simulation["thought"]["objects"][0]["material"]["material_graph_id"], "fibrous")

    def test_environment_sensor_fusion_drives_continuous_state(self):
        result = self._create(
            "adapt-environment",
            fabric=fabric(),
            readings={"temperature": 20, "ambient_light": 50},
            policy={
                "drivers": [
                    {"sensor": "temperature", "min": 0, "max": 40, "weight": 1},
                    {"sensor": "ambient_light", "min": 0, "max": 100, "weight": 1},
                ],
                "from_state": {"observation_scale": 1, "choice": "default"},
                "to_state": {"observation_scale": 1, "choice": "alert"},
            },
        )
        self.assertAlmostEqual(result["adaptation_factor"], 0.5)
        self.assertEqual(len(result["sensor_trace"]), 2)
        self.assertEqual(result["truth_status"], "EXPLICIT_SENSOR_FUSION_SELECTED_CONTINUOUS_CHAMELEON_STATE")
        self.assertEqual(result["thought"]["objects"][0]["id"], "body-cell::body")

    def test_missing_sensor_reading_holds_instead_of_inventing_environment(self):
        result = self.machine.create({
            "kind": "sensor-adapt",
            "inputs": {
                "operation": "adapt-environment",
                "fabric": fabric(),
                "readings": {"temperature": 20},
                "policy": {
                    "drivers": [{"sensor": "humidity", "min": 0, "max": 100}],
                    "from_state": {"observation_scale": 1, "choice": "default"},
                    "to_state": {"observation_scale": 1, "choice": "alert"},
                },
            },
        })
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertIn("missing sensor", result["message"])

    def test_reality_feedback_reopens_simulation_on_measured_numeric_discrepancy(self):
        simulation = self._simulation(thought(roughness=0.2))
        feedback = self._create(
            "compare-reality",
            simulation=simulation,
            context_key="browser-A/scale-1",
            observation={
                "source": "authorized browser witness",
                "executor": "test-observer",
                "measurements": [{
                    "object_id": "body",
                    "channel": "material",
                    "field": "roughness",
                    "observed": 0.3,
                    "tolerance": 0.01,
                }],
            },
        )
        self.assertTrue(feedback["reopen_simulation"])
        self.assertAlmostEqual(feedback["discrepancies"][0]["delta"], 0.1)
        self.assertAlmostEqual(feedback["discrepancies"][0]["compensating_input_candidate"], 0.1)
        self.assertFalse(feedback["generalization_allowed"])

        rerun = self._create("recalibrate-simulation", simulation=simulation, feedback=feedback)
        self.assertTrue(rerun["reopened"])
        self.assertEqual(rerun["simulation"]["status"], "NO_KNOWN_IMPROVEMENTS")
        self.assertTrue(math.isclose(rerun["simulation"]["thought"]["objects"][0]["material"]["roughness"], 0.1, abs_tol=1e-9))

    def test_reality_feedback_within_tolerance_does_not_reopen(self):
        simulation = self._simulation(thought(roughness=0.2))
        feedback = self._create(
            "compare-reality",
            simulation=simulation,
            context_key="browser-A/scale-1",
            observation={
                "source": "authorized browser witness",
                "executor": "test-observer",
                "measurements": [{
                    "object_id": "body",
                    "channel": "material",
                    "field": "roughness",
                    "observed": 0.205,
                    "tolerance": 0.01,
                }],
            },
        )
        self.assertFalse(feedback["reopen_simulation"])
        rerun = self._create("recalibrate-simulation", simulation=simulation, feedback=feedback)
        self.assertEqual(rerun["status"], "NO_REALITY_DISCREPANCY_TO_REOPEN")

    def test_calibration_history_is_explicit_context_evidence_and_duplicate_safe(self):
        simulation = self._simulation(thought(roughness=0.2))
        feedback = self._create(
            "compare-reality",
            simulation=simulation,
            context_key="browser-A/scale-1",
            observation={
                "source": "authorized browser witness",
                "executor": "test-observer",
                "measurements": [{
                    "object_id": "body",
                    "channel": "material",
                    "field": "roughness",
                    "observed": 0.35,
                }],
            },
        )
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            first = record_calibration(root, feedback)
            second = record_calibration(root, feedback)
            self.assertEqual(first["status"], "EXACT_CONTEXT_CALIBRATION_RECORDED")
            self.assertEqual(second["status"], "CALIBRATION_ALREADY_RECORDED")
            history = inspect_calibrations(root, context_key="browser-A/scale-1")
            self.assertEqual(len(history["entries"]), 1)
            stat = history["numeric_stats"]["body::material::roughness"]
            self.assertEqual(stat["count"], 1)
            self.assertAlmostEqual(stat["mean_delta"], 0.15)
            self.assertFalse(history["generalization_allowed"])


if __name__ == "__main__":
    unittest.main()

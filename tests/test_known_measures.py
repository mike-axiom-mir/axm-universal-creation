from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_stickers import (domain_family, known_measure, measure_catalog, measure_value,
                          resolve_family_with_measures)
from axm_uc.machine import UniversalCreationMachine
from axm_uc.math_creation import bind_request, execute


class KnownMeasureTests(unittest.TestCase):
    def test_catalog_records_validate_and_keep_scope(self):
        catalog = measure_catalog()
        self.assertGreaterEqual(len(catalog), 4)
        for summary in catalog:
            record = known_measure(summary["id"])
            self.assertEqual(record["schema"], "axm.known-measure/v1")
            self.assertTrue(record["source"]["url"].startswith("https://"))
            self.assertIn("kind", record["scope"])

    def test_exact_values_keep_different_bases(self):
        light = known_measure("si.speed_of_light_vacuum")
        gravity = known_measure("convention.standard_gravity")
        atmosphere = known_measure("convention.standard_atmosphere")
        self.assertEqual(light["basis"], "si_definition")
        self.assertEqual(light["quantity"]["value"], 299792458.0)
        self.assertEqual(gravity["basis"], "conventional")
        self.assertEqual(gravity["quantity"]["value"], 9.80665)
        self.assertEqual(atmosphere["quantity"]["value"], 101325.0)

    def test_values_use_dimension_registry(self):
        self.assertEqual(measure_value("convention.astronomical_unit", "km"), 149597870.7)
        with self.assertRaisesRegex(ValueError, "incompatible"):
            measure_value("convention.standard_gravity", "m")

    def test_measure_can_drive_family_with_provenance(self):
        result = resolve_family_with_measures(
            domain_family("motion.constant_acceleration"),
            overrides={"initial_velocity": 0.0, "duration": 1.0},
            measure_overrides={"acceleration": "convention.standard_gravity"},
        )
        acceleration = result["parameters"]["acceleration"]
        self.assertEqual(acceleration["value"], 9.80665)
        self.assertEqual(acceleration["selected_by"], "known_measure")
        self.assertEqual(acceleration["known_measure"]["basis"], "conventional")
        self.assertAlmostEqual(result["derived"]["final_velocity"]["value"], 9.80665)
        self.assertIn("particular physical object", result["truth_boundary"])

    def test_measure_dimension_mismatch_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "incompatible unit dimensions"):
            resolve_family_with_measures(
                domain_family("geometry.circle"),
                measure_overrides={"radius": "convention.standard_gravity"},
            )

    def test_numeric_and_measure_collision_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "cannot target the same parameter"):
            resolve_family_with_measures(
                domain_family("motion.constant_acceleration"),
                overrides={"acceleration": 1.0},
                measure_overrides={"acceleration": "convention.standard_gravity"},
            )

    def test_measure_drives_real_universal_creation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "gravity.json"
            spec = {
                "schema": "axm.math-create/v1",
                "family_id": "motion.constant_acceleration",
                "measure_overrides": {"acceleration": "convention.standard_gravity"},
                "overrides": {"initial_velocity": 0.0, "duration": 1.0},
                "template": {
                    "kind": "json-file",
                    "direction": "create sourced conventional-gravity motion state",
                    "inputs": {"path": str(target), "value": {"final_velocity": 0.0}},
                },
                "bindings": {"final_velocity": ["inputs", "value", "final_velocity"]},
            }
            result = execute(UniversalCreationMachine(ROOT), spec)
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertAlmostEqual(written["final_velocity"], 9.80665)
            self.assertEqual(result["math"]["parameters"]["acceleration"]["selected_by"], "known_measure")

    def test_math_create_rejects_unknown_measure(self):
        spec = {
            "schema": "axm.math-create/v1",
            "family_id": "geometry.box",
            "measure_overrides": {"width": "does.not.exist"},
            "template": {"kind": "json-file", "direction": "test", "inputs": {"path": "x.json", "value": {"width": 0.0}}},
            "bindings": {"width": ["inputs", "value", "width"]},
        }
        with self.assertRaisesRegex(ValueError, "unknown known measure"):
            bind_request(spec)


if __name__ == "__main__":
    unittest.main()

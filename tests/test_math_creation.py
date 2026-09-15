from __future__ import annotations

import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.math_creation import bind_request, execute


def wheel_family():
    return {
        "schema": "axm.math-family/v1",
        "id": "wheel",
        "parameters": {
            "radius": {"unit": "m", "min": 0.2, "max": 1.0, "default": 0.5,
                       "truth": "measured", "uncertainty": 0.002, "source": "fixture measurement"},
            "hub_radius": {"unit": "m", "min": 0.05, "max": 0.4, "default": 0.15,
                           "truth": "empirical", "source": "fixture design range"},
        },
        "variants": {"compact": {"radius": 0.35, "hub_radius": 0.1}},
        "derived": {
            "circumference": {
                "unit": "m", "truth": "exact",
                "expr": {"op": {"name": "mul", "args": [{"const": "tau"}, {"param": "radius"}]}},
            }
        },
        "constraints": [
            {"label": "hub_within_wheel", "left": {"param": "hub_radius"}, "op": "le",
             "right": {"op": {"name": "mul", "args": [{"param": "radius"}, 0.45]}}}
        ],
    }


def request(path: str):
    return {
        "schema": "axm.math-create/v1",
        "family": wheel_family(),
        "variant": "compact",
        "template": {
            "kind": "json-file",
            "direction": "create inspectable math-resolved design state",
            "inputs": {"path": path, "value": {"radius": 0.0, "circumference": 0.0}},
        },
        "bindings": {
            "radius": ["inputs", "value", "radius"],
            "circumference": ["inputs", "value", "circumference"],
        },
    }


class MathCreationTests(unittest.TestCase):
    def test_binds_resolved_values_without_mutating_template(self):
        spec = request("ignored.json")
        bound = bind_request(spec)
        self.assertEqual(spec["template"]["inputs"]["value"]["radius"], 0.0)
        self.assertEqual(bound["request"]["inputs"]["value"]["radius"], 0.35)
        self.assertAlmostEqual(bound["request"]["inputs"]["value"]["circumference"], math.tau * 0.35)
        self.assertEqual(bound["family_source"], "inline")

    def test_math_result_drives_real_machine_creation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "wheel.json"
            result = execute(UniversalCreationMachine(ROOT), request(str(target)))
            self.assertEqual(result["type"], "MATH_CREATION_RESULT")
            self.assertEqual(result["creation"]["type"], "CREATION_RESULT")
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(written["radius"], 0.35)
            self.assertAlmostEqual(written["circumference"], math.tau * 0.35)
            self.assertTrue(result["math"]["constraints"][0]["passed"])
            self.assertEqual(result["math"]["derived"]["circumference"]["truth"], "measured")

    def test_builtin_family_id_drives_real_machine_creation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "motion.json"
            spec = {
                "schema": "axm.math-create/v1",
                "family_id": "motion.linear",
                "overrides": {"distance": 100.0, "duration": 10.0},
                "template": {
                    "kind": "json-file",
                    "direction": "create unit-aware motion state",
                    "inputs": {"path": str(target), "value": {"speed_mps": 0.0, "speed_kmh": 0.0}},
                },
                "bindings": {
                    "speed_mps": ["inputs", "value", "speed_mps"],
                    "speed_kmh": ["inputs", "value", "speed_kmh"],
                },
            }
            result = execute(UniversalCreationMachine(ROOT), spec)
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["family_source"], "builtin:motion.linear")
            self.assertEqual(written["speed_mps"], 10.0)
            self.assertAlmostEqual(written["speed_kmh"], 36.0)

    def test_family_source_is_explicit_and_unambiguous(self):
        spec = request("ignored.json")
        spec["family_id"] = "geometry.circle"
        with self.assertRaisesRegex(ValueError, "exactly one"):
            bind_request(spec)
        del spec["family"]
        del spec["family_id"]
        with self.assertRaisesRegex(ValueError, "exactly one"):
            bind_request(spec)

    def test_binding_cannot_silently_create_or_replace_nonnumeric_targets(self):
        spec = request("ignored.json")
        spec["bindings"]["radius"] = ["inputs", "missing"]
        with self.assertRaisesRegex(ValueError, "does not exist"):
            bind_request(spec)
        spec = request("ignored.json")
        spec["template"]["inputs"]["value"]["radius"] = "guess"
        with self.assertRaisesRegex(ValueError, "numeric"):
            bind_request(spec)


if __name__ == "__main__":
    unittest.main()

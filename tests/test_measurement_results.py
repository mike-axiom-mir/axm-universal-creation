from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_stickers import (domain_family, measurement_value, resolve_family_with_evidence,
                          standard_uncertainty, validate_measurement_result)
from axm_uc.machine import UniversalCreationMachine
from axm_uc.math_creation import execute


def radius_measurement(*, expanded: bool = False):
    uncertainty = {
        "kind": "expanded" if expanded else "standard",
        "value": 0.8 if expanded else 0.4,
        "unit": "mm",
        "evaluation": "type_a",
        "degrees_of_freedom": 4,
    }
    if expanded:
        uncertainty["coverage_factor"] = 2.0
        uncertainty["coverage_probability"] = 0.95
    return {
        "schema": "axm.measurement-result/v1",
        "id": "fixture.wheel.radius",
        "measurand": "synthetic wheel radius",
        "quantity": {"value": 350.2, "unit": "mm"},
        "uncertainty": uncertainty,
        "method": {
            "description": "five repeated synthetic caliper readings",
            "statistic": "mean",
            "sample_count": 5,
            "instrument": "synthetic caliper fixture",
        },
        "scope": {
            "kind": "test_fixture",
            "applies_to": "one synthetic wheel fixture",
            "conditions": ["test-only evidence; not a real-world population claim"],
        },
        "source": {
            "kind": "local_record",
            "authority": "AXM test fixture",
            "title": "Synthetic radius measurement record",
            "locator": "tests/test_measurement_results.py:radius_measurement",
            "sha256": "0" * 64,
        },
        "observed_at": "2026-09-15",
        "notes": ["Synthetic test record; demonstrates evidence plumbing only."],
    }


class MeasurementResultTests(unittest.TestCase):
    def test_result_requires_value_uncertainty_scope_method_and_provenance(self):
        record = validate_measurement_result(radius_measurement())
        self.assertEqual(record["quantity"], {"value": 350.2, "unit": "mm"})
        self.assertEqual(record["uncertainty"]["kind"], "standard")
        self.assertEqual(record["source"]["kind"], "local_record")

    def test_expanded_uncertainty_converts_to_standard_equivalent_via_k(self):
        record = radius_measurement(expanded=True)
        self.assertAlmostEqual(standard_uncertainty(record, "m"), 0.0004)
        self.assertAlmostEqual(measurement_value(record, "m"), 0.3502)

    def test_expanded_uncertainty_requires_coverage_factor(self):
        record = radius_measurement(expanded=True)
        del record["uncertainty"]["coverage_factor"]
        with self.assertRaisesRegex(ValueError, "coverage_factor"):
            validate_measurement_result(record)

    def test_type_a_requires_series(self):
        record = radius_measurement()
        record["method"]["sample_count"] = 1
        with self.assertRaisesRegex(ValueError, "series"):
            validate_measurement_result(record)

    def test_uncertainty_dimension_mismatch_fails_closed(self):
        record = radius_measurement()
        record["uncertainty"]["unit"] = "s"
        with self.assertRaisesRegex(ValueError, "incompatible"):
            validate_measurement_result(record)

    def test_source_requires_https_or_digest(self):
        record = radius_measurement()
        del record["source"]["sha256"]
        with self.assertRaisesRegex(ValueError, "url or sha256"):
            validate_measurement_result(record)

    def test_measurement_drives_math_and_preserves_measured_truth(self):
        result = resolve_family_with_evidence(
            domain_family("geometry.circle"),
            measurement_overrides={"radius": radius_measurement()},
        )
        radius = result["parameters"]["radius"]
        self.assertAlmostEqual(radius["value"], 0.3502)
        self.assertAlmostEqual(radius["uncertainty"], 0.0004)
        self.assertEqual(radius["truth"], "measured")
        self.assertEqual(radius["selected_by"], "measurement_result")
        self.assertEqual(radius["uncertainty_basis"], "reported_standard")
        self.assertEqual(result["derived"]["circumference"]["truth"], "measured")

    def test_expanded_measurement_marks_uncertainty_derivation(self):
        result = resolve_family_with_evidence(
            domain_family("geometry.circle"),
            measurement_overrides={"radius": radius_measurement(expanded=True)},
        )
        radius = result["parameters"]["radius"]
        self.assertAlmostEqual(radius["uncertainty"], 0.0004)
        self.assertEqual(radius["uncertainty_basis"], "expanded_divided_by_coverage_factor")

    def test_evidence_sources_cannot_compete_for_one_parameter(self):
        with self.assertRaisesRegex(ValueError, "cannot target the same parameter"):
            resolve_family_with_evidence(
                domain_family("geometry.circle"),
                overrides={"radius": 0.5},
                measurement_overrides={"radius": radius_measurement()},
            )
        with self.assertRaisesRegex(ValueError, "cannot target the same parameter"):
            resolve_family_with_evidence(
                domain_family("geometry.circle"),
                measure_overrides={"radius": "convention.astronomical_unit"},
                measurement_overrides={"radius": radius_measurement()},
            )

    def test_measurement_result_drives_real_universal_creation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "measured_circle.json"
            spec = {
                "schema": "axm.math-create/v1",
                "family_id": "geometry.circle",
                "measurement_overrides": {"radius": radius_measurement()},
                "template": {
                    "kind": "json-file",
                    "direction": "create measured circle state",
                    "inputs": {"path": str(target), "value": {"radius": 0.0, "circumference": 0.0}},
                },
                "bindings": {
                    "radius": ["inputs", "value", "radius"],
                    "circumference": ["inputs", "value", "circumference"],
                },
            }
            result = execute(UniversalCreationMachine(ROOT), spec)
            written = json.loads(target.read_text(encoding="utf-8"))
            self.assertAlmostEqual(written["radius"], 0.3502)
            self.assertAlmostEqual(written["circumference"], math.tau * 0.3502)
            self.assertEqual(result["math"]["parameters"]["radius"]["truth"], "measured")


if __name__ == "__main__":
    unittest.main()

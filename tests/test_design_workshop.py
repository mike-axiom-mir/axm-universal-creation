from pathlib import Path
import tempfile
import unittest

from axm_stickers.placement import identity
from axm_uc.design_workshop import (
    OBSERVATION_SCHEMA,
    SKETCH_SCHEMA,
    compare_sketch,
    materialize_sketch,
    validate_sketch,
)
from axm_uc.machine import UniversalCreationMachine

ROOT = Path(__file__).resolve().parents[1]


def frame(x=0.0, y=0.0, z=0.0):
    value = identity(); value[3] = float(x); value[7] = float(y); value[11] = float(z); return value


def part(part_id, x, y=0.0, z=0.0):
    return {"id": part_id, "shape": "box", "frame": frame(x, y, z), "size": [1.0, 0.2, 0.2],
            "role": "structure", "notes": "rough workshop block"}


def sketch():
    return {
        "schema": SKETCH_SCHEMA,
        "id": "straight-frame",
        "purpose": "rough frame plan with workshop gauges",
        "units": "m",
        "parts": [part("left", -1), part("center", 0), part("right", 1)],
        "gauges": [
            {"id": "ruler", "type": "distance", "a": "left", "b": "right", "target": 2.0, "tolerance": 0.01},
            {"id": "straightedge", "type": "alignment", "parts": ["left", "center", "right"], "axis": "x", "tolerance": 0.01},
            {"id": "spacing-jig", "type": "spacing", "parts": ["left", "center", "right"], "axis": "x", "target": 1.0, "tolerance": 0.01},
            {"id": "square", "type": "angle", "a": "left", "a_axis": "x", "b": "center", "b_axis": "y", "target_degrees": 90.0, "tolerance_degrees": 0.01},
            {"id": "level", "type": "orientation", "part": "left", "local_axis": "x", "world_axis": "x", "target_degrees": 0.0, "tolerance_degrees": 0.01},
            {"id": "mirror", "type": "symmetry", "pairs": [{"a": "left", "b": "right"}], "axis": "x", "center": 0.0, "tolerance": 0.01},
            {"id": "caliper", "type": "size", "part": "left", "target": [1.0, 0.2, 0.2], "tolerance": 0.001}
        ],
        "tolerances": {"position": 0.01, "size": 0.001, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "explicit fixture"}
    }


def observation(checked, center_y=0.0):
    rows = []
    for row in checked["parts"]:
        value = {"id": row["id"], "frame": list(row["frame"]), "size": list(row["size"])}
        if row["id"] == "center": value["frame"][7] = center_y
        rows.append(value)
    return {"schema": OBSERVATION_SCHEMA, "sketch_digest": checked["sketch_digest"], "parts": rows,
            "observer": {"kind": "test-fixture", "source": "explicit numeric state"}}


class DesignWorkshopTests(unittest.TestCase):
    def test_exact_build_passes_all_workshop_instruments(self):
        checked = validate_sketch(sketch())
        report = compare_sketch(checked, observation(checked))
        self.assertEqual(report["status"], "PASS")
        self.assertTrue(report["passed"])
        self.assertEqual({row["status"] for row in report["gauges"]}, {"PASS"})

    def test_crooked_center_is_numeric_failure_not_visual_guess(self):
        checked = validate_sketch(sketch())
        report = compare_sketch(checked, observation(checked, center_y=0.2))
        self.assertEqual(report["status"], "FAIL")
        gauges = {row["id"]: row for row in report["gauges"]}
        self.assertEqual(gauges["straightedge"]["status"], "FAIL")
        self.assertGreater(gauges["straightedge"]["residual"], gauges["straightedge"]["tolerance"])
        self.assertIn("center", report["repair_direction"])

    def test_observation_digest_drift_fails_closed(self):
        checked = validate_sketch(sketch())
        observed = observation(checked); observed["sketch_digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(Exception, "does not match exact sketch digest"):
            compare_sketch(checked, observed)

    def test_materialized_sketch_keeps_exact_json_and_schematic_svg_separate(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            result = materialize_sketch(root, "creations/workshop-blockout", sketch())
            target = Path(result["path"])
            self.assertTrue((target / "sketch.json").is_file())
            svg = (target / "sketch.svg").read_text(encoding="utf-8")
            self.assertIn("schematic blockout", svg)
            self.assertIn("not a render", svg)

    def test_universal_creation_machine_routes_design_workshop(self):
        machine = UniversalCreationMachine(ROOT)
        result = machine.create({"kind": "design-workshop", "inputs": {"operation": "inspect-workshop"}})
        self.assertEqual(result["type"], "CREATION_RESULT")
        self.assertEqual(result["capability"], "AXM-CAP-DESIGN-WORKSHOP")
        self.assertIn("distance/ruler", result["result"]["instruments"])


if __name__ == "__main__":
    unittest.main()

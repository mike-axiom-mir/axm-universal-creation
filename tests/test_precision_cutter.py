from __future__ import annotations

import math
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.precision_cutter import PrecisionCutterError, build_cut
from axm_uc.procedural_3d import verify_glb


def material() -> dict:
    return {"color": "#7A8FA8FF", "metallic": 0.55, "roughness": 0.32}


def profile_spec() -> dict:
    return {
        "schema": "axm.precision-cutter/v0.1",
        "name": "L cut plate",
        "operation": "profile-cut",
        "thickness": 0.2,
        "material": material(),
        "profile": [[-2, -1], [2, -1], [2, 0], [0, 0], [0, 2], [-2, 2]],
    }


def hole_spec(*, kerf: float = 0.0) -> dict:
    return {
        "schema": "axm.precision-cutter/v0.1",
        "name": "Panel with calculated hole",
        "operation": "round-through-hole",
        "thickness": 0.3,
        "kerf": kerf,
        "material": material(),
        "stock_size": [4.0, 3.0],
        "hole": {"center": [0.4, -0.2], "radius": 0.5, "segments": 32},
    }


def socket_spec(*, kerf: float = 0.02) -> dict:
    return {
        "schema": "axm.precision-cutter/v0.1",
        "name": "Calculated receiver socket",
        "operation": "round-socket",
        "thickness": 0.45,
        "kerf": kerf,
        "material": material(),
        "stock_size": [4.0, 4.0],
        "socket": {
            "center": [0.0, 0.0],
            "source_radius": 0.5,
            "clearance": 0.05,
            "segments": 48,
        },
    }


class PrecisionCutterTests(unittest.TestCase):
    def test_concave_profile_is_deterministic_and_measured(self):
        first = build_cut(profile_spec())
        second = build_cut(profile_spec())
        self.assertEqual(first["specification_sha256"], second["specification_sha256"])
        self.assertEqual(first["surface_specification"], second["surface_specification"])
        self.assertAlmostEqual(first["metrics"]["profile_area"], 8.0)
        self.assertAlmostEqual(first["metrics"]["solid_volume"], 1.6)
        self.assertEqual(first["metrics"]["top_surface_triangles"], 4)
        self.assertFalse(first["metrics"]["kerf_applied"])
        self.assertEqual(first["truth_boundary"]["visual_quality"], "NOT_TESTED")
        self.assertFalse(first["truth_boundary"]["full_arbitrary_mesh_csg"])

    def test_round_hole_applies_half_kerf_to_cut_radius(self):
        cut = build_cut(hole_spec(kerf=0.10))
        metrics = cut["metrics"]
        self.assertAlmostEqual(metrics["requested_radius"], 0.5)
        self.assertAlmostEqual(metrics["effective_radius"], 0.55)
        self.assertAlmostEqual(metrics["kerf"], 0.10)
        self.assertGreater(metrics["polygonized_removed_area"], 0.0)
        self.assertLess(metrics["polygonized_removed_area"], metrics["stock_area"])
        self.assertAlmostEqual(metrics["analytic_requested_removed_area"], math.pi * 0.25)
        self.assertAlmostEqual(metrics["analytic_effective_removed_area"], math.pi * 0.55 * 0.55)

    def test_socket_exposes_requested_and_geometric_clearance(self):
        cut = build_cut(socket_spec(kerf=0.02))
        metrics = cut["metrics"]
        self.assertAlmostEqual(metrics["source_radius"], 0.5)
        self.assertAlmostEqual(metrics["requested_radial_clearance"], 0.05)
        self.assertAlmostEqual(metrics["requested_radius"], 0.55)
        self.assertAlmostEqual(metrics["effective_radius"], 0.56)
        self.assertAlmostEqual(metrics["geometric_radial_clearance"], 0.06)

    def test_live_machine_routes_cutter_and_existing_glb_validator_proves_output(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "socket.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "laser-socket-cut",
                "inputs": {"path": str(target), "specification": socket_spec()},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(body["truth_status"], "VALIDATED_DETERMINISTIC_PRECISION_CUT")
            self.assertTrue(body["glb_validation"]["passed"])
            self.assertTrue(target.is_file())
            self.assertEqual(body["sha256"], __import__("hashlib").sha256(target.read_bytes()).hexdigest())
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertFalse(body["rendered_appearance_observed"])
            self.assertEqual(body["truth_boundary"]["physical_laser_process"], "NOT_SIMULATED")

    def test_same_cut_recipe_publishes_identical_glb_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            first = Path(td) / "first.glb"
            second = Path(td) / "second.glb"
            machine = UniversalCreationMachine(ROOT)
            a = machine.create({
                "kind": "laser-through-hole",
                "inputs": {"path": str(first), "specification": hole_spec(kerf=0.04)},
            })
            b = machine.create({
                "kind": "laser-through-hole",
                "inputs": {"path": str(second), "specification": hole_spec(kerf=0.04)},
            })
            self.assertEqual(a["type"], "CREATION_RESULT", a)
            self.assertEqual(b["type"], "CREATION_RESULT", b)
            self.assertEqual(first.read_bytes(), second.read_bytes())
            self.assertEqual(a["result"]["sha256"], b["result"]["sha256"])

    def test_self_intersection_and_impossible_hole_fail_closed(self):
        bow_tie = profile_spec()
        bow_tie["profile"] = [[-1, -1], [1, 1], [-1, 1], [1, -1]]
        with self.assertRaisesRegex(PrecisionCutterError, "simple non-self-intersecting"):
            build_cut(bow_tie)
        too_large = hole_spec()
        too_large["hole"]["radius"] = 2.0
        with self.assertRaisesRegex(PrecisionCutterError, "strictly inside"):
            build_cut(too_large)

    def test_failed_replacement_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "panel.glb"
            target.write_bytes(b"preserve-me")
            bad = hole_spec()
            bad["hole"]["radius"] = 99.0
            result = UniversalCreationMachine(ROOT).create({
                "kind": "precision-cut-3d",
                "inputs": {"path": str(target), "specification": bad, "replace": True},
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual(target.read_bytes(), b"preserve-me")

    def test_machine_body_and_undeclared_arbitrary_csg_stay_blocked(self):
        target = ROOT / "precision-cut-should-not-exist.glb"
        if target.exists():
            target.unlink()
        result = UniversalCreationMachine(ROOT).create({
            "kind": "laser-cut-profile",
            "inputs": {"path": str(target), "specification": profile_spec()},
        })
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertFalse(target.exists())

        unsupported = profile_spec()
        unsupported["source_glb"] = "some-existing-model.glb"
        with self.assertRaises(PrecisionCutterError):
            build_cut(unsupported)


if __name__ == "__main__":
    unittest.main()

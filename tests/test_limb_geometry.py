from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.limb_geometry import two_bone_entry_range


class LimbGeometryTests(unittest.TestCase):
    def test_actual_exported_pose_regressions(self):
        fixture = json.loads((ROOT / "tests/fixtures/two_bone_entry.json").read_text())
        for case in fixture["cases"]:
            with self.subTest(case=case["name"], version=case["version"]):
                result = two_bone_entry_range(case["shoulder"], case["wrist"],
                                             *case["segment_lengths"], case["entry_axis"])
                self.assertEqual(result.status, "reachable")
                self.assertAlmostEqual(result.minimum_entry_m, case["expected_minimum"], places=12)
                self.assertAlmostEqual(result.maximum_entry_m, case["expected_maximum"], places=12)
                self.assertEqual(result.classify_minimum(.06), case["expected_sixty_mm"])
        # The two imported examples are surface-clear despite missing the 60mm
        # preference. Entry feasibility must not become a collision certificate.
        clear = [c for c in fixture["cases"] if c["version"] == 4]
        self.assertEqual(len(clear), 2)
        self.assertTrue(all(c["surface_pairs"] == 0 and c["expected_sixty_mm"] == "impossible" for c in clear))

    def test_perpendicular_axis_has_known_symmetric_circle_range(self):
        result = two_bone_entry_range((0, 0, 0), (0, 0, 6), 5, 5, (0, 7, 0))
        self.assertEqual(result.center, (0, 0, 3))
        self.assertAlmostEqual(result.radius_m, 4)
        self.assertAlmostEqual(result.minimum_entry_m, -4)
        self.assertAlmostEqual(result.maximum_entry_m, 4)

    def test_parallel_axis_is_constant_for_every_bend_angle(self):
        result = two_bone_entry_range((0, 0, 0), (0, 0, 6), 5, 5, (0, 0, 2))
        self.assertEqual((result.minimum_entry_m, result.maximum_entry_m), (-3, -3))
        reverse = two_bone_entry_range((0, 0, 0), (0, 0, 6), 5, 5, (0, 0, -2))
        self.assertEqual((reverse.minimum_entry_m, reverse.maximum_entry_m), (3, 3))

    def test_range_contains_independently_sampled_known_circle(self):
        axis = (1/math.sqrt(2), 0, 1/math.sqrt(2))
        result = two_bone_entry_range((0, 0, 0), (0, 0, 6), 5, 5, axis)
        entries = [(4*math.cos(k*math.tau/360)-3)/math.sqrt(2) for k in range(360)]
        self.assertAlmostEqual(min(entries), result.minimum_entry_m)
        self.assertAlmostEqual(max(entries), result.maximum_entry_m)

    def test_straight_and_fully_folded_chains_are_point_loci(self):
        straight = two_bone_entry_range((0, 0, 0), (3, 0, 0), 1, 2, (1, 0, 0))
        folded = two_bone_entry_range((0, 0, 0), (1, 0, 0), 1, 2, (1, 0, 0))
        for result, center in ((straight, (1, 0, 0)), (folded, (-1, 0, 0))):
            self.assertEqual(result.locus, "point")
            self.assertEqual(result.center, center)
            self.assertEqual((result.minimum_entry_m, result.maximum_entry_m), (-2, -2))

    def test_unreachable_wrists_are_not_projected_or_bend_clamped(self):
        for wrist in ((4, 0, 0), (.5, 0, 0), (0, 0, 0)):
            result = two_bone_entry_range((0, 0, 0), wrist, 1, 2, (1, 0, 0))
            self.assertEqual(result.status, "unreachable")
            self.assertIsNone(result.center)
            self.assertIsNone(result.maximum_entry_m)
            self.assertEqual(result.classify_minimum(-100), "unreachable")

    def test_coincident_equal_segments_have_a_sphere_of_elbows(self):
        result = two_bone_entry_range((2, 3, 4), (2, 3, 4), 5, 5, (1, 2, 3))
        self.assertEqual(result.locus, "sphere")
        self.assertEqual((result.minimum_entry_m, result.maximum_entry_m), (-5, 5))

    def test_rigid_motion_scale_and_axis_magnitude(self):
        for scale in (1e-100, 1e-6, 1, 1e100):
            # A 90-degree rotation moves the known Z-axis chain to X.
            result = two_bone_entry_range((0, 0, 0), (6*scale, 0, 0), 5*scale, 5*scale, (0, 1e300, 0))
            self.assertAlmostEqual(result.minimum_entry_m/scale, -4)
            self.assertAlmostEqual(result.maximum_entry_m/scale, 4)
        translated = two_bone_entry_range((1e8, -2e8, 3e8), (1e8, -2e8, 3e8+6), 5, 5, (0, 1, 0))
        self.assertAlmostEqual(translated.minimum_entry_m, -4)
        self.assertAlmostEqual(translated.maximum_entry_m, 4)

    def test_nearly_coincident_chain_preserves_circle_when_squares_underflow(self):
        result = two_bone_entry_range((0, 0, 0), (0, 0, 1e-200), 1, 1, (0, 1, 0))
        self.assertEqual(result.locus, "circle")
        self.assertEqual(result.center, (0, 0, 5e-201))
        self.assertAlmostEqual(result.radius_m, 1)
        self.assertAlmostEqual(result.minimum_entry_m, -1)
        self.assertAlmostEqual(result.maximum_entry_m, 1)

    def test_required_threshold_boundary_is_explicit(self):
        result = two_bone_entry_range((0, 0, 0), (0, 0, 6), 5, 5, (0, 1, 0))
        self.assertEqual(result.classify_minimum(4), "boundary")
        self.assertEqual(result.classify_minimum(4+5e-10), "boundary")
        self.assertEqual(result.classify_minimum(4+1e-6), "impossible")
        self.assertEqual(result.classify_minimum(4-1e-6), "possible")
        for value in (0, -1, math.inf, True):
            with self.assertRaises(ValueError):
                result.classify_minimum(0, tolerance_m=value)

    def test_invalid_input_and_unrepresentable_endpoint_difference(self):
        bad = [((), (0, 0, 1), 1, 1, (0, 1, 0)),
               ((0, 0, 0), (0, 0, 1), 0, 1, (0, 1, 0)),
               ((0, 0, 0), (0, 0, 1), 1, True, (0, 1, 0)),
               ((0, 0, 0), (0, 0, 1), 1, 1, (0, 0, 0)),
               ((math.nan, 0, 0), (0, 0, 1), 1, 1, (0, 1, 0)),
               ((0, 0, 0), (0, 0, 1), 1, math.inf, (0, 1, 0))]
        for args in bad:
            with self.subTest(args=args), self.assertRaises(ValueError):
                two_bone_entry_range(*args)
        held = two_bone_entry_range((-1e308, 0, 0), (1e308, 0, 0), 1e308, 1e308, (0, 1, 0))
        self.assertEqual(held.status, "hold")


if __name__ == "__main__":
    unittest.main()

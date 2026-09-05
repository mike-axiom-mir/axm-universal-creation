from __future__ import annotations

import json
import math
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.triangle_queries import ClosedTriangleSurface

VERTICES = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, 0, 1)]
FACES = [(0, 2, 1), (0, 1, 3), (0, 3, 2), (1, 2, 3)]


class TriangleQueryTests(unittest.TestCase):
    def test_imported_rotated_receiver_repeated_face_regression(self):
        data = json.loads((ROOT / "tests/fixtures/containment_rehit.json").read_text())
        surface = ClosedTriangleSurface(data["vertices"], data["triangles"])
        self.assertEqual(len(data["samples"]), 9)
        for sample in data["samples"]:
            with self.subTest(point=sample["point"]):
                self.assertEqual(surface.classify(sample["point"]), sample["expected"])
        # Old ray counts were odd despite the receiver's separating bottom plane.
        self.assertTrue(all(s["weapon_local_y"] < .055 for s in data["samples"][:-1]))
        self.assertTrue(all(sum(n % 2 for n in s["legacy_ray_counts"]) >= 2 for s in data["samples"][:-1]))

    def test_positive_negative_boundary_and_outside_inside_aabb(self):
        surface = ClosedTriangleSurface(VERTICES, FACES)
        for point, expected in [((.1, .1, .1), "inside"), ((.7, .7, .7), "outside"), ((2, 0, 0), "outside"), ((0, .2, .3), "boundary"), ((0, 0, 0), "boundary"), ((1/3, 1/3, 1/3), "boundary")]:
            with self.subTest(point=point):
                self.assertEqual(surface.classify(point), expected)

    def test_rigid_transform_and_scale_do_not_turn_outside_into_inside(self):
        def transform(p, scale):
            x, y, z = (v*scale for v in p)
            return (1.2+x*math.cos(.6)-z*math.sin(.6), -.5+y, .7+x*math.sin(.6)+z*math.cos(.6))
        for scale in (.01, 1, 100):
            surface = ClosedTriangleSurface([transform(p, scale) for p in VERTICES], FACES)
            for p, expected in [((.1, .1, .1), "inside"), ((.7, .7, .7), "outside"), ((-.1, .1, .1), "outside")]:
                self.assertEqual(surface.classify(transform(p, scale)), expected)

    def test_reversing_face_winding_preserves_classification(self):
        surface = ClosedTriangleSurface(VERTICES, [tuple(reversed(f)) for f in FACES])
        self.assertEqual(surface.classify((.1, .1, .1)), "inside")
        self.assertEqual(surface.classify((.7, .7, .7)), "outside")

    def test_tolerance_boundary_is_not_strict_penetration(self):
        surface = ClosedTriangleSurface(VERTICES, FACES)
        self.assertEqual(surface.classify((5e-8, .1, .1)), "boundary")
        self.assertEqual(surface.classify((-5e-8, .1, .1)), "boundary")
        self.assertEqual(surface.classify((1e-5, .1, .1)), "inside")
        self.assertEqual(surface.classify((-1e-5, .1, .1)), "outside")

    def test_sub_resolution_separate_crossings_hold_instead_of_becoming_one_hit(self):
        vertices = [(-1,-1,0), (1,-1,0), (1,1,0), (-1,1,0), (-1,-1,5e-8), (1,-1,5e-8), (1,1,5e-8), (-1,1,5e-8)]
        faces = [(0,2,1), (0,3,2), (4,5,6), (4,6,7), (0,1,5), (0,5,4), (1,2,6), (1,6,5), (2,3,7), (2,7,6), (3,0,4), (3,4,7)]
        rotate = lambda p: ((p[0]+p[2])/math.sqrt(2), p[1], (-p[0]+p[2])/math.sqrt(2))
        surface = ClosedTriangleSurface([rotate(p) for p in vertices], faces)
        self.assertEqual(surface.classify(rotate((.2,0,-.1))), "hold")

    def test_open_or_degenerate_surfaces_are_rejected(self):
        for faces in (FACES[:-1], [(0, 0, 1)], FACES+[FACES[0]]):
            with self.subTest(faces=faces), self.assertRaises(ValueError):
                ClosedTriangleSurface(VERTICES, faces)
        with self.assertRaises(ValueError):
            ClosedTriangleSurface([(0, 0, 0), (1, 0, 0), (2, 0, 0), (0, 0, 1)], FACES)

    def test_nonfinite_coordinates_and_invalid_indices_are_rejected(self):
        for bad in (math.nan, math.inf, -math.inf):
            with self.assertRaises(ValueError):
                ClosedTriangleSurface([(bad, 0, 0), *VERTICES[1:]], FACES)
            with self.assertRaises(ValueError):
                ClosedTriangleSurface(VERTICES, FACES).classify((bad, 0, 0))
        for tolerance in (0, -1, math.inf, math.nan, True):
            with self.assertRaises(ValueError):
                ClosedTriangleSurface(VERTICES, FACES, tolerance_m=tolerance)
        with self.assertRaises(ValueError):
            ClosedTriangleSurface(VERTICES, [(0, 1, 9), *FACES[1:]])


if __name__ == "__main__":
    unittest.main()

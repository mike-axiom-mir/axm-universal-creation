import unittest

from axm_uc.mesh_self_intersection import inspect_triangle_self_intersections


class MeshSelfIntersectionNoncoplanarTests(unittest.TestCase):
    def test_noncoplanar_crossing_is_reported(self):
        positions = [
            (-1.0, -1.0, 0.0),
            (1.0, -1.0, 0.0),
            (0.0, 1.0, 0.0),
            (0.0, -0.5, -1.0),
            (0.0, -0.5, 1.0),
            (0.0, 0.75, 0.0),
        ]
        report = inspect_triangle_self_intersections(
            positions,
            [0, 1, 2, 3, 4, 5],
        )
        self.assertTrue(report["inspection_complete"])
        self.assertEqual(report["broad_phase_candidate_pairs"], 1)
        self.assertEqual(report["status"], "SELF_INTERSECTIONS_DETECTED")
        self.assertEqual(report["self_intersection_pair_count"], 1)
        self.assertEqual(report["examples"], [{"triangle_a": 0, "triangle_b": 1}])


if __name__ == "__main__":
    unittest.main()

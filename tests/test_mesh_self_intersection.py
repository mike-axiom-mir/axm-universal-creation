import unittest

from axm_uc.mesh_self_intersection import (
    DONOR_PROVENANCE,
    HARD_MAX_TRIANGLE_PAIR_CHECKS,
    MeshSelfIntersectionError,
    inspect_triangle_self_intersections,
)


class MeshSelfIntersectionTests(unittest.TestCase):
    def test_separated_nonadjacent_triangles_pass_complete_scan(self):
        positions = [
            (0, 0, 0), (1, 0, 0), (0, 1, 0),
            (3, 0, 0), (4, 0, 0), (3, 1, 0),
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["status"], "PASS_NO_NONADJACENT_SELF_INTERSECTIONS")
        self.assertTrue(report["inspection_complete"])
        self.assertEqual(report["triangle_pair_checks_required"], 1)
        self.assertEqual(report["triangle_pair_checks_performed"], 1)
        self.assertEqual(report["broad_phase_candidate_pairs"], 0)
        self.assertEqual(report["self_intersection_pair_count"], 0)
        self.assertTrue(report["truth_boundary"]["nonadjacent_triangle_self_intersection_checked"])
        self.assertFalse(report["truth_boundary"]["adjacent_foldover_or_contact_checked"])
        self.assertFalse(report["truth_boundary"]["repair_or_adoption_authorized"])

    def test_coplanar_nonadjacent_overlap_is_reported(self):
        positions = [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (0.5, 0.5, 0), (1.5, 0.5, 0), (0.5, 1.5, 0),
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["status"], "SELF_INTERSECTIONS_DETECTED")
        self.assertEqual(report["broad_phase_candidate_pairs"], 1)
        self.assertEqual(report["self_intersection_pair_count"], 1)
        self.assertEqual(report["examples"], [{"triangle_a": 0, "triangle_b": 1}])

    def test_exact_source_topological_neighbors_are_excluded(self):
        positions = [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (2, 0, 0), (0, 2, 0),
        ]
        report = inspect_triangle_self_intersections(positions, [0, 1, 2, 0, 3, 4])
        self.assertEqual(report["status"], "PASS_NO_NONADJACENT_SELF_INTERSECTIONS")
        self.assertEqual(report["triangle_pair_checks_performed"], 1)
        self.assertEqual(report["skipped_topological_neighbor_pairs"], 1)
        self.assertEqual(report["broad_phase_candidate_pairs"], 0)
        self.assertEqual(report["self_intersection_pair_count"], 0)

    def test_pair_budget_holds_before_quadratic_scan(self):
        positions = []
        indices = []
        for triangle in range(4):
            base = len(positions)
            z = float(triangle * 2)
            positions.extend(((0, 0, z), (1, 0, z), (0, 1, z)))
            indices.extend((base, base + 1, base + 2))

        report = inspect_triangle_self_intersections(
            positions,
            indices,
            max_triangle_pair_checks=5,
        )
        self.assertEqual(report["status"], "HOLD_TRIANGLE_PAIR_BUDGET_EXCEEDED")
        self.assertFalse(report["inspection_complete"])
        self.assertEqual(report["triangle_pair_checks_required"], 6)
        self.assertEqual(report["triangle_pair_checks_performed"], 0)
        self.assertIsNone(report["skipped_topological_neighbor_pairs"])
        self.assertIsNone(report["broad_phase_candidate_pairs"])
        self.assertIsNone(report["self_intersection_pair_count"])
        self.assertEqual(report["examples"], [])
        self.assertFalse(report["truth_boundary"]["nonadjacent_triangle_self_intersection_checked"])

    def test_budget_hold_never_relabels_partial_prefix_as_clean(self):
        positions = [
            (0, 0, 0), (2, 0, 0), (0, 2, 0),
            (0.5, 0.5, 0), (1.5, 0.5, 0), (0.5, 1.5, 0),
            (5, 0, 0), (6, 0, 0), (5, 1, 0),
        ]
        report = inspect_triangle_self_intersections(
            positions,
            list(range(9)),
            max_triangle_pair_checks=2,
        )
        self.assertEqual(report["status"], "HOLD_TRIANGLE_PAIR_BUDGET_EXCEEDED")
        self.assertEqual(report["triangle_pair_checks_required"], 3)
        self.assertEqual(report["triangle_pair_checks_performed"], 0)
        self.assertIsNone(report["self_intersection_pair_count"])

    def test_examples_are_bounded_without_hiding_total_count(self):
        triangle = [(0, 0, 0), (2, 0, 0), (0, 2, 0)]
        positions = triangle + triangle + triangle
        indices = list(range(9))
        report = inspect_triangle_self_intersections(positions, indices, max_examples=1)
        self.assertEqual(report["triangle_pair_checks_performed"], 3)
        self.assertEqual(report["self_intersection_pair_count"], 3)
        self.assertEqual(len(report["examples"]), 1)
        self.assertEqual(
            report,
            inspect_triangle_self_intersections(positions, indices, max_examples=1),
            "observer evidence must replay deterministically",
        )

    def test_invalid_geometry_fails_closed_when_scan_is_within_budget(self):
        with self.assertRaisesRegex(MeshSelfIntersectionError, "collapsed by index"):
            inspect_triangle_self_intersections(
                [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                [0, 0, 2],
            )
        with self.assertRaisesRegex(MeshSelfIntersectionError, "geometrically degenerate"):
            inspect_triangle_self_intersections(
                [(0, 0, 0), (1, 0, 0), (2, 0, 0)],
                [0, 1, 2],
            )

    def test_budget_override_has_hard_ceiling(self):
        with self.assertRaisesRegex(MeshSelfIntersectionError, "hard ceiling"):
            inspect_triangle_self_intersections(
                [(0, 0, 0), (1, 0, 0), (0, 1, 0)],
                [0, 1, 2],
                max_triangle_pair_checks=HARD_MAX_TRIANGLE_PAIR_CHECKS + 1,
            )

    def test_donor_provenance_is_explicit_and_receiving_results_are_not_inherited(self):
        self.assertEqual(len(DONOR_PROVENANCE), 2)
        self.assertEqual(DONOR_PROVENANCE[0]["repository"], "mike-axiom-mir/axm-animal-design")
        self.assertEqual(DONOR_PROVENANCE[1]["repository"], "mike-axiom-mir/axm-character-design")
        self.assertNotIn("result", DONOR_PROVENANCE[0])
        self.assertNotIn("result", DONOR_PROVENANCE[1])


if __name__ == "__main__":
    unittest.main()

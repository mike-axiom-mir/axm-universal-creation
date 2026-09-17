import math
import unittest

from axm_uc.mesh_topology import MeshTopologyError, inspect_mesh_topology


TETRA_POSITIONS = [
    (0.0, 0.0, 0.0),
    (1.0, 0.0, 0.0),
    (0.0, 1.0, 0.0),
    (0.0, 0.0, 1.0),
]
TETRA_OUTWARD = [
    0, 2, 1,
    0, 1, 3,
    0, 3, 2,
    1, 2, 3,
]


def _reverse_all(indices):
    reversed_indices = []
    for offset in range(0, len(indices), 3):
        a, b, c = indices[offset:offset + 3]
        reversed_indices.extend((a, c, b))
    return reversed_indices


class MeshClosedOrientationTests(unittest.TestCase):
    def test_opt_in_preserves_default_report_shape(self):
        default_report = inspect_mesh_topology(TETRA_POSITIONS, TETRA_OUTWARD)
        self.assertNotIn("closed_component_orientation", default_report)
        self.assertEqual(default_report["status"], "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE")

        opted_in = inspect_mesh_topology(
            TETRA_POSITIONS,
            TETRA_OUTWARD,
            include_closed_component_orientation=True,
        )
        self.assertIn("closed_component_orientation", opted_in)
        self.assertEqual(opted_in["status"], default_report["status"])
        for key, value in default_report.items():
            self.assertEqual(opted_in[key], value)

    def test_coherent_closed_tetra_reports_positive_signed_orientation(self):
        report = inspect_mesh_topology(
            TETRA_POSITIONS,
            TETRA_OUTWARD,
            include_closed_component_orientation=True,
            orientation_frame_label="fixture-right-handed-xyz",
            orientation_handedness="RIGHT_HANDED",
        )["closed_component_orientation"]

        self.assertTrue(report["inspection_complete"])
        self.assertEqual(report["component_count"], 1)
        self.assertEqual(report["orientable_component_count"], 1)
        component = report["components"][0]
        self.assertEqual(component["closure_state"], "CLOSED")
        self.assertEqual(component["current_shared_edge_orientation_state"], "CONSISTENT")
        self.assertEqual(component["orientability_state"], "ORIENTABLE")
        self.assertEqual(component["diagnostic_face_flip_count"], 0)
        self.assertAlmostEqual(component["current_signed_volume"], 1.0 / 6.0)
        self.assertEqual(component["current_signed_volume_state"], "POSITIVE")
        self.assertAlmostEqual(component["coherent_candidate_signed_volume"], 1.0 / 6.0)
        self.assertEqual(component["coherent_candidate_signed_volume_state"], "POSITIVE")
        self.assertFalse(component["global_sign_normalized"])
        self.assertEqual(report["coordinate_frame"]["label"], "fixture-right-handed-xyz")
        self.assertEqual(report["coordinate_frame"]["handedness"], "RIGHT_HANDED")
        boundary = report["truth_boundary"]
        self.assertTrue(boundary["read_only_observer"])
        self.assertTrue(boundary["parity_solution_diagnostic_only"])
        self.assertFalse(boundary["source_winding_repaired"])
        self.assertFalse(boundary["positive_signed_volume_called_outward"])
        self.assertFalse(boundary["renderer_front_face_or_culling_checked"])
        self.assertFalse(boundary["self_intersection_checked"])
        self.assertFalse(boundary["physical_volume_certified"])

    def test_global_reverse_is_still_orientable_but_signed_volume_changes_sign(self):
        report = inspect_mesh_topology(
            TETRA_POSITIONS,
            _reverse_all(TETRA_OUTWARD),
            include_closed_component_orientation=True,
        )["closed_component_orientation"]["components"][0]

        self.assertEqual(report["closure_state"], "CLOSED")
        self.assertEqual(report["current_shared_edge_orientation_state"], "CONSISTENT")
        self.assertEqual(report["orientability_state"], "ORIENTABLE")
        self.assertEqual(report["diagnostic_face_flip_count"], 0)
        self.assertAlmostEqual(report["current_signed_volume"], -1.0 / 6.0)
        self.assertEqual(report["current_signed_volume_state"], "NEGATIVE")
        self.assertAlmostEqual(report["coherent_candidate_signed_volume"], -1.0 / 6.0)
        self.assertEqual(report["coherent_candidate_signed_volume_state"], "NEGATIVE")

    def test_locally_inconsistent_tetra_is_orientable_without_mutating_input(self):
        inconsistent = [*TETRA_OUTWARD[:-3], 1, 3, 2]
        full_report = inspect_mesh_topology(
            TETRA_POSITIONS,
            inconsistent,
            include_closed_component_orientation=True,
        )
        component = full_report["closed_component_orientation"]["components"][0]

        self.assertEqual(full_report["orientation_conflict_edge_count"], 3)
        self.assertEqual(full_report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(component["closure_state"], "CLOSED")
        self.assertEqual(component["current_shared_edge_orientation_state"], "CONFLICTING")
        self.assertEqual(component["orientability_state"], "ORIENTABLE")
        self.assertEqual(component["diagnostic_face_flip_count"], 1)
        self.assertEqual(component["diagnostic_face_flip_examples"], [3])
        self.assertIsNone(component["current_signed_volume"])
        self.assertEqual(component["current_signed_volume_state"], "NOT_EVALUATED")
        self.assertAlmostEqual(component["coherent_candidate_signed_volume"], 1.0 / 6.0)
        self.assertEqual(component["coherent_candidate_signed_volume_state"], "POSITIVE")
        self.assertFalse(full_report["closed_component_orientation"]["truth_boundary"]["source_geometry_rewritten"])

    def test_closed_non_orientable_projective_plane_fixture_fails_parity_solution(self):
        # Minimal six-vertex / ten-face triangulation of the real projective plane.
        # Every undirected edge has exactly two incident faces, yet no global face
        # orientation can make every shared edge oppose.  Coordinates are only a
        # finite non-degenerate embedding of the abstract indexed complex; this
        # observer does not claim self-intersection freedom.
        faces_1_based = [
            (1, 2, 3), (1, 2, 4), (1, 3, 5), (1, 4, 6), (1, 5, 6),
            (2, 3, 6), (2, 4, 5), (2, 5, 6), (3, 4, 5), (3, 4, 6),
        ]
        indices = [index - 1 for face in faces_1_based for index in face]
        positions = [(float(t), float(t * t), float(t * t * t)) for t in range(1, 7)]

        full_report = inspect_mesh_topology(
            positions,
            indices,
            include_closed_component_orientation=True,
            weld_tolerance=1e-9,
        )
        orientation = full_report["closed_component_orientation"]
        component = orientation["components"][0]

        self.assertEqual(full_report["boundary_edge_count"], 0)
        self.assertEqual(full_report["nonmanifold_edge_count"], 0)
        self.assertGreater(full_report["orientation_conflict_edge_count"], 0)
        self.assertTrue(orientation["inspection_complete"])
        self.assertEqual(orientation["non_orientable_component_count"], 1)
        self.assertEqual(component["closure_state"], "CLOSED")
        self.assertEqual(component["orientability_state"], "NON_ORIENTABLE")
        self.assertIsNone(component["parity_solution_sha256"])
        self.assertIsNone(component["diagnostic_face_flip_count"])
        self.assertIsNone(component["coherent_candidate_signed_volume"])

    def test_open_component_is_explicitly_not_evaluated(self):
        report = inspect_mesh_topology(
            [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)],
            [0, 1, 2, 0, 2, 3],
            include_closed_component_orientation=True,
        )["closed_component_orientation"]
        component = report["components"][0]

        self.assertFalse(report["inspection_complete"])
        self.assertEqual(report["not_evaluated_component_count"], 1)
        self.assertEqual(component["closure_state"], "OPEN")
        self.assertEqual(component["orientability_state"], "NOT_EVALUATED")
        self.assertEqual(component["not_evaluated_reason"], "OPEN_COMPONENT")
        self.assertIsNone(component["current_signed_volume"])
        self.assertIsNone(component["coherent_candidate_signed_volume"])

    def test_component_work_budget_fails_closed_without_partial_parity_verdict(self):
        report = inspect_mesh_topology(
            TETRA_POSITIONS,
            TETRA_OUTWARD,
            include_closed_component_orientation=True,
            orientation_triangle_budget=3,
        )["closed_component_orientation"]
        component = report["components"][0]

        self.assertFalse(report["inspection_complete"])
        self.assertEqual(component["orientability_state"], "NOT_EVALUATED")
        self.assertEqual(component["not_evaluated_reason"], "TRIANGLE_WORK_BUDGET_EXCEEDED")
        self.assertEqual(component["orientation_constraint_edge_count"], 0)
        self.assertIsNone(component["parity_solution_sha256"])
        self.assertIsNone(component["diagnostic_face_flip_count"])
        self.assertIsNone(component["current_signed_volume"])
        self.assertIsNone(component["coherent_candidate_signed_volume"])

    def test_near_zero_volume_is_reported_without_relabelling_orientability(self):
        component = inspect_mesh_topology(
            TETRA_POSITIONS,
            TETRA_OUTWARD,
            include_closed_component_orientation=True,
            orientation_volume_epsilon=1.0,
        )["closed_component_orientation"]["components"][0]

        self.assertEqual(component["orientability_state"], "ORIENTABLE")
        self.assertEqual(component["current_signed_volume_state"], "NEAR_ZERO")
        self.assertEqual(component["coherent_candidate_signed_volume_state"], "NEAR_ZERO")

    def test_collapsed_input_makes_orientation_inspection_incomplete(self):
        report = inspect_mesh_topology(
            [(0, 0, 0), (0.5e-6, 0, 0), (0, 1, 0)],
            [0, 1, 2],
            include_closed_component_orientation=True,
            weld_tolerance=1e-6,
        )["closed_component_orientation"]

        self.assertFalse(report["inspection_complete"])
        self.assertEqual(report["global_not_evaluated_reason"], "COLLAPSED_TRIANGLES_PRESENT")
        self.assertEqual(report["component_count"], 0)

    def test_invalid_orientation_options_fail_closed_only_when_requested(self):
        # Orientation options are dormant when the observer is not requested.
        inspect_mesh_topology(
            TETRA_POSITIONS,
            TETRA_OUTWARD,
            orientation_triangle_budget=0,
            orientation_volume_epsilon=math.nan,
            orientation_frame_label="",
            orientation_handedness="SIDEWAYS",
        )

        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology(
                TETRA_POSITIONS,
                TETRA_OUTWARD,
                include_closed_component_orientation=True,
                orientation_triangle_budget=0,
            )
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology(
                TETRA_POSITIONS,
                TETRA_OUTWARD,
                include_closed_component_orientation=True,
                orientation_volume_epsilon=math.nan,
            )
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology(
                TETRA_POSITIONS,
                TETRA_OUTWARD,
                include_closed_component_orientation=True,
                orientation_frame_label="",
            )
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology(
                TETRA_POSITIONS,
                TETRA_OUTWARD,
                include_closed_component_orientation=True,
                orientation_handedness="SIDEWAYS",
            )


if __name__ == "__main__":
    unittest.main()

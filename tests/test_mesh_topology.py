import math
import unittest

from axm_uc.mesh_topology import MAX_EXAMPLES, MeshTopologyError, inspect_mesh_topology
from axm_uc.procedural_3d import _box_geometry, _cylinder_geometry, _pyramid_geometry


class MeshTopologyTests(unittest.TestCase):
    def test_native_closed_primitives_survive_seam_weld(self):
        builders = (
            ("box", lambda: _box_geometry()),
            ("pyramid", lambda: _pyramid_geometry()),
            ("cylinder", lambda: _cylinder_geometry(12)),
        )
        for name, build in builders:
            with self.subTest(name=name):
                positions, _normals, indices = build()
                report = inspect_mesh_topology(positions, indices)
                self.assertEqual(report["status"], "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE")
                self.assertEqual(report["boundary_edge_count"], 0)
                self.assertEqual(report["nonmanifold_edge_count"], 0)
                self.assertEqual(report["orientation_conflict_edge_count"], 0)
                self.assertEqual(report["collapsed_triangle_count"], 0)
                self.assertTrue(report["closed_by_edge_incidence"])
                self.assertTrue(report["orientation_consistent_by_shared_edge"])
                self.assertTrue(report["all_source_vertices_referenced"])
                self.assertEqual(report["source_vertex_fan_observed_count"], report["referenced_source_vertex_count"])
                self.assertTrue(report["all_referenced_source_vertex_fans_connected"])
                self.assertEqual(report["disconnected_source_vertex_fan_count"], 0)

    def test_box_face_duplicates_weld_to_eight_geometric_vertices(self):
        positions, _normals, indices = _box_geometry()
        report = inspect_mesh_topology(positions, indices)
        self.assertEqual(report["source_vertex_count"], 24)
        self.assertEqual(report["referenced_source_vertex_count"], 24)
        self.assertEqual(report["unreferenced_source_vertex_count"], 0)
        self.assertTrue(report["all_source_vertices_referenced"])
        self.assertEqual(report["examples"]["unreferenced_source_vertices"], [])
        self.assertEqual(report["source_vertex_fan_observed_count"], 24)
        self.assertEqual(report["disconnected_source_vertex_fan_count"], 0)
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])
        self.assertEqual(report["welded_vertex_count"], 8)
        self.assertEqual(report["welded_vertex_reduction"], 16)
        self.assertEqual(report["triangle_count"], 12)
        self.assertEqual(report["edge_count"], 18)

    def test_unreferenced_source_vertex_is_reported_without_changing_edge_or_fan_status(self):
        positions, _normals, indices = _box_geometry()
        positions = [*positions, (99.0, 99.0, 99.0)]
        report = inspect_mesh_topology(positions, indices)

        self.assertEqual(report["status"], "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE")
        self.assertEqual(report["source_vertex_count"], 25)
        self.assertEqual(report["referenced_source_vertex_count"], 24)
        self.assertEqual(report["unreferenced_source_vertex_count"], 1)
        self.assertFalse(report["all_source_vertices_referenced"])
        self.assertEqual(report["examples"]["unreferenced_source_vertices"], [24])
        self.assertEqual(report["source_vertex_fan_observed_count"], 24)
        self.assertEqual(report["disconnected_source_vertex_fan_count"], 0)
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])
        self.assertTrue(report["truth_boundary"]["source_vertex_liveness_checked"])
        self.assertFalse(report["truth_boundary"]["source_vertex_pruning_performed"])

    def test_unreferenced_examples_are_bounded_deterministic_source_indices(self):
        positions, _normals, indices = _box_geometry()
        first_unused = len(positions)
        extra = [(100.0 + index, 0.0, 0.0) for index in range(MAX_EXAMPLES + 4)]
        report = inspect_mesh_topology([*positions, *extra], indices)

        self.assertEqual(report["referenced_source_vertex_count"], first_unused)
        self.assertEqual(report["unreferenced_source_vertex_count"], MAX_EXAMPLES + 4)
        self.assertEqual(
            report["examples"]["unreferenced_source_vertices"],
            list(range(first_unused, first_unused + MAX_EXAMPLES)),
        )
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])

    def test_open_quad_reports_boundary_edges_without_calling_it_invalid(self):
        positions = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        report = inspect_mesh_topology(positions, [0, 1, 2, 0, 2, 3])
        self.assertEqual(report["status"], "OPEN_EDGE_MANIFOLD_CANDIDATE")
        self.assertEqual(report["boundary_edge_count"], 4)
        self.assertEqual(report["nonmanifold_edge_count"], 0)
        self.assertEqual(report["orientation_conflict_edge_count"], 0)
        self.assertFalse(report["closed_by_edge_incidence"])
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])

    def test_two_closed_tetrahedra_sharing_only_one_source_vertex_expose_bow_tie_fan(self):
        positions = [
            (0, 0, 0),
            (1, 0, 0), (0, 1, 0), (0, 0, 1),
            (-1, 0, 0), (0, -1, 0), (0, 0, -1),
        ]
        indices = [
            0, 2, 1,
            0, 1, 3,
            1, 2, 3,
            2, 0, 3,
            0, 5, 4,
            0, 4, 6,
            4, 5, 6,
            5, 0, 6,
        ]
        report = inspect_mesh_topology(positions, indices)

        self.assertEqual(report["status"], "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE")
        self.assertEqual(report["boundary_edge_count"], 0)
        self.assertEqual(report["nonmanifold_edge_count"], 0)
        self.assertEqual(report["orientation_conflict_edge_count"], 0)
        self.assertEqual(report["triangle_component_count"], 2)
        self.assertFalse(report["all_referenced_source_vertex_fans_connected"])
        self.assertEqual(report["source_vertex_fan_observed_count"], 7)
        self.assertEqual(report["disconnected_source_vertex_fan_count"], 1)
        self.assertEqual(report["max_source_vertex_fan_components"], 2)
        self.assertEqual(
            report["examples"]["disconnected_source_vertex_fans"],
            [{"vertex": 0, "incident_triangle_count": 6, "fan_component_count": 2}],
        )

    def test_high_incidence_source_edge_uses_one_connected_fan_without_pairwise_expansion(self):
        face_count = 1024
        positions = [(0.0, 0.0, 0.0), (1.0, 0.0, 0.0)]
        positions.extend((0.5, float(index + 1), 1.0) for index in range(face_count))
        indices = []
        for index in range(face_count):
            indices.extend((0, 1, index + 2))

        report = inspect_mesh_topology(positions, indices)
        self.assertEqual(report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(report["nonmanifold_edge_count"], 1)
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])
        self.assertEqual(report["max_source_vertex_fan_components"], 1)
        self.assertEqual(report["source_vertex_fan_observed_count"], face_count + 2)

    def test_exact_index_collapsed_triangle_fails_closed_for_fan_completeness(self):
        report = inspect_mesh_topology([(0, 0, 0), (1, 0, 0)], [0, 0, 1])
        self.assertEqual(report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(report["collapsed_triangle_count"], 1)
        self.assertEqual(report["referenced_source_vertex_count"], 2)
        self.assertEqual(report["source_vertex_fan_observed_count"], 0)
        self.assertFalse(report["all_referenced_source_vertex_fans_connected"])

    def test_three_faces_on_one_edge_report_nonmanifold_edge(self):
        positions = [
            (0, 0, 0), (1, 0, 0),
            (0, 1, 0), (0, -1, 0), (0, 0, 1),
        ]
        report = inspect_mesh_topology(positions, [0, 1, 2, 1, 0, 3, 0, 1, 4])
        self.assertEqual(report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(report["nonmanifold_edge_count"], 1)
        self.assertIn([0, 1], report["examples"]["nonmanifold_edges"])

    def test_same_direction_shared_edge_reports_orientation_conflict(self):
        positions = [(0, 0, 0), (1, 0, 0), (0, 1, 0), (0, -1, 0)]
        report = inspect_mesh_topology(positions, [0, 1, 2, 0, 1, 3])
        self.assertEqual(report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(report["orientation_conflict_edge_count"], 1)
        self.assertIn([0, 1], report["examples"]["orientation_conflict_edges"])

    def test_tolerance_weld_can_expose_collapsed_triangle(self):
        positions = [(0, 0, 0), (0.5e-6, 0, 0), (0, 1, 0)]
        report = inspect_mesh_topology(positions, [0, 1, 2], weld_tolerance=1e-6)
        self.assertEqual(report["status"], "INVALID_EDGE_TOPOLOGY")
        self.assertEqual(report["collapsed_triangle_count"], 1)
        self.assertEqual(report["examples"]["collapsed_triangles"], [0])
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])

    def test_representative_weld_does_not_chain_across_wider_seam(self):
        positions = [(0, 0, 0), (0.75e-6, 0, 0), (1.5e-6, 0, 0), (0, 1, 0)]
        report = inspect_mesh_topology(positions, [0, 2, 3], weld_tolerance=1e-6)
        self.assertEqual(report["welded_vertex_count"], 3)
        self.assertEqual(report["collapsed_triangle_count"], 0)
        self.assertEqual(report["referenced_source_vertex_count"], 3)
        self.assertEqual(report["unreferenced_source_vertex_count"], 1)
        self.assertEqual(report["examples"]["unreferenced_source_vertices"], [1])
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])

    def test_reports_multiple_disconnected_triangle_components(self):
        positions = [
            (0, 0, 0), (1, 0, 0), (0, 1, 0),
            (10, 0, 0), (11, 0, 0), (10, 1, 0),
        ]
        report = inspect_mesh_topology(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["triangle_component_count"], 2)
        self.assertTrue(report["all_referenced_source_vertex_fans_connected"])

    def test_truth_boundary_stays_structural(self):
        report = inspect_mesh_topology([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 2])
        boundary = report["truth_boundary"]
        self.assertTrue(boundary["source_vertex_liveness_checked"])
        self.assertFalse(boundary["source_vertex_pruning_performed"])
        self.assertTrue(boundary["source_indexed_vertex_fan_connectivity_checked"])
        self.assertTrue(boundary["source_index_collapsed_triangles_excluded_from_vertex_fans"])
        self.assertTrue(boundary["fan_work_bounded_by_source_face_edge_incidence"])
        self.assertFalse(boundary["vertex_manifoldness_checked"])
        self.assertFalse(boundary["seam_welded_geometric_vertex_manifoldness_checked"])
        self.assertFalse(boundary["self_intersection_checked"])
        self.assertFalse(boundary["deformation_quality_checked"])
        self.assertFalse(boundary["collision_suitability_checked"])
        self.assertFalse(boundary["visual_quality_checked"])

    def test_rejects_invalid_inputs(self):
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology([], [])
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1])
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 3])
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology([(math.nan, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 2])
        with self.assertRaises(MeshTopologyError):
            inspect_mesh_topology([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 2], weld_tolerance=0)


if __name__ == "__main__":
    unittest.main()

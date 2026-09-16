import math
import unittest

from axm_uc.mesh_topology import MeshTopologyError, inspect_mesh_topology
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

    def test_box_face_duplicates_weld_to_eight_geometric_vertices(self):
        positions, _normals, indices = _box_geometry()
        report = inspect_mesh_topology(positions, indices)
        self.assertEqual(report["source_vertex_count"], 24)
        self.assertEqual(report["welded_vertex_count"], 8)
        self.assertEqual(report["welded_vertex_reduction"], 16)
        self.assertEqual(report["triangle_count"], 12)
        self.assertEqual(report["edge_count"], 18)

    def test_open_quad_reports_boundary_edges_without_calling_it_invalid(self):
        positions = [(0, 0, 0), (1, 0, 0), (1, 1, 0), (0, 1, 0)]
        report = inspect_mesh_topology(positions, [0, 1, 2, 0, 2, 3])
        self.assertEqual(report["status"], "OPEN_EDGE_MANIFOLD_CANDIDATE")
        self.assertEqual(report["boundary_edge_count"], 4)
        self.assertEqual(report["nonmanifold_edge_count"], 0)
        self.assertEqual(report["orientation_conflict_edge_count"], 0)
        self.assertFalse(report["closed_by_edge_incidence"])

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

    def test_representative_weld_does_not_chain_across_wider_seam(self):
        positions = [(0, 0, 0), (0.75e-6, 0, 0), (1.5e-6, 0, 0), (0, 1, 0)]
        report = inspect_mesh_topology(positions, [0, 2, 3], weld_tolerance=1e-6)
        self.assertEqual(report["welded_vertex_count"], 3)
        self.assertEqual(report["collapsed_triangle_count"], 0)

    def test_reports_multiple_disconnected_triangle_components(self):
        positions = [
            (0, 0, 0), (1, 0, 0), (0, 1, 0),
            (10, 0, 0), (11, 0, 0), (10, 1, 0),
        ]
        report = inspect_mesh_topology(positions, [0, 1, 2, 3, 4, 5])
        self.assertEqual(report["triangle_component_count"], 2)

    def test_truth_boundary_stays_structural(self):
        report = inspect_mesh_topology([(0, 0, 0), (1, 0, 0), (0, 1, 0)], [0, 1, 2])
        boundary = report["truth_boundary"]
        self.assertFalse(boundary["vertex_manifoldness_checked"])
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

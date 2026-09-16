from __future__ import annotations

import copy
import hashlib
import math
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.mesh_precision_cutter import MeshPrecisionCutterError
from axm_uc.oriented_mesh_precision_cutter import (
    ORIENTED_MESH_CUTTER_SCHEMA,
    build_oriented_source_mesh_cut,
)
from axm_uc.precision_cutter import build_cut
from axm_uc.procedural_3d import publish_glb, verify_glb


def material() -> dict:
    return {"color": "#527A91FF", "metallic": 0.35, "roughness": 0.42}


def _matmul(a, b):
    return [
        [sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3)]
        for row in range(3)
    ]


def rotation_matrix(rx=0.37, ry=-0.61, rz=0.29):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    x = [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]]
    y = [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]]
    z = [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]]
    return _matmul(z, _matmul(y, x))


def transform_vector(matrix, vector):
    return [sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3)]


def transformed_box_surface(
    *, size=(4.0, 2.0, 3.0), translation=(5.0, 2.0, -1.0), rotation=None
):
    rotation = rotation or rotation_matrix()
    sx, sy, sz = size
    built = build_cut(
        {
            "schema": "axm.precision-cutter/v0.1",
            "name": "Local stock",
            "operation": "profile-cut",
            "thickness": sy,
            "material": material(),
            "profile": [
                [-sx / 2.0, -sz / 2.0],
                [sx / 2.0, -sz / 2.0],
                [sx / 2.0, sz / 2.0],
                [-sx / 2.0, sz / 2.0],
            ],
        }
    )
    surface = copy.deepcopy(built["surface_specification"])
    surface["name"] = "Rotated existing stock"
    primitive = surface["primitives"][0]
    primitive["positions"] = [
        [
            transform_vector(rotation, point)[axis] + translation[axis]
            for axis in range(3)
        ]
        for point in primitive["positions"]
    ]
    primitive["normals"] = [
        transform_vector(rotation, normal) for normal in primitive["normals"]
    ]
    return surface


def frame_axes(rotation=None):
    rotation = rotation or rotation_matrix()
    return [
        [rotation[row][column] for row in range(3)] for column in range(3)
    ]


def hole_spec(axis_vector, center=(5.0, 2.0, -1.0)):
    return {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "name": "Rotated source hole",
        "operation": "round-through-hole",
        "axis_vector": list(axis_vector),
        "center": list(center),
        "radius": 0.42,
        "segments": 24,
        "kerf": 0.04,
    }


def notch_spec(axis_vector, center=(5.0, 2.0, -1.0), side="u-max"):
    return {
        "schema": ORIENTED_MESH_CUTTER_SCHEMA,
        "name": "Rotated source notch",
        "operation": "box-notch",
        "axis_vector": list(axis_vector),
        "center": list(center),
        "side": side,
        "span": 0.72,
        "depth": 0.38,
        "kerf": 0.06,
    }


class OrientedMeshPrecisionCutterTests(unittest.TestCase):
    def _source(self, directory, *, rotation=None):
        source = Path(directory) / "rotated-source.glb"
        publish_glb(source, transformed_box_surface(rotation=rotation))
        return source

    def test_live_route_cuts_rotated_existing_glb_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            original = source.read_bytes()
            target = Path(td) / "cut.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-oriented-hole",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "specification": hole_spec(axes[1]),
                        "expected_source_sha256": hashlib.sha256(original).hexdigest(),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(
                body["truth_status"],
                "VALIDATED_ORIENTED_EXISTING_MESH_PRECISION_CUT",
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(body["source"]["unchanged_after_publication"])
            self.assertTrue(body["glb_validation"]["passed"])
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertEqual(
                body["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertTrue(
                body["truth_boundary"]["rotated_translated_source_supported"]
            )
            self.assertFalse(body["truth_boundary"]["full_arbitrary_mesh_csg"])

    def test_rotated_source_hole_works_on_all_three_proven_frame_axes(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            for axis_vector in axes:
                with self.subTest(axis_vector=axis_vector):
                    built = build_oriented_source_mesh_cut(
                        source, hole_spec(axis_vector)
                    )
                    self.assertEqual(
                        built["output_topology"]["status"],
                        "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
                    )
                    self.assertAlmostEqual(built["metrics"]["axis_alignment"], 1.0, places=6)
                    self.assertGreater(
                        built["metrics"]["removed_volume_by_closed_mesh"], 0
                    )
                    self.assertTrue(
                        built["source"]["recognition"]["all_eight_corners_observed"]
                    )

    def test_rotated_box_notch_uses_source_local_cross_section(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            for side in ("u-min", "u-max", "v-min", "v-max"):
                with self.subTest(side=side):
                    built = build_oriented_source_mesh_cut(
                        source, notch_spec(axes[1], side=side)
                    )
                    self.assertEqual(
                        built["output_topology"]["status"],
                        "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
                    )
                    self.assertAlmostEqual(built["metrics"]["effective_span"], 0.78)
                    self.assertAlmostEqual(built["metrics"]["effective_depth"], 0.41)
                    self.assertGreater(built["metrics"]["removed_volume"], 0)

    def test_diagonal_axis_relative_to_source_frame_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            diagonal = [axes[0][index] + axes[1][index] for index in range(3)]
            length = math.sqrt(sum(value * value for value in diagonal))
            diagonal = [value / length for value in diagonal]
            with self.assertRaises(MeshPrecisionCutterError):
                build_oriented_source_mesh_cut(source, hole_spec(diagonal))

    def test_same_rotated_source_and_recipe_replay_identically(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            machine = UniversalCreationMachine(ROOT)
            bodies = []
            for name in ("one.glb", "two.glb"):
                target = Path(td) / name
                result = machine.create(
                    {
                        "kind": "mesh-precision-cut-3d",
                        "inputs": {
                            "source_path": str(source),
                            "path": str(target),
                            "specification": hole_spec(axes[2]),
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                bodies.append(target.read_bytes())
            self.assertEqual(bodies[0], bodies[1])

    def test_v03_does_not_claim_general_chaining_or_arbitrary_csg(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            source = self._source(td, rotation=rotation)
            built = build_oriented_source_mesh_cut(
                source, hole_spec(frame_axes(rotation)[0])
            )
            truth = built["truth_boundary"]
            self.assertEqual(
                truth["output_to_next_arbitrary_cut_chaining"],
                "NOT_YET_SUPPORTED",
            )
            self.assertEqual(
                truth["arbitrary_angle_relative_to_source_frame"],
                "NOT_SUPPORTED",
            )
            self.assertFalse(truth["full_arbitrary_mesh_csg"])


if __name__ == "__main__":
    unittest.main()

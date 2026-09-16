from __future__ import annotations

import hashlib
import json
import math
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.mesh_general_hole_chain import (
    GENERAL_HOLE_CHAIN_SCHEMA,
    build_general_hole_chain,
)
from axm_uc.mesh_hole_fabrication_chain import HOLE_CHAIN_SCHEMA
from axm_uc.mesh_precision_cutter import MeshPrecisionCutterError
from axm_uc.precision_cutter import build_cut
from axm_uc.procedural_3d import publish_glb, verify_glb


def material() -> dict:
    return {"color": "#527A91FF", "metallic": 0.35, "roughness": 0.42}


def box_spec(size=(6.0, 2.0, 5.0), translation=(0.0, 0.0, 0.0)) -> dict:
    return {
        "schema": "axm.procedural-3d/v0.1",
        "name": "General sweep stock",
        "primitives": [
            {
                "id": "stock",
                "type": "box",
                "size": list(size),
                "translation": list(translation),
                "material": material(),
            }
        ],
    }


def _matmul(a, b):
    return [
        [sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3)]
        for row in range(3)
    ]


def rotation_matrix(rx=0.33, ry=-0.51, rz=0.27):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    x = [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]]
    y = [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]]
    z = [[cz, -sz, 0.0], [sz, cz, 0.0], [0.0, 0.0, 1.0]]
    return _matmul(z, _matmul(y, x))


def transform_vector(matrix, vector):
    return [
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    ]


def transformed_box_surface(
    size=(6.0, 2.0, 5.0), translation=(2.0, -1.0, 3.0), rotation=None
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
    surface = json.loads(json.dumps(built["surface_specification"]))
    primitive = surface["primitives"][0]
    primitive["positions"] = [
        [
            transform_vector(rotation, point)[axis] + translation[axis]
            for axis in range(3)
        ]
        for point in primitive["positions"]
    ]
    primitive["normals"] = [transform_vector(rotation, normal) for normal in primitive["normals"]]
    surface["name"] = "Rotated general sweep stock"
    return surface


def frame_axes(rotation):
    return [[rotation[row][column] for row in range(3)] for column in range(3)]


def world_point(translation, axes, u, y, v):
    return [
        translation[index]
        + axes[0][index] * u
        + axes[1][index] * y
        + axes[2][index] * v
        for index in range(3)
    ]


def hole(hole_id, center, radius=0.3, segments=16, kerf=0.0):
    return {
        "id": hole_id,
        "center": list(center),
        "radius": radius,
        "segments": segments,
        "kerf": kerf,
    }


def v06_spec(name, holes, axis_vector=(0.0, 1.0, 0.0)):
    return {
        "schema": GENERAL_HOLE_CHAIN_SCHEMA,
        "name": name,
        "axis_vector": list(axis_vector),
        "holes": list(holes),
    }


def v05_spec(name, holes, axis_vector=(0.0, 1.0, 0.0)):
    return {
        "schema": HOLE_CHAIN_SCHEMA,
        "name": name,
        "axis_vector": list(axis_vector),
        "holes": list(holes),
    }


class GeneralHoleSweepTests(unittest.TestCase):
    def _source(self, directory: str) -> Path:
        source = Path(directory) / "source.glb"
        publish_glb(source, box_spec())
        return source

    def test_nonseparable_diagonal_holes_are_now_closed_and_valid(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            target = Path(td) / "diagonal.glb"
            receipt = Path(td) / "diagonal.json"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "specification": v06_spec(
                            "Diagonal holes",
                            [
                                hole("a", (-0.25, 0.0, -0.25), radius=0.3),
                                hole("b", (0.25, 0.0, 0.25), radius=0.3),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(
                body["truth_status"],
                "VALIDATED_HASH_LINKED_GENERAL_SAME_AXIS_HOLE_SWEEP",
            )
            self.assertEqual(body["cumulative_hole_count"], 2)
            self.assertTrue(body["glb_validation"]["passed"])
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertEqual(
                body["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertFalse(
                body["truth_boundary"]["projection_separability_required"]
            )
            self.assertGreater(body["geometry"]["sweep_strips"], 1)

    def test_three_arbitrary_nonoverlapping_same_axis_holes_match_volume_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            built = build_general_hole_chain(
                source,
                v06_spec(
                    "Three sweep holes",
                    [
                        hole("a", (-0.55, 0.0, -0.95), radius=0.34, segments=18),
                        hole("b", (0.28, 0.0, 1.05), radius=0.43, segments=22),
                        hole("c", (1.25, 0.0, -0.35), radius=0.27, segments=14),
                    ],
                ),
            )
            self.assertEqual(
                built["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            expected = (
                built["metrics"]["source_volume"]
                - built["metrics"]["polygonized_removed_area"]
                * built["metrics"]["fabrication_thickness"]
            )
            self.assertAlmostEqual(built["metrics"]["output_volume"], expected, places=5)

    def test_v05_lineage_is_verified_then_upgraded_to_v06(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            old_target = Path(td) / "v05.glb"
            old_receipt = Path(td) / "v05.json"
            old = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(old_target),
                        "receipt_path": str(old_receipt),
                        "specification": v05_spec(
                            "Old separable pair",
                            [
                                hole("left", (-1.25, 0.0, 0.0), radius=0.32),
                                hole("right", (1.25, 0.0, 0.2), radius=0.32),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(old["type"], "CREATION_RESULT", old)
            old_body = old["result"]
            new_target = Path(td) / "v06.glb"
            new_receipt = Path(td) / "v06.json"
            upgraded = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(old_target),
                        "lineage_path": str(old_receipt),
                        "expected_source_sha256": old_body["sha256"],
                        "expected_lineage_sha256": old_body["lineage_sha256"],
                        "path": str(new_target),
                        "receipt_path": str(new_receipt),
                        "specification": v06_spec(
                            "Upgrade and append",
                            [hole("diagonal", (0.0, 0.0, 0.55), radius=0.26, segments=20)],
                        ),
                    },
                }
            )
            self.assertEqual(upgraded["type"], "CREATION_RESULT", upgraded)
            body = upgraded["result"]
            self.assertTrue(body["upgraded_from_v05"])
            self.assertEqual(body["parent_lineage_sha256"], old_body["lineage_sha256"])
            self.assertEqual(body["cumulative_hole_count"], 3)
            lineage = json.loads(new_receipt.read_text(encoding="utf-8"))
            self.assertEqual(lineage["schema"], "axm.mesh-hole-fabrication-lineage/v0.6")

    def test_v06_resume_rebuilds_exact_prior_sweep_before_append(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            first_target = Path(td) / "first.glb"
            first_receipt = Path(td) / "first.json"
            first = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(first_target),
                        "receipt_path": str(first_receipt),
                        "specification": v06_spec(
                            "First sweep",
                            [
                                hole("a", (-0.25, 0.0, -0.25), radius=0.3),
                                hole("b", (0.25, 0.0, 0.25), radius=0.3),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            first_body = first["result"]
            second = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(first_target),
                        "lineage_path": str(first_receipt),
                        "expected_source_sha256": first_body["sha256"],
                        "expected_lineage_sha256": first_body["lineage_sha256"],
                        "path": str(Path(td) / "second.glb"),
                        "receipt_path": str(Path(td) / "second.json"),
                        "specification": v06_spec(
                            "Second sweep",
                            [hole("c", (1.15, 0.0, -0.85), radius=0.25, segments=18)],
                        ),
                    },
                }
            )
            self.assertEqual(second["type"], "CREATION_RESULT", second)
            self.assertTrue(
                second["result"]["truth_boundary"]["previous_output_recompiled_before_resume"]
            )

    def test_rotated_nonseparable_layout_uses_same_sweep_contract(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            translation = (2.0, -1.0, 3.0)
            source = Path(td) / "rotated.glb"
            publish_glb(
                source,
                transformed_box_surface(translation=translation, rotation=rotation),
            )
            centers = [
                world_point(translation, axes, -0.25, 0.0, -0.25),
                world_point(translation, axes, 0.25, 0.0, 0.25),
            ]
            built = build_general_hole_chain(
                source,
                v06_spec(
                    "Rotated diagonal sweep",
                    [hole("a", centers[0]), hole("b", centers[1])],
                    axis_vector=axes[1],
                ),
            )
            self.assertEqual(
                built["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )

    def test_overlap_still_fails_and_tampered_v06_receipt_cannot_resume(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            with self.assertRaises(MeshPrecisionCutterError):
                build_general_hole_chain(
                    source,
                    v06_spec(
                        "Overlap",
                        [
                            hole("a", (-0.15, 0.0, 0.0), radius=0.35),
                            hole("b", (0.15, 0.0, 0.0), radius=0.35),
                        ],
                    ),
                )
            machine = UniversalCreationMachine(ROOT)
            target = Path(td) / "good.glb"
            receipt = Path(td) / "good.json"
            first = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "specification": v06_spec(
                            "Good",
                            [hole("a", (-0.25, 0.0, -0.25)), hole("b", (0.25, 0.0, 0.25))],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            tampered = json.loads(receipt.read_text(encoding="utf-8"))
            tampered["holes"][0]["requested_radius"] += 0.001
            receipt.write_text(json.dumps(tampered), encoding="utf-8")
            refused = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(target),
                        "lineage_path": str(receipt),
                        "path": str(Path(td) / "refused.glb"),
                        "specification": v06_spec(
                            "Refused",
                            [hole("c", (1.0, 0.0, 1.0), radius=0.2)],
                        ),
                    },
                }
            )
            self.assertEqual(refused["type"], "CREATION_ERROR", refused)

    def test_same_general_sweep_replays_identically(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            spec = v06_spec(
                "Replay",
                [hole("a", (-0.25, 0.0, -0.25)), hole("b", (0.25, 0.0, 0.25))],
            )
            bodies = []
            receipts = []
            for name in ("one", "two"):
                target = Path(td) / f"{name}.glb"
                receipt = Path(td) / f"{name}.json"
                result = machine.create(
                    {
                        "kind": "mesh-hole-sweep-chain",
                        "inputs": {
                            "source_path": str(source),
                            "path": str(target),
                            "receipt_path": str(receipt),
                            "specification": spec,
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                bodies.append(target.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(receipts[0], receipts[1])


if __name__ == "__main__":
    unittest.main()

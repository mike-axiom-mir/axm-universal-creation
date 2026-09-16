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
from axm_uc.mesh_hole_fabrication_chain import (
    HOLE_CHAIN_SCHEMA,
    build_hole_fabrication_chain,
)
from axm_uc.mesh_precision_cutter import MeshPrecisionCutterError
from axm_uc.precision_cutter import build_cut
from axm_uc.procedural_3d import publish_glb, verify_glb


def material() -> dict:
    return {"color": "#527A91FF", "metallic": 0.35, "roughness": 0.42}


def box_spec(*, size=(6.0, 2.0, 5.0), translation=(0.0, 0.0, 0.0)) -> dict:
    return {
        "schema": "axm.procedural-3d/v0.1",
        "name": "Hole-chain stock",
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


def rotation_matrix(rx=0.31, ry=-0.47, rz=0.22):
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
    *, size=(6.0, 2.0, 5.0), translation=(2.0, -1.0, 3.0), rotation=None
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
    surface["name"] = "Rotated hole-chain stock"
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
    return [[rotation[row][column] for row in range(3)] for column in range(3)]


def world_point(translation, axes, u, y, v):
    return [
        translation[index]
        + axes[0][index] * u
        + axes[1][index] * y
        + axes[2][index] * v
        for index in range(3)
    ]


def hole(hole_id, center, radius=0.36, segments=20, kerf=0.04):
    return {
        "id": hole_id,
        "center": list(center),
        "radius": radius,
        "segments": segments,
        "kerf": kerf,
    }


def chain_spec(name, holes, axis_vector=(0.0, 1.0, 0.0)):
    return {
        "schema": HOLE_CHAIN_SCHEMA,
        "name": name,
        "axis_vector": list(axis_vector),
        "holes": list(holes),
    }


class MeshHoleFabricationChainTests(unittest.TestCase):
    def _source(self, directory: str) -> Path:
        source = Path(directory) / "source.glb"
        publish_glb(source, box_spec())
        return source

    def test_live_route_builds_two_holes_and_writes_hash_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            original = source.read_bytes()
            target = Path(td) / "two-holes.glb"
            receipt = Path(td) / "two-holes.lineage.json"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "expected_source_sha256": hashlib.sha256(original).hexdigest(),
                        "specification": chain_spec(
                            "Two stable holes",
                            [
                                hole("left", (-1.45, 0.0, -0.2), segments=18),
                                hole("right", (1.35, 0.0, 0.45), radius=0.42, segments=24),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(
                body["truth_status"],
                "VALIDATED_HASH_LINKED_MULTI_HOLE_FABRICATION_CHAIN",
            )
            self.assertEqual(body["cumulative_hole_count"], 2)
            self.assertEqual(body["partition_axis"], "u")
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(body["source_unchanged_after_publication"])
            self.assertTrue(body["glb_validation"]["passed"])
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertEqual(
                body["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            lineage = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(len(lineage["holes"]), 2)
            self.assertEqual(len(lineage["steps"]), 2)
            self.assertEqual(lineage["lineage_sha256"], body["lineage_sha256"])

    def test_resume_rebuilds_prior_bytes_then_appends_third_hole(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            first_target = Path(td) / "stage-one.glb"
            first_receipt = Path(td) / "stage-one.json"
            first = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(first_target),
                        "receipt_path": str(first_receipt),
                        "specification": chain_spec(
                            "Stage one",
                            [
                                hole("left", (-1.5, 0.0, -0.1)),
                                hole("right", (1.5, 0.0, 0.25)),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            first_body = first["result"]
            first_lineage = json.loads(first_receipt.read_text(encoding="utf-8"))
            first_hole_receipt = dict(first_lineage["holes"][0])

            second_target = Path(td) / "stage-two.glb"
            second_receipt = Path(td) / "stage-two.json"
            second = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(first_target),
                        "lineage_path": str(first_receipt),
                        "expected_lineage_sha256": first_body["lineage_sha256"],
                        "expected_source_sha256": first_body["sha256"],
                        "path": str(second_target),
                        "receipt_path": str(second_receipt),
                        "specification": chain_spec(
                            "Stage two",
                            [hole("middle", (0.0, 0.0, 1.1), radius=0.28, segments=16)],
                        ),
                    },
                }
            )
            self.assertEqual(second["type"], "CREATION_RESULT", second)
            body = second["result"]
            self.assertEqual(body["cumulative_hole_count"], 3)
            self.assertEqual(body["parent_lineage_sha256"], first_body["lineage_sha256"])
            lineage = json.loads(second_receipt.read_text(encoding="utf-8"))
            self.assertEqual(lineage["holes"][0], first_hole_receipt)
            self.assertTrue(
                lineage["truth_boundary"]["previous_output_recompiled_before_resume"]
            )
            self.assertTrue(
                lineage["truth_boundary"]["inner_hole_boundaries_stable_when_new_holes_are_appended"]
            )

    def test_v_partition_handles_holes_whose_u_projections_overlap(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            built = build_hole_fabrication_chain(
                source,
                chain_spec(
                    "V partition",
                    [
                        hole("low", (0.0, 0.0, -1.25), radius=0.34),
                        hole("high", (0.12, 0.0, 1.2), radius=0.34, segments=24),
                    ],
                ),
            )
            self.assertEqual(built["partition_axis"], "v")
            self.assertEqual(
                built["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertGreater(built["metrics"]["removed_volume"], 0.0)

    def test_rotated_source_uses_proven_local_frame_for_multiple_holes(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            translation = (2.0, -1.0, 3.0)
            source = Path(td) / "rotated.glb"
            publish_glb(
                source,
                transformed_box_surface(rotation=rotation, translation=translation),
            )
            centers = [
                world_point(translation, axes, -1.45, 0.0, -0.25),
                world_point(translation, axes, 1.35, 0.0, 0.4),
            ]
            built = build_hole_fabrication_chain(
                source,
                chain_spec(
                    "Rotated multi-hole stock",
                    [hole("a", centers[0]), hole("b", centers[1], radius=0.4)],
                    axis_vector=axes[1],
                ),
            )
            self.assertEqual(
                built["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertTrue(
                built["truth_boundary"]["rotated_translated_source_supported"]
            )

    def test_tampered_artifact_or_receipt_cannot_resume(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            target = Path(td) / "base.glb"
            receipt = Path(td) / "base.json"
            first = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "specification": chain_spec(
                            "Base holes",
                            [hole("a", (-1.3, 0.0, 0.0)), hole("b", (1.3, 0.0, 0.2))],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            original_target = target.read_bytes()
            original_receipt = receipt.read_bytes()

            tampered = bytearray(original_target)
            tampered[-1] ^= 1
            target.write_bytes(bytes(tampered))
            result = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(target),
                        "lineage_path": str(receipt),
                        "path": str(Path(td) / "refused-a.glb"),
                        "specification": chain_spec(
                            "Refuse artifact",
                            [hole("c", (0.0, 0.0, 1.1), radius=0.25)],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)

            target.write_bytes(original_target)
            value = json.loads(original_receipt.decode("utf-8"))
            value["holes"][0]["requested_radius"] += 0.001
            receipt.write_text(json.dumps(value), encoding="utf-8")
            result = machine.create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(target),
                        "lineage_path": str(receipt),
                        "path": str(Path(td) / "refused-b.glb"),
                        "specification": chain_spec(
                            "Refuse receipt",
                            [hole("c", (0.0, 0.0, 1.1), radius=0.25)],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)

    def test_overlap_and_nonseparable_layouts_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            with self.assertRaises(MeshPrecisionCutterError):
                build_hole_fabrication_chain(
                    source,
                    chain_spec(
                        "Overlap",
                        [
                            hole("a", (-0.2, 0.0, 0.0), radius=0.4),
                            hole("b", (0.2, 0.0, 0.0), radius=0.4),
                        ],
                    ),
                )
            with self.assertRaises(MeshPrecisionCutterError):
                build_hole_fabrication_chain(
                    source,
                    chain_spec(
                        "Nonseparable",
                        [
                            hole("a", (-0.25, 0.0, -0.25), radius=0.3),
                            hole("b", (0.25, 0.0, 0.25), radius=0.3),
                        ],
                    ),
                )

    def test_same_request_replays_to_identical_glb_and_lineage(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            bodies = []
            receipts = []
            specification = chain_spec(
                "Deterministic holes",
                [hole("left", (-1.4, 0.0, 0.0)), hole("right", (1.4, 0.0, 0.3))],
            )
            for prefix in ("one", "two"):
                target = Path(td) / f"{prefix}.glb"
                receipt = Path(td) / f"{prefix}.json"
                result = machine.create(
                    {
                        "kind": "mesh-laser-hole-chain",
                        "inputs": {
                            "source_path": str(source),
                            "path": str(target),
                            "receipt_path": str(receipt),
                            "specification": specification,
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                bodies.append(target.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(bodies[0], bodies[1])
            self.assertEqual(receipts[0], receipts[1])

    def test_machine_body_receipt_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            forbidden = ROOT / "forbidden-hole-lineage.json"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-hole-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(Path(td) / "safe.glb"),
                        "receipt_path": str(forbidden),
                        "specification": chain_spec(
                            "Protected receipt",
                            [hole("a", (0.0, 0.0, 0.0))],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()

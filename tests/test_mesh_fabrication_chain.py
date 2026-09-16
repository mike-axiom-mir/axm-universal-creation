from __future__ import annotations

import copy
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
from axm_uc.mesh_fabrication_chain import (
    FABRICATION_CHAIN_SCHEMA,
    build_fabrication_chain,
)
from axm_uc.mesh_precision_cutter import MeshPrecisionCutterError
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
    return [
        sum(matrix[row][column] * vector[column] for column in range(3))
        for row in range(3)
    ]


def transformed_box_surface(
    *, size=(4.0, 2.0, 3.0), translation=(5.0, 2.0, -1.0), rotation=None
):
    rotation = rotation or rotation_matrix()
    sx, sy, sz = size
    built = build_cut(
        {
            "schema": "axm.precision-cutter/v0.1",
            "name": "Chain stock",
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
    surface["name"] = "Rotated chain source"
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


def world_point(local, rotation=None, translation=(5.0, 2.0, -1.0)):
    rotation = rotation or rotation_matrix()
    moved = transform_vector(rotation, local)
    return [moved[index] + translation[index] for index in range(3)]


def notch(cut_id, local_center, side, *, span=0.62, depth=0.34, kerf=0.04, rotation=None):
    return {
        "id": cut_id,
        "operation": "box-notch",
        "center": world_point(local_center, rotation=rotation),
        "side": side,
        "span": span,
        "depth": depth,
        "kerf": kerf,
    }


def chain_spec(name, axis_vector, cuts):
    return {
        "schema": FABRICATION_CHAIN_SCHEMA,
        "name": name,
        "axis_vector": list(axis_vector),
        "cuts": cuts,
    }


class MeshFabricationChainTests(unittest.TestCase):
    def _source(self, directory, *, rotation=None):
        source = Path(directory) / "source.glb"
        publish_glb(source, transformed_box_surface(rotation=rotation))
        return source

    def test_live_route_builds_two_cut_chain_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            original = source.read_bytes()
            target = Path(td) / "stage-one.glb"
            receipt = Path(td) / "stage-one.fabrication.json"
            spec = chain_spec(
                "Two notch chain",
                axes[1],
                [
                    notch("bottom-a", (-0.8, 0.0, 0.0), "v-min", rotation=rotation),
                    notch("right-a", (0.0, 0.0, 0.45), "u-max", rotation=rotation),
                ],
            )
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "specification": spec,
                        "expected_source_sha256": hashlib.sha256(original).hexdigest(),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(
                body["truth_status"], "VALIDATED_HASH_LINKED_FABRICATION_CHAIN"
            )
            self.assertEqual(body["cumulative_cut_count"], 2)
            self.assertTrue(receipt.is_file())
            lineage = json.loads(receipt.read_text())
            self.assertEqual(len(lineage["cuts"]), 2)
            self.assertEqual(len(lineage["steps"]), 2)
            self.assertEqual(lineage["output"]["sha256"], body["sha256"])
            self.assertEqual(lineage["lineage_sha256"], body["lineage_sha256"])
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertEqual(
                body["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )

    def test_resume_recompiles_parent_then_appends_third_cut(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            stage_one = Path(td) / "one.glb"
            receipt_one = Path(td) / "one.json"
            first = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-cut-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(stage_one),
                        "receipt_path": str(receipt_one),
                        "specification": chain_spec(
                            "Stage one",
                            axes[1],
                            [
                                notch("bottom-a", (-0.8, 0.0, 0.0), "v-min", rotation=rotation),
                                notch("right-a", (0.0, 0.0, 0.45), "u-max", rotation=rotation),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            one_bytes = stage_one.read_bytes()
            stage_two = Path(td) / "two.glb"
            receipt_two = Path(td) / "two.json"
            second = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(stage_one),
                        "path": str(stage_two),
                        "lineage_path": str(receipt_one),
                        "receipt_path": str(receipt_two),
                        "expected_lineage_sha256": first["result"]["lineage_sha256"],
                        "specification": chain_spec(
                            "Stage two",
                            axes[1],
                            [
                                notch("top-a", (0.75, 0.0, 0.0), "v-max", rotation=rotation)
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(second["type"], "CREATION_RESULT", second)
            body = second["result"]
            self.assertEqual(body["cumulative_cut_count"], 3)
            self.assertEqual(
                body["parent_lineage_sha256"], first["result"]["lineage_sha256"]
            )
            lineage = json.loads(receipt_two.read_text())
            self.assertEqual(
                [row["id"] for row in lineage["cuts"]],
                ["bottom-a", "right-a", "top-a"],
            )
            self.assertEqual(len(lineage["steps"]), 3)
            self.assertEqual(stage_one.read_bytes(), one_bytes)
            self.assertNotEqual(stage_two.read_bytes(), stage_one.read_bytes())
            self.assertTrue(
                lineage["truth_boundary"]["previous_output_recompiled_before_resume"]
            )

    def test_parent_artifact_tamper_blocks_resume_before_output(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            first_target = Path(td) / "one.glb"
            first_receipt = Path(td) / "one.json"
            first = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(first_target),
                        "receipt_path": str(first_receipt),
                        "specification": chain_spec(
                            "First",
                            axes[1],
                            [notch("bottom", (-0.7, 0, 0), "v-min", rotation=rotation)],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            tampered = bytearray(first_target.read_bytes())
            tampered[-1] ^= 1
            first_target.write_bytes(bytes(tampered))
            output = Path(td) / "blocked.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(first_target),
                        "path": str(output),
                        "lineage_path": str(first_receipt),
                        "specification": chain_spec(
                            "Blocked",
                            axes[1],
                            [notch("top", (0.7, 0, 0), "v-max", rotation=rotation)],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(output.exists())

    def test_receipt_tamper_blocks_resume_even_if_json_is_valid(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            first_target = Path(td) / "one.glb"
            first_receipt = Path(td) / "one.json"
            first = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(first_target),
                        "receipt_path": str(first_receipt),
                        "specification": chain_spec(
                            "First",
                            axes[1],
                            [notch("bottom", (-0.7, 0, 0), "v-min", rotation=rotation)],
                        ),
                    },
                }
            )
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            lineage = json.loads(first_receipt.read_text())
            lineage["cuts"][0]["requested_depth"] += 0.01
            first_receipt.write_text(json.dumps(lineage), encoding="utf-8")
            output = Path(td) / "blocked.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(first_target),
                        "path": str(output),
                        "lineage_path": str(first_receipt),
                        "specification": chain_spec(
                            "Blocked",
                            axes[1],
                            [notch("top", (0.7, 0, 0), "v-max", rotation=rotation)],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(output.exists())

    def test_overlapping_notches_and_duplicate_ids_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            overlap = chain_spec(
                "Overlap",
                axes[1],
                [
                    notch("a", (0.0, 0, 0), "v-min", span=1.0, depth=0.5, rotation=rotation),
                    notch("b", (0.2, 0, 0), "v-min", span=1.0, depth=0.5, rotation=rotation),
                ],
            )
            with self.assertRaises(MeshPrecisionCutterError):
                build_fabrication_chain(source, overlap)
            duplicate = copy.deepcopy(overlap)
            duplicate["cuts"][1]["id"] = "a"
            with self.assertRaises(MeshPrecisionCutterError):
                build_fabrication_chain(source, duplicate)

    def test_initial_chain_replays_to_identical_glb_and_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            spec = chain_spec(
                "Stable chain",
                axes[1],
                [
                    notch("bottom-a", (-0.8, 0.0, 0.0), "v-min", rotation=rotation),
                    notch("top-a", (0.8, 0.0, 0.0), "v-max", rotation=rotation),
                ],
            )
            outputs = []
            receipts = []
            machine = UniversalCreationMachine(ROOT)
            for prefix in ("a", "b"):
                target = Path(td) / f"{prefix}.glb"
                receipt = Path(td) / f"{prefix}.json"
                result = machine.create(
                    {
                        "kind": "mesh-fabrication-chain",
                        "inputs": {
                            "source_path": str(source),
                            "path": str(target),
                            "receipt_path": str(receipt),
                            "specification": spec,
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                outputs.append(target.read_bytes())
                receipts.append(json.loads(receipt.read_text()))
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(receipts[0], receipts[1])

    def test_chain_truth_boundary_stays_bounded(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            built = build_fabrication_chain(
                source,
                chain_spec(
                    "Bounded",
                    axes[1],
                    [notch("one", (-0.6, 0, 0), "v-min", rotation=rotation)],
                ),
            )
            truth = built["truth_boundary"]
            self.assertTrue(truth["hash_linked_append_only_steps"])
            self.assertEqual(truth["round_hole_chaining"], "NOT_SUPPORTED")
            self.assertEqual(truth["cross_axis_chain"], "NOT_SUPPORTED")
            self.assertFalse(truth["full_arbitrary_mesh_csg"])
            self.assertEqual(
                truth["cryptographic_authorship_signature"], "NOT_PROVIDED"
            )

    def test_machine_body_receipt_path_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            rotation = rotation_matrix()
            axes = frame_axes(rotation)
            source = self._source(td, rotation=rotation)
            target = Path(td) / "cut.glb"
            forbidden = ROOT / "forbidden-fabrication-lineage.json"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(forbidden),
                        "specification": chain_spec(
                            "Blocked receipt",
                            axes[1],
                            [notch("one", (-0.6, 0, 0), "v-min", rotation=rotation)],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(target.exists())
            self.assertFalse(forbidden.exists())


if __name__ == "__main__":
    unittest.main()

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
from axm_uc.mesh_mixed_fabrication import (
    MIXED_FABRICATION_SCHEMA,
    MIXED_LINEAGE_SCHEMA,
    build_mixed_fabrication,
    publish_mixed_fabrication,
)
from axm_uc.mesh_precision_cutter import MeshPrecisionCutterError
from axm_uc.precision_cutter import build_cut
from axm_uc.procedural_3d import publish_glb, verify_glb


def material() -> dict:
    return {"color": "#527A91FF", "metallic": 0.35, "roughness": 0.42}


def _matmul(a, b):
    return [[sum(a[row][k] * b[k][column] for k in range(3)) for column in range(3)] for row in range(3)]


def rotation_matrix(rx=0.31, ry=-0.47, rz=0.22):
    cx, sx = math.cos(rx), math.sin(rx)
    cy, sy = math.cos(ry), math.sin(ry)
    cz, sz = math.cos(rz), math.sin(rz)
    x = [[1.0, 0.0, 0.0], [0.0, cx, -sx], [0.0, sx, cx]]
    y = [[cy, 0.0, sy], [0.0, 1.0, 0.0], [-sy, 0.0, cy]]
    z = [[cz, -sz, 0.0], [sz, cz, -0.0], [0.0, 0.0, 1.0]]
    return _matmul(z, _matmul(y, x))


def transform_vector(matrix, vector):
    return [sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3)]


def world_point(local, rotation, translation=(5.0, 2.0, -1.0)):
    rotated = transform_vector(rotation, local)
    return [rotated[index] + translation[index] for index in range(3)]


def frame_axes(rotation):
    return [[rotation[row][column] for row in range(3)] for column in range(3)]


def transformed_box_surface(*, size=(4.0, 2.0, 3.0), translation=(5.0, 2.0, -1.0), rotation=None):
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
    surface["name"] = "Rotated mixed stock"
    primitive = surface["primitives"][0]
    primitive["positions"] = [world_point(point, rotation, translation) for point in primitive["positions"]]
    primitive["normals"] = [transform_vector(rotation, normal) for normal in primitive["normals"]]
    return surface


def hole(operation_id, local_center, rotation, radius=0.30, segments=20):
    return {
        "id": operation_id,
        "operation": "round-through-hole",
        "center": world_point(local_center, rotation),
        "radius": radius,
        "segments": segments,
        "kerf": 0.02,
    }


def legacy_hole(operation_id, local_center, rotation, radius=0.30, segments=20):
    body = hole(operation_id, local_center, rotation, radius=radius, segments=segments)
    body.pop("operation")
    return body


def notch(operation_id, local_center, rotation, side="u-max", span=0.52, depth=0.34):
    return {
        "id": operation_id,
        "operation": "box-notch",
        "center": world_point(local_center, rotation),
        "side": side,
        "span": span,
        "depth": depth,
        "kerf": 0.02,
    }


def mixed_spec(name, rotation, operations):
    return {
        "schema": MIXED_FABRICATION_SCHEMA,
        "name": name,
        "axis_vector": frame_axes(rotation)[1],
        "operations": operations,
    }


class MixedFabricationTests(unittest.TestCase):
    def _source(self, directory, rotation=None):
        rotation = rotation or rotation_matrix()
        source = Path(directory) / "stock.glb"
        publish_glb(source, transformed_box_surface(rotation=rotation))
        return source, rotation

    def test_live_route_builds_hole_and_notch_in_one_closed_body(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            target = Path(td) / "mixed.glb"
            receipt = Path(td) / "mixed.json"
            machine = UniversalCreationMachine(ROOT)
            result = machine.create(
                {
                    "kind": "mesh-mixed-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "receipt_path": str(receipt),
                        "specification": mixed_spec(
                            "Mixed body",
                            rotation,
                            [
                                hole("hole-a", [-0.8, 0.0, 0.55], rotation),
                                notch("notch-a", [0.0, 0.0, -0.70], rotation),
                            ],
                        ),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(body["truth_status"], "VALIDATED_HASH_LINKED_MIXED_FABRICATION_CHAIN")
            self.assertEqual(body["metrics"]["hole_count"], 1)
            self.assertEqual(body["metrics"]["notch_count"], 1)
            self.assertEqual(body["output_topology"]["status"], "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE")
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            lineage = json.loads(receipt.read_text(encoding="utf-8"))
            self.assertEqual(lineage["schema"], MIXED_LINEAGE_SCHEMA)
            self.assertTrue(lineage["truth_boundary"]["same_axis_mixed_holes_and_notches"])

    def test_v07_resume_rebuilds_exact_parent_then_appends_third_operation(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            first = Path(td) / "first.glb"
            first_receipt = Path(td) / "first.json"
            result1 = publish_mixed_fabrication(
                source,
                first,
                mixed_spec(
                    "First mixed",
                    rotation,
                    [
                        hole("hole-a", [-0.9, 0.0, 0.55], rotation),
                        notch("notch-a", [0.0, 0.0, -0.75], rotation),
                    ],
                ),
                receipt_path=first_receipt,
            )
            second = Path(td) / "second.glb"
            second_receipt = Path(td) / "second.json"
            result2 = publish_mixed_fabrication(
                first,
                second,
                mixed_spec(
                    "Second mixed",
                    rotation,
                    [notch("notch-b", [0.75, 0.0, 0.0], rotation, side="v-max", span=0.42, depth=0.24)],
                ),
                lineage_path=first_receipt,
                receipt_path=second_receipt,
                expected_source_sha256=result1["sha256"],
                expected_lineage_sha256=result1["lineage_sha256"],
            )
            self.assertEqual(result2["parent_lineage_sha256"], result1["lineage_sha256"])
            self.assertEqual(result2["cumulative_operation_count"], 3)
            self.assertEqual(result2["metrics"]["hole_count"], 1)
            self.assertEqual(result2["metrics"]["notch_count"], 2)
            self.assertTrue(result2["truth_boundary"]["v07_resume_requires_exact_v07_recompile"])

    def test_upgrades_exact_v04_notch_lineage_before_adding_hole(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            axes = frame_axes(rotation)
            prior = Path(td) / "prior-notch.glb"
            prior_receipt = Path(td) / "prior-notch.json"
            machine = UniversalCreationMachine(ROOT)
            old = machine.create(
                {
                    "kind": "mesh-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(prior),
                        "receipt_path": str(prior_receipt),
                        "specification": {
                            "schema": "axm.mesh-fabrication-chain/v0.4",
                            "name": "Old notch",
                            "axis_vector": axes[1],
                            "cuts": [notch("notch-a", [0.0, 0.0, -0.72], rotation)],
                        },
                    },
                }
            )
            self.assertEqual(old["type"], "CREATION_RESULT", old)
            target = Path(td) / "upgraded.glb"
            receipt = Path(td) / "upgraded.json"
            upgraded = publish_mixed_fabrication(
                prior,
                target,
                mixed_spec("Upgraded mixed", rotation, [hole("hole-a", [-0.85, 0.0, 0.55], rotation)]),
                lineage_path=prior_receipt,
                receipt_path=receipt,
                expected_source_sha256=old["result"]["sha256"],
                expected_lineage_sha256=old["result"]["lineage_sha256"],
            )
            self.assertEqual(upgraded["migration"]["from_schema"], "axm.mesh-fabrication-lineage/v0.4")
            self.assertTrue(upgraded["migration"]["prior_output_exactly_recompiled_by_legacy_engine"])
            self.assertEqual(upgraded["cumulative_operation_count"], 2)

    def test_upgrades_exact_v06_hole_lineage_before_adding_notch(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            axes = frame_axes(rotation)
            prior = Path(td) / "prior-hole.glb"
            prior_receipt = Path(td) / "prior-hole.json"
            machine = UniversalCreationMachine(ROOT)
            old = machine.create(
                {
                    "kind": "mesh-hole-sweep-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(prior),
                        "receipt_path": str(prior_receipt),
                        "specification": {
                            "schema": "axm.mesh-hole-fabrication-chain/v0.6",
                            "name": "Old hole",
                            "axis_vector": axes[1],
                            "holes": [legacy_hole("hole-a", [-0.85, 0.0, 0.55], rotation)],
                        },
                    },
                }
            )
            self.assertEqual(old["type"], "CREATION_RESULT", old)
            target = Path(td) / "upgraded.glb"
            receipt = Path(td) / "upgraded.json"
            upgraded = publish_mixed_fabrication(
                prior,
                target,
                mixed_spec("Upgraded mixed", rotation, [notch("notch-a", [0.0, 0.0, -0.72], rotation)]),
                lineage_path=prior_receipt,
                receipt_path=receipt,
                expected_source_sha256=old["result"]["sha256"],
                expected_lineage_sha256=old["result"]["lineage_sha256"],
            )
            self.assertEqual(upgraded["migration"]["from_schema"], "axm.mesh-hole-fabrication-lineage/v0.6")
            self.assertEqual(upgraded["metrics"]["hole_count"], 1)
            self.assertEqual(upgraded["metrics"]["notch_count"], 1)

    def test_hole_touching_notch_fails_closed(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            spec = mixed_spec(
                "Conflict",
                rotation,
                [
                    hole("hole-a", [1.62, 0.0, 0.0], rotation, radius=0.30),
                    notch("notch-a", [0.0, 0.0, 0.0], rotation, side="u-max", span=0.70, depth=0.52),
                ],
            )
            with self.assertRaises(MeshPrecisionCutterError):
                build_mixed_fabrication(source, spec)

    def test_tampered_parent_artifact_or_receipt_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            first = Path(td) / "first.glb"
            receipt = Path(td) / "first.json"
            result = publish_mixed_fabrication(
                source,
                first,
                mixed_spec("First", rotation, [hole("hole-a", [-0.8, 0.0, 0.5], rotation), notch("notch-a", [0.0, 0.0, -0.7], rotation)]),
                receipt_path=receipt,
            )
            original = first.read_bytes()
            first.write_bytes(original + b"tamper")
            with self.assertRaises(MeshPrecisionCutterError):
                build_mixed_fabrication(
                    first,
                    mixed_spec("Second", rotation, [notch("notch-b", [0.7, 0.0, 0.0], rotation, side="v-max", span=0.4, depth=0.2)]),
                    lineage_path=receipt,
                    expected_lineage_sha256=result["lineage_sha256"],
                )
            first.write_bytes(original)
            data = json.loads(receipt.read_text(encoding="utf-8"))
            data["operations"][0]["requested_radius"] = 0.99
            receipt.write_text(json.dumps(data), encoding="utf-8")
            with self.assertRaises(MeshPrecisionCutterError):
                build_mixed_fabrication(
                    first,
                    mixed_spec("Second", rotation, [notch("notch-b", [0.7, 0.0, 0.0], rotation, side="v-max", span=0.4, depth=0.2)]),
                    lineage_path=receipt,
                )

    def test_same_source_and_recipe_are_byte_deterministic(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            spec = mixed_spec(
                "Replay",
                rotation,
                [hole("hole-a", [-0.8, 0.0, 0.55], rotation), notch("notch-a", [0.0, 0.0, -0.7], rotation)],
            )
            outputs = []
            receipts = []
            for index in (1, 2):
                target = Path(td) / f"out-{index}.glb"
                receipt = Path(td) / f"out-{index}.json"
                publish_mixed_fabrication(source, target, spec, receipt_path=receipt)
                outputs.append(target.read_bytes())
                receipts.append(receipt.read_bytes())
            self.assertEqual(outputs[0], outputs[1])
            self.assertEqual(receipts[0], receipts[1])

    def test_machine_body_receipt_is_rejected_by_live_adapter(self):
        with tempfile.TemporaryDirectory() as td:
            source, rotation = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            result = machine.create(
                {
                    "kind": "mesh-mixed-fabrication-chain",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(Path(td) / "out.glb"),
                        "receipt_path": str(ROOT / "src" / "forbidden-mixed-receipt.json"),
                        "specification": mixed_spec("Protected", rotation, [hole("hole-a", [-0.8, 0.0, 0.5], rotation), notch("notch-a", [0.0, 0.0, -0.7], rotation)]),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)


if __name__ == "__main__":
    unittest.main()

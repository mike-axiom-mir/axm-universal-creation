from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.mesh_precision_cutter import (
    MESH_CUTTER_SCHEMA,
    build_source_mesh_cut,
)
from axm_uc.procedural_3d import publish_glb, verify_glb


def material() -> dict:
    return {"color": "#527A91FF", "metallic": 0.35, "roughness": 0.42}


def box_spec(*, size=(4.0, 2.0, 3.0), translation=(5.0, 2.0, -1.0)) -> dict:
    return {
        "schema": "axm.procedural-3d/v0.1",
        "name": "Source box",
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


def pyramid_spec() -> dict:
    return {
        "schema": "axm.procedural-3d/v0.1",
        "name": "Not a box",
        "primitives": [
            {
                "id": "stock",
                "type": "pyramid",
                "size": [4.0, 2.0, 3.0],
                "translation": [5.0, 2.0, -1.0],
                "material": material(),
            }
        ],
    }


def multi_spec() -> dict:
    spec = box_spec()
    spec["primitives"].append(
        {
            "id": "second",
            "type": "box",
            "size": [1.0, 1.0, 1.0],
            "translation": [10.0, 0.0, 0.0],
            "material": material(),
        }
    )
    return spec


def hole_spec(axis="y") -> dict:
    return {
        "schema": MESH_CUTTER_SCHEMA,
        "name": f"Existing mesh hole {axis}",
        "operation": "round-through-hole",
        "axis": axis,
        "center": [5.0, 2.0, -1.0],
        "radius": 0.45,
        "segments": 24,
        "kerf": 0.04,
    }


def notch_spec(side="u-max") -> dict:
    return {
        "schema": MESH_CUTTER_SCHEMA,
        "name": f"Existing mesh notch {side}",
        "operation": "box-notch",
        "axis": "y",
        "center": [5.0, 2.0, -1.0],
        "side": side,
        "span": 0.8,
        "depth": 0.5,
        "kerf": 0.1,
    }


class MeshPrecisionCutterTests(unittest.TestCase):
    def _source(self, directory: str, specification=None) -> Path:
        source = Path(directory) / "source.glb"
        publish_glb(source, specification or box_spec())
        return source

    def test_live_route_cuts_real_existing_glb_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            original = source.read_bytes()
            target = Path(td) / "cut.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-through-hole",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "specification": hole_spec(),
                        "expected_source_sha256": hashlib.sha256(original).hexdigest(),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(
                body["truth_status"], "VALIDATED_EXISTING_MESH_PRECISION_CUT"
            )
            self.assertEqual(source.read_bytes(), original)
            self.assertTrue(body["source"]["unchanged_after_publication"])
            self.assertEqual(
                body["source_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertEqual(
                body["output_topology"]["status"],
                "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
            )
            self.assertTrue(body["glb_validation"]["passed"])
            self.assertTrue(verify_glb(target.read_bytes())["passed"])
            self.assertLess(body["metrics"]["output_volume"], body["metrics"]["source_volume"])
            self.assertFalse(body["truth_boundary"]["full_arbitrary_mesh_csg"])

    def test_round_hole_works_on_all_three_principal_axes(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            for axis in ("x", "y", "z"):
                with self.subTest(axis=axis):
                    built = build_source_mesh_cut(source, hole_spec(axis))
                    self.assertEqual(
                        built["output_topology"]["status"],
                        "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
                    )
                    self.assertEqual(built["metrics"]["cut_axis"], axis)
                    self.assertGreater(built["metrics"]["removed_volume_by_closed_mesh"], 0)

    def test_box_notch_cuts_each_boundary_side_and_reports_kerf(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            for side in ("u-min", "u-max", "v-min", "v-max"):
                with self.subTest(side=side):
                    built = build_source_mesh_cut(source, notch_spec(side))
                    self.assertEqual(
                        built["output_topology"]["status"],
                        "CLOSED_ORIENTED_EDGE_MANIFOLD_CANDIDATE",
                    )
                    self.assertAlmostEqual(built["metrics"]["effective_span"], 0.9)
                    self.assertAlmostEqual(built["metrics"]["effective_depth"], 0.55)
                    self.assertGreater(built["metrics"]["removed_volume"], 0)

    def test_same_source_and_recipe_replay_to_identical_glb(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            machine = UniversalCreationMachine(ROOT)
            outputs = []
            for name in ("a.glb", "b.glb"):
                target = Path(td) / name
                result = machine.create(
                    {
                        "kind": "mesh-precision-cut-3d",
                        "inputs": {
                            "source_path": str(source),
                            "path": str(target),
                            "specification": hole_spec(),
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                outputs.append(target.read_bytes())
            self.assertEqual(outputs[0], outputs[1])

    def test_digest_mismatch_and_same_path_fail_before_mutation(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            original = source.read_bytes()
            target = Path(td) / "target.glb"
            mismatch = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-through-hole",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(target),
                        "expected_source_sha256": "0" * 64,
                        "specification": hole_spec(),
                    },
                }
            )
            self.assertEqual(mismatch["type"], "CREATION_ERROR", mismatch)
            self.assertFalse(target.exists())
            same = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-through-hole",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(source),
                        "specification": hole_spec(),
                        "replace": True,
                    },
                }
            )
            self.assertEqual(same["type"], "CREATION_ERROR", same)
            self.assertEqual(source.read_bytes(), original)

    def test_non_box_and_multi_primitive_sources_fail_closed(self):
        with tempfile.TemporaryDirectory() as td:
            for index, specification in enumerate((pyramid_spec(), multi_spec())):
                with self.subTest(index=index):
                    source = Path(td) / f"source-{index}.glb"
                    target = Path(td) / f"target-{index}.glb"
                    publish_glb(source, specification)
                    result = UniversalCreationMachine(ROOT).create(
                        {
                            "kind": "mesh-laser-box-notch",
                            "inputs": {
                                "source_path": str(source),
                                "path": str(target),
                                "specification": notch_spec(),
                            },
                        }
                    )
                    self.assertEqual(result["type"], "CREATION_ERROR", result)
                    self.assertFalse(target.exists())

    def test_machine_body_is_not_a_source_or_destination_surface(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            forbidden_target = ROOT / "forbidden-mesh-cut.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-through-hole",
                    "inputs": {
                        "source_path": str(source),
                        "path": str(forbidden_target),
                        "specification": hole_spec(),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(forbidden_target.exists())

            target = Path(td) / "blocked.glb"
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "mesh-laser-through-hole",
                    "inputs": {
                        "source_path": str(ROOT / "machine.contract.json"),
                        "path": str(target),
                        "specification": hole_spec(),
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(target.exists())

    def test_source_material_and_truth_boundary_are_preserved_explicitly(self):
        with tempfile.TemporaryDirectory() as td:
            source = self._source(td)
            built = build_source_mesh_cut(source, hole_spec())
            self.assertEqual(built["source"]["material"], material())
            self.assertEqual(built["source"]["material_mode"], "exact-supported-PBR")
            self.assertEqual(
                built["truth_boundary"]["uv_texture_tangent_or_vertex_color_preservation"],
                "NOT_SUPPORTED_AND_REJECTED",
            )
            self.assertEqual(built["truth_boundary"]["self_intersection"], "NOT_PROVEN")


if __name__ == "__main__":
    unittest.main()

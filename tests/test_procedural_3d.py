from __future__ import annotations

import tempfile
import unittest
import json
import struct
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import Procedural3DError, build_glb, verify_glb


def tower_spec() -> dict:
    return {
        "schema": "axm.procedural-3d/v0.1",
        "name": "Command Tower",
        "primitives": [
            {
                "id": "base",
                "type": "box",
                "size": [4, 0.8, 4],
                "translation": [0, 0.4, 0],
                "material": {"color": "#163A49FF", "metallic": 0.65, "roughness": 0.35},
            },
            {
                "id": "column",
                "type": "cylinder",
                "size": [2.4, 5, 2.4],
                "translation": [0, 3.3, 0],
                "segments": 20,
                "material": {"color": "#20CFC4FF", "metallic": 0.4, "roughness": 0.28},
            },
            {
                "id": "roof",
                "type": "pyramid",
                "size": [4.2, 2.4, 4.2],
                "translation": [0, 7, 0],
                "material": {"color": "#FFB547FF", "metallic": 0.2, "roughness": 0.5},
            },
        ],
    }


class Procedural3DTests(unittest.TestCase):
    @staticmethod
    def _decoded_asset(body):
        json_length = struct.unpack_from("<I", body, 12)[0]
        document = json.loads(body[20:20 + json_length])
        binary_start = 28 + json_length
        return document, binary_start

    def test_exported_closed_primitives_have_outward_winding_and_positive_volume(self):
        for kind in ("box", "pyramid", "cylinder"):
            for segments in ((3, 16, 64) if kind == "cylinder" else (None,)):
                with self.subTest(kind=kind, segments=segments):
                    primitive = {"id": "shape", "type": kind, "size": [1, 1, 1],
                                 "translation": [0, 0, 0],
                                 "material": {"color": "#808080FF", "metallic": 0.5, "roughness": 0.5}}
                    if segments is not None:
                        primitive["segments"] = segments
                    body = build_glb({"schema": "axm.procedural-3d/v0.1", "name": "Surface check", "primitives": [primitive]})["body"]
                    receipt = verify_glb(body)
                    self.assertTrue(receipt["geometry_validation"]["winding_matches_vertex_normals"])
                    document, binary_start = self._decoded_asset(body)
                    def read(ref, fmt):
                        accessor = document["accessors"][ref]
                        view = document["bufferViews"][accessor["bufferView"]]
                        start = binary_start + view.get("byteOffset", 0) + accessor.get("byteOffset", 0)
                        return [struct.unpack_from(fmt, body, start + i * struct.calcsize(fmt)) for i in range(accessor["count"])]
                    mesh = document["meshes"][0]["primitives"][0]
                    points = read(mesh["attributes"]["POSITION"], "<fff")
                    indices = [row[0] for row in read(mesh["indices"], "<H")]
                    volume = 0
                    for offset in range(0, len(indices), 3):
                        a, b, c = (points[i] for i in indices[offset:offset+3])
                        cross = (b[1]*c[2]-b[2]*c[1], b[2]*c[0]-b[0]*c[2], b[0]*c[1]-b[1]*c[0])
                        volume += sum(a[i]*cross[i] for i in range(3))/6
                    self.assertGreater(volume, 0)

    def test_validator_rejects_actual_binary_geometry_defects(self):
        original = build_glb(tower_spec())["body"]
        document, binary_start = self._decoded_asset(original)
        mesh = document["meshes"][0]["primitives"][0]
        def address(ref):
            a = document["accessors"][ref]
            return binary_start + document["bufferViews"][a["bufferView"]].get("byteOffset", 0) + a.get("byteOffset", 0)
        index_start = address(mesh["indices"])
        position_start = address(mesh["attributes"]["POSITION"])
        face = struct.unpack_from("<HHH", original, index_start)
        corruptions = [
            (index_start, "<HHH", (face[0], face[2], face[1]), "winding"),
            (index_start, "<HHH", (face[0], face[0], face[2]), "degenerate"),
            (index_start, "<H", (65535,), "indices"),
            (position_start, "<f", (float("nan"),), "non-finite"),
        ]
        for offset, fmt, values, expected in corruptions:
            with self.subTest(defect=expected):
                corrupted = bytearray(original)
                struct.pack_into(fmt, corrupted, offset, *values)
                with self.assertRaisesRegex(Procedural3DError, expected):
                    verify_glb(bytes(corrupted))

    def test_same_spec_emits_identical_complete_glb(self):
        first = build_glb(tower_spec())
        second = build_glb(tower_spec())
        self.assertEqual(first["body"], second["body"])
        self.assertEqual(first["specification_sha256"], second["specification_sha256"])
        receipt = verify_glb(first["body"], expected_spec_digest=first["specification_sha256"])
        self.assertTrue(receipt["passed"])
        self.assertEqual(receipt["primitives"], 3)
        self.assertEqual(receipt["nodes"], 3)
        self.assertGreater(receipt["triangles"], 20)

    def test_live_capability_publishes_and_reparses_exact_asset(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tower.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "procedural-glb-asset",
                "inputs": {"path": str(target), "specification": tower_spec()},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(body["truth_status"], "VALIDATED_DETERMINISTIC_GLB_ASSET")
            self.assertTrue(body["post_publish_validation"]["passed"])
            self.assertEqual(target.read_bytes(), build_glb(tower_spec())["body"])
            self.assertFalse(body["rendered_appearance_observed"])
            self.assertFalse(body["host_import_compatibility_observed"])

    def test_closed_fields_bounds_suffix_and_corruption_fail(self):
        spec = tower_spec()
        spec["prompt"] = "make it AAA"
        with self.assertRaises(Procedural3DError):
            build_glb(spec)
        corrupt = bytearray(build_glb(tower_spec())["body"])
        corrupt[8:12] = (1).to_bytes(4, "little")
        with self.assertRaises(Procedural3DError):
            verify_glb(bytes(corrupt))
        with tempfile.TemporaryDirectory() as td:
            wrong = UniversalCreationMachine(ROOT).create({
                "kind": "procedural-glb-asset",
                "inputs": {"path": str(Path(td) / "tower.bin"), "specification": tower_spec()},
            })
            self.assertEqual(wrong["type"], "CREATION_ERROR", wrong)
            self.assertFalse((Path(td) / "tower.bin").exists())

    def test_invalid_replacement_input_preserves_existing_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tower.glb"
            target.write_bytes(b"original")
            invalid = tower_spec()
            invalid["primitives"][0]["size"] = [0, 1, 1]
            result = UniversalCreationMachine(ROOT).create({
                "kind": "procedural-glb-asset",
                "inputs": {"path": str(target), "specification": invalid, "replace": True},
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual(target.read_bytes(), b"original")


if __name__ == "__main__":
    unittest.main()

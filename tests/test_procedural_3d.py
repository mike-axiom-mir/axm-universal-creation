from __future__ import annotations

import tempfile
import unittest
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

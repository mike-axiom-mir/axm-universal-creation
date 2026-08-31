from __future__ import annotations

import json
import struct
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.visual_3d import assess_3d_output, catalog_3d, compile_3d_request, compile_adaptive_3d_request, inspect_glb, record_3d_review
from axm_uc.visual_assets_bridge import operate_visual_expansion


def minimal_glb() -> bytes:
    payload = {
        "asset": {"version": "2.0", "generator": "test-forge"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"name": "AXM_TEST_LOD0", "mesh": 0}],
        "meshes": [{"name": "AXM_TEST", "primitives": [{"indices": 0, "mode": 4, "material": 0}]}],
        "accessors": [{"count": 9, "componentType": 5123, "type": "SCALAR"}],
        "materials": [{"name": "AX_Gunmetal"}],
    }
    encoded = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded += b" " * ((4 - len(encoded) % 4) % 4)
    length = 12 + 8 + len(encoded)
    return struct.pack("<4sII", b"glTF", 2, length) + struct.pack("<I4s", len(encoded), b"JSON") + encoded


class Visual3DForgeTests(unittest.TestCase):
    def test_catalog_exposes_engine_ready_outputs_and_runtime_truth(self):
        catalog = catalog_3d()
        self.assertEqual(catalog["truth_status"], "EXECUTABLE_BLENDER_BACKED_3D_FORGE")
        self.assertEqual(set(catalog["assets"]), {"axiom-bastion-frame", "mir-sanctuary-keeper"})
        self.assertIn("glb", catalog["outputs"])
        self.assertTrue(catalog["truth"]["generatorAndVerificationLiveInMachine"])
        self.assertTrue(catalog["truth"]["visualTasteRequiresRenderedReview"])

    def test_request_is_faction_bound_and_has_lod_collision_requirements(self):
        request = compile_3d_request({"asset_id": "axiom-bastion-frame", "seed": 41027})
        self.assertEqual(request["faction"], "axiom")
        self.assertEqual(request["lod_ratios"], {"lod0": 1.0, "lod1": .48, "lod2": .18})
        self.assertTrue(request["requirements"]["separate_collision_export"])
        self.assertEqual(request["context_key"], "3d/axiom-bastion-frame/hero")
        self.assertTrue(request["requirements"]["artifact_bound_visual_acceptance"])
        with self.assertRaises(ValueError):
            compile_3d_request({"asset_id": "invented-asset"})

    def test_inspector_decodes_real_glb_structure_and_triangles(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "asset.glb"
            path.write_bytes(minimal_glb())
            result = inspect_glb(path)
        self.assertEqual(result["truth_status"], "DECODED_GLTF_STRUCTURE")
        self.assertEqual(result["triangles"], 3)
        self.assertEqual(result["node_names"], ["AXM_TEST_LOD0"])
        self.assertEqual(result["materials"], ["AX_Gunmetal"])

    def test_bridge_routes_3d_planning_without_starting_renderer(self):
        result = operate_visual_expansion(Path("."), {
            "operation": "3d-plan",
            "request": {"asset_id": "mir-sanctuary-keeper", "quality": "production"},
        })
        self.assertEqual(result["faction"], "mir")
        self.assertEqual(result["quality"], "production")

    def test_failed_review_replays_only_in_exact_3d_context(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            png = root / "proof.png"
            import zlib
            raw = b"\x00" + bytes((10, 20, 30, 255))
            def chunk(kind, payload):
                return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)
            png.write_bytes(b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0)) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b""))
            record_3d_review(root, {
                "context_key": "3d/axiom-bastion-frame/hero",
                "artifact_path": str(png),
                "criteria": {"aaa-form-hierarchy": "FAIL"},
                "lessons": [{
                    "id": "replace-primitive-masses",
                    "evidence": "Large blocks read as toy construction.",
                    "patch": {"avoid_add": ["visible primitive-block construction"]},
                }],
            })
            adapted = compile_adaptive_3d_request(root, {"asset_id": "axiom-bastion-frame"})
            untouched = compile_adaptive_3d_request(root, {"asset_id": "mir-sanctuary-keeper"})
        self.assertEqual(adapted["applied_lesson_ids"], ["replace-primitive-masses"])
        self.assertIn("visible primitive-block construction", adapted["request"]["avoid"])
        self.assertEqual(untouched["applied_lesson_ids"], [])

    def test_aaa_assessment_requires_technical_and_bound_visual_pass(self):
        proof_sha = "a" * 64
        receipt = {"inspections": {
            "lod0": {"triangles": 100000, "materials": list("abcdef"), "images": 15, "textures": 15},
            "lod1": {"triangles": 48000}, "lod2": {"triangles": 18000}, "collision": {"meshes": 5},
        }}
        manifest = {
            "source": {"sha256": "b" * 64},
            "exports": {name: {} for name in ("lod0", "lod1", "lod2", "collision")},
            "render_proofs": [{"sha256": proof_sha} for _ in range(4)],
        }
        pending = assess_3d_output(receipt, manifest)
        self.assertTrue(pending["technical_pass"])
        self.assertFalse(pending["visual_pass"])
        criteria = {name: "PASS" for name in catalog_3d()["aaa_quality_gates"]["required_visual_criteria"]}
        accepted = assess_3d_output(receipt, manifest, {"artifact_sha256": proof_sha, "criteria": criteria})
        self.assertEqual(accepted["status"], "AAA_ACCEPTED")


if __name__ == "__main__":
    unittest.main()

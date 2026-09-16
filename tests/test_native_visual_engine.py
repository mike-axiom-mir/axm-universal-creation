from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.native_visual_engine import (
    ENGINE_ID,
    SCENE_SCHEMA,
    catalog_native_visual,
    compile_scene,
    demo_scene,
    render_html,
    scene_sha256,
    write_visual_bundle,
)


class NativeVisualEngineTests(unittest.TestCase):
    def test_catalog_declares_blender_bridge_without_pixel_parity_claim(self):
        catalog = catalog_native_visual()
        self.assertEqual(catalog["truth_status"], "EXECUTABLE_CODED_VISUAL_RUNTIME")
        self.assertEqual(catalog["bridge"]["target"], "Blender bpy")
        self.assertFalse(catalog["bridge"]["pixel_parity_claimed"])
        self.assertTrue(catalog["truth"]["live_pixels_require_webgl2_host_evidence"])

    def test_scene_contract_is_deterministic_and_truth_bounded(self):
        first = demo_scene()
        second = compile_scene(first)
        self.assertEqual(first["schema"], SCENE_SCHEMA)
        self.assertEqual(first["engine"], ENGINE_ID)
        self.assertEqual(first["scene_sha256"], second["scene_sha256"])
        self.assertEqual(first["scene_sha256"], scene_sha256(first))
        self.assertFalse(first["truth"]["final_asset_authoring_replacement"])
        self.assertTrue(first["truth"]["external_javascript_dependencies"] is False)

    def test_invalid_or_ambiguous_scene_state_is_rejected(self):
        with self.assertRaises(ValueError):
            compile_scene({"objects": [{"id": "same"}, {"id": "same"}]})
        with self.assertRaises(ValueError):
            compile_scene({"objects": [{"id": "bad", "primitive": "teapot"}]})
        with self.assertRaises(ValueError):
            compile_scene({"objects": [{"id": "flat", "scale": [1, 0, 1]}]})
        with self.assertRaises(ValueError):
            compile_scene({"camera": {"near": 10, "far": 1}})

    def test_html_is_self_contained_webgl2_runtime(self):
        html = render_html(demo_scene())
        self.assertIn("getContext('webgl2'", html)
        self.assertIn("#version 300 es", html)
        self.assertIn("AXM native WebGL2 preview", html)
        self.assertNotIn("<script src=", html)
        self.assertNotIn("https://", html)
        self.assertNotIn("http://", html)

    def test_bundle_writes_scene_html_and_hash_receipt(self):
        with tempfile.TemporaryDirectory() as temporary:
            receipt = write_visual_bundle(temporary, demo_scene())
            root = Path(temporary)
            scene = json.loads((root / "scene.json").read_text(encoding="utf-8"))
            html = (root / "index.html").read_text(encoding="utf-8")
            stored = json.loads((root / "receipt.json").read_text(encoding="utf-8"))
        self.assertEqual(receipt, stored)
        self.assertEqual(receipt["status"], "NATIVE_VISUAL_BUNDLE_COMPILED")
        self.assertEqual(scene["scene_sha256"], receipt["scene_sha256"])
        self.assertIn(scene["title"], html)
        self.assertTrue(receipt["truth"]["bundle_is_self_contained"])
        self.assertFalse(receipt["truth"]["webgl_execution_tested_here"])

    def test_bundle_refuses_nonempty_output_without_replace(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "keep.txt").write_text("do not silently overwrite", encoding="utf-8")
            with self.assertRaises(FileExistsError):
                write_visual_bundle(root, demo_scene())
            receipt = write_visual_bundle(root, demo_scene(), replace=True)
        self.assertEqual(receipt["status"], "NATIVE_VISUAL_BUNDLE_COMPILED")


if __name__ == "__main__":
    unittest.main()

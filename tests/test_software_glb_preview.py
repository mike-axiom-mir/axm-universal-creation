from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.procedural_3d import build_glb
from axm_uc.software_glb_preview import publish_glb_preview, render_glb_preview
from axm_uc.visual_assets_cli import main
from axm_uc.visual_learning import inspect_png


def asset():
    return build_glb({
        "schema": "axm.procedural-3d/v0.1", "name": "Preview fixture",
        "primitives": [{
            "id": "body", "type": "box", "size": [2.4, 1.0, 4.0],
            "translation": [0, .5, 0],
            "material": {"color": "#2A7B86FF", "metallic": .55,
                         "roughness": .32, "emissive": "#082A2EFF"},
        }],
    })["body"]


class SoftwareGlbPreviewTests(unittest.TestCase):
    def test_renders_deterministic_geometry_bound_png(self):
        source = asset()
        first = render_glb_preview(source, width=160, height=120, supersample=1)
        second = render_glb_preview(source, width=160, height=120, supersample=1)
        self.assertEqual(first, second)
        self.assertEqual(first["receipt"]["lighting"], "studio")
        self.assertEqual(first["receipt"]["light_count"], 4)
        self.assertGreater(first["receipt"]["contact_shadow_pixels"], 0)
        self.assertTrue(first["body"].startswith(b"\x89PNG\r\n\x1a\n"))
        self.assertEqual(first["receipt"]["triangles"], 12)
        self.assertGreater(first["receipt"]["visible_triangles"], 0)
        self.assertEqual(first["receipt"]["bounds"]["min"], [-1.2, 0.0, -2.0])

    def test_publish_and_cli_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            model = Path(td) / "model.glb"
            model.write_bytes(asset())
            preview = Path(td) / "preview.png"
            receipt = publish_glb_preview(model, preview, width=128, height=96, supersample=1)
            self.assertEqual(receipt["width"], 128)
            self.assertEqual(inspect_png(preview)["width"], 128)
            with self.assertRaises(FileExistsError):
                publish_glb_preview(model, preview)
            cli_preview = Path(td) / "cli.png"
            self.assertEqual(main(["software-glb-preview", str(model), str(cli_preview),
                                   "--width", "128", "--height", "96", "--supersample", "1"]), 0)
            self.assertTrue(cli_preview.is_file())

    def test_unknown_clip_and_bounds_fail(self):
        with self.assertRaisesRegex(ValueError, "unknown preview clip"):
            render_glb_preview(asset(), clip="drive", width=96, height=96, supersample=1)
        with self.assertRaisesRegex(ValueError, "width"):
            render_glb_preview(asset(), width=32, height=96, supersample=1)
        with self.assertRaisesRegex(ValueError, "lighting"):
            render_glb_preview(asset(), width=96, height=96, supersample=1, lighting="mystery")


if __name__ == "__main__":
    unittest.main()

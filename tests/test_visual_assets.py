from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.visual_assets import (
    DECALS, FIXTURES, GRADIENTS, MATERIALS, OBJ_FIXTURES, PALETTES, TEXTURES,
    catalog, generate_asset, generate_kit, generate_material, generate_texture,
)
from axm_uc.visual_assets_cli import main as cli_main


class VisualAssetTests(unittest.TestCase):
    def test_catalog_only_lists_executable_families(self):
        data = catalog()
        self.assertTrue(data["deterministic"])
        self.assertGreaterEqual(len(TEXTURES), 20)
        self.assertGreaterEqual(len(GRADIENTS), 10)
        self.assertGreaterEqual(len(MATERIALS), 10)
        self.assertGreaterEqual(len(FIXTURES), 20)
        self.assertGreaterEqual(len(DECALS), 10)
        self.assertGreaterEqual(len(PALETTES), 8)

    def test_every_catalog_entry_really_generates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for index, kind in enumerate(TEXTURES):
                out = root / "textures" / f"{kind}.png"
                generate_asset(category="texture", kind=kind, path=out, seed=index, size=10)
                self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
            for kind in GRADIENTS:
                out = root / "gradients" / f"{kind}.png"
                generate_asset(category="gradient", kind=kind, path=out, size=10)
                self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
            for index, kind in enumerate(MATERIALS):
                out = root / "materials" / kind
                generate_asset(category="material", kind=kind, path=out, seed=index, size=8)
                self.assertEqual((out / "albedo.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
                self.assertEqual((out / "normal.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
            for index, kind in enumerate(FIXTURES):
                out = root / "fixtures" / f"{kind}.svg"
                generate_asset(category="fixture", kind=kind, path=out, seed=index)
                ET.fromstring(out.read_text())
            for index, kind in enumerate(OBJ_FIXTURES):
                out = root / "fixtures3d" / f"{kind}.obj"
                generate_asset(category="fixture", kind=kind, path=out, format="obj", seed=index)
                text = out.read_text()
                self.assertIn("\nv ", text, kind)
                self.assertIn("\nf ", text, kind)
            for index, kind in enumerate(DECALS):
                out = root / "decals" / f"{kind}.svg"
                generate_asset(category="decal", kind=kind, path=out, seed=index)
                ET.fromstring(out.read_text())
            for index, kind in enumerate(PALETTES):
                out = root / "palettes" / kind
                generate_asset(category="palette", kind=kind, path=out, seed=index, count=5)
                ET.fromstring((out / "swatches.svg").read_text())
                self.assertEqual(len(json.loads((out / "palette.json").read_text())["colors"]), 5)

    def test_texture_is_real_png_and_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            a = Path(tmp) / "a.png"
            b = Path(tmp) / "b.png"
            ra = generate_texture(a, "wood", seed=77, size=32)
            rb = generate_texture(b, "wood", seed=77, size=32)
            self.assertEqual(a.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            self.assertEqual(a.read_bytes(), b.read_bytes())
            self.assertEqual(ra["sha256"], rb["sha256"])

    def test_material_pack_emits_pbr_channels(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "steel"
            result = generate_material(out, "steel", seed=4, size=24)
            names = {row["path"] for row in result["files"]}
            for required in ("albedo.png", "roughness.png", "metallic.png", "height.png", "normal.png", "ao.png", "emissive.png", "opacity.png", "material.json"):
                self.assertIn(required, names)
                self.assertTrue((out / required).is_file())
            self.assertEqual((out / "normal.png").read_bytes()[:8], b"\x89PNG\r\n\x1a\n")

    def test_starter_kit_has_manifest_and_multiple_real_asset_types(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "kit"
            result = generate_kit(out, profile="starter", seed=5, size=16)
            manifest = json.loads(Path(result["manifest"]).read_text())
            self.assertEqual(manifest["profile"], "starter")
            paths = {row["path"] for row in manifest["files"]}
            self.assertTrue(any(p.startswith("textures/") and p.endswith(".png") for p in paths))
            self.assertTrue(any(p.startswith("materials/") and p.endswith("normal.png") for p in paths))
            self.assertTrue(any(p.startswith("fixtures/") and p.endswith(".svg") for p in paths))
            self.assertTrue(any(p.startswith("fixtures-3d/") and p.endswith(".obj") for p in paths))
            self.assertTrue(any(p.startswith("decals/") and p.endswith(".svg") for p in paths))
            self.assertTrue(any(p.startswith("palettes/") and p.endswith("palette.json") for p in paths))

    def test_cli_generates_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "marble.png"
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = cli_main(["generate", "texture", "marble", str(out), "--seed", "9", "--size", "12"])
            self.assertEqual(code, 0)
            self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")
            receipt = json.loads(stdout.getvalue())
            self.assertEqual(receipt["kind"], "marble")


if __name__ == "__main__":
    unittest.main()

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

from axm_uc.visual_expanded import (
    expansion_catalog, generate_expanded_asset, generate_expansion_kit, generate_pigment,
)
from axm_uc.visual_surface import SURFACES
from axm_uc.visual_pigment import PIGMENTS, SMART_MASKS
from axm_uc.visual_sprite import SPRITES
from axm_uc.visual_parts import MESH_PARTS, VECTOR_PARTS
from axm_uc.visual_assets_cli import combined_catalog, main as cli_main


class VisualExpansionTests(unittest.TestCase):
    def test_catalog_has_large_executable_expansion(self):
        data = expansion_catalog()
        self.assertTrue(data["deterministic"])
        self.assertGreaterEqual(len(SURFACES), 50)
        self.assertGreaterEqual(len(PIGMENTS), 18)
        self.assertEqual(len(SMART_MASKS), 12)
        self.assertGreaterEqual(len(SPRITES), 20)
        self.assertGreaterEqual(len(MESH_PARTS), 30)
        self.assertGreaterEqual(len(VECTOR_PARTS), 30)
        combined = combined_catalog()["outputs"]
        for category in ("surface", "pigment", "sprite", "mesh", "vector-part"):
            self.assertIn(category, combined)

    def test_every_expansion_catalog_entry_really_generates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for i, kind in enumerate(SURFACES):
                out = root / "surfaces" / f"{kind}.png"
                generate_expanded_asset(category="surface", kind=kind, path=out, seed=i, size=8)
                self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
            for i, kind in enumerate(PIGMENTS):
                out = root / "pigments" / kind
                result = generate_expanded_asset(category="pigment", kind=kind, path=out, seed=i, size=6)
                self.assertEqual(set(result["smart_masks"]), set(SMART_MASKS))
                self.assertTrue((out / "albedo.png").is_file(), kind)
                self.assertTrue((out / "mask-edge-wear.png").is_file(), kind)
                self.assertTrue((out / "mask-cavity-dirt.png").is_file(), kind)
                self.assertTrue((out / "pigment.json").is_file(), kind)
            for i, kind in enumerate(SPRITES):
                out = root / "sprites" / f"{kind}.png"
                generate_expanded_asset(category="sprite", kind=kind, path=out, seed=i, frame_size=8, frames=2)
                self.assertEqual(out.read_bytes()[:8], b"\x89PNG\r\n\x1a\n", kind)
                self.assertTrue(out.with_suffix(".png.json").is_file())
            for i, kind in enumerate(MESH_PARTS):
                out = root / "mesh" / f"{kind}.obj"
                generate_expanded_asset(category="mesh", kind=kind, path=out, seed=i)
                text = out.read_text()
                self.assertIn("\nv ", text, kind)
                self.assertIn("\nf ", text, kind)
            for i, kind in enumerate(VECTOR_PARTS):
                out = root / "vector" / f"{kind}.svg"
                generate_expanded_asset(category="vector-part", kind=kind, path=out, seed=i)
                ET.fromstring(out.read_text())

    def test_pigment_pack_has_pbr_and_smart_masks(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "military"
            result = generate_pigment(out, "military-paint", seed=9, size=12, age=.8, damage=.6, moisture=.4)
            files = {row["path"] for row in result["files"]}
            for channel in ("albedo", "roughness", "metallic", "height", "normal", "ao", "emissive", "opacity"):
                self.assertIn(f"{channel}.png", files)
            for mask in SMART_MASKS:
                self.assertIn(f"mask-{mask}.png", files)
            manifest = json.loads((out / "pigment.json").read_text())
            self.assertEqual(manifest["age"], .8)
            self.assertEqual(set(manifest["smart_masks"]), set(SMART_MASKS))

    def test_expansion_kit_has_every_new_asset_class(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "kit"
            result = generate_expansion_kit(out, profile="starter", seed=5, size=8)
            manifest = json.loads(Path(result["manifest"]).read_text())
            paths = {row["path"] for row in manifest["files"]}
            self.assertTrue(any(p.startswith("surfaces/") for p in paths))
            self.assertTrue(any(p.startswith("pigments/") and p.endswith("mask-edge-wear.png") for p in paths))
            self.assertTrue(any(p.startswith("sprites/") and p.endswith(".png") for p in paths))
            self.assertTrue(any(p.startswith("meshes/") and p.endswith(".obj") for p in paths))
            self.assertTrue(any(p.startswith("vector-parts/") and p.endswith(".svg") for p in paths))

    def test_cli_generates_smart_pigment_and_sprite(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            pigment = root / "pigment"
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = cli_main(["generate", "pigment", "painted-metal", str(pigment), "--seed", "3", "--size", "8"])
            self.assertEqual(code, 0)
            self.assertEqual(json.loads(stdout.getvalue())["category"], "pigment")
            sprite = root / "bot.png"
            with contextlib.redirect_stdout(io.StringIO()):
                code = cli_main(["generate", "sprite", "bot", str(sprite), "--seed", "3", "--frame-size", "8", "--frames", "2"])
            self.assertEqual(code, 0)
            self.assertEqual(sprite.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()

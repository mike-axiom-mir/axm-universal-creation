from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from axm_uc.procedural_3d import verify_glb
from axm_uc.vehicle_art_direction import (
    PALETTES, REQUEST_SCHEMA, apply_vehicle_art_direction,
    compile_vehicle_art_direction, publish_vehicle_art_direction,
    vehicle_art_direction_catalog,
)
from axm_uc.visual_assets_cli import main as assets_cli


def surface():
    return {
        "schema": "axm.surface-3d/v0.1", "name": "vehicle-style-test",
        "primitives": [{
            "id": "door-armor__paint",
            "positions": [[-1, .2, 0], [1, .2, 0], [1, 1.2, 0], [-1, 1.2, 0]],
            "normals": [[0, 0, 1]] * 4, "indices": [0, 1, 2, 0, 2, 3],
            "colors": [[1, 1, 1, 1]] * 4,
            "material": {"color": "#337E82FF", "metallic": .45, "roughness": .66},
        }, {
            "id": "headlight__cyan",
            "positions": [[-.2, .4, .02], [.2, .4, .02], [.2, .7, .02], [-.2, .7, .02]],
            "normals": [[0, 0, 1]] * 4, "indices": [0, 1, 2, 0, 2, 3],
            "material": {"color": "#37D9DCFF", "metallic": .15, "roughness": .23},
        }],
    }


def request():
    return {
        "schema": REQUEST_SCHEMA, "palette": "industrial-teal", "seed": 17,
        "finish": "satin", "custom_slots": {"primary": "#155E68"},
        "weathering": {"dirt": .32, "wear": .24, "scratches": .18, "edge_damage": .2},
        "markings": [{
            "id": "door-chevron", "style": "chevron", "slot": "warning",
            "center": [0, .7, .01], "right": [1, 0, 0], "up": [0, 1, 0],
            "size": [1.2, .55], "bands": 2, "offset": .002,
        }],
        "upgrades": [{
            "id": "armor", "level": 2, "maximum": 3, "targets": ["*armor*"],
            "slots": ["secondary", "primary", "metal_dark", "metal_bright"],
            "finishes": [None, "satin", "matte", "bare-metal"],
        }],
    }


class VehicleArtDirectionTests(unittest.TestCase):
    def test_catalog_exposes_real_choices_and_truth_boundary(self):
        catalog = vehicle_art_direction_catalog()
        self.assertEqual(catalog["request_schema"], REQUEST_SCHEMA)
        self.assertGreaterEqual(len(catalog["palettes"]), 5)
        self.assertIn("gloss", catalog["finishes"])
        self.assertIn("chevron", catalog["marking_styles"])
        self.assertEqual(catalog["weather_channels"], ["dirt", "wear", "scratches", "edge_damage"])
        self.assertIn("not inferred physical history", catalog["truth"])

    def test_compile_resolves_custom_slots_and_upgrade_variants(self):
        result = compile_vehicle_art_direction(request())
        self.assertEqual(result["palette"]["primary"], "#155E68FF")
        self.assertEqual(len(result["upgrade_variants"]["armor"]), 4)
        self.assertEqual([row["level"] for row in result["upgrade_variants"]["armor"] if row["active"]], [2])
        self.assertEqual(PALETTES["industrial-teal"]["primary"], "#28777BFF")

    def test_realization_is_deterministic_preserves_source_and_adds_real_marking_geometry(self):
        original = surface()
        first = apply_vehicle_art_direction(original, request())
        second = apply_vehicle_art_direction(original, request())
        self.assertEqual(first, second)
        self.assertEqual(original, surface())
        self.assertTrue(first["receipt"]["geometry_preserved"])
        self.assertEqual(first["receipt"]["marking_layers"], 1)
        self.assertEqual(first["receipt"]["upgrade_hits"], {"armor": 1})
        self.assertEqual(len(first["realization"]["primitives"]), 3)
        armor = first["realization"]["primitives"][0]
        self.assertEqual(armor["material"]["color"], "#FFFFFFFF")
        self.assertGreater(armor["material"]["metallic"], .49)
        light = first["realization"]["primitives"][1]
        self.assertEqual(light["material"]["emissive"], first["compiled"]["palette"]["light_primary"])
        marking = first["realization"]["primitives"][2]
        self.assertGreater(len(marking["positions"]), 4)

    def test_publication_contains_actual_verified_glb(self):
        with tempfile.TemporaryDirectory() as temporary:
            output = Path(temporary) / "styled"
            receipt = publish_vehicle_art_direction(output, surface(), request())
            self.assertEqual(receipt["files"], ["art-direction.json", "asset.glb", "realization.json", "source.json"])
            self.assertEqual(verify_glb((output / "asset.glb").read_bytes())["triangles"], 12)
            manifest = json.loads((output / "art-direction.json").read_text())
            self.assertEqual(manifest["receipt"]["palette"], "industrial-teal")
            with self.assertRaises(FileExistsError):
                publish_vehicle_art_direction(output, surface(), request())

    def test_invalid_choices_fail_closed(self):
        bad = request()
        bad["custom_slots"] = {"mystery": "#FFFFFF"}
        with self.assertRaisesRegex(ValueError, "unknown custom"):
            compile_vehicle_art_direction(bad)
        bad = request()
        bad["upgrades"][0]["slots"] = ["primary"]
        with self.assertRaisesRegex(ValueError, "every level"):
            compile_vehicle_art_direction(bad)

    def test_cli_catalog_and_compose_use_the_same_public_surface(self):
        stream = io.StringIO()
        with redirect_stdout(stream):
            self.assertEqual(assets_cli(["vehicle-art-catalog"]), 0)
        self.assertEqual(json.loads(stream.getvalue())["request_schema"], REQUEST_SCHEMA)
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            request_path, mesh_path, output = root / "request.json", root / "mesh.json", root / "styled"
            request_path.write_text(json.dumps(request()))
            mesh_path.write_text(json.dumps(surface()))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(assets_cli(["vehicle-art-compose", str(request_path),
                                             str(mesh_path), str(output)]), 0)
            self.assertTrue((output / "asset.glb").is_file())


if __name__ == "__main__":
    unittest.main()

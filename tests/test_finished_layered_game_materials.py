import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_uc.finished_layered_game_materials import (
    FINISH_BY_NAME,
    finished_layered_game_material_fields,
    generate_finished_layered_game_material,
)
from axm_uc.layered_game_materials import layered_game_material_fields
from axm_uc.rich_game_material_bridge import load_rich_material_bundle
from axm_uc.rich_game_material_cli import main as material_cli


class FinishedLayeredGameMaterialTests(unittest.TestCase):
    def test_finish_changes_layered_fields_without_losing_layer_masks(self):
        layers = [
            {"type": "salt", "amount": .28, "scale": 8.0},
            {"type": "scuff", "amount": .32, "scale": 19.0},
        ]
        layered, expected_masks = layered_game_material_fields(
            "scratched-fiberglass", layers, 24, 55, (35, 112, 145)
        )
        finished, actual_masks = finished_layered_game_material_fields(
            "scratched-fiberglass", layers, 24, 55, (35, 112, 145), "comic-salvage"
        )
        self.assertEqual(expected_masks, actual_masks)
        self.assertNotEqual(layered["base_color"][1], finished["base_color"][1])
        self.assertNotEqual(layered["roughness"][1], finished["roughness"][1])
        self.assertNotEqual(layered["normal"][1], finished["normal"][1])
        self.assertEqual(finished["orm"][1][0::3], finished["ao"][1])
        self.assertEqual(finished["orm"][1][1::3], finished["roughness"][1])
        self.assertEqual(finished["orm"][1][2::3], finished["metallic"][1])

    def test_finished_bundle_roundtrips_through_existing_blender_bridge(self):
        with tempfile.TemporaryDirectory(prefix="axm-finished-layered-") as temp:
            folder = Path(temp) / "bundle"
            manifest = generate_finished_layered_game_material(
                folder,
                "sun-faded-plastic",
                [
                    {"type": "salt", "amount": .25},
                    {"type": "decal-stripe", "amount": .18, "color": [235, 224, 190]},
                ],
                size=24,
                seed=71,
                color=(225, 133, 28),
                finish="comic-salvage",
            )
            self.assertEqual(manifest["game_finish"], "comic-salvage")
            self.assertEqual(manifest["schema"], "axm.layered-game-material/v0.1")
            loaded = load_rich_material_bundle(folder)
            self.assertEqual(loaded["manifest_kind"], "layered")
            self.assertEqual(loaded["manifest"]["game_finish"], "comic-salvage")
            self.assertEqual(len(loaded["manifest"]["layers"]), 2)
            self.assertEqual(set(loaded["manifest"]["maps"]), {
                "base_color", "roughness", "metallic", "height", "normal", "ao", "orm"
            })

    def _run_cli(self, argv):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = material_cli(argv)
        self.assertEqual(code, 0)
        return json.loads(stream.getvalue())

    def test_layer_cli_accepts_explicit_game_finish(self):
        with tempfile.TemporaryDirectory(prefix="axm-finished-cli-") as temp:
            root = Path(temp)
            request = root / "request.json"
            request.write_text(json.dumps({
                "schema": "axm.layered-game-material-request/v0.1",
                "base_profile": "canvas",
                "finish": "painted-adventure",
                "size": 16,
                "seed": 7,
                "color": [171, 71, 58],
                "layers": [{"type": "sun-bleach", "amount": .25}],
            }), encoding="utf-8")
            target = root / "out"
            payload = self._run_cli(["layer-create", str(request), str(target)])
            self.assertEqual(payload["game_finish"], "painted-adventure")
            self.assertTrue((target / "layered-game-material.json").is_file())
            self.assertTrue((target / payload["layers"][0]["file"]).is_file())

    def test_finish_names_are_bounded_known_uc_profiles(self):
        self.assertEqual(
            set(FINISH_BY_NAME),
            {"realistic", "comic-salvage", "painted-adventure", "graphic-toon"},
        )
        with self.assertRaisesRegex(ValueError, "unknown game finish"):
            finished_layered_game_material_fields("canvas", [], 16, 1, None, "secret-style")


if __name__ == "__main__":
    unittest.main()

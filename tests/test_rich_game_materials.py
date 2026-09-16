import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_uc.layered_game_materials import (
    LAYER_BY_NAME,
    generate_layered_game_material,
    layered_game_material_catalog,
    layered_game_material_fields,
)
from axm_uc.rich_game_materials import (
    PROFILE_BY_NAME,
    PROFILES,
    generate_rich_game_material,
    rich_game_material_catalog,
    rich_game_material_fields,
)
from axm_uc.rich_game_material_bridge import load_rich_material_bundle
from axm_uc.rich_game_material_cli import main as rich_material_cli


class RichGameMaterialTests(unittest.TestCase):
    def test_rich_catalog_exposes_broad_game_surface_range(self):
        names = {profile.name for profile in PROFILES}
        self.assertGreaterEqual(len(names), 18)
        self.assertTrue({
            "molded-plastic", "sun-faded-plastic", "painted-fiberglass",
            "canvas", "sailcloth", "dry-rope", "weathered-aluminum",
            "oxidized-steel", "driftwood", "eva-foam", "weathered-rubber",
        } <= names)
        catalog = rich_game_material_catalog()
        self.assertEqual(catalog["schema"], "axm.rich-game-material-catalog/v0.1")
        self.assertEqual(catalog["dependencies"], [])

    def test_rich_material_fields_are_complete_and_deterministic(self):
        for profile in sorted(PROFILE_BY_NAME):
            with self.subTest(profile=profile):
                first = rich_game_material_fields(profile, size=24, seed=77)
                second = rich_game_material_fields(profile, size=24, seed=77)
                self.assertEqual(first, second)
                self.assertEqual(
                    set(first),
                    {"base_color", "roughness", "metallic", "height", "normal", "ao", "orm"},
                )
                self.assertEqual(len(first["base_color"][1]), 24 * 24 * 3)
                self.assertEqual(len(first["normal"][1]), 24 * 24 * 3)
                self.assertEqual(len(first["orm"][1]), 24 * 24 * 3)
                self.assertEqual(first["orm"][1][0::3], first["ao"][1])
                self.assertEqual(first["orm"][1][1::3], first["roughness"][1])
                self.assertEqual(first["orm"][1][2::3], first["metallic"][1])

    def test_profiles_are_visually_distinct_in_generated_fields(self):
        plastic = rich_game_material_fields("molded-plastic", 32, 9)
        rope = rich_game_material_fields("dry-rope", 32, 9)
        metal = rich_game_material_fields("weathered-aluminum", 32, 9)
        self.assertNotEqual(plastic["base_color"][1], rope["base_color"][1])
        self.assertNotEqual(plastic["normal"][1], rope["normal"][1])
        self.assertNotEqual(metal["metallic"][1], plastic["metallic"][1])

    def test_bundle_roundtrip_and_tamper_detection(self):
        with tempfile.TemporaryDirectory(prefix="axm-rich-material-test-") as temp:
            folder = Path(temp) / "material"
            manifest = generate_rich_game_material(
                folder, "sun-faded-plastic", 32, 123, (220, 132, 31)
            )
            loaded = load_rich_material_bundle(folder)
            self.assertEqual(loaded["manifest_kind"], "rich")
            self.assertEqual(loaded["manifest"]["profile"], "sun-faded-plastic")
            self.assertEqual(
                loaded["manifest"]["maps"]["base_color"]["sha256"],
                manifest["maps"]["base_color"]["sha256"],
            )

            base = folder / "base_color.png"
            base.write_bytes(base.read_bytes() + b"x")
            with self.assertRaisesRegex(ValueError, "digest mismatch"):
                load_rich_material_bundle(folder)

    def test_layer_catalog_exposes_readable_game_surface_overlays(self):
        catalog = layered_game_material_catalog()
        self.assertEqual(catalog["schema"], "axm.layered-game-material-catalog/v0.1")
        self.assertGreaterEqual(len(catalog["layer_types"]), 9)
        self.assertTrue({
            "salt", "dirt", "wetness", "scuff", "paint-chip", "rust",
            "sun-bleach", "algae", "decal-stripe",
        } <= set(LAYER_BY_NAME))
        self.assertIn("not mesh-curvature", catalog["truth"])

    def test_layered_fields_are_deterministic_and_change_multiple_channels(self):
        recipe = [
            {"type": "salt", "amount": .35, "scale": 8.0},
            {"type": "scuff", "amount": .28, "scale": 17.0},
            {"type": "wetness", "amount": .12, "scale": 3.0},
        ]
        base = rich_game_material_fields("sun-faded-plastic", 24, 91, (220, 128, 30))
        first, first_masks = layered_game_material_fields(
            "sun-faded-plastic", recipe, 24, 91, (220, 128, 30)
        )
        second, second_masks = layered_game_material_fields(
            "sun-faded-plastic", recipe, 24, 91, (220, 128, 30)
        )
        self.assertEqual(first, second)
        self.assertEqual(first_masks, second_masks)
        self.assertNotEqual(first["base_color"][1], base["base_color"][1])
        self.assertNotEqual(first["roughness"][1], base["roughness"][1])
        self.assertNotEqual(first["normal"][1], base["normal"][1])
        self.assertEqual(first["orm"][1][0::3], first["ao"][1])
        self.assertEqual(first["orm"][1][1::3], first["roughness"][1])
        self.assertEqual(first["orm"][1][2::3], first["metallic"][1])
        self.assertEqual([m["type"] for m in first_masks], ["salt", "scuff", "wetness"])

    def test_layered_bundle_roundtrips_through_existing_blender_bridge_contract(self):
        with tempfile.TemporaryDirectory(prefix="axm-layered-material-test-") as temp:
            folder = Path(temp) / "layered"
            manifest = generate_layered_game_material(
                folder,
                "weathered-aluminum",
                [
                    {"type": "salt", "amount": .25},
                    {"type": "scuff", "amount": .30},
                ],
                size=24,
                seed=51,
                color=(72, 84, 92),
            )
            loaded = load_rich_material_bundle(folder)
            self.assertEqual(loaded["manifest_kind"], "layered")
            self.assertEqual(loaded["manifest"]["base_profile"], "weathered-aluminum")
            self.assertEqual(len(loaded["manifest"]["layers"]), 2)
            self.assertEqual(
                loaded["manifest"]["maps"]["normal"]["sha256"],
                manifest["maps"]["normal"]["sha256"],
            )
            mask = folder / loaded["manifest"]["layers"][0]["file"]
            mask.write_bytes(mask.read_bytes() + b"x")
            with self.assertRaisesRegex(ValueError, "mask digest mismatch"):
                load_rich_material_bundle(folder)

    def test_layer_validation_rejects_hidden_or_unbounded_inputs(self):
        with self.assertRaisesRegex(ValueError, "unknown type"):
            layered_game_material_fields("canvas", [{"type": "magic-ai-wear"}], 16, 1)
        with self.assertRaisesRegex(ValueError, "amount"):
            layered_game_material_fields("canvas", [{"type": "dirt", "amount": 1.2}], 16, 1)
        with self.assertRaisesRegex(ValueError, "at most 16"):
            layered_game_material_fields("canvas", [{"type": "dirt"}] * 17, 16, 1)

    def _run_cli(self, argv):
        stream = io.StringIO()
        with contextlib.redirect_stdout(stream):
            code = rich_material_cli(argv)
        self.assertEqual(code, 0)
        return json.loads(stream.getvalue())

    def test_rich_material_cli_catalog_is_normal_uc_surface(self):
        payload = self._run_cli(["catalog"])
        self.assertEqual(payload["schema"], "axm.rich-game-material-catalog/v0.1")
        self.assertGreaterEqual(len(payload["profiles"]), 18)
        layers = self._run_cli(["layer-catalog"])
        self.assertEqual(layers["schema"], "axm.layered-game-material-catalog/v0.1")

    def test_rich_material_cli_creates_immutable_portable_bundle(self):
        with tempfile.TemporaryDirectory(prefix="axm-rich-material-cli-") as temp:
            target = Path(temp) / "canvas"
            payload = self._run_cli([
                "create", "canvas", str(target), "--size", "16", "--seed", "44",
                "--color", "150", "82", "57",
            ])
            self.assertEqual(payload["profile"], "canvas")
            self.assertEqual(payload["size"], 16)
            self.assertEqual(payload["color"], [150, 82, 57])
            self.assertEqual(
                set(payload["maps"]),
                {"base_color", "roughness", "metallic", "height", "normal", "ao", "orm"},
            )
            for record in payload["maps"].values():
                self.assertTrue((target / record["file"]).is_file())

    def test_layered_cli_recipe_preserves_masks_and_receipt(self):
        with tempfile.TemporaryDirectory(prefix="axm-layered-material-cli-") as temp:
            root = Path(temp)
            request = root / "request.json"
            request.write_text(json.dumps({
                "schema": "axm.layered-game-material-request/v0.1",
                "base_profile": "painted-fiberglass",
                "size": 16,
                "seed": 92,
                "color": [38, 111, 142],
                "layers": [
                    {"type": "salt", "amount": .30},
                    {"type": "decal-stripe", "amount": .25, "color": [220, 60, 40]},
                ],
            }), encoding="utf-8")
            target = root / "output"
            payload = self._run_cli(["layer-create", str(request), str(target)])
            self.assertEqual(payload["schema"], "axm.layered-game-material/v0.1")
            self.assertEqual(payload["base_profile"], "painted-fiberglass")
            self.assertEqual(len(payload["layers"]), 2)
            self.assertTrue((target / payload["layers"][0]["file"]).is_file())
            self.assertTrue((target / "layered-game-material.json").is_file())


if __name__ == "__main__":
    unittest.main()

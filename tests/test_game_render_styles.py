import copy
import io
import json
import struct
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from axm_uc.game_render_styles import (apply_game_render_style, game_render_style_catalog,
                                       publish_game_render_style)
from axm_uc.procedural_3d import build_glb, verify_glb
from axm_uc.visual_assets_cli import main


def fixture():
    positions = [[0, 0, 0], [1, 0, 0], [0, 1, 0],
                 [0, 0, 0], [0, 1, 0], [0, 0, 1]]
    normals = [[0, 0, 1]] * 3 + [[1, 0, 0]] * 3
    return {"schema": "axm.surface-3d/v0.1", "name": "render-style-fixture", "primitives": [{
        "id": "panel__paint", "positions": positions, "normals": normals,
        "indices": [0, 1, 2, 3, 4, 5],
        "colors": [[.92, .84, .72, 1], [.86, .78, .67, 1], [.80, .73, .62, 1],
                   [.92, .84, .72, 1], [.86, .78, .67, 1], [.80, .73, .62, 1]],
        "material": {"color": "#7F5A32FF", "metallic": .35, "roughness": .72},
    }]}


def glb_document(body):
    length = struct.unpack_from("<I", body, 12)[0]
    return json.loads(body[20:20 + length])


class GameRenderStyleTests(unittest.TestCase):
    def test_catalog_separates_portable_bake_from_engine_shader_features(self):
        catalog = game_render_style_catalog()
        names = {row["name"] for row in catalog["styles"]}
        self.assertEqual(names, {"realistic-pbr", "graphic-toon-baked", "painted-adventure-baked"})
        self.assertIn("camera-responsive outlines", catalog["target_engine_adapter_features"])
        self.assertEqual(catalog["portable_dynamic_features"], [])
        self.assertTrue(catalog["canonical_source_preserved"])

    def test_realistic_is_exact_pbr_identity_and_keeps_legacy_glb_shape(self):
        mesh = fixture()
        result = apply_game_render_style(mesh, "realistic-pbr", 9)
        self.assertEqual(result["source"], mesh)
        self.assertEqual(result["realization"], mesh)
        document = build_glb(result["realization"])["document"]
        self.assertNotIn("extensionsUsed", document)
        self.assertNotIn("unlit", result["realization"]["primitives"][0]["material"])

    def test_graphic_style_changes_final_color_not_geometry_and_exports_unlit(self):
        mesh = fixture()
        original = copy.deepcopy(mesh)
        result = apply_game_render_style(mesh, "graphic-toon-baked", 471)
        self.assertEqual(mesh, original)
        self.assertEqual(result["source"], original)
        source, styled = original["primitives"][0], result["realization"]["primitives"][0]
        for key in ("positions", "normals", "indices"):
            self.assertEqual(styled[key], source[key])
        self.assertNotEqual(styled["colors"], source["colors"])
        self.assertEqual(styled["material"], {"color": "#FFFFFFFF", "metallic": 0,
                                               "roughness": 1, "unlit": True})
        built = build_glb(result["realization"])
        document = built["document"]
        self.assertEqual(document["extensionsRequired"], ["KHR_materials_unlit"])
        self.assertEqual(document["materials"][0]["extensions"], {"KHR_materials_unlit": {}})
        self.assertEqual(verify_glb(built["body"])["unlit_materials"], 1)

    def test_painterly_is_deterministic_position_coherent_and_seeded(self):
        mesh = fixture()
        a = apply_game_render_style(mesh, "painted-adventure-baked", 4)
        b = apply_game_render_style(mesh, "painted-adventure-baked", 4)
        c = apply_game_render_style(mesh, "painted-adventure-baked", 5)
        self.assertEqual(a, b)
        self.assertNotEqual(a["realization"]["primitives"][0]["colors"],
                            c["realization"]["primitives"][0]["colors"])
        self.assertNotEqual(a["realization"]["primitives"][0]["colors"],
                            apply_game_render_style(mesh, "graphic-toon-baked", 4)["realization"]["primitives"][0]["colors"])

    def test_light_direction_changes_bake_and_zero_direction_fails(self):
        mesh = fixture()
        top = apply_game_render_style(mesh, light_direction=(0, 0, 1))
        side = apply_game_render_style(mesh, light_direction=(1, 0, 0))
        self.assertNotEqual(top["realization"], side["realization"])
        with self.assertRaisesRegex(ValueError, "must not be zero"):
            apply_game_render_style(mesh, light_direction=(0, 0, 0))

    def test_publisher_emits_actual_glb_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "render"
            result = publish_game_render_style(target, fixture(), "graphic-toon-baked", 7)
            self.assertEqual(result["files"], ["asset.glb", "realization.json", "render-style.json", "source.json"])
            self.assertEqual(verify_glb((target / "asset.glb").read_bytes())["unlit_materials"], 1)
            with self.assertRaises(FileExistsError):
                publish_game_render_style(target, fixture())

    def test_cli_publishes_selected_style(self):
        with tempfile.TemporaryDirectory() as tmp:
            request, target = Path(tmp) / "request.json", Path(tmp) / "result"
            request.write_text(json.dumps({"mesh": fixture()}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["game-render", str(request), str(target),
                                       "--style", "painted-adventure-baked", "--seed", "31",
                                       "--light", "-.2", ".9", ".4"]), 0)
            manifest = json.loads((target / "render-style.json").read_text())
            self.assertEqual(manifest["style"]["name"], "painted-adventure-baked")

    def test_validation_rejects_missing_colors_unknown_fields_and_bad_unlit_type(self):
        mesh = fixture()
        broken = copy.deepcopy(mesh)
        broken["primitives"][0].pop("colors")
        with self.assertRaisesRegex(ValueError, "linear RGBA"):
            apply_game_render_style(broken)
        broken = copy.deepcopy(mesh)
        broken["primitives"][0]["material"]["secret"] = "shader"
        with self.assertRaisesRegex(ValueError, "fields"):
            apply_game_render_style(broken)
        broken = copy.deepcopy(mesh)
        broken["primitives"][0]["material"]["unlit"] = 1
        with self.assertRaisesRegex(ValueError, "boolean"):
            apply_game_render_style(broken)


if __name__ == "__main__":
    unittest.main()

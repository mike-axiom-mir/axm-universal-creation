import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from axm_uc.game_form_styles import apply_game_form, game_form_catalog, publish_game_form
from axm_uc.visual_assets_cli import main


def cube(component, center=(0, 1, 0), size=(2, 2, 2), material="#E2A42BFF"):
    cx, cy, cz = center
    sx, sy, sz = (value / 2 for value in size)
    positions = [[cx + x * sx, cy + y * sy, cz + z * sz]
                 for x, y, z in ((-1, -1, -1), (1, -1, -1), (1, 1, -1), (-1, 1, -1),
                                 (-1, -1, 1), (1, -1, 1), (1, 1, 1), (-1, 1, 1))]
    indices = [0, 2, 1, 0, 3, 2, 4, 5, 6, 4, 6, 7,
               0, 1, 5, 0, 5, 4, 3, 7, 6, 3, 6, 2,
               0, 4, 7, 0, 7, 3, 1, 2, 6, 1, 6, 5]
    return {"id": component + "__paint", "positions": positions,
            "normals": [[0, 1, 0] for _ in positions], "indices": indices,
            "colors": [[1, 1, 1, 1] for _ in positions],
            "material": {"color": material, "metallic": .4, "roughness": .7}}


def fixture():
    mesh = {"schema": "axm.surface-3d/v0.1", "name": "form-fixture",
            "primitives": [cube("body"), cube("tool", (1.65, 1.4, 0), (.8, .8, .8)),
                           cube("badge", (0, 1.6, -1.1), (.4, .4, .2))]}
    parts = {
        "body": {"role": "body", "hierarchy": "large",
                 "anchors": {"ground": [0, 0, 0]}, "anchor_falloff": .2},
        "tool": {"role": "functional", "hierarchy": "medium",
                 "anchors": {"socket": [1.25, 1.4, 0]}, "anchor_falloff": .2},
        "badge": {"role": "detail", "hierarchy": "small", "anchors": {}},
    }
    return mesh, parts


class GameFormStyleTests(unittest.TestCase):
    def test_catalog_keeps_realistic_and_distinct_game_profiles(self):
        catalog = game_form_catalog()
        profiles = {row["name"]: row for row in catalog["styles"]}
        self.assertEqual(set(profiles), {"realistic", "comic-salvage", "heroic-toon", "storybook-chunky"})
        self.assertEqual(profiles["realistic"]["vertical_scale"], 1)
        self.assertGreater(profiles["comic-salvage"]["functional_scale"], 1.25)
        self.assertNotEqual(profiles["comic-salvage"]["taper"], 0)
        self.assertTrue(catalog["preserves_canonical_source"])

    def test_realistic_is_geometry_identity_and_source_is_immutable(self):
        mesh, parts = fixture()
        original = copy.deepcopy(mesh)
        result = apply_game_form(mesh, parts, "realistic", 9)
        self.assertEqual(mesh, original)
        self.assertEqual(result["source"], original)
        self.assertEqual(result["realization"], original)
        self.assertTrue(result["gates"]["canonical-source-embedded"])

    def test_comic_form_changes_geometry_not_materials_or_source(self):
        mesh, parts = fixture()
        original = copy.deepcopy(mesh)
        result = apply_game_form(mesh, parts, "comic-salvage", 471)
        self.assertEqual(result["source"], original)
        source_by_id = {p["id"]: p for p in original["primitives"]}
        changed = 0
        for primitive in result["realization"]["primitives"]:
            source = source_by_id[primitive["id"]]
            changed += primitive["positions"] != source["positions"]
            self.assertEqual(primitive["material"], source["material"])
            self.assertEqual(primitive["colors"], source["colors"])
            for normal in primitive["normals"]:
                self.assertAlmostEqual(sum(value * value for value in normal), 1, places=6)
        self.assertEqual(changed, 3)

    def test_functional_exaggeration_and_small_detail_suppression_are_real(self):
        mesh, parts = fixture()
        result = apply_game_form(mesh, parts, "comic-salvage", 471)["realization"]
        output = {primitive["id"].split("__")[0]: primitive for primitive in result["primitives"]}
        def width(primitive):
            xs = [point[0] for point in primitive["positions"]]
            return max(xs) - min(xs)
        self.assertGreater(width(output["tool"]), .8)
        self.assertLess(width(output["badge"]), .4)
        self.assertNotAlmostEqual(width(output["body"]), 2)

    def test_declared_contacts_and_sockets_are_exactly_preserved(self):
        mesh, parts = fixture()
        result = apply_game_form(mesh, parts, "storybook-chunky", 71)
        self.assertTrue(result["gates"]["all-declared-anchors-preserved"])
        self.assertEqual({row["name"] for row in result["anchor_receipt"]}, {"ground", "socket"})
        for row in result["anchor_receipt"]:
            self.assertEqual(row["before"], row["after"])
            self.assertEqual(row["drift"], 0)

    def test_asymmetry_is_deterministic_and_seeded(self):
        mesh, parts = fixture()
        a = apply_game_form(mesh, parts, "comic-salvage", 1)["realization"]
        b = apply_game_form(mesh, parts, "comic-salvage", 1)["realization"]
        variants = [apply_game_form(mesh, parts, "comic-salvage", seed)["realization"]
                    for seed in range(2, 12)]
        self.assertEqual(a, b)
        self.assertTrue(any(candidate != a for candidate in variants))

    def test_cli_publishes_source_realization_and_refuses_overwrite(self):
        mesh, parts = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp) / "request.json"
            output = Path(tmp) / "form"
            request.write_text(json.dumps({"mesh": mesh, "parts": parts}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["game-form", str(request), str(output),
                                       "--style", "heroic-toon", "--seed", "17"]), 0)
            self.assertEqual(sorted(path.name for path in output.iterdir()),
                             ["form-manifest.json", "realization.json", "source.json"])
            manifest = json.loads((output / "form-manifest.json").read_text())
            self.assertEqual(manifest["style"]["name"], "heroic-toon")
            self.assertTrue(manifest["gates"]["all-declared-anchors-preserved"])
            with self.assertRaises(FileExistsError):
                publish_game_form(output, mesh, parts)

    def test_validation_rejects_partial_specs_invalid_anchors_and_bad_triangles(self):
        mesh, parts = fixture()
        for bad in ({"body": parts["body"]}, {**parts, "ghost": parts["body"]}):
            with self.assertRaisesRegex(ValueError, "exactly cover"):
                apply_game_form(mesh, bad)
        broken = copy.deepcopy(parts)
        broken["body"]["anchors"] = {"bad": [0, float("nan"), 0]}
        with self.assertRaisesRegex(ValueError, "finite"):
            apply_game_form(mesh, broken)
        broken_mesh = copy.deepcopy(mesh)
        broken_mesh["primitives"][0]["indices"] = [0, 1]
        with self.assertRaisesRegex(ValueError, "triangles"):
            apply_game_form(broken_mesh, parts)


if __name__ == "__main__":
    unittest.main()

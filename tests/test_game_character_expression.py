import copy
import io
import json
import math
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from axm_uc.game_character_expression import (apply_character_expression,
                                               game_character_expression_catalog,
                                               publish_character_expression)
from axm_uc.procedural_3d import verify_glb
from axm_uc.rts_mesh import SalvageMesh
from axm_uc.visual_assets_cli import main


def fixture():
    mesh = SalvageMesh()
    with mesh.part("body", (0, 0, 0)):
        mesh.roundbox("body", (0, .8, 0), (1.1, 1.2, .55), "paint", .1)
    with mesh.part("head", (0, 1.65, 0)):
        mesh.ellipsoid("head", (0, 1.65, 0), (1.0, .72, .58), "ivory", 10, 6)
    with mesh.part("shell", (0, 1.65, .31)):
        mesh.ring("identity-ring", (0, 1.65, .31), .30, .035, "signal", axis="z")
    with mesh.part("nose", (0, 1.57, .38)):
        mesh.ellipsoid("nose", (0, 1.57, .38), (.12, .10, .10), "signal", 7, 4)
    for side, x in (("left", -.20), ("right", .20)):
        with mesh.part(f"eye_{side}", (x, 1.73, .36)):
            mesh.ellipsoid("eye", (x, 1.73, .36), (.20, .20, .08), "cyan", 8, 5)
        with mesh.part(f"brow_{side}", (x, 1.90, .39)):
            mesh.beam("brow", (x-.10, 1.90, .39), (x+.10, 1.90, .39), .035, .035, "rubber")
    with mesh.part("mouth", (0, 1.46, .39)):
        mesh.beam("mouth", (-.16, 1.46, .39), (.16, 1.46, .39), .045, .035, "red")
    for side, x in (("left", -.64), ("right", .64)):
        with mesh.part(f"arm_{side}", (x, 1.23, 0)):
            mesh.beam("arm", (x, 1.23, 0), (x, .58, .04), .16, .16, "iron")
        with mesh.part(f"leg_{side}", (x*.48, .28, 0)):
            mesh.beam("leg", (x*.48, .28, 0), (x*.48, -.24, 0), .20, .22, "signal")
    with mesh.part("prop", (-.64, .52, .04)):
        mesh.ring("wrench", (-.64, .32, .04), .16, .045, "signal", axis="z", ratio=.7)
    return mesh.surface_spec("character-expression-fixture")


def specs(mesh=None):
    return {
        "body": {"role": "body", "side": "center", "parent": None, "pivot": [0, .2, 0]},
        "head": {"role": "head", "side": "center", "parent": "body", "pivot": [0, 1.35, 0]},
        "shell": {"role": "face-shell", "side": "center", "parent": "head", "pivot": [0, 1.65, .31], "identity_protected": True},
        "nose": {"role": "identity", "side": "center", "parent": "head", "pivot": [0, 1.57, .38], "identity_protected": True},
        "eye_left": {"role": "eye", "side": "left", "parent": "head", "pivot": [-.20, 1.73, .36]},
        "eye_right": {"role": "eye", "side": "right", "parent": "head", "pivot": [.20, 1.73, .36]},
        "brow_left": {"role": "brow", "side": "left", "parent": "head", "pivot": [-.20, 1.90, .39]},
        "brow_right": {"role": "brow", "side": "right", "parent": "head", "pivot": [.20, 1.90, .39]},
        "mouth": {"role": "mouth", "side": "center", "parent": "head", "pivot": [0, 1.46, .39]},
        "arm_left": {"role": "arm", "side": "left", "parent": "body", "pivot": [-.64, 1.23, 0]},
        "arm_right": {"role": "arm", "side": "right", "parent": "body", "pivot": [.64, 1.23, 0]},
        "leg_left": {"role": "leg", "side": "left", "parent": "body", "pivot": [-.31, .28, 0]},
        "leg_right": {"role": "leg", "side": "right", "parent": "body", "pivot": [.31, .28, 0]},
        "prop": {"role": "prop", "side": "left", "parent": "arm_left", "pivot": [-.64, .52, .04]},
    }


class CharacterExpressionTests(unittest.TestCase):
    def test_catalog_states_static_identity_and_animation_boundaries(self):
        catalog = game_character_expression_catalog()
        self.assertEqual({row["name"] for row in catalog["expressions"]},
                         {"neutral", "curious", "mischief", "alarmed", "determined"})
        self.assertIn("victory", {row["name"] for row in catalog["stances"]})
        self.assertIn("does not infer a rig", catalog["truth"])

    def test_neutral_expression_and_stance_are_exact_identity(self):
        mesh = fixture()
        result = apply_character_expression(mesh, specs(), "neutral", "neutral")
        self.assertEqual(result["source"], mesh)
        self.assertEqual(result["realization"], mesh)
        self.assertTrue(result["identity_receipt"]["passed"])

    def test_mischief_ready_changes_geometry_without_mutating_source(self):
        mesh, parts = fixture(), specs()
        original, authored = copy.deepcopy(mesh), copy.deepcopy(parts)
        result = apply_character_expression(mesh, parts, "mischief", "mechanic-ready")
        self.assertEqual(mesh, original)
        self.assertEqual(parts, authored)
        self.assertNotEqual(result["realization"], original)
        self.assertTrue(result["gates"]["protected-identity-preserved"])

    def test_nonuniform_expression_uses_inverse_transpose_authored_normals(self):
        mesh = fixture()
        eye = next(p for p in mesh["primitives"] if p["id"].startswith("eye_left__"))
        eye["normals"][0] = [math.sqrt(.5), math.sqrt(.5), 0]
        result = apply_character_expression(mesh, specs(), "curious", "neutral")
        styled = next(p for p in result["realization"]["primitives"] if p["id"].startswith("eye_left__"))
        normal = styled["normals"][0]
        self.assertAlmostEqual(math.sqrt(sum(value * value for value in normal)), 1, places=7)
        self.assertNotAlmostEqual(normal[0], normal[1], places=3)

    def test_mischief_winks_and_preserves_authored_eye_spacing(self):
        mesh = fixture()
        result = apply_character_expression(mesh, specs(), "mischief", "neutral")
        source = {p["id"].split("__", 1)[0]: p for p in mesh["primitives"]}
        styled = {p["id"].split("__", 1)[0]: p for p in result["realization"]["primitives"]}
        def span_y(primitive):
            return max(p[1] for p in primitive["positions"]) - min(p[1] for p in primitive["positions"])
        self.assertGreater(span_y(styled["eye_left"]), span_y(styled["eye_right"]) * 3)
        self.assertAlmostEqual(result["identity_receipt"]["maximum_authored_eye_pivot_spacing_error"], 0)
        self.assertNotEqual(styled["mouth"]["positions"], source["mouth"]["positions"])

    def test_protected_identity_shape_and_relationship_survive_story_pose(self):
        result = apply_character_expression(fixture(), specs(), "alarmed", "comic-sneak")
        receipt = result["identity_receipt"]
        self.assertEqual(receipt["protected_components"], ["nose", "shell"])
        self.assertLessEqual(receipt["maximum_protected_radial_signature_error"], 1e-7)
        self.assertLessEqual(receipt["maximum_protected_pairwise_pivot_distance_error"], 1e-7)

    def test_all_expression_stance_pairs_are_deterministic_valid_glbs(self):
        mesh, parts = fixture(), specs()
        catalog = game_character_expression_catalog()
        for expression in (row["name"] for row in catalog["expressions"]):
            for stance in (row["name"] for row in catalog["stances"]):
                one = apply_character_expression(mesh, parts, expression, stance)
                two = apply_character_expression(mesh, parts, expression, stance)
                self.assertEqual(one, two)
                self.assertTrue(one["gates"]["static-glb-valid"])

    def test_validation_rejects_cycle_missing_semantics_and_split_identity(self):
        mesh, parts = fixture(), specs()
        broken = copy.deepcopy(parts)
        broken["body"]["parent"] = "head"
        with self.assertRaisesRegex(ValueError, "cycle"):
            apply_character_expression(mesh, broken)
        broken = copy.deepcopy(parts)
        broken.pop("mouth")
        with self.assertRaisesRegex(ValueError, "exactly cover"):
            apply_character_expression(mesh, broken)
        broken = copy.deepcopy(parts)
        broken["nose"]["parent"] = "body"
        with self.assertRaisesRegex(ValueError, "share one parent"):
            apply_character_expression(mesh, broken)

    def test_publisher_and_cli_emit_actual_glb_and_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as tmp:
            direct = Path(tmp) / "direct"
            result = publish_character_expression(direct, fixture(), specs(), "curious", "victory")
            self.assertEqual(result["files"], ["asset.glb", "character-expression.json", "realization.json", "source.json"])
            self.assertGreater(verify_glb((direct / "asset.glb").read_bytes())["triangles"], 0)
            with self.assertRaises(FileExistsError):
                publish_character_expression(direct, fixture(), specs())
            request, target = Path(tmp) / "request.json", Path(tmp) / "cli"
            request.write_text(json.dumps({"mesh": fixture(), "parts": specs()}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["character-expression", str(request), str(target),
                                       "--expression", "alarmed", "--stance", "comic-sneak"]), 0)
            manifest = json.loads((target / "character-expression.json").read_text())
            self.assertEqual(manifest["expression"]["name"], "alarmed")


if __name__ == "__main__":
    unittest.main()

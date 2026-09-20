from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.character_recipe import CharacterRecipeError, compile_character_recipe
from axm_uc.form_pattern import FormPatternError, compile_form_pattern
from axm_uc.machine import UniversalCreationMachine


def form_recipe() -> dict:
    return {
        "schema": "axm.form-pattern/v0.1",
        "name": "Small tree person",
        "parts": [
            {
                "id": "trunk",
                "role": "trunk",
                "pattern": "loft",
                "sections": [
                    {"at": 0.10, "radius": [0.22, 0.18]},
                    {"at": 0.70, "radius": [0.30, 0.22], "offset": [0.03, 0.00]},
                    {"at": 1.10, "radius": [0.25, 0.20], "offset": [-0.02, 0.01]},
                ],
                "segments": 16,
                "material": {"color": "#76502FFF", "metallic": 0.0, "roughness": 0.78},
            },
            {
                "id": "branch-left",
                "role": "branch",
                "pattern": "tube",
                "path": [[-0.08, 0.00, 0.85], [-0.30, 0.00, 1.18], [-0.50, 0.02, 1.32]],
                "radius": [0.07, 0.05, 0.025],
                "segments": 10,
                "material": {"color": "#4A2C18FF", "metallic": 0.0, "roughness": 0.82},
            },
            {
                "id": "eye-shell",
                "role": "face",
                "pattern": "revolve",
                "profile": [[0.02, -0.08], [0.10, -0.04], [0.12, 0.04], [0.04, 0.08]],
                "segments": 18,
                "translation": [0.0, -0.20, 0.92],
                "rotation": [1.57079632679, 0.0, 0.0],
                "material": {"color": "#A86934FF", "metallic": 0.0, "roughness": 0.45},
            },
        ],
        "metadata": {"intent": "cute bonsai-tree playable race"},
    }


def character_recipe() -> dict:
    return {
        "schema": "axm.character-recipe/v0.1",
        "name": "Bonsai race test character",
        "character": {
            "race_id": "bonsai-nature-race",
            "body_family": "rooted-small-tree",
            "height_m": 1.35,
        },
        "form": form_recipe(),
        "sockets": [
            {"id": "hand-right", "part": "trunk", "position": [0.28, 0.0, 0.72], "purpose": "tool attachment"}
        ],
        "clothing_regions": [
            {"id": "torso-wrap", "parts": ["trunk"], "body_family": "rooted-small-tree", "attachment_tags": ["wrap", "belt"]}
        ],
        "material_intent": {
            "families": ["wood", "moss", "leaf"],
            "response": {"family": "wood-oiled"},
            "part_responses": {"branch-left": {"family": "wood-oiled"}},
            "notes": "retained intent; renderer binding remains separate",
        },
    }


class FormAndCharacterRecipeTests(unittest.TestCase):
    def test_base_procedural_3d_route_retains_specification_by_default(self):
        specification = {
            "schema": "axm.procedural-3d/v0.1",
            "name": "retained box",
            "primitives": [{
                "id": "body",
                "type": "box",
                "size": [1.0, 2.0, 3.0],
                "translation": [0.0, 0.0, 0.0],
                "material": {"color": "#887766FF", "metallic": 0.0, "roughness": 0.7}
            }]
        }
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "box.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "procedural-3d-asset",
                "inputs": {"path": str(target), "specification": specification},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            source = json.loads(Path(result["result"]["creator_source"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(source["kind"], "procedural-3d-specification")
            self.assertEqual(source["specification"], specification)
            self.assertTrue(source["source_authority"])

    def test_freeform_patterns_compile_to_explicit_surfaces(self):
        compiled = compile_form_pattern(form_recipe())
        self.assertEqual(compiled["truth_status"], "COMPILED_GENERIC_SURFACE_PATTERN")
        self.assertEqual(compiled["part_count"], 3)
        self.assertGreater(compiled["vertex_count"], 50)
        self.assertGreater(compiled["triangle_count"], 50)
        self.assertEqual(compiled["specification"]["schema"], "axm.surface-3d/v0.1")
        self.assertEqual({row["pattern"] for row in compiled["parts_index"]}, {"loft", "tube", "revolve"})

    def test_form_route_publishes_glb_and_exact_source_sidecar(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "tree.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "form-pattern-asset",
                "inputs": {"path": str(target), "recipe": form_recipe()},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertTrue(target.is_file())
            sidecar = Path(body["creator_source"]["path"])
            self.assertTrue(sidecar.is_file())
            source = json.loads(sidecar.read_text(encoding="utf-8"))
            self.assertEqual(source["kind"], "form-pattern")
            self.assertEqual(source["recipe"], form_recipe())
            self.assertTrue(source["source_authority"])
            self.assertTrue(source["realization_is_secondary"])

    def test_whole_character_retains_body_family_sockets_clothing_and_material_intent(self):
        compiled = compile_character_recipe(character_recipe())
        self.assertEqual(compiled["truth_status"], "COMPILED_STATIC_WHOLE_CHARACTER")
        self.assertEqual(compiled["character"]["body_family"], "rooted-small-tree")
        self.assertEqual(compiled["sockets"][0]["id"], "hand-right")
        self.assertEqual(compiled["clothing_regions"][0]["id"], "torso-wrap")
        self.assertEqual(compiled["material_response_status"], "HOLD_RENDERER_BINDING_NOT_TESTED")
        self.assertEqual(compiled["material_response_holds"], ["branch-left", "default"])
        self.assertIn("surface.anisotropy", compiled["material_response_resolutions"]["default"]["active_organs"])

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "character.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "character-recipe-asset",
                "inputs": {"path": str(target), "recipe": character_recipe()},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            source = json.loads(Path(result["result"]["creator_source"]["path"]).read_text(encoding="utf-8"))
            self.assertEqual(source["kind"], "whole-character-recipe")
            self.assertEqual(source["character"]["race_id"], "bonsai-nature-race")
            self.assertEqual(source["clothing_regions"][0]["body_family"], "rooted-small-tree")
            self.assertEqual(source["material_intent"]["families"], ["wood", "moss", "leaf"])
            self.assertEqual(source["rig_status"], "NOT_PRESENT")
            self.assertEqual(source["animation_status"], "NOT_PRESENT")

    def test_generic_rig_and_animation_requests_hold_instead_of_faking_support(self):
        rigged = character_recipe()
        rigged["rig"] = {"kind": "humanoid"}
        with self.assertRaises(CharacterRecipeError) as caught:
            compile_character_recipe(rigged)
        self.assertEqual(caught.exception.status, "HOLD_GENERIC_CHARACTER_RIG_NOT_IMPLEMENTED")

        animated = character_recipe()
        animated["animation"] = ["idle"]
        with self.assertRaises(CharacterRecipeError) as caught:
            compile_character_recipe(animated)
        self.assertEqual(caught.exception.status, "HOLD_GENERIC_CHARACTER_ANIMATION_NOT_IMPLEMENTED")

    def test_invalid_freeform_pattern_holds(self):
        recipe = form_recipe()
        recipe["parts"][0]["pattern"] = "magic-sculpt"
        with self.assertRaises(FormPatternError) as caught:
            compile_form_pattern(recipe)
        self.assertEqual(caught.exception.status, "HOLD_FORM_PATTERN_UNSUPPORTED_PATTERN")


if __name__ == "__main__":
    unittest.main()

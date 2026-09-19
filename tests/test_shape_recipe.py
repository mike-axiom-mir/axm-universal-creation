from __future__ import annotations

import tempfile
import unittest
from copy import deepcopy
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb
from axm_uc.shape_recipe import (
    SOURCE_PROVENANCE,
    ShapeRecipeError,
    compile_shape_recipe,
)


def lattice_recipe(n: int = 4) -> dict:
    return {
        "schema": "axm.shape-recipe/v0.1",
        "name": "Lattice shell",
        "vars": {"n": n, "gap": 0.55},
        "parts": [
            {
                "repeat": ["var", "n"],
                "as": "x",
                "body": [
                    {
                        "repeat": ["var", "n"],
                        "as": "y",
                        "body": [
                            {
                                "repeat": ["var", "n"],
                                "as": "z",
                                "body": [
                                    {
                                        "when": [
                                            "or",
                                            ["or", ["==", ["var", "x"], 0], ["==", ["var", "y"], 0]],
                                            ["==", ["var", "z"], 0],
                                        ],
                                        "shape": "box",
                                        "size": [0.2, 0.2, 0.2],
                                        "pos": [
                                            ["*", ["var", "gap"], ["var", "x"]],
                                            ["*", ["var", "gap"], ["var", "y"]],
                                            ["*", ["var", "gap"], ["var", "z"]],
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ],
            }
        ],
    }


def composed_recipe() -> dict:
    return {
        "schema": "axm.shape-recipe/v0.1",
        "name": "Painted adjustable rails",
        "definitions": {
            "rail": {
                "vars": {"count": 3, "gap": 1.0},
                "parts": [{
                    "repeat": ["var", "count"],
                    "as": "i",
                    "body": [{
                        "shape": "box",
                        "size": [0.4, 0.2, 0.3],
                        "pos": [["*", ["var", "gap"], ["var", "i"]], 0, 0],
                    }],
                }],
            }
        },
        "paint": {
            "vars": {"span": 4.0},
            "color": [
                ["min", 1, ["max", 0, ["/", ["+", ["var", "x"], 2], ["var", "span"]]]],
                0.25,
                ["if", [">", ["var", "y"], 1], 0.9, 0.3],
            ],
        },
        "parts": [
            {"use": "rail", "with": {"count": 2}, "pos": [0, 0, 0]},
            {"use": "rail", "with": {"count": 4}, "pos": [0, 2, 0], "scale": 0.5},
        ],
    }


class ShapeRecipeTests(unittest.TestCase):
    def test_nested_loops_conditions_and_expressions_expand_into_real_geometry(self):
        compiled = compile_shape_recipe(lattice_recipe())
        self.assertEqual(compiled["truth_status"], "COMPILED_BOUNDED_SHAPE_RECIPE")
        self.assertEqual(compiled["parts_generated"], 37)
        self.assertEqual(compiled["specification"]["primitives"][-1]["translation"][2], 0.0)
        self.assertAlmostEqual(compiled["specification"]["primitives"][-1]["translation"][0], 1.65)
        self.assertAlmostEqual(compiled["specification"]["primitives"][-1]["translation"][1], 1.65)
        first = build_glb(compiled["specification"])
        second = build_glb(compile_shape_recipe(lattice_recipe())["specification"])
        self.assertEqual(first["body"], second["body"])

    def test_named_numbers_turn_one_recipe_into_a_family_without_hidden_state(self):
        small = compile_shape_recipe(lattice_recipe(4))
        large = compile_shape_recipe(lattice_recipe(5))
        self.assertEqual(small["parts_generated"], 37)
        self.assertEqual(large["parts_generated"], 61)
        self.assertNotEqual(small["recipe_sha256"], large["recipe_sha256"])
        self.assertEqual(compile_shape_recipe(lattice_recipe(4)), small)

    def test_runaway_depth_work_and_unknown_expressions_hold_before_publication(self):
        runaway = {
            "schema": "axm.shape-recipe/v0.1",
            "name": "Runaway",
            "vars": {"n": 99_999},
            "parts": [{"repeat": ["var", "n"], "body": [{"shape": "box"}]}],
        }
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(runaway)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_OVER_BUDGET")

        over_budget = deepcopy(runaway)
        over_budget["vars"]["n"] = 4_000
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(over_budget)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_OVER_BUDGET")

        body: dict = {"shape": "box"}
        for _ in range(9):
            body = {"body": [body]}
        too_deep = {"schema": "axm.shape-recipe/v0.1", "name": "Deep", "parts": [body]}
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(too_deep)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_TOO_DEEP")

        unknown = {"schema": "axm.shape-recipe/v0.1", "name": "Unknown", "parts": [
            {"shape": "box", "size": [["sin", 1], 1, 1]}
        ]}
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(unknown)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_EXPRESSION")

    def test_receiver_gaps_hold_instead_of_silently_changing_the_shape(self):
        rotated = {"schema": "axm.shape-recipe/v0.1", "name": "Rotated", "parts": [
            {"shape": "box", "rot": [0, 0.5, 0]}
        ]}
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(rotated)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_ROTATION_UNSUPPORTED")

        sphere = {"schema": "axm.shape-recipe/v0.1", "name": "Sphere", "parts": [
            {"shape": "sphere"}
        ]}
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(sphere)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_UNSUPPORTED_SHAPE")

    def test_definitions_compose_with_per_use_settings_and_position_paint(self):
        recipe = composed_recipe()
        unchanged = deepcopy(recipe)
        compiled = compile_shape_recipe(recipe)
        self.assertEqual(recipe, unchanged, "compilation must not rewrite shared definitions")
        self.assertEqual(compiled["parts_generated"], 6)
        self.assertEqual(compiled["definitions_declared"], 1)
        self.assertEqual(compiled["composition_uses"], 2)
        self.assertEqual(compiled["settings_overrides"], 2)
        self.assertEqual(compiled["deepest_composition_depth"], 1)
        self.assertEqual(compiled["paint_mode"], "primitive-center")
        self.assertEqual(compiled["paint_applications"], 6)
        primitives = compiled["specification"]["primitives"]
        self.assertEqual(primitives[2]["translation"], [0.0, 2.0, 0.0])
        self.assertEqual(primitives[2]["size"], [0.2, 0.1, 0.15])
        self.assertNotEqual(primitives[0]["material"]["color"], primitives[-1]["material"]["color"])
        self.assertEqual(
            build_glb(compiled["specification"])["body"],
            build_glb(compile_shape_recipe(composed_recipe())["specification"])["body"],
        )

    def test_composition_holds_missing_cycles_depth_unknown_settings_and_shared_budget(self):
        missing = composed_recipe()
        missing["parts"] = [{"use": "nowhere"}]
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(missing)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_DEFINITION_NOT_FOUND")

        cycle = composed_recipe()
        cycle["definitions"] = {
            "a": {"parts": [{"use": "b"}]},
            "b": {"parts": [{"use": "a"}]},
        }
        cycle["parts"] = [{"use": "a"}]
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(cycle)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_USES_ITSELF")

        deep = composed_recipe()
        deep["definitions"] = {
            f"d{index}": {"parts": [{"use": f"d{index + 1}"}]} for index in range(4)
        }
        deep["definitions"]["d4"] = {"parts": [{"shape": "box"}]}
        deep["parts"] = [{"use": "d0"}]
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(deep)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_COMPOSITION_TOO_DEEP")

        settings = composed_recipe()
        settings["parts"] = [{"use": "rail", "with": {"undeclared": 2}}]
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(settings)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_SETTINGS_NOT_ACCEPTED")

        greedy = composed_recipe()
        greedy["budget"] = 128
        greedy["definitions"]["rail"]["vars"]["count"] = 100
        greedy["parts"] = [{"use": "rail"}, {"use": "rail"}]
        with self.assertRaises(ShapeRecipeError) as caught:
            compile_shape_recipe(greedy)
        self.assertEqual(caught.exception.status, "HOLD_SHAPE_RECIPE_OVER_BUDGET")

    def test_composed_definition_change_reaches_every_use(self):
        recipe = composed_recipe()
        boxes = compile_shape_recipe(recipe)
        recipe["definitions"]["rail"]["parts"][0]["body"][0]["shape"] = "pyramid"
        pyramids = compile_shape_recipe(recipe)
        self.assertTrue(all(part["type"] == "box" for part in boxes["specification"]["primitives"]))
        self.assertTrue(all(part["type"] == "pyramid" for part in pyramids["specification"]["primitives"]))
        self.assertNotEqual(boxes["recipe_sha256"], pyramids["recipe_sha256"])

    def test_live_capability_publishes_through_existing_validated_glb_path(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "lattice.glb"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "shape-recipe-asset",
                "inputs": {"path": str(target), "recipe": lattice_recipe()},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(body["truth_status"], "VALIDATED_DETERMINISTIC_GLB_ASSET")
            self.assertEqual(body["shape_recipe"]["parts_generated"], 37)
            self.assertEqual(body["post_publish_validation"]["primitives"], 37)
            self.assertTrue(body["post_publish_validation"]["passed"])
            self.assertTrue(target.is_file())

    def test_pinned_morphtile_origin_is_visible_without_embedding_its_runtime(self):
        compiled = compile_shape_recipe(lattice_recipe())
        self.assertEqual(
            SOURCE_PROVENANCE["commit"],
            "379098956c4da962b70ad68b60ea1bb8a75f5028",
        )
        self.assertEqual(compiled["source_provenance"], SOURCE_PROVENANCE)
        self.assertIn("no MorphTile runtime", SOURCE_PROVENANCE["integration"])


if __name__ == "__main__":
    unittest.main()

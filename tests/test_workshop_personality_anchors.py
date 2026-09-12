import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "blender" / "axm_salvage_personality.py"


class WorkshopPersonalityAnchorTests(unittest.TestCase):
    def test_source_parses_and_exposes_large_anchor_helpers(self):
        text = SOURCE.read_text(encoding="utf-8")
        tree = ast.parse(text)
        function_names = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertTrue(
            {"salvage_grin", "roof_wheel_vane", "rear_trophy_rack"}.issubset(function_names)
        )

    def test_workshop_life_calls_all_three_large_anchors(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        workshop = next(
            node for node in tree.body
            if isinstance(node, ast.FunctionDef) and node.name == "workshop_life"
        )
        called = {
            node.func.id
            for node in ast.walk(workshop)
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
        }
        self.assertTrue(
            {"salvage_grin", "roof_wheel_vane", "rear_trophy_rack"}.issubset(called)
        )

    def test_anchor_names_remain_semantically_distinct_in_source(self):
        text = SOURCE.read_text(encoding="utf-8")
        for required in (
            "front salvage grin",
            "roof vane salvage wheel",
            "rear trophy spare wheel",
        ):
            self.assertIn(required, text)


if __name__ == "__main__":
    unittest.main()

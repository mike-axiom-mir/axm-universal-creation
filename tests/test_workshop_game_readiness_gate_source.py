import ast
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tools" / "blender" / "verify_rts_workshop.py"


class WorkshopGameReadinessGateSourceTests(unittest.TestCase):
    def test_verifier_source_parses_and_defines_gate_builder(self):
        tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
        function_names = {
            node.name for node in tree.body if isinstance(node, ast.FunctionDef)
        }
        self.assertIn("game_readiness_gates", function_names)

    def test_required_unproven_gates_stay_explicit(self):
        text = SOURCE.read_text(encoding="utf-8")
        for gate in (
            "lod_perceptual_equivalence",
            "collision",
            "navigation",
            "target_engine_import",
            "target_rts_integration",
            "target_device_fps",
            "material_texture_budget_acceptance",
            "visual_quality",
        ):
            self.assertIn(f"'{gate}':'NOT_TESTED'", text)

    def test_cost_surfaces_are_reported(self):
        text = SOURCE.read_text(encoding="utf-8")
        for field in (
            "double_sided_materials",
            "embedded_compressed_bytes",
            "estimated_rgba8_bytes_before_mips",
            "lod1_triangle_ratio",
        ):
            self.assertIn(field, text)

    def test_game_ready_nonclaim_remains_in_source(self):
        text = SOURCE.read_text(encoding="utf-8")
        self.assertIn("A valid GLB is not a game-ready asset by itself.", text)


if __name__ == "__main__":
    unittest.main()

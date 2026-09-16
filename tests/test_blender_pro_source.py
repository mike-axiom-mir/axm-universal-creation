from __future__ import annotations

import ast
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class BlenderProSourceTests(unittest.TestCase):
    def test_blender_pro_helper_is_syntax_valid_and_truth_bounded(self):
        source = (ROOT / "tools" / "blender" / "axm_blender_pro.py").read_text(encoding="utf-8")
        ast.parse(source)
        self.assertIn('"preview"', source)
        self.assertIn('"lookdev"', source)
        self.assertIn('"hero"', source)
        self.assertIn('"proof"', source)
        self.assertIn("visual_acceptance_requires_rendered_review", source)
        self.assertIn("structural_scene_checks_only", source)
        self.assertIn("NATIVE_SCENE_SCHEMA", source)
        self.assertIn("def apply_native_scene", source)
        self.assertIn("shared_scene_contract_realized", source)
        self.assertIn("renderer_pixel_parity_claimed", source)
        self.assertIn("def main(argv:", source)
        self.assertIn("bpy.ops.wm.save_as_mainfile", source)


if __name__ == "__main__":
    unittest.main()

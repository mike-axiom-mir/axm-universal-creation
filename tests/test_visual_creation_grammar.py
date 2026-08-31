from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.visual_creation_grammar import (
    DEFAULT_TEMPORAL_BEATS,
    VISUAL_ALIASES,
    compile_visual_recipe,
    grammar_catalog,
)
from axm_uc.visual_assets_bridge import operate_visual_expansion
from axm_uc.visual_assets_cli import main as cli_main


class VisualCreationGrammarTests(unittest.TestCase):
    def test_catalog_collapses_command_vocabulary_into_axes(self):
        catalog = grammar_catalog()
        self.assertEqual(catalog["truth_status"], "EXECUTABLE_COMPOSITION_GRAMMAR")
        self.assertGreaterEqual(len(VISUAL_ALIASES), 50)
        self.assertIn("decomposition", catalog["axes"])
        self.assertIn("camera", catalog["axes"])
        self.assertTrue(catalog["truth"]["aliasesAreGrammarCompositionsNotSeparateOrgans"])

    def test_same_structured_request_replays_exactly(self):
        request = {
            "subject": "modular robot",
            "aliases": ["explodedview", "cinematicshot", "brandidentity"],
            "seed": 42,
            "scene": {"lighting": "soft rim + key"},
            "criteria": ["clear silhouette", "readable layers"],
        }
        first = compile_visual_recipe(request)
        second = compile_visual_recipe(request)
        self.assertEqual(first, second)
        self.assertIn("exploded", first["axes"]["decomposition"])
        self.assertIn("cinematic", first["axes"]["camera"])
        self.assertIn("brand-led", first["axes"]["style"])
        self.assertIn("mesh", first["generator_hints"])
        self.assertIn("palette", first["generator_hints"])
        self.assertFalse(first["truth"]["visualQualityJudged"])

    def test_temporal_storyboard_is_exact_and_duration_bound(self):
        recipe = compile_visual_recipe({
            "subject": "machine assembly reveal",
            "aliases": ["assemblyview", "motionfreeze"],
            "temporal": {"enabled": True, "duration_seconds": 10},
        })
        timeline = recipe["temporal"]["timeline"]
        self.assertEqual([row["beat"] for row in timeline], list(DEFAULT_TEMPORAL_BEATS))
        self.assertEqual(timeline[0]["start_ms"], 0)
        self.assertEqual(timeline[-1]["end_ms"], 10000)
        self.assertEqual(sum(row["duration_ms"] for row in timeline), 10000)
        self.assertIn("sprite", recipe["generator_hints"])
        self.assertEqual(recipe["quality_loop"]["stages"][3]["status"], "PENDING_RENDER_HOST")

    def test_invalid_alias_and_mode_fail_closed(self):
        with self.assertRaises(ValueError):
            compile_visual_recipe({"subject": "thing", "aliases": ["magic-unknown-mode"]})
        with self.assertRaises(ValueError):
            compile_visual_recipe({"subject": "thing", "camera": ["telepathic-camera"]})
        with self.assertRaises(ValueError):
            compile_visual_recipe({"subject": "thing", "temporal": {"enabled": True, "beats": ["unknown-beat"]}})

    def test_bridge_compiles_recipe_without_output_path(self):
        result = operate_visual_expansion(Path("."), {
            "operation": "plan",
            "request": {
                "subject": "tiny planet",
                "aliases": ["3drender", "customscene", "texturefocus"],
            },
        })
        self.assertEqual(result["schema"], "axm.visual-creation-recipe/v0.1")
        catalog = operate_visual_expansion(Path("."), {"operation": "grammar-catalog"})
        self.assertEqual(catalog["schema"], "axm.visual-creation-grammar/v0.1")

    def test_cli_plan_reads_structured_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            request = Path(tmp) / "request.json"
            request.write_text(json.dumps({
                "subject": "robotic globe",
                "aliases": ["heroshot", "retrofuturistic"],
            }), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = cli_main(["plan", str(request)])
            self.assertEqual(code, 0)
            result = json.loads(stdout.getvalue())
            self.assertEqual(result["subject"], "robotic globe")
            self.assertIn("retrofuturistic", result["axes"]["style"])


if __name__ == "__main__":
    unittest.main()

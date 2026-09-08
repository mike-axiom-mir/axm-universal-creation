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
from axm_uc.visual_base import png_bytes
from axm_uc.visual_learning import compile_adaptive_visual_recipe, inspect_png, inspect_visual_learning, record_visual_use


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
        self.assertEqual(result["schema"], "axm.visual-creation-recipe/v0.2")
        catalog = operate_visual_expansion(Path("."), {"operation": "grammar-catalog"})
        self.assertEqual(catalog["schema"], "axm.visual-creation-grammar/v0.2")

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

    def test_png_inspection_distinguishes_preview_appearance_from_actual_alpha(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rgb = root / "checker-preview.png"
            rgba = root / "actual-alpha.png"
            rgb.write_bytes(png_bytes(2, 1, [[(230, 230, 230), (255, 255, 255)]], mode="RGB"))
            rgba.write_bytes(png_bytes(2, 1, [[(10, 20, 30, 0), (10, 20, 30, 255)]], mode="RGBA"))
            rgb_result = inspect_png(rgb)
            rgba_result = inspect_png(rgba)
            self.assertFalse(rgb_result["alpha_channel"])
            self.assertFalse(rgb_result["actual_transparent_pixels"])
            self.assertEqual(rgba_result["alpha_extrema"], [0, 255])
            self.assertTrue(rgba_result["actual_transparent_pixels"])

    def test_visual_use_updates_compact_context_profile_and_replays_lesson(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "fake-transparent.png"
            artifact.write_bytes(png_bytes(2, 1, [[(230, 230, 230), (255, 255, 255)]], mode="RGB"))
            observation = {
                "context_key": "rts/atlas/transparent",
                "source": "host PNG inspection",
                "executor": "test",
                "artifact_path": str(artifact),
                "technical_requirements": {"real_alpha": True},
                "criteria": {"silhouette": "PASS", "actual-alpha": "FAIL"},
                "lessons": [{
                    "id": "verify-real-alpha",
                    "evidence": "RGB output contained a painted checkerboard and no alpha channel",
                    "patch": {
                        "criteria_add": ["actual decoded transparent pixels"],
                        "constraints_add": ["output real RGBA alpha, never a painted checkerboard"],
                        "technical_requirements": {"real_alpha": True},
                    },
                }],
            }
            first = record_visual_use(root, observation)
            second = record_visual_use(root, observation)
            self.assertEqual(first["status"], "VISUAL_USE_PROFILE_UPDATED")
            self.assertFalse(first["inspection"]["actual_transparent_pixels"])
            self.assertEqual(second["status"], "VISUAL_USE_ALREADY_RECORDED")

            profile = inspect_visual_learning(root, context_key="rts/atlas/transparent")
            context = profile["contexts"]["rts/atlas/transparent"]
            self.assertEqual(context["use_count"], 1)
            self.assertNotIn("dedup_digests", context)
            self.assertEqual(context["technical"]["real_alpha"]["fail"], 1)

            adaptive = compile_adaptive_visual_recipe(root, {
                "context_key": "rts/atlas/transparent",
                "subject": "seven RTS units",
                "criteria": ["distinct silhouettes"],
            })
            self.assertEqual(adaptive["learning_status"], "EXACT_CONTEXT_LESSONS_REPLAYED")
            self.assertEqual(adaptive["applied_lesson_ids"], ["verify-real-alpha"])
            self.assertIn("actual decoded transparent pixels", adaptive["recipe"]["quality_loop"]["stages"][4]["criteria"])
            self.assertTrue(adaptive["recipe"]["technical_requirements"]["real_alpha"])
            self.assertIn("output real rgba alpha, never a painted checkerboard", adaptive["recipe"]["constraints"])

    def test_visual_learning_stays_context_bound_and_explicit_scene_wins(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            artifact = root / "alpha.png"
            artifact.write_bytes(png_bytes(1, 1, [[(10, 20, 30, 0)]], mode="RGBA"))
            record_visual_use(root, {
                "context_key": "mir/building",
                "source": "visual review",
                "executor": "test",
                "artifact_path": str(artifact),
                "lessons": [{
                    "id": "warm-key",
                    "evidence": "cold lighting flattened brass trim",
                    "patch": {"scene": {"lighting": "warm neutral key with cyan rim"}},
                }],
            })
            learned = compile_adaptive_visual_recipe(root, {
                "context_key": "mir/building",
                "subject": "Mir forge",
                "scene": {"lighting": "explicit sunset key"},
            })
            untouched = compile_adaptive_visual_recipe(root, {
                "context_key": "axiom/building",
                "subject": "Axiom tower",
            })
            self.assertEqual(learned["recipe"]["scene_director"]["lighting"], "explicit sunset key")
            self.assertEqual(untouched["learning_status"], "NO_EXACT_CONTEXT_LESSONS")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.visual_assets_bridge import operate_visual_expansion
from axm_uc.visual_assets_cli import main as cli_main
from axm_uc.visual_state_prompt_atlas import (
    VisualStateError,
    compile_visual_state,
    extract_visual_commands,
    visual_state_catalog,
    visual_state_documents,
)


class VisualStatePromptAtlasTests(unittest.TestCase):
    def test_source_backed_catalog_contains_exact_99_unique_commands(self):
        catalog = visual_state_catalog(include_aliases=True)

        self.assertEqual(catalog["truth_status"], "SOURCE_BACKED_STATE_DIRECTION_ATLAS")
        self.assertEqual(catalog["alias_count"], 99)
        self.assertEqual([row["index"] for row in catalog["aliases"]], list(range(1, 100)))
        self.assertEqual(len({row["command"] for row in catalog["aliases"]}), 99)
        self.assertFalse(catalog["source_provenance"]["source_images_redistributed"])
        self.assertFalse(catalog["truth"]["aliasesAreMagicCommands"])
        self.assertFalse(catalog["truth"]["appearanceStateUniquelyDetermines3D"])

    def test_all_five_machine_documents_are_cross_validated(self):
        documents = visual_state_documents()

        self.assertEqual(set(documents), {"aliases", "schema", "conflicts", "blend", "compiler"})
        fields = documents["schema"]["fields"]
        path_rules = documents["blend"]["path_rules"]
        self.assertEqual(set(fields), set(path_rules))
        for row in documents["aliases"]["aliases"]:
            self.assertTrue(row["state"])
            self.assertTrue(set(row["state"]).issubset(fields))

    def test_slash_string_and_list_forms_canonicalize_to_source_order(self):
        expected = ["goldenhour", "rimlight", "3drender", "isometric", "miniature"]
        slash = extract_visual_commands("/rimlight /miniature /3drender /goldenhour /isometric /rimlight")
        listed = extract_visual_commands(["rimlight", "/miniature", "3drender", "goldenhour", "isometric"])

        self.assertEqual(slash, expected)
        self.assertEqual(listed, expected)

    def test_same_alias_set_reaches_same_state_independent_of_input_order(self):
        first = compile_visual_state({
            "subject": "miniature robotic planet",
            "commands": ["/rimlight", "/3drender", "/isometric", "/miniature", "/goldenhour"],
        })
        second = compile_visual_state({
            "subject": "miniature robotic planet",
            "commands": "/goldenhour /miniature /isometric /3drender /rimlight",
        })

        self.assertEqual(first["commands"], second["commands"])
        self.assertEqual(first["state"], second["state"])
        self.assertEqual(first["state_sha256"], second["state_sha256"])
        self.assertEqual(first["truth_status"], "COMPILED_VISUAL_STATE")
        self.assertIn("mesh", first["generator_hints"])
        self.assertIn("projection", first["generator_hints"])

    def test_ranked_quality_aliases_merge_without_last_write_wins(self):
        first = compile_visual_state({
            "subject": "quality fixture",
            "commands": ["/4k", "/8k"],
        })
        second = compile_visual_state({
            "subject": "quality fixture",
            "commands": ["/8k", "/4k"],
        })

        self.assertEqual(first["state"], second["state"])
        self.assertEqual(first["state"]["projection"]["resolution_tier"], "8k")
        self.assertEqual(first["state"]["projection"]["detail_level"], 0.9)
        self.assertFalse(first["truth"]["silentLastWriteWins"])

    def test_opposing_camera_state_holds_but_sequence_mode_is_explicit(self):
        held = compile_visual_state({
            "subject": "camera conflict fixture",
            "commands": ["/topdown", "/wormseyeview"],
        })
        sequence = compile_visual_state({
            "subject": "camera sequence fixture",
            "commands": ["/topdown", "/wormseyeview"],
            "mode": "sequence",
        })

        self.assertEqual(held["truth_status"], "HOLD_VISUAL_STATE_CONFLICT")
        self.assertEqual(held["summary"]["unresolved_holds"], 1)
        self.assertEqual(sequence["truth_status"], "COMPILED_VISUAL_STATE")
        self.assertEqual(sequence["conflicts"][0]["status"], "RESOLVED_BY_REQUEST_MODE")

    def test_style_tension_is_visible_without_becoming_fake_impossibility(self):
        result = compile_visual_state({
            "subject": "restrained digital poster",
            "commands": ["/minimalist", "/glitch"],
        })

        self.assertEqual(result["truth_status"], "COMPILED_VISUAL_STATE_WITH_WARNINGS")
        self.assertEqual(result["summary"]["unresolved_holds"], 0)
        self.assertEqual(result["conflicts"][0]["severity"], "WARNING")
        self.assertNotIn("impossible", json.dumps(result, sort_keys=True).casefold())

    def test_caller_resolution_is_recorded_but_not_promoted_to_proof(self):
        result = compile_visual_state({
            "subject": "split camera storyboard",
            "commands": ["/topdown", "/wormseyeview"],
            "resolutions": {
                "camera-opposing-elevation": "top-down establishing frame and upward reveal frame"
            },
        })

        self.assertEqual(result["truth_status"], "COMPILED_VISUAL_STATE")
        self.assertEqual(
            result["conflicts"][0]["status"],
            "CALLER_RESOLUTION_RECORDED_NOT_PROVEN",
        )
        self.assertFalse(result["truth"]["callerResolutionIsRendererProof"])

    def test_overrides_are_schema_validated_and_visible_in_contributions(self):
        result = compile_visual_state({
            "subject": "controlled composition",
            "commands": ["/minimalist", "/luxury"],
            "overrides": {"appearance.composition_density": 0.1},
        })

        self.assertEqual(result["state"]["appearance"]["composition_density"], 0.1)
        self.assertEqual(
            result["contributions"]["appearance.composition_density"][-1]["source"],
            "explicit-override",
        )
        with self.assertRaises(VisualStateError):
            compile_visual_state({
                "subject": "bad override",
                "commands": ["/minimalist"],
                "overrides": {"appearance.fake-field": 1},
            })
        with self.assertRaises(VisualStateError):
            compile_visual_state({
                "subject": "bad range",
                "commands": ["/minimalist"],
                "overrides": {"appearance.composition_density": 4},
            })

    def test_unknown_commands_fail_closed(self):
        with self.assertRaises(VisualStateError):
            compile_visual_state({
                "subject": "unknown fixture",
                "commands": ["/telepathiccamera"],
            })

    def test_cross_media_output_preserves_missing_animation_and_3d_state(self):
        result = compile_visual_state({
            "subject": "robot character",
            "commands": ["/3drender", "/motionblur", "/chrome"],
        })

        self.assertEqual(result["cross_media_projection"]["animation"]["status"], "PARTIAL_STATE_DIRECTION")
        self.assertIn(
            "geometry and topology",
            result["cross_media_projection"]["3d"]["still_missing"],
        )
        self.assertFalse(result["truth"]["compiledAppearanceUniquelyDetermines3D"])
        self.assertFalse(result["truth"]["compiledStaticStateUniquelyDeterminesAnimation"])
        self.assertFalse(result["truth"]["visualQualityJudged"])

    def test_readable_table_covers_every_command_without_source_graphics(self):
        text = (ROOT / "VISUAL_PROMPT_STATE_ATLAS.md").read_text(encoding="utf-8")
        commands = [row["command"] for row in visual_state_catalog(include_aliases=True)["aliases"]]

        for command in commands:
            self.assertIn(f"`{command}`", text)
        self.assertIn("source graphics are not redistributed", text.casefold())

    def test_cli_and_bridge_expose_read_only_catalog_and_compiler(self):
        with contextlib.redirect_stdout(io.StringIO()) as stdout:
            code = cli_main(["state-catalog"])
        self.assertEqual(code, 0)
        self.assertEqual(json.loads(stdout.getvalue())["alias_count"], 99)

        with tempfile.TemporaryDirectory() as tmp:
            request_path = Path(tmp) / "visual-state-request.json"
            request_path.write_text(json.dumps({
                "subject": "tiny machine world",
                "commands": "/3drender /isometric /miniature",
            }), encoding="utf-8")
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = cli_main(["state-compile", str(request_path)])
            self.assertEqual(code, 0)
            compiled = json.loads(stdout.getvalue())
            self.assertEqual(compiled["truth_status"], "COMPILED_VISUAL_STATE")
            self.assertIn("3d", compiled["state"]["appearance"]["render_modes"])

        bridged = operate_visual_expansion(ROOT, {
            "operation": "state-compile",
            "request": {
                "subject": "visual bridge fixture",
                "commands": ["/forest", "/mist", "/goldenhour"],
            },
        })
        self.assertEqual(bridged["schema"], "axm.visual-state-compilation/v0.1")
        self.assertFalse(bridged["truth"]["automaticExecution"])


if __name__ == "__main__":
    unittest.main()

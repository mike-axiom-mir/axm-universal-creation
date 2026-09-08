from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_browser import DesignBrowserError, capture_local_browser
from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_interaction import (
    INTERACTION_PROBE_SCHEMA,
    DesignInteractionError,
    instrument_interaction_html,
    interaction_measurements,
    normalize_interaction_recipes,
    parse_interaction_probe,
)
from axm_uc.design_observer import judge_rendered_design


FAKE_BROWSER = r'''#!/usr/bin/env python3
import json
import pathlib
import sys

if "--version" in sys.argv:
    print("Chromium Interaction Fixture 1.0")
    raise SystemExit(0)

screenshot = next((pathlib.Path(arg.split("=", 1)[1]) for arg in sys.argv if arg.startswith("--screenshot=")), None)
if screenshot is None:
    raise SystemExit(2)
screenshot.write_bytes(b"\x89PNG\r\n\x1a\nAXM-INTERACTION-FIXTURE")

runtime = {
    "schema": "axm.browser-runtime-probe/v0.1",
    "viewport": {"width": 800, "height": 600, "device_pixel_ratio": 1, "scroll_width": 800, "scroll_height": 600},
    "horizontal_overflow": False,
    "focus": {"method": "programmatic-focus-computed-outline", "focusable_count": 1, "focus_visible_count": 1, "all_focusables_visible": True},
    "motion": {"prefers_reduced_motion": False, "observed_motion_element_count": 0, "max_duration_ms": 0},
    "contrast": {"method": "opaque-computed-text-on-nearest-opaque-background", "sample_count": 1, "minimum_text_contrast": 7.0},
    "runtime_errors": [], "runtime_error_count": 0,
    "accessibility": {"method": "bounded-dom-heuristics-not-accessibility-tree", "issue_count": 0, "issues": [], "landmark_count": 1, "heading_count": 1, "control_count": 1},
}
interaction = {
    "schema": "axm.browser-interaction-probe/v0.1",
    "method": "explicit-programmatic-focus-and-bounded-synthetic-activation-on-temporary-local-copy",
    "activation_authorized": True,
    "requested_recipe_count": 1,
    "completed_recipe_count": 1,
    "interaction_error_count": 0,
    "blocked_or_probe_errors": [],
    "recipes": [{"id": "open-panel", "status": "PASS", "steps": [{"index": 0, "action": "activate", "selector": "#toggle", "status": "PASS", "synthetic_activation": True, "state_change_detected": True}]}],
    "truth_boundary": {
        "real_keyboard_tab_traversal": False,
        "trusted_user_input_events": False,
        "form_submission_allowed": False,
        "arbitrary_link_navigation_allowed": False,
        "original_source_modified": False,
    },
}
print(
    "<html><body><main>fixture</main>"
    "<script id='axm-design-runtime-probe' type='application/json'>" + json.dumps(runtime) + "</script>"
    "<script id='axm-design-interaction-probe' type='application/json'>" + json.dumps(interaction) + "</script>"
    "</body></html>"
)
'''


class DesignInteractionTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.interaction",
            "version": "0.7.0",
            "purpose": "bounded interaction fixture",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [], "radii": [], "typography": [], "custom": [],
            },
            "layout": {"breakpoints": [], "principles": ["single viewport"]},
            "components": [{
                "id": "toggle",
                "description": "Explicit button-like control.",
                "roles": ["primary-action"],
                "tags": ["control"],
                "interactive": True,
                "states": ["default", "focus", "active"],
                "source_status": "explicit-test-semantics",
            }],
            "motion": {"durations": [], "easings": [], "reduced_motion_strategy": "disable-nonessential"},
            "materials": {"signals": [], "principles": []},
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": True,
                "reduced_motion_required": False,
                "responsive_required": False,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture"},
        })
        return compose_design_plan(genome, {
            "goal": "interaction-observed local design",
            "required_roles": ["primary-action"],
            "components": [],
            "viewports": ["desktop"],
            "contrast_pairs": [{"foreground": "text", "background": "surface"}],
        })

    @staticmethod
    def write_browser(path: Path) -> None:
        path.write_text(FAKE_BROWSER, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_recipe_contract_requires_explicit_activation_authority(self):
        focus = normalize_interaction_recipes([
            {"id": "focus-primary", "steps": [{"action": "focus", "selector": "#toggle"}]}
        ])
        self.assertEqual(focus[0]["steps"][0]["action"], "focus")

        with self.assertRaises(DesignInteractionError):
            normalize_interaction_recipes([
                {"id": "activate-primary", "steps": [{"action": "activate", "selector": "#toggle"}]}
            ])

        activated = normalize_interaction_recipes(
            [{"id": "activate-primary", "steps": [{"action": "activate", "selector": "#toggle"}]}],
            True,
        )
        self.assertEqual(activated[0]["steps"][0]["action"], "activate")

    def test_instrumentation_and_probe_parser_preserve_truth_boundary(self):
        source = "<!doctype html><html><body><button id='toggle'>Toggle</button></body></html>"
        result = instrument_interaction_html(
            source,
            [{"id": "focus-primary", "steps": [{"action": "focus", "selector": "#toggle"}]}],
        )
        self.assertEqual(source, "<!doctype html><html><body><button id='toggle'>Toggle</button></body></html>")
        self.assertTrue(result["instrumented"])
        self.assertIn("data-axm-interaction-probe", result["html"])
        self.assertIn(INTERACTION_PROBE_SCHEMA, result["html"])

        probe = {
            "schema": INTERACTION_PROBE_SCHEMA,
            "requested_recipe_count": 1,
            "completed_recipe_count": 1,
            "interaction_error_count": 0,
            "recipes": [],
        }
        dom = (
            "<html><body><script id='axm-design-interaction-probe' type='application/json'>"
            + json.dumps(probe)
            + "</script></body></html>"
        )
        self.assertEqual(parse_interaction_probe(dom), probe)
        self.assertEqual(interaction_measurements(probe), {"interaction_error_count": 0})

    def test_browser_capture_feeds_explicit_interaction_gate_without_perceptual_claim(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            original = "<!doctype html><html><body><button id='toggle'>Toggle</button></body></html>"
            target.write_text(original, encoding="utf-8")
            browser = parent / "chromium-interaction-fixture"
            self.write_browser(browser)
            output = parent / "capture"

            result = capture_local_browser(
                ROOT,
                plan,
                target,
                output,
                browser,
                {"desktop": {"width": 800, "height": 600, "device_pixel_ratio": 1}},
                interaction_recipes_raw=[
                    {"id": "open-panel", "steps": [{"action": "activate", "selector": "#toggle"}]}
                ],
                allow_synthetic_activation=True,
            )

            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertTrue((output / "desktop.interaction.json").is_file())
            self.assertEqual(result["observation"]["captures"][0]["measurements"]["interaction_error_count"], 0)
            interaction_receipt = result["receipt"]["interaction_probe"]
            self.assertTrue(interaction_receipt["requested"])
            self.assertTrue(interaction_receipt["activation_authorized"])
            self.assertFalse(interaction_receipt["real_keyboard_tab_traversal_claimed"])
            self.assertFalse(interaction_receipt["trusted_user_input_claimed"])
            self.assertFalse(interaction_receipt["form_submission_allowed"])
            self.assertFalse(interaction_receipt["arbitrary_link_navigation_allowed"])
            self.assertEqual(
                result["receipt"]["browser"]["profile_policy"],
                "fresh temporary user-data directory for every normal/reduced viewport run",
            )

            judgment = judge_rendered_design(plan, result["observation"], required_assessments=[])
            by_gate = {row["gate"]: row for row in judgment["gates"]}
            self.assertEqual(by_gate["interaction-error-observation"]["status"], "PASS")
            self.assertEqual(by_gate["horizontal-overflow"]["status"], "PASS")
            self.assertEqual(by_gate["observed-focus-visibility"]["status"], "PASS")
            self.assertEqual(by_gate["observed-rendered-text-contrast"]["status"], "PASS")

    def test_unauthorized_activation_fails_before_evidence_output(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text(
                "<!doctype html><html><body><button id='toggle'>Toggle</button></body></html>",
                encoding="utf-8",
            )
            browser = parent / "chromium-interaction-fixture"
            self.write_browser(browser)
            output = parent / "must-not-exist"
            with self.assertRaises(DesignBrowserError):
                capture_local_browser(
                    ROOT,
                    plan,
                    target,
                    output,
                    browser,
                    {"desktop": {"width": 800, "height": 600}},
                    interaction_recipes_raw=[
                        {"id": "activate", "steps": [{"action": "activate", "selector": "#toggle"}]}
                    ],
                    allow_synthetic_activation=False,
                )
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import stat
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_browser import capture_local_browser
from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_observer import judge_rendered_design
from axm_uc.design_runtime_probe import (
    RUNTIME_PROBE_SCHEMA,
    instrument_local_html,
    parse_runtime_probe,
    runtime_measurements,
)

FAKE_BROWSER = r'''#!/usr/bin/env python3
import json
import pathlib
import sys
if "--version" in sys.argv:
    print("Chromium Runtime Fixture 1.0")
    raise SystemExit(0)
screenshot = next((pathlib.Path(arg.split("=", 1)[1]) for arg in sys.argv if arg.startswith("--screenshot=")), None)
if screenshot is None:
    raise SystemExit(2)
screenshot.write_bytes(b"\x89PNG\r\n\x1a\nAXM-RUNTIME-FIXTURE")
reduced = "--force-prefers-reduced-motion=reduce" in sys.argv
probe = {
    "schema": "axm.browser-runtime-probe/v0.1",
    "viewport": {"width": 800, "height": 600, "device_pixel_ratio": 1, "scroll_width": 800, "scroll_height": 600},
    "horizontal_overflow": False,
    "focus": {"method": "programmatic-focus-computed-outline", "focusable_count": 1, "focus_visible_count": 1, "all_focusables_visible": True},
    "motion": {"prefers_reduced_motion": reduced, "observed_motion_element_count": 1, "max_duration_ms": 0 if reduced else 200},
    "contrast": {"method": "opaque-computed-text-on-nearest-opaque-background", "sample_count": 1, "minimum_text_contrast": 7.0},
    "runtime_errors": [], "runtime_error_count": 0,
    "accessibility": {"method": "bounded-dom-heuristics-not-accessibility-tree", "issue_count": 1, "issues": [{"kind": "image-missing-alt"}], "landmark_count": 1, "heading_count": 1, "control_count": 1},
}
print("<html><body><main>fixture</main><script id='axm-design-runtime-probe' type='application/json'>" + json.dumps(probe) + "</script></body></html>")
'''


class DesignRuntimeProbeTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.runtime-probe",
            "version": "0.5.0",
            "purpose": "runtime probe fixture",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [], "radii": [], "typography": [], "custom": [],
            },
            "layout": {"breakpoints": [], "principles": ["single viewport fixture"]},
            "components": [{
                "id": "primary-button",
                "description": "Explicit primary control.",
                "roles": ["primary-action"],
                "tags": ["control"],
                "interactive": True,
                "states": ["default", "focus"],
                "source_status": "explicit-test-semantics",
            }],
            "motion": {"durations": [{"id": "quick", "value": "200ms", "usage": "micro"}], "easings": [], "reduced_motion_strategy": "disable-nonessential"},
            "materials": {"signals": [], "principles": []},
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": True,
                "reduced_motion_required": True,
                "responsive_required": True,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture"},
        })
        return compose_design_plan(genome, {
            "goal": "runtime-observed local design",
            "required_roles": ["primary-action"],
            "components": [],
            "viewports": ["desktop"],
            "contrast_pairs": [{"foreground": "text", "background": "surface"}],
        })

    def test_probe_parser_and_duration_reduction_are_bounded(self):
        normal = {"schema": RUNTIME_PROBE_SCHEMA, "horizontal_overflow": False, "focus": {"all_focusables_visible": True}, "motion": {"observed_motion_element_count": 1, "max_duration_ms": 200}, "contrast": {"minimum_text_contrast": 7.0}}
        reduced = {"schema": RUNTIME_PROBE_SCHEMA, "motion": {"prefers_reduced_motion": True, "observed_motion_element_count": 1, "max_duration_ms": 50}}
        measured = runtime_measurements(normal, reduced)
        self.assertEqual(measured["horizontal_overflow"], False)
        self.assertEqual(measured["focus_visible"], True)
        self.assertEqual(measured["minimum_text_contrast"], 7.0)
        self.assertEqual(measured["reduced_motion_honored"], True)

        unchanged = dict(reduced)
        unchanged["motion"] = dict(reduced["motion"], max_duration_ms=200)
        self.assertNotIn("reduced_motion_honored", runtime_measurements(normal, unchanged))

    def test_instrumented_copy_keeps_source_unchanged_and_embeds_probe(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "index.html"
            original = "<!doctype html><html><head><link rel='stylesheet' href='style.css'></head><body>AXM</body></html>"
            target.write_text(original, encoding="utf-8")
            instrumented = instrument_local_html(target)
            self.assertEqual(target.read_text(encoding="utf-8"), original)
            self.assertIn("data-axm-runtime-probe", instrumented["html"])
            self.assertIn(target.parent.as_uri(), instrumented["html"])

            probe = {"schema": RUNTIME_PROBE_SCHEMA, "horizontal_overflow": False}
            dom = "<html><body><script id='axm-design-runtime-probe' type='application/json'>" + json.dumps(probe) + "</script></body></html>"
            self.assertEqual(parse_runtime_probe(dom), probe)

    def test_browser_capture_feeds_real_runtime_measurements_without_perceptual_overclaim(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body><button>Go</button></body></html>", encoding="utf-8")
            browser = parent / "chromium-runtime-fixture"
            browser.write_text(FAKE_BROWSER, encoding="utf-8")
            browser.chmod(browser.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)
            output = parent / "capture"
            result = capture_local_browser(
                ROOT, plan, target, output, browser,
                {"desktop": {"width": 800, "height": 600, "device_pixel_ratio": 1}},
            )
            capture = result["observation"]["captures"][0]
            self.assertEqual(capture["measurements"]["horizontal_overflow"], False)
            self.assertEqual(capture["measurements"]["focus_visible"], True)
            self.assertEqual(capture["measurements"]["minimum_text_contrast"], 7.0)
            self.assertEqual(capture["measurements"]["reduced_motion_honored"], True)
            self.assertTrue((output / "desktop.runtime.json").is_file())
            runtime = json.loads((output / "desktop.runtime.json").read_text(encoding="utf-8"))
            self.assertEqual(runtime["runtime_error_count"], 0)
            self.assertEqual(runtime["accessibility"]["issue_count"], 1)
            self.assertFalse(result["receipt"]["runtime_probe"]["perceptual_assessments_generated"])
            self.assertFalse(result["receipt"]["runtime_probe"]["accessibility_tree_claimed"])

            judgment = judge_rendered_design(plan, result["observation"], required_assessments=[])
            by_gate = {row["gate"]: row for row in judgment["gates"]}
            self.assertEqual(by_gate["horizontal-overflow"]["status"], "PASS")
            self.assertEqual(by_gate["observed-focus-visibility"]["status"], "PASS")
            self.assertEqual(by_gate["observed-reduced-motion"]["status"], "PASS")
            self.assertEqual(by_gate["observed-rendered-text-contrast"]["status"], "PASS")
            self.assertEqual(by_gate["interaction-error-observation"]["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()

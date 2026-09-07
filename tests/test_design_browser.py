from __future__ import annotations

import json
import os
import stat
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_browser import BROWSER_CAPTURE_SCHEMA, DesignBrowserError, capture_local_browser
from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_observer import judge_rendered_design
from axm_uc.machine import UniversalCreationMachine


FAKE_BROWSER = r'''#!/usr/bin/env python3
import pathlib
import sys

if "--version" in sys.argv:
    print("Chromium Fixture 1.0")
    raise SystemExit(0)

screenshot = None
for arg in sys.argv:
    if arg.startswith("--screenshot="):
        screenshot = pathlib.Path(arg.split("=", 1)[1])
        break
if screenshot is None:
    print("missing screenshot path", file=sys.stderr)
    raise SystemExit(2)
screenshot.write_bytes(b"\x89PNG\r\n\x1a\nAXM-FIXTURE")
print("<!doctype html><html><body><main id='captured'>fixture</main></body></html>")
'''


class DesignBrowserTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.browser-design",
            "version": "0.3.0",
            "purpose": "exercise the optional local browser observer bridge",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [],
                "radii": [],
                "typography": [],
                "custom": [],
            },
            "layout": {
                "breakpoints": [{"id": "wide", "query": "768px", "width_px": 768}],
                "principles": ["adapt layout to explicit viewport evidence"],
            },
            "components": [{
                "id": "primary-button",
                "description": "Explicit primary action control.",
                "roles": ["primary-action"],
                "tags": ["control"],
                "interactive": True,
                "states": ["default", "hover", "focus", "active", "disabled"],
                "source_status": "explicit-test-semantics",
            }],
            "motion": {
                "durations": [{"id": "quick", "value": "160ms", "usage": "micro-interaction"}],
                "easings": [],
                "reduced_motion_strategy": "disable-nonessential",
            },
            "materials": {
                "signals": [],
                "principles": ["keep surface evidence distinct from browser proof"],
            },
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": True,
                "reduced_motion_required": True,
                "responsive_required": True,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture", "browser_capture_performed": False},
        })
        return compose_design_plan(
            genome,
            {
                "goal": "responsive browser-observed design",
                "required_roles": ["primary-action"],
                "components": [],
                "viewports": ["mobile", "desktop"],
                "contrast_pairs": [{"foreground": "text", "background": "surface"}],
            },
        )

    @staticmethod
    def write_browser(path: Path) -> None:
        path.write_text(FAKE_BROWSER, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    @staticmethod
    def viewport_sizes() -> dict:
        return {
            "mobile": {"width": 390, "height": 844, "device_pixel_ratio": 1},
            "desktop": {"width": 1440, "height": 900, "device_pixel_ratio": 1},
        }

    def test_capture_materializes_real_artifact_bytes_and_exact_receipts(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "site"
            target.mkdir()
            (target / "index.html").write_text("<!doctype html><html><body>AXM</body></html>", encoding="utf-8")
            browser = parent / "chromium-fixture"
            self.write_browser(browser)
            output = parent / "capture"

            result = capture_local_browser(
                ROOT,
                plan,
                target,
                output,
                browser,
                self.viewport_sizes(),
                timeout_seconds=10,
            )

            self.assertEqual(result["truth_status"], "LOCAL_HEADLESS_BROWSER_CAPTURE_MATERIALIZED")
            self.assertEqual(result["receipt"]["schema"], BROWSER_CAPTURE_SCHEMA)
            self.assertEqual(result["receipt"]["browser"]["version"], "Chromium Fixture 1.0")
            self.assertEqual(result["receipt"]["plan_digest"], plan["plan_digest"])
            self.assertEqual(
                set(result["files"]),
                {
                    "browser.capture.json",
                    "desktop.dom.html",
                    "desktop.png",
                    "mobile.dom.html",
                    "mobile.png",
                },
            )
            for name in ("mobile.png", "desktop.png", "mobile.dom.html", "desktop.dom.html"):
                self.assertTrue((output / name).is_file())
                self.assertGreater((output / name).stat().st_size, 0)

            observation = result["observation"]
            self.assertTrue(observation["evidence_boundary"]["artifact_bytes_fetched_or_verified"])
            self.assertTrue(observation["evidence_boundary"]["browser_or_screen_control_claimed"])
            self.assertTrue(
                all(
                    artifact["bytes_verified_or_fetched_by_design_fabric"]
                    for capture in observation["captures"]
                    for artifact in capture["artifacts"]
                )
            )
            receipt_on_disk = json.loads((output / "browser.capture.json").read_text(encoding="utf-8"))
            self.assertEqual(receipt_on_disk["capture_receipt_digest"], result["receipt"]["capture_receipt_digest"])

    def test_browser_artifacts_do_not_fake_visual_pass_without_measurements_or_assessments(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body>AXM</body></html>", encoding="utf-8")
            browser = parent / "chromium-fixture"
            self.write_browser(browser)
            result = capture_local_browser(
                ROOT,
                plan,
                target,
                parent / "capture",
                browser,
                self.viewport_sizes(),
            )
            judgment = judge_rendered_design(plan, result["observation"])

        self.assertEqual(judgment["status"], "HOLD")
        by_gate = {row["gate"]: row for row in judgment["gates"]}
        self.assertEqual(by_gate["viewport-render-coverage"]["status"], "PASS")
        self.assertEqual(by_gate["screenshot-evidence-coverage"]["status"], "PASS")
        self.assertEqual(by_gate["horizontal-overflow"]["status"], "HOLD")
        self.assertEqual(by_gate["external-perceptual-assessments"]["status"], "HOLD")

    def test_url_machine_body_existing_output_and_missing_browser_fail_closed(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body>AXM</body></html>", encoding="utf-8")
            browser = parent / "chromium-fixture"
            self.write_browser(browser)

            with self.assertRaises(DesignBrowserError):
                capture_local_browser(
                    ROOT,
                    plan,
                    "https://example.com",
                    parent / "url-capture",
                    browser,
                    self.viewport_sizes(),
                )

            existing = parent / "existing"
            existing.mkdir()
            with self.assertRaises(DesignBrowserError):
                capture_local_browser(
                    ROOT,
                    plan,
                    target,
                    existing,
                    browser,
                    self.viewport_sizes(),
                )

            with self.assertRaises(DesignBrowserError) as missing:
                capture_local_browser(
                    ROOT,
                    plan,
                    target,
                    parent / "missing-browser",
                    "axm-browser-that-does-not-exist",
                    self.viewport_sizes(),
                )
            self.assertEqual(missing.exception.details["status"], "HOLD_BROWSER_EXECUTOR_UNAVAILABLE")

        blocked = ROOT / "src" / "should-not-write-browser-evidence"
        try:
            with self.assertRaises(DesignBrowserError):
                capture_local_browser(
                    ROOT,
                    plan,
                    ROOT / "README.md",
                    blocked,
                    sys.executable,
                    self.viewport_sizes(),
                )
        finally:
            self.assertFalse(blocked.exists())

    def test_live_machine_routes_capture_through_design_fabric(self):
        machine = UniversalCreationMachine(ROOT)
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body>AXM</body></html>", encoding="utf-8")
            browser = parent / "chromium-fixture"
            self.write_browser(browser)
            result = machine.create({
                "kind": "capture-design-browser-observation",
                "inputs": {
                    "operation": "capture-browser",
                    "plan": plan,
                    "target": str(target),
                    "path": str(parent / "capture"),
                    "browser_executable": str(browser),
                    "viewport_sizes": self.viewport_sizes(),
                    "timeout_seconds": 10,
                },
            })

        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertEqual(result["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(result["result"]["truth_status"], "LOCAL_HEADLESS_BROWSER_CAPTURE_MATERIALIZED")


if __name__ == "__main__":
    unittest.main()

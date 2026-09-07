from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_observer import (
    INTEGRATED_JUDGMENT_SCHEMA,
    RENDER_OBSERVATION_SCHEMA,
    REPAIR_PLAN_SCHEMA,
    DesignObserverError,
    judge_rendered_design,
    propose_design_repair,
    record_render_observation,
)
from axm_uc.machine import UniversalCreationMachine


class DesignObserverTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.rendered-design",
            "version": "0.2.0",
            "purpose": "exercise the rendered design evidence loop",
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
                "principles": ["adapt layout by observed viewport"],
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
                "principles": ["keep surface evidence separate from renderer claims"],
            },
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": True,
                "reduced_motion_required": True,
                "responsive_required": True,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture", "visual_capture_performed": False},
        })
        return compose_design_plan(
            genome,
            {
                "goal": "responsive rendered design under observation",
                "required_roles": ["primary-action"],
                "components": [],
                "viewports": ["mobile", "desktop"],
                "contrast_pairs": [{"foreground": "text", "background": "surface"}],
            },
        )

    @staticmethod
    def capture(viewport: str, width: int, *, digest_char: str, overflow: bool = False, hierarchy: str = "PASS") -> dict:
        assessments = []
        for assessment_id in ("visual-hierarchy", "spacing-consistency", "component-coherence"):
            status = hierarchy if assessment_id == "visual-hierarchy" else "PASS"
            assessments.append({
                "id": assessment_id,
                "status": status,
                "confidence": 0.9,
                "basis": f"explicit external fixture assessment for {assessment_id} at {viewport}",
            })
        return {
            "viewport": {"id": viewport, "width": width, "height": 900, "device_pixel_ratio": 1},
            "artifacts": [{
                "kind": "screenshot",
                "digest": digest_char * 64,
                "uri": f"fixture://{viewport}.png",
                "mime_type": "image/png",
                "bytes": 1234,
            }],
            "measurements": {
                "horizontal_overflow": overflow,
                "focus_visible": True,
                "reduced_motion_honored": True,
                "minimum_text_contrast": 21,
                "interaction_error_count": 0,
            },
            "assessments": assessments,
        }

    def complete_observation(self, plan: dict) -> dict:
        return record_render_observation(
            plan["plan_digest"],
            {
                "kind": "test-fixture",
                "id": "axm.test.render-observer",
                "version": "1",
                "basis": "deterministic test evidence only",
            },
            [
                self.capture("mobile", 390, digest_char="a"),
                self.capture("desktop", 1440, digest_char="b"),
            ],
        )

    def test_render_observation_receipt_is_deterministic_and_does_not_fake_capture(self):
        plan = self.plan()
        first = self.complete_observation(plan)
        second = self.complete_observation(plan)
        self.assertEqual(first["schema"], RENDER_OBSERVATION_SCHEMA)
        self.assertEqual(first["observation_digest"], second["observation_digest"])
        self.assertEqual(first["plan_digest"], plan["plan_digest"])
        self.assertFalse(first["evidence_boundary"]["artifact_bytes_fetched_or_verified"])
        self.assertFalse(first["evidence_boundary"]["browser_or_screen_control_claimed"])
        self.assertFalse(first["captures"][0]["artifacts"][0]["bytes_verified_or_fetched_by_design_fabric"])

    def test_complete_two_viewport_external_evidence_can_pass_integrated_gates(self):
        plan = self.plan()
        observation = self.complete_observation(plan)
        judgment = judge_rendered_design(plan, observation)
        self.assertEqual(judgment["schema"], INTEGRATED_JUDGMENT_SCHEMA)
        self.assertEqual(judgment["status"], "PASS")
        self.assertTrue(judgment["passed"])
        self.assertTrue(all(row["status"] == "PASS" for row in judgment["gates"]))
        self.assertEqual(judgment["observer"]["id"], "axm.test.render-observer")
        self.assertIn("external observer assessments remain attributed observations rather than objective aesthetic truth", judgment["truth_boundary"])

    def test_missing_render_coverage_holds_instead_of_becoming_visual_quality_claim(self):
        plan = self.plan()
        observation = record_render_observation(
            plan["plan_digest"],
            {"kind": "browser-tool", "id": "fixture.browser"},
            [self.capture("mobile", 390, digest_char="c")],
        )
        judgment = judge_rendered_design(plan, observation)
        self.assertEqual(judgment["status"], "HOLD")
        by_gate = {row["gate"]: row for row in judgment["gates"]}
        self.assertEqual(by_gate["viewport-render-coverage"]["status"], "HOLD")
        self.assertEqual(by_gate["screenshot-evidence-coverage"]["status"], "HOLD")
        self.assertIn("desktop", by_gate["viewport-render-coverage"]["evidence"]["missing"])

    def test_observed_failures_create_repair_direction_without_rewriting_source(self):
        plan = self.plan()
        observation = record_render_observation(
            plan["plan_digest"],
            {"kind": "model", "id": "fixture.visual-reviewer", "version": "test"},
            [
                self.capture("mobile", 390, digest_char="d", overflow=True, hierarchy="FAIL"),
                self.capture("desktop", 1440, digest_char="e"),
            ],
        )
        judgment = judge_rendered_design(plan, observation)
        self.assertEqual(judgment["status"], "FAIL")
        by_gate = {row["gate"]: row for row in judgment["gates"]}
        self.assertEqual(by_gate["horizontal-overflow"]["status"], "FAIL")
        self.assertEqual(by_gate["external-perceptual-assessments"]["status"], "FAIL")

        repair = propose_design_repair(judgment)
        self.assertEqual(repair["schema"], REPAIR_PLAN_SCHEMA)
        self.assertEqual(repair["status"], "REPAIR_PLAN_READY_FROM_OBSERVED_GAPS")
        targets = {row["target"] for row in repair["actions"]}
        self.assertIn("responsive-layout", targets)
        self.assertIn("visual-composition", targets)
        self.assertFalse(repair["automatic_source_rewrite"])
        self.assertFalse(repair["automatic_acceptance"])

    def test_plan_digest_and_artifact_digest_fail_closed(self):
        plan = self.plan()
        observation = self.complete_observation(plan)
        mismatched = copy.deepcopy(observation)
        mismatched["plan_digest"] = "sha256:" + "f" * 64
        with self.assertRaises(DesignObserverError):
            judge_rendered_design(plan, mismatched)

        bad_capture = self.capture("mobile", 390, digest_char="a")
        bad_capture["artifacts"][0]["digest"] = "not-a-digest"
        with self.assertRaises(DesignObserverError):
            record_render_observation(
                plan["plan_digest"],
                {"kind": "human", "id": "fixture.human"},
                [bad_capture],
            )

    def test_live_machine_routes_observer_operations_through_same_design_capability(self):
        machine = UniversalCreationMachine(ROOT)
        inspection = machine.create({
            "kind": "inspect-design-observer",
            "inputs": {"operation": "inspect-observer"},
        })
        self.assertEqual(inspection["type"], "CREATION_RESULT")
        self.assertEqual(inspection["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertFalse(inspection["result"]["browser_capture_performed_by_this_module"])

        plan = self.plan()
        recorded = machine.create({
            "kind": "record-design-render-observation",
            "inputs": {
                "operation": "record-render-observation",
                "plan_digest": plan["plan_digest"],
                "observer": {"kind": "test-fixture", "id": "machine.fixture"},
                "captures": [
                    self.capture("mobile", 390, digest_char="1"),
                    self.capture("desktop", 1440, digest_char="2"),
                ],
            },
        })
        self.assertEqual(recorded["type"], "CREATION_RESULT", recorded)
        judged = machine.create({
            "kind": "judge-rendered-design",
            "inputs": {
                "operation": "judge-rendered",
                "plan": plan,
                "observation": recorded["result"],
            },
        })
        self.assertEqual(judged["type"], "CREATION_RESULT", judged)
        self.assertEqual(judged["result"]["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

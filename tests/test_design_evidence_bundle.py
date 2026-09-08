from __future__ import annotations

import copy
import hashlib
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_evidence_bundle import (
    VIEWPORT_EVIDENCE_BUNDLE_SCHEMA,
    DesignEvidenceBundleError,
    consolidate_viewport_evidence,
    project_consensus_render_observation,
)
from axm_uc.design_observer import record_render_observation
from axm_uc.machine import UniversalCreationMachine


PLAN_DIGEST = "sha256:" + "a" * 64
VIEWPORT = {"id": "desktop", "width": 800, "height": 600, "device_pixel_ratio": 1}


def digest_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def observation(
    *,
    observer_kind: str,
    observer_id: str,
    artifacts: list[dict] | None = None,
    measurements: dict | None = None,
    assessments: list[dict] | None = None,
) -> dict:
    return record_render_observation(
        PLAN_DIGEST,
        {"kind": observer_kind, "id": observer_id, "version": "1"},
        [{
            "viewport": VIEWPORT,
            "artifacts": artifacts or [],
            "measurements": measurements or {},
            "assessments": assessments or [],
        }],
    )


class DesignEvidenceBundleTests(unittest.TestCase):
    def test_same_viewport_sources_are_joined_without_losing_provenance(self):
        screenshot_digest = digest_bytes(b"same-render")
        browser = observation(
            observer_kind="browser-tool",
            observer_id="chromium-headless-cli",
            artifacts=[
                {
                    "kind": "screenshot",
                    "digest": screenshot_digest,
                    "mime_type": "image/png",
                    "bytes": 11,
                },
                {
                    "kind": "dom-snapshot",
                    "digest": digest_bytes(b"dom"),
                    "mime_type": "text/html",
                    "bytes": 3,
                },
            ],
            measurements={
                "horizontal_overflow": False,
                "focus_visible": True,
                "minimum_text_contrast": 7.0,
            },
        )
        cdp = observation(
            observer_kind="browser-tool",
            observer_id="chromium-cdp-semantics",
            artifacts=[
                {
                    "kind": "accessibility-tree",
                    "digest": digest_bytes(b"ax-tree"),
                    "mime_type": "application/json",
                    "bytes": 7,
                },
                {
                    "kind": "interaction-log",
                    "digest": digest_bytes(b"tabs"),
                    "mime_type": "application/json",
                    "bytes": 4,
                },
            ],
            measurements={
                "focus_visible": True,
                "interaction_error_count": 0,
            },
            assessments=[
                {
                    "id": "accessibility-tree-integrity",
                    "status": "PASS",
                    "confidence": 1.0,
                    "basis": "browser accessibility tree captured",
                },
                {
                    "id": "cdp-tab-traversal-integrity",
                    "status": "PASS",
                    "confidence": 1.0,
                    "basis": "bounded browser Tab traversal captured",
                },
            ],
        )
        model = observation(
            observer_kind="model",
            observer_id="visual-observer-fixture",
            artifacts=[
                {
                    "kind": "screenshot",
                    "digest": screenshot_digest,
                    "mime_type": "image/png",
                    "bytes": 11,
                }
            ],
            assessments=[
                {
                    "id": "visual-hierarchy",
                    "status": "PASS",
                    "confidence": 0.82,
                    "basis": "attributed fixture assessment for hierarchy",
                },
                {
                    "id": "spacing-consistency",
                    "status": "PASS",
                    "confidence": 0.78,
                    "basis": "attributed fixture assessment for spacing",
                },
                {
                    "id": "component-coherence",
                    "status": "PASS",
                    "confidence": 0.80,
                    "basis": "attributed fixture assessment for component coherence",
                },
            ],
        )

        bundle = consolidate_viewport_evidence(
            PLAN_DIGEST,
            VIEWPORT,
            [browser, cdp, model],
        )

        self.assertEqual(bundle["schema"], VIEWPORT_EVIDENCE_BUNDLE_SCHEMA)
        self.assertEqual(bundle["coverage"]["source_observation_count"], 3)
        self.assertEqual(bundle["resolution"]["measurements"]["focus_visible"]["status"], "CONSISTENT")
        self.assertEqual(bundle["resolution"]["measurements"]["focus_visible"]["source_count"], 2)
        self.assertEqual(bundle["resolution"]["measurements"]["focus_visible"]["consensus_value"], True)
        self.assertEqual(bundle["resolution"]["conflicts"], {"measurements": [], "assessments": []})
        self.assertEqual(bundle["coverage"]["artifact_kind_counts"]["accessibility-tree"], 1)
        self.assertEqual(bundle["coverage"]["artifact_kind_counts"]["interaction-log"], 1)
        self.assertEqual(
            bundle["coverage"]["default_perceptual_assessments"]["visual-hierarchy"]["consensus_status"],
            "PASS",
        )
        self.assertTrue(bundle["claim_boundary"]["source_observations_preserved"])
        self.assertFalse(bundle["claim_boundary"]["aesthetic_truth_inferred"])

        projected = project_consensus_render_observation(bundle)
        render_observation = projected["observation"]
        capture = render_observation["captures"][0]
        self.assertEqual(capture["measurements"]["focus_visible"], True)
        self.assertEqual(capture["measurements"]["horizontal_overflow"], False)
        self.assertEqual(capture["measurements"]["interaction_error_count"], 0)
        self.assertEqual(len([row for row in capture["artifacts"] if row["kind"] == "screenshot"]), 1)
        by_assessment = {row["id"]: row for row in capture["assessments"]}
        self.assertEqual(by_assessment["visual-hierarchy"]["status"], "PASS")
        self.assertIn("visual-observer-fixture", by_assessment["visual-hierarchy"]["basis"])
        self.assertEqual(render_observation["source_bundle_digest"], bundle["bundle_digest"])
        self.assertFalse(projected["claim_boundary"]["automatic_aesthetic_pass"])

    def test_conflicting_claims_are_retained_and_omitted_from_projection(self):
        first = observation(
            observer_kind="browser-tool",
            observer_id="runtime-a",
            measurements={"focus_visible": True, "horizontal_overflow": False},
            assessments=[{
                "id": "visual-hierarchy",
                "status": "PASS",
                "confidence": 0.7,
                "basis": "observer A",
            }],
        )
        second = observation(
            observer_kind="browser-tool",
            observer_id="runtime-b",
            measurements={"focus_visible": False, "horizontal_overflow": False},
            assessments=[{
                "id": "visual-hierarchy",
                "status": "HOLD",
                "confidence": 0.9,
                "basis": "observer B",
            }],
        )

        bundle = consolidate_viewport_evidence(PLAN_DIGEST, VIEWPORT, [first, second])
        self.assertEqual(bundle["resolution"]["measurements"]["focus_visible"]["status"], "CONFLICT")
        self.assertEqual(bundle["resolution"]["assessments"]["visual-hierarchy"]["status"], "CONFLICT")
        self.assertEqual(bundle["resolution"]["conflicts"]["measurements"], ["focus_visible"])
        self.assertEqual(bundle["resolution"]["conflicts"]["assessments"], ["visual-hierarchy"])

        projected = project_consensus_render_observation(bundle)
        capture = projected["observation"]["captures"][0]
        self.assertNotIn("focus_visible", capture["measurements"])
        self.assertEqual(capture["measurements"]["horizontal_overflow"], False)
        self.assertNotIn("visual-hierarchy", {row["id"] for row in capture["assessments"]})
        self.assertEqual(projected["omitted_conflicts"]["measurements"], ["focus_visible"])

    def test_digest_drift_wrong_plan_duplicate_and_viewport_mismatch_fail_closed(self):
        base = observation(
            observer_kind="test-fixture",
            observer_id="source",
            measurements={"horizontal_overflow": False},
        )

        drifted = copy.deepcopy(base)
        drifted["captures"][0]["measurements"]["horizontal_overflow"] = True
        with self.assertRaises(DesignEvidenceBundleError):
            consolidate_viewport_evidence(PLAN_DIGEST, VIEWPORT, [drifted])

        with self.assertRaises(DesignEvidenceBundleError):
            consolidate_viewport_evidence("sha256:" + "b" * 64, VIEWPORT, [base])

        with self.assertRaises(DesignEvidenceBundleError):
            consolidate_viewport_evidence(PLAN_DIGEST, VIEWPORT, [base, base])

        wrong_viewport = dict(VIEWPORT, width=801)
        with self.assertRaises(DesignEvidenceBundleError):
            consolidate_viewport_evidence(PLAN_DIGEST, wrong_viewport, [base])

    def test_projection_is_itself_digest_bound_and_can_reenter_bundle_flow(self):
        source = observation(
            observer_kind="test-fixture",
            observer_id="source",
            artifacts=[{
                "kind": "screenshot",
                "digest": digest_bytes(b"image"),
                "mime_type": "image/png",
                "bytes": 5,
            }],
            measurements={"horizontal_overflow": False},
        )
        bundle = consolidate_viewport_evidence(PLAN_DIGEST, VIEWPORT, [source])
        projection = project_consensus_render_observation(bundle)["observation"]
        replay = consolidate_viewport_evidence(PLAN_DIGEST, VIEWPORT, [projection])
        self.assertEqual(replay["coverage"]["source_observation_count"], 1)
        self.assertEqual(replay["resolution"]["measurements"]["horizontal_overflow"]["consensus_value"], False)
        self.assertTrue(projection["observation_digest"].startswith("sha256:"))

    def test_live_machine_routes_bundle_and_consensus_projection_through_design_fabric(self):
        source = observation(
            observer_kind="test-fixture",
            observer_id="live-source",
            artifacts=[{
                "kind": "screenshot",
                "digest": digest_bytes(b"live-image"),
                "mime_type": "image/png",
                "bytes": 10,
            }],
            measurements={"horizontal_overflow": False},
        )
        machine = UniversalCreationMachine(ROOT)
        bundled = machine.create({
            "kind": "consolidate-design-viewport-evidence",
            "inputs": {
                "operation": "consolidate-viewport-evidence",
                "plan_digest": PLAN_DIGEST,
                "viewport": VIEWPORT,
                "observations": [source],
            },
        })
        self.assertEqual(bundled["type"], "CREATION_RESULT", bundled)
        self.assertEqual(bundled["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(bundled["result"]["schema"], VIEWPORT_EVIDENCE_BUNDLE_SCHEMA)

        projected = machine.create({
            "kind": "project-design-consensus-render-observation",
            "inputs": {
                "operation": "project-consensus-render-observation",
                "bundle": bundled["result"],
            },
        })
        self.assertEqual(projected["type"], "CREATION_RESULT", projected)
        self.assertEqual(projected["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(
            projected["result"]["observation"]["captures"][0]["measurements"]["horizontal_overflow"],
            False,
        )
        self.assertFalse(projected["result"]["claim_boundary"]["automatic_acceptance"])


if __name__ == "__main__":
    unittest.main()

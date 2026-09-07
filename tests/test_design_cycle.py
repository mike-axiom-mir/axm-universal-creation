from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_compare import RENDER_COMPARISON_SCHEMA
from axm_uc.design_cycle import REPAIR_CYCLE_SCHEMA, DesignCycleError, record_repair_cycle
from axm_uc.design_observer import (
    INTEGRATED_JUDGMENT_SCHEMA,
    RENDER_OBSERVATION_SCHEMA,
    REPAIR_PLAN_SCHEMA,
)
from axm_uc.machine import UniversalCreationMachine


def digest(char: str) -> str:
    return "sha256:" + char * 64


def fixture_bundle() -> dict:
    before_plan = digest("1")
    after_plan = digest("2")
    before_observation_digest = digest("3")
    after_observation_digest = digest("4")
    before_judgment_digest = digest("5")
    after_judgment_digest = digest("6")

    before_observation = {
        "schema": RENDER_OBSERVATION_SCHEMA,
        "plan_digest": before_plan,
        "observation_digest": before_observation_digest,
        "captures": [],
    }
    after_observation = {
        "schema": RENDER_OBSERVATION_SCHEMA,
        "plan_digest": after_plan,
        "observation_digest": after_observation_digest,
        "captures": [],
    }
    before_judgment = {
        "schema": INTEGRATED_JUDGMENT_SCHEMA,
        "status": "FAIL",
        "passed": False,
        "plan_digest": before_plan,
        "observation_digest": before_observation_digest,
        "judgment_digest": before_judgment_digest,
        "gates": [
            {"gate": "horizontal-overflow", "status": "FAIL", "evidence": {"observations": [True]}},
            {"gate": "observed-focus-visibility", "status": "PASS", "evidence": {}},
        ],
    }
    after_judgment = {
        "schema": INTEGRATED_JUDGMENT_SCHEMA,
        "status": "PASS",
        "passed": True,
        "plan_digest": after_plan,
        "observation_digest": after_observation_digest,
        "judgment_digest": after_judgment_digest,
        "gates": [
            {"gate": "horizontal-overflow", "status": "PASS", "evidence": {"observations": [False]}},
            {"gate": "observed-focus-visibility", "status": "PASS", "evidence": {}},
        ],
    }
    repair_plan = {
        "schema": REPAIR_PLAN_SCHEMA,
        "truth_status": "DETERMINISTIC_REPAIR_DIRECTION_FROM_EXPLICIT_GATE_EVIDENCE",
        "status": "REPAIR_PLAN_READY_FROM_OBSERVED_GAPS",
        "source_judgment_digest": before_judgment_digest,
        "repair_plan_digest": digest("7"),
        "actions": [{"gate": "horizontal-overflow", "status": "FAIL", "target": "responsive-layout"}],
        "automatic_source_rewrite": False,
        "automatic_acceptance": False,
    }
    repair_result = {
        "path": "/tmp/project",
        "project_type": "static-web",
        "published": True,
        "truth_status": "OBSERVED_TRANSACTIONAL_PROJECT_REPAIR",
        "intent": {"operations": [{"op": "update", "path": "index.html", "content": "after"}]},
        "observed": {
            "applied_operations": [{"op": "update", "path": "index.html"}],
            "before_files": [{"path": "index.html", "sha256": digest("8")}],
            "after_files": [{"path": "index.html", "sha256": digest("9")}],
        },
        "expected_files": {"index.html": "after"},
        "validation": {"passed": True, "checks": []},
        "grammar_inventory": {"truth_status": "OBSERVED_EXTENSION_GRAMMAR_INVENTORY", "files": []},
    }
    comparison = {
        "schema": RENDER_COMPARISON_SCHEMA,
        "truth_status": "DETERMINISTIC_BOUND_SCREENSHOT_CHANGE_MEASUREMENT",
        "status": "PASS",
        "viewport": "desktop",
        "before": {
            "plan_digest": before_plan,
            "observation_digest": before_observation_digest,
            "artifact_digest": digest("a"),
            "dimensions": [800, 600],
        },
        "after": {
            "plan_digest": after_plan,
            "observation_digest": after_observation_digest,
            "artifact_digest": digest("b"),
            "dimensions": [800, 600],
        },
        "change": {"changed_fraction": 0.125},
        "comparison_digest": digest("c"),
    }
    return {
        "before_judgment": before_judgment,
        "repair_plan": repair_plan,
        "repair_result": repair_result,
        "before_observation": before_observation,
        "after_observation": after_observation,
        "comparison": comparison,
        "after_judgment": after_judgment,
    }


class DesignCycleTests(unittest.TestCase):
    def test_cycle_binds_exact_evidence_without_turning_gate_progress_into_quality_claim(self):
        bundle = fixture_bundle()
        result = record_repair_cycle(**{f"{key}_raw": value for key, value in bundle.items()})

        self.assertEqual(result["schema"], REPAIR_CYCLE_SCHEMA)
        self.assertEqual(result["status"], "DECLARED_GATES_PASS_AFTER_REPAIR_NOT_AUTO_ACCEPTED")
        self.assertEqual(result["status_transition"], {"before": "FAIL", "after": "PASS", "movement": "TOWARD_PASS"})
        overflow = next(row for row in result["gate_transitions"] if row["gate"] == "horizontal-overflow")
        self.assertEqual(overflow["movement"], "TOWARD_PASS")
        self.assertEqual(result["comparison"]["changed_fraction"], 0.125)
        self.assertTrue(result["claim_boundary"]["repair_execution_observed"])
        self.assertFalse(result["claim_boundary"]["visual_quality_improvement_proven"])
        self.assertFalse(result["claim_boundary"]["semantic_correctness_proven"])
        self.assertFalse(result["claim_boundary"]["human_acceptance_granted"])
        self.assertFalse(result["automatic_acceptance"])
        self.assertTrue(result["cycle_digest"].startswith("sha256:"))

    def test_continuity_mismatch_and_unpublished_repair_fail_closed(self):
        bundle = fixture_bundle()
        mismatch = copy.deepcopy(bundle)
        mismatch["repair_plan"]["source_judgment_digest"] = digest("d")
        with self.assertRaises(DesignCycleError):
            record_repair_cycle(**{f"{key}_raw": value for key, value in mismatch.items()})

        unpublished = copy.deepcopy(bundle)
        unpublished["repair_result"]["published"] = False
        with self.assertRaises(DesignCycleError):
            record_repair_cycle(**{f"{key}_raw": value for key, value in unpublished.items()})

        wrong_after = copy.deepcopy(bundle)
        wrong_after["comparison"]["after"]["observation_digest"] = digest("e")
        with self.assertRaises(DesignCycleError):
            record_repair_cycle(**{f"{key}_raw": value for key, value in wrong_after.items()})

    def test_live_machine_routes_cycle_receipt_through_design_fabric(self):
        bundle = fixture_bundle()
        result = UniversalCreationMachine(ROOT).create({
            "kind": "record-design-repair-cycle",
            "inputs": {"operation": "record-repair-cycle", **bundle},
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertEqual(result["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(result["result"]["schema"], REPAIR_CYCLE_SCHEMA)
        self.assertFalse(result["result"]["automatic_acceptance"])


if __name__ == "__main__":
    unittest.main()

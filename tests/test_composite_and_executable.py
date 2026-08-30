from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class CompositeAndExecutableTests(unittest.TestCase):
    def test_executable_anatomy_counts_only_explicit_implementation_bindings(self):
        machine = UniversalCreationMachine(ROOT)
        summary = machine.executable()["summary"]
        self.assertEqual(summary["truth_status"], "EXPLICIT_LIVE_CAPABILITY_BINDINGS")
        self.assertEqual(summary["implemented_master_records"], 2)
        self.assertEqual(summary["implemented_master_by_level"], {"component": 2})

        project = machine.executable(master_id="AXM-24-WORKSPACE-COLLABORATION-C-010-project")["master"]
        self.assertEqual(project["status"], "live-backed")
        self.assertIn("AXM-CAP-WRITE-PROJECT", project["implemented_by"])

        report = machine.executable(master_id="AXM-20-TESTING-OBSERVABILITY-C-015-validation-report")["master"]
        self.assertEqual(report["status"], "live-backed")
        self.assertIn("AXM-CAP-VERIFY-PROJECT", report["implemented_by"])

    def test_planner_surfaces_explicit_live_anatomy_bindings(self):
        plan = UniversalCreationMachine(ROOT).plan({
            "kind": "software-project",
            "direction": "create a project with deterministic validation",
            "inputs": {"path": "creations/planned", "files": {"README.md": "# planned\n"}},
        }, per_level=20)
        coverage = plan["executable_anatomy"]["selected_records_with_declared_binding"]
        self.assertTrue(any(row["master_id"] == "AXM-24-WORKSPACE-COLLABORATION-C-010-project" for row in coverage))

    def test_first_composite_candidate_runs_existing_live_capabilities(self):
        machine = UniversalCreationMachine(ROOT)
        candidate = ROOT / "capabilities/candidates/AXM-CAP-BUILD-VERIFY-PROJECT.json"
        result = machine.test_candidate(candidate)
        self.assertTrue(result["passed"], result)
        self.assertTrue(result["build_debris_cleaned"])
        self.assertTrue(result["tests"][0]["result"]["build"]["published"])
        self.assertTrue(result["tests"][0]["result"]["verification"]["passed"])

    def test_composite_cycle_is_rejected(self):
        machine = UniversalCreationMachine(ROOT)
        manifest = {
            "id": "AXM-CAP-SELF-CYCLE",
            "input_contract": {"required": []},
            "implementation": {
                "kind": "DETERMINISTIC_COMPOSITE",
                "steps": [{"id": "again", "capability": "AXM-CAP-SELF-CYCLE", "inputs": {}}],
            },
        }
        # A non-live self reference fails before any hidden recursion can occur.
        with self.assertRaisesRegex(Exception, "not live"):
            machine.capabilities.invoke(manifest, {})


if __name__ == "__main__":
    unittest.main()

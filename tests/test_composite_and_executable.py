from __future__ import annotations

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
        self.assertEqual(summary["implemented_master_records"], 7)
        self.assertEqual(summary["implemented_master_by_level"], {"component": 7})
        self.assertEqual(summary["live_capabilities"], 11)
        self.assertEqual(summary["resolved_bindings"], 18)

        project = machine.executable(master_id="AXM-24-WORKSPACE-COLLABORATION-C-010-project")["master"]
        self.assertEqual(project["status"], "live-backed")
        self.assertIn("AXM-CAP-WRITE-PROJECT", project["implemented_by"])

        report = machine.executable(master_id="AXM-20-TESTING-OBSERVABILITY-C-015-validation-report")["master"]
        self.assertEqual(report["status"], "live-backed")
        self.assertIn("AXM-CAP-VERIFY-PROJECT", report["implemented_by"])

        patch = machine.executable(master_id="AXM-05-CODE-GRAMMAR-C-029-code-patch")["master"]
        self.assertEqual(patch["status"], "live-backed")
        self.assertEqual(patch["implemented_by"], ["AXM-CAP-PATCH-PROJECT"])

        template = machine.executable(master_id="AXM-05-CODE-GRAMMAR-C-022-code-template")["master"]
        self.assertEqual(template["status"], "live-backed")
        self.assertEqual(template["implemented_by"], ["AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE"])

        workspace = machine.executable(master_id="AXM-24-WORKSPACE-COLLABORATION-C-011-workspace")["master"]
        self.assertEqual(workspace["status"], "live-backed")
        self.assertEqual(workspace["implemented_by"], ["AXM-CAP-SELF-WORKSPACE"])

        dependency_graph = machine.executable(master_id="AXM-05-CODE-GRAMMAR-C-025-dependency-graph")["master"]
        self.assertEqual(dependency_graph["status"], "live-backed")
        self.assertEqual(dependency_graph["implemented_by"], ["AXM-CAP-ASSEMBLE-ORGAN-PROJECT"])

        interface_contract = machine.executable(master_id="AXM-00-FOUNDATION-C-019-interface-contract")["master"]
        self.assertEqual(interface_contract["status"], "live-backed")
        self.assertEqual(interface_contract["implemented_by"], ["AXM-CAP-ASSEMBLE-ORGAN-PROJECT"])

    def test_planner_surfaces_explicit_live_anatomy_bindings(self):
        plan = UniversalCreationMachine(ROOT).plan({
            "kind": "software-project",
            "direction": "create a project with deterministic validation",
            "inputs": {"path": "creations/planned", "files": {"README.md": "# planned\n"}},
        }, per_level=20)
        coverage = plan["executable_anatomy"]["selected_records_with_declared_binding"]
        self.assertTrue(any(row["master_id"] == "AXM-24-WORKSPACE-COLLABORATION-C-010-project" for row in coverage))

    def test_promoted_composite_routes_as_live_capability_without_new_source_function(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "composite-site"
            machine = UniversalCreationMachine(ROOT)
            result = machine.create({
                "kind": "verified-static-web-project",
                "direction": "create and independently verify a small local site",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<!doctype html><html><body><main>Live composite</main></body></html>"
                    },
                    "checks": [
                        {"type": "contains", "path": "index.html", "text": "Live composite"}
                    ],
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-BUILD-VERIFY-PROJECT")
            self.assertTrue(result["result"]["build"]["published"])
            self.assertTrue(result["result"]["verification"]["passed"])
            self.assertEqual((target / "index.html").read_text(encoding="utf-8"), "<!doctype html><html><body><main>Live composite</main></body></html>")

            manifest = machine.capabilities.by_id("AXM-CAP-BUILD-VERIFY-PROJECT")
            self.assertEqual(manifest["implementation"]["kind"], "DETERMINISTIC_COMPOSITE")
            self.assertEqual(manifest["implementation"]["source"], "this manifest")

    def test_verified_composite_keeps_failed_creation_out_of_target(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "strict-composite-site"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "verified-static-web-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {"index.html": "<script src=\"missing.js\"></script>"},
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse(target.exists())

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
        with self.assertRaisesRegex(Exception, "not live"):
            machine.capabilities.invoke(manifest, {})


if __name__ == "__main__":
    unittest.main()

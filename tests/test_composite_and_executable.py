from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.capabilities import CapabilityError, _resolve_binding
from axm_uc.machine import UniversalCreationMachine


class CompositeAndExecutableTests(unittest.TestCase):
    def test_executable_anatomy_counts_only_explicit_implementation_bindings(self):
        machine = UniversalCreationMachine(ROOT)
        summary = machine.executable()["summary"]
        self.assertEqual(summary["truth_status"], "EXPLICIT_LIVE_CAPABILITY_BINDINGS")
        self.assertEqual(summary["implemented_master_records"], 28)
        self.assertEqual(summary["implemented_master_by_level"], {"component": 19, "organ": 9})
        self.assertEqual(summary["live_capabilities"], 21)
        self.assertEqual(summary["resolved_bindings"], 59)

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
        self.assertEqual(
            dependency_graph["implemented_by"],
            ["AXM-CAP-ASSEMBLE-ORGAN-PROJECT", "AXM-CAP-COMPOSE-ORGAN-PROJECT"],
        )

        interface_contract = machine.executable(master_id="AXM-00-FOUNDATION-C-019-interface-contract")["master"]
        self.assertEqual(interface_contract["status"], "live-backed")
        self.assertEqual(
            interface_contract["implemented_by"],
            [
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT",
                "AXM-CAP-COMPOSE-ORGAN-PROJECT",
                "AXM-CAP-EXPLORE-ORGAN-GAP",
            ],
        )

        package_manifest = machine.executable(master_id="AXM-06-BUILD-PACKAGE-C-001-package-manifest")["master"]
        self.assertEqual(package_manifest["status"], "live-backed")
        self.assertEqual(package_manifest["implemented_by"], ["AXM-CAP-INSPECT-EXECUTABLE-ORGANS"])

        artifact_builder = machine.executable(master_id="AXM-06-BUILD-PACKAGE-O-004-artifact-builder")["master"]
        self.assertEqual(artifact_builder["status"], "live-backed")
        self.assertEqual(artifact_builder["implemented_by"], ["AXM-CAP-SPAWN-CREATION-UNIT"])

        interface_validator = machine.executable(master_id="AXM-00-FOUNDATION-O-012-interface-validator")["master"]
        self.assertEqual(interface_validator["status"], "live-backed")
        self.assertEqual(interface_validator["implemented_by"], ["AXM-CAP-MATERIALIZE-ORGANS"])

        evidence_collector = machine.executable(master_id="AXM-01-PROVENANCE-O-002-evidence-collector")["master"]
        self.assertEqual(evidence_collector["status"], "live-backed")
        self.assertEqual(evidence_collector["implemented_by"], ["AXM-CAP-MATERIALIZE-ORGANS"])

        adapter = machine.executable(master_id="AXM-19-AI-ML-AGENTS-C-009-adapter")["master"]
        self.assertEqual(adapter["status"], "live-backed")
        self.assertEqual(adapter["implemented_by"], ["AXM-CAP-SYNTHESIZE-CREATION-GAP"])

        rollback = machine.executable(master_id="AXM-01-PROVENANCE-C-014-rollback-snapshot")["master"]
        self.assertEqual(rollback["status"], "live-backed")
        self.assertEqual(rollback["implemented_by"], ["AXM-CAP-EVOLVE-MACHINE"])

        renderer = machine.executable(master_id="AXM-12-RENDERING-MATERIALS-O-012-renderer")["master"]
        self.assertEqual(renderer["status"], "live-backed")
        self.assertEqual(renderer["implemented_by"], ["AXM-CAP-PAINTGUN-SPECIALIST"])

        state_machine = machine.executable(master_id="AXM-03-TIME-STATE-EVENT-C-004-state-machine")["master"]
        self.assertEqual(state_machine["status"], "live-backed")
        self.assertEqual(state_machine["implemented_by"], ["AXM-CAP-SIMULATE-CREATION"])

        lod_group = machine.executable(master_id="AXM-11-3D-SPATIAL-C-028-level-of-detail-group")["master"]
        self.assertEqual(lod_group["status"], "live-backed")
        self.assertEqual(lod_group["implemented_by"], ["AXM-CAP-SIMULATE-CREATION"])

        specialist_summoner = machine.executable(master_id="AXM-19-AI-ML-AGENTS-O-021-specialist-summoner")["master"]
        self.assertEqual(specialist_summoner["status"], "live-backed")
        self.assertEqual(specialist_summoner["implemented_by"], ["AXM-CAP-SPECIALIST-TOURNAMENT"])

        specialist_profile = machine.executable(master_id="AXM-19-AI-ML-AGENTS-C-035-specialist-profile")["master"]
        self.assertEqual(specialist_profile["status"], "live-backed")
        self.assertEqual(specialist_profile["implemented_by"], ["AXM-CAP-SPECIALIST-TOURNAMENT"])

        project_planner = machine.executable(master_id="AXM-24-WORKSPACE-COLLABORATION-O-006-project-planner")["master"]
        self.assertEqual(project_planner["status"], "live-backed")
        self.assertEqual(project_planner["implemented_by"], ["AXM-CAP-SPECIALIST-TOURNAMENT"])

        workflow_engine = machine.executable(master_id="AXM-03-TIME-STATE-EVENT-O-007-workflow-engine")["master"]
        self.assertEqual(workflow_engine["status"], "live-backed")
        self.assertEqual(workflow_engine["implemented_by"], ["AXM-CAP-SPECIALIST-TOURNAMENT"])

        workflow_step = machine.executable(master_id="AXM-03-TIME-STATE-EVENT-C-015-workflow-step")["master"]
        self.assertEqual(workflow_step["status"], "live-backed")
        self.assertEqual(workflow_step["implemented_by"], ["AXM-CAP-SPECIALIST-TOURNAMENT"])

        chameleon_records = [
            "AXM-11-3D-SPATIAL-C-018-morph-target",
            "AXM-13-ANIMATION-VIDEO-C-005-morph-animation",
            "AXM-12-RENDERING-MATERIALS-C-007-material-graph",
            "AXM-23-PROCEDURAL-C-013-procedural-material-graph",
            "AXM-12-RENDERING-MATERIALS-O-001-material-compiler",
            "AXM-15-SIMULATION-XR-C-019-sensor-model",
            "AXM-15-SIMULATION-XR-O-011-sensor-fusion-organ",
        ]
        for master_id in chameleon_records:
            view = machine.executable(master_id=master_id)["master"]
            self.assertEqual(view["status"], "live-backed", master_id)
            self.assertEqual(view["implemented_by"], ["AXM-CAP-SIMULATE-CREATION"], master_id)

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

    def test_file_receipt_digest_projection_is_closed_and_deterministic(self):
        digest_a = "a" * 64
        digest_b = "b" * 64
        binding = {
            "from": "steps.build.files",
            "transform": "file-digest-map",
        }
        result = _resolve_binding(
            binding,
            {},
            {"build": {"files": [
                {"path": "index.html", "bytes": 1, "sha256": digest_a},
                {"path": "style.css", "bytes": 2, "sha256": digest_b},
            ]}},
        )
        self.assertEqual(result, {"index.html": digest_a, "style.css": digest_b})

        with self.assertRaisesRegex(CapabilityError, "unique"):
            _resolve_binding(binding, {}, {"build": {"files": [
                {"path": "same.txt", "sha256": digest_a},
                {"path": "same.txt", "sha256": digest_b},
            ]}})
        with self.assertRaisesRegex(CapabilityError, "SHA-256"):
            _resolve_binding(binding, {}, {"build": {"files": [{"path": "bad.txt", "sha256": "not-a-digest"}]}})
        with self.assertRaisesRegex(CapabilityError, "unsupported"):
            _resolve_binding(
                {"from": "steps.build.files", "transform": "arbitrary-expression"},
                {},
                {"build": {"files": [{"path": "a.txt", "sha256": digest_a}]}},
            )


if __name__ == "__main__":
    unittest.main()

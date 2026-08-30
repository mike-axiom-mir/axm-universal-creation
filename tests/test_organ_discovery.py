from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.gap_synthesis import analyze_creation_gap, compile_gap_proposal
from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_discovery import discover_interface_assembly


class InterfaceOrganDiscoveryTests(unittest.TestCase):
    @staticmethod
    def _goal(required_interfaces: list[str] | None = None) -> dict:
        return {
            "schema": "axm.interface-organ-goal/v0.1",
            "id": "axm.test.interface-discovered-site",
            "version": "1.0.0",
            "project_type": "static-web",
            "required_interfaces": required_interfaces or ["local-interaction"],
            "bindings": {
                "document-shell": {
                    "idle_label": "Create",
                    "title": "Interface-discovered creation",
                },
                "visual-theme": {"background": "#10223b"},
                "local-interaction": {
                    "active_label": "Created",
                    "state": "created",
                },
            },
        }

    @classmethod
    def _gap_request(
        cls,
        path: str,
        report_path: str,
        required_interfaces: list[str] | None = None,
    ) -> dict:
        goal = cls._goal(required_interfaces)
        if required_interfaces != ["unavailable-creation-interface"]:
            bindings = goal["bindings"]
        else:
            bindings = {}
        goal["bindings"] = bindings
        return {
            "kind": "verified-interface-organ-project-with-json-report",
            "direction": "discover an exact organ body from interfaces, verify it, and preserve the receipt",
            "inputs": {
                "path": path,
                "organ_goal": goal,
                "checks": [
                    {
                        "type": "contains",
                        "path": "index.html",
                        "text": "Interface-discovered creation",
                    }
                ],
                "replace": False,
                "report_path": report_path,
            },
        }

    def test_goal_only_names_required_interface_and_discovers_exact_transitive_closure(self):
        result = discover_interface_assembly(ROOT, self._goal())
        self.assertEqual(result["status"], "READY_EXACT_INTERFACE_ASSEMBLY")
        self.assertEqual(result["search"]["states_observed"], 4)
        self.assertEqual(
            result["selected_candidate"]["package_refs"],
            [
                "axm.web.shell@1.0.0",
                "axm.web.theme@1.0.0",
                "axm.web.interaction@1.0.0",
            ],
        )
        self.assertEqual(
            result["assembly"]["organs"],
            [
                {
                    "instance_id": "shell-organ",
                    "ref": "axm.web.shell@1.0.0",
                    "depends_on": [],
                    "bindings": {
                        "idle_label": "Create",
                        "title": "Interface-discovered creation",
                    },
                },
                {
                    "instance_id": "theme-organ",
                    "ref": "axm.web.theme@1.0.0",
                    "depends_on": ["shell-organ"],
                    "bindings": {"background": "#10223b"},
                },
                {
                    "instance_id": "interaction-organ",
                    "ref": "axm.web.interaction@1.0.0",
                    "depends_on": ["theme-organ"],
                    "bindings": {
                        "active_label": "Created",
                        "state": "created",
                    },
                },
            ],
        )
        self.assertFalse(result["automatic_or_fuzzy_selection"])
        self.assertFalse(result["runtime_wiring_invented"])

    def test_discovery_inspection_is_read_only_and_direct_composition_is_repeatable(self):
        machine = UniversalCreationMachine(ROOT)
        planned = machine.create({
            "kind": "discover-organ-assembly",
            "inputs": {"organ_goal": self._goal()},
        })
        self.assertEqual(planned["type"], "CREATION_RESULT", planned)
        self.assertEqual(
            planned["result"]["assembly_plan"]["status"],
            "READY_EXACT_INTERFACE_ASSEMBLY",
        )

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            receipts = []
            bodies = []
            for name in ("first", "second"):
                target = parent / name
                result = machine.create({
                    "kind": "interface-organ-project",
                    "inputs": {
                        "path": str(target),
                        "organ_goal": self._goal(),
                        "checks": [
                            {
                                "type": "contains",
                                "path": "index.html",
                                "text": "Interface-discovered creation",
                            }
                        ],
                        "publish_mode": "validated",
                    },
                })
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                self.assertEqual(result["result"]["creation_status"], "VALIDATED_CREATION")
                self.assertEqual(
                    result["result"]["organ_discovery"]["status"],
                    "READY_EXACT_INTERFACE_ASSEMBLY",
                )
                receipts.append(result["result"]["files"])
                bodies.append({
                    path.name: path.read_text(encoding="utf-8")
                    for path in sorted(target.iterdir())
                })
            self.assertEqual(receipts[0], receipts[1])
            self.assertEqual(bodies[0], bodies[1])

    def test_missing_interface_emits_forge_ready_organ_contract_and_creates_nothing(self):
        goal = self._goal(["unavailable-creation-interface"])
        goal["bindings"] = {}
        discovery = discover_interface_assembly(ROOT, goal)
        self.assertEqual(discovery["status"], "HOLD_MISSING_ORGAN_INTERFACE")
        self.assertEqual(discovery["missing_interfaces"], ["unavailable-creation-interface"])
        contract = discovery["missing_unit_contracts"][0]
        self.assertEqual(contract["kind"], "organ")
        self.assertEqual(contract["must_provide"], ["unavailable-creation-interface"])
        self.assertTrue(contract["source_and_tests_required"])
        self.assertFalse(contract["automatic_source_invention"])
        self.assertEqual(contract["admission_authority"], "NONE")

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "held"
            created = UniversalCreationMachine(ROOT).create({
                "kind": "interface-organ-project",
                "inputs": {"path": str(target), "organ_goal": goal},
            })
            self.assertEqual(created["type"], "CREATION_ERROR")
            self.assertEqual(
                created["details"]["organ_discovery"]["status"],
                "HOLD_MISSING_ORGAN_INTERFACE",
            )
            self.assertFalse(target.exists())

    def test_unique_assembly_with_incomplete_bindings_stays_on_typed_hold(self):
        goal = self._goal()
        goal["bindings"] = {
            "document-shell": goal["bindings"]["document-shell"],
        }
        result = discover_interface_assembly(ROOT, goal)
        self.assertEqual(result["status"], "HOLD_ORGAN_BINDING_CONTRACT")
        self.assertEqual(
            [row["ref"] for row in result["binding_issues"]],
            ["axm.web.theme@1.0.0", "axm.web.interaction@1.0.0"],
        )
        self.assertIsNone(result["assembly"])

    def test_equal_minimum_provider_sets_stay_ambiguous(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            shutil.copytree(ROOT / "executable-organs", root / "executable-organs")
            theme_path = root / "executable-organs/axm.web.theme-1.0.0.json"
            alternative = json.loads(theme_path.read_text(encoding="utf-8"))
            alternative["id"] = "axm.web.theme-alt"
            alternative["purpose"] = "An exact alternative visual-theme provider used to prove ambiguity holds."
            (root / "executable-organs/axm.web.theme-alt-1.0.0.json").write_text(
                json.dumps(alternative),
                encoding="utf-8",
            )
            result = discover_interface_assembly(root, self._goal(["visual-theme"]))
        self.assertEqual(result["status"], "HOLD_AMBIGUOUS_ORGAN_ASSEMBLY")
        self.assertEqual(len(result["candidate_assemblies"]), 2)
        self.assertIsNone(result["assembly"])

    def test_gap_compiler_builds_and_tests_discovered_organ_verify_report_recipe(self):
        request = self._gap_request(
            "creations/original-interface-site",
            "creations/original-interface-report.json",
        )
        analysis = analyze_creation_gap(ROOT, request)
        self.assertEqual(analysis["status"], "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN")
        selected = analysis["selected_blueprint"]
        self.assertEqual(selected["producer"]["profile"], "interface-discovered-organ-assembly")
        self.assertEqual(selected["step_order"], ["produce", "verify", "report"])
        self.assertEqual(
            [row["ref"] for row in selected["dependencies"]],
            [
                "AXM-CAP-COMPOSE-ORGAN-PROJECT@0.1.0",
                "AXM-CAP-VERIFY-PROJECT@0.5.0",
                "AXM-CAP-WRITE-JSON@0.1.0",
            ],
        )
        first = compile_gap_proposal(ROOT, request)
        second = compile_gap_proposal(ROOT, request)
        self.assertEqual(first["proposal_digest"], second["proposal_digest"])
        self.assertEqual(first["proposal"], second["proposal"])
        manifest = json.loads(first["proposal"]["files"]["capability.json"])
        self.assertEqual(
            [step["capability"] for step in manifest["implementation"]["steps"]],
            [
                "AXM-CAP-COMPOSE-ORGAN-PROJECT",
                "AXM-CAP-VERIFY-PROJECT",
                "AXM-CAP-WRITE-JSON",
            ],
        )

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-must-not-exist"
            requested_report = parent / "original-report-must-not-exist.json"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(parent / "detached-candidate"),
                    "request": self._gap_request(str(requested), str(requested_report)),
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            self.assertFalse(requested.exists())
            self.assertFalse(requested_report.exists())
            candidate_test = explored["test"]["kind_test"]["capability_test"]["tests"][0]
            self.assertEqual(
                candidate_test["result"]["production"]["organ_discovery"]["status"],
                "READY_EXACT_INTERFACE_ASSEMBLY",
            )
            self.assertTrue(candidate_test["result"]["verification"]["passed"])
            self.assertTrue(candidate_test["json_file_result_check"]["passed"])
            self.assertIsNone(
                UniversalCreationMachine(ROOT).capabilities.route(
                    "verified-interface-organ-project-with-json-report"
                )
            )

    def test_gap_preserves_missing_interface_hold_without_compiling(self):
        request = self._gap_request(
            "creations/held-interface-site",
            "creations/held-interface-report.json",
            ["unavailable-creation-interface"],
        )
        analysis = analyze_creation_gap(ROOT, request)
        self.assertEqual(analysis["status"], "HOLD_MISSING_ORGAN_INTERFACE")
        discovery = analysis["composite_candidates"][0]["organ_discovery"]
        self.assertEqual(
            discovery["missing_unit_contracts"][0]["must_provide"],
            ["unavailable-creation-interface"],
        )
        compiled = compile_gap_proposal(ROOT, request)
        self.assertIsNone(compiled["proposal"])
        self.assertTrue(compiled["hold_preserved"])


if __name__ == "__main__":
    unittest.main()

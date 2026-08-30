from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_discovery import discover_interface_assembly
from axm_uc.organ_library import ExecutableOrganLibrary


ZERO_AUTHORITY = {
    "execute": False,
    "install": False,
    "register": False,
    "promote": False,
    "merge": False,
    "canon": False,
    "permissions": False,
}


def root_fit() -> dict:
    return {
        "truth": {
            "fit": True,
            "basis": "The exact source, declarations, test, and remaining proof boundary are explicit.",
        },
        "agency": {
            "fit": True,
            "basis": "The candidate remains detached and grants itself no authority.",
        },
        "continuity": {
            "fit": True,
            "basis": "The live executable-organ library remains unchanged.",
        },
        "wisdom-before-speed": {
            "fit": True,
            "basis": "The observed gap must close and build before any separate review decision.",
        },
    }


class MissingOrganClosureTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    @staticmethod
    def _goal() -> dict:
        return {
            "schema": "axm.interface-organ-goal/v0.1",
            "id": "axm.test.status-panel-site",
            "version": "1.0.0",
            "project_type": "static-web",
            "required_interfaces": ["status-panel"],
            "bindings": {
                "document-shell": {
                    "idle_label": "Create closure",
                    "title": "Detached organ closure",
                },
                "visual-theme": {"background": "#10223b"},
                "local-interaction": {
                    "active_label": "Closure created",
                    "state": "created",
                },
                "status-panel": {"message": "Candidate closes exact gap"},
            },
        }

    @staticmethod
    def _package() -> dict:
        return {
            "schema": "axm.executable-software-organ/v0.1",
            "id": "axm.web.status-panel",
            "version": "1.0.0",
            "status": "executable",
            "purpose": "Own one exact status panel after local interaction.",
            "project_types": ["static-web"],
            "parameters": ["message"],
            "provides": ["status-panel"],
            "requires": ["local-interaction"],
            "files": {
                "status.html": "<!doctype html><html><body><aside>[[AXM:message]]</aside></body></html>\n"
            },
            "anatomy_refs": ["AXM-09-UI-INTERACTION-C-001-ui-component"],
            "provenance": {
                "kind": "human-ai-supplied-test-source",
                "basis": "Explicit source supplied to test one observed missing-interface closure.",
            },
            "limitations": [
                "This exact fragment does not prove browser-rendered visual quality or runtime behavior."
            ],
        }

    @classmethod
    def _proposal(cls, package: dict | None = None) -> dict:
        package = copy.deepcopy(package if package is not None else cls._package())
        return {
            "schema": "axm.creation-unit-spawn-proposal/v0.1",
            "id": package["id"],
            "version": package["version"],
            "kind": "organ",
            "purpose": "Supply one explicit status-panel organ for a detached missing-interface experiment.",
            "files": {
                "organ.json": json.dumps(package, indent=2, sort_keys=True) + "\n",
            },
            "implementation": {
                "kind": "DETERMINISTIC_SOURCE",
                "entrypoint": "organ.json",
                "source_files": ["organ.json"],
            },
            "contracts": {
                "inputs": {"bindings": ["message"]},
                "outputs": {"files": ["status.html"]},
                "provides": copy.deepcopy(package["provides"]),
                "requires": copy.deepcopy(package["requires"]),
            },
            "dependencies": [
                {
                    "kind": "organ",
                    "ref": "axm.web.interaction@1.0.0",
                    "optional": False,
                }
            ],
            "relationships": [
                {"type": "closes-interface-gap", "target": "status-panel"},
            ],
            "verification": {
                "checks": [{"type": "json-valid", "path": "organ.json"}],
            },
            "provenance": {
                "kind": "human-ai-supplied-test-source",
                "refs": ["HOLD_MISSING_ORGAN_INTERFACE:status-panel"],
                "basis": "The explicit source is tested without claiming automatic invention or admission.",
            },
            "limitations": [
                "This candidate proves only its exact detached closure fixture.",
            ],
            "authority": copy.deepcopy(ZERO_AUTHORITY),
            "root_fit": root_fit(),
        }

    def _request(self, target: Path, proposal: dict, checks: list[dict] | None = None) -> dict:
        return self.machine.create({
            "kind": "explore-missing-organ-closure",
            "inputs": {
                "path": str(target),
                "organ_goal": self._goal(),
                "proposal": proposal,
                "checks": checks or [
                    {
                        "type": "contains",
                        "path": "status.html",
                        "text": "Candidate closes exact gap",
                    }
                ],
            },
        })

    def test_explicit_candidate_closes_gap_in_ephemeral_build_without_installation(self):
        initial = discover_interface_assembly(ROOT, self._goal())
        self.assertEqual(initial["status"], "HOLD_MISSING_ORGAN_INTERFACE")
        self.assertEqual(initial["missing_interfaces"], ["status-panel"])
        before_refs = ExecutableOrganLibrary(ROOT).summary()["package_refs"]

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "candidate"
            result = self._request(target, self._proposal())
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            closure = result["result"]
            self.assertTrue(closure["passed"], closure)
            self.assertEqual(
                closure["status"],
                "TESTED_DETACHED_ORGAN_CLOSES_INTERFACE_GAP",
            )
            self.assertTrue(target.is_dir())
            self.assertTrue(closure["candidate_test"]["passed"])
            self.assertTrue(closure["contract_alignment"]["passed"])
            self.assertEqual(closure["candidate_package"]["source_path"], "organ.json")
            self.assertIn("disposable", closure["candidate_package"]["source_context"])
            self.assertEqual(
                closure["closure_discovery"]["status"],
                "READY_EXACT_INTERFACE_ASSEMBLY",
            )
            self.assertIn(
                "axm.web.status-panel@1.0.0",
                closure["closure_discovery"]["selected_candidate"]["package_refs"],
            )
            self.assertEqual(closure["closure_build"]["creation_status"], "VALIDATED_CREATION")
            self.assertEqual(
                [row["path"] for row in closure["closure_build"]["files"]],
                ["app.js", "index.html", "status.html", "style.css"],
            )
            self.assertTrue(closure["closure_build"]["ephemeral_project_disposed"])
            self.assertFalse(closure["candidate_installed"])
            self.assertFalse(closure["candidate_admission_requested"])

        self.assertEqual(ExecutableOrganLibrary(ROOT).summary()["package_refs"], before_refs)
        self.assertEqual(
            discover_interface_assembly(ROOT, self._goal())["status"],
            "HOLD_MISSING_ORGAN_INTERFACE",
        )

    def test_same_design_reproduces_package_and_closure_receipts(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            first = self._request(parent / "first", self._proposal())["result"]
            second = self._request(parent / "second", self._proposal())["result"]
            self.assertTrue(first["passed"] and second["passed"])
            self.assertEqual(
                first["spawn"]["spawn_receipt"]["proposal_digest"],
                second["spawn"]["spawn_receipt"]["proposal_digest"],
            )
            self.assertEqual(
                first["spawn"]["spawn_receipt"]["package_digest"],
                second["spawn"]["spawn_receipt"]["package_digest"],
            )
            self.assertEqual(first["closure_discovery"], second["closure_discovery"])
            self.assertEqual(first["closure_build"]["files"], second["closure_build"]["files"])

    def test_contract_drift_and_unrelated_organ_hold_before_materialization(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            drift = self._proposal()
            drift["contracts"]["provides"] = []
            drifted = self._request(parent / "drift", drift)["result"]
            self.assertEqual(drifted["status"], "HOLD_ORGAN_PROPOSAL_CONTRACT_MISMATCH")
            self.assertFalse(drifted["candidate_target_created"])
            self.assertFalse((parent / "drift").exists())

            package = self._package()
            package["provides"] = ["unrelated-panel"]
            unrelated = self._request(parent / "unrelated", self._proposal(package))["result"]
            self.assertEqual(unrelated["status"], "HOLD_ORGAN_PROPOSAL_NOT_LINKED_TO_GAP")
            self.assertFalse(unrelated["candidate_target_created"])
            self.assertFalse((parent / "unrelated").exists())

    def test_invalid_package_holds_before_detached_output(self):
        package = self._package()
        package["parameters"] = []
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "invalid"
            held = self._request(target, self._proposal(package))["result"]
            self.assertEqual(held["status"], "HOLD_CANDIDATE_ORGAN_PACKAGE_INVALID")
            self.assertFalse(held["candidate_target_created"])
            self.assertFalse(target.exists())

    def test_tested_candidate_can_still_hold_on_incomplete_closure_or_failed_build(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            package = self._package()
            package["requires"] = ["unavailable-transitive-interface"]
            incomplete = self._request(parent / "incomplete", self._proposal(package))["result"]
            self.assertEqual(incomplete["status"], "HOLD_CANDIDATE_ORGAN_CLOSURE_INCOMPLETE")
            self.assertTrue(incomplete["candidate_test"]["passed"])
            self.assertTrue((parent / "incomplete").is_dir())
            self.assertEqual(
                incomplete["closure_discovery"]["status"],
                "HOLD_MISSING_ORGAN_INTERFACE",
            )

            failed = self._request(
                parent / "failed-build",
                self._proposal(),
                checks=[
                    {
                        "type": "contains",
                        "path": "status.html",
                        "text": "text that is deliberately absent",
                    }
                ],
            )["result"]
            self.assertEqual(failed["status"], "HOLD_CANDIDATE_ORGAN_CLOSURE_BUILD_FAILED")
            self.assertTrue(failed["candidate_test"]["passed"])
            self.assertTrue((parent / "failed-build").is_dir())

    def test_machine_inspection_exposes_closure_boundary(self):
        summary = self.machine.inspect()["organ_gap_closure"]
        self.assertTrue(summary["requires_explicit_supplied_organ_proposal"])
        self.assertTrue(summary["ephemeral_candidate_library_overlay"])
        self.assertTrue(summary["full_ephemeral_closure_build"])
        self.assertFalse(summary["automatic_source_invention"])
        self.assertFalse(summary["automatic_install_or_admission"])

    def test_checks_and_replace_types_are_not_coerced(self):
        with tempfile.TemporaryDirectory() as td:
            for field, value, message in (
                ("checks", {"type": "json-valid"}, "checks must be a list"),
                ("replace", "false", "replace must be a boolean"),
            ):
                inputs = {
                    "path": str(Path(td) / field),
                    "organ_goal": self._goal(),
                    "proposal": self._proposal(),
                    field: value,
                }
                result = self.machine.create({
                    "kind": "explore-missing-organ-closure",
                    "inputs": inputs,
                })
                self.assertEqual(result["type"], "CREATION_ERROR", result)
                self.assertIn(message, result["message"])
                self.assertFalse((Path(td) / field).exists())


if __name__ == "__main__":
    unittest.main()

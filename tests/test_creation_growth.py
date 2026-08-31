from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_library import ExecutableOrganLibrary


ANATOMY_ID = "AXM-09-UI-INTERACTION-O-015-notification-manager"


def growth_request() -> dict:
    return {
        "kind": "status-panel-site",
        "inputs": {
            "path": "creations/grown-status-panel",
            "organ_goal": {
                "schema": "axm.interface-organ-goal/v0.1",
                "id": "axm.example.grown-status-panel-site",
                "version": "1.0.0",
                "project_type": "static-web",
                "required_interfaces": ["status-panel"],
                "bindings": {
                    "document-shell": {"idle_label": "Create", "title": "Bounded creation growth"},
                    "visual-theme": {"background": "#07131c"},
                    "local-interaction": {"active_label": "Created", "state": "created"},
                    "status-panel": {"message": "Created through bounded organ growth"},
                },
            },
            "checks": [
                {"type": "contains", "path": "status.html", "text": "Created through bounded organ growth"}
            ],
        },
    }


def status_panel_package() -> dict:
    return {
        "schema": "axm.executable-software-organ/v0.1",
        "id": "axm.web.grown-status-panel",
        "version": "1.0.0",
        "status": "executable",
        "purpose": "Render one explicit status-panel fragment for the bounded creation-growth experiment.",
        "project_types": ["static-web"],
        "parameters": ["message"],
        "provides": ["status-panel"],
        "requires": ["local-interaction"],
        "files": {
            "status.html": "<!doctype html><html><body><aside>[[AXM:message]]</aside></body></html>\n"
        },
        "anatomy_refs": [ANATOMY_ID],
        "provenance": {
            "kind": "local-authored-source",
            "basis": "Explicit bounded example source supplied to connect the materialization census to one observed creation gap.",
        },
        "limitations": [
            "This fragment does not prove browser-rendered visual quality, accessibility, or runtime behavior."
        ],
    }


class CreationGrowthTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    def _create(self, operation: str, **extra) -> dict:
        return self.machine.create({
            "kind": "creation-organ-growth",
            "inputs": {"operation": operation, "request": growth_request(), **extra},
        })

    def test_analyze_links_exact_creation_gap_without_selecting_source(self):
        result = self._create("analyze")
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        body = result["result"]
        self.assertEqual(body["missing_interface"], "status-panel")
        self.assertEqual(body["analysis"]["status"], "HOLD_MISSING_ORGAN_INTERFACE")
        self.assertFalse(body["source_invented"])
        self.assertFalse(body["live_machine_body_modified"])

    def test_prepare_compiles_explicit_anatomy_package_and_exact_interface(self):
        result = self._create("prepare", anatomy_id=ANATOMY_ID, package=status_panel_package())
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        body = result["result"]
        self.assertEqual(body["missing_interface"], "status-panel")
        self.assertEqual(body["anatomy_id"], ANATOMY_ID)
        self.assertEqual(body["anatomy_materialization_before"]["state"], "IMPLEMENTATION_REQUIRED")
        self.assertIn("status-panel", body["package_provides"])
        self.assertFalse(body["materialized"])
        self.assertFalse(body["candidate_installed"])

    def test_materialized_candidate_closes_full_ephemeral_creation_without_installing(self):
        refs_before = ExecutableOrganLibrary(ROOT).summary()["package_refs"]
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "growth-candidate"
            result = self._create(
                "materialize-and-test",
                anatomy_id=ANATOMY_ID,
                package=status_panel_package(),
                path=str(target),
                checks=growth_request()["inputs"]["checks"],
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertTrue(body["passed"], body)
            self.assertEqual(body["status"], "TESTED_CREATION_GROWTH_CANDIDATE")
            self.assertTrue(body["generic_compose_capability_expansion_observed_in_ephemeral_space"])
            self.assertTrue(body["closure"]["candidate_selected_in_closure"])
            self.assertTrue((target / "organ.json").is_file())
            self.assertFalse(body["candidate_installed"])
            self.assertFalse(body["live_machine_body_modified"])
        self.assertEqual(ExecutableOrganLibrary(ROOT).summary()["package_refs"], refs_before)

    def test_non_gap_and_wrong_interface_hold_without_writing(self):
        with tempfile.TemporaryDirectory() as td:
            covered = self.machine.create({
                "kind": "creation-organ-growth",
                "inputs": {
                    "operation": "materialize-and-test",
                    "request": {"kind": "text-file", "inputs": {"path": "creations/x.txt", "content": "x"}},
                    "anatomy_id": ANATOMY_ID,
                    "package": status_panel_package(),
                    "path": str(Path(td) / "covered"),
                },
            })
            self.assertEqual(covered["type"], "CREATION_ERROR", covered)
            self.assertIn("requires an observed missing", covered["message"])
            wrong = status_panel_package()
            wrong["provides"] = ["other-interface"]
            held = self._create(
                "materialize-and-test",
                anatomy_id=ANATOMY_ID,
                package=wrong,
                path=str(Path(td) / "wrong"),
            )
            self.assertEqual(held["type"], "CREATION_ERROR", held)
            self.assertIn("does not provide", held["message"])
            self.assertFalse((Path(td) / "wrong").exists())


if __name__ == "__main__":
    unittest.main()

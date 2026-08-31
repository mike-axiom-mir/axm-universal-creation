from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_library import ExecutableOrganLibrary
from axm_uc.organ_materialization import (
    ZERO_AUTHORITY,
    _package_connectivity,
    census_organs,
    compile_organ_proposal,
)


ANATOMY_ID = "AXM-00-FOUNDATION-O-001-identity-registry"


def identity_registry_package() -> dict:
    return {
        "schema": "axm.executable-software-organ/v0.1",
        "id": "axm.foundation.identity-registry.document",
        "version": "1.0.0",
        "status": "executable",
        "purpose": "Render a deterministic initial identity-registry JSON document for one explicit namespace.",
        "project_types": ["generic"],
        "parameters": ["namespace"],
        "provides": ["identity-registry-document"],
        "requires": [],
        "files": {
            "identity-registry.json": (
                "{\n"
                "  \"schema\": \"axm.identity-registry/v0.1\",\n"
                "  \"namespace\": \"[[AXM:namespace]]\",\n"
                "  \"identities\": []\n"
                "}\n"
            ),
        },
        "anatomy_refs": [ANATOMY_ID],
        "provenance": {
            "kind": "local-authored-source",
            "basis": "A bounded deterministic implementation supplied explicitly for the organ-materialization example.",
        },
        "limitations": [
            "This package renders an initial registry document; it does not implement persistence, authentication, or concurrent identity management."
        ],
    }


class OrganMaterializationTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    def _create(self, handle: str, inputs: dict) -> dict:
        return self.machine.create({"kind": handle, "inputs": inputs})

    def test_census_accounts_for_every_organ_without_inflating_executable_truth(self):
        result = census_organs(ROOT)
        summary = result["summary"]
        self.assertEqual(summary["declared_anatomy_organs"], 415)
        self.assertEqual(summary["observed_registry_organs"], 415)
        self.assertEqual(summary["standalone_organ_source_files"], 415)
        self.assertEqual(summary["source_record_states"]["EXACT"], 415)
        self.assertTrue(summary["source_records_exact"])
        self.assertEqual(summary["installed_executable_packages"], 3)
        self.assertEqual(summary["anatomy_with_installed_packages"], 3)
        self.assertEqual(summary["anatomy_requiring_implementation"], 412)
        self.assertEqual(
            summary["anatomy_materialization_states"],
            {
                "CONNECTED_EXECUTABLE_PACKAGE": 3,
                "EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES": 0,
                "IMPLEMENTATION_REQUIRED": 412,
            },
        )
        self.assertFalse(summary["all_descriptive_organs_executable"])
        self.assertEqual(result["pagination"]["returned"], 415)
        self.assertEqual(len(result["organs"]), 415)

    def test_census_filters_and_pages_exact_rows(self):
        connected = self._create("inspect-organ-materialization", {
            "operation": "census",
            "state": "CONNECTED_EXECUTABLE_PACKAGE",
            "limit": 2,
        })
        self.assertEqual(connected["type"], "CREATION_RESULT", connected)
        page = connected["result"]
        self.assertEqual(page["pagination"]["matched"], 3)
        self.assertEqual(page["pagination"]["returned"], 2)
        self.assertTrue(page["pagination"]["has_more"])
        self.assertTrue(all(
            row["materialization"]["state"] == "CONNECTED_EXECUTABLE_PACKAGE"
            for row in page["organs"]
        ))

        selected = self.machine.organ_census(anatomy_id=ANATOMY_ID)
        self.assertEqual(selected["pagination"]["matched"], 1)
        self.assertEqual(selected["organs"][0]["materialization"]["state"], "IMPLEMENTATION_REQUIRED")

    def test_connectivity_requires_a_finite_transitive_provider_chain(self):
        packages = [
            {"ref": "base@1.0.0", "project_types": ["generic"], "provides": ["base"], "requires": []},
            {"ref": "middle@1.0.0", "project_types": ["generic"], "provides": ["middle"], "requires": ["base"]},
            {"ref": "top@1.0.0", "project_types": ["generic"], "provides": ["top"], "requires": ["middle"]},
            {"ref": "cycle-a@1.0.0", "project_types": ["generic"], "provides": ["cycle-a"], "requires": ["cycle-b"]},
            {"ref": "cycle-b@1.0.0", "project_types": ["generic"], "provides": ["cycle-b"], "requires": ["cycle-a"]},
        ]
        connectivity = _package_connectivity(packages)
        self.assertEqual(connectivity["top@1.0.0"]["connected_project_types"], ["generic"])
        self.assertTrue(connectivity["top@1.0.0"]["interface_coverage_complete"])
        self.assertFalse(connectivity["cycle-a@1.0.0"]["interface_coverage_complete"])
        self.assertEqual(connectivity["cycle-a@1.0.0"]["unresolved_required_interfaces"], ["cycle-b"])

    def test_compiler_emits_closed_forge_proposal_from_explicit_source(self):
        proposal = compile_organ_proposal(ROOT, ANATOMY_ID, identity_registry_package())
        self.assertEqual(proposal["kind"], "organ")
        self.assertEqual(proposal["id"], "axm.foundation.identity-registry.document")
        self.assertEqual(proposal["authority"], ZERO_AUTHORITY)
        self.assertEqual(proposal["contracts"]["provides"], ["identity-registry-document"])
        self.assertEqual(proposal["contracts"]["requires"], [])
        self.assertEqual(
            proposal["relationships"],
            [{"type": "materializes-anatomy", "target": ANATOMY_ID}],
        )
        self.assertEqual(proposal["implementation"]["entrypoint"], "organ.json")
        package = json.loads(proposal["files"]["organ.json"])
        self.assertEqual(package, identity_registry_package())
        self.assertEqual(proposal["provenance"]["refs"], [f"organs/{ANATOMY_ID}.json"])

        example = json.loads(
            (ROOT / "examples/requests/materialize_identity_registry_organ.json").read_text(encoding="utf-8")
        )
        self.assertEqual(example["inputs"]["anatomy_id"], ANATOMY_ID)
        self.assertEqual(example["inputs"]["package"], identity_registry_package())

    def test_materialize_and_test_builds_detached_candidate_without_installing(self):
        refs_before = ExecutableOrganLibrary(ROOT).summary()["package_refs"]
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "identity-organ"
            result = self._create("materialize-organ-candidate", {
                "operation": "materialize-and-test",
                "path": str(target),
                "anatomy_id": ANATOMY_ID,
                "package": identity_registry_package(),
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertTrue(body["passed"], body)
            self.assertEqual(body["truth_status"], "MATERIALIZED_TESTED_DETACHED_ORGAN_CANDIDATE")
            self.assertTrue((target / "organ.json").is_file())
            self.assertTrue((target / "axm.proposal.json").is_file())
            self.assertTrue(body["test"]["kind_test"]["passed"])
            self.assertEqual(
                body["test"]["kind_test"]["evidence_strength"],
                "EXECUTABLE_ORGAN_PACKAGE_SCHEMA_VALIDATION",
            )
            self.assertFalse(body["installed"])
            self.assertFalse(body["registered"])
            self.assertFalse(body["connected_to_live_library"])
            self.assertFalse(body["live_machine_body_modified"])
        self.assertEqual(ExecutableOrganLibrary(ROOT).summary()["package_refs"], refs_before)

    def test_unknown_or_uncited_anatomy_and_installed_ref_are_rejected(self):
        unknown = self._create("prepare-organ-materialization", {
            "operation": "prepare",
            "anatomy_id": "AXM-00-FOUNDATION-O-999-unknown",
            "package": identity_registry_package(),
        })
        self.assertEqual(unknown["type"], "CREATION_ERROR")
        self.assertIn("unknown organ anatomy ID", unknown["message"])

        uncited_package = identity_registry_package()
        uncited_package["anatomy_refs"] = ["AXM-00-FOUNDATION-O-002-schema-registry"]
        uncited = self._create("prepare-organ-materialization", {
            "operation": "prepare",
            "anatomy_id": ANATOMY_ID,
            "package": uncited_package,
        })
        self.assertEqual(uncited["type"], "CREATION_ERROR")
        self.assertIn("does not explicitly materialize", uncited["message"])

        installed_package = json.loads(
            (ROOT / "executable-organs/axm.web.shell-1.0.0.json").read_text(encoding="utf-8")
        )
        collision = self._create("prepare-organ-materialization", {
            "operation": "prepare",
            "anatomy_id": installed_package["anatomy_refs"][0],
            "package": installed_package,
        })
        self.assertEqual(collision["type"], "CREATION_ERROR")
        self.assertIn("already installed", collision["message"])

    def test_operation_contract_fails_closed_before_writing(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "candidate"
            missing_package = self._create("materialize-organ-candidate", {
                "operation": "materialize-and-test",
                "path": str(target),
                "anatomy_id": ANATOMY_ID,
            })
            self.assertEqual(missing_package["type"], "CREATION_ERROR")
            self.assertIn("missing required implementation inputs", missing_package["message"])
            self.assertFalse(target.exists())

            unsupported = self._create("inspect-organ-materialization", {
                "operation": "census",
                "package": identity_registry_package(),
            })
            self.assertEqual(unsupported["type"], "CREATION_ERROR")
            self.assertIn("unsupported fields", unsupported["message"])

    def test_machine_inspection_exposes_census_summary_and_live_route(self):
        inspection = self.machine.inspect()
        self.assertEqual(inspection["organ_materialization"]["observed_registry_organs"], 415)
        capability = next(
            item for item in inspection["live_capabilities"] if item["id"] == "AXM-CAP-MATERIALIZE-ORGANS"
        )
        self.assertIn("materialize-organ-candidate", capability["handles"])


if __name__ == "__main__":
    unittest.main()

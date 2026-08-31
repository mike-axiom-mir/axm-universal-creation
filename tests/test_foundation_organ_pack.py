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
from axm_uc.organ_library import EXECUTABLE_ORGAN_SCHEMA, ExecutableOrganLibrary
from axm_uc.organ_materialization import census_organs


FOUNDATION_PREFIX = "AXM-00-FOUNDATION-O-"


class FoundationOrganPackTests(unittest.TestCase):
    def test_all_twelve_packages_have_passing_v02_fixtures_and_exact_anatomy_lineage(self):
        library = ExecutableOrganLibrary(ROOT)
        refs = [ref for ref in library.summary()["package_refs"] if ref.startswith("axm.foundation.")]
        self.assertEqual(len(refs), 12)
        self.assertEqual(library.summary()["packages"], 15)
        self.assertEqual(library.summary()["packages_by_schema"][EXECUTABLE_ORGAN_SCHEMA], 12)
        self.assertEqual(library.summary()["declared_fixtures"], 12)

        anatomy_refs: list[str] = []
        for ref in refs:
            package = library.inspect(ref)
            self.assertEqual(package["schema"], EXECUTABLE_ORGAN_SCHEMA)
            self.assertEqual(len(package["anatomy_refs"]), 1)
            anatomy_refs.extend(package["anatomy_refs"])
            fixture_test = library.test(ref)
            self.assertTrue(fixture_test["passed"], fixture_test)
            self.assertEqual(fixture_test["fixture_count"], 1)
            self.assertFalse(fixture_test["runtime_executed"])

        self.assertEqual(len(set(anatomy_refs)), 12)
        self.assertTrue(all(anatomy_ref.startswith(FOUNDATION_PREFIX) for anatomy_ref in anatomy_refs))

    def test_exact_twelve_organ_assembly_builds_one_validated_dependency_connected_pack(self):
        request = json.loads(
            (ROOT / "examples/requests/create_foundation_organ_pack.json").read_text(encoding="utf-8")
        )
        with tempfile.TemporaryDirectory() as td:
            request = copy.deepcopy(request)
            target = Path(td) / "foundation-pack"
            request["inputs"]["path"] = str(target)
            request["inputs"]["replace"] = False
            result = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            body = result["result"]
            self.assertEqual(body["creation_status"], "VALIDATED_CREATION")
            self.assertEqual(body["executable_organ_resolution"]["referenced_package_count"], 12)
            assembly = body["organ_assembly"]
            self.assertEqual(assembly["declared_organ_count"], 12)
            self.assertTrue(assembly["declared_interface_contracts_verified"])
            self.assertFalse(assembly["source_interface_conformance_verified"])
            self.assertEqual(
                assembly["dependency_order"],
                [
                    "identity-registry",
                    "schema-registry",
                    "metadata-manager",
                    "capability-registry",
                    "canonicalization",
                    "version-manager",
                    "dependency-resolver",
                    "relationship-graph",
                    "extension-manager",
                    "compatibility-checker",
                    "migration-manager",
                    "interface-validator",
                ],
            )
            self.assertEqual(len(assembly["file_ownership"]), 12)
            self.assertEqual(len(body["files"]), 12)
            self.assertTrue(all(path.suffix == ".json" for path in target.rglob("*.json")))

    def test_census_connects_the_foundation_twelve_without_inflating_the_remaining_queue(self):
        census = census_organs(ROOT)
        summary = census["summary"]
        self.assertEqual(summary["declared_anatomy_organs"], 415)
        self.assertEqual(summary["installed_executable_packages"], 15)
        self.assertEqual(summary["anatomy_with_installed_packages"], 15)
        self.assertEqual(summary["anatomy_requiring_implementation"], 400)
        self.assertEqual(
            summary["anatomy_materialization_states"],
            {
                "CONNECTED_EXECUTABLE_PACKAGE": 15,
                "EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES": 0,
                "IMPLEMENTATION_REQUIRED": 400,
            },
        )
        foundation = [
            row for row in census["organs"]
            if row["anatomy_id"].startswith(FOUNDATION_PREFIX)
        ]
        self.assertEqual(len(foundation), 12)
        self.assertTrue(all(
            row["materialization"]["state"] == "CONNECTED_EXECUTABLE_PACKAGE"
            for row in foundation
        ))


if __name__ == "__main__":
    unittest.main()

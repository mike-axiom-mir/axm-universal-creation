from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.organ_library import EXECUTABLE_ORGAN_SCHEMA, ExecutableOrganError, ExecutableOrganLibrary


class ExecutableOrganLibraryTests(unittest.TestCase):
    def _request(self, target: Path, title: str, background: str) -> dict:
        return {
            "kind": "organ-static-web-project",
            "direction": "reuse installed executable organs with a caller-selected perspective",
            "inputs": {
                "path": str(target),
                "assembly": {
                    "id": "axm.test.reusable-site",
                    "version": "1.0.0",
                    "project_type": "static-web",
                    "organs": [
                        {
                            "instance_id": "interaction",
                            "ref": "axm.web.interaction@1.0.0",
                            "depends_on": ["theme"],
                            "bindings": {"active_label": "Awake", "state": "awake"},
                        },
                        {
                            "instance_id": "theme",
                            "ref": "axm.web.theme@1.0.0",
                            "depends_on": ["shell"],
                            "bindings": {"background": background},
                        },
                        {
                            "instance_id": "shell",
                            "ref": "axm.web.shell@1.0.0",
                            "bindings": {"idle_label": "Wake", "title": title},
                        },
                    ],
                },
                "variables": {},
            },
        }

    def test_library_lists_only_installed_executable_packages(self):
        library = ExecutableOrganLibrary(ROOT)
        summary = library.summary()
        self.assertEqual(summary["truth_status"], "EXACT_LOCAL_EXECUTABLE_ORGAN_PACKAGES")
        self.assertEqual(summary["schema"], EXECUTABLE_ORGAN_SCHEMA)
        self.assertEqual(summary["packages"], 3)
        self.assertFalse(summary["descriptive_anatomy_organs_automatically_executable"])

        rows = library.list(project_type="static-web", provides="visual-theme")
        self.assertEqual([row["ref"] for row in rows], ["axm.web.theme@1.0.0"])
        self.assertNotIn("files", rows[0])
        inspected = library.inspect("axm.web.theme@1.0.0")
        self.assertIn("style.css", inspected["files"])
        self.assertEqual(inspected["source_path"], "executable-organs/axm.web.theme-1.0.0.json")
        master = {
            row["id"]
            for row in json.loads(
                (ROOT / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json").read_text(encoding="utf-8")
            )["records"]
        }
        self.assertTrue(all(
            anatomy_id in master
            for ref in summary["package_refs"]
            for anatomy_id in library.inspect(ref)["anatomy_refs"]
        ))

    def test_package_schema_rejects_unknown_fields(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            folder = root / "executable-organs"
            folder.mkdir()
            package = json.loads(
                (ROOT / "executable-organs/axm.web.theme-1.0.0.json").read_text(encoding="utf-8")
            )
            package["hidden_magic"] = True
            (folder / "bad.json").write_text(json.dumps(package), encoding="utf-8")
            with self.assertRaises(ExecutableOrganError) as raised:
                ExecutableOrganLibrary(root)
            self.assertEqual(raised.exception.details["unexpected_fields"], ["hidden_magic"])

    def test_machine_exposes_package_summary_and_complete_exact_inspection(self):
        machine = UniversalCreationMachine(ROOT)
        self.assertEqual(machine.inspect()["executable_organs"]["packages"], 3)
        listed = machine.create({
            "kind": "list-executable-organs",
            "inputs": {"project_type": "static-web"},
        })
        self.assertEqual(listed["type"], "CREATION_RESULT", listed)
        self.assertEqual(len(listed["result"]["packages"]), 3)

        inspected = machine.create({
            "kind": "resolve-executable-organ",
            "inputs": {"ref": "axm.web.shell@1.0.0"},
        })
        self.assertEqual(inspected["type"], "CREATION_RESULT", inspected)
        self.assertIn("index.html", inspected["result"]["package"]["files"])

    def test_same_installed_organs_create_distinct_bodies_from_distinct_bindings(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            machine = UniversalCreationMachine(ROOT)
            first = machine.create(self._request(parent / "first", "First Perspective", "#111122"))
            second = machine.create(self._request(parent / "second", "Second Perspective", "#224411"))
            self.assertEqual(first["type"], "CREATION_RESULT", first)
            self.assertEqual(second["type"], "CREATION_RESULT", second)
            self.assertEqual(first["result"]["creation_status"], "VALIDATED_CREATION")
            self.assertEqual(second["result"]["creation_status"], "VALIDATED_CREATION")
            self.assertIn("First Perspective", (parent / "first/index.html").read_text(encoding="utf-8"))
            self.assertIn("Second Perspective", (parent / "second/index.html").read_text(encoding="utf-8"))
            self.assertNotEqual(
                (parent / "first/style.css").read_text(encoding="utf-8"),
                (parent / "second/style.css").read_text(encoding="utf-8"),
            )

            resolution = first["result"]["executable_organ_resolution"]
            self.assertEqual(resolution["referenced_package_count"], 3)
            self.assertFalse(resolution["descriptive_anatomy_organs_promoted"])
            self.assertFalse(resolution["automatic_or_fuzzy_selection"])
            self.assertEqual(
                first["result"]["organ_assembly"]["dependency_order"],
                ["shell", "theme", "interaction"],
            )
            self.assertEqual(first["result"]["organ_assembly"]["assembly_variables_used"], [])
            self.assertTrue(all(
                row["variable_scope"] == "organ-bindings"
                for row in first["result"]["organ_assembly"]["organs"]
            ))

    def test_references_reject_missing_packages_binding_drift_and_source_override(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            machine = UniversalCreationMachine(ROOT)
            missing = self._request(parent / "missing", "Missing", "#000")
            missing["inputs"]["assembly"]["organs"][0]["ref"] = "axm.web.missing@1.0.0"
            result = machine.create(missing)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["requested_ref"], "axm.web.missing@1.0.0")

            drift = self._request(parent / "drift", "Drift", "#000")
            del drift["inputs"]["assembly"]["organs"][2]["bindings"]["title"]
            result = machine.create(drift)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["missing_parameters"], ["title"])

            wrong_type = self._request(parent / "wrong-type", "Wrong", "#000")
            wrong_type["inputs"]["assembly"]["organs"][2]["bindings"]["title"] = 7
            result = machine.create(wrong_type)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["non_text_bindings"], ["title"])

            override = self._request(parent / "override", "Override", "#000")
            override["inputs"]["assembly"]["organs"][2]["files"] = {"index.html": "silently replaced"}
            result = machine.create(override)
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertEqual(result["details"]["unexpected_fields"], ["files"])
            self.assertFalse((parent / "missing").exists())
            self.assertFalse((parent / "drift").exists())
            self.assertFalse((parent / "wrong-type").exists())
            self.assertFalse((parent / "override").exists())

    def test_referenced_organ_trial_reverifies_exact_creation_digests(self):
        with tempfile.TemporaryDirectory() as td:
            result = UniversalCreationMachine(ROOT).trial(
                self._request(Path(td) / "trial", "Trial Perspective", "#101020")
            )
            self.assertTrue(result["passed"], result)
            checks = result["verification"]["result"]["checks"]
            digest_check = next(row for row in checks if row["type"] == "expected-file-digests")
            self.assertTrue(digest_check["passed"])
            self.assertEqual(len(digest_check["files"]), 3)


if __name__ == "__main__":
    unittest.main()

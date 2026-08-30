from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class ProjectRepairTests(unittest.TestCase):
    def _create(self, target: Path, files: dict[str, str], project_type: str = "generic") -> UniversalCreationMachine:
        machine = UniversalCreationMachine(ROOT)
        result = machine.create({
            "kind": "software-project",
            "inputs": {
                "path": str(target),
                "project_type": project_type,
                "files": files,
            },
        })
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        return machine

    def test_patch_applies_only_explicit_file_operations_and_preserves_untouched_files(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "project"
            machine = self._create(target, {
                "keep.txt": "keep\n",
                "update.txt": "before\n",
                "delete.txt": "delete me\n",
                "rename.txt": "rename me\n",
                "script.js": "console.log('kept');\n",
            })
            result = machine.create({
                "kind": "patch-project",
                "inputs": {
                    "path": str(target),
                    "operations": [
                        {"op": "update", "path": "update.txt", "content": "after\n"},
                        {"op": "add", "path": "added.md", "content": "# added\n"},
                        {"op": "delete", "path": "delete.txt"},
                        {"op": "rename", "from": "rename.txt", "to": "renamed.txt"},
                    ],
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            repair = result["result"]
            self.assertEqual(repair["truth_status"], "OBSERVED_TRANSACTIONAL_PROJECT_REPAIR")
            self.assertTrue(repair["published"])
            self.assertEqual((target / "keep.txt").read_text(encoding="utf-8"), "keep\n")
            self.assertEqual((target / "update.txt").read_text(encoding="utf-8"), "after\n")
            self.assertEqual((target / "added.md").read_text(encoding="utf-8"), "# added\n")
            self.assertFalse((target / "delete.txt").exists())
            self.assertFalse((target / "rename.txt").exists())
            self.assertEqual((target / "renamed.txt").read_text(encoding="utf-8"), "rename me\n")
            self.assertEqual(repair["expected_files"], {"update.txt": "after\n", "added.md": "# added\n"})
            inventory = repair["grammar_inventory"]
            self.assertEqual(inventory["truth_status"], "OBSERVED_EXTENSION_GRAMMAR_INVENTORY")
            js = next(row for row in inventory["files"] if row["path"] == "script.js")
            self.assertEqual(js["grammar_id"], "javascript")
            self.assertEqual(js["validation"], "identified-not-parser-validated")

    def test_invalid_static_web_repair_never_replaces_original(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "site"
            original = "<!doctype html><html><body><main>before</main></body></html>"
            machine = self._create(target, {"index.html": original}, project_type="static-web")
            result = machine.create({
                "kind": "patch-static-web-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "operations": [
                        {"op": "update", "path": "index.html", "content": "<link rel=\"stylesheet\" href=\"missing.css\"><main>after</main>"}
                    ],
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertTrue(result["details"]["original_unchanged"])
            self.assertEqual((target / "index.html").read_text(encoding="utf-8"), original)

    def test_invalid_python_repair_is_blocked_by_existing_parser_validation(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "python-project"
            original = "def answer():\n    return 42\n"
            machine = self._create(target, {"app.py": original}, project_type="python")
            result = machine.create({
                "kind": "patch-python-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "python",
                    "operations": [
                        {"op": "update", "path": "app.py", "content": "def broken(:\n    pass\n"}
                    ],
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual(result["details"]["phase"], "pre-publish")
            self.assertEqual((target / "app.py").read_text(encoding="utf-8"), original)

    def test_unsafe_repair_path_is_rejected_before_original_changes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "project"
            machine = self._create(target, {"safe.txt": "safe\n"})
            result = machine.create({
                "kind": "patch-project",
                "inputs": {
                    "path": str(target),
                    "operations": [{"op": "update", "path": "../escape.txt", "content": "no\n"}],
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual((target / "safe.txt").read_text(encoding="utf-8"), "safe\n")
            self.assertFalse((Path(td) / "escape.txt").exists())

    def test_machine_body_cannot_be_repaired_as_normal_creation(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "patch-project",
            "inputs": {
                "path": str(ROOT),
                "operations": [{"op": "update", "path": "README.md", "content": "blocked\n"}],
            },
        })
        self.assertEqual(result["type"], "CREATION_ERROR", result)
        self.assertIn("machine body", result["message"])

    def test_verified_repair_is_a_live_manifest_only_composite(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "site"
            before = "<!doctype html><html><body><main>before</main></body></html>"
            after = "<!doctype html><html><body><main>after</main></body></html>"
            machine = self._create(target, {"index.html": before}, project_type="static-web")
            result = machine.create({
                "kind": "verified-static-web-repair",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "operations": [{"op": "update", "path": "index.html", "content": after}],
                    "checks": [{"type": "contains", "path": "index.html", "text": "<main>after</main>"}],
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-VERIFIED-PROJECT-REPAIR")
            self.assertTrue(result["result"]["repair"]["published"])
            self.assertTrue(result["result"]["verification"]["passed"])
            self.assertEqual((target / "index.html").read_text(encoding="utf-8"), after)
            manifest = machine.capabilities.by_id("AXM-CAP-VERIFIED-PROJECT-REPAIR")
            self.assertEqual(manifest["implementation"]["kind"], "DETERMINISTIC_COMPOSITE")
            self.assertEqual(manifest["implementation"]["source"], "this manifest")


if __name__ == "__main__":
    unittest.main()

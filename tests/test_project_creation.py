from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.project import ProjectError, build_project


class ProjectCreationTests(unittest.TestCase):
    def test_static_web_project_is_built_and_reverified(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "site"
            machine = UniversalCreationMachine(ROOT)
            request = {
                "kind": "static-web-project",
                "direction": "create a small local interactive website",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<!doctype html><html><head><link rel=\"stylesheet\" href=\"style.css\"></head><body><main>AXM</main><script src=\"app.js\"></script></body></html>",
                        "style.css": "body { font-family: system-ui; }\n",
                        "app.js": "document.querySelector('main').dataset.ready = 'yes';\n",
                    },
                    "checks": [
                        {"type": "contains", "path": "index.html", "text": "<main>AXM</main>"},
                        {"type": "nonempty", "path": "app.js"},
                    ],
                },
            }
            result = machine.create(request)
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertTrue(result["result"]["validation"]["passed"])
            self.assertTrue((target / "index.html").is_file())
            self.assertTrue((target / "style.css").is_file())
            self.assertTrue((target / "app.js").is_file())
            self.assertTrue(any(x["type"] == "expected-files-exact" for x in result["result"]["validation"]["checks"]))

            verify = machine.create({
                "kind": "verify-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "checks": request["inputs"]["checks"],
                    "expected_files": request["inputs"]["files"],
                },
            })
            self.assertEqual(verify["type"], "CREATION_RESULT")
            self.assertTrue(verify["result"]["passed"])

    def test_broken_local_web_reference_blocks_publish(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "broken-site"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "static-web-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<html><head><link rel=\"stylesheet\" href=\"missing.css\"></head><body></body></html>"
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertFalse(result["details"]["validation"]["passed"])
            self.assertFalse(target.exists())

    def test_broken_local_reference_on_nested_html_page_blocks_publish(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "broken-multi-page-site"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "static-web-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<a href=\"pages/about.html\">About</a>",
                        "pages/about.html": "<script src=\"missing.js\"></script>",
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            validation = result["details"]["validation"]
            self.assertFalse(validation["passed"])
            nested = next(
                row
                for row in validation["checks"]
                if row["type"] == "html-local-links" and row.get("path") == "pages/about.html"
            )
            self.assertFalse(nested["passed"])
            self.assertEqual(nested["unresolved"][0]["reference"], "missing.js")
            self.assertFalse(target.exists())

    def test_nested_html_reference_resolves_relative_to_that_page(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "valid-multi-page-site"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "static-web-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<a href=\"pages/about.htm\">About</a>",
                        "pages/about.htm": "<script src=\"../app.js\"></script>",
                        "app.js": "document.body.dataset.ready = 'yes';\n",
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            html_checks = {
                row["path"]: row
                for row in result["result"]["validation"]["checks"]
                if row["type"] == "html-local-links"
            }
            self.assertEqual(set(html_checks), {"index.html", "pages/about.htm"})
            self.assertTrue(html_checks["pages/about.htm"]["passed"])
            self.assertEqual(html_checks["pages/about.htm"]["local_references"][0]["resolved"], "app.js")

    def test_project_file_cannot_escape_project_root(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "project"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "software-project",
                "inputs": {
                    "path": str(target),
                    "files": {"../escape.txt": "nope"},
                },
            })
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertIn("stay inside the project", result["message"])
            self.assertFalse(target.exists())

    def test_python_project_is_compiled_without_execution(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "python-project"
            request = {
                "kind": "python-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "python",
                    "files": {
                        "app.py": "def answer():\n    return 42\n",
                        "README.md": "# tiny project\n",
                    },
                },
            }
            result = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertTrue(result["result"]["validation"]["passed"])
            compile_checks = [x for x in result["result"]["validation"]["checks"] if x["type"] == "python-compile"]
            self.assertEqual(len(compile_checks), 1)
            self.assertTrue(compile_checks[0]["passed"])

    def test_generic_project_never_passes_with_zero_checks(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "generic"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "software-project",
                "inputs": {"path": str(target), "files": {"note.txt": "hello"}},
            })
            self.assertEqual(result["type"], "CREATION_RESULT")
            checks = result["result"]["validation"]["checks"]
            self.assertTrue(any(row["type"] == "project-nonempty" for row in checks))
            self.assertTrue(any(row["type"] == "expected-files-exact" for row in checks))

    def test_expected_file_verification_detects_later_change(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "generic"
            machine = UniversalCreationMachine(ROOT)
            created = machine.create({
                "kind": "software-project",
                "inputs": {"path": str(target), "files": {"note.txt": "original"}},
            })
            self.assertEqual(created["type"], "CREATION_RESULT")
            (target / "note.txt").write_text("changed", encoding="utf-8")
            verify = machine.create({
                "kind": "verify-project",
                "inputs": {"path": str(target), "expected_files": {"note.txt": "original"}},
            })
            self.assertEqual(verify["type"], "CREATION_RESULT")
            self.assertFalse(verify["result"]["passed"])
            exact = next(row for row in verify["result"]["checks"] if row["type"] == "expected-files-exact")
            self.assertFalse(exact["passed"])

    def test_failed_post_publish_validation_restores_previous_project(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "replace-me"
            target.mkdir()
            (target / "old.txt").write_text("old", encoding="utf-8")
            good = {"passed": True, "checks": [], "files": [], "limitations": []}
            bad = {"passed": False, "checks": [{"type": "forced", "passed": False}], "files": [], "limitations": []}
            with patch("axm_uc.project.validate_project", side_effect=[good, bad]):
                with self.assertRaises(ProjectError):
                    build_project(target, {"new.txt": "new"}, replace=True)
            self.assertTrue((target / "old.txt").is_file())
            self.assertEqual((target / "old.txt").read_text(encoding="utf-8"), "old")
            self.assertFalse((target / "new.txt").exists())

    def test_trial_returns_plan_create_verify_in_one_result(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "trial-site"
            result = UniversalCreationMachine(ROOT).trial({
                "kind": "static-web-project",
                "direction": "create a local landing page with a button",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<!doctype html><html><body><button id=\"go\">Go</button><script src=\"app.js\"></script></body></html>",
                        "app.js": "document.querySelector('#go').addEventListener('click', () => document.body.dataset.clicked = 'yes');\n",
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_TRIAL")
            self.assertTrue(result["passed"])
            self.assertEqual(result["creation"]["type"], "CREATION_RESULT")
            self.assertEqual(result["verification"]["type"], "CREATION_RESULT")
            self.assertEqual(result["truth_status"], "OBSERVED_DETERMINISTIC_PROJECT_VALIDATION")
            self.assertEqual(result["plan"]["type"], "CREATION_DECOMPOSITION")


if __name__ == "__main__":
    unittest.main()

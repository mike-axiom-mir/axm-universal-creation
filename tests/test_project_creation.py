from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from axm_uc.machine import UniversalCreationMachine


ROOT = Path(__file__).resolve().parents[1]


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

            verify = machine.create({
                "kind": "verify-project",
                "inputs": {
                    "path": str(target),
                    "project_type": "static-web",
                    "checks": request["inputs"]["checks"],
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

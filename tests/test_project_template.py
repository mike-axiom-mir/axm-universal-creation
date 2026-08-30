from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class ProjectTemplateTests(unittest.TestCase):
    def _create(self, target: Path, template: dict, variables: dict, **extra):
        inputs = {"path": str(target), "template": template, "variables": variables, **extra}
        return UniversalCreationMachine(ROOT).create({
            "kind": "templated-static-web-project",
            "direction": "instantiate a reusable local software perspective",
            "inputs": inputs,
        })

    def test_template_instantiates_paths_and_contents_once(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "templated-site"
            result = self._create(
                target,
                {
                    "id": "axm.example.local-site",
                    "version": "1.0.0",
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<main>[[AXM:title]]</main><script src=\"[[AXM:script]]\"></script>",
                        "[[AXM:script]]": "document.body.dataset.message = '[[AXM:message]]';\n",
                        "data.json": "{\"theme\": \"[[AXM:theme]]\"}\n",
                    },
                },
                {"title": "Creation", "script": "app.js", "message": "free", "theme": "violet"},
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            creation = result["result"]
            self.assertEqual(creation["creation_status"], "VALIDATED_CREATION")
            self.assertEqual(creation["template_instance"]["template_id"], "axm.example.local-site")
            self.assertFalse(creation["template_instance"]["recursive_expansion"])
            self.assertEqual((target / "app.js").read_text(encoding="utf-8"), "document.body.dataset.message = 'free';\n")
            self.assertEqual(creation["template_instance"]["variables_used"], ["message", "script", "theme", "title"])

    def test_imperfect_template_result_survives_as_grounded_draft(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "draft-site"
            result = self._create(
                target,
                {
                    "id": "axm.example.draft",
                    "version": "1.0.0",
                    "project_type": "static-web",
                    "files": {"index.html": "<script src=\"[[AXM:missing_path]]\"></script>"},
                },
                {"missing_path": "not-built-yet.js"},
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["result"]["creation_status"], "GROUNDED_DRAFT")
            self.assertTrue((target / "index.html").is_file())
            self.assertEqual(result["result"]["grounding"]["observed_gap_count"], 1)

    def test_template_requires_every_variable_and_rejects_unused_values(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "missing-variable"
            template = {
                "id": "axm.example.variables",
                "version": "1.0.0",
                "project_type": "static-web",
                "files": {"index.html": "<main>[[AXM:title]]</main>"},
            }
            missing = self._create(target, template, {})
            self.assertEqual(missing["type"], "CREATION_ERROR")
            self.assertEqual(missing["details"]["missing_variables"], ["title"])
            unused = self._create(target, template, {"title": "yes", "extra": "no"})
            self.assertEqual(unused["type"], "CREATION_ERROR")
            self.assertEqual(unused["details"]["unused_variables"], ["extra"])
            self.assertFalse(target.exists())

    def test_rendered_path_collision_and_escape_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "unsafe-template"
            collision = self._create(
                target,
                {
                    "id": "axm.example.collision",
                    "version": "1.0.0",
                    "project_type": "generic",
                    "files": {"[[AXM:first]]": "one", "[[AXM:second]]": "two"},
                },
                {"first": "same.txt", "second": "same.txt"},
            )
            self.assertEqual(collision["type"], "CREATION_ERROR")
            self.assertEqual(collision["details"]["rendered_path"], "same.txt")

            escape = self._create(
                target,
                {
                    "id": "axm.example.escape",
                    "version": "1.0.0",
                    "project_type": "generic",
                    "files": {"[[AXM:path]]": "no"},
                },
                {"path": "../escape.txt"},
            )
            self.assertEqual(escape["type"], "CREATION_ERROR")
            self.assertIn("stay inside", escape["message"])
            self.assertFalse((Path(td) / "escape.txt").exists())

    def test_template_substitution_is_non_recursive(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "single-pass"
            result = self._create(
                target,
                {
                    "id": "axm.example.single-pass",
                    "version": "1.0.0",
                    "project_type": "generic",
                    "files": {"note.txt": "[[AXM:value]]"},
                },
                {"value": "[[AXM:not-expanded]]"},
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual((target / "note.txt").read_text(encoding="utf-8"), "[[AXM:not-expanded]]")

    def test_malformed_reserved_placeholder_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "malformed"
            result = self._create(
                target,
                {
                    "id": "axm.example.malformed",
                    "version": "1.0.0",
                    "project_type": "generic",
                    "files": {"note.txt": "[[AXM:broken placeholder]]"},
                },
                {},
            )
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertIn("malformed", result["message"])

    def test_machine_can_create_inspectable_candidate_source_for_itself(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "next-body-candidate"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "self-candidate-project",
                "direction": "create an inspectable candidate organ for the next machine body",
                "inputs": {
                    "path": str(target),
                    "template": {
                        "id": "axm.self-candidate.python-organ",
                        "version": "1.0.0",
                        "project_type": "python",
                        "files": {
                            "src/[[AXM:module_name]].py": "def describe():\n    return '[[AXM:purpose]]'\n",
                            "candidate.json": "{\"id\": \"[[AXM:candidate_id]]\", \"status\": \"candidate\"}\n",
                        },
                    },
                    "variables": {
                        "module_name": "new_organ",
                        "purpose": "candidate creation organ",
                        "candidate_id": "AXM-CANDIDATE-CREATION-ORGAN",
                    },
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE")
            self.assertEqual(result["result"]["creation_status"], "VALIDATED_CREATION")
            self.assertTrue((target / "src/new_organ.py").is_file())
            self.assertTrue((target / "candidate.json").is_file())
            compile_check = next(
                row for row in result["result"]["validation"]["checks"] if row["type"] == "python-compile"
            )
            self.assertTrue(compile_check["passed"])


if __name__ == "__main__":
    unittest.main()

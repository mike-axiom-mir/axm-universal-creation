from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class OrganProjectTests(unittest.TestCase):
    def _create(self, target: Path, assembly: dict, variables: dict, **extra):
        return UniversalCreationMachine(ROOT).create({
            "kind": "software-organ-assembly",
            "direction": "assemble an inspectable software body from reusable organs",
            "inputs": {
                "path": str(target),
                "assembly": assembly,
                "variables": variables,
                **extra,
            },
        })

    def test_organs_resolve_dependencies_and_own_disjoint_files(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "organ-site"
            result = self._create(
                target,
                {
                    "id": "axm.example.organ-site",
                    "version": "1.0.0",
                    "project_type": "static-web",
                    "organs": [
                        {
                            "id": "interaction-organ",
                            "version": "1.0.0",
                            "purpose": "local interaction",
                            "depends_on": ["theme-organ"],
                            "provides": ["local-interaction"],
                            "requires": ["document-shell", "visual-theme"],
                            "files": {"app.js": "document.body.dataset.message = '[[AXM:message]]';\n"},
                        },
                        {
                            "id": "theme-organ",
                            "version": "1.0.0",
                            "depends_on": ["shell-organ"],
                            "provides": ["visual-theme"],
                            "requires": ["document-shell"],
                            "files": {"style.css": "body { color: [[AXM:accent]]; }\n"},
                        },
                        {
                            "id": "shell-organ",
                            "version": "1.0.0",
                            "provides": ["document-shell"],
                            "files": {
                                "index.html": "<main>[[AXM:title]]</main><link rel=\"stylesheet\" href=\"style.css\"><script src=\"app.js\"></script>"
                            },
                        },
                    ],
                },
                {"title": "Organ Creation", "accent": "violet", "message": "alive"},
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            creation = result["result"]
            self.assertEqual(creation["creation_status"], "VALIDATED_CREATION")
            receipt = creation["organ_assembly"]
            self.assertEqual(receipt["dependency_order"], ["shell-organ", "theme-organ", "interaction-organ"])
            self.assertEqual(receipt["declared_organ_count"], 3)
            self.assertTrue(receipt["declared_interface_contracts_verified"])
            self.assertFalse(receipt["source_interface_conformance_verified"])
            providers = {row["interface"]: row["organ_id"] for row in receipt["interface_providers"]}
            self.assertEqual(providers, {
                "document-shell": "shell-organ",
                "local-interaction": "interaction-organ",
                "visual-theme": "theme-organ",
            })
            self.assertEqual(receipt["variables_used"], ["accent", "message", "title"])
            owners = {row["path"]: row["organ_id"] for row in receipt["file_ownership"]}
            self.assertEqual(owners, {
                "app.js": "interaction-organ",
                "index.html": "shell-organ",
                "style.css": "theme-organ",
            })
            self.assertEqual((target / "app.js").read_text(encoding="utf-8"), "document.body.dataset.message = 'alive';\n")

    def test_simultaneously_ready_organs_preserve_declared_order(self):
        with tempfile.TemporaryDirectory() as td:
            result = self._create(
                Path(td) / "stable-order",
                {
                    "id": "stable-order",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [
                        {"id": "second-named", "version": "1", "files": {"second.txt": "second"}},
                        {"id": "first-named", "version": "1", "files": {"first.txt": "first"}},
                        {
                            "id": "dependent",
                            "version": "1",
                            "depends_on": ["first-named", "second-named"],
                            "files": {"dependent.txt": "dependent"},
                        },
                    ],
                },
                {},
            )
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(
                result["result"]["organ_assembly"]["dependency_order"],
                ["second-named", "first-named", "dependent"],
            )

    def test_missing_dependency_and_cycle_are_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            missing = self._create(
                parent / "missing",
                {
                    "id": "missing-dependency",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [{
                        "id": "ui-organ",
                        "version": "1",
                        "depends_on": ["state-organ"],
                        "files": {"ui.txt": "ui"},
                    }],
                },
                {},
            )
            self.assertEqual(missing["type"], "CREATION_ERROR")
            self.assertEqual(missing["details"]["missing_dependencies"], ["state-organ"])

            cycle = self._create(
                parent / "cycle",
                {
                    "id": "cycle",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [
                        {"id": "a", "version": "1", "depends_on": ["b"], "files": {"a.txt": "a"}},
                        {"id": "b", "version": "1", "depends_on": ["a"], "files": {"b.txt": "b"}},
                    ],
                },
                {},
            )
            self.assertEqual(cycle["type"], "CREATION_ERROR")
            self.assertEqual(cycle["details"]["cycle_candidates"], ["a", "b"])
            self.assertFalse((parent / "missing").exists())
            self.assertFalse((parent / "cycle").exists())

    def test_rendered_file_ownership_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "collision"
            result = self._create(
                target,
                {
                    "id": "collision",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [
                        {"id": "one", "version": "1", "files": {"[[AXM:path]]": "one"}},
                        {"id": "two", "version": "1", "files": {"shared.txt": "two"}},
                    ],
                },
                {"path": "shared.txt"},
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual(result["details"]["rendered_path"], "shared.txt")
            self.assertEqual(result["details"]["first_organ"], "one")
            self.assertEqual(result["details"]["second_organ"], "two")
            self.assertFalse(target.exists())

    def test_declared_interfaces_need_reachable_unambiguous_providers(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            missing = self._create(
                parent / "missing-interface",
                {
                    "id": "missing-interface",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [{
                        "id": "ui-organ",
                        "version": "1",
                        "requires": ["state-model"],
                        "files": {"ui.txt": "ui"},
                    }],
                },
                {},
            )
            self.assertEqual(missing["type"], "CREATION_ERROR")
            self.assertEqual(missing["details"]["missing_interfaces"], ["state-model"])

            unreachable = self._create(
                parent / "unreachable-interface",
                {
                    "id": "unreachable-interface",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [
                        {"id": "state-organ", "version": "1", "provides": ["state-model"], "files": {"state.txt": "state"}},
                        {"id": "ui-organ", "version": "1", "requires": ["state-model"], "files": {"ui.txt": "ui"}},
                    ],
                },
                {},
            )
            self.assertEqual(unreachable["type"], "CREATION_ERROR")
            detail = unreachable["details"]["unreachable_interfaces"][0]
            self.assertEqual(detail["organ_id"], "ui-organ")
            self.assertEqual(detail["provider"], "state-organ")

            duplicate = self._create(
                parent / "duplicate-interface",
                {
                    "id": "duplicate-interface",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [
                        {"id": "state-a", "version": "1", "provides": ["state-model"], "files": {"a.txt": "a"}},
                        {"id": "state-b", "version": "1", "provides": ["state-model"], "files": {"b.txt": "b"}},
                    ],
                },
                {},
            )
            self.assertEqual(duplicate["type"], "CREATION_ERROR")
            self.assertEqual(duplicate["details"]["interface"], "state-model")
            self.assertEqual(duplicate["details"]["first_organ"], "state-a")
            self.assertEqual(duplicate["details"]["second_organ"], "state-b")
            self.assertFalse((parent / "missing-interface").exists())
            self.assertFalse((parent / "unreachable-interface").exists())
            self.assertFalse((parent / "duplicate-interface").exists())

    def test_shared_variables_must_be_used_somewhere_in_the_assembly(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "unused"
            result = self._create(
                target,
                {
                    "id": "unused",
                    "version": "1",
                    "project_type": "generic",
                    "organs": [{"id": "body", "version": "1", "files": {"body.txt": "[[AXM:used]]"}}],
                },
                {"used": "yes", "unused": "no"},
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertEqual(result["details"]["unused_variables"], ["unused"])
            self.assertFalse(target.exists())

    def test_imperfect_organ_body_can_remain_grounded_or_be_explicitly_strict(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            assembly = {
                "id": "imperfect-data",
                "version": "1",
                "project_type": "generic",
                "organs": [{"id": "data-organ", "version": "1", "files": {"data.json": "{not-json}"}}],
            }
            draft = self._create(parent / "draft", assembly, {})
            self.assertEqual(draft["type"], "CREATION_RESULT", draft)
            self.assertEqual(draft["result"]["creation_status"], "GROUNDED_DRAFT")
            self.assertTrue((parent / "draft/data.json").is_file())

            strict = self._create(parent / "strict", assembly, {}, publish_mode="validated")
            self.assertEqual(strict["type"], "CREATION_ERROR", strict)
            self.assertFalse((parent / "strict").exists())


if __name__ == "__main__":
    unittest.main()

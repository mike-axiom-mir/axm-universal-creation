from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class CreationBoundaryTests(unittest.TestCase):
    def test_root_machine_file_cannot_be_overwritten_by_normal_creation(self):
        machine = UniversalCreationMachine(ROOT)
        readme = ROOT / "README.md"
        before = readme.read_text(encoding="utf-8")
        result = machine.create({
            "kind": "text-file",
            "inputs": {"path": str(readme), "content": "overwrite"},
        })
        self.assertEqual(result["type"], "CREATION_ERROR")
        self.assertIn("machine body", result["message"])
        self.assertEqual(readme.read_text(encoding="utf-8"), before)

    def test_creations_directory_remains_an_allowed_repo_local_output_surface(self):
        machine = UniversalCreationMachine(ROOT)
        target = ROOT / "creations" / "boundary-test.txt"
        try:
            result = machine.create({
                "kind": "text-file",
                "inputs": {"path": str(target), "content": "allowed\n"},
            })
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(target.read_text(encoding="utf-8"), "allowed\n")
        finally:
            if target.exists():
                target.unlink()

    def test_output_outside_repo_is_still_allowed(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "outside.txt"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "text-file",
                "inputs": {"path": str(target), "content": "outside\n"},
            })
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(target.read_text(encoding="utf-8"), "outside\n")


if __name__ == "__main__":
    unittest.main()

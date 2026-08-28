from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class MachineTests(unittest.TestCase):
    def test_live_creation_routes_and_writes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "hello.txt"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "text-file",
                "direction": "create exact text",
                "inputs": {"path": str(target), "content": "hello\n"},
            })
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello\n")

    def test_unsatisfied_request_emits_structured_directional_gap(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "markdown-file",
            "direction": "create editable Markdown",
            "inputs": {"path": "creations/x.md", "content": "# x"},
        })
        self.assertEqual(result["type"], "CAPABILITY_GAP")
        self.assertEqual(result["directional_outcome"], "create editable Markdown")
        self.assertEqual(result["truth_status"], "HYPOTHESIS")
        self.assertTrue(result["existing_partial_coverage"])

    def test_candidate_can_be_tested_and_build_debris_is_cleaned(self):
        candidate = ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json"
        result = UniversalCreationMachine(ROOT).test_candidate(candidate)
        self.assertTrue(result["passed"])
        self.assertTrue(result["build_debris_cleaned"])
        self.assertFalse((ROOT / ".axm-build").exists())


if __name__ == "__main__":
    unittest.main()

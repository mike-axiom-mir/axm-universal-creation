from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class CandidateAdoptionTests(unittest.TestCase):
    def _mini_machine(self, td: str) -> Path:
        root = Path(td)
        (root / "capabilities/live").mkdir(parents=True)
        (root / "capabilities/candidates").mkdir(parents=True)
        (root / "state").mkdir()
        (root / "creations").mkdir()
        (root / "reference/AXM_Universal_Creation_Map_v0.1/registry").mkdir(parents=True)
        (root / "machine.contract.json").write_text('{"roots":["truth","agency","continuity","wisdom-before-speed"]}', encoding="utf-8")
        (root / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json").write_text('{"records":[]}', encoding="utf-8")
        (root / "reference/AXM_Universal_Creation_Map_v0.1/registry/core_build_seed.json").write_text('{"records":[]}', encoding="utf-8")
        base = json.loads((ROOT / "capabilities/live/AXM-CAP-WRITE-TEXT.json").read_text(encoding="utf-8"))
        (root / "capabilities/live/AXM-CAP-WRITE-TEXT.json").write_text(json.dumps(base), encoding="utf-8")
        candidate = json.loads((ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").read_text(encoding="utf-8"))
        (root / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").write_text(json.dumps(candidate), encoding="utf-8")
        return root

    def test_adoption_is_direct_and_consumes_internal_candidate(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._mini_machine(td)
            candidate = root / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json"
            machine = UniversalCreationMachine(root)
            result = machine.adopt_candidate(candidate)
            self.assertTrue(result["adopted"])
            self.assertFalse(candidate.exists())
            self.assertTrue((root / "capabilities/live/AXM-CAP-WRITE-MARKDOWN.json").exists())
            output = root / "creations" / "made.md"
            routed = machine.create({"kind": "markdown-file", "inputs": {"path": str(output), "content": "# made\n"}})
            self.assertEqual(routed["type"], "CREATION_RESULT")
            self.assertEqual(output.read_text(encoding="utf-8"), "# made\n")


if __name__ == "__main__":
    unittest.main()

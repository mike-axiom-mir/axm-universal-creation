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
    @staticmethod
    def _root_fit_decision() -> dict:
        return {
            "decision_source": "bounded-test-fixture",
            "decided_by": "tests/test_candidate_adoption.py",
            "evidence_refs": ["candidate test result"],
            "roots": {
                "truth": {"fit": True, "basis": "Candidate evidence and transition remain inspectable."},
                "agency": {"fit": True, "basis": "Adoption is an explicit separate choice."},
                "continuity": {"fit": True, "basis": "Daily recovery is established before mutation."},
                "wisdom-before-speed": {"fit": True, "basis": "The candidate is tested before adoption."},
            },
        }

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
            result = machine.adopt_candidate(candidate, root_fit=self._root_fit_decision())
            self.assertTrue(result["adopted"])
            self.assertEqual(result["truth_status"], "ADOPTED_LIVE_CAPABILITY_WITH_DAILY_RECOVERY")
            self.assertTrue(result["transition"]["installed"])
            self.assertTrue(result["transition"]["registered"])
            self.assertTrue(result["transition"]["routed"])
            self.assertTrue(Path(result["recovery_snapshot"]["path"]).is_file())
            self.assertFalse(candidate.exists())
            self.assertTrue((root / "capabilities/live/AXM-CAP-WRITE-MARKDOWN.json").exists())
            output = root / "creations" / "made.md"
            routed = machine.create({"kind": "markdown-file", "inputs": {"path": str(output), "content": "# made\n"}})
            self.assertEqual(routed["type"], "CREATION_RESULT")
            self.assertEqual(output.read_text(encoding="utf-8"), "# made\n")

    def test_adoption_without_attributed_current_decision_holds_before_candidate_testing(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._mini_machine(td)
            candidate = root / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json"
            result = UniversalCreationMachine(root).adopt_candidate(candidate)
            self.assertFalse(result["adopted"])
            self.assertEqual(result["truth_status"], "HOLD_CURRENT_ROOT_FIT_DECISION")
            self.assertFalse(result["live_machine_body_modified"])
            self.assertTrue(candidate.is_file())
            self.assertFalse((root / ".axm-build").exists())


if __name__ == "__main__":
    unittest.main()

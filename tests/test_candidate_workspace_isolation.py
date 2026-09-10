from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.candidate import test_capability_candidate


class CandidateWorkspaceIsolationTests(unittest.TestCase):
    def _machine_root(self, temporary_root: Path) -> tuple[Path, Path]:
        machine_root = temporary_root / "machine"
        live_dir = machine_root / "capabilities" / "live"
        candidate_dir = machine_root / "capabilities" / "candidates"
        live_dir.mkdir(parents=True)
        candidate_dir.mkdir(parents=True)
        shutil.copy2(
            ROOT / "capabilities/live/AXM-CAP-WRITE-TEXT.json",
            live_dir / "AXM-CAP-WRITE-TEXT.json",
        )
        candidate_path = candidate_dir / "AXM-CAP-WRITE-MARKDOWN.json"
        shutil.copy2(
            ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json",
            candidate_path,
        )
        return machine_root, candidate_path

    def _foreign_workspace(self, machine_root: Path) -> Path:
        sentinel = machine_root / ".axm-build" / "candidate-other-worker" / "sentinel.txt"
        sentinel.parent.mkdir(parents=True)
        sentinel.write_text("other candidate is still running\n", encoding="utf-8")
        return sentinel

    def test_successful_candidate_test_preserves_foreign_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            machine_root, candidate_path = self._machine_root(Path(td))
            sentinel = self._foreign_workspace(machine_root)

            result = test_capability_candidate(machine_root, candidate_path)

            self.assertTrue(result["passed"])
            self.assertTrue(result["build_debris_cleaned"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "other candidate is still running\n")

    def test_failed_candidate_test_preserves_foreign_workspace(self):
        with tempfile.TemporaryDirectory() as td:
            machine_root, candidate_path = self._machine_root(Path(td))
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            candidate["tests"][0]["expect"]["file_text"] = "deliberate mismatch\n"
            candidate_path.write_text(json.dumps(candidate), encoding="utf-8")
            sentinel = self._foreign_workspace(machine_root)

            result = test_capability_candidate(machine_root, candidate_path)

            self.assertFalse(result["passed"])
            self.assertTrue(result["build_debris_cleaned"])
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "other candidate is still running\n")


if __name__ == "__main__":
    unittest.main()

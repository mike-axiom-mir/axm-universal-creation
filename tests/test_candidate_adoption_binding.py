from __future__ import annotations

import hashlib
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class CandidateAdoptionBindingTests(unittest.TestCase):
    def _candidate_copy(self, temporary_root: Path) -> Path:
        candidate = json.loads(
            (ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").read_text(encoding="utf-8")
        )
        candidate["id"] = "AXM-CAP-ADOPTION-BINDING-PROBE"
        candidate["handles"] = ["markdown-file-adoption-binding-probe"]
        path = temporary_root / "candidate.json"
        path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        return path

    def test_candidate_test_receipts_bind_exact_source_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            candidate_path = self._candidate_copy(Path(td))
            expected_digest = f"sha256:{hashlib.sha256(candidate_path.read_bytes()).hexdigest()}"

            result = UniversalCreationMachine(ROOT).test_candidate(candidate_path)

            self.assertTrue(result["passed"])
            self.assertEqual(result["candidate_source_sha256"], expected_digest)

    def test_adoption_refuses_success_without_source_identity_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            candidate_path = self._candidate_copy(Path(td))
            machine = UniversalCreationMachine(ROOT)
            machine.test_candidate = lambda _path: {"passed": True}  # type: ignore[method-assign]

            with patch("axm_uc.evolution.ensure_daily_recovery_snapshot") as snapshot, patch(
                "axm_uc.machine.atomic_write_json"
            ) as install:
                result = machine.adopt_candidate(candidate_path)

            self.assertFalse(result["adopted"])
            self.assertEqual(result["truth_status"], "HOLD_CANDIDATE_TEST_EVIDENCE_INCOMPLETE")
            snapshot.assert_not_called()
            install.assert_not_called()

    def test_adoption_refuses_candidate_changed_after_successful_test(self):
        with tempfile.TemporaryDirectory() as td:
            candidate_path = self._candidate_copy(Path(td))
            machine = UniversalCreationMachine(ROOT)
            original_test_candidate = machine.test_candidate

            def test_then_mutate(path: Path) -> dict:
                result = original_test_candidate(path)
                self.assertTrue(result["passed"])
                mutated = json.loads(path.read_text(encoding="utf-8"))
                mutated["purpose"] = "MUTATED AFTER SUCCESSFUL TEST"
                path.write_text(json.dumps(mutated, indent=2) + "\n", encoding="utf-8")
                return result

            machine.test_candidate = test_then_mutate  # type: ignore[method-assign]

            with patch("axm_uc.evolution.ensure_daily_recovery_snapshot") as snapshot, patch(
                "axm_uc.machine.atomic_write_json"
            ) as install:
                result = machine.adopt_candidate(candidate_path)

            self.assertFalse(result["adopted"])
            self.assertEqual(result["truth_status"], "HOLD_CANDIDATE_SOURCE_DRIFT")
            self.assertEqual(
                result["expected_candidate_source_sha256"],
                result["test"]["candidate_source_sha256"],
            )
            self.assertNotEqual(
                result["expected_candidate_source_sha256"],
                result["observed_candidate_source_sha256"],
            )
            snapshot.assert_not_called()
            install.assert_not_called()

    def test_adoption_refuses_candidate_removed_after_successful_test(self):
        with tempfile.TemporaryDirectory() as td:
            candidate_path = self._candidate_copy(Path(td))
            machine = UniversalCreationMachine(ROOT)
            original_test_candidate = machine.test_candidate

            def test_then_remove(path: Path) -> dict:
                result = original_test_candidate(path)
                self.assertTrue(result["passed"])
                path.unlink()
                return result

            machine.test_candidate = test_then_remove  # type: ignore[method-assign]

            with patch("axm_uc.evolution.ensure_daily_recovery_snapshot") as snapshot, patch(
                "axm_uc.machine.atomic_write_json"
            ) as install:
                result = machine.adopt_candidate(candidate_path)

            self.assertFalse(result["adopted"])
            self.assertEqual(result["truth_status"], "HOLD_CANDIDATE_SOURCE_UNAVAILABLE_AFTER_TEST")
            self.assertEqual(
                result["expected_candidate_source_sha256"],
                result["test"]["candidate_source_sha256"],
            )
            snapshot.assert_not_called()
            install.assert_not_called()

    def test_unchanged_candidate_installs_exact_tested_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            candidate_path = self._candidate_copy(Path(td))
            expected = json.loads(candidate_path.read_text(encoding="utf-8"))
            machine = UniversalCreationMachine(ROOT)

            with patch(
                "axm_uc.evolution.ensure_daily_recovery_snapshot",
                return_value={"truth_status": "TEST_SNAPSHOT_READY"},
            ), patch("axm_uc.machine.atomic_write_json") as install:
                result = machine.adopt_candidate(candidate_path)

            self.assertTrue(result["adopted"])
            self.assertEqual(result["candidate_source_sha256"], result["test"]["candidate_source_sha256"])
            installed = install.call_args.args[1]
            self.assertEqual(installed["id"], expected["id"])
            self.assertEqual(installed["purpose"], expected["purpose"])
            self.assertEqual(installed["status"], "live")


if __name__ == "__main__":
    unittest.main()

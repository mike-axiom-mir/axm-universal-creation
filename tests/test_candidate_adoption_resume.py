from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.atomic import atomic_write_json as real_atomic_write_json
from axm_uc.machine import UniversalCreationMachine


class CandidateAdoptionResumeTests(unittest.TestCase):
    def _mini_machine(self, td: str) -> tuple[Path, Path]:
        root = Path(td)
        (root / "capabilities/live").mkdir(parents=True)
        candidates = root / "capabilities/candidates"
        candidates.mkdir(parents=True)
        (root / "state").mkdir()
        (root / "creations").mkdir()
        registry = root / "reference/AXM_Universal_Creation_Map_v0.1/registry"
        registry.mkdir(parents=True)
        (root / "machine.contract.json").write_text(
            '{"roots":["truth","agency","continuity","wisdom-before-speed"]}',
            encoding="utf-8",
        )
        (registry / "master_registry.json").write_text('{"records":[]}', encoding="utf-8")
        (registry / "core_build_seed.json").write_text('{"records":[]}', encoding="utf-8")
        base = json.loads((ROOT / "capabilities/live/AXM-CAP-WRITE-TEXT.json").read_text(encoding="utf-8"))
        (root / "capabilities/live/AXM-CAP-WRITE-TEXT.json").write_text(
            json.dumps(base),
            encoding="utf-8",
        )
        candidate = json.loads(
            (ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").read_text(encoding="utf-8")
        )
        candidate["id"] = "AXM-CAP-INTERRUPTED-ADOPTION-PROBE"
        candidate["handles"] = ["interrupted-adoption-probe"]
        candidate_path = candidates / "interrupted.json"
        candidate_path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        return root, candidate_path

    def test_retry_reconstructs_completion_from_exact_live_manifest(self):
        with tempfile.TemporaryDirectory() as td:
            root, candidate_path = self._mini_machine(td)
            machine = UniversalCreationMachine(root)

            def publish_then_interrupt(path: Path, value: object) -> None:
                real_atomic_write_json(path, value)
                raise RuntimeError("injected interruption after live publication")

            with patch(
                "axm_uc.evolution.ensure_daily_recovery_snapshot",
                return_value={"truth_status": "TEST_SNAPSHOT_READY", "path": str(root / "before.zip")},
            ), patch("axm_uc.machine.atomic_write_json", side_effect=publish_then_interrupt):
                with self.assertRaisesRegex(RuntimeError, "injected interruption"):
                    machine.adopt_candidate(candidate_path)

            live = root / "capabilities/live/AXM-CAP-INTERRUPTED-ADOPTION-PROBE.json"
            self.assertTrue(live.is_file(), "the atomic live publication committed before interruption")
            self.assertTrue(candidate_path.is_file(), "cleanup did not complete")

            with patch("axm_uc.evolution.ensure_daily_recovery_snapshot") as snapshot:
                resumed = machine.adopt_candidate(candidate_path)

            self.assertTrue(resumed["adopted"], resumed)
            self.assertEqual(resumed["truth_status"], "RESUMED_COMMITTED_CANDIDATE_ADOPTION")
            self.assertTrue(resumed["transition"]["reconstructed_from_canonical_state"])
            self.assertFalse(resumed["transition"]["installed_now"])
            self.assertFalse(candidate_path.exists())
            snapshot.assert_not_called()

            routed = machine.create({
                "kind": "interrupted-adoption-probe",
                "inputs": {"path": str(root / "creations/resumed.md"), "content": "# resumed\n"},
            })
            self.assertEqual(routed["type"], "CREATION_RESULT")

    def test_retry_keeps_conflicting_live_manifest_and_candidate_untouched(self):
        with tempfile.TemporaryDirectory() as td:
            root, candidate_path = self._mini_machine(td)
            candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
            conflicting = dict(candidate)
            conflicting["status"] = "live"
            conflicting["purpose"] = "different live capability"
            target = root / "capabilities/live/AXM-CAP-INTERRUPTED-ADOPTION-PROBE.json"
            real_atomic_write_json(target, conflicting)
            before = target.read_bytes()

            with patch("axm_uc.evolution.ensure_daily_recovery_snapshot") as snapshot:
                held = UniversalCreationMachine(root).adopt_candidate(candidate_path)

            self.assertFalse(held["adopted"])
            self.assertEqual(held["truth_status"], "HOLD_LIVE_CAPABILITY_ID_COLLISION")
            self.assertEqual(target.read_bytes(), before)
            self.assertTrue(candidate_path.exists())
            snapshot.assert_not_called()


if __name__ == "__main__":
    unittest.main()

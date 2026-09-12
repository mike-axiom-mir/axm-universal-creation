from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


_CHILD = r'''
import json
import sys
import time
from pathlib import Path

root = Path(sys.argv[1])
candidate = Path(sys.argv[2])
ready = Path(sys.argv[3])
release = Path(sys.argv[4])
result_path = Path(sys.argv[5])

from axm_uc.machine import UniversalCreationMachine
import axm_uc.evolution as evolution


def gated_snapshot(machine_root, **_kwargs):
    # Adoption has already passed the live-target collision check when this
    # seam is reached. Hold that exact pre-publication state so a second real
    # process can attempt the same live capability ID deterministically.
    ready.write_text("ready\n", encoding="utf-8")
    deadline = time.monotonic() + 20.0
    while not release.exists():
        if time.monotonic() >= deadline:
            raise RuntimeError("timed out waiting for concurrent adoption release")
        time.sleep(0.01)
    return {"truth_status": "TEST_SNAPSHOT_READY", "path": str(machine_root / "test-snapshot.zip")}


evolution.ensure_daily_recovery_snapshot = gated_snapshot
result = UniversalCreationMachine(root).adopt_candidate(candidate)
result_path.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
'''


class CandidateAdoptionSingleWriterTests(unittest.TestCase):
    def _mini_machine(self, td: str) -> Path:
        root = Path(td)
        (root / "capabilities/live").mkdir(parents=True)
        (root / "capabilities/candidates").mkdir(parents=True)
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
        (root / "capabilities/live/AXM-CAP-WRITE-TEXT.json").write_text(json.dumps(base), encoding="utf-8")
        return root

    def _candidate(self, root: Path, name: str, purpose: str) -> Path:
        candidate = json.loads(
            (ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").read_text(encoding="utf-8")
        )
        candidate["id"] = "AXM-CAP-CONCURRENT-ADOPTION-PROBE"
        candidate["purpose"] = purpose
        candidate["handles"] = ["concurrent-adoption-probe"]
        path = root / "capabilities/candidates" / name
        path.write_text(json.dumps(candidate, indent=2) + "\n", encoding="utf-8")
        return path

    def test_only_one_process_may_cross_candidate_adoption_publication_boundary(self):
        with tempfile.TemporaryDirectory() as td:
            root = self._mini_machine(td)
            first = self._candidate(root, "first.json", "first process candidate")
            second = self._candidate(root, "second.json", "second process candidate")
            ready = root / "first-ready"
            release = root / "release-first"
            child_result_path = root / "first-result.json"

            env = os.environ.copy()
            env["PYTHONPATH"] = str(ROOT / "src")
            child = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    _CHILD,
                    str(root),
                    str(first),
                    str(ready),
                    str(release),
                    str(child_result_path),
                ],
                cwd=ROOT,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )
            try:
                deadline = time.monotonic() + 20.0
                while not ready.exists():
                    if child.poll() is not None:
                        stdout, stderr = child.communicate()
                        self.fail(f"first adoption exited before publication barrier: stdout={stdout!r} stderr={stderr!r}")
                    if time.monotonic() >= deadline:
                        self.fail("first adoption did not reach publication barrier")
                    time.sleep(0.01)

                with patch(
                    "axm_uc.evolution.ensure_daily_recovery_snapshot",
                    return_value={"truth_status": "TEST_SNAPSHOT_READY", "path": str(root / "test-snapshot.zip")},
                ):
                    contender = UniversalCreationMachine(root).adopt_candidate(second)
            finally:
                release.write_text("release\n", encoding="utf-8")

            stdout, stderr = child.communicate(timeout=20)
            self.assertEqual(child.returncode, 0, f"first adoption failed: stdout={stdout!r} stderr={stderr!r}")
            first_result = json.loads(child_result_path.read_text(encoding="utf-8"))

            self.assertTrue(first_result["adopted"], first_result)
            self.assertFalse(contender["adopted"], contender)
            self.assertEqual(contender["truth_status"], "HOLD_CANDIDATE_ADOPTION_BUSY")
            self.assertTrue(second.exists(), "busy contender must remain available for a later explicit retry")

            live = json.loads(
                (root / "capabilities/live/AXM-CAP-CONCURRENT-ADOPTION-PROBE.json").read_text(encoding="utf-8")
            )
            self.assertEqual(live["purpose"], "first process candidate")


if __name__ == "__main__":
    unittest.main()

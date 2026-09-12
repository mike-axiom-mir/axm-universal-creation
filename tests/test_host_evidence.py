from __future__ import annotations

import datetime as dt
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.host_evidence import HOST_EVIDENCE_SCHEMA, HostEvidenceError, bind_host_evidence
from axm_uc.machine import UniversalCreationMachine


class HostEvidenceTests(unittest.TestCase):
    NOW = dt.datetime(2026, 8, 31, 12, 0, tzinfo=dt.timezone.utc)

    @staticmethod
    def _project(parent: Path) -> tuple[Path, dict[str, str]]:
        target = parent / "project"
        target.mkdir()
        files = {
            "index.html": b"<!doctype html><button id='start'>Start</button>\n",
            "game.js": b"document.querySelector('#start').disabled = false;\n",
        }
        for relative, content in files.items():
            (target / relative).write_bytes(content)
        return target, {path: hashlib.sha256(content).hexdigest() for path, content in files.items()}

    def _inputs(self, target: Path, digests: dict[str, str], *, status: str = "PASS") -> dict:
        claim_status = "PASS" if status == "PASS" else status
        return {
            "operation": "bind",
            "path": str(target),
            "expected_file_digests": digests,
            "evidence": {
                "schema": HOST_EVIDENCE_SCHEMA,
                "kind": "browser-interaction",
                "status": status,
                "observed_by": "bounded browser verifier",
                "observed_at": "2026-08-31T11:59:00Z",
                "valid_for_seconds": 600,
                "claims": [
                    {
                        "claim": "The Start control is visible and accepts one click.",
                        "status": claim_status,
                        "basis": "One bounded browser interaction completed against this exact body.",
                        "evidence_refs": ["browser-receipt:test"],
                    }
                ],
                "limitations": ["No long-duration gameplay claim was tested."],
            },
        }

    def test_fresh_external_evidence_binds_to_the_exact_project_body(self):
        with tempfile.TemporaryDirectory() as td:
            target, digests = self._project(Path(td))
            receipt = bind_host_evidence(ROOT, self._inputs(target, digests), now=self.NOW)
            self.assertEqual(receipt["effective_status"], "PASS")
            self.assertEqual(receipt["evidence"]["freshness"], "FRESH")
            self.assertFalse(receipt["authority"]["core_independently_reperformed_observation"])
            self.assertFalse(receipt["authority"]["execution_authority_granted"])

    def test_changed_project_body_rejects_prechange_evidence(self):
        with tempfile.TemporaryDirectory() as td:
            target, digests = self._project(Path(td))
            (target / "game.js").write_text("changed\n", encoding="utf-8")
            with self.assertRaisesRegex(HostEvidenceError, "exact project body") as caught:
                bind_host_evidence(ROOT, self._inputs(target, digests), now=self.NOW)
            self.assertEqual(caught.exception.details["changed_paths"], ["game.js"])

    def test_stale_observation_becomes_unknown_without_rewriting_original_status(self):
        with tempfile.TemporaryDirectory() as td:
            target, digests = self._project(Path(td))
            receipt = bind_host_evidence(
                ROOT,
                self._inputs(target, digests),
                now=self.NOW + dt.timedelta(hours=1),
            )
            self.assertEqual(receipt["evidence"]["status"], "PASS")
            self.assertEqual(receipt["effective_status"], "UNKNOWN")

    def test_overall_pass_cannot_hide_an_unknown_claim(self):
        with tempfile.TemporaryDirectory() as td:
            target, digests = self._project(Path(td))
            inputs = self._inputs(target, digests)
            inputs["evidence"]["claims"][0]["status"] = "UNKNOWN"
            with self.assertRaisesRegex(HostEvidenceError, "overall PASS"):
                bind_host_evidence(ROOT, inputs, now=self.NOW)

    def test_machine_exposes_evidence_boundary_without_claiming_it_ran_the_browser(self):
        result = UniversalCreationMachine(ROOT).create(
            {"kind": "inspect-host-evidence", "inputs": {"operation": "inspect"}}
        )
        self.assertEqual(result["type"], "CREATION_RESULT")
        self.assertFalse(result["result"]["external_status_is_independently_judged_by_core"])


if __name__ == "__main__":
    unittest.main()

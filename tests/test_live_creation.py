from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.live_creation import LIVE_CREATION_SCHEMA, LiveCreationError, run_live_creation


class LiveCreationRuntimeTests(unittest.TestCase):
    def _source(self, root: Path) -> Path:
        source = root / "creation"
        source.mkdir()
        (source / "status.txt").write_text("broken\n", encoding="utf-8")
        (source / "verify.py").write_text(
            "from pathlib import Path\n"
            "raise SystemExit(0 if Path('status.txt').read_text(encoding='utf-8').strip() == 'ready' else 3)\n",
            encoding="utf-8",
        )
        return source

    def _manifest(self, *, scope: str = "workspace") -> dict:
        return {
            "schema": LIVE_CREATION_SCHEMA,
            "run_id": "repair-proof",
            "domain": "software",
            "source": "creation",
            "max_iterations": 3,
            "policy": {
                "repair_scope": scope,
                "replace_existing_run": True,
            },
            "execute": [
                {"id": "verify", "argv": ["@python", "verify.py"]},
            ],
            "observe": [
                {"id": "status-ready", "kind": "contains", "path": "status.txt", "value": "ready"},
            ],
            "repairs": [
                {
                    "when": "status-ready",
                    "operation": "replace_text",
                    "path": "status.txt",
                    "old": "broken",
                    "new": "ready",
                }
            ],
        }

    def test_repairs_disposable_runtime_then_reexecutes_until_declared_evidence_passes(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self._source(root)
            receipt = run_live_creation(root, self._manifest())
            self.assertEqual(receipt["status"], "COMPLETE", receipt)
            self.assertEqual(len(receipt["iterations"]), 2)
            self.assertFalse(receipt["iterations"][0]["passed"])
            self.assertTrue(receipt["iterations"][0]["repairs"][0]["workspace"]["changed"])
            self.assertTrue(receipt["iterations"][1]["passed"])
            self.assertEqual(source.joinpath("status.txt").read_text(encoding="utf-8"), "broken\n")
            workspace = root / receipt["runtime_workspace"]
            self.assertEqual(workspace.joinpath("status.txt").read_text(encoding="utf-8"), "ready\n")
            saved = json.loads((root / receipt["receipt_path"]).read_text(encoding="utf-8"))
            self.assertEqual(saved["status"], "COMPLETE")

    def test_explicit_writeback_can_repair_canonical_creation_state(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            source = self._source(root)
            receipt = run_live_creation(root, self._manifest(scope="workspace-and-source"))
            self.assertEqual(receipt["status"], "COMPLETE", receipt)
            self.assertTrue(receipt["canonical_source_changed"])
            self.assertEqual(source.joinpath("status.txt").read_text(encoding="utf-8"), "ready\n")

    def test_holds_instead_of_claiming_done_when_evidence_fails_without_repair(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._source(root)
            manifest = self._manifest()
            manifest["repairs"] = []
            receipt = run_live_creation(root, manifest)
            self.assertEqual(receipt["status"], "HOLD")
            self.assertEqual(len(receipt["iterations"]), 1)
            self.assertIn("no declared repair", receipt["stop_reason"])

    def test_rejects_path_escape(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._source(root)
            manifest = self._manifest()
            manifest["source"] = "../outside"
            with self.assertRaises(LiveCreationError):
                run_live_creation(root, manifest)

    def test_non_python_command_requires_explicit_allowlist(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self._source(root)
            manifest = self._manifest()
            manifest["execute"] = [{"id": "nope", "argv": ["node", "--version"]}]
            with self.assertRaises(LiveCreationError):
                run_live_creation(root, manifest)


if __name__ == "__main__":
    unittest.main()

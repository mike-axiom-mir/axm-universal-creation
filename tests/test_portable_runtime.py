from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from axm_uc.portable import (
    MANIFEST_PATH,
    PortableRuntimeError,
    build_portable_runtime,
    verify_portable_runtime,
)


ROOT = Path(__file__).resolve().parents[1]
TEST_REVISION = "d98fbf3ee16da0541f2d823ec3194889a9132837"


class PortableRuntimeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temporary = tempfile.TemporaryDirectory()
        cls.directory = Path(cls.temporary.name)
        cls.first = cls.directory / "runtime-a.zip"
        cls.second = cls.directory / "runtime-b.zip"
        cls.untracked = ROOT / "assets/.portable-untracked-sentinel"
        cls.untracked.write_text("must not enter capsule", encoding="utf-8")
        try:
            cls.first_receipt = build_portable_runtime(
                ROOT, cls.first, source_revision=TEST_REVISION
            )
            cls.second_receipt = build_portable_runtime(
                ROOT, cls.second, source_revision=TEST_REVISION
            )
        finally:
            cls.untracked.unlink(missing_ok=True)

    @classmethod
    def tearDownClass(cls):
        cls.temporary.cleanup()

    def test_same_body_and_revision_produce_identical_archive(self):
        self.assertEqual(
            self.first_receipt["archiveSha256"],
            self.second_receipt["archiveSha256"],
        )
        self.assertEqual(self.first.read_bytes(), self.second.read_bytes())
        self.assertEqual(self.first_receipt["status"], "PASS")
        self.assertGreater(self.first_receipt["fileCount"], 2_000)
        with zipfile.ZipFile(self.first) as archive:
            self.assertNotIn("assets/.portable-untracked-sentinel", archive.namelist())

    def test_verifier_accepts_pinned_archive_and_exact_lineage(self):
        receipt = verify_portable_runtime(
            self.first,
            expected_sha256=self.first_receipt["archiveSha256"],
        )
        self.assertEqual(receipt["status"], "PASS")
        self.assertEqual(receipt["source"]["revision"], TEST_REVISION)
        self.assertEqual(receipt["source"]["revisionKind"], "declared")
        self.assertFalse(receipt["authority"]["adoptsCandidate"])
        self.assertFalse(receipt["authority"]["changesSourceMachine"])
        self.assertFalse(receipt["authority"]["declaresCanon"])

    def test_extracted_launcher_runs_from_unrelated_working_directory(self):
        extracted = self.directory / "extracted"
        extracted.mkdir()
        with zipfile.ZipFile(self.first) as archive:
            archive.extractall(extracted)
        outside = self.directory / "outside"
        outside.mkdir()
        completed = subprocess.run(
            [sys.executable, str(extracted / "run.py"), "inspect", "--limit", "1"],
            cwd=outside,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(completed.returncode, 0, completed.stderr)
        result = json.loads(completed.stdout)
        self.assertEqual(result["machine"]["name"], "AXM Universal Creation")
        self.assertEqual(result["registry"]["master_candidates"], 2_165)
        self.assertEqual(result["organ_materialization"]["declared_anatomy_organs"], 415)

        trial = subprocess.run(
            [
                sys.executable,
                str(extracted / "run.py"),
                "trial",
                str(extracted / "examples/requests/create_real_site.json"),
            ],
            cwd=outside,
            check=False,
            capture_output=True,
            text=True,
            timeout=60,
        )
        self.assertEqual(trial.returncode, 0, trial.stderr)
        trial_result = json.loads(trial.stdout)
        self.assertTrue(trial_result["passed"])
        self.assertTrue((extracted / "creations/first-real-site/index.html").is_file())

    def test_changed_declared_file_fails_closed(self):
        tampered = self.directory / "tampered.zip"
        with zipfile.ZipFile(self.first) as source, zipfile.ZipFile(
            tampered, "w", compression=zipfile.ZIP_STORED
        ) as target:
            for info in source.infolist():
                data = source.read(info.filename)
                if info.filename == "machine.contract.json":
                    data = data.replace(b'"standalone": true', b'"standalone": false')
                target.writestr(info, data)
        with self.assertRaisesRegex(PortableRuntimeError, "content mismatch"):
            verify_portable_runtime(tampered)

    def test_undeclared_and_unsafe_entries_fail_closed(self):
        extra = self.directory / "extra.zip"
        extra.write_bytes(self.first.read_bytes())
        with zipfile.ZipFile(extra, "a", compression=zipfile.ZIP_STORED) as archive:
            info = zipfile.ZipInfo("undeclared.txt", date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = zipfile.ZIP_STORED
            info.create_system = 3
            info.external_attr = 0o644 << 16
            archive.writestr(info, "not in manifest")
        with self.assertRaisesRegex(PortableRuntimeError, "inventory"):
            verify_portable_runtime(extra)

        escaped = self.directory / "escaped.zip"
        with zipfile.ZipFile(escaped, "w", compression=zipfile.ZIP_STORED) as archive:
            archive.writestr("../escape.txt", "escape")
            archive.writestr(MANIFEST_PATH, "{}")
        with self.assertRaisesRegex(PortableRuntimeError, "unsafe archive path"):
            verify_portable_runtime(escaped)

    def test_portable_cli_returns_hold_for_wrong_pinned_digest(self):
        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "axm_uc.portable_cli",
                "verify",
                str(self.first),
                "--expected-sha256",
                "0" * 64,
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 2)
        result = json.loads(completed.stdout)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("pinned value", result["error"])


if __name__ == "__main__":
    unittest.main()

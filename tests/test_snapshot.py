from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.snapshot import SNAPSHOT_MANIFEST, create_daily_snapshot, restore_snapshot, verify_snapshot


class SnapshotTests(unittest.TestCase):
    def test_one_snapshot_per_day_and_restore_quarantines_current_body(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            root.mkdir()
            (root / "state").mkdir()
            (root / "machine.contract.json").write_text("{}", encoding="utf-8")
            (root / "body.txt").write_text("good", encoding="utf-8")
            day = dt.date(2026, 8, 28)
            first = create_daily_snapshot(root, parent / "snaps", today=day)
            second = create_daily_snapshot(root, parent / "snaps", today=day)
            self.assertTrue(first["created"])
            self.assertFalse(second["created"])
            self.assertEqual(first["schema"], "axm.universal-creation.snapshot/v1")
            verified = verify_snapshot(Path(first["path"]))
            self.assertEqual(verified["integrity"], "manifest-sha256")
            self.assertEqual(verified["file_count"], 2)
            (root / "body.txt").write_text("bad", encoding="utf-8")
            restored = restore_snapshot(root, Path(first["path"]), confirm=True)
            self.assertTrue(restored["restored"])
            self.assertEqual(restored["verification"]["manifest_sha256"], first["manifest_sha256"])
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "good")
            self.assertFalse((root / SNAPSHOT_MANIFEST).exists())
            quarantine = Path(restored["quarantine"])
            self.assertEqual((quarantine / "body.txt").read_text(encoding="utf-8"), "bad")

    def test_manifest_payload_drift_is_rejected_before_current_body_moves(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            root.mkdir()
            (root / "body.txt").write_text("known-good", encoding="utf-8")
            created = create_daily_snapshot(root, parent / "snaps", today=dt.date(2026, 9, 9))
            original = Path(created["path"])
            tampered = parent / "tampered.zip"
            with zipfile.ZipFile(original, "r") as source, zipfile.ZipFile(tampered, "w") as target:
                for info in source.infolist():
                    data = b"re-sealed-drift" if info.filename == "body.txt" else source.read(info)
                    target.writestr(info, data)
            (root / "body.txt").write_text("current-state", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "snapshot (byte count|sha256) mismatch"):
                restore_snapshot(root, tampered, confirm=True)
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "current-state")
            self.assertEqual(list(parent.glob("machine.quarantine-*")), [])

    def test_snapshot_cannot_overwrite_preserved_git_state(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            root.mkdir()
            (root / ".git").mkdir()
            (root / ".git" / "config").write_text("trusted", encoding="utf-8")
            (root / "body.txt").write_text("current", encoding="utf-8")
            hostile = parent / "hostile.zip"
            with zipfile.ZipFile(hostile, "w") as archive:
                archive.writestr("body.txt", "older")
                archive.writestr(".git/config", "forged")
            with self.assertRaisesRegex(ValueError, "forbidden snapshot path"):
                restore_snapshot(root, hostile, confirm=True)
            self.assertEqual((root / ".git" / "config").read_text(encoding="utf-8"), "trusted")
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "current")
            self.assertEqual(list(parent.glob("machine.quarantine-*")), [])

    def test_legacy_snapshot_remains_explicitly_crc_only(self):
        with tempfile.TemporaryDirectory() as td:
            snapshot = Path(td) / "legacy.zip"
            with zipfile.ZipFile(snapshot, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                archive.writestr("body.txt", "legacy")
            verified = verify_snapshot(snapshot)
            self.assertTrue(verified["valid"])
            self.assertEqual(verified["schema"], "legacy-zip")
            self.assertEqual(verified["integrity"], "zip-crc-only")
            self.assertIsNone(verified["manifest_sha256"])

    def test_manifest_rejects_undeclared_extra_payload(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            root.mkdir()
            (root / "body.txt").write_text("known-good", encoding="utf-8")
            created = create_daily_snapshot(root, parent / "snaps", today=dt.date(2026, 9, 9))
            original = Path(created["path"])
            expanded = parent / "expanded.zip"
            with zipfile.ZipFile(original, "r") as source, zipfile.ZipFile(expanded, "w") as target:
                for info in source.infolist():
                    target.writestr(info, source.read(info))
                target.writestr("undeclared.txt", "not in manifest")
            with self.assertRaisesRegex(ValueError, "manifest file set"):
                verify_snapshot(expanded)


if __name__ == "__main__":
    unittest.main()

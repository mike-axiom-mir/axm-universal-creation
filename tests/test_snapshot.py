from __future__ import annotations

import datetime as dt
import stat
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.snapshot import create_daily_snapshot, restore_snapshot


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
            (root / "body.txt").write_text("bad", encoding="utf-8")
            restored = restore_snapshot(root, Path(first["path"]), confirm=True)
            self.assertTrue(restored["restored"])
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "good")
            quarantine = Path(restored["quarantine"])
            self.assertEqual((quarantine / "body.txt").read_text(encoding="utf-8"), "bad")

    def test_snapshot_refuses_links_and_output_inside_machine_root(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            root.mkdir()
            outside = parent / "private.txt"
            outside.write_text("must remain outside", encoding="utf-8")
            link = root / "linked-private.txt"
            try:
                link.symlink_to(outside)
            except OSError as error:
                self.skipTest(f"symlink creation unavailable: {error}")

            output = parent / "snapshots"
            with self.assertRaisesRegex(ValueError, "unsafe snapshot symlink"):
                create_daily_snapshot(root, output)
            self.assertEqual(list(output.iterdir()), [])

            link.unlink()
            with self.assertRaisesRegex(ValueError, "outside the machine root"):
                create_daily_snapshot(root, root / "snapshots")

    def test_restore_rejects_protected_and_symlink_entries_before_moving_body(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            root = parent / "machine"
            (root / ".git").mkdir(parents=True)
            (root / ".git" / "config").write_text("trusted", encoding="utf-8")
            (root / "body.txt").write_text("current", encoding="utf-8")

            protected = parent / "protected.zip"
            with zipfile.ZipFile(protected, "w") as archive:
                archive.writestr(".git/config", "replaced")
                archive.writestr("body.txt", "archive")
            with self.assertRaisesRegex(ValueError, "protected snapshot path"):
                restore_snapshot(root, protected, confirm=True)
            self.assertEqual((root / ".git" / "config").read_text(encoding="utf-8"), "trusted")
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "current")
            self.assertEqual(list(parent.glob("machine.quarantine-*")), [])

            linked = parent / "linked.zip"
            link_info = zipfile.ZipInfo("linked-private.txt")
            link_info.create_system = 3
            link_info.external_attr = (stat.S_IFLNK | 0o777) << 16
            with zipfile.ZipFile(linked, "w") as archive:
                archive.writestr(link_info, "../private.txt")
            with self.assertRaisesRegex(ValueError, "symlink entry"):
                restore_snapshot(root, linked, confirm=True)
            self.assertEqual((root / "body.txt").read_text(encoding="utf-8"), "current")
            self.assertEqual(list(parent.glob("machine.quarantine-*")), [])


if __name__ == "__main__":
    unittest.main()

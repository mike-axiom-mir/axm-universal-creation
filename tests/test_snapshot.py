from __future__ import annotations

import datetime as dt
import sys
import tempfile
import unittest
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


if __name__ == "__main__":
    unittest.main()

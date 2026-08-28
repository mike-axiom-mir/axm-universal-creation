from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.integrity import refresh, verify


class IntegrityTests(unittest.TestCase):
    def test_hash_mismatch_describes_state_and_does_not_block_creation(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            (root / "state").mkdir()
            file = root / "body.txt"
            file.write_text("one", encoding="utf-8")
            refresh(root)
            self.assertEqual(verify(root)["status"], "clean")
            file.write_text("two", encoding="utf-8")
            result = verify(root)
            self.assertEqual(result["status"], "changed")
            self.assertFalse(result["blocks_creation"])
            self.assertIn("body.txt", result["changed"])


if __name__ == "__main__":
    unittest.main()

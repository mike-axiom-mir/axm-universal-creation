from __future__ import annotations

import unittest
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.registry import Registry


class RegistryTests(unittest.TestCase):
    def test_handoff_counts_are_preserved(self):
        summary = Registry(ROOT).summary()
        self.assertEqual(summary["master_candidates"], 2165)
        self.assertEqual(summary["master_by_level"], {"atom": 1000, "component": 750, "organ": 415})
        self.assertEqual(summary["implementation_kernel_records"], 100)

    def test_search_uses_real_baseline(self):
        rows = Registry(ROOT).search("identifier", level="atom", limit=5)
        self.assertTrue(rows)
        self.assertTrue(all(row["level"] == "atom" for row in rows))


if __name__ == "__main__":
    unittest.main()

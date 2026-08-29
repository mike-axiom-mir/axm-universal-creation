from __future__ import annotations

import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json"
EXPECTED = {"atom": 1000, "component": 750, "organ": 415}
LEVEL_DIRS = {
    "atom": ROOT / "atoms",
    "component": ROOT / "components",
    "organ": ROOT / "organs",
}


class RegistryMaterializationTests(unittest.TestCase):
    def test_full_registry_is_materialized_and_matches_canonical_source(self):
        master = json.loads(MASTER.read_text(encoding="utf-8"))["records"]
        self.assertEqual(len(master), 2165)
        canonical = {row["id"]: row for row in master}
        self.assertEqual(len(canonical), 2165)

        seen: dict[str, dict] = {}
        for level, folder in LEVEL_DIRS.items():
            files = sorted(folder.glob("*.json"))
            self.assertEqual(len(files), EXPECTED[level], level)
            for path in files:
                row = json.loads(path.read_text(encoding="utf-8"))
                self.assertEqual(row["level"], level, str(path))
                self.assertIn(row["id"], canonical, str(path))
                self.assertEqual(row, canonical[row["id"]], row["id"])
                self.assertNotIn(row["id"], seen, row["id"])
                seen[row["id"]] = row

        self.assertEqual(set(seen), set(canonical))

    def test_materialization_manifest_matches_expected_body(self):
        manifest = json.loads((ROOT / "registry_materialization.json").read_text(encoding="utf-8"))
        self.assertEqual(manifest["total"], 2165)
        self.assertEqual(manifest["counts"], EXPECTED)


if __name__ == "__main__":
    unittest.main()

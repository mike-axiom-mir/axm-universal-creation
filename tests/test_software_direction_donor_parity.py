from __future__ import annotations

import importlib.util
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.directions import SoftwareDirections


spec = importlib.util.spec_from_file_location(
    "verify_software_direction_donor",
    ROOT / "tools" / "verify_software_direction_donor.py",
)
assert spec is not None and spec.loader is not None
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


class SoftwareDirectionDonorParityTests(unittest.TestCase):
    def test_direction_set_permutations_have_one_consumer_identity(self):
        directions = SoftwareDirections(ROOT)
        first = directions.compose({
            "direction_ids": ["game", "collaboration-multiplayer", "game"],
            "execution": ["hard-real-time"],
            "risk": ["public-facing"],
        })
        second = directions.compose({
            "direction_ids": ["collaboration-multiplayer", "game", "collaboration-multiplayer"],
            "execution": ["hard-real-time"],
            "risk": ["public-facing"],
        })
        self.assertEqual(first, second)
        self.assertEqual(first["direction_ids"], ["collaboration-multiplayer", "game"])
        self.assertEqual(first["duplicate_direction_count"], 1)
        self.assertFalse(first["direction_is_authority"])

    def test_verifier_accepts_semantically_identical_catalogs(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider"
            shutil.copytree(ROOT / "reference" / "software-directions", provider / "software-directions")
            receipt = verifier.verify_donor(ROOT, provider, provider_revision="TEST_FIXTURE")
        self.assertTrue(receipt["passed"])
        self.assertTrue(receipt["catalog_parity"])
        self.assertEqual(receipt["profile_count"], 29)
        self.assertEqual(receipt["authority"], {
            "selection": False,
            "execution": False,
            "admission": False,
            "merge": False,
            "canon": False,
        })

    def test_verifier_fails_closed_on_semantic_catalog_drift(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider"
            shutil.copytree(ROOT / "reference" / "software-directions", provider / "software-directions")
            catalog_path = provider / "software-directions" / "direction-catalog.json"
            catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
            catalog["profiles"][0]["description"] += " drift"
            catalog_path.write_text(json.dumps(catalog), encoding="utf-8")
            receipt = verifier.verify_donor(ROOT, provider, provider_revision="DRIFT_FIXTURE")
        self.assertFalse(receipt["passed"])
        self.assertFalse(receipt["catalog_parity"])
        self.assertIn("direction-catalog.json", receipt["mismatched_catalogs"])

    def test_verifier_rejects_symlinked_catalog_source(self):
        with tempfile.TemporaryDirectory() as tmp:
            provider = Path(tmp) / "provider"
            source = ROOT / "reference" / "software-directions"
            shutil.copytree(source, provider / "software-directions")
            axis_path = provider / "software-directions" / "axis-catalog.json"
            target_path = provider / "axis-copy.json"
            shutil.copy2(axis_path, target_path)
            axis_path.unlink()
            try:
                axis_path.symlink_to(target_path)
            except OSError:
                self.skipTest("symlinks unavailable on this host")
            with self.assertRaises(ValueError):
                verifier.verify_donor(ROOT, provider, provider_revision="SYMLINK_FIXTURE")


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from axm_uc.fabric_sources import FabricSourceError, inspect_fabric_sources


class FabricSourceTests(unittest.TestCase):
    def test_declared_sources_do_not_fetch_network_or_transfer_authority(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = inspect_fabric_sources(Path(tmp))
        self.assertEqual(report["schema"], "axm.fabric-source-resolution/v1")
        self.assertEqual(report["source_count"], 4)
        self.assertFalse(report["network_fetch_performed"])
        self.assertFalse(report["authority_change"])
        self.assertTrue(all(not row["network_fetch_performed"] for row in report["sources"]))
        self.assertTrue(all(not row["authority_change"] for row in report["sources"]))

    def test_local_fallbacks_are_observed_without_becoming_preferred_fabric(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "capabilities/platform-hands").mkdir(parents=True)
            report = inspect_fabric_sources(root, source_id="hands-fabric")
        source = report["sources"][0]
        self.assertEqual(source["status"], "LOCAL_FALLBACK_AVAILABLE")
        self.assertFalse(source["preferred_path_exists"])
        self.assertEqual(len(source["active_local_paths"]), 1)
        self.assertTrue(source["active_local_paths"][0].endswith("capabilities/platform-hands"))

    def test_preferred_mount_outranks_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "fabrics/organs").mkdir(parents=True)
            (root / "organs").mkdir()
            report = inspect_fabric_sources(root, source_id="organ-fabric")
        source = report["sources"][0]
        self.assertEqual(source["status"], "PREFERRED_LOCAL_SOURCE_AVAILABLE")
        self.assertEqual(source["active_local_paths"], [source["preferred_path"]])

    def test_explicit_missing_override_does_not_silently_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "capabilities/platform-hands").mkdir(parents=True)
            report = inspect_fabric_sources(
                root,
                source_id="hands-fabric",
                overrides={"hands-fabric": "chosen/missing-hands"},
            )
        source = report["sources"][0]
        self.assertEqual(source["status"], "EXPLICIT_SOURCE_MISSING")
        self.assertEqual(source["active_local_paths"], [])
        self.assertEqual(source["fallbacks"], [])

    def test_archive_is_preservation_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = inspect_fabric_sources(Path(tmp), source_id="organ-archive")
        self.assertFalse(report["sources"][0]["callable_by_default"])

    def test_unknown_source_and_override_are_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(FabricSourceError):
                inspect_fabric_sources(root, source_id="missing")
            with self.assertRaises(FabricSourceError):
                inspect_fabric_sources(root, overrides={"missing": "somewhere"})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class MaterialDonorInvariantReceiptTests(unittest.TestCase):
    def _run(self) -> dict:
        run = subprocess.run(
            [sys.executable, str(ROOT / "tools" / "material_donor_invariant_receipt.py")],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(run.returncode, 0, run.stderr)
        return json.loads(run.stdout)

    def test_receipt_is_deterministic_and_keeps_authority_false(self) -> None:
        first = self._run()
        second = self._run()
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "axm.universal-creation.material-donor-invariant-receipt/v1")
        self.assertEqual(first["producer"]["adapterFormat"], "axm-material-donor-pack")
        self.assertEqual(first["producer"]["adapterVersion"], "0.2.0")
        self.assertTrue(first["producer"]["fixtureSha256"])
        self.assertTrue(all(value is False for value in first["authority"].values()))

    def test_complete_and_ambiguous_observations_preserve_donor_semantics(self) -> None:
        receipt = self._run()
        observations = receipt["observations"]

        complete = observations["complete"]
        self.assertEqual(complete["truthStatus"], "READY_EXACT_MATERIAL_DONOR_ADAPTER")
        self.assertEqual(complete["source"]["pack_id"], "invariant-probe-pack")
        self.assertEqual(complete["source"]["source_library_id"], "invariant-probe-library")
        self.assertEqual(
            {item["entryId"] for item in complete["acceptedEntries"]},
            {"probe-base", "probe-roughness"},
        )
        self.assertTrue(all(item["source"]["method"] == "self-made-invariant-probe" for item in complete["acceptedEntries"]))
        self.assertFalse(complete["renderingVerified"])

        unassigned = observations["unassigned"]
        self.assertEqual(unassigned["truthStatus"], "PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS")
        self.assertTrue(unassigned["strictRejected"])
        self.assertEqual(len(unassigned["heldEntries"]), 1)
        self.assertIn("no supported explicit channel hint", unassigned["heldEntries"][0]["reason"])

        family = observations["familyConflict"]
        self.assertEqual(family["truthStatus"], "PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS")
        self.assertEqual(family["acceptedFamilyCount"], 0)
        self.assertEqual(family["heldFamilies"][0]["duplicate_channels"], ["base-color"])
        self.assertEqual(len(family["acceptedEntries"]), 3)

    def test_unsupported_version_is_retained_as_fail_closed_observation(self) -> None:
        receipt = self._run()
        unsupported = receipt["observations"]["unsupportedVersion"]
        self.assertTrue(unsupported["rejected"])
        self.assertIn("unsupported material donor version", unsupported["message"])
        self.assertIn("Executable donor-owned observations", receipt["truthBoundary"]["claim"])


if __name__ == "__main__":
    unittest.main()

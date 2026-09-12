from __future__ import annotations

import copy
import unittest
from pathlib import Path

from axm_uc.capabilities import CapabilityStore
from axm_uc.material_donor import MaterialDonorError, adapt_material_donor_pack


ROOT = Path(__file__).resolve().parents[1]
BASE_DATA = "data:image/png;base64,iVBORw0KGgo="
ROUGH_DATA = "data:image/png;base64,iVBORw0KGgp="


def donor_pack() -> dict:
    return {
        "format": "axm-material-donor-pack",
        "version": "0.2.0",
        "id": "donor-test-pack",
        "exportedAt": "2026-09-12T00:00:00Z",
        "library": {
            "sourceFormat": "axm-material-library",
            "sourceVersion": "0.4.0",
            "sourceLibraryId": "library-test",
            "entries": [
                {
                    "id": "material-base",
                    "name": "painted-metal-base.png",
                    "kind": "texture",
                    "mime": "image/png",
                    "width": 1,
                    "height": 1,
                    "dataUrl": BASE_DATA,
                    "source": {"method": "self-made-test"},
                    "usage": {"channelHint": "base-color", "channelBasis": "operator-declared"},
                    "tags": ["metal"],
                },
                {
                    "id": "material-roughness",
                    "name": "painted-metal-roughness.png",
                    "kind": "roughness",
                    "mime": "image/png",
                    "width": 1,
                    "height": 1,
                    "dataUrl": ROUGH_DATA,
                    "source": {"method": "self-made-test"},
                    "usage": {"channelHint": "roughness", "channelBasis": "operator-declared"},
                    "tags": ["metal"],
                },
            ],
            "families": [
                {
                    "id": "family-painted-metal",
                    "name": "painted metal",
                    "purpose": "test reusable base + roughness family",
                    "entryIds": ["material-base", "material-roughness"],
                    "tags": ["metal"],
                }
            ],
        },
        "assets": [],
        "workspace": {},
        "layers": [],
        "experiment": None,
    }


class MaterialDonorAdapterTests(unittest.TestCase):
    def test_complete_pack_becomes_valid_asset_atom_material(self) -> None:
        result = adapt_material_donor_pack(donor_pack(), strict=True)
        self.assertEqual(result["truth_status"], "READY_EXACT_MATERIAL_DONOR_ADAPTER")
        self.assertEqual(result["receipt"]["accepted_entries"], 2)
        self.assertEqual(result["receipt"]["accepted_families"], 1)
        self.assertFalse(result["receipt"]["rendering_verified"])

        package = result["asset_package"]
        self.assertEqual(package["schema"], "axm.asset-atom-package/v0.1")
        self.assertEqual(package["asset_class"], "material.library")
        kinds = [atom["kind"] for atom in package["atoms"]]
        self.assertEqual(kinds.count("texture"), 2)
        self.assertEqual(kinds.count("material"), 1)

        material = next(atom for atom in package["atoms"] if atom["kind"] == "material")
        self.assertEqual(
            sorted(material["payload"]["texture_bindings"]),
            ["base-color", "roughness"],
        )
        self.assertEqual(sorted(material["uses"]), sorted(material["payload"]["texture_bindings"].values()))
        self.assertTrue(all(atom["payload"]["resource"]["uri"].startswith("donor://") for atom in package["atoms"] if atom["kind"] == "texture"))
        self.assertTrue(all(atom["payload"]["resource"]["digest"].startswith("sha256:") for atom in package["atoms"] if atom["kind"] == "texture"))

    def test_live_capability_route_invokes_same_adapter(self) -> None:
        store = CapabilityStore(ROOT)
        manifest = store.route("import-material-donor-pack")
        self.assertIsNotNone(manifest)
        self.assertEqual(manifest["id"], "AXM-CAP-IMPORT-MATERIAL-DONOR")
        result = store.invoke(manifest, {"donor_pack": donor_pack(), "strict": True})
        self.assertEqual(result["truth_status"], "READY_EXACT_MATERIAL_DONOR_ADAPTER")
        self.assertEqual(result["receipt"]["accepted_entries"], 2)
        self.assertEqual(result["receipt"]["accepted_families"], 1)
        self.assertEqual(result["asset_package"]["schema"], "axm.asset-atom-package/v0.1")

    def test_unassigned_entry_is_visible_hold_not_silent_guess(self) -> None:
        pack = donor_pack()
        pack["library"]["entries"].append(
            {
                "id": "material-unknown",
                "name": "mystery.png",
                "kind": "texture",
                "mime": "image/png",
                "width": 1,
                "height": 1,
                "dataUrl": BASE_DATA,
                "source": {"method": "test"},
                "usage": {"channelHint": "unassigned", "channelBasis": "operator-declared"},
            }
        )
        result = adapt_material_donor_pack(pack)
        self.assertEqual(result["truth_status"], "PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS")
        self.assertEqual(result["receipt"]["accepted_entries"], 2)
        self.assertEqual(len(result["receipt"]["held_entries"]), 1)
        self.assertIn("no supported explicit channel hint", result["receipt"]["held_entries"][0]["reason"])
        with self.assertRaises(MaterialDonorError):
            adapt_material_donor_pack(pack, strict=True)

    def test_duplicate_family_channel_holds_family_but_keeps_textures(self) -> None:
        pack = donor_pack()
        duplicate = copy.deepcopy(pack["library"]["entries"][0])
        duplicate["id"] = "material-base-2"
        duplicate["name"] = "second-base.png"
        pack["library"]["entries"].append(duplicate)
        pack["library"]["families"][0]["entryIds"].append("material-base-2")
        result = adapt_material_donor_pack(pack)
        self.assertEqual(result["receipt"]["accepted_entries"], 3)
        self.assertEqual(result["receipt"]["accepted_families"], 0)
        self.assertEqual(len(result["receipt"]["held_families"]), 1)
        self.assertEqual(result["receipt"]["held_families"][0]["duplicate_channels"], ["base-color"])
        self.assertTrue(all(atom["kind"] == "texture" for atom in result["asset_package"]["atoms"]))

    def test_wrong_version_fails_closed(self) -> None:
        pack = donor_pack()
        pack["version"] = "0.1.0"
        with self.assertRaises(MaterialDonorError):
            adapt_material_donor_pack(pack)

    def test_mime_mismatch_holds_entry(self) -> None:
        pack = donor_pack()
        pack["library"]["entries"][0]["mime"] = "image/webp"
        result = adapt_material_donor_pack(pack)
        self.assertEqual(result["receipt"]["accepted_entries"], 1)
        self.assertEqual(len(result["receipt"]["held_entries"]), 1)
        self.assertIn("MIME does not match", result["receipt"]["held_entries"][0]["reason"])


if __name__ == "__main__":
    unittest.main()

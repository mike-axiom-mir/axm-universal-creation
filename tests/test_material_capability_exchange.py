from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from axm_uc.material_capability_exchange import (
    MaterialCapabilityError,
    consume_material_capability_pack,
    validate_material_capability_pack,
    validate_material_use_feedback,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "material-capability-packs" / "painted-metal-v0.18.json"


class MaterialCapabilityExchangeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_fixture_matches_v018_identity_contract(self) -> None:
        validated = validate_material_capability_pack(self.pack)
        self.assertEqual(validated["id"], "material-capability-pack-55c82b2d")
        self.assertEqual(validated["fingerprint"], "55c82b2d")
        self.assertEqual(len(validated["capabilities"]), 3)

    def test_detached_material_capabilities_are_adopted_and_pattern_is_hold(self) -> None:
        result = consume_material_capability_pack(self.pack)
        self.assertEqual(result["truth_status"], "PARTIAL_EXACT_MATERIAL_CAPABILITY_CONSUMER_WITH_HOLDS")
        self.assertEqual(result["receipt"]["declared_capabilities"], 3)
        self.assertEqual(result["receipt"]["adopted_capabilities"], 2)
        self.assertEqual(result["receipt"]["held_capabilities"], 1)
        self.assertFalse(result["receipt"]["live_topology_modified"])
        self.assertFalse(result["receipt"]["canonical_state_modified"])

        package = result["asset_package"]
        self.assertIsNotNone(package)
        atom_ids = {atom["id"] for atom in package["atoms"]}
        self.assertIn("texture-surface-base", atom_ids)
        self.assertIn("material-painted-metal-family", atom_ids)

        feedback = result["feedback"]
        validate_material_use_feedback(feedback, self.pack)
        events = {event["capabilityId"]: event for event in feedback["events"]}
        self.assertEqual(events["cap-material-entry-a2c5429f"]["action"], "adopted")
        self.assertEqual(events["cap-material-entry-a2c5429f"]["outcome"], "PASS")
        self.assertEqual(events["cap-material-entry-a2c5429f"]["derivedIds"], ["texture-surface-base"])
        self.assertEqual(events["cap-material-family-2d93291f"]["action"], "adopted")
        self.assertEqual(events["cap-material-family-2d93291f"]["derivedIds"], ["material-painted-metal-family"])
        self.assertEqual(events["cap-pattern-4445f3c4"]["action"], "inspected")
        self.assertEqual(events["cap-pattern-4445f3c4"]["outcome"], "HOLD")

    def test_output_is_deterministic(self) -> None:
        first = consume_material_capability_pack(self.pack)
        second = consume_material_capability_pack(self.pack)
        self.assertEqual(first["feedback"], second["feedback"])
        self.assertEqual(first["asset_package"], second["asset_package"])

    def test_tampered_payload_is_rejected_before_use(self) -> None:
        tampered = copy.deepcopy(self.pack)
        tampered["capabilities"][0]["payload"]["name"] = "tampered"
        with self.assertRaises(MaterialCapabilityError):
            validate_material_capability_pack(tampered)

    def test_tampered_capability_fingerprint_is_rejected_even_if_pack_fingerprint_is_unchanged(self) -> None:
        tampered = copy.deepcopy(self.pack)
        tampered["capabilities"][0]["fingerprint"] = "00000000"
        with self.assertRaises(MaterialCapabilityError):
            validate_material_capability_pack(tampered)

    def test_strict_mode_refuses_unsupported_capability_hold(self) -> None:
        with self.assertRaises(MaterialCapabilityError) as context:
            consume_material_capability_pack(self.pack, strict=True)
        self.assertIn("some capabilities were not adopted exactly", str(context.exception))
        self.assertIn("feedback", context.exception.details)

    def test_feedback_linkage_rejects_wrong_pack(self) -> None:
        result = consume_material_capability_pack(self.pack)
        wrong = copy.deepcopy(self.pack)
        wrong["id"] = "material-capability-pack-wrong"
        with self.assertRaises(MaterialCapabilityError):
            validate_material_use_feedback(result["feedback"], wrong)


if __name__ == "__main__":
    unittest.main()

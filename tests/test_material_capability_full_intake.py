from __future__ import annotations

import copy
import json
from pathlib import Path
import unittest

from axm_uc.material_capability_exchange import validate_material_capability_pack
from axm_uc.material_capability_full_intake import (
    FullMaterialCapabilityError,
    PATTERN_SCHEMA,
    RECIPE_SCHEMA,
    SPRITE_SCHEMA,
    consume_material_capability_pack_full,
    project_pattern,
    project_recipe,
    project_sprite_candidate,
    validate_full_material_use_feedback,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "material-capability-packs" / "full-circulation-v0.18.json"
FEEDBACK_FIXTURE = ROOT / "examples" / "material-capability-packs" / "full-circulation-v0.18-feedback.json"


class FullMaterialCapabilityIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = json.loads(FIXTURE.read_text(encoding="utf-8"))
        self.expected_feedback = json.loads(FEEDBACK_FIXTURE.read_text(encoding="utf-8"))
        self.by_kind = {row["kind"]: row for row in self.pack["capabilities"]}

    def test_full_circulation_fixture_matches_v018_contract(self) -> None:
        validated = validate_material_capability_pack(self.pack)
        self.assertEqual(validated["id"], "material-capability-pack-756825c8")
        self.assertEqual(validated["fingerprint"], "756825c8")
        self.assertEqual(
            {row["kind"] for row in validated["capabilities"]},
            {"material-entry", "material-family", "sprite-candidate", "recipe", "pattern"},
        )

    def test_all_five_capability_kinds_adopt_into_detached_state(self) -> None:
        result = consume_material_capability_pack_full(self.pack, strict=True)
        self.assertEqual(result["truth_status"], "READY_EXACT_FULL_MATERIAL_CAPABILITY_CONSUMER")
        self.assertEqual(result["receipt"]["declared_capabilities"], 5)
        self.assertEqual(result["receipt"]["adopted_capabilities"], 5)
        self.assertEqual(result["receipt"]["held_capabilities"], 0)
        self.assertEqual(result["receipt"]["detached_visual_descriptors"], 3)
        self.assertFalse(result["receipt"]["live_topology_modified"])
        self.assertFalse(result["receipt"]["canonical_state_modified"])
        self.assertFalse(result["receipt"]["rendering_verified"])

        package = result["asset_package"]
        self.assertIsNotNone(package)
        atom_ids = {atom["id"] for atom in package["atoms"]}
        self.assertIn("texture-surface-base", atom_ids)
        self.assertIn("material-painted-metal-family", atom_ids)

        projections = {row["schema"]: row for row in result["detached_visual_capabilities"]}
        self.assertEqual(set(projections), {SPRITE_SCHEMA, RECIPE_SCHEMA, PATTERN_SCHEMA})

        sprite = projections[SPRITE_SCHEMA]
        self.assertEqual(sprite["atlasId"], "rust-corrosion")
        self.assertEqual(sprite["normalizedBounds"]["x"], 0.125)
        self.assertEqual(sprite["normalizedBounds"]["height"], 0.28125)
        self.assertEqual(sprite["id"], "uc-sprite-052e2cac")

        recipe = projections[RECIPE_SCHEMA]
        self.assertTrue(recipe["transparent"])
        self.assertEqual(recipe["layerCount"], 2)
        self.assertEqual(recipe["recipeFingerprint"], "2e2e0454")
        self.assertEqual(recipe["id"], "uc-recipe-922067f2")

        pattern = projections[PATTERN_SCHEMA]
        self.assertEqual(pattern["support"], 2)
        self.assertEqual(pattern["slotCount"], 2)
        self.assertEqual(pattern["id"], "uc-pattern-49da0176")

        feedback = result["feedback"]
        validate_full_material_use_feedback(feedback, self.pack)
        self.assertEqual(feedback, self.expected_feedback)
        self.assertEqual(feedback["id"], "material-use-feedback-4e1937b3")
        self.assertEqual(len(feedback["events"]), 5)
        for event in feedback["events"]:
            self.assertEqual(event["action"], "adopted")
            self.assertEqual(event["outcome"], "PASS")
            self.assertTrue(event["derivedIds"])

    def test_full_intake_is_deterministic(self) -> None:
        first = consume_material_capability_pack_full(self.pack, strict=True)
        second = consume_material_capability_pack_full(self.pack, strict=True)
        self.assertEqual(first, second)
        self.assertEqual(first["feedback"], self.expected_feedback)

    def test_sprite_projection_refuses_bounds_outside_atlas(self) -> None:
        capability = copy.deepcopy(self.by_kind["sprite-candidate"])
        capability["payload"]["normalizedBounds"] = {"x": 0.9, "y": 0.1, "width": 0.2, "height": 0.2}
        with self.assertRaises(FullMaterialCapabilityError):
            project_sprite_candidate(capability)

    def test_recipe_projection_refuses_nontransparent_recipe(self) -> None:
        capability = copy.deepcopy(self.by_kind["recipe"])
        capability["payload"]["recipe"]["canvas"]["transparent"] = False
        with self.assertRaises(FullMaterialCapabilityError):
            project_recipe(capability)

    def test_pattern_projection_refuses_invalid_support(self) -> None:
        capability = copy.deepcopy(self.by_kind["pattern"])
        capability["payload"]["pattern"]["support"] = 0
        capability["payload"]["support"] = 0
        with self.assertRaises(FullMaterialCapabilityError):
            project_pattern(capability)

    def test_projection_ids_are_bound_to_exact_capability_state(self) -> None:
        original = project_sprite_candidate(self.by_kind["sprite-candidate"])
        modified = copy.deepcopy(self.by_kind["sprite-candidate"])
        modified["payload"]["alphaCoverage"]["visibleShare"] = 0.62
        changed = project_sprite_candidate(modified)
        self.assertNotEqual(original["id"], changed["id"])


if __name__ == "__main__":
    unittest.main()

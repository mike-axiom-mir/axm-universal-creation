from __future__ import annotations

import copy
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.material_capability_realization import (
    MaterialCapabilityRealizationError,
    REALIZATION_SCHEMA,
    REALIZER_CONSUMER,
    build_material_capability_svg,
    realize_material_capability_pack,
    validate_realization_feedback,
)


ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "examples" / "material-capability-packs" / "full-circulation-v0.18.json"


class MaterialCapabilityRealizationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.pack = json.loads(FIXTURE.read_text(encoding="utf-8"))

    def test_all_five_capability_kinds_drive_one_native_svg_creation(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "material-capability-realization.svg"
            result = realize_material_capability_pack(self.pack, target)

            self.assertEqual(result["schema"], REALIZATION_SCHEMA)
            self.assertEqual(result["truth_status"], "OBSERVED_GENERATED_NATIVE_MATERIAL_CAPABILITY_CREATION")
            self.assertTrue(target.is_file())
            self.assertEqual(result["output"]["format"], "svg")
            self.assertEqual(result["output"]["mime"], "image/svg+xml")
            self.assertTrue(result["output"]["transparent"])
            self.assertEqual(result["source"]["pack_id"], self.pack["id"])
            self.assertEqual(set(result["source"]["selected_capabilities"]), {
                "material-entry", "material-family", "sprite-candidate", "recipe", "pattern"
            })

            text = target.read_text(encoding="utf-8")
            self.assertIn("axm.uc.material-capability-realization/v0.1", text)
            self.assertIn("rust-corrosion", text)
            self.assertIn("mix-blend-mode:overlay", text)
            self.assertIn("axm-sprite-window", text)

            feedback = validate_realization_feedback(result["feedback"], self.pack)
            self.assertEqual(feedback["consumer"], REALIZER_CONSUMER)
            self.assertEqual(len(feedback["events"]), 5)
            self.assertEqual({event["action"] for event in feedback["events"]}, {"reused"})
            self.assertEqual({event["outcome"] for event in feedback["events"]}, {"PASS"})
            self.assertEqual({event["derivedIds"][0] for event in feedback["events"]}, {result["id"]})
            self.assertTrue(all(event["evidence"]["svgArtifactGenerated"] for event in feedback["events"]))
            self.assertTrue(all(event["evidence"]["producerPixelsRendered"] is False for event in feedback["events"]))

    def test_realization_is_path_independent_and_deterministic(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            first = realize_material_capability_pack(self.pack, Path(directory) / "a.svg")
            second = realize_material_capability_pack(self.pack, Path(directory) / "b.svg")
            self.assertEqual(first["id"], second["id"])
            self.assertEqual(first["output"]["sha256"], second["output"]["sha256"])
            self.assertEqual(first["output"]["bytes"], second["output"]["bytes"])
            self.assertEqual(first["feedback"], second["feedback"])

    def test_recipe_change_changes_native_creation_output(self) -> None:
        original = build_material_capability_svg(self.pack)
        changed_pack = copy.deepcopy(self.pack)
        recipe = next(row for row in changed_pack["capabilities"] if row["kind"] == "recipe")
        recipe["payload"]["recipe"]["layers"][1]["opacity"] = 0.19
        # Recompute capability and pack identities exactly as the v0.18 contract requires.
        from axm_uc import material_capability_exchange as exchange
        recipe["id"] = exchange._capability_identity(recipe["kind"], recipe["sourceId"], recipe["payload"])
        recipe["fingerprint"] = exchange._capability_fingerprint(recipe)
        basis = {
            "producer": changed_pack["producer"],
            "capabilities": [{"id": row["id"], "fingerprint": row["fingerprint"]} for row in changed_pack["capabilities"]],
        }
        changed_pack["fingerprint"] = exchange._fnv1a_js(exchange._stable_json(basis))
        changed_pack["id"] = f"material-capability-pack-{changed_pack['fingerprint']}"
        changed = build_material_capability_svg(changed_pack)
        self.assertNotEqual(original["id"], changed["id"])
        self.assertNotEqual(original["svg"], changed["svg"])

    def test_multiple_same_kind_requires_explicit_selection(self) -> None:
        duplicate = copy.deepcopy(self.pack)
        extra = copy.deepcopy(next(row for row in duplicate["capabilities"] if row["kind"] == "pattern"))
        extra["sourceId"] = "pattern-extra"
        extra["payload"]["pattern"]["id"] = "pattern-extra"
        from axm_uc import material_capability_exchange as exchange
        extra["id"] = exchange._capability_identity(extra["kind"], extra["sourceId"], extra["payload"])
        extra["fingerprint"] = exchange._capability_fingerprint(extra)
        duplicate["capabilities"].append(extra)
        basis = {
            "producer": duplicate["producer"],
            "capabilities": [{"id": row["id"], "fingerprint": row["fingerprint"]} for row in duplicate["capabilities"]],
        }
        duplicate["fingerprint"] = exchange._fnv1a_js(exchange._stable_json(basis))
        duplicate["id"] = f"material-capability-pack-{duplicate['fingerprint']}"
        with self.assertRaises(MaterialCapabilityRealizationError):
            build_material_capability_svg(duplicate)

    def test_feedback_tamper_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            result = realize_material_capability_pack(self.pack, Path(directory) / "a.svg")
            tampered = copy.deepcopy(result["feedback"])
            tampered["events"][0]["evidence"]["producerPixelsRendered"] = True
            with self.assertRaises(MaterialCapabilityRealizationError):
                validate_realization_feedback(tampered, self.pack)


if __name__ == "__main__":
    unittest.main()

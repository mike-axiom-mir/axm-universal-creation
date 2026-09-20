from __future__ import annotations

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.direction_router import compile_direction_contract, route_direction
from axm_uc.machine import UniversalCreationMachine


MORPHTILE_PROMPT = (
    "Build a high-quality 3D MorphTile demonstration with a human, cheap tracked "
    "hand controls, a TV/world, an AI collaborator, editable construction and reusable assets."
)


class DirectionRouterTests(unittest.TestCase):
    def test_morphtile_language_becomes_explicit_direction_contract(self):
        contract = compile_direction_contract({"prompt": MORPHTILE_PROMPT})
        self.assertEqual(contract["medium"], "3d")
        self.assertEqual(contract["dimensionality"], "3d")
        self.assertEqual(contract["quality_bar"], "high")
        self.assertEqual(contract["editability"], "required")
        self.assertEqual(contract["reusable_assets"], "required")
        self.assertTrue(contract["interaction"]["required"])
        self.assertIn("tracked hand controls", contract["interaction"]["details"])
        self.assertIn("AI collaborator", contract["interaction"]["details"])

    def test_paintgun_is_visible_but_cannot_satisfy_rich_3d_direction(self):
        result = route_direction(ROOT, {"prompt": MORPHTILE_PROMPT})
        self.assertEqual(result["type"], "DIRECTION_HOLD")
        routes = {row["capability_id"]: row for row in result["decision"]["candidate_routes"]}
        paintgun = routes["AXM-CAP-PAINTGUN-SPECIALIST"]
        self.assertEqual(paintgun["state"], "COMPATIBLE_BUT_INSUFFICIENT")
        self.assertIn("medium:3d", paintgun["missing_requirements"])
        self.assertIn("tracked-input", result["decision"]["production_graph"]["missing_requirements"])
        self.assertIn("ai-collaboration", result["decision"]["production_graph"]["missing_requirements"])
        self.assertIn("AXM-CAP-GENERATE-SHAPE-RECIPE-3D", routes)
        self.assertEqual(result["decision"]["production_graph"]["steps"][0]["capability_id"], "AXM-CAP-GENERATE-SHAPE-RECIPE-3D")

    def test_create_without_internal_kind_returns_honest_direction_hold(self):
        result = UniversalCreationMachine(ROOT).create({"prompt": MORPHTILE_PROMPT})
        self.assertEqual(result["type"], "DIRECTION_HOLD")
        self.assertNotEqual(result.get("capability"), "AXM-CAP-PAINTGUN-SPECIALIST")

    def test_sufficient_exact_route_executes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "direction.txt"
            result = route_direction(ROOT, {
                "prompt": "Create an editable text document",
                "kind": "text-file",
                "inputs": {"path": str(target), "content": "direction preserved\n"},
                "direction_contract": {
                    "deliverables": ["text file"],
                    "medium": "text",
                    "dimensionality": "not-applicable",
                    "editability": "required",
                    "verification": [],
                    "ambiguity": [],
                },
            })
            self.assertEqual(result["type"], "DIRECTION_RESULT")
            self.assertEqual(result["decision"]["exact_route"]["state"], "COMPATIBLE_AND_SUFFICIENT")
            self.assertEqual(target.read_text(encoding="utf-8"), "direction preserved\n")

    def test_complete_character_intent_can_infer_one_unique_live_route_without_internal_kind(self):
        recipe = {
            "schema": "axm.character-recipe/v0.1",
            "name": "Intent routed tree person",
            "character": {"race_id": "tree", "body_family": "rooted-small"},
            "form": {
                "schema": "axm.form-pattern/v0.1",
                "name": "Tree body",
                "parts": [{
                    "id": "body",
                    "role": "body",
                    "pattern": "loft",
                    "sections": [
                        {"at": 0.0, "radius": [0.20, 0.18]},
                        {"at": 0.8, "radius": [0.28, 0.22]},
                        {"at": 1.2, "radius": [0.18, 0.16]}
                    ],
                    "material": {"color": "#76502FFF", "metallic": 0.0, "roughness": 0.8}
                }]
            }
        }
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "character.glb"
            result = UniversalCreationMachine(ROOT).create({
                "prompt": "Create a complete editable reusable static 3D character from this character recipe",
                "inputs": {"path": str(target), "recipe": recipe},
            })
            self.assertEqual(result["type"], "DIRECTION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-GENERATE-CHARACTER-RECIPE-3D")
            self.assertEqual(result["decision"]["requested_kind"], None)
            self.assertEqual(result["decision"]["inferred_kind"], "character-recipe-asset")
            self.assertEqual(
                result["decision"]["route_selection"],
                "unique-best-installed-route-from-direction-and-complete-inputs",
            )
            self.assertTrue(target.is_file())
            self.assertTrue(Path(result["result"]["creator_source"]["path"]).is_file())

    def test_temporary_candidate_repairs_in_isolation_without_canon_change(self):
        source = json.loads((ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json").read_text(encoding="utf-8"))
        failed = copy.deepcopy(source)
        failed["id"] = "AXM-CAP-TEMPORARY-MARKDOWN-FAILED"
        failed["tests"][0]["expect"]["file_text"] = "deliberate mismatch\n"
        repaired = copy.deepcopy(source)
        repaired["id"] = "AXM-CAP-TEMPORARY-MARKDOWN-REPAIRED"
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "artifact.md"
            result = route_direction(ROOT, {
                "prompt": "Create an editable Markdown document",
                "candidate_instance": {
                    "path": str(Path(td) / "instance"),
                    "manifests": [failed, repaired],
                    "execution_inputs": {"path": str(output), "content": "# isolated\n"},
                    "disposition": "retain-recipe-outside-canon",
                },
            })
            instance = result["candidate_instance"]
            self.assertEqual(result["type"], "DIRECTION_HOLD")
            self.assertEqual(instance["status"], "HOLD_ARTIFACT_NOT_INDEPENDENTLY_VERIFIED")
            self.assertEqual(instance["repair_attempt_count"], 1)
            self.assertFalse(instance["attempts"][0]["passed"])
            self.assertTrue(instance["attempts"][1]["passed"])
            self.assertTrue(instance["canonical_live_unchanged"])
            self.assertFalse(instance["installed"])
            self.assertFalse(instance["registered"])
            self.assertEqual(output.read_text(encoding="utf-8"), "# isolated\n")
            self.assertTrue((Path(instance["workspace"]) / "instance-receipt.json").is_file())


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class CreationDecompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.machine = UniversalCreationMachine(ROOT)

    def test_identifier_request_surfaces_explicit_atom_with_evidence(self):
        plan = self.machine.plan(
            {
                "kind": "identifier",
                "direction": "create a stable identifier",
            },
            per_level=6,
        )
        self.assertEqual(plan["type"], "CREATION_DECOMPOSITION")
        self.assertEqual(plan["truth_status"], "DETERMINISTIC_LEXICAL_BASELINE")
        atom_hits = plan["registry_matches"]["atom"]
        ids = {hit["id"] for hit in atom_hits}
        self.assertIn("AXM-00-FOUNDATION-A-001-identifier", ids)
        identifier = next(hit for hit in atom_hits if hit["id"] == "AXM-00-FOUNDATION-A-001-identifier")
        self.assertIn("identifier", identifier["evidence"]["name"])
        self.assertTrue(identifier["phrase_match"])

    def test_json_file_reports_exact_live_capability_coverage(self):
        plan = self.machine.plan(
            {
                "kind": "json-file",
                "direction": "create an inspectable JSON file",
                "inputs": {"path": "creations/example.json", "value": {"hello": "world"}},
            }
        )
        exact = [hit for hit in plan["live_capability_coverage"] if hit["exact_handle_match"]]
        self.assertTrue(exact)
        self.assertEqual(exact[0]["id"], "AXM-CAP-WRITE-JSON")
        self.assertTrue(exact[0]["ready_with_supplied_inputs"])
        self.assertEqual(exact[0]["missing_required_inputs"], [])
        self.assertEqual(plan["gap"]["status"], "covered")
        self.assertIsNone(plan["gap"]["smallest_visible_gap"])

    def test_exact_project_route_with_missing_files_is_an_input_gap_not_coverage(self):
        plan = self.machine.plan(
            {
                "kind": "software-project",
                "direction": "create a playable local RTS prototype",
                "inputs": {"path": "creations/rts"},
            }
        )
        exact = next(hit for hit in plan["live_capability_coverage"] if hit["exact_handle_match"])
        self.assertEqual(exact["id"], "AXM-CAP-WRITE-PROJECT")
        self.assertFalse(exact["ready_with_supplied_inputs"])
        self.assertEqual(exact["missing_required_inputs"], ["files"])
        self.assertEqual(exact["route_status"], "EXACT_ROUTE_INPUTS_INCOMPLETE")
        self.assertEqual(plan["gap"]["status"], "input-gap")
        self.assertEqual(plan["gap"]["truth_status"], "EXACT_ROUTE_PRESENT_REQUIRED_INPUTS_MISSING")
        self.assertEqual(plan["gap"]["smallest_visible_gap"]["kind"], "missing-required-inputs")

    def test_mesh_request_uses_existing_component_and_organ_anatomy(self):
        plan = self.machine.plan(
            {
                "kind": "mesh-file",
                "direction": "create and process a 3D mesh",
                "constraints": {"inspectable": True},
            },
            per_level=8,
        )
        component_names = [str(hit["name"]).casefold() for hit in plan["registry_matches"]["component"]]
        organ_names = [str(hit["name"]).casefold() for hit in plan["registry_matches"]["organ"]]
        self.assertTrue(any("mesh" in name for name in component_names))
        self.assertTrue(any("mesh" in name or "mesh" in hit["id"].casefold() for name, hit in zip(organ_names, plan["registry_matches"]["organ"])))
        self.assertEqual(plan["gap"]["status"], "visible-gap")
        self.assertEqual(plan["gap"]["truth_status"], "HYPOTHESIS")

    def test_unroutable_creation_gap_embeds_registry_decomposition(self):
        result = self.machine.create(
            {
                "kind": "mesh-file",
                "direction": "create a reusable mesh",
                "inputs": {"name": "test-mesh"},
            }
        )
        self.assertEqual(result["type"], "CAPABILITY_GAP")
        self.assertEqual(result["decomposition"]["type"], "CREATION_DECOMPOSITION")
        self.assertTrue(result["decomposition"]["registry_matches"]["component"])


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine


class MachineTests(unittest.TestCase):
    def test_inspection_exposes_new_standalone_capability_growth_without_inflated_proof(self):
        growth = UniversalCreationMachine(ROOT).inspect()["standalone_capability_growth"]
        self.assertEqual(growth["mixed_project"]["maximum_files"], 256)
        self.assertFalse(growth["mixed_project"]["runtime_or_semantic_behavior_proven"])
        self.assertEqual(growth["portable_bundle"]["operations"], ["pack", "inspect", "unpack"])
        self.assertFalse(growth["portable_bundle"]["runtime_compatibility_proven"])
        self.assertEqual(growth["state_machine"]["missing_transition_behavior"], "HOLD_NO_DECLARED_TRANSITION")
        self.assertFalse(growth["state_machine"]["effects_executed"])
        self.assertEqual(growth["procedural_media"]["operations"], ["png", "wav"])
        self.assertTrue(growth["procedural_media"]["container_and_payload_reverified_after_publish"])
        self.assertFalse(growth["procedural_media"]["appearance_or_audio_quality_proven"])
        self.assertEqual(growth["browser_game"]["schema"], "axm.browser-arena/v0.1")
        self.assertEqual(growth["browser_game"]["runtime_dependencies"], [])
        self.assertFalse(growth["browser_game"]["browser_execution_observed"])
        self.assertTrue(growth["creation_growth"]["uses_415_organ_census"])
        self.assertFalse(growth["creation_growth"]["automatic_source_invention"])
        self.assertEqual(growth["procedural_3d"]["container"], "glTF 2.0 binary GLB")
        self.assertFalse(growth["procedural_3d"]["rendered_appearance_or_host_compatibility_proven"])

    def test_live_creation_routes_and_writes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "hello.txt"
            result = UniversalCreationMachine(ROOT).create({
                "kind": "text-file",
                "direction": "create exact text",
                "inputs": {"path": str(target), "content": "hello\n"},
            })
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(target.read_text(encoding="utf-8"), "hello\n")

    def test_unsatisfied_request_emits_structured_directional_gap(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "markdown-file",
            "direction": "create editable Markdown",
            "inputs": {"path": "creations/x.md", "content": "# x"},
        })
        self.assertEqual(result["type"], "CAPABILITY_GAP")
        self.assertEqual(result["directional_outcome"], "create editable Markdown")
        self.assertEqual(result["truth_status"], "HYPOTHESIS")
        self.assertTrue(result["existing_partial_coverage"])

    def test_exact_route_missing_files_exposes_explicit_local_provider_bridge(self):
        result = UniversalCreationMachine(ROOT).create({
            "kind": "software-project",
            "direction": "create a playable local RTS prototype",
            "inputs": {"path": "creations/rts"},
        })
        self.assertEqual(result["type"], "CAPABILITY_INPUT_GAP")
        self.assertEqual(result["truth_status"], "ROUTE_PRESENT_REQUIRED_INPUTS_MISSING")
        self.assertEqual(result["route"], "AXM-CAP-WRITE-PROJECT")
        self.assertEqual(result["missing_required_inputs"], ["files"])
        bridge = result["local_provider_bridge"]
        self.assertEqual(bridge["status"], "READY_FOR_EXPLICIT_LOCAL_PROVIDER_SELECTION")
        self.assertFalse(bridge["automatic_call_made"])
        self.assertEqual(bridge["request"]["kind"], "provider-backed-project")

    def test_candidate_can_be_tested_and_build_debris_is_cleaned(self):
        candidate = ROOT / "capabilities/candidates/AXM-CAP-WRITE-MARKDOWN.json"
        result = UniversalCreationMachine(ROOT).test_candidate(candidate)
        self.assertTrue(result["passed"])
        self.assertTrue(result["build_debris_cleaned"])
        self.assertFalse((ROOT / ".axm-build").exists())


if __name__ == "__main__":
    unittest.main()

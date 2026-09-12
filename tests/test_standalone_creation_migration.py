from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.capabilities import CapabilityStore
from axm_uc.decompose import CreationDecomposer
from axm_uc.registry import Registry


RECOVERED_CAPABILITIES = {
    "AXM-CAP-BIND-HOST-EVIDENCE",
    "AXM-CAP-BUILD-OFFLINE-BROWSER-GAME",
    "AXM-CAP-DETERMINISTIC-STATE-MACHINE",
    "AXM-CAP-GENERATE-PROCEDURAL-3D",
    "AXM-CAP-GENERATE-PROCEDURAL-MEDIA",
    "AXM-CAP-GROW-CREATION-WITH-ORGAN",
    "AXM-CAP-LOCAL-CREATION-PROVIDER",
    "AXM-CAP-PORTABLE-CREATION-BUNDLE",
    "AXM-CAP-WRITE-MIXED-PROJECT",
}


class StandaloneCreationMigrationTests(unittest.TestCase):
    def setUp(self):
        self.store = CapabilityStore(ROOT)

    def test_all_recovered_capabilities_are_live_and_have_known_entrypoints(self):
        live = {str(manifest.get("id")): manifest for manifest in self.store.live()}
        self.assertTrue(RECOVERED_CAPABILITIES.issubset(live))
        for capability_id in sorted(RECOVERED_CAPABILITIES):
            manifest = live[capability_id]
            implementation = manifest.get("implementation", {})
            self.assertIn(
                implementation.get("kind"),
                {"DETERMINISTIC_SOURCE", "LOCAL_PROVIDER_BOUNDARY", "EXTERNAL_EVIDENCE_BOUNDARY"},
            )
            self.assertTrue(str(implementation.get("entrypoint", "")).startswith("builtin:"))

    def test_boundary_capabilities_remain_explicit_and_inspectable_without_calling_a_provider(self):
        provider = self.store.by_id("AXM-CAP-LOCAL-CREATION-PROVIDER")
        self.assertIsNotNone(provider)
        self.assertEqual(provider["implementation"]["kind"], "LOCAL_PROVIDER_BOUNDARY")
        result = self.store.invoke(provider, {"operation": "inspect"})
        self.assertFalse(result.get("automatic_call_made", False))
        self.assertFalse(result.get("cloud_control_plane_allowed", False))

        evidence = self.store.by_id("AXM-CAP-BIND-HOST-EVIDENCE")
        self.assertIsNotNone(evidence)
        self.assertEqual(evidence["implementation"]["kind"], "EXTERNAL_EVIDENCE_BOUNDARY")
        inspected = self.store.invoke(evidence, {"operation": "inspect"})
        self.assertIn("truth_status", inspected)

    def test_operation_specific_required_inputs_are_enforced(self):
        provider = self.store.by_id("AXM-CAP-LOCAL-CREATION-PROVIDER")
        self.assertIsNotNone(provider)
        self.assertEqual(
            self.store.missing_required_inputs(provider, {"operation": "create"}),
            ["goal", "path", "provider"],
        )
        self.assertEqual(
            self.store.missing_required_inputs(
                provider,
                {"operation": "create", "goal": "x", "path": "creations/x", "provider": {}},
            ),
            [],
        )

    def test_decomposition_reports_exact_route_input_gap_instead_of_false_coverage(self):
        decomposer = CreationDecomposer(Registry(ROOT), self.store)
        result = decomposer.decompose(
            {
                "kind": "provider-backed-project",
                "direction": "create one project through an explicitly selected local provider",
                "inputs": {"operation": "create"},
            }
        )
        gap = result["gap"]
        self.assertEqual(gap["status"], "input-gap")
        self.assertEqual(gap["truth_status"], "EXACT_ROUTE_PRESENT_REQUIRED_INPUTS_MISSING")
        self.assertEqual(gap["route"], "AXM-CAP-LOCAL-CREATION-PROVIDER")
        self.assertEqual(gap["smallest_visible_gap"]["missing_required_inputs"], ["goal", "path", "provider"])


if __name__ == "__main__":
    unittest.main()

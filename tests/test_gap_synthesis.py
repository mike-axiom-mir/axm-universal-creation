from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.gap_synthesis import GapSynthesisError, analyze_creation_gap, compile_gap_proposal
from axm_uc.machine import UniversalCreationMachine


class GapSynthesisTests(unittest.TestCase):
    def setUp(self):
        self.machine = UniversalCreationMachine(ROOT)

    @staticmethod
    def _note_request(path: str = "creations/requested.note") -> dict:
        return {
            "kind": "portable-note-file",
            "direction": "create an exact portable note",
            "inputs": {"path": path, "content": "# Exact request\n\nOne observed fixture.\n"},
        }

    def test_unroutable_creation_exposes_ready_gap_synthesis_without_inflating_live_coverage(self):
        result = self.machine.create(self._note_request())
        self.assertEqual(result["type"], "CAPABILITY_GAP")
        synthesis = result["gap_synthesis"]
        self.assertEqual(synthesis["status"], "SYNTHESIS_READY_UNIQUE_STRUCTURAL_BRIDGE")
        self.assertEqual(synthesis["selected_bridge"]["capability_id"], "AXM-CAP-WRITE-TEXT")
        self.assertFalse(synthesis["semantic_equivalence_proven"])
        self.assertIsNone(self.machine.capabilities.route("portable-note-file"))

    def test_existing_detached_candidate_is_reused_before_duplicate_synthesis(self):
        analysis = analyze_creation_gap(ROOT, {
            "kind": "markdown-file",
            "inputs": {"path": "creations/requested.md", "content": "# Existing\n"},
        })
        self.assertEqual(analysis["status"], "REUSE_EXISTING_CANDIDATE_BEFORE_SYNTHESIS")
        self.assertEqual(analysis["existing_candidates"][0]["capability_id"], "AXM-CAP-WRITE-MARKDOWN")
        proposed = compile_gap_proposal(ROOT, analysis["request"])
        self.assertIsNone(proposed["proposal"])

    def test_analyze_is_read_only_and_binds_exact_request_digest(self):
        with tempfile.TemporaryDirectory() as td:
            requested = Path(td) / "must-not-exist.md"
            creation = self.machine.create({
                "kind": "analyze-creation-gap",
                "inputs": {"operation": "analyze", "request": self._note_request(str(requested))},
            })
            self.assertEqual(creation["type"], "CREATION_RESULT", creation)
            result = creation["result"]
            self.assertEqual(result["operation"], "analyze")
            self.assertEqual(result["schema"], "axm.creation-gap-analysis/v0.1")
            self.assertTrue(result["analysis_digest"].startswith("sha256:"))
            self.assertFalse(requested.exists())

    def test_same_gap_compiles_to_same_closed_proposal(self):
        request = self._note_request()
        first = compile_gap_proposal(ROOT, request)
        second = compile_gap_proposal(ROOT, request)
        self.assertEqual(first["status"], "DETACHED_PROPOSAL_READY")
        self.assertEqual(first["proposal_digest"], second["proposal_digest"])
        self.assertEqual(first["proposal"], second["proposal"])
        self.assertEqual(first["proposal"]["authority"], {
            "execute": False,
            "install": False,
            "register": False,
            "promote": False,
            "merge": False,
            "canon": False,
            "permissions": False,
        })
        entry = json.loads(first["proposal"]["files"]["capability.json"])
        self.assertEqual(entry["implementation"]["delegate"], "AXM-CAP-WRITE-TEXT")
        self.assertTrue(entry["tests"][0]["inputs"]["path"].startswith("${TEST_DIR}/"))

        with self.assertRaises(GapSynthesisError):
            compile_gap_proposal(ROOT, request, candidate_id="AXM-CAP-WRITE-TEXT")

    def test_materialize_and_test_runs_request_shaped_fixture_without_using_requested_destination(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-destination.md"
            target = parent / "detached-candidate"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(target),
                    "request": self._note_request(str(requested)),
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            self.assertEqual(explored["status"], "TESTED_DETACHED_CANDIDATE")
            self.assertEqual(explored["test"]["kind_test"]["evidence_strength"], "DECLARED_CANDIDATE_TESTS_EXECUTED")
            self.assertFalse(explored["original_request_destination_used"])
            self.assertFalse(requested.exists())
            self.assertTrue((target / "gap-analysis.json").is_file())
            self.assertTrue((target / "capability.json").is_file())
            self.assertFalse(explored["installed"])
            self.assertFalse(explored["admission_requested"])
            self.assertIsNone(explored["live_route_after_experiment"])
            self.assertIsNone(self.machine.capabilities.route("portable-note-file"))

    def test_covered_and_unsupported_requests_hold_without_creating_targets(self):
        covered = analyze_creation_gap(ROOT, {
            "kind": "text-file",
            "inputs": {"path": "creations/a.txt", "content": "a"},
        })
        self.assertEqual(covered["status"], "COVERED_NO_SYNTHESIS_NEEDED")
        self.assertEqual(covered["exact_live_route"]["capability_id"], "AXM-CAP-WRITE-TEXT")

        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "unsupported"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(target),
                    "request": {"kind": "mesh-file", "inputs": {"vertices": []}},
                },
            })
            held = result["result"]
            self.assertEqual(held["status"], "HOLD_NO_SUPPORTED_SYNTHESIS_BLUEPRINT")
            self.assertFalse(held["passed"])
            self.assertFalse(held["target_created"])
            self.assertFalse(target.exists())

    def test_ambiguous_structural_bridges_hold_until_one_observed_id_is_explicit(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live = root / "capabilities/live"
            live.mkdir(parents=True)
            base = json.loads((ROOT / "capabilities/live/AXM-CAP-WRITE-TEXT.json").read_text(encoding="utf-8"))
            first = dict(base)
            first.update({"id": "AXM-CAP-TEXT-A", "version": "1.0.0"})
            second = dict(base)
            second.update({"id": "AXM-CAP-TEXT-B", "version": "1.0.0"})
            (live / "a.json").write_text(json.dumps(first), encoding="utf-8")
            (live / "b.json").write_text(json.dumps(second), encoding="utf-8")

            request = self._note_request()
            analysis = analyze_creation_gap(root, request)
            self.assertEqual(analysis["status"], "HOLD_AMBIGUOUS_STRUCTURAL_BRIDGE")
            self.assertIsNone(analysis["selected_bridge"])
            held = compile_gap_proposal(root, request)
            self.assertIsNone(held["proposal"])
            selected = compile_gap_proposal(root, request, bridge_capability_id="AXM-CAP-TEXT-B")
            self.assertEqual(selected["selected_bridge"]["capability_id"], "AXM-CAP-TEXT-B")

            with self.assertRaises(GapSynthesisError):
                compile_gap_proposal(root, request, bridge_capability_id="AXM-CAP-NOT-OBSERVED")

    def test_inspection_exposes_potential_and_truth_boundary(self):
        inspection = self.machine.inspect()
        summary = inspection["gap_synthesis"]
        self.assertIn("axm.blueprint.exact-utf8-file-route-alias/v0.1", summary["implemented_blueprints"])
        self.assertFalse(summary["semantic_source_invention"])
        self.assertFalse(summary["automatic_admission"])
        self.assertEqual(len(inspection["live_capabilities"]), 14)


if __name__ == "__main__":
    unittest.main()

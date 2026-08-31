from __future__ import annotations

import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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

    @staticmethod
    def _verified_template_request(path: str = "creations/requested-template-site") -> dict:
        return {
            "kind": "verified-templated-static-web-project",
            "direction": "create an exact templated site and independently verify its emitted digest receipt",
            "inputs": {
                "path": path,
                "template": {
                    "id": "example.verified-template-site",
                    "version": "0.1.0",
                    "project_type": "static-web",
                    "files": {
                        "index.html": "<!doctype html><html><body><h1>[[AXM:title]]</h1><link rel=\"stylesheet\" href=\"style.css\"></body></html>\n",
                        "style.css": "body { color: [[AXM:color]]; }\n",
                    },
                },
                "variables": {"title": "Composite creation", "color": "#223344"},
                "checks": [{"type": "contains", "path": "index.html", "text": "Composite creation"}],
            },
        }

    @staticmethod
    def _verified_organ_request(path: str = "creations/requested-organ-site") -> dict:
        request = json.loads(
            (ROOT / "examples/requests/create_reusable_organ_site.json").read_text(encoding="utf-8")
        )
        request["kind"] = "verified-reusable-organ-static-web-project"
        request["direction"] = "assemble exact executable organs and independently verify their emitted digest receipt"
        request["inputs"]["path"] = path
        request["inputs"]["replace"] = False
        return request

    @classmethod
    def _verified_organ_report_request(
        cls,
        path: str = "creations/requested-organ-report-site",
        report_path: str = "creations/requested-organ-verification.json",
    ) -> dict:
        request = cls._verified_organ_request(path)
        request["kind"] = "verified-reusable-organ-project-with-json-report"
        request["direction"] = "assemble exact executable organs, verify their receipt, and persist that exact evidence as JSON"
        request["inputs"]["report_path"] = report_path
        return request

    @staticmethod
    def _verified_files_report_request(
        path: str = "creations/requested-files-site",
        report_path: str = "creations/requested-files-verification.json",
    ) -> dict:
        return {
            "kind": "verified-exact-files-project-with-json-report",
            "direction": "create exact files, independently verify them, and persist the exact evidence as JSON",
            "inputs": {
                "path": path,
                "files": {"README.md": "# Reuse first\n"},
                "project_type": "generic",
                "checks": [{"type": "contains", "path": "README.md", "text": "Reuse first"}],
                "replace": False,
                "report_path": report_path,
            },
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

    def test_template_gap_compiles_deterministic_two_capability_recipe(self):
        request = self._verified_template_request()
        analysis = analyze_creation_gap(ROOT, request)
        self.assertEqual(analysis["status"], "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN")
        self.assertEqual(
            analysis["selected_blueprint"]["blueprint"],
            "axm.blueprint.bounded-project-recipe-graph/v0.1",
        )
        self.assertEqual(
            [row["ref"] for row in analysis["selected_blueprint"]["dependencies"]],
            [
                "AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE@0.2.0",
                "AXM-CAP-VERIFY-PROJECT@0.6.0",
            ],
        )

        first = compile_gap_proposal(ROOT, request)
        second = compile_gap_proposal(ROOT, request)
        self.assertEqual(first["status"], "DETACHED_COMPOSITE_PROPOSAL_READY")
        self.assertEqual(first["proposal_digest"], second["proposal_digest"])
        manifest = json.loads(first["proposal"]["files"]["capability.json"])
        self.assertEqual(manifest["implementation"]["kind"], "DETERMINISTIC_COMPOSITE")
        self.assertEqual(
            [step["capability"] for step in manifest["implementation"]["steps"]],
            ["AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE", "AXM-CAP-VERIFY-PROJECT"],
        )
        digest_binding = manifest["implementation"]["steps"][1]["inputs"]["expected_file_digests"]
        self.assertEqual(digest_binding, {
            "from": "steps.produce.files",
            "transform": "file-digest-map",
        })
        self.assertTrue(manifest["tests"][0]["inputs"]["path"].startswith("${TEST_DIR}/"))
        self.assertFalse(first["proposal"]["authority"]["execute"])

        with self.assertRaises(GapSynthesisError):
            compile_gap_proposal(ROOT, request, candidate_id="AXM-CAP-VERIFY-PROJECT")

    def test_template_composite_materializes_and_tests_full_chain_without_original_destination(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-must-not-exist"
            target = parent / "detached-composite"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(target),
                    "request": self._verified_template_request(str(requested)),
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            self.assertEqual(explored["status"], "TESTED_DETACHED_CANDIDATE")
            self.assertFalse(requested.exists())
            self.assertIsNone(explored["selected_bridge"])
            self.assertEqual(
                explored["selected_blueprint"]["blueprint"],
                "axm.blueprint.bounded-project-recipe-graph/v0.1",
            )
            candidate_test = explored["test"]["kind_test"]["capability_test"]["tests"][0]
            self.assertTrue(candidate_test["result"]["production"]["published"])
            self.assertTrue(candidate_test["result"]["verification"]["passed"])
            digest_check = next(
                row
                for row in candidate_test["result"]["verification"]["checks"]
                if row["type"] == "expected-file-digests"
            )
            self.assertTrue(digest_check["passed"])
            self.assertTrue(all(row["passed"] for row in digest_check["files"]))
            self.assertIsNone(self.machine.capabilities.route("verified-templated-static-web-project"))

    def test_organ_gap_discovers_exact_producer_and_compiles_same_recipe(self):
        request = self._verified_organ_request()
        analysis = analyze_creation_gap(ROOT, request)
        self.assertEqual(analysis["status"], "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN")
        selected = analysis["selected_blueprint"]
        self.assertEqual(selected["producer"]["profile"], "exact-executable-organ-assembly")
        self.assertEqual(
            [row["ref"] for row in selected["dependencies"]],
            [
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT@0.3.0",
                "AXM-CAP-VERIFY-PROJECT@0.6.0",
            ],
        )
        self.assertEqual(selected["producer_preview_evidence"]["executable_organ_resolution"]["referenced_package_count"], 3)

        first = compile_gap_proposal(ROOT, request)
        second = compile_gap_proposal(ROOT, request)
        self.assertEqual(first["proposal_digest"], second["proposal_digest"])
        self.assertEqual(first["proposal"], second["proposal"])
        manifest = json.loads(first["proposal"]["files"]["capability.json"])
        self.assertEqual(
            [step["capability"] for step in manifest["implementation"]["steps"]],
            ["AXM-CAP-ASSEMBLE-ORGAN-PROJECT", "AXM-CAP-VERIFY-PROJECT"],
        )
        self.assertEqual(manifest["implementation"]["steps"][0]["id"], "produce")
        self.assertFalse(first["proposal"]["authority"]["install"])

    def test_organ_composite_materializes_full_exact_chain_without_original_destination(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-organ-must-not-exist"
            target = parent / "detached-organ-composite"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(target),
                    "request": self._verified_organ_request(str(requested)),
                },
            })
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            self.assertFalse(requested.exists())
            candidate_test = explored["test"]["kind_test"]["capability_test"]["tests"][0]
            production = candidate_test["result"]["production"]
            self.assertEqual(
                production["organ_assembly"]["dependency_order"],
                ["shell-organ", "theme-organ", "interaction-organ"],
            )
            self.assertEqual(production["executable_organ_resolution"]["referenced_package_count"], 3)
            self.assertTrue(candidate_test["result"]["verification"]["passed"])
            self.assertIsNone(self.machine.capabilities.route("verified-reusable-organ-static-web-project"))

    def test_organ_report_gap_discovers_and_compiles_exact_three_step_recipe(self):
        request = self._verified_organ_report_request()
        analysis = analyze_creation_gap(ROOT, request)
        selected = analysis["selected_blueprint"]
        self.assertEqual(analysis["status"], "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN")
        self.assertEqual(selected["goal"], "verified-project-with-json-report")
        self.assertEqual(selected["step_order"], ["produce", "verify", "report"])
        self.assertEqual(selected["step_count"], 3)
        self.assertEqual(selected["maximum_step_count"], 3)
        self.assertEqual(
            [row["ref"] for row in selected["dependencies"]],
            [
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT@0.3.0",
                "AXM-CAP-VERIFY-PROJECT@0.6.0",
                "AXM-CAP-WRITE-JSON@0.1.0",
            ],
        )

        first = compile_gap_proposal(ROOT, request)
        second = compile_gap_proposal(ROOT, request)
        self.assertEqual(first["proposal_digest"], second["proposal_digest"])
        manifest = json.loads(first["proposal"]["files"]["capability.json"])
        self.assertEqual(
            [step["capability"] for step in manifest["implementation"]["steps"]],
            [
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT",
                "AXM-CAP-VERIFY-PROJECT",
                "AXM-CAP-WRITE-JSON",
            ],
        )
        self.assertEqual(
            manifest["implementation"]["steps"][2]["inputs"]["value"],
            {"from": "steps.verify"},
        )
        self.assertEqual(
            manifest["tests"][0]["expect"]["json_file_equals_result"]["result_field"],
            "verification",
        )

    def test_organ_report_recipe_materializes_and_proves_exact_json_receipt(self):
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-organ-must-not-exist"
            requested_report = parent / "original-report-must-not-exist.json"
            target = parent / "detached-organ-report-composite"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(target),
                    "request": self._verified_organ_report_request(
                        str(requested),
                        str(requested_report),
                    ),
                },
            })
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            self.assertFalse(requested.exists())
            self.assertFalse(requested_report.exists())
            candidate_test = explored["test"]["kind_test"]["capability_test"]["tests"][0]
            self.assertTrue(candidate_test["result"]["verification"]["passed"])
            self.assertEqual(candidate_test["result"]["report"]["kind"], "json")
            self.assertTrue(candidate_test["json_file_result_check"]["passed"])
            self.assertIsNone(
                self.machine.capabilities.route("verified-reusable-organ-project-with-json-report")
            )

    def test_raw_files_report_recipe_reuses_shorter_verified_composite(self):
        request = self._verified_files_report_request()
        analysis = analyze_creation_gap(ROOT, request)
        selected = analysis["selected_blueprint"]
        self.assertEqual(selected["producer"]["profile"], "existing-verified-project-composite")
        self.assertEqual(selected["step_order"], ["produce", "report"])
        self.assertEqual(selected["step_count"], 2)
        self.assertTrue(selected["reuses_existing_verified_composite"])
        self.assertTrue(selected["path_selection"]["reuse_precedes_new_embodiment"])
        self.assertEqual(
            [(row["producer_profile"], row["step_count"]) for row in selected["candidate_paths"]],
            [("exact-project-files", 3), ("existing-verified-project-composite", 2)],
        )
        manifest = json.loads(
            compile_gap_proposal(ROOT, request)["proposal"]["files"]["capability.json"]
        )
        self.assertEqual(
            [step["capability"] for step in manifest["implementation"]["steps"]],
            ["AXM-CAP-BUILD-VERIFY-PROJECT", "AXM-CAP-WRITE-JSON"],
        )
        self.assertEqual(
            manifest["implementation"]["steps"][1]["inputs"]["value"],
            {"from": "steps.produce.verification"},
        )
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            requested = parent / "original-files-must-not-exist"
            requested_report = parent / "original-files-report-must-not-exist.json"
            result = self.machine.create({
                "kind": "explore-gap-candidate",
                "inputs": {
                    "operation": "materialize-and-test",
                    "path": str(parent / "detached-files-report-composite"),
                    "request": self._verified_files_report_request(
                        str(requested),
                        str(requested_report),
                    ),
                },
            })
            explored = result["result"]
            self.assertTrue(explored["passed"], explored)
            candidate_test = explored["test"]["kind_test"]["capability_test"]["tests"][0]
            self.assertTrue(candidate_test["json_file_result_check"]["passed"])
            self.assertFalse(requested.exists())
            self.assertFalse(requested_report.exists())

    def test_report_recipe_holds_on_missing_reporter_or_depth_overflow(self):
        request = self._verified_organ_report_request()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live = root / "capabilities/live"
            live.mkdir(parents=True)
            shutil.copytree(ROOT / "executable-organs", root / "executable-organs")
            for filename in (
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT.json",
                "AXM-CAP-VERIFY-PROJECT.json",
            ):
                shutil.copy2(ROOT / "capabilities/live" / filename, live / filename)
            missing = analyze_creation_gap(root, request)
            self.assertEqual(missing["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertEqual(
                missing["composite_candidates"][0]["missing_links"][0]["expected_ref"],
                "AXM-CAP-WRITE-JSON@0.1.0",
            )
            reporter = json.loads(
                (ROOT / "capabilities/live/AXM-CAP-WRITE-JSON.json").read_text(encoding="utf-8")
            )
            reporter["output_contract"]["format"] = "yaml"
            (live / "AXM-CAP-WRITE-JSON.json").write_text(
                json.dumps(reporter),
                encoding="utf-8",
            )
            drifted = analyze_creation_gap(root, request)
            self.assertEqual(drifted["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertIn(
                "JSON reporter dependency contract mismatch",
                drifted["composite_candidates"][0]["missing_links"][0]["reason"],
            )

        with patch("axm_uc.gap_synthesis.MAX_PROJECT_RECIPE_STEPS", 2):
            over_depth = analyze_creation_gap(ROOT, request)
            held = compile_gap_proposal(ROOT, request)
        self.assertEqual(over_depth["status"], "HOLD_RECIPE_DEPTH_EXCEEDED")
        self.assertIsNone(over_depth["selected_blueprint"])
        self.assertIsNone(held["proposal"])

    def test_organ_recipe_holds_on_missing_or_drifted_receipt_contract(self):
        request = self._verified_organ_request()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live = root / "capabilities/live"
            live.mkdir(parents=True)
            shutil.copytree(ROOT / "executable-organs", root / "executable-organs")
            verify = (ROOT / "capabilities/live/AXM-CAP-VERIFY-PROJECT.json").read_text(encoding="utf-8")
            (live / "verify.json").write_text(verify, encoding="utf-8")
            missing = analyze_creation_gap(root, request)
            self.assertEqual(missing["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertEqual(
                missing["composite_candidates"][0]["missing_links"][0]["expected_ref"],
                "AXM-CAP-ASSEMBLE-ORGAN-PROJECT@0.3.0",
            )

            assembler = json.loads(
                (ROOT / "capabilities/live/AXM-CAP-ASSEMBLE-ORGAN-PROJECT.json").read_text(encoding="utf-8")
            )
            assembler["output_contract"]["contains"].remove("files")
            (live / "assembler.json").write_text(json.dumps(assembler), encoding="utf-8")
            drifted = analyze_creation_gap(root, request)
            self.assertEqual(drifted["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertIn("contract mismatch", drifted["composite_candidates"][0]["missing_links"][0]["reason"])

    def test_ambiguous_producer_markers_and_unknown_organ_refs_hold(self):
        ambiguous = self._verified_template_request()
        ambiguous["inputs"]["assembly"] = self._verified_organ_request()["inputs"]["assembly"]
        analysis = analyze_creation_gap(ROOT, ambiguous)
        self.assertEqual(analysis["status"], "HOLD_AMBIGUOUS_COMPOSITE_RECIPE")
        self.assertIsNone(compile_gap_proposal(ROOT, ambiguous)["proposal"])

        unknown = self._verified_organ_request()
        unknown["inputs"]["assembly"]["organs"][0]["ref"] = "axm.web.missing@9.9.9"
        held = analyze_creation_gap(ROOT, unknown)
        self.assertEqual(held["status"], "HOLD_NO_SUPPORTED_SYNTHESIS_BLUEPRINT")
        self.assertIn("not installed", held["composite_request_issue"])

    def test_composite_blueprint_holds_when_exact_link_is_missing_or_ambiguous(self):
        request = self._verified_template_request()
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            live = root / "capabilities/live"
            live.mkdir(parents=True)
            template = (ROOT / "capabilities/live/AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE.json").read_text(encoding="utf-8")
            (live / "template.json").write_text(template, encoding="utf-8")
            missing = analyze_creation_gap(root, request)
            self.assertEqual(missing["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertEqual(
                missing["composite_candidates"][0]["missing_links"][0]["expected_ref"],
                "AXM-CAP-VERIFY-PROJECT@0.6.0",
            )
            self.assertIsNone(compile_gap_proposal(root, request)["proposal"])

            verify = json.loads((ROOT / "capabilities/live/AXM-CAP-VERIFY-PROJECT.json").read_text(encoding="utf-8"))
            (live / "verify-a.json").write_text(json.dumps(verify), encoding="utf-8")
            self.assertEqual(
                analyze_creation_gap(root, request)["status"],
                "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN",
            )

            broken_verify = json.loads(json.dumps(verify))
            del broken_verify["input_contract"]["properties"]["expected_file_digests"]
            (live / "verify-a.json").write_text(json.dumps(broken_verify), encoding="utf-8")
            broken = analyze_creation_gap(root, request)
            self.assertEqual(broken["status"], "HOLD_MISSING_COMPOSITE_LINK")
            self.assertIn("contract mismatch", broken["composite_candidates"][0]["missing_links"][0]["reason"])

            (live / "verify-a.json").write_text(json.dumps(verify), encoding="utf-8")
            (live / "verify-b.json").write_text(json.dumps(verify), encoding="utf-8")
            ambiguous = analyze_creation_gap(root, request)
            self.assertEqual(ambiguous["status"], "HOLD_AMBIGUOUS_COMPOSITE_LINK")
            self.assertIsNone(ambiguous["selected_blueprint"])

    def test_invalid_template_request_stays_on_unsupported_hold(self):
        request = self._verified_template_request()
        request["inputs"]["variables"] = {}
        analysis = analyze_creation_gap(ROOT, request)
        self.assertEqual(analysis["status"], "HOLD_NO_SUPPORTED_SYNTHESIS_BLUEPRINT")
        self.assertIn("template variables are missing", analysis["composite_request_issue"])
        self.assertIsNone(compile_gap_proposal(ROOT, request)["proposal"])

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
        self.assertIn("axm.blueprint.bounded-project-recipe-graph/v0.1", summary["implemented_blueprints"])
        self.assertEqual(
            [row["profile"] for row in summary["project_producer_profiles"]],
            [
                "strict-project-template",
                "exact-executable-organ-assembly",
                "interface-discovered-organ-assembly",
                "exact-project-files",
                "existing-verified-project-composite",
            ],
        )
        self.assertEqual(summary["closed_binding_transforms"], ["file-digest-map"])
        self.assertEqual(summary["closed_binding_edges"], ["file-digest-map", "exact-whole-object"])
        self.assertEqual(summary["maximum_project_recipe_steps"], 3)
        self.assertTrue(summary["reuse_precedes_new_embodiment"])
        self.assertFalse(summary["semantic_source_invention"])
        self.assertFalse(summary["automatic_admission"])
        self.assertEqual(len(inspection["live_capabilities"]), 25)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import hashlib
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.capabilities import CapabilityError, CapabilityStore
from axm_uc.profession_crew import operate_profession_crew
from axm_uc.procedural_3d import build_glb
from axm_uc.static_asset_target_evidence import PACKET_SCHEMA


class ProfessionTargetEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "capabilities/live", self.root / "capabilities/live")
        self.target = self.root / "creations/asset.glb"
        self.target.parent.mkdir()
        self.spec = {"schema": "axm.procedural-3d/v0.1", "name": "Target adapter fixture",
                     "primitives": [{"id": "body", "type": "box", "size": [2, 1, 3], "translation": [0, 0, 0],
                                     "material": {"color": "#446688FF", "metallic": 0.5, "roughness": 0.4}}]}
        self.target.write_bytes(build_glb(self.spec)["body"])
        self.packet = {"schema": PACKET_SCHEMA, "artifact_sha256": hashlib.sha256(self.target.read_bytes()).hexdigest(),
                       "target": {"engine": "Fixture Engine", "version": "1", "context": "RTS vehicle"},
                       "required_lanes": ["target_engine_import", "collision"],
                       "lanes": {"target_engine_import": {"status": "PASS", "evidence": [{"kind": "TESTED",
                           "source": "fixture://declared-import", "summary": "Supplied test fixture; no engine was launched."}]},
                           "collision": {"status": "NOT_TESTED"}}}

    def job(self):
        return {"operation": "run", "crew_id": "target-team", "run_id": "target-001", "work_type": "3d",
                "goal": "Check external target evidence without inventing actual target execution",
                "steps": [{"id": "target-check", "profession_id": "technical-artist", "action": {
                    "kind": "verify-static-asset-target", "inputs": {"path": str(self.target), "packet": copy.deepcopy(self.packet),
                    "target": copy.deepcopy(self.packet["target"]), "required_lanes": list(self.packet["required_lanes"])}}}]}

    def run_job(self, job=None):
        return operate_profession_crew(self.root, job or self.job())

    def state(self):
        return operate_profession_crew(self.root, {"operation": "inspect", "crew_id": "target-team"})

    def complete_job(self):
        job = self.job()
        job["steps"][0]["action"]["inputs"]["packet"]["lanes"]["collision"] = {
            "status": "PASS", "evidence": [{"kind": "TESTED", "source": "fixture://declared-collision",
                "summary": "Supplied test fixture only; adapter does not perform this collision test."}]}
        return job

    def test_live_adapter_route_and_read_only_behavior(self):
        store = CapabilityStore(self.root)
        manifest = store.route("verify-static-asset-target")
        self.assertIsNotNone(manifest)
        before = self.target.read_bytes()
        result = store.invoke(manifest, self.job()["steps"][0]["action"]["inputs"])
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["execution_scope"], "EXTERNAL_PACKET_VALIDATION_ONLY")
        self.assertFalse(result["independently_reproduced"])
        self.assertEqual(self.target.read_bytes(), before)

    def test_missing_collision_holds_and_names_owning_profession(self):
        result = self.run_job()
        self.assertEqual(result["status"], "HOLD_TARGET_EVIDENCE")
        self.assertIn({"lane": "collision", "profession_id": "gameplay-engineer", "reason": "REQUIRED_NOT_TESTED"}, result["handoff"]["requirements"])
        self.assertEqual(self.state()["practice"], {})

    def test_complete_packet_is_not_professional_experience_or_independent_test(self):
        result = self.run_job(self.complete_job())
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        observed = result["observations"][0]
        self.assertEqual(observed["evidence_origin"], "EXTERNAL_EVIDENCE_PACKET")
        self.assertFalse(observed["target_evidence"]["independently_reproduced"])
        self.assertEqual(result["professional_acceptance"], "NOT_TESTED")
        self.assertEqual(self.state()["practice"], {})
        verified = operate_profession_crew(self.root, {"operation": "verify", "crew_id": "target-team", "run_id": "target-001"})
        self.assertEqual(verified["status"], "PASS")
        self.assertFalse(verified["checks"][0]["target_evidence"]["independently_reproduced"])

    def test_required_contract_cannot_be_weakened_inside_packet(self):
        job = self.complete_job()
        packet = job["steps"][0]["action"]["inputs"]["packet"]
        packet["required_lanes"] = ["target_engine_import"]
        del packet["lanes"]["collision"]
        result = self.run_job(job)
        self.assertEqual(result["status"], "HOLD_TARGET_EVIDENCE")
        self.assertIn("REQUIRED_LANES_OMITTED", result["observations"][0]["target_evidence"]["finding_counts"])
        self.assertEqual(self.state()["practice"], {})

    def test_wrong_engine_version_or_context_cannot_be_accepted(self):
        for field in ["engine", "version", "context"]:
            with self.subTest(field=field):
                job = self.complete_job()
                job["run_id"] = field
                job["steps"][0]["action"]["inputs"]["packet"]["target"][field] = "different"
                result = self.run_job(job)
                self.assertEqual(result["status"], "HOLD_TARGET_EVIDENCE")
                self.assertIn("TARGET_CONTEXT_MISMATCH", result["observations"][0]["target_evidence"]["finding_counts"])

    def test_weak_visual_evidence_is_handed_to_art_director(self):
        job = self.complete_job()
        inputs = job["steps"][0]["action"]["inputs"]
        inputs["required_lanes"].append("lod_perceptual_equivalence")
        inputs["packet"]["required_lanes"].append("lod_perceptual_equivalence")
        inputs["packet"]["lanes"]["lod_perceptual_equivalence"] = {"status": "PASS", "evidence": [{"kind": "TESTED",
            "source": "fixture://triangle-count", "summary": "Source structure only, no visual observation."}]}
        result = self.run_job(job)
        self.assertEqual(result["status"], "HOLD_TARGET_EVIDENCE")
        self.assertTrue(any(r["profession_id"] == "art-director" for r in result["handoff"]["requirements"]))
        self.assertEqual(result["visual_quality"], "NOT_TESTED")

    def test_reported_optional_failure_remains_failure_without_training_credit(self):
        job = self.complete_job()
        job["steps"][0]["action"]["inputs"]["packet"]["lanes"]["target_device_performance"] = {"status": "FAIL"}
        result = self.run_job(job)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertTrue(any(r["profession_id"] == "graphics-engineer" for r in result["handoff"]["requirements"]))
        self.assertEqual(self.state()["practice"], {})

    def test_hold_stops_downstream_action(self):
        job = self.job()
        job["steps"].append({"id": "deliver", "depends_on": ["target-check"], "action": {"kind": "text-file",
            "inputs": {"path": "creations/delivered.txt", "content": "must not be written"}}})
        self.assertEqual(self.run_job(job)["status"], "HOLD_TARGET_EVIDENCE")
        self.assertFalse((self.root / "creations/delivered.txt").exists())

    def test_provider_pass_does_not_override_fresh_observer(self):
        with patch.object(CapabilityStore, "invoke", return_value={"status": "PASS", "independently_reproduced": True}):
            self.assertEqual(self.run_job()["status"], "HOLD_TARGET_EVIDENCE")
        self.assertEqual(self.state()["practice"], {})

    def test_artifact_change_invalidates_existing_packet_and_stored_run(self):
        self.run_job(self.complete_job())
        self.spec["name"] = "Changed artifact"
        self.target.write_bytes(build_glb(self.spec)["body"])
        result = operate_profession_crew(self.root, {"operation": "verify", "crew_id": "target-team", "run_id": "target-001"})
        self.assertEqual(result["status"], "NOT_CURRENT_PASS")
        self.assertEqual(result["checks"][0]["status"], "STALE")

    def test_plan_binds_target_contract_and_exposes_evidence_scope(self):
        job = self.job()
        job["operation"] = "plan"
        first = operate_profession_crew(self.root, job)
        job["steps"][0]["action"]["inputs"]["target"]["version"] = "2"
        second = operate_profession_crew(self.root, job)
        self.assertNotEqual(first["stations"][0]["practice_key"], second["stations"][0]["practice_key"])
        self.assertEqual(first["stations"][0]["evidence_scope"], "EXTERNAL_PACKET_VALIDATION_ONLY")

    def test_unknown_requirement_rejected_without_state_changes(self):
        job = self.job()
        job["steps"][0]["action"]["inputs"]["required_lanes"] = ["imaginary"]
        with self.assertRaises(ValueError):
            self.run_job(job)
        self.assertFalse((self.root / "state").exists())

    def test_navigation_handoff_has_original_profession_contract_in_plan(self):
        job = self.job()
        inputs = job["steps"][0]["action"]["inputs"]
        # A packet may impose extra requirements; its missing owners must also
        # appear in the plan, even when the job's minimum did not name them.
        inputs["packet"]["required_lanes"].append(" navigation ")
        result = self.run_job(job)
        self.assertIn({"lane": "navigation", "profession_id": "world-encounter-designer", "reason": "MISSING_REQUIRED_LANE"}, result["handoff"]["requirements"])
        owner = next(p for p in result["plan"]["crew"] if p["id"] == "world-encounter-designer")
        self.assertTrue(owner["procedures"])
        self.assertTrue(owner["sources"])
        self.assertEqual(owner["execution_role"], "consultation/handoff; not executed")

    def test_provider_exception_does_not_teach_a_target_failure(self):
        with patch.object(CapabilityStore, "invoke", side_effect=OSError("fixture provider unavailable")):
            result = self.run_job()
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertEqual(result["observations"][0]["evidence_origin"], "EXTERNAL_EVIDENCE_PACKET")
        self.assertEqual(result["handoff"]["requirements"][0]["reason"], "EXECUTION_OR_OBSERVATION_ERROR")
        self.assertEqual(self.state()["practice"], {})

    def test_direct_adapter_rejects_symlink_and_protected_artifacts(self):
        link = self.root / "creations/link.glb"
        link.symlink_to(self.target)
        store = CapabilityStore(self.root)
        manifest = store.route("verify-static-asset-target")
        inputs = self.job()["steps"][0]["action"]["inputs"]
        for path in [str(link), "state/asset.glb"]:
            with self.subTest(path=path), self.assertRaises(CapabilityError):
                store.invoke(manifest, {**inputs, "path": path})

    def test_optional_not_tested_does_not_block_or_invent_handoff(self):
        job = self.complete_job()
        job["steps"][0]["action"]["inputs"]["packet"]["lanes"]["navigation"] = {"status": "NOT_TESTED"}
        result = self.run_job(job)
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertNotIn("handoff", result)
        self.assertEqual(result["observations"][0]["target_evidence"]["lane_results"]["navigation"]["status"], "NOT_TESTED")


if __name__ == "__main__":
    unittest.main()

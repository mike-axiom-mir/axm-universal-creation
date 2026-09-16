from __future__ import annotations

import copy
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.adoption_lock import candidate_adoption_lock
from axm_uc.capabilities import CapabilityError, CapabilityStore
from axm_uc.machine import UniversalCreationMachine
from axm_uc.profession_crew import ProfessionCrewError, operate_profession_crew


class ProfessionCrewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "capabilities/live", self.root / "capabilities/live")

    def call(self, operation, **inputs):
        return operate_profession_crew(self.root, {"operation": operation, **inputs})

    def job(self, files=None, **extra):
        job = {"crew_id": "test", "run_id": "first", "work_type": "software", "goal": "Create exact local software with bounded checks",
               "context": {"target": "offline-python"}, "steps": [{"id": "build", "profession_id": "backend-engineer",
               "action": {"kind": "python-project", "inputs": {"path": "creations/one", "files": files or {"main.py": "print('hello')\n"}}}}]}
        job.update(extra)
        return job

    def test_catalog_retains_provenance_bodies_and_original_workflows(self):
        catalog = self.call("catalog")
        self.assertEqual(len(catalog["catalog"]["professions"]), 18)
        self.assertTrue(all(r["body"]["status"] == "EXPERIMENTAL" for r in catalog["catalog"]["professions"]))
        qa = next(r for r in catalog["catalog"]["professions"] if r["id"] == "software-qa-playtest")
        self.assertTrue(any(p.endswith("maps/workflow.json") for p in qa["workflow_files"]))
        self.assertEqual(len(catalog["catalog"]["origin"]["commit"]), 40)

    def test_live_machine_route(self):
        result = UniversalCreationMachine(ROOT).create({"kind": "profession-crew", "inputs": {"operation": "catalog"}})
        self.assertEqual(result["type"], "CREATION_RESULT")
        self.assertEqual(len(result["result"]["catalog"]["professions"]), 18)

    def test_existing_specialist_tournament_receives_profession_workflows(self):
        from axm_uc.specialist_pool import rank_tournament
        request = {"operation": "prepare", "profession_workflow": self.job(), "pool_size": 8, "max_teams": 4}
        result = UniversalCreationMachine(ROOT).create({"kind": "specialist-tournament", "inputs": request})
        self.assertEqual(result["type"], "CREATION_RESULT", result)
        tournament = result["result"]
        self.assertEqual(tournament["profession_workflow"]["source"]["repository"], "mike-axiom-mir/axm-profession-fabric")
        self.assertTrue(tournament["parallel_challenge_packets"][0]["professional_contracts"])
        ranking = rank_tournament(tournament, {})
        self.assertFalse(ranking["points_awarded"])
        self.assertFalse(ranking["complete_parallel_judging"])

    def test_plan_is_deterministic_and_does_not_write_state(self):
        self.assertEqual(self.call("plan", **self.job()), self.call("plan", **self.job()))
        self.assertFalse((self.root / "state").exists())

    def test_existing_stepwise_contract_and_profession_handoffs(self):
        plan = self.call("plan", **self.job())
        self.assertIn("plan_digest", plan["stepwise_plan"])
        self.assertTrue(plan["crew"][0]["procedures"])
        self.assertTrue(any(c["execution_role"].startswith("consultation") for c in plan["crew"]))

    def test_real_artifact_roundtrip_and_cold_restart(self):
        result = self.call("run", **self.job())
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertTrue((self.root / "creations/one/main.py").is_file())
        cold = self.call("inspect", crew_id="test")
        self.assertEqual(cold["runs"]["first"], result)
        self.assertEqual(self.call("verify", crew_id="test", run_id="first")["status"], "PASS")
        self.assertEqual(result["professional_acceptance"], "NOT_TESTED")

    def test_failure_changes_next_job_before_target_is_written(self):
        bad = self.job({"main.py": "def broken(:\n"})
        first = self.call("run", **bad)
        self.assertEqual(first["status"], "HOLD_FAILED_CHECK")
        later = copy.deepcopy(bad)
        later["run_id"] = "second"
        later["steps"][0]["action"]["inputs"]["path"] = "creations/two"
        plan = self.call("plan", **later)
        self.assertTrue(plan["stations"][0]["learned_preflight"])
        held = self.call("run", **later)
        self.assertEqual(held["status"], "HOLD_LEARNED_PREFLIGHT")
        self.assertFalse((self.root / "creations/two").exists())
        fixed = copy.deepcopy(later)
        fixed["run_id"] = "repair"
        fixed["steps"][0]["action"]["inputs"]["files"] = {"main.py": "print('repaired')\n"}
        self.assertEqual(self.call("run", **fixed)["status"], "COMPLETE_BOUNDED_CHECKS")
        practice = list(self.call("inspect", crew_id="test")["practice"].values())[0]
        self.assertEqual(len(practice["passed_cases"]), 1)
        self.assertEqual(len(practice["failed_cases"]), 1)

    def test_replay_never_executes_or_manufactures_experience(self):
        job = self.job()
        self.call("run", **job)
        with patch.object(CapabilityStore, "invoke", side_effect=AssertionError("must not execute")):
            replay = self.call("run", **job)
        self.assertTrue(replay["replayed"])
        changed = self.job(goal="Different job")
        with self.assertRaisesRegex(ProfessionCrewError, "different request"):
            self.call("run", **changed)

    def test_same_artifact_under_new_job_id_is_not_new_experience(self):
        self.call("run", **self.job())
        next_job = self.job(run_id="repeat")
        next_job["steps"][0]["action"]["inputs"]["path"] = "creations/repeat"
        self.call("run", **next_job)
        row = next(iter(self.call("inspect", crew_id="test")["practice"].values()))
        self.assertEqual(len(row["passed_cases"]), 1)

    def test_context_and_runtime_changes_do_not_transfer_learning(self):
        bad = self.job({"main.py": "def broken(:\n"})
        self.call("run", **bad)
        other = copy.deepcopy(bad)
        other["context"] = {"target": "different-platform"}
        self.assertFalse(self.call("plan", **other)["stations"][0]["learned_preflight"])
        with patch("axm_uc.profession_crew._revision", return_value="changed-runtime"):
            self.assertFalse(self.call("plan", **bad)["stations"][0]["learned_preflight"])
            self.assertEqual(self.call("verify", crew_id="test", run_id="first")["status"], "NOT_CURRENT_PASS")

    def test_no_cross_crew_experience(self):
        bad = self.job({"main.py": "def broken(:\n"})
        self.call("run", **bad)
        bad["crew_id"] = "other"
        self.assertFalse(self.call("plan", **bad)["stations"][0]["learned_preflight"])

    def test_changed_artifact_invalidates_old_receipt(self):
        self.call("run", **self.job())
        (self.root / "creations/one/main.py").write_text("print('different valid code')\n")
        result = self.call("verify", crew_id="test", run_id="first")
        self.assertEqual(result["status"], "NOT_CURRENT_PASS")
        self.assertEqual(result["checks"][0]["status"], "STALE")

    def test_provider_pass_claim_is_not_accepted_as_artifact_evidence(self):
        with patch.object(CapabilityStore, "invoke", return_value={"passed": True, "validation": {"passed": True}}):
            result = self.call("run", **self.job())
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertFalse(any(r["passed_cases"] for r in self.call("inspect", crew_id="test")["practice"].values()))

    def test_missing_adapter_and_required_judgment_hold(self):
        for kind, judgment, expected in [("unknown-animator", "NOT_TESTED", "HOLD_CAPABILITY_GAP"),
                                          ("python-project", "REQUIRED", "HOLD_JUDGMENT")]:
            job = self.job(crew_id=kind)
            job["steps"][0]["action"]["kind"] = kind
            job["steps"][0]["judgment"] = judgment
            result = self.call("run", **job)
            self.assertEqual(result["status"], expected)
            self.assertEqual(self.call("inspect", crew_id=kind)["practice"], {})

    def test_interrupted_run_does_not_replay_unknown_side_effects(self):
        job = self.job()
        with patch.object(CapabilityStore, "invoke", side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                self.call("run", **job)
        self.assertEqual(self.call("run", **job)["status"], "HOLD_INTERRUPTED")
        self.assertEqual(self.call("inspect", crew_id="test")["practice"], {})

    def test_failure_stops_dependent_station(self):
        job = self.job({"main.py": "def broken(:\n"})
        job["steps"].append({"id": "later", "depends_on": ["build"], "action": {"kind": "text-file", "inputs": {"path": "creations/later.txt", "content": "must not exist"}}})
        result = self.call("run", **job)
        self.assertEqual(len(result["observations"]), 1)
        self.assertFalse((self.root / "creations/later.txt").exists())

    def test_future_dependency_rejected_before_mutation(self):
        job = self.job()
        job["steps"][0]["depends_on"] = ["future"]
        with self.assertRaises(Exception):
            self.call("run", **job)
        self.assertFalse((self.root / "state").exists())

    def test_unknown_profession_skill_and_bad_fit_rejected(self):
        for field, value in [("profession_id", "imaginary"), ("profession_id", "sound-designer"), ("skill_id", "imaginary")]:
            job = self.job()
            job["steps"][0][field] = value
            with self.assertRaises(ProfessionCrewError):
                self.call("plan", **job)

    def test_path_escape_and_machine_writes_rejected(self):
        with self.assertRaises(ProfessionCrewError):
            self.call("inspect", crew_id="../escape")
        job = self.job()
        job["steps"][0]["action"]["inputs"]["path"] = "src"
        with self.assertRaises(ProfessionCrewError):
            self.call("run", **job)

    def test_state_symlink_rejected(self):
        outside = self.root / "outside"
        outside.mkdir()
        (self.root / "state").symlink_to(outside, target_is_directory=True)
        with self.assertRaises(ProfessionCrewError):
            self.call("run", **self.job())
        self.assertEqual(list(outside.iterdir()), [])

    def test_competing_writer_fails_without_losing_state(self):
        path = self.root / "state/profession-crews/test.json"
        with candidate_adoption_lock(path):
            store = CapabilityStore(self.root)
            with self.assertRaises(CapabilityError):
                store.invoke(store.route("profession-crew"), {"operation": "run", **self.job()})
        self.assertFalse(path.exists())

    def test_json_exact_roundtrip_and_semantic_boundary(self):
        job = self.job()
        job["steps"][0]["action"] = {"kind": "json-file", "inputs": {"path": "creations/one.json", "value": {"answer": 7}}}
        result = self.call("run", **job)
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertEqual(result["observations"][0]["professional_acceptance"], "NOT_TESTED")

    def test_create_to_qa_handoff_uses_real_project_evidence(self):
        job = json.loads((ROOT / "examples/profession-crew-python.json").read_text())["inputs"]
        result = operate_profession_crew(self.root, job)
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertEqual([r["station"] for r in result["observations"]], ["implementation", "verification"])
        self.assertEqual(self.call("verify", crew_id="software-crew", run_id="hello-001")["status"], "PASS")

    def test_real_glb_is_observed_without_visual_quality_claim(self):
        job = self.job(work_type="3d")
        job["steps"] = [{"id": "mesh", "profession_id": "3d-artist", "action": {"kind": "procedural-glb-asset", "inputs": {
            "path": "creations/proof.glb", "specification": {"schema": "axm.procedural-3d/v0.1", "name": "Crew proof",
            "primitives": [{"id": "body", "type": "box", "size": [2, 1, 3], "translation": [0, 0, 0],
                            "material": {"color": "#446688FF", "metallic": 0.5, "roughness": 0.4}}]}}}}]
        result = self.call("run", **job)
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS", result)
        self.assertEqual(result["visual_quality"], "NOT_TESTED")
        self.assertEqual(self.call("verify", crew_id="test", run_id="first")["status"], "PASS")

    def test_valid_but_wrong_glb_does_not_satisfy_requested_asset(self):
        from axm_uc.procedural_3d import build_glb
        spec = {"schema": "axm.procedural-3d/v0.1", "name": "Requested",
                "primitives": [{"id": "body", "type": "box", "size": [2, 1, 3], "translation": [0, 0, 0],
                                "material": {"color": "#446688FF", "metallic": 0.5, "roughness": 0.4}}]}
        wrong = copy.deepcopy(spec)
        wrong["name"] = "Substituted"
        target = self.root / "creations/wrong.glb"
        target.parent.mkdir()
        target.write_bytes(build_glb(wrong)["body"])
        job = self.job(work_type="3d")
        job["steps"] = [{"id": "model", "profession_id": "3d-artist", "action": {"kind": "procedural-glb-asset",
                         "inputs": {"path": str(target), "specification": spec}}}]
        with patch.object(CapabilityStore, "invoke", return_value={"passed": True}):
            result = self.call("run", **job)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertIn("specification", result["observations"][0]["error"])


if __name__ == "__main__":
    unittest.main()

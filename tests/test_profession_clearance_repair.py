from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from axm_stickers import Registry
from axm_uc.capabilities import CapabilityStore
from axm_uc.profession_clearance_repair import observe_repair, procedure, run_repair
from axm_uc.profession_crew import operate_profession_crew
from test_sticker_clearance_contact import frame, make_assembly, pin, register_shape

ROOT = Path(__file__).resolve().parents[1]


class ProfessionClearanceRepairTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "capabilities/live", self.root / "capabilities/live")
        (self.root / "creations").mkdir()
        self.database = self.root / "creations/source.sqlite"
        self.first = self.assembly("small", 1.0, 0.8)
        self.second = self.assembly("large", 2.0, 1.2)

    def assembly(self, name, width, x):
        with Registry(self.database) as registry:
            body = register_shape(registry, name + "-body", size=(width, 1, 1))
            moving = register_shape(registry, name + "-wheel")
            result = make_assembly(registry, name, [("chassis", body, frame(), {}),
                                                   ("wheel", moving, frame(x), {})])
            return pin(result)

    def inputs(self, assembly=None, label="first", **extra):
        result = {"path": "creations/" + label, "database": str(self.database), "assembly": assembly or self.first,
                  "moving": "wheel", "fixed": ["chassis"], "axis": "+x", "minimum_m": 0.1,
                  "max_translation_m": 0.6, "output_id": "repaired-" + label}
        result.update(extra)
        return result

    def job(self, inputs=None, label="first", **extra):
        return {"operation": "run", "crew_id": "fit-team", "run_id": label, "work_type": "3d",
                "goal": "Repair a bounded static clearance defect and retain a verified procedure",
                "context": {"family": "rigid-vehicle", "units": "m"},
                "steps": [{"id": "fit", "profession_id": "technical-artist", "action": {
                    "kind": "repair-sticker-clearance", "inputs": inputs or self.inputs(label=label)}}], **extra}

    def state(self):
        return operate_profession_crew(self.root, {"operation": "inspect", "crew_id": "fit-team"})

    def test_cold_search_repairs_actual_geometry_and_preserves_source_registry(self):
        before_bytes = self.database.read_bytes()
        result = run_repair(self.root, self.inputs())
        self.assertEqual(result["before"]["status"], "FAIL")
        self.assertEqual(result["status"], "PASS")
        self.assertGreater(len(result["trials"]), 1)
        self.assertEqual(result["procedure"], procedure("+x"))
        self.assertEqual(self.database.read_bytes(), before_bytes)
        fresh = observe_repair(self.root, self.inputs())
        self.assertEqual(fresh["status"], "PASS")
        self.assertGreaterEqual(fresh["after"]["requirements"][0]["pair"]["clearance_m"], 0.1)
        self.assertEqual(fresh["professional_acceptance"], "NOT_TESTED")

    def test_cold_restart_reuses_parameterized_rule_on_new_geometry(self):
        first = operate_profession_crew(self.root, self.job())
        self.assertEqual(first["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertFalse(first["plan"]["stations"][0]["reused_procedure"])
        second_job = self.job(self.inputs(self.second, "second"), label="second")
        second = operate_profession_crew(self.root, second_job)
        self.assertTrue(second["plan"]["stations"][0]["reused_procedure"])
        self.assertEqual(second["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertNotEqual(first["observations"][0]["distance_m"], second["observations"][0]["distance_m"])
        report = json.loads((self.root / "creations/second/repair.json").read_text())
        self.assertEqual(report["selection"], "RETAINED_PROCEDURE")
        self.assertEqual(len(report["trials"]), 1)
        self.assertEqual(next(iter(self.state()["practice"].values()))["procedure"], procedure("+x"))

    def test_movement_bound_holds_without_learning_or_downstream_output(self):
        job = self.job(self.inputs(max_translation_m=0.05))
        job["steps"].append({"id": "deliver", "depends_on": ["fit"], "action": {"kind": "text-file",
            "inputs": {"path": "creations/delivery.txt", "content": "unverified"}}})
        result = operate_profession_crew(self.root, job)
        self.assertEqual(result["status"], "HOLD_REPAIR_BOUNDARY")
        self.assertEqual(self.state()["practice"], {})
        self.assertFalse((self.root / "creations/delivery.txt").exists())

    def test_learned_rule_does_not_bypass_new_movement_limit(self):
        operate_profession_crew(self.root, self.job())
        job = self.job(self.inputs(self.second, "limited", max_translation_m=0.1), label="limited")
        result = operate_profession_crew(self.root, job)
        self.assertTrue(result["plan"]["stations"][0]["reused_procedure"])
        self.assertEqual(result["status"], "HOLD_REPAIR_BOUNDARY")
        row = next(iter(self.state()["practice"].values()))
        self.assertEqual(len(row["passed_cases"]), 1)

    def test_axis_context_and_runtime_changes_do_not_transfer_procedure(self):
        operate_profession_crew(self.root, self.job())
        for job in [self.job(self.inputs(axis="-x"), operation="plan"),
                    self.job(operation="plan", context={"family": "other"})]:
            self.assertFalse(operate_profession_crew(self.root, job)["stations"][0]["reused_procedure"])
        with patch("axm_uc.profession_crew._revision", return_value="new-runtime"):
            self.assertFalse(operate_profession_crew(self.root, self.job(operation="plan"))["stations"][0]["reused_procedure"])

    def test_claimed_provider_success_cannot_teach_without_artifacts(self):
        with patch.object(CapabilityStore, "invoke", return_value={"status": "PASS", "procedure": procedure("+x")}):
            result = operate_profession_crew(self.root, self.job())
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertFalse(any(row.get("procedure") for row in self.state()["practice"].values()))

    def test_replay_does_not_reexecute_or_duplicate_learning(self):
        operate_profession_crew(self.root, self.job())
        with patch.object(CapabilityStore, "invoke", side_effect=AssertionError("must not run")):
            repeated = operate_profession_crew(self.root, self.job())
        self.assertTrue(repeated["replayed"])
        self.assertEqual(len(next(iter(self.state()["practice"].values()))["passed_cases"]), 1)

    def test_new_destination_does_not_duplicate_same_repair_experience(self):
        operate_profession_crew(self.root, self.job())
        again = operate_profession_crew(self.root, self.job(label="same-case"))
        self.assertTrue(again["plan"]["stations"][0]["reused_procedure"])
        self.assertEqual(again["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertEqual(len(next(iter(self.state()["practice"].values()))["passed_cases"]), 1)

    def test_animated_source_cannot_receive_a_static_repair(self):
        with Registry(self.database) as registry:
            source = registry.get(self.first["id"], self.first["version"])
            source["id"] = "animated"
            child = source["recipe"]["children"][1]
            child["motion"] = [{"time": 0, "frame": child["target"]["frame"]}, {"time": 1, "frame": frame(1.0)}]
            registry.register(source)
        result = operate_profession_crew(self.root, self.job(self.inputs(pin(source))))
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertIn("motion-aware", result["observations"][0]["error"])
        self.assertFalse(any(row.get("procedure") for row in self.state()["practice"].values()))

    def test_replaced_glb_invalidates_verification(self):
        operate_profession_crew(self.root, self.job())
        path = self.root / "creations/first"
        (path / "after.glb").write_bytes((path / "before.glb").read_bytes())
        result = operate_profession_crew(self.root, {"operation": "verify", "crew_id": "fit-team", "run_id": "first"})
        self.assertEqual(result["status"], "NOT_CURRENT_PASS")
        self.assertEqual(result["checks"][0]["status"], "STALE")

    def test_stored_pass_cannot_turn_unrepaired_output_into_success(self):
        inputs = self.inputs(max_translation_m=0.05)
        run_repair(self.root, inputs)
        path = self.root / "creations/first/repair.json"
        report = json.loads(path.read_text()); report["status"] = "PASS"; report["procedure"] = procedure("+x")
        path.write_text(json.dumps(report))
        fresh = observe_repair(self.root, inputs)
        self.assertEqual(fresh["status"], "HOLD")
        self.assertIsNone(fresh["learned_procedure"])

    def test_already_clear_does_not_invent_repair_experience(self):
        clear = self.assembly("clear", 1, 2)
        result = operate_profession_crew(self.root, self.job(self.inputs(clear)))
        self.assertEqual(result["status"], "COMPLETE_BOUNDED_CHECKS")
        self.assertIsNone(result["observations"][0]["learned_procedure"])
        self.assertFalse(any(row.get("procedure") for row in self.state()["practice"].values()))

    def test_unsupported_procedure_and_bad_bound_rejected_before_state(self):
        for extra in [{"procedure": {"operator": "run-code"}}, {"max_translation_m": float("nan")}, {"axis": "anything"}]:
            with self.subTest(extra=extra), self.assertRaises(ValueError):
                operate_profession_crew(self.root, self.job(self.inputs(**extra)))
        self.assertFalse((self.root / "state").exists())

    def test_existing_output_and_protected_registry_are_not_overwritten(self):
        run_repair(self.root, self.inputs())
        with self.assertRaises(FileExistsError):
            run_repair(self.root, self.inputs())
        with self.assertRaises(ValueError):
            operate_profession_crew(self.root, self.job(self.inputs(database="state/private.sqlite"), operation="plan"))

    def test_requested_additional_pair_blocks_an_incomplete_repair(self):
        with Registry(self.database) as registry:
            block = register_shape(registry, "block")
            source = make_assembly(registry, "guarded", [("chassis", block, frame(), {}),
                ("wheel", block, frame(0.8), {}), ("guard", block, frame(1.9), {})])
        result = run_repair(self.root, self.inputs(pin(source), fixed=["chassis", "guard"]))
        self.assertEqual(result["status"], "HOLD")
        self.assertIsNone(result["procedure"])

    def test_negative_axis_repair_is_verified_on_actual_geometry(self):
        left = self.assembly("left", 1, -0.8)
        inputs = self.inputs(left, axis="-x")
        self.assertEqual(run_repair(self.root, inputs)["status"], "PASS")
        self.assertEqual(observe_repair(self.root, inputs)["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

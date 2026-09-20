import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from axm_uc.atlas_pipeline import operate_atlas
from axm_uc.capabilities import CapabilityStore
from axm_uc.workflow_discovery import origin, plan, uses
from axm_uc.workflow_experiments import experiment
from axm_uc.workflow_memory import read_memory

ROOT = Path(__file__).resolve().parents[1]


def request():
    value = json.loads((ROOT / "examples/workflows/vent-hood.json").read_text())["inputs"]["request"]
    value["inputs"]["render"]["values"][0].update(width=64, height=64)
    value["goals"]["preview"]["checks"][0]["min"] = 100
    return value


class WorkflowDiscoveryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.folder = Path(cls.temp.name)
        cls.memory = cls.folder / "memory"
        cls.request = request()
        cls.result = experiment(ROOT, cls.request, str(cls.folder / "first"), memory=str(cls.memory))

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def output(self, name):
        return str(self.folder / name)

    def observation(self, result, outcome):
        return json.loads((Path(result["path"]) / outcome["observation"]).read_text())

    def small(self):
        req = request()
        req["inputs"]["material"]["values"] = req["inputs"]["material"]["values"][:1]
        req["inputs"]["bake"]["values"] = req["inputs"]["bake"]["values"][1:2]
        req["operators"] = ["generate-material", "measure-material", "derive-uvless", "bake-material", "measure-asset", "render-preview"]
        return req

    def test_deterministic_composition_discovers_two_routes_and_keeps_origins(self):
        req = request()
        original = copy.deepcopy(req)
        first = plan(ROOT, req)
        self.assertEqual(first, plan(ROOT, req))
        self.assertEqual(req, original)
        self.assertEqual(first["status"], "READY")
        self.assertEqual(len(first["candidates"]), 8)
        self.assertEqual(len({c["signature"] for c in first["candidates"]}), 2)
        for candidate in first["candidates"]:
            program = candidate["program"]
            self.assertEqual(origin(program["outputs"]["asset"], program["nodes"], first["operators"]),
                             origin(program["outputs"]["preview"], program["nodes"], first["operators"]))
            self.assertTrue(uses(program["outputs"]["asset"], program["outputs"]["material"], program["nodes"]))

    def test_actual_iteration_repairs_uvs_and_ranks_quality_then_confirms(self):
        result = self.result
        self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
        self.assertEqual(result["trials"], 12)
        self.assertEqual(len(result["ranked"]), 4)
        observed = [self.observation(result, o) for o in result["outcomes"]]
        direct = next(o for o in observed if any(n["operator"] == "bind-material" for n in o["program"]["nodes"]))
        diagnosis = direct["cases"][0]["diagnosis"]
        self.assertEqual(direct["status"], "REJECTED")
        self.assertEqual(diagnosis["operator"], "measure-asset")
        self.assertLess(diagnosis["metrics"]["texels_per_m"], 35)
        self.assertTrue(diagnosis["not_executed"])
        selected = self.observation(result, result["selected"])
        first_valid = next(o for o in observed if o["status"] == "CONFIRMED")
        self.assertLess(selected["ranking"]["weighted_worst_deficit"], first_valid["ranking"]["weighted_worst_deficit"])
        self.assertGreater(selected["cases"][0]["metrics"]["asset"]["texels_per_m"], 90)
        self.assertEqual(selected["cases"][0]["metrics"]["material"]["map_size"], 32)
        self.assertTrue(all(c["repeatable"] for c in selected["confirmation"]))
        self.assertEqual({r["mode"] for r in result["rounds"]}, {"explore", "repair", "refine"})
        self.assertEqual(len(read_memory(ROOT, str(self.memory))["workflows"]), 1)

    def test_learning_rebinds_under_a_search_budget_too_small_to_rediscover(self):
        req = self.small()
        req["budget"]["states"] = 1
        # Catalog restriction changes the environment pin; use the original scope.
        req.pop("operators")
        self.assertEqual(plan(ROOT, req)["status"], "HOLD_CAPABILITY_GAP")
        reused = plan(ROOT, req, memory=str(self.memory))
        self.assertEqual(reused["status"], "READY", reused)
        self.assertTrue(all(c["reused_structure"] for c in reused["candidates"]))
        replay = experiment(ROOT, req, self.output("rebound"), memory=str(self.memory))
        self.assertEqual(replay["status"], "VERIFIED_WORKFLOWS", replay)
        self.assertGreater(replay["trials"], 0)
        self.assertEqual(len(read_memory(ROOT, str(self.memory))["workflows"]), 1)

    def test_reused_workflow_rechecks_stricter_goals_and_does_not_inherit_pass(self):
        req = self.small(); req.pop("operators")
        req["budget"]["states"] = 1
        req["goals"]["asset"]["checks"][0]["min"] = 100000
        result = experiment(ROOT, req, self.output("strict"), memory=str(self.memory))
        self.assertEqual(result["status"], "HOLD_NO_CONFIRMED_WORKFLOW", result)
        self.assertTrue(all(o["status"] != "CONFIRMED" for o in result["outcomes"]))
        observation = self.observation(result, result["outcomes"][0])
        self.assertTrue(observation["reused_structure"])
        self.assertEqual(observation["cases"][0]["diagnosis"]["operator"], "measure-asset")

    def test_stress_failure_blocks_retention_even_when_baseline_passes(self):
        req = self.small()
        enlarged = copy.deepcopy(req["inputs"]["surface"]["values"][0])
        for p in enlarged["primitives"]:
            p["positions"] = [[v * 4 for v in xyz] for xyz in p["positions"]]
        req["scenarios"] = [{"id": "larger-geometry", "inputs": {"surface": enlarged}}]
        memory = self.output("stress-memory")
        result = experiment(ROOT, req, self.output("stress"), memory=memory)
        self.assertEqual(result["status"], "HOLD_NO_CONFIRMED_WORKFLOW")
        obs = self.observation(result, result["outcomes"][0])
        self.assertEqual([c["status"] for c in obs["cases"]], ["PASS", "FAIL"])
        self.assertEqual(read_memory(ROOT, memory)["workflows"], [])

    def test_ranking_uses_worst_observed_scenario(self):
        req = self.small()
        larger = copy.deepcopy(req["inputs"]["surface"]["values"][0])
        for p in larger["primitives"]:
            p["positions"] = [[v * 1.25 for v in xyz] for xyz in p["positions"]]
        req["scenarios"] = [{"id": "larger", "inputs": {"surface": larger}}]
        result = experiment(ROOT, req, self.output("worst-case"))
        self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
        obs = self.observation(result, result["selected"])
        low = min(c["metrics"]["asset"]["texels_per_m"] for c in obs["cases"])
        self.assertAlmostEqual(obs["ranking"]["objective_deficits"][0], (90 - low) / 90)
        self.assertEqual(obs["confirmation"][0]["scenario"], "larger")

    def test_missing_observer_units_and_type_fit_hold_without_writes(self):
        for field in ("metric", "unit", "source-type"):
            req = request()
            if field == "metric":
                req["goals"]["asset"]["checks"][0]["metric"] = "artistic_beauty"
            elif field == "unit":
                req["goals"]["asset"]["checks"][0]["unit"] = "px/cm"
                req["objectives"][0]["unit"] = "px/cm"
            else:
                req["inputs"]["surface"]["type"]["units"] = "mm"
            out = self.output("gap-" + field)
            result = experiment(ROOT, req, out)
            self.assertEqual(result["status"], "HOLD_CAPABILITY_GAP", result)
            self.assertFalse(Path(out).exists())

    def test_budget_cannot_promote_unconfirmed_or_partial_cases(self):
        req = self.small(); req["budget"]["trials"] = 1
        memory = self.output("budget-memory")
        result = experiment(ROOT, req, self.output("budget"), memory=memory)
        self.assertEqual(result["status"], "HOLD_NO_CONFIRMED_WORKFLOW")
        self.assertEqual(result["outcomes"][0]["status"], "INCOMPLETE")
        self.assertEqual(result["trials"], 1)
        self.assertEqual(read_memory(ROOT, memory)["workflows"], [])

    def test_confirmation_rejects_changed_product_bytes(self):
        from axm_uc import workflow_experiments as module
        actual = module._case
        calls = []
        def changed(*args):
            outcome = actual(*args); calls.append(outcome)
            if len(calls) == 2:
                outcome["product_hashes"] = {"asset.glb": "changed"}
            return outcome
        with patch.object(module, "_case", side_effect=changed):
            result = experiment(ROOT, self.small(), self.output("nondeterministic"))
        self.assertEqual(result["outcomes"][0]["status"], "CONFIRMATION_FAILED")
        self.assertIsNone(result["selected"])

    def test_failure_prefix_reuse_stops_duplicate_work_but_not_changed_context(self):
        req = self.small()
        req["goals"]["asset"]["checks"][0]["min"] = 100000
        req["inputs"]["render"]["values"].append({"width": 80, "height": 80})
        result = experiment(ROOT, req, self.output("prune"))
        self.assertEqual(result["trials"], 1)
        self.assertEqual([o["status"] for o in result["outcomes"]], ["REJECTED", "PRUNED_IDENTICAL_FAILURE"])
        req["inputs"]["bake"]["values"].append({"atlas_size": 128, "padding_px": 4})
        changed = experiment(ROOT, req, self.output("prune-changed"))
        self.assertEqual(changed["trials"], 2)

    def test_execution_errors_are_not_cached_as_deterministic_failures(self):
        req = self.small()
        req["inputs"]["material"]["values"][0]["color"] = "invalid"
        req["inputs"]["render"]["values"].append({"width": 80, "height": 80})
        result = experiment(ROOT, req, self.output("uncached-errors"))
        self.assertEqual(result["trials"], 2)
        self.assertTrue(all(o["status"] == "REJECTED" for o in result["outcomes"]))

    def test_changed_runtime_pin_invalidates_memory_and_expected_plan_before_writes(self):
        req = self.small(); req.pop("operators")
        before = plan(ROOT, req, memory=str(self.memory))
        with patch("axm_uc.workflow_discovery.runtime_pin", return_value="changed"):
            req["budget"]["states"] = 1
            fresh = plan(ROOT, req, memory=str(self.memory))
            self.assertTrue(fresh["memory"]["stale"])
            self.assertEqual(fresh["status"], "READY")
            self.assertTrue(all(c["reused_structure"] for c in fresh["candidates"]))
            self.assertFalse(any(c["prior_evidence_current"] for c in fresh["candidates"]))
            result = experiment(ROOT, req, self.output("stale"), memory=str(self.memory), expected_plan=before["plan_sha256"])
        self.assertEqual(result["status"], "HOLD_STALE_PLAN")
        self.assertFalse(Path(self.output("stale")).exists())

    def test_recolors_and_source_renames_do_not_count_as_new_structures(self):
        req = request(); before = plan(ROOT, req)
        req["inputs"]["pigment"] = req["inputs"].pop("material")
        for value in req["inputs"]["pigment"]["values"]:
            value["color"] = [170, 30, 50]
        req["intent"] = "Another name for the same technical task"
        after = plan(ROOT, req)
        self.assertEqual({c["signature"] for c in before["candidates"]}, {c["signature"] for c in after["candidates"]})

    def test_memory_is_queryable_through_atlas_and_tampering_is_ignored(self):
        result = operate_atlas(ROOT, {"operation": "query", "categories": ["learned-workflow"], "memory": str(self.memory)})
        self.assertEqual(result["matches"], 1)
        memory = self.folder / "tampered-memory"
        shutil.copytree(self.memory, memory)
        one = next((memory / "workflows").glob("*.json"))
        value = json.loads(one.read_text()); value["program"]["nodes"][0]["operator"] = "uninstalled"
        one.write_text(json.dumps(value))
        report = read_memory(ROOT, str(memory))
        self.assertEqual(report["workflows"], [])
        self.assertTrue(report["ignored"])

    def test_machine_interface_and_output_protection(self):
        store = CapabilityStore(ROOT)
        cap = store.route("workflow-discovery")
        report = store.invoke(cap, {"operation": "plan", "request": self.small()})
        self.assertEqual(report["status"], "READY")
        with self.assertRaisesRegex(ValueError, "live machine"):
            experiment(ROOT, self.small(), str(ROOT / "src/workflow-write"))
        with self.assertRaisesRegex(ValueError, "separate"):
            experiment(ROOT, self.small(), self.output("nested"), memory=self.output("nested/memory"))

    def test_invalid_cycles_nonfinite_inputs_and_unpinned_file_ingress_rejected(self):
        bad = request(); bad["goals"]["material"]["uses_goal"] = "asset"
        with self.assertRaisesRegex(ValueError, "cyclic"):
            plan(ROOT, bad)
        bad = request(); bad["objectives"][0]["scale"] = float("nan")
        with self.assertRaises(ValueError):
            plan(ROOT, bad)
        bad = request(); bad["objectives"][0]["unit"] = "px/cm"
        with self.assertRaisesRegex(ValueError, "conflicting units"):
            plan(ROOT, bad)
        bad = request(); bad["inputs"]["surface"]["values"] = ["/tmp/unpinned.glb"]
        with self.assertRaisesRegex(ValueError, "unpinned"):
            plan(ROOT, bad)

    def test_character_probe_executes_decoded_motion_and_missing_contact_metric_fails(self):
        recipe = json.loads((ROOT / "examples/character-motion/seedling-performance.json").read_text())["inputs"]["recipe"]
        req = {"schema": "axm.workflow-experiment/v0.1", "intent": "Verify queried motion geometry",
               "inputs": {"body": {"type": {"kind": "character-recipe"}, "values": [recipe]},
                          "probe": {"type": {"kind": "motion-probe"}, "values": [{"clip": "walk", "times": [0, .37, 2.37]}]}},
               "goals": {"motion": {"type": {"kind": "motion-observation", "units": "m"},
                          "checks": [{"metric": "maximum_target_error_m", "unit": "m", "max": .000001}]}},
               "budget": {"trials": 2}}
        result = experiment(ROOT, req, self.output("motion"))
        self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
        req["goals"]["motion"]["checks"].append({"metric": "maximum_contact_slip_m", "unit": "m", "max": .001})
        missing = experiment(ROOT, req, self.output("motion-no-contact"))
        self.assertEqual(missing["status"], "HOLD_NO_CONFIRMED_WORKFLOW")
        observation = self.observation(missing, missing["outcomes"][0])
        self.assertIn("absent", observation["cases"][0]["diagnosis"]["failed_checks"][0]["error"])

    def test_form_recipe_can_discover_a_new_material_and_preview_pipeline(self):
        req = self.small()
        req["inputs"].pop("surface")
        req["inputs"]["form"] = {"type": {"kind": "form-recipe"}, "values": [{
            "schema": "axm.form-pattern/v0.1", "name": "Parametric tapered cover",
            "parts": [{"id": "cover", "pattern": "revolve", "segments": 8,
                       "profile": [[.12, 0], [.18, .3], [.1, .45]],
                       "material": {"color": "#ffffff", "metallic": 1, "roughness": 1}}]}]}
        req["inputs"]["bake"]["values"] = [{"atlas_size": 128, "padding_px": 4}]
        req["goals"]["asset"]["checks"][0]["min"] = 1
        req["operators"].remove("derive-uvless")
        req["operators"].append("compile-form")
        result = experiment(ROOT, req, self.output("form"))
        self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
        obs = self.observation(result, result["selected"])
        self.assertTrue(any(n["operator"] == "compile-form" for n in obs["program"]["nodes"]))

    @unittest.skipUnless(shutil.which("node"), "Node is required for actual code verification")
    def test_code_operator_executes_both_languages_and_retains_sources(self):
        code = json.loads((ROOT / "examples/code/restock-project.json").read_text())["inputs"]["request"]
        req = {"schema": "axm.workflow-experiment/v0.1", "intent": "Run declared inventory acceptance cases",
               "inputs": {"program": {"type": {"kind": "code-request"}, "values": [code]}},
               "goals": {"code": {"type": {"kind": "code-project", "quality": "checked"},
                          "checks": [{"metric": "cases", "unit": "count", "min": 3},
                                     {"metric": "languages", "unit": "count", "min": 2}]}},
               "budget": {"trials": 2}}
        result = experiment(ROOT, req, self.output("code"))
        self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
        obs = self.observation(result, result["selected"])
        self.assertTrue(any(p.endswith(".js") for p in obs["cases"][0]["product_hashes"]))
        self.assertTrue(any(p.endswith(".py") for p in obs["cases"][0]["product_hashes"]))


if __name__ == "__main__":
    unittest.main()

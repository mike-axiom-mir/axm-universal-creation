import copy
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.atlas_pipeline import build_intent, operate_atlas, plan_intent
from axm_uc.code_system import create_code_system_project, operate_code_system, run_code_system_station
from axm_uc.code_system_contract import digest
from axm_uc.capabilities import CapabilityError
from axm_uc.machine import UniversalCreationMachine


def fixture(name="inventory"):
    return json.loads((ROOT / "examples/code-systems" / (name + ".json")).read_text())


@unittest.skipUnless(shutil.which("node"), "Node is required for bundled code compilation")
class CodeSystemTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.inventory = operate_code_system(ROOT, fixture())
        cls.combat = operate_code_system(ROOT, fixture("combat"))
        for report in (cls.inventory, cls.combat):
            if report["status"] != "VERIFIED_FOR_SCENARIOS":
                raise AssertionError(str(report.get("diagnostic") or report.get("verification")))

    def emit(self, result, root):
        for name, source in result["files"].items():
            path = root / name; path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(source, encoding="utf-8", newline="\n")

    def command(self, root, language, *args):
        command = ["node", str(root / "javascript/runtime.js")] if language == "javascript" else [sys.executable, str(root / "python/runtime.py")]
        env = dict(os.environ); env.pop("PYTHONPATH", None)
        return subprocess.run([*command, *args], cwd=root.parent, env=env, capture_output=True, text=True, encoding="utf-8", timeout=30)

    def test_real_software_and_game_have_observed_scenarios_and_complete_declared_exploration(self):
        for report, states, edges, transitions in [(self.inventory, 64, 234, 6), (self.combat, 46, 245, 10)]:
            verification = report["verification"]
            self.assertEqual(verification["issues"], [])
            self.assertEqual(len(verification["observations"]), 4)
            self.assertTrue(all(row["passed"] for row in verification["case_checks"]))
            self.assertEqual(verification["observed_transition_count"], transitions)
            for row in verification["observations"]:
                output = row["output"]
                self.assertTrue(output["input_unchanged"])
                self.assertTrue(all(s["replay_equal"] and s["recovery_equal"] for s in output["scenarios"]))
                self.assertEqual(output["exploration"]["status"], "BOUNDED_COMPLETE")
                self.assertEqual(output["exploration"]["states"], states)
                self.assertEqual(output["exploration"]["edges"], edges)
            for filename, source in report["files"].items():
                import hashlib
                self.assertEqual(report["artifact_sha256"][filename], hashlib.sha256(source.encode()).hexdigest())

    def test_declaration_order_does_not_change_generated_system(self):
        request = fixture(); request["action"] = "build"
        before = copy.deepcopy(request)
        one = operate_code_system(ROOT, request)
        self.assertEqual(request, before)
        self.assertIsNone(one["verification"])
        self.assertIsNone(one["retention"])
        for key in ("functions", "exports"):
            request["job"]["program"][key].reverse()
        request["job"]["cases"].reverse()
        for key in ("bindings", "invariants", "scenarios"):
            request["system"][key].reverse()
        for key in ("states", "transitions"):
            request["system"]["machine"][key].reverse()
        two = operate_code_system(ROOT, request)
        self.assertEqual(two["status"], "CANDIDATE", two.get("diagnostic"))
        self.assertEqual(one["files"], two["files"])
        self.assertEqual(one["system_sha256"], two["system_sha256"])

    def test_exploration_finds_shortest_sequence_bug_that_function_cases_and_scenarios_miss(self):
        request = fixture("combat")
        hit = next(f for f in request["job"]["program"]["functions"] if f["name"] == "hit")
        hit["body"]["fields"]["health"] = hit["body"]["fields"]["health"]["right"]  # remove only the zero clamp
        result = operate_code_system(ROOT, request)
        self.assertEqual(result["code_workflow"]["result"], "VERIFIED_FOR_CASES")
        self.assertEqual(result["status"], "HOLD")
        self.assertTrue(all(row["passed"] for row in result["verification"]["case_checks"]))
        self.assertEqual(result["files"], {})
        self.assertIsNone(result["retention"])
        for observation in result["verification"]["observations"]:
            exploration = observation["output"]["exploration"]
            self.assertEqual(exploration["status"], "COUNTEREXAMPLE")
            failed = exploration["counterexample"]
            self.assertEqual([e["type"] for e in failed["events"]], ["start", "hit", "hit", "hit"])
            self.assertEqual(failed["result"]["status"], "HOLD_INVARIANT")
            self.assertEqual(failed["result"]["state"], failed["before"])
            self.assertEqual(failed["before"]["model"]["health"], 2)

    def test_wrong_scenario_oracle_holds_even_when_grammar_cases_pass(self):
        request = fixture(); request["system"]["scenarios"][0]["steps"][0]["expect"]["state"]["model"]["stock"] = 999
        result = operate_code_system(ROOT, request)
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["code_workflow"]["result"], "VERIFIED_FOR_CASES")
        self.assertTrue(any(row["code"] == "SCENARIO_EXPECTATION" for row in result["verification"]["issues"]))

    def test_exhausted_budget_and_unobserved_transitions_cannot_pass(self):
        limited = fixture(); limited["system"]["exploration"]["max_edges"] = 1
        held = operate_code_system(ROOT, limited)
        self.assertEqual(held["status"], "HOLD")
        self.assertTrue(any(row["code"] == "EXPLORATION_BUDGET_EXHAUSTED" for row in held["verification"]["issues"]))
        unreachable = fixture()
        unreachable["system"]["machine"]["states"].append("unreachable")
        unreachable["system"]["machine"]["transitions"].append({"from": "unreachable", "event": "restock", "to": "unreachable", "effects": []})
        held = operate_code_system(ROOT, unreachable)
        self.assertEqual(held["status"], "HOLD")
        self.assertTrue(any(row["code"] == "TRANSITION_COVERAGE_INCOMPLETE" for row in held["verification"]["issues"]))

    def test_malformed_composition_is_held_before_compiler_or_observer_invocation(self):
        variants = []
        request = fixture(); request["system"]["bindings"][0]["guard"] = "missing"; variants.append(request)
        request = fixture(); request["system"]["bindings"].append(copy.deepcopy(request["system"]["bindings"][0])); variants.append(request)
        request = fixture(); request["system"]["initial_model"]["stock"] = float("nan"); variants.append(request)
        request = fixture(); request["system"]["exploration"]["max_depth"] = True; variants.append(request)
        request = fixture(); request["observations"] = [{"status": "PASS"}]; variants.append(request)
        request = fixture(); request["system"]["machine"]["transitions"].append(copy.deepcopy(request["system"]["machine"]["transitions"][0])); variants.append(request)
        request = fixture(); request["job"]["program"]["functions"][1]["returns"] = "number"; variants.append(request)
        with patch("axm_uc.code_system.run_grammar_tool") as compiler, patch("axm_uc.code_system._execute") as executor:
            for request in variants:
                self.assertEqual(operate_code_system(ROOT, request)["status"], "HOLD")
            compiler.assert_not_called(); executor.assert_not_called()

    def test_type_error_and_raw_code_never_reach_stateful_executor(self):
        for body in [{"op": "literal", "type": "string", "value": "wrong"}, {"op": "raw", "source": "process.exit()"}]:
            request = fixture(); request["job"]["program"]["functions"][1]["body"] = body
            with patch("axm_uc.code_system._execute") as executor:
                self.assertEqual(operate_code_system(ROOT, request)["status"], "HOLD")
                executor.assert_not_called()

    def test_portable_checkpoint_crosses_languages_and_refuses_changed_state_or_system(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "portable"; root.mkdir(); self.emit(self.combat, root)
            scenario = fixture("combat")["system"]["scenarios"][0]
            events = [step["event"] for step in scenario["steps"][:5]]
            path = root / "events.json"; path.write_text(json.dumps(events))
            for source, receiver in [("javascript", "python"), ("python", "javascript")]:
                checkpoint = self.command(root, source, "checkpoint", str(path))
                self.assertEqual(checkpoint.returncode, 0, checkpoint.stderr)
                snapshot = json.loads(checkpoint.stdout)
                saved = root / "checkpoint.json"; saved.write_text(json.dumps(snapshot))
                restored = self.command(root, receiver, "restore", str(saved))
                self.assertEqual(restored.returncode, 0, restored.stderr)
                self.assertEqual(json.loads(restored.stdout), scenario["steps"][4]["expect"]["state"])
                for bad in ({**snapshot, "system_sha256": "0" * 64}, {**snapshot, "state": {"phase": "running", "model": {"health": 9, "enemy": 6, "ammo": 2}}}):
                    saved.write_text(json.dumps(bad))
                    failed = self.command(root, receiver, "restore", str(saved))
                    self.assertEqual(failed.returncode, 2)
                    self.assertIn("CHECKPOINT_", failed.stderr)

    def test_python_only_emission_still_observes_real_session_twice(self):
        request = fixture(); request["action"] = "verify"; request["job"]["languages"] = ["python"]
        report = operate_code_system(ROOT, request)
        self.assertEqual(report["status"], "VERIFIED_FOR_SCENARIOS")
        self.assertEqual(len(report["verification"]["observations"]), 2)
        self.assertTrue(all(path.startswith("python/") for path in report["files"]))

    def test_generated_verifier_exits_nonzero_and_source_edits_are_detected(self):
        request = fixture(); request["action"] = "build"
        request["system"]["scenarios"][0]["steps"][0]["expect"]["state"]["model"]["stock"] = 999
        built = operate_code_system(ROOT, request)
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "project"; root.mkdir(); self.emit(built, root)
            for language, suffix in (("javascript", "js"), ("python", "py")):
                verified = self.command(root, language, "verify")
                self.assertEqual(verified.returncode, 1, verified.stderr)
                self.assertEqual(json.loads(verified.stdout)["status"], "HOLD")
                self.assertIn("SCENARIO_EXPECTATION", verified.stdout)
                module = root / language / ("module." + suffix)
                module.write_bytes(module.read_bytes() + (b'\n// edited\n' if suffix == "js" else b'\n# edited\n'))
                refused = self.command(root, language, "observe")
                self.assertEqual(refused.returncode, 2)
                self.assertIn("RUNTIME_SOURCE_CHANGED", refused.stderr)

    def test_two_python_products_can_load_in_one_host_without_module_cache_collision(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            self.emit(self.inventory, root / "inventory"); self.emit(self.combat, root / "combat")
            script = root / "host.py"
            script.write_text('import importlib.util, json\nfrom pathlib import Path\n'
                'def load(name):\n'
                '    path=Path(__file__).parent/name/"python/runtime.py"\n'
                '    spec=importlib.util.spec_from_file_location(name+"_runtime",path)\n'
                '    module=importlib.util.module_from_spec(spec); spec.loader.exec_module(module)\n'
                '    return module.load()\n'
                'inventory=load("inventory"); combat=load("combat")\n'
                'print(json.dumps([inventory.initial(),combat.initial(),inventory.initial()]))\n')
            env = dict(os.environ); env.pop("PYTHONPATH", None)
            result = subprocess.run([sys.executable, str(script)], cwd=root.parent, env=env, capture_output=True, text=True, timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            a, b, again = json.loads(result.stdout)
            self.assertEqual(a, again)
            self.assertEqual(a["model"], fixture()["system"]["initial_model"])
            self.assertEqual(b["model"], fixture("combat")["system"]["initial_model"])

    def test_retention_is_idempotent_and_restore_requires_fresh_verification(self):
        request = fixture(); request["archive"] = self.inventory["code_workflow"]["retention"]["archive"]
        request["system_archive"] = self.inventory["retention"]["archive"]
        before = copy.deepcopy(request)
        result = operate_code_system(ROOT, request)
        self.assertEqual(result["status"], "VERIFIED_FOR_SCENARIOS")
        self.assertEqual(result["retention"], self.inventory["retention"])
        self.assertEqual(request, before)
        restored = operate_code_system(ROOT, {"action": "restore", "system_archive": result["retention"]["archive"], "structural_sha256": result["retention"]["structural_sha256"]})
        self.assertEqual(restored["request"], fixture())
        self.assertEqual(restored["verification"], "REQUIRES_FRESH_EXECUTION")

    def test_function_and_project_renames_do_not_create_new_behavior_atoms(self):
        request = fixture()
        names = {function["name"]: "renamed_" + function["name"] for function in request["job"]["program"]["functions"]}
        def rename_calls(value):
            if isinstance(value, dict):
                if value.get("op") == "call": value["function"] = names[value["function"]]
                for child in value.values(): rename_calls(child)
            elif isinstance(value, list):
                for child in value: rename_calls(child)
        for function in request["job"]["program"]["functions"]:
            function["name"] = names[function["name"]]; rename_calls(function["body"])
        request["job"]["program"]["exports"] = [names[name] for name in request["job"]["program"]["exports"]]
        for case in request["job"]["cases"]: case["function"] = names[case["function"]]
        for binding in request["system"]["bindings"]:
            binding["reducer"] = names[binding["reducer"]]
            if "guard" in binding: binding["guard"] = names[binding["guard"]]
        for invariant in request["system"]["invariants"]: invariant["function"] = names[invariant["function"]]
        request["job"]["id"] = "renamed-system"
        request["job"]["program"]["name"] = "renamed_program"
        request["system"]["machine"]["id"] = "renamed-graph"
        request["system_archive"] = self.inventory["retention"]["archive"]
        result = operate_code_system(ROOT, request)
        self.assertEqual(result["status"], "VERIFIED_FOR_SCENARIOS", result.get("diagnostic"))
        self.assertEqual(result["retention"]["structural_sha256"], self.inventory["retention"]["structural_sha256"])
        self.assertEqual(len(result["retention"]["archive"]["entries"]), 1)

    def test_restored_parts_form_a_new_workflow_without_losing_original(self):
        original = self.inventory["retention"]
        restored = operate_code_system(ROOT, {"action": "restore", "system_archive": original["archive"], "structural_sha256": original["structural_sha256"]})["request"]
        restored["job"]["id"] = "inventory-with-audit"
        restored["system"]["machine"]["transitions"].append({"from": "open", "event": "audit", "to": "open", "effects": [{"type": "audit-requested"}]})
        restored["system"]["bindings"].append({"event": "audit", "reducer": "idle"})
        restored["system"]["exploration"]["events"].append({"type": "audit", "args": []})
        restored["system_archive"] = original["archive"]
        restored["archive"] = self.inventory["code_workflow"]["retention"]["archive"]
        result = operate_code_system(ROOT, restored)
        self.assertEqual(result["status"], "VERIFIED_FOR_SCENARIOS", result.get("diagnostic"))
        self.assertEqual(len(result["retention"]["archive"]["entries"]), 2)
        self.assertEqual(len(original["archive"]["entries"]), 1)
        self.assertEqual(len(result["code_workflow"]["retention"]["archive"]["entries"]), len(self.inventory["code_workflow"]["retention"]["archive"]["entries"]))

    def test_changed_archives_are_refused(self):
        for target in ("structure", "construction"):
            archive = copy.deepcopy(self.inventory["retention"]["archive"])
            archive["entries"][0][target]["extra"] = "changed"
            result = operate_code_system(ROOT, {"action": "restore", "system_archive": archive, "structural_sha256": archive["entries"][0]["structural_sha256"]})
            self.assertEqual(result["status"], "HOLD")
            self.assertIn("identity mismatch", result["diagnostic"])

    def test_project_protections_precede_execution_and_failed_cases_publish_nothing(self):
        with tempfile.TemporaryDirectory() as td:
            existing = Path(td) / "existing"; existing.mkdir()
            with patch("axm_uc.code_system.operate_code_system") as execute:
                for path in (existing, ROOT / "src/forbidden-code-system"):
                    with self.assertRaises(CapabilityError): create_code_system_project(ROOT, {"path": str(path), "request": fixture()})
                execute.assert_not_called()
            bad = fixture(); bad["system"]["exploration"]["max_states"] = 1
            target = Path(td) / "failed"
            result = UniversalCreationMachine(ROOT).create({"kind": "code-system-project", "inputs": {"path": str(target), "request": bad}})
            self.assertEqual(result["type"], "CREATION_ERROR")
            self.assertFalse(target.exists())

    def test_atlas_build_retains_retrievable_construction_and_reverifies_reuse(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td); memory = root / "experience"
            intent = json.loads((ROOT / "examples/creation-atlas/inventory-system.json").read_text())["inputs"]["intent"]
            plan = plan_intent(ROOT, intent)
            self.assertEqual(plan["status"], "READY", plan.get("gaps"))
            first = build_intent(ROOT, intent, str(root / "first"), memory=str(memory))
            self.assertEqual(first["status"], "CHECKS_PASSED", first.get("error"))
            self.assertTrue((root / "first/code/python/runtime.py").is_file())
            patterns = operate_atlas(ROOT, {"operation": "query", "memory": str(memory), "categories": ["code-pattern"]})
            self.assertEqual(patterns["matches"], 1)
            pattern = patterns["entries"][0]["id"]
            intent["parameters"]["request"] = {"atlas": pattern, "path": ["request"]}
            again = build_intent(ROOT, intent, str(root / "reused"), memory=str(memory))
            self.assertEqual(again["status"], "CHECKS_PASSED", again.get("error"))
            knowledge = operate_atlas(ROOT, {"operation": "experience", "memory": str(memory)})
            self.assertEqual(knowledge["retained_code_system_signatures"], 1)
            self.assertEqual(knowledge["observations"], 2)
            self.assertFalse(knowledge["automatic_canon_admission"])

    def test_cli_returns_nonzero_for_held_system(self):
        with tempfile.TemporaryDirectory() as td:
            path = Path(td) / "request.json"; path.write_text('{"action":"verify"}')
            completed = subprocess.run([sys.executable, "-m", "axm_uc", "--root", str(ROOT), "code-system", str(path)],
                cwd=td, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, capture_output=True, text=True, timeout=30)
            self.assertEqual(completed.returncode, 2, completed.stderr)
            self.assertEqual(json.loads(completed.stdout)["status"], "HOLD")

    def test_discovery_station_refuses_generation_only_before_writing(self):
        request = fixture(); request["action"] = "build"
        with tempfile.TemporaryDirectory() as td:
            output = Path(td) / "not-verified"
            with self.assertRaisesRegex(ValueError, "verify or retain"):
                run_code_system_station(ROOT, {"operation": "verify-code-system", "path": str(output),
                                              "values": {"request": request}})
            self.assertFalse(output.exists())

    def test_unicode_effects_survive_a_non_utf8_python_terminal(self):
        request = fixture(); request["action"] = "build"
        label = "r\u00e9serve \U0001f30d"
        edge = next(t for t in request["system"]["machine"]["transitions"] if t["event"] == "reserve")
        edge["effects"].append({"label": label})
        for scenario in request["system"]["scenarios"]:
            for step in scenario["steps"]:
                if step["event"]["type"] == "reserve" and step["expect"]["status"] == "APPLIED":
                    step["expect"]["effects"] = copy.deepcopy(edge["effects"])
        built = operate_code_system(ROOT, request)
        self.assertEqual(built["status"], "CANDIDATE")
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); self.emit(built, folder)
            python = subprocess.run([sys.executable, str(folder / "python/runtime.py"), "verify"],
                cwd=folder, env={**os.environ, "PYTHONIOENCODING": "ascii"}, capture_output=True, timeout=30)
            self.assertEqual(python.returncode, 0, python.stderr)
            observed = json.loads(python.stdout)
            javascript = self.command(folder, "javascript", "verify")
            self.assertEqual(javascript.returncode, 0, javascript.stderr)
            self.assertEqual(observed, json.loads(javascript.stdout))
            self.assertEqual(observed["status"], "PASS")
            self.assertTrue(any(e.get("label") == label for s in observed["observations"]["scenarios"]
                                for step in s["steps"] for e in step["effects"]))

    def test_workflow_discovery_executes_confirms_retains_and_rechecks_stateful_code(self):
        from axm_uc.workflow_discovery import plan
        from axm_uc.workflow_experiments import experiment
        from axm_uc.workflow_memory import read_memory
        request = {"schema": "axm.workflow-experiment/v0.1", "intent": "Create recoverable combat logic in both languages",
            "inputs": {"construction": {"type": {"kind": "code-system-request"}, "values": [fixture("combat")]}},
            "goals": {"session": {"type": {"kind": "stateful-code-project", "quality": "checked"},
                "checks": [{"metric": "transition_coverage", "unit": "ratio", "min": 1, "max": 1},
                           {"metric": "languages", "unit": "count", "min": 2},
                           {"metric": "exploration_depth", "unit": "count", "min": 6}]}},
            "budget": {"trials": 2}}
        discovered = plan(ROOT, request)
        self.assertEqual(discovered["status"], "READY", discovered)
        self.assertEqual([[n["operator"] for n in c["program"]["nodes"]] for c in discovered["candidates"]], [["verify-code-system"]])
        with tempfile.TemporaryDirectory() as td:
            folder = Path(td); memory = str(folder / "memory")
            result = experiment(ROOT, request, str(folder / "first"), memory=memory)
            self.assertEqual(result["status"], "VERIFIED_WORKFLOWS", result)
            self.assertEqual(result["trials"], 2)
            observation = json.loads((folder / "first" / result["selected"]["observation"]).read_text())
            self.assertEqual(observation["cases"][0]["metrics"]["session"],
                             {"transition_coverage": 1, "languages": 2, "exploration_depth": 6})
            self.assertTrue(observation["confirmation"][0]["repeatable"])
            self.assertTrue(any(p.endswith("runtime.js") for p in observation["cases"][0]["product_hashes"]))
            self.assertTrue(any(p.endswith("runtime.py") for p in observation["cases"][0]["product_hashes"]))
            self.assertEqual(len(read_memory(ROOT, memory)["workflows"]), 1)
            request["budget"]["states"] = 1
            self.assertEqual(plan(ROOT, request)["status"], "HOLD_CAPABILITY_GAP")
            rebound = plan(ROOT, request, memory=memory)
            self.assertEqual(rebound["status"], "READY")
            self.assertTrue(rebound["candidates"][0]["reused_structure"])
            request["goals"]["session"]["checks"][2]["min"] = 7
            strict = experiment(ROOT, request, str(folder / "strict"), memory=memory)
            self.assertEqual(strict["status"], "HOLD_NO_CONFIRMED_WORKFLOW", strict)
            self.assertIsNone(strict["selected"])
            self.assertEqual(len(read_memory(ROOT, memory)["workflows"]), 1)


if __name__ == "__main__":
    unittest.main()

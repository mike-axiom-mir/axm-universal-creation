import copy
import json
from pathlib import Path
import shutil
import tempfile
import unittest

from axm_uc.atlas_pipeline import build_intent, operate_atlas, plan_intent
from axm_uc.capabilities import CapabilityStore
from axm_uc.creation_atlas import CreationAtlas, digest

ROOT = Path(__file__).resolve().parents[1]


class CreationAtlasTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for directory in ("capabilities/live", "atlas", "examples/construction-search", "examples/code", "executable-organs", "asset-packages"):
            shutil.copytree(ROOT / directory, self.root / directory)
        source = ROOT / "third_party/code-professions/provenance.json"
        destination = self.root / "third_party/code-professions/provenance.json"
        destination.parent.mkdir(parents=True)
        shutil.copy2(source, destination)

    def intent(self, name="vessel"):
        return json.loads((ROOT / "examples/creation-atlas" / (name + ".json")).read_text())["inputs"]["intent"]

    def pack(self):
        return json.loads((self.root / "atlas/construction.json").read_text())

    def save_pack(self, pack):
        (self.root / "atlas/construction.json").write_text(json.dumps(pack))

    def test_index_joins_real_sources_without_promoting_descriptors(self):
        atlas = CreationAtlas(self.root)
        self.assertEqual(atlas.summary(), CreationAtlas(self.root).summary())
        for category in ("texture", "shape", "organ", "capability", "protocol", "workflow", "blueprint", "material", "file"):
            self.assertGreater(atlas.summary()["categories"][category], 0)
        row = atlas.query("armor normal", ["texture"])["entries"][0]
        self.assertEqual(row["evidence"]["status"], "VALIDATED_DESCRIPTOR_RESOURCES_NOT_RESOLVED")
        self.assertFalse(row["evidence"]["execution_observed_by_indexing"])
        self.assertEqual(len(row["source"]["sha256"]), 64)
        closure = atlas.closure(["blueprint:checked-material"])
        self.assertIn("capability:AXM-CAP-INSPECT-GAME-MATERIAL", [r["id"] for r in closure["entries"]])
        store = CapabilityStore(self.root)
        self.assertEqual(store.invoke(store.route("creation-atlas"), {"operation": "summary"}), atlas.summary())

    def test_categories_and_blueprints_extend_as_data(self):
        pack = self.pack()
        pack["entries"].append({"id": "acoustics:room", "category": "acoustics", "summary": "Declared room response", "data": {"seconds": 1.2}})
        route = copy.deepcopy(pack["blueprints"][0])
        route.update(id="custom-construction", direction="custom-direction")
        pack["blueprints"].append(route)
        self.save_pack(pack)
        atlas = CreationAtlas(self.root)
        self.assertEqual(atlas.query(categories=["acoustics"])["matches"], 1)
        request = self.intent(); request["direction"] = "custom-direction"
        self.assertEqual(plan_intent(self.root, request)["selected"]["blueprint"]["id"], "custom-construction")
        pack["entries"].append(copy.deepcopy(pack["entries"][-1])); self.save_pack(pack)
        with self.assertRaisesRegex(ValueError, "duplicate atlas"):
            CreationAtlas(self.root)

    def test_plan_binds_exact_goals_and_does_not_write(self):
        request = self.intent()
        before = copy.deepcopy(request)
        first = plan_intent(self.root, request)
        self.assertEqual(first, plan_intent(self.root, request))
        self.assertEqual(request, before)
        self.assertEqual(first["status"], "READY")
        self.assertIn("recipe:vessel", [r["id"] for r in first["selected"]["knowledge"]["entries"]])
        self.assertFalse((self.root / "creations").exists())
        request["goals"].append("photorealistic-and-physically-stable")
        held = build_intent(self.root, request, "creations/unknown")
        self.assertEqual(held["status"], "HOLD_CAPABILITY_GAP")
        self.assertFalse((self.root / "creations").exists())
        request["direction"] = "uninstalled-direction"
        self.assertIn("no blueprint", plan_intent(self.root, request)["gaps"][0])

    def test_missing_sources_inputs_metrics_and_capabilities_hold_before_creation(self):
        request = self.intent(); request["parameters"]["search"]["atlas"] = "recipe:missing"
        self.assertEqual(plan_intent(self.root, request)["status"], "HOLD_CAPABILITY_GAP")
        request = self.intent(); request["parameters"] = {}
        self.assertIn("missing parameter: search", plan_intent(self.root, request)["gaps"])
        search = CreationAtlas(self.root).get("recipe:vessel")["data"]["value"]
        search["criteria"][0]["metric"] = "beauty"
        request["parameters"] = {"search": search}
        self.assertEqual(plan_intent(self.root, request)["status"], "HOLD_CAPABILITY_GAP")
        (self.root / "capabilities/live/AXM-CAP-CONSTRUCTION-SEARCH.json").unlink()
        self.assertEqual(plan_intent(self.root, self.intent())["status"], "HOLD_CAPABILITY_GAP")

    def test_actual_search_retention_warm_reuse_and_changed_goals_remeasure(self):
        request = self.intent()
        first = build_intent(self.root, request, "creations/first", memory="creations/experience")
        self.assertEqual(first["status"], "CHECKS_PASSED", first.get("error"))
        self.assertTrue((self.root / "creations/first/search/winner.glb.source.json").is_file())
        second = build_intent(self.root, request, "creations/second", memory="creations/experience")
        self.assertEqual(second["status"], "CHECKS_PASSED")
        self.assertEqual(second["steps"]["search"]["counts"]["visited"], 1)
        self.assertTrue(second["reused_experience"])
        search = CreationAtlas(self.root).get("recipe:vessel")["data"]["value"]
        search["criteria"][0].update(min=50, max=60)
        request["parameters"]["search"] = search
        third = build_intent(self.root, request, "creations/impossible", memory="creations/experience")
        self.assertEqual(third["status"], "HOLD_FAILED_CHECK")
        self.assertTrue(third["reused_experience"])
        self.assertFalse((self.root / "creations/impossible/search/winner.glb").exists())
        memory = operate_atlas(self.root, {"operation": "experience", "memory": "creations/experience"})
        self.assertEqual(memory["observations"], 3)
        self.assertEqual(memory["retained_measured_signatures"], 1)
        self.assertFalse(memory["automatic_canon_admission"])
        patterns = operate_atlas(self.root, {"operation": "query", "memory": "creations/experience", "categories": ["construction-pattern"]})
        self.assertEqual(patterns["matches"], 1)
        observed = operate_atlas(self.root, {"operation": "get", "memory": "creations/experience", "id": memory["records"][0]["id"]})
        self.assertEqual(observed["category"], "experience")

    def test_stale_plan_detects_changed_source_and_experience(self):
        request = self.intent()
        plan = plan_intent(self.root, request, memory="creations/memory")
        build_intent(self.root, request, "creations/first", memory="creations/memory")
        result = build_intent(self.root, request, "creations/stale", memory="creations/memory", plan_sha256=plan["plan_sha256"])
        self.assertEqual(result["status"], "HOLD_STALE_PLAN")
        self.assertFalse((self.root / "creations/stale").exists())
        plan = plan_intent(self.root, request)
        path = self.root / "examples/construction-search/vessel.json"
        body = json.loads(path.read_text()); body["inputs"]["search"]["budget"]["candidates"] = 2
        path.write_text(json.dumps(body))
        self.assertEqual(build_intent(self.root, request, "creations/changed", plan_sha256=plan["plan_sha256"])["status"], "HOLD_STALE_PLAN")

    def test_material_pipeline_decodes_output_and_stops_on_failed_policy(self):
        request = self.intent("material")
        first = build_intent(self.root, request, "creations/material")
        self.assertEqual(first["status"], "CHECKS_PASSED", first.get("error"))
        self.assertEqual(first["steps"]["inspect"]["measurements"]["size"], 128)
        request["parameters"]["policy"]["minimum_size"] = 256
        failed = build_intent(self.root, request, "creations/material-failed", memory="creations/memory")
        self.assertEqual(failed["status"], "HOLD_FAILED_CHECK")
        self.assertFalse(failed["goals"]["material-policy"][0]["passed"])
        self.assertTrue((self.root / "creations/material-failed/intent.json").exists())

    def test_organ_goal_resolves_actual_libraries_then_checks_project(self):
        request = self.intent("software")
        plan = plan_intent(self.root, request)
        refs = [r["id"] for r in plan["selected"]["knowledge"]["entries"]]
        self.assertIn("organ:axm.web.shell@1.0.0", refs)
        result = build_intent(self.root, request, "creations/software")
        self.assertEqual(result["status"], "CHECKS_PASSED", result.get("error"))
        self.assertTrue(result["steps"]["verify"]["passed"])
        request["parameters"]["organ_goal"]["required_interfaces"] = ["missing-interface"]
        held = build_intent(self.root, request, "creations/missing")
        self.assertEqual(held["status"], "HOLD_CAPABILITY_GAP")
        self.assertFalse((self.root / "creations/missing").exists())

    @unittest.skipUnless(shutil.which("node"), "Node is required for observed typed-code execution")
    def test_newly_installed_compiler_composes_through_blueprint_data(self):
        for directory in ("third_party/code-professions", "third_party/grammar-workbench"):
            shutil.copytree(ROOT / directory, self.root / directory, dirs_exist_ok=True)
        request = self.intent("programming")
        result = build_intent(self.root, request, "creations/programming")
        self.assertEqual(result["status"], "CHECKS_PASSED", result.get("error"))
        self.assertEqual(result["steps"]["compile-verify"]["code_workflow"]["languages"], ["javascript", "python"])
        self.assertTrue((self.root / "creations/programming/code/archive.json").is_file())
        candidate = CreationAtlas(self.root).get("recipe:restock-code")["data"]["value"]
        candidate["action"] = "build"
        request["parameters"]["request"] = candidate
        self.assertEqual(plan_intent(self.root, request)["status"], "HOLD_CAPABILITY_GAP")

    def test_dependency_cycles_forward_bindings_and_missing_evidence_reject(self):
        pack = self.pack(); route = pack["blueprints"][0]
        route["steps"][0]["depends_on"] = ["search"]; self.save_pack(pack)
        with self.assertRaisesRegex(ValueError, "cyclic"):
            plan_intent(self.root, self.intent())
        route["steps"][0]["depends_on"] = []
        route["steps"][0]["inputs"]["search"] = {"from": "steps.future.result"}; self.save_pack(pack)
        with self.assertRaisesRegex(ValueError, "dependency"):
            plan_intent(self.root, self.intent())
        route["steps"][0]["inputs"]["search"] = {"from": "request.search"}
        route["goals"]["retained-source"] = []; self.save_pack(pack)
        with self.assertRaisesRegex(ValueError, "observable check"):
            plan_intent(self.root, self.intent())

    def test_paths_existing_outputs_and_modified_memory_preserve_state(self):
        request = self.intent()
        with self.assertRaisesRegex(ValueError, "live machine"):
            build_intent(self.root, request, "src/overwrite")
        with self.assertRaisesRegex(ValueError, "separate directories"):
            build_intent(self.root, request, "creations/same", memory="creations/same/memory")
        build_intent(self.root, request, "creations/first", memory="creations/memory")
        old = (self.root / "creations/first/run.json").read_bytes()
        with self.assertRaisesRegex(ValueError, "already exists"):
            build_intent(self.root, request, "creations/first")
        self.assertEqual((self.root / "creations/first/run.json").read_bytes(), old)
        memory_file = next((self.root / "creations/memory").glob("*.json"))
        body = json.loads(memory_file.read_text()); body["status"] = "tampered"
        memory_file.write_text(json.dumps(body))
        plan = plan_intent(self.root, request, memory="creations/memory")
        self.assertEqual(plan["experience"]["observations"], 0)
        self.assertEqual(len(plan["experience"]["ignored"]), 1)
        self.assertEqual(plan["selected"]["reused_experience"], [])
        pack = self.pack(); pack["entries"][0]["source_data"] = {"path": "../outside.json"}; self.save_pack(pack)
        with self.assertRaisesRegex(ValueError, "inside"):
            CreationAtlas(self.root)


if __name__ == "__main__":
    unittest.main()

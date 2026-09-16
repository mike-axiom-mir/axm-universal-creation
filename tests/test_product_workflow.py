import copy
import hashlib
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from axm_uc.capabilities import CapabilityStore
from axm_uc.material_pipeline import material_quality, observe_station
from axm_uc.product_workflow import PROFILES, operate_product_workflow
from test_native_textures import panel

ROOT = Path(__file__).resolve().parents[1]


class ProductWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT/"capabilities/live", self.root/"capabilities/live")

    def call(self, operation, **inputs):
        return operate_product_workflow(self.root, {"operation": operation, **inputs})

    def request(self, kind="material"):
        return {"product_type": kind, "path": "creations/one", "run_id": "first",
                "brief": {"purpose": "Build an inspectable workshop panel", "target": "offline native GLB", "quality_intent": "Readable warm painted surface with controlled wear"},
                "recipe": {"paint": {"family": "painted-metal", "size": 16, "seed": 3}},
                "material_policy": {"minimum_size": 16}, "minimum_texels_per_m": 10,
                "specification": panel(), "preview": {"width": 64, "height": 64}}

    def test_all_product_profiles_have_order_owners_and_honest_gaps(self):
        for kind in PROFILES:
            request = self.request(kind)
            first = self.call("plan", **request)
            self.assertEqual(first, self.call("plan", **request))
            steps = first["stepwise_plan"]["steps"]
            self.assertEqual(steps[0]["id"], "brief")
            self.assertEqual(steps[-1]["id"], "retained-practice")
            self.assertTrue(first["unbound_stages"])
            self.assertTrue(all(s["mode"] == "analysis" for s in steps))
            self.assertTrue(all(s["professional_scope"] for s in first["stages"]))
        self.assertFalse((self.root/"state").exists())

    def test_live_product_route(self):
        store = CapabilityStore(self.root)
        result = store.invoke(store.route("product-workflow"), {"operation": "catalog"})
        self.assertEqual(set(result["products"]), set(PROFILES))

    def test_real_material_run_replay_and_tamper_detection(self):
        request = self.request()
        result = self.call("build", **request)
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        self.assertFalse(result["manifest"]["released"])
        self.assertEqual(self.call("verify", path=result["delivery"])["status"], "PASS")
        self.assertEqual(self.call("build", **request)["status"], "RECORDED_DRAFT")
        (self.root/"creations/one/materials/paint/base_color.png").write_bytes(b"corrupted")
        with self.assertRaises((ValueError, OSError)):
            material_quality(self.root/"creations/one/materials/paint")
        self.assertEqual(self.call("build", **request)["status"], "HOLD_STALE_OR_INCOMPLETE")

    def test_quality_failure_stops_before_asset_and_preview(self):
        request = self.request("static-3d")
        request["material_policy"] = {"minimum_size": 128}
        result = self.call("build", **request)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertFalse((self.root/"creations/one/asset.glb").exists())
        self.assertFalse((self.root/"creations/one/previews").exists())

    def test_world_dimension_failure_stops_before_render(self):
        request = self.request("static-3d")
        request["maximum_size_m"] = [.5, 1, 1]
        result = self.call("build", **request)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK")
        self.assertTrue((self.root/"creations/one/asset.glb").exists())
        self.assertFalse((self.root/"creations/one/previews").exists())

    def test_static_asset_end_to_end_and_refinement_preserves_previous(self):
        request = self.request("static-3d")
        first = self.call("build", **request)
        self.assertEqual(first["status"], "DRAFT_BUILT_REVIEW_REQUIRED", first)
        prior = (self.root/"creations/one/asset.glb").read_bytes()
        request.update(path="creations/two", run_id="second", refines=first["delivery"], revision_reason="Change surface color while keeping geometry")
        request["recipe"]["paint"]["color"] = [20,100,160]
        second = self.call("refine", **request)
        self.assertEqual(second["fresh"]["status"], "PASS", second)
        self.assertEqual((self.root/"creations/one/asset.glb").read_bytes(), prior)
        self.assertNotEqual((self.root/"creations/two/asset.glb").read_bytes(), prior)
        self.assertTrue(second["manifest"]["parent"]["sha256"])
        self.assertEqual(self.call("verify", path=first["delivery"])["status"], "PASS")

    def test_existing_target_and_invalid_refinement_refuse_writes(self):
        request = self.request()
        path = self.root/request["path"]
        path.mkdir(parents=True)
        sentinel = path/"source.json"
        sentinel.write_text("preserve")
        with self.assertRaises(FileExistsError):
            self.call("build", **request)
        self.assertEqual(sentinel.read_text(), "preserve")
        with self.assertRaises(ValueError):
            self.call("refine", **request)

    def test_software_and_web_draft_recipes_use_existing_checks(self):
        for index, kind in enumerate(("software", "web")):
            request = self.request(kind)
            request.update(path="creations/"+kind, run_id=kind)
            request["files"] = {"main.py": "print('hello')\n"} if kind == "software" else {"index.html": "<!doctype html><html><head><title>Test</title></head><body><h1>Test</h1></body></html>"}
            result = self.call("build", **request)
            self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)

    def test_unimplemented_products_remain_explicit_plans(self):
        with self.assertRaisesRegex(ValueError, "currently has a plan"):
            self.call("build", **self.request("game"))
        self.assertFalse((self.root/"creations").exists())

    def test_animated_recipe_requires_authored_source(self):
        with self.assertRaisesRegex(ValueError, "authored rigged GLB"):
            self.call("build", **self.request("animated-3d"))

    def test_forged_quality_report_cannot_satisfy_fresh_observer(self):
        request = self.request()
        result = self.call("build", **request)
        path = self.root/"creations/one/checks/paint.json"
        report = json.loads(path.read_text())
        report["measurements"]["size"] = 4096
        path.write_text(json.dumps(report))
        self.assertEqual(self.call("verify", path=result["delivery"])["status"], "NOT_CURRENT_PASS")


if __name__ == "__main__":
    unittest.main()

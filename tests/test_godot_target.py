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

from axm_uc.capabilities import CapabilityStore
from axm_uc.godot_target import _geometry_checks, _poses, observe_station, run_station, target_options
from axm_uc.game_pose_runtime import GamePoseAsset
from axm_uc.procedural_3d import build_glb
from axm_uc.product_workflow import compile_draft, operate_product_workflow
from test_native_textures import panel

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from mesh_production_demo import flex_asset


class TargetContracts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "capabilities/live", self.root / "capabilities/live")
        (self.root / "creations").mkdir()
        (self.root / "creations/source.glb").write_bytes(flex_asset())
        self.inputs = {"asset": "creations/source.glb", "path": "creations/target", "options": {"engine": "godot", "width": 96, "height": 96}}

    def request(self):
        return {"operation": "build", "product_type": "animated-3d", "path": "creations/flex", "run_id": "godot-flex",
                "asset": "creations/source.glb", "brief": {"purpose": "Verify authored flex in game engine", "target": "Godot", "quality_intent": "Preserved shape and continuous closed flex"},
                "production": {"target": copy.deepcopy(self.inputs["options"])}}

    def test_station_is_registered_and_product_selects_actual_engine(self):
        store = CapabilityStore(self.root)
        self.assertIsNotNone(store.route("validate-godot-target"))
        compiled = compile_draft(self.root, self.request())
        self.assertEqual(compiled["job"]["steps"][-1]["action"]["kind"], "validate-godot-target")

    def test_multiple_targets_are_distinct_ordered_stations(self):
        request = self.request()
        request["production"] = {"targets": [{"engine": "blender-cycles"}, {"engine": "godot"}]}
        steps = compile_draft(self.root, request)["job"]["steps"]
        self.assertEqual([s["action"]["kind"] for s in steps[-2:]], ["validate-blender-target", "validate-godot-target"])
        self.assertEqual(steps[-1]["depends_on"], [steps[-2]["id"]])
        self.assertNotEqual(steps[-1]["action"]["inputs"]["path"], steps[-2]["action"]["inputs"]["path"])

    def test_unavailable_or_ambiguous_target_cannot_borrow_a_pass(self):
        for production in ({"target": {"engine": "unity"}}, {"target": {"engine": "unreal"}},
                           {"targets": [{"engine": "godot"}, {"engine": "godot"}]},
                           {"targets": []}, {"target": {}, "targets": [{}]}):
            request = self.request()
            request["production"] = production
            with self.assertRaises(ValueError):
                compile_draft(self.root, request)
        self.assertFalse((self.root / "creations/flex").exists())

    def test_missing_runtime_does_not_publish_output(self):
        with patch.dict(os.environ, {"AXM_GODOT": str(self.root / "missing-godot")}):
            with self.assertRaisesRegex(RuntimeError, "backend unavailable"):
                run_station(self.root, "validate-godot-target", self.inputs)
        self.assertFalse((self.root / "creations/target").exists())

    def test_existing_output_and_source_are_preserved(self):
        (self.root / "creations/target").mkdir()
        sentinel = self.root / "creations/target/keep.txt"
        sentinel.write_text("unchanged")
        with self.assertRaises(FileExistsError):
            run_station(self.root, "validate-godot-target", self.inputs)
        self.assertEqual(sentinel.read_text(), "unchanged")

    def test_worker_failure_retains_log_input_and_failure_report(self):
        source = (self.root / "creations/source.glb").read_bytes()
        with patch("axm_uc.godot_target.godot_executable", return_value=sys.executable), \
             patch("axm_uc.godot_target.subprocess.run", return_value=subprocess.CompletedProcess([], 2)):
            report = run_station(self.root, "validate-godot-target", self.inputs)
        self.assertEqual(report["status"], "FAIL")
        self.assertIn("worker.log", report["failure"])
        self.assertTrue((self.root / "creations/target/worker.log").exists())
        self.assertEqual((self.root / "creations/target/asset.glb").read_bytes(), source)
        self.assertEqual((self.root / "creations/source.glb").read_bytes(), source)

    def test_options_and_playback_are_bounded(self):
        for options in ({"width": True}, {"width": 1025}, {"engine": "unreal"}, {"views": []},
                        {"playback": {"clip": "Flex", "fps": 0, "frames": 30}},
                        {"width": 1024, "height": 1024, "playback": {"clip": "Flex", "fps": 60, "frames": 121}}):
            with self.assertRaises(ValueError):
                target_options({"options": options})
        asset = GamePoseAsset(flex_asset())
        for playback in ({"clip": "Unknown", "fps": 30, "frames": 3}, {"clip": "Flex", "fps": 1, "frames": 3}):
            with self.assertRaises(ValueError):
                _poses(asset, target_options({"options": {"playback": playback}}))

    def test_missing_and_wrong_target_geometry_are_rejected(self):
        asset = GamePoseAsset(flex_asset())
        poses = [{"clip": "Flex", "time_s": .5}]
        self.assertFalse(_geometry_checks(asset, poses, [], 44)[1])
        false_bounds = [{"bounds_m": {"min": [0, 0, 0], "max": [0, 0, 0]}, "triangles": 44}]
        self.assertFalse(_geometry_checks(asset, poses, false_bounds, 44)[1])


@unittest.skipUnless(os.environ.get("AXM_GODOT"), "requires actual configured Godot and graphics display")
class RealGodotTarget(unittest.TestCase):
    setUp = TargetContracts.setUp
    request = TargetContracts.request

    def assert_product(self, result, target):
        report = self.root / target / "report.json"
        detail = report.read_text() if report.exists() else json.dumps(result["run"].get("error", result["status"]))
        if result["status"] != "DRAFT_BUILT_REVIEW_REQUIRED" and os.environ.get("AXM_TARGET_FAILURES"):
            shutil.copytree(self.root, Path(os.environ["AXM_TARGET_FAILURES"]) / self._testMethodName, dirs_exist_ok=True)
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", detail)
    def test_actual_textured_import_render_and_tamper_observation(self):
        # The existing UC compiler makes an actual textured asset and observes
        # all material, native preview and game-engine stations.
        request = {"operation": "build", "product_type": "static-3d", "path": "creations/panel", "run_id": "godot-panel",
            "brief": {"purpose": "Import and render a textured UC panel", "target": "Godot", "quality_intent": "Exact source and visible decoded materials"},
            "recipe": {"paint": {"family": "painted-metal", "size": 16, "seed": 3}},
            "material_policy": {"minimum_size": 16}, "minimum_texels_per_m": 1,
            "specification": panel(), "preview": {"width": 64, "height": 64},
            "production": {"target": {"engine": "godot", "width": 96, "height": 96, "views": [{"yaw": 0., "elevation": .3}]}}}
        result = operate_product_workflow(self.root, request)
        self.assert_product(result, "creations/panel/target")
        self.assertEqual(result["fresh"]["status"], "PASS", result)
        self.assertFalse(result["manifest"]["released"])
        inputs = {"asset": "creations/panel/asset.glb", "path": "creations/panel/target", "options": request["production"]["target"]}
        evidence = self.root / inputs["path"]
        report = json.loads((evidence / "report.json").read_text())
        self.assertTrue(report["material_bindings"][0]["albedo"])
        (evidence / "view-00.png").write_bytes(b"tampered render")
        self.assertEqual(observe_station(self.root, "validate-godot-target", inputs)["status"], "FAIL")

    def test_actual_skin_playback_and_forged_receipt(self):
        request = self.request()
        request["production"]["target"].update(
            views=[{"yaw": .5, "elevation": .3, "clip": "Flex", "time_s": .5}],
            playback={"clip": "Flex", "fps": 8, "frames": 9})
        result = operate_product_workflow(self.root, request)
        self.assert_product(result, "creations/flex/target")
        report_path = self.root / "creations/flex/target/report.json"
        report = json.loads(report_path.read_text())
        self.assertEqual(len(report["playback_comparison"]), 9)
        self.assertLess(max(r["bounds_error_m"] for r in report["playback_comparison"]), 1e-4)
        inputs = {"asset": "creations/flex/asset.glb", "path": "creations/flex/target", "options": request["production"]["target"]}
        report["pose_comparison"][0]["bounds_error_m"] = 123
        report_path.write_text(json.dumps(report))
        self.assertEqual(observe_station(self.root, "validate-godot-target", inputs)["status"], "FAIL")


if __name__ == "__main__":
    unittest.main()

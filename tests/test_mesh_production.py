import copy
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from axm_uc.mesh_production import blender_executable, observe_station, run_station
from axm_uc.native_textures import decode_png
from axm_uc.product_workflow import operate_product_workflow
from test_native_textures import maps, panel
from test_game_pose_runtime import encode, fixture

ROOT = Path(__file__).resolve().parents[1]
BLENDER = os.environ.get("AXM_BLENDER") or shutil.which("blender")


class NativeProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root/"creations").mkdir()
        doc,binary = fixture()
        self.body = encode(doc,binary)
        (self.root/"creations/rig.glb").write_bytes(self.body)

    def test_animation_copy_preserves_source_and_detects_tamper(self):
        request = {"path":"creations/copy.glb","asset":"creations/rig.glb"}
        run_station(self.root,"copy-animation-asset",request)
        self.assertEqual(observe_station(self.root,"copy-animation-asset",request)["status"],"PASS")
        (self.root/"creations/copy.glb").write_bytes(b"changed")
        self.assertEqual(observe_station(self.root,"copy-animation-asset",request)["status"],"FAIL")
        self.assertEqual((self.root/"creations/rig.glb").read_bytes(),self.body)

    def test_stale_deformation_report_cannot_pass(self):
        request = {"path":"creations/check.json","asset":"creations/rig.glb"}
        run_station(self.root,"inspect-deformation",request)
        stored = json.loads((self.root/"creations/check.json").read_text())
        stored["clips"][0]["minimum_area_ratio"] = 1e9
        (self.root/"creations/check.json").write_text(json.dumps(stored))
        self.assertEqual(observe_station(self.root,"inspect-deformation",request)["status"],"FAIL")

    def test_missing_blender_is_an_explicit_error_without_output(self):
        with patch.dict(os.environ,{"AXM_BLENDER":"/not/a/blender"}):
            with self.assertRaisesRegex(RuntimeError,"backend unavailable"):
                run_station(self.root,"unwrap-surface-uv",{"path":"creations/uv","specification":panel()})
        self.assertFalse((self.root/"creations/uv").exists())

    def test_failed_declared_loop_stops_workflow_before_target(self):
        shutil.copytree(ROOT/"capabilities/live",self.root/"capabilities/live")
        request = {"operation":"build","product_type":"animated-3d","path":"creations/product","run_id":"bad-loop",
                   "asset":"creations/rig.glb","brief":{"purpose":"Verify a closed loop","target":"blender-cycles","quality_intent":"No endpoint discontinuity"},
                   "production":{"deformation":{"loop_clips":["Slide"]},"target":{}}}
        result = operate_product_workflow(self.root,request)
        self.assertEqual(result["status"],"HOLD_FAILED_CHECK")
        self.assertTrue((self.root/"creations/product/asset.glb").exists())
        self.assertFalse((self.root/"creations/product/target").exists())

    def test_existing_output_and_invalid_options_refuse(self):
        with self.assertRaises(FileExistsError):
            run_station(self.root,"copy-animation-asset",{"path":"creations/rig.glb","asset":"creations/rig.glb"})
        for options in ({"width":100000},{"engine":"unknown"},{"views":[]},{"samples":float("nan")}):
            with self.assertRaises(ValueError):
                run_station(self.root,"validate-blender-target",{"path":"creations/target","asset":"creations/rig.glb","options":options})


@unittest.skipUnless(BLENDER,"optional real Blender backend not configured")
class BlenderProductionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def unwrap(self,size=32):
        request = {"path":"creations/uv","specification":panel(),"options":{"resolution":size,"padding_px":2}}
        r = run_station(self.root,"unwrap-surface-uv",request)
        self.assertEqual(r["status"],"PASS",r)
        return request,json.loads((self.root/"creations/uv/surface.json").read_text())

    def test_real_unwrap_reproduces_and_forged_layout_fails(self):
        request,spec = self.unwrap()
        self.assertEqual(observe_station(self.root,"unwrap-surface-uv",request)["status"],"PASS")
        spec["primitives"][0]["texcoords"][0][0] = -1
        (self.root/"creations/uv/surface.json").write_text(json.dumps(spec))
        self.assertEqual(observe_station(self.root,"unwrap-surface-uv",request)["status"],"FAIL")

    def test_real_mesh_ao_high_to_low_transfer_and_missed_cage(self):
        _,spec = self.unwrap(16)
        spec["primitives"][0]["id"] = "paint.001"
        spec["primitives"][0]["textures"] = maps()
        high = panel()
        high["primitives"][0]["id"] = "paint.001"
        # A raised tilted plane has a known non-flat tangent normal. The
        # projection reaches it only when the outward cage covers its height.
        for p in high["primitives"][0]["positions"]:
            p[2] = .04+p[0]*.03
        high["primitives"][0]["normals"] = [[-.0299865,0,.9995503]]*4
        request = {"path":"creations/baked","specification":spec,"high_specification":high,
                   "options":{"size":16,"margin_px":1,"samples":2,"cage_extrusion":.08,"max_ray_distance":.2}}
        r = run_station(self.root,"bake-mesh-maps",request)
        self.assertEqual(r["status"],"PASS",r)
        data = decode_png((self.root/"creations/baked/paint.001-normal.png").read_bytes())[2]
        self.assertTrue(any(0 < data[i] < 127 or data[i] > 129 for i in range(0,len(data),3)))
        self.assertEqual(observe_station(self.root,"bake-mesh-maps",request)["status"],"PASS")
        request["path"] = "creations/missed"
        request["options"].update(cage_extrusion=0,max_ray_distance=.001)
        missed = run_station(self.root,"bake-mesh-maps",request)
        self.assertEqual(missed["status"],"FAIL",missed)
        self.assertGreater(missed["bake"][0]["unhit_normal_texels"],0)

    def test_real_product_connects_uv_bake_and_target_and_preserves_source(self):
        shutil.copytree(ROOT/"capabilities/live",self.root/"capabilities/live")
        spec = panel()
        before = copy.deepcopy(spec)
        request = {"operation":"build","product_type":"static-3d","path":"creations/product","run_id":"production",
            "brief":{"purpose":"Test ordered production","target":"blender-cycles","quality_intent":"Explicit small technical fixture"},
            "specification":spec,"recipe":{"paint":{"family":"painted-metal","size":16}},
            "material_policy":{"minimum_size":16},"minimum_texels_per_m":1,"preview":{"width":64,"height":64},
            "production":{"uv":{"resolution":16,"padding_px":1},"bake":{"size":16,"margin_px":1,"samples":1},
                          "target":{"width":64,"height":64,"samples":1,"views":[{"yaw":.4,"elevation":.2}]}}}
        result = operate_product_workflow(self.root,request)
        self.assertEqual(result["status"],"DRAFT_BUILT_REVIEW_REQUIRED",result)
        self.assertEqual(spec,before)
        self.assertFalse(result["manifest"]["released"])
        report = json.loads((self.root/"creations/product/target/report.json").read_text())
        self.assertEqual(report["status"],"PASS")
        self.assertGreater(report["images"][0]["asset_visible_pixels"],0)
        self.assertEqual(report["backend"]["version"].split(".")[0],"4")


if __name__ == "__main__":
    unittest.main()

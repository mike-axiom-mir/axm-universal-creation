import copy
import math
import struct
import unittest

from axm_uc.mesh_quality import inspect_deformation, inspect_uv_layout
from test_game_pose_runtime import encode, fixture
from test_native_textures import panel


class MeshQualityTests(unittest.TestCase):
    def test_shared_edge_is_not_overlap_and_border_is_measured(self):
        spec = panel()
        spec["primitives"][0]["texcoords"] = [[.1,.9],[.9,.9],[.9,.1],[.1,.1]]
        report = inspect_uv_layout(spec,100,5)
        self.assertEqual(report["status"],"PASS")
        self.assertEqual(report["groups"][0]["islands"],1)
        self.assertAlmostEqual(report["groups"][0]["border_padding_px"],10)

    def test_positive_area_overlap_detects_duplicate_triangles(self):
        spec = panel()
        spec["primitives"][0]["indices"] += [0,1,2]
        r = inspect_uv_layout(spec,128,0)
        self.assertEqual(r["status"],"FAIL")
        self.assertGreater(r["groups"][0]["overlap_area_uv"],0)

    def test_geometrically_disconnected_charts_need_padding(self):
        spec = panel()
        group = spec["primitives"][0]
        group["positions"] = [[0,0,0],[1,0,0],[0,1,0],[5,0,0],[6,0,0],[5,1,0]]
        group["indices"] = [0,1,2,3,4,5]
        group["texcoords"] = [[.1,.1],[.4,.1],[.1,.4],[.41,.1],[.7,.1],[.7,.4]]
        r = inspect_uv_layout(spec,100,2)
        self.assertEqual(r["groups"][0]["overlapping_pairs"],0)
        self.assertFalse(r["groups"][0]["checks"]["island_padding"])

    def test_uv_bounds_and_collapse_fail(self):
        for uv in ([[0,0]]*4,[[-.2,1],[1,1],[1,0],[0,0]]):
            spec = panel()
            spec["primitives"][0]["texcoords"] = uv
            self.assertEqual(inspect_uv_layout(spec,128,1)["status"],"FAIL")

    def test_authored_keys_and_subdivisions_are_sampled(self):
        doc,binary = fixture()
        report = inspect_deformation(encode(doc,binary),{"minimum_area_ratio":.001,"maximum_edge_ratio":10})
        self.assertEqual(report["clips"][0]["times_s"],[0,.25,.5,.75,1])
        self.assertGreater(report["clips"][0]["maximum_motion_m"],0)

    def test_loop_and_contact_policies_detect_real_drift(self):
        doc,binary = fixture()
        r = inspect_deformation(encode(doc,binary),{"loop_clips":["Slide"],"contacts":[
            {"clip":"Slide","mesh":0,"vertex":0,"start_s":0,"end_s":1,"maximum_drift_m":.01}]})
        slide = next(c for c in r["clips"] if c["clip"] == "Slide")
        self.assertFalse(slide["checks"]["declared_loop_continuity"])
        self.assertFalse(slide["checks"]["declared_contacts"])
        self.assertAlmostEqual(slide["contacts"][0]["observed_maximum_drift_m"],2.)

    def test_scale_collapse_at_authored_extreme_is_detected(self):
        doc,binary = fixture()
        # Reuse the two vec3 translation values as a root scale channel.
        anim = doc["animations"][1]
        anim["channels"][0]["target"]["path"] = "scale"
        ref = anim["samplers"][0]["output"]
        offset = doc["bufferViews"][doc["accessors"][ref]["bufferView"]]["byteOffset"]
        struct.pack_into("<6f",binary,offset,1,1,1,0,0,0)
        r = inspect_deformation(encode(doc,binary))
        row = next(c for c in r["clips"] if c["clip"] == "Slide")
        self.assertEqual(row["minimum_area_ratio"],0)
        self.assertFalse(row["checks"]["no_sampled_collapse"])

    def test_policy_rejects_unknown_clip_invalid_bounds_and_unbounded_sampling(self):
        doc,binary = fixture()
        for policy in ({"loop_clips":["absent"]},{"samples_per_interval":100000},{"maximum_edge_ratio":float("nan")},{"anything":True}):
            with self.assertRaises(ValueError):
                inspect_deformation(encode(doc,binary),policy)


if __name__ == "__main__":
    unittest.main()

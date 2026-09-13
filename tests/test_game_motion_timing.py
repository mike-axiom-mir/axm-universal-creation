import copy
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_motion_timing import (PROFILES, compose_game_motion,
                                       game_motion_timing_catalog, publish_game_motion)
from axm_uc.visual_assets_cli import main


def request(loop=True):
    half = math.sin(math.pi / 4)
    return {
        "name": "Hammer_Slam",
        "fps": 30,
        "duration": 1.2,
        "loop": loop,
        "channels": [
            {"target": "Root", "path": "translation", "rest": [0, 0, 0],
             "action": [0, -.12, 0], "contact_at_impact": True},
            {"target": "Hammer", "path": "rotation", "rest": [0, 0, 0, 1],
             "action": [half, 0, 0, half], "anticipation_scale": .8,
             "contact_at_impact": True},
            {"target": "Body", "path": "scale", "rest": [1, 1, 1],
             "action": [1.08, .86, 1.08]},
        ],
    }


class GameMotionTimingTests(unittest.TestCase):
    def test_catalog_exposes_distinct_timing_not_geometry_or_material_claims(self):
        catalog = game_motion_timing_catalog()
        self.assertEqual([row["name"] for row in catalog["profiles"]], [row.name for row in PROFILES])
        self.assertTrue(catalog["canonical_source_preserved"])
        self.assertTrue(catalog["material_and_geometry_unchanged"])
        self.assertIn("does not infer a rig", catalog["truth"])

    def test_all_profiles_are_deterministic_accelerated_and_have_exact_events(self):
        source = request()
        original = copy.deepcopy(source)
        digests = set()
        for profile in PROFILES:
            one = compose_game_motion(source, profile.name)
            two = compose_game_motion(source, profile.name)
            self.assertEqual(one, two)
            self.assertTrue(one["receipt"]["passed"])
            self.assertGreater(one["receipt"]["action_acceleration_ratio"], 1)
            events = {row["name"]: row["frame"] for row in one["clip"]["events"]}
            self.assertEqual(one["clip"]["tracks"][0]["values"][events["impact"]], [0, -.12, 0])
            self.assertEqual(one["receipt"]["maximum_loop_seam_error"], 0)
            digests.add(json.dumps(one["profile"], sort_keys=True))
        self.assertEqual(len(digests), len(PROFILES))
        self.assertEqual(source, original)

    def test_motion_is_sampled_every_frame_with_strict_portable_times(self):
        result = compose_game_motion(request(), "weighty-salvage")
        clip = result["clip"]
        expected = round(clip["duration"] * clip["fps"]) + 1
        for track in clip["tracks"]:
            self.assertEqual(len(track["times"]), expected)
            self.assertEqual(len(track["values"]), expected)
            self.assertTrue(all(b > a for a, b in zip(track["times"], track["times"][1:])))
            self.assertEqual(track["interpolation"], "LINEAR")

    def test_quaternions_stay_normalized_and_follow_shortest_hemisphere(self):
        source = request()
        source["channels"][1]["action"] = [-math.sin(math.pi / 4), 0, 0, -math.sin(math.pi / 4)]
        result = compose_game_motion(source, "snappy-comic")
        rotation = result["clip"]["tracks"][1]
        self.assertLessEqual(result["receipt"]["maximum_quaternion_norm_error"], 1e-10)
        for value in rotation["values"]:
            self.assertAlmostEqual(sum(component * component for component in value), 1, places=10)
        self.assertGreater(rotation["values"][result["receipt"]["impact_frame"]][3], 0)

    def test_profile_changes_timing_shape_not_requested_endpoints(self):
        source = request()
        heavy = compose_game_motion(source, "weighty-salvage")
        comic = compose_game_motion(source, "snappy-comic")
        self.assertNotEqual(heavy["clip"]["events"], comic["clip"]["events"])
        for channel, a, b in zip(source["channels"], heavy["clip"]["tracks"], comic["clip"]["tracks"]):
            self.assertEqual(a["values"][0], b["values"][0])
            self.assertEqual(a["values"][-1], b["values"][-1])
            for value, expected in zip(a["values"][heavy["receipt"]["impact_frame"]], channel["action"]):
                self.assertAlmostEqual(abs(value), abs(expected), places=12)
            for value, expected in zip(b["values"][comic["receipt"]["impact_frame"]], channel["action"]):
                self.assertAlmostEqual(abs(value), abs(expected), places=12)

    def test_nonloop_clip_still_settles_without_claiming_a_loop_requirement(self):
        result = compose_game_motion(request(False), "restrained-product")
        self.assertFalse(result["clip"]["loop"])
        self.assertEqual(result["receipt"]["final_settle_weight"], 0)
        self.assertTrue(result["gates"]["loop-seam-exact-when-requested"])

    def test_validation_rejects_ambiguous_or_unsafe_requests(self):
        cases = []
        bad = request(); bad["extra"] = True; cases.append(bad)
        bad = request(); bad["fps"] = 5; cases.append(bad)
        bad = request(); bad["channels"].append(copy.deepcopy(bad["channels"][0])); cases.append(bad)
        bad = request(); bad["channels"][1]["rest"] = [0, 0, 0, 0]; cases.append(bad)
        bad = request(); bad["channels"][2]["action"] = [-1, 1, 1]; cases.append(bad)
        for bad in cases:
            with self.assertRaises(ValueError):
                compose_game_motion(bad)
        unsafe = request()
        unsafe["channels"][2]["rest"] = [.01, .01, .01]
        unsafe["channels"][2]["action"] = [10, 10, 10]
        with self.assertRaisesRegex(ValueError, "invert scale"):
            compose_game_motion(unsafe, "snappy-comic")

    def test_publisher_and_cli_are_transactional(self):
        with tempfile.TemporaryDirectory() as tmp:
            direct = Path(tmp) / "direct"
            published = publish_game_motion(direct, request(), "springy-adventure")
            self.assertEqual(published["files"], ["motion-clip.json", "motion-receipt.json", "source.json"])
            with self.assertRaises(FileExistsError):
                publish_game_motion(direct, request())
            request_path, output = Path(tmp) / "request.json", Path(tmp) / "cli"
            request_path.write_text(json.dumps(request()))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["motion-compose", str(request_path), str(output),
                                       "--profile", "snappy-comic"]), 0)
            self.assertEqual(json.loads((output / "motion-clip.json").read_text())["name"], "Hammer_Slam")


if __name__ == "__main__":
    unittest.main()

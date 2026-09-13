import copy
import io
import json
import math
from contextlib import redirect_stdout
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_motion_timing import compose_game_motion
from axm_uc.game_secondary_motion import (PROFILES, compose_secondary_motion,
                                          game_secondary_motion_catalog,
                                          publish_secondary_motion)
from axm_uc.visual_assets_cli import main


def primary():
    half = math.sin(math.pi / 4)
    return compose_game_motion({
        "name": "Bell_Smack", "fps": 30, "duration": 1.2, "loop": True,
        "channels": [
            {"target": "Root", "path": "translation", "rest": [0, 0, 0],
             "action": [0, 0, -.1]},
            {"target": "Hammer", "path": "rotation", "rest": [0, 0, 0, 1],
             "action": [0, 0, -half, half]},
        ],
    }, "weighty-salvage")


def request():
    return {
        "name": "Bell_Smack_With_Followthrough",
        "attachments": [
            {"target": "Coil", "path": "scale", "rest": [1, 1, 1],
             "axis": [0, 0, 1], "amplitude": .16,
             "driver_target": "Root", "driver_path": "translation", "driver_component": 2,
             "motion_class": "coil-spring"},
            {"target": "Antenna", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [0, 1, 0], "amplitude": .34,
             "driver_target": "Root", "driver_path": "translation", "driver_component": 2,
             "motion_class": "antenna"},
            {"target": "CapeTip", "path": "rotation", "rest": [0, 0, 0, 1],
             "axis": [1, 0, 0], "amplitude": .46,
             "driver_target": "Hammer", "driver_path": "rotation", "driver_component": 2,
             "motion_class": "cloth-tail", "lag_frames": 4},
            {"target": "ToolBag", "path": "translation", "rest": [0, 0, 0],
             "axis": [1, 0, 0], "amplitude": .09,
             "driver_target": "Hammer", "driver_path": "rotation", "driver_component": 2,
             "motion_class": "carried-prop", "direction": -1},
        ],
    }


class GameSecondaryMotionTests(unittest.TestCase):
    def test_catalog_names_real_secondary_classes_and_truth_boundary(self):
        catalog = game_secondary_motion_catalog()
        self.assertEqual([row["name"] for row in catalog["profiles"]],
                         [profile.name for profile in PROFILES])
        self.assertTrue(catalog["canonical_primary_preserved"])
        self.assertIn("does not infer a rig", catalog["truth"])
        self.assertIn("soft-body", catalog["truth"])

    def test_composition_is_deterministic_and_preserves_both_sources(self):
        source_primary, source_request = primary(), request()
        saved_primary, saved_request = copy.deepcopy(source_primary), copy.deepcopy(source_request)
        one = compose_secondary_motion(source_primary, source_request)
        two = compose_secondary_motion(source_primary, source_request)
        self.assertEqual(one, two)
        self.assertEqual(source_primary, saved_primary)
        self.assertEqual(source_request, saved_request)
        self.assertEqual(one["primary"], source_primary)
        self.assertEqual(one["source"], source_request)
        self.assertTrue(one["gates"]["primary-byte-equivalent"])

    def test_every_track_uses_primary_clock_and_closes_exactly(self):
        result = compose_secondary_motion(primary(), request())
        source_times = result["primary"]["clip"]["tracks"][0]["times"]
        for track in result["clip"]["tracks"]:
            self.assertEqual(track["times"], source_times)
            self.assertEqual(track["interpolation"], "LINEAR")
            self.assertEqual(track["values"][0], track["values"][-1])
        self.assertEqual(result["receipt"]["maximum_loop_seam_error"], 0)
        self.assertTrue(result["receipt"]["passed"])

    def test_classes_create_bounded_distinct_followthrough(self):
        result = compose_secondary_motion(primary(), request())
        receipts = result["receipt"]["tracks"]
        self.assertEqual({row["motion_class"] for row in receipts},
                         {profile.name for profile in PROFILES})
        self.assertEqual(len({round(row["peak_displacement"], 5) for row in receipts}), 4)
        for row in receipts:
            self.assertGreater(row["peak_displacement"], 0)
            self.assertLessEqual(row["peak_displacement"], row["amplitude_limit"])

    def test_declared_lag_is_causal_and_chainable(self):
        source = request()
        source["attachments"] = [copy.deepcopy(source["attachments"][1]) for _ in range(3)]
        for index, row in enumerate(source["attachments"]):
            row["target"] = f"Antenna_{index}"
            row["lag_frames"] = index * 3
        result = compose_secondary_motion(primary(), source)
        observed = [row["observed_response_lag_frames"] for row in result["receipt"]["tracks"]]
        self.assertEqual(observed, [0, 3, 6])

    def test_rotation_values_are_normalized_and_scale_stays_positive(self):
        result = compose_secondary_motion(primary(), request())
        for track in result["clip"]["tracks"]:
            if track["path"] == "rotation":
                for value in track["values"]:
                    self.assertAlmostEqual(sum(item * item for item in value), 1, places=10)
            if track["path"] == "scale":
                self.assertTrue(all(component > 0 for value in track["values"] for component in value))

    def test_validation_rejects_unknown_drivers_duplicates_and_unsafe_scale(self):
        cases = []
        bad = request(); bad["extra"] = True; cases.append(bad)
        bad = request(); bad["attachments"][0]["driver_target"] = "Missing"; cases.append(bad)
        bad = request(); bad["attachments"].append(copy.deepcopy(bad["attachments"][0])); cases.append(bad)
        bad = request(); bad["attachments"][0]["rest"] = [.1, .1, .1]; cases.append(bad)
        bad = request(); bad["attachments"][1]["axis"] = [0, 0, 0]; cases.append(bad)
        for item in cases:
            with self.assertRaises(ValueError):
                compose_secondary_motion(primary(), item)

    def test_static_primary_driver_fails_instead_of_inventing_motion(self):
        source_primary = primary()
        track = source_primary["clip"]["tracks"][0]
        track["values"] = [track["values"][0] for _ in track["values"]]
        source_request = request()
        source_request["attachments"] = [source_request["attachments"][0]]
        with self.assertRaisesRegex(ValueError, "has no motion"):
            compose_secondary_motion(source_primary, source_request)

    def test_publisher_and_cli_are_transactional(self):
        with tempfile.TemporaryDirectory() as tmp:
            direct = Path(tmp) / "direct"
            published = publish_secondary_motion(direct, primary(), request())
            self.assertEqual(published["files"],
                             ["primary.json", "secondary-clip.json", "secondary-receipt.json", "source.json"])
            with self.assertRaises(FileExistsError):
                publish_secondary_motion(direct, primary(), request())
            primary_path, request_path = Path(tmp) / "primary.json", Path(tmp) / "request.json"
            primary_path.write_text(json.dumps(primary()))
            request_path.write_text(json.dumps(request()))
            output = Path(tmp) / "cli"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["secondary-motion-compose", str(primary_path),
                                       str(request_path), str(output)]), 0)
            clip = json.loads((output / "secondary-clip.json").read_text())
            self.assertEqual(clip["name"], "Bell_Smack_With_Followthrough")


if __name__ == "__main__":
    unittest.main()

import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_functional_motion import (FUNCTIONAL_MOTION_SCHEMA,
                                            compose_game_functional_motion,
                                            game_functional_motion_catalog,
                                            publish_game_functional_motion)
from axm_uc.visual_assets_cli import main


def request():
    return {
        "name": "Courier_Function",
        "fps": 30,
        "frame_count": 61,
        "locomotion": {"root_target": "Root", "start": [0, 0, 0], "end": [0, -2.4, 0],
                       "start_frame": 5, "end_frame": 40, "easing": "smoothstep"},
        "wheels": [{"target": "Wheel.L", "radius_m": .34, "axis": [1, 0, 0], "direction": -1},
                   {"target": "Wheel.R", "radius_m": .19, "axis": [1, 0, 0], "direction": -1}],
        "projectile": {"target": "Package", "start": [0, 0, 0], "landing": [1.4, -.3, 0],
                       "gravity": [0, -9.81, 0], "release_frame": 12, "impact_frame": 48},
    }


class GameFunctionalMotionTests(unittest.TestCase):
    def test_composes_portable_function_tracks(self):
        result = compose_game_functional_motion(request())
        self.assertEqual(result["schema"], FUNCTIONAL_MOTION_SCHEMA)
        self.assertEqual([row["target"] for row in result["clip"]["tracks"]],
                         ["Root", "Wheel.L", "Wheel.R", "Package"])
        self.assertTrue(all(row["interpolation"] == "LINEAR" for row in result["clip"]["tracks"]))

    def test_wheel_rotation_is_derived_from_distance_and_radius(self):
        result = compose_game_functional_motion(request())
        rows = result["receipt"]["wheels"]
        self.assertAlmostEqual(abs(rows[0]["rotation_radians"]), 2.4 / .34)
        self.assertAlmostEqual(abs(rows[1]["rotation_radians"]), 2.4 / .19)
        self.assertLess(result["receipt"]["maximum_no_slip_residual_m"], 1e-12)

    def test_projectile_hits_endpoint_under_constant_gravity(self):
        result = compose_game_functional_motion(request())
        track = next(row for row in result["clip"]["tracks"] if row["target"] == "Package")
        self.assertEqual(track["values"][12], [0, 0, 0])
        self.assertEqual(track["values"][48], [1.4, -.3, 0])
        self.assertEqual(result["receipt"]["projectile_impact_residual_m"], 0)
        self.assertGreater(result["receipt"]["projectile"]["apex_height_along_gravity_m"], 1)

    def test_deterministic_and_preserves_request(self):
        raw = request(); before = copy.deepcopy(raw)
        first = compose_game_functional_motion(raw)
        self.assertEqual(first, compose_game_functional_motion(raw))
        self.assertEqual(raw, before)

    def test_locomotion_and_projectile_can_be_used_independently(self):
        raw = request(); raw["projectile"] = None
        self.assertNotIn("projectile", compose_game_functional_motion(raw)["receipt"])
        raw = request(); raw["locomotion"] = None; raw["wheels"] = []
        result = compose_game_functional_motion(raw)
        self.assertEqual([row["target"] for row in result["clip"]["tracks"]], ["Package"])

    def test_rejects_unsafe_or_incoherent_requests(self):
        cases = []
        raw = request(); raw["wheels"][0]["radius_m"] = 0; cases.append(raw)
        raw = request(); raw["wheels"][0]["axis"] = [2, 0, 0]; cases.append(raw)
        raw = request(); raw["wheels"][1]["target"] = "Wheel.L"; cases.append(raw)
        raw = request(); raw["wheels"] = []; cases.append(raw)
        raw = request(); raw["projectile"]["gravity"] = [0, 0, 0]; cases.append(raw)
        raw = request(); raw["projectile"]["impact_frame"] = raw["projectile"]["release_frame"]; cases.append(raw)
        raw = request(); raw["locomotion"] = None; raw["wheels"] = []; raw["projectile"] = None; cases.append(raw)
        for case in cases:
            with self.assertRaises(ValueError):
                compose_game_functional_motion(case)

    def test_catalog_keeps_truth_boundary(self):
        catalog = game_functional_motion_catalog()
        self.assertTrue(catalog["canonical_source_preserved"])
        self.assertIn("does not infer wheels", catalog["truth"])

    def test_publisher_and_cli_are_transactional(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output = root / "direct"
            publish_game_functional_motion(output, request())
            with self.assertRaises(FileExistsError):
                publish_game_functional_motion(output, request())
            (root / "request.json").write_text(json.dumps(request()))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["functional-motion-compose", str(root / "request.json"), str(root / "cli")]), 0)
            self.assertEqual(json.loads((root / "cli" / "functional-motion.json").read_text())["schema"], FUNCTIONAL_MOTION_SCHEMA)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import math
import tempfile
import unittest
from pathlib import Path

import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.rigid_vehicle_motion import (REQUEST_SCHEMA, compile_rigid_vehicle_motion,
                                         publish_rigid_vehicle_motion)
from axm_uc.visual_assets_cli import main


def request():
    lights = {"head": True, "brake": False, "reverse": False, "damage": False}
    rows = []
    for index, (distance, steer) in enumerate(((12.0, 0.0), (12.5, 0.8), (13.0, -0.4))):
        rows.append({
            "time_s": index * .25, "distance_m": distance, "steer": steer,
            "suspension_m": [0, .04 * index, -.02 * index, 0],
            "body_heave_m": .01 * index, "body_pitch_rad": -.02 * index,
            "body_roll_rad": .015 * index, "impact_offset_m": [0, 0, 0],
            "impact_rotation_rad": [0, 0, 0], "damage_stage": index,
            "lights": dict(lights, brake=index == 2),
        })
    return {
        "schema": REQUEST_SCHEMA, "name": "Road test",
        "contract": {
            "wheel_radius_m": .5,
            "wheel_positions_m": {
                "front-left": [-1, 0, 1.5], "front-right": [1, 0, 1.5],
                "rear-left": [-1, 0, -1.5], "rear-right": [1, 0, -1.5],
            },
            "max_steer_rad": .6, "max_suspension_m": .2,
            "max_body_rotation_rad": .3, "max_impact_offset_m": .4,
        },
        "samples": rows,
    }


class RigidVehicleMotionTests(unittest.TestCase):
    def test_compiles_deterministically_without_mutation(self):
        source = request()
        original = copy.deepcopy(source)
        first = compile_rigid_vehicle_motion(source)
        second = compile_rigid_vehicle_motion(source)
        self.assertEqual(source, original)
        self.assertEqual(first, second)
        self.assertEqual(first["receipt"]["trace_count"], 9)
        self.assertEqual(first["receipt"]["sample_count"], 3)
        self.assertAlmostEqual(first["receipt"]["wheel_rotation_radians"], -2)
        self.assertEqual(first["traces"]["wheel-front-left"][0]["frame"],
                         [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.])
        front = first["traces"]["corner-front-left"][1]["frame"]
        rear = first["traces"]["corner-rear-left"][1]["frame"]
        self.assertNotEqual(front[0], 1)
        self.assertEqual(rear[0], 1)
        self.assertEqual(first["presentation_states"][2]["damage_stage"], 2)
        self.assertTrue(first["presentation_states"][2]["lights"]["brake"])

    def test_aliasing_and_malformed_inputs_fail(self):
        sparse = request()
        sparse["samples"][1]["distance_m"] = 20
        sparse["samples"][2]["distance_m"] = 21
        with self.assertRaisesRegex(ValueError, "denser"):
            compile_rigid_vehicle_motion(sparse)
        malformed = request()
        malformed["samples"][0]["lights"]["magic"] = True
        with self.assertRaisesRegex(ValueError, "lights"):
            compile_rigid_vehicle_motion(malformed)
        backwards = request()
        backwards["samples"][1]["distance_m"] = 11
        with self.assertRaisesRegex(ValueError, "backwards"):
            compile_rigid_vehicle_motion(backwards)
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "invalid-motion"
            with self.assertRaisesRegex(ValueError, "backwards"):
                publish_rigid_vehicle_motion(target, backwards)
            self.assertFalse(target.exists())

    def test_publish_and_cli_refuse_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "motion"
            result = publish_rigid_vehicle_motion(target, request())
            self.assertEqual(json.loads((target / "vehicle-motion.json").read_text()), result)
            with self.assertRaises(FileExistsError):
                publish_rigid_vehicle_motion(target, request())
            source = Path(td) / "request.json"
            source.write_text(json.dumps(request()), encoding="utf-8")
            cli_target = Path(td) / "cli-motion"
            self.assertEqual(main(["vehicle-motion-compose", str(source), str(cli_target)]), 0)
            self.assertTrue((cli_target / "vehicle-motion-source.json").is_file())


if __name__ == "__main__":
    unittest.main()

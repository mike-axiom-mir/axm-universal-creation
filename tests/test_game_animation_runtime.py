import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_animation_runtime import (ANIMATION_RUNTIME_SCHEMA,
                                            compile_game_animation_runtime,
                                            game_animation_runtime_catalog,
                                            publish_game_animation_replay,
                                            replay_game_animation_runtime)
from axm_uc.visual_assets_cli import main


def parcel_imp_runtime():
    return {
        "schema": ANIMATION_RUNTIME_SCHEMA, "id": "parcel-imp", "initial_state": "idle",
        "clips": [
            {"name": "Idle_Parcel_Panic", "duration_s": 1.6, "loop": True,
             "root_motion_m": [0, 0, 0], "events": [{"name": "blink", "time_s": .4}]},
            {"name": "Delivery_Dash", "duration_s": 1.0, "loop": False,
             "root_motion_m": [0, 0, -1.25], "events": [{"name": "dash-impact", "time_s": .6}]},
            {"name": "Package_Launch", "duration_s": 38 / 30, "loop": False,
             "root_motion_m": [0, 0, 0], "events": [{"name": "release", "time_s": .3},
                                                        {"name": "apex", "time_s": .67},
                                                        {"name": "impact", "time_s": 1.2}]},
        ],
        "states": [
            {"name": "idle", "clip": "Idle_Parcel_Panic", "speed": 1, "root_motion": "ignore", "completion_event": None},
            {"name": "dash", "clip": "Delivery_Dash", "speed": 1, "root_motion": "apply", "completion_event": "complete"},
            {"name": "launch", "clip": "Package_Launch", "speed": 1, "root_motion": "ignore", "completion_event": "complete"},
        ],
        "transitions": [
            {"from": "idle", "event": "move", "to": "dash", "blend_s": .08},
            {"from": "idle", "event": "launch", "to": "launch", "blend_s": .12},
            {"from": "dash", "event": "complete", "to": "idle", "blend_s": .1},
            {"from": "dash", "event": "stop", "to": "idle", "blend_s": .05},
            {"from": "launch", "event": "complete", "to": "idle", "blend_s": .15},
        ],
    }


class GameAnimationRuntimeTests(unittest.TestCase):
    def test_compiles_exact_asset_clip_contract(self):
        result = compile_game_animation_runtime(parcel_imp_runtime())
        self.assertEqual(result["source"]["initial_state"], "idle")
        self.assertEqual(len(result["source"]["clips"]), 3)

    def test_dash_applies_exact_root_motion_and_completes_to_idle(self):
        result = replay_game_animation_runtime(parcel_imp_runtime(), [{"event": "move"}, {"dt": .4}, {"dt": .6}])
        self.assertEqual(result["final_state"], "idle")
        self.assertEqual(result["world_translation_m"], [0, 0, -1.25])
        self.assertTrue(result["transcript"][-1]["emitted"][-1]["automatic"])

    def test_launch_dispatches_release_apex_impact_and_returns(self):
        result = replay_game_animation_runtime(parcel_imp_runtime(), [{"event": "launch"}, {"dt": 38 / 30}])
        events = [row["event"] for row in result["transcript"][-1]["emitted"]]
        self.assertEqual(events, ["release", "apex", "impact", "complete"])
        self.assertEqual(result["final_state"], "idle")

    def test_loop_wrap_is_independent_of_step_partition(self):
        one = replay_game_animation_runtime(parcel_imp_runtime(), [{"dt": 3.4}])
        split = replay_game_animation_runtime(parcel_imp_runtime(), [{"dt": 1.1}, {"dt": 2.3}])
        self.assertAlmostEqual(one["transcript"][-1]["clip_time_s"], split["transcript"][-1]["clip_time_s"])
        self.assertEqual(one["transcript"][-1]["cycles"], split["transcript"][-1]["cycles"])

    def test_extract_returns_motion_without_moving_world(self):
        raw = parcel_imp_runtime(); raw["states"][1]["root_motion"] = "extract"
        result = replay_game_animation_runtime(raw, [{"event": "move"}, {"dt": .5}])
        self.assertEqual(result["world_translation_m"], [0, 0, 0])
        self.assertEqual(result["transcript"][-1]["extracted_root_motion_m"], [0, 0, -.625])

    def test_unknown_event_holds_without_state_change(self):
        result = replay_game_animation_runtime(parcel_imp_runtime(), [{"event": "teleport"}])
        self.assertEqual(result["final_state"], "idle")
        self.assertEqual(result["transcript"][0]["emitted"][0]["type"], "HOLD_NO_DECLARED_TRANSITION")

    def test_validation_rejects_incoherent_runtime(self):
        cases = []
        raw = parcel_imp_runtime(); raw["states"][1]["clip"] = "missing"; cases.append(raw)
        raw = parcel_imp_runtime(); raw["transitions"].append(copy.deepcopy(raw["transitions"][0])); cases.append(raw)
        raw = parcel_imp_runtime(); raw["states"][0]["completion_event"] = "complete"; cases.append(raw)
        raw = parcel_imp_runtime(); raw["states"][2]["completion_event"] = "missing"; cases.append(raw)
        raw = parcel_imp_runtime(); raw["clips"][2]["events"].reverse(); cases.append(raw)
        for raw in cases:
            with self.assertRaises(ValueError): compile_game_animation_runtime(raw)

    def test_deterministic_and_preserves_source(self):
        raw = parcel_imp_runtime(); before = copy.deepcopy(raw); commands = [{"event": "move"}, {"dt": 1}]
        self.assertEqual(replay_game_animation_runtime(raw, commands), replay_game_animation_runtime(raw, commands))
        self.assertEqual(raw, before)

    def test_catalog_publisher_and_cli_keep_truth_boundary(self):
        self.assertIn("does not load a GLB", game_animation_runtime_catalog()["truth"])
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); direct = root / "direct"
            publish_game_animation_replay(direct, parcel_imp_runtime(), [{"dt": .1}])
            with self.assertRaises(FileExistsError):
                publish_game_animation_replay(direct, parcel_imp_runtime(), [])
            request = root / "request.json"
            request.write_text(json.dumps({"runtime": parcel_imp_runtime(), "commands": [{"event": "move"}, {"dt": 1}]}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["animation-runtime-replay", str(request), str(root / "cli")]), 0)


if __name__ == "__main__": unittest.main()

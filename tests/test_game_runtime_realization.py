import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_runtime_realization import (
    PLAN_SCHEMA, SOURCE_SCHEMA, compose_game_runtime_realization,
    game_runtime_realization_catalog, publish_game_runtime_realization,
)
from axm_uc.visual_assets_cli import main


def anchor(name, kind="socket", x=0):
    return {"name": name, "kind": kind, "position": [x, 0, 0],
            "forward": [0, 0, 1], "up": [0, 1, 0]}


def source():
    anchors = [anchor("tool"), anchor("wheel", "contact", -.3)]
    observations = {
        "LOD0": [("near", 0, 1), ("play", 0, 1), ("far", 0, 1)],
        "LOD1": [("near", .012, .998), ("play", .005, .999), ("far", .002, .9995)],
        "LOD2": [("near", .04, .990), ("play", .018, .996), ("far", .005, .999)],
    }
    def observed(lod):
        return [{"view": view, "rgba_rmse": rmse, "silhouette_iou": iou}
                for view, rmse, iou in observations[lod]]
    return {
        "schema": SOURCE_SCHEMA, "asset_id": "clockwork-smacker", "canonical_lod": "LOD0",
        "source_sha256": "a" * 64,
        "features": [
            {"name": "hero-shape", "hierarchy": "primary", "world_size_m": .8, "min_pixels": 5},
            {"name": "clock-face", "hierarchy": "secondary", "world_size_m": .15, "min_pixels": 10},
            {"name": "lucky-duck", "hierarchy": "detail", "world_size_m": .06, "min_pixels": 8},
        ],
        "lods": [
            {"name": "LOD0", "triangles": 60000, "max_deviation_m": 0,
             "features": ["hero-shape", "clock-face", "lucky-duck"], "anchors": anchors,
             "render_observations": observed("LOD0")},
            {"name": "LOD1", "triangles": 28000, "max_deviation_m": .002,
             "features": ["hero-shape", "clock-face"], "anchors": copy.deepcopy(anchors),
             "render_observations": observed("LOD1")},
            {"name": "LOD2", "triangles": 9000, "max_deviation_m": .005,
             "features": ["hero-shape"], "anchors": copy.deepcopy(anchors),
             "render_observations": observed("LOD2")},
        ],
    }


def request():
    return {"anchor_position_tolerance_m": .001, "anchor_angle_tolerance_deg": .1,
            "views": [
                {"name": "near", "distance_m": 2.5, "vertical_fov_deg": 60,
                 "viewport_height_px": 1080, "error_budget_px": 2,
                 "max_rgba_rmse": .01, "min_silhouette_iou": .995},
                {"name": "play", "distance_m": 10, "vertical_fov_deg": 60,
                 "viewport_height_px": 1080, "error_budget_px": 2,
                 "max_rgba_rmse": .01, "min_silhouette_iou": .995},
                {"name": "far", "distance_m": 40, "vertical_fov_deg": 60,
                 "viewport_height_px": 1080, "error_budget_px": 2,
                 "max_rgba_rmse": .01, "min_silhouette_iou": .995},
            ]}


class RuntimeRealizationTests(unittest.TestCase):
    def test_catalog_keeps_truth_boundaries(self):
        catalog = game_runtime_realization_catalog()
        self.assertTrue(catalog["canonical_source_preserved"])
        self.assertIn("does not measure meshes", catalog["truth"])

    def test_selects_cheapest_eligible_lod_at_each_distance(self):
        result = compose_game_runtime_realization(source(), request())
        self.assertEqual(result["schema"], PLAN_SCHEMA)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual([row["selected_lod"] for row in result["decisions"]],
                         ["LOD0", "LOD1", "LOD2"])

    def test_features_are_required_only_while_projected_readable(self):
        result = compose_game_runtime_realization(source(), request())
        self.assertEqual(result["decisions"][0]["required_features"],
                         ["clock-face", "hero-shape", "lucky-duck"])
        self.assertEqual(result["decisions"][1]["required_features"],
                         ["clock-face", "hero-shape"])
        self.assertEqual(result["decisions"][2]["required_features"], ["hero-shape"])

    def test_anchor_drift_blocks_only_the_drifting_lod(self):
        raw = source()
        raw["lods"][2]["anchors"][0]["position"][0] = .01
        result = compose_game_runtime_realization(raw, request())
        far = result["decisions"][2]
        self.assertEqual(far["selected_lod"], "LOD1")
        self.assertFalse(next(row for row in far["candidates"] if row["lod"] == "LOD2")["anchors_pass"])

    def test_render_evidence_blocks_geometry_only_false_confidence(self):
        result = compose_game_runtime_realization(source(), request())
        near_lod2 = next(row for row in result["decisions"][0]["candidates"] if row["lod"] == "LOD2")
        self.assertLessEqual(near_lod2["projected_error_px"], request()["views"][0]["error_budget_px"])
        self.assertFalse(near_lod2["render_pass"])
        self.assertEqual(result["decisions"][0]["selected_lod"], "LOD0")

    def test_canonical_lod_remains_honest_fallback(self):
        raw = source()
        raw["lods"][0]["max_deviation_m"] = 0
        req = request()
        req["anchor_position_tolerance_m"] = 0
        for lod in raw["lods"]:
            lod["anchors"][0]["position"][0] = .01
        result = compose_game_runtime_realization(raw, req)
        self.assertEqual(result["status"], "PASS")  # all LODs share the same canonical frame
        raw["lods"][1]["anchors"][0]["position"][0] = .02
        raw["lods"][2]["anchors"][0]["position"][0] = .02
        req["views"] = [dict(req["views"][0], error_budget_px=.01)]
        result = compose_game_runtime_realization(raw, req)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["decisions"][0]["selected_lod"], "LOD0")

    def test_deterministic_and_preserves_caller_sources(self):
        raw, req = source(), request()
        before = (copy.deepcopy(raw), copy.deepcopy(req))
        first = compose_game_runtime_realization(raw, req)
        self.assertEqual(first, compose_game_runtime_realization(raw, req))
        self.assertEqual((raw, req), before)
        self.assertEqual(first["source"], raw)

    def test_validation_rejects_bad_ladder_feature_and_anchor_frames(self):
        cases = []
        raw = source(); raw["lods"][1]["triangles"] = raw["lods"][0]["triangles"]; cases.append(raw)
        raw = source(); raw["lods"][1]["features"].append("invented"); cases.append(raw)
        raw = source(); raw["lods"][1]["anchors"].pop(); cases.append(raw)
        raw = source(); raw["lods"][1]["anchors"][0]["forward"] = [0, 2, 0]; cases.append(raw)
        raw = source(); raw["lods"][1]["render_observations"].clear(); cases.append(raw)
        for case in cases:
            with self.assertRaises(ValueError):
                compose_game_runtime_realization(case, request())

    def test_publisher_and_cli_are_transactional(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            output = root / "direct"
            publish_game_runtime_realization(output, source(), request())
            self.assertEqual(json.loads((output / "source.json").read_text()), source())
            with self.assertRaises(FileExistsError):
                publish_game_runtime_realization(output, source(), request())
            (root / "source.json").write_text(json.dumps(source()))
            (root / "request.json").write_text(json.dumps(request()))
            cli = root / "cli"
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["game-realization-plan", str(root / "source.json"),
                                       str(root / "request.json"), str(cli)]), 0)
            self.assertTrue((cli / "realization-plan.json").is_file())


if __name__ == "__main__":
    unittest.main()

import copy
from contextlib import redirect_stdout
import io
import json
from pathlib import Path
import tempfile
import unittest

from axm_uc.game_showcase_contract import (RECEIPT_SCHEMA, SOURCE_SCHEMA,
                                            compose_game_showcase, game_showcase_catalog,
                                            publish_game_showcase)
from axm_uc.visual_assets_cli import main


def source():
    return {
        "schema": SOURCE_SCHEMA, "asset_id": "parcel-imp", "canonical_source_sha256": "a" * 64,
        "styles": [{"name": "realistic", "role": "canonical-realistic"},
                   {"name": "comic-salvage", "role": "selected-game"}],
        "materials": [
            {"name": "paint", "family": "painted-metal", "finish": "comic-salvage", "realized": True},
            {"name": "rubber", "family": "rubber", "finish": "realistic", "realized": True},
            {"name": "cloth", "family": "woven-fabric", "finish": "painterly-adventure", "realized": True}],
        "rig": {"bones": ["Root", "Body", "Wheel.Contact", "Package.Socket", "Antenna", "Receipt"],
                "clips": [{"name": "Idle_Fidget", "frames": 49, "fps": 24, "loop": True, "loop_seam_m": 0},
                          {"name": "Package_Launch", "frames": 37, "fps": 24, "loop": False, "loop_seam_m": 0}]},
        "secondary_motion": [
            {"target": "Antenna", "motion_class": "antenna", "max_track_error": 0.000001, "loop_seam_m": 0},
            {"target": "Receipt", "motion_class": "cloth-tail", "max_track_error": 0.000002, "loop_seam_m": 0}],
        "anchors": [
            {"name": "Wheel.Contact", "kind": "contact", "position_drift_m": 0.00001, "angle_drift_deg": 0, "surface_distance_m": 0.00001},
            {"name": "Package.Socket", "kind": "socket", "position_drift_m": 0.00001, "angle_drift_deg": 0, "surface_distance_m": 0}],
        "lods": [
            {"name": "LOD0", "triangles": 42000, "max_deviation_m": 0, "identity_features": ["face", "wheel", "parcel"]},
            {"name": "LOD1", "triangles": 17000, "max_deviation_m": .003, "identity_features": ["face", "wheel", "parcel"]}],
        "views": [
            {"name": "play", "selected_lod": "LOD1", "rgba_rmse": .009, "silhouette_iou": .997, "max_rgba_rmse": .02, "min_silhouette_iou": .99},
            {"name": "far", "selected_lod": "LOD1", "rgba_rmse": .006, "silhouette_iou": .998, "max_rgba_rmse": .02, "min_silhouette_iou": .99}],
        "files": [{"name": "parcel-imp-lod0.glb", "sha256": "b" * 64, "bytes": 100},
                  {"name": "parcel-imp.blend", "sha256": "c" * 64, "bytes": 200}],
        "thresholds": {"loop_seam_m": .0001, "secondary_track_error": .0001,
                       "anchor_position_m": .001, "anchor_angle_deg": .1, "contact_surface_m": .001},
        "limits": ["No target-engine playback was performed.", "Visual quality requires human review."],
    }


class GameShowcaseContractTests(unittest.TestCase):
    def test_pass_requires_all_layers(self):
        result = compose_game_showcase(source())
        self.assertEqual(result["schema"], RECEIPT_SCHEMA)
        self.assertEqual(result["status"], "PASS")
        self.assertTrue(all(result["gates"].values()))

    def test_preserves_source_and_is_deterministic(self):
        raw = source(); before = copy.deepcopy(raw)
        first = compose_game_showcase(raw)
        self.assertEqual(first, compose_game_showcase(raw))
        self.assertEqual(raw, before)

    def test_each_measured_failure_holds(self):
        cases = []
        raw = source(); raw["materials"][0]["realized"] = False; cases.append(raw)
        raw = source(); raw["rig"]["clips"][0]["loop_seam_m"] = .1; cases.append(raw)
        raw = source(); raw["secondary_motion"][0]["max_track_error"] = .1; cases.append(raw)
        raw = source(); raw["anchors"][0]["surface_distance_m"] = .1; cases.append(raw)
        raw = source(); raw["lods"][0]["identity_features"] = ["face"]; cases.append(raw)
        raw = source(); raw["views"][0]["silhouette_iou"] = .2; cases.append(raw)
        raw = source(); raw["files"][0]["name"] = "parcel.obj"; cases.append(raw)
        for case in cases:
            self.assertEqual(compose_game_showcase(case)["status"], "HOLD")

    def test_rejects_structural_shortcuts(self):
        cases = []
        raw = source(); raw["styles"] = raw["styles"][:1]; cases.append(raw)
        raw = source(); raw["materials"] = raw["materials"][:2]; cases.append(raw)
        raw = source(); raw["secondary_motion"][0]["target"] = "Missing"; cases.append(raw)
        raw = source(); raw["anchors"] = raw["anchors"][:1]; cases.append(raw)
        raw = source(); raw["lods"][1]["triangles"] = 50000; cases.append(raw)
        raw = source(); raw["views"][0]["selected_lod"] = "LOD9"; cases.append(raw)
        raw = source(); raw["files"][0]["name"] = "../escape.glb"; cases.append(raw)
        for case in cases:
            with self.assertRaises(ValueError):
                compose_game_showcase(case)

    def test_catalog_and_truth_boundary(self):
        catalog = game_showcase_catalog()
        self.assertTrue(catalog["canonical_source_preserved"])
        self.assertIn("does not judge art", catalog["truth"])

    def test_publisher_and_cli_are_transactional(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary); output = root / "direct"
            publish_game_showcase(output, source())
            self.assertTrue((output / "showcase-receipt.json").is_file())
            with self.assertRaises(FileExistsError):
                publish_game_showcase(output, source())
            (root / "source.json").write_text(json.dumps(source()))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["game-showcase-verify", str(root / "source.json"), str(root / "cli")]), 0)
            self.assertEqual(json.loads((root / "cli" / "showcase-receipt.json").read_text())["status"], "PASS")


if __name__ == "__main__":
    unittest.main()

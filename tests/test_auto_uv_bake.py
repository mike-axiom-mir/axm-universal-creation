import copy
import json
import shutil
import tempfile
import unittest
from pathlib import Path

from axm_uc.product_workflow import operate_product_workflow
from test_native_textures import panel

ROOT = Path(__file__).resolve().parents[1]


def uvless_panel():
    spec = panel()
    for group in spec["primitives"]:
        group.pop("texcoords", None)
    spec["name"] = "automatic unwrap panel"
    return spec


def hard_fold():
    diagonal = 0.7071067811865476
    return {
        "schema": "axm.surface-3d/v0.1",
        "name": "hard fold",
        "primitives": [{
            "id": "paint",
            "positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1]],
            "normals": [[diagonal, 0, diagonal], [0, 0, 1], [diagonal, 0, diagonal], [1, 0, 0]],
            "indices": [0, 1, 2, 0, 2, 3],
            "material": {"color": "#ffffff", "metallic": 1, "roughness": 1},
        }],
    }


class AutoUvBakeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        shutil.copytree(ROOT / "capabilities/live", self.root / "capabilities/live")

    def request(self, path="creations/auto", run_id="auto-1"):
        return {
            "operation": "build",
            "product_type": "static-3d",
            "path": path,
            "run_id": run_id,
            "brief": {
                "purpose": "Prove a UV-less surface can reach a bounded textured draft",
                "target": "offline native GLB",
                "quality_intent": "Technical unwrap and bake evidence before visual review",
            },
            "recipe": {"paint": {"family": "painted-metal", "size": 16, "seed": 9}},
            "material_policy": {"minimum_size": 16},
            "minimum_texels_per_m": 10,
            "specification": uvless_panel(),
            "unwrap_bake": {"atlas_size": 64, "padding_px": 4},
            "preview": {"width": 64, "height": 64},
        }

    def call(self, **request):
        return operate_product_workflow(self.root, request)

    def test_uvless_static_asset_groups_planar_faces_into_one_real_chart(self):
        result = self.call(**self.request())
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        folder = self.root / "creations/auto/auto-bake"
        self.assertTrue((folder / "asset.glb").is_file())
        self.assertTrue((folder / "atlases/paint-base_color.png").is_file())
        receipt = json.loads((folder / "receipt.json").read_text())
        self.assertEqual(receipt["schema"], "axm.auto-unwrap-bake/v1")
        self.assertEqual(receipt["method"], "connected-planar-chart-grid-v2")
        group = receipt["groups"][0]
        self.assertTrue(group["inter_chart_overlap_free_by_construction"])
        self.assertEqual(group["intra_chart_overlap"], "NOT_TESTED")
        self.assertEqual(group["triangle_count"], 2)
        self.assertEqual(group["chart_count"], 1)
        self.assertEqual(group["baked_vertices"], 4)
        self.assertEqual(group["saved_vertex_duplicates_vs_triangle_fallback"], 2)
        self.assertEqual(group["padding_px"], 4)
        self.assertEqual(group["charts"][0]["triangles"], [0, 1])
        self.assertEqual(group["charts"][0]["intra_chart_overlap"], "NOT_TESTED")
        self.assertEqual(receipt["visual_quality"], "NOT_TESTED")
        self.assertEqual(result["manifest"]["visual_quality"], "NOT_TESTED")
        self.assertEqual(result["manifest"]["professional_acceptance"], "NOT_TESTED")
        verified = self.call(operation="verify", path=result["delivery"])
        self.assertEqual(verified["status"], "PASS", verified)

    def test_hard_fold_remains_two_charts_at_default_seam_angle(self):
        request = self.request("creations/fold", "fold-1")
        request["specification"] = hard_fold()
        result = self.call(**request)
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        receipt = json.loads((self.root / "creations/fold/auto-bake/receipt.json").read_text())
        group = receipt["groups"][0]
        self.assertEqual(group["triangle_count"], 2)
        self.assertEqual(group["chart_count"], 2)
        self.assertEqual([row["triangles"] for row in group["charts"]], [[0], [1]])
        self.assertEqual(group["seam_angle_degrees"], 35.0)

    def test_seam_angle_is_bounded_and_receipted(self):
        request = self.request("creations/angle", "angle-1")
        request["unwrap_bake"]["seam_angle_degrees"] = 12
        result = self.call(**request)
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        receipt = json.loads((self.root / "creations/angle/auto-bake/receipt.json").read_text())
        self.assertEqual(receipt["options"]["seam_angle_degrees"], 12.0)
        bad = self.request("creations/bad-angle", "bad-angle-1")
        bad["unwrap_bake"]["seam_angle_degrees"] = 90
        result = self.call(**bad)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK", result)
        self.assertFalse((self.root / "creations/bad-angle/auto-bake").exists())

    def test_existing_supplied_uv_route_is_preserved(self):
        request = self.request("creations/supplied", "supplied-1")
        request["specification"] = panel()
        result = self.call(**request)
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        self.assertTrue((self.root / "creations/supplied/asset.glb").is_file())
        self.assertFalse((self.root / "creations/supplied/auto-bake").exists())

    def test_failed_auto_bake_preserves_the_failed_draft_without_downstream_render(self):
        request = self.request("creations/failed", "failed-1")
        request["unwrap_bake"] = {"atlas_size": 32, "padding_px": 15}
        result = self.call(**request)
        self.assertEqual(result["status"], "HOLD_FAILED_CHECK", result)
        base = self.root / "creations/failed"
        self.assertTrue((base / "source.json").is_file())
        self.assertTrue((base / "materials/paint/game-material.json").is_file())
        self.assertFalse((base / "auto-bake").exists())
        self.assertFalse((base / "previews").exists())

    def test_atlas_tamper_breaks_fresh_verification(self):
        result = self.call(**self.request())
        atlas = self.root / "creations/auto/auto-bake/atlases/paint-base_color.png"
        original = atlas.read_bytes()
        atlas.write_bytes(original[:-1] + bytes([original[-1] ^ 1]))
        verified = self.call(operation="verify", path=result["delivery"])
        self.assertEqual(verified["status"], "NOT_CURRENT_PASS")

    def test_mixed_uv_and_uvless_groups_are_rejected_before_writes(self):
        request = self.request("creations/mixed", "mixed-1")
        spec = panel()
        second = copy.deepcopy(spec["primitives"][0])
        second["id"] = "bare"
        second.pop("texcoords")
        spec["primitives"].append(second)
        request["specification"] = spec
        request["recipe"]["bare"] = {"family": "rubber", "size": 16, "seed": 2}
        with self.assertRaisesRegex(ValueError, "cannot mix supplied-UV and UV-less"):
            self.call(**request)
        self.assertFalse((self.root / "creations/mixed").exists())


if __name__ == "__main__":
    unittest.main()

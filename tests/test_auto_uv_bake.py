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

    def test_uvless_static_asset_gets_real_atlas_receipt_and_stays_review_required(self):
        result = self.call(**self.request())
        self.assertEqual(result["status"], "DRAFT_BUILT_REVIEW_REQUIRED", result)
        folder = self.root / "creations/auto/auto-bake"
        self.assertTrue((folder / "asset.glb").is_file())
        self.assertTrue((folder / "atlases/paint-base_color.png").is_file())
        receipt = json.loads((folder / "receipt.json").read_text())
        self.assertEqual(receipt["schema"], "axm.auto-unwrap-bake/v1")
        self.assertEqual(receipt["method"], "triangle-chart-grid-v1")
        self.assertTrue(receipt["groups"][0]["overlap_free_by_construction"])
        self.assertEqual(receipt["groups"][0]["padding_px"], 4)
        self.assertEqual(receipt["visual_quality"], "NOT_TESTED")
        self.assertEqual(result["manifest"]["visual_quality"], "NOT_TESTED")
        self.assertEqual(result["manifest"]["professional_acceptance"], "NOT_TESTED")
        verified = self.call(operation="verify", path=result["delivery"])
        self.assertEqual(verified["status"], "PASS", verified)

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

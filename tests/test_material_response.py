import copy
import unittest

from axm_uc.material_response import (
    MaterialResponseHold,
    active_organs,
    material_response_catalog,
    resolve_material_graph_response,
    resolve_material_response,
)


class MaterialResponseTests(unittest.TestCase):
    def test_catalog_preserves_bounded_breadth_and_evidence(self):
        value = material_response_catalog()
        self.assertEqual(value["counts"], {"families": 13, "organs": 8})
        self.assertEqual(value["evidence"], "declared_contract_match_not_tested")
        self.assertEqual(value["renderer_binding"], "NOT_CLAIMED")

    def test_skin_living_resolves_without_claiming_uc_renderer_binding(self):
        value = resolve_material_response("skin-living")
        self.assertEqual(
            set(value["active_organs"]),
            {"surface.subsurface", "surface.sheen", "surface.coat", "surface.breakup"},
        )
        self.assertEqual(value["renderer_binding"], "HOLD_RENDERER_BINDING_NOT_TESTED")

    def test_variant_is_explicit_and_preserves_family(self):
        value = resolve_material_response("skin-living", variant="sweating")
        self.assertEqual(value["family"], "skin-living")
        self.assertEqual(value["variant"], "sweating")
        self.assertEqual(value["response"]["clearcoat"]["weight"], 0.7)

    def test_unknown_family_and_unknown_override_fail_closed(self):
        with self.assertRaises(MaterialResponseHold):
            resolve_material_response("not-a-family")
        with self.assertRaises(MaterialResponseHold):
            resolve_material_response("skin-living", overrides={"magic_unknown_lobe": {"weight": 1}})

    def test_zero_weight_organs_are_true_noop(self):
        response = {
            "base_color": [0.5, 0.5, 0.5],
            "roughness": 0.5,
            "subsurface": {"weight": 0, "radius_mm": [2, 1, 0.5]},
            "sheen": {"weight": 0},
            "anisotropy": {"strength": 0},
            "clearcoat": {"weight": 0},
            "breakup": {"roughness_variation": 0, "color_variation": 0, "scale_mm": 2},
            "transmission": 0,
            "iridescence": {"weight": 0},
            "layers": [],
        }
        self.assertEqual(active_organs(response), [])

    def test_graph_without_response_remains_unchanged_path(self):
        self.assertEqual(
            resolve_material_graph_response({"schema": "axm.material-graph/v1"}),
            {"status": "PASS_NO_RESPONSE", "response": None},
        )


if __name__ == "__main__":
    unittest.main()

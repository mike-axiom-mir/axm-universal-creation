import copy
import unittest

from axm_uc.indexed_surface_eligibility import INPUT_SCHEMA, observe_indexed_surface_eligibility


def base_spec():
    return {
        "schema": INPUT_SCHEMA,
        "source_identity": "fixture-source",
        "surface_identity": "fixture-surface",
        "source": {"vertex_count": 4, "indices": [0, 1, 2, 0, 2, 3]},
        "render": {
            "vertex_count": 4,
            "indices": [0, 1, 2, 0, 2, 3],
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0]],
                "NORMAL": [[0, 0, 1]] * 4,
            },
        },
    }


class IndexedSurfaceEligibilityTests(unittest.TestCase):
    def test_preserves_valid_source_indexing(self):
        report = observe_indexed_surface_eligibility(base_spec())
        self.assertEqual(report["eligibility_state"], "PRESERVE_SOURCE_INDEXING")
        self.assertEqual(report["render_domain_state"], "SAME_AS_SOURCE")
        self.assertEqual(report["candidate"]["vertex_count"], 4)
        self.assertTrue(report["split_observation"]["position_only_weld_safe"])

    def test_expanded_triangle_corners_become_tuple_dedup_candidate_only_with_explicit_split_declaration(self):
        spec = base_spec()
        spec["render"] = {
            "vertex_count": 6,
            "source_vertex_indices": [0, 1, 2, 0, 2, 3],
            "protected_split_ids": [None] * 6,
            "indices": list(range(6)),
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 0, 0], [1, 1, 0], [0, 1, 0]],
                "NORMAL": [[0, 0, 1]] * 6,
            },
        }
        report = observe_indexed_surface_eligibility(spec)
        self.assertEqual(report["eligibility_state"], "POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE")
        self.assertEqual(report["candidate"]["vertex_count"], 4)
        self.assertEqual(report["candidate"]["indices"], [0, 1, 2, 0, 2, 3])

        held = copy.deepcopy(spec)
        del held["render"]["protected_split_ids"]
        report = observe_indexed_surface_eligibility(held)
        self.assertEqual(report["eligibility_state"], "HOLD_ATTRIBUTE_SEAM_AMBIGUITY")
        self.assertIsNone(report["candidate"])

    def test_uv_seam_survives_full_tuple_reasoning(self):
        spec = base_spec()
        spec["render"] = {
            "vertex_count": 5,
            "source_vertex_indices": [0, 1, 2, 3, 0],
            "protected_split_ids": [None] * 5,
            "indices": [0, 1, 2, 4, 2, 3],
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]],
                "NORMAL": [[0, 0, 1]] * 5,
                "TEXCOORD_0": [[0, 0], [1, 0], [1, 1], [0, 1], [1, 0]],
            },
        }
        report = observe_indexed_surface_eligibility(spec)
        self.assertEqual(report["render_domain_state"], "RENDER_DOMAIN_SPLIT_REQUIRED")
        self.assertEqual(report["candidate"]["vertex_count"], 5)
        self.assertFalse(report["split_observation"]["position_only_weld_safe"])
        self.assertEqual(report["split_observation"]["split_groups_by_channel"]["TEXCOORD_0"], 1)

    def test_explicit_protected_topology_split_survives_even_when_attributes_match(self):
        spec = base_spec()
        spec["render"] = {
            "vertex_count": 5,
            "source_vertex_indices": [0, 1, 2, 3, 0],
            "protected_split_ids": ["front", None, None, None, "back"],
            "indices": [0, 1, 2, 4, 2, 3],
            "channels": {
                "POSITION": [[0, 0, 0], [1, 0, 0], [1, 1, 0], [0, 1, 0], [0, 0, 0]],
                "NORMAL": [[0, 0, 1]] * 5,
            },
        }
        report = observe_indexed_surface_eligibility(spec)
        self.assertEqual(report["render_domain_state"], "RENDER_DOMAIN_SPLIT_REQUIRED")
        self.assertEqual(report["candidate"]["vertex_count"], 5)
        self.assertEqual(report["split_observation"]["protected_split_id_count"], 2)
        self.assertFalse(report["split_observation"]["position_only_weld_safe"])

    def test_unknown_channel_fails_closed_without_candidate(self):
        spec = base_spec()
        spec["render"]["channels"]["MORPH_POSITION_0"] = [[0, 0, 0]] * 4
        report = observe_indexed_surface_eligibility(spec)
        self.assertEqual(report["eligibility_state"], "NOT_EVALUATED_UNSUPPORTED_CHANNEL")
        self.assertEqual(report["unsupported_channels"], ["MORPH_POSITION_0"])
        self.assertIsNone(report["candidate"])

    def test_digests_are_deterministic_and_input_sensitive(self):
        one = observe_indexed_surface_eligibility(base_spec())
        two = observe_indexed_surface_eligibility(base_spec())
        self.assertEqual(one["input_digest"], two["input_digest"])
        changed = base_spec()
        changed["render"]["channels"]["NORMAL"][0] = [0, 1, 0]
        three = observe_indexed_surface_eligibility(changed)
        self.assertNotEqual(one["input_digest"], three["input_digest"])
        self.assertNotEqual(one["channel_digests"]["NORMAL"], three["channel_digests"]["NORMAL"])


if __name__ == "__main__":
    unittest.main()

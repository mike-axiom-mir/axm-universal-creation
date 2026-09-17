import unittest

from axm_uc.indexed_surface_eligibility import (
    CROSS_SOURCE_TUPLE_POLICY,
    INPUT_SCHEMA,
    observe_indexed_surface_eligibility,
)


class IndexedSurfaceCrossSourceMetricTests(unittest.TestCase):
    def test_participating_source_vertex_count_is_unique_across_candidate_groups(self):
        spec = {
            "schema": INPUT_SCHEMA,
            "source_identity": "repeated-cross-source-participant",
            "surface_identity": "metric-regression",
            "candidate_identity_policy": CROSS_SOURCE_TUPLE_POLICY,
            "source": {
                "vertex_count": 3,
                "indices": [0, 1, 2, 0, 2, 1],
            },
            "render": {
                "vertex_count": 6,
                "source_vertex_indices": [0, 1, 2, 0, 2, 1],
                "protected_split_ids": [None] * 6,
                "indices": list(range(6)),
                "channels": {
                    "POSITION": [
                        [0, 0, 0],
                        [0, 0, 0],
                        [1, 0, 0],
                        [1, 0, 0],
                        [2, 0, 0],
                        [2, 0, 0],
                    ],
                    "NORMAL": [[0, 0, 1]] * 6,
                },
            },
        }

        report = observe_indexed_surface_eligibility(spec)

        self.assertEqual(report["eligibility_state"], "POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE")
        self.assertEqual(report["candidate"]["vertex_count"], 3)
        self.assertEqual(
            report["cross_source_observation"]["candidate_groups_spanning_multiple_source_vertices"],
            3,
        )
        self.assertEqual(
            report["cross_source_observation"]["source_vertices_participating_in_cross_source_groups"],
            3,
        )


if __name__ == "__main__":
    unittest.main()

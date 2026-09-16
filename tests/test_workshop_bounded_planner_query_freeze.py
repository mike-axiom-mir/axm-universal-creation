from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from axm_stickers import Registry
from axm_uc.design_workshop import validate_sketch
from axm_uc.workshop_bounded_planner import preview_workshop_plan, retain_workshop_plan
from tests.test_workshop_bounded_planner import pin, planner, register_box, sketch_single


class WorkshopBoundedPlannerQueryFreezeTests(unittest.TestCase):
    def test_retained_assembly_matching_same_query_cannot_change_pinned_candidate_universe(self):
        sketch = validate_sketch(sketch_single())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            register_box(registry, "wrong", (1.2, 1.2, 1.2), tags=["candidate"])
            exact = register_box(registry, "exact", (1, 1, 1), tags=["candidate"])
            # No adapter filter: the retained assembly below really does match this
            # same socket+tag query after publication.
            slot = {"part": "body", "query": {"adapter": None, "socket": "mount", "tag": "candidate", "limit": 8}}
            request = planner(sketch, [slot])
            preview = preview_workshop_plan(registry, sketch, request)
            self.assertEqual(preview["selection"]["selection"]["body"], pin(exact))
            self.assertEqual(len(preview["resolved_slots"][0]["candidates"]), 2)

            pinned = copy.deepcopy(request)
            pinned["planner_digest"] = preview["planner_digest"]
            retained = retain_workshop_plan(registry, sketch, pinned, {
                "id": "retained-query-match",
                "name": "Retained query match",
                "version": 1,
                "socket": "mount",
                "tags": ["candidate"],
                "origin": {"author": "AXM test", "license": "CC0-1.0", "source": "query-freeze regression"},
            })
            self.assertEqual(retained["status"], "PASS", retained)
            self.assertTrue(retained["new_registry_entry"])
            self.assertEqual(retained["planner_digest"], preview["planner_digest"])
            self.assertEqual(registry.get("retained-query-match", 1)["recipe"]["children"][0]["instance"]["sticker"], pin(exact))

            # A fresh query now sees the retained assembly too, proving the test
            # actually exercises the candidate-universe mutation that retention
            # must not retroactively feed back into the pinned decision.
            fresh = copy.deepcopy(request)
            new_preview = preview_workshop_plan(registry, sketch, fresh)
            self.assertEqual(len(new_preview["resolved_slots"][0]["candidates"]), 3)
            self.assertNotEqual(new_preview["planner_digest"], preview["planner_digest"])


if __name__ == "__main__":
    unittest.main()

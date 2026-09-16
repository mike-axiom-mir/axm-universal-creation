from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.procedural_3d import build_glb, verify_glb
from axm_uc.rigid_scene_graph import (
    RigidSceneGraphError,
    rebind_rigid_scene_graph,
    verify_rigid_scene_graph,
)


def surface() -> dict:
    def group(name: str, x: float) -> dict:
        return {
            "id": name,
            "positions": [[x, 0, 0], [x + 1, 0, 0], [x, 1, 0]],
            "normals": [[0, 0, 1], [0, 0, 1], [0, 0, 1]],
            "indices": [0, 1, 2],
            "material": {"color": "#808080FF", "metallic": 0.2, "roughness": 0.7},
        }
    return {
        "schema": "axm.surface-3d/v0.1",
        "name": "rigid-scene-graph-neutral-fixture",
        "primitives": [group("body", 0), group("lid", 2), group("keeper", 4), group("lever", 6)],
    }


def manifest() -> dict:
    return {
        "schema": "axm.rigid-scene-graph/v0.1",
        "nodes": [
            {"name": "keeper", "parent": "lid", "translation": [0, 0, 0]},
            {"name": "lid", "parent": None, "translation": [0, 0.5, 0]},
            {"name": "lever", "parent": None, "translation": [0, 0, 0]},
        ],
    }


class RigidSceneGraphTests(unittest.TestCase):
    def test_rebind_is_deterministic_and_preserves_geometry_payload(self):
        baseline = build_glb(surface())
        first = rebind_rigid_scene_graph(
            baseline["body"], manifest(), expected_spec_digest=baseline["specification_sha256"]
        )
        second = rebind_rigid_scene_graph(
            baseline["body"], manifest(), expected_spec_digest=baseline["specification_sha256"]
        )
        self.assertEqual(first["body"], second["body"])
        self.assertEqual(first["manifest_sha256"], second["manifest_sha256"])
        receipt = first["receipt"]
        self.assertEqual(receipt["result"], "PASS_RIGID_SCENE_GRAPH_REBIND")
        self.assertTrue(receipt["binary_geometry_payload_identical"])
        self.assertEqual(receipt["triangles_before"], 4)
        self.assertEqual(receipt["triangles_after"], 4)
        self.assertEqual(receipt["parent_edges"], 1)
        self.assertEqual(receipt["scene_roots_after"], ["body", "lid", "lever"])
        self.assertFalse(receipt["truth_boundary"]["uc_inferred_domain_ownership"])
        self.assertFalse(receipt["truth_boundary"]["animation_clip_authored"])
        self.assertEqual(verify_glb(first["body"])["triangles"], 4)
        verified = verify_rigid_scene_graph(first["body"], expected_manifest_digest=first["manifest_sha256"])
        self.assertEqual(verified["parent_by_child"], {"keeper": "lid"})

    def test_manifest_order_does_not_change_output(self):
        baseline = build_glb(surface())
        original = manifest()
        reordered = copy.deepcopy(original)
        reordered["nodes"] = list(reversed(reordered["nodes"]))
        a = rebind_rigid_scene_graph(baseline["body"], original)
        b = rebind_rigid_scene_graph(baseline["body"], reordered)
        self.assertEqual(a["manifest_sha256"], b["manifest_sha256"])
        self.assertEqual(a["body"], b["body"])

    def test_unknown_parent_and_cycle_fail_closed(self):
        baseline = build_glb(surface())["body"]
        unknown = manifest()
        unknown["nodes"][0]["parent"] = "not-present"
        with self.assertRaisesRegex(RigidSceneGraphError, "parent"):
            rebind_rigid_scene_graph(baseline, unknown)
        cycle = {
            "schema": "axm.rigid-scene-graph/v0.1",
            "nodes": [
                {"name": "lid", "parent": "keeper"},
                {"name": "keeper", "parent": "lid"},
            ],
        }
        with self.assertRaisesRegex(RigidSceneGraphError, "cycle"):
            rebind_rigid_scene_graph(baseline, cycle)

    def test_nonflat_input_is_rejected_instead_of_silently_reparented(self):
        baseline = build_glb(surface())
        once = rebind_rigid_scene_graph(baseline["body"], manifest())["body"]
        with self.assertRaisesRegex(RigidSceneGraphError, "not the bounded flat UC scene"):
            rebind_rigid_scene_graph(once, manifest())

    def test_nonunit_rotation_is_rejected(self):
        baseline = build_glb(surface())["body"]
        bad = manifest()
        bad["nodes"][1]["rotation"] = [0, 0, 0, 2]
        with self.assertRaisesRegex(RigidSceneGraphError, "unit length"):
            rebind_rigid_scene_graph(baseline, bad)


if __name__ == "__main__":
    unittest.main()

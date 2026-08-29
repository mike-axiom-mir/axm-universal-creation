from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.registry import Registry
from axm_uc.topology import KernelTopology


class KernelTopologyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.bridge = KernelTopology(Registry(ROOT))

    def test_current_topology_baseline_is_measured_not_invented(self):
        summary = self.bridge.summary()
        self.assertEqual(summary["master_records"], 2165)
        self.assertEqual(summary["core_records"], 100)
        self.assertEqual(summary["master_dependency_edges"], 0)
        self.assertEqual(summary["master_relationship_edges"], 0)
        self.assertEqual(summary["core_dependency_edges"], 175)
        self.assertEqual(summary["core_resolved_dependency_edges"], 175)
        self.assertEqual(summary["core_unresolved_dependency_edges"], 0)
        self.assertEqual(summary["traversable_master_records"], 104)
        self.assertEqual(summary["ambiguous_master_records"], 0)
        self.assertEqual(summary["unresolved_master_records"], 2061)
        self.assertEqual(summary["core_records_reached_by_crosswalk"], 94)
        self.assertEqual(summary["core_records_without_master_crosswalk"], 6)

    def test_exact_graph_crosswalk_enters_declared_kernel_dependencies(self):
        master_id = "AXM-02-DATA-MATH-C-012-graph"
        mapping = self.bridge.mapping_for_master(master_id)
        self.assertTrue(mapping["traversable"])
        self.assertEqual(mapping["status"], "exact-name-level")
        self.assertEqual(mapping["core_id"], "AXM-CORE-C-006-graph")

        traversal = self.bridge.traverse_core([mapping["core_id"]], max_depth=4)
        node_ids = {row["id"] for row in traversal["nodes"]}
        self.assertIn("AXM-CORE-C-006-graph", node_ids)
        self.assertIn("AXM-CORE-A-028-node-reference", node_ids)
        self.assertIn("AXM-CORE-A-029-edge", node_ids)
        self.assertIn("AXM-CORE-A-022-relation-predicate", node_ids)
        self.assertFalse(traversal["unresolved_edges"])

    def test_weaker_scene_graph_similarity_is_visible_but_not_traversable(self):
        mapping = self.bridge.mapping_for_master("AXM-11-3D-SPATIAL-C-021-scene-graph")
        self.assertFalse(mapping["traversable"])
        self.assertEqual(mapping["status"], "unresolved")
        suggestions = mapping.get("candidate_suggestions", [])
        self.assertTrue(suggestions)
        self.assertTrue(all(item["traversable"] is False for item in suggestions))
        self.assertTrue(any(item["core_id"] == "AXM-CORE-C-006-graph" for item in suggestions))

    def test_planner_uses_kernel_graph_when_selected_anatomy_has_exact_bridge(self):
        result = UniversalCreationMachine(ROOT).plan(
            {
                "kind": "graph-model",
                "direction": "create a graph with nodes edges and typed relation predicates",
                "inputs": {"nodes": [], "edges": []},
            },
            per_level=8,
        )
        self.assertEqual(result["type"], "CREATION_DECOMPOSITION")
        topology = result["kernel_topology"]
        seeds = topology["traversal"]["seed_ids"]
        self.assertIn("AXM-CORE-C-006-graph", seeds)
        self.assertTrue(topology["traversal"]["edges"])
        self.assertEqual(result["gap"]["smallest_visible_gap"]["kind"], "kernel-backed-unimplemented-path")

    def test_machine_can_inspect_topology_from_master_or_core_side(self):
        machine = UniversalCreationMachine(ROOT)
        master_view = machine.topology(master_id="AXM-02-DATA-MATH-C-012-graph", depth=3)
        self.assertEqual(master_view["master_mapping"]["core_id"], "AXM-CORE-C-006-graph")
        self.assertTrue(master_view["traversal"]["nodes"])

        core_view = machine.topology(core_id="AXM-CORE-C-006-graph", depth=2)
        self.assertEqual(core_view["core_record"]["name"], "graph")
        self.assertTrue(any(row["id"] == "AXM-02-DATA-MATH-C-012-graph" for row in core_view["core_master_matches"]))


if __name__ == "__main__":
    unittest.main()

"""Exact Monolith graph helpers; see third_party/pipeline-provenance.json."""
from __future__ import annotations
from typing import Any

SCHEMA_VERSION = "0.1"


STATUS_BY_MIN_SCORE = {
    3: "declared_contract_path_not_tested",
    2: "structurally_possible_path_not_tested",
    1: "inferred_candidate_path_not_tested",
}


def capability_node_id(module: str, capability: str) -> str:
    return f"{module}::{capability}"


def build_pipeline_graph(analysis: dict[str, Any]) -> dict[str, Any]:
    nodes: list[dict[str, Any]] = []
    by_node: dict[str, dict[str, Any]] = {}

    for module in sorted(analysis["modules"], key=lambda item: str(item.get("module", "")).lower()):
        module_name = str(module.get("module", ""))
        for cap in sorted(module.get("capabilities", []), key=lambda item: str(item.get("id", "")).lower()):
            cap_id = str(cap.get("id", ""))
            node_id = capability_node_id(module_name, cap_id)
            node = {
                "id": node_id,
                "module": module_name,
                "repository": module.get("repository"),
                "capability": cap_id,
                "description": cap.get("description"),
                "source": cap.get("source"),
                "evidence_status": cap.get("evidence_status", "unknown"),
                "confidence": cap.get("confidence"),
                "provides": sorted({str(x) for x in cap.get("provides", []) if str(x).strip()}),
                "accepts": sorted({str(x) for x in cap.get("accepts", []) if str(x).strip()}),
                "tags": sorted({str(x) for x in cap.get("tags", []) if str(x).strip()}),
            }
            nodes.append(node)
            by_node[node_id] = node

    edges: list[dict[str, Any]] = []
    for edge in analysis.get("graph", {}).get("edges", []):
        from_id = capability_node_id(str(edge.get("from", "")), str(edge.get("producer_capability", "")))
        to_id = capability_node_id(str(edge.get("to", "")), str(edge.get("consumer_capability", "")))
        if from_id not in by_node or to_id not in by_node:
            continue
        score = int(edge.get("score", 1))
        edges.append({
            "from": from_id,
            "to": to_id,
            "from_module": edge.get("from"),
            "to_module": edge.get("to"),
            "provided": edge.get("provided"),
            "accepted": edge.get("accepted"),
            "match": edge.get("match"),
            "evidence_status": edge.get("status", "unknown"),
            "score": score,
            "truth_boundary": "candidate capability relation only; no runtime execution is implied",
        })

    edges.sort(key=lambda item: (-item["score"], item["from"].lower(), item["to"].lower(), str(item["provided"])))
    incoming = {node["id"]: 0 for node in nodes}
    outgoing = {node["id"]: 0 for node in nodes}
    for edge in edges:
        incoming[edge["to"]] += 1
        outgoing[edge["from"]] += 1

    for node in nodes:
        node["incoming_candidate_edges"] = incoming[node["id"]]
        node["outgoing_candidate_edges"] = outgoing[node["id"]]

    return {
        "schema": "axm.monolith.pipeline-graph/v0.1",
        "schema_version": SCHEMA_VERSION,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "nodes": nodes,
        "edges": edges,
        "truth_boundary": "Capability-level candidate graph only. No edge or path becomes VERIFIED through graph construction.",
    }


def path_status(edges: list[dict[str, Any]]) -> str:
    if not edges:
        return "single_capability_not_pipeline"
    minimum = min(max(1, min(3, int(edge.get("score", 1)))) for edge in edges)
    return STATUS_BY_MIN_SCORE[minimum]


def pipeline_id(nodes: list[str]) -> str:
    return " -> ".join(nodes)

from __future__ import annotations

import re
from collections import deque
from typing import Any

from .registry import Registry

TOKEN_RE = re.compile(r"[a-z0-9]+")


def _normalize(value: Any) -> str:
    return " ".join(TOKEN_RE.findall(str(value).casefold()))


def _tokens(value: Any) -> set[str]:
    return {token for token in TOKEN_RE.findall(str(value).casefold()) if len(token) > 1}


class KernelTopology:
    """Inspectable bridge between the broad master anatomy and the core kernel.

    Traversal is deliberately conservative. A master record becomes a traversable
    kernel seed only when its normalized name and anatomy level exactly match one
    unique core-kernel record. Weaker lexical/source similarities are exposed as
    suggestions but never silently promoted into dependency edges.
    """

    def __init__(self, registry: Registry):
        self.registry = registry
        self.master = registry.master_records()
        self.core = registry.core_records()
        self.master_index = {str(row.get("id")): row for row in self.master if row.get("id")}
        self.core_index = {str(row.get("id")): row for row in self.core if row.get("id")}

        self.core_by_key: dict[tuple[str, str], list[dict[str, Any]]] = {}
        for row in self.core:
            key = (str(row.get("level", "")).casefold(), _normalize(row.get("name", "")))
            self.core_by_key.setdefault(key, []).append(row)

        self.master_by_core: dict[str, list[dict[str, Any]]] = {}
        self.master_crosswalk: dict[str, dict[str, Any]] = {}
        for row in self.master:
            mapping = self._map_master(row)
            master_id = str(row.get("id"))
            self.master_crosswalk[master_id] = mapping
            if mapping.get("traversable") is True:
                core_id = str(mapping["core_id"])
                self.master_by_core.setdefault(core_id, []).append(row)

    @staticmethod
    def _source_overlap(master: dict[str, Any], core: dict[str, Any]) -> list[str]:
        return sorted(set(master.get("source_keys") or []) & set(core.get("source_keys") or []))

    def _candidate_suggestions(self, master: dict[str, Any], limit: int = 5) -> list[dict[str, Any]]:
        level = str(master.get("level", "")).casefold()
        master_name_tokens = _tokens(master.get("name", ""))
        master_definition_tokens = _tokens(master.get("definition", ""))
        suggestions: list[dict[str, Any]] = []
        for core in self.core:
            if str(core.get("level", "")).casefold() != level:
                continue
            name_overlap = sorted(master_name_tokens & _tokens(core.get("name", "")))
            definition_overlap = sorted(master_definition_tokens & _tokens(core.get("definition", "")))
            source_overlap = self._source_overlap(master, core)
            score = (12 * len(name_overlap)) + (2 * len(definition_overlap)) + (3 * len(source_overlap))
            if score <= 0:
                continue
            suggestions.append(
                {
                    "core_id": core.get("id"),
                    "core_name": core.get("name"),
                    "score": score,
                    "name_token_overlap": name_overlap,
                    "definition_token_overlap": definition_overlap[:12],
                    "source_key_overlap": source_overlap,
                    "traversable": False,
                    "meaning": "candidate correspondence only; not a dependency edge",
                }
            )
        suggestions.sort(key=lambda item: (-int(item["score"]), str(item["core_id"])))
        return suggestions[: max(1, limit)]

    def _map_master(self, master: dict[str, Any]) -> dict[str, Any]:
        key = (str(master.get("level", "")).casefold(), _normalize(master.get("name", "")))
        exact = self.core_by_key.get(key, [])
        if len(exact) == 1:
            core = exact[0]
            return {
                "master_id": master.get("id"),
                "master_name": master.get("name"),
                "master_level": master.get("level"),
                "status": "exact-name-level",
                "truth_status": "DETERMINISTIC_EXACT_CROSSWALK",
                "traversable": True,
                "core_id": core.get("id"),
                "core_name": core.get("name"),
                "evidence": {
                    "normalized_name": key[1],
                    "same_level": True,
                    "source_key_overlap": self._source_overlap(master, core),
                },
            }
        if len(exact) > 1:
            return {
                "master_id": master.get("id"),
                "master_name": master.get("name"),
                "master_level": master.get("level"),
                "status": "ambiguous-exact-name-level",
                "truth_status": "UNRESOLVED",
                "traversable": False,
                "core_candidates": [row.get("id") for row in exact],
                "reason": "more than one core record has the same normalized name and level",
            }
        return {
            "master_id": master.get("id"),
            "master_name": master.get("name"),
            "master_level": master.get("level"),
            "status": "unresolved",
            "truth_status": "UNRESOLVED",
            "traversable": False,
            "candidate_suggestions": self._candidate_suggestions(master),
            "reason": "no exact normalized-name plus level bridge exists",
        }

    def mapping_for_master(self, master_id: str) -> dict[str, Any]:
        mapping = self.master_crosswalk.get(str(master_id))
        if mapping is None:
            raise KeyError(f"unknown master record: {master_id}")
        return mapping

    def master_matches_for_core(self, core_id: str) -> list[dict[str, Any]]:
        rows = self.master_by_core.get(str(core_id), [])
        return [
            {
                "id": row.get("id"),
                "name": row.get("name"),
                "level": row.get("level"),
                "domain": row.get("domain"),
                "domain_code": row.get("domain_code"),
            }
            for row in rows
        ]

    def summary(self) -> dict[str, Any]:
        core_ids = set(self.core_index)
        dependency_edges = 0
        resolved_edges = 0
        relationship_edges = 0
        for row in self.core:
            dependencies = list(row.get("dependencies") or [])
            relationships = list(row.get("relationships") or [])
            dependency_edges += len(dependencies)
            relationship_edges += len(relationships)
            resolved_edges += sum(1 for target in dependencies if str(target) in core_ids)

        master_dependency_edges = sum(len(row.get("dependencies") or []) for row in self.master)
        master_relationship_edges = sum(len(row.get("relationships") or []) for row in self.master)
        traversable = [mapping for mapping in self.master_crosswalk.values() if mapping.get("traversable") is True]
        ambiguous = [mapping for mapping in self.master_crosswalk.values() if mapping.get("status") == "ambiguous-exact-name-level"]
        mapped_core_ids = {str(mapping["core_id"]) for mapping in traversable}
        return {
            "truth_status": "OBSERVED_REGISTRY_TOPOLOGY",
            "mapping_method": "exact normalized name plus same anatomy level; weaker suggestions never create edges",
            "master_records": len(self.master),
            "core_records": len(self.core),
            "master_dependency_edges": master_dependency_edges,
            "master_relationship_edges": master_relationship_edges,
            "core_dependency_edges": dependency_edges,
            "core_resolved_dependency_edges": resolved_edges,
            "core_unresolved_dependency_edges": dependency_edges - resolved_edges,
            "core_relationship_edges": relationship_edges,
            "traversable_master_records": len(traversable),
            "ambiguous_master_records": len(ambiguous),
            "unresolved_master_records": len(self.master) - len(traversable) - len(ambiguous),
            "core_records_reached_by_crosswalk": len(mapped_core_ids),
            "core_records_without_master_crosswalk": len(self.core) - len(mapped_core_ids),
        }

    def traverse_core(self, seed_ids: list[str], max_depth: int = 6) -> dict[str, Any]:
        max_depth = max(0, min(int(max_depth), 32))
        seeds = [str(seed) for seed in seed_ids if str(seed) in self.core_index]
        queue: deque[tuple[str, int]] = deque((seed, 0) for seed in seeds)
        seen_depth: dict[str, int] = {}
        edges: list[dict[str, Any]] = []
        unresolved: list[dict[str, Any]] = []

        while queue:
            current_id, depth = queue.popleft()
            previous = seen_depth.get(current_id)
            if previous is not None and previous <= depth:
                continue
            seen_depth[current_id] = depth
            if depth >= max_depth:
                continue
            current = self.core_index[current_id]
            for dependency_id in current.get("dependencies") or []:
                dependency_id = str(dependency_id)
                edge = {"source": current_id, "target": dependency_id, "type": "dependency"}
                if dependency_id not in self.core_index:
                    unresolved.append(edge)
                    continue
                edges.append(edge)
                queue.append((dependency_id, depth + 1))

        nodes: list[dict[str, Any]] = []
        for core_id, depth in sorted(seen_depth.items(), key=lambda pair: (pair[1], pair[0])):
            row = self.core_index[core_id]
            nodes.append(
                {
                    "id": core_id,
                    "name": row.get("name"),
                    "level": row.get("level"),
                    "depth": depth,
                    "maturity": row.get("maturity"),
                    "registry_status": row.get("registry_status"),
                    "dependencies": list(row.get("dependencies") or []),
                    "master_matches": self.master_matches_for_core(core_id),
                }
            )

        return {
            "truth_status": "OBSERVED_CORE_DEPENDENCY_TRAVERSAL",
            "seed_ids": seeds,
            "max_depth": max_depth,
            "nodes": nodes,
            "edges": edges,
            "unresolved_edges": unresolved,
            "limitations": [
                "core-kernel topology is an implementation seed, not proof that the represented capability is live",
                "only declared core dependencies are traversed; candidate crosswalk suggestions never create edges",
            ],
        }

    def for_selected_anatomy(
        self,
        selected: dict[str, list[dict[str, Any]]],
        max_depth: int = 6,
        max_seeds: int = 12,
    ) -> dict[str, Any]:
        mappings: list[dict[str, Any]] = []
        seed_ids: list[str] = []
        seen_seed: set[str] = set()

        for level in ("organ", "component", "atom"):
            for hit in selected.get(level, []):
                master_id = str(hit.get("id"))
                mapping = dict(self.mapping_for_master(master_id))
                mapping["request_match_score"] = hit.get("score")
                mapping["request_match_strength"] = hit.get("strength")
                mappings.append(mapping)
                if mapping.get("traversable") is True:
                    core_id = str(mapping["core_id"])
                    if core_id not in seen_seed and len(seed_ids) < max_seeds:
                        seen_seed.add(core_id)
                        seed_ids.append(core_id)

        traversal = self.traverse_core(seed_ids, max_depth=max_depth) if seed_ids else {
            "truth_status": "OBSERVED_CORE_DEPENDENCY_TRAVERSAL",
            "seed_ids": [],
            "max_depth": max_depth,
            "nodes": [],
            "edges": [],
            "unresolved_edges": [],
            "limitations": ["no selected master anatomy record had a traversable exact crosswalk into the kernel"],
        }
        return {
            "truth_status": "DETERMINISTIC_CROSSWALK_PLUS_DECLARED_KERNEL_GRAPH",
            "crosswalk_rule": "only exact normalized name plus same level is traversable",
            "selected_master_mappings": mappings,
            "traversal": traversal,
        }

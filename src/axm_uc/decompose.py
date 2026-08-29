from __future__ import annotations

import re
from typing import Any

from .capabilities import CapabilityStore
from .registry import Registry
from .topology import KernelTopology

TOKEN_RE = re.compile(r"[a-z0-9]+")
STOP_WORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "in",
        "into",
        "is",
        "it",
        "of",
        "on",
        "or",
        "the",
        "to",
        "with",
    }
)
FIELD_WEIGHTS = {
    "name": 12,
    "id": 5,
    "domain_code": 5,
    "domain": 4,
    "definition": 3,
}
LEVELS = ("atom", "component", "organ")


def _normalize(value: Any) -> str:
    return " ".join(TOKEN_RE.findall(str(value).casefold()))


def _tokens(value: Any) -> set[str]:
    return {
        token
        for token in TOKEN_RE.findall(str(value).casefold())
        if token not in STOP_WORDS and len(token) > 1
    }


def _flatten(value: Any) -> list[str]:
    result: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            result.append(str(key))
            result.extend(_flatten(value[key]))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            result.extend(_flatten(item))
    elif value is not None:
        result.append(str(value))
    return result


def _strength(score: int) -> str:
    if score >= 36:
        return "strong"
    if score >= 18:
        return "medium"
    return "weak"


class CreationDecomposer:
    """Deterministic bridge from a request into explicit AXM anatomy and topology.

    Lexical matching remains a visible baseline. Exact name+level crosswalks may
    then enter the separately declared core-kernel dependency graph. Weaker
    crosswalk suggestions stay suggestions and never silently create graph edges.
    """

    def __init__(self, registry: Registry, capabilities: CapabilityStore):
        self.registry = registry
        self.capabilities = capabilities
        self.topology = KernelTopology(registry)

    @staticmethod
    def _request_text(request: dict[str, Any]) -> tuple[str, set[str]]:
        flattened = _flatten(request)
        text = " ".join(flattened)
        return _normalize(text), _tokens(text)

    @staticmethod
    def _record_hit(record: dict[str, Any], request_text: str, terms: set[str]) -> dict[str, Any] | None:
        evidence: dict[str, list[str]] = {}
        score = 0
        for field, weight in FIELD_WEIGHTS.items():
            matched = sorted(terms & _tokens(record.get(field, "")))
            if matched:
                evidence[field] = matched
                score += len(matched) * weight

        name = str(record.get("name", ""))
        normalized_name = _normalize(name)
        phrase_match = bool(normalized_name and normalized_name in request_text)
        if phrase_match:
            score += 18

        if score <= 0:
            return None

        return {
            "id": record.get("id"),
            "level": record.get("level"),
            "name": name,
            "domain": record.get("domain"),
            "domain_code": record.get("domain_code"),
            "score": score,
            "strength": _strength(score),
            "evidence": evidence,
            "phrase_match": phrase_match,
            "dependencies": list(record.get("dependencies") or []),
            "relationships": list(record.get("relationships") or []),
        }

    @staticmethod
    def _capability_hit(capability: dict[str, Any], terms: set[str], kind: str) -> dict[str, Any] | None:
        handles = [str(handle) for handle in capability.get("handles", [])]
        exact = kind in handles
        searchable = " ".join(
            [str(capability.get("id", "")), str(capability.get("purpose", "")), *handles]
        )
        matched = sorted(terms & _tokens(searchable))
        if not exact and not matched:
            return None
        score = (50 if exact else 0) + (8 * len(matched))
        return {
            "id": capability.get("id"),
            "purpose": capability.get("purpose"),
            "handles": handles,
            "exact_handle_match": exact,
            "matched_terms": matched,
            "score": score,
            "required_inputs": sorted(capability.get("input_contract", {}).get("required", [])),
            "manifest": capability.get("_manifest_path"),
        }

    def _dependency_hints(
        self,
        selected: dict[str, list[dict[str, Any]]],
        index: dict[str, dict[str, Any]],
        limit: int = 24,
    ) -> list[dict[str, Any]]:
        """Direct master-map dependency hints kept for backwards compatibility.

        The current master map is flat, so useful dependency topology normally
        comes from ``kernel_topology`` rather than this field.
        """
        hints: list[dict[str, Any]] = []
        seen: set[tuple[str, str]] = set()
        for level in reversed(LEVELS):
            for hit in selected[level]:
                for dependency_id in hit.get("dependencies", []):
                    key = (str(hit.get("id")), str(dependency_id))
                    if key in seen:
                        continue
                    seen.add(key)
                    dependency = index.get(str(dependency_id))
                    hints.append(
                        {
                            "required_by": hit.get("id"),
                            "dependency_id": dependency_id,
                            "resolved": dependency is not None,
                            "dependency_level": dependency.get("level") if dependency else None,
                            "dependency_name": dependency.get("name") if dependency else None,
                        }
                    )
                    if len(hints) >= limit:
                        return hints
        return hints

    @staticmethod
    def _gap(
        request: dict[str, Any],
        selected: dict[str, list[dict[str, Any]]],
        live_hits: list[dict[str, Any]],
        kernel_topology: dict[str, Any],
    ) -> dict[str, Any]:
        exact = next((hit for hit in live_hits if hit["exact_handle_match"]), None)
        if exact:
            return {
                "status": "covered",
                "truth_status": "DETERMINISTIC_ROUTE_MATCH",
                "smallest_visible_gap": None,
                "covered_by": exact["id"],
            }

        inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
        input_keys = set(inputs)
        reusable = next(
            (
                hit
                for hit in live_hits
                if hit["required_inputs"] and set(hit["required_inputs"]).issubset(input_keys)
            ),
            None,
        )
        if reusable:
            return {
                "status": "visible-gap",
                "truth_status": "HYPOTHESIS",
                "smallest_visible_gap": {
                    "kind": "routing-or-adapter",
                    "reuse_capability": reusable["id"],
                    "reason": "existing live machinery already accepts the supplied required input shape",
                },
            }

        traversal = kernel_topology.get("traversal") if isinstance(kernel_topology, dict) else None
        nodes = traversal.get("nodes", []) if isinstance(traversal, dict) else []
        seeds = traversal.get("seed_ids", []) if isinstance(traversal, dict) else []
        if nodes and seeds:
            seed_node = next((node for node in nodes if node.get("id") == seeds[0]), nodes[0])
            return {
                "status": "visible-gap",
                "truth_status": "HYPOTHESIS",
                "smallest_visible_gap": {
                    "kind": "kernel-backed-unimplemented-path",
                    "kernel_seed": seed_node.get("id"),
                    "kernel_name": seed_node.get("name"),
                    "declared_dependency_nodes": len(nodes),
                    "declared_dependency_edges": len(traversal.get("edges", [])),
                    "reason": "selected master anatomy has an exact crosswalk into a declared kernel dependency path, but kernel topology is not proof of a live implementation",
                },
            }

        for level in ("organ", "component", "atom"):
            if selected[level]:
                top = selected[level][0]
                return {
                    "status": "visible-gap",
                    "truth_status": "HYPOTHESIS",
                    "smallest_visible_gap": {
                        "kind": f"unimplemented-{level}-path",
                        "registry_target": top["id"],
                        "registry_name": top["name"],
                        "reason": "highest-scoring explicit anatomy currently related to the request; registry presence is not implementation proof",
                    },
                }

        return {
            "status": "unresolved-gap",
            "truth_status": "HYPOTHESIS",
            "smallest_visible_gap": {
                "kind": "taxonomy-or-capability-gap",
                "reason": "no current live capability, traversable kernel bridge, or lexical registry match explains the request",
            },
        }

    def decompose(self, request: dict[str, Any], per_level: int = 6) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be an object")
        kind = request.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("request.kind must be a non-empty string")
        per_level = max(1, min(int(per_level), 50))

        request_text, terms = self._request_text(request)
        records = self.registry.master_records()
        index = {str(record.get("id")): record for record in records if record.get("id")}
        candidates: dict[str, list[dict[str, Any]]] = {level: [] for level in LEVELS}

        for record in records:
            level = str(record.get("level", ""))
            if level not in candidates:
                continue
            hit = self._record_hit(record, request_text, terms)
            if hit:
                candidates[level].append(hit)

        selected: dict[str, list[dict[str, Any]]] = {}
        for level in LEVELS:
            candidates[level].sort(key=lambda item: (-int(item["score"]), str(item["id"])))
            selected[level] = candidates[level][:per_level]

        live_hits = [
            hit
            for capability in self.capabilities.live()
            if (hit := self._capability_hit(capability, terms, kind)) is not None
        ]
        live_hits.sort(key=lambda item: (-int(item["score"]), str(item["id"])))

        kernel_topology = self.topology.for_selected_anatomy(selected)
        master_dependency_hints = self._dependency_hints(selected, index)

        return {
            "type": "CREATION_DECOMPOSITION",
            "truth_status": "DETERMINISTIC_LEXICAL_BASELINE_PLUS_DECLARED_KERNEL_TOPOLOGY",
            "directional_outcome": request.get("direction") or request.get("purpose") or kind,
            "request_kind": kind,
            "request_terms": sorted(terms),
            "method": {
                "matcher": "explicit token overlap plus exact registry-name phrase boost",
                "field_weights": dict(FIELD_WEIGHTS),
                "semantic_inference": False,
                "learned_model": False,
                "kernel_crosswalk": "only exact normalized name plus same level is traversable",
                "meaning": "candidate anatomy plus declared kernel dependencies; neither registry presence nor kernel presence proves a live implementation",
            },
            "live_capability_coverage": live_hits[:8],
            "registry_matches": selected,
            "dependency_hints": master_dependency_hints,
            "master_dependency_hints": master_dependency_hints,
            "kernel_topology": kernel_topology,
            "gap": self._gap(request, selected, live_hits, kernel_topology),
        }

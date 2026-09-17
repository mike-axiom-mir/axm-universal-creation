"""Fail-closed observer for attribute-aware indexed surface eligibility.

This module never mutates a surface. It computes a deterministic candidate
index domain from exact declared render attributes and caller-declared protected
split identity. Visual equality, runtime savings, adoption and domain-specific
meaning remain outside this contract.
"""
from __future__ import annotations

import hashlib
import json
import math
from typing import Any

SCHEMA = "axm.indexed-surface-eligibility-report/v0.1"
INPUT_SCHEMA = "axm.indexed-surface-lineage/v0.1"
MAX_VERTICES = 250_000
MAX_INDICES = 3_000_000
MAX_CHANNELS = 16
MAX_TEXT = 256

SUPPORTED_CHANNELS = {
    "POSITION": (3,),
    "NORMAL": (3,),
    "TEXCOORD_0": (2,),
    "TANGENT": (4,),
    "COLOR_0": (3, 4),
    "JOINTS_0": (4,),
    "WEIGHTS_0": (4,),
}

NON_CLAIMS = [
    "No surface is mutated or adopted by this observer.",
    "Structural eligibility does not prove rendered equality or visual acceptance.",
    "Candidate counts do not prove target-host or target-device memory/performance savings.",
    "No domain-specific seam, topology, skin, material or animation policy is inferred.",
]


def _stable(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def _digest(value: Any) -> str:
    return hashlib.sha256(_stable(value)).hexdigest()


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value or len(value) > MAX_TEXT:
        raise ValueError(f"{label} must be non-empty bounded text")
    return value


def _integer(value: Any, label: str, low: int, high: int) -> int:
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")
    return value


def _number(value: Any, label: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    if isinstance(value, float) and value == 0.0:
        return 0.0
    return value


def _indices(value: Any, count: int, label: str) -> list[int]:
    if not isinstance(value, list) or not value or len(value) > MAX_INDICES or len(value) % 3:
        raise ValueError(f"{label} must be a bounded non-empty triangle index list")
    return [_integer(item, f"{label}[{i}]", 0, count - 1) for i, item in enumerate(value)]


def _channels(value: Any, render_count: int) -> tuple[dict[str, list[tuple[int | float, ...]]], list[str]]:
    if not isinstance(value, dict) or not value or len(value) > MAX_CHANNELS:
        raise ValueError("render.channels must be a bounded non-empty object")
    unknown = sorted(name for name in value if name not in SUPPORTED_CHANNELS)
    if "POSITION" not in value:
        raise ValueError("render.channels requires POSITION")
    if unknown:
        return {}, unknown
    output: dict[str, list[tuple[int | float, ...]]] = {}
    for name in sorted(value):
        rows = value[name]
        if not isinstance(rows, list) or len(rows) != render_count:
            raise ValueError(f"{name} must contain exactly {render_count} rows")
        allowed = SUPPORTED_CHANNELS[name]
        normalized = []
        for index, row in enumerate(rows):
            if not isinstance(row, (list, tuple)) or len(row) not in allowed:
                widths = "/".join(str(width) for width in allowed)
                raise ValueError(f"{name}[{index}] must have width {widths}")
            normalized.append(tuple(_number(item, f"{name}[{index}]") for item in row))
        output[name] = normalized
    return output, []


def _base_report(source_identity: str, surface_identity: str) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "source_identity": source_identity,
        "surface_identity": surface_identity,
        "observer_only": True,
        "non_claims": list(NON_CLAIMS),
    }


def observe_indexed_surface_eligibility(spec: dict[str, Any]) -> dict[str, Any]:
    """Inspect an explicit source/render lineage without changing the surface."""
    if not isinstance(spec, dict) or spec.get("schema") != INPUT_SCHEMA:
        raise ValueError(f"spec must use {INPUT_SCHEMA}")
    source_identity = _text(spec.get("source_identity"), "source_identity")
    surface_identity = _text(spec.get("surface_identity"), "surface_identity")
    source = spec.get("source")
    render = spec.get("render")
    if not isinstance(source, dict) or not isinstance(render, dict):
        raise ValueError("source and render must be objects")

    source_count = _integer(source.get("vertex_count"), "source.vertex_count", 1, MAX_VERTICES)
    render_count = _integer(render.get("vertex_count"), "render.vertex_count", 1, MAX_VERTICES)
    source_indices = _indices(source.get("indices"), source_count, "source.indices")
    render_indices = _indices(render.get("indices"), render_count, "render.indices")

    mapping_value = render.get("source_vertex_indices")
    if mapping_value is None:
        if source_count != render_count:
            raise ValueError("expanded render domains require source_vertex_indices")
        mapping = list(range(render_count))
    else:
        if not isinstance(mapping_value, list) or len(mapping_value) != render_count:
            raise ValueError("render.source_vertex_indices must match render.vertex_count")
        mapping = [
            _integer(item, f"render.source_vertex_indices[{i}]", 0, source_count - 1)
            for i, item in enumerate(mapping_value)
        ]

    base = _base_report(source_identity, surface_identity)
    base["input_digest"] = _digest(spec)
    base["source_domain"] = {
        "vertex_count": source_count,
        "index_count": len(source_indices),
        "triangle_count": len(source_indices) // 3,
        "digest": _digest({"vertex_count": source_count, "indices": source_indices}),
    }
    base["render_domain"] = {
        "vertex_count": render_count,
        "index_count": len(render_indices),
        "triangle_count": len(render_indices) // 3,
        "source_mapping_digest": _digest(mapping),
    }

    channels, unknown = _channels(render.get("channels"), render_count)
    if unknown:
        base.update({
            "eligibility_state": "NOT_EVALUATED_UNSUPPORTED_CHANNEL",
            "render_domain_state": "NOT_EVALUATED",
            "unsupported_channels": unknown,
            "candidate": None,
        })
        return base

    base["declared_channels"] = sorted(channels)
    base["channel_digests"] = {name: _digest(rows) for name, rows in channels.items()}

    protected_present = "protected_split_ids" in render
    protected_value = render.get("protected_split_ids")
    if not protected_present:
        if render_count != source_count or mapping != list(range(render_count)):
            base.update({
                "eligibility_state": "HOLD_ATTRIBUTE_SEAM_AMBIGUITY",
                "render_domain_state": "NOT_EVALUATED",
                "hold_reason": "expanded or remapped render domain requires explicit protected_split_ids; use null entries to declare no extra protected identity",
                "candidate": None,
            })
            return base
        protected = [None] * render_count
    else:
        if not isinstance(protected_value, list) or len(protected_value) != render_count:
            raise ValueError("render.protected_split_ids must match render.vertex_count")
        protected = []
        for i, item in enumerate(protected_value):
            if item is None:
                protected.append(None)
            elif isinstance(item, str) and item and len(item) <= MAX_TEXT:
                protected.append(item)
            else:
                raise ValueError(f"render.protected_split_ids[{i}] must be null or bounded non-empty text")

    channel_order = sorted(channels)
    keys = []
    for index in range(render_count):
        key = [mapping[index]]
        key.extend([name, channels[name][index]] for name in channel_order)
        if protected[index] is not None:
            key.append(["PROTECTED_SPLIT", protected[index]])
        keys.append(key)

    candidate_map: list[int] = []
    key_to_candidate: dict[bytes, int] = {}
    for key in keys:
        encoded = _stable(key)
        candidate = key_to_candidate.get(encoded)
        if candidate is None:
            candidate = len(key_to_candidate)
            key_to_candidate[encoded] = candidate
        candidate_map.append(candidate)
    candidate_indices = [candidate_map[index] for index in render_indices]
    candidate_count = len(key_to_candidate)

    by_position: dict[bytes, list[int]] = {}
    for index, row in enumerate(channels["POSITION"]):
        by_position.setdefault(_stable(row), []).append(index)
    split_groups = [
        group for group in by_position.values()
        if len(group) > 1 and len({candidate_map[index] for index in group}) > 1
    ]

    per_channel_splits: dict[str, int] = {}
    for name in channel_order:
        count = 0
        for group in by_position.values():
            if len(group) > 1 and len({channels[name][index] for index in group}) > 1:
                count += 1
        per_channel_splits[name] = count

    protected_groups = len({item for item in protected if item is not None})
    domain_state = "SAME_AS_SOURCE"
    if render_count != source_count or mapping != list(range(render_count)):
        domain_state = "RENDER_DOMAIN_SPLIT_REQUIRED" if candidate_count > source_count else "RENDER_DOMAIN_DERIVED"

    if candidate_count < render_count:
        eligibility = "POST_ATTRIBUTE_TUPLE_DEDUP_CANDIDATE"
    elif source_count == render_count and mapping == list(range(render_count)):
        eligibility = "PRESERVE_SOURCE_INDEXING"
    else:
        eligibility = "PRESERVE_RENDER_DOMAIN_INDEXING"

    base["eligibility_state"] = eligibility
    base["render_domain_state"] = domain_state
    base["unsupported_channels"] = []
    base["split_observation"] = {
        "position_coincident_split_groups": len(split_groups),
        "split_groups_by_channel": per_channel_splits,
        "protected_split_id_count": protected_groups,
        "position_only_weld_safe": len(split_groups) == 0,
    }
    base["candidate"] = {
        "vertex_count": candidate_count,
        "index_count": len(candidate_indices),
        "triangle_count": len(candidate_indices) // 3,
        "render_vertex_to_candidate": candidate_map,
        "indices": candidate_indices,
        "key_digest": _digest(keys),
        "mapping_digest": _digest(candidate_map),
        "index_digest": _digest(candidate_indices),
    }
    return base

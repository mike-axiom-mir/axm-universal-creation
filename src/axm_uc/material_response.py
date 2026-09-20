"""Bounded material-response intent above UC texture/channel material data.

The imported Opus response pack is data/contract evidence, not renderer proof.
This module resolves named families and keeps unbound renderer behavior as HOLD.
"""
from __future__ import annotations

import copy
import hashlib
import json
from importlib.resources import files
from typing import Any

EVIDENCE = "declared_contract_match_not_tested"
SOURCE_ARCHIVE_SHA256 = "9b263ddd536c7f9aa1b6640ad7672283c0e30e7c2b818a7ee23076aafdd1a363"
SOURCE_PACK_SHA256 = "cc101f7f975e4334570b89d3dacede28e537f6ae09fd11af49d9864a2d064cf5"

BASE_KEYS = {"base_color", "roughness", "metallic", "specular", "ior", "note"}
ORGAN_BY_KEY = {
    "subsurface": "surface.subsurface",
    "sheen": "surface.sheen",
    "anisotropy": "surface.anisotropy",
    "clearcoat": "surface.coat",
    "breakup": "surface.breakup",
    "transmission": "surface.transmission",
    "transmission_tint": "surface.transmission",
    "absorption": "surface.transmission",
    "dispersion": "surface.transmission",
    "iridescence": "surface.iridescence",
    "layers": "surface.wear_layer",
    "flake": "surface.coat",
}


class MaterialResponseHold(ValueError):
    """A requested response cannot be honestly resolved/bound."""


def _root():
    return files("axm_uc").joinpath("data", "material_response")


def _load(name: str) -> Any:
    return json.loads(_root().joinpath(name).read_text(encoding="utf-8"))


def _digest_bytes(name: str) -> str:
    return hashlib.sha256(_root().joinpath(name).read_bytes()).hexdigest()


def _organ_records() -> dict[str, dict[str, Any]]:
    values = _load("organs.json")
    if not isinstance(values, list):
        raise MaterialResponseHold("material-response organ data must be a list")
    result = {}
    for value in values:
        if not isinstance(value, dict) or value.get("format") != "axm-material-response-organ":
            raise MaterialResponseHold("invalid material-response organ record")
        organ_id = value.get("id")
        if not isinstance(organ_id, str) or organ_id in result:
            raise MaterialResponseHold("material-response organ ids must be unique strings")
        result[organ_id] = value
    return result


def _pack() -> dict[str, Any]:
    value = _load("pack.json")
    if not isinstance(value, dict) or value.get("format") != "axm-material-response-pack":
        raise MaterialResponseHold("invalid material-response pack")
    families = value.get("families")
    if not isinstance(families, list) or not families:
        raise MaterialResponseHold("material-response pack has no families")
    return value


def _active(value: Any, key: str, response: dict[str, Any]) -> bool:
    if key == "transmission":
        weight = value.get("weight", 0) if isinstance(value, dict) else value
        return isinstance(weight, (int, float)) and not isinstance(weight, bool) and abs(float(weight)) > 1e-12
    if key in {"transmission_tint", "absorption", "dispersion"}:
        return _active(response.get("transmission", 0), "transmission", response)
    if key == "layers":
        return isinstance(value, list) and any(
            isinstance(layer, dict) and float(layer.get("weight", 1) or 0) > 1e-12 for layer in value
        )
    if key == "anisotropy":
        return isinstance(value, dict) and abs(float(value.get("strength", 0) or 0)) > 1e-12
    if key == "breakup":
        if not isinstance(value, dict):
            return False
        return any(
            isinstance(v, (int, float)) and not isinstance(v, bool) and abs(float(v)) > 1e-12
            for k, v in value.items() if k not in {"scale_mm", "octaves"}
        )
    if key in {"subsurface", "sheen", "clearcoat", "iridescence", "flake"}:
        return isinstance(value, dict) and float(value.get("weight", 0) or 0) > 1e-12
    return value is not None


def active_organs(response: dict[str, Any]) -> list[str]:
    if not isinstance(response, dict):
        raise MaterialResponseHold("material response must be an object")
    records = _organ_records()
    active = set()
    for key, value in response.items():
        if key in BASE_KEYS:
            continue
        organ_id = ORGAN_BY_KEY.get(key)
        if organ_id is None:
            raise MaterialResponseHold(f"unknown material-response key: {key}")
        if organ_id not in records:
            raise MaterialResponseHold(f"material-response organ is not present: {organ_id}")
        if _active(value, key, response):
            active.add(organ_id)
    return sorted(active)


def _deep_merge(base: Any, patch: Any) -> Any:
    if isinstance(base, dict) and isinstance(patch, dict):
        result = copy.deepcopy(base)
        for key, value in patch.items():
            result[key] = _deep_merge(result[key], value) if key in result else copy.deepcopy(value)
        return result
    return copy.deepcopy(patch)


def resolve_material_response(
    family: str,
    *,
    variant: str | None = None,
    overrides: dict[str, Any] | None = None,
    base_color: list[float] | None = None,
) -> dict[str, Any]:
    pack = _pack()
    matches = [item for item in pack["families"] if item.get("id") == family]
    if len(matches) != 1:
        raise MaterialResponseHold(f"unknown material-response family: {family}")
    item = matches[0]
    response = copy.deepcopy(item["response"])
    if variant is not None:
        variants = item.get("variants", {})
        if variant not in variants:
            raise MaterialResponseHold(f"unknown {family} variant: {variant}")
        response = _deep_merge(response, variants[variant])
    if overrides is not None:
        if not isinstance(overrides, dict):
            raise MaterialResponseHold("material-response overrides must be an object")
        response = _deep_merge(response, overrides)
    if base_color is not None:
        if not isinstance(base_color, list) or len(base_color) != 3:
            raise MaterialResponseHold("base_color override must be RGB")
        response["base_color"] = [float(v) for v in base_color]
    organs = active_organs(response)
    return {
        "schema": "axm.material-response-resolution/v0.1",
        "family": family,
        "variant": variant,
        "purpose": item.get("purpose"),
        "response": response,
        "active_organs": organs,
        "evidence": EVIDENCE,
        "renderer_binding": "HOLD_RENDERER_BINDING_NOT_TESTED" if organs else "PASS_NO_ACTIVE_ORGANS",
        "source": {
            "archive_sha256": SOURCE_ARCHIVE_SHA256,
            "declared_source_pack_sha256": SOURCE_PACK_SHA256,
            "repo_pack_sha256": _digest_bytes("pack.json"),
        },
        "truth": (
            "This resolves explicit material behavior intent above channel/texture values. "
            "It does not prove that any UC renderer has bound the active organs."
        ),
    }


def resolve_material_graph_response(graph: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(graph, dict):
        raise MaterialResponseHold("material graph must be an object")
    spec = graph.get("response")
    if spec is None:
        return {"status": "PASS_NO_RESPONSE", "response": None}
    if not isinstance(spec, dict) or set(spec) - {"family", "variant", "overrides"}:
        raise MaterialResponseHold("material graph response accepts family, optional variant and overrides")
    result = resolve_material_response(
        spec.get("family"),
        variant=spec.get("variant"),
        overrides=spec.get("overrides"),
    )
    return {"status": result["renderer_binding"], "response": result}


def material_response_catalog() -> dict[str, Any]:
    pack = _pack()
    organs = _organ_records()
    return {
        "schema": "axm.material-response-catalog/v0.1",
        "families": [
            {"id": item["id"], "purpose": item.get("purpose"), "variants": sorted(item.get("variants", {}))}
            for item in pack["families"]
        ],
        "organs": [
            {
                "id": value["id"],
                "name": value.get("name"),
                "evidence": value.get("evidence"),
                "known_losses": copy.deepcopy(value.get("known_losses", [])),
            }
            for value in sorted(organs.values(), key=lambda item: item["id"])
        ],
        "counts": {"families": len(pack["families"]), "organs": len(organs)},
        "evidence": EVIDENCE,
        "renderer_binding": "NOT_CLAIMED",
        "source": {
            "archive_sha256": SOURCE_ARCHIVE_SHA256,
            "declared_source_pack_sha256": SOURCE_PACK_SHA256,
            "repo_pack_sha256": _digest_bytes("pack.json"),
        },
    }

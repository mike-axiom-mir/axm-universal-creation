from __future__ import annotations

import copy
import json
from typing import Any

from . import material_capability_exchange as exchange


VERSION = "0.19.0"
SPRITE_SCHEMA = "axm.uc.material-sprite-candidate/v0.1"
RECIPE_SCHEMA = "axm.uc.material-recipe/v0.1"
PATTERN_SCHEMA = "axm.uc.material-pattern/v0.1"
MAX_DESCRIPTOR_BYTES = 262_144
MAX_RECIPE_LAYERS = 64
MAX_PATTERN_SLOTS = 128
CONSUMER = {
    "system": "AXM Universal Creation",
    "repository": "mike-axiom-mir/axm-universal-creation",
    "adapter": "material-capability-consumer/v0.19.0",
    "instance": None,
}


class FullMaterialCapabilityError(exchange.MaterialCapabilityError):
    pass


def _json_size(value: Any) -> int:
    try:
        return len(
            json.dumps(
                value,
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            ).encode("utf-8")
        )
    except (TypeError, ValueError) as exc:
        raise FullMaterialCapabilityError("visual capability payload must be deterministic JSON") from exc


def _require_bounded(value: Any, label: str) -> None:
    size = _json_size(value)
    if size > MAX_DESCRIPTOR_BYTES:
        raise FullMaterialCapabilityError(
            f"{label} exceeds the detached descriptor bound",
            {"bytes": size, "maximum": MAX_DESCRIPTOR_BYTES},
        )


def _projection_id(prefix: str, capability: dict[str, Any]) -> str:
    basis = {
        "capabilityId": capability["id"],
        "capabilityFingerprint": capability["fingerprint"],
        "payload": capability["payload"],
    }
    return f"uc-{prefix}-{exchange._fnv1a_js(exchange._stable_json(basis))}"


def _number(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FullMaterialCapabilityError(f"{label} must be numeric")
    number = float(value)
    if number != number or number in {float("inf"), float("-inf")}:
        raise FullMaterialCapabilityError(f"{label} must be finite")
    return number


def _normalized_bounds(raw: Any) -> dict[str, float]:
    if not isinstance(raw, dict):
        raise FullMaterialCapabilityError("sprite normalizedBounds must be an object")
    result = {key: _number(raw.get(key), f"normalizedBounds.{key}") for key in ("x", "y", "width", "height")}
    if result["x"] < 0 or result["y"] < 0 or result["width"] <= 0 or result["height"] <= 0:
        raise FullMaterialCapabilityError("sprite normalizedBounds must be positive and inside the source atlas")
    if result["x"] + result["width"] > 1.000001 or result["y"] + result["height"] > 1.000001:
        raise FullMaterialCapabilityError("sprite normalizedBounds exceed the source atlas")
    return result


def project_sprite_candidate(capability: dict[str, Any]) -> dict[str, Any]:
    payload = capability.get("payload") or {}
    atlas_id = str(payload.get("atlasId") or "").strip()
    if not atlas_id:
        raise FullMaterialCapabilityError("sprite-candidate atlasId is required")
    bounds = _normalized_bounds(payload.get("normalizedBounds"))
    _require_bounded(payload, "sprite-candidate payload")
    return {
        "schema": SPRITE_SCHEMA,
        "id": _projection_id("sprite", capability),
        "source": {
            "capabilityId": capability["id"],
            "capabilityFingerprint": capability["fingerprint"],
            "sourceId": capability["sourceId"],
            "provenance": copy.deepcopy(capability.get("provenance") or {}),
        },
        "atlasId": atlas_id,
        "normalizedBounds": bounds,
        "observedBounds": copy.deepcopy(payload.get("bounds")),
        "alphaCoverage": copy.deepcopy(payload.get("alphaCoverage") or {}),
        "componentCount": payload.get("componentCount"),
        "pixelCount": payload.get("pixelCount"),
        "rgbaHash": payload.get("rgbaHash"),
        "spriteFile": payload.get("spriteFile"),
        "spriteSha256": payload.get("spriteSha256"),
        "truthBoundary": {
            "geometry": "The detached descriptor preserves the producer-declared alpha-derived atlas bounds exactly.",
            "semantics": "A sprite candidate is not promoted into semantic object recognition.",
            "rendering": "Descriptor adoption does not prove source-byte availability or renderer output.",
            "authority": "Detached intake does not modify live Universal Creation topology or canonical project state.",
        },
    }


def project_recipe(capability: dict[str, Any]) -> dict[str, Any]:
    payload = capability.get("payload") or {}
    recipe = payload.get("recipe")
    if not isinstance(recipe, dict):
        raise FullMaterialCapabilityError("recipe capability requires payload.recipe")
    if recipe.get("format") != "axm-premade-composition" or recipe.get("version") != "0.12.0":
        raise FullMaterialCapabilityError("recipe capability requires axm-premade-composition/v0.12.0")
    canvas = recipe.get("canvas")
    if not isinstance(canvas, dict) or canvas.get("transparent") is not True:
        raise FullMaterialCapabilityError("recipe intake requires transparent:true")
    layers = recipe.get("layers")
    if not isinstance(layers, list) or len(layers) > MAX_RECIPE_LAYERS:
        raise FullMaterialCapabilityError(f"recipe layers must contain 0..{MAX_RECIPE_LAYERS} items")
    for index, layer in enumerate(layers):
        if not isinstance(layer, dict) or not str(layer.get("assetId") or "").strip():
            raise FullMaterialCapabilityError(f"recipe layer {index} requires assetId")
    recipe_fingerprint = str(payload.get("recipeFingerprint") or "").strip()
    if not recipe_fingerprint:
        raise FullMaterialCapabilityError("recipeFingerprint is required")
    _require_bounded(recipe, "recipe")
    return {
        "schema": RECIPE_SCHEMA,
        "id": _projection_id("recipe", capability),
        "source": {
            "capabilityId": capability["id"],
            "capabilityFingerprint": capability["fingerprint"],
            "sourceId": capability["sourceId"],
            "provenance": copy.deepcopy(capability.get("provenance") or {}),
        },
        "recipeFingerprint": recipe_fingerprint,
        "premadePack": copy.deepcopy(payload.get("premadePack") or {}),
        "layerCount": len(layers),
        "transparent": True,
        "recipe": copy.deepcopy(recipe),
        "truthBoundary": {
            "state": "The exact deterministic recipe state is retained as a detached Universal Creation descriptor.",
            "rendering": "Universal Creation has not rendered or visually judged this recipe by adopting the descriptor.",
            "assets": "Referenced atlas assets are preserved by ID; their bytes are not implied to be installed here.",
            "authority": "Recipe intake does not auto-create, promote, or overwrite canonical project state.",
        },
    }


def project_pattern(capability: dict[str, Any]) -> dict[str, Any]:
    payload = capability.get("payload") or {}
    pattern = payload.get("pattern")
    if not isinstance(pattern, dict):
        raise FullMaterialCapabilityError("pattern capability requires payload.pattern")
    pattern_id = str(pattern.get("id") or "").strip()
    if not pattern_id or pattern_id != capability["sourceId"]:
        raise FullMaterialCapabilityError("pattern id must match capability sourceId")
    support = pattern.get("support", payload.get("support"))
    if isinstance(support, bool) or not isinstance(support, int) or support < 1:
        raise FullMaterialCapabilityError("pattern support must be a positive integer")
    slots = pattern.get("slots")
    if not isinstance(slots, list) or not 1 <= len(slots) <= MAX_PATTERN_SLOTS:
        raise FullMaterialCapabilityError(f"pattern slots must contain 1..{MAX_PATTERN_SLOTS} items")
    seen_orders: set[int] = set()
    for index, slot in enumerate(slots):
        if not isinstance(slot, dict):
            raise FullMaterialCapabilityError(f"pattern slot {index} must be an object")
        order = slot.get("order")
        if isinstance(order, bool) or not isinstance(order, int) or order < 0 or order in seen_orders:
            raise FullMaterialCapabilityError("pattern slot order must be unique non-negative integers")
        seen_orders.add(order)
        if not str(slot.get("role") or "").strip() or not str(slot.get("kind") or "").strip():
            raise FullMaterialCapabilityError(f"pattern slot {index} requires role and kind")
    _require_bounded(pattern, "pattern")
    return {
        "schema": PATTERN_SCHEMA,
        "id": _projection_id("pattern", capability),
        "source": {
            "capabilityId": capability["id"],
            "capabilityFingerprint": capability["fingerprint"],
            "sourceId": capability["sourceId"],
            "provenance": copy.deepcopy(capability.get("provenance") or {}),
        },
        "support": support,
        "slotCount": len(slots),
        "pattern": copy.deepcopy(pattern),
        "truthBoundary": {
            "learning": "Pattern support is recurrence among explicit producer keeper history, not preference or quality truth.",
            "semantics": "Pattern structure is retained without inferring creator intent beyond the supplied fields.",
            "execution": "Descriptor adoption does not make the pattern an active Universal Creation generation rule.",
            "authority": "Pattern intake does not auto-promote recipes, alter memory, or modify canonical project state.",
        },
    }


def _feedback_event(
    capability_id: str,
    action: str,
    outcome: str,
    *,
    evidence: dict[str, Any],
    derived_ids: list[str],
    note: str,
) -> dict[str, Any]:
    return exchange._event(
        capability_id,
        action,
        outcome,
        evidence=evidence,
        derived_ids=derived_ids,
        note=note,
    )


def _create_feedback(pack: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    basis = {
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": CONSUMER,
        "events": events,
    }
    fingerprint = exchange._fnv1a_js(exchange._stable_json(basis))
    return {
        "format": exchange.FEEDBACK_FORMAT,
        "version": exchange.FEEDBACK_VERSION,
        "id": f"material-use-feedback-{fingerprint}",
        "fingerprint": fingerprint,
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": copy.deepcopy(CONSUMER),
        "events": copy.deepcopy(events),
        "note": "AXM Universal Creation full detached material-capability intake receipt.",
        "truthBoundary": {
            "use": "PASS adopted means a bounded detached Universal Creation representation was created for the named capability.",
            "quality": "Adoption does not prove beauty, realism, PBR correctness, semantic understanding, or renderer output.",
            "authority": "Feedback cannot silently rewrite either repository's canonical state.",
        },
    }


def validate_full_material_use_feedback(feedback: Any, raw_pack: Any) -> dict[str, Any]:
    pack = exchange.validate_material_capability_pack(raw_pack)
    if not isinstance(feedback, dict):
        raise FullMaterialCapabilityError("material use feedback must be an object")
    if feedback.get("format") != exchange.FEEDBACK_FORMAT or feedback.get("version") != exchange.FEEDBACK_VERSION:
        raise FullMaterialCapabilityError(f"expected {exchange.FEEDBACK_FORMAT}/{exchange.FEEDBACK_VERSION}")
    if feedback.get("packId") != pack["id"] or feedback.get("packFingerprint") != pack["fingerprint"]:
        raise FullMaterialCapabilityError("feedback capability-pack linkage mismatch")
    if feedback.get("consumer") != CONSUMER:
        raise FullMaterialCapabilityError("feedback consumer identity mismatch")
    events = feedback.get("events")
    if not isinstance(events, list) or not events:
        raise FullMaterialCapabilityError("feedback requires non-empty events")
    capability_ids = {item["id"] for item in pack["capabilities"]}
    normalized: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("capabilityId") not in capability_ids:
            raise FullMaterialCapabilityError(f"feedback event {index} references an unknown capability")
        rebuilt = exchange._event(
            event["capabilityId"],
            str(event.get("action") or ""),
            str(event.get("outcome") or ""),
            evidence=event.get("evidence") if isinstance(event.get("evidence"), dict) else {},
            derived_ids=event.get("derivedIds") if isinstance(event.get("derivedIds"), list) else [],
            note=str(event.get("note") or ""),
        )
        if rebuilt != event:
            raise FullMaterialCapabilityError("feedback event identity/content mismatch", {"index": index})
        normalized.append(copy.deepcopy(event))
    if len({event["id"] for event in normalized}) != len(normalized):
        raise FullMaterialCapabilityError("duplicate feedback event")
    basis = {
        "packId": feedback["packId"],
        "packFingerprint": feedback["packFingerprint"],
        "consumer": feedback["consumer"],
        "events": normalized,
    }
    expected = exchange._fnv1a_js(exchange._stable_json(basis))
    if feedback.get("fingerprint") != expected or feedback.get("id") != f"material-use-feedback-{expected}":
        raise FullMaterialCapabilityError("feedback fingerprint/id mismatch")
    return copy.deepcopy(feedback)


def consume_material_capability_pack_full(raw_pack: Any, *, strict: bool = False) -> dict[str, Any]:
    pack = exchange.validate_material_capability_pack(raw_pack)
    base_result = exchange.consume_material_capability_pack(pack, strict=False)
    base_events = {event["capabilityId"]: event for event in base_result["feedback"]["events"]}

    events: list[dict[str, Any]] = []
    projections: list[dict[str, Any]] = []

    for capability in pack["capabilities"]:
        kind = capability["kind"]
        capability_id = capability["id"]
        if kind in {"material-entry", "material-family"}:
            prior = base_events[capability_id]
            if prior["outcome"] == "PASS" and prior["action"] == "adopted":
                events.append(
                    _feedback_event(
                        capability_id,
                        "adopted",
                        "PASS",
                        evidence={
                            "projection": "validated-asset-atom",
                            "detached": True,
                            "assetAtomValidated": True,
                            "renderingVerified": False,
                        },
                        derived_ids=copy.deepcopy(prior.get("derivedIds") or []),
                        note="Mapped exactly through the existing detached Material Donor -> Asset Atom adapter.",
                    )
                )
            else:
                events.append(
                    _feedback_event(
                        capability_id,
                        "inspected",
                        prior.get("outcome") or "HOLD",
                        evidence={"projection": "material-donor", "detached": True, "priorEvidence": copy.deepcopy(prior.get("evidence") or {})},
                        derived_ids=copy.deepcopy(prior.get("derivedIds") or []),
                        note=prior.get("note") or "Material capability could not be mapped exactly.",
                    )
                )
            continue

        try:
            if kind == "sprite-candidate":
                projection = project_sprite_candidate(capability)
                evidence = {
                    "projectionFormat": SPRITE_SCHEMA,
                    "alphaBoundsPreserved": True,
                    "semanticRecognition": False,
                    "renderingVerified": False,
                }
                note = "Adopted as an exact detached alpha-bounded sprite descriptor."
            elif kind == "recipe":
                projection = project_recipe(capability)
                evidence = {
                    "projectionFormat": RECIPE_SCHEMA,
                    "layers": projection["layerCount"],
                    "transparent": True,
                    "renderingVerified": False,
                }
                note = "Adopted as an exact detached deterministic material-composition recipe."
            elif kind == "pattern":
                projection = project_pattern(capability)
                evidence = {
                    "projectionFormat": PATTERN_SCHEMA,
                    "slots": projection["slotCount"],
                    "support": projection["support"],
                    "recurrenceOnly": True,
                    "autonomousPromotion": False,
                }
                note = "Adopted as an exact detached keeper-derived pattern descriptor."
            else:
                raise FullMaterialCapabilityError(f"unsupported capability kind: {kind}")
            projections.append(projection)
            events.append(
                _feedback_event(
                    capability_id,
                    "adopted",
                    "PASS",
                    evidence=evidence,
                    derived_ids=[projection["id"]],
                    note=note,
                )
            )
        except FullMaterialCapabilityError as exc:
            events.append(
                _feedback_event(
                    capability_id,
                    "inspected",
                    "HOLD",
                    evidence={"detached": True, "reason": str(exc), "details": copy.deepcopy(exc.details)},
                    derived_ids=[],
                    note="Capability stayed HOLD because the bounded detached contract could not be satisfied exactly.",
                )
            )

    feedback = _create_feedback(pack, events)
    validate_full_material_use_feedback(feedback, pack)
    adopted = [event["capabilityId"] for event in events if event["action"] == "adopted" and event["outcome"] == "PASS"]
    held = [event["capabilityId"] for event in events if event["capabilityId"] not in set(adopted)]
    if strict and held:
        raise FullMaterialCapabilityError(
            "strict full material capability intake is on HOLD because some capabilities were not adopted exactly",
            {"held_capability_ids": held, "feedback": feedback},
        )

    return {
        "truth_status": "READY_EXACT_FULL_MATERIAL_CAPABILITY_CONSUMER" if not held else "PARTIAL_EXACT_FULL_MATERIAL_CAPABILITY_CONSUMER_WITH_HOLDS",
        "source": {
            "format": pack["format"],
            "version": pack["version"],
            "pack_id": pack["id"],
            "pack_fingerprint": pack["fingerprint"],
            "producer": copy.deepcopy(pack["producer"]),
        },
        "receipt": {
            "declared_capabilities": len(pack["capabilities"]),
            "adopted_capabilities": len(adopted),
            "held_capabilities": len(held),
            "adopted_capability_ids": adopted,
            "held_capability_ids": held,
            "detached_visual_descriptors": len(projections),
            "live_topology_modified": False,
            "canonical_state_modified": False,
            "rendering_verified": False,
        },
        "asset_package": copy.deepcopy(base_result.get("asset_package")),
        "asset_validation": copy.deepcopy(base_result.get("asset_validation")),
        "detached_visual_capabilities": projections,
        "feedback": feedback,
        "truthBoundary": {
            "adoption": "All PASS events describe bounded detached representations only.",
            "rendering": "Sprite, recipe, and pattern descriptor intake does not prove visual output or runtime installation.",
            "quality": "No PASS event claims aesthetics, semantic understanding, PBR correctness, or physical truth.",
            "authority": "Nothing in this adapter changes live topology, canonical project state, keeper status, or pattern-memory authority automatically.",
        },
    }

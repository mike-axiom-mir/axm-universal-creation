from __future__ import annotations

import copy
import json
from typing import Any

from .material_donor import MaterialDonorError, adapt_material_donor_pack


CAPABILITY_PACK_FORMAT = "axm-material-capability-pack"
CAPABILITY_PACK_VERSION = "0.18.0"
FEEDBACK_FORMAT = "axm-material-use-feedback"
FEEDBACK_VERSION = "0.18.0"
SUPPORTED_KINDS = {
    "material-entry",
    "material-family",
    "sprite-candidate",
    "recipe",
    "pattern",
}
SUPPORTED_ACTIONS = {
    "inspected",
    "validated",
    "rendered",
    "adopted",
    "modified",
    "rejected",
    "reused",
}
SUPPORTED_OUTCOMES = {"PASS", "HOLD", "REJECT"}
MAX_CAPABILITIES = 512
CONSUMER = {
    "system": "AXM Universal Creation",
    "repository": "mike-axiom-mir/axm-universal-creation",
    "adapter": "material-capability-consumer/v0.18.0",
    "instance": None,
}


class MaterialCapabilityError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _stable_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise MaterialCapabilityError("capability exchange state must be deterministic JSON") from exc


def _fnv1a_js(value: Any) -> str:
    """Match the Surface Fabric JS FNV-1a helper exactly for JSON text.

    The producer hashes the low byte of each JavaScript UTF-16 code unit. Encoding
    to UTF-16LE and walking every low byte preserves that behavior for non-ASCII
    strings as well as the normal ASCII contract fixtures.
    """

    encoded = str(value if value is not None else "").encode("utf-16-le", "surrogatepass")
    result = 0x811C9DC5
    for index in range(0, len(encoded), 2):
        result ^= encoded[index]
        result = (result * 0x01000193) & 0xFFFFFFFF
    return f"{result:08x}"


def _text(value: Any, label: str, maximum: int = 4000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaterialCapabilityError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise MaterialCapabilityError(f"{label} exceeds its {maximum}-character bound")
    return result


def _capability_identity(kind: str, source_id: str, payload: Any) -> str:
    basis = {"kind": kind, "sourceId": source_id, "payload": payload}
    return f"cap-{kind}-{_fnv1a_js(_stable_json(basis))}"


def _capability_fingerprint(capability: dict[str, Any]) -> str:
    basis = {
        "kind": capability["kind"],
        "sourceId": capability["sourceId"],
        "payload": capability.get("payload") or {},
        "provenance": capability.get("provenance") or {},
        "refs": capability.get("refs") or {},
    }
    return _fnv1a_js(_stable_json(basis))


def validate_material_capability_pack(raw_pack: Any) -> dict[str, Any]:
    if not isinstance(raw_pack, dict):
        raise MaterialCapabilityError("material capability pack must be an object")
    if raw_pack.get("format") != CAPABILITY_PACK_FORMAT:
        raise MaterialCapabilityError(
            "unsupported material capability pack format",
            {"expected": CAPABILITY_PACK_FORMAT, "observed": raw_pack.get("format")},
        )
    if raw_pack.get("version") != CAPABILITY_PACK_VERSION:
        raise MaterialCapabilityError(
            "unsupported material capability pack version",
            {"expected": CAPABILITY_PACK_VERSION, "observed": raw_pack.get("version")},
        )
    producer = raw_pack.get("producer")
    if not isinstance(producer, dict) or not str(producer.get("system") or "").strip():
        raise MaterialCapabilityError("capability pack producer.system is required")
    capabilities = raw_pack.get("capabilities")
    if not isinstance(capabilities, list) or not 1 <= len(capabilities) <= MAX_CAPABILITIES:
        raise MaterialCapabilityError(f"capability pack must contain 1..{MAX_CAPABILITIES} capabilities")

    ids: set[str] = set()
    for index, capability in enumerate(capabilities):
        if not isinstance(capability, dict):
            raise MaterialCapabilityError(f"capabilities[{index}] must be an object")
        kind = _text(capability.get("kind"), f"capabilities[{index}].kind", 64)
        if kind not in SUPPORTED_KINDS:
            raise MaterialCapabilityError(
                f"unsupported capability kind: {kind}",
                {"index": index, "supported": sorted(SUPPORTED_KINDS)},
            )
        source_id = _text(capability.get("sourceId"), f"capabilities[{index}].sourceId", 512)
        payload = capability.get("payload")
        if not isinstance(payload, dict):
            raise MaterialCapabilityError(f"capabilities[{index}].payload must be an object")
        capability_id = _text(capability.get("id"), f"capabilities[{index}].id", 512)
        if capability_id in ids:
            raise MaterialCapabilityError(f"duplicate capability id: {capability_id}")
        ids.add(capability_id)
        expected_id = _capability_identity(kind, source_id, payload)
        if capability_id != expected_id:
            raise MaterialCapabilityError(
                "capability identity mismatch",
                {"capability_id": capability_id, "expected": expected_id},
            )
        expected_fingerprint = _capability_fingerprint(capability)
        if capability.get("fingerprint") != expected_fingerprint:
            raise MaterialCapabilityError(
                "capability fingerprint mismatch",
                {
                    "capability_id": capability_id,
                    "expected": expected_fingerprint,
                    "observed": capability.get("fingerprint"),
                },
            )

    basis = {
        "producer": producer,
        "capabilities": [
            {"id": capability["id"], "fingerprint": capability["fingerprint"]}
            for capability in capabilities
        ],
    }
    expected_fingerprint = _fnv1a_js(_stable_json(basis))
    expected_id = f"material-capability-pack-{expected_fingerprint}"
    if raw_pack.get("fingerprint") != expected_fingerprint or raw_pack.get("id") != expected_id:
        raise MaterialCapabilityError(
            "capability pack fingerprint/id mismatch",
            {
                "expected_fingerprint": expected_fingerprint,
                "observed_fingerprint": raw_pack.get("fingerprint"),
                "expected_id": expected_id,
                "observed_id": raw_pack.get("id"),
            },
        )
    return copy.deepcopy(raw_pack)


def _synthetic_donor_pack(pack: dict[str, Any]) -> dict[str, Any] | None:
    entries: list[dict[str, Any]] = []
    families: list[dict[str, Any]] = []
    for capability in pack["capabilities"]:
        payload = capability.get("payload") or {}
        if capability["kind"] == "material-entry":
            entries.append(
                {
                    "id": capability["sourceId"],
                    "name": payload.get("name") or capability["sourceId"],
                    "kind": payload.get("kind") or "texture",
                    "mime": payload.get("mime") or "application/octet-stream",
                    "width": payload.get("width") or 0,
                    "height": payload.get("height") or 0,
                    "bytes": payload.get("bytes"),
                    "dataUrl": payload.get("dataUrl"),
                    "payload": copy.deepcopy(payload.get("payload") or {}),
                    "usage": copy.deepcopy(payload.get("usage") or {}),
                    "tags": copy.deepcopy(payload.get("tags") or []),
                    "source": {
                        "method": "axm-material-capability-pack/v0.18.0",
                        "capabilityId": capability["id"],
                        "capabilityFingerprint": capability["fingerprint"],
                        "producer": copy.deepcopy(pack["producer"]),
                        "sourceProvenance": copy.deepcopy(capability.get("provenance") or {}),
                    },
                }
            )
        elif capability["kind"] == "material-family":
            entry_ids = payload.get("entryIds")
            families.append(
                {
                    "id": capability["sourceId"],
                    "name": payload.get("name") or capability["sourceId"],
                    "purpose": payload.get("purpose") or "",
                    "entryIds": copy.deepcopy(entry_ids if isinstance(entry_ids, list) else []),
                    "tags": copy.deepcopy(payload.get("tags") or []),
                }
            )
    if not entries:
        return None
    return {
        "format": "axm-material-donor-pack",
        "version": "0.2.0",
        "id": f"uc-capability-donor-{pack['fingerprint']}",
        "exportedAt": None,
        "purpose": "Detached AXM Universal Creation intake of v0.18 Material / Surface capabilities.",
        "library": {
            "sourceFormat": CAPABILITY_PACK_FORMAT,
            "sourceVersion": CAPABILITY_PACK_VERSION,
            "sourceLibraryId": pack["id"],
            "entries": entries,
            "families": families,
        },
        "assets": copy.deepcopy(entries),
        "workspace": {},
        "layers": [],
        "experiment": None,
        "truthBoundary": {
            "provenance": "Capability IDs/fingerprints remain attached to the synthetic donor entry source metadata.",
            "routing": "Channel meaning comes only from explicit capability usage state; Universal Creation does not infer physical-material semantics.",
            "downstream": "Adaptation creates detached validated Asset Atom state; it does not silently install into live Universal Creation topology.",
        },
    }


def _event(
    capability_id: str,
    action: str,
    outcome: str,
    *,
    evidence: dict[str, Any] | None = None,
    derived_ids: list[str] | None = None,
    note: str = "",
) -> dict[str, Any]:
    normalized_action = action.strip().casefold()
    normalized_outcome = outcome.strip().upper()
    if normalized_action not in SUPPORTED_ACTIONS:
        raise MaterialCapabilityError(f"unsupported feedback action: {normalized_action}")
    if normalized_outcome not in SUPPORTED_OUTCOMES:
        raise MaterialCapabilityError(f"unsupported feedback outcome: {normalized_outcome}")
    normalized_evidence = copy.deepcopy(evidence or {})
    normalized_derived = sorted({str(item).strip() for item in (derived_ids or []) if str(item).strip()})
    normalized_note = str(note or "").strip()
    basis = {
        "capabilityId": capability_id,
        "action": normalized_action,
        "outcome": normalized_outcome,
        "evidence": normalized_evidence,
        "derivedIds": normalized_derived,
        "note": normalized_note,
    }
    return {
        "id": f"use-event-{_fnv1a_js(_stable_json(basis))}",
        **basis,
    }


def _create_feedback(pack: dict[str, Any], events: list[dict[str, Any]]) -> dict[str, Any]:
    if not events:
        raise MaterialCapabilityError("use feedback requires at least one explicit event")
    ids = [event["id"] for event in events]
    if len(ids) != len(set(ids)):
        raise MaterialCapabilityError("duplicate feedback events are not allowed")
    consumer = copy.deepcopy(CONSUMER)
    basis = {
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": consumer,
        "events": events,
    }
    fingerprint = _fnv1a_js(_stable_json(basis))
    return {
        "format": FEEDBACK_FORMAT,
        "version": FEEDBACK_VERSION,
        "id": f"material-use-feedback-{fingerprint}",
        "fingerprint": fingerprint,
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": consumer,
        "events": copy.deepcopy(events),
        "note": "AXM Universal Creation detached material-capability consumption receipt.",
        "truthBoundary": {
            "use": "PASS adopted means Universal Creation created validated detached Asset Atom state from the named capability; it does not prove visual or physical quality.",
            "adoption": "Detached adoption is not live-topology installation, automatic canonical promotion, or authority over Material / Surface Fabric.",
            "rejection": "Unsupported or unusable capability state remains explicit HOLD/REJECT evidence.",
            "privacy": "Feedback contains only adapter evidence derived from the supplied capability pack.",
        },
    }


def validate_material_use_feedback(feedback: Any, raw_pack: Any) -> dict[str, Any]:
    pack = validate_material_capability_pack(raw_pack)
    if not isinstance(feedback, dict):
        raise MaterialCapabilityError("material use feedback must be an object")
    if feedback.get("format") != FEEDBACK_FORMAT or feedback.get("version") != FEEDBACK_VERSION:
        raise MaterialCapabilityError(f"expected {FEEDBACK_FORMAT}/{FEEDBACK_VERSION}")
    if feedback.get("packId") != pack["id"] or feedback.get("packFingerprint") != pack["fingerprint"]:
        raise MaterialCapabilityError("feedback capability-pack linkage mismatch")
    if feedback.get("consumer") != CONSUMER:
        raise MaterialCapabilityError("feedback consumer identity mismatch")
    events = feedback.get("events")
    if not isinstance(events, list) or not events:
        raise MaterialCapabilityError("feedback requires non-empty events")
    capability_ids = {item["id"] for item in pack["capabilities"]}
    normalized_events: list[dict[str, Any]] = []
    for index, raw_event in enumerate(events):
        if not isinstance(raw_event, dict):
            raise MaterialCapabilityError(f"feedback event {index} must be an object")
        capability_id = _text(raw_event.get("capabilityId"), f"events[{index}].capabilityId", 512)
        if capability_id not in capability_ids:
            raise MaterialCapabilityError(f"feedback references unknown capability: {capability_id}")
        normalized = _event(
            capability_id,
            _text(raw_event.get("action"), f"events[{index}].action", 64),
            _text(raw_event.get("outcome"), f"events[{index}].outcome", 64),
            evidence=raw_event.get("evidence") if isinstance(raw_event.get("evidence"), dict) else {},
            derived_ids=raw_event.get("derivedIds") if isinstance(raw_event.get("derivedIds"), list) else [],
            note=str(raw_event.get("note") or ""),
        )
        if normalized["id"] != raw_event.get("id"):
            raise MaterialCapabilityError("feedback event identity mismatch", {"index": index})
        normalized_events.append(copy.deepcopy(raw_event))
    if len({event["id"] for event in normalized_events}) != len(normalized_events):
        raise MaterialCapabilityError("duplicate feedback event id")
    basis = {
        "packId": feedback["packId"],
        "packFingerprint": feedback["packFingerprint"],
        "consumer": feedback["consumer"],
        "events": normalized_events,
    }
    expected = _fnv1a_js(_stable_json(basis))
    if feedback.get("fingerprint") != expected or feedback.get("id") != f"material-use-feedback-{expected}":
        raise MaterialCapabilityError("feedback fingerprint/id mismatch")
    return copy.deepcopy(feedback)


def consume_material_capability_pack(raw_pack: Any, *, strict: bool = False) -> dict[str, Any]:
    pack = validate_material_capability_pack(raw_pack)
    capabilities = pack["capabilities"]
    capability_by_source = {
        (capability["kind"], capability["sourceId"]): capability
        for capability in capabilities
    }

    donor_pack = _synthetic_donor_pack(pack)
    material_result: dict[str, Any] | None = None
    material_error: MaterialDonorError | None = None
    if donor_pack is not None:
        try:
            material_result = adapt_material_donor_pack(donor_pack, strict=False)
        except MaterialDonorError as exc:
            material_error = exc

    accepted_entry_atoms: dict[str, str] = {}
    accepted_family_atoms: dict[str, str] = {}
    entry_holds: dict[str, Any] = {}
    family_holds: dict[str, Any] = {}
    if material_result is not None:
        accepted_entry_atoms = {
            item["entry_id"]: item["texture_atom"]
            for item in material_result.get("accepted_entries", [])
        }
        accepted_family_atoms = {
            item["family_id"]: item["material_atom"]
            for item in material_result.get("accepted_families", [])
        }
        for hold in material_result.get("receipt", {}).get("held_entries", []):
            key = str(hold.get("entry_id") or f"index:{hold.get('index')}")
            entry_holds[key] = copy.deepcopy(hold)
        for hold in material_result.get("receipt", {}).get("held_families", []):
            key = str(hold.get("family_id") or f"index:{hold.get('index')}")
            family_holds[key] = copy.deepcopy(hold)
    elif material_error is not None:
        details = material_error.details or {}
        for hold in details.get("held_entries", []):
            key = str(hold.get("entry_id") or f"index:{hold.get('index')}")
            entry_holds[key] = copy.deepcopy(hold)
        for hold in details.get("held_families", []):
            key = str(hold.get("family_id") or f"index:{hold.get('index')}")
            family_holds[key] = copy.deepcopy(hold)

    events: list[dict[str, Any]] = []
    adopted_capability_ids: list[str] = []
    held_capability_ids: list[str] = []
    for capability in capabilities:
        kind = capability["kind"]
        source_id = capability["sourceId"]
        if kind == "material-entry" and source_id in accepted_entry_atoms:
            atom_id = accepted_entry_atoms[source_id]
            events.append(
                _event(
                    capability["id"],
                    "adopted",
                    "PASS",
                    evidence={
                        "adapter": CONSUMER["adapter"],
                        "consumerPath": "detached-asset-atom-adapter",
                        "resourceBytesVerified": "data-url-decode-and-sha256-only",
                        "channelSource": "explicit-capability-usage-hint",
                        "canonicalInstallation": False,
                    },
                    derived_ids=[atom_id],
                    note="Material entry adapted into validated detached Asset Atom texture state.",
                )
            )
            adopted_capability_ids.append(capability["id"])
        elif kind == "material-family" and source_id in accepted_family_atoms:
            atom_id = accepted_family_atoms[source_id]
            accepted_family = next(
                (item for item in material_result.get("accepted_families", []) if item["family_id"] == source_id),
                {},
            )
            events.append(
                _event(
                    capability["id"],
                    "adopted",
                    "PASS",
                    evidence={
                        "adapter": CONSUMER["adapter"],
                        "consumerPath": "detached-asset-atom-adapter",
                        "textureBindings": copy.deepcopy(accepted_family.get("texture_bindings") or {}),
                        "canonicalInstallation": False,
                    },
                    derived_ids=[atom_id],
                    note="Material family adapted into validated detached Asset Atom material state.",
                )
            )
            adopted_capability_ids.append(capability["id"])
        elif kind in {"material-entry", "material-family"}:
            hold = (entry_holds if kind == "material-entry" else family_holds).get(source_id)
            reason = (
                str(hold.get("reason"))
                if isinstance(hold, dict) and hold.get("reason")
                else str(material_error or "material capability could not be mapped exactly")
            )
            events.append(
                _event(
                    capability["id"],
                    "validated",
                    "HOLD",
                    evidence={
                        "adapter": CONSUMER["adapter"],
                        "reason": reason,
                        "canonicalInstallation": False,
                    },
                    note="Material capability remains on HOLD; no guessed adoption was performed.",
                )
            )
            held_capability_ids.append(capability["id"])
        else:
            events.append(
                _event(
                    capability["id"],
                    "inspected",
                    "HOLD",
                    evidence={
                        "adapter": CONSUMER["adapter"],
                        "reason": f"{kind} has no bounded Universal Creation adoption path in this first v0.18 adapter",
                        "canonicalInstallation": False,
                    },
                    note="Capability was preserved as explicit HOLD instead of being silently reinterpreted.",
                )
            )
            held_capability_ids.append(capability["id"])

    feedback = _create_feedback(pack, events)
    validate_material_use_feedback(feedback, pack)

    holds_exist = bool(held_capability_ids)
    if strict and holds_exist:
        raise MaterialCapabilityError(
            "strict material capability intake is on HOLD because some capabilities were not adopted exactly",
            {
                "adopted_capability_ids": adopted_capability_ids,
                "held_capability_ids": held_capability_ids,
                "feedback": feedback,
            },
        )

    return {
        "truth_status": (
            "READY_EXACT_MATERIAL_CAPABILITY_CONSUMER_FEEDBACK"
            if not holds_exist
            else "PARTIAL_EXACT_MATERIAL_CAPABILITY_CONSUMER_WITH_HOLDS"
        ),
        "source": {
            "format": CAPABILITY_PACK_FORMAT,
            "version": CAPABILITY_PACK_VERSION,
            "pack_id": pack["id"],
            "pack_fingerprint": pack["fingerprint"],
            "producer": copy.deepcopy(pack["producer"]),
        },
        "receipt": {
            "declared_capabilities": len(capabilities),
            "adopted_capabilities": len(adopted_capability_ids),
            "held_capabilities": len(held_capability_ids),
            "adopted_capability_ids": adopted_capability_ids,
            "held_capability_ids": held_capability_ids,
            "live_topology_modified": False,
            "canonical_state_modified": False,
        },
        "material_adapter": copy.deepcopy(material_result),
        "asset_package": copy.deepcopy(material_result.get("asset_package")) if material_result else None,
        "feedback": feedback,
        "truth_boundary": [
            "The consumer validates exact v0.18 capability identity/fingerprints before use.",
            "PASS adopted means a material capability produced validated detached Asset Atom state; it does not mean live installation, beauty, PBR correctness, or physical truth.",
            "Recipe, pattern, and sprite capabilities remain HOLD until Universal Creation has a bounded native consumer path for them.",
            "Feedback is evidence for Material / Surface Fabric and cannot auto-promote either repository's canonical state.",
        ],
    }

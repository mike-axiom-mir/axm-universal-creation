from __future__ import annotations

import base64
import binascii
import copy
import hashlib
import json
import re
from typing import Any
from urllib.parse import unquote_to_bytes

from .asset_atoms import AssetAtomError, validate_asset_package


DONOR_FORMAT = "axm-material-donor-pack"
DONOR_VERSION = "0.2.0"
MAX_ENTRIES = 128
MAX_FAMILIES = 128
MAX_DATA_URL_CHARS = 16_000_000
SUPPORTED_CHANNELS = {
    "base-color",
    "normal",
    "roughness",
    "metallic",
    "ambient-occlusion",
    "height",
    "displacement",
    "emissive",
    "opacity",
    "color-mask",
    "decal",
    "microdetail",
}
DATA_URL_RE = re.compile(r"^data:([^;,]+)(;base64)?,(.*)$", re.DOTALL | re.IGNORECASE)


class MaterialDonorError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise MaterialDonorError("material donor pack must contain deterministic JSON data") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MaterialDonorError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise MaterialDonorError(f"{label} exceeds its {maximum}-character bound")
    return result


def _safe_atom_id(prefix: str, value: Any) -> str:
    source = str(value or "").strip()
    clean = re.sub(r"[^A-Za-z0-9_.:-]+", "-", source).strip("-.:_")
    if not clean:
        clean = hashlib.sha256(source.encode("utf-8")).hexdigest()[:16]
    result = f"{prefix}-{clean}"
    if not result[0].isalpha():
        result = f"x-{result}"
    return result[:128].rstrip("-.:_")


def _decode_data_url(value: Any, *, entry_id: str) -> tuple[str, bytes]:
    data_url = _text(value, f"entry {entry_id} dataUrl", MAX_DATA_URL_CHARS)
    match = DATA_URL_RE.fullmatch(data_url)
    if match is None:
        raise MaterialDonorError(
            "material donor entry payload must be a data URL",
            {"entry_id": entry_id},
        )
    mime = match.group(1).strip().casefold()
    payload = match.group(3)
    try:
        if match.group(2):
            raw = base64.b64decode(payload, validate=True)
        else:
            raw = unquote_to_bytes(payload)
    except (binascii.Error, ValueError) as exc:
        raise MaterialDonorError(
            "material donor entry data URL payload could not be decoded",
            {"entry_id": entry_id},
        ) from exc
    if not raw:
        raise MaterialDonorError(
            "material donor entry payload is empty",
            {"entry_id": entry_id},
        )
    return mime, raw


def _color_space(channel: str) -> str:
    if channel == "normal":
        return "normal-data"
    if channel in {
        "roughness",
        "metallic",
        "ambient-occlusion",
        "height",
        "displacement",
        "opacity",
        "color-mask",
    }:
        return "scalar-data"
    return "srgb"


def _entry_channel(entry: dict[str, Any]) -> str:
    usage = entry.get("usage")
    if not isinstance(usage, dict):
        return "unassigned"
    channel = str(usage.get("channelHint", "unassigned")).strip().casefold().replace("_", "-")
    return channel if channel in SUPPORTED_CHANNELS else "unassigned"


def _validate_pack(raw_pack: Any) -> dict[str, Any]:
    if not isinstance(raw_pack, dict):
        raise MaterialDonorError("material donor pack must be an object")
    if raw_pack.get("format") != DONOR_FORMAT:
        raise MaterialDonorError(
            "unsupported material donor format",
            {"expected": DONOR_FORMAT, "observed": raw_pack.get("format")},
        )
    if raw_pack.get("version") != DONOR_VERSION:
        raise MaterialDonorError(
            "unsupported material donor version",
            {"expected": DONOR_VERSION, "observed": raw_pack.get("version")},
        )
    library = raw_pack.get("library")
    if not isinstance(library, dict):
        raise MaterialDonorError("material donor v0.2 pack is missing its library object")
    entries = library.get("entries")
    families = library.get("families")
    if not isinstance(entries, list) or not 1 <= len(entries) <= MAX_ENTRIES:
        raise MaterialDonorError(f"material donor entries must contain 1..{MAX_ENTRIES} items")
    if not isinstance(families, list) or len(families) > MAX_FAMILIES:
        raise MaterialDonorError(f"material donor families must contain 0..{MAX_FAMILIES} items")
    return copy.deepcopy(raw_pack)


def adapt_material_donor_pack(raw_pack: Any, *, strict: bool = False) -> dict[str, Any]:
    pack = _validate_pack(raw_pack)
    pack_id = str(pack.get("id") or f"donor-{_digest(pack)[:16]}")
    entries = pack["library"]["entries"]
    families = pack["library"]["families"]

    atoms: list[dict[str, Any]] = []
    texture_atom_by_entry: dict[str, str] = {}
    accepted_entries: list[dict[str, Any]] = []
    held_entries: list[dict[str, Any]] = []

    seen_entry_ids: set[str] = set()
    for index, raw_entry in enumerate(entries):
        if not isinstance(raw_entry, dict):
            held_entries.append({"index": index, "reason": "entry is not an object"})
            continue
        try:
            entry_id = _text(raw_entry.get("id"), f"entries[{index}].id", 128)
        except MaterialDonorError as exc:
            held_entries.append({"index": index, "reason": str(exc)})
            continue
        if entry_id in seen_entry_ids:
            held_entries.append({"entry_id": entry_id, "reason": "duplicate entry id"})
            continue
        seen_entry_ids.add(entry_id)

        channel = _entry_channel(raw_entry)
        if channel == "unassigned":
            held_entries.append({
                "entry_id": entry_id,
                "reason": "entry has no supported explicit channel hint",
                "observed_hint": raw_entry.get("usage", {}).get("channelHint") if isinstance(raw_entry.get("usage"), dict) else None,
            })
            continue
        try:
            data_mime, payload_bytes = _decode_data_url(raw_entry.get("dataUrl"), entry_id=entry_id)
            declared_mime = str(raw_entry.get("mime") or data_mime).strip().casefold()
            if declared_mime != data_mime:
                raise MaterialDonorError(
                    "entry MIME does not match data URL MIME",
                    {"entry_id": entry_id, "declared_mime": declared_mime, "data_url_mime": data_mime},
                )
        except MaterialDonorError as exc:
            held_entries.append({"entry_id": entry_id, "reason": str(exc), "details": exc.details})
            continue

        digest = hashlib.sha256(payload_bytes).hexdigest()
        texture_atom_id = _safe_atom_id("texture", entry_id)
        if texture_atom_id in {atom["id"] for atom in atoms}:
            held_entries.append({"entry_id": entry_id, "reason": "normalized texture atom id collision"})
            continue
        purpose_name = str(raw_entry.get("name") or entry_id).strip()[:160]
        atoms.append(
            {
                "id": texture_atom_id,
                "kind": "texture",
                "purpose": f"Material donor texture: {purpose_name}",
                "uses": [],
                "payload": {
                    "channel": channel,
                    "resource": {
                        "uri": f"donor://{_safe_atom_id('pack', pack_id)}/{texture_atom_id}",
                        "mime_type": declared_mime,
                        "digest": f"sha256:{digest}",
                        "color_space": _color_space(channel),
                    },
                    "uv_set": 0,
                    "tiling": [1, 1],
                    "offset": [0, 0],
                    "strength": 1,
                },
            }
        )
        texture_atom_by_entry[entry_id] = texture_atom_id
        accepted_entries.append(
            {
                "entry_id": entry_id,
                "texture_atom": texture_atom_id,
                "channel": channel,
                "mime_type": declared_mime,
                "decoded_bytes": len(payload_bytes),
                "sha256": digest,
                "source": copy.deepcopy(raw_entry.get("source") or {}),
            }
        )

    if not accepted_entries:
        raise MaterialDonorError(
            "material donor pack has no entries that can be adapted without guessing",
            {"held_entries": held_entries},
        )

    accepted_families: list[dict[str, Any]] = []
    held_families: list[dict[str, Any]] = []
    texture_ids_used_by_materials: set[str] = set()
    seen_family_ids: set[str] = set()

    for index, raw_family in enumerate(families):
        if not isinstance(raw_family, dict):
            held_families.append({"index": index, "reason": "family is not an object"})
            continue
        family_id = str(raw_family.get("id") or f"family-{index + 1}").strip()
        if family_id in seen_family_ids:
            held_families.append({"family_id": family_id, "reason": "duplicate family id"})
            continue
        seen_family_ids.add(family_id)
        member_ids = raw_family.get("entryIds")
        if not isinstance(member_ids, list) or not member_ids:
            held_families.append({"family_id": family_id, "reason": "family has no entryIds"})
            continue

        bindings: dict[str, str] = {}
        missing_members: list[str] = []
        duplicate_channels: list[str] = []
        used_texture_ids: list[str] = []
        for member in member_ids:
            entry_id = str(member)
            texture_id = texture_atom_by_entry.get(entry_id)
            if texture_id is None:
                missing_members.append(entry_id)
                continue
            accepted = next(item for item in accepted_entries if item["entry_id"] == entry_id)
            channel = accepted["channel"]
            if channel in bindings:
                duplicate_channels.append(channel)
                continue
            bindings[channel] = texture_id
            used_texture_ids.append(texture_id)

        if missing_members or duplicate_channels or not bindings:
            held_families.append(
                {
                    "family_id": family_id,
                    "reason": "family cannot be mapped exactly to one texture per supported channel",
                    "missing_or_held_members": sorted(set(missing_members)),
                    "duplicate_channels": sorted(set(duplicate_channels)),
                }
            )
            continue

        material_atom_id = _safe_atom_id("material", family_id)
        if material_atom_id in {atom["id"] for atom in atoms}:
            held_families.append({"family_id": family_id, "reason": "normalized material atom id collision"})
            continue
        uses = sorted(set(used_texture_ids))
        atoms.append(
            {
                "id": material_atom_id,
                "kind": "material",
                "purpose": f"Material donor family: {str(raw_family.get('name') or family_id).strip()[:160]}",
                "uses": uses,
                "payload": {
                    "scalars": {},
                    "colors": {},
                    "texture_bindings": dict(sorted(bindings.items())),
                    "masks": [],
                    "overlays": [],
                },
            }
        )
        texture_ids_used_by_materials.update(uses)
        accepted_families.append(
            {
                "family_id": family_id,
                "material_atom": material_atom_id,
                "entry_ids": [str(item) for item in member_ids],
                "texture_bindings": dict(sorted(bindings.items())),
            }
        )

    root_atoms = [item["material_atom"] for item in accepted_families]
    root_atoms.extend(
        item["texture_atom"]
        for item in accepted_entries
        if item["texture_atom"] not in texture_ids_used_by_materials
    )
    root_atoms = sorted(set(root_atoms))

    package = {
        "schema": "axm.asset-atom-package/v0.1",
        "id": f"axm.material-donor.{_digest({'pack_id': pack_id, 'entries': accepted_entries, 'families': accepted_families})[:20]}",
        "version": "0.1.0",
        "asset_class": "material.library",
        "root_atoms": root_atoms,
        "atoms": atoms,
    }

    try:
        normalized = validate_asset_package(package)
    except AssetAtomError as exc:
        raise MaterialDonorError(
            "adapted material donor package failed the existing Asset Atom validator",
            {"asset_atom_error": str(exc), "asset_atom_details": exc.details},
        ) from exc

    holds_exist = bool(held_entries or held_families)
    if strict and holds_exist:
        raise MaterialDonorError(
            "strict material donor adaptation is on HOLD because some donor state could not be mapped exactly",
            {"held_entries": held_entries, "held_families": held_families},
        )

    return {
        "truth_status": "READY_EXACT_MATERIAL_DONOR_ADAPTER" if not holds_exist else "PARTIAL_EXACT_MATERIAL_DONOR_ADAPTER_WITH_HOLDS",
        "source": {
            "format": DONOR_FORMAT,
            "version": DONOR_VERSION,
            "pack_id": pack_id,
            "exported_at": pack.get("exportedAt"),
            "source_library_id": pack.get("library", {}).get("sourceLibraryId"),
        },
        "receipt": {
            "declared_entries": len(entries),
            "accepted_entries": len(accepted_entries),
            "held_entries": held_entries,
            "declared_families": len(families),
            "accepted_families": len(accepted_families),
            "held_families": held_families,
            "resource_bytes_verified": "data-url-decode-and-sha256-only",
            "rendering_verified": False,
            "physical_material_correctness_verified": False,
        },
        "accepted_entries": accepted_entries,
        "accepted_families": accepted_families,
        "asset_package": {key: value for key, value in normalized.items() if key != "validation"},
        "asset_validation": normalized["validation"],
        "truth_boundary": {
            "channel_mapping": "Uses only donor-pack channelHint values already explicit in the source pack; no semantic material recognition is performed.",
            "resource_uri": "Asset Atom resources use donor:// descriptors plus SHA-256 evidence; this adapter does not install or render donor bytes.",
            "families": "A donor family becomes a material atom only when every accepted member maps to one unique supported texture channel.",
            "holds": "Unassigned, undecodable, conflicting, or otherwise unmappable donor state remains visible instead of being silently discarded.",
        },
    }

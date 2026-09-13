from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.material_donor import (  # noqa: E402
    DONOR_FORMAT,
    DONOR_VERSION,
    MaterialDonorError,
    adapt_material_donor_pack,
)

SCHEMA = "axm.universal-creation.material-donor-invariant-receipt/v1"
DEFAULT_FIXTURE = ROOT / "fixtures" / "material-donor-invariant-probe-v1.json"


def _load_fixture(path: Path) -> tuple[dict[str, Any], str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8"))
    if not isinstance(value, dict):
        raise ValueError("material donor invariant probe fixture must be a JSON object")
    return value, hashlib.sha256(raw).hexdigest()


def _accepted_summary(result: dict[str, Any]) -> list[dict[str, Any]]:
    return sorted(
        [
            {
                "entryId": item.get("entry_id"),
                "channel": item.get("channel"),
                "source": copy.deepcopy(item.get("source")),
            }
            for item in result.get("accepted_entries", [])
            if isinstance(item, dict)
        ],
        key=lambda item: str(item.get("entryId")),
    )


def build_receipt(fixture_path: Path = DEFAULT_FIXTURE) -> dict[str, Any]:
    pack, fixture_sha256 = _load_fixture(fixture_path)

    complete = adapt_material_donor_pack(pack, strict=True)

    unassigned_pack = copy.deepcopy(pack)
    probe = copy.deepcopy(unassigned_pack["library"]["entries"][0])
    probe["id"] = "probe-unassigned"
    probe["name"] = "probe-unassigned.png"
    probe["usage"] = {
        "channelHint": "unassigned",
        "channelBasis": "operator-declared",
    }
    unassigned_pack["library"]["entries"].append(probe)
    unassigned = adapt_material_donor_pack(unassigned_pack, strict=False)
    strict_rejected = False
    try:
        adapt_material_donor_pack(unassigned_pack, strict=True)
    except MaterialDonorError:
        strict_rejected = True

    family_pack = copy.deepcopy(pack)
    duplicate = copy.deepcopy(family_pack["library"]["entries"][0])
    duplicate["id"] = "probe-base-duplicate"
    duplicate["name"] = "probe-base-duplicate.png"
    family_pack["library"]["entries"].append(duplicate)
    family_pack["library"]["families"][0]["entryIds"].append(duplicate["id"])
    family_conflict = adapt_material_donor_pack(family_pack, strict=False)

    unsupported_pack = copy.deepcopy(pack)
    unsupported_pack["version"] = "0.1.0"
    unsupported_rejected = False
    unsupported_message = None
    try:
        adapt_material_donor_pack(unsupported_pack, strict=False)
    except MaterialDonorError as exc:
        unsupported_rejected = True
        unsupported_message = str(exc)

    return {
        "schema": SCHEMA,
        "producer": {
            "repository": "mike-axiom-mir/axm-universal-creation",
            "tool": "tools/material_donor_invariant_receipt.py",
            "fixture": str(fixture_path.relative_to(ROOT)).replace("\\", "/"),
            "fixtureSha256": fixture_sha256,
            "adapterFormat": DONOR_FORMAT,
            "adapterVersion": DONOR_VERSION,
        },
        "observations": {
            "complete": {
                "truthStatus": complete.get("truth_status"),
                "source": copy.deepcopy(complete.get("source")),
                "acceptedEntries": _accepted_summary(complete),
                "heldEntryCount": len(complete.get("receipt", {}).get("held_entries", [])),
                "heldFamilyCount": len(complete.get("receipt", {}).get("held_families", [])),
                "renderingVerified": complete.get("receipt", {}).get("rendering_verified"),
            },
            "unassigned": {
                "truthStatus": unassigned.get("truth_status"),
                "acceptedEntries": _accepted_summary(unassigned),
                "heldEntries": copy.deepcopy(unassigned.get("receipt", {}).get("held_entries", [])),
                "strictRejected": strict_rejected,
            },
            "familyConflict": {
                "truthStatus": family_conflict.get("truth_status"),
                "acceptedEntries": _accepted_summary(family_conflict),
                "acceptedFamilyCount": len(family_conflict.get("accepted_families", [])),
                "heldFamilies": copy.deepcopy(family_conflict.get("receipt", {}).get("held_families", [])),
            },
            "unsupportedVersion": {
                "rejected": unsupported_rejected,
                "message": unsupported_message,
            },
        },
        "authority": {
            "mayExecute": False,
            "mayMerge": False,
            "mayPromote": False,
            "mayDeclareCanon": False,
        },
        "truthBoundary": {
            "claim": "Executable donor-owned observations for the exact material-donor adapter and bounded probe fixture.",
            "notProven": [
                "authorship",
                "image semantic correctness",
                "PBR correctness",
                "rendering",
                "deployment",
                "constitutional authority",
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Emit a bounded donor-owned INV-10 evidence receipt.")
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    receipt = build_receipt(args.fixture.resolve())
    sys.stdout.write(json.dumps(receipt, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any


CATALOG_NAMES = ("axis-catalog.json", "direction-catalog.json")
EXPECTED_DIRECTION_SCHEMA = "axm.code.software-direction-catalog.v1"
EXPECTED_AXIS_SCHEMA = "axm.code.software-direction-axis-catalog.v1"


def _regular_json(path: Path) -> Any:
    if path.is_symlink():
        raise ValueError(f"catalog source must not be a symlink: {path}")
    if not path.is_file():
        raise ValueError(f"catalog source is missing or not a regular file: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def _semantic_digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def verify_donor(consumer_root: Path, provider_root: Path, provider_revision: str) -> dict[str, Any]:
    consumer_root = Path(consumer_root).resolve()
    provider_root = Path(provider_root).resolve()
    consumer_dir = consumer_root / "reference" / "software-directions"
    provider_dir = provider_root / "software-directions"

    comparisons: list[dict[str, Any]] = []
    mismatched: list[str] = []
    loaded: dict[str, tuple[Any, Any]] = {}
    for name in CATALOG_NAMES:
        consumer = _regular_json(consumer_dir / name)
        provider = _regular_json(provider_dir / name)
        loaded[name] = (consumer, provider)
        same = consumer == provider
        if not same:
            mismatched.append(name)
        comparisons.append({
            "catalog": name,
            "semantic_equal": same,
            "consumer_sha256": _semantic_digest(consumer),
            "provider_sha256": _semantic_digest(provider),
        })

    consumer_axes, provider_axes = loaded["axis-catalog.json"]
    consumer_directions, provider_directions = loaded["direction-catalog.json"]
    if consumer_axes.get("schema") != EXPECTED_AXIS_SCHEMA or provider_axes.get("schema") != EXPECTED_AXIS_SCHEMA:
        raise ValueError("unexpected software direction axis catalog schema")
    if consumer_directions.get("schema") != EXPECTED_DIRECTION_SCHEMA or provider_directions.get("schema") != EXPECTED_DIRECTION_SCHEMA:
        raise ValueError("unexpected software direction catalog schema")
    if consumer_directions.get("status") != "TEST" or provider_directions.get("status") != "TEST":
        raise ValueError("software direction donor verification only admits TEST catalogs")

    consumer_profiles = consumer_directions.get("profiles")
    provider_profiles = provider_directions.get("profiles")
    if not isinstance(consumer_profiles, list) or not isinstance(provider_profiles, list):
        raise ValueError("software direction profiles must be arrays")
    consumer_ids = [str(profile.get("id", "")) for profile in consumer_profiles if isinstance(profile, dict)]
    provider_ids = [str(profile.get("id", "")) for profile in provider_profiles if isinstance(profile, dict)]
    if len(consumer_ids) != 29 or len(set(consumer_ids)) != 29:
        raise ValueError("consumer software direction catalog must contain 29 unique profiles")
    if len(provider_ids) != 29 or len(set(provider_ids)) != 29:
        raise ValueError("provider software direction catalog must contain 29 unique profiles")

    parity = not mismatched and consumer_ids == provider_ids
    return {
        "schema": "axm.universal-creation.software-direction-donor-verification/v1",
        "passed": parity,
        "catalog_parity": parity,
        "consumer": {
            "repository": "mike-axiom-mir/axm-universal-creation",
            "path": "reference/software-directions",
        },
        "provider": {
            "repository": "mike-axiom-mir/axm-102-grammer",
            "revision": str(provider_revision),
            "path": "software-directions",
            "revision_is_caller_pinned_not_authorship_proof": True,
        },
        "profile_count": len(consumer_ids),
        "profile_ids_equal": consumer_ids == provider_ids,
        "catalogs": comparisons,
        "mismatched_catalogs": mismatched,
        "truth_boundary": {
            "semantic_catalog_parity_only": True,
            "byte_identity_required": False,
            "provider_behavior_verified_separately": True,
            "authorship_proven": False,
            "runtime_dependency_created": False,
        },
        "authority": {
            "selection": False,
            "execution": False,
            "admission": False,
            "merge": False,
            "canon": False,
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify Universal Creation's donor-derived software-direction catalogs against an explicit provider checkout."
    )
    parser.add_argument("--provider-root", required=True, type=Path)
    parser.add_argument("--provider-revision", required=True)
    parser.add_argument("--consumer-root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    receipt = verify_donor(args.consumer_root, args.provider_root, args.provider_revision)
    if args.json:
        print(json.dumps(receipt, indent=2, sort_keys=True))
    else:
        status = "PASS" if receipt["passed"] else "HOLD"
        print(f"software direction donor parity: {status}")
        for row in receipt["catalogs"]:
            print(f"- {row['catalog']}: semantic_equal={row['semantic_equal']} consumer={row['consumer_sha256']} provider={row['provider_sha256']}")
    return 0 if receipt["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())

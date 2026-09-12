#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.material_capability_exchange import (  # noqa: E402
    MaterialCapabilityError,
    consume_material_capability_pack,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Consume an AXM Material / Surface Fabric v0.18 capability pack in detached Universal Creation state."
    )
    parser.add_argument("input", type=Path, help="axm-material-capability-pack/v0.18.0 JSON file")
    parser.add_argument("--out", type=Path, help="write complete consumer result JSON")
    parser.add_argument("--feedback-out", type=Path, help="write axm-material-use-feedback/v0.18.0 JSON")
    parser.add_argument("--strict", action="store_true", help="fail if any capability remains HOLD")
    return parser.parse_args()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        raw = json.loads(args.input.read_text(encoding="utf-8"))
        result = consume_material_capability_pack(raw, strict=args.strict)
    except (OSError, json.JSONDecodeError, MaterialCapabilityError) as exc:
        print(json.dumps({"status": "HOLD", "error": str(exc), "details": getattr(exc, "details", {})}, indent=2))
        return 2

    if args.out:
        write_json(args.out, result)
    if args.feedback_out:
        write_json(args.feedback_out, result["feedback"])
    print(json.dumps({
        "truth_status": result["truth_status"],
        "receipt": result["receipt"],
        "feedback_id": result["feedback"]["id"],
        "feedback_fingerprint": result["feedback"]["fingerprint"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

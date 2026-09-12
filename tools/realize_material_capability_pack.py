#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.material_capability_realization import (  # noqa: E402
    MaterialCapabilityRealizationError,
    realize_material_capability_pack,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create a deterministic native Universal Creation SVG from one of every Material Fabric v0.18 capability kind."
    )
    parser.add_argument("input", type=Path, help="axm-material-capability-pack/v0.18.0 JSON file")
    parser.add_argument("output", type=Path, help="target SVG file")
    parser.add_argument("--receipt-out", type=Path, help="write complete realization receipt JSON")
    parser.add_argument("--feedback-out", type=Path, help="write axm-material-use-feedback/v0.18.0 JSON")
    parser.add_argument("--seed", default="native-realization", help="deterministic native realization seed")
    parser.add_argument("--replace", action="store_true", help="overwrite output SVG if it already exists")
    return parser.parse_args()


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    try:
        pack = json.loads(args.input.read_text(encoding="utf-8"))
        result = realize_material_capability_pack(
            pack,
            args.output,
            seed=args.seed,
            replace=args.replace,
        )
    except (OSError, json.JSONDecodeError, MaterialCapabilityRealizationError, FileExistsError) as exc:
        print(json.dumps({"status": "HOLD", "error": str(exc), "details": getattr(exc, "details", {})}, indent=2))
        return 2

    if args.receipt_out:
        write_json(args.receipt_out, result)
    if args.feedback_out:
        write_json(args.feedback_out, result["feedback"])
    print(json.dumps({
        "truth_status": result["truth_status"],
        "creation_id": result["id"],
        "output": result["output"],
        "feedback_id": result["feedback"]["id"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.material_donor import MaterialDonorError, adapt_material_donor_pack


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Validate one axm-material-donor-pack/v0.2 file and adapt its explicit "
            "material routing into the existing AXM Asset Atom texture/material grammar."
        )
    )
    parser.add_argument("pack", type=Path, help="Path to one donor-pack JSON file.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Fail if any donor entry or family remains on HOLD.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        raw = json.loads(args.pack.read_text(encoding="utf-8"))
    except FileNotFoundError:
        print(json.dumps({"truth_status": "HOLD", "error": "donor pack file does not exist", "path": str(args.pack)}, indent=2), file=sys.stderr)
        return 2
    except (OSError, json.JSONDecodeError) as exc:
        print(json.dumps({"truth_status": "HOLD", "error": f"donor pack could not be read as JSON: {exc}", "path": str(args.pack)}, indent=2), file=sys.stderr)
        return 2

    try:
        result = adapt_material_donor_pack(raw, strict=args.strict)
    except MaterialDonorError as exc:
        print(
            json.dumps(
                {
                    "truth_status": "HOLD",
                    "error": str(exc),
                    "details": exc.details,
                    "path": str(args.pack),
                },
                indent=2,
                sort_keys=True,
            ),
            file=sys.stderr,
        )
        return 2

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

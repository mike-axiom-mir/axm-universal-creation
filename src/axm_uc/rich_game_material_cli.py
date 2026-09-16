"""Command-line access to UC's expanded deterministic game-material profiles."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .rich_game_materials import PROFILE_BY_NAME, generate_rich_game_material, rich_game_material_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axm-rich-materials",
        description="AXM expanded deterministic PBR game-material forge",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="show every rich game-material profile and truth boundary")

    create = sub.add_parser("create", help="write one immutable rich PBR material bundle")
    create.add_argument("profile", choices=sorted(PROFILE_BY_NAME))
    create.add_argument("path", help="new output directory; existing paths are never overwritten")
    create.add_argument("--size", type=int, default=256)
    create.add_argument("--seed", type=int, default=1)
    create.add_argument("--color", type=int, nargs=3, metavar=("R", "G", "B"))
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = rich_game_material_catalog()
        else:
            color = tuple(args.color) if args.color is not None else None
            result = generate_rich_game_material(
                Path(args.path), args.profile, size=args.size, seed=args.seed, color=color
            )
    except (FileExistsError, OSError, ValueError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

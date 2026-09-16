"""Command-line access to UC's deterministic rich/layered game materials."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .layered_game_materials import generate_layered_game_material, layered_game_material_catalog
from .rich_game_materials import PROFILE_BY_NAME, generate_rich_game_material, rich_game_material_catalog


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axm-rich-materials",
        description="AXM deterministic PBR game-material forge",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="show every rich base-material profile and truth boundary")
    sub.add_parser("layer-catalog", help="show reusable layer types and truth boundary")

    create = sub.add_parser("create", help="write one immutable rich PBR base-material bundle")
    create.add_argument("profile", choices=sorted(PROFILE_BY_NAME))
    create.add_argument("path", help="new output directory; existing paths are never overwritten")
    create.add_argument("--size", type=int, default=256)
    create.add_argument("--seed", type=int, default=1)
    create.add_argument("--color", type=int, nargs=3, metavar=("R", "G", "B"))

    layered = sub.add_parser("layer-create", help="compose an immutable layered material from a JSON recipe")
    layered.add_argument("recipe", help="JSON recipe with base_profile/layers and optional size/seed/color")
    layered.add_argument("path", help="new output directory; existing paths are never overwritten")
    return parser


def _load_layer_recipe(path: str) -> dict:
    recipe_path = Path(path)
    data = json.loads(recipe_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != "axm.layered-game-material-request/v0.1":
        raise ValueError("unsupported layered material request schema")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        if args.command == "catalog":
            result = rich_game_material_catalog()
        elif args.command == "layer-catalog":
            result = layered_game_material_catalog()
        elif args.command == "create":
            color = tuple(args.color) if args.color is not None else None
            result = generate_rich_game_material(
                Path(args.path), args.profile, size=args.size, seed=args.seed, color=color
            )
        else:
            recipe = _load_layer_recipe(args.recipe)
            raw_color = recipe.get("color")
            color = tuple(raw_color) if raw_color is not None else None
            result = generate_layered_game_material(
                Path(args.path),
                recipe["base_profile"],
                recipe.get("layers", []),
                size=int(recipe.get("size", 256)),
                seed=int(recipe.get("seed", 1)),
                color=color,
            )
    except (FileExistsError, OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        parser.error(str(exc))
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

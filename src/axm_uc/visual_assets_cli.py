from __future__ import annotations

import argparse
import json

from .visual_assets import catalog, generate_asset, generate_kit


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-assets", description="AXM deterministic procedural visual asset forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="show every executable generator family")
    generate = sub.add_parser("generate", help="generate one real asset or material pack")
    generate.add_argument("category", choices=["texture", "gradient", "material", "fixture", "decal", "palette"])
    generate.add_argument("kind")
    generate.add_argument("path")
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--size", type=int, default=256)
    generate.add_argument("--scale", type=float, default=1.0)
    generate.add_argument("--angle", type=float, default=35.0)
    generate.add_argument("--format", choices=["svg", "obj"])
    generate.add_argument("--count", type=int, default=7)
    generate.add_argument("--colors", nargs="+")
    generate.add_argument("--replace", action="store_true")
    kit = sub.add_parser("kit", help="generate a reusable visual asset kit plus provenance manifest")
    kit.add_argument("path")
    kit.add_argument("--profile", choices=["starter", "full"], default="starter")
    kit.add_argument("--seed", type=int, default=0)
    kit.add_argument("--size", type=int, default=96)
    kit.add_argument("--replace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        result = catalog()
    elif args.command == "kit":
        result = generate_kit(args.path, profile=args.profile, seed=args.seed, size=args.size, replace=args.replace)
    else:
        result = generate_asset(category=args.category, kind=args.kind, path=args.path, seed=args.seed, size=args.size, scale=args.scale, angle=args.angle, format=args.format, count=args.count, colors=args.colors, replace=args.replace)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

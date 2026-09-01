from __future__ import annotations

import argparse
import json
from pathlib import Path

from .visual_assets import catalog as base_catalog, generate_asset, generate_kit
from .visual_creation_grammar import compile_visual_recipe, grammar_catalog
from .visual_expanded import expansion_catalog, generate_expanded_asset, generate_expansion_kit
from .visual_state_prompt_atlas import compile_visual_state, visual_state_catalog

BASE_CATEGORIES = ["texture", "gradient", "material", "fixture", "decal", "palette"]
EXPANDED_CATEGORIES = ["surface", "pigment", "sprite", "mesh", "vector-part"]


def combined_catalog() -> dict:
    base = base_catalog()
    expanded = expansion_catalog()
    outputs = dict(base.get("outputs", {}))
    outputs.update(expanded.get("outputs", {}))
    return {
        "schema": "axm.procedural-visual-assets.combined/v0.2",
        "truth_status": "EXECUTABLE_GENERATOR_CATALOG",
        "deterministic": True,
        "dependencies": [],
        "outputs": outputs,
        "visual_grammar": grammar_catalog(),
        "visual_state_atlas": visual_state_catalog(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-assets", description="AXM deterministic procedural visual asset forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="show every executable generator family")
    sub.add_parser("grammar-catalog", help="show the composable visual-intent grammar")
    plan = sub.add_parser("plan", help="compile one structured visual request into a deterministic recipe")
    plan.add_argument("request", help="path to a UTF-8 JSON visual request")

    state_catalog = sub.add_parser("state-catalog", help="show the source-backed 99-command visual state atlas")
    state_catalog.add_argument("--include-aliases", action="store_true")
    state_compile = sub.add_parser(
        "state-compile",
        help="compile visual slash-command shorthand into renderer-neutral state",
    )
    state_compile.add_argument("request", help="path to a UTF-8 JSON visual state request")

    generate = sub.add_parser("generate", help="generate one real asset, material, pigment, sprite, mesh, or vector part")
    generate.add_argument("category", choices=BASE_CATEGORIES + EXPANDED_CATEGORIES)
    generate.add_argument("kind")
    generate.add_argument("path")
    generate.add_argument("--seed", type=int, default=0)
    generate.add_argument("--size", type=int, default=256)
    generate.add_argument("--scale", type=float, default=1.0)
    generate.add_argument("--angle", type=float, default=35.0)
    generate.add_argument("--format", choices=["svg", "obj"])
    generate.add_argument("--count", type=int, default=7)
    generate.add_argument("--colors", nargs="+")
    generate.add_argument("--age", type=float, default=.5)
    generate.add_argument("--damage", type=float, default=.35)
    generate.add_argument("--moisture", type=float, default=.25)
    generate.add_argument("--frame-size", type=int, default=32)
    generate.add_argument("--frames", type=int, default=4)
    generate.add_argument("--columns", type=int)
    generate.add_argument("--replace", action="store_true")

    kit = sub.add_parser("kit", help="generate the original reusable visual asset kit plus provenance manifest")
    kit.add_argument("path")
    kit.add_argument("--profile", choices=["starter", "full"], default="starter")
    kit.add_argument("--seed", type=int, default=0)
    kit.add_argument("--size", type=int, default=96)
    kit.add_argument("--replace", action="store_true")

    ex = sub.add_parser("expansion-kit", help="generate smart pigments, surfaces, sprites, meshes, and vector parts as one kit")
    ex.add_argument("path")
    ex.add_argument("--profile", choices=["starter", "full"], default="starter")
    ex.add_argument("--seed", type=int, default=0)
    ex.add_argument("--size", type=int, default=48)
    ex.add_argument("--replace", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        result = combined_catalog()
    elif args.command == "grammar-catalog":
        result = grammar_catalog()
    elif args.command == "plan":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        result = compile_visual_recipe(request)
    elif args.command == "state-catalog":
        result = visual_state_catalog(include_aliases=args.include_aliases)
    elif args.command == "state-compile":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        result = compile_visual_state(request)
    elif args.command == "kit":
        result = generate_kit(args.path, profile=args.profile, seed=args.seed, size=args.size, replace=args.replace)
    elif args.command == "expansion-kit":
        result = generate_expansion_kit(args.path, profile=args.profile, seed=args.seed, size=args.size, replace=args.replace)
    elif args.category in EXPANDED_CATEGORIES:
        result = generate_expanded_asset(
            category=args.category, kind=args.kind, path=args.path, seed=args.seed, size=args.size,
            scale=args.scale, colors=args.colors, age=args.age, damage=args.damage,
            moisture=args.moisture, frame_size=args.frame_size, frames=args.frames,
            columns=args.columns, replace=args.replace,
        )
    else:
        result = generate_asset(
            category=args.category, kind=args.kind, path=args.path, seed=args.seed,
            size=args.size, scale=args.scale, angle=args.angle, format=args.format,
            count=args.count, colors=args.colors, replace=args.replace,
        )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

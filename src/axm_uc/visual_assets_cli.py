from __future__ import annotations

import argparse
import json
from pathlib import Path

from .visual_assets import catalog as base_catalog, generate_asset, generate_kit
from .visual_creation_grammar import compile_visual_recipe, grammar_catalog
from .visual_expanded import expansion_catalog, generate_expanded_asset, generate_expansion_kit
from .visual_learning import compile_adaptive_visual_recipe, inspect_png, inspect_visual_learning, record_visual_use
from .visual_3d import (
    assess_3d_output,
    catalog_3d,
    compile_3d_request,
    compile_adaptive_3d_request,
    forge_3d_asset,
    inspect_glb,
    record_3d_review,
)

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
        "three_d_forge": catalog_3d(),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-assets", description="AXM deterministic procedural visual asset forge")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="show every executable generator family")
    sub.add_parser("grammar-catalog", help="show the composable visual-intent grammar")
    plan = sub.add_parser("plan", help="compile one structured visual request into a deterministic recipe")
    plan.add_argument("request", help="path to a UTF-8 JSON visual request")
    adaptive = sub.add_parser("plan-adaptive", help="compile a request with exact-context lessons from prior use")
    adaptive.add_argument("request", help="path to a UTF-8 JSON visual request")
    adaptive.add_argument("--state-root", default=".")
    png = sub.add_parser("inspect-png", help="verify PNG structure and real alpha pixels")
    png.add_argument("path")
    learn = sub.add_parser("learn-use", help="record one evidence-bound visual-use observation")
    learn.add_argument("observation", help="path to a UTF-8 JSON observation")
    learn.add_argument("--state-root", default=".")
    learning = sub.add_parser("learning", help="inspect the compact current visual-use profile")
    learning.add_argument("--state-root", default=".")
    learning.add_argument("--context")
    sub.add_parser("3d-catalog", help="show engine-ready 3D forge assets, outputs, and runtime contract")
    plan_3d = sub.add_parser("3d-plan", help="compile a validated engine-ready 3D request")
    plan_3d.add_argument("request", help="path to a UTF-8 JSON 3D request")
    adaptive_3d = sub.add_parser("3d-plan-adaptive", help="replay exact-context lessons into a 3D request")
    adaptive_3d.add_argument("request", help="path to a UTF-8 JSON 3D request")
    adaptive_3d.add_argument("--state-root", default=".")
    review_3d = sub.add_parser("3d-review", help="record one artifact-bound 3D render review")
    review_3d.add_argument("review", help="path to a UTF-8 JSON 3D review")
    review_3d.add_argument("--state-root", default=".")
    assess_3d = sub.add_parser("3d-assess", help="apply technical and artifact-bound visual AAA gates")
    assess_3d.add_argument("receipt")
    assess_3d.add_argument("manifest")
    assess_3d.add_argument("--visual-review")
    inspect_3d = sub.add_parser("inspect-glb", help="decode GLB structure and report meshes, triangles, and materials")
    inspect_3d.add_argument("path")
    forge_3d = sub.add_parser("3d-forge", help="generate LODs, collisions, GLBs, source blend, and render proofs")
    forge_3d.add_argument("request", help="path to a UTF-8 JSON 3D request")
    forge_3d.add_argument("output", help="explicit output directory")
    forge_3d.add_argument("--blender", help="Blender executable; otherwise AXM_BLENDER or PATH")

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
    elif args.command == "plan-adaptive":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        result = compile_adaptive_visual_recipe(args.state_root, request)
    elif args.command == "inspect-png":
        result = inspect_png(args.path)
    elif args.command == "learn-use":
        observation = json.loads(Path(args.observation).read_text(encoding="utf-8"))
        result = record_visual_use(args.state_root, observation)
    elif args.command == "learning":
        result = inspect_visual_learning(args.state_root, context_key=args.context)
    elif args.command == "3d-catalog":
        result = catalog_3d()
    elif args.command == "3d-plan":
        result = compile_3d_request(json.loads(Path(args.request).read_text(encoding="utf-8")))
    elif args.command == "3d-plan-adaptive":
        result = compile_adaptive_3d_request(args.state_root, json.loads(Path(args.request).read_text(encoding="utf-8")))
    elif args.command == "3d-review":
        result = record_3d_review(args.state_root, json.loads(Path(args.review).read_text(encoding="utf-8")))
    elif args.command == "3d-assess":
        review = json.loads(Path(args.visual_review).read_text(encoding="utf-8")) if args.visual_review else None
        result = assess_3d_output(
            json.loads(Path(args.receipt).read_text(encoding="utf-8")),
            json.loads(Path(args.manifest).read_text(encoding="utf-8")),
            review,
        )
    elif args.command == "inspect-glb":
        result = inspect_glb(args.path)
    elif args.command == "3d-forge":
        request = json.loads(Path(args.request).read_text(encoding="utf-8"))
        result = forge_3d_asset(Path.cwd(), request, args.output, blender=args.blender)
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

"""CLI for AXM visual archetypes and whole-product foundations."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from .visual_templates import (catalog, get, digest, screen_project, product_project,
                               install_builtins)


def _print(value) -> None:
    print(json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True))


def _write_project(project: dict, target: Path) -> dict:
    if target.exists():
        raise ValueError("output path already exists")
    files = project.get("files")
    if not isinstance(files, dict) or not files:
        raise ValueError("project files are missing")
    target.mkdir(parents=True)
    written = []
    try:
        for raw_name, body in files.items():
            name = Path(raw_name)
            if name.is_absolute() or ".." in name.parts or not isinstance(body, str):
                raise ValueError("project contains unsafe path/content")
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
            written.append(raw_name)
    except BaseException:
        # Only remove files created in this new target; never touch pre-existing output.
        import shutil
        shutil.rmtree(target, ignore_errors=True)
        raise
    receipt = {
        "schema": "axm.visual-template-write/v1",
        "project_id": project["id"],
        "project_version": project["version"],
        "path": str(target),
        "files": sorted(written),
        "truth": "Deterministic template files written; visual quality, gameplay and interaction were not runtime-tested by this command.",
    }
    (target / "receipt.json").write_text(json.dumps(receipt, indent=2, sort_keys=True), encoding="utf-8")
    return receipt


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-visual-templates", description="AXM visual archetype catalog")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog", help="list built-in primitives, styles, screens and whole products")
    show = sub.add_parser("show", help="show one exact built-in visual template")
    show.add_argument("id")
    render = sub.add_parser("render", help="write an offline SVG/HTML structural preview")
    render.add_argument("id")
    render.add_argument("path")
    render.add_argument("--width", type=int, default=1920)
    render.add_argument("--height", type=int, default=1080)
    render.add_argument("--title")
    install = sub.add_parser("install-registry", help="explicitly install all built-ins into an existing/new Sticker Registry")
    install.add_argument("database")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.command == "catalog":
        _print(catalog())
        return 0
    if args.command == "show":
        template = get(args.id)
        _print({"template": template, "digest": digest(template)})
        return 0
    if args.command == "render":
        template = get(args.id)
        project = product_project(args.id, args.width, args.height, args.title) if template["kind"] == "product" else screen_project(args.id, args.width, args.height, args.title)
        try:
            receipt = _write_project(project, Path(args.path))
        except (ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        _print(receipt)
        return 0
    if args.command == "install-registry":
        from axm_stickers import Registry
        try:
            with Registry(args.database) as registry:
                pins = install_builtins(registry)
        except (ValueError, OSError) as exc:
            raise SystemExit(str(exc)) from exc
        _print({"schema":"axm.visual-template-install/v1","database":args.database,"registered":pins,"count":len(pins)})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

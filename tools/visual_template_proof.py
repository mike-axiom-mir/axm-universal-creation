#!/usr/bin/env python3
"""Produce deterministic evidence for the composed visual-template fabric."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from axm_uc import visual_templates as vt


SIZES=[(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
GAME_PRODUCTS=("game.racing.full","game.coop.action","game.rts.command")


def _write_project(project: dict, target: Path) -> list[str]:
    target.mkdir()
    written=[]
    for name,body in project["files"].items():
        path=target/name
        path.parent.mkdir(parents=True,exist_ok=True)
        path.write_text(body,encoding="utf-8")
        if name.endswith(".svg"):
            ElementTree.fromstring(body)
        written.append(str(path))
    return written


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: python tools/visual_template_proof.py NEW_OUTPUT_DIRECTORY")
    out=Path(argv[1])
    if out.exists():
        raise SystemExit("output path already exists")
    out.mkdir(parents=True)
    try:
        counts=vt.validate_catalog()
        if counts != {"styles":7,"primitives":24,"screens":39,"products":5}:
            raise AssertionError(f"unexpected composed catalog: {counts}")

        evidence=[]
        for product_id in GAME_PRODUCTS:
            expected=vt.get(product_id)
            for width,height in SIZES:
                resolved=vt.product_resolution(product_id,width,height)
                if [row["template"]["id"] for row in resolved["screens"]] != expected["screens"]:
                    raise AssertionError(f"screen order drift: {product_id}")
                for screen in resolved["screens"]:
                    for name,(x,y,w,h) in screen["regions"].items():
                        if min(x,y,w,h) < 0 or x+w > width+1e-6 or y+h > height+1e-6:
                            raise AssertionError(f"out of bounds: {screen['template']['id']} {name}")
                evidence.append({
                    "product":product_id,
                    "viewport":[width,height],
                    "screen_count":len(resolved["screens"]),
                    "flow_edges":len(resolved["flow"]),
                })

        outputs=[]
        galleries=(
            ("game.racing.full",1920,1080,"racing-full","AXM Full Racing Foundation"),
            ("game.coop.action",1280,720,"coop-action","AXM Co-op Action Foundation"),
            ("game.rts.command",1920,1080,"rts-command","AXM RTS Command Foundation"),
        )
        for product_id,width,height,folder,title in galleries:
            outputs.extend(_write_project(vt.product_project(product_id,width,height,title),out/folder))

        mobile=vt.screen_project("product.mobile.home",1080,1920,"AXM Mobile Foundation")
        outputs.extend(_write_project(mobile,out/"mobile-home"))

        racing=vt.get("game.racing.full")
        required={"game.racing.accessibility","game.racing.recovery","game.racing.hud.split","game.racing.tuning","game.racing.replay"}
        if not required <= set(racing["screens"]):
            raise AssertionError("full racing foundation lost required professional surfaces")

        receipt={
            "schema":"axm.visual-template-proof/v2",
            "catalog":counts,
            "composition":vt.CATALOG_COMPOSITION,
            "product_evidence":evidence,
            "galleries":{
                "game.racing.full":{"screens":len(vt.get("game.racing.full")["screens"]),"path":"racing-full/index.html"},
                "game.coop.action":{"screens":len(vt.get("game.coop.action")["screens"]),"path":"coop-action/index.html"},
                "game.rts.command":{"screens":len(vt.get("game.rts.command")["screens"]),"path":"rts-command/index.html"},
            },
            "parsed_svg_count":sum(1 for path in outputs if path.endswith(".svg")),
            "truth":"Offline contract/layout evidence only. SVG/HTML structure was generated and SVG parsed; target-engine interaction, gameplay, typography rendering, accessibility audit and aesthetic acceptance were not observed.",
        }
        (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

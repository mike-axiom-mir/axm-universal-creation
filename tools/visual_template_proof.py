#!/usr/bin/env python3
"""Produce deterministic evidence for the built-in visual-template fabric."""
from __future__ import annotations

import json
from pathlib import Path
import shutil
import sys
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from axm_uc.visual_templates import (catalog, product_project, product_resolution,
                                     screen_project, validate_catalog)


def main(argv: list[str]) -> int:
    if len(argv) != 2:
        raise SystemExit("usage: python tools/visual_template_proof.py NEW_OUTPUT_DIRECTORY")
    out = Path(argv[1])
    if out.exists():
        raise SystemExit("output path already exists")
    out.mkdir(parents=True)
    try:
        sizes = [(640,360),(1080,1920),(1280,720),(1920,1080),(2560,1080),(3840,2160)]
        evidence = []
        for width,height in sizes:
            resolved = product_resolution("game.racing.performance", width, height)
            for screen in resolved["screens"]:
                for name,(x,y,w,h) in screen["regions"].items():
                    if min(x,y,w,h) < 0 or x+w > width+1e-6 or y+h > height+1e-6:
                        raise AssertionError(f"out of bounds: {screen['template']['id']} {name}")
            evidence.append({"viewport":[width,height],"screen_count":len(resolved["screens"]),"flow_edges":len(resolved["flow"])})
        product = product_project("game.racing.performance", 1920, 1080, "AXM Racing Product Foundation")
        gallery = out / "racing-product"
        gallery.mkdir()
        for name,body in product["files"].items():
            path=gallery/name; path.parent.mkdir(parents=True,exist_ok=True); path.write_text(body,encoding="utf-8")
            if name.endswith(".svg"):
                ElementTree.fromstring(body)
        mobile = screen_project("product.mobile.home",1080,1920,"AXM Mobile Foundation")
        mobile_dir=out/"mobile-home"; mobile_dir.mkdir()
        for name,body in mobile["files"].items():
            (mobile_dir/name).write_text(body,encoding="utf-8")
            if name.endswith(".svg"): ElementTree.fromstring(body)
        receipt={
            "schema":"axm.visual-template-proof/v1",
            "catalog":catalog()["counts"],
            "validated":validate_catalog(),
            "racing_product":evidence,
            "outputs":["racing-product/index.html","racing-product/product.json","mobile-home/index.html","mobile-home/screen.svg"],
            "truth":"Offline contract/layout evidence only. SVG/HTML structure was parsed; target-engine interaction, gameplay, typography rendering and aesthetic acceptance were not observed.",
        }
        (out/"receipt.json").write_text(json.dumps(receipt,indent=2,sort_keys=True),encoding="utf-8")
        print(json.dumps(receipt,indent=2,sort_keys=True))
    except BaseException:
        shutil.rmtree(out,ignore_errors=True)
        raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))

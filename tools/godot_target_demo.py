"""Observe the same preserved UC field case and authored rig in real Godot.

Requires AXM_GODOT plus a working graphical display (Xvfb/Mesa is valid on CI).
All input artwork is the original UC fixture published in Run 004.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.godot_target import run_station, observe_station


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    root = args.output.resolve()
    root.mkdir(parents=True, exist_ok=False)
    (root / "creations/sources").mkdir(parents=True)
    source = ROOT / "docs/profession-crew-growth/evidence/product-004"
    results = {}
    for name, asset, options in [
        ("case", "field-service-case.glb", {"width": 640, "height": 480,
            "views": [{"yaw": .57, "elevation": .3}, {"yaw": -2.1, "elevation": .4}]}),
        ("flex", "flex.glb", {"width": 320, "height": 400,
            "views": [{"yaw": .5, "elevation": .3, "clip": "Flex", "time_s": 0},
                      {"yaw": .5, "elevation": .3, "clip": "Flex", "time_s": .5}],
            "playback": {"clip": "Flex", "fps": 24, "frames": 25}}),
    ]:
        shutil.copyfile(source / asset, root / "creations/sources" / asset)
        inputs = {"asset": "creations/sources/" + asset, "path": "creations/" + name, "options": {"engine": "godot", **options}}
        report = run_station(root, "validate-godot-target", inputs)
        fresh = observe_station(root, "validate-godot-target", inputs)
        results[name] = {"status": report["status"], "fresh": fresh, "source_sha256": report["source_sha256"]}
        (root / "verification.json").write_text(json.dumps(results, indent=2) + "\n")
        print(name, report["status"], fresh["status"], flush=True)
        if report["status"] != "PASS" or fresh["status"] != "PASS":
            raise RuntimeError("Target observation failed; retained output contains the evidence")
    print("PASS: actual Godot case and stepped-animation observations; review required", flush=True)


if __name__ == "__main__":
    main()

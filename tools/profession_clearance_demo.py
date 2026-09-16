"""Native UC vehicle -> measured repair -> persistent procedure -> new vehicle.

Uses the existing near-detail RTS recipes without substituting proxy geometry.
The demo deliberately exports static rest-pose assemblies; it does not certify
the original drive animations, steering, mounts or the whole vehicle.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys
import subprocess

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_stickers import Registry, instance
from axm_stickers.assembly import save_assembly
from axm_stickers.core import digest
from axm_stickers.placement import identity
from axm_uc.procedural_3d import build_glb
from axm_uc.rts_detail import dress
from axm_uc.rts_foundry import catalog
from axm_uc.rts_mesh import SalvageMesh
from axm_uc.rts_recipes import vehicle
from axm_uc.software_glb_preview import render_glb_preview
from axm_uc.sticker_adapter import register_glb


class MeasurableVehicle(SalvageMesh):
    def face(self, mat, verts, tag, weather=True):
        # Group the existing chassis faces separately. Same recipe, coordinates,
        # normals, colours and triangles; no simplified collision substitute.
        previous = self.active
        if tag == "chassis" and previous == "body":
            self.active = "chassis"
        try:
            super().face(mat, verts, tag, weather)
        finally:
            self.active = previous


def cold_worker(machine, request):
    program = ("import json,sys; from pathlib import Path; "
               "from axm_uc.profession_crew import operate_profession_crew; "
               "print(json.dumps(operate_profession_crew(Path(sys.argv[1]), json.load(sys.stdin))))")
    result = subprocess.run([sys.executable, "-c", program, str(machine)], input=json.dumps(request),
                            text=True, capture_output=True, check=True, timeout=180,
                            env={**os.environ, "PYTHONPATH": str(ROOT / "src")})
    return json.loads(result.stdout)


def source_vehicle(registry, asset_id):
    asset = next(row for row in catalog()["assets"] if row["id"] == asset_id)
    mesh = MeasurableVehicle(False)
    vehicle(mesh, asset_id); dress(mesh, asset)
    surface = mesh.surface_spec(asset_id)
    parts = {"wheel": [], "chassis": [], "other": []}
    for group in surface["primitives"]:
        key = "wheel" if group["id"].startswith("wheel-0__") else "chassis" if group["id"].startswith("chassis__") else "other"
        parts[key].append(group)
    children = []
    origin = {"author": "AXM UC existing RTS recipes", "license": "Apache-2.0",
              "source": "rts_recipes.vehicle + rts_detail.dress; near-detail static rest pose; chassis faces regrouped for measurement"}
    for name, groups in parts.items():
        specification = {**surface, "name": asset_id + "-" + name, "primitives": groups}
        body = build_glb(specification)["body"]
        sticker = register_glb(registry, body, id=asset_id + "-" + name, name=asset_id + " " + name,
                               socket="mount", editable_source=json.dumps(specification, sort_keys=True).encode(), **origin)
        children.append({"instance": instance(sticker, name),
                         "target": {"space": "3d", "socket": "mount", "frame": identity()}, "motion": None, "clip": None})
    assembly = save_assembly(registry, id=asset_id, name=asset_id, children=children, origin=origin)
    return {"id": assembly["id"], "version": assembly["version"], "digest": digest(assembly)}, {
        "asset_id": asset_id, "lod": "near", "triangles": sum(len(g["indices"]) // 3 for g in surface["primitives"]),
        "selected_wheel_triangles": sum(len(g["indices"]) // 3 for g in parts["wheel"]),
        "selected_chassis_triangles": sum(len(g["indices"]) // 3 for g in parts["chassis"])}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--no-render", action="store_true", help="geometry/learning demonstration only")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("choose a fresh demo destination")
    machine = output / "machine"
    shutil.copytree(ROOT / "capabilities/live", machine / "capabilities/live")
    (machine / "creations").mkdir()
    database = machine / "creations/vehicles.sqlite"
    rows = []
    for index, asset_id in enumerate(("scrap-buggy", "flatbed-convoy-truck")):
        print("Preparing " + asset_id, flush=True)
        with Registry(database) as registry:
            assembly, source = source_vehicle(registry, asset_id)
        job = {"operation": "run", "crew_id": "vehicle-fit", "run_id": asset_id, "work_type": "3d",
               "goal": "Learn and reuse a verified static wheel-to-chassis clearance repair",
               "context": {"family": "UC RTS rigid vehicles", "units": "m"},
               "steps": [{"id": "wheel-fit", "profession_id": "technical-artist", "action": {
                   "kind": "repair-sticker-clearance", "inputs": {"path": "creations/" + asset_id,
                       "database": str(database), "assembly": assembly, "moving": "wheel", "fixed": ["chassis"],
                       "axis": "-x", "minimum_m": 0.06, "max_translation_m": 0.45,
                       "output_id": asset_id + "-clearance-repaired"}}}]}
        run = cold_worker(machine, job)
        folder = machine / "creations" / asset_id
        (output / (asset_id + "-run.json")).write_text(json.dumps(run, indent=2) + "\n")
        if run["status"] != "COMPLETE_BOUNDED_CHECKS":
            print(json.dumps(run["observations"], indent=2), flush=True)
            return 1
        report = json.loads((folder / "repair.json").read_text())
        fresh = cold_worker(machine, {"operation": "verify", "crew_id": "vehicle-fit", "run_id": asset_id})
        measured = run["observations"][0]
        row = {**source, "before": measured["before"]["requirements"][0]["pair"],
               "after": measured["after"]["requirements"][0]["pair"], "distance_m": measured["distance_m"],
               "selection": report["selection"], "search_trials": len(report["trials"]),
               "reused_procedure": run["plan"]["stations"][0]["reused_procedure"],
               "fresh_verification": fresh["status"], "renders": []}
        if row["reused_procedure"] != bool(index) or fresh["status"] != "PASS":
            raise AssertionError("expected cold discovery followed by verified procedure reuse")
        if not args.no_render:
            for view, yaw, elevation in (("front", 0.0, 0.20), ("top", 0.10, 1.20)):
                for stage in ("before", "after"):
                    print("Rendering " + asset_id + " " + view + " " + stage, flush=True)
                    rendered = render_glb_preview((folder / (stage + ".glb")).read_bytes(), width=640, height=420,
                                                  yaw=yaw, elevation=elevation, supersample=1, lighting="studio")
                    name = asset_id + "-" + view + "-" + stage + ".png"
                    (output / name).write_bytes(rendered["body"])
                    row["renders"].append({"file": name, **rendered["receipt"]})
        rows.append(row)
    result = {"schema": "axm.profession-clearance-demo/v1", "status": "PASS", "cases": rows,
              "crew_worker_restarted_between_jobs": True,
              "demo_script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              "scope": "One selected wheel against the actual chassis on two existing near-detail static vehicle recipes; no proxy geometry.",
              "limits": ["Other clearance pairs, mounts, steering, suspension, physics and target engines are untested.",
                         "Offline inspection renders are automatically framed per artifact; they do not prove PBR equivalence or professional visual quality.",
                         "Procedure discovery selects and verifies a built-in parameterized rule; it does not synthesize new code."],
              "sources": {name: hashlib.sha256((ROOT / "src/axm_uc" / name).read_bytes()).hexdigest()
                          for name in ("rts_mesh.py", "rts_recipes.py", "rts_detail.py", "profession_clearance_repair.py", "profession_crew.py")}}
    (output / "demo-report.json").write_text(json.dumps(result, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"status": result["status"], "cases": [{k: row[k] for k in
          ("asset_id", "distance_m", "selection", "search_trials", "reused_procedure", "fresh_verification")} for row in rows]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise product quality failure -> preserved revision -> textured delivery.

Original deterministic field-case recipe, built with UC's SurfaceBuilder. No
external models, texture assets, Blender or network access are used.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import shutil
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb
from axm_uc.product_workflow import operate_product_workflow
from axm_uc.software_glb_preview import render_glb_preview
from axm_uc.surface_geometry import SurfaceBuilder, cross, norm, sub


class UVBuilder(SurfaceBuilder):
    def box(self, tag, center, size, mat):
        # The old SurfaceBuilder helper swaps X/Z size through beam's local
        # frame. Preserve its existing recipes; this explicit adapter uses XYZ.
        self.beam(tag, (center[0], center[1]-size[1]/2, center[2]),
                  (center[0], center[1]+size[1]/2, center[2]), size[0], size[2], mat)

    def face(self, mat, verts, tag, weather=True):
        before = len(self.groups.get(mat, {}).get("p", []))
        super().face(mat, verts, tag, weather=False)
        group = self.groups[mat]
        if len(group["p"]) == before:
            return
        # Authored planar mapping per polygon. Reuse/overlap between separate
        # panels is intentional; this is not a general atlas unwrap/baker.
        u = norm(sub(verts[1], verts[0]))
        n = norm(cross(sub(verts[1], verts[0]), sub(verts[2], verts[0])))
        v = cross(n, u)
        coords = [[sum((p[i]-verts[0][i])*axis[i] for i in range(3)) for axis in (u, v)] for p in group["p"][before:]]
        low, high = ([min(p[i] for p in coords) for i in (0, 1)], [max(p[i] for p in coords) for i in (0, 1)])
        group.setdefault("uv", []).extend([[(p[i]-low[i])/(high[i]-low[i]) for i in (0, 1)] for p in coords])


def field_case():
    m = UVBuilder()
    ring = [(-.81,-.55),(.81,-.55),(.9,-.46),(.9,.46),(.81,.55),(-.81,.55),(-.9,.46),(-.9,-.46)]
    bottom, top = [[(x,y,z) for x,z in ring] for y in (.14,1.1)]
    m.face("paint", bottom, "bottom")
    m.face("paint", list(reversed(top)), "lid")
    for i in range(8):
        j = (i+1)%8
        m.face("paint", [bottom[i],top[i],top[j],bottom[j]], "bevel-body")
    m.box("front-seal", (0,.62,.56), (1.52,.69,.045), "rubber")
    m.box("front-service-panel", (0,.62,.598), (1.39,.57,.045), "paint")
    for x in (-.8,.8):
        for z in (-.49,.49):
            m.box("corner-guard", (x,.32,z), (.15,.35,.17), "steel")
            m.box("lid-guard", (x,1.06,z), (.17,.15,.18), "steel")
    for x in (-.59,.59):
        m.box("latch-body", (x,.93,.615), (.17,.24,.09), "rubber")
        m.box("latch-lever", (x,.95,.679), (.11,.17,.04), "steel")
        m.box("latch-tip", (x,.86,.70), (.14,.035,.05), "steel")
    for x in (-.61,.61):
        for y in (.43,.77):
            m.pipe("panel-fastener", [(x,y,.624),(x,y,.65)], .027, "steel", sides=10)
    for i in range(7):
        m.box("vent-slot", (.14+i*.065,.60,.628), (.027,.25,.018), "rubber")
    m.box("display-frame", (-.35,.63,.63), (.35,.20,.023), "steel")
    m.box("display-inset", (-.35,.63,.65), (.29,.14,.018), "rubber")
    for i in range(3):
        m.box("status-bars", (-.44+i*.085,.63,.667), (.048,.06,.014), "paint")
    for x in (-.42,.42):
        m.box("handle-mount", (x,1.13,0), (.15,.08,.21), "steel")
    m.pipe("carry-handle", [(-.42,1.17,0),(-.33,1.34,0),(.33,1.34,0),(.42,1.17,0)], .045, "rubber", sides=10)
    for z in (-.33,.33):
        m.box("top-stiffener", (0,1.13,z), (1.22,.065,.08), "steel")
    for x in (-.59,.59):
        m.box("foot", (x,.10,0), (.32,.15,.92), "rubber")
    groups = [{"id": name, "positions": g["p"], "normals": g["n"], "indices": g["i"], "texcoords": g["uv"],
               "material": {"color": "#ffffff", "metallic": 1, "roughness": 1}} for name,g in m.groups.items()]
    return {"schema": "axm.surface-3d/v0.1", "name": "AXM field service case", "primitives": groups}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    parser.add_argument("--quick", action="store_true", help="small actual renders for CI")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("choose a fresh demonstration directory")
    machine = output/"machine"
    shutil.copytree(ROOT/"capabilities/live", machine/"capabilities/live")
    size = 32 if args.quick else 128
    options = {"width": 96 if args.quick else 640, "height": 80 if args.quick else 480,
               "yaw": .57, "elevation": .30, "supersample": 1}
    specification = field_case()
    request = {"operation": "build", "crew_id": "product-materials", "run_id": "draft-low-resolution",
        "product_type": "static-3d", "path": "creations/draft-01",
        "brief": {"purpose": "Create a serviceable industrial field case with a complete editable material path",
            "target": "Native offline GLB inspection, metres; no engine import claim",
            "quality_intent": "Warm worn ochre panels, dark rubber seals, exposed steel guards; clear primary silhouette and layered service details",
            "acceptance": "Every part textured, complete map contracts, at least the declared map size, measured density, two light setups; aesthetic review remains separate",
            "uv_intent": "Explicit planar mapping per polygon; shared material UV space; no unique baked atlas or automatic padding"},
        "recipe": {
            "paint": {"family": "painted-metal", "size": 16 if args.quick else 32, "seed": 21,
                      "color": [201,137,42], "layer": {"amount": .12, "scratch_count": 6, "chip_scale": 36, "edge_normal_strength": .004,
                          "substrate_rgb": [87,98,108], "substrate_roughness": .38},
                      "surface_parameters": {"wear": .12, "scratches": 8, "grain_scale": 64,
                          "height_grain_amplitude": .025, "height_broad_amplitude": .006, "height_scratch_depth": .035,
                          "height_pit_depth": .02, "pit_wear_strength": .1, "base_grain_variation": .06,
                          "roughness_grain_variation": .04, "normal_strength": .85}},
            "rubber": {"family": "rubber", "size": size, "seed": 11, "color": [35,43,49]},
            "steel": {"family": "painted-metal", "size": size, "seed": 8, "color": [95,111,125],
                      "layer": {"amount": 1.0, "substrate_rgb": [125,139,150], "substrate_roughness": .32},
                      "surface_parameters": {"wear": .2, "scratches": 4, "normal_strength": .6, "height_grain_amplitude": .02,
                          "height_broad_amplitude": .005, "height_scratch_depth": .015, "height_pit_depth": .01}}},
        "material_policy": {"minimum_size": size}, "minimum_texels_per_m": size*.5,
        "maximum_size_m": [1.82, 1.5, 1.31],
        "specification": specification, "preview": options}
    print("Run 1: material resolution must fail before asset publication", flush=True)
    first = operate_product_workflow(machine, request)
    if first["status"] != "HOLD_FAILED_CHECK" or (machine/"creations/draft-01/asset.glb").exists():
        raise AssertionError("expected real map-size hold before asset publication")
    original_manifest = Path(first["delivery"]).read_bytes()
    request.update(operation="refine", run_id="draft-corrected", path="creations/draft-02", refines=first["delivery"],
                   revision_reason="Increase generated map size to the brief's declared minimum; preserve geometry and palette")
    request["recipe"]["paint"]["size"] = size
    print("Run 2: regenerate, check, bind, measure and render the corrected product", flush=True)
    second = operate_product_workflow(machine, request)
    if second["status"] != "DRAFT_BUILT_REVIEW_REQUIRED":
        print(json.dumps(second["run"], indent=2), flush=True)
        return 1
    if Path(first["delivery"]).read_bytes() != original_manifest:
        raise AssertionError("refinement changed the previous delivery")
    folder = machine/"creations/draft-02"
    print("Capturing scalar-material baseline with the same geometry and camera", flush=True)
    flat = copy.deepcopy(specification)
    colors = {"paint": "#94500c", "rubber": "#040607", "steel": "#343f49"}
    for group in flat["primitives"]:
        group["material"].update(color=colors[group["id"]], metallic=1 if group["id"] == "steel" else 0, roughness=.55)
    baseline = render_glb_preview(build_glb(flat)["body"], **options, lighting="studio")
    (output/"before-scalar.png").write_bytes(baseline["body"])
    for name in ("studio", "garage"):
        shutil.copyfile(folder/"previews"/(name+".png"), output/("after-"+name+".png"))
    shutil.copyfile(folder/"asset.glb", output/"field-service-case.glb")
    observations = second["run"]["observations"]
    receipts = [r["render_receipt"] for r in observations if "render_receipt" in r]
    report = {"schema": "axm.product-workflow-demo/v1", "first_status": first["status"], "second_status": second["status"],
        "fresh_verification": second["fresh"]["status"], "previous_delivery_preserved": True,
        "executed_stations": [r["station"] for r in observations],
        "triangle_count": sum(len(g["indices"])//3 for g in specification["primitives"]),
        "material_families": [r["family"] for r in request["recipe"].values()], "map_size": size,
        "baseline": baseline["receipt"], "renders": receipts,
        "quality": json.loads((folder/"checks/asset.json").read_text()),
        "stage_observations": second["manifest"]["stage_observations"],
        "evidence_files": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in output.iterdir() if p.is_file()},
        "source_hashes": {name: hashlib.sha256((ROOT/"src/axm_uc"/name).read_bytes()).hexdigest() for name in
            ("product_workflow.py", "material_pipeline.py", "native_textures.py", "texture_shading.py", "procedural_3d.py", "software_glb_preview.py", "profession_crew.py", "game_material_styles.py", "donor_metal.py", "__init__.py", "growth_lane_compat.py")},
        "demo_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        "limitations": ["Demonstrates workflow and texture realization; not photorealism, artistic acceptance, target-engine import, animation or a shipped game.",
            "Triangle-derived tangent frame is not MikkTSpace parity. No image-based reflections, anisotropic filtering, automatic unwrap, mesh baking or compressed texture export."]}
    (output/"product-demo-report.json").write_text(json.dumps(report, indent=2, sort_keys=True)+"\n")
    print(json.dumps({k: report[k] for k in ("first_status", "second_status", "fresh_verification", "previous_delivery_preserved", "triangle_count", "map_size")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Exercise automatic UVs, real baking, Cycles reflection and rig/target checks.

Requires an explicit local Blender runtime (AXM_BLENDER or PATH). All model and
material sources are original procedural fixtures; no network/art downloads.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import math
from pathlib import Path
import shutil
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from axm_uc.game_pose_runtime import _parse
from axm_uc.mesh_production import run_station
from axm_uc.mesh_quality import inspect_deformation
from axm_uc.procedural_3d import build_glb
from axm_uc.product_workflow import operate_product_workflow
from axm_uc.surface_geometry import SurfaceBuilder
from product_workflow_demo import field_case


def flex_asset(collapse=False):
    """Authored two-joint closed flex clip on a thick, five-section strip."""
    builder = SurfaceBuilder()
    rings = [[(x,y,z) for x,z in [(-.22,-.09),(.22,-.09),(.22,.09),(-.22,.09)]] for y in [0,.4,.8,1.2,1.6,2.]]
    for row,next_row in zip(rings,rings[1:]):
        for i in range(4):
            j = (i+1)%4
            builder.face("strap",[row[j],row[i],next_row[i],next_row[j]],"flex",weather=False)
    builder.face("strap",rings[0],"base",weather=False)
    builder.face("strap",list(reversed(rings[-1])),"end",weather=False)
    group = builder.groups["strap"]
    spec = {"schema":"axm.surface-3d/v0.1","name":"Authored flex strip","primitives":[
        {"id":"strap","positions":group["p"],"normals":group["n"],"indices":group["i"],
         "material":{"color":"#c9892a","metallic":.35,"roughness":.32}}]}
    doc,bin_body = _parse(build_glb(spec)["body"])
    binary = bytearray(bin_body)
    def add(rows,shape,code="f",component=5126):
        binary.extend(b"\0"*(-len(binary)%4))
        start = len(binary)
        for row in rows:
            binary.extend(struct.pack("<"+code*len(row),*row))
        doc["bufferViews"].append({"buffer":0,"byteOffset":start,"byteLength":len(binary)-start})
        doc["accessors"].append({"bufferView":len(doc["bufferViews"])-1,"componentType":component,"count":len(rows),"type":shape})
        return len(doc["accessors"])-1
    doc["nodes"] += [{"name":"Base","children":[2]},{"name":"FlexJoint","translation":[0,1,0]}]
    doc["scenes"][0]["nodes"].append(1)
    doc["nodes"][0]["skin"] = 0
    identity = [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]
    inverse = list(identity)
    inverse[13] = -1
    doc["skins"] = [{"joints":[1,2],"inverseBindMatrices":add([identity,inverse],"MAT4")}]
    attributes = doc["meshes"][0]["primitives"][0]["attributes"]
    attributes["JOINTS_0"] = add([[0,1,0,0] for _ in group["p"]],"VEC4","B",5121)
    weights = [max(0,min(1,(p[1]-.4)/1.2)) for p in group["p"]]
    attributes["WEIGHTS_0"] = add([[1-w,w,0,0] for w in weights],"VEC4")
    times = add([[0],[.5],[1]],"SCALAR")
    if collapse:
        values,path,node = [[1,1,1],[0,0,0],[1,1,1]],"scale",1
    else:
        angle = math.radians(55)/2
        values,path,node = [[0,0,0,1],[0,0,math.sin(angle),math.cos(angle)],[0,0,0,1]],"rotation",2
    doc["animations"] = [{"name":"Flex","samplers":[{"input":times,"output":add(values,"VEC3" if collapse else "VEC4"),"interpolation":"LINEAR"}],
                           "channels":[{"sampler":0,"target":{"node":node,"path":path}}]}]
    doc["buffers"][0]["byteLength"] = len(binary)
    text = json.dumps(doc,separators=(",",":")).encode()
    text += b" "*(-len(text)%4)
    binary.extend(b"\0"*(-len(binary)%4))
    return struct.pack("<4sII",b"glTF",2,28+len(text)+len(binary))+struct.pack("<II",len(text),0x4E4F534A)+text+struct.pack("<II",len(binary),0x004E4942)+binary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output",type=Path)
    parser.add_argument("--quick",action="store_true")
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        raise FileExistsError("choose a new output directory")
    root = output/"machine"
    shutil.copytree(ROOT/"capabilities/live",root/"capabilities/live")
    size = 128 if args.quick else 256
    spec = field_case()
    for g in spec["primitives"]:
        g.pop("texcoords")
    request = {"operation":"build","product_type":"static-3d","path":"creations/case","run_id":"case-production",
        "brief":{"purpose":"Prepare the industrial field case from source geometry through target rendering",
                 "target":"Blender 4.3 Cycles CPU and native GLB","quality_intent":"Restrained ochre coating, rubber seals and satin steel; mesh contact darkening, coherent scale, readable silhouette"},
        "recipe":{
            "paint":{"family":"painted-metal","size":size,"seed":21,"color":[201,137,42],
                     "surface_parameters":{"wear":.03,"scratches":0,"normal_strength":.25,"height_grain_amplitude":.012,
                                           "height_broad_amplitude":.001,"height_pit_depth":.005,"base_grain_variation":.02,"roughness_grain_variation":.025}},
            "rubber":{"family":"rubber","size":size,"seed":11,"color":[35,43,49]},
            "steel":{"family":"painted-metal","size":size,"seed":8,"color":[125,139,150],
                     "layer":{"amount":1.0,"substrate_rgb":[125,139,150],"substrate_roughness":.3},
                     "surface_parameters":{"wear":1.,"scratches":0,"normal_strength":.2,"height_grain_amplitude":.01,
                                           "height_broad_amplitude":.001,"height_pit_depth":.002,"base_grain_variation":.02}}},
        "specification":spec,"material_policy":{"minimum_size":size},"minimum_texels_per_m":4 if args.quick else 12,
        "maximum_size_m":[1.82,1.5,1.31],"preview":{"width":96 if args.quick else 640,"height":80 if args.quick else 480},
        "production":{"uv":{"resolution":size,"padding_px":1 if args.quick else 2},
                      "bake":{"size":size,"margin_px":1 if args.quick else 2,"samples":2 if args.quick else 24},
                      "target":{"width":96 if args.quick else 800,"height":80 if args.quick else 600,"samples":2 if args.quick else 48,
                                "views":[{"yaw":.57,"elevation":.3},{"yaw":-2.1,"elevation":.4}]}}}
    print("Run static production through the actual profession workflow",flush=True)
    result = operate_product_workflow(root,request)
    if result["status"] != "DRAFT_BUILT_REVIEW_REQUIRED":
        print(json.dumps(result,indent=2),flush=True)
        raise RuntimeError("static production held")
    assets = root/"creations/sources"
    assets.mkdir()
    body = flex_asset()
    (assets/"flex.glb").write_bytes(body)
    failure = inspect_deformation(flex_asset(collapse=True))
    if failure["status"] != "FAIL":
        raise AssertionError("collapsed authored extreme must fail")
    (output/"collapsed-extreme.json").write_text(json.dumps(failure,indent=2)+"\n")
    animated = {"operation":"build","product_type":"animated-3d","path":"creations/flex","run_id":"flex-production",
        "asset":"creations/sources/flex.glb","brief":{"purpose":"Preserve and validate an authored two-joint flex clip",
        "target":"Blender 4.3 Cycles CPU","quality_intent":"Closed bend without triangle collapse, excessive stretch or movement at its fixed base"},
        "production":{"deformation":{"loop_clips":["Flex"],"contacts":[{"clip":"Flex","mesh":0,"vertex":0,"start_s":0,"end_s":1,"maximum_drift_m":.001}]},
            "target":{"width":96 if args.quick else 480,"height":96 if args.quick else 600,"samples":2 if args.quick else 32,
                      "views":[{"yaw":.5,"elevation":.3,"clip":"Flex","time_s":0},{"yaw":.5,"elevation":.3,"clip":"Flex","time_s":.5}]}}}
    print("Check collapsed extreme, then run the preserved good rig through native and Blender checks",flush=True)
    motion = operate_product_workflow(root,animated)
    if motion["status"] != "DRAFT_BUILT_REVIEW_REQUIRED":
        print(json.dumps(motion,indent=2),flush=True)
        raise RuntimeError("animated production held")
    report = {"schema":"axm.mesh-production-demo/v1","status":"PASS","static":result["manifest"],"animated":motion["manifest"],
              "collapsed_extreme":failure["status"],"source_preserved":(assets/"flex.glb").read_bytes() == body,
              "sources":{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [
                  Path(__file__),ROOT/"src/axm_uc/mesh_production.py",ROOT/"src/axm_uc/mesh_quality.py",ROOT/"src/axm_uc/blender_production_worker.py",ROOT/"src/axm_uc/product_workflow.py"]}}
    (output/"production-report.json").write_text(json.dumps(report,indent=2)+"\n")
    print(json.dumps({"status":"PASS","report":str(output/"production-report.json")}),flush=True)


if __name__ == "__main__":
    main()

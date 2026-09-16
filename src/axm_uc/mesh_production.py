"""Optional Blender production stations and dependency-free deformation checks.

Every operation has a fresh observer. Blender jobs use a fixed local worker and
bounded JSON, preserve source, and publish only into a new output directory.
"""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

from .atomic import atomic_write_bytes, atomic_write_json
from .fabric_noise import png_bytes
from .game_pose_runtime import GamePoseAsset, _parse
from .mesh_quality import inspect_deformation, inspect_uv_layout, number
from .native_textures import decode_png
from .procedural_3d import build_glb
from .software_glb_preview import _accessor

KINDS = {"unwrap-surface-uv", "bake-mesh-maps", "validate-blender-target", "inspect-deformation", "copy-animation-asset"}
WORKER = Path(__file__).with_name("blender_production_worker.py")


def _target(root,value):
    from .profession_crew import _target as target
    return target(root,value)


def _sha(body):
    return hashlib.sha256(body).hexdigest()


def _digest(value):
    return _sha(json.dumps(value,sort_keys=True,separators=(",",":"),allow_nan=False).encode())


def blender_executable():
    value = os.environ.get("AXM_BLENDER") or shutil.which("blender")
    if not value or not Path(value).is_file():
        raise RuntimeError("Blender backend unavailable. Install Blender and set AXM_BLENDER to its executable; native UC remains available.")
    return str(Path(value).resolve())


def _worker(request,output):
    executable = blender_executable()
    output.mkdir(parents=True,exist_ok=False)
    atomic_write_json(output/"worker-request.json",{**request,"output":str(output)})
    command = [executable,"--background","--factory-startup","--disable-autoexec","--threads","2",
               "--python-exit-code","2","--python",str(WORKER),"--",str(output/"worker-request.json")]
    with (output/"worker.log").open("wb") as log:
        try:
            result = subprocess.run(command,stdout=log,stderr=subprocess.STDOUT,timeout=240,check=False)
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("Blender job exceeded its 240-second bound") from exc
    if result.returncode or not (output/"worker-result.json").is_file():
        tail = (output/"worker.log").read_text(errors="replace")[-5000:]
        raise RuntimeError("Blender production job failed: "+tail)
    return json.loads((output/"worker-result.json").read_text())


def _asset(root,value):
    path = _target(root,value)
    body = path.read_bytes()
    GamePoseAsset(body)
    doc,_ = _parse(body)
    if any("uri" in image for image in doc.get("images",[])):
        raise ValueError("production target requires embedded images; external URIs are unsupported")
    return path,body


def _surface(root,value):
    source = json.loads(_target(root,value).read_text()) if isinstance(value,str) else copy.deepcopy(value)
    if not isinstance(source,dict) or source.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("requires a native surface specification or its path")
    build_glb(source)  # existing geometry/texture validation
    return json.loads(json.dumps(source,allow_nan=False))


def _options(inputs,defaults):
    options = inputs.get("options",{})
    if not isinstance(options,dict) or set(options)-defaults.keys():
        raise ValueError("unsupported production options")
    return {**defaults,**options}


def _unwrap_options(inputs):
    p = _options(inputs,{"resolution":128,"padding_px":2,"angle_limit_degrees":66})
    number(p["resolution"],"resolution",16,2048,True)
    number(p["padding_px"],"padding_px",1,p["resolution"]/8,True)
    number(p["angle_limit_degrees"],"angle_limit_degrees",1,89)
    return p


def _bake_options(inputs):
    p = _options(inputs,{"size":128,"samples":16,"margin_px":2,"cage_extrusion":.02,"max_ray_distance":.1})
    number(p["size"],"size",16,512,True)
    number(p["samples"],"samples",1,128,True)
    number(p["margin_px"],"margin_px",1,32,True)
    number(p["cage_extrusion"],"cage_extrusion",0,10)
    number(p["max_ray_distance"],"max_ray_distance",.00001,10)
    return p


def _target_options(inputs):
    p = _options(inputs,{"engine":"blender-cycles","width":640,"height":480,"samples":32,"environment_strength":.5,"denoise":True,
                         "views":[{"yaw":.6,"elevation":.35},{"yaw":-1.8,"elevation":.3}],"pose_samples":3})
    if p["engine"] != "blender-cycles":
        raise ValueError("target adapter currently executes blender-cycles only")
    for key in ("width","height"):
        number(p[key],key,64,1024,True)
    number(p["samples"],"samples",1,128,True)
    number(p["environment_strength"],"environment_strength",0,5)
    if type(p["denoise"]) is not bool:
        raise ValueError("denoise must be boolean")
    number(p["pose_samples"],"pose_samples",2,16,True)
    if not isinstance(p["views"],list) or not 1 <= len(p["views"]) <= 8:
        raise ValueError("target views must have 1..8 camera/pose states")
    for view in p["views"]:
        if not isinstance(view,dict) or set(view)-{"yaw","elevation","clip","time_s"}:
            raise ValueError("invalid target view")
        number(view.get("yaw"),"yaw",-6.284,6.284)
        number(view.get("elevation"),"elevation",-.1,1.45)
        number(view.get("time_s",0),"time_s",0,600)
    return p


def validate_station(root,kind,inputs):
    _target(root,inputs.get("path"))
    if kind not in KINDS:
        raise ValueError("unknown mesh production station")
    if kind == "unwrap-surface-uv":
        _unwrap_options(inputs)
    elif kind == "bake-mesh-maps":
        _bake_options(inputs)
        if inputs.get("high_specification") is not None and not isinstance(inputs["high_specification"],(dict,str)):
            raise ValueError("high_specification requires an explicit source")
    else:
        _target(root,inputs.get("asset"))
        if kind == "validate-blender-target":
            _target_options(inputs)


def _geometry_signature(source):
    return [{"id":g["id"],"material":g.get("material"),"size":g.get("size"),"translation":g.get("translation"),
             "corners":[{key:g[key][i] for key in ("positions","normals","colors") if key in g} for i in g["indices"]]}
            for g in source["primitives"]]


def _covered_pixels(group,size):
    uv,ids = group["texcoords"],group["indices"]
    covered,visits = set(),0
    for i in range(0,len(ids),3):
        a,b,c = [[uv[j][k]*size for k in range(2)] for j in ids[i:i+3]]
        det = (b[1]-c[1])*(a[0]-c[0])+(c[0]-b[0])*(a[1]-c[1])
        if abs(det) < 1e-9:
            continue
        for y in range(max(0,int(min(a[1],b[1],c[1]))),min(size,int(max(a[1],b[1],c[1]))+1)):
            for x in range(max(0,int(min(a[0],b[0],c[0]))),min(size,int(max(a[0],b[0],c[0]))+1)):
                visits += 1
                if visits > 8_000_000:
                    raise ValueError("bake coverage raster budget exceeded")
                u = ((b[1]-c[1])*(x+.5-c[0])+(c[0]-b[0])*(y+.5-c[1]))/det
                v = ((c[1]-a[1])*(x+.5-c[0])+(a[0]-c[0])*(y+.5-c[1]))/det
                if min(u,v,1-u-v) > 1e-6:
                    covered.add(y*size+x)
    return sorted(covered)


def _produce(root,kind,inputs,output):
    if kind == "unwrap-surface-uv":
        source = _surface(root,inputs.get("specification"))
        if any("textures" in g for g in source["primitives"]):
            raise ValueError("unwrap before material binding; existing textures require explicit rebaking")
        p = _unwrap_options(inputs)
        worker = _worker({"operation":"unwrap","specification":source,**p},output)
        derivative = json.loads((output/"surface.json").read_text())
        build_glb(derivative)
        quality = inspect_uv_layout(derivative,p["resolution"],p["padding_px"])
        checks = [{"type":"source-geometry-preserved","passed":_geometry_signature(source) == _geometry_signature(derivative)},
                  {"type":"unique-atlas-and-padding","passed":quality["status"] == "PASS"}]
        source_digest = _digest(source)
        details = {"uv":quality}
    elif kind == "bake-mesh-maps":
        if "materials" in inputs:
            from .material_pipeline import bound_specification
            source = bound_specification(root,inputs)
        else:
            source = _surface(root,inputs.get("specification"))
        p = _bake_options(inputs)
        # The baker requires a verified unique atlas. Padding is kept separate
        # from the dilation radius, so neighbors cannot be silently certified.
        quality = inspect_uv_layout(source,p["size"],p["margin_px"])
        if quality["status"] != "PASS":
            raise ValueError("mesh bake requires unique UVs and sufficient padding")
        if any("textures" not in g for g in source["primitives"]):
            raise ValueError("mesh bake requires textured surface groups")
        high = _surface(root,inputs["high_specification"]) if inputs.get("high_specification") is not None else None
        if high and {g["id"] for g in high["primitives"]} != {g["id"] for g in source["primitives"]}:
            raise ValueError("high-detail source group ids must match low source")
        with tempfile.TemporaryDirectory(prefix="uc-bake-source-") as folder:
            # Blender truncates names and renumbers numeric suffixes on import.
            # Internal temporary names avoid identity loss for valid UC ids.
            names = {g["id"]:"uc-mesh-"+str(i) for i,g in enumerate(source["primitives"])}
            low_bridge = copy.deepcopy(source)
            for g in low_bridge["primitives"]:
                g["id"] = names[g["id"]]
            low_path = Path(folder)/"low.glb"
            low_path.write_bytes(build_glb(low_bridge)["body"])
            request = {"operation":"bake","asset":str(low_path),**p}
            if high:
                high_path = Path(folder)/"high.glb"
                high_bridge = copy.deepcopy(high)
                for g in high_bridge["primitives"]:
                    g["id"] = names[g["id"]]
                high_path.write_bytes(build_glb(high_bridge)["body"])
                request["high_asset"] = str(high_path)
            worker = _worker(request,output)
        original_names = {v:k for k,v in names.items()}
        for row in worker["groups"]:
            name = original_names[row["id"]]
            for role in ("ao","normal"):
                if role in row:
                    destination = name+"-"+role+".png"
                    (output/row[role]).rename(output/destination)
                    row[role] = destination
            row["id"] = name
        derivative, measurements = copy.deepcopy(source),[]
        for group in derivative["primitives"]:
            size = p["size"]
            textures = group["textures"]
            orm = decode_png(base64.b64decode(textures["orm"]))
            ao = decode_png((output/(group["id"]+"-ao.png")).read_bytes())
            if orm[:2] != (size,size) or ao[:2] != (size,size):
                raise ValueError("bake size must match source texture maps")
            data = bytearray(orm[2])
            for i in range(0,len(data),3):
                data[i] = round(data[i]*ao[2][i]/255)
            textures["orm"] = base64.b64encode(png_bytes(size,size,3,bytes(data))).decode()
            covered = _covered_pixels(group,size)
            row = {"id":group["id"],"covered_texels":len(covered),
                   "ao_min":min((ao[2][i*3] for i in covered),default=0),"ao_max":max((ao[2][i*3] for i in covered),default=0)}
            if high:
                normal_body = (output/(group["id"]+"-normal.png")).read_bytes()
                normal = decode_png(normal_body)
                missing = sum(normal[2][i*3:i*3+3] == b"\0\0\0" for i in covered)
                projection = next(r["projection"] for r in worker["groups"] if r["id"] == group["id"])
                row["unhit_normal_texels"] = max(missing,projection["unhit_texels"])
                row["projection"] = projection
                # Explicit geometric transfer replaces the generated tangent
                # normal. Procedural detail is not silently mixed into it.
                textures["normal"] = base64.b64encode(normal_body).decode()
            measurements.append(row)
        atomic_write_json(output/"surface.json",derivative)
        atomic_write_bytes(output/"asset.glb",build_glb(derivative)["body"])
        checks = [{"type":"source-geometry-and-uv-preserved","passed":all(a[k] == b[k] for a,b in zip(source["primitives"],derivative["primitives"]) for k in ("positions","normals","indices","texcoords"))},
                  {"type":"covered-bake-texels","passed":all(r["covered_texels"] > 0 for r in measurements)},
                  {"type":"normal-projection-hits","passed":all(r.get("unhit_normal_texels",0) == 0 and r.get("projection",{"covered_texels":1})["covered_texels"] > 0 for r in measurements)}]
        source_digest = _digest({"low":source,"high":high})
        details = {"bake":measurements,"normal_policy":"replace with high-detail tangent normal" if high else "preserve original tangent normal"}
    elif kind == "validate-blender-target":
        asset_path,body = _asset(root,inputs.get("asset"))
        p = _target_options(inputs)
        asset = GamePoseAsset(body)
        clips = asset.describe()["clips"]
        poses = [{"clip":None,"time_s":0.}]
        for clip in clips:
            poses += [{"clip":clip["name"],"time_s":clip["duration_s"]*i/(p["pose_samples"]-1)} for i in range(p["pose_samples"])]
        if len(poses)>64:
            raise ValueError("target pose budget exceeded")
        for view in p["views"]:
            asset.sample(view.get("clip"),view.get("time_s",0.),vertices=True)
        worker = _worker({"operation":"target","asset":str(asset_path),"render":True,"poses":poses,**p},output)
        doc,binary = _parse(body)
        triangles = sum((doc["accessors"][pr["indices"]]["count"] if "indices" in pr else doc["accessors"][pr["attributes"]["POSITION"]]["count"])//3
                        for node in doc["nodes"] if "mesh" in node for pr in doc["meshes"][node["mesh"]]["primitives"])
        geometry_rows = []
        for pose,observed in zip(poses,worker["poses"]):
            points = [p for mesh in asset.sample(pose["clip"],pose["time_s"],vertices=True)["meshes"] for p in mesh["positions"]]
            expected = {"min":[min(p[k] for p in points) for k in range(3)],"max":[max(p[k] for p in points) for k in range(3)]}
            error = max(abs(expected[key][k]-observed["geometry"]["bounds_m"][key][k]) for key in ("min","max") for k in range(3))
            geometry_rows.append({**pose,"bounds_error_m":error,"triangles_match":observed["geometry"]["triangles"] == triangles})
        image_rows = []
        for i in range(len(p["views"])):
            path = output/f"view-{i:02d}.png"
            w,h,data = decode_png(path.read_bytes())
            mw,mh,mask = decode_png((output/f"coverage-{i:02d}.png").read_bytes())
            image_rows.append({"file":path.name,"width":w,"height":h,"channel_range":max(data)-min(data),
                               "asset_visible_pixels":sum(v > 127 for v in mask[::3]),"mask_dimensions_match":(mw,mh) == (w,h)})
        imported = worker["import"]
        expected_bindings = 0
        for node in doc["nodes"]:
            if "mesh" not in node:
                continue
            for primitive in doc["meshes"][node["mesh"]]["primitives"]:
                material = doc.get("materials",[])[primitive["material"]] if "material" in primitive else {}
                pbr = material.get("pbrMetallicRoughness",{})
                expected_bindings += sum(k in pbr for k in ("baseColorTexture","metallicRoughnessTexture")) + sum(k in material for k in ("normalTexture","occlusionTexture","emissiveTexture"))
        checks = [{"type":"all-target-poses-observed","passed":len(geometry_rows) == len(poses)},
                  {"type":"native-target-geometry-agreement","passed":all(r["bounds_error_m"] < 1e-4 and r["triangles_match"] for r in geometry_rows)},
                  {"type":"target-material-images-decoded","passed":all(r["decoded_images"] and (not r["images"] or r["uv_layers"]) for r in imported["materials"]) and sum(r["images"] for r in imported["materials"]) >= expected_bindings},
                  {"type":"target-views-rendered","passed":all(r["width"] == p["width"] and r["height"] == p["height"] and r["channel_range"] > 8 and r["asset_visible_pixels"] > 0 and r["mask_dimensions_match"] for r in image_rows)}]
        source_digest = _sha(body)
        details = {"target":"blender-cycles","pose_comparison":geometry_rows,"images":image_rows,
                   "scope":"Fresh Blender imports, native-vs-target pose bounds/triangle counts, image decode and Cycles renders. No Unity/Unreal/Godot, game controls or device performance claim."}
    else:
        raise ValueError("unsupported backend production operation")
    report = {"schema":"axm.mesh-production/v1","kind":kind,"source_sha256":source_digest,"options":p,
              "backend":{"version":worker["blender_version"],"build":worker["blender_build"],"worker_sha256":worker["worker_sha256"]},
              "status":"PASS" if all(r["passed"] for r in checks) else "FAIL","checks":checks,**details}
    report["artifacts"] = {file.name:_sha(file.read_bytes()) for file in output.iterdir() if file.suffix in (".png",".glb") or file.name == "surface.json"}
    atomic_write_json(output/"report.json",report)
    return report


def run_station(root,kind,inputs):
    validate_station(root,kind,inputs)
    path = _target(root,inputs["path"])
    if path.exists():
        raise FileExistsError("mesh station refuses existing output")
    if kind in {"inspect-deformation","copy-animation-asset"}:
        _,body = _asset(root,inputs.get("asset"))
        if kind == "copy-animation-asset":
            atomic_write_bytes(path,body)
            return {"status":"COPIED","sha256":_sha(body)}
        report = inspect_deformation(body,inputs.get("policy"))
        atomic_write_json(path,report)
        return report
    # Failed/partial backend writes stay in a temporary directory. No incomplete
    # result can masquerade as an output of the station.
    with tempfile.TemporaryDirectory(prefix="uc-production-") as folder:
        generated = Path(folder)/"result"
        report = _produce(root,kind,inputs,generated)
        path.parent.mkdir(parents=True,exist_ok=True)
        shutil.copytree(generated,path)
    return report


def observe_station(root,kind,inputs):
    validate_station(root,kind,inputs)
    path = _target(root,inputs["path"])
    if kind == "copy-animation-asset":
        _,body = _asset(root,inputs.get("asset"))
        checks = [{"type":"exact-preserved-animation-source","passed":path.read_bytes() == body}]
    elif kind == "inspect-deformation":
        _,body = _asset(root,inputs.get("asset"))
        expected = inspect_deformation(body,inputs.get("policy"))
        checks = [{"type":"fresh-deformation-measurement","passed":json.loads(path.read_text()) == expected},*expected["checks"]]
    else:
        # Rerun the actual backend, including renders. A supplied PASS or old
        # worker receipt cannot establish that the current source works.
        with tempfile.TemporaryDirectory(prefix="uc-observe-production-") as folder:
            expected = _produce(root,kind,inputs,Path(folder)/"fresh")
        stored = json.loads((path/"report.json").read_text())
        checks = [{"type":"fresh-backend-reproduction","passed":stored == expected},*expected["checks"]]
        checks += [{"type":"artifact-"+name,"passed":(path/name).is_file() and _sha((path/name).read_bytes()) == digest}
                   for name,digest in expected["artifacts"].items()]
    return {"status":"PASS" if checks and all(c["passed"] for c in checks) else "FAIL","checks":checks,
            "professional_acceptance":"NOT_TESTED","visual_quality":"REQUIRES_REVIEW",
            "scope":"Current source, explicit geometric policy and selected backend only; no automatic artistic or product acceptance."}

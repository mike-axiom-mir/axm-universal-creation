"""Portable, rigged character adapters owned by the creation machine."""
from __future__ import annotations

import json
from pathlib import Path
import struct
import subprocess
import time
from typing import Any

from .atomic import atomic_write_json
from .visual_3d import _sha256, inspect_glb, resolve_blender
from .visual_learning import inspect_visual_learning

CHARACTER_ID = "axm-oops"
EXPECTED_CLIPS = {"Idle", "Walk_InPlace", "Wave", "Oops_Recover"}


def character_catalog() -> dict[str, Any]:
    return {
        "schema": "axm.rigged-character-catalog/v0.1",
        "characters": {CHARACTER_ID: {"name": "OOPS", "role": "comic futuristic repair courier",
                                      "binding": "rigid mechanical skin", "materials": "single PBR atlas",
                                      "detail_profiles": {"1":"lightweight", "2":"original release",
                                                          "3":"crafted forms and unique baked surfaces"},
                                      "animation_clips": sorted(EXPECTED_CLIPS)}},
        "outputs": ["blend", "glb", "fbx", "png", "json"],
        "truth": {"targetEngineSetupRequired": True, "aaaCertification": False,
                  "exhaustiveOriginalityClearance": False, "generatorLivesInMachine": True},
    }


def inspect_rigged_character(path: str | Path) -> dict[str, Any]:
    """Read GLB skin and animation structure; playback needs a separate importer."""
    target = Path(path).resolve()
    basic = inspect_glb(target)
    data = target.read_bytes()
    length = struct.unpack_from("<I", data, 12)[0]
    document = json.loads(data[20:20+length].decode().rstrip(" \0\r\n"))
    skins, nodes = document.get("skins", []), document.get("nodes", [])
    animations = document.get("animations", [])
    meshes = document.get("meshes", [])
    skinned_meshes = {node["mesh"] for node in nodes if "skin" in node and "mesh" in node}
    primitives = [primitive for index in skinned_meshes for primitive in meshes[index].get("primitives", [])]
    gates = {
        "one-skeleton": len(skins) == 1,
        "nonempty-joints": bool(skins) and len(skins[0].get("joints", [])) >= 20,
        "all-meshes-skinned": bool(meshes) and len(skinned_meshes) == len(meshes),
        "skin-attributes": bool(primitives) and all({"JOINTS_0", "WEIGHTS_0", "POSITION", "NORMAL", "TEXCOORD_0"}
                                                      <= set(row.get("attributes", {})) for row in primitives),
        "four-required-clips": EXPECTED_CLIPS <= {row.get("name") for row in animations},
        "nonempty-animation-channels": bool(animations) and all(row.get("channels") and row.get("samplers") for row in animations),
        "one-pbr-material": len(basic["materials"]) == 1,
        "embedded-pbr-images": basic["images"] >= 2,
    }
    return {
        **basic, "schema": "axm.rigged-character-inspection/v0.1", "gates": gates,
        "status": "RIGGED_STRUCTURE_PASS" if all(gates.values()) else "RIGGED_STRUCTURE_REVIEW_REQUIRED",
        "joint_names": [nodes[index].get("name") for skin in skins for index in skin.get("joints", [])],
        "animations": [{"name":row.get("name"),"channels":len(row.get("channels", []))} for row in animations],
        "surface_features":{
            "tangents":bool(primitives) and all("TANGENT" in row.get("attributes",{}) for row in primitives),
            "base_color_map":all("baseColorTexture" in mat.get("pbrMetallicRoughness",{}) for mat in document.get("materials",[])),
            "metal_roughness_map":all("metallicRoughnessTexture" in mat.get("pbrMetallicRoughness",{}) for mat in document.get("materials",[])),
            "normal_map":all("normalTexture" in mat for mat in document.get("materials",[])),
            "occlusion_map":all("occlusionTexture" in mat for mat in document.get("materials",[])),
        },
        "truth": "Structural inspection is not playback or engine-integration certification.",
    }


def forge_rigged_character(root: str | Path, request: Any, output: str | Path, *,
                           blender: str | Path | None = None, timeout_seconds: int = 2400) -> dict[str, Any]:
    if not isinstance(request, dict) or request.get("asset_id", CHARACTER_ID) != CHARACTER_ID:
        raise ValueError("rigged character request must select axm-oops")
    resolution = request.get("render_resolution", 960)
    detail = request.get("detail_pass", 2)
    texture_resolution = request.get("texture_resolution", 2048)
    if type(resolution) is not int or not 256 <= resolution <= 2048:
        raise ValueError("render_resolution must be an integer between 256 and 2048")
    if type(detail) is not int or detail not in (1, 2, 3):
        raise ValueError("detail_pass must be 1, 2, or 3")
    if type(texture_resolution) is not int or texture_resolution not in (1024, 2048, 4096):
        raise ValueError("texture_resolution must be 1024, 2048, or 4096")
    for flag in ("no_render", "auto_provision_runtime", "verify_roundtrip"):
        if flag in request and type(request[flag]) is not bool:
            raise ValueError(f"{flag} must be a boolean")
    machine = Path(root).resolve()
    script = machine / "tools" / "blender" / "axm_oops_character.py"
    if not script.is_file():
        raise FileNotFoundError(script)
    target = Path(output).resolve()
    if target.exists():
        raise FileExistsError(f"character output already exists: {target}")
    executable, runtime = resolve_blender(blender, auto_provision=request.get("auto_provision_runtime", True))
    target.mkdir(parents=True, exist_ok=False)
    context = "3d/axm-oops/rigged-v1"
    learning = inspect_visual_learning(root, context_key=context)
    normalized = {"asset_id":CHARACTER_ID,"context_key":context,"render_resolution":resolution,
                  "detail_pass":detail,"render":not request.get("no_render", False),
                  "texture_resolution":texture_resolution,
                  "verify_roundtrip":request.get("verify_roundtrip",False),
                  "prior_exact_context_observations":learning["contexts"].get(context, {}),
                  "truth":"Observations inform the builder; prose alone is not a geometry edit."}
    atomic_write_json(target / "character-request.json", normalized)
    command = [str(executable),"--background","--factory-startup","--python-exit-code","1","--python",str(script),"--",
               "--output",str(target),"--resolution",str(resolution),"--detail",str(detail),
               "--texture-resolution",str(texture_resolution)]
    if request.get("no_render", False):
        command.append("--no-render")
    # Stream logs to disk so a canceled render still leaves useful diagnostics.
    started=time.monotonic()
    with (target / "build.stdout.txt").open("w",encoding="utf-8") as stdout, (target / "build.stderr.txt").open("w",encoding="utf-8") as stderr:
        completed = subprocess.run(command,stdout=stdout,stderr=stderr,timeout=timeout_seconds,check=False)
    if completed.returncode:
        raise RuntimeError(f"character forge failed ({completed.returncode}); inspect {target / 'build.stderr.txt'}")
    manifest = json.loads((target / "character-manifest.json").read_text(encoding="utf-8"))
    inspections = {lod:inspect_rigged_character(target / manifest["exports"][lod]["path"])
                   for lod in ("lod0","lod1","lod2")}
    receipt = {"schema":"axm.rigged-character-forge/v0.1","asset_id":CHARACTER_ID,
               "output":str(target),"runtime":runtime,"builder_sha256":_sha256(script),
               "supporting_builder_sha256":{name:_sha256(script.parent/name) for name in
                   ("axm_blender_forge.py","axm_character_surfaces.py") if (script.parent/name).is_file()},
               "inspections":inspections,"status":"STRUCTURE_CHECKED_PLAYBACK_REVIEW_REQUIRED",
               "visual_acceptance": "REQUIRED", "originality_clearance":"NOT_EXHAUSTIVELY_CHECKED"}
    if any(row["status"] != "RIGGED_STRUCTURE_PASS" for row in inspections.values()):
        receipt["status"] = "STRUCTURE_FAILED"
    if detail>=3:
        receipt["crafted_surface_structure"]={lod:all(row["surface_features"].values()) for lod,row in inspections.items()}
        if not all(receipt["crafted_surface_structure"].values()):
            receipt["status"]="SURFACE_STRUCTURE_FAILED"
    if request.get("verify_roundtrip",False):
        verifier=script.parent/"verify_rigged_character.py"
        command=[str(executable),"--background","--factory-startup","--python-exit-code","1",
                 "--python",str(verifier),"--","--directory",str(target)]
        with (target/"verify.stdout.txt").open("w",encoding="utf-8") as stdout, (target/"verify.stderr.txt").open("w",encoding="utf-8") as stderr:
            checked=subprocess.run(command,stdout=stdout,stderr=stderr,
                timeout=max(1,timeout_seconds-(time.monotonic()-started)),check=False)
        report_path=target/"roundtrip-verification.json"
        report=json.loads(report_path.read_text(encoding="utf-8")) if report_path.is_file() else {}
        receipt["roundtrip"]={"returncode":checked.returncode,"status":report.get("status","MISSING_REPORT"),
                              "verifier_sha256":_sha256(verifier),
                              "report_sha256":_sha256(report_path) if report_path.is_file() else None}
        if checked.returncode or report.get("status")!="PASS":
            receipt["status"]="ROUNDTRIP_FAILED"
        elif receipt["status"]=="STRUCTURE_CHECKED_PLAYBACK_REVIEW_REQUIRED":
            receipt["status"]="STRUCTURE_AND_PLAYBACK_CHECKED_VISUAL_REVIEW_REQUIRED"
    atomic_write_json(target / "character-receipt.json", receipt)
    return receipt

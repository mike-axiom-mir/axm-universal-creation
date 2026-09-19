"""Executable material/asset stations with fresh artifact observers."""
from __future__ import annotations

import base64
import copy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json
from .auto_uv_bake import build_directory as build_auto_uv_bake, verify_directory as verify_auto_uv_bake
from .game_material_bridge import load_material_bundle
from .game_material_styles import WearLayer, game_material_request, generate_game_material
from .native_textures import decode_png, texture_set_from_bundle
from .procedural_3d import build_glb, publish_glb, verify_glb
from .software_glb_preview import publish_glb_preview, render_glb_preview
from .material_uv_evidence import inspect_material_uv_density
from .game_pose_runtime import GamePoseAsset
from . import mesh_production, godot_target

KINDS = {"generate-game-material", "inspect-game-material", "bind-textured-asset",
         "auto-unwrap-bake-asset", "inspect-textured-asset", "render-asset-preview"} | mesh_production.KINDS | godot_target.KINDS


def _target(root, value):
    from .profession_crew import _target as target
    return target(root, value)


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False)


def material_options(inputs):
    recipe = inputs.get("recipe")
    allowed = {"family", "size", "seed", "finish", "color", "layer", "surface_parameters"}
    if not isinstance(recipe, dict) or "family" not in recipe or set(recipe) - allowed:
        raise ValueError("material recipe requires family and supported generation parameters")
    options = copy.deepcopy(recipe)
    if "layer" in options:
        if not isinstance(options["layer"], dict):
            raise ValueError("layer must contain explicit WearLayer parameters")
        options["layer"] = WearLayer(**options["layer"])
    return options


def material_quality(folder, policy=None):
    policy = {} if policy is None else policy
    defaults = {"minimum_size": 64, "maximum_png_bytes": 8*1024*1024,
                "maximum_normal_error": .03, "require_tileable": False, "maximum_edge_error": .025}
    if not isinstance(policy, dict) or set(policy) - defaults.keys():
        raise ValueError("unsupported material quality policy")
    policy = {**defaults, **policy}
    for key in ("minimum_size", "maximum_png_bytes"):
        if type(policy[key]) is not int or not 1 <= policy[key] <= 32*1024*1024:
            raise ValueError("invalid material quality bound: " + key)
    for key in ("maximum_normal_error", "maximum_edge_error"):
        if type(policy[key]) not in (int, float) or not math.isfinite(policy[key]) or not 0 <= policy[key] <= 1:
            raise ValueError("invalid material quality bound: " + key)
    if type(policy["require_tileable"]) is not bool:
        raise ValueError("require_tileable must be boolean")
    bundle = load_material_bundle(folder)
    decoded = {name: decode_png(bundle["pngs"][name]) for name in ("base_color", "normal", "orm")}
    normal = decoded["normal"][2]
    errors = [abs(math.sqrt(sum((2*c/255-1)**2 for c in normal[i:i+3]))-1) for i in range(0, len(normal), 3)]
    edge_errors = {}
    for name, (w, h, data) in decoded.items():
        horizontal = [abs(data[(y*w)*3+c]-data[(y*w+w-1)*3+c])/255 for y in range(h) for c in range(3)]
        vertical = [abs(data[x*3+c]-data[((h-1)*w+x)*3+c])/255 for x in range(w) for c in range(3)]
        edge_errors[name] = {"mean": max(sum(horizontal)/len(horizontal), sum(vertical)/len(vertical)),
                             "maximum": max(horizontal+vertical)}
    png_bytes = sum(len(data) for data in bundle["pngs"].values())
    width, height = bundle["dimensions"]
    checks = [
        {"type": "complete-integrity-color-space-contract", "passed": True},
        {"type": "minimum-map-size", "passed": min(width, height) >= policy["minimum_size"]},
        {"type": "texture-byte-budget", "passed": png_bytes <= policy["maximum_png_bytes"]},
        {"type": "unit-normal-length", "passed": max(errors) <= policy["maximum_normal_error"]},
    ]
    if policy["require_tileable"]:
        checks.append({"type": "opposite-edge-pixel-agreement", "passed": all(r["maximum"] <= policy["maximum_edge_error"] for r in edge_errors.values())})
    measurements = {"dimensions": [width, height], "png_bytes": png_bytes,
                    "maximum_normal_error": max(errors), "opposite_edges": edge_errors}
    if width == height:
        measurements["size"] = width
    return {"schema": "axm.material-quality/v1", "status": "PASS" if all(r["passed"] for r in checks) else "FAIL",
            "manifest_sha256": bundle["manifest_sha256"], "policy": policy, "checks": checks,
            "measurements": measurements,
            "limitations": ["Pixel agreement does not prove perceptually seamless repetition or mip padding.",
                "Map integrity and unit normals do not prove artistic quality, scanned realism or mesh-aware wear."]}


def bound_specification(root, inputs):
    specification = copy.deepcopy(inputs.get("specification"))
    if isinstance(specification, str):
        specification = json.loads(_target(root, specification).read_text(encoding="utf-8"))
    bindings = inputs.get("materials")
    if not isinstance(specification, dict) or specification.get("schema") != "axm.surface-3d/v0.1":
        raise ValueError("native material binding requires an explicit surface specification")
    if not isinstance(bindings, dict) or not bindings or len(bindings) > 16:
        raise ValueError("materials must map 1..16 surface group ids to verified bundle paths")
    groups = {p["id"]: p for p in specification.get("primitives", [])}
    if set(bindings) - groups.keys():
        raise ValueError("material binding names an unknown surface group")
    for name, value in bindings.items():
        if not isinstance(value, dict) or set(value) - {"path", "wrap"} or "path" not in value:
            raise ValueError("material binding requires path and optional wrap")
        group = groups[name]
        if "textures" in group:
            raise ValueError("binding cannot silently replace existing surface textures")
        bundle = load_material_bundle(_target(root, value["path"]))
        group["textures"] = texture_set_from_bundle(bundle, wrap=value.get("wrap", "clamp"))
        # Factors and vertex colors remain caller-controlled linear multipliers.
    return specification


def asset_quality(root, inputs):
    path = _target(root, inputs.get("asset"))
    body = path.read_bytes()
    geometry = verify_glb(body)
    meshes = GamePoseAsset(body).sample(vertices=True)["meshes"]
    points = [p for mesh in meshes for p in mesh["positions"]]
    bounds = {"min": [min(p[i] for p in points) for i in range(3)], "max": [max(p[i] for p in points) for i in range(3)]}
    size = [bounds["max"][i]-bounds["min"][i] for i in range(3)]
    uv = inspect_material_uv_density(path)
    threshold = inputs.get("minimum_texels_per_m", 64)
    if type(threshold) not in (int, float) or not math.isfinite(threshold) or not 0 < threshold <= 100000:
        raise ValueError("minimum_texels_per_m must be positive and bounded")
    densities = [b["texels_per_m"]["p10"] for p in uv["primitives"] for b in p.get("bindings", [])]
    checks = [{"type": "native-geometry-and-textures", "passed": geometry["passed"]},
              {"type": "texture-coverage", "passed": geometry["textured_primitives"] == geometry["primitives"]},
              {"type": "uv-density", "passed": bool(densities) and min(densities) >= threshold},
              {"type": "uv-findings", "passed": not uv["findings"]}]
    if "maximum_size_m" in inputs:
        maximum = inputs["maximum_size_m"]
        if not isinstance(maximum, list) or len(maximum) != 3 or any(type(v) not in (int, float) or not math.isfinite(v) or not 0 < v <= 100000 for v in maximum):
            raise ValueError("maximum_size_m requires three positive finite metre bounds")
        checks.append({"type": "maximum-world-dimensions", "passed": all(size[i] <= maximum[i]+1e-6 for i in range(3))})
    return {"schema": "axm.textured-asset-quality/v1", "status": "PASS" if all(r["passed"] for r in checks) else "FAIL",
            "artifact_sha256": hashlib.sha256(path.read_bytes()).hexdigest(), "checks": checks,
            "minimum_texels_per_m": threshold, "geometry": geometry, "uv": uv,
            "bounds_m": bounds, "size_m": size,
            "limitations": ["Density is measured, not a universal quality score. Automatic fallback receipts can prove generated chart separation/padding, but not smart seams, tangent parity or engine acceptance."]}


def validate_station(root, kind, inputs):
    if kind in godot_target.KINDS:
        return godot_target.validate_station(root, kind, inputs)
    if kind in mesh_production.KINDS:
        return mesh_production.validate_station(root, kind, inputs)
    if kind not in KINDS or not isinstance(inputs, dict):
        raise ValueError("unsupported material station")
    _target(root, inputs.get("path"))
    if kind == "generate-game-material":
        material_options(inputs)
    if kind in {"bind-textured-asset", "auto-unwrap-bake-asset"}:
        # Existence belongs to execution: upstream stations may create these.
        if not isinstance(inputs.get("materials"), dict):
            raise ValueError("materials mapping is required")
        for value in inputs["materials"].values():
            _target(root, value.get("path"))
    if kind in {"inspect-game-material", "inspect-textured-asset", "render-asset-preview"}:
        _target(root, inputs.get("material" if kind == "inspect-game-material" else "asset"))


def run_station(root, kind, inputs):
    if kind in godot_target.KINDS:
        return godot_target.run_station(root, kind, inputs)
    if kind in mesh_production.KINDS:
        return mesh_production.run_station(root, kind, inputs)
    validate_station(root, kind, inputs)
    target = _target(root, inputs["path"])
    if target.exists():
        raise FileExistsError("material station refuses to overwrite: " + str(target))
    if kind == "generate-game-material":
        return generate_game_material(target, **material_options(inputs))
    if kind == "bind-textured-asset":
        return publish_glb(target, bound_specification(root, inputs))
    if kind == "auto-unwrap-bake-asset":
        return build_auto_uv_bake(target, inputs.get("specification"), inputs.get("materials"), inputs.get("options"),
                                  resolve_material=lambda value: _target(root, value))
    if kind == "render-asset-preview":
        return publish_glb_preview(_target(root, inputs["asset"]), target, **inputs.get("options", {}))
    report = (material_quality(_target(root, inputs["material"]), inputs.get("policy"))
              if kind == "inspect-game-material" else asset_quality(root, inputs))
    atomic_write_json(target, report)
    return report


def observe_station(root, kind, inputs):
    if kind in godot_target.KINDS:
        return godot_target.observe_station(root, kind, inputs)
    if kind in mesh_production.KINDS:
        return mesh_production.observe_station(root, kind, inputs)
    validate_station(root, kind, inputs)
    target = _target(root, inputs["path"])
    checks, details = [], {}
    if kind == "generate-game-material":
        expected = game_material_request("unused", **material_options(inputs))["inputs"]
        bundle = load_material_bundle(target)
        manifest = json.loads(expected["text_files"]["game-material.json"])
        passed = bundle["manifest"] == manifest and all(bundle["pngs"][name] == base64.b64decode(expected["binary_files"][name+".png"]["content"]) for name in manifest["maps"])
        checks = [{"type": "exact-generated-material", "passed": passed}]
    elif kind == "bind-textured-asset":
        expected = build_glb(bound_specification(root, inputs))["body"]
        checks = [{"type": "exact-textured-asset", "passed": target.read_bytes() == expected}]
    elif kind == "auto-unwrap-bake-asset":
        expected = verify_auto_uv_bake(target, inputs.get("specification"), inputs.get("materials"), inputs.get("options"),
                                       resolve_material=lambda value: _target(root, value))
        checks = expected["checks"]
        details = {"unwrap_bake_receipt": expected["receipt"]}
    elif kind == "render-asset-preview":
        expected = render_glb_preview(_target(root, inputs["asset"]).read_bytes(), **inputs.get("options", {}))
        checks = [{"type": "fresh-exact-render", "passed": target.read_bytes() == expected["body"]}]
        details = {"render_receipt": expected["receipt"]}
    else:
        expected = (material_quality(_target(root, inputs["material"]), inputs.get("policy"))
                    if kind == "inspect-game-material" else asset_quality(root, inputs))
        stored = json.loads(target.read_text(encoding="utf-8"))
        checks = [{"type": "fresh-quality-report", "passed": stored == expected}, *expected["checks"]]
        details = {"quality_report": expected}
    return {"status": "PASS" if checks and all(r["passed"] for r in checks) else "FAIL", "checks": checks, **details,
            "visual_quality": "NOT_TESTED", "professional_acceptance": "NOT_TESTED",
            "limitations": ["These are local byte, geometry, map, unwrap/bake and render observations. Aesthetic review and target acceptance remain separate."]}

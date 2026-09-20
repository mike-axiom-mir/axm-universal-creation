"""Small construction/observation adapters; no arbitrary code or claimed simulation."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from .atomic import atomic_write_json
from .atlas_pipeline import _output


def run_station(root, inputs):
    from .material_pipeline import run_station as material_station, bound_specification, asset_quality
    from .procedural_3d import build_glb, publish_glb, verify_glb

    if set(inputs) != {"operation", "path", "values"} or not isinstance(inputs["values"], dict):
        raise ValueError("workflow station requires operation, path and values")
    action, values = inputs["operation"], deepcopy(inputs["values"])
    from .workflow_contracts import load_operators
    operators, _ = load_operators(root)
    contract = next((o for o in operators.values() if o["operation"] == action
                     and o["capability"] == "AXM-CAP-WORKFLOW-STATION"), None)
    if contract is None or set(values) != set(contract["needs"]):
        raise ValueError("unknown workflow station or mismatched input ports")
    target = _output(root, inputs["path"])
    if target.exists():
        raise ValueError("workflow station output already exists")
    target.mkdir(parents=True)
    atomic_write_json(target / "inputs.json", values)
    metrics, status = {}, "PASS"
    if action == "compile-form":
        from .form_pattern import compile_form_pattern
        evidence = compile_form_pattern(values["recipe"])
        value = evidence["specification"]
        verify_glb(build_glb(value)["body"])
        atomic_write_json(target / "surface.json", value)
    elif action == "derive-uvless":
        value = values["surface"]
        before = verify_glb(build_glb(value)["body"])
        if any("textures" in part for part in value["primitives"]):
            raise ValueError("UV derivation needs unbound source geometry")
        for part in value["primitives"]:
            part.pop("texcoords", None)
        after = verify_glb(build_glb(value)["body"])
        evidence = {"before": before, "after": after,
                    "change": "UVs removed from derived geometry; retained input is authoritative."}
        atomic_write_json(target / "surface.json", value)
    elif action == "generate-material":
        value = str(target / "material")
        evidence = material_station(root, "generate-game-material", {"path": value, "recipe": values["recipe"]})
    elif action == "measure-material":
        value = values["material"]
        evidence = material_station(root, "inspect-game-material", {
            "path": str(target / "quality.json"), "material": value, "policy": values["policy"]})
        status = evidence["status"]
        measurements = evidence["measurements"]
        metrics = {"map_size": min(measurements["dimensions"]), "png_bytes": measurements["png_bytes"],
                   "normal_error": measurements["maximum_normal_error"]}
    elif action in {"bind-material", "bake-material"}:
        surface = values["surface"]
        bindings = {p["id"]: {"path": values["material"], "wrap": "clamp"} for p in surface["primitives"]}
        if action == "bind-material":
            value = str(target / "asset.glb")
            evidence = publish_glb(Path(value), bound_specification(root, {"specification": surface, "materials": bindings}))
        else:
            folder = target / "bake"
            evidence = material_station(root, "auto-unwrap-bake-asset", {"path": str(folder),
                "specification": surface, "materials": bindings, "options": values["options"]})
            value = str(folder / "asset.glb")
        verify_glb(Path(value).read_bytes())
    elif action == "measure-asset":
        value = values["asset"]
        if set(values["policy"]) - {"minimum_texels_per_m", "maximum_size_m"}:
            raise ValueError("asset policy contains unsupported fields")
        evidence = asset_quality(root, {"asset": value, **values["policy"]})
        status = evidence["status"]
        densities = [b["texels_per_m"]["p10"] for p in evidence["uv"]["primitives"] for b in p.get("bindings", [])]
        metrics = {"artifact_bytes": Path(value).stat().st_size, "triangles": evidence["geometry"]["triangles"],
                   **{f"size_{axis}_m": size for axis, size in zip("xyz", evidence["size_m"])}}
        if densities:
            metrics["texels_per_m"] = min(densities)
    elif action == "render-preview":
        value = str(target / "preview.png")
        evidence = material_station(root, "render-asset-preview", {
            "path": value, "asset": values["asset"], "options": values["options"]})
        metrics = {key: evidence[key] for key in ("visible_triangles", "texture_shaded_pixels", "width", "height")}
        metrics["png_bytes"] = Path(value).stat().st_size
    elif action == "measure-motion":
        from .character_controller import CharacterController
        evidence = CharacterController(values["recipe"]).measure(**values["probe"])
        metrics = evidence["metrics"]
        value = str(target / "observation.json")
    elif action == "verify-code":
        from .code_creation import create_code_project
        if values["request"].get("action") not in {"verify", "retain"}:
            raise ValueError("workflow code experiments require actual verify or retain execution")
        value = str(target / "project")
        evidence = create_code_project(root, {"path": value, "request": values["request"]})
        report = evidence["code_workflow"]
        status = "PASS" if report["result"] == "VERIFIED_FOR_CASES" else "FAIL"
        metrics = {"cases": report["caseCount"], "requirements": report["requirementCount"],
                   "languages": len(report["languages"])}
    else:
        raise ValueError("workflow station implementation unavailable: " + str(action))
    result = {"status": status, "value": value, "metrics": metrics, "evidence": evidence}
    atomic_write_json(target / "observation.json", result)
    return result

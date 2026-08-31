from __future__ import annotations

import hashlib
import json
import os
import shutil
import struct
import subprocess
from pathlib import Path
from typing import Any

from .visual_learning import inspect_visual_learning, record_visual_use


FORGE_REQUEST_SCHEMA = "axm.3d-forge-request/v0.1"
FORGE_RECEIPT_SCHEMA = "axm.3d-forge-receipt/v0.1"
FORGE_INSPECTION_SCHEMA = "axm.glb-inspection/v0.1"
ASSET_CATALOG = {
    "axiom-bastion-frame": {
        "faction": "axiom",
        "archetype": "heavy-command-walker",
        "scale_meters": 5.8,
        "palette": ["gunmetal", "pale-armor", "electric-cyan", "signal-amber"],
    },
    "mir-sanctuary-keeper": {
        "faction": "mir",
        "archetype": "biomorphic-guardian",
        "scale_meters": 5.4,
        "palette": ["ivory", "brass", "rose-gold", "cyan", "magenta"],
    },
}
LOD_TARGETS = {"lod0": 1.0, "lod1": 0.48, "lod2": 0.18}
BLENDER_BOOTSTRAP = {
    "version": "5.2.1 LTS",
    "windows_x64_url": "https://mirror.blender.org/release/Blender5.2/blender-5.2.1-windows-x64.zip",
    "windows_x64_sha256": "0e631dad7d0cad6d5d18abdd2e2550f6c0213215334eda00ddbd3d22b96ecb2c",
}
AAA_QUALITY_GATES = {
    "minimum_lod0_triangles": 80000,
    "minimum_materials": 5,
    "minimum_embedded_images": 15,
    "minimum_embedded_textures": 15,
    "minimum_render_angles": 4,
    "required_visual_criteria": [
        "aaa-form-hierarchy",
        "non-toy-proportions",
        "functional-topology-all-angles",
        "faction-silhouette",
        "material-authenticity",
    ],
}


def _text(value: Any, field: str, maximum: int = 200) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} must be non-empty")
    if len(result) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return result


def catalog_3d() -> dict[str, Any]:
    return {
        "schema": "axm.3d-forge-catalog/v0.1",
        "truth_status": "EXECUTABLE_BLENDER_BACKED_3D_FORGE",
        "assets": ASSET_CATALOG,
        "lod_targets": LOD_TARGETS,
        "outputs": ["blend", "glb", "png", "json"],
        "bootstrap": BLENDER_BOOTSTRAP,
        "quality_evidence": [
            "decoded GLB structure",
            "mesh and triangle counts",
            "named LOD and collision exports",
            "material role coverage",
            "rendered multi-angle previews",
            "artifact-bound visual acceptance",
        ],
        "aaa_quality_gates": AAA_QUALITY_GATES,
        "truth": {
            "rendererIsExternalRuntime": True,
            "generatorAndVerificationLiveInMachine": True,
            "visualTasteRequiresRenderedReview": True,
        },
    }


def compile_3d_request(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TypeError("3D forge request must be an object")
    asset_id = _text(raw.get("asset_id"), "asset_id").casefold()
    if asset_id not in ASSET_CATALOG:
        raise ValueError(f"unsupported 3D asset: {asset_id}")
    profile = ASSET_CATALOG[asset_id]
    seed = int(raw.get("seed", 0))
    if seed < 0 or seed > 2_147_483_647:
        raise ValueError("seed must be between 0 and 2147483647")
    quality = str(raw.get("quality", "hero")).strip().casefold()
    if quality not in {"hero", "production"}:
        raise ValueError("quality must be hero or production")
    context_key = str(raw.get("context_key") or f"3d/{asset_id}/{quality}").strip()
    if not context_key:
        raise ValueError("context_key must be non-empty")
    return {
        "schema": FORGE_REQUEST_SCHEMA,
        "asset_id": asset_id,
        "faction": profile["faction"],
        "archetype": profile["archetype"],
        "scale_meters": profile["scale_meters"],
        "palette": list(profile["palette"]),
        "seed": seed,
        "quality": quality,
        "context_key": context_key,
        "lod_ratios": dict(LOD_TARGETS),
        "render": {
            "resolution": int(raw.get("render_resolution", 768)),
            "angles_degrees": list(raw.get("angles_degrees", [32, 122, 212, 302])),
            "transparent": bool(raw.get("transparent", False)),
        },
        "requirements": {
            "meters_per_unit": 1.0,
            "grounded_pivot": True,
            "separate_collision_export": True,
            "pbr_material_roles": True,
            "multi_angle_render_proof": True,
            "embedded_pbr_textures": True,
            "artifact_bound_visual_acceptance": True,
        },
        "criteria": list(raw.get("criteria", [])),
        "constraints": list(raw.get("constraints", [])),
        "avoid": list(raw.get("avoid", [])),
        "technical_requirements": {
            **AAA_QUALITY_GATES,
            **(raw.get("technical_requirements", {}) if isinstance(raw.get("technical_requirements"), dict) else {}),
        },
    }


def compile_adaptive_3d_request(root: str | Path, raw: Any) -> dict[str, Any]:
    """Replay only lessons recorded for this exact asset/quality context."""
    normalized = compile_3d_request(raw)
    context_key = normalized["context_key"]
    profile = inspect_visual_learning(root, context_key=context_key)
    context = profile["contexts"].get(context_key, {})
    applied: list[str] = []
    for lesson_id in sorted(context.get("lessons", {})):
        lesson = context["lessons"][lesson_id]
        if lesson.get("status") != "ACTIVE_EXACT_CONTEXT":
            continue
        patch = lesson.get("patch", {})
        for patch_field, target in (
            ("criteria_add", "criteria"),
            ("constraints_add", "constraints"),
            ("avoid_add", "avoid"),
        ):
            for item in patch.get(patch_field, []):
                if item not in normalized[target]:
                    normalized[target].append(item)
        for field, value in patch.get("technical_requirements", {}).items():
            normalized["technical_requirements"].setdefault(field, value)
        applied.append(lesson_id)
    return {
        "schema": "axm.adaptive-3d-forge-request/v0.1",
        "context_key": context_key,
        "learning_status": "EXACT_CONTEXT_LESSONS_REPLAYED" if applied else "NO_EXACT_CONTEXT_LESSONS",
        "applied_lesson_ids": applied,
        "request": normalized,
        "truth": {
            "observationsAreContextBound": True,
            "automaticSourceModification": False,
            "visualAcceptanceIsArtifactBound": True,
        },
    }


def record_3d_review(root: str | Path, review: Any) -> dict[str, Any]:
    """Persist a compact lesson from one rendered proof, never the raw image."""
    if not isinstance(review, dict):
        raise TypeError("3D review must be an object")
    payload = dict(review)
    payload.setdefault("source", "3d-forge-render-proof")
    payload.setdefault("executor", "bounded-visual-review")
    return record_visual_use(root, payload)


def assess_3d_output(receipt: dict[str, Any], manifest: dict[str, Any], visual_review: Any = None) -> dict[str, Any]:
    """Separate engine-export success from artifact-bound AAA acceptance."""
    inspections = receipt.get("inspections", {})
    lod0 = inspections.get("lod0", {})
    exports = manifest.get("exports", {})
    render_proofs = manifest.get("render_proofs", [])
    gates = {
        "lod0-triangle-budget": int(lod0.get("triangles", 0)) >= AAA_QUALITY_GATES["minimum_lod0_triangles"],
        "lod-triangle-descent": int(inspections.get("lod0", {}).get("triangles", 0))
        > int(inspections.get("lod1", {}).get("triangles", 0))
        > int(inspections.get("lod2", {}).get("triangles", 0)) > 0,
        "collision-export": int(inspections.get("collision", {}).get("meshes", 0)) > 0,
        "material-roles": len(lod0.get("materials", [])) >= AAA_QUALITY_GATES["minimum_materials"],
        "embedded-images": int(lod0.get("images", 0)) >= AAA_QUALITY_GATES["minimum_embedded_images"],
        "embedded-textures": int(lod0.get("textures", 0)) >= AAA_QUALITY_GATES["minimum_embedded_textures"],
        "multi-angle-proof": len(render_proofs) >= AAA_QUALITY_GATES["minimum_render_angles"],
        "source-blend": bool(manifest.get("source", {}).get("sha256")),
        "named-exports": all(name in exports for name in ("lod0", "lod1", "lod2", "collision")),
    }
    visual = {"status": "REQUIRED", "criteria": {}, "artifact_sha256": None}
    if visual_review is not None:
        if not isinstance(visual_review, dict):
            raise TypeError("visual_review must be an object")
        valid_artifacts = {row.get("sha256") for row in render_proofs}
        artifact_sha = str(visual_review.get("artifact_sha256", ""))
        criteria = {str(k): str(v).upper() for k, v in visual_review.get("criteria", {}).items()}
        required = AAA_QUALITY_GATES["required_visual_criteria"]
        bound = artifact_sha in valid_artifacts
        passed = bound and all(criteria.get(name) == "PASS" for name in required)
        visual = {
            "status": "PASS" if passed else "FAIL",
            "artifact_sha256": artifact_sha or None,
            "artifact_bound": bound,
            "criteria": criteria,
            "required_criteria": required,
        }
    technical_pass = all(gates.values())
    accepted = technical_pass and visual["status"] == "PASS"
    return {
        "schema": "axm.3d-aaa-acceptance/v0.1",
        "status": "AAA_ACCEPTED" if accepted else "REJECTED_OR_REVIEW_REQUIRED",
        "technical_pass": technical_pass,
        "visual_pass": visual["status"] == "PASS",
        "gates": gates,
        "visual_review": visual,
        "truth": "Export success alone never constitutes AAA acceptance.",
    }


def find_blender(explicit: str | Path | None = None) -> Path:
    candidates: list[Path] = []
    if explicit:
        candidates.append(Path(explicit))
    if os.environ.get("AXM_BLENDER"):
        candidates.append(Path(os.environ["AXM_BLENDER"]))
    discovered = shutil.which("blender")
    if discovered:
        candidates.append(Path(discovered))
    for candidate in candidates:
        resolved = candidate.expanduser().resolve()
        if resolved.is_file():
            return resolved
    raise FileNotFoundError(
        "Blender was not found. Set AXM_BLENDER or use --blender after running the verified bootstrap."
    )


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def inspect_glb(path: str | Path) -> dict[str, Any]:
    target = Path(path).resolve()
    data = target.read_bytes()
    if len(data) < 20:
        raise ValueError("GLB is too short")
    magic, version, length = struct.unpack_from("<4sII", data, 0)
    if magic != b"glTF" or version != 2 or length != len(data):
        raise ValueError("artifact is not a complete GLB v2 container")
    json_length, json_kind = struct.unpack_from("<I4s", data, 12)
    if json_kind != b"JSON":
        raise ValueError("GLB first chunk is not JSON")
    payload = json.loads(data[20:20 + json_length].decode("utf-8").rstrip(" \t\r\n\x00"))
    accessors = payload.get("accessors", [])
    meshes = payload.get("meshes", [])
    triangles = 0
    primitives = 0
    for mesh in meshes:
        for primitive in mesh.get("primitives", []):
            primitives += 1
            if primitive.get("mode", 4) != 4:
                continue
            index = primitive.get("indices")
            if isinstance(index, int) and index < len(accessors):
                triangles += int(accessors[index].get("count", 0)) // 3
    nodes = payload.get("nodes", [])
    return {
        "schema": FORGE_INSPECTION_SCHEMA,
        "truth_status": "DECODED_GLTF_STRUCTURE",
        "path": str(target),
        "bytes": len(data),
        "sha256": _sha256(target),
        "generator": payload.get("asset", {}).get("generator"),
        "scenes": len(payload.get("scenes", [])),
        "nodes": len(nodes),
        "node_names": [row.get("name", "") for row in nodes],
        "meshes": len(meshes),
        "primitives": primitives,
        "triangles": triangles,
        "materials": [row.get("name", "") for row in payload.get("materials", [])],
        "images": len(payload.get("images", [])),
        "textures": len(payload.get("textures", [])),
    }


def forge_3d_asset(
    root: str | Path,
    request: Any,
    output: str | Path,
    *,
    blender: str | Path | None = None,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    machine_root = Path(root).resolve()
    # Every forge run replays exact-context observations. A caller can still
    # override learned defaults explicitly in the request.
    normalized = compile_adaptive_3d_request(machine_root, request)["request"]
    target = Path(output).resolve()
    target.mkdir(parents=True, exist_ok=True)
    request_path = target / "forge-request.json"
    request_path.write_text(json.dumps(normalized, indent=2) + "\n", encoding="utf-8", newline="\n")
    executable = find_blender(blender)
    script = machine_root / "tools" / "blender" / "axm_blender_forge.py"
    if not script.is_file():
        raise FileNotFoundError(f"machine 3D forge script is missing: {script}")
    command = [
        str(executable), "--background", "--factory-startup", "--python", str(script), "--",
        "--request", str(request_path), "--output", str(target),
    ]
    completed = subprocess.run(command, capture_output=True, text=True, timeout=timeout_seconds, check=False)
    (target / "blender.stdout.txt").write_text(completed.stdout, encoding="utf-8", newline="\n")
    (target / "blender.stderr.txt").write_text(completed.stderr, encoding="utf-8", newline="\n")
    if completed.returncode != 0:
        raise RuntimeError(f"Blender forge failed with code {completed.returncode}; inspect blender.stderr.txt")
    manifest_path = target / "asset-manifest.json"
    if not manifest_path.is_file():
        raise RuntimeError("Blender forge did not produce asset-manifest.json")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    inspections = {}
    for lod in ("lod0", "lod1", "lod2", "collision"):
        relative = manifest["exports"][lod]["path"]
        inspections[lod] = inspect_glb(target / relative)
    receipt = {
        "schema": FORGE_RECEIPT_SCHEMA,
        "truth_status": "BLENDER_FORGE_EXECUTED_AND_GLB_DECODED",
        "asset_id": normalized["asset_id"],
        "blender": str(executable),
        "request": str(request_path),
        "manifest": str(manifest_path),
        "inspections": inspections,
        "render_proofs": manifest.get("render_proofs", []),
    }
    receipt["acceptance"] = assess_3d_output(receipt, manifest)
    receipt_path = target / "forge-receipt.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8", newline="\n")
    return receipt

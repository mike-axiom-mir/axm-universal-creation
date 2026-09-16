"""Product-specific plans and executable draft recipes over existing UC crews.

The recipe compiler is not another agent coordinator. It uses the existing
stepwise plan contract and profession crew runner; judgments remain explicit.
"""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

from .atomic import atomic_write_json
from .capabilities import CapabilityStore
from .profession_crew import SUPPORTED, _catalog, _fingerprint, _id, _load, _target, plan_crew, run_crew, verify_run
from .stepwise_workflow import validate_step_plan


def _stage(identity, owner, evidence, gate="observe"):
    return {"id": identity, "profession_id": owner, "expected_evidence": evidence, "gate": gate}


BRIEF = _stage("brief", "art-director", "Purpose, audience, target device, units, budget and explicit acceptance conditions", "declared")
DIRECTION = _stage("direction", "art-director", "References/provenance, composition, palette, material identity and detail hierarchy", "review")
MATERIAL = [
    _stage("surface-intent", "3d-artist", "Physical scale, substrate/coating, channel meanings and colour-space contract", "declared"),
    _stage("maps", "3d-artist", "Base colour, normal, roughness, metallic, AO, height and optional protected wear layers"),
    _stage("map-checks", "technical-artist", "Decoded images, normal direction/length, budgets and declared tiling policy"),
    _stage("look-development", "graphics-engineer", "Actual maps rendered on the product at intended scale under multiple lights"),
]
ASSET = [
    _stage("blockout", "3d-artist", "Silhouette, dimensions, primary forms and assembly relationships", "review"),
    _stage("geometry", "3d-artist", "Primary/secondary forms, normals, winding, pivots, sockets and topology"),
    _stage("uv-layout", "technical-artist", "Noncollapsed UVs, texel density, seams, overlaps, padding and scale"),
    *MATERIAL,
    _stage("assembly", "technical-artist", "Textures bound to exact parts; contacts, clearances and mounts inspected"),
]
ENDING = [
    _stage("refinement", "art-director", "Defect-led revision with preserved source, previous version and fresh downstream checks", "review"),
    _stage("target-validation", "software-qa-playtest", "Actual target import/runtime, budgets, accessibility and required edge cases", "target"),
    _stage("delivery", "integration-release-engineer", "Editable source, artifacts, dependencies, licenses, instructions and unresolved limits", "review"),
    _stage("retained-practice", "software-maintainer", "Distinct local observations; transfer only within compatible context", "observe"),
]
PROFILES = {
    "material": {"work_type": "3d", "stages": [BRIEF, DIRECTION, *MATERIAL, *ENDING]},
    "static-3d": {"work_type": "3d", "stages": [BRIEF, DIRECTION, *ASSET,
        _stage("lod-collision", "technical-artist", "Distance/detail comparison, collision representation and placement checks"), *ENDING]},
    "animated-3d": {"work_type": "animation", "stages": [BRIEF, DIRECTION, *ASSET,
        _stage("rig-deformation", "technical-artist", "Hierarchy, bind pose, weights, deformation extremes and attachment stability"),
        _stage("motion", "motion-designer", "Timing, contact, arcs, secondary motion, loops and transitions"),
        _stage("motion-inspection", "software-qa-playtest", "Multiple sampled poses and live continuous playback in the target", "target"), *ENDING]},
    "game": {"work_type": "game", "stages": [BRIEF, DIRECTION,
        _stage("playable-loop", "gameplay-engineer", "Start, primary verbs, feedback, loss/retry, victory and input parity"),
        _stage("rules", "game-systems-designer", "Deterministic state, progression, solvability and explicit tradeoffs"),
        _stage("world", "world-encounter-designer", "Traversal, reachability, pacing, spawns, encounters and spatial readability"),
        _stage("asset-production", "technical-artist", "Static/animated product workflows for constituent assets"),
        _stage("audio-feedback", "sound-designer", "Event-linked sounds, mix hierarchy, levels and hearing accessibility"),
        _stage("playtest", "software-qa-playtest", "Real runtime controls, complete round, edge states and device performance", "target"), *ENDING]},
    "software": {"work_type": "software", "stages": [
        _stage("brief", "software-architect", "Users, problem, interfaces, privacy and explicit acceptance conditions", "declared"),
        _stage("architecture", "software-architect", "Data ownership, interfaces, offline behavior, failure and recovery", "review"),
        _stage("implementation", "backend-engineer", "Working source, bounded dependencies and meaningful behavior"),
        _stage("verification", "software-qa-playtest", "Runtime behavior, errors, save/recovery, compatibility and resource measurements"), *ENDING]},
    "web": {"work_type": "web", "stages": [BRIEF, DIRECTION,
        _stage("interaction", "frontend-engineer", "User flow and empty/loading/error/success states", "review"),
        _stage("implementation", "frontend-engineer", "Functional source, responsive layout and semantic controls"),
        _stage("verification", "software-qa-playtest", "Browser actions, screenshots, keyboard/touch and accessible states", "target"), *ENDING]},
    "image": {"work_type": "web", "stages": [BRIEF, DIRECTION,
        _stage("composition", "visual-designer", "Hierarchy, focal point, shape language, contrast and typography", "review"),
        _stage("layers", "visual-designer", "Editable construction, masks, edges, colour management and export sizes"),
        _stage("image-inspection", "art-director", "Rendered image at intended size; edges, crops, readability and artefacts", "review"), *ENDING]},
    "audio": {"work_type": "audio", "stages": [
        _stage("brief", "sound-designer", "Purpose, timing, playback context and loudness constraints", "declared"),
        _stage("source-design", "sound-designer", "Source provenance, synthesis/editing and sonic identity", "review"),
        _stage("mix", "sound-designer", "Layering, envelopes, frequency balance and headroom"),
        _stage("listening", "sound-designer", "Actual listening, clipping, loops, transitions and playback systems", "review"), *ENDING]},
}

# Shared lifecycle phases keep domain-appropriate ownership.
for _kind, _profile in PROFILES.items():
    _profile["stages"] = copy.deepcopy(_profile["stages"])
    for _row in _profile["stages"]:
        if _row["id"] == "refinement" and _kind in {"software", "web", "audio"}:
            _row["profession_id"] = {"software": "software-maintainer", "web": "visual-designer", "audio": "sound-designer"}[_kind]
        if _row["id"] == "retained-practice":
            _row["profession_id"] = {"material": "technical-artist", "static-3d": "technical-artist", "animated-3d": "technical-artist",
                "game": "game-systems-designer", "image": "visual-designer", "audio": "sound-designer"}.get(_kind, "software-maintainer")


def _brief(inputs):
    brief = inputs.get("brief")
    if not isinstance(brief, dict):
        raise ValueError("product brief must be an object")
    for key in ("purpose", "target", "quality_intent"):
        if not isinstance(brief.get(key), str) or not 1 <= len(brief[key].strip()) <= 4000:
            raise ValueError("brief requires explicit " + key)
    if len(json.dumps(brief, allow_nan=False)) > 32000:
        raise ValueError("brief exceeds 32 KB")
    return copy.deepcopy(brief)


def plan_product(root, inputs):
    kind = inputs.get("product_type")
    if kind not in PROFILES:
        raise ValueError("product_type must be one of: " + ", ".join(PROFILES))
    brief, profile = _brief(inputs), copy.deepcopy(PROFILES[kind])
    bindings = inputs.get("stage_actions", {})
    if not isinstance(bindings, dict) or set(bindings) - {s["id"] for s in profile["stages"]}:
        raise ValueError("stage_actions contains unknown product stages")
    catalog = {row["id"]: row for row in _catalog()["professions"]}
    steps, previous, gaps = [], [], []
    for stage in profile["stages"]:
        step = {"id": stage["id"], "purpose": stage["expected_evidence"], "depends_on": previous,
                "expected_evidence": [stage["expected_evidence"]], "mode": "analysis",
                "perspective_focus": stage["profession_id"], "stop_condition": "Unresolved evidence or required judgment holds this stage"}
        if stage["id"] in bindings:
            action = bindings[stage["id"]]
            if not isinstance(action, dict):
                raise ValueError("stage action must be an object")
            step.update(mode="action", action=copy.deepcopy(action))
            stage["live_route"] = CapabilityStore(root).route(action.get("kind")) is not None
            stage["crew_observer"] = action.get("kind") in SUPPORTED
        else:
            gaps.append({"stage": stage["id"], "owner": stage["profession_id"], "needed": stage["expected_evidence"]})
        steps.append(step)
        previous = [stage["id"]]
        stage["professional_scope"] = catalog[stage["profession_id"]]["body"]["scope"]
    return {"schema": "axm.product-workflow-plan/v1", "product_type": kind, "brief": brief,
            "stages": profile["stages"], "unbound_stages": gaps,
            "stepwise_plan": validate_step_plan({"goal": brief["purpose"], "steps": steps}),
            "draft_recipe_available": kind in {"material", "static-3d", "software", "web"},
            "status": "PLANNED", "truth": "Product-specific work contracts. Unbound stages are work to do, not executed specialists or acceptance."}


def compile_draft(root, inputs):
    plan = plan_product(root, inputs)
    kind, brief = inputs["product_type"], plan["brief"]
    if kind not in {"material", "static-3d", "software", "web"}:
        raise ValueError("this product currently has a plan; supply actions to the stepwise workflow for execution")
    path = _target(root, inputs.get("path"))
    crew_id, run_id = _id(inputs.get("crew_id", "products"), "crew_id"), _id(inputs.get("run_id"), "run_id")
    steps, artifacts = [], []
    def add(identity, owner, action_kind, destination, **params):
        artifact = path / destination
        steps.append({"id": identity, "profession_id": owner,
            "depends_on": [steps[-1]["id"]] if steps else [],
            "purpose": identity.replace("-", " "),
            "action": {"kind": action_kind, "inputs": {"path": str(artifact), **params}}})
        if action_kind == "generate-game-material":
            steps[-1]["skill_id"] = "surface-authoring"
        artifacts.append(destination)
    parent = None
    if inputs.get("refines"):
        previous = _target(root, inputs["refines"])
        if previous.parent == path or previous.parent in path.parents or path in previous.parents:
            raise ValueError("refinement must use a separate sibling product directory")
        prior = json.loads(previous.read_text(encoding="utf-8"))
        if prior.get("schema") != "axm.product-delivery/v1" or prior.get("product_type") != kind:
            raise ValueError("refinement requires a prior delivery of the same product type")
        if not isinstance(inputs.get("revision_reason"), str) or not inputs["revision_reason"].strip():
            raise ValueError("refinement requires an explicit revision reason")
        parent = {"manifest": str(previous), "sha256": hashlib.sha256(previous.read_bytes()).hexdigest(),
                  "reason": inputs["revision_reason"]}
    canonical = {"schema": "axm.product-source/v1", "product_type": kind, "brief": brief,
                 "recipe": copy.deepcopy(inputs.get("recipe", {})), "specification": copy.deepcopy(inputs.get("specification")),
                 "files": copy.deepcopy(inputs.get("files")), "parent": parent,
                 "quality_contract": {k: copy.deepcopy(inputs.get(k)) for k in ("material_policy", "minimum_texels_per_m", "maximum_size_m", "preview", "checks")},
                 "source_status": "DECLARED_INTENT; not an aesthetic approval"}
    owner = {"software": "software-architect", "web": "visual-designer"}.get(kind, "art-director")
    add("brief-source", owner, "json-file", "source.json", value=canonical)
    if kind in {"material", "static-3d"}:
        recipes = inputs.get("recipe")
        if not isinstance(recipes, dict) or not 1 <= len(recipes) <= 8:
            raise ValueError("recipe maps 1..8 named materials to generator parameters")
        bindings = {}
        for name, recipe in recipes.items():
            _id(name, "material name")
            destination = "materials/" + name
            add("generate-"+name, "3d-artist", "generate-game-material", destination, recipe=recipe)
            add("check-"+name, "technical-artist", "inspect-game-material", "checks/"+name+".json",
                material=str(path/destination), policy=inputs.get("material_policy", {}))
            bindings[name] = {"path": str(path/destination), "wrap": "clamp"}
        if kind == "static-3d":
            add("textured-assembly", "technical-artist", "bind-textured-asset", "asset.glb",
                specification=inputs.get("specification"), materials=bindings)
            add("uv-geometry-check", "technical-artist", "inspect-textured-asset", "checks/asset.json",
                asset=str(path/"asset.glb"), minimum_texels_per_m=inputs.get("minimum_texels_per_m", 64))
            if "maximum_size_m" in inputs:
                steps[-1]["action"]["inputs"]["maximum_size_m"] = copy.deepcopy(inputs["maximum_size_m"])
            options = {"width": 480, "height": 360, "supersample": 1, **inputs.get("preview", {})}
            for light in ("studio", "garage"):
                add("preview-"+light, "graphics-engineer", "render-asset-preview", "previews/"+light+".png",
                    asset=str(path/"asset.glb"), options={**options, "lighting": light})
    else:
        project_type = "python" if kind == "software" else "static-web"
        action = "python-project" if kind == "software" else "static-web-project"
        owner = "backend-engineer" if kind == "software" else "frontend-engineer"
        add("implementation", owner, action, "project", files=inputs.get("files"), checks=inputs.get("checks", []))
        add("fresh-verification", "software-qa-playtest", "verify-project", "project", project_type=project_type,
            expected_files=inputs.get("files"), checks=inputs.get("checks", []))
    job = {"crew_id": crew_id, "run_id": run_id, "goal": brief["purpose"], "work_type": PROFILES[kind]["work_type"],
           "context": {"product_type": kind, "target": brief["target"], "quality_intent": brief["quality_intent"]}, "steps": steps}
    # Existing crew and stepwise contracts validate the compiled sequence.
    plan_crew(root, job)
    return {"plan": plan, "job": job, "artifacts": list(dict.fromkeys(artifacts)), "path": path, "parent": parent}


def build_product(root, inputs):
    compiled = compile_draft(root, inputs)
    job, path = compiled["job"], compiled["path"]
    if path.exists() and job["run_id"] not in _load(root, job["crew_id"])["runs"]:
        raise FileExistsError("new product draft requires a new directory")
    # Replay is handled by the crew; it never repeats writes after interruption.
    record = run_crew(root, job)
    fresh = verify_run(root, job)
    manifest_path = path / "delivery.json"
    if record.get("replayed"):
        current = verify_product(root, {"path": str(manifest_path)}) if manifest_path.is_file() else {"status": "NOT_CURRENT_PASS"}
        return {"status": "RECORDED_DRAFT" if current["status"] == "PASS" else "HOLD_STALE_OR_INCOMPLETE",
                "run": record, "fresh": fresh, "delivery": str(manifest_path), "replayed": True}
    rows = []
    for name in compiled["artifacts"]:
        artifact = path/name
        if artifact.exists():
            rows.append({"path": name, "fingerprint": _fingerprint(artifact)})
    status = "DRAFT_BUILT_REVIEW_REQUIRED" if fresh["status"] == "PASS" else record["status"]
    stage_observations = _stage_observations(inputs["product_type"], compiled["plan"], record)
    manifest = {"schema": "axm.product-delivery/v1", "product_type": inputs["product_type"], "status": status,
                "crew_id": job["crew_id"], "run_id": job["run_id"], "parent": compiled["parent"],
                "artifacts": rows, "plan": compiled["plan"], "fresh_verification": fresh["status"],
                "observed_stations": [r["station"] for r in record["observations"]],
                "stage_observations": stage_observations,
                "remaining_work": [s for s in stage_observations if s["status"] != "OBSERVED_BOUNDED"],
                "professional_acceptance": "NOT_TESTED", "visual_quality": "NOT_TESTED", "released": False,
                "truth": "Executable draft recipe completed only where observed. Product lifecycle planning does not certify artistic, target or final delivery acceptance."}
    path.mkdir(parents=True, exist_ok=True)
    if manifest_path.exists():
        raise FileExistsError("delivery manifest already exists")
    atomic_write_json(manifest_path, manifest)
    return {"status": status, "delivery": str(manifest_path), "run": record, "fresh": fresh, "manifest": manifest}


def _stage_observations(kind, plan, record):
    observed = {r["station"] for r in record["observations"] if r["status"] == "PASS"}
    result = []
    for stage in plan["stages"]:
        identity = stage["id"]
        station_ids = []
        status, scope = "PENDING", stage["expected_evidence"]
        if identity in {"brief", "direction", "surface-intent"} and "brief-source" in observed:
            status, station_ids = "DECLARED", ["brief-source"]
        if identity == "maps":
            station_ids = sorted(s for s in observed if s.startswith("generate-"))
            if station_ids:
                status, scope = "OBSERVED_BOUNDED", "Exact generated maps; no artistic acceptance"
        if identity == "map-checks":
            station_ids = sorted(s for s in observed if s.startswith("check-"))
            expected = [s["id"] for s in record["plan"]["stations"] if s["id"].startswith("check-")]
            if station_ids and set(station_ids) == set(expected):
                status, scope = "OBSERVED_BOUNDED", "Fresh map quality checks against explicit policy"
        if identity in {"geometry", "uv-layout", "assembly"} and "uv-geometry-check" in observed:
            status, station_ids = "PARTIAL", ["textured-assembly", "uv-geometry-check"]
            scope = "Geometry, texture coverage and UV density measured; topology/seams/overlaps/padding/mounts remain unverified"
        if identity == "look-development" and {"preview-studio", "preview-garage"} <= observed:
            status, station_ids = "PARTIAL", ["preview-studio", "preview-garage"]
            scope = "Exact texture renders in two lighting profiles; aesthetic judgment remains open"
        if identity == "implementation" and "implementation" in observed:
            status, station_ids = "OBSERVED_BOUNDED", ["implementation"]
            scope = "Supplied source published and checked; generated source is not semantic acceptance"
        if identity == "verification" and "fresh-verification" in observed:
            status, station_ids = "PARTIAL", ["fresh-verification"]
            scope = "Project checks only; real user behavior and target execution remain separate"
        if identity == "retained-practice" and observed:
            status, station_ids = "OBSERVED_BOUNDED", sorted(observed)
            scope = "Existing crew stores distinct local observations; no rank or automatic recipe synthesis"
        result.append({"stage": identity, "profession_id": stage["profession_id"], "status": status,
                       "observed_stations": station_ids, "scope": scope})
    return result


def verify_product(root, inputs):
    path = _target(root, inputs.get("path"))
    manifest = json.loads(path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "axm.product-delivery/v1":
        raise ValueError("unsupported product delivery")
    checks = []
    for row in manifest["artifacts"]:
        artifact = _target(root, str(path.parent/row["path"]))
        if not artifact.is_relative_to(path.parent):
            raise ValueError("delivery artifact escapes product directory")
        checks.append({"path": row["path"], "same_artifact": artifact.exists() and _fingerprint(artifact) == row["fingerprint"]})
    fresh = verify_run(root, manifest)
    return {"status": "PASS" if checks and all(r["same_artifact"] for r in checks) and fresh["status"] == "PASS" else "NOT_CURRENT_PASS",
            "artifacts": checks, "fresh": fresh, "released": False, "professional_acceptance": "NOT_TESTED"}


def operate_product_workflow(root, inputs):
    root = Path(root).resolve()
    operation = inputs.get("operation", "catalog")
    if operation == "catalog":
        return {"schema": "axm.product-workflow-catalog/v1", "products": copy.deepcopy(PROFILES),
                "draft_recipes": ["material", "static-3d", "software", "web"],
                "orchestration": "Existing profession crews and stepwise workflows; no autonomous aesthetic judgment"}
    if operation == "plan":
        return plan_product(root, inputs)
    if operation in ("build", "refine"):
        if operation == "refine" and not inputs.get("refines"):
            raise ValueError("refine requires a previous delivery manifest")
        return build_product(root, inputs)
    if operation == "verify":
        return verify_product(root, inputs)
    raise ValueError("unsupported product workflow operation")

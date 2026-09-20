"""Direction-first routing and request-scoped candidate overlays.

The router does not replace capability manifests with a second registry.  It
derives every route claim from the currently installed manifests, compares those
claims with one explicit direction contract, and either executes a sufficient
exact route or returns a typed HOLD.  A caller may also supply bounded candidate
manifests; those are tested and optionally invoked outside the live registry.
"""
from __future__ import annotations

import copy
import hashlib
import json
import re
import shutil
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .candidate import test_capability_candidate
from .capabilities import CapabilityError, CapabilityStore


CONTRACT_SCHEMA = "axm.direction-contract/v0.1"
DECISION_SCHEMA = "axm.direction-route-decision/v0.1"
INSTANCE_SCHEMA = "axm.temporary-candidate-instance/v0.1"
ROUTE_STATES = (
    "COMPATIBLE_AND_SUFFICIENT",
    "COMPATIBLE_BUT_INSUFFICIENT",
    "INCOMPATIBLE",
    "UNKNOWN_HOLD",
)
CONTRACT_FIELDS = {
    "purpose", "deliverables", "medium", "dimensionality", "motion",
    "subjects", "environment", "interaction", "platform_use", "quality_bar",
    "editability", "reusable_assets", "provenance", "constraints",
    "verification", "ambiguity",
}
DISPOSITIONS = {
    "discard",
    "retain-artifact-only",
    "retain-recipe-outside-canon",
    "generalize-reusable-candidate",
    "propose-admission",
}


def _digest(value: Any) -> str:
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return "sha256:" + hashlib.sha256(body.encode("utf-8")).hexdigest()


def _words(value: str) -> set[str]:
    ignored = {
        "a", "an", "and", "as", "at", "be", "by", "for", "from", "in",
        "into", "is", "it", "of", "on", "or", "that", "the", "this", "to",
        "using", "with",
    }
    return {word for word in re.findall(r"[a-z0-9]+", value.casefold()) if len(word) > 1 and word not in ignored}


def _list(value: Any, field: str) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, list):
        values = value
    else:
        raise ValueError(f"direction contract {field} must be text or a list of text")
    normalized = []
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"direction contract {field} entries must be non-empty text")
        normalized.append(item.strip())
    return list(dict.fromkeys(normalized))


def _required(value: Any, field: str) -> dict[str, Any]:
    if value is None:
        return {"required": False, "details": []}
    if isinstance(value, bool):
        return {"required": value, "details": []}
    if isinstance(value, str):
        return {"required": value.casefold() not in {"none", "not-required", "false"}, "details": [value.strip()]}
    if isinstance(value, list):
        details = _list(value, field)
        return {"required": bool(details), "details": details}
    if isinstance(value, dict):
        unexpected = set(value) - {"required", "details"}
        if unexpected or not isinstance(value.get("required", False), bool):
            raise ValueError(f"direction contract {field} requires boolean required and optional details")
        return {"required": value.get("required", False), "details": _list(value.get("details"), field)}
    raise ValueError(f"direction contract {field} is invalid")


def compile_direction_contract(raw_request: Any) -> dict[str, Any]:
    if not isinstance(raw_request, dict):
        raise TypeError("direction request must be an object")
    prompt = raw_request.get("prompt") or raw_request.get("direction") or raw_request.get("purpose")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("direction request requires non-empty prompt, direction, or purpose text")
    prompt = prompt.strip()
    lower = prompt.casefold()
    explicit = raw_request.get("direction_contract", {})
    if not isinstance(explicit, dict) or set(explicit) - CONTRACT_FIELDS:
        raise ValueError("direction_contract contains unsupported fields")

    if re.search(r"\b(3d|three[- ]dimensional|spatial|glb)\b", lower):
        medium, dimensionality = "3d", "3d"
    elif re.search(r"\b(game|playable)\b", lower):
        medium, dimensionality = "game", "unspecified"
    elif re.search(r"\b(web|website|browser)\b", lower):
        medium, dimensionality = "web", "2d"
    elif re.search(r"\b(2d|image|illustration|poster|svg)\b", lower):
        medium, dimensionality = "image", "2d"
    elif re.search(r"\b(text|markdown|document)\b", lower):
        medium, dimensionality = "text", "not-applicable"
    else:
        medium, dimensionality = "unspecified", "unspecified"

    deliverables = []
    for token, label in (("demonstration", "demonstration"), ("demo", "demonstration"),
                         ("game", "game"), ("asset", "asset"), ("project", "project")):
        if re.search(rf"\b{token}\b", lower):
            deliverables.append(label)
    subjects = [label for token, label in (("human", "human"), ("character", "character"),
                ("ai collaborator", "AI collaborator"), ("boat", "boat")) if token in lower]
    environment = [label for token, label in (("tv", "TV"), ("world", "world"),
                   ("room", "room"), ("island", "island")) if re.search(rf"\b{token}\b", lower)]
    interactions = []
    if "hand control" in lower or "tracked hand" in lower or "hand tracking" in lower:
        interactions.append("tracked hand controls")
    elif re.search(r"\b(controls?|interactive|interaction|controller|touch)\b", lower):
        interactions.append("interactive controls")
    if "ai collaborator" in lower:
        interactions.append("AI collaborator")
    platform = [label for token, label in (("tv", "TV"), ("browser", "browser"),
                ("web", "web"), ("game", "game runtime")) if re.search(rf"\b{token}\b", lower)]
    ambiguity = []
    if medium == "unspecified":
        ambiguity.append("medium")
    if not deliverables:
        ambiguity.append("deliverables")

    inferred = {
        "purpose": prompt,
        "deliverables": list(dict.fromkeys(deliverables)),
        "medium": medium,
        "dimensionality": dimensionality,
        "motion": {"required": bool(re.search(r"\b(animated?|animation|motion|moving)\b", lower)), "details": []},
        "subjects": list(dict.fromkeys(subjects)),
        "environment": list(dict.fromkeys(environment)),
        "interaction": {"required": bool(interactions), "details": list(dict.fromkeys(interactions))},
        "platform_use": list(dict.fromkeys(platform)),
        "quality_bar": "high" if re.search(r"\b(high[- ]quality|polished|production[- ]quality|cinematic)\b", lower) else "standard",
        "editability": "required" if re.search(r"\b(editable|source[- ]available)\b", lower) else "unspecified",
        "reusable_assets": "required" if re.search(r"\b(reusable|reuse|portable assets?)\b", lower) else "unspecified",
        "provenance": "preserve",
        "constraints": {},
        "verification": ["artifact verification"],
        "ambiguity": ambiguity,
    }
    merged = {**inferred, **copy.deepcopy(explicit)}
    for field in ("deliverables", "subjects", "environment", "platform_use", "verification", "ambiguity"):
        merged[field] = _list(merged.get(field), field)
    for field in ("motion", "interaction"):
        merged[field] = _required(merged.get(field), field)
    for field in ("purpose", "medium", "dimensionality", "quality_bar", "editability", "reusable_assets", "provenance"):
        if not isinstance(merged.get(field), str) or not merged[field].strip():
            raise ValueError(f"direction contract {field} must be non-empty text")
        merged[field] = merged[field].strip()
    if not isinstance(merged.get("constraints"), dict):
        raise ValueError("direction contract constraints must be an object")
    contract = {"schema": CONTRACT_SCHEMA, **merged, "source_language": prompt}
    contract["contract_digest"] = _digest(contract)
    return contract


def _requirements(contract: dict[str, Any]) -> set[str]:
    required = {"artifact"} if contract["deliverables"] else set()
    medium = contract["medium"].casefold()
    dimensionality = contract["dimensionality"].casefold()
    if medium != "unspecified":
        required.add("medium:" + medium)
    if dimensionality in {"2d", "3d"}:
        required.add("dimensionality:" + dimensionality)
    if contract["motion"]["required"]:
        required.add("motion")
    if contract["interaction"]["required"]:
        required.add("interaction")
    details = " ".join(contract["interaction"]["details"]).casefold()
    if "tracked hand" in details or "hand tracking" in details:
        required.add("tracked-input")
    if "ai collaborator" in details:
        required.add("ai-collaboration")
    if contract["editability"].casefold() == "required":
        required.add("editability")
    if contract["reusable_assets"].casefold() == "required":
        required.add("reusable-assets")
    if contract["quality_bar"].casefold() == "high":
        required.add("quality-process")
    if contract["verification"]:
        required.add("verification")
    return required


def _manifest_text(manifest: dict[str, Any], include_limits: bool = False) -> str:
    fields = [manifest.get("id"), manifest.get("purpose"), manifest.get("handles"), manifest.get("input_contract"), manifest.get("output_contract")]
    if include_limits:
        fields.append(manifest.get("limitations"))
    return json.dumps(fields, ensure_ascii=False, sort_keys=True).casefold()


def _profile(manifest: dict[str, Any], prompt_words: set[str], inputs: dict[str, Any]) -> dict[str, Any]:
    declared = json.dumps(
        [manifest.get("id"), manifest.get("purpose"), manifest.get("handles"), manifest.get("output_contract")],
        ensure_ascii=False,
        sort_keys=True,
    ).casefold()
    limits = " ".join(str(value).casefold() for value in manifest.get("limitations", []))
    claims: set[str] = set()
    evidence: dict[str, list[str]] = {}

    def claim(feature: str, basis: str) -> None:
        claims.add(feature)
        evidence.setdefault(feature, []).append(basis)

    output = manifest.get("output_contract", {})
    output_kind = str(output.get("kind", "")).casefold()
    handles = " ".join(str(value).casefold() for value in manifest.get("handles", []))
    purpose = str(manifest.get("purpose", "")).casefold()
    if output_kind and output_kind not in {"measurement", "descriptor"}:
        claim("artifact", "output_contract.kind=" + output_kind)
    if any(token in declared for token in ("glb", "procedural-3d", "static-3d", "animated-3d", "3d scene", "mesh-production")):
        claim("medium:3d", "manifest output/handle declares 3D or GLB")
        claim("dimensionality:3d", "manifest output/handle declares 3D or GLB")
    if any(token in handles + " " + output_kind for token in ("static-web", "browser", "webgl", "web-project")):
        claim("medium:web", "manifest handle/output declares web or browser runtime")
    if any(token in handles + " " + output_kind for token in ("game", "playable")):
        claim("medium:game", "manifest handle/output declares game/playable output")
    if any(token in handles + " " + output_kind for token in ("image", "svg", "paintgun-visual")):
        claim("medium:image", "manifest handle/output declares image/SVG visual output")
        claim("dimensionality:2d", "manifest handle/output declares image/SVG visual output")
    if any(token in handles + " " + output_kind for token in ("text-file", "markdown", "document", "file")):
        claim("medium:text", "manifest handle/output declares textual file output")
    if any(token in declared for token in ("animation", "motion", "rigged", "pose")):
        claim("motion", "manifest contract explicitly names motion/animation/pose evidence")
    if any(token in handles + " " + output_kind for token in ("game", "interactive", "browser", "runtime")) or "interaction" in purpose:
        claim("interaction", "manifest handle/output declares an interactive or runtime surface")
    if any(token in declared for token in ("hand tracking", "tracked hand", "tracked input")):
        claim("tracked-input", "manifest contract explicitly names tracked input")
    if any(token in declared for token in ("ai collaborator", "machine collaborator")):
        claim("ai-collaboration", "manifest contract explicitly names an AI collaborator")
    if output_kind in {"file", "text", "text-file"} or any(token in declared for token in ("editable", "source", "recipe", "project", "package")):
        claim("editability", "manifest contract retains project, source, recipe, or package state")
    if any(token in declared for token in ("reusable", "recipe", "asset package", "material bundle", "portable")):
        claim("reusable-assets", "manifest contract declares reusable recipe/package/material state")
    if any(token in declared for token in ("verify", "validate", "inspect", "observer", "evidence", "receipt")):
        claim("verification", "manifest contract declares verification, observation, or receipts")
    if any(token in declared for token in ("aftertouch", "judge", "refine", "product-workflow", "quality process", "quality workflow")):
        claim("quality-process", "manifest contract declares bounded judgment/refinement/quality work")

    contradictions = []
    if "svg/static-web renderer" in limits or "not a physically accurate 3d" in limits:
        contradictions.append("does not provide the requested 3D production surface")
    if "animation" in limits and any(token in limits for token in ("not part", "unsupported", "does not")):
        contradictions.append("animation is outside the declared route")
    if "artistic acceptance" in limits or "aesthetic" in limits and "not" in limits:
        contradictions.append("aesthetic acceptance remains outside the route")

    required_inputs = CapabilityStore.required_inputs(manifest, inputs)
    missing_inputs = CapabilityStore.missing_required_inputs(manifest, inputs)
    manifest_words = _words(_manifest_text(manifest, include_limits=True))
    semantic_overlap = sorted(prompt_words & manifest_words)
    return {
        "capability_id": manifest.get("id"),
        "version": manifest.get("version"),
        "handles": copy.deepcopy(manifest.get("handles", [])),
        "claims": sorted(claims),
        "claim_evidence": evidence,
        "contradictions": contradictions,
        "required_inputs": required_inputs,
        "missing_required_inputs": missing_inputs,
        "semantic_overlap": semantic_overlap,
        "dependencies": copy.deepcopy(manifest.get("dependencies", [])),
        "manifest_path": manifest.get("_manifest_path"),
    }


def _classify(profile: dict[str, Any], required: set[str]) -> dict[str, Any]:
    claims = set(profile["claims"])
    covered = sorted(required & claims)
    missing = sorted(required - claims)
    has_conflicting_dimension = (
        "dimensionality:3d" in required and "dimensionality:2d" in claims
        and "dimensionality:3d" not in claims
    )
    if not required:
        state = "UNKNOWN_HOLD"
    elif not missing and not profile["missing_required_inputs"] and not profile["contradictions"]:
        state = "COMPATIBLE_AND_SUFFICIENT"
    elif covered or profile["semantic_overlap"] or (has_conflicting_dimension and "medium:image" in claims):
        state = "COMPATIBLE_BUT_INSUFFICIENT"
    elif has_conflicting_dimension:
        state = "INCOMPATIBLE"
    else:
        state = "UNKNOWN_HOLD"
    return {**profile, "state": state, "covered_requirements": covered, "missing_requirements": missing}


def _unique_inferred_route(routes: list[dict[str, Any]]) -> tuple[dict[str, Any] | None, str | None]:
    """Infer one exact live route only when installed evidence makes it unambiguous.

    This never invents route inputs and never executes a composition graph.  It
    exists so ordinary language plus already-complete route inputs can reach one
    clearly best installed capability without requiring the caller to know UC's
    internal handle name.
    """
    candidates = [
        route for route in routes
        if route["state"] == "COMPATIBLE_AND_SUFFICIENT"
        and not route["missing_required_inputs"]
        and not route["contradictions"]
        and route["handles"]
        and len(route["semantic_overlap"]) >= 2
    ]
    if not candidates:
        return None, None
    scored = sorted(
        candidates,
        key=lambda route: (
            -len(route["semantic_overlap"]),
            -len(route["covered_requirements"]),
            str(route["capability_id"]),
        ),
    )
    top = scored[0]
    top_score = (len(top["semantic_overlap"]), len(top["covered_requirements"]))
    tied = [
        route for route in scored
        if (len(route["semantic_overlap"]), len(route["covered_requirements"])) == top_score
    ]
    if len(tied) != 1:
        return None, None
    return top, str(top["handles"][0])


def _composition(routes: list[dict[str, Any]], required: set[str]) -> dict[str, Any]:
    missing = set(required)
    selected: list[dict[str, Any]] = []
    remaining = [
        route for route in routes
        if route["state"] != "INCOMPATIBLE"
        and not any("does not provide the requested 3D" in item for item in route["contradictions"])
    ]
    while missing and remaining and len(selected) < 8:
        pool = remaining
        if not selected:
            core = {feature for feature in required if feature.startswith("medium:") or feature.startswith("dimensionality:")}
            anchored = [route for route in remaining if core and core <= set(route["claims"])]
            if anchored:
                pool = anchored
        if not selected and pool is not remaining:
            pool.sort(key=lambda route: (
                -len(route["semantic_overlap"]),
                -len(missing & set(route["claims"])),
                len(route["missing_required_inputs"]),
                str(route["capability_id"]),
            ))
        else:
            pool.sort(key=lambda route: (
                -len(missing & set(route["claims"])),
                -len(route["semantic_overlap"]),
                len(route["missing_required_inputs"]),
                str(route["capability_id"]),
            ))
        route = pool[0]
        remaining.remove(route)
        coverage = sorted(missing & set(route["claims"]))
        if not coverage:
            break
        selected.append({
            "capability_id": route["capability_id"],
            "handles": route["handles"],
            "covers": coverage,
            "missing_required_inputs": route["missing_required_inputs"],
            "dependencies": route["dependencies"],
            "claim_evidence": {feature: route["claim_evidence"][feature] for feature in coverage},
        })
        missing -= set(coverage)
    return {
        "state": "COMPATIBLE_AND_SUFFICIENT" if not missing else "COMPATIBLE_BUT_INSUFFICIENT",
        "steps": selected,
        "covered_requirements": sorted(required - missing),
        "missing_requirements": sorted(missing),
        "execution_ready": not missing and all(not step["missing_required_inputs"] for step in selected),
        "selection_basis": "bounded greedy coverage over claims derived from installed manifests; this is a plan, not semantic or execution proof",
    }


def _content_gaps(request: dict[str, Any], contract: dict[str, Any]) -> list[str]:
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    keys = set(inputs)
    gaps = list(contract["ambiguity"])
    if contract["dimensionality"].casefold() == "3d" and not keys & {"recipe", "scene", "specification", "asset", "files"}:
        gaps.append("explicit 3D scene, recipe, specification, asset, or source files")
    interaction = " ".join(contract["interaction"]["details"]).casefold()
    if ("tracked hand" in interaction or "hand tracking" in interaction) and not keys & {"control_contract", "interaction_contract", "tracking_input"}:
        gaps.append("tracked-hand input and calibration contract")
    if "ai collaborator" in interaction and not keys & {"collaborator_contract", "agent_contract"}:
        gaps.append("AI collaborator behavior, authority, and failure contract")
    if contract["quality_bar"].casefold() == "high" and not keys & {"acceptance", "quality_evidence", "reference"}:
        gaps.append("rendered quality evidence or an explicit acceptance contract")
    return list(dict.fromkeys(gaps))


def _live_digest(root: Path) -> str:
    rows = []
    for path in sorted((root / "capabilities" / "live").glob("*.json")):
        rows.append([path.name, hashlib.sha256(path.read_bytes()).hexdigest()])
    return _digest(rows)


def _candidate_workspace(root: Path, spec: dict[str, Any], contract: dict[str, Any]) -> Path:
    value = spec.get("path")
    if value is None:
        value = root / "creations" / "temporary-candidates" / contract["contract_digest"].split(":", 1)[1][:16]
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = root / path
    path = path.resolve()
    try:
        relative = path.relative_to(root)
    except ValueError:
        return path
    if not relative.parts or relative.parts[0] != "creations":
        raise ValueError("temporary candidate workspace must be under creations/ or outside the machine root")
    return path


def _verified_execution(result: Any) -> bool:
    if not isinstance(result, dict):
        return False
    if result.get("passed") is True or result.get("verified") is True:
        return True
    validation = result.get("validation")
    if isinstance(validation, dict) and (validation.get("passed") is True or validation.get("status") == "PASS"):
        return True
    return result.get("fresh_verification") == "PASS"


def run_temporary_candidate_instance(root: Path, contract: dict[str, Any], raw_spec: Any) -> dict[str, Any]:
    if not isinstance(raw_spec, dict):
        raise ValueError("candidate_instance must be an object")
    allowed = {"path", "manifest", "manifests", "execution_inputs", "execute", "disposition", "replace"}
    if set(raw_spec) - allowed:
        raise ValueError("candidate_instance contains unsupported fields")
    manifests = raw_spec.get("manifests")
    if manifests is None:
        manifests = [raw_spec.get("manifest")]
    if not isinstance(manifests, list) or not 1 <= len(manifests) <= 4 or any(not isinstance(item, dict) for item in manifests):
        raise ValueError("candidate_instance requires one to four candidate manifests")
    disposition = str(raw_spec.get("disposition", "retain-recipe-outside-canon")).strip().casefold()
    if disposition not in DISPOSITIONS:
        raise ValueError("unsupported candidate disposition")
    execute = raw_spec.get("execute", True)
    replace = raw_spec.get("replace", False)
    if not isinstance(execute, bool) or not isinstance(replace, bool):
        raise ValueError("candidate execute and replace flags must be boolean")
    execution_inputs = raw_spec.get("execution_inputs", {})
    if not isinstance(execution_inputs, dict):
        raise ValueError("candidate execution_inputs must be an object")

    workspace = _candidate_workspace(root, raw_spec, contract)
    if workspace.exists():
        if not replace:
            raise FileExistsError("temporary candidate workspace already exists")
        shutil.rmtree(workspace)
    workspace.mkdir(parents=True)
    atomic_write_json(workspace / "direction-contract.json", contract)
    before = _live_digest(root)
    attempts = []
    selected_manifest = None
    for index, manifest in enumerate(manifests, 1):
        candidate = copy.deepcopy(manifest)
        candidate["status"] = "candidate"
        attempt = workspace / f"attempt-{index:02d}"
        attempt.mkdir()
        candidate_path = attempt / "candidate.json"
        atomic_write_json(candidate_path, candidate)
        test = test_capability_candidate(root, candidate_path)
        atomic_write_json(attempt / "test.json", test)
        attempts.append({
            "attempt": index,
            "candidate": candidate.get("id"),
            "passed": test.get("passed") is True,
            "candidate_path": str(candidate_path),
            "test_path": str(attempt / "test.json"),
        })
        if test.get("passed") is True:
            selected_manifest = candidate
            break

    execution = None
    execution_error = None
    if selected_manifest is not None and execute:
        try:
            execution = CapabilityStore(root).invoke(selected_manifest, copy.deepcopy(execution_inputs))
        except CapabilityError as exc:
            execution_error = {"message": str(exc), "details": exc.details}
        except Exception as exc:  # Evidence is retained; the live registry is still untouched.
            execution_error = {"message": str(exc), "exception": type(exc).__name__}
        atomic_write_json(workspace / "execution.json", execution if execution_error is None else {"error": execution_error})

    after = _live_digest(root)
    canonical_unchanged = before == after
    verified_artifact = execution is not None and _verified_execution(execution)
    status = (
        "HOLD_CANDIDATE_TEST_FAILED" if selected_manifest is None
        else "HOLD_CANDIDATE_EXECUTION_FAILED" if execution_error is not None
        else "VERIFIED_ARTIFACT" if verified_artifact
        else "VERIFIED_CANDIDATE_NO_ARTIFACT" if not execute
        else "HOLD_ARTIFACT_NOT_INDEPENDENTLY_VERIFIED"
    )
    if disposition == "retain-artifact-only" and not verified_artifact:
        disposition = "retain-recipe-outside-canon"
    if disposition in {"discard", "retain-artifact-only"}:
        for path in workspace.glob("attempt-*/candidate.json"):
            path.unlink(missing_ok=True)
    receipt = {
        "schema": INSTANCE_SCHEMA,
        "status": status,
        "contract_digest": contract["contract_digest"],
        "workspace": str(workspace),
        "attempts": attempts,
        "repair_attempt_count": max(0, len(attempts) - 1),
        "execution": execution,
        "execution_error": execution_error,
        "artifact_independently_verified": verified_artifact,
        "disposition": disposition,
        "canonical_live_digest_before": before,
        "canonical_live_digest_after": after,
        "canonical_live_unchanged": canonical_unchanged,
        "installed": False,
        "registered": False,
        "routed_in_canon": False,
        "automatic_canon_admission": False,
    }
    atomic_write_json(workspace / "instance-receipt.json", receipt)
    return receipt


def direction_routing_summary() -> dict[str, Any]:
    return {
        "contract_schema": CONTRACT_SCHEMA,
        "decision_schema": DECISION_SCHEMA,
        "route_states": list(ROUTE_STATES),
        "temporary_candidate_schema": INSTANCE_SCHEMA,
        "candidate_dispositions": sorted(DISPOSITIONS),
        "manifest_derived_claims": True,
        "unique_best_route_inference": "allowed only with complete inputs, >=2 semantic overlaps, no tie, and a sufficient live route",
        "composition_auto_execution": False,
        "automatic_canon_admission": False,
        "truth_boundary": "A route name or produced artifact is insufficient when the direction contract is not covered. Unknown semantics, missing inputs, and unverified outputs remain typed HOLDs.",
    }


def route_direction(root: Path, raw_request: Any) -> dict[str, Any]:
    root = Path(root).resolve()
    request = copy.deepcopy(raw_request)
    contract = compile_direction_contract(request)
    required = _requirements(contract)
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    prompt_words = _words(contract["source_language"])
    store = CapabilityStore(root)
    manifests = [manifest for manifest in store.live() if manifest.get("id") != "AXM-CAP-DIRECTION-ROUTER"]
    routes = [_classify(_profile(manifest, prompt_words, inputs), required) for manifest in manifests]
    routes.sort(key=lambda route: (
        0 if route["state"] == "COMPATIBLE_AND_SUFFICIENT" else 1 if route["state"] == "COMPATIBLE_BUT_INSUFFICIENT" else 2,
        -len(route["covered_requirements"]),
        -len(route["semantic_overlap"]),
        str(route["capability_id"]),
    ))
    kind = request.get("kind")
    exact = next((route for route in routes if isinstance(kind, str) and kind in route["handles"]), None)
    inferred_kind = None
    route_selection = "caller-explicit-kind" if exact is not None else "none"
    if exact is None and kind is None:
        exact, inferred_kind = _unique_inferred_route(routes)
        if exact is not None:
            route_selection = "unique-best-installed-route-from-direction-and-complete-inputs"
    execution_kind = kind if isinstance(kind, str) else inferred_kind
    composition = _composition(routes, required)
    gaps = _content_gaps(request, contract)
    if exact is not None:
        gaps.extend("missing route input: " + value for value in exact["missing_required_inputs"])
        gaps.extend("route requirement: " + value for value in exact["missing_requirements"])
        gaps.extend("route contradiction: " + value for value in exact["contradictions"])
    gaps = list(dict.fromkeys(gaps))
    decision = {
        "schema": DECISION_SCHEMA,
        "contract": contract,
        "required_route_features": sorted(required),
        "requested_kind": kind,
        "inferred_kind": inferred_kind,
        "route_selection": route_selection,
        "exact_route": exact,
        "candidate_routes": routes,
        "production_graph": composition,
        "gaps": gaps,
        "registry_source": "current live capability manifests",
        "selection_is_semantic_proof": False,
    }
    decision["decision_digest"] = _digest(decision)

    if "candidate_instance" in request:
        instance = run_temporary_candidate_instance(root, contract, request["candidate_instance"])
        result_type = "DIRECTION_RESULT" if instance["status"] == "VERIFIED_ARTIFACT" else "DIRECTION_HOLD"
        return {"type": result_type, "decision": decision, "candidate_instance": instance,
                "truth_status": instance["status"]}

    execute = request.get("execute", True)
    if not isinstance(execute, bool):
        raise ValueError("direction request execute must be boolean")
    if exact is not None and exact["state"] == "COMPATIBLE_AND_SUFFICIENT" and not gaps:
        if not execute:
            return {"type": "DIRECTION_ROUTE_PLAN", "truth_status": "SUFFICIENT_ROUTE_NOT_EXECUTED", "decision": decision}
        manifest = store.route(str(execution_kind))
        if manifest is None:
            return {
                "type": "DIRECTION_HOLD",
                "truth_status": "HOLD_SELECTED_ROUTE_NOT_LIVE",
                "decision": decision,
            }
        try:
            result = store.invoke(manifest, inputs)
        except CapabilityError as exc:
            return {"type": "DIRECTION_HOLD", "truth_status": "HOLD_ROUTE_EXECUTION_FAILED", "decision": decision,
                    "error": {"message": str(exc), "details": exc.details}}
        return {"type": "DIRECTION_RESULT", "truth_status": "EXECUTED_COMPATIBLE_AND_SUFFICIENT_ROUTE",
                "decision": decision, "capability": manifest.get("id"), "result": result}

    hold = (
        "HOLD_EXACT_ROUTE_INSUFFICIENT" if exact is not None
        else "HOLD_COMPOSITION_INPUTS_OR_SEMANTICS_REQUIRED" if composition["steps"]
        else "HOLD_NO_COMPATIBLE_ROUTE"
    )
    if not gaps and exact is None:
        decision["gaps"] = ["no exact executable route was selected from ordinary language alone"]
    return {"type": "DIRECTION_HOLD", "truth_status": hold, "decision": decision,
            "safe_next_step": "supply the missing bounded contracts or a detached candidate instance; canonical UC remains unchanged"}

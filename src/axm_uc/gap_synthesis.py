from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .capabilities import CapabilityStore
from .spawn import SPAWN_PROPOSAL_SCHEMA, spawn_unit, test_spawned_unit, validate_spawn_proposal


GAP_ANALYSIS_SCHEMA = "axm.creation-gap-analysis/v0.1"
GAP_PROPOSAL_RESULT_SCHEMA = "axm.creation-gap-proposal-result/v0.1"
GAP_EXPLORATION_RESULT_SCHEMA = "axm.creation-gap-exploration-result/v0.1"
EXACT_TEXT_ALIAS_BLUEPRINT = "axm.blueprint.exact-utf8-file-route-alias/v0.1"
SUPPORTED_OPERATIONS = ("analyze", "propose", "materialize-and-test")
SUPPORTED_IMPLEMENTATIONS = {
    "DETERMINISTIC_SOURCE",
    "DETERMINISTIC_ALIAS",
    "DETERMINISTIC_COMPOSITE",
}
MAX_REQUEST_BYTES = 256 * 1024
SLUG_RE = re.compile(r"[^a-z0-9]+")

ZERO_AUTHORITY = {
    "execute": False,
    "install": False,
    "register": False,
    "promote": False,
    "merge": False,
    "canon": False,
    "permissions": False,
}


class GapSynthesisError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise GapSynthesisError("gap synthesis inputs must be exact JSON-compatible data") from exc


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _required_text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise GapSynthesisError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise GapSynthesisError(f"{label} exceeds its {maximum}-character bound")
    return text


def _slug(value: str, maximum: int = 80) -> str:
    slug = SLUG_RE.sub("-", value.casefold()).strip("-")[:maximum].rstrip("-")
    if len(slug) < 2:
        raise GapSynthesisError("request kind cannot form a stable candidate identifier", {"kind": value})
    return slug


def _normalized_request(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise GapSynthesisError("request must be an object")
    request = copy.deepcopy(value)
    kind = _required_text(request.get("kind"), "request.kind", maximum=128)
    request["kind"] = kind
    if "inputs" not in request:
        request["inputs"] = {}
    if not isinstance(request["inputs"], dict):
        raise GapSynthesisError("request.inputs must be an object")
    encoded = _canonical_bytes(request)
    if len(encoded) > MAX_REQUEST_BYTES:
        raise GapSynthesisError(f"request exceeds the {MAX_REQUEST_BYTES}-byte synthesis bound")
    return request


def _public_manifest(manifest: dict[str, Any]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in manifest.items() if not key.startswith("_")}


def _manifest_digest(root: Path, manifest: dict[str, Any]) -> str:
    relative = manifest.get("_manifest_path")
    if isinstance(relative, str):
        path = Path(root) / relative
        if path.is_file():
            return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"
    return _digest(_public_manifest(manifest))


def _candidate_bridge(root: Path, manifest: dict[str, Any], input_keys: set[str]) -> dict[str, Any] | None:
    capability_id = manifest.get("id")
    if not isinstance(capability_id, str) or not capability_id.strip():
        return None
    required = manifest.get("input_contract", {}).get("required")
    if (
        not isinstance(required, list)
        or any(not isinstance(item, str) or not item for item in required)
        or set(required) != input_keys
        or input_keys != {"path", "content"}
    ):
        return None
    implementation = manifest.get("implementation")
    if not isinstance(implementation, dict) or implementation.get("kind") not in SUPPORTED_IMPLEMENTATIONS:
        return None
    output = manifest.get("output_contract")
    if not isinstance(output, dict) or output.get("kind") != "file" or output.get("encoding") != "utf-8":
        return None
    version = manifest.get("version")
    if not isinstance(version, str) or not version.strip():
        return None
    return {
        "capability_id": capability_id,
        "version": version,
        "ref": f"{capability_id}@{version}",
        "manifest": manifest.get("_manifest_path"),
        "manifest_digest": _manifest_digest(root, manifest),
        "implementation_kind": implementation.get("kind"),
        "required_inputs": sorted(required),
        "output_contract": copy.deepcopy(output),
        "blueprint": EXACT_TEXT_ALIAS_BLUEPRINT,
        "structural_basis": "required inputs are exactly path+content and the live output contract declares an exact UTF-8 file",
        "semantic_equivalence_proven": False,
        "candidate_is_live_route_selection": False,
    }


def _existing_candidate(root: Path, manifest: dict[str, Any], request_kind: str) -> dict[str, Any] | None:
    path = manifest.get("_manifest_path")
    handles = manifest.get("handles")
    if (
        not isinstance(path, str)
        or not path.startswith("capabilities/candidates/")
        or not isinstance(handles, list)
        or request_kind not in handles
    ):
        return None
    capability_id = manifest.get("id")
    version = manifest.get("version")
    if not isinstance(capability_id, str) or not capability_id or not isinstance(version, str) or not version:
        return None
    return {
        "capability_id": capability_id,
        "version": version,
        "ref": f"{capability_id}@{version}",
        "manifest": path,
        "manifest_digest": _manifest_digest(root, manifest),
        "handles": copy.deepcopy(handles),
        "candidate_test_available": True,
        "candidate_is_live": False,
        "candidate_is_admitted": False,
    }


def gap_synthesis_summary() -> dict[str, Any]:
    return {
        "truth_status": "BOUNDED_DETERMINISTIC_GAP_TO_PROPOSAL_COMPILER",
        "analysis_schema": GAP_ANALYSIS_SCHEMA,
        "proposal_result_schema": GAP_PROPOSAL_RESULT_SCHEMA,
        "exploration_result_schema": GAP_EXPLORATION_RESULT_SCHEMA,
        "operations": list(SUPPORTED_OPERATIONS),
        "implemented_blueprints": {
            EXACT_TEXT_ALIAS_BLUEPRINT: "Compile a missing exact UTF-8 file route into a detached alias-capability hypothesis when one compatible live primitive is uniquely visible."
        },
        "gap_trigger_required": True,
        "existing_candidate_reuse_precedes_new_synthesis": True,
        "detached_experiment_allowed": True,
        "semantic_source_invention": False,
        "ambiguous_bridge_auto_selection": False,
        "unsupported_gap_is_hold": True,
        "automatic_admission": False,
        "automatic_install_or_registration": False,
        "automatic_merge_or_canon_change": False,
    }


def analyze_creation_gap(root: Path, raw_request: Any) -> dict[str, Any]:
    root = Path(root).resolve()
    request = _normalized_request(raw_request)
    store = CapabilityStore(root)
    live_manifests = store.live()
    all_manifests = store.registry.capability_manifests(include_candidates=True)
    exact = next((manifest for manifest in live_manifests if request["kind"] in manifest.get("handles", [])), None)
    inputs = request["inputs"]
    existing_candidates = [
        row
        for manifest in all_manifests
        if (row := _existing_candidate(root, manifest, request["kind"])) is not None
    ]
    existing_candidates.sort(key=lambda item: str(item["capability_id"]))
    candidates: list[dict[str, Any]] = []
    if exact is None and not existing_candidates and isinstance(inputs.get("path"), str) and isinstance(inputs.get("content"), str):
        for manifest in live_manifests:
            row = _candidate_bridge(root, manifest, set(inputs))
            if row is not None:
                candidates.append(row)
    candidates.sort(key=lambda item: str(item["capability_id"]))

    if exact is not None:
        status = "COVERED_NO_SYNTHESIS_NEEDED"
        truth_status = "OBSERVED_LIVE_ROUTE"
        selected: dict[str, Any] | None = None
        hold_reason = "the requested kind already has a live route"
    elif len(existing_candidates) == 1:
        status = "REUSE_EXISTING_CANDIDATE_BEFORE_SYNTHESIS"
        truth_status = "OBSERVED_EXISTING_DETACHED_CANDIDATE"
        selected = None
        hold_reason = "one existing detached candidate already handles this request kind; test or inspect it before generating duplicate machinery"
    elif len(existing_candidates) > 1:
        status = "HOLD_AMBIGUOUS_EXISTING_CANDIDATES"
        truth_status = "DETERMINISTIC_AMBIGUITY_HOLD"
        selected = None
        hold_reason = "multiple existing detached candidates handle this request kind; no candidate is silently selected"
    elif len(candidates) == 1:
        status = "SYNTHESIS_READY_UNIQUE_STRUCTURAL_BRIDGE"
        truth_status = "DETERMINISTIC_STRUCTURAL_BRIDGE_HYPOTHESIS"
        selected = copy.deepcopy(candidates[0])
        hold_reason = None
    elif len(candidates) > 1:
        status = "HOLD_AMBIGUOUS_STRUCTURAL_BRIDGE"
        truth_status = "DETERMINISTIC_AMBIGUITY_HOLD"
        selected = None
        hold_reason = "more than one live primitive fits the implemented structural blueprint; no route is silently selected"
    else:
        status = "HOLD_NO_SUPPORTED_SYNTHESIS_BLUEPRINT"
        truth_status = "DETERMINISTIC_UNSUPPORTED_GAP_HOLD"
        selected = None
        hold_reason = "no implemented deterministic blueprint can compile this gap without inventing missing semantics or source"

    exact_route = None
    if exact is not None:
        exact_route = {
            "capability_id": exact.get("id"),
            "version": exact.get("version"),
            "manifest": exact.get("_manifest_path"),
            "manifest_digest": _manifest_digest(root, exact),
        }
    without_digest = {
        "schema": GAP_ANALYSIS_SCHEMA,
        "status": status,
        "truth_status": truth_status,
        "request": request,
        "request_digest": _digest(request),
        "request_kind": request["kind"],
        "observed_live_capability_count": len(live_manifests),
        "exact_live_route": exact_route,
        "implemented_blueprint": EXACT_TEXT_ALIAS_BLUEPRINT,
        "existing_candidates": existing_candidates,
        "candidate_bridges": candidates,
        "selected_bridge": selected,
        "hold_reason": hold_reason,
        "selection_authority": "NONE",
        "semantic_equivalence_proven": False,
        "source_code_invented": False,
        "safe_next_step": (
            "compile and test one detached adapter hypothesis"
            if selected
            else "test or inspect the existing detached candidate"
            if len(existing_candidates) == 1
            else "retain the typed hold or supply an explicit supported bridge/design"
        ),
        "limitations": [
            "matching one input/output shape does not prove that two creation meanings are equivalent",
            "the implemented compiler creates only manifest-level aliases for exact UTF-8 file routes",
            "the request-shaped test proves one supplied example and not general semantic behavior",
            "analysis grants no execution, installation, registration, admission, merge, CANON, or permission authority",
        ],
    }
    return {**without_digest, "analysis_digest": _digest(without_digest)}


def _root_fit(request_kind: str, bridge_id: str) -> dict[str, Any]:
    return {
        "truth": {
            "fit": True,
            "basis": f"The candidate labels the {request_kind!r} route as a structural adapter hypothesis and does not claim semantic equivalence beyond its exact fixture.",
        },
        "agency": {
            "fit": True,
            "basis": "The caller retains the requested content and output choice; the detached proposal grants itself no execution, installation, admission, merge, CANON, or permission authority.",
        },
        "continuity": {
            "fit": True,
            "basis": f"The candidate reuses the declared live dependency {bridge_id} in a detached package without replacing the continuing machine.",
        },
        "wisdom-before-speed": {
            "fit": True,
            "basis": "The compiler emits the smallest currently supported adapter and requires an observed request-shaped test instead of generating a redundant writer implementation.",
        },
    }


def _fixture_path(raw_path: str) -> str:
    normalized = raw_path.replace("\\", "/")
    suffix = PurePosixPath(normalized).suffix.casefold()
    if not suffix or len(suffix) > 16 or any(character not in ".abcdefghijklmnopqrstuvwxyz0123456789" for character in suffix):
        suffix = ".txt"
    return f"${{TEST_DIR}}/request-example{suffix}"


def compile_gap_proposal(
    root: Path,
    raw_request: Any,
    *,
    bridge_capability_id: Any = None,
    candidate_id: Any = None,
    version: Any = "0.1.0",
) -> dict[str, Any]:
    root = Path(root).resolve()
    analysis = analyze_creation_gap(root, raw_request)
    candidates = analysis["candidate_bridges"]
    selected: dict[str, Any] | None = None
    selection_basis: str | None = None

    if bridge_capability_id is not None:
        bridge_id = _required_text(bridge_capability_id, "bridge_capability_id", maximum=160)
        selected = next((item for item in candidates if item["capability_id"] == bridge_id), None)
        if selected is None:
            raise GapSynthesisError(
                "the requested bridge is not an observed candidate for this gap and blueprint",
                {"bridge_capability_id": bridge_id, "observed_candidates": [item["capability_id"] for item in candidates]},
            )
        selection_basis = "caller supplied one exact ID from the observed structural candidates"
    elif len(candidates) == 1:
        selected = candidates[0]
        selection_basis = "the implemented blueprint observed one unique structural bridge; this selects an experiment, not a live route"

    if selected is None:
        return {
            "schema": GAP_PROPOSAL_RESULT_SCHEMA,
            "operation": "propose",
            "status": analysis["status"],
            "truth_status": analysis["truth_status"],
            "analysis": analysis,
            "proposal": None,
            "proposal_digest": None,
            "target_created": False,
            "hold_preserved": True,
        }

    request = analysis["request"]
    request_kind = request["kind"]
    inputs = request["inputs"]
    kind_slug = _slug(request_kind)
    generated_id = f"axm.generated.capability.{kind_slug}"
    unit_id = _required_text(candidate_id if candidate_id is not None else generated_id, "candidate_id", maximum=128)
    unit_version = _required_text(version, "version", maximum=32)
    direction = request.get("direction") or request.get("purpose") or request_kind
    if not isinstance(direction, str) or not direction.strip():
        direction = request_kind
    direction = direction.strip()[:600]
    bridge_id = str(selected["capability_id"])
    bridge_ref = str(selected["ref"])
    current_live = CapabilityStore(root).live()
    existing_ids = sorted(
        str(manifest.get("id"))
        for manifest in current_live
        if isinstance(manifest.get("id"), str)
    )
    if unit_id in existing_ids:
        raise GapSynthesisError(
            "gap synthesis will not shadow an existing live capability identity",
            {"candidate_id": unit_id},
        )
    current_bridge = next(
        (manifest for manifest in current_live if manifest.get("id") == bridge_id),
        None,
    )
    if current_bridge is None:
        raise GapSynthesisError(
            "the selected live bridge disappeared before proposal compilation",
            {"bridge_capability_id": bridge_id},
        )
    current_bridge_digest = _manifest_digest(root, current_bridge)
    if current_bridge_digest != selected["manifest_digest"]:
        raise GapSynthesisError(
            "the selected live bridge changed after gap analysis; re-analyze before compiling",
            {
                "bridge_capability_id": bridge_id,
                "analysis_manifest_digest": selected["manifest_digest"],
                "current_manifest_digest": current_bridge_digest,
            },
        )
    fit = _root_fit(request_kind, bridge_id)
    fixture_path = _fixture_path(str(inputs["path"]))
    content = str(inputs["content"])

    candidate_manifest = {
        "id": unit_id,
        "version": unit_version,
        "status": "candidate",
        "purpose": f"Explore the missing route {request_kind!r} for the directional outcome {direction!r} by reusing the exact UTF-8 file primitive {bridge_id}.",
        "handles": [request_kind],
        "input_contract": {
            "required": ["path", "content"],
            "properties": copy.deepcopy(current_bridge.get("input_contract", {}).get("properties", {})),
        },
        "output_contract": copy.deepcopy(selected["output_contract"]),
        "dependencies": [bridge_id],
        "relationships": [
            {"type": "delegates-to", "target": bridge_id},
            {"type": "explores-gap", "target": analysis["request_digest"]},
        ],
        "implementation": {
            "kind": "DETERMINISTIC_ALIAS",
            "delegate": bridge_id,
            "source": "this generated manifest",
        },
        "limitations": [
            "This is a detached structural adapter hypothesis, not proof that the requested format has no semantics beyond exact UTF-8 text.",
            "The declared test covers only the exact request-shaped content fixture in disposable build space.",
            "The original requested destination is not used during candidate testing.",
        ],
        "persistent_state": None,
        "tests": [
            {
                "inputs": {"path": fixture_path, "content": content},
                "expect": {
                    "file_text": content,
                    "result_fields": {"kind": "text", "bytes": len(content.encode("utf-8"))},
                },
            }
        ],
        "root_fit": copy.deepcopy(fit),
    }
    gap_file = {
        **copy.deepcopy(analysis),
        "proposal_selection": {
            "bridge_capability_id": bridge_id,
            "selection_basis": selection_basis,
            "selection_is_admission_authority": False,
            "selection_is_semantic_proof": False,
        },
    }
    files = {
        "capability.json": _json_text(candidate_manifest),
        "gap-analysis.json": _json_text(gap_file),
    }
    proposal = {
        "schema": SPAWN_PROPOSAL_SCHEMA,
        "id": unit_id,
        "version": unit_version,
        "kind": "capability",
        "purpose": candidate_manifest["purpose"],
        "files": files,
        "implementation": {
            "kind": "DETERMINISTIC_ALIAS",
            "entrypoint": "capability.json",
            "source_files": ["capability.json", "gap-analysis.json"],
        },
        "contracts": {
            "inputs": copy.deepcopy(candidate_manifest["input_contract"]),
            "outputs": copy.deepcopy(candidate_manifest["output_contract"]),
            "provides": [f"creation.route.{kind_slug}"],
            "requires": [f"live.capability.{_slug(bridge_id)}"],
        },
        "dependencies": [{"kind": "capability", "ref": bridge_ref, "optional": False}],
        "relationships": [
            {"type": "delegates-to", "target": bridge_ref},
            {"type": "compiled-from-gap", "target": analysis["request_digest"]},
            {"type": "uses-blueprint", "target": EXACT_TEXT_ALIAS_BLUEPRINT},
        ],
        "verification": {
            "checks": [
                {"type": "json-valid", "path": "capability.json"},
                {"type": "json-valid", "path": "gap-analysis.json"},
            ]
        },
        "provenance": {
            "kind": "deterministic-gap-synthesis",
            "refs": [
                analysis["request_digest"],
                bridge_ref,
                selected["manifest_digest"],
                EXACT_TEXT_ALIAS_BLUEPRINT,
            ],
            "basis": "A real unroutable request exposed a gap; one exact implemented blueprint compiled the observed compatible live primitive into the smallest detached adapter hypothesis.",
        },
        "limitations": copy.deepcopy(candidate_manifest["limitations"]),
        "authority": copy.deepcopy(ZERO_AUTHORITY),
        "root_fit": copy.deepcopy(fit),
    }
    normalized = validate_spawn_proposal(proposal)
    return {
        "schema": GAP_PROPOSAL_RESULT_SCHEMA,
        "operation": "propose",
        "status": "DETACHED_PROPOSAL_READY",
        "truth_status": "DETERMINISTIC_GAP_DERIVED_ADAPTER_PROPOSAL",
        "analysis": analysis,
        "selected_bridge": copy.deepcopy(selected),
        "selection_basis": selection_basis,
        "proposal": normalized,
        "proposal_digest": _digest(normalized),
        "target_created": False,
        "semantic_equivalence_proven": False,
        "admission_requested": False,
    }


def operate_gap_synthesis(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    if operation not in SUPPORTED_OPERATIONS:
        raise GapSynthesisError(
            "unsupported gap synthesis operation",
            {"operation": operation, "supported_operations": list(SUPPORTED_OPERATIONS)},
        )
    request = inputs.get("request")
    if operation == "analyze":
        return {"operation": "analyze", **analyze_creation_gap(root, request)}

    proposed = compile_gap_proposal(
        root,
        request,
        bridge_capability_id=inputs.get("bridge_capability_id"),
        candidate_id=inputs.get("candidate_id"),
        version=inputs.get("version", "0.1.0"),
    )
    if operation == "propose":
        return proposed
    if proposed["proposal"] is None:
        return {
            "schema": GAP_EXPLORATION_RESULT_SCHEMA,
            "operation": "materialize-and-test",
            "status": proposed["status"],
            "truth_status": proposed["truth_status"],
            "passed": False,
            "analysis": proposed["analysis"],
            "proposal": None,
            "proposal_digest": None,
            "target_created": False,
            "hold_preserved": True,
            "installed": False,
            "registered": False,
            "admission_requested": False,
        }

    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise GapSynthesisError("replace must be boolean when supplied")
    target_text = _required_text(inputs.get("path"), "path", maximum=1000)
    target = Path(target_text).expanduser()
    if not target.is_absolute():
        target = Path(root) / target
    target = target.resolve()
    spawned = spawn_unit(target, proposed["proposal"], replace=bool(inputs.get("replace", False)))
    tested = test_spawned_unit(root, target)
    handle = proposed["analysis"]["request_kind"]
    live_after = CapabilityStore(root).route(handle)
    passed = tested.get("passed") is True
    return {
        "schema": GAP_EXPLORATION_RESULT_SCHEMA,
        "operation": "materialize-and-test",
        "status": "TESTED_DETACHED_CANDIDATE" if passed else "HELD_FAILED_TESTS",
        "truth_status": "OBSERVED_REQUEST_SHAPED_DETACHED_GAP_EXPERIMENT",
        "passed": passed,
        "path": str(target),
        "analysis": proposed["analysis"],
        "proposal_digest": proposed["proposal_digest"],
        "selected_bridge": proposed["selected_bridge"],
        "spawn": spawned,
        "test": tested,
        "original_request_destination_used": False,
        "request_fixture_executed_only_in_disposable_test_space": True,
        "live_route_after_experiment": live_after.get("id") if live_after else None,
        "installed": False,
        "registered": False,
        "admission_requested": False,
        "promoted": False,
        "merged": False,
        "canon_changed": False,
        "permissions_changed": False,
        "next_step": "the detached candidate may be inspected, revised, or separately choose to request admission review" if passed else "retain the failed evidence and revise or abandon the hypothesis",
    }

from __future__ import annotations

import copy
import hashlib
import json
import re
from pathlib import Path, PurePosixPath
from typing import Any

from .capabilities import CapabilityStore
from .organ_library import ExecutableOrganError, resolve_organ_assembly
from .organ_discovery import OrganDiscoveryError, discover_interface_assembly
from .organ_project import preview_organ_project
from .project import ProjectError, preview_project_files
from .spawn import SPAWN_PROPOSAL_SCHEMA, spawn_unit, test_spawned_unit, validate_spawn_proposal
from .template import render_project_template


GAP_ANALYSIS_SCHEMA = "axm.creation-gap-analysis/v0.1"
GAP_PROPOSAL_RESULT_SCHEMA = "axm.creation-gap-proposal-result/v0.1"
GAP_EXPLORATION_RESULT_SCHEMA = "axm.creation-gap-exploration-result/v0.1"
EXACT_TEXT_ALIAS_BLUEPRINT = "axm.blueprint.exact-utf8-file-route-alias/v0.1"
BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT = "axm.blueprint.bounded-project-recipe-graph/v0.1"
TEMPLATE_CAPABILITY = ("AXM-CAP-INSTANTIATE-PROJECT-TEMPLATE", "0.2.0")
ORGAN_CAPABILITY = ("AXM-CAP-ASSEMBLE-ORGAN-PROJECT", "0.3.0")
COMPOSE_ORGAN_CAPABILITY = ("AXM-CAP-COMPOSE-ORGAN-PROJECT", "0.1.0")
WRITE_PROJECT_CAPABILITY = ("AXM-CAP-WRITE-PROJECT", "0.6.0")
VERIFIED_FILES_CAPABILITY = ("AXM-CAP-BUILD-VERIFY-PROJECT", "0.2.0")
VERIFY_CAPABILITY = ("AXM-CAP-VERIFY-PROJECT", "0.5.0")
REPORT_CAPABILITY = ("AXM-CAP-WRITE-JSON", "0.1.0")
MAX_PROJECT_RECIPE_STEPS = 3
PROJECT_PRODUCER_PROFILES = (
    {
        "profile": "strict-project-template",
        "marker": "template",
        "capability": TEMPLATE_CAPABILITY,
        "entrypoint": "builtin:instantiate_project_template",
        "output_kind": "templated-project-result",
        "required_inputs": ("path", "template", "variables"),
        "optional_inputs": ("checks", "replace"),
        "already_verified": False,
    },
    {
        "profile": "exact-executable-organ-assembly",
        "marker": "assembly",
        "capability": ORGAN_CAPABILITY,
        "entrypoint": "builtin:assemble_organ_project",
        "output_kind": "organ-assembled-project-result",
        "required_inputs": ("path", "assembly", "variables"),
        "optional_inputs": ("checks", "replace"),
        "already_verified": False,
    },
    {
        "profile": "interface-discovered-organ-assembly",
        "marker": "organ_goal",
        "capability": COMPOSE_ORGAN_CAPABILITY,
        "entrypoint": "builtin:compose_organ_project",
        "output_kind": "interface-composed-organ-project-result",
        "required_inputs": ("path", "organ_goal"),
        "optional_inputs": ("checks", "replace"),
        "already_verified": False,
    },
    {
        "profile": "exact-project-files",
        "marker": "files",
        "capability": WRITE_PROJECT_CAPABILITY,
        "entrypoint": "builtin:write_project",
        "output_kind": "directory",
        "required_inputs": ("path", "files"),
        "optional_inputs": ("project_type", "checks", "replace"),
        "already_verified": False,
    },
    {
        "profile": "existing-verified-project-composite",
        "marker": "files",
        "capability": VERIFIED_FILES_CAPABILITY,
        "implementation_kind": "DETERMINISTIC_COMPOSITE",
        "output_kind": "verified-project-composite-result",
        "required_inputs": ("path", "files"),
        "optional_inputs": ("project_type", "checks", "replace"),
        "already_verified": True,
    },
)
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


def _project_recipe_dependency_issue(
    capability_id: str,
    manifest: dict[str, Any],
    role: str,
    producer_profile: dict[str, Any] | None = None,
) -> str | None:
    implementation = manifest.get("implementation")
    if not isinstance(implementation, dict) or implementation.get("kind") not in SUPPORTED_IMPLEMENTATIONS:
        return "dependency has no supported deterministic implementation"
    input_contract = manifest.get("input_contract")
    output_contract = manifest.get("output_contract")
    if not isinstance(input_contract, dict) or not isinstance(output_contract, dict):
        return "dependency input/output contract is not an object"
    required = input_contract.get("required")
    properties = input_contract.get("properties")
    if not isinstance(required, list) or not isinstance(properties, dict):
        return "dependency contract does not expose required and properties fields"
    if any(not isinstance(item, str) or not item for item in required):
        return "dependency contract required entries must be non-empty text"
    if role == "producer" and producer_profile is not None:
        supported_inputs = set(producer_profile["required_inputs"]) | set(producer_profile["optional_inputs"])
        if not producer_profile["already_verified"]:
            supported_inputs.add("publish_mode")
        missing_inputs = sorted(set(producer_profile["required_inputs"]) - set(required))
        unsupported_required_inputs = sorted(set(required) - supported_inputs)
        missing_properties = sorted(supported_inputs - set(properties))
        contains = output_contract.get("contains")
        if not isinstance(contains, list):
            return "project producer contract does not expose contains fields"
        expected_outputs = (
            {"path", "build", "verification"}
            if producer_profile["already_verified"]
            else {"path", "project_type", "published", "creation_status", "files"}
        )
        missing_outputs = sorted(expected_outputs - set(contains))
        entrypoint = implementation.get("entrypoint")
        expected_implementation = producer_profile.get("implementation_kind", "DETERMINISTIC_SOURCE")
        implementation_issue = implementation.get("kind") != expected_implementation
        entrypoint_issue = (
            expected_implementation == "DETERMINISTIC_SOURCE"
            and entrypoint != producer_profile.get("entrypoint")
        )
        if (
            output_contract.get("kind") != producer_profile["output_kind"]
            or implementation_issue
            or entrypoint_issue
            or missing_inputs
            or unsupported_required_inputs
            or missing_properties
            or missing_outputs
        ):
            return (
                "project producer contract mismatch; "
                f"implementation={implementation.get('kind')!r}, entrypoint={entrypoint!r}, "
                f"missing inputs={missing_inputs}, "
                f"unsupported required inputs={unsupported_required_inputs}, "
                f"missing properties={missing_properties}, missing outputs={missing_outputs}"
            )
    elif role == "verifier" and capability_id == VERIFY_CAPABILITY[0]:
        contains = output_contract.get("contains")
        if not isinstance(contains, list):
            return "verifier dependency contract does not expose contains fields"
        missing_inputs = sorted({"path"} - set(required))
        unsupported_required_inputs = sorted(
            set(required) - {"path", "project_type", "checks", "expected_file_digests"}
        )
        missing_properties = sorted({"expected_file_digests"} - set(properties))
        missing_outputs = sorted({"passed"} - set(contains))
        if (
            output_contract.get("kind") != "project-validation-report"
            or implementation.get("kind") != "DETERMINISTIC_SOURCE"
            or implementation.get("entrypoint") != "builtin:verify_project"
            or missing_inputs
            or unsupported_required_inputs
            or missing_properties
            or missing_outputs
        ):
            return (
                "verifier dependency contract mismatch; "
                f"missing inputs={missing_inputs}, unsupported required inputs={unsupported_required_inputs}, "
                f"missing properties={missing_properties}, missing outputs={missing_outputs}"
            )
    elif role == "reporter" and capability_id == REPORT_CAPABILITY[0]:
        missing_inputs = sorted({"path", "value"} - set(required))
        unsupported_required_inputs = sorted(set(required) - {"path", "value"})
        missing_properties = sorted({"path", "value"} - set(properties))
        if (
            output_contract.get("kind") != "file"
            or output_contract.get("encoding") != "utf-8"
            or output_contract.get("format") != "json"
            or implementation.get("kind") != "DETERMINISTIC_SOURCE"
            or implementation.get("entrypoint") != "builtin:write_json"
            or missing_inputs
            or unsupported_required_inputs
            or missing_properties
        ):
            return (
                "JSON reporter dependency contract mismatch; "
                f"missing inputs={missing_inputs}, unsupported required inputs={unsupported_required_inputs}, "
                f"missing properties={missing_properties}"
            )
    return None


def _preview_project_producer(
    root: Path,
    profile: dict[str, Any],
    inputs: dict[str, Any],
) -> dict[str, Any]:
    if profile["profile"] == "strict-project-template":
        rendered = render_project_template(inputs["template"], inputs["variables"])
        instance = rendered["template_instance"]
        return {
            "project_type": instance["project_type"],
            "files": rendered["files"],
            "evidence": {
                "template_id": instance["template_id"],
                "template_version": instance["template_version"],
                "variables_used": instance["variables_used"],
            },
        }
    if profile["profile"] == "exact-executable-organ-assembly":
        resolved, resolution = resolve_organ_assembly(root, inputs["assembly"])
        preview = preview_organ_project(resolved, inputs["variables"])
        return {
            "project_type": preview["project_type"],
            "files": preview["files"],
            "evidence": {
                "executable_organ_resolution": resolution,
                "organ_assembly": preview["organ_assembly"],
            },
        }
    if profile["profile"] == "interface-discovered-organ-assembly":
        discovery = discover_interface_assembly(root, inputs["organ_goal"])
        if discovery["status"] != "READY_EXACT_INTERFACE_ASSEMBLY":
            raise GapSynthesisError(
                "interface-driven organ discovery is on HOLD",
                {"organ_discovery": discovery},
            )
        resolved, resolution = resolve_organ_assembly(root, discovery["assembly"])
        preview = preview_organ_project(resolved, discovery["variables"])
        return {
            "project_type": preview["project_type"],
            "files": preview["files"],
            "evidence": {
                "organ_discovery": discovery,
                "executable_organ_resolution": resolution,
                "organ_assembly": preview["organ_assembly"],
            },
        }
    if profile["marker"] == "files":
        preview = preview_project_files(inputs["files"], inputs.get("project_type", "generic"))
        if preview["project_type"] not in {"generic", "static-web", "python"}:
            raise ProjectError("project_type must be generic, static-web, or python")
        return {
            **preview,
            "evidence": {
                "exact_request_file_paths": sorted(preview["files"]),
                "existing_verified_composite_reused": profile["already_verified"],
            },
        }
    raise GapSynthesisError(
        "project producer profile has no deterministic preview adapter",
        {"profile": profile.get("profile")},
    )


def _recipe_dependency_observations(
    root: Path,
    live_manifests: list[dict[str, Any]],
    specs: list[tuple[tuple[str, str], str, dict[str, Any] | None]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    dependencies: list[dict[str, Any]] = []
    missing_links: list[dict[str, Any]] = []
    ambiguous_links: list[dict[str, Any]] = []
    for (capability_id, expected_version), role, profile in specs:
        matches = [manifest for manifest in live_manifests if manifest.get("id") == capability_id]
        expected_ref = f"{capability_id}@{expected_version}"
        if not matches:
            missing_links.append({
                "capability_id": capability_id,
                "expected_ref": expected_ref,
                "role": role,
                "reason": "required live capability ID is absent",
            })
            continue
        if len(matches) > 1:
            ambiguous_links.append({
                "capability_id": capability_id,
                "expected_ref": expected_ref,
                "role": role,
                "observed_manifests": sorted(str(item.get("_manifest_path")) for item in matches),
                "reason": "more than one live manifest declares the required capability ID",
            })
            continue
        manifest = matches[0]
        if manifest.get("version") != expected_version:
            missing_links.append({
                "capability_id": capability_id,
                "expected_ref": expected_ref,
                "observed_version": manifest.get("version"),
                "role": role,
                "reason": "the implemented blueprint requires the exact tested dependency version",
            })
            continue
        contract_issue = _project_recipe_dependency_issue(capability_id, manifest, role, profile)
        if contract_issue is not None:
            missing_links.append({
                "capability_id": capability_id,
                "expected_ref": expected_ref,
                "role": role,
                "reason": contract_issue,
            })
            continue
        dependencies.append({
            "capability_id": capability_id,
            "version": expected_version,
            "ref": expected_ref,
            "role": role,
            "manifest": manifest.get("_manifest_path"),
            "manifest_digest": _manifest_digest(root, manifest),
            "implementation_kind": manifest.get("implementation", {}).get("kind"),
        })
    return dependencies, missing_links, ambiguous_links


def _project_recipe_path(
    root: Path,
    live_manifests: list[dict[str, Any]],
    profile: dict[str, Any],
    inputs: dict[str, Any],
    preview: dict[str, Any],
) -> dict[str, Any]:
    report_requested = "report_path" in inputs
    specs: list[tuple[tuple[str, str], str, dict[str, Any] | None]] = [
        (profile["capability"], "producer", profile),
    ]
    step_order = ["produce"]
    edges: list[dict[str, Any]] = []
    if not profile["already_verified"]:
        specs.append((VERIFY_CAPABILITY, "verifier", None))
        step_order.append("verify")
        edges.append({
            "id": "project-file-receipt-to-independent-verification",
            "from": "steps.produce.path+project_type+files",
            "to": "steps.verify.path+project_type+expected_file_digests",
            "binding": "file-digest-map",
            "transform": "file-digest-map",
        })
    if report_requested:
        specs.append((REPORT_CAPABILITY, "reporter", None))
        step_order.append("report")
        verification_source = "steps.produce.verification" if profile["already_verified"] else "steps.verify"
        edges.append({
            "id": "verification-report-to-exact-json-artifact",
            "from": verification_source,
            "to": "steps.report.value",
            "binding": "exact-whole-object",
            "transform": None,
        })

    dependencies, missing_links, ambiguous_links = _recipe_dependency_observations(
        root, live_manifests, specs
    )
    if len(step_order) > MAX_PROJECT_RECIPE_STEPS:
        status = "HOLD_RECIPE_DEPTH_EXCEEDED"
    elif ambiguous_links:
        status = "HOLD_AMBIGUOUS_COMPOSITE_LINK"
    elif missing_links:
        status = "HOLD_MISSING_COMPOSITE_LINK"
    else:
        status = "READY_EXACT_COMPOSITE_CHAIN"
    producer_id, producer_version = profile["capability"]
    return {
        "blueprint": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
        "status": status,
        "producer": {
            "profile": profile["profile"],
            "capability_id": producer_id,
            "version": producer_version,
            "ref": f"{producer_id}@{producer_version}",
            "entrypoint": profile.get("entrypoint"),
            "output_kind": profile["output_kind"],
            "already_verified": profile["already_verified"],
        },
        "goal": "verified-project-with-json-report" if report_requested else "verified-project",
        "required_inputs": [
            *profile["required_inputs"],
            *(["report_path"] if report_requested else []),
        ],
        "optional_inputs": list(profile["optional_inputs"]),
        "project_type": preview.get("project_type"),
        "rendered_paths": sorted(preview.get("files", {})),
        "producer_preview_evidence": copy.deepcopy(preview.get("evidence", {})),
        "step_order": step_order,
        "step_count": len(step_order),
        "maximum_step_count": MAX_PROJECT_RECIPE_STEPS,
        "edges": edges,
        "dependencies": dependencies,
        "missing_links": missing_links,
        "ambiguous_links": ambiguous_links,
        "reuses_existing_verified_composite": profile["already_verified"],
        "runtime_behavior_proven": False,
        "candidate_is_live_route_selection": False,
    }


def _bounded_project_recipe_candidate(
    root: Path,
    live_manifests: list[dict[str, Any]],
    inputs: dict[str, Any],
) -> tuple[dict[str, Any] | None, str | None]:
    input_keys = set(inputs)
    applicable_markers = sorted({
        profile["marker"]
        for profile in PROJECT_PRODUCER_PROFILES
        if profile["marker"] in input_keys
    })
    applicable_profiles = [
        profile for profile in PROJECT_PRODUCER_PROFILES if profile["marker"] in applicable_markers
    ]
    if not applicable_profiles:
        return None, None
    if len(applicable_markers) > 1:
        return {
            "blueprint": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
            "status": "HOLD_AMBIGUOUS_COMPOSITE_RECIPE",
            "applicable_markers": applicable_markers,
            "applicable_producer_profiles": [profile["profile"] for profile in applicable_profiles],
            "dependencies": [],
            "missing_links": [],
            "ambiguous_links": [],
            "runtime_behavior_proven": False,
            "candidate_is_live_route_selection": False,
        }, None

    profile = applicable_profiles[0]
    required = set(profile["required_inputs"])
    optional = set(profile["optional_inputs"])
    allowed = required | optional | {"report_path"}
    missing_inputs = sorted(required - input_keys)
    unexpected_inputs = sorted(input_keys - allowed)
    invalid: list[str] = []
    if missing_inputs:
        invalid.append(f"missing request inputs: {', '.join(missing_inputs)}")
    if unexpected_inputs:
        invalid.append(f"unsupported request inputs: {', '.join(unexpected_inputs)}")
    if "path" in inputs and (not isinstance(inputs["path"], str) or not inputs["path"].strip()):
        invalid.append("path must be non-empty text")
    if "checks" in inputs and not isinstance(inputs["checks"], list):
        invalid.append("checks must be a list when supplied")
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        invalid.append("replace must be boolean when supplied")
    if "project_type" in inputs and not isinstance(inputs["project_type"], str):
        invalid.append("project_type must be text when supplied")
    if "report_path" in inputs and (
        not isinstance(inputs["report_path"], str) or not inputs["report_path"].strip()
    ):
        invalid.append("report_path must be non-empty text when supplied")
    preview: dict[str, Any] | None = None
    if not invalid:
        try:
            preview = _preview_project_producer(root, profile, inputs)
        except (ProjectError, ExecutableOrganError, OrganDiscoveryError, GapSynthesisError) as exc:
            discovery = getattr(exc, "details", {}).get("organ_discovery")
            if isinstance(discovery, dict) and str(discovery.get("status", "")).startswith("HOLD_"):
                return {
                    "blueprint": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
                    "status": discovery["status"],
                    "goal": "verified-project-with-json-report" if "report_path" in inputs else "verified-project",
                    "organ_discovery": discovery,
                    "dependencies": [],
                    "missing_links": [],
                    "ambiguous_links": [],
                    "runtime_behavior_proven": False,
                    "candidate_is_live_route_selection": False,
                }, None
            invalid.append(f"project producer request is not deterministically previewable: {exc}")
    if invalid or preview is None:
        return None, "; ".join(invalid)

    paths = [
        _project_recipe_path(root, live_manifests, candidate_profile, inputs, preview)
        for candidate_profile in applicable_profiles
    ]
    ready = [path for path in paths if path["status"] == "READY_EXACT_COMPOSITE_CHAIN"]
    selectable = ready if ready else paths
    shortest = min(path["step_count"] for path in selectable)
    finalists = [path for path in selectable if path["step_count"] == shortest]
    summaries = [
        {
            "producer_profile": path["producer"]["profile"],
            "producer_ref": path["producer"]["ref"],
            "status": path["status"],
            "step_order": path["step_order"],
            "step_count": path["step_count"],
            "reuses_existing_verified_composite": path["reuses_existing_verified_composite"],
        }
        for path in paths
    ]
    if len(finalists) != 1:
        return {
            "blueprint": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
            "status": "HOLD_AMBIGUOUS_RECIPE_PATH",
            "goal": paths[0]["goal"],
            "candidate_paths": summaries,
            "dependencies": [],
            "missing_links": [],
            "ambiguous_links": [],
            "runtime_behavior_proven": False,
            "candidate_is_live_route_selection": False,
        }, None
    selected = finalists[0]
    selected["candidate_paths"] = summaries
    selected["path_selection"] = {
        "strategy": "shortest ready exact path; no ready path means shortest explicit HOLD",
        "ready_path_count": len(ready),
        "selected_profile": selected["producer"]["profile"],
        "selected_step_count": selected["step_count"],
        "reuse_precedes_new_embodiment": selected["reuses_existing_verified_composite"],
        "selection_is_semantic_proof": False,
    }
    selected["structural_basis"] = (
        "bounded exact-contract graph search selected one shortest complete path from a request-compatible "
        "producer to independent verification and, when requested, an exact JSON receipt artifact"
    )
    return selected, None


def gap_synthesis_summary() -> dict[str, Any]:
    return {
        "truth_status": "BOUNDED_DETERMINISTIC_GAP_TO_PROPOSAL_COMPILER",
        "analysis_schema": GAP_ANALYSIS_SCHEMA,
        "proposal_result_schema": GAP_PROPOSAL_RESULT_SCHEMA,
        "exploration_result_schema": GAP_EXPLORATION_RESULT_SCHEMA,
        "operations": list(SUPPORTED_OPERATIONS),
        "implemented_blueprints": {
            EXACT_TEXT_ALIAS_BLUEPRINT: "Compile a missing exact UTF-8 file route into a detached alias-capability hypothesis when one compatible live primitive is uniquely visible.",
            BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT: "Search a bounded exact-contract graph for the shortest complete project recipe: create, independently verify when needed, and optionally persist the exact verification receipt as JSON.",
        },
        "project_producer_profiles": [
            {
                "profile": profile["profile"],
                "marker": profile["marker"],
                "ref": f"{profile['capability'][0]}@{profile['capability'][1]}",
                "output_kind": profile["output_kind"],
                "already_verified": profile["already_verified"],
            }
            for profile in PROJECT_PRODUCER_PROFILES
        ],
        "maximum_project_recipe_steps": MAX_PROJECT_RECIPE_STEPS,
        "recipe_path_selection": "shortest ready exact path; no ready path means shortest explicit HOLD",
        "reuse_precedes_new_embodiment": True,
        "gap_trigger_required": True,
        "existing_candidate_reuse_precedes_new_synthesis": True,
        "detached_experiment_allowed": True,
        "semantic_source_invention": False,
        "ambiguous_bridge_auto_selection": False,
        "missing_or_ambiguous_composite_link_is_hold": True,
        "closed_binding_transforms": ["file-digest-map"],
        "closed_binding_edges": ["file-digest-map", "exact-whole-object"],
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
    composite_candidate: dict[str, Any] | None = None
    composite_invalid_reason: str | None = None
    if exact is None and not existing_candidates:
        composite_candidate, composite_invalid_reason = _bounded_project_recipe_candidate(root, live_manifests, inputs)
    composite_candidates = [composite_candidate] if composite_candidate is not None else []

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
    elif composite_candidate is not None and composite_candidate["status"] == "READY_EXACT_COMPOSITE_CHAIN":
        status = "SYNTHESIS_READY_EXACT_COMPOSITE_CHAIN"
        truth_status = "DETERMINISTIC_COMPOSITE_CHAIN_HYPOTHESIS"
        selected = None
        hold_reason = None
    elif composite_candidate is not None and composite_candidate["status"] == "HOLD_AMBIGUOUS_COMPOSITE_LINK":
        status = "HOLD_AMBIGUOUS_COMPOSITE_LINK"
        truth_status = "DETERMINISTIC_AMBIGUITY_HOLD"
        selected = None
        hold_reason = "the composite blueprint observed ambiguous required dependency identities; no link is silently selected"
    elif composite_candidate is not None and composite_candidate["status"] == "HOLD_AMBIGUOUS_COMPOSITE_RECIPE":
        status = "HOLD_AMBIGUOUS_COMPOSITE_RECIPE"
        truth_status = "DETERMINISTIC_AMBIGUITY_HOLD"
        selected = None
        hold_reason = "more than one supported producer profile matches the request markers; no creation recipe is silently selected"
    elif composite_candidate is not None and composite_candidate["status"] == "HOLD_AMBIGUOUS_RECIPE_PATH":
        status = "HOLD_AMBIGUOUS_RECIPE_PATH"
        truth_status = "DETERMINISTIC_AMBIGUITY_HOLD"
        selected = None
        hold_reason = "more than one equally short exact recipe path is ready; no path is silently selected"
    elif composite_candidate is not None and composite_candidate["status"] == "HOLD_RECIPE_DEPTH_EXCEEDED":
        status = "HOLD_RECIPE_DEPTH_EXCEEDED"
        truth_status = "DETERMINISTIC_BOUNDED_SEARCH_HOLD"
        selected = None
        hold_reason = "the shortest applicable exact recipe exceeds the explicit maximum step count"
    elif composite_candidate is not None and composite_candidate["status"] in {
        "HOLD_MISSING_ORGAN_INTERFACE",
        "HOLD_AMBIGUOUS_ORGAN_ASSEMBLY",
        "HOLD_ORGAN_BINDING_CONTRACT",
        "HOLD_ORGAN_DISCOVERY_SEARCH_BOUND",
        "HOLD_NO_COMPLETE_ORGAN_ASSEMBLY",
    }:
        status = composite_candidate["status"]
        truth_status = str(
            composite_candidate.get("organ_discovery", {}).get(
                "truth_status", "DETERMINISTIC_ORGAN_DISCOVERY_HOLD"
            )
        )
        selected = None
        hold_reason = str(
            composite_candidate.get("organ_discovery", {}).get(
                "hold_reason", "interface-driven organ discovery remains on HOLD"
            )
        )
    elif composite_candidate is not None and composite_candidate["status"] == "HOLD_MISSING_COMPOSITE_LINK":
        status = "HOLD_MISSING_COMPOSITE_LINK"
        truth_status = "DETERMINISTIC_INCOMPLETE_CHAIN_HOLD"
        selected = None
        hold_reason = "the composite blueprint is applicable but one or more exact tested live dependency links are missing"
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
        hold_reason = composite_invalid_reason or "no implemented deterministic blueprint can compile this gap without inventing missing semantics or source"

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
        "implemented_blueprints": [EXACT_TEXT_ALIAS_BLUEPRINT, BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT],
        "implemented_blueprint": (
            BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT
            if composite_candidate is not None
            else EXACT_TEXT_ALIAS_BLUEPRINT
            if candidates
            else None
        ),
        "existing_candidates": existing_candidates,
        "candidate_bridges": candidates,
        "selected_bridge": selected,
        "composite_candidates": composite_candidates,
        "selected_blueprint": (
            copy.deepcopy(composite_candidate)
            if composite_candidate is not None and composite_candidate["status"] == "READY_EXACT_COMPOSITE_CHAIN"
            else None
        ),
        "composite_request_issue": composite_invalid_reason,
        "hold_reason": hold_reason,
        "selection_authority": "NONE",
        "semantic_equivalence_proven": False,
        "source_code_invented": False,
        "safe_next_step": (
            "compile and test one detached composite recipe hypothesis"
            if composite_candidate is not None and composite_candidate["status"] == "READY_EXACT_COMPOSITE_CHAIN"
            else "compile and test one detached adapter hypothesis"
            if selected
            else "test or inspect the existing detached candidate"
            if len(existing_candidates) == 1
            else "retain the typed hold or supply an explicit supported bridge/design"
        ),
        "limitations": [
            "matching one input/output shape does not prove that two creation meanings are equivalent",
            "the implemented compiler creates only exact UTF-8 aliases and project recipes of at most three steps over explicitly supported exact producer, verifier, and JSON reporter contracts",
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


def _composite_root_fit(
    request_kind: str,
    dependency_refs: list[str],
    step_count: int,
    reused_verified_composite: bool,
) -> dict[str, Any]:
    joined = ", ".join(dependency_refs)
    return {
        "truth": {
            "fit": True,
            "basis": f"The {request_kind!r} candidate exposes its discovered {step_count}-step recipe, exact dependency refs and bindings, request fixture, and evidence boundary without claiming general synthesis.",
        },
        "agency": {
            "fit": True,
            "basis": "The caller supplies the exact producer inputs, checks, and destination; the detached proposal grants itself no execution, installation, admission, merge, CANON, or permission authority.",
        },
        "continuity": {
            "fit": True,
            "basis": f"The candidate composes the continuing live capabilities {joined} without replacing them or the active machine body; existing verified composite reused={reused_verified_composite}.",
        },
        "wisdom-before-speed": {
            "fit": True,
            "basis": "The compiler chooses the shortest complete exact-contract path, rejects incomplete or over-depth wiring, and tests the full chain in disposable space before any admission choice.",
        },
    }


def _compile_bounded_project_recipe_proposal(
    root: Path,
    analysis: dict[str, Any],
    *,
    candidate_id: Any,
    version: Any,
) -> dict[str, Any]:
    selected = analysis["selected_blueprint"]
    request = analysis["request"]
    request_kind = request["kind"]
    inputs = request["inputs"]
    producer_name = selected["producer"]["profile"]
    profile = next(
        (item for item in PROJECT_PRODUCER_PROFILES if item["profile"] == producer_name),
        None,
    )
    if profile is None:
        raise GapSynthesisError(
            "the selected project producer profile is no longer implemented; re-analyze before compiling",
            {"profile": producer_name},
        )
    producer_id, _producer_version = profile["capability"]
    verify_id, _verify_version = VERIFY_CAPABILITY
    report_id, _report_version = REPORT_CAPABILITY
    report_requested = selected["goal"] == "verified-project-with-json-report"
    kind_slug = _slug(request_kind)
    generated_id = f"axm.generated.capability.{kind_slug}"
    unit_id = _required_text(candidate_id if candidate_id is not None else generated_id, "candidate_id", maximum=128)
    unit_version = _required_text(version, "version", maximum=32)
    direction = request.get("direction") or request.get("purpose") or request_kind
    if not isinstance(direction, str) or not direction.strip():
        direction = request_kind
    direction = direction.strip()[:600]

    current_live = CapabilityStore(root).live()
    current_by_id: dict[str, list[dict[str, Any]]] = {}
    for manifest in current_live:
        capability_id = manifest.get("id")
        if isinstance(capability_id, str):
            current_by_id.setdefault(capability_id, []).append(manifest)
    if unit_id in current_by_id:
        raise GapSynthesisError(
            "gap synthesis will not shadow an existing live capability identity",
            {"candidate_id": unit_id},
        )
    dependency_refs: list[str] = []
    dependency_digests: list[str] = []
    dependency_ids: list[str] = []
    for observed in selected["dependencies"]:
        capability_id = str(observed["capability_id"])
        current = current_by_id.get(capability_id, [])
        if len(current) != 1:
            raise GapSynthesisError(
                "a required composite dependency disappeared or became ambiguous after analysis; re-analyze before compiling",
                {"capability_id": capability_id, "observed_live_matches": len(current)},
            )
        manifest = current[0]
        current_ref = f"{capability_id}@{manifest.get('version')}"
        current_digest = _manifest_digest(root, manifest)
        if current_ref != observed["ref"] or current_digest != observed["manifest_digest"]:
            raise GapSynthesisError(
                "a required composite dependency changed after gap analysis; re-analyze before compiling",
                {
                    "capability_id": capability_id,
                    "analysis_ref": observed["ref"],
                    "current_ref": current_ref,
                    "analysis_manifest_digest": observed["manifest_digest"],
                    "current_manifest_digest": current_digest,
                },
            )
        dependency_ids.append(capability_id)
        dependency_refs.append(current_ref)
        dependency_digests.append(current_digest)

    try:
        preview = _preview_project_producer(root, profile, inputs)
    except (ProjectError, ExecutableOrganError, OrganDiscoveryError, GapSynthesisError) as exc:
        raise GapSynthesisError(
            "the project producer request changed or is no longer deterministically previewable; re-analyze before compiling",
            getattr(exc, "details", {}),
        ) from exc
    fixture_root = "${TEST_DIR}/request-example-project"
    expected_fixture_files = {
        f"{fixture_root}/{relative}": content
        for relative, content in sorted(preview["files"].items())
    }
    checks = copy.deepcopy(inputs.get("checks", []))
    live_input_properties = current_by_id[producer_id][0].get("input_contract", {}).get("properties", {})
    input_properties = {
        key: copy.deepcopy(live_input_properties[key])
        for key in (*profile["required_inputs"], *profile["optional_inputs"])
        if key in live_input_properties
    }
    if report_requested:
        input_properties["report_path"] = (
            "destination JSON file for the exact independent verification receipt"
        )
    producer_step_inputs = {
        key: {"from": f"request.{key}"}
        for key in profile["required_inputs"]
    }
    optional_defaults = {"checks": [], "replace": False, "project_type": "generic"}
    producer_step_inputs.update({
        key: {"from": f"request.{key}", "default": copy.deepcopy(optional_defaults[key])}
        for key in profile["optional_inputs"]
    })
    if not profile["already_verified"]:
        producer_step_inputs["publish_mode"] = "validated"
    fixture_inputs = {
        key: copy.deepcopy(inputs[key])
        for key in profile["required_inputs"]
    }
    for key in profile["optional_inputs"]:
        fixture_inputs[key] = copy.deepcopy(inputs.get(key, optional_defaults[key]))
    fixture_inputs["path"] = fixture_root
    fixture_inputs["checks"] = checks
    fixture_inputs["replace"] = False
    fixture_report_path = "${TEST_DIR}/request-verification-report.json"
    if report_requested:
        fixture_inputs["report_path"] = fixture_report_path

    steps: list[dict[str, Any]] = [
        {
            "id": "produce",
            "capability": producer_id,
            "inputs": producer_step_inputs,
        }
    ]
    if profile["already_verified"]:
        production_binding = {"from": "steps.produce.build"}
        verification_binding = {"from": "steps.produce.verification"}
    else:
        steps.append({
            "id": "verify",
            "capability": verify_id,
            "inputs": {
                "path": {"from": "steps.produce.path"},
                "project_type": {"from": "steps.produce.project_type"},
                "checks": {"from": "request.checks", "default": []},
                "expected_file_digests": {
                    "from": "steps.produce.files",
                    "transform": "file-digest-map",
                },
            },
        })
        production_binding = {"from": "steps.produce"}
        verification_binding = {"from": "steps.verify"}
    if report_requested:
        steps.append({
            "id": "report",
            "capability": report_id,
            "inputs": {
                "path": {"from": "request.report_path"},
                "value": copy.deepcopy(verification_binding),
            },
        })
    outputs = {
        "path": {"from": "steps.produce.path"},
        "production": production_binding,
        "verification": verification_binding,
    }
    if report_requested:
        outputs["report"] = {"from": "steps.report"}
    output_contract = {
        "kind": (
            "verified-project-with-json-report-result"
            if report_requested
            else "verified-receipted-project-result"
        ),
        "contains": [
            "path",
            "production",
            "verification",
            *(["report"] if report_requested else []),
        ],
    }
    fit = _composite_root_fit(
        request_kind,
        dependency_refs,
        selected["step_count"],
        profile["already_verified"],
    )
    candidate_manifest = {
        "id": unit_id,
        "version": unit_version,
        "status": "candidate",
        "purpose": f"Explore the missing route {request_kind!r} for the directional outcome {direction!r} through the selected bounded exact-contract recipe {selected['step_order']!r}.",
        "handles": [request_kind],
        "input_contract": {
            "required": [
                *profile["required_inputs"],
                *(["report_path"] if report_requested else []),
            ],
            "properties": input_properties,
        },
        "output_contract": output_contract,
        "dependencies": dependency_ids,
        "relationships": [
            *({"type": "composes", "target": dependency_id} for dependency_id in dependency_ids),
            {"type": "explores-gap", "target": analysis["request_digest"]},
        ],
        "implementation": {
            "kind": "DETERMINISTIC_COMPOSITE",
            "source": "this generated manifest",
            "steps": steps,
            "outputs": outputs,
        },
        "limitations": [
            f"This detached candidate implements only the selected bounded {producer_name} recipe {selected['step_order']!r}; it does not invent producer inputs, checks, organ wiring, or new semantic source.",
            "The independent verifier proves deterministic structural checks and byte identity against the immediately preceding creation receipt; it does not execute generated code or prove visual quality.",
            "The optional JSON reporter persists the exact verification object; it does not reinterpret or improve that evidence.",
            "The declared test covers only the exact request-shaped producer fixture in disposable build space.",
            "The original requested project and report destinations are not used during candidate testing.",
        ],
        "persistent_state": None,
        "tests": [
            {
                "inputs": fixture_inputs,
                "expect": {
                    "files": expected_fixture_files,
                    "result_fields": {
                        "production.published": True,
                        "production.creation_status": "VALIDATED_CREATION",
                        "verification.passed": True,
                        **({
                            "production.organ_discovery.status": "READY_EXACT_INTERFACE_ASSEMBLY"
                        } if producer_name == "interface-discovered-organ-assembly" else {}),
                        **({"report.kind": "json"} if report_requested else {}),
                    },
                    **({
                        "json_file_equals_result": {
                            "path": fixture_report_path,
                            "result_field": "verification",
                        }
                    } if report_requested else {}),
                },
            }
        ],
        "root_fit": copy.deepcopy(fit),
    }
    gap_file = {
        **copy.deepcopy(analysis),
        "proposal_selection": {
            "blueprint": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
            "producer_profile": producer_name,
            "dependency_refs": dependency_refs,
            "step_order": copy.deepcopy(selected["step_order"]),
            "selection_basis": "bounded graph search selected the shortest ready request-compatible path whose exact live dependency contracts and closed bindings were uniquely present",
            "selection_is_admission_authority": False,
            "selection_is_general_semantic_proof": False,
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
            "kind": "DETERMINISTIC_COMPOSITE",
            "entrypoint": "capability.json",
            "source_files": ["capability.json", "gap-analysis.json"],
        },
        "contracts": {
            "inputs": copy.deepcopy(candidate_manifest["input_contract"]),
            "outputs": copy.deepcopy(output_contract),
            "provides": [f"creation.route.{kind_slug}"],
            "requires": [f"live.capability.{_slug(item)}" for item in dependency_ids],
        },
        "dependencies": [
            {"kind": "capability", "ref": ref, "optional": False}
            for ref in dependency_refs
        ],
        "relationships": [
            *({"type": "composes", "target": ref} for ref in dependency_refs),
            {"type": "compiled-from-gap", "target": analysis["request_digest"]},
            {"type": "uses-blueprint", "target": BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT},
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
                BOUNDED_PROJECT_RECIPE_GRAPH_BLUEPRINT,
                *dependency_refs,
                *dependency_digests,
            ],
            "basis": f"A real unroutable project request exposed a gap; bounded exact-contract search selected the {selected['step_count']}-step {producer_name} path, reused existing verified composition when shorter, and added only closed receipt-verification or exact-object-report bindings.",
        },
        "limitations": copy.deepcopy(candidate_manifest["limitations"]),
        "authority": copy.deepcopy(ZERO_AUTHORITY),
        "root_fit": copy.deepcopy(fit),
    }
    normalized = validate_spawn_proposal(proposal)
    return {
        "schema": GAP_PROPOSAL_RESULT_SCHEMA,
        "operation": "propose",
        "status": "DETACHED_COMPOSITE_PROPOSAL_READY",
        "truth_status": "DETERMINISTIC_GAP_DERIVED_COMPOSITE_PROPOSAL",
        "analysis": analysis,
        "selected_bridge": None,
        "selected_blueprint": copy.deepcopy(selected),
        "selection_basis": gap_file["proposal_selection"]["selection_basis"],
        "proposal": normalized,
        "proposal_digest": _digest(normalized),
        "target_created": False,
        "semantic_equivalence_proven": False,
        "runtime_behavior_proven": False,
        "admission_requested": False,
    }


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
    if analysis["selected_blueprint"] is not None:
        if bridge_capability_id is not None:
            raise GapSynthesisError(
                "bridge_capability_id applies only to observed single-bridge alias candidates, not discovered composite blueprints",
                {"selected_blueprint": analysis["selected_blueprint"]["blueprint"]},
            )
        return _compile_bounded_project_recipe_proposal(
            root,
            analysis,
            candidate_id=candidate_id,
            version=version,
        )
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
        "selected_blueprint": EXACT_TEXT_ALIAS_BLUEPRINT,
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
        "selected_bridge": proposed.get("selected_bridge"),
        "selected_blueprint": proposed.get("selected_blueprint"),
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

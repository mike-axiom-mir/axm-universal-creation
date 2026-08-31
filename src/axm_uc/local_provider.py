from __future__ import annotations

import hashlib
import ipaddress
import json
import os
import re
import socket
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit, urlunsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

from .grammar import grammar_inventory
from .project import ProjectError, build_project, validate_project


PROVIDER_REQUEST_SCHEMA = "axm.local-creation-provider-request/v0.1"
PROVIDER_RESPONSE_SCHEMA = "axm.local-creation-provider-response/v0.1"
PROVIDER_RECEIPT_SCHEMA = "axm.local-creation-provider-receipt/v0.1"
SPECIALIST_CHECKPOINT_REQUEST_SCHEMA = "axm.local-specialist-checkpoint-request/v0.1"
SPECIALIST_CHECKPOINT_RESPONSE_SCHEMA = "axm.local-specialist-checkpoint-response/v0.1"
DEFAULT_ENDPOINT = "http://127.0.0.1:7789/v1"
DEFAULT_MODEL = "waldo"
MAX_RESPONSE_BYTES = 8 << 20
MAX_PROJECT_BYTES = 2 << 20
MAX_PROJECT_FILES = 128
ENV_NAME = re.compile(r"^[A-Z_][A-Z0-9_]*$")


class _RejectRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):  # noqa: ANN001 - stdlib override
        return None


class LocalProviderError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 10000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise LocalProviderError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise LocalProviderError(f"{label} exceeds its {maximum}-character bound")
    return text


def normalize_loopback_endpoint(raw: Any) -> str:
    endpoint = _required_text(raw if raw is not None else DEFAULT_ENDPOINT, "provider.endpoint", 1000)
    parsed = urlsplit(endpoint)
    hostname = (parsed.hostname or "").casefold()
    if parsed.scheme != "http" or hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise LocalProviderError(
            "local creation provider endpoint must use plain HTTP on an explicit loopback host",
            {
                "endpoint": endpoint,
                "allowed_hosts": ["127.0.0.1", "localhost", "::1"],
                "cloud_control_plane_allowed": False,
            },
        )
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise LocalProviderError("provider.endpoint may not contain credentials, query parameters, or fragments")
    try:
        port = parsed.port
    except ValueError as exc:
        raise LocalProviderError("provider.endpoint contains an invalid port") from exc
    try:
        addresses = {
            row[4][0]
            for row in socket.getaddrinfo(hostname, port or 80, type=socket.SOCK_STREAM)
        }
    except OSError as exc:
        raise LocalProviderError("local creation provider host could not be resolved", {"host": hostname}) from exc
    if not addresses or any(not ipaddress.ip_address(address).is_loopback for address in addresses):
        raise LocalProviderError(
            "local creation provider host did not resolve exclusively to loopback addresses",
            {"host": hostname, "resolved_addresses": sorted(addresses)},
        )
    path = parsed.path.rstrip("/")
    return urlunsplit(("http", parsed.netloc, path, "", ""))


def _safe_project_files(raw: Any) -> dict[str, str]:
    if not isinstance(raw, dict) or not raw:
        raise LocalProviderError("provider response files must be a non-empty object")
    if len(raw) > MAX_PROJECT_FILES:
        raise LocalProviderError(
            f"provider response exceeds the {MAX_PROJECT_FILES}-file bound",
            {"file_count": len(raw)},
        )
    files: dict[str, str] = {}
    total = 0
    for raw_path, content in raw.items():
        path_text = str(raw_path).replace("\\", "/").strip()
        path = PurePosixPath(path_text)
        if (
            not path_text
            or path_text.endswith("/")
            or path.is_absolute()
            or any(part in {"", ".", ".."} for part in path.parts)
        ):
            raise LocalProviderError(
                "provider response contains a project path that is not safely relative",
                {"path": path_text},
            )
        normalized_path = path.as_posix()
        if normalized_path in files:
            raise LocalProviderError("provider response contains duplicate normalized paths", {"path": normalized_path})
        if not isinstance(content, str):
            raise LocalProviderError(
                "local provider v0.1 accepts UTF-8 text project files only",
                {"path": normalized_path, "received_type": type(content).__name__},
            )
        total += len(content.encode("utf-8"))
        if total > MAX_PROJECT_BYTES:
            raise LocalProviderError(
                f"provider response exceeds the {MAX_PROJECT_BYTES}-byte project bound",
                {"observed_bytes": total},
            )
        files[normalized_path] = content
    return files


def _provider_config(raw: Any) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise LocalProviderError("provider must be an object")
    allowed = {"endpoint", "model", "api_key_env", "timeout_seconds", "allow_call"}
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise LocalProviderError("provider contains unsupported fields", {"unexpected_fields": unexpected})
    endpoint = normalize_loopback_endpoint(raw.get("endpoint", DEFAULT_ENDPOINT))
    model = _required_text(raw.get("model", DEFAULT_MODEL), "provider.model", 200)
    timeout = raw.get("timeout_seconds", 120)
    if not isinstance(timeout, int) or isinstance(timeout, bool) or timeout < 1 or timeout > 600:
        raise LocalProviderError("provider.timeout_seconds must be an integer from 1 through 600")
    key_env = raw.get("api_key_env")
    if key_env is not None:
        key_env = _required_text(key_env, "provider.api_key_env", 200)
        if ENV_NAME.fullmatch(key_env) is None:
            raise LocalProviderError("provider.api_key_env must be an uppercase environment-variable name")
    allow_call = raw.get("allow_call", False)
    if not isinstance(allow_call, bool):
        raise LocalProviderError("provider.allow_call must be boolean")
    return {
        "endpoint": endpoint,
        "model": model,
        "api_key_env": key_env,
        "timeout_seconds": timeout,
        "allow_call": allow_call,
    }


def provider_summary() -> dict[str, Any]:
    return {
        "truth_status": "EXPLICIT_MODEL_INDEPENDENT_LOCAL_PROVIDER_BOUNDARY",
        "request_schema": PROVIDER_REQUEST_SCHEMA,
        "response_schema": PROVIDER_RESPONSE_SCHEMA,
        "receipt_schema": PROVIDER_RECEIPT_SCHEMA,
        "default_endpoint": DEFAULT_ENDPOINT,
        "default_model": DEFAULT_MODEL,
        "compatible_provider_shape": "OpenAI-compatible POST /chat/completions",
        "known_local_hosts": [
            "AXM Local Workshop native WALDO bridge",
            "LM Studio or another explicitly selected OpenAI-compatible loopback endpoint",
        ],
        "provider_is_authority": False,
        "provider_output_is_implementation_proof": False,
        "automatic_call_without_explicit_allow": False,
        "cloud_control_plane_allowed": False,
        "automatic_machine_body_mutation": False,
        "bounded_specialist_checkpoint_execution": True,
        "specialist_profiles_are_method_overlays_not_independent_identities": True,
        "project_limits": {"files": MAX_PROJECT_FILES, "utf8_bytes": MAX_PROJECT_BYTES},
    }


def prepare_provider_request(inputs: dict[str, Any]) -> dict[str, Any]:
    goal = _required_text(inputs.get("goal"), "goal", 20000)
    project_type = str(inputs.get("project_type", "generic")).strip().casefold()
    if project_type not in {"generic", "static-web", "python"}:
        raise LocalProviderError("project_type must be generic, static-web, or python")
    constraints = inputs.get("constraints", {})
    if not isinstance(constraints, dict):
        raise LocalProviderError("constraints must be an object")
    context = inputs.get("context", {})
    if not isinstance(context, dict):
        raise LocalProviderError("context must be an object")
    packet = {
        "schema": PROVIDER_REQUEST_SCHEMA,
        "goal": goal,
        "project_type": project_type,
        "constraints": constraints,
        "context": context,
        "response_contract": {
            "schema": PROVIDER_RESPONSE_SCHEMA,
            "allowed_keys": ["schema", "project_type", "files", "summary", "limitations"],
            "files": "non-empty mapping of safe project-relative paths to exact UTF-8 text",
            "maximum_files": MAX_PROJECT_FILES,
            "maximum_total_utf8_bytes": MAX_PROJECT_BYTES,
        },
        "authority_boundary": {
            "proposal_only": True,
            "may_mutate_machine_body": False,
            "may_install_or_adopt": False,
            "host_will_validate_before_publication": True,
            "runtime_browser_and_visual_truth_remain_separate_evidence": True,
        },
    }
    return {**packet, "request_digest": _digest(packet)}


def _system_prompt() -> str:
    return (
        "You are a local creation provider connected to AXM Universal Creation. "
        "Return exactly one JSON object and no Markdown. Follow the supplied response contract. "
        "The host—not you—controls paths, validation, publication, authority, installation, and adoption. "
        "Do not claim that code ran, browser interaction passed, visuals were judged, or the machine changed."
    )


def _call_provider(packet: dict[str, Any], provider: dict[str, Any], system_prompt: str) -> tuple[str, dict[str, Any]]:
    if provider["allow_call"] is not True:
        raise LocalProviderError(
            "local provider call requires provider.allow_call=true",
            {"prepared_request": packet, "provider": {k: v for k, v in provider.items() if k != "api_key_env"}},
        )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": json.dumps(packet, ensure_ascii=False, sort_keys=True)},
    ]
    body = _canonical_bytes({"model": provider["model"], "messages": messages, "stream": False})
    if len(body) > MAX_PROJECT_BYTES:
        raise LocalProviderError("local provider request exceeds the 2 MiB request bound")
    request = Request(
        provider["endpoint"] + "/chat/completions",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    if provider["api_key_env"]:
        value = os.environ.get(str(provider["api_key_env"]), "")
        if not value:
            raise LocalProviderError(
                "local provider API-key environment variable is not available",
                {"api_key_env": provider["api_key_env"]},
            )
        request.add_header("Authorization", "Bearer " + value)
    try:
        opener = build_opener(ProxyHandler({}), _RejectRedirects())
        with opener.open(request, timeout=provider["timeout_seconds"]) as response:
            raw = response.read(MAX_RESPONSE_BYTES + 1)
            status = int(getattr(response, "status", 200))
    except HTTPError as exc:
        detail = exc.read(4096).decode("utf-8", errors="replace")
        raise LocalProviderError(
            "local provider rejected the creation request",
            {"status": exc.code, "response_excerpt": detail[:1000]},
        ) from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise LocalProviderError(
            "local creation provider is unavailable",
            {"endpoint": provider["endpoint"], "next_action": "start AXM Local Workshop or select another loopback provider"},
        ) from exc
    if len(raw) > MAX_RESPONSE_BYTES:
        raise LocalProviderError("local provider response exceeds the 8 MiB transport bound")
    return _extract_response_content(raw), {
        "endpoint": provider["endpoint"],
        "model": provider["model"],
        "transport": "openai-compatible-loopback-http",
        "status": status,
        "raw_response_digest": f"sha256:{hashlib.sha256(raw).hexdigest()}",
    }


def _extract_response_content(raw: bytes) -> str:
    try:
        body = json.loads(raw.decode("utf-8"))
        choices = body["choices"]
        content = choices[0]["message"]["content"]
    except (UnicodeError, json.JSONDecodeError, KeyError, IndexError, TypeError) as exc:
        raise LocalProviderError("local provider returned an invalid OpenAI-compatible response") from exc
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = [part.get("text", "") for part in content if isinstance(part, dict) and part.get("type") == "text"]
        return "\n".join(str(part) for part in parts if str(part).strip())
    raise LocalProviderError("local provider response content must be text")


def _parse_proposal(content: str, expected_project_type: str) -> dict[str, Any]:
    try:
        proposal = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LocalProviderError(
            "local provider did not return the required JSON creation proposal",
            {"line": exc.lineno, "column": exc.colno},
        ) from exc
    if not isinstance(proposal, dict):
        raise LocalProviderError("local provider proposal must be a JSON object")
    allowed = {"schema", "project_type", "files", "summary", "limitations"}
    unexpected = sorted(set(proposal) - allowed)
    if unexpected:
        raise LocalProviderError("local provider proposal contains unsupported fields", {"unexpected_fields": unexpected})
    if proposal.get("schema") != PROVIDER_RESPONSE_SCHEMA:
        raise LocalProviderError(
            "local provider proposal schema is not supported",
            {"expected": PROVIDER_RESPONSE_SCHEMA, "received": proposal.get("schema")},
        )
    project_type = str(proposal.get("project_type", "")).strip().casefold()
    if project_type != expected_project_type:
        raise LocalProviderError(
            "local provider changed the caller-selected project type",
            {"expected": expected_project_type, "received": project_type},
        )
    summary = _required_text(proposal.get("summary"), "provider response summary", 4000)
    limitations = proposal.get("limitations", [])
    if not isinstance(limitations, list) or any(not isinstance(item, str) or not item.strip() for item in limitations):
        raise LocalProviderError("provider response limitations must be a list of non-empty text")
    return {
        "schema": PROVIDER_RESPONSE_SCHEMA,
        "project_type": project_type,
        "files": _safe_project_files(proposal.get("files")),
        "summary": summary,
        "limitations": [item.strip() for item in limitations],
    }


def invoke_provider(inputs: dict[str, Any]) -> dict[str, Any]:
    packet = prepare_provider_request(inputs)
    provider = _provider_config(inputs.get("provider"))
    content, provider_receipt = _call_provider(packet, provider, _system_prompt())
    proposal = _parse_proposal(content, str(packet["project_type"]))
    return {
        "schema": PROVIDER_RECEIPT_SCHEMA,
        "truth_status": "VALIDATED_LOCAL_PROVIDER_PROPOSAL_NOT_YET_MATERIALIZED",
        "request": packet,
        "request_digest": packet["request_digest"],
        "provider": {key: value for key, value in provider_receipt.items() if key != "raw_response_digest"},
        "raw_response_digest": provider_receipt["raw_response_digest"],
        "proposal": proposal,
        "proposal_digest": _digest(proposal),
        "authority": {
            "provider_selected_files": True,
            "provider_selected_destination": False,
            "installed": False,
            "adopted": False,
            "machine_body_modified": False,
        },
    }


def analyze_specialist_checkpoint(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    from .stepwise_workflow import StepwiseWorkflowError, _verify_checkpoint, _verify_workflow, record_checkpoint_analysis

    try:
        workflow = _verify_workflow(inputs.get("workflow"))
        checkpoint = _verify_checkpoint(inputs.get("checkpoint"), workflow)
    except StepwiseWorkflowError as exc:
        raise LocalProviderError(str(exc), exc.details) from exc
    expected_ids = [str(row["id"]) for row in checkpoint["perspectives"]]
    packet_body = {
        "schema": SPECIALIST_CHECKPOINT_REQUEST_SCHEMA,
        "goal": workflow["goal"],
        "current_step": workflow["plan"]["steps"][workflow["cursor"]],
        "checkpoint": checkpoint,
        "response_contract": {
            "schema": SPECIALIST_CHECKPOINT_RESPONSE_SCHEMA,
            "exact_specialist_ids": expected_ids,
            "each_analysis": {
                "analysis": "non-empty text grounded only in the supplied packet",
                "decision": ["PROCEED", "SPLIT", "REPLAN", "HOLD"],
                "evidence_refs": "one or more non-empty references; use explicit unknown references when evidence is absent",
            },
            "allowed_top_level_keys": ["schema", "analyses", "limitations"],
        },
        "truth_boundary": {
            "one_provider_supplies_all_method_overlays": True,
            "independent_specialist_identities_claimed": False,
            "provider_analysis_is_objective_proof": False,
        },
    }
    packet = {**packet_body, "request_digest": _digest(packet_body)}
    provider = _provider_config(inputs.get("provider"))
    system_prompt = (
        "You are the explicitly selected local cognition provider for one AXM perspective checkpoint. "
        "Return exactly one JSON object and no Markdown. Apply each supplied specialist profile as a bounded method overlay; "
        "do not claim separate identities, independent execution, external evidence, or objective correctness. "
        "Follow the exact specialist ids and response contract. Name unknowns as unknowns."
    )
    content, provider_receipt = _call_provider(packet, provider, system_prompt)
    try:
        response = json.loads(content)
    except json.JSONDecodeError as exc:
        raise LocalProviderError(
            "local provider did not return the required JSON checkpoint analysis",
            {"line": exc.lineno, "column": exc.colno},
        ) from exc
    if not isinstance(response, dict) or set(response) - {"schema", "analyses", "limitations"}:
        raise LocalProviderError("local checkpoint response has an unsupported shape")
    if response.get("schema") != SPECIALIST_CHECKPOINT_RESPONSE_SCHEMA:
        raise LocalProviderError(
            "local checkpoint response schema is not supported",
            {"expected": SPECIALIST_CHECKPOINT_RESPONSE_SCHEMA, "received": response.get("schema")},
        )
    limitations = response.get("limitations", [])
    if not isinstance(limitations, list) or any(not isinstance(item, str) or not item.strip() for item in limitations):
        raise LocalProviderError("local checkpoint limitations must be a list of non-empty text")
    try:
        updated = record_checkpoint_analysis(workflow, checkpoint, response.get("analyses"))
    except StepwiseWorkflowError as exc:
        raise LocalProviderError(
            "local checkpoint analysis failed the deterministic workflow contract: " + str(exc),
            exc.details,
        ) from exc
    normalized_response = {
        "schema": SPECIALIST_CHECKPOINT_RESPONSE_SCHEMA,
        "analyses": updated["timeline"][-1]["analyses"],
        "limitations": [item.strip() for item in limitations],
    }
    allowed_ref_prefixes = ("provider:", "checkpoint:", "workflow:", "unknown:")
    unsupported_refs = sorted(
        {
            ref
            for analysis in normalized_response["analyses"].values()
            for ref in analysis["evidence_refs"]
            if not ref.casefold().startswith(allowed_ref_prefixes)
        }
    )
    if unsupported_refs:
        raise LocalProviderError(
            "local checkpoint analysis may cite only provider, checkpoint, workflow, or explicit unknown references",
            {"unsupported_evidence_refs": unsupported_refs},
        )
    return {
        "operation": "analyze-checkpoint",
        "truth_status": "VALIDATED_LOCAL_PROVIDER_PERSPECTIVE_ANALYSIS_RECORDED",
        "request": packet,
        "provider": {key: value for key, value in provider_receipt.items() if key != "raw_response_digest"},
        "raw_response_digest": provider_receipt["raw_response_digest"],
        "response": normalized_response,
        "response_digest": _digest(normalized_response),
        "workflow": updated,
        "authority": {
            "provider_supplied_analysis": True,
            "independent_specialist_identities_claimed": False,
            "provider_analysis_is_external_evidence": False,
            "provider_selected_workflow_transition": False,
            "deterministic_most_conservative_transition_rule_applied": True,
            "machine_body_modified": False,
        },
    }


def create_from_provider(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = Path(str(inputs.get("path", ""))).expanduser()
    if not target.is_absolute():
        target = Path(root) / target
    target = target.resolve()
    receipt = invoke_provider(inputs)
    proposal = receipt["proposal"]
    checks = inputs.get("checks")
    if checks is not None and not isinstance(checks, list):
        raise LocalProviderError("checks must be a list")
    replace = inputs.get("replace", False)
    if not isinstance(replace, bool):
        raise LocalProviderError("replace must be boolean")
    publish_mode = str(inputs.get("publish_mode", "validated"))
    try:
        creation = build_project(
            target=target,
            files=proposal["files"],
            project_type=proposal["project_type"],
            checks=checks,
            replace=replace,
            publish_mode=publish_mode,
        )
        creation["grammar_inventory"] = grammar_inventory(target)
        expected_digests = {row["path"]: row["sha256"] for row in creation.get("files", [])}
        verification = validate_project(
            target,
            project_type=proposal["project_type"],
            checks=checks,
            expected_files=proposal["files"],
            expected_file_digests=expected_digests,
        )
        verification["grammar_inventory"] = grammar_inventory(target)
    except ProjectError as exc:
        raise LocalProviderError(str(exc), exc.details) from exc
    passed = creation.get("published") is True and verification.get("passed") is True
    return {
        "operation": "create",
        "truth_status": "LOCAL_PROVIDER_PROJECT_STRUCTURALLY_VERIFIED" if passed else "LOCAL_PROVIDER_PROJECT_HAS_VISIBLE_GAPS",
        "passed": passed,
        "path": str(target),
        "provider_receipt": receipt,
        "creation": creation,
        "verification": verification,
        "host_evidence_status": "NOT_OBSERVED",
        "host_evidence_needed": [
            "runtime execution when the project has executable behavior",
            "browser interaction for web projects",
            "visual inspection for appearance claims",
            "gameplay or domain evidence for semantic requirements",
        ],
        "limitations": [
            "local provider output is a proposal and is not proof of semantic correctness",
            "structural verification does not prove runtime, browser, visual, gameplay, or user-experience behavior",
            "this local provider milestone accepts UTF-8 text project files only",
        ],
    }


def operate_local_provider(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    if operation == "inspect":
        return {"operation": operation, **provider_summary()}
    if operation == "prepare":
        return {
            "operation": operation,
            "truth_status": "LOCAL_PROVIDER_REQUEST_PREPARED_NO_CALL_MADE",
            "request": prepare_provider_request(inputs),
            "provider": _provider_config(inputs.get("provider")),
        }
    if operation == "invoke":
        return {"operation": operation, **invoke_provider(inputs)}
    if operation == "create":
        return create_from_provider(root, inputs)
    if operation == "analyze-checkpoint":
        return analyze_specialist_checkpoint(root, inputs)
    raise LocalProviderError(
        "unsupported local provider operation",
        {
            "operation": operation,
            "supported_operations": ["inspect", "prepare", "invoke", "create", "analyze-checkpoint"],
        },
    )

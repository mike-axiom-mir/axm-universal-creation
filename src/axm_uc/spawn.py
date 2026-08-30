from __future__ import annotations

import copy
import hashlib
import json
import re
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .atomic import atomic_write_json
from .candidate import test_capability_candidate
from .organ_library import ExecutableOrganError, ExecutableOrganLibrary
from .project import CHECKS, ProjectError, build_project, validate_project
from .root_fit import evaluate_declared_root_fit


SPAWN_PROPOSAL_SCHEMA = "axm.creation-unit-spawn-proposal/v0.1"
SPAWNED_UNIT_SCHEMA = "axm.spawned-creation-unit/v0.1"
SPAWN_RECEIPT_SCHEMA = "axm.creation-unit-spawn-receipt/v0.1"
ADMISSION_REQUEST_SCHEMA = "axm.creation-unit-admission-request/v0.1"

PROPOSAL_FILE = "axm.proposal.json"
UNIT_FILE = "axm.unit.json"
RECEIPT_FILE = "axm.spawn-receipt.json"
ADMISSION_FILE = "axm.admission-request.json"
CORE_FILES = {PROPOSAL_FILE, UNIT_FILE, RECEIPT_FILE, ADMISSION_FILE}

FIRST_CLASS_KINDS = {
    "hand": "A bounded callable adapter or actuator candidate; it uses the capability-manifest test lane in this version.",
    "capability": "A callable creation-ability candidate with detached manifest tests.",
    "organ": "A reusable subsystem package candidate validated against the executable-organ package contract.",
    "protocol": "A typed exchange-contract candidate; structure is checked but no transport runtime is implied.",
    "skill": "A portable bounded method or instruction package; it grants no capability or authority by itself.",
    "specialist": "A temporary method overlay composed from declared skills; it is not identity, expertise proof, or independent evidence.",
    "recipe": "A deterministic build-definition candidate; this version materializes and checks it but does not auto-activate it as a new forge builder.",
}

IMPLEMENTATION_KINDS = {
    "DETERMINISTIC_SOURCE",
    "DETERMINISTIC_ALIAS",
    "DETERMINISTIC_COMPOSITE",
    "DETERMINISTIC_CONTRACT",
    "DETERMINISTIC_RECIPE",
    "INSTRUCTION_ONLY",
    "HOST_MEDIATED",
    "METHOD_OVERLAY",
    "LEARNED_INSPECTABLE",
    "EXTERNAL_BLACK_BOX",
    "HUMAN_SUPPLIED",
    "UNKNOWN",
}

AUTHORITY_FIELDS = (
    "execute",
    "install",
    "register",
    "promote",
    "merge",
    "canon",
    "permissions",
)

ID_RE = re.compile(r"[a-z][a-z0-9_.-]{2,127}")
KIND_RE = re.compile(r"[a-z][a-z0-9-]{1,63}")
VERSION_RE = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
INTERFACE_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
MAX_FILES = 128
MAX_TOTAL_BYTES = 2 * 1024 * 1024


class SpawnError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _digest_bytes(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _digest_value(value: Any) -> str:
    return _digest_bytes(_canonical_bytes(value))


def _json_text(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _required_text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SpawnError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise SpawnError(f"{label} exceeds its {maximum}-character bound")
    return text


def _closed_object(value: Any, label: str, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SpawnError(f"{label} must be an object")
    optional = optional or set()
    missing = sorted(required - set(value))
    unexpected = sorted(set(value) - required - optional)
    if missing or unexpected:
        raise SpawnError(
            f"{label} does not match its closed contract",
            {"field": label, "missing_fields": missing, "unexpected_fields": unexpected},
        )
    return value


def _safe_relative_path(raw: Any, label: str) -> str:
    text = _required_text(raw, label, maximum=240).replace("\\", "/")
    path = PurePosixPath(text)
    if path.is_absolute() or text.endswith("/") or any(part in {"", ".", ".."} for part in path.parts):
        raise SpawnError(f"{label} must stay inside the spawned unit", {"path": text})
    return path.as_posix()


def _text_list(value: Any, label: str, *, allow_empty: bool = True, maximum: int = 128) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        qualifier = "a non-empty list" if not allow_empty else "a list"
        raise SpawnError(f"{label} must be {qualifier}")
    if len(value) > maximum:
        raise SpawnError(f"{label} exceeds its {maximum}-entry bound")
    result: list[str] = []
    for index, raw in enumerate(value):
        text = _required_text(raw, f"{label}[{index}]", maximum=500)
        if text in result:
            raise SpawnError(f"{label} entries must be unique", {"duplicate": text})
        result.append(text)
    return result


def _interface_list(value: Any, label: str) -> list[str]:
    values = _text_list(value, label)
    invalid = [item for item in values if INTERFACE_RE.fullmatch(item) is None]
    if invalid:
        raise SpawnError(f"{label} has invalid interface names", {"invalid": invalid})
    return values


def _authority(value: Any) -> dict[str, bool]:
    raw = _closed_object(value, "proposal.authority", set(AUTHORITY_FIELDS))
    widened = sorted(field for field in AUTHORITY_FIELDS if raw.get(field) is not False)
    if widened:
        raise SpawnError(
            "a spawn proposal cannot grant itself authority",
            {"fields_not_explicitly_false": widened},
        )
    return {field: False for field in AUTHORITY_FIELDS}


def _normal_checks(value: Any, files: dict[str, str]) -> list[dict[str, Any]]:
    raw = _closed_object(value, "proposal.verification", {"checks"})
    checks = raw["checks"]
    if not isinstance(checks, list) or not checks or len(checks) > 64:
        raise SpawnError("proposal.verification.checks must be a non-empty list with at most 64 entries")
    normalized: list[dict[str, Any]] = []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            raise SpawnError(f"proposal.verification.checks[{index}] must be an object")
        kind = _required_text(check.get("type"), f"proposal.verification.checks[{index}].type", maximum=80).casefold()
        if kind not in CHECKS:
            raise SpawnError(
                "proposal requests an unsupported deterministic check",
                {"index": index, "check": kind, "supported_checks": sorted(CHECKS)},
            )
        normalized_check = copy.deepcopy(check)
        normalized_check["type"] = kind
        if "path" in normalized_check:
            normalized_path = _safe_relative_path(normalized_check["path"], f"proposal.verification.checks[{index}].path")
            if normalized_path not in files:
                raise SpawnError(
                    "proposal verification check names a file outside the supplied payload",
                    {"index": index, "path": normalized_path},
                )
            normalized_check["path"] = normalized_path
        normalized.append(normalized_check)
    return normalized


def _kind_specific_proposal_checks(kind: str, implementation: dict[str, Any]) -> None:
    implementation_kind = implementation["kind"]
    entrypoint = implementation["entrypoint"]
    if kind in {"hand", "capability"}:
        if implementation_kind not in {"DETERMINISTIC_SOURCE", "DETERMINISTIC_ALIAS", "DETERMINISTIC_COMPOSITE"}:
            raise SpawnError(f"{kind} candidates currently require a deterministic capability implementation kind")
        if not entrypoint.endswith(".json"):
            raise SpawnError(f"{kind} candidates currently require a JSON capability-manifest entrypoint")
    elif kind == "organ":
        if implementation_kind != "DETERMINISTIC_SOURCE" or not entrypoint.endswith(".json"):
            raise SpawnError("organ candidates currently require a deterministic executable-organ JSON entrypoint")
    elif kind == "protocol":
        if implementation_kind != "DETERMINISTIC_CONTRACT" or not entrypoint.endswith(".json"):
            raise SpawnError("protocol candidates require a deterministic-contract JSON entrypoint")
    elif kind == "skill":
        if implementation_kind not in {"INSTRUCTION_ONLY", "HOST_MEDIATED", "DETERMINISTIC_SOURCE"}:
            raise SpawnError("skill candidates must be instruction-only, host-mediated, or deterministic source")
        if not entrypoint.casefold().endswith(".md"):
            raise SpawnError("skill candidates require a Markdown entrypoint")
    elif kind == "specialist":
        if implementation_kind != "METHOD_OVERLAY" or not entrypoint.endswith(".json"):
            raise SpawnError("specialist candidates require a method-overlay JSON entrypoint")
    elif kind == "recipe":
        if implementation_kind != "DETERMINISTIC_RECIPE" or not entrypoint.endswith(".json"):
            raise SpawnError("recipe candidates require a deterministic-recipe JSON entrypoint")


def validate_spawn_proposal(value: Any) -> dict[str, Any]:
    required = {
        "schema",
        "id",
        "version",
        "kind",
        "purpose",
        "files",
        "implementation",
        "contracts",
        "dependencies",
        "relationships",
        "verification",
        "provenance",
        "limitations",
        "authority",
        "root_fit",
    }
    proposal = _closed_object(value, "proposal", required)
    if proposal["schema"] != SPAWN_PROPOSAL_SCHEMA:
        raise SpawnError(
            "proposal schema is unsupported",
            {"expected_schema": SPAWN_PROPOSAL_SCHEMA, "actual_schema": proposal.get("schema")},
        )

    unit_id = _required_text(proposal["id"], "proposal.id", maximum=128)
    if ID_RE.fullmatch(unit_id) is None:
        raise SpawnError("proposal.id is invalid", {"id": unit_id})
    version = _required_text(proposal["version"], "proposal.version", maximum=32)
    if VERSION_RE.fullmatch(version) is None:
        raise SpawnError("proposal.version must use numeric semantic version form", {"version": version})
    kind = _required_text(proposal["kind"], "proposal.kind", maximum=64).casefold()
    if KIND_RE.fullmatch(kind) is None:
        raise SpawnError("proposal.kind is invalid", {"kind": kind})
    purpose = _required_text(proposal["purpose"], "proposal.purpose", maximum=1000)

    if not isinstance(proposal["files"], dict) or not proposal["files"] or len(proposal["files"]) > MAX_FILES:
        raise SpawnError(f"proposal.files must contain between 1 and {MAX_FILES} text files")
    files: dict[str, str] = {}
    total_bytes = 0
    for raw_path, content in proposal["files"].items():
        path = _safe_relative_path(raw_path, "proposal file path")
        if path in CORE_FILES or path.startswith(".axm/"):
            raise SpawnError("proposal file path is reserved for forge evidence", {"path": path})
        if path in files:
            raise SpawnError("proposal file paths collide after normalization", {"path": path})
        if not isinstance(content, str):
            raise SpawnError("proposal files must contain exact UTF-8 text", {"path": path})
        total_bytes += len(content.encode("utf-8"))
        if total_bytes > MAX_TOTAL_BYTES:
            raise SpawnError(f"proposal payload exceeds the {MAX_TOTAL_BYTES}-byte bound")
        files[path] = content

    implementation_raw = _closed_object(
        proposal["implementation"],
        "proposal.implementation",
        {"kind", "entrypoint", "source_files"},
        {"runtime"},
    )
    implementation_kind = _required_text(implementation_raw["kind"], "proposal.implementation.kind", maximum=80).upper()
    if implementation_kind not in IMPLEMENTATION_KINDS:
        raise SpawnError(
            "proposal implementation kind is unsupported",
            {"kind": implementation_kind, "supported_kinds": sorted(IMPLEMENTATION_KINDS)},
        )
    entrypoint = _safe_relative_path(implementation_raw["entrypoint"], "proposal.implementation.entrypoint")
    source_files = [
        _safe_relative_path(path, "proposal.implementation.source_files entry")
        for path in _text_list(implementation_raw["source_files"], "proposal.implementation.source_files", allow_empty=False)
    ]
    if len(set(source_files)) != len(source_files):
        raise SpawnError("proposal.implementation.source_files entries must be unique")
    missing_sources = sorted({entrypoint, *source_files} - set(files))
    if missing_sources:
        raise SpawnError("proposal implementation files are missing from the payload", {"missing_files": missing_sources})
    implementation: dict[str, Any] = {
        "kind": implementation_kind,
        "entrypoint": entrypoint,
        "source_files": source_files,
    }
    if "runtime" in implementation_raw:
        implementation["runtime"] = _required_text(implementation_raw["runtime"], "proposal.implementation.runtime", maximum=200)
    _kind_specific_proposal_checks(kind, implementation)

    contracts_raw = _closed_object(
        proposal["contracts"],
        "proposal.contracts",
        {"inputs", "outputs", "provides", "requires"},
    )
    if not isinstance(contracts_raw["inputs"], dict) or not isinstance(contracts_raw["outputs"], dict):
        raise SpawnError("proposal.contracts inputs and outputs must be objects")
    contracts = {
        "inputs": copy.deepcopy(contracts_raw["inputs"]),
        "outputs": copy.deepcopy(contracts_raw["outputs"]),
        "provides": _interface_list(contracts_raw["provides"], "proposal.contracts.provides"),
        "requires": _interface_list(contracts_raw["requires"], "proposal.contracts.requires"),
    }
    overlap = sorted(set(contracts["provides"]) & set(contracts["requires"]))
    if overlap:
        raise SpawnError("a unit cannot both provide and require the same interface", {"interfaces": overlap})

    if not isinstance(proposal["dependencies"], list) or len(proposal["dependencies"]) > 128:
        raise SpawnError("proposal.dependencies must be a list with at most 128 entries")
    dependencies: list[dict[str, Any]] = []
    dependency_refs: set[str] = set()
    for index, dependency in enumerate(proposal["dependencies"]):
        row = _closed_object(dependency, f"proposal.dependencies[{index}]", {"kind", "ref", "optional"})
        dependency_kind = _required_text(row["kind"], f"proposal.dependencies[{index}].kind", maximum=64).casefold()
        if KIND_RE.fullmatch(dependency_kind) is None:
            raise SpawnError("dependency kind is invalid", {"index": index, "kind": dependency_kind})
        ref = _required_text(row["ref"], f"proposal.dependencies[{index}].ref", maximum=240)
        if "@" not in ref:
            raise SpawnError("dependency refs must be exact id@version references", {"index": index, "ref": ref})
        if not isinstance(row["optional"], bool):
            raise SpawnError("dependency optional must be boolean", {"index": index})
        key = f"{dependency_kind}:{ref}"
        if key in dependency_refs:
            raise SpawnError("proposal dependencies must be unique", {"duplicate": key})
        dependency_refs.add(key)
        dependencies.append({"kind": dependency_kind, "ref": ref, "optional": row["optional"]})

    if not isinstance(proposal["relationships"], list) or len(proposal["relationships"]) > 128:
        raise SpawnError("proposal.relationships must be a list with at most 128 entries")
    relationships: list[dict[str, str]] = []
    for index, relationship in enumerate(proposal["relationships"]):
        row = _closed_object(relationship, f"proposal.relationships[{index}]", {"type", "target"})
        relationships.append({
            "type": _required_text(row["type"], f"proposal.relationships[{index}].type", maximum=120),
            "target": _required_text(row["target"], f"proposal.relationships[{index}].target", maximum=240),
        })

    checks = _normal_checks(proposal["verification"], files)
    provenance_raw = _closed_object(proposal["provenance"], "proposal.provenance", {"kind", "refs", "basis"})
    provenance = {
        "kind": _required_text(provenance_raw["kind"], "proposal.provenance.kind", maximum=120),
        "refs": _text_list(provenance_raw["refs"], "proposal.provenance.refs", allow_empty=False),
        "basis": _required_text(provenance_raw["basis"], "proposal.provenance.basis", maximum=1000),
    }
    limitations = _text_list(proposal["limitations"], "proposal.limitations", allow_empty=False)
    authority = _authority(proposal["authority"])
    root_fit = evaluate_declared_root_fit(proposal)
    if root_fit.get("fit") is not True:
        raise SpawnError("proposal must include an inspectable positive four-root fit", {"root_fit": root_fit})

    normalized = {
        "schema": SPAWN_PROPOSAL_SCHEMA,
        "id": unit_id,
        "version": version,
        "kind": kind,
        "purpose": purpose,
        "files": files,
        "implementation": implementation,
        "contracts": contracts,
        "dependencies": dependencies,
        "relationships": relationships,
        "verification": {"checks": checks},
        "provenance": provenance,
        "limitations": limitations,
        "authority": authority,
        "root_fit": copy.deepcopy(proposal["root_fit"]),
    }
    return normalized


def creation_forge_summary() -> dict[str, Any]:
    return {
        "truth_status": "DETERMINISTIC_DETACHED_CREATION_UNIT_FORGE",
        "proposal_schema": SPAWN_PROPOSAL_SCHEMA,
        "package_schema": SPAWNED_UNIT_SCHEMA,
        "first_class_kinds": copy.deepcopy(FIRST_CLASS_KINDS),
        "extension_kinds_allowed": True,
        "operations": ["spawn", "inspect", "test", "request-admission-check"],
        "deterministic_rebuild_from_same_proposal": True,
        "normal_output_is_detached": True,
        "automatic_execution": False,
        "automatic_install_or_registration": False,
        "automatic_merge_or_promotion": False,
        "capability_and_hand_candidates_receive_declared_test_execution": True,
        "organ_candidates_receive_executable_package_schema_validation": True,
        "other_kinds_currently_receive_structural_and_declared_file_checks": True,
        "candidate_design_source": "supplied by a human, AI, deterministic recipe, or explicitly labelled external boundary; the forge does not claim to invent semantic design by itself",
    }


def _payload_records(files: dict[str, str]) -> list[dict[str, Any]]:
    return [
        {"path": path, "bytes": len(content.encode("utf-8")), "digest": _digest_bytes(content.encode("utf-8"))}
        for path, content in sorted(files.items())
    ]


def _materialization_checks(proposal: dict[str, Any]) -> list[dict[str, Any]]:
    checks = copy.deepcopy(proposal["verification"]["checks"])
    required_checks = [{"type": "file-exists", "path": proposal["implementation"]["entrypoint"]}]
    required_checks.extend({"type": "nonempty", "path": path} for path in proposal["implementation"]["source_files"])
    return [*required_checks, *checks]


def _project_type(proposal: dict[str, Any]) -> str:
    return "python" if any(path.casefold().endswith(".py") for path in proposal["files"]) else "generic"


def _core_package(proposal: dict[str, Any]) -> tuple[dict[str, Any], dict[str, str]]:
    proposal_digest = _digest_value(proposal)
    payload = _payload_records(proposal["files"])
    manifest = {
        "schema": SPAWNED_UNIT_SCHEMA,
        "id": proposal["id"],
        "version": proposal["version"],
        "ref": f"{proposal['id']}@{proposal['version']}",
        "status": "DETACHED_CANDIDATE",
        "kind": proposal["kind"],
        "kind_contract": "FIRST_CLASS" if proposal["kind"] in FIRST_CLASS_KINDS else "OPEN_EXTENSION_GENERIC",
        "purpose": proposal["purpose"],
        "implementation": copy.deepcopy(proposal["implementation"]),
        "contracts": copy.deepcopy(proposal["contracts"]),
        "dependencies": copy.deepcopy(proposal["dependencies"]),
        "relationships": copy.deepcopy(proposal["relationships"]),
        "verification": copy.deepcopy(proposal["verification"]),
        "provenance": copy.deepcopy(proposal["provenance"]),
        "limitations": copy.deepcopy(proposal["limitations"]),
        "authority": copy.deepcopy(proposal["authority"]),
        "root_fit": copy.deepcopy(proposal["root_fit"]),
        "proposal_digest": proposal_digest,
        "payload_files": payload,
        "truth_boundaries": {
            "materialized_is_not_installed": True,
            "materialized_is_not_registered": True,
            "materialized_is_not_runtime_proof": True,
            "materialized_is_not_merge_approval": True,
            "capability_is_not_authority": True,
        },
    }
    proposal_text = _json_text(proposal)
    manifest_text = _json_text(manifest)
    package_files = {
        **proposal["files"],
        PROPOSAL_FILE: proposal_text,
        UNIT_FILE: manifest_text,
    }
    return manifest, package_files


def spawn_unit(target: Path, raw_proposal: Any, replace: bool = False) -> dict[str, Any]:
    target = Path(target).resolve()
    proposal = validate_spawn_proposal(raw_proposal)
    manifest, pre_receipt_files = _core_package(proposal)
    checks = _materialization_checks(proposal)
    project_type = _project_type(proposal)

    with tempfile.TemporaryDirectory(prefix="axm-spawn-stage-") as temp_dir:
        staged_target = Path(temp_dir) / "candidate"
        staged = build_project(
            target=staged_target,
            files=pre_receipt_files,
            project_type=project_type,
            checks=checks,
            publish_mode="validated",
        )

    manifest_digest = _digest_bytes(pre_receipt_files[UNIT_FILE].encode("utf-8"))
    proposal_digest = manifest["proposal_digest"]
    package_digest = _digest_value({
        "proposal_digest": proposal_digest,
        "manifest_digest": manifest_digest,
        "payload_files": manifest["payload_files"],
    })
    body_records = _payload_records(pre_receipt_files)
    receipt_without_digest = {
        "schema": SPAWN_RECEIPT_SCHEMA,
        "status": "MATERIALIZED",
        "unit_ref": manifest["ref"],
        "kind": manifest["kind"],
        "kind_contract": manifest["kind_contract"],
        "proposal_digest": proposal_digest,
        "manifest_digest": manifest_digest,
        "package_digest": package_digest,
        "body_files": body_records,
        "project_type": project_type,
        "staged_validation_passed": staged["validation"]["passed"] is True,
        "staged_check_count": len(staged["validation"]["checks"]),
        "generated_code_executed": False,
        "installed": False,
        "registered": False,
        "promoted": False,
        "merged": False,
        "canon_changed": False,
        "permissions_changed": False,
        "runtime_evidence": "NOT_YET_OBSERVED; use the separate test operation",
    }
    receipt = {**receipt_without_digest, "receipt_digest": _digest_value(receipt_without_digest)}
    final_files = {**pre_receipt_files, RECEIPT_FILE: _json_text(receipt)}
    result = build_project(
        target=target,
        files=final_files,
        project_type=project_type,
        checks=checks,
        replace=replace,
        publish_mode="validated",
    )
    result.update({
        "operation": "spawn",
        "truth_status": "MATERIALIZED_DETACHED_CREATION_UNIT",
        "unit": manifest,
        "spawn_receipt": receipt,
        "live_machine_body_modified": False,
        "next_operation": "test",
    })
    return result


def _load_json(path: Path, label: str) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise SpawnError(f"could not read {label}: {exc}", {"path": str(path)}) from exc
    if not isinstance(value, dict):
        raise SpawnError(f"{label} must be a JSON object", {"path": str(path)})
    return value


def _actual_files(candidate: Path) -> list[str]:
    rows: list[str] = []
    for path in sorted(candidate.rglob("*")):
        if path.is_symlink():
            raise SpawnError("spawned unit contains a symbolic link; link semantics are not implemented", {"path": path.relative_to(candidate).as_posix()})
        if path.is_file():
            rows.append(path.relative_to(candidate).as_posix())
    return rows


def inspect_spawned_unit(candidate: Path) -> dict[str, Any]:
    candidate = Path(candidate).resolve()
    if not candidate.is_dir():
        raise SpawnError("spawned unit path is not a directory", {"path": str(candidate)})
    proposal = validate_spawn_proposal(_load_json(candidate / PROPOSAL_FILE, "spawn proposal"))
    manifest = _load_json(candidate / UNIT_FILE, "spawned unit manifest")
    receipt = _load_json(candidate / RECEIPT_FILE, "spawn receipt")

    expected_manifest, expected_pre_receipt_files = _core_package(proposal)
    expected_files = sorted([*expected_pre_receipt_files, RECEIPT_FILE])
    actual_files = _actual_files(candidate)
    allowed_runtime = [ADMISSION_FILE] if ADMISSION_FILE in actual_files else []
    unexpected_files = sorted(set(actual_files) - set(expected_files) - set(allowed_runtime))
    missing_files = sorted(set(expected_files) - set(actual_files))

    payload_checks: list[dict[str, Any]] = []
    for row in expected_manifest["payload_files"]:
        path = candidate.joinpath(*PurePosixPath(row["path"]).parts)
        actual_digest = _digest_bytes(path.read_bytes()) if path.is_file() else None
        payload_checks.append({
            "path": row["path"],
            "passed": actual_digest == row["digest"],
            "expected_digest": row["digest"],
            "actual_digest": actual_digest,
        })

    proposal_digest = _digest_value(proposal)
    manifest_text = (candidate / UNIT_FILE).read_bytes()
    manifest_digest = _digest_bytes(manifest_text)
    expected_package_digest = _digest_value({
        "proposal_digest": proposal_digest,
        "manifest_digest": manifest_digest,
        "payload_files": expected_manifest["payload_files"],
    })
    receipt_without_digest = {key: copy.deepcopy(value) for key, value in receipt.items() if key != "receipt_digest"}
    checks = {
        "proposal_digest": receipt.get("proposal_digest") == proposal_digest == manifest.get("proposal_digest"),
        "manifest_exact": manifest == expected_manifest,
        "manifest_digest": receipt.get("manifest_digest") == manifest_digest,
        "package_digest": receipt.get("package_digest") == expected_package_digest,
        "receipt_digest": receipt.get("receipt_digest") == _digest_value(receipt_without_digest),
        "payload_digests": bool(payload_checks) and all(row["passed"] for row in payload_checks),
        "file_set": not missing_files and not unexpected_files,
        "authority_closed": all(manifest.get("authority", {}).get(field) is False for field in AUTHORITY_FIELDS),
        "root_fit": evaluate_declared_root_fit(manifest).get("fit") is True,
    }
    passed = all(checks.values())
    admission: dict[str, Any] | None = None
    if ADMISSION_FILE in actual_files:
        prior = _load_json(candidate / ADMISSION_FILE, "admission request")
        admission = {
            "state": prior.get("state"),
            "unit_ref": prior.get("unit_ref"),
            "kind": prior.get("kind"),
            "test_passed": prior.get("test_passed"),
            "request_digest": prior.get("request_digest"),
        }
    return {
        "operation": "inspect",
        "truth_status": "OBSERVED_SPAWNED_UNIT_INTEGRITY",
        "path": str(candidate),
        "passed": passed,
        "unit": manifest,
        "spawn_receipt": receipt,
        "checks": checks,
        "payload_checks": payload_checks,
        "missing_files": missing_files,
        "unexpected_files": unexpected_files,
        "admission_request": admission,
        "live_machine_body_modified": False,
    }


def _identity_check(unit: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    expected = {"id": unit["id"], "version": unit["version"]}
    actual = {"id": entry.get("id"), "version": entry.get("version")}
    return {"passed": actual == expected, "expected": expected, "actual": actual}


def _test_kind(root: Path, candidate: Path, unit: dict[str, Any]) -> dict[str, Any]:
    kind = unit["kind"]
    entrypoint = candidate.joinpath(*PurePosixPath(unit["implementation"]["entrypoint"]).parts)
    if kind in {"hand", "capability"}:
        entry = _load_json(entrypoint, f"{kind} capability manifest")
        identity = _identity_check(unit, entry)
        capability_test = test_capability_candidate(root, entrypoint) if identity["passed"] else {
            "passed": False,
            "errors": ["entrypoint identity does not match the spawned unit"],
            "tests": [],
        }
        return {
            "kind": kind,
            "evidence_strength": "DECLARED_CANDIDATE_TESTS_EXECUTED",
            "passed": identity["passed"] and capability_test.get("passed") is True,
            "identity": identity,
            "capability_test": capability_test,
            "runtime_scope": "only the candidate's declared tests; no general behavior proof",
        }
    if kind == "organ":
        entry = _load_json(entrypoint, "executable organ package")
        identity = _identity_check(unit, entry)
        organ_result: dict[str, Any]
        try:
            with tempfile.TemporaryDirectory(prefix="axm-organ-candidate-") as temp_dir:
                organ_root = Path(temp_dir)
                folder = organ_root / "executable-organs"
                folder.mkdir()
                (folder / "candidate.json").write_text(entrypoint.read_text(encoding="utf-8"), encoding="utf-8")
                library = ExecutableOrganLibrary(organ_root)
                organ_result = {"passed": True, "package": library.inspect(f"{unit['id']}@{unit['version']}")}
        except ExecutableOrganError as exc:
            organ_result = {"passed": False, "error": str(exc), "details": exc.details}
        return {
            "kind": kind,
            "evidence_strength": "EXECUTABLE_ORGAN_PACKAGE_SCHEMA_VALIDATION",
            "passed": identity["passed"] and organ_result["passed"],
            "identity": identity,
            "organ_package_validation": organ_result,
            "runtime_executed": False,
        }
    if kind in {"protocol", "specialist", "recipe"}:
        entry = _load_json(entrypoint, f"{kind} entrypoint")
        identity = _identity_check(unit, entry)
        return {
            "kind": kind,
            "evidence_strength": "STRUCTURAL_ENTRYPOINT_AND_DECLARED_FILE_CHECKS",
            "passed": identity["passed"],
            "identity": identity,
            "runtime_executed": False,
        }
    return {
        "kind": kind,
        "evidence_strength": "DECLARED_FILE_CHECKS_ONLY",
        "passed": entrypoint.is_file() and entrypoint.stat().st_size > 0,
        "runtime_executed": False,
    }


def test_spawned_unit(root: Path, candidate: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    candidate = Path(candidate).resolve()
    inspection = inspect_spawned_unit(candidate)
    if not inspection["passed"]:
        return {
            "operation": "test",
            "truth_status": "SPAWNED_UNIT_INTEGRITY_FAILED",
            "path": str(candidate),
            "passed": False,
            "inspection": inspection,
            "live_machine_body_modified": False,
        }

    unit = inspection["unit"]
    expected_digests = {
        row["path"]: row["digest"].removeprefix("sha256:")
        for row in inspection["spawn_receipt"]["body_files"]
    }
    structural = validate_project(
        candidate,
        project_type=inspection["spawn_receipt"]["project_type"],
        checks=_materialization_checks(validate_spawn_proposal(_load_json(candidate / PROPOSAL_FILE, "spawn proposal"))),
        expected_file_digests=expected_digests,
    )
    kind_test = _test_kind(root, candidate, unit)
    passed = structural["passed"] is True and kind_test["passed"] is True
    return {
        "operation": "test",
        "truth_status": "OBSERVED_BOUNDED_SPAWNED_UNIT_TEST",
        "path": str(candidate),
        "passed": passed,
        "unit_ref": unit["ref"],
        "kind": unit["kind"],
        "inspection": inspection,
        "structural_validation": structural,
        "kind_test": kind_test,
        "installed": False,
        "registered": False,
        "promoted": False,
        "merged": False,
        "live_machine_body_modified": False,
        "limitations": [
            "a passing result covers only the exact deterministic checks shown",
            "materialization and package integrity do not by themselves prove semantic behavior",
            "visual, network, external-system, and physical effects require separate authorized evidence",
        ],
    }


def request_admission_check(
    root: Path,
    candidate: Path,
    readiness_statement: Any,
    requested_by: Any,
) -> dict[str, Any]:
    readiness = _required_text(readiness_statement, "readiness_statement", maximum=2000)
    requester = _required_text(requested_by, "requested_by", maximum=200)
    tested = test_spawned_unit(root, candidate)
    unit = tested.get("inspection", {}).get("unit", {})
    receipt = tested.get("inspection", {}).get("spawn_receipt", {})
    request_without_digest = {
        "schema": ADMISSION_REQUEST_SCHEMA,
        "state": "READY_FOR_HUMAN_ADMISSION_REVIEW" if tested["passed"] else "HELD_FAILED_TESTS",
        "unit_ref": unit.get("ref"),
        "kind": unit.get("kind"),
        "package_digest": receipt.get("package_digest"),
        "requested_by": requester,
        "readiness_statement": readiness,
        "test_passed": tested["passed"],
        "test_evidence_digest": _digest_value(tested),
        "test_evidence": tested,
        "approval_granted": False,
        "installed": False,
        "registered": False,
        "promoted": False,
        "merged": False,
        "canon_changed": False,
        "permissions_changed": False,
        "selection_authority": "NONE",
        "next_decision": "an authorized human or machine-body owner may inspect the exact candidate and separately choose whether and how to admit it",
    }
    request = {**request_without_digest, "request_digest": _digest_value(request_without_digest)}
    artifact = Path(candidate).resolve() / ADMISSION_FILE
    atomic_write_json(artifact, request)
    return {
        "operation": "request-admission-check",
        "truth_status": "ADMISSION_REVIEW_REQUESTED_NOT_APPROVED",
        "path": str(Path(candidate).resolve()),
        "request_state": request["state"],
        "request_artifact": str(artifact),
        "request": request,
        "admission_performed": False,
        "live_machine_body_modified": False,
    }


def operate_spawn_unit(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    path = Path(str(inputs.get("path", ""))).expanduser()
    if not path.is_absolute():
        path = Path(root) / path
    path = path.resolve()
    if operation == "spawn":
        if "replace" in inputs and not isinstance(inputs["replace"], bool):
            raise SpawnError("replace must be boolean when supplied")
        return spawn_unit(path, inputs.get("proposal"), replace=bool(inputs.get("replace", False)))
    if operation == "inspect":
        return inspect_spawned_unit(path)
    if operation == "test":
        return test_spawned_unit(root, path)
    if operation == "request-admission-check":
        return request_admission_check(
            root,
            path,
            readiness_statement=inputs.get("readiness_statement"),
            requested_by=inputs.get("requested_by", "spawned-unit-candidate"),
        )
    raise SpawnError(
        "unsupported creation-unit forge operation",
        {"operation": operation, "supported_operations": creation_forge_summary()["operations"]},
    )

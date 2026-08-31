from __future__ import annotations

import copy
import hashlib
import json
import tempfile
from pathlib import Path
from typing import Any

from .organ_library import ExecutableOrganError, ExecutableOrganLibrary
from .registry import Registry
from .spawn import SpawnError, spawn_unit, test_spawned_unit, validate_spawn_proposal


ORGAN_CENSUS_SCHEMA = "axm.organ-materialization-census/v0.1"
ORGAN_PROPOSAL_COMPILER_SCHEMA = "axm.organ-proposal-compiler/v0.1"
MATERIALIZATION_STATES = {
    "CONNECTED_EXECUTABLE_PACKAGE",
    "EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES",
    "IMPLEMENTATION_REQUIRED",
}
ZERO_AUTHORITY = {
    "execute": False,
    "install": False,
    "register": False,
    "promote": False,
    "merge": False,
    "canon": False,
    "permissions": False,
}


class OrganMaterializationError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _required_text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrganMaterializationError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise OrganMaterializationError(f"{label} exceeds its {maximum}-character bound")
    return text


def _bounded_integer(value: Any, label: str, *, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise OrganMaterializationError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n"


def _organ_records(root: Path) -> tuple[list[dict[str, Any]], dict[str, dict[str, Any]]]:
    records = [record for record in Registry(root).master_records() if record.get("level") == "organ"]
    records.sort(key=lambda record: str(record.get("id", "")))
    by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        organ_id = _required_text(record.get("id"), "registry organ id", maximum=240)
        if organ_id in by_id:
            raise OrganMaterializationError("registry organ IDs must be unique", {"duplicate_id": organ_id})
        by_id[organ_id] = record
    return records, by_id


def _source_observations(
    root: Path,
    records: list[dict[str, Any]],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    observations: dict[str, dict[str, Any]] = {}
    for record in records:
        organ_id = str(record["id"])
        relative = f"organs/{organ_id}.json"
        path = root / relative
        observation: dict[str, Any] = {"path": relative, "status": "MISSING"}
        if path.is_file():
            try:
                observed = json.loads(path.read_text(encoding="utf-8"))
                observation["status"] = "EXACT" if observed == record else "DIVERGENT"
            except (OSError, UnicodeError, json.JSONDecodeError) as exc:
                observation.update({"status": "INVALID", "error": str(exc)})
        observations[organ_id] = observation
    known = set(observations)
    extra = sorted(path.relative_to(root).as_posix() for path in (root / "organs").glob("*.json") if path.stem not in known)
    return observations, extra


def _declared_organ_total(root: Path) -> int | None:
    path = root / "registry_materialization.json"
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError):
        return None
    count = value.get("counts", {}).get("organ") if isinstance(value, dict) else None
    return count if isinstance(count, int) and not isinstance(count, bool) else None


def _package_connectivity(packages: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    by_ref = {package["ref"]: package for package in packages}
    connected_types: dict[str, set[str]] = {ref: set() for ref in by_ref}
    changed = True
    while changed:
        changed = False
        for package in packages:
            for project_type in package["project_types"]:
                if project_type in connected_types[package["ref"]]:
                    continue
                requirements_covered = all(
                    any(
                        required in provider["provides"]
                        and project_type in provider["project_types"]
                        and project_type in connected_types[provider["ref"]]
                        for provider in packages
                    )
                    for required in package["requires"]
                )
                if requirements_covered:
                    connected_types[package["ref"]].add(project_type)
                    changed = True

    connectivity: dict[str, dict[str, Any]] = {}
    for package in packages:
        missing: list[str] = []
        providers: dict[str, list[str]] = {}
        connected_providers: dict[str, list[str]] = {}
        for required in package["requires"]:
            matches = sorted(
                candidate["ref"]
                for candidate in packages
                if required in candidate["provides"]
                and set(package["project_types"]).intersection(candidate["project_types"])
            )
            ready_matches = sorted(
                candidate["ref"]
                for candidate in packages
                if required in candidate["provides"]
                and set(package["project_types"]).intersection(connected_types[candidate["ref"]])
            )
            providers[required] = matches
            connected_providers[required] = ready_matches
            if not ready_matches:
                missing.append(required)
        connectivity[package["ref"]] = {
            "required_interface_providers": providers,
            "connected_required_interface_providers": connected_providers,
            "unresolved_required_interfaces": missing,
            "connected_project_types": sorted(connected_types[package["ref"]]),
            "interface_coverage_complete": bool(connected_types[package["ref"]]),
        }
    return connectivity


def _census_data(root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    root = Path(root).resolve()
    records, by_id = _organ_records(root)
    source_observations, extra_source_files = _source_observations(root, records)
    library = ExecutableOrganLibrary(root)
    packages = library.list()
    connectivity = _package_connectivity(packages)

    package_refs_by_anatomy: dict[str, list[str]] = {organ_id: [] for organ_id in by_id}
    dangling_anatomy_refs: list[dict[str, str]] = []
    packages_without_anatomy_refs: list[str] = []
    for package in packages:
        if not package["anatomy_refs"]:
            packages_without_anatomy_refs.append(package["ref"])
        for anatomy_ref in package["anatomy_refs"]:
            if anatomy_ref in package_refs_by_anatomy:
                package_refs_by_anatomy[anatomy_ref].append(package["ref"])
            else:
                dangling_anatomy_refs.append({"package_ref": package["ref"], "anatomy_ref": anatomy_ref})

    package_by_ref = {package["ref"]: package for package in packages}
    rows: list[dict[str, Any]] = []
    for record in records:
        organ_id = str(record["id"])
        package_refs = sorted(package_refs_by_anatomy[organ_id])
        connected_package_refs = [
            ref for ref in package_refs if connectivity[ref]["interface_coverage_complete"]
        ]
        incomplete_package_refs = [
            ref for ref in package_refs if not connectivity[ref]["interface_coverage_complete"]
        ]
        unresolved = sorted({
            interface
            for ref in incomplete_package_refs
            for interface in connectivity[ref]["unresolved_required_interfaces"]
        })
        if not package_refs:
            state = "IMPLEMENTATION_REQUIRED"
        elif connected_package_refs:
            state = "CONNECTED_EXECUTABLE_PACKAGE"
        else:
            state = "EXECUTABLE_PACKAGE_WITH_MISSING_INTERFACES"
        rows.append({
            "anatomy_id": organ_id,
            "name": record.get("name"),
            "domain_code": record.get("domain_code"),
            "domain": record.get("domain"),
            "registry_status": record.get("registry_status"),
            "maturity": record.get("maturity"),
            "source_basis": record.get("source_basis"),
            "source_keys": copy.deepcopy(record.get("source_keys", [])),
            "descriptive_source": source_observations[organ_id],
            "materialization": {
                "state": state,
                "package_refs": package_refs,
                "connected_package_refs": connected_package_refs,
                "package_refs_with_missing_interfaces": incomplete_package_refs,
                "provided_interfaces": sorted({
                    interface for ref in package_refs for interface in package_by_ref[ref]["provides"]
                }),
                "required_interfaces": sorted({
                    interface for ref in package_refs for interface in package_by_ref[ref]["requires"]
                }),
                "unresolved_required_interfaces": unresolved,
                "package_connectivity": [
                    {"package_ref": ref, **copy.deepcopy(connectivity[ref])}
                    for ref in package_refs
                ],
                "installed_package_count": len(package_refs),
            },
        })

    state_counts = {state: 0 for state in sorted(MATERIALIZATION_STATES)}
    for row in rows:
        state_counts[row["materialization"]["state"]] += 1
    source_counts = {state: 0 for state in ("EXACT", "MISSING", "DIVERGENT", "INVALID")}
    for observation in source_observations.values():
        source_counts[observation["status"]] += 1
    summary = {
        "schema": ORGAN_CENSUS_SCHEMA,
        "truth_status": "OBSERVED_ORGAN_MATERIALIZATION_CENSUS",
        "declared_anatomy_organs": _declared_organ_total(root),
        "observed_registry_organs": len(records),
        "standalone_organ_source_files": len(list((root / "organs").glob("*.json"))),
        "source_record_states": source_counts,
        "source_records_exact": source_counts["EXACT"] == len(records) and not extra_source_files,
        "extra_source_files": extra_source_files,
        "installed_executable_packages": len(packages),
        "installed_package_refs": sorted(package_by_ref),
        "anatomy_materialization_states": state_counts,
        "anatomy_with_installed_packages": len(records) - state_counts["IMPLEMENTATION_REQUIRED"],
        "anatomy_requiring_implementation": state_counts["IMPLEMENTATION_REQUIRED"],
        "dangling_installed_anatomy_refs": dangling_anatomy_refs,
        "installed_packages_without_anatomy_refs": sorted(packages_without_anatomy_refs),
        "all_descriptive_organs_executable": state_counts["IMPLEMENTATION_REQUIRED"] == 0,
        "connectivity_meaning": "a finite transitive chain of exact installed provided/required interfaces within one declared project type; not uniqueness, semantic conformance, or runtime proof",
        "truth_boundaries": {
            "descriptive_record_is_executable_body": False,
            "package_schema_validation_is_runtime_proof": False,
            "interface_coverage_is_semantic_conformance": False,
            "candidate_materialization_is_installation": False,
        },
    }
    return summary, rows


def organ_materialization_summary(root: Path) -> dict[str, Any]:
    summary, _rows = _census_data(root)
    return summary


def census_organs(
    root: Path,
    *,
    anatomy_id: Any = None,
    domain_code: Any = None,
    state: Any = None,
    offset: Any = 0,
    limit: Any = 415,
) -> dict[str, Any]:
    summary, rows = _census_data(root)
    if anatomy_id is not None:
        selected_id = _required_text(anatomy_id, "anatomy_id", maximum=240)
        rows = [row for row in rows if row["anatomy_id"] == selected_id]
        if not rows:
            raise OrganMaterializationError("unknown organ anatomy ID", {"anatomy_id": selected_id})
    if domain_code is not None:
        selected_domain = _required_text(domain_code, "domain_code", maximum=120).casefold()
        rows = [row for row in rows if str(row["domain_code"]).casefold() == selected_domain]
    if state is not None:
        selected_state = _required_text(state, "state", maximum=80).upper()
        if selected_state not in MATERIALIZATION_STATES:
            raise OrganMaterializationError(
                "unsupported organ materialization state",
                {"state": selected_state, "supported_states": sorted(MATERIALIZATION_STATES)},
            )
        rows = [row for row in rows if row["materialization"]["state"] == selected_state]
    selected_offset = _bounded_integer(offset, "offset", minimum=0, maximum=415)
    selected_limit = _bounded_integer(limit, "limit", minimum=1, maximum=415)
    page = rows[selected_offset:selected_offset + selected_limit]
    return {
        "operation": "census",
        "truth_status": summary["truth_status"],
        "summary": summary,
        "filters": {
            "anatomy_id": anatomy_id,
            "domain_code": domain_code,
            "state": state,
        },
        "pagination": {
            "offset": selected_offset,
            "limit": selected_limit,
            "matched": len(rows),
            "returned": len(page),
            "has_more": selected_offset + len(page) < len(rows),
        },
        "organs": page,
        "live_machine_body_modified": False,
    }


def _validated_package(raw_package: Any) -> dict[str, Any]:
    if not isinstance(raw_package, dict):
        raise OrganMaterializationError("package must be an executable-organ package object")
    with tempfile.TemporaryDirectory(prefix="axm-organ-materialization-package-") as temp_dir:
        root = Path(temp_dir)
        folder = root / "executable-organs"
        folder.mkdir()
        (folder / "candidate.json").write_text(_canonical_json(raw_package), encoding="utf-8")
        try:
            library = ExecutableOrganLibrary(root)
            refs = library.summary()["package_refs"]
            package = library.inspect(refs[0])
        except ExecutableOrganError as exc:
            raise OrganMaterializationError(str(exc), exc.details) from exc
    package.pop("ref", None)
    package.pop("source_path", None)
    return package


def compile_organ_proposal(root: Path, anatomy_id: Any, raw_package: Any) -> dict[str, Any]:
    root = Path(root).resolve()
    selected_id = _required_text(anatomy_id, "anatomy_id", maximum=240)
    records, by_id = _organ_records(root)
    record = by_id.get(selected_id)
    if record is None:
        raise OrganMaterializationError("unknown organ anatomy ID", {"anatomy_id": selected_id})
    observations, _extra = _source_observations(root, records)
    if observations[selected_id]["status"] != "EXACT":
        raise OrganMaterializationError(
            "organ anatomy source must exactly match the canonical registry record",
            {"anatomy_id": selected_id, "source": observations[selected_id]},
        )

    package = _validated_package(raw_package)
    package_ref = f"{package['id']}@{package['version']}"
    if selected_id not in package["anatomy_refs"]:
        raise OrganMaterializationError(
            "package does not explicitly materialize the selected anatomy ID",
            {"anatomy_id": selected_id, "package_anatomy_refs": package["anatomy_refs"]},
        )
    unknown_refs = sorted(set(package["anatomy_refs"]) - set(by_id))
    if unknown_refs:
        raise OrganMaterializationError(
            "package names unknown anatomy references",
            {"unknown_anatomy_refs": unknown_refs},
        )
    nonexact_refs = [ref for ref in package["anatomy_refs"] if observations[ref]["status"] != "EXACT"]
    if nonexact_refs:
        raise OrganMaterializationError(
            "every package anatomy reference must have an exact standalone source record",
            {"nonexact_anatomy_refs": nonexact_refs},
        )
    installed_refs = set(ExecutableOrganLibrary(root).summary()["package_refs"])
    if package_ref in installed_refs:
        raise OrganMaterializationError(
            "an executable organ with this exact ref is already installed",
            {"package_ref": package_ref},
        )

    entrypoint = "organ.json"
    package_text = _canonical_json(package)
    package_sha256 = hashlib.sha256(package_text.encode("utf-8")).hexdigest()
    provenance_basis = (
        "Compiled only from the explicitly supplied executable-organ package and exact cited anatomy records. "
        f"Supplied package basis: {package['provenance']['basis']}"
    )
    if len(provenance_basis) > 1000:
        raise OrganMaterializationError("compiled proposal provenance basis exceeds its 1000-character bound")
    limitations = [*package["limitations"]]
    compiler_limit = (
        "This candidate proves exact package structure and declared deterministic file checks; semantic interface "
        "conformance and emitted runtime behavior require separate evidence."
    )
    if compiler_limit not in limitations:
        limitations.append(compiler_limit)
    proposal = {
        "schema": "axm.creation-unit-spawn-proposal/v0.1",
        "id": package["id"],
        "version": package["version"],
        "kind": "organ",
        "purpose": package["purpose"],
        "files": {entrypoint: package_text},
        "implementation": {
            "kind": "DETERMINISTIC_SOURCE",
            "entrypoint": entrypoint,
            "source_files": [entrypoint],
        },
        "contracts": {
            "inputs": {
                "parameters": copy.deepcopy(package["parameters"]),
                "project_types": copy.deepcopy(package["project_types"]),
            },
            "outputs": {
                "template_files": sorted(package["files"]),
                "project_types": copy.deepcopy(package["project_types"]),
            },
            "provides": copy.deepcopy(package["provides"]),
            "requires": copy.deepcopy(package["requires"]),
        },
        "dependencies": [],
        "relationships": [
            {"type": "materializes-anatomy", "target": ref}
            for ref in package["anatomy_refs"]
        ],
        "verification": {
            "checks": [
                {"type": "json-valid", "path": entrypoint},
                {"type": "json-value", "path": entrypoint, "json_path": ["schema"], "equals": package["schema"]},
                {"type": "json-value", "path": entrypoint, "json_path": ["id"], "equals": package["id"]},
                {"type": "json-value", "path": entrypoint, "json_path": ["version"], "equals": package["version"]},
                {"type": "json-value", "path": entrypoint, "json_path": ["status"], "equals": "executable"},
                {"type": "sha256", "path": entrypoint, "sha256": package_sha256},
            ],
        },
        "provenance": {
            "kind": "compiled-explicit-organ-package",
            "refs": [f"organs/{ref}.json" for ref in package["anatomy_refs"]],
            "basis": provenance_basis,
        },
        "limitations": limitations,
        "authority": copy.deepcopy(ZERO_AUTHORITY),
        "root_fit": {
            "truth": {
                "fit": True,
                "basis": "The exact supplied package, anatomy references, compiler checks, and unproven runtime boundary remain visible.",
            },
            "agency": {
                "fit": True,
                "basis": "The caller chooses the implementation source and target anatomy; the detached proposal grants itself no authority.",
            },
            "continuity": {
                "fit": True,
                "basis": "Compilation produces a detached candidate and does not replace or install into the continuing machine.",
            },
            "wisdom-before-speed": {
                "fit": True,
                "basis": "Exact package validation and bounded tests precede any separate adoption decision.",
            },
        },
    }
    try:
        return validate_spawn_proposal(proposal)
    except SpawnError as exc:
        raise OrganMaterializationError(str(exc), exc.details) from exc


def prepare_organ_materialization(root: Path, anatomy_id: Any, raw_package: Any) -> dict[str, Any]:
    proposal = compile_organ_proposal(root, anatomy_id, raw_package)
    return {
        "operation": "prepare",
        "schema": ORGAN_PROPOSAL_COMPILER_SCHEMA,
        "truth_status": "FORGE_READY_EXPLICIT_ORGAN_PROPOSAL",
        "anatomy_id": str(anatomy_id).strip(),
        "package_ref": f"{proposal['id']}@{proposal['version']}",
        "proposal": proposal,
        "source_invented": False,
        "materialized": False,
        "tested": False,
        "installed": False,
        "registered": False,
        "live_machine_body_modified": False,
        "next_operation": "materialize-and-test",
    }


def materialize_and_test_organ(
    root: Path,
    target: Path,
    anatomy_id: Any,
    raw_package: Any,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    proposal = compile_organ_proposal(root, anatomy_id, raw_package)
    spawned = spawn_unit(target, proposal, replace=replace)
    tested = test_spawned_unit(root, target)
    passed = tested.get("passed") is True
    return {
        "operation": "materialize-and-test",
        "schema": ORGAN_PROPOSAL_COMPILER_SCHEMA,
        "truth_status": (
            "MATERIALIZED_TESTED_DETACHED_ORGAN_CANDIDATE"
            if passed
            else "MATERIALIZED_DETACHED_ORGAN_CANDIDATE_TEST_FAILED"
        ),
        "passed": passed,
        "anatomy_id": str(anatomy_id).strip(),
        "package_ref": f"{proposal['id']}@{proposal['version']}",
        "path": str(Path(target).resolve()),
        "proposal": proposal,
        "spawn": spawned,
        "test": tested,
        "source_invented": False,
        "materialized": True,
        "tested": True,
        "installed": False,
        "registered": False,
        "promoted": False,
        "connected_to_live_library": False,
        "live_machine_body_modified": False,
        "next_operation": "adopt-organ" if passed else "repair-supplied-package-or-checks",
    }


def operate_organ_materialization(root: Path, inputs: Any) -> dict[str, Any]:
    if not isinstance(inputs, dict):
        raise OrganMaterializationError("organ materialization inputs must be an object")
    operation = _required_text(inputs.get("operation"), "operation", maximum=80).casefold()
    allowed_by_operation = {
        "census": {"operation", "anatomy_id", "domain_code", "state", "offset", "limit"},
        "prepare": {"operation", "anatomy_id", "package"},
        "materialize-and-test": {"operation", "path", "anatomy_id", "package", "replace"},
    }
    allowed = allowed_by_operation.get(operation)
    if allowed is None:
        raise OrganMaterializationError(
            "unsupported organ materialization operation",
            {"operation": operation, "supported_operations": sorted(allowed_by_operation)},
        )
    unexpected = sorted(set(inputs) - allowed)
    if unexpected:
        raise OrganMaterializationError(
            "organ materialization inputs contain unsupported fields",
            {"operation": operation, "unexpected_fields": unexpected},
        )
    if operation == "census":
        return census_organs(
            root,
            anatomy_id=inputs.get("anatomy_id"),
            domain_code=inputs.get("domain_code"),
            state=inputs.get("state"),
            offset=inputs.get("offset", 0),
            limit=inputs.get("limit", 415),
        )
    missing = sorted(field for field in ("anatomy_id", "package") if field not in inputs)
    if missing:
        raise OrganMaterializationError(
            "organ materialization is missing required implementation inputs",
            {"operation": operation, "missing_fields": missing},
        )
    if operation == "prepare":
        return prepare_organ_materialization(root, inputs["anatomy_id"], inputs["package"])
    if "path" not in inputs:
        raise OrganMaterializationError(
            "materialize-and-test requires a detached candidate path",
            {"missing_fields": ["path"]},
        )
    if "replace" in inputs and not isinstance(inputs["replace"], bool):
        raise OrganMaterializationError("replace must be a boolean")
    return materialize_and_test_organ(
        root,
        Path(_required_text(inputs["path"], "path", maximum=1000)),
        inputs["anatomy_id"],
        inputs["package"],
        replace=inputs.get("replace", False),
    )

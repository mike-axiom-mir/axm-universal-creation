from __future__ import annotations

import copy
import hashlib
import json
import shutil
import tempfile
from pathlib import Path, PurePosixPath
from typing import Any

from .organ_discovery import discover_interface_assembly
from .organ_library import ExecutableOrganError, ExecutableOrganLibrary, resolve_organ_assembly
from .organ_project import assemble_organ_project
from .project import ProjectError


ORGAN_GAP_EXPERIMENT_SCHEMA = "axm.missing-organ-closure-experiment/v0.1"


class OrganGapError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


class CandidateSourceDriftError(OrganGapError):
    pass


def _sha256_text(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode('utf-8')).hexdigest()}"


def _public_candidate_package(proposal: dict[str, Any]) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    entrypoint = proposal["implementation"]["entrypoint"]
    text = proposal["files"][entrypoint]
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        return None, {
            "reason": "the supplied organ entrypoint is not valid JSON",
            "entrypoint": entrypoint,
            "line": exc.lineno,
            "column": exc.colno,
        }
    if not isinstance(raw, dict):
        return None, {
            "reason": "the supplied organ entrypoint must be a JSON object",
            "entrypoint": entrypoint,
        }
    expected_ref = f"{proposal['id']}@{proposal['version']}"
    try:
        with tempfile.TemporaryDirectory(prefix="axm-organ-gap-package-") as temp_dir:
            package_root = Path(temp_dir)
            folder = package_root / "executable-organs"
            folder.mkdir()
            (folder / "candidate.json").write_text(text, encoding="utf-8")
            package = ExecutableOrganLibrary(package_root).inspect(expected_ref)
    except ExecutableOrganError as exc:
        return None, {
            "reason": "the supplied organ entrypoint does not satisfy the executable-organ package contract",
            "entrypoint": entrypoint,
            "error": str(exc),
            "details": copy.deepcopy(exc.details),
        }
    package["source_path"] = entrypoint
    package["source_context"] = "supplied Forge proposal entrypoint validated in a disposable package library"
    return package, None


def _contract_alignment(
    proposal: dict[str, Any],
    package: dict[str, Any],
) -> dict[str, Any]:
    declared_provides = set(proposal["contracts"]["provides"])
    declared_requires = set(proposal["contracts"]["requires"])
    package_provides = set(package["provides"])
    package_requires = set(package["requires"])
    return {
        "passed": declared_provides == package_provides and declared_requires == package_requires,
        "proposal_provides": sorted(declared_provides),
        "package_provides": sorted(package_provides),
        "missing_provides_in_proposal": sorted(package_provides - declared_provides),
        "unexpected_provides_in_proposal": sorted(declared_provides - package_provides),
        "proposal_requires": sorted(declared_requires),
        "package_requires": sorted(package_requires),
        "missing_requires_in_proposal": sorted(package_requires - declared_requires),
        "unexpected_requires_in_proposal": sorted(declared_requires - package_requires),
        "comparison": "exact set equality between Forge unit contracts and executable-organ package declarations",
    }


def _base_result(
    target: Path,
    initial_discovery: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema": ORGAN_GAP_EXPERIMENT_SCHEMA,
        "operation": "explore-missing-organ-closure",
        "path": str(target),
        "initial_discovery": copy.deepcopy(initial_discovery),
        "missing_unit_contracts": copy.deepcopy(initial_discovery.get("missing_unit_contracts", [])),
        "selection_authority": "NONE",
        "admission_authority": "NONE",
        "automatic_source_invention": False,
        "candidate_design_supplied_to_operation": True,
        "live_machine_body_modified": False,
        "installed": False,
        "registered": False,
        "promoted": False,
        "merged": False,
        "canon_changed": False,
        "permissions_changed": False,
    }


def _hold(
    base: dict[str, Any],
    status: str,
    truth_status: str,
    reason: str,
    **evidence: Any,
) -> dict[str, Any]:
    return {
        **base,
        "status": status,
        "truth_status": truth_status,
        "passed": False,
        "hold_reason": reason,
        "candidate_target_created": bool(base.get("candidate_target_created", False)),
        **evidence,
    }


def _overlay_sources(
    root: Path,
    overlay_root: Path,
    candidate_entrypoint: Path,
    candidate_digest: str,
) -> list[dict[str, Any]]:
    overlay_folder = overlay_root / "executable-organs"
    overlay_folder.mkdir()
    receipts: list[dict[str, Any]] = []
    for source in sorted((root / "executable-organs").glob("*.json")):
        destination = overlay_folder / source.name
        shutil.copy2(source, destination)
        receipts.append({
            "role": "installed-live-source",
            "source_path": source.relative_to(root).as_posix(),
            "overlay_path": destination.relative_to(overlay_root).as_posix(),
            "sha256": f"sha256:{hashlib.sha256(destination.read_bytes()).hexdigest()}",
        })
    candidate_name = f"candidate-{candidate_digest.removeprefix('sha256:')[:16]}.json"
    destination = overlay_folder / candidate_name
    if destination.exists():
        raise OrganGapError(
            "candidate overlay path collides with an installed package source",
            {"overlay_path": destination.relative_to(overlay_root).as_posix()},
        )
    shutil.copy2(candidate_entrypoint, destination)
    copied_digest = f"sha256:{hashlib.sha256(destination.read_bytes()).hexdigest()}"
    if copied_digest != candidate_digest:
        raise CandidateSourceDriftError(
            "candidate organ source changed after its detached Forge test",
            {
                "source_path": str(candidate_entrypoint),
                "overlay_path": destination.relative_to(overlay_root).as_posix(),
                "expected_sha256": candidate_digest,
                "observed_sha256": copied_digest,
            },
        )
    receipts.append({
        "role": "detached-candidate-source",
        "source_path": str(candidate_entrypoint),
        "overlay_path": destination.relative_to(overlay_root).as_posix(),
        "sha256": candidate_digest,
    })
    return receipts


def _disposed_build_receipt(result: dict[str, Any]) -> dict[str, Any]:
    receipt = copy.deepcopy(result)
    receipt.pop("path", None)
    receipt["ephemeral_project_disposed"] = True
    receipt["project_persisted_outside_candidate"] = False
    receipt["runtime_behavior_executed"] = False
    return receipt


def explore_missing_organ_closure(
    root: Path,
    target: Path,
    raw_goal: Any,
    raw_proposal: Any,
    *,
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    from .spawn import SpawnError, spawn_unit, test_spawned_unit, validate_spawn_proposal

    root = Path(root).resolve()
    target = Path(target).resolve()
    initial = discover_interface_assembly(root, raw_goal)
    base = _base_result(target, initial)
    if initial["status"] != "HOLD_MISSING_ORGAN_INTERFACE":
        return _hold(
            base,
            "HOLD_NO_MISSING_ORGAN_INTERFACE_TO_CLOSE",
            "DETERMINISTIC_SCOPE_HOLD",
            "this operation begins only from a currently observed missing executable-organ interface",
        )

    try:
        proposal = validate_spawn_proposal(raw_proposal)
    except SpawnError as exc:
        return _hold(
            base,
            "HOLD_INVALID_ORGAN_FORGE_PROPOSAL",
            "DETERMINISTIC_PROPOSAL_CONTRACT_HOLD",
            "the supplied design does not satisfy the closed Creation-Unit Forge proposal contract",
            proposal_error={"message": str(exc), "details": copy.deepcopy(exc.details)},
        )
    if proposal["kind"] != "organ":
        return _hold(
            base,
            "HOLD_FORGE_PROPOSAL_IS_NOT_ORGAN",
            "DETERMINISTIC_KIND_HOLD",
            "a missing executable-organ interface can be tested here only with an explicit organ proposal",
            supplied_kind=proposal["kind"],
        )

    package, package_issue = _public_candidate_package(proposal)
    if package is None:
        return _hold(
            base,
            "HOLD_CANDIDATE_ORGAN_PACKAGE_INVALID",
            "DETERMINISTIC_PACKAGE_CONTRACT_HOLD",
            "the supplied organ source failed exact package validation before detached materialization",
            package_issue=package_issue,
        )

    alignment = _contract_alignment(proposal, package)
    if not alignment["passed"]:
        return _hold(
            base,
            "HOLD_ORGAN_PROPOSAL_CONTRACT_MISMATCH",
            "DETERMINISTIC_CONTRACT_ALIGNMENT_HOLD",
            "the Forge unit contract and executable-organ package interface declarations must agree exactly",
            candidate_package=package,
            contract_alignment=alignment,
        )

    missing_interfaces = set(initial["missing_interfaces"])
    addressed_interfaces = sorted(missing_interfaces & set(package["provides"]))
    if not addressed_interfaces:
        return _hold(
            base,
            "HOLD_ORGAN_PROPOSAL_NOT_LINKED_TO_GAP",
            "DETERMINISTIC_GAP_LINK_HOLD",
            "the candidate package does not provide any interface named by the observed missing-interface contracts",
            candidate_package=package,
            contract_alignment=alignment,
            observed_missing_interfaces=sorted(missing_interfaces),
        )

    installed_refs = set(ExecutableOrganLibrary(root).summary()["package_refs"])
    candidate_ref = package["ref"]
    if candidate_ref in installed_refs:
        return _hold(
            base,
            "HOLD_CANDIDATE_ORGAN_REF_COLLISION",
            "DETERMINISTIC_IDENTITY_COLLISION_HOLD",
            "the detached candidate may not shadow an installed exact package ref",
            candidate_ref=candidate_ref,
        )

    try:
        spawned = spawn_unit(target, proposal, replace=replace)
        tested = test_spawned_unit(root, target)
    except (ProjectError, SpawnError) as exc:
        raise OrganGapError(str(exc), getattr(exc, "details", {})) from exc
    experiment_base = {
        **base,
        "candidate_ref": candidate_ref,
        "candidate_package": package,
        "candidate_package_digest": _sha256_text(proposal["files"][proposal["implementation"]["entrypoint"]]),
        "addressed_missing_interfaces": addressed_interfaces,
        "contract_alignment": alignment,
        "spawn": spawned,
        "candidate_test": tested,
        "candidate_target_created": True,
        "candidate_still_detached": True,
    }
    if not tested["passed"]:
        return _hold(
            experiment_base,
            "HOLD_CANDIDATE_ORGAN_TEST_FAILED",
            "OBSERVED_DETACHED_CANDIDATE_TEST_HOLD",
            "the detached organ candidate did not pass its Forge integrity and package tests",
        )

    entrypoint = target.joinpath(*PurePosixPath(proposal["implementation"]["entrypoint"]).parts)
    candidate_digest = experiment_base["candidate_package_digest"]
    with tempfile.TemporaryDirectory(prefix="axm-organ-gap-overlay-") as overlay_dir:
        overlay_root = Path(overlay_dir)
        try:
            sources = _overlay_sources(root, overlay_root, entrypoint, candidate_digest)
        except CandidateSourceDriftError as exc:
            return _hold(
                experiment_base,
                "HOLD_CANDIDATE_ORGAN_SOURCE_DRIFT",
                "OBSERVED_DETACHED_CANDIDATE_SOURCE_DRIFT_HOLD",
                "the candidate entrypoint bytes no longer match the source that passed the detached Forge test",
                source_drift={"message": str(exc), "details": copy.deepcopy(exc.details)},
            )
        overlay_library = ExecutableOrganLibrary(overlay_root)
        final_discovery = discover_interface_assembly(overlay_root, raw_goal)
        overlay_receipt = {
            "truth_status": "EPHEMERAL_EXACT_ORGAN_LIBRARY_OVERLAY",
            "source_files": sources,
            "package_refs": overlay_library.summary()["package_refs"],
            "candidate_ref": candidate_ref,
            "candidate_present_only_for_experiment": True,
            "live_library_modified": False,
            "overlay_disposed_after_experiment": True,
        }
        if final_discovery["status"] != "READY_EXACT_INTERFACE_ASSEMBLY":
            return _hold(
                experiment_base,
                "HOLD_CANDIDATE_ORGAN_CLOSURE_INCOMPLETE",
                "OBSERVED_EPHEMERAL_CLOSURE_HOLD",
                "the tested detached candidate was made visible in an ephemeral exact library, but the original goal still did not resolve READY",
                overlay=overlay_receipt,
                closure_discovery=final_discovery,
            )
        selected_refs = final_discovery["selected_candidate"]["package_refs"]
        if candidate_ref not in selected_refs:
            return _hold(
                experiment_base,
                "HOLD_CANDIDATE_ORGAN_NOT_SELECTED",
                "OBSERVED_EPHEMERAL_SELECTION_HOLD",
                "the original goal became READY without selecting the supplied detached candidate, so this experiment did not prove that candidate closed the gap",
                overlay=overlay_receipt,
                closure_discovery=final_discovery,
            )
        try:
            resolved, resolution = resolve_organ_assembly(overlay_root, final_discovery["assembly"])
            closure_target = overlay_root / "ephemeral-closure-project"
            build = assemble_organ_project(
                target=closure_target,
                assembly=resolved,
                variables=final_discovery["variables"],
                checks=checks,
                replace=False,
                publish_mode="validated",
            )
        except (ProjectError, ExecutableOrganError) as exc:
            return _hold(
                experiment_base,
                "HOLD_CANDIDATE_ORGAN_CLOSURE_BUILD_FAILED",
                "OBSERVED_EPHEMERAL_BUILD_HOLD",
                "the candidate completed exact interface discovery but the ephemeral full assembly did not pass validated publication",
                overlay=overlay_receipt,
                closure_discovery=final_discovery,
                closure_build_error={"message": str(exc), "details": copy.deepcopy(exc.details)},
            )

    return {
        **experiment_base,
        "status": "TESTED_DETACHED_ORGAN_CLOSES_INTERFACE_GAP",
        "truth_status": "OBSERVED_EPHEMERAL_EXACT_ORGAN_CLOSURE_BUILD",
        "passed": True,
        "hold_reason": None,
        "overlay": overlay_receipt,
        "closure_discovery": final_discovery,
        "closure_resolution": resolution,
        "closure_build": _disposed_build_receipt(build),
        "original_goal_became_ready": True,
        "candidate_selected_in_closure": True,
        "candidate_installed": False,
        "candidate_admission_requested": False,
        "next_decision": "inspect the detached evidence and separately choose whether to request admission review; this experiment does not install the organ",
        "limitations": [
            "the closure build proves one exact request-shaped structural assembly and validation receipt",
            "declared interface names and a passing rendered build do not prove source-level semantic conformance or runtime behavior",
            "the candidate exists only in its detached Forge package; the live executable-organ library remains unchanged",
        ],
    }


def organ_gap_summary() -> dict[str, Any]:
    return {
        "schema": ORGAN_GAP_EXPERIMENT_SCHEMA,
        "operation": "explore-missing-organ-closure",
        "starts_from_typed_missing_interface_hold": True,
        "requires_explicit_supplied_organ_proposal": True,
        "forge_materialization_and_test_reused": True,
        "ephemeral_candidate_library_overlay": True,
        "full_ephemeral_closure_build": True,
        "automatic_source_invention": False,
        "automatic_install_or_admission": False,
        "runtime_behavior_proven": False,
    }

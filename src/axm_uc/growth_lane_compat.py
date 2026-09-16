from __future__ import annotations

from pathlib import Path
from typing import Any


def _install_project_checks() -> None:
    from . import project

    media_signatures = {
        "gif": lambda content: content.startswith((b"GIF87a", b"GIF89a")),
        "glb": lambda content: content.startswith(b"glTF"),
        "jpeg": lambda content: content.startswith(b"\xff\xd8\xff"),
        "ogg": lambda content: content.startswith(b"OggS"),
        "pdf": lambda content: content.startswith(b"%PDF-"),
        "png": lambda content: content.startswith(b"\x89PNG\r\n\x1a\n"),
        "wav": lambda content: len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WAVE",
        "webp": lambda content: len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP",
        "zip": lambda content: content.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")),
    }

    def media_signature(root: Path, check: dict[str, Any]) -> dict[str, Any]:
        relative = str(check.get("path", ""))
        expected = str(check.get("format", "")).strip().casefold()
        if expected not in media_signatures:
            return {
                "type": "media-signature",
                "path": relative,
                "format": expected,
                "passed": False,
                "error": "format must be one of: " + ", ".join(sorted(media_signatures)),
            }
        try:
            content = project._resolve_inside(root, relative).read_bytes()
        except (project.ProjectError, OSError) as exc:
            return {
                "type": "media-signature",
                "path": relative,
                "format": expected,
                "passed": False,
                "error": str(exc),
            }
        return {
            "type": "media-signature",
            "path": relative,
            "format": expected,
            "passed": bool(media_signatures[expected](content)),
            "bytes": len(content),
            "proof_scope": "container/file signature only; content decoding and semantic quality are not proven",
        }

    def utf8_valid(root: Path, check: dict[str, Any]) -> dict[str, Any]:
        relative = str(check.get("path", ""))
        try:
            content = project._resolve_inside(root, relative).read_bytes()
            content.decode("utf-8", errors="strict")
        except (project.ProjectError, OSError, UnicodeError) as exc:
            return {"type": "utf8-valid", "path": relative, "passed": False, "error": str(exc)}
        return {"type": "utf8-valid", "path": relative, "passed": True, "bytes": len(content)}

    # Do not overwrite a future native implementation.
    project.CHECKS.setdefault("media-signature", media_signature)
    project.CHECKS.setdefault("utf8-valid", utf8_valid)


def _provider_bridge_request(request: dict[str, Any], missing: list[str]) -> dict[str, Any] | None:
    kind = str(request.get("kind", ""))
    inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
    if missing != ["files"] or kind not in {
        "software-project",
        "static-web-project",
        "python-project",
        "verified-software-project",
        "verified-static-web-project",
        "verified-python-project",
    }:
        return None
    path = inputs.get("path")
    if not isinstance(path, str) or not path.strip():
        return None
    if "static-web" in kind:
        project_type = "static-web"
    elif "python" in kind:
        project_type = "python"
    else:
        project_type = str(inputs.get("project_type", "generic"))
    provider_inputs: dict[str, Any] = {
        "operation": "create",
        "goal": request.get("direction") or request.get("purpose") or kind,
        "path": path,
        "project_type": project_type,
        "constraints": request.get("constraints", {}),
        "context": {
            "original_request_kind": kind,
            "software_directions": request.get("software_directions", {}),
        },
        "publish_mode": inputs.get("publish_mode", "validated"),
        "replace": inputs.get("replace", False),
    }
    if isinstance(inputs.get("checks"), list):
        provider_inputs["checks"] = inputs["checks"]
    return {"kind": "provider-backed-project", "inputs": provider_inputs}


def _install_machine_creation_contract() -> None:
    from .capabilities import CapabilityError
    from .machine import UniversalCreationMachine

    if getattr(UniversalCreationMachine, "_growth_lane_compat_installed", False):
        return

    original_create = UniversalCreationMachine.create

    def capability_input_gap(self, request: dict[str, Any], manifest: dict[str, Any], missing: list[str]) -> dict[str, Any]:
        bridge = _provider_bridge_request(request, missing)
        inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
        return {
            "type": "CAPABILITY_INPUT_GAP",
            "truth_status": "ROUTE_PRESENT_REQUIRED_INPUTS_MISSING",
            "request_kind": request.get("kind"),
            "directional_outcome": request.get("direction") or request.get("purpose") or request.get("kind"),
            "route": manifest.get("id"),
            "required_inputs": self.capabilities.required_inputs(manifest, inputs),
            "supplied_inputs": sorted(inputs),
            "missing_required_inputs": missing,
            "decomposition": self.plan(request, per_level=4),
            "local_provider_bridge": (
                {
                    "status": "READY_FOR_EXPLICIT_LOCAL_PROVIDER_SELECTION",
                    "request": bridge,
                    "next_action": "add an explicit provider object with allow_call=true, or invoke the provider-backed-project route separately",
                    "automatic_call_made": False,
                }
                if bridge is not None
                else {
                    "status": "NO_CURRENT_PROVIDER_BRIDGE_FOR_INPUT_SHAPE",
                    "automatic_call_made": False,
                }
            ),
        }

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be an object")
        kind = request.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("request.kind must be a non-empty string")
        manifest = self.capabilities.route(kind)
        if manifest is None:
            return original_create(self, request)
        inputs = request.get("inputs", {})
        if not isinstance(inputs, dict):
            return {
                "type": "CREATION_ERROR",
                "capability": manifest.get("id"),
                "message": "request.inputs must be an object",
            }
        missing = self.capabilities.missing_required_inputs(manifest, inputs)
        if missing:
            provider = request.get("provider")
            bridge = _provider_bridge_request(request, missing)
            if isinstance(provider, dict) and bridge is not None:
                bridge["inputs"]["provider"] = provider
                provider_manifest = self.capabilities.route("provider-backed-project")
                if provider_manifest is None:
                    return {
                        "type": "CAPABILITY_GAP",
                        "truth_status": "LOCAL_PROVIDER_BRIDGE_NOT_LIVE",
                        "request_kind": request.get("kind"),
                        "directional_outcome": request.get("direction") or request.get("purpose") or request.get("kind"),
                    }
                try:
                    result = self.capabilities.invoke(provider_manifest, bridge["inputs"])
                except CapabilityError as exc:
                    error = {
                        "type": "CREATION_ERROR",
                        "capability": provider_manifest.get("id"),
                        "message": str(exc),
                    }
                    if exc.details:
                        error["details"] = exc.details
                    return error
                return {
                    "type": "CREATION_RESULT",
                    "capability": provider_manifest.get("id"),
                    "directional_outcome": request.get("direction") or request.get("purpose") or request.get("kind"),
                    "filled_missing_inputs": missing,
                    "original_route": manifest.get("id"),
                    "result": result,
                }
            return capability_input_gap(self, request, manifest, missing)
        return original_create(self, request)

    def trial(self, request: dict[str, Any], per_level: int = 6) -> dict[str, Any]:
        plan = self.plan(request, per_level=per_level)
        creation = self.create(request)
        verification: dict[str, Any] | None = None
        passed = False

        if creation.get("type") == "CREATION_RESULT":
            result = creation.get("result") if isinstance(creation.get("result"), dict) else {}
            project_path = result.get("path")
            inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
            provider_creation = result.get("creation") if isinstance(result.get("creation"), dict) else {}
            observed_validation = (
                result.get("validation")
                if isinstance(result.get("validation"), dict)
                else provider_creation.get("validation")
            )
            if project_path and isinstance(observed_validation, dict):
                created_files = (
                    result.get("files")
                    if isinstance(result.get("files"), list)
                    else provider_creation.get("files")
                    if isinstance(provider_creation.get("files"), list)
                    else []
                )
                expected_file_digests = {
                    str(row["path"]): str(row["sha256"])
                    for row in created_files
                    if isinstance(row, dict) and "path" in row and "sha256" in row
                }
                provider_receipt = result.get("provider_receipt") if isinstance(result.get("provider_receipt"), dict) else {}
                provider_proposal = provider_receipt.get("proposal") if isinstance(provider_receipt.get("proposal"), dict) else {}
                expected_files = (
                    inputs.get("files")
                    if isinstance(inputs.get("files"), dict)
                    else provider_proposal.get("files")
                    if isinstance(provider_proposal.get("files"), dict)
                    else None
                )
                verification = self.create({
                    "kind": "verify-project",
                    "direction": f"verify creation trial for {request.get('kind')}",
                    "inputs": {
                        "path": project_path,
                        "project_type": inputs.get(
                            "project_type",
                            result.get("project_type", provider_creation.get("project_type", "generic")),
                        ),
                        "checks": inputs.get("checks", []),
                        "expected_files": expected_files,
                        "expected_file_digests": expected_file_digests,
                    },
                })
                passed = (
                    verification.get("type") == "CREATION_RESULT"
                    and isinstance(verification.get("result"), dict)
                    and verification["result"].get("passed") is True
                )

        return {
            "type": "CREATION_TRIAL",
            "passed": passed,
            "truth_status": "OBSERVED_DETERMINISTIC_PROJECT_VALIDATION",
            "plan": plan,
            "creation": creation,
            "verification": verification,
            "limitations": [
                "generated code was not executed by this trial",
                "browser visuals and interactive behavior still require a browser/user/authorized host test",
            ],
        }

    UniversalCreationMachine.create = create
    UniversalCreationMachine.trial = trial
    UniversalCreationMachine._growth_lane_compat_installed = True


def _install_aftertouch_preview_contract() -> None:
    from . import capabilities
    from .aftertouch_preview import (
        AftertouchPreviewError,
        bind_advance_preview,
        bind_prepare_preview,
        operate_aftertouch_preview,
        preflight_preview_advance,
    )

    original = capabilities.BUILTINS.get("builtin:evolution_aftertouch")
    if original is None or getattr(original, "_aftertouch_preview_wrapped", False):
        return

    preview_operations = {
        "inspect-preview",
        "preview-summary",
        "inspect-preview-policy",
        "capture-preview",
        "preview-candidate",
        "capture-intermediate-preview",
        "record-preview-feedback",
        "review-preview",
        "record-user-preview",
    }
    prepare_operations = {"prepare", "start", "prepare-chamber"}
    advance_operations = {"advance", "advance-round", "judge-round"}

    def preview_aware_aftertouch(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        operation = str(inputs.get("operation", "prepare")).strip().casefold()
        try:
            if operation in preview_operations:
                return operate_aftertouch_preview(root, inputs)
            preflight_preview_advance(inputs)
            result = original(root, inputs)
            if operation in prepare_operations:
                return bind_prepare_preview(inputs, result)
            if operation in advance_operations:
                return bind_advance_preview(root, inputs, result)
            return result
        except AftertouchPreviewError as exc:
            raise capabilities.CapabilityError(str(exc), exc.details) from exc

    preview_aware_aftertouch._aftertouch_preview_wrapped = True
    capabilities.BUILTINS["builtin:evolution_aftertouch"] = preview_aware_aftertouch
    capabilities.BUILTINS.setdefault("builtin:aftertouch_preview", operate_aftertouch_preview)


def _install_precision_cutter_v06() -> None:
    """Layer only the v0.6 sweep schema over the already-registered cutter builtin."""
    from . import capabilities
    from .mesh_general_hole_chain import GENERAL_HOLE_CHAIN_SCHEMA, publish_general_hole_chain
    from .mesh_precision_cutter import MeshPrecisionCutterError

    original = capabilities.BUILTINS.get("builtin:precision_cutter")
    if original is None or getattr(original, "_v06_hole_sweep_wrapped", False):
        return

    def v06_aware_precision_cutter(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        specification = inputs.get("specification")
        schema = specification.get("schema") if isinstance(specification, dict) else None
        if schema != GENERAL_HOLE_CHAIN_SCHEMA:
            return original(root, inputs)
        if "source_path" not in inputs or "path" not in inputs:
            return original(root, inputs)
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool):
            raise capabilities.CapabilityError("precision cutter replace must be a boolean")
        source = capabilities._resolve_output_path(root, str(inputs["source_path"]))
        target = capabilities._resolve_output_path(root, str(inputs["path"]))
        if capabilities._is_machine_body_path(root, source):
            raise capabilities.CapabilityError(
                "v0.6 hole sweep cannot read the protected live machine body as source material"
            )
        if capabilities._is_machine_body_path(root, target):
            raise capabilities.CapabilityError(
                "v0.6 hole sweep cannot rewrite the protected live machine body"
            )
        lineage = None
        if "lineage_path" in inputs:
            lineage = capabilities._resolve_output_path(root, str(inputs["lineage_path"]))
            if capabilities._is_machine_body_path(root, lineage):
                raise capabilities.CapabilityError(
                    "v0.6 hole-sweep lineage must stay on an ordinary creation surface"
                )
        if "receipt_path" in inputs:
            receipt = capabilities._resolve_output_path(root, str(inputs["receipt_path"]))
        else:
            receipt = target.with_suffix(target.suffix + ".hole-sweep.json")
        if capabilities._is_machine_body_path(root, receipt):
            raise capabilities.CapabilityError(
                "v0.6 hole-sweep receipt cannot rewrite the live machine body"
            )
        try:
            return publish_general_hole_chain(
                source,
                target,
                specification,
                lineage_path=lineage,
                receipt_path=receipt,
                expected_source_sha256=inputs.get("expected_source_sha256"),
                expected_lineage_sha256=inputs.get("expected_lineage_sha256"),
                replace=replace,
            )
        except MeshPrecisionCutterError as exc:
            raise capabilities.CapabilityError(str(exc), exc.details) from exc

    v06_aware_precision_cutter._v06_hole_sweep_wrapped = True
    capabilities.BUILTINS["builtin:precision_cutter"] = v06_aware_precision_cutter


def _install_precision_cutter_v07() -> None:
    """Layer only the v0.7 mixed same-axis schema over the v0.6-aware cutter."""
    from . import capabilities
    from .mesh_mixed_fabrication import MIXED_FABRICATION_SCHEMA, publish_mixed_fabrication
    from .mesh_precision_cutter import MeshPrecisionCutterError

    original = capabilities.BUILTINS.get("builtin:precision_cutter")
    if original is None or getattr(original, "_v07_mixed_fabrication_wrapped", False):
        return

    def v07_aware_precision_cutter(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
        specification = inputs.get("specification")
        schema = specification.get("schema") if isinstance(specification, dict) else None
        if schema != MIXED_FABRICATION_SCHEMA:
            return original(root, inputs)
        if "source_path" not in inputs or "path" not in inputs:
            return original(root, inputs)
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool):
            raise capabilities.CapabilityError("precision cutter replace must be a boolean")
        source = capabilities._resolve_output_path(root, str(inputs["source_path"]))
        target = capabilities._resolve_output_path(root, str(inputs["path"]))
        if capabilities._is_machine_body_path(root, source):
            raise capabilities.CapabilityError(
                "v0.7 mixed fabrication cannot read the protected live machine body as source material"
            )
        if capabilities._is_machine_body_path(root, target):
            raise capabilities.CapabilityError(
                "v0.7 mixed fabrication cannot rewrite the protected live machine body"
            )
        lineage = None
        if "lineage_path" in inputs:
            lineage = capabilities._resolve_output_path(root, str(inputs["lineage_path"]))
            if capabilities._is_machine_body_path(root, lineage):
                raise capabilities.CapabilityError(
                    "v0.7 mixed lineage must stay on an ordinary creation surface"
                )
        if "receipt_path" in inputs:
            receipt = capabilities._resolve_output_path(root, str(inputs["receipt_path"]))
        else:
            receipt = target.with_suffix(target.suffix + ".mixed-fabrication.json")
        if capabilities._is_machine_body_path(root, receipt):
            raise capabilities.CapabilityError(
                "v0.7 mixed fabrication receipt cannot rewrite the live machine body"
            )
        try:
            return publish_mixed_fabrication(
                source,
                target,
                specification,
                lineage_path=lineage,
                receipt_path=receipt,
                expected_source_sha256=inputs.get("expected_source_sha256"),
                expected_lineage_sha256=inputs.get("expected_lineage_sha256"),
                replace=replace,
            )
        except MeshPrecisionCutterError as exc:
            raise capabilities.CapabilityError(str(exc), exc.details) from exc

    v07_aware_precision_cutter._v07_mixed_fabrication_wrapped = True
    capabilities.BUILTINS["builtin:precision_cutter"] = v07_aware_precision_cutter


def install_growth_lane_compatibility() -> None:
    """Install only the framework seams required by recovered growth-lane capabilities.

    The compatibility layer does not change candidate adoption, snapshot/recovery,
    root governance, CANON authority, or provider consent rules.
    """
    _install_project_checks()
    _install_machine_creation_contract()
    _install_aftertouch_preview_contract()
    _install_precision_cutter_v06()
    _install_precision_cutter_v07()

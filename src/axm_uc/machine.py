from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .candidate import test_capability_candidate
from .capabilities import CapabilityError, CapabilityStore
from .decompose import CreationDecomposer
from .directions import SoftwareDirections
from .executable import ExecutableAnatomy
from .gap_synthesis import analyze_creation_gap, gap_synthesis_summary
from .host_evidence import host_evidence_summary
from .local_provider import provider_summary
from .organ_library import ExecutableOrganLibrary
from .organ_discovery import organ_discovery_summary
from .organ_gap import organ_gap_summary
from .registry import Registry
from .spawn import creation_forge_summary


class UniversalCreationMachine:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.registry = Registry(self.root)
        self.capabilities = CapabilityStore(self.root)
        self.decomposer = CreationDecomposer(self.registry, self.capabilities)
        self.executable_anatomy = ExecutableAnatomy(self.registry, self.capabilities, self.decomposer.topology)
        self.direction_model = SoftwareDirections(self.root)

    def inspect(self, query: str = "", level: str | None = None, limit: int = 20) -> dict[str, Any]:
        from .evolution import evolution_summary

        contract = json.loads((self.root / "machine.contract.json").read_text(encoding="utf-8"))
        return {
            "machine": contract,
            "registry": self.registry.summary(),
            "topology": self.decomposer.topology.summary(),
            "executable_anatomy": self.executable_anatomy.summary(),
            "software_directions": self.direction_model.summary(),
            "executable_organs": ExecutableOrganLibrary(self.root).summary(),
            "organ_discovery": organ_discovery_summary(),
            "organ_gap_closure": organ_gap_summary(),
            "creation_forge": creation_forge_summary(),
            "gap_synthesis": gap_synthesis_summary(),
            "local_creation_provider": provider_summary(),
            "host_evidence": host_evidence_summary(),
            "self_evolution": evolution_summary(),
            "live_capabilities": self.capabilities.live(),
            "records": self.registry.search(query=query, level=level, limit=limit) if (query or level) else [],
        }

    def creation_forge(self) -> dict[str, Any]:
        return {"type": "CREATION_UNIT_FORGE", **creation_forge_summary()}

    def gap_forge(self) -> dict[str, Any]:
        return {"type": "CREATION_GAP_SYNTHESIS", **gap_synthesis_summary()}

    def software_directions(self, direction_id: str | None = None, suggest: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "SOFTWARE_DIRECTIONS",
            "summary": self.direction_model.summary(),
        }
        if direction_id:
            profile = self.direction_model.profile(direction_id)
            if profile is None:
                raise KeyError(f"unknown software direction: {direction_id}")
            result["profile"] = profile
        if suggest:
            result["suggestions"] = self.direction_model.suggest({"goals": [suggest]})
        return result

    def executable_organs(
        self,
        ref: str | None = None,
        project_type: str | None = None,
        provides: str | None = None,
    ) -> dict[str, Any]:
        library = ExecutableOrganLibrary(self.root)
        result: dict[str, Any] = {
            "type": "EXECUTABLE_ORGAN_LIBRARY",
            "summary": library.summary(),
        }
        if ref:
            result["package"] = library.inspect(ref)
        else:
            result["packages"] = library.list(project_type=project_type, provides=provides)
        return result

    def topology(self, master_id: str | None = None, core_id: str | None = None, depth: int = 6) -> dict[str, Any]:
        bridge = self.decomposer.topology
        result: dict[str, Any] = {"type": "ANATOMY_KERNEL_TOPOLOGY", "summary": bridge.summary()}
        if master_id:
            mapping = bridge.mapping_for_master(master_id)
            result["master_mapping"] = mapping
            if mapping.get("traversable") is True:
                result["traversal"] = bridge.traverse_core([str(mapping["core_id"])], max_depth=depth)
        if core_id:
            core = bridge.core_index.get(str(core_id))
            if core is None:
                raise KeyError(f"unknown core record: {core_id}")
            result["core_record"] = core
            result["core_master_matches"] = bridge.master_matches_for_core(str(core_id))
            result["traversal"] = bridge.traverse_core([str(core_id)], max_depth=depth)
        return result

    def executable(self, master_id: str | None = None, core_id: str | None = None) -> dict[str, Any]:
        result: dict[str, Any] = {
            "type": "EXECUTABLE_ANATOMY",
            "summary": self.executable_anatomy.summary(),
        }
        if master_id:
            result["master"] = self.executable_anatomy.for_master(master_id)
        if core_id:
            result["core"] = self.executable_anatomy.for_core(core_id)
        return result

    def plan(self, request: dict[str, Any], per_level: int = 6) -> dict[str, Any]:
        """Map a request onto software direction, anatomy, topology, and live coverage.

        Direction suggestions never select themselves. Only an explicit
        ``software_directions`` selection enriches anatomy matching.
        """
        direction_analysis = self.direction_model.analyze_request(request)
        explicit_context = self.direction_model.planning_context(direction_analysis["stack"])
        result = self.decomposer.decompose(request, per_level=per_level, extra_context=explicit_context)
        result["software_direction"] = direction_analysis
        result["executable_anatomy"] = self.executable_anatomy.for_selected(result["registry_matches"])
        return result

    def _capability_gap(self, request: dict[str, Any]) -> dict[str, Any]:
        kind = str(request.get("kind", "unknown"))
        inputs = request.get("inputs") if isinstance(request.get("inputs"), dict) else {}
        input_keys = set(inputs)
        partial: list[dict[str, Any]] = []
        for capability in self.capabilities.live():
            required = set(capability.get("input_contract", {}).get("required", []))
            if required and required.issubset(input_keys):
                partial.append({
                    "id": capability.get("id"),
                    "purpose": capability.get("purpose"),
                    "handles": capability.get("handles", []),
                    "covered_inputs": sorted(required),
                })
        if partial:
            smallest = "a routing/adapter or composite capability may be enough because existing live machinery already accepts the required input shape"
        else:
            smallest = f"a live capability able to reach creation kind '{kind}' from the supplied inputs"
        return {
            "type": "CAPABILITY_GAP",
            "truth_status": "HYPOTHESIS",
            "request_kind": kind,
            "directional_outcome": request.get("direction") or request.get("purpose") or kind,
            "constraints": request.get("constraints", {}),
            "existing_partial_coverage": partial,
            "smallest_missing_capability_currently_justified": smallest,
            "supported_creation_kinds": sorted({h for c in self.capabilities.live() for h in c.get("handles", [])}),
            "decomposition": self.plan(request, per_level=4),
            "gap_synthesis": analyze_creation_gap(self.root, request),
        }

    @staticmethod
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

    def _capability_input_gap(
        self,
        request: dict[str, Any],
        manifest: dict[str, Any],
        missing: list[str],
    ) -> dict[str, Any]:
        bridge = self._provider_bridge_request(request, missing)
        return {
            "type": "CAPABILITY_INPUT_GAP",
            "truth_status": "ROUTE_PRESENT_REQUIRED_INPUTS_MISSING",
            "request_kind": request.get("kind"),
            "directional_outcome": request.get("direction") or request.get("purpose") or request.get("kind"),
            "route": manifest.get("id"),
            "required_inputs": self.capabilities.required_inputs(
                manifest,
                request.get("inputs") if isinstance(request.get("inputs"), dict) else {},
            ),
            "supplied_inputs": sorted((request.get("inputs") or {}).keys()),
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

    def _try_explicit_provider_bridge(
        self,
        request: dict[str, Any],
        missing: list[str],
    ) -> dict[str, Any] | None:
        provider = request.get("provider")
        bridge = self._provider_bridge_request(request, missing)
        if not isinstance(provider, dict) or bridge is None:
            return None
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
            "original_route": (
                original.get("id")
                if (original := self.capabilities.route(str(request.get("kind", "")))) is not None
                else None
            ),
            "result": result,
        }

    def create(self, request: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(request, dict):
            raise TypeError("request must be an object")
        kind = request.get("kind")
        if not isinstance(kind, str) or not kind.strip():
            raise ValueError("request.kind must be a non-empty string")
        manifest = self.capabilities.route(kind)
        if manifest is None:
            return self._capability_gap(request)
        inputs = request.get("inputs", {})
        if not isinstance(inputs, dict):
            return {
                "type": "CREATION_ERROR",
                "capability": manifest.get("id"),
                "message": "request.inputs must be an object",
            }
        missing = self.capabilities.missing_required_inputs(manifest, inputs)
        if missing:
            bridged = self._try_explicit_provider_bridge(request, missing)
            if bridged is not None:
                return bridged
            return self._capability_input_gap(request, manifest, missing)
        try:
            result = self.capabilities.invoke(manifest, inputs)
        except CapabilityError as exc:
            error = {
                "type": "CREATION_ERROR",
                "capability": manifest.get("id"),
                "message": str(exc),
            }
            if exc.details:
                error["details"] = exc.details
            return error
        return {
            "type": "CREATION_RESULT",
            "capability": manifest.get("id"),
            "directional_outcome": request.get("direction") or request.get("purpose") or kind,
            "result": result,
        }

    def trial(self, request: dict[str, Any], per_level: int = 6) -> dict[str, Any]:
        """Plan, create, then independently re-verify a project-style creation."""
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
                provider_receipt = (
                    result.get("provider_receipt")
                    if isinstance(result.get("provider_receipt"), dict)
                    else {}
                )
                provider_proposal = (
                    provider_receipt.get("proposal")
                    if isinstance(provider_receipt.get("proposal"), dict)
                    else {}
                )
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

    def test_candidate(self, candidate_path: Path) -> dict[str, Any]:
        return test_capability_candidate(self.root, candidate_path)

    def adopt_candidate(self, candidate_path: Path, root_fit: Any = None) -> dict[str, Any]:
        from .evolution import ensure_daily_recovery_snapshot
        from .root_fit import evaluate_root_fit_decision

        candidate_path = Path(candidate_path).resolve()
        adoption_fit = evaluate_root_fit_decision(root_fit)
        if adoption_fit.get("fit") is not True:
            return {
                "adopted": False,
                "truth_status": "HOLD_CURRENT_ROOT_FIT_DECISION",
                "root_fit_decision": adoption_fit,
                "live_machine_body_modified": False,
            }
        test = self.test_candidate(candidate_path)
        if not test.get("passed"):
            return {"adopted": False, "test": test}
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        target = self.root / "capabilities/live" / f"{candidate['id']}.json"
        if target.exists():
            return {
                "adopted": False,
                "truth_status": "HOLD_LIVE_CAPABILITY_ID_COLLISION",
                "capability": candidate.get("id"),
                "manifest": str(target.relative_to(self.root)),
                "test": test,
            }
        recovery = ensure_daily_recovery_snapshot(self.root)
        candidate["status"] = "live"
        atomic_write_json(target, candidate)
        candidates_dir = (self.root / "capabilities/candidates").resolve()
        try:
            candidate_path.relative_to(candidates_dir)
        except ValueError:
            pass
        else:
            candidate_path.unlink()
        self.executable_anatomy = ExecutableAnatomy(self.registry, self.capabilities, self.decomposer.topology)
        return {
            "adopted": True,
            "truth_status": "ADOPTED_LIVE_CAPABILITY_WITH_DAILY_RECOVERY",
            "capability": candidate["id"],
            "manifest": str(target.relative_to(self.root)),
            "recovery_snapshot": recovery,
            "adoption_root_fit": adoption_fit,
            "transition": {
                "installed": True,
                "registered": True,
                "routed": True,
            },
            "test": test,
        }

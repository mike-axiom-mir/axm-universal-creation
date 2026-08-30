from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .capabilities import CapabilityError, CapabilityStore
from .decompose import CreationDecomposer
from .executable import ExecutableAnatomy
from .registry import Registry
from .root_fit import evaluate_declared_root_fit


def _expand_test_value(value: Any, test_dir: str) -> Any:
    if isinstance(value, str):
        return value.replace("${TEST_DIR}", test_dir)
    if isinstance(value, dict):
        expanded: dict[Any, Any] = {}
        for key, item in value.items():
            expanded_key = key.replace("${TEST_DIR}", test_dir) if isinstance(key, str) else key
            expanded[expanded_key] = _expand_test_value(item, test_dir)
        return expanded
    if isinstance(value, list):
        return [_expand_test_value(item, test_dir) for item in value]
    return copy.deepcopy(value)


def _result_field(result: Any, path: str) -> Any:
    value = result
    for part in str(path).split("."):
        if not isinstance(value, dict) or part not in value:
            raise KeyError(path)
        value = value[part]
    return value


class UniversalCreationMachine:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.registry = Registry(self.root)
        self.capabilities = CapabilityStore(self.root)
        self.decomposer = CreationDecomposer(self.registry, self.capabilities)
        self.executable_anatomy = ExecutableAnatomy(self.registry, self.capabilities, self.decomposer.topology)

    def inspect(self, query: str = "", level: str | None = None, limit: int = 20) -> dict[str, Any]:
        contract = json.loads((self.root / "machine.contract.json").read_text(encoding="utf-8"))
        return {
            "machine": contract,
            "registry": self.registry.summary(),
            "topology": self.decomposer.topology.summary(),
            "executable_anatomy": self.executable_anatomy.summary(),
            "live_capabilities": self.capabilities.live(),
            "records": self.registry.search(query=query, level=level, limit=limit) if (query or level) else [],
        }

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
        """Map a creation request onto explicit anatomy, topology, and live coverage."""
        result = self.decomposer.decompose(request, per_level=per_level)
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
        try:
            result = self.capabilities.invoke(manifest, request.get("inputs", {}))
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
            if project_path and isinstance(result.get("validation"), dict):
                verification = self.create({
                    "kind": "verify-project",
                    "direction": f"verify creation trial for {request.get('kind')}",
                    "inputs": {
                        "path": project_path,
                        "project_type": inputs.get("project_type", result.get("project_type", "generic")),
                        "checks": inputs.get("checks", []),
                        "expected_files": inputs.get("files", {}),
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
        candidate_path = Path(candidate_path)
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        errors: list[str] = []
        required_fields = ("id", "purpose", "handles", "implementation", "input_contract", "tests", "root_fit")
        for field in required_fields:
            if field not in candidate:
                errors.append(f"missing field: {field}")
        root_fit = evaluate_declared_root_fit(candidate)
        if errors:
            return {"passed": False, "errors": errors, "root_fit": root_fit, "tests": []}

        build_root = self.root / ".axm-build" / f"candidate-{uuid.uuid4().hex}"
        build_root.mkdir(parents=True, exist_ok=False)
        test_results: list[dict[str, Any]] = []
        try:
            test_manifest = copy.deepcopy(candidate)
            test_manifest["status"] = "candidate-under-test"
            for index, test in enumerate(candidate.get("tests", []), start=1):
                inputs = _expand_test_value(test.get("inputs", {}), str(build_root))
                expected = _expand_test_value(test.get("expect", {}), str(build_root))
                try:
                    result = self.capabilities.invoke(test_manifest, inputs)
                    passed_test = True
                    detail: dict[str, Any] = {"result": result}
                    if "file_text" in expected:
                        output_path = Path(result["path"])
                        actual = output_path.read_text(encoding="utf-8")
                        match = actual == expected["file_text"]
                        passed_test = passed_test and match
                        detail["actual_file_text"] = actual
                    files_expected = expected.get("files")
                    if isinstance(files_expected, dict):
                        file_checks: list[dict[str, Any]] = []
                        for raw_path, expected_text in files_expected.items():
                            path = Path(str(raw_path))
                            try:
                                actual = path.read_text(encoding="utf-8")
                                match = actual == expected_text
                                file_checks.append({"path": str(path), "passed": match})
                            except Exception as exc:
                                match = False
                                file_checks.append({"path": str(path), "passed": False, "error": str(exc)})
                            passed_test = passed_test and match
                        detail["file_checks"] = file_checks
                    result_fields = expected.get("result_fields")
                    if isinstance(result_fields, dict):
                        field_checks: list[dict[str, Any]] = []
                        for field_path, expected_value in result_fields.items():
                            try:
                                actual_value = _result_field(result, str(field_path))
                                match = actual_value == expected_value
                                field_checks.append({"field": field_path, "passed": match, "actual": actual_value})
                            except KeyError:
                                match = False
                                field_checks.append({"field": field_path, "passed": False, "error": "field not found"})
                            passed_test = passed_test and match
                        detail["result_field_checks"] = field_checks
                    test_results.append({"index": index, "passed": passed_test, **detail})
                except Exception as exc:
                    test_results.append({"index": index, "passed": False, "error": str(exc)})
        finally:
            shutil.rmtree(self.root / ".axm-build", ignore_errors=True)

        passed = bool(test_results) and all(item.get("passed") for item in test_results) and root_fit.get("fit") is True
        return {
            "passed": passed,
            "candidate": candidate.get("id"),
            "tests": test_results,
            "root_fit": root_fit,
            "build_debris_cleaned": not (self.root / ".axm-build").exists(),
        }

    def adopt_candidate(self, candidate_path: Path) -> dict[str, Any]:
        candidate_path = Path(candidate_path).resolve()
        test = self.test_candidate(candidate_path)
        if not test.get("passed"):
            return {"adopted": False, "test": test}
        candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
        candidate["status"] = "live"
        target = self.root / "capabilities/live" / f"{candidate['id']}.json"
        atomic_write_json(target, candidate)
        candidates_dir = (self.root / "capabilities/candidates").resolve()
        try:
            candidate_path.relative_to(candidates_dir)
        except ValueError:
            pass
        else:
            candidate_path.unlink()
        return {
            "adopted": True,
            "capability": candidate["id"],
            "manifest": str(target.relative_to(self.root)),
            "test": test,
        }

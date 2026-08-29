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
from .registry import Registry
from .root_fit import evaluate_declared_root_fit


class UniversalCreationMachine:
    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.registry = Registry(self.root)
        self.capabilities = CapabilityStore(self.root)
        self.decomposer = CreationDecomposer(self.registry, self.capabilities)

    def inspect(self, query: str = "", level: str | None = None, limit: int = 20) -> dict[str, Any]:
        contract = json.loads((self.root / "machine.contract.json").read_text(encoding="utf-8"))
        return {
            "machine": contract,
            "registry": self.registry.summary(),
            "live_capabilities": self.capabilities.live(),
            "records": self.registry.search(query=query, level=level, limit=limit) if (query or level) else [],
        }

    def plan(self, request: dict[str, Any], per_level: int = 6) -> dict[str, Any]:
        """Map a creation request onto the explicit registry before inventing machinery."""
        return self.decomposer.decompose(request, per_level=per_level)

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
            smallest = "a routing/adapter capability may be enough because existing live machinery already accepts the required input shape"
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
            return {
                "type": "CREATION_ERROR",
                "capability": manifest.get("id"),
                "message": str(exc),
            }
        return {
            "type": "CREATION_RESULT",
            "capability": manifest.get("id"),
            "directional_outcome": request.get("direction") or request.get("purpose") or kind,
            "result": result,
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
                inputs = copy.deepcopy(test.get("inputs", {}))
                for key, value in list(inputs.items()):
                    if isinstance(value, str):
                        inputs[key] = value.replace("${TEST_DIR}", str(build_root))
                try:
                    result = self.capabilities.invoke(test_manifest, inputs)
                    expected = test.get("expect", {})
                    passed = True
                    detail: dict[str, Any] = {"result": result}
                    if "file_text" in expected:
                        output_path = Path(result["path"])
                        actual = output_path.read_text(encoding="utf-8")
                        passed = actual == expected["file_text"]
                        detail["actual_file_text"] = actual
                    test_results.append({"index": index, "passed": passed, **detail})
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

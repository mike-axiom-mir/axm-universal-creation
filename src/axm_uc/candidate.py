from __future__ import annotations

import copy
import json
import shutil
import uuid
from pathlib import Path
from typing import Any

from .capabilities import CapabilityStore
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


def _unsafe_test_paths(value: Any, location: str = "inputs") -> list[dict[str, str]]:
    unsafe: list[dict[str, str]] = []
    if isinstance(value, dict):
        for key, item in value.items():
            child = f"{location}.{key}"
            if str(key).casefold() == "path":
                if not isinstance(item, str) or not item.startswith("${TEST_DIR}/"):
                    unsafe.append({"field": child, "value": repr(item)})
            unsafe.extend(_unsafe_test_paths(item, child))
    elif isinstance(value, list):
        for index, item in enumerate(value):
            unsafe.extend(_unsafe_test_paths(item, f"{location}[{index}]"))
    return unsafe


def test_capability_candidate(root: Path, candidate_path: Path) -> dict[str, Any]:
    """Exercise one detached capability manifest against the current live dependencies.

    The candidate is invoked directly and never routed, installed, or registered.
    Its declared tests run in short-lived machine-owned build space.
    """
    root = Path(root).resolve()
    candidate_path = Path(candidate_path).resolve()
    candidate = json.loads(candidate_path.read_text(encoding="utf-8"))
    errors: list[str] = []
    required_fields = ("id", "purpose", "handles", "implementation", "input_contract", "tests", "root_fit")
    for field in required_fields:
        if field not in candidate:
            errors.append(f"missing field: {field}")
    if "handles" in candidate and (
        not isinstance(candidate["handles"], list)
        or not candidate["handles"]
        or any(not isinstance(item, str) or not item.strip() for item in candidate["handles"])
    ):
        errors.append("handles must be a non-empty list of non-empty text")
    if "implementation" in candidate and not isinstance(candidate["implementation"], dict):
        errors.append("implementation must be an object")
    if "input_contract" in candidate and not isinstance(candidate["input_contract"], dict):
        errors.append("input_contract must be an object")
    if "tests" in candidate and (
        not isinstance(candidate["tests"], list)
        or not candidate["tests"]
        or any(not isinstance(item, dict) for item in candidate["tests"])
    ):
        errors.append("tests must be a non-empty list of objects")
    if isinstance(candidate.get("tests"), list):
        unsafe_paths = [
            unsafe
            for test in candidate["tests"]
            if isinstance(test, dict)
            for unsafe in _unsafe_test_paths(test.get("inputs", {}))
        ]
        if unsafe_paths:
            errors.append("candidate test input paths must stay under ${TEST_DIR}/")
    root_fit = evaluate_declared_root_fit(candidate)
    if errors:
        result = {"passed": False, "errors": errors, "root_fit": root_fit, "tests": []}
        if "unsafe_paths" in locals() and unsafe_paths:
            result["unsafe_test_paths"] = unsafe_paths
        return result

    build_root = root / ".axm-build" / f"candidate-{uuid.uuid4().hex}"
    build_root.mkdir(parents=True, exist_ok=False)
    test_results: list[dict[str, Any]] = []
    capabilities = CapabilityStore(root)
    try:
        test_manifest = copy.deepcopy(candidate)
        test_manifest["status"] = "candidate-under-test"
        for index, test in enumerate(candidate.get("tests", []), start=1):
            try:
                inputs = _expand_test_value(test.get("inputs", {}), str(build_root))
                expected = _expand_test_value(test.get("expect", {}), str(build_root))
                if not isinstance(inputs, dict) or not isinstance(expected, dict):
                    raise TypeError("candidate test inputs and expect must be objects")
                result = capabilities.invoke(test_manifest, inputs)
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
        shutil.rmtree(root / ".axm-build", ignore_errors=True)

    passed = bool(test_results) and all(item.get("passed") for item in test_results) and root_fit.get("fit") is True
    return {
        "passed": passed,
        "candidate": candidate.get("id"),
        "tests": test_results,
        "root_fit": root_fit,
        "build_debris_cleaned": not (root / ".axm-build").exists(),
        "installed": False,
        "registered": False,
        "routed": False,
    }

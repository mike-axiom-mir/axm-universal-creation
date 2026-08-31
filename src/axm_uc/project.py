from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import uuid
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


PUBLISH_MODES = {"validated", "grounded-draft"}


class ProjectError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _safe_relative_path(raw: str) -> PurePosixPath:
    text = str(raw).replace("\\", "/").strip()
    if not text or text.endswith("/"):
        raise ProjectError(f"invalid project file path: {raw!r}")
    path = PurePosixPath(text)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ProjectError(f"project file path must stay inside the project: {raw!r}")
    return path


def _resolve_inside(root: Path, relative: str) -> Path:
    rel = _safe_relative_path(relative)
    target = root.joinpath(*rel.parts).resolve()
    try:
        target.relative_to(root.resolve())
    except ValueError as exc:
        raise ProjectError(f"project path escapes project root: {relative!r}") from exc
    return target


def _file_manifest(root: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for path in sorted(p for p in root.rglob("*") if p.is_file() and not p.is_symlink()):
        rel = path.relative_to(root).as_posix()
        content = path.read_bytes()
        rows.append({
            "path": rel,
            "bytes": len(content),
            "sha256": hashlib.sha256(content).hexdigest(),
        })
    return rows


class _LocalReferenceParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.references: list[tuple[str, str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        for key, value in attrs:
            if value is None:
                continue
            if key in {"src", "href"}:
                self.references.append((tag, key, value))


CSS_URL_PATTERN = re.compile(r"url\(\s*(['\"]?)([^)'\"]+)\1\s*\)", re.IGNORECASE)
CSS_IMPORT_PATTERN = re.compile(r"@import\s+(?:url\(\s*)?(['\"])([^'\"]+)\1\s*\)?", re.IGNORECASE)
JS_IMPORT_PATTERNS = (
    re.compile(r"\b(?:import|export)\s+(?:[^'\"]*?\sfrom\s+)?['\"]([^'\"]+)['\"]"),
    re.compile(r"\bimport\s*\(\s*['\"]([^'\"]+)['\"]\s*\)"),
)


def _reference_is_external(value: str) -> bool:
    stripped = value.strip()
    if not stripped or stripped.startswith("#") or stripped.startswith("//"):
        return True
    parsed = urlsplit(stripped)
    return parsed.scheme.casefold() in {
        "http",
        "https",
        "mailto",
        "tel",
        "data",
        "javascript",
    }


def _validate_local_references(
    root: Path,
    source_path: Path,
    references: list[dict[str, str]],
    check_type: str,
) -> dict[str, Any]:
    unresolved: list[dict[str, Any]] = []
    local: list[dict[str, Any]] = []
    external: list[str] = []

    for reference in references:
        value = reference["reference"]
        if _reference_is_external(value) or reference.get("external") == "true":
            external.append(value)
            continue
        parsed = urlsplit(value)
        candidate_text = unquote(parsed.path)
        if candidate_text.startswith("/"):
            unresolved.append({
                **reference,
                "reason": "absolute browser path is not portable for a local file project",
            })
            continue
        candidate = (source_path.parent / candidate_text).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            unresolved.append({**reference, "reason": "reference escapes project root"})
            continue
        exists = candidate.is_file()
        local.append({
            **reference,
            "resolved": candidate.relative_to(root).as_posix() if exists else candidate_text,
            "exists": exists,
        })
        if not exists:
            unresolved.append({**reference, "reason": "referenced local file does not exist"})

    return {
        "type": check_type,
        "path": source_path.relative_to(root).as_posix(),
        "passed": not unresolved,
        "local_references": local,
        "external_references": sorted(set(external)),
        "unresolved": unresolved,
    }


def _validate_html_links(root: Path, html_path: Path) -> dict[str, Any]:
    parser = _LocalReferenceParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    references = [
        {"tag": tag, "attribute": attr, "reference": value}
        for tag, attr, value in parser.references
    ]
    return _validate_local_references(root, html_path, references, "html-local-links")


def _validate_css_links(root: Path, css_path: Path) -> dict[str, Any]:
    text = css_path.read_text(encoding="utf-8")
    references: list[dict[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for kind, pattern in (("url", CSS_URL_PATTERN), ("import", CSS_IMPORT_PATTERN)):
        for match in pattern.finditer(text):
            value = match.group(2).strip()
            key = (kind, value)
            if key not in seen:
                references.append({"syntax": kind, "reference": value})
                seen.add(key)
    return _validate_local_references(root, css_path, references, "css-local-links")


def _validate_javascript_imports(root: Path, script_path: Path) -> dict[str, Any]:
    text = script_path.read_text(encoding="utf-8")
    values: list[str] = []
    for pattern in JS_IMPORT_PATTERNS:
        values.extend(match.group(1).strip() for match in pattern.finditer(text))
    references: list[dict[str, str]] = []
    for value in dict.fromkeys(values):
        bare = not value.startswith((".", "/")) and not urlsplit(value).scheme
        references.append({
            "syntax": "module-import",
            "reference": value,
            "external": "true" if bare else "false",
        })
    return _validate_local_references(root, script_path, references, "javascript-local-imports")


def _check_no_symlinks(root: Path, _check: dict[str, Any]) -> dict[str, Any]:
    links = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_symlink())
    return {"type": "project-no-symlinks", "passed": not links, "symlinks": links}


def _check_project_nonempty(root: Path, _check: dict[str, Any]) -> dict[str, Any]:
    files = _file_manifest(root)
    return {"type": "project-nonempty", "passed": bool(files), "file_count": len(files)}


def _check_file_exists(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
    except ProjectError as exc:
        return {"type": "file-exists", "path": relative, "passed": False, "error": str(exc)}
    return {"type": "file-exists", "path": relative, "passed": path.is_file()}


def _check_nonempty(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
    except ProjectError as exc:
        return {"type": "nonempty", "path": relative, "passed": False, "error": str(exc)}
    passed = path.is_file() and path.stat().st_size > 0
    return {"type": "nonempty", "path": relative, "passed": passed, "bytes": path.stat().st_size if path.is_file() else 0}


def _check_contains(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    needle = str(check.get("text", ""))
    try:
        path = _resolve_inside(root, relative)
        text = path.read_text(encoding="utf-8")
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": "contains", "path": relative, "text": needle, "passed": False, "error": str(exc)}
    return {"type": "contains", "path": relative, "text": needle, "passed": needle in text}


def _check_file_absent(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
    except ProjectError as exc:
        return {"type": "file-absent", "path": relative, "passed": False, "error": str(exc)}
    return {"type": "file-absent", "path": relative, "passed": not path.exists()}


def _check_not_contains(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    needle = check.get("text")
    if not isinstance(needle, str) or not needle:
        return {
            "type": "not-contains",
            "path": relative,
            "passed": False,
            "error": "text must be a non-empty string",
        }
    try:
        path = _resolve_inside(root, relative)
        text = path.read_text(encoding="utf-8")
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": "not-contains", "path": relative, "text": needle, "passed": False, "error": str(exc)}
    return {"type": "not-contains", "path": relative, "text": needle, "passed": needle not in text}


def _integer_bound(check: dict[str, Any], key: str) -> tuple[int | None, str | None]:
    value = check.get(key)
    if value is None:
        return None, None
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        return None, f"{key} must be a non-negative integer"
    return value, None


def _check_bounded_measure(
    root: Path,
    check: dict[str, Any],
    check_type: str,
    measure: str,
) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    minimum, minimum_error = _integer_bound(check, "minimum")
    maximum, maximum_error = _integer_bound(check, "maximum")
    error = minimum_error or maximum_error
    if error or (minimum is None and maximum is None):
        return {
            "type": check_type,
            "path": relative,
            "passed": False,
            "error": error or "minimum or maximum is required",
        }
    if minimum is not None and maximum is not None and minimum > maximum:
        return {
            "type": check_type,
            "path": relative,
            "passed": False,
            "error": "minimum cannot exceed maximum",
        }
    try:
        path = _resolve_inside(root, relative)
        if measure == "lines":
            observed = len(path.read_text(encoding="utf-8").splitlines())
        else:
            observed = len(path.read_bytes())
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": check_type, "path": relative, "passed": False, "error": str(exc)}
    passed = (minimum is None or observed >= minimum) and (maximum is None or observed <= maximum)
    return {
        "type": check_type,
        "path": relative,
        "passed": passed,
        measure: observed,
        "minimum": minimum,
        "maximum": maximum,
    }


def _check_line_count(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _check_bounded_measure(root, check, "line-count", "lines")


def _check_byte_size(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    return _check_bounded_measure(root, check, "byte-size", "bytes")


def _check_sha256(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    expected = str(check.get("sha256", "")).strip().casefold()
    if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
        return {
            "type": "sha256",
            "path": relative,
            "passed": False,
            "error": "sha256 must be 64 hexadecimal characters",
        }
    try:
        path = _resolve_inside(root, relative)
        content = path.read_bytes()
    except (ProjectError, OSError) as exc:
        return {"type": "sha256", "path": relative, "passed": False, "error": str(exc)}
    actual = hashlib.sha256(content).hexdigest()
    return {
        "type": "sha256",
        "path": relative,
        "passed": actual == expected,
        "expected_sha256": expected,
        "actual_sha256": actual,
        "actual_bytes": len(content),
    }


def _check_json_value(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    json_path = check.get("json_path")
    if not isinstance(json_path, list) or not json_path:
        return {
            "type": "json-value",
            "path": relative,
            "passed": False,
            "error": "json_path must be a non-empty list of object keys or array indexes",
        }
    if "equals" not in check:
        return {"type": "json-value", "path": relative, "passed": False, "error": "equals is required"}
    try:
        path = _resolve_inside(root, relative)
        value: Any = json.loads(path.read_text(encoding="utf-8"))
        for part in json_path:
            if isinstance(value, dict) and isinstance(part, str) and part in value:
                value = value[part]
            elif isinstance(value, list) and isinstance(part, int) and not isinstance(part, bool) and 0 <= part < len(value):
                value = value[part]
            else:
                raise KeyError(part)
    except (ProjectError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"type": "json-value", "path": relative, "json_path": json_path, "passed": False, "error": str(exc)}
    except KeyError as exc:
        return {
            "type": "json-value",
            "path": relative,
            "json_path": json_path,
            "passed": False,
            "error": f"JSON path segment not found: {exc.args[0]!r}",
        }
    expected = check["equals"]
    passed = type(value) is type(expected) and value == expected
    return {
        "type": "json-value",
        "path": relative,
        "json_path": json_path,
        "passed": passed,
        "expected": expected,
        "actual": value,
    }


def _check_file_set(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    raw_files = check.get("files")
    mode = str(check.get("mode", "contains")).strip().casefold()
    if not isinstance(raw_files, list) or not raw_files:
        return {"type": "file-set", "passed": False, "error": "files must be a non-empty list"}
    if mode not in {"contains", "exact"}:
        return {"type": "file-set", "passed": False, "error": "mode must be contains or exact"}
    expected: list[str] = []
    try:
        for raw in raw_files:
            normalized = _safe_relative_path(str(raw)).as_posix()
            if normalized not in expected:
                expected.append(normalized)
    except ProjectError as exc:
        return {"type": "file-set", "passed": False, "error": str(exc)}
    actual = sorted(path.relative_to(root).as_posix() for path in root.rglob("*") if path.is_file())
    missing = sorted(set(expected) - set(actual))
    unexpected = sorted(set(actual) - set(expected)) if mode == "exact" else []
    return {
        "type": "file-set",
        "mode": mode,
        "passed": not missing and not unexpected,
        "expected": expected,
        "actual": actual,
        "missing": missing,
        "unexpected": unexpected,
    }


def _check_json(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
        json.loads(path.read_text(encoding="utf-8"))
    except (ProjectError, OSError, UnicodeError, json.JSONDecodeError) as exc:
        return {"type": "json-valid", "path": relative, "passed": False, "error": str(exc)}
    return {"type": "json-valid", "path": relative, "passed": True}


def _compile_python(path: Path) -> tuple[bool, str | None]:
    try:
        compile(path.read_text(encoding="utf-8"), str(path), "exec", dont_inherit=True)
    except (OSError, UnicodeError, SyntaxError) as exc:
        return False, str(exc)
    return True, None


def _check_python(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    raw = check.get("path")
    paths: list[Path]
    if raw:
        try:
            paths = [_resolve_inside(root, str(raw))]
        except ProjectError as exc:
            return {"type": "python-compile", "path": str(raw), "passed": False, "error": str(exc)}
    else:
        paths = sorted(root.rglob("*.py"))
    results: list[dict[str, Any]] = []
    for path in paths:
        passed, error = _compile_python(path)
        row: dict[str, Any] = {
            "path": path.relative_to(root).as_posix(),
            "passed": passed,
        }
        if error:
            row["error"] = error
        results.append(row)
    return {
        "type": "python-compile",
        "passed": bool(results) and all(row["passed"] for row in results),
        "files": results,
    }


def _check_html_links(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", "index.html"))
    try:
        path = _resolve_inside(root, relative)
        if not path.is_file():
            return {"type": "html-local-links", "path": relative, "passed": False, "error": "HTML file does not exist"}
        return _validate_html_links(root, path)
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": "html-local-links", "path": relative, "passed": False, "error": str(exc)}


def _check_css_links(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
        if not path.is_file():
            return {"type": "css-local-links", "path": relative, "passed": False, "error": "CSS file does not exist"}
        return _validate_css_links(root, path)
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": "css-local-links", "path": relative, "passed": False, "error": str(exc)}


def _check_javascript_imports(root: Path, check: dict[str, Any]) -> dict[str, Any]:
    relative = str(check.get("path", ""))
    try:
        path = _resolve_inside(root, relative)
        if not path.is_file():
            return {
                "type": "javascript-local-imports",
                "path": relative,
                "passed": False,
                "error": "JavaScript module does not exist",
            }
        return _validate_javascript_imports(root, path)
    except (ProjectError, OSError, UnicodeError) as exc:
        return {"type": "javascript-local-imports", "path": relative, "passed": False, "error": str(exc)}


def _check_expected_files(root: Path, expected_files: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = True
    for raw_path, expected in expected_files.items():
        relative = str(raw_path)
        if not isinstance(expected, str):
            rows.append({"path": relative, "passed": False, "error": "expected text must be a string"})
            passed = False
            continue
        try:
            path = _resolve_inside(root, relative)
            actual = path.read_text(encoding="utf-8")
        except (ProjectError, OSError, UnicodeError) as exc:
            rows.append({"path": relative, "passed": False, "error": str(exc)})
            passed = False
            continue
        match = actual == expected
        rows.append({
            "path": relative,
            "passed": match,
            "expected_bytes": len(expected.encode("utf-8")),
            "actual_bytes": len(actual.encode("utf-8")),
        })
        passed = passed and match
    return {"type": "expected-files-exact", "passed": passed and bool(rows), "files": rows}


def _check_expected_file_digests(root: Path, expected_digests: dict[str, Any]) -> dict[str, Any]:
    rows: list[dict[str, Any]] = []
    passed = True
    for raw_path, raw_expected in expected_digests.items():
        relative = str(raw_path)
        expected = str(raw_expected).strip()
        if len(expected) != 64 or any(character not in "0123456789abcdef" for character in expected):
            rows.append({"path": relative, "passed": False, "error": "expected SHA-256 must be 64 lowercase hexadecimal characters"})
            passed = False
            continue
        try:
            path = _resolve_inside(root, relative)
            content = path.read_bytes()
        except (ProjectError, OSError) as exc:
            rows.append({"path": relative, "passed": False, "error": str(exc)})
            passed = False
            continue
        actual = hashlib.sha256(content).hexdigest()
        match = actual == expected
        rows.append({
            "path": relative,
            "passed": match,
            "expected_sha256": expected,
            "actual_sha256": actual,
            "actual_bytes": len(content),
        })
        passed = passed and match
    return {"type": "expected-file-digests", "passed": passed and bool(rows), "files": rows}


def _publication_integrity(validation: dict[str, Any]) -> bool:
    checks = validation.get("checks") if isinstance(validation.get("checks"), list) else []
    required = {
        row.get("type"): row.get("passed") is True
        for row in checks
        if row.get("type") in {"project-nonempty", "expected-files-exact"}
    }
    return required == {"project-nonempty": True, "expected-files-exact": True}


def _grounding(validation: dict[str, Any], publish_mode: str) -> dict[str, Any]:
    checks = validation.get("checks") if isinstance(validation.get("checks"), list) else []
    gaps = [row for row in checks if row.get("passed") is not True]
    validation_passed = validation.get("passed") is True
    return {
        "truth_status": "OBSERVED_DETERMINISTIC_PROJECT_VALIDATION",
        "publish_mode": publish_mode,
        "creation_status": "VALIDATED_CREATION" if validation_passed else "GROUNDED_DRAFT",
        "validation_passed": validation_passed,
        "creation_retained": True,
        "observed_gap_count": len(gaps),
        "observed_gaps": gaps,
        "gap_meaning": "failed checks expose current creation or capability gaps; they are not automatically a prohibition on retaining the creation",
    }


CHECKS = {
    "project-nonempty": _check_project_nonempty,
    "file-exists": _check_file_exists,
    "file-absent": _check_file_absent,
    "nonempty": _check_nonempty,
    "contains": _check_contains,
    "not-contains": _check_not_contains,
    "line-count": _check_line_count,
    "byte-size": _check_byte_size,
    "sha256": _check_sha256,
    "json-valid": _check_json,
    "json-value": _check_json_value,
    "file-set": _check_file_set,
    "python-compile": _check_python,
    "html-local-links": _check_html_links,
    "css-local-links": _check_css_links,
    "javascript-local-imports": _check_javascript_imports,
}


def validate_project(
    root: Path,
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    expected_files: dict[str, Any] | None = None,
    expected_file_digests: dict[str, Any] | None = None,
) -> dict[str, Any]:
    root = Path(root).resolve()
    results: list[dict[str, Any]] = []
    project_type = str(project_type or "generic").strip().casefold()

    if not root.is_dir():
        return {
            "passed": False,
            "project_type": project_type,
            "checks": [{"type": "project-directory", "passed": False, "error": "project directory does not exist"}],
            "files": [],
            "limitations": ["validation does not execute generated code"],
        }

    results.append(_check_project_nonempty(root, {}))
    results.append(_check_no_symlinks(root, {}))
    json_files = sorted(
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path.suffix.casefold() == ".json"
    )
    for relative in json_files:
        results.append(_check_json(root, {"path": relative}))
    if project_type in {"static-web", "web", "static-web-project"}:
        results.append(_check_file_exists(root, {"path": "index.html"}))
        html_files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and path.suffix.casefold() in {".html", ".htm"}
        )
        for relative in html_files:
            results.append(_check_html_links(root, {"path": relative}))
        css_files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*.css")
            if path.is_file() and not path.is_symlink()
        )
        for relative in css_files:
            results.append(_check_css_links(root, {"path": relative}))
        script_files = sorted(
            path.relative_to(root).as_posix()
            for path in root.rglob("*")
            if path.is_file() and not path.is_symlink() and path.suffix.casefold() in {".js", ".mjs"}
        )
        for relative in script_files:
            results.append(_check_javascript_imports(root, {"path": relative}))
    if project_type in {"python", "python-project"}:
        results.append(_check_python(root, {}))

    for check in checks or []:
        if not isinstance(check, dict):
            results.append({"type": "invalid-check", "passed": False, "error": "deterministic check must be an object"})
            continue
        kind = str(check.get("type", "")).strip().casefold()
        fn = CHECKS.get(kind)
        if fn is None:
            results.append({"type": kind or "unknown", "passed": False, "error": "unsupported deterministic check"})
            continue
        results.append(fn(root, check))

    if expected_files is not None:
        results.append(_check_expected_files(root, expected_files))
    if expected_file_digests is not None:
        results.append(_check_expected_file_digests(root, expected_file_digests))

    return {
        "passed": bool(results) and all(row.get("passed") is True for row in results),
        "project_type": project_type,
        "checks": results,
        "files": _file_manifest(root),
        "limitations": [
            "generated code is not executed by deterministic project validation",
            "visual appearance and interactive browser behavior require a browser/user/authorized host to test",
            "CSS and JavaScript local-reference checks are bounded lexical checks, not full browser or language execution",
        ],
    }


def _begin_publish(stage: Path, target: Path, replace: bool) -> Path | None:
    backup: Path | None = None
    if target.exists():
        if not replace:
            raise ProjectError(f"target project already exists: {target}")
        if not target.is_dir():
            raise ProjectError(f"target exists and is not a directory: {target}")
        backup = target.with_name(f".{target.name}.axm-backup-{uuid.uuid4().hex}")
        os.replace(target, backup)
    try:
        os.replace(stage, target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            os.replace(backup, target)
        raise
    return backup


def _rollback_publish(target: Path, backup: Path | None) -> None:
    if target.exists():
        if target.is_dir():
            shutil.rmtree(target)
        else:
            target.unlink()
    if backup is not None and backup.exists():
        os.replace(backup, target)


def preview_project_files(files: Any, project_type: Any = "generic") -> dict[str, Any]:
    """Normalize one exact UTF-8 project file map without touching the filesystem."""
    if not isinstance(files, dict) or not files:
        raise ProjectError("files must be a non-empty object mapping relative paths to text content")

    normalized_files: dict[str, str] = {}
    for raw_path, raw_content in files.items():
        rel = _safe_relative_path(str(raw_path))
        key = rel.as_posix()
        if key in normalized_files:
            raise ProjectError(f"duplicate project file path: {key}")
        if not isinstance(raw_content, str):
            raise ProjectError(f"project file content must be text for the current milestone: {key}")
        normalized_files[key] = raw_content
    return {
        "project_type": str(project_type or "generic").strip().casefold(),
        "files": normalized_files,
    }


def build_project(
    target: Path,
    files: dict[str, Any],
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
    publish_mode: str = "validated",
) -> dict[str, Any]:
    target = Path(target).resolve()
    publish_mode = str(publish_mode).strip().casefold()
    if publish_mode not in PUBLISH_MODES:
        raise ProjectError("publish_mode must be validated or grounded-draft")
    preview = preview_project_files(files, project_type)
    project_type = preview["project_type"]
    expected_files = preview["files"]
    normalized = [(PurePosixPath(path), content) for path, content in expected_files.items()]

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(f".{target.name}.axm-build-{uuid.uuid4().hex}")
    if stage.exists():
        raise ProjectError(f"unexpected staging collision: {stage}")
    stage.mkdir(parents=False)

    backup: Path | None = None
    published = False
    try:
        for rel, content in normalized:
            path = stage.joinpath(*rel.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")

        validation = validate_project(stage, project_type=project_type, checks=checks, expected_files=expected_files)
        if not _publication_integrity(validation):
            raise ProjectError("project publication integrity failed before publish", {"phase": "pre-publish", "validation": validation})
        if publish_mode == "validated" and not validation["passed"]:
            raise ProjectError("project validation failed before publish", {"phase": "pre-publish", "validation": validation})

        backup = _begin_publish(stage, target, replace=replace)
        published = True
        published_validation = validate_project(target, project_type=project_type, checks=checks, expected_files=expected_files)
        if not _publication_integrity(published_validation):
            _rollback_publish(target, backup)
            published = False
            raise ProjectError(
                "project publication integrity failed after publish; previous body restored",
                {"phase": "post-publish", "validation": published_validation, "rolled_back": True},
            )
        if publish_mode == "validated" and not published_validation["passed"]:
            _rollback_publish(target, backup)
            published = False
            raise ProjectError(
                "project validation failed after publish; previous body restored",
                {"phase": "post-publish", "validation": published_validation, "rolled_back": True},
            )

        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return {
            "path": str(target),
            "project_type": str(project_type or "generic"),
            "published": True,
            "publish_mode": publish_mode,
            "creation_status": "VALIDATED_CREATION" if published_validation["passed"] else "GROUNDED_DRAFT",
            "files": _file_manifest(target),
            "validation": published_validation,
            "grounding": _grounding(published_validation, publish_mode),
        }
    except Exception:
        if published and target.exists():
            _rollback_publish(target, backup)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

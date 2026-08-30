from __future__ import annotations

import json
import os
import shutil
import uuid
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlsplit


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
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        rel = path.relative_to(root).as_posix()
        rows.append({"path": rel, "bytes": path.stat().st_size})
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


def _validate_html_links(root: Path, html_path: Path) -> dict[str, Any]:
    parser = _LocalReferenceParser()
    parser.feed(html_path.read_text(encoding="utf-8"))
    unresolved: list[dict[str, Any]] = []
    local: list[dict[str, Any]] = []
    external: list[str] = []

    for tag, attr, value in parser.references:
        if _reference_is_external(value):
            external.append(value)
            continue
        parsed = urlsplit(value)
        candidate_text = unquote(parsed.path)
        if candidate_text.startswith("/"):
            unresolved.append({
                "reference": value,
                "reason": "absolute browser path is not portable for a local file project",
            })
            continue
        candidate = (html_path.parent / candidate_text).resolve()
        try:
            candidate.relative_to(root.resolve())
        except ValueError:
            unresolved.append({"reference": value, "reason": "reference escapes project root"})
            continue
        exists = candidate.exists()
        local.append({
            "reference": value,
            "resolved": candidate.relative_to(root).as_posix() if exists else candidate_text,
            "exists": exists,
        })
        if not exists:
            unresolved.append({"reference": value, "reason": "referenced local file does not exist"})

    return {
        "type": "html-local-links",
        "path": html_path.relative_to(root).as_posix(),
        "passed": not unresolved,
        "local_references": local,
        "external_references": sorted(set(external)),
        "unresolved": unresolved,
    }


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


CHECKS = {
    "project-nonempty": _check_project_nonempty,
    "file-exists": _check_file_exists,
    "nonempty": _check_nonempty,
    "contains": _check_contains,
    "json-valid": _check_json,
    "python-compile": _check_python,
    "html-local-links": _check_html_links,
}


def validate_project(
    root: Path,
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    expected_files: dict[str, Any] | None = None,
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
    if project_type in {"static-web", "web", "static-web-project"}:
        results.append(_check_file_exists(root, {"path": "index.html"}))
        if (root / "index.html").is_file():
            results.append(_check_html_links(root, {"path": "index.html"}))
    if project_type in {"python", "python-project"}:
        results.append(_check_python(root, {}))

    for check in checks or []:
        kind = str(check.get("type", "")).strip().casefold()
        fn = CHECKS.get(kind)
        if fn is None:
            results.append({"type": kind or "unknown", "passed": False, "error": "unsupported deterministic check"})
            continue
        results.append(fn(root, check))

    if expected_files is not None:
        results.append(_check_expected_files(root, expected_files))

    return {
        "passed": bool(results) and all(row.get("passed") is True for row in results),
        "project_type": project_type,
        "checks": results,
        "files": _file_manifest(root),
        "limitations": [
            "generated code is not executed by deterministic project validation",
            "visual appearance and interactive browser behavior require a browser/user/authorized host to test",
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


def build_project(
    target: Path,
    files: dict[str, Any],
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    target = Path(target).resolve()
    if not isinstance(files, dict) or not files:
        raise ProjectError("files must be a non-empty object mapping relative paths to text content")

    normalized: list[tuple[PurePosixPath, str]] = []
    seen: set[str] = set()
    expected_files: dict[str, str] = {}
    for raw_path, raw_content in files.items():
        rel = _safe_relative_path(str(raw_path))
        key = rel.as_posix()
        if key in seen:
            raise ProjectError(f"duplicate project file path: {key}")
        seen.add(key)
        if not isinstance(raw_content, str):
            raise ProjectError(f"project file content must be text for the current milestone: {key}")
        normalized.append((rel, raw_content))
        expected_files[key] = raw_content

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
        if not validation["passed"]:
            raise ProjectError("project validation failed before publish", {"phase": "pre-publish", "validation": validation})

        backup = _begin_publish(stage, target, replace=replace)
        published = True
        published_validation = validate_project(target, project_type=project_type, checks=checks, expected_files=expected_files)
        if not published_validation["passed"]:
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
            "files": _file_manifest(target),
            "validation": published_validation,
        }
    except Exception:
        if published and target.exists():
            _rollback_publish(target, backup)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

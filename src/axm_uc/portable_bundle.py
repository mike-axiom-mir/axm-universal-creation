from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import uuid
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

from .project import (
    ProjectError,
    _begin_publish,
    _check_no_symlinks,
    _file_manifest,
    _rollback_publish,
    _safe_relative_path,
    validate_project,
)


BUNDLE_SCHEMA = "axm.portable-creation-bundle/v0.1"
MANIFEST_NAME = "AXM-CREATION-MANIFEST.json"
MAX_ARCHIVE_BYTES = 128 * 1024 * 1024
MAX_BODY_BYTES = 128 * 1024 * 1024
MAX_FILE_BYTES = 64 * 1024 * 1024
MAX_FILES = 1024


def portable_bundle_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_EXACT_PORTABLE_CREATION_BUNDLE",
        "schema": BUNDLE_SCHEMA,
        "operations": ["pack", "inspect", "unpack"],
        "maximum_files": MAX_FILES,
        "maximum_archive_bytes": MAX_ARCHIVE_BYTES,
        "maximum_body_bytes": MAX_BODY_BYTES,
        "symlinks_allowed": False,
        "runtime_compatibility_proven": False,
    }


class PortableBundleError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def _zip_info(name: str) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    return info


def _inside(parent: Path, child: Path) -> bool:
    try:
        child.resolve().relative_to(parent.resolve())
    except ValueError:
        return False
    return True


def _validate_file_rows(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not raw or len(raw) > MAX_FILES:
        raise PortableBundleError(f"bundle manifest files must contain 1..{MAX_FILES} entries")
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    total = 0
    for index, row in enumerate(raw):
        if not isinstance(row, dict) or set(row) != {"path", "bytes", "sha256"}:
            raise PortableBundleError("bundle file receipt must contain exactly path, bytes, and sha256", {"index": index})
        path = _safe_relative_path(str(row.get("path", ""))).as_posix()
        if path in seen:
            raise PortableBundleError("bundle manifest contains a duplicate path", {"path": path})
        size = row.get("bytes")
        digest = row.get("sha256")
        if isinstance(size, bool) or not isinstance(size, int) or size < 0 or size > MAX_FILE_BYTES:
            raise PortableBundleError("bundle file size is outside the supported boundary", {"path": path, "bytes": size})
        if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
            raise PortableBundleError("bundle file SHA-256 is invalid", {"path": path})
        total += size
        if total > MAX_BODY_BYTES:
            raise PortableBundleError("bundle body exceeds the supported byte boundary")
        rows.append({"path": path, "bytes": size, "sha256": digest})
        seen.add(path)
    return rows


def inspect_bundle(path: Path) -> dict[str, Any]:
    path = Path(path).resolve()
    if not path.is_file():
        raise PortableBundleError(f"portable creation bundle does not exist: {path}")
    archive_bytes = path.stat().st_size
    if archive_bytes > MAX_ARCHIVE_BYTES:
        raise PortableBundleError("portable creation bundle exceeds the archive byte boundary")
    try:
        with zipfile.ZipFile(path, "r") as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if len(names) != len(set(names)):
                raise PortableBundleError("portable creation bundle contains duplicate ZIP entries")
            if len(infos) > MAX_FILES + 1:
                raise PortableBundleError("portable creation bundle contains too many ZIP entries")
            for info in infos:
                if info.is_dir() or info.compress_type != zipfile.ZIP_STORED:
                    raise PortableBundleError("bundle entries must be regular uncompressed files", {"entry": info.filename})
                if stat.S_ISLNK(info.external_attr >> 16):
                    raise PortableBundleError("bundle symlink entries are forbidden", {"entry": info.filename})
                if info.file_size > MAX_FILE_BYTES:
                    raise PortableBundleError("bundle entry exceeds the per-file boundary", {"entry": info.filename})
            if MANIFEST_NAME not in names:
                raise PortableBundleError(f"bundle is missing {MANIFEST_NAME}")
            manifest_bytes = archive.read(MANIFEST_NAME)
            if len(manifest_bytes) > 1024 * 1024:
                raise PortableBundleError("bundle manifest exceeds one MiB")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            if not isinstance(manifest, dict) or set(manifest) != {"schema", "name", "project_type", "files"}:
                raise PortableBundleError("bundle manifest shape is unsupported")
            if manifest.get("schema") != BUNDLE_SCHEMA:
                raise PortableBundleError("bundle manifest schema is unsupported")
            if not isinstance(manifest.get("name"), str) or not manifest["name"].strip():
                raise PortableBundleError("bundle manifest name must be non-empty text")
            if not isinstance(manifest.get("project_type"), str) or not manifest["project_type"].strip():
                raise PortableBundleError("bundle manifest project_type must be non-empty text")
            rows = _validate_file_rows(manifest.get("files"))
            expected_entries = {MANIFEST_NAME, *(f"body/{row['path']}" for row in rows)}
            if set(names) != expected_entries:
                raise PortableBundleError(
                    "bundle ZIP entries do not exactly match the manifest",
                    {
                        "missing_entries": sorted(expected_entries - set(names)),
                        "unexpected_entries": sorted(set(names) - expected_entries),
                    },
                )
            observed: list[dict[str, Any]] = []
            for row in rows:
                body = archive.read(f"body/{row['path']}")
                actual = {"path": row["path"], "bytes": len(body), "sha256": _digest(body)}
                actual["passed"] = actual["bytes"] == row["bytes"] and actual["sha256"] == row["sha256"]
                observed.append(actual)
            if not all(row["passed"] for row in observed):
                raise PortableBundleError("bundle body does not match its manifest", {"observed_files": observed})
    except PortableBundleError:
        raise
    except (OSError, RuntimeError, UnicodeError, json.JSONDecodeError, zipfile.BadZipFile, ProjectError) as exc:
        raise PortableBundleError("portable creation bundle could not be safely inspected", {"error": str(exc)}) from exc
    return {
        "truth_status": "OBSERVED_EXACT_PORTABLE_BUNDLE_BYTES",
        "path": str(path),
        "archive_bytes": archive_bytes,
        "archive_sha256": _digest(path.read_bytes()),
        "manifest": {**manifest, "files": rows},
        "observed_files": observed,
        "passed": True,
        "proof_scope": "archive shape, path safety, byte counts, and SHA-256 identity; runtime and semantic behavior are not proven",
    }


def pack_bundle(
    source: Path,
    path: Path,
    *,
    project_type: str = "generic",
    name: str | None = None,
    replace: bool = False,
) -> dict[str, Any]:
    source = Path(source).resolve()
    path = Path(path).resolve()
    if not source.is_dir():
        raise PortableBundleError(f"bundle source project does not exist: {source}")
    if _inside(source, path):
        raise PortableBundleError("bundle archive cannot be written inside its source project")
    no_links = _check_no_symlinks(source, {})
    if no_links["passed"] is not True:
        raise PortableBundleError("bundle source contains forbidden symlinks", {"validation": no_links})
    validation = validate_project(source, project_type=project_type)
    if validation["passed"] is not True:
        raise PortableBundleError("bundle source failed deterministic project validation", {"validation": validation})
    files = _file_manifest(source)
    if len(files) > MAX_FILES or sum(row["bytes"] for row in files) > MAX_BODY_BYTES:
        raise PortableBundleError("bundle source exceeds the supported file or byte boundary")
    bundle_name = name if name is not None else source.name
    if not isinstance(bundle_name, str) or not bundle_name.strip() or len(bundle_name) > 200:
        raise PortableBundleError("bundle name must be 1..200 characters of text")
    manifest = {
        "schema": BUNDLE_SCHEMA,
        "name": bundle_name.strip(),
        "project_type": str(project_type or "generic").strip().casefold(),
        "files": files,
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not replace:
        raise PortableBundleError(f"bundle target already exists: {path}")
    stage = path.with_name(f".{path.name}.axm-bundle-{uuid.uuid4().hex}")
    try:
        with zipfile.ZipFile(stage, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
            archive.writestr(_zip_info(MANIFEST_NAME), _canonical_json(manifest))
            for row in files:
                archive.writestr(_zip_info(f"body/{row['path']}"), (source / row["path"]).read_bytes())
        inspected = inspect_bundle(stage)
        os.replace(stage, path)
    finally:
        if stage.exists():
            stage.unlink()
    return {
        "operation": "pack",
        "path": str(path),
        "source": str(source),
        "packed": True,
        "archive_bytes": path.stat().st_size,
        "archive_sha256": _digest(path.read_bytes()),
        "manifest": manifest,
        "pre_pack_validation": validation,
        "staged_bundle_inspection": inspected,
    }


def unpack_bundle(path: Path, target: Path, *, replace: bool = False) -> dict[str, Any]:
    path = Path(path).resolve()
    target = Path(target).resolve()
    if _inside(target, path):
        raise PortableBundleError("bundle archive cannot be read from inside its target project")
    inspected = inspect_bundle(path)
    manifest = inspected["manifest"]
    expected_digests = {row["path"]: row["sha256"] for row in manifest["files"]}
    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(f".{target.name}.axm-unpack-{uuid.uuid4().hex}")
    if stage.exists():
        raise PortableBundleError(f"unexpected bundle staging collision: {stage}")
    stage.mkdir(parents=False)
    backup: Path | None = None
    published = False
    try:
        with zipfile.ZipFile(path, "r") as archive:
            for row in manifest["files"]:
                rel = PurePosixPath(row["path"])
                destination = stage.joinpath(*rel.parts)
                destination.parent.mkdir(parents=True, exist_ok=True)
                destination.write_bytes(archive.read(f"body/{row['path']}"))
        validation = validate_project(
            stage,
            project_type=manifest["project_type"],
            expected_file_digests=expected_digests,
        )
        if validation["passed"] is not True:
            raise PortableBundleError("unpacked project failed deterministic validation", {"validation": validation})
        backup = _begin_publish(stage, target, replace=replace)
        published = True
        published_validation = validate_project(
            target,
            project_type=manifest["project_type"],
            expected_file_digests=expected_digests,
        )
        if published_validation["passed"] is not True:
            _rollback_publish(target, backup)
            published = False
            raise PortableBundleError(
                "published bundle body failed verification; previous target restored",
                {"validation": published_validation, "rolled_back": True},
            )
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return {
            "operation": "unpack",
            "path": str(path),
            "target": str(target),
            "published": True,
            "bundle_inspection": inspected,
            "validation": published_validation,
            "files": _file_manifest(target),
        }
    except ProjectError as exc:
        raise PortableBundleError(str(exc), exc.details) from exc
    except Exception:
        if published and target.exists():
            _rollback_publish(target, backup)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)


def operate_portable_bundle(inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "inspect")).strip().casefold()
    if operation == "inspect":
        return {"operation": "inspect", **inspect_bundle(Path(str(inputs["path"])))}
    if operation == "pack":
        return pack_bundle(
            Path(str(inputs["source"])),
            Path(str(inputs["path"])),
            project_type=str(inputs.get("project_type", "generic")),
            name=inputs.get("name"),
            replace=bool(inputs.get("replace", False)),
        )
    if operation == "unpack":
        return unpack_bundle(
            Path(str(inputs["path"])),
            Path(str(inputs["target"])),
            replace=bool(inputs.get("replace", False)),
        )
    raise PortableBundleError("portable bundle operation must be inspect, pack, or unpack")

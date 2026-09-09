from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".axm-build", "snapshots"}
SNAPSHOT_MANIFEST = ".axm-snapshot-manifest.json"
SNAPSHOT_SCHEMA = "axm.universal-creation.snapshot/v1"


def _iter_snapshot_files(root: Path):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(root)
        if any(part in EXCLUDED_DIRS for part in rel.parts):
            continue
        if path.suffix == ".pyc":
            continue
        yield path, rel


def _write_snapshot_file(archive: zipfile.ZipFile, path: Path, rel: Path) -> dict[str, Any]:
    info = zipfile.ZipInfo.from_file(path, rel.as_posix())
    info.compress_type = zipfile.ZIP_DEFLATED
    hasher = hashlib.sha256()
    size = 0
    with path.open("rb") as source, archive.open(info, "w") as target:
        while True:
            chunk = source.read(1024 * 1024)
            if not chunk:
                break
            target.write(chunk)
            hasher.update(chunk)
            size += len(chunk)
    return {"path": rel.as_posix(), "bytes": size, "sha256": hasher.hexdigest()}


def _manifest_bytes(day: dt.date, files: list[dict[str, Any]]) -> bytes:
    manifest = {
        "schema": SNAPSHOT_SCHEMA,
        "day": day.isoformat(),
        "file_count": len(files),
        "content_bytes": sum(item["bytes"] for item in files),
        "files": files,
    }
    return (json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode("utf-8")


def create_daily_snapshot(root: Path, output_dir: Path | None = None, replace: bool = False, today: dt.date | None = None) -> dict[str, Any]:
    root = Path(root).resolve()
    day = today or dt.date.today()
    out_dir = Path(output_dir).resolve() if output_dir else root.parent / "axm-universal-creation-snapshots"
    out_dir.mkdir(parents=True, exist_ok=True)
    target = out_dir / f"AXM_Universal_Creation_{day.isoformat()}.zip"
    if target.exists() and not replace:
        return {"created": False, "reason": "daily snapshot already exists", "path": str(target)}
    temp = target.with_suffix(".zip.axm-build")
    try:
        files: list[dict[str, Any]] = []
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, rel in _iter_snapshot_files(root):
                files.append(_write_snapshot_file(archive, path, rel))
            manifest = _manifest_bytes(day, files)
            archive.writestr(SNAPSHOT_MANIFEST, manifest, compress_type=zipfile.ZIP_DEFLATED)
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return {
        "created": True,
        "path": str(target),
        "bytes": target.stat().st_size,
        "schema": SNAPSHOT_SCHEMA,
        "file_count": len(files),
        "content_bytes": sum(item["bytes"] for item in files),
        "manifest_sha256": hashlib.sha256(manifest).hexdigest(),
    }


def _canonical_member_path(name: str) -> PurePosixPath:
    if not name or "\x00" in name or "\\" in name:
        raise ValueError(f"unsafe snapshot path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or name != path.as_posix() or ".." in path.parts:
        raise ValueError(f"unsafe snapshot path: {name}")
    if len(name) >= 2 and name[0].isalpha() and name[1] == ":":
        raise ValueError(f"unsafe snapshot path: {name}")
    return path


def _validate_archive(archive: zipfile.ZipFile) -> list[zipfile.ZipInfo]:
    seen: set[str] = set()
    payload: list[zipfile.ZipInfo] = []
    for info in archive.infolist():
        if info.is_dir():
            raise ValueError(f"snapshot contains directory entry: {info.filename}")
        path = _canonical_member_path(info.filename)
        name = path.as_posix()
        if name in seen:
            raise ValueError(f"duplicate snapshot path: {name}")
        seen.add(name)
        if name == SNAPSHOT_MANIFEST:
            continue
        if any(part in EXCLUDED_DIRS for part in path.parts):
            raise ValueError(f"forbidden snapshot path: {name}")
        payload.append(info)
    payload_names = {info.filename for info in payload}
    for name in payload_names:
        parts = PurePosixPath(name).parts
        for index in range(1, len(parts)):
            if PurePosixPath(*parts[:index]).as_posix() in payload_names:
                raise ValueError(f"snapshot file/directory collision: {name}")
    bad = archive.testzip()
    if bad is not None:
        raise ValueError(f"snapshot CRC check failed: {bad}")
    return payload


def _verify_manifest(archive: zipfile.ZipFile, payload: list[zipfile.ZipInfo]) -> dict[str, Any]:
    try:
        raw = archive.read(SNAPSHOT_MANIFEST)
        manifest = json.loads(raw.decode("utf-8"))
    except (KeyError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("invalid snapshot manifest") from exc
    if not isinstance(manifest, dict) or set(manifest) != {"schema", "day", "file_count", "content_bytes", "files"}:
        raise ValueError("invalid snapshot manifest shape")
    if manifest["schema"] != SNAPSHOT_SCHEMA:
        raise ValueError(f"unsupported snapshot schema: {manifest['schema']!r}")
    try:
        dt.date.fromisoformat(manifest["day"])
    except (TypeError, ValueError) as exc:
        raise ValueError("invalid snapshot manifest day") from exc
    files = manifest["files"]
    if not isinstance(files, list):
        raise ValueError("invalid snapshot manifest files")
    declared: dict[str, dict[str, Any]] = {}
    for item in files:
        if not isinstance(item, dict) or set(item) != {"path", "bytes", "sha256"}:
            raise ValueError("invalid snapshot manifest file entry")
        path = item["path"]
        if not isinstance(path, str) or _canonical_member_path(path).as_posix() != path:
            raise ValueError("invalid snapshot manifest file path")
        if path == SNAPSHOT_MANIFEST or any(part in EXCLUDED_DIRS for part in PurePosixPath(path).parts):
            raise ValueError(f"forbidden snapshot manifest path: {path}")
        if path in declared:
            raise ValueError(f"duplicate snapshot manifest path: {path}")
        size = item["bytes"]
        sha256 = item["sha256"]
        if not isinstance(size, int) or isinstance(size, bool) or size < 0:
            raise ValueError(f"invalid snapshot byte count: {path}")
        if not isinstance(sha256, str) or len(sha256) != 64 or any(ch not in "0123456789abcdef" for ch in sha256):
            raise ValueError(f"invalid snapshot sha256: {path}")
        declared[path] = item
    actual = {info.filename: info for info in payload}
    if set(declared) != set(actual):
        raise ValueError("snapshot manifest file set does not match archive payload")
    if manifest["file_count"] != len(declared):
        raise ValueError("snapshot manifest file count mismatch")
    if manifest["content_bytes"] != sum(item["bytes"] for item in declared.values()):
        raise ValueError("snapshot manifest content byte count mismatch")
    for path, item in declared.items():
        info = actual[path]
        if info.file_size != item["bytes"]:
            raise ValueError(f"snapshot byte count mismatch: {path}")
        observed = hashlib.sha256(archive.read(info)).hexdigest()
        if observed != item["sha256"]:
            raise ValueError(f"snapshot sha256 mismatch: {path}")
    return {
        "valid": True,
        "schema": SNAPSHOT_SCHEMA,
        "integrity": "manifest-sha256",
        "day": manifest["day"],
        "file_count": manifest["file_count"],
        "content_bytes": manifest["content_bytes"],
        "manifest_sha256": hashlib.sha256(raw).hexdigest(),
    }


def _verify_archive(archive: zipfile.ZipFile) -> dict[str, Any]:
    payload = _validate_archive(archive)
    names = {info.filename for info in archive.infolist()}
    if SNAPSHOT_MANIFEST in names:
        return _verify_manifest(archive, payload)
    return {
        "valid": True,
        "schema": "legacy-zip",
        "integrity": "zip-crc-only",
        "day": None,
        "file_count": len(payload),
        "content_bytes": sum(info.file_size for info in payload),
        "manifest_sha256": None,
    }


def verify_snapshot(snapshot: Path) -> dict[str, Any]:
    snapshot = Path(snapshot).resolve()
    try:
        with zipfile.ZipFile(snapshot, "r") as archive:
            result = _verify_archive(archive)
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid snapshot archive") from exc
    return {**result, "snapshot": str(snapshot)}


def restore_snapshot(root: Path, snapshot: Path, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise ValueError("restore requires explicit confirm=True")
    root = Path(root).resolve()
    snapshot = Path(snapshot).resolve()
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    quarantine = root.parent / f"{root.name}.quarantine-{stamp}"

    try:
        with zipfile.ZipFile(snapshot, "r") as archive:
            verification = _verify_archive(archive)
            quarantine.mkdir(parents=True, exist_ok=False)

            # Move the current body aside while preserving .git in place. This is recovery,
            # not a merge-back workflow. Archive verification is complete before mutation.
            for child in list(root.iterdir()):
                if child.name == ".git":
                    continue
                shutil.move(str(child), str(quarantine / child.name))

            try:
                for info in archive.infolist():
                    if info.filename == SNAPSHOT_MANIFEST:
                        continue
                    archive.extract(info, root)
            except Exception:
                # A failed extraction returns the moved body to its original location.
                for child in list(root.iterdir()):
                    if child.name == ".git":
                        continue
                    if child.is_dir():
                        shutil.rmtree(child)
                    else:
                        child.unlink()
                for child in list(quarantine.iterdir()):
                    shutil.move(str(child), str(root / child.name))
                quarantine.rmdir()
                raise
    except zipfile.BadZipFile as exc:
        raise ValueError("invalid snapshot archive") from exc
    return {
        "restored": True,
        "snapshot": str(snapshot),
        "quarantine": str(quarantine),
        "verification": verification,
    }

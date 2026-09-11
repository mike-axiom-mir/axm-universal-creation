from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import stat
import subprocess
import tempfile
from typing import Any
import zipfile


MANIFEST_SCHEMA = "axm.universal-creation.portable-runtime/v0.1"
RECEIPT_SCHEMA = "axm.universal-creation.portable-runtime-receipt/v0.1"
RUNTIME_VERSION = "0.1.0"
MANIFEST_PATH = "portable-runtime.manifest.json"
LAUNCHER_PATH = "run.py"
SOURCE_REPOSITORY = "mike-axiom-mir/axm-universal-creation"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
MAX_EXPANDED_BYTES = 512 * 1024 * 1024
MAX_ENTRY_BYTES = 128 * 1024 * 1024
MAX_FILES = 5_000

ROOT_FILES = (
    "LICENSE",
    "PORTABLE_RUNTIME.md",
    "README.md",
    "THIRD_PARTY.json",
    "machine.contract.json",
    "pyproject.toml",
    "registry_materialization.json",
)
ROOT_DIRECTORIES = (
    "asset-packages",
    "assets",
    "atoms",
    "capabilities",
    "components",
    "creations",
    "examples",
    "executable-organs",
    "interfaces",
    "organs",
    "reference",
    "src",
    "state",
    "tools",
)
REQUIRED_ENTRIES = frozenset(
    {
        LAUNCHER_PATH,
        "LICENSE",
        "THIRD_PARTY.json",
        "machine.contract.json",
        "registry_materialization.json",
        "src/axm_uc/__main__.py",
        "src/axm_uc/cli.py",
        "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json",
        "reference/AXM_Universal_Creation_Map_v0.1/registry/core_build_seed.json",
    }
)

LAUNCHER = b'''from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.cli import main


if __name__ == "__main__":
    raise SystemExit(main(["--root", str(ROOT), *sys.argv[1:]]))
'''


class PortableRuntimeError(ValueError):
    """A portable runtime could not be built or admitted truthfully."""


def _canonical_bytes(value: Any) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, separators=(",", ":"), sort_keys=True)
        + "\n"
    ).encode("utf-8")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _file_record(path: str, data: bytes, mode: int) -> dict[str, Any]:
    return {"path": path, "sha256": _sha256(data), "size": len(data), "mode": mode}


def _safe_archive_path(value: Any) -> str:
    if not isinstance(value, str) or not value or "\\" in value or "\x00" in value:
        raise PortableRuntimeError("archive paths must be non-empty normalized POSIX paths")
    path = PurePosixPath(value)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise PortableRuntimeError(f"unsafe archive path: {value!r}")
    normalized = path.as_posix()
    if normalized != value:
        raise PortableRuntimeError(f"non-canonical archive path: {value!r}")
    return normalized


def _strict_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise PortableRuntimeError(f"duplicate manifest key: {key}")
        result[key] = value
    return result


def _reject_constant(value: str) -> None:
    raise PortableRuntimeError(f"non-finite manifest number: {value}")


def _load_manifest(data: bytes) -> dict[str, Any]:
    try:
        value = json.loads(
            data.decode("utf-8"),
            object_pairs_hook=_strict_object,
            parse_constant=_reject_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PortableRuntimeError("portable manifest is not strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise PortableRuntimeError("portable manifest must be an object")
    return value


def _source_revision(root: Path, declared: str | None) -> tuple[str, str]:
    if declared is not None:
        if not declared or len(declared) > 200 or any(ord(char) < 32 for char in declared):
            raise PortableRuntimeError("source revision must be a non-empty printable string of at most 200 characters")
        return declared, "declared"
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        )
    except (FileNotFoundError, subprocess.SubprocessError):
        return "unavailable", "unavailable"
    revision = completed.stdout.strip()
    if len(revision) != 40 or any(char not in "0123456789abcdef" for char in revision):
        return "unavailable", "unavailable"
    return revision, "git-head-observation"


def _tracked_runtime_paths(root: Path) -> list[str]:
    try:
        completed = subprocess.run(
            ["git", "ls-files", "-z", "--", *ROOT_FILES, *ROOT_DIRECTORIES],
            cwd=root,
            check=True,
            capture_output=True,
            timeout=30,
        )
    except (FileNotFoundError, subprocess.SubprocessError) as exc:
        raise PortableRuntimeError(
            "portable runtime build requires a Git-tracked source inventory"
        ) from exc
    try:
        paths = completed.stdout.decode("utf-8").split("\x00")
    except UnicodeDecodeError as exc:
        raise PortableRuntimeError("Git-tracked runtime paths must be UTF-8") from exc
    normalized = sorted(_safe_archive_path(path) for path in paths if path)
    if not normalized or len(normalized) != len(set(normalized)):
        raise PortableRuntimeError("Git-tracked runtime inventory is empty or ambiguous")
    missing_roots = [relative for relative in ROOT_FILES if relative not in normalized]
    if missing_roots:
        raise PortableRuntimeError(
            "required portable runtime source is not Git-tracked: "
            + ", ".join(missing_roots)
        )
    return normalized


def _collect_runtime(root: Path) -> dict[str, tuple[bytes, int]]:
    root = root.resolve()
    files: dict[str, tuple[bytes, int]] = {}

    def add(path: Path) -> None:
        if path.is_symlink():
            raise PortableRuntimeError(f"portable runtime refuses symlink: {path.relative_to(root).as_posix()}")
        if not path.is_file():
            raise PortableRuntimeError(f"portable runtime expected regular file: {path.relative_to(root).as_posix()}")
        relative = _safe_archive_path(path.relative_to(root).as_posix())
        if relative in files:
            raise PortableRuntimeError(f"duplicate portable runtime path: {relative}")
        data = path.read_bytes()
        if len(data) > MAX_ENTRY_BYTES:
            raise PortableRuntimeError(f"portable runtime file exceeds limit: {relative}")
        files[relative] = (data, 0o644)

    for relative in _tracked_runtime_paths(root):
        add(root / relative)
    files[LAUNCHER_PATH] = (LAUNCHER, 0o755)
    if len(files) > MAX_FILES:
        raise PortableRuntimeError(f"portable runtime exceeds {MAX_FILES} files")
    total = sum(len(data) for data, _mode in files.values())
    if total > MAX_EXPANDED_BYTES:
        raise PortableRuntimeError(f"portable runtime exceeds {MAX_EXPANDED_BYTES} expanded bytes")
    missing = sorted(REQUIRED_ENTRIES - set(files))
    if missing:
        raise PortableRuntimeError("portable runtime is missing required entry: " + ", ".join(missing))
    return files


def _zip_info(path: str, mode: int) -> zipfile.ZipInfo:
    info = zipfile.ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
    info.compress_type = zipfile.ZIP_STORED
    info.create_system = 3
    info.external_attr = mode << 16
    info.flag_bits = 0x800
    return info


def build_portable_runtime(
    root: str | Path,
    output: str | Path,
    *,
    source_revision: str | None = None,
) -> dict[str, Any]:
    root_path = Path(root).resolve()
    if not (root_path / "machine.contract.json").is_file():
        raise PortableRuntimeError("machine root does not contain machine.contract.json")
    files = _collect_runtime(root_path)
    records = [
        _file_record(path, data, mode)
        for path, (data, mode) in sorted(files.items())
    ]
    content_digest = _sha256(_canonical_bytes(records))
    revision, revision_kind = _source_revision(root_path, source_revision)
    third_party_hash = _sha256(files["THIRD_PARTY.json"][0])
    manifest = {
        "schema": MANIFEST_SCHEMA,
        "runtimeVersion": RUNTIME_VERSION,
        "source": {
            "repository": SOURCE_REPOSITORY,
            "revision": revision,
            "revisionKind": revision_kind,
            "contentDigest": content_digest,
            "licenseFile": "LICENSE",
            "thirdPartyLedger": {
                "path": "THIRD_PARTY.json",
                "sha256": third_party_hash,
            },
        },
        "entrypoint": {
            "command": "python run.py <command>",
            "path": LAUNCHER_PATH,
            "minimumPython": "3.11",
        },
        "files": records,
        "contentDigest": content_digest,
        "fileCount": len(records),
        "expandedBytes": sum(record["size"] for record in records),
        "container": {
            "format": "zip",
            "compression": "stored",
            "fixedTimestamp": "1980-01-01T00:00:00Z",
            "inventory": "git-tracked-runtime-allowlist/v0.1",
        },
        "authority": {
            "adoptsCandidate": False,
            "changesSourceMachine": False,
            "declaresCanon": False,
        },
    }
    manifest_bytes = _canonical_bytes(manifest)
    output_path = Path(output).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            prefix=f".{output_path.name}.", suffix=".tmp", dir=output_path.parent, delete=False
        ) as handle:
            temporary = Path(handle.name)
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_STORED, allowZip64=True) as archive:
            for path, (data, mode) in sorted(files.items()):
                archive.writestr(_zip_info(path, mode), data)
            archive.writestr(_zip_info(MANIFEST_PATH, 0o644), manifest_bytes)
        os.replace(temporary, output_path)
        output_path.chmod(0o644)
        temporary = None
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    receipt = verify_portable_runtime(output_path)
    receipt["sourceRevision"] = revision
    receipt["output"] = str(output_path)
    return receipt


def verify_portable_runtime(
    archive_path: str | Path,
    *,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    path = Path(archive_path).resolve()
    if not path.is_file() or path.is_symlink():
        raise PortableRuntimeError("portable runtime archive must be a regular file")
    archive_bytes = path.read_bytes()
    if len(archive_bytes) > MAX_ARCHIVE_BYTES:
        raise PortableRuntimeError(f"portable runtime archive exceeds {MAX_ARCHIVE_BYTES} bytes")
    archive_hash = _sha256(archive_bytes)
    if expected_sha256 is not None and archive_hash != expected_sha256:
        raise PortableRuntimeError("portable runtime archive SHA-256 does not match the pinned value")

    try:
        archive = zipfile.ZipFile(path, "r")
    except zipfile.BadZipFile as exc:
        raise PortableRuntimeError("portable runtime is not a valid ZIP archive") from exc
    with archive:
        infos = archive.infolist()
        if not infos or len(infos) > MAX_FILES + 1:
            raise PortableRuntimeError("portable runtime file count is outside the supported limit")
        names: set[str] = set()
        expanded = 0
        for info in infos:
            name = _safe_archive_path(info.filename)
            if name in names:
                raise PortableRuntimeError(f"duplicate archive entry: {name}")
            names.add(name)
            if info.is_dir():
                raise PortableRuntimeError(f"directory entries are not permitted: {name}")
            unix_mode = (info.external_attr >> 16) & 0xFFFF
            if stat.S_IFMT(unix_mode) == stat.S_IFLNK:
                raise PortableRuntimeError(f"symlink archive entry is not permitted: {name}")
            if info.compress_type != zipfile.ZIP_STORED:
                raise PortableRuntimeError(f"unexpected compression method: {name}")
            if info.date_time != (1980, 1, 1, 0, 0, 0):
                raise PortableRuntimeError(f"unexpected archive timestamp: {name}")
            if info.file_size > MAX_ENTRY_BYTES:
                raise PortableRuntimeError(f"archive entry exceeds limit: {name}")
            expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise PortableRuntimeError("portable runtime expanded size exceeds limit")
        if MANIFEST_PATH not in names:
            raise PortableRuntimeError("portable runtime manifest is missing")
        manifest = _load_manifest(archive.read(MANIFEST_PATH))
        required_manifest_keys = {
            "schema",
            "runtimeVersion",
            "source",
            "entrypoint",
            "files",
            "contentDigest",
            "fileCount",
            "expandedBytes",
            "container",
            "authority",
        }
        if set(manifest) != required_manifest_keys:
            raise PortableRuntimeError("portable runtime manifest shape is not exact")
        if manifest["schema"] != MANIFEST_SCHEMA or manifest["runtimeVersion"] != RUNTIME_VERSION:
            raise PortableRuntimeError("portable runtime schema or version is unsupported")
        records = manifest["files"]
        if (
            not isinstance(records, list)
            or not isinstance(manifest["fileCount"], int)
            or isinstance(manifest["fileCount"], bool)
            or manifest["fileCount"] != len(records)
        ):
            raise PortableRuntimeError("portable runtime manifest file count is inconsistent")
        declared: set[str] = set()
        verified_records: list[dict[str, Any]] = []
        verified_bytes = 0
        for index, record in enumerate(records):
            if not isinstance(record, dict) or set(record) != {"path", "sha256", "size", "mode"}:
                raise PortableRuntimeError(f"portable runtime file record {index} is not exact")
            name = _safe_archive_path(record["path"])
            if name == MANIFEST_PATH or name in declared:
                raise PortableRuntimeError(f"duplicate or reserved manifest path: {name}")
            declared.add(name)
            if name not in names:
                raise PortableRuntimeError(f"portable runtime inventory is missing declared path: {name}")
            if not isinstance(record["size"], int) or isinstance(record["size"], bool) or record["size"] < 0:
                raise PortableRuntimeError(f"invalid declared size: {name}")
            if record["mode"] not in {0o644, 0o755}:
                raise PortableRuntimeError(f"invalid declared mode: {name}")
            digest = record["sha256"]
            if not isinstance(digest, str) or len(digest) != 64 or any(char not in "0123456789abcdef" for char in digest):
                raise PortableRuntimeError(f"invalid declared SHA-256: {name}")
            info = archive.getinfo(name)
            data = archive.read(name)
            mode = (info.external_attr >> 16) & 0o777
            if len(data) != record["size"] or _sha256(data) != digest or mode != record["mode"]:
                raise PortableRuntimeError(f"portable runtime content mismatch: {name}")
            verified_records.append(record)
            verified_bytes += len(data)
        if [record["path"] for record in verified_records] != sorted(declared):
            raise PortableRuntimeError("portable runtime file records are not canonically ordered")
        if names != declared | {MANIFEST_PATH}:
            raise PortableRuntimeError("portable runtime inventory does not match its manifest")
        if not REQUIRED_ENTRIES.issubset(declared):
            raise PortableRuntimeError("portable runtime required entry is missing")
        if (
            not isinstance(manifest["expandedBytes"], int)
            or isinstance(manifest["expandedBytes"], bool)
            or manifest["expandedBytes"] != verified_bytes
        ):
            raise PortableRuntimeError("portable runtime expanded byte count is inconsistent")
        content_digest = _sha256(_canonical_bytes(verified_records))
        if manifest["contentDigest"] != content_digest:
            raise PortableRuntimeError("portable runtime content digest is inconsistent")
        source = manifest["source"]
        if not isinstance(source, dict) or set(source) != {
            "repository",
            "revision",
            "revisionKind",
            "contentDigest",
            "licenseFile",
            "thirdPartyLedger",
        }:
            raise PortableRuntimeError("portable runtime source lineage shape is not exact")
        if source.get("repository") != SOURCE_REPOSITORY:
            raise PortableRuntimeError("portable runtime source repository is unsupported")
        revision = source.get("revision")
        if (
            not isinstance(revision, str)
            or not revision
            or len(revision) > 200
            or any(ord(char) < 32 for char in revision)
        ):
            raise PortableRuntimeError("portable runtime source revision is invalid")
        if source.get("revisionKind") not in {
            "declared",
            "git-head-observation",
            "unavailable",
        }:
            raise PortableRuntimeError("portable runtime source revision kind is unsupported")
        if source.get("contentDigest") != content_digest:
            raise PortableRuntimeError("portable runtime source lineage is not bound to its content")
        if source.get("licenseFile") != "LICENSE":
            raise PortableRuntimeError("portable runtime license path is not exact")
        ledger = source.get("thirdPartyLedger")
        record_by_path = {record["path"]: record for record in verified_records}
        if ledger != {
            "path": "THIRD_PARTY.json",
            "sha256": record_by_path["THIRD_PARTY.json"]["sha256"],
        }:
            raise PortableRuntimeError("portable runtime third-party lineage is not exact")
        entrypoint = manifest["entrypoint"]
        if entrypoint != {
            "command": "python run.py <command>",
            "path": LAUNCHER_PATH,
            "minimumPython": "3.11",
        }:
            raise PortableRuntimeError("portable runtime entrypoint is not supported")
        if manifest["container"] != {
            "format": "zip",
            "compression": "stored",
            "fixedTimestamp": "1980-01-01T00:00:00Z",
            "inventory": "git-tracked-runtime-allowlist/v0.1",
        }:
            raise PortableRuntimeError("portable runtime container contract is not exact")
        authority = manifest["authority"]
        if authority != {
            "adoptsCandidate": False,
            "changesSourceMachine": False,
            "declaresCanon": False,
        }:
            raise PortableRuntimeError("portable runtime authority boundary is not exact")
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "PASS",
        "archiveSha256": archive_hash,
        "contentDigest": content_digest,
        "fileCount": len(verified_records),
        "expandedBytes": verified_bytes,
        "entrypoint": "python run.py <command>",
        "source": manifest["source"],
        "authority": manifest["authority"],
    }

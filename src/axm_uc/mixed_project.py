from __future__ import annotations

import base64
import binascii
import hashlib
import shutil
import uuid
from pathlib import Path, PurePosixPath
from typing import Any

from .project import (
    PUBLISH_MODES,
    ProjectError,
    _begin_publish,
    _file_manifest,
    _grounding,
    _publication_integrity,
    _rollback_publish,
    _safe_relative_path,
    validate_project,
)


MAX_FILES = 256
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_PROJECT_BYTES = 64 * 1024 * 1024


def mixed_project_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_BOUNDED_MIXED_PROJECT_CREATION",
        "handles": ["mixed-media-project", "asset-project", "binary-asset-project", "game-asset-project"],
        "text_encoding": "utf-8",
        "binary_input_encoding": "strict-base64",
        "maximum_files": MAX_FILES,
        "maximum_file_bytes": MAX_FILE_BYTES,
        "maximum_project_bytes": MAX_PROJECT_BYTES,
        "all_file_digests_reverified_after_publish": True,
        "runtime_or_semantic_behavior_proven": False,
    }


def _sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _normalize_text_files(raw: Any) -> tuple[dict[str, str], dict[str, bytes]]:
    if raw is None:
        return {}, {}
    if not isinstance(raw, dict):
        raise ProjectError("text_files must be an object mapping relative paths to UTF-8 text")
    text: dict[str, str] = {}
    encoded: dict[str, bytes] = {}
    for raw_path, content in raw.items():
        path = _safe_relative_path(str(raw_path)).as_posix()
        if path in encoded:
            raise ProjectError(f"duplicate mixed-project path: {path}")
        if not isinstance(content, str):
            raise ProjectError(f"mixed-project text content must be a string: {path}")
        body = content.encode("utf-8")
        if len(body) > MAX_FILE_BYTES:
            raise ProjectError(f"mixed-project file exceeds {MAX_FILE_BYTES} bytes: {path}")
        text[path] = content
        encoded[path] = body
    return text, encoded


def _normalize_binary_files(raw: Any, occupied: set[str]) -> tuple[dict[str, bytes], list[dict[str, Any]]]:
    if raw is None:
        return {}, []
    if not isinstance(raw, dict):
        raise ProjectError("binary_files must be an object mapping relative paths to binary descriptors")
    decoded: dict[str, bytes] = {}
    receipts: list[dict[str, Any]] = []
    for raw_path, descriptor in raw.items():
        path = _safe_relative_path(str(raw_path)).as_posix()
        if path in occupied or path in decoded:
            raise ProjectError(f"duplicate mixed-project path: {path}")
        if not isinstance(descriptor, dict):
            raise ProjectError(f"binary descriptor must be an object: {path}")
        unexpected = sorted(set(descriptor) - {"encoding", "content", "media_type", "sha256"})
        if unexpected:
            raise ProjectError(
                f"binary descriptor contains unsupported fields: {path}",
                {"path": path, "unexpected_fields": unexpected},
            )
        if descriptor.get("encoding") != "base64":
            raise ProjectError(f"binary descriptor encoding must be base64: {path}")
        content = descriptor.get("content")
        if not isinstance(content, str):
            raise ProjectError(f"binary descriptor content must be base64 text: {path}")
        if len(content) > ((MAX_FILE_BYTES + 2) // 3) * 4:
            raise ProjectError(f"mixed-project file exceeds {MAX_FILE_BYTES} decoded bytes: {path}")
        try:
            body = base64.b64decode(content.encode("ascii"), validate=True)
        except (UnicodeEncodeError, binascii.Error) as exc:
            raise ProjectError(f"binary descriptor is not strict base64: {path}") from exc
        if len(body) > MAX_FILE_BYTES:
            raise ProjectError(f"mixed-project file exceeds {MAX_FILE_BYTES} decoded bytes: {path}")
        declared_sha = descriptor.get("sha256")
        digest = _sha256(body)
        if declared_sha is not None:
            if not isinstance(declared_sha, str) or declared_sha != digest:
                raise ProjectError(
                    f"binary descriptor SHA-256 does not match decoded bytes: {path}",
                    {"path": path, "declared_sha256": declared_sha, "observed_sha256": digest},
                )
        media_type = descriptor.get("media_type")
        if media_type is not None and (not isinstance(media_type, str) or not media_type.strip()):
            raise ProjectError(f"binary descriptor media_type must be non-empty text when supplied: {path}")
        decoded[path] = body
        receipts.append(
            {
                "path": path,
                "bytes": len(body),
                "sha256": digest,
                "declared_media_type": media_type.strip() if isinstance(media_type, str) else None,
                "media_type_verified": False,
            }
        )
    return decoded, receipts


def preview_mixed_project(
    text_files: Any,
    binary_files: Any,
    project_type: Any = "generic",
) -> dict[str, Any]:
    text, text_bytes = _normalize_text_files(text_files)
    binary, binary_receipts = _normalize_binary_files(binary_files, set(text_bytes))
    files = {**text_bytes, **binary}
    if not files:
        raise ProjectError("a mixed project requires at least one text_files or binary_files entry")
    if len(files) > MAX_FILES:
        raise ProjectError(f"mixed project exceeds the {MAX_FILES}-file boundary")
    total_bytes = sum(len(content) for content in files.values())
    if total_bytes > MAX_PROJECT_BYTES:
        raise ProjectError(f"mixed project exceeds the {MAX_PROJECT_BYTES}-byte boundary")
    return {
        "project_type": str(project_type or "generic").strip().casefold(),
        "text_files": text,
        "files": files,
        "expected_file_digests": {path: _sha256(content) for path, content in files.items()},
        "binary_receipts": binary_receipts,
        "total_bytes": total_bytes,
    }


def build_mixed_project(
    target: Path,
    *,
    text_files: Any = None,
    binary_files: Any = None,
    project_type: str = "generic",
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
    publish_mode: str = "validated",
) -> dict[str, Any]:
    target = Path(target).resolve()
    publish_mode = str(publish_mode).strip().casefold()
    if publish_mode not in PUBLISH_MODES:
        raise ProjectError("publish_mode must be validated or grounded-draft")
    preview = preview_mixed_project(text_files, binary_files, project_type)
    expected_text = preview["text_files"] or None
    expected_digests = preview["expected_file_digests"]

    target.parent.mkdir(parents=True, exist_ok=True)
    stage = target.with_name(f".{target.name}.axm-build-{uuid.uuid4().hex}")
    if stage.exists():
        raise ProjectError(f"unexpected staging collision: {stage}")
    stage.mkdir(parents=False)

    backup: Path | None = None
    published = False
    try:
        for raw_path, content in preview["files"].items():
            rel = PurePosixPath(raw_path)
            path = stage.joinpath(*rel.parts)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        validation = validate_project(
            stage,
            project_type=preview["project_type"],
            checks=checks,
            expected_files=expected_text,
            expected_file_digests=expected_digests,
        )
        if not _publication_integrity(validation):
            raise ProjectError(
                "mixed-project publication integrity failed before publish",
                {"phase": "pre-publish", "validation": validation},
            )
        if publish_mode == "validated" and not validation["passed"]:
            raise ProjectError(
                "mixed-project validation failed before publish",
                {"phase": "pre-publish", "validation": validation},
            )

        backup = _begin_publish(stage, target, replace=replace)
        published = True
        published_validation = validate_project(
            target,
            project_type=preview["project_type"],
            checks=checks,
            expected_files=expected_text,
            expected_file_digests=expected_digests,
        )
        if not _publication_integrity(published_validation) or (
            publish_mode == "validated" and not published_validation["passed"]
        ):
            _rollback_publish(target, backup)
            published = False
            raise ProjectError(
                "mixed-project validation failed after publish; previous body restored",
                {"phase": "post-publish", "validation": published_validation, "rolled_back": True},
            )
        if backup is not None and backup.exists():
            shutil.rmtree(backup)
        return {
            "path": str(target),
            "project_type": preview["project_type"],
            "published": True,
            "publish_mode": publish_mode,
            "creation_status": "VALIDATED_CREATION" if published_validation["passed"] else "GROUNDED_DRAFT",
            "files": _file_manifest(target),
            "binary_receipts": preview["binary_receipts"],
            "validation": published_validation,
            "grounding": _grounding(published_validation, publish_mode),
            "limits": {
                "maximum_files": MAX_FILES,
                "maximum_file_bytes": MAX_FILE_BYTES,
                "maximum_project_bytes": MAX_PROJECT_BYTES,
            },
        }
    except Exception:
        if published and target.exists():
            _rollback_publish(target, backup)
        raise
    finally:
        if stage.exists():
            shutil.rmtree(stage, ignore_errors=True)

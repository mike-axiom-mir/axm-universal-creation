from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json

EXCLUDED_PARTS = {".git", "creations", ".axm-build", "__pycache__", ".pytest_cache", "snapshots"}
EXCLUDED_FILES = {"state/integrity.json"}


def _included(root: Path, path: Path) -> bool:
    rel = path.relative_to(root)
    rel_text = rel.as_posix()
    if rel_text in EXCLUDED_FILES:
        return False
    if any(part in EXCLUDED_PARTS for part in rel.parts):
        return False
    if any(part.endswith(".pyc") for part in rel.parts):
        return False
    if rel.parts[:2] == ("capabilities", "candidates"):
        return False
    return path.is_file()


def compute_manifest(root: Path) -> dict[str, Any]:
    root = Path(root)
    files: dict[str, Any] = {}
    body = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if _included(root, p)):
        data = path.read_bytes()
        digest = hashlib.sha256(data).hexdigest()
        rel = path.relative_to(root).as_posix()
        files[rel] = {"sha256": digest, "bytes": len(data)}
        body.update(rel.encode("utf-8"))
        body.update(b"\0")
        body.update(digest.encode("ascii"))
        body.update(b"\n")
    return {
        "algorithm": "sha256",
        "meaning": "current-body integrity baseline; state diagnosis, not participant trust",
        "body_sha256": body.hexdigest(),
        "files": files,
    }


def refresh(root: Path) -> dict[str, Any]:
    manifest = compute_manifest(root)
    atomic_write_json(Path(root) / "state/integrity.json", manifest)
    return manifest


def verify(root: Path) -> dict[str, Any]:
    baseline_path = Path(root) / "state/integrity.json"
    current = compute_manifest(root)
    if not baseline_path.exists():
        return {"status": "missing-baseline", "current": current, "blocks_creation": False}
    baseline = json.loads(baseline_path.read_text(encoding="utf-8"))
    old = baseline.get("files", {})
    new = current.get("files", {})
    added = sorted(set(new) - set(old))
    missing = sorted(set(old) - set(new))
    changed = sorted(k for k in set(old) & set(new) if old[k].get("sha256") != new[k].get("sha256"))
    status = "clean" if not (added or missing or changed) else "changed"
    return {
        "status": status,
        "blocks_creation": False,
        "body_sha256": current["body_sha256"],
        "baseline_body_sha256": baseline.get("body_sha256"),
        "added": added,
        "missing": missing,
        "changed": changed,
    }

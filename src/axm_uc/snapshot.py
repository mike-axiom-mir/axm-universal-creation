from __future__ import annotations

import datetime as dt
import os
import shutil
import zipfile
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .integrity import refresh as refresh_integrity

EXCLUDED_DIRS = {".git", "__pycache__", ".pytest_cache", ".axm-build", "snapshots"}


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
        with zipfile.ZipFile(temp, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for path, rel in _iter_snapshot_files(root):
                archive.write(path, rel.as_posix())
        os.replace(temp, target)
    finally:
        if temp.exists():
            temp.unlink()
    return {"created": True, "path": str(target), "bytes": target.stat().st_size}


def _validate_archive(archive: zipfile.ZipFile) -> None:
    for info in archive.infolist():
        path = Path(info.filename)
        if path.is_absolute() or ".." in path.parts:
            raise ValueError(f"unsafe snapshot path: {info.filename}")


def restore_snapshot(root: Path, snapshot: Path, confirm: bool = False) -> dict[str, Any]:
    if not confirm:
        raise ValueError("restore requires explicit confirm=True")
    root = Path(root).resolve()
    snapshot = Path(snapshot).resolve()
    stamp = dt.datetime.now().strftime("%Y%m%dT%H%M%S")
    quarantine = root.parent / f"{root.name}.quarantine-{stamp}"
    quarantine.mkdir(parents=True, exist_ok=False)

    # Move the current body aside while preserving .git in place. This is recovery,
    # not a merge-back workflow.
    for child in list(root.iterdir()):
        if child.name == ".git":
            continue
        shutil.move(str(child), str(quarantine / child.name))

    try:
        with zipfile.ZipFile(snapshot, "r") as archive:
            _validate_archive(archive)
            archive.extractall(root)
        refresh_integrity(root)
    except Exception:
        # A failed restore returns the moved body to its original location.
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
    return {"restored": True, "snapshot": str(snapshot), "quarantine": str(quarantine)}

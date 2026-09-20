from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .atomic import atomic_write_bytes, atomic_write_json
from .procedural_3d import Procedural3DError, publish_glb


SOURCE_SCHEMA = "axm.creator-source/v1"


class CreatorRetentionError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise CreatorRetentionError("creator source must be finite JSON data") from exc


def source_sidecar_path(target: str | Path) -> Path:
    target = Path(target).resolve()
    return target.with_suffix(target.suffix + ".source.json")


def creator_source_summary() -> dict[str, Any]:
    return {
        "schema": SOURCE_SCHEMA,
        "truth_status": "SOURCE_AUTHORITY_RETAINED_BESIDE_REALIZATION",
        "default_for": [
            "procedural-3d publication through the UC live capability",
            "shape-recipe publication",
            "form-pattern publication",
            "character-recipe publication",
        ],
        "realization_is_source_authority": False,
        "automatic_canon_admission": False,
        "truth_boundary": (
            "The sidecar retains the declared construction causes needed to reproduce or reshape "
            "the output. It does not prove visual quality, semantic adequacy, animation, physics, "
            "or target-engine integration."
        ),
    }


def _normalize_source(source: Any) -> dict[str, Any]:
    if not isinstance(source, dict):
        raise CreatorRetentionError("creator source must be an object")
    normalized = deepcopy(source)
    normalized.setdefault("schema", SOURCE_SCHEMA)
    if normalized["schema"] != SOURCE_SCHEMA:
        raise CreatorRetentionError("unsupported creator-source schema")
    normalized.setdefault("source_authority", True)
    normalized.setdefault("realization_is_secondary", True)
    normalized.setdefault("automatic_canon_admission", False)
    normalized.setdefault(
        "truth_boundary",
        "Retained construction state is replay/edit evidence, not automatic aesthetic or runtime acceptance.",
    )
    _canonical(normalized)
    return normalized


def publish_retained_glb(
    target: str | Path,
    specification: Any,
    source: Any,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    """Atomically publish a GLB plus its construction-source sidecar.

    The ordinary GLB remains a realization.  The sidecar is the inspectable source
    authority for replay/editing.  A failed sidecar publication rolls the GLB back
    to the exact prior bytes rather than leaving an output that silently lost its
    construction state.
    """
    target = Path(target).resolve()
    sidecar = source_sidecar_path(target)
    if sidecar.exists() and sidecar.is_dir():
        raise CreatorRetentionError("creator-source sidecar path is an existing directory")
    if sidecar.exists() and not replace:
        raise CreatorRetentionError(
            "creator-source sidecar already exists and replace is false",
            {"sidecar": str(sidecar)},
        )

    normalized = _normalize_source(source)
    previous_asset = target.read_bytes() if target.is_file() else None
    previous_source = sidecar.read_bytes() if sidecar.is_file() else None

    try:
        result = publish_glb(target, specification, replace=replace)
        retained = {
            **normalized,
            "artifact": {
                "path": str(target),
                "sha256": result["sha256"],
                "specification_sha256": result["specification_sha256"],
            },
        }
        retained["source_sha256"] = hashlib.sha256(_canonical({
            key: value for key, value in retained.items() if key != "source_sha256"
        })).hexdigest()
        atomic_write_json(sidecar, retained)
        observed = json.loads(sidecar.read_text(encoding="utf-8"))
        if observed != retained:
            raise CreatorRetentionError("published creator-source sidecar differs from retained source")
    except Exception:
        if previous_asset is None:
            if target.exists() and target.is_file():
                target.unlink()
        else:
            atomic_write_bytes(target, previous_asset)
        if previous_source is None:
            if sidecar.exists() and sidecar.is_file():
                sidecar.unlink()
        else:
            atomic_write_bytes(sidecar, previous_source)
        raise

    result["creator_source"] = {
        "path": str(sidecar),
        "sha256": hashlib.sha256(sidecar.read_bytes()).hexdigest(),
        "source_authority": True,
        "realization_is_secondary": True,
        "schema": SOURCE_SCHEMA,
    }
    return result

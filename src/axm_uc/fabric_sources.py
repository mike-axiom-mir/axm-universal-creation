from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class FabricSourceError(ValueError):
    """Raised when a fabric-source request is structurally invalid."""


@dataclass(frozen=True)
class FabricSource:
    id: str
    repository: str
    kind: str
    preferred_mount: str
    fallback_paths: tuple[str, ...] = ()
    callable_by_default: bool = True
    notes: str = ""


SOURCES: tuple[FabricSource, ...] = (
    FabricSource(
        id="hands-fabric",
        repository="mike-axiom-mir/axm-hands-fabric",
        kind="executable-capability-fabric",
        preferred_mount="fabrics/hands",
        fallback_paths=("capabilities/platform-hands", "capabilities/special-effect-hands"),
        notes=(
            "Preferred shared source for caller-neutral executable Hands. Current UC capsules remain "
            "local donor snapshots until an explicit Hands Fabric mount/package is supplied."
        ),
    ),
    FabricSource(
        id="organ-fabric",
        repository="mike-axiom-mir/axm-organ-fabric",
        kind="internal-organ-fabric",
        preferred_mount="fabrics/organs",
        fallback_paths=("organs", "executable-organs"),
        notes=(
            "Preferred shared source for organ discovery/growth. UC's local descriptive and executable "
            "organ bodies remain valid local fallbacks and retain their separate truth status."
        ),
    ),
    FabricSource(
        id="organ-archive",
        repository="mike-axiom-mir/axm-organ-archive",
        kind="preservation-archive",
        preferred_mount="fabrics/organ-archive",
        callable_by_default=False,
        notes=(
            "Preservation source only. Archived bodies may be inspected or explicitly restored, but archive "
            "presence never makes an organ live, canonical, or executable."
        ),
    ),
    FabricSource(
        id="visual-effect-fabric",
        repository="mike-axiom-mir/axm-visual-effect-fabric",
        kind="specialized-visual-effect-fabric",
        preferred_mount="fabrics/visual-effects",
        fallback_paths=("capabilities/special-effect-hands",),
        notes=(
            "Preferred specialist source for reusable visual-effect machinery. The local special-effect Hands "
            "capsule is a pinned donor proof, not a transparent mirror of the whole Fabric."
        ),
    ),
)


def _source_map() -> dict[str, FabricSource]:
    return {source.id: source for source in SOURCES}


def _resolve_path(root: Path, value: str) -> Path:
    text = str(value).strip()
    if not text:
        raise FabricSourceError("fabric source path must be non-empty text")
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = root / path
    return path.resolve()


def inspect_fabric_sources(
    root: Path,
    *,
    overrides: Mapping[str, str] | None = None,
    source_id: str | None = None,
) -> dict[str, Any]:
    """Inspect preferred shared fabrics without performing network access.

    An explicit override is authoritative for that source. If it is missing on disk,
    the resolver reports that fact rather than silently falling back to another body.
    Without an override, an explicit local mount is preferred, then declared local
    donor fallbacks are reported. No path selection grants CANON, permission, or
    publication authority.
    """

    root = Path(root).resolve()
    source_by_id = _source_map()
    override_map = dict(overrides or {})
    unknown = sorted(set(override_map) - set(source_by_id))
    if unknown:
        raise FabricSourceError(f"unknown fabric source override(s): {', '.join(unknown)}")

    selected: tuple[FabricSource, ...]
    if source_id is None:
        selected = SOURCES
    else:
        normalized = str(source_id).strip()
        if normalized not in source_by_id:
            raise FabricSourceError(f"unknown fabric source: {normalized or '<empty>'}")
        selected = (source_by_id[normalized],)

    records: list[dict[str, Any]] = []
    for source in selected:
        explicit = source.id in override_map
        preferred = _resolve_path(root, override_map[source.id]) if explicit else (root / source.preferred_mount).resolve()
        preferred_exists = preferred.exists()

        fallback_rows: list[dict[str, Any]] = []
        if not explicit:
            for rel in source.fallback_paths:
                path = (root / rel).resolve()
                fallback_rows.append(
                    {
                        "path": str(path),
                        "relative_path": rel,
                        "exists": path.exists(),
                        "kind": "local-donor-fallback",
                    }
                )

        existing_fallbacks = [row for row in fallback_rows if row["exists"]]
        if explicit and not preferred_exists:
            status = "EXPLICIT_SOURCE_MISSING"
            active_paths: list[str] = []
        elif preferred_exists:
            status = "PREFERRED_LOCAL_SOURCE_AVAILABLE"
            active_paths = [str(preferred)]
        elif existing_fallbacks:
            status = "LOCAL_FALLBACK_AVAILABLE"
            active_paths = [row["path"] for row in existing_fallbacks]
        else:
            status = "DECLARED_SOURCE_NOT_MOUNTED"
            active_paths = []

        records.append(
            {
                "id": source.id,
                "repository": source.repository,
                "kind": source.kind,
                "status": status,
                "callable_by_default": source.callable_by_default,
                "preferred_path": str(preferred),
                "preferred_path_exists": preferred_exists,
                "explicit_override": explicit,
                "active_local_paths": active_paths,
                "fallbacks": fallback_rows,
                "notes": source.notes,
                "network_fetch_performed": False,
                "authority_change": False,
            }
        )

    return {
        "schema": "axm.fabric-source-resolution/v1",
        "truth_status": "OBSERVED_LOCAL_FABRIC_SOURCE_AVAILABILITY",
        "root": str(root),
        "source_count": len(records),
        "sources": records,
        "network_fetch_performed": False,
        "authority_change": False,
    }

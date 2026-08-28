from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable


class Registry:
    def __init__(self, root: Path):
        self.root = Path(root)
        self.master_path = self.root / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json"
        self.core_path = self.root / "reference/AXM_Universal_Creation_Map_v0.1/registry/core_build_seed.json"

    @staticmethod
    def _records(path: Path) -> list[dict[str, Any]]:
        data = json.loads(path.read_text(encoding="utf-8"))
        records = data.get("records")
        if not isinstance(records, list):
            raise ValueError(f"Registry has no records list: {path}")
        return records

    def master_records(self) -> list[dict[str, Any]]:
        return self._records(self.master_path)

    def core_records(self) -> list[dict[str, Any]]:
        return self._records(self.core_path)

    def capability_manifests(self, include_candidates: bool = False) -> list[dict[str, Any]]:
        folders = [self.root / "capabilities/live"]
        if include_candidates:
            folders.append(self.root / "capabilities/candidates")
        result: list[dict[str, Any]] = []
        for folder in folders:
            if not folder.exists():
                continue
            for path in sorted(folder.glob("*.json")):
                item = json.loads(path.read_text(encoding="utf-8"))
                item["_manifest_path"] = str(path.relative_to(self.root))
                result.append(item)
        return result

    def summary(self) -> dict[str, Any]:
        master = self.master_records()
        core = self.core_records()
        counts: dict[str, int] = {}
        for record in master:
            level = str(record.get("level", "unknown"))
            counts[level] = counts.get(level, 0) + 1
        return {
            "master_candidates": len(master),
            "master_by_level": counts,
            "implementation_kernel_records": len(core),
            "live_capabilities": len(self.capability_manifests()),
            "candidate_capabilities": len(self.capability_manifests(include_candidates=True)) - len(self.capability_manifests()),
            "master_source": str(self.master_path.relative_to(self.root)),
            "core_source": str(self.core_path.relative_to(self.root)),
        }

    def search(self, query: str = "", level: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        q = query.strip().casefold()
        records: Iterable[dict[str, Any]] = self.master_records()
        if level:
            records = (r for r in records if str(r.get("level", "")).casefold() == level.casefold())
        if q:
            records = (
                r for r in records
                if q in " ".join(str(r.get(k, "")) for k in ("id", "name", "definition", "domain", "domain_code")).casefold()
            )
        return list(records)[: max(1, limit)]

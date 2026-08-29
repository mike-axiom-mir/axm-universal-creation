from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MASTER = ROOT / "reference/AXM_Universal_Creation_Map_v0.1/registry/master_registry.json"
LEVEL_DIRS = {
    "atom": ROOT / "atoms",
    "component": ROOT / "components",
    "organ": ROOT / "organs",
}
EXPECTED = {"atom": 1000, "component": 750, "organ": 415}


def load_records() -> list[dict]:
    data = json.loads(MASTER.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list):
        raise ValueError("master_registry.json has no records list")
    return records


def safe_name(record_id: str) -> str:
    if not record_id or any(ch in record_id for ch in "/\\\0"):
        raise ValueError(f"unsafe registry id: {record_id!r}")
    return f"{record_id}.json"


def materialize() -> dict[str, int]:
    records = load_records()
    counts = {key: 0 for key in LEVEL_DIRS}

    for folder in LEVEL_DIRS.values():
        folder.mkdir(parents=True, exist_ok=True)
        for path in folder.glob("*.json"):
            path.unlink()
        keep = folder / ".gitkeep"
        if keep.exists():
            keep.unlink()

    seen: set[str] = set()
    for record in records:
        level = str(record.get("level", ""))
        if level not in LEVEL_DIRS:
            raise ValueError(f"unsupported registry level: {level!r}")
        record_id = str(record.get("id", ""))
        if record_id in seen:
            raise ValueError(f"duplicate registry id: {record_id}")
        seen.add(record_id)
        target = LEVEL_DIRS[level] / safe_name(record_id)
        target.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        counts[level] += 1

    if counts != EXPECTED:
        raise AssertionError(f"materialized counts {counts} != {EXPECTED}")

    manifest = {
        "canonical_source": str(MASTER.relative_to(ROOT)),
        "total": len(records),
        "counts": counts,
        "format": "one complete registry record per JSON file",
    }
    (ROOT / "registry_materialization.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    return counts


def verify() -> None:
    records = load_records()
    canonical = {str(record["id"]): record for record in records}
    found: dict[str, dict] = {}

    for level, folder in LEVEL_DIRS.items():
        files = sorted(folder.glob("*.json"))
        if len(files) != EXPECTED[level]:
            raise AssertionError(f"{level}: {len(files)} files != {EXPECTED[level]}")
        for path in files:
            record = json.loads(path.read_text(encoding="utf-8"))
            record_id = str(record.get("id", ""))
            if record.get("level") != level:
                raise AssertionError(f"wrong level in {path}: {record.get('level')}")
            if record_id not in canonical:
                raise AssertionError(f"unknown materialized id: {record_id}")
            if record != canonical[record_id]:
                raise AssertionError(f"materialized record differs from canonical: {record_id}")
            if record_id in found:
                raise AssertionError(f"duplicate materialized id: {record_id}")
            found[record_id] = record

    if set(found) != set(canonical):
        missing = sorted(set(canonical) - set(found))[:10]
        extra = sorted(set(found) - set(canonical))[:10]
        raise AssertionError(f"materialized id mismatch missing={missing} extra={extra}")


if __name__ == "__main__":
    counts = materialize()
    verify()
    print(f"materialized and verified {sum(counts.values())} registry entries: {counts}")

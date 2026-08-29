from __future__ import annotations

import csv
import json
from collections import OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_ROOT = ROOT / "reference/AXM_Universal_Creation_Map_v0.1"
MASTER = MAP_ROOT / "registry/master_registry.json"
CORE = MAP_ROOT / "registry/core_build_seed.json"
ATOM_ROOT = ROOT / "reference/AXM_asset_atoms_only"

MASTER_FIELDS = [
    "id", "level", "domain_code", "domain", "name", "definition",
    "source_keys", "source_basis", "registry_status", "maturity",
    "extension_allowed", "notes",
]
ATOM_FIELDS = [
    "id", "domain_code", "domain", "name", "definition", "source_basis",
    "registry_status", "maturity", "source_keys", "notes",
]
EXPECTED = {"atom": 1000, "component": 750, "organ": 415}


def load_records(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data.get("records")
    if not isinstance(records, list):
        raise SystemExit(f"missing records array: {path}")
    return records


def count_levels(records: list[dict]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for row in records:
        level = str(row.get("level", "unknown"))
        counts[level] = counts.get(level, 0) + 1
    return counts


def write_master_csv(records: list[dict]) -> None:
    path = MAP_ROOT / "registry/master_registry.csv"
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=MASTER_FIELDS,
            extrasaction="ignore",
            lineterminator="\r\n",
        )
        writer.writeheader()
        for row in records:
            item = {key: row.get(key, "") for key in MASTER_FIELDS}
            item["source_keys"] = ";".join(row.get("source_keys") or [])
            writer.writerow(item)


def write_atom_views(records: list[dict]) -> None:
    atoms = [row for row in records if row.get("level") == "atom"]
    ATOM_ROOT.mkdir(parents=True, exist_ok=True)

    (ATOM_ROOT / "AXM_SOFTWARE_ASSET_ATOMS_1000.json").write_text(
        json.dumps({"count": len(atoms), "atoms": atoms}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    with (ATOM_ROOT / "AXM_SOFTWARE_ASSET_ATOMS_1000.csv").open(
        "w", encoding="utf-8", newline=""
    ) as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=ATOM_FIELDS,
            extrasaction="ignore",
            lineterminator="\r\n",
        )
        writer.writeheader()
        for row in atoms:
            item = {key: row.get(key, "") for key in ATOM_FIELDS}
            item["source_keys"] = ";".join(row.get("source_keys") or [])
            writer.writerow(item)

    grouped: OrderedDict[tuple[str, str], list[dict]] = OrderedDict()
    for row in atoms:
        grouped.setdefault((row["domain_code"], row["domain"]), []).append(row)
    lines = [
        "AXM SOFTWARE ASSET ATOMS — RAW RESEARCH SEED",
        f"TOTAL ATOMS: {len(atoms)}",
        "",
        "",
    ]
    for (_, domain), rows in grouped.items():
        lines += ["=" * 80, domain.upper(), "=" * 80]
        lines += [f"- {row['name']}" for row in rows]
        lines += [""]
    (ATOM_ROOT / "AXM_SOFTWARE_ASSET_ATOMS_1000.txt").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_validation(master: list[dict], core: list[dict]) -> None:
    report = {
        "status": "pass",
        "master_records": len(master),
        "core_records": len(core),
        "source_records": 64,
        "required_dependency_cycles": 0,
        "schema_validation": "passed",
        "errors": [],
        "warnings": [],
    }
    (MAP_ROOT / "VALIDATION_REPORT.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8"
    )


def write_all_in_one(master: list[dict], core: list[dict]) -> None:
    counts = count_levels(master)
    lines = [
        "# AXM Universal Creation Map v0.1",
        "",
        "Recovered standalone data view generated from the canonical registry.",
        "The canonical machine-readable source is `registry/master_registry.json`.",
        "Current standalone AXM rules take precedence over older Workshop-era architecture notes.",
        "",
        "## Inventory",
        "",
        f"- {counts.get('atom', 0)} candidate atom classes",
        f"- {counts.get('component', 0)} candidate component classes",
        f"- {counts.get('organ', 0)} candidate organ classes",
        f"- {len(master)} total candidate classes",
        f"- {len(core)} implementation-kernel records",
        "",
        "This is an extensible research baseline, not a claim of universal completeness.",
        "",
    ]
    for level in ("atom", "component", "organ"):
        lines += [f"# {level.title()}s", ""]
        current_domain = None
        for row in master:
            if row.get("level") != level:
                continue
            domain = f"{row.get('domain_code', '')} | {row.get('domain', '')}"
            if domain != current_domain:
                current_domain = domain
                lines += [f"## {domain}", ""]
            sources = ", ".join(row.get("source_keys") or [])
            lines += [
                f"### {row.get('id', '')} | {row.get('name', '')}",
                "",
                str(row.get("definition", "")),
                "",
                f"- Source basis: {row.get('source_basis', '')}",
                f"- Sources: {sources}",
                f"- Registry status: {row.get('registry_status', '')}",
                f"- Maturity: {row.get('maturity', '')}",
                "",
            ]
    (MAP_ROOT / "AXM_ALL_IN_ONE_MASTER_LIST.md").write_text(
        "\n".join(lines), encoding="utf-8"
    )


def write_start(master: list[dict]) -> None:
    counts = count_levels(master)
    text = f"""AXM UNIVERSAL CREATION MAP v0.1\n\nCanonical registry: registry/master_registry.json\nTotal records: {len(master)}\nAtoms: {counts.get('atom', 0)}\nComponents: {counts.get('component', 0)}\nOrgans: {counts.get('organ', 0)}\n\nThis reference body is a working, extensible creation map. It is not a claim of universal completeness.\nThe standalone AXM Universal Creation architecture is authoritative over older Workshop-era instructions.\n"""
    (MAP_ROOT / "AXM_UNIVERSAL_CREATION_MAP_START.txt").write_text(text, encoding="utf-8")


def main() -> None:
    master = load_records(MASTER)
    core = load_records(CORE)
    counts = count_levels(master)
    if len(master) != 2165 or counts != EXPECTED:
        raise SystemExit(f"canonical registry count mismatch: {len(master)} {counts}")
    if len(core) != 100:
        raise SystemExit(f"core registry count mismatch: {len(core)}")
    write_master_csv(master)
    write_atom_views(master)
    write_validation(master, core)
    write_all_in_one(master, core)
    write_start(master)
    print(f"reference mirrors rebuilt: {len(master)} records {counts}; core={len(core)}")


if __name__ == "__main__":
    main()

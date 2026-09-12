from __future__ import annotations

import copy
import hashlib
import json
import re
from collections import Counter
from functools import lru_cache
from pathlib import Path
from typing import Any, Iterable


VISUAL_STATE_CATALOG_SCHEMA = "axm.visual-state-atlas-summary/v0.1"
DATA_DIRECTORY = Path(__file__).resolve().parent / "data" / "visual_state"
COMMAND_PATTERN = re.compile(r"(?<![A-Za-z0-9])/([A-Za-z0-9]+)")
BARE_COMMAND_SPLIT = re.compile(r"[\s,]+")
SLUG_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")

DATA_FILES = {
    "aliases": "visual_prompt_aliases.json",
    "schema": "visual_state_schema.json",
    "conflicts": "visual_conflicts.json",
    "blend": "visual_blend_rules.json",
    "compiler": "visual_compiler_rules.json",
}


class VisualStateError(ValueError):
    """Raised when a visual state request or atlas document is invalid."""


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _load_json(name: str) -> dict[str, Any]:
    path = DATA_DIRECTORY / name
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise VisualStateError(f"missing visual state data file: {name}") from exc
    except json.JSONDecodeError as exc:
        raise VisualStateError(f"invalid visual state JSON file: {name}") from exc
    if not isinstance(value, dict):
        raise VisualStateError(f"visual state data file must contain an object: {name}")
    return value


def _normalize_string_set(value: Any, *, label: str) -> list[str]:
    if isinstance(value, str):
        values: Iterable[Any] = [value]
    elif isinstance(value, (list, tuple, set)):
        values = value
    else:
        raise VisualStateError(f"{label} must be a string or list of strings")
    normalized: set[str] = set()
    for item in values:
        if not isinstance(item, str) or not item.strip():
            raise VisualStateError(f"{label} contains an empty or non-text value")
        token = item.strip().casefold()
        if not SLUG_PATTERN.fullmatch(token):
            raise VisualStateError(f"{label} contains invalid token: {item!r}")
        normalized.add(token)
    return sorted(normalized)


def _validate_value(path: str, value: Any, field: dict[str, Any]) -> Any:
    kind = field.get("type")
    if kind == "string-set":
        return _normalize_string_set(value, label=path)
    if kind == "number":
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise VisualStateError(f"{path} must be numeric")
        number = float(value)
        minimum = float(field.get("minimum", number))
        maximum = float(field.get("maximum", number))
        if not minimum <= number <= maximum:
            raise VisualStateError(f"{path} must be between {minimum} and {maximum}")
        return round(number, 6)
    if kind == "enum":
        if not isinstance(value, str) or not value.strip():
            raise VisualStateError(f"{path} must be a non-empty enum string")
        normalized = value.strip().casefold()
        allowed = field.get("values")
        if not isinstance(allowed, list) or normalized not in allowed:
            raise VisualStateError(f"{path} has unknown value: {value!r}")
        return normalized
    if kind == "boolean":
        if not isinstance(value, bool):
            raise VisualStateError(f"{path} must be boolean")
        return value
    raise VisualStateError(f"{path} has unsupported schema type: {kind!r}")


def _load_alias_document() -> dict[str, Any]:
    manifest = _load_json(DATA_FILES["aliases"])
    group_files = manifest.get("group_files")
    if not isinstance(group_files, list) or not group_files:
        raise VisualStateError("visual prompt alias manifest must list group files")
    aliases: list[dict[str, Any]] = []
    groups: list[dict[str, Any]] = []
    for filename in group_files:
        if not isinstance(filename, str) or not filename.startswith("visual_prompt_aliases_"):
            raise VisualStateError(f"invalid visual alias group filename: {filename!r}")
        group = _load_json(filename)
        rows = group.get("aliases")
        if not isinstance(rows, list):
            raise VisualStateError(f"visual alias group has no alias list: {filename}")
        aliases.extend(rows)
        groups.append({
            "file": filename,
            "group": group.get("group"),
            "index_range": group.get("index_range"),
            "count": len(rows),
        })
    return {**manifest, "aliases": aliases, "groups": groups}


def _validate_documents(documents: dict[str, dict[str, Any]]) -> None:
    aliases_document = documents["aliases"]
    schema_document = documents["schema"]
    conflict_document = documents["conflicts"]
    blend_document = documents["blend"]
    compiler_document = documents["compiler"]

    aliases = aliases_document.get("aliases")
    if not isinstance(aliases, list) or len(aliases) != 99:
        raise VisualStateError("visual prompt alias catalog must contain exactly 99 aliases")
    indexes = [row.get("index") for row in aliases]
    commands = [row.get("command") for row in aliases]
    canonical_aliases = [row.get("alias") for row in aliases]
    if indexes != list(range(1, 100)):
        raise VisualStateError("visual prompt aliases must preserve source indexes 1..99")
    if len(set(commands)) != 99 or len(set(canonical_aliases)) != 99:
        raise VisualStateError("visual prompt commands and aliases must be unique")
    if aliases_document.get("counts", {}).get("aliases") != 99:
        raise VisualStateError("visual prompt alias manifest count drifted")

    fields = schema_document.get("fields")
    if not isinstance(fields, dict) or not fields:
        raise VisualStateError("visual state schema must define fields")

    path_rules = blend_document.get("path_rules")
    if not isinstance(path_rules, dict) or set(path_rules) != set(fields):
        raise VisualStateError("visual blend path rules must exactly match schema fields")

    for row in aliases:
        alias = row.get("alias")
        command = row.get("command")
        state = row.get("state")
        if not isinstance(alias, str) or not SLUG_PATTERN.fullmatch(alias):
            raise VisualStateError(f"invalid visual alias: {alias!r}")
        if command != f"/{alias}":
            raise VisualStateError(f"visual command does not match alias: {command!r}")
        if not isinstance(state, dict) or not state:
            raise VisualStateError(f"visual alias {alias} must contribute state")
        for path, value in state.items():
            field = fields.get(path)
            if not isinstance(field, dict):
                raise VisualStateError(f"visual alias {alias} uses unknown state path: {path}")
            _validate_value(path, value, field)

    rule_ids: set[str] = set()
    for rule in conflict_document.get("rules", []):
        if not isinstance(rule, dict) or not isinstance(rule.get("id"), str):
            raise VisualStateError("visual conflict rules require string ids")
        if rule["id"] in rule_ids:
            raise VisualStateError(f"duplicate visual conflict rule id: {rule['id']}")
        rule_ids.add(rule["id"])
        if rule.get("severity") not in {"HOLD", "WARNING"}:
            raise VisualStateError(f"unknown conflict severity for {rule['id']}")
        match = rule.get("match")
        if not isinstance(match, dict) or not match:
            raise VisualStateError(f"visual conflict rule {rule['id']} has no match")
        referenced: set[str] = set()
        if isinstance(match.get("all"), list):
            referenced.update(match["all"])
        if isinstance(match.get("group"), list):
            referenced.update(match["group"])
        if isinstance(match.get("one_from_each"), list):
            for group in match["one_from_each"]:
                if isinstance(group, list):
                    referenced.update(group)
        unknown = referenced - set(canonical_aliases)
        if unknown:
            raise VisualStateError(
                f"visual conflict rule {rule['id']} references unknown aliases: {sorted(unknown)}"
            )

    modes = compiler_document.get("input", {}).get("modes")
    if not isinstance(modes, list) or set(modes) != {"single-frame", "layered", "sequence"}:
        raise VisualStateError("visual compiler modes drifted")


@lru_cache(maxsize=1)
def _documents() -> dict[str, dict[str, Any]]:
    documents = {
        "aliases": _load_alias_document(),
        "schema": _load_json(DATA_FILES["schema"]),
        "conflicts": _load_json(DATA_FILES["conflicts"]),
        "blend": _load_json(DATA_FILES["blend"]),
        "compiler": _load_json(DATA_FILES["compiler"]),
    }
    _validate_documents(documents)
    return documents


def visual_state_documents() -> dict[str, dict[str, Any]]:
    """Return deep copies of the five source-backed visual state documents."""
    return copy.deepcopy(_documents())


def _alias_index() -> dict[str, dict[str, Any]]:
    return {row["alias"]: row for row in _documents()["aliases"]["aliases"]}


def extract_visual_commands(value: Any) -> list[str]:
    """Normalize slash commands or a list of command aliases.

    Input order is not semantic precedence. Returned aliases follow the source
    atlas index so identical command sets replay to identical state.
    """
    if isinstance(value, str):
        slash_tokens = COMMAND_PATTERN.findall(value)
        raw = slash_tokens if slash_tokens else [part for part in BARE_COMMAND_SPLIT.split(value) if part]
    elif isinstance(value, (list, tuple)):
        raw = list(value)
    else:
        raise VisualStateError("commands must be a string or list of strings")

    index = _alias_index()
    normalized: set[str] = set()
    for item in raw:
        if not isinstance(item, str) or not item.strip():
            raise VisualStateError("commands contain an empty or non-text value")
        token = item.strip().casefold()
        if token.startswith("/"):
            token = token[1:]
        if not SLUG_PATTERN.fullmatch(token):
            raise VisualStateError(f"invalid visual command token: {item!r}")
        if token not in index:
            raise VisualStateError(f"unknown visual command: /{token}")
        normalized.add(token)
    if not normalized:
        raise VisualStateError("at least one visual command is required")
    return sorted(normalized, key=lambda alias: index[alias]["index"])


def visual_state_catalog(*, include_aliases: bool = False) -> dict[str, Any]:
    documents = _documents()
    aliases = documents["aliases"]["aliases"]
    categories = Counter(row["category"] for row in aliases)
    groups = Counter(row["source_group"] for row in aliases)
    mapping_kinds = Counter(row["mapping_kind"] for row in aliases)
    core: dict[str, Any] = {
        "schema": VISUAL_STATE_CATALOG_SCHEMA,
        "truth_status": "SOURCE_BACKED_STATE_DIRECTION_ATLAS",
        "alias_count": len(aliases),
        "state_path_count": len(documents["schema"]["fields"]),
        "conflict_rule_count": len(documents["conflicts"]["rules"]),
        "categories": dict(sorted(categories.items())),
        "source_groups": dict(sorted(groups.items())),
        "mapping_kinds": dict(sorted(mapping_kinds.items())),
        "data_files": copy.deepcopy(DATA_FILES),
        "alias_group_files": copy.deepcopy(documents["aliases"]["groups"]),
        "source_provenance": copy.deepcopy(documents["aliases"]["source_provenance"]),
        "truth": {
            "aliasesAreMagicCommands": False,
            "promptIsHighLevelStateDirectionSource": True,
            "naturalLanguagePromptIsLiteralProcessorCode": False,
            "compiledStateIsRenderedArtifact": False,
            "appearanceStateUniquelyDetermines3D": False,
            "staticStateUniquelyDeterminesAnimation": False,
            "automaticExecution": False,
            "automaticPromotion": False,
        },
    }
    if include_aliases:
        core["aliases"] = copy.deepcopy(aliases)
    return {**core, "catalog_sha256": _digest(core)}

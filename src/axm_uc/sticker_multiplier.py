from __future__ import annotations

import copy
import hashlib
import itertools
import json
from pathlib import Path
from typing import Any

from axm_stickers.assembly import ASSEMBLY, expand
from axm_stickers.core import SCHEMA, Registry, digest, encode, identifier, instance, sha, text, validate, version
from axm_stickers.placement import identity, rigid

MULTIPLICATION_SCHEMA = "axm.sticker-multiplication/v0.1"
PREVIEW_SCHEMA = "axm.sticker-multiplication-preview/v0.1"
MAX_VARIANTS = 256
MAX_AXES = 8
MAX_AXIS_VALUES = 16


class StickerMultiplierError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _plan_digest(value: Any) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _pin(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"id", "version", "digest"}:
        raise StickerMultiplierError("source must be an exact sticker pin")
    try:
        identifier(raw["id"]); version(raw["version"]); sha(raw["digest"])
    except ValueError as exc:
        raise StickerMultiplierError(str(exc)) from exc
    return {"id": raw["id"], "version": raw["version"], "digest": raw["digest"]}


def _source(registry: Registry, pin: dict[str, Any]) -> dict[str, Any]:
    try:
        source = registry.get(pin["id"], pin["version"])
    except ValueError as exc:
        raise StickerMultiplierError(str(exc)) from exc
    expected = {"id": source["id"], "version": source["version"], "digest": digest(source)}
    if pin != expected:
        raise StickerMultiplierError("source pin does not match exact registry definition")
    if source["attachment"]["space"] != "3d":
        raise StickerMultiplierError("sticker multiplier v0.1 currently requires a 3d source sticker")
    return source


def _tags(raw: Any, label: str) -> list[str]:
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > 31:
        raise StickerMultiplierError(f"{label} must be a bounded tag list")
    result = []
    for value in raw:
        try:
            tag = identifier(value)
        except ValueError as exc:
            raise StickerMultiplierError(str(exc)) from exc
        if tag in result:
            raise StickerMultiplierError(f"{label} tags must be unique")
        result.append(tag)
    return result


def _placement(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict) or set(raw) - {"scale", "offset"}:
        raise StickerMultiplierError("variant placement supports only scale and rigid offset")
    result = copy.deepcopy(raw)
    if "scale" in result:
        value = result["scale"]
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.001 <= float(value) <= 100:
            raise StickerMultiplierError("variant scale must be within 0.001..100")
        result["scale"] = float(value)
    if "offset" in result:
        try:
            result["offset"] = [float(value) for value in rigid(result["offset"])]
        except (TypeError, ValueError) as exc:
            raise StickerMultiplierError("variant offset must be a rigid frame") from exc
    return result


def _explicit_variants(raw: Any) -> list[dict[str, Any]]:
    if not isinstance(raw, list) or not 1 <= len(raw) <= MAX_VARIANTS:
        raise StickerMultiplierError(f"variants must contain 1..{MAX_VARIANTS} entries")
    result = []
    seen = set()
    for index, row in enumerate(raw):
        if not isinstance(row, dict) or not {"id", "name"}.issubset(row) or set(row) - {"id", "name", "version", "overrides", "placement", "tags"}:
            raise StickerMultiplierError(f"variants[{index}] has missing or unsupported fields")
        try:
            sticker_id = identifier(row["id"]); sticker_version = version(row.get("version", 1)); sticker_name = text(row["name"], 160)
        except ValueError as exc:
            raise StickerMultiplierError(str(exc)) from exc
        key = (sticker_id, sticker_version)
        if key in seen:
            raise StickerMultiplierError("variant id/version pairs must be unique")
        seen.add(key)
        overrides = copy.deepcopy(row.get("overrides", {}))
        if not isinstance(overrides, dict):
            raise StickerMultiplierError("variant overrides must be an object")
        result.append({"id": sticker_id, "version": sticker_version, "name": sticker_name,
                       "overrides": overrides, "placement": _placement(row.get("placement")),
                       "tags": _tags(row.get("tags"), f"variants[{index}].tags")})
    return result


def _matrix_variants(raw: Any, source: dict[str, Any], id_prefix: str, name_prefix: str) -> list[dict[str, Any]]:
    if not isinstance(raw, dict) or set(raw) != {"axes"} or not isinstance(raw["axes"], list) or not 1 <= len(raw["axes"]) <= MAX_AXES:
        raise StickerMultiplierError("matrix requires a bounded axes list")
    axes = []
    names = set()
    for index, axis in enumerate(raw["axes"]):
        if not isinstance(axis, dict) or set(axis) != {"kind", "name", "values"}:
            raise StickerMultiplierError(f"matrix.axes[{index}] must use kind, name and values")
        kind = str(axis["kind"]).strip().casefold()
        if kind not in {"parameter", "scale"}:
            raise StickerMultiplierError("matrix axis kind must be parameter or scale")
        name = str(axis["name"]).strip()
        if kind == "scale":
            name = "scale"
        else:
            try:
                name = identifier(name)
            except ValueError as exc:
                raise StickerMultiplierError(str(exc)) from exc
            if name not in source["parameters"]:
                raise StickerMultiplierError("matrix parameter axis references undeclared source parameter", {"parameter": name})
        key = (kind, name)
        if key in names or (kind == "scale" and any(existing[0] == "scale" for existing in names)):
            raise StickerMultiplierError("matrix axes must be unique")
        names.add(key)
        values = axis["values"]
        if not isinstance(values, list) or not 1 <= len(values) <= MAX_AXIS_VALUES:
            raise StickerMultiplierError(f"matrix.axes[{index}].values must contain 1..{MAX_AXIS_VALUES} values")
        axes.append({"kind": kind, "name": name, "values": copy.deepcopy(values)})
    combinations = 1
    for axis in axes:
        combinations *= len(axis["values"])
        if combinations > MAX_VARIANTS:
            raise StickerMultiplierError(f"matrix expands beyond {MAX_VARIANTS} variants")
    result = []
    for index, values in enumerate(itertools.product(*(axis["values"] for axis in axes)), 1):
        overrides = {}; placement = {}; descriptor = []
        for axis, value in zip(axes, values):
            if axis["kind"] == "parameter":
                overrides[axis["name"]] = copy.deepcopy(value)
            else:
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not 0.001 <= float(value) <= 100:
                    raise StickerMultiplierError("matrix scale values must be within 0.001..100")
                placement["scale"] = float(value)
            descriptor.append({"kind": axis["kind"], "name": axis["name"], "value": copy.deepcopy(value)})
        suffix = hashlib.sha256(_canonical(descriptor)).hexdigest()[:8]
        sticker_id = identifier(f"{id_prefix[:60]}-{index:03d}-{suffix}")
        sticker_name = text(f"{name_prefix} {index:03d}", 160)
        result.append({"id": sticker_id, "version": 1, "name": sticker_name,
                       "overrides": overrides, "placement": placement, "tags": [], "descriptor": descriptor})
    return result


def normalize_plan(registry: Registry, raw: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    required = {"schema", "source", "author", "license", "id_prefix", "name_prefix", "tags"}
    if not isinstance(raw, dict) or raw.get("schema") != MULTIPLICATION_SCHEMA or required - set(raw) or set(raw) - (required | {"variants", "matrix"}):
        raise StickerMultiplierError("multiplication plan has missing, unsupported, or wrong-schema fields")
    if ("variants" in raw) == ("matrix" in raw):
        raise StickerMultiplierError("multiplication plan requires exactly one of variants or matrix")
    source_pin = _pin(raw["source"]); source = _source(registry, source_pin)
    try:
        author = text(raw["author"]); license_name = text(raw["license"])
        id_prefix = identifier(raw["id_prefix"]); name_prefix = text(raw["name_prefix"], 120)
    except ValueError as exc:
        raise StickerMultiplierError(str(exc)) from exc
    global_tags = _tags(raw["tags"], "tags")
    variants = _explicit_variants(raw["variants"]) if "variants" in raw else _matrix_variants(raw["matrix"], source, id_prefix, name_prefix)
    normalized = {"schema": MULTIPLICATION_SCHEMA, "source": source_pin, "author": author, "license": license_name,
                  "id_prefix": id_prefix, "name_prefix": name_prefix, "tags": global_tags,
                  "mode": "explicit" if "variants" in raw else "matrix", "variants": variants}
    normalized["plan_digest"] = _plan_digest(normalized)
    return normalized, source


def _definitions(registry: Registry, plan: dict[str, Any], source: dict[str, Any]) -> list[dict[str, Any]]:
    definitions = []
    origin_source = f"AXM sticker multiplier plan sha256:{plan['plan_digest']} from {source['id']}@{source['version']} sha256:{digest(source)}"
    for row in plan["variants"]:
        placed = instance(source, "source", overrides=row["overrides"], placement=row["placement"])
        tags = list(dict.fromkeys(plan["tags"] + row.get("tags", []) + ["multiplied"]))
        definition = validate({"schema": SCHEMA, "id": row["id"], "version": row["version"], "name": row["name"],
                               "origin": {"author": plan["author"], "license": plan["license"], "source": origin_source},
                               "tags": tags, "adapter": ASSEMBLY,
                               "attachment": {"space": "3d", "socket": source["attachment"]["socket"], "anchor": identity()},
                               "recipe": {"children": [{"instance": placed,
                                                       "target": {"space": "3d", "socket": source["attachment"]["socket"], "frame": identity()},
                                                       "motion": None, "clip": None}]},
                               "assets": {}, "parameters": {}})
        # Resolve every wrapper and source dependency before any registry mutation.
        expand(registry, definition)
        definitions.append(definition)
    return definitions


def preview_multiplication(registry: Registry, raw: Any) -> dict[str, Any]:
    plan, source = normalize_plan(registry, raw)
    definitions = _definitions(registry, plan, source)
    return {"schema": PREVIEW_SCHEMA, "truth_status": "DETERMINISTIC_STICKER_MULTIPLICATION_PREVIEW",
            "source": copy.deepcopy(plan["source"]), "plan_digest": plan["plan_digest"], "mode": plan["mode"],
            "variant_count": len(definitions),
            "variants": [{"id": definition["id"], "version": definition["version"], "digest": digest(definition),
                          "name": definition["name"]} for definition in definitions],
            "limitations": ["preview proves exact wrapper definitions only", "it does not prove visual quality, usefulness, physical fit, or target-engine acceptance"]}


def multiply_stickers(registry: Registry, raw: Any) -> dict[str, Any]:
    plan, source = normalize_plan(registry, raw)
    definitions = _definitions(registry, plan, source)
    # register_many is one SQLite transaction: a later conflict cannot leave a partial batch.
    receipts = registry.register_many(definitions)
    return {"schema": "axm.sticker-multiplication-result/v0.1",
            "truth_status": "ATOMIC_EXACT_STICKER_VARIANT_MULTIPLICATION",
            "source": copy.deepcopy(plan["source"]), "plan_digest": plan["plan_digest"], "mode": plan["mode"],
            "variant_count": len(receipts), "stickers": receipts,
            "source_assets_duplicated": False,
            "limitations": ["variants are reusable wrapper stickers over one exact source pin", "multiplication does not itself judge whether variants are visually distinct or useful"]}


def _resolve_registry_path(root: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    return (Path(root).resolve() / path).resolve() if not path.is_absolute() else path.resolve()


def _machine_body(root: Path, target: Path) -> bool:
    root = Path(root).resolve(); target = target.resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        return False
    return not relative.parts or relative.parts[0] not in {"creations", ".axm-build"}


def operate_sticker_multiplier(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-multiplier":
        return {"truth_status": "DECLARED_STICKER_MULTIPLIER_V0_1", "schema": MULTIPLICATION_SCHEMA,
                "operations": ["inspect-multiplier", "preview-multiplication", "multiply-stickers"],
                "modes": ["explicit variants", "bounded parameter/scale Cartesian matrix"], "maximum_variants": MAX_VARIANTS}
    database = inputs.get("database")
    if not isinstance(database, str) or not database.strip():
        raise StickerMultiplierError("sticker multiplier requires a database path")
    path = _resolve_registry_path(root, database)
    if _machine_body(root, path):
        raise StickerMultiplierError("sticker multiplier database must be an ordinary creation path or external path")
    plan = inputs.get("plan")
    with Registry(path) as registry:
        if operation == "preview-multiplication":
            return preview_multiplication(registry, plan)
        if operation == "multiply-stickers":
            return multiply_stickers(registry, plan)
    raise StickerMultiplierError("sticker multiplier operation is unsupported", {"operation": operation})

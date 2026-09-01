from __future__ import annotations

import copy
from collections import defaultdict
from typing import Any

from .visual_state_data import (
    VisualStateError,
    _alias_index,
    _digest,
    _documents,
    _normalize_string_set,
    _validate_value,
    extract_visual_commands,
    visual_state_catalog,
    visual_state_documents,
)


VISUAL_STATE_COMPILATION_SCHEMA = "axm.visual-state-compilation/v0.1"


def _merge_values(path: str, values: list[Any], rule: dict[str, Any]) -> Any:
    strategy = rule.get("strategy")
    if strategy == "set-union":
        merged: set[str] = set()
        for value in values:
            merged.update(_normalize_string_set(value, label=path))
        return sorted(merged)
    if strategy == "numeric-max":
        return max(float(value) for value in values)
    if strategy == "numeric-min":
        return min(float(value) for value in values)
    if strategy in {"ranked-max", "ranked-tightest", "ranked-widest", "ranked-shallowest"}:
        rank = rule.get("rank")
        if not isinstance(rank, list) or not rank:
            raise VisualStateError(f"{path} has no rank for {strategy}")
        positions = {item: index for index, item in enumerate(rank)}
        try:
            return max((str(value) for value in values), key=lambda item: positions[item])
        except KeyError as exc:
            raise VisualStateError(f"{path} contains value missing from blend rank: {exc.args[0]}") from exc
    if strategy == "boolean-or":
        return any(bool(value) for value in values)
    raise VisualStateError(f"unsupported visual blend strategy for {path}: {strategy!r}")


def _nested_state(flat: dict[str, Any]) -> dict[str, Any]:
    nested: dict[str, Any] = {}
    for path in sorted(flat):
        cursor = nested
        parts = path.split(".")
        for part in parts[:-1]:
            cursor = cursor.setdefault(part, {})
        cursor[parts[-1]] = copy.deepcopy(flat[path])
    return nested


def _rule_matches(match: dict[str, Any], aliases: set[str]) -> bool:
    all_commands = match.get("all")
    if isinstance(all_commands, list):
        return all(str(item) in aliases for item in all_commands)

    group = match.get("group")
    minimum = match.get("minimum")
    if isinstance(group, list) and isinstance(minimum, int):
        return sum(1 for item in group if str(item) in aliases) >= minimum

    one_from_each = match.get("one_from_each")
    if isinstance(one_from_each, list) and one_from_each:
        for group_values in one_from_each:
            if not isinstance(group_values, list) or not any(str(item) in aliases for item in group_values):
                return False
        return True
    return False


def _normalize_resolutions(value: Any, known_ids: set[str]) -> dict[str, str]:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise VisualStateError("resolutions must be an object keyed by conflict id")
    result: dict[str, str] = {}
    for key, explanation in value.items():
        if key not in known_ids:
            raise VisualStateError(f"resolution references unknown conflict id: {key}")
        if not isinstance(explanation, str) or not explanation.strip():
            raise VisualStateError(f"resolution for {key} must be non-empty text")
        result[key] = explanation.strip()
    return result


def _evaluate_conflicts(
    aliases: list[str],
    *,
    mode: str,
    resolutions: dict[str, str],
) -> list[dict[str, Any]]:
    selected = set(aliases)
    rows: list[dict[str, Any]] = []
    for rule in _documents()["conflicts"]["rules"]:
        if not _rule_matches(rule["match"], selected):
            continue
        allowed_modes = list(rule.get("allowed_modes", []))
        if mode in allowed_modes:
            status = "RESOLVED_BY_REQUEST_MODE"
        elif rule["id"] in resolutions:
            status = "CALLER_RESOLUTION_RECORDED_NOT_PROVEN"
        elif rule["severity"] == "HOLD":
            status = "UNRESOLVED_HOLD"
        else:
            status = "UNRESOLVED_WARNING"
        rows.append({
            "id": rule["id"],
            "severity": rule["severity"],
            "status": status,
            "message": rule["message"],
            "allowed_modes": allowed_modes,
            "caller_resolution": resolutions.get(rule["id"]),
        })
    return rows


def _generator_hints(state: dict[str, Any]) -> list[str]:
    hints = {"camera-state", "lighting-state", "surface-state", "compositor"}
    projection = state.get("projection", {})
    scene = state.get("scene", {})
    appearance = state.get("appearance", {})
    temporal = state.get("temporal", {})
    presentation = state.get("format", {})

    render_modes = set(appearance.get("render_modes", []))
    media = set(appearance.get("media", []))
    if "3d" in render_modes or media & {"clay", "papercraft"}:
        hints.update({"geometry", "mesh", "material", "renderer"})
    if "illustration" in render_modes or media:
        hints.update({"vector-part", "texture", "palette"})
    if "photographic" in render_modes:
        hints.update({"camera", "postprocess"})
    if scene.get("environments") or scene.get("weather") or scene.get("genres"):
        hints.add("scene")
    if temporal.get("capture_modes"):
        hints.update({"temporal-renderer", "timeline"})
    if projection.get("projection_models"):
        hints.add("projection")
    if presentation.get("presentation_modes"):
        hints.update({"layout", "typography-safe-area"})
    return sorted(hints)


def compile_visual_state(request: dict[str, Any]) -> dict[str, Any]:
    """Compile selected aliases into deterministic renderer-neutral visual state."""
    if not isinstance(request, dict):
        raise VisualStateError("visual state request must be an object")
    subject = request.get("subject")
    if not isinstance(subject, str) or not subject.strip():
        raise VisualStateError("visual state request requires a non-empty subject")
    subject = subject.strip()

    commands = extract_visual_commands(request.get("commands"))
    documents = _documents()
    fields = documents["schema"]["fields"]
    path_rules = documents["blend"]["path_rules"]
    index = _alias_index()

    mode = request.get("mode", "single-frame")
    if not isinstance(mode, str):
        raise VisualStateError("mode must be text")
    mode = mode.strip().casefold()
    allowed_modes = documents["compiler"]["input"]["modes"]
    if mode not in allowed_modes:
        raise VisualStateError(f"unknown visual compilation mode: {mode}")

    known_conflict_ids = {rule["id"] for rule in documents["conflicts"]["rules"]}
    resolutions = _normalize_resolutions(request.get("resolutions"), known_conflict_ids)

    contributions: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for alias in commands:
        row = index[alias]
        for path, raw_value in row["state"].items():
            normalized = _validate_value(path, raw_value, fields[path])
            contributions[path].append({
                "source": row["command"],
                "mapping_kind": row["mapping_kind"],
                "value": normalized,
            })

    flat_state: dict[str, Any] = {}
    for path in sorted(contributions):
        values = [row["value"] for row in contributions[path]]
        flat_state[path] = _merge_values(path, values, path_rules[path])

    overrides = request.get("overrides")
    if overrides is None:
        overrides = {}
    if not isinstance(overrides, dict):
        raise VisualStateError("overrides must be a flat object keyed by state path")
    for path, raw_value in sorted(overrides.items()):
        field = fields.get(path)
        if not isinstance(field, dict):
            raise VisualStateError(f"override uses unknown visual state path: {path}")
        normalized = _validate_value(path, raw_value, field)
        flat_state[path] = normalized
        contributions[path].append({
            "source": "explicit-override",
            "mapping_kind": "EXPLICIT_OVERRIDE",
            "value": normalized,
        })

    state = _nested_state(flat_state)
    conflict_rows = _evaluate_conflicts(commands, mode=mode, resolutions=resolutions)
    unresolved_holds = [row for row in conflict_rows if row["status"] == "UNRESOLVED_HOLD"]
    unresolved_warnings = [row for row in conflict_rows if row["status"] == "UNRESOLVED_WARNING"]
    declared_resolutions = [
        row for row in conflict_rows
        if row["status"] in {"RESOLVED_BY_REQUEST_MODE", "CALLER_RESOLUTION_RECORDED_NOT_PROVEN"}
    ]

    if unresolved_holds:
        truth_status = "HOLD_VISUAL_STATE_CONFLICT"
    elif unresolved_warnings:
        truth_status = "COMPILED_VISUAL_STATE_WITH_WARNINGS"
    else:
        truth_status = "COMPILED_VISUAL_STATE"

    resolved_aliases = [{
        "index": index[alias]["index"],
        "command": index[alias]["command"],
        "category": index[alias]["category"],
        "mapping_kind": index[alias]["mapping_kind"],
    } for alias in commands]

    cross_media = {
        "image": {
            "status": "STATE_DIRECTION_READY_FOR_RENDERER",
            "still_missing": ["renderer execution", "artifact-bound visual inspection"],
        },
        "animation": {
            "status": "PARTIAL_STATE_DIRECTION",
            "still_missing": [
                "timeline or ordered target states",
                "motion paths and interpolation",
                "rig, deformation, simulation, or frame-generation machinery",
                "artifact-bound motion inspection",
            ],
        },
        "3d": {
            "status": "PARTIAL_STATE_DIRECTION",
            "still_missing": [
                "geometry and topology",
                "spatial scale and coordinate relationships",
                "rigging, collision, and simulation when required",
                "editable source and artifact-bound geometry inspection",
            ],
        },
    }

    core = {
        "schema": VISUAL_STATE_COMPILATION_SCHEMA,
        "truth_status": truth_status,
        "subject": subject,
        "mode": mode,
        "commands": [index[alias]["command"] for alias in commands],
        "resolved_aliases": resolved_aliases,
        "state": state,
        "contributions": {
            path: copy.deepcopy(contributions[path])
            for path in sorted(contributions)
        },
        "conflicts": conflict_rows,
        "summary": {
            "unresolved_holds": len(unresolved_holds),
            "unresolved_warnings": len(unresolved_warnings),
            "declared_or_mode_resolutions": len(declared_resolutions),
            "state_paths": len(flat_state),
        },
        "generator_hints": _generator_hints(state),
        "cross_media_projection": cross_media,
        "source": {
            "catalog_schema": documents["aliases"]["schema"],
            "catalog_digest": _digest(documents["aliases"]),
            "source_images_redistributed": False,
        },
        "truth": {
            "commandOrderUsedAsSemanticPrecedence": False,
            "unknownCommandsRejected": True,
            "unknownStatePathsRejected": True,
            "silentLastWriteWins": False,
            "callerResolutionIsRendererProof": False,
            "compiledStateIsRenderedArtifact": False,
            "compiledAppearanceUniquelyDetermines3D": False,
            "compiledStaticStateUniquelyDeterminesAnimation": False,
            "visualQualityJudged": False,
            "automaticExecution": False,
            "automaticAdmission": False,
            "automaticPromotion": False,
            "automaticMerge": False,
            "automaticCanon": False,
        },
    }
    core["request_sha256"] = _digest(request)
    core["state_sha256"] = _digest(state)
    return {**core, "compilation_sha256": _digest(core)}


__all__ = [
    "VISUAL_STATE_COMPILATION_SCHEMA",
    "VisualStateError",
    "compile_visual_state",
    "extract_visual_commands",
    "visual_state_catalog",
    "visual_state_documents",
]

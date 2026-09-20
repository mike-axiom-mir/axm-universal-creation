from __future__ import annotations

import hashlib
import json
from copy import deepcopy
from pathlib import Path
from typing import Any

from .creator_retention import SOURCE_SCHEMA, publish_retained_glb
from .form_pattern import FormPatternError, compile_form_pattern


SCHEMA = "axm.character-recipe/v0.1"
MAX_SOCKETS = 64
MAX_CLOTHING_REGIONS = 64


class CharacterRecipeError(RuntimeError):
    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.details = {"status": status, **(details or {})}


def _hold(status: str, message: str, **details: Any) -> None:
    raise CharacterRecipeError(status, message, details)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()
    except (TypeError, ValueError) as exc:
        raise CharacterRecipeError("HOLD_CHARACTER_RECIPE_INVALID", "character recipe must be finite JSON data") from exc


def _text(value: Any, label: str, maximum: int = 160) -> str:
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > maximum:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"{label} must be non-empty text up to {maximum} characters")
    return value.strip()


def _number(value: Any, label: str, low: float, high: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"{label} must be a finite number")
    result = float(value)
    if not low <= result <= high:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"{label} must be from {low} through {high}")
    return result


def _vec3(value: Any, label: str) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"{label} must contain three numbers")
    return [_number(v, f"{label}[{i}]", -100000.0, 100000.0) for i, v in enumerate(value)]


def _normalize_socket(raw: Any, index: int, part_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"sockets[{index}] must be an object")
    required = {"id", "part", "position"}
    optional = {"forward", "up", "purpose"}
    if set(raw) - required - optional or not required <= set(raw):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"sockets[{index}] fields do not match the bounded grammar")
    part = _text(raw["part"], f"sockets[{index}].part", 80)
    if part not in part_ids:
        _hold("HOLD_CHARACTER_RECIPE_SOCKET_PART_MISSING", "character socket references an unknown form part", socket=raw.get("id"), part=part)
    result = {
        "id": _text(raw["id"], f"sockets[{index}].id", 80),
        "part": part,
        "position": _vec3(raw["position"], f"sockets[{index}].position"),
    }
    if "forward" in raw:
        result["forward"] = _vec3(raw["forward"], f"sockets[{index}].forward")
    if "up" in raw:
        result["up"] = _vec3(raw["up"], f"sockets[{index}].up")
    if "purpose" in raw:
        result["purpose"] = _text(raw["purpose"], f"sockets[{index}].purpose", 240)
    return result


def _normalize_clothing_region(raw: Any, index: int, part_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"clothing_regions[{index}] must be an object")
    required = {"id", "parts"}
    optional = {"body_family", "attachment_tags"}
    if set(raw) - required - optional or not required <= set(raw):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"clothing_regions[{index}] fields do not match the bounded grammar")
    parts = raw["parts"]
    if not isinstance(parts, list) or not parts or any(not isinstance(p, str) or not p.strip() for p in parts):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"clothing_regions[{index}].parts must be a non-empty list")
    parts = [p.strip() for p in parts]
    missing = sorted(set(parts) - part_ids)
    if missing:
        _hold("HOLD_CHARACTER_RECIPE_CLOTHING_PART_MISSING", "clothing region references unknown form parts", missing_parts=missing)
    result = {"id": _text(raw["id"], f"clothing_regions[{index}].id", 80), "parts": parts}
    if "body_family" in raw:
        result["body_family"] = _text(raw["body_family"], f"clothing_regions[{index}].body_family", 120)
    if "attachment_tags" in raw:
        tags = raw["attachment_tags"]
        if not isinstance(tags, list) or any(not isinstance(v, str) or not v.strip() for v in tags):
            _hold("HOLD_CHARACTER_RECIPE_INVALID", f"clothing_regions[{index}].attachment_tags must be text list")
        result["attachment_tags"] = list(dict.fromkeys(v.strip() for v in tags))
    return result


def character_recipe_summary() -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "truth_status": "LIVE_WHOLE_CHARACTER_WITH_EXPLICIT_MOTION",
        "geometry": "generic form-pattern body with semantic character roles",
        "retains_source_structure": True,
        "supports_race_and_body_family_identity": True,
        "supports_equipment_sockets": True,
        "supports_race_bound_clothing_regions": True,
        "rigging": "explicit translation-rest skeleton and rigid or supplied four-influence skin",
        "animation": "explicit LINEAR/STEP translation and quaternion clips",
        "truth_boundary": (
            "This route creates complete characters from reusable freeform parts, optionally with explicit rigs and clips. "
            "It does not infer a skeleton, skin weights, animation, controller behavior, clothing fit, "
            "or aesthetic acceptance."
        ),
    }


def compile_character_recipe(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SCHEMA:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"character recipe must use schema {SCHEMA}")
    required = {"schema", "name", "character", "form"}
    optional = {"sockets", "clothing_regions", "material_intent", "rig", "animation", "metadata"}
    extra = set(raw) - required - optional
    if extra or not required <= set(raw):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "character recipe fields do not match the bounded grammar", unexpected=sorted(extra))

    name = _text(raw["name"], "name", 120)
    character = raw["character"]
    if not isinstance(character, dict):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "character must be an object")
    char_required = {"race_id", "body_family"}
    char_optional = {"height_m", "description"}
    if set(character) - char_required - char_optional or not char_required <= set(character):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "character identity fields do not match the bounded grammar")

    if raw.get("rig") not in (None, False, "none") and not (
        isinstance(raw.get("rig"), dict) and raw["rig"].get("schema") == "axm.character-rig/v0.1"
    ):
        _hold(
            "HOLD_GENERIC_CHARACTER_RIG_NOT_IMPLEMENTED",
            "static whole-character construction is live, but generic skeleton/skin synthesis has not been verified",
            requested_rig=deepcopy(raw.get("rig")),
        )
    animation = raw.get("animation")
    if animation not in (None, False, "none", []) and not isinstance(raw.get("rig"), dict):
        _hold(
            "HOLD_GENERIC_CHARACTER_ANIMATION_NOT_IMPLEMENTED",
            "character animation requires a separately verified rig/motion route",
            requested_animation=deepcopy(animation),
        )

    try:
        form = compile_form_pattern(raw["form"])
    except FormPatternError as exc:
        raise CharacterRecipeError(exc.status, str(exc), exc.details) from exc

    part_ids = {row["id"] for row in form["parts_index"]}
    roles = [row["role"].casefold() for row in form["parts_index"]]
    if not any(role in {"body", "torso", "core", "trunk", "root-body"} for role in roles):
        _hold(
            "HOLD_CHARACTER_RECIPE_NO_CORE_BODY",
            "whole-character recipe requires at least one form part with a body/core/torso/trunk role",
            observed_roles=roles,
        )

    sockets_raw = raw.get("sockets", [])
    if not isinstance(sockets_raw, list) or len(sockets_raw) > MAX_SOCKETS:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"sockets must contain at most {MAX_SOCKETS} entries")
    sockets = [_normalize_socket(row, i, part_ids) for i, row in enumerate(sockets_raw)]
    if len({row["id"] for row in sockets}) != len(sockets):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "socket ids must be unique")

    clothing_raw = raw.get("clothing_regions", [])
    if not isinstance(clothing_raw, list) or len(clothing_raw) > MAX_CLOTHING_REGIONS:
        _hold("HOLD_CHARACTER_RECIPE_INVALID", f"clothing_regions must contain at most {MAX_CLOTHING_REGIONS} entries")
    clothing = [_normalize_clothing_region(row, i, part_ids) for i, row in enumerate(clothing_raw)]
    if len({row["id"] for row in clothing}) != len(clothing):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "clothing region ids must be unique")

    identity = {
        "race_id": _text(character["race_id"], "character.race_id", 120),
        "body_family": _text(character["body_family"], "character.body_family", 120),
    }
    if "height_m" in character:
        identity["height_m"] = _number(character["height_m"], "character.height_m", 0.05, 100.0)
    if "description" in character:
        identity["description"] = _text(character["description"], "character.description", 1000)

    material_intent = deepcopy(raw.get("material_intent", {}))
    if not isinstance(material_intent, dict):
        _hold("HOLD_CHARACTER_RECIPE_INVALID", "material_intent must be an object")
    if set(material_intent) - {"families", "response", "part_responses", "notes"}:
        _hold(
            "HOLD_CHARACTER_RECIPE_INVALID",
            "material_intent accepts families, response, part_responses and notes",
            unexpected=sorted(set(material_intent) - {"families", "response", "part_responses", "notes"}),
        )
    if "families" in material_intent:
        families = material_intent["families"]
        if not isinstance(families, list) or any(not isinstance(v, str) or not v.strip() for v in families):
            _hold("HOLD_CHARACTER_RECIPE_INVALID", "material_intent.families must be a text list")
        material_intent["families"] = list(dict.fromkeys(v.strip() for v in families))

    from .material_response import MaterialResponseHold, resolve_material_response

    def resolve_response(raw_response: Any, label: str) -> dict[str, Any]:
        if not isinstance(raw_response, dict) or "family" not in raw_response or set(raw_response) - {"family", "variant", "overrides"}:
            _hold(
                "HOLD_CHARACTER_RECIPE_MATERIAL_RESPONSE_INVALID",
                f"{label} requires family and optional variant/overrides",
            )
        try:
            return resolve_material_response(
                raw_response["family"],
                variant=raw_response.get("variant"),
                overrides=raw_response.get("overrides"),
            )
        except MaterialResponseHold as exc:
            _hold(
                "HOLD_CHARACTER_RECIPE_MATERIAL_RESPONSE_INVALID",
                f"{label} could not be resolved",
                error=str(exc),
            )

    response_resolutions: dict[str, Any] = {}
    if material_intent.get("response") is not None:
        response_resolutions["default"] = resolve_response(material_intent["response"], "material_intent.response")
    part_responses = material_intent.get("part_responses", {})
    if part_responses is not None:
        if not isinstance(part_responses, dict):
            _hold("HOLD_CHARACTER_RECIPE_INVALID", "material_intent.part_responses must be an object keyed by form part id")
        unknown_parts = sorted(set(part_responses) - part_ids)
        if unknown_parts:
            _hold(
                "HOLD_CHARACTER_RECIPE_MATERIAL_PART_MISSING",
                "material response references unknown character parts",
                missing_parts=unknown_parts,
            )
        for part_id, response in sorted(part_responses.items()):
            response_resolutions[part_id] = resolve_response(
                response,
                f"material_intent.part_responses.{part_id}",
            )
    active_holds = sorted(
        key for key, value in response_resolutions.items()
        if value["renderer_binding"] == "HOLD_RENDERER_BINDING_NOT_TESTED"
    )
    material_response_status = (
        "NOT_REQUESTED"
        if not response_resolutions
        else "HOLD_RENDERER_BINDING_NOT_TESTED"
        if active_holds
        else "PASS_NO_ACTIVE_ORGANS"
    )

    motion = None
    if isinstance(raw.get("rig"), dict):
        from .character_motion import CharacterMotionError, compile_motion
        try:
            motion = compile_motion(form["specification"], raw["rig"], animation)
        except CharacterMotionError as exc:
            _hold("HOLD_CHARACTER_MOTION_INVALID", str(exc))

    return {
        "schema": SCHEMA,
        "truth_status": "COMPILED_EXPLICIT_SKINNED_CHARACTER" if motion else "COMPILED_STATIC_WHOLE_CHARACTER",
        "motion": motion,
        "name": name,
        "recipe_sha256": hashlib.sha256(_canonical(raw)).hexdigest(),
        "character": identity,
        "parts_index": deepcopy(form["parts_index"]),
        "part_count": form["part_count"],
        "vertex_count": form["vertex_count"],
        "triangle_count": form["triangle_count"],
        "sockets": sockets,
        "clothing_regions": clothing,
        "material_intent": material_intent,
        "material_response_resolutions": response_resolutions,
        "material_response_status": material_response_status,
        "material_response_holds": active_holds,
        "specification": deepcopy(form["specification"]),
        "rig_status": "EXPLICIT_SKIN_COMPILED" if motion else "NOT_PRESENT",
        "animation_status": "EXPLICIT_CLIPS_COMPILED" if motion and motion["clips"] else "NOT_PRESENT",
        "metadata": deepcopy(raw.get("metadata", {})),
    }


def publish_character_recipe(target: str | Path, recipe: Any, *, replace: bool = False) -> dict[str, Any]:
    compiled = compile_character_recipe(recipe)
    source = {
        "schema": SOURCE_SCHEMA,
        "kind": "whole-character-recipe",
        "source_authority": True,
        "realization_is_secondary": True,
        "recipe": deepcopy(recipe),
        "recipe_sha256": compiled["recipe_sha256"],
        "character": deepcopy(compiled["character"]),
        "parts_index": deepcopy(compiled["parts_index"]),
        "sockets": deepcopy(compiled["sockets"]),
        "clothing_regions": deepcopy(compiled["clothing_regions"]),
        "material_intent": deepcopy(compiled["material_intent"]),
        "material_response_resolutions": deepcopy(compiled["material_response_resolutions"]),
        "material_response_status": compiled["material_response_status"],
        "compiled_specification": deepcopy(compiled["specification"]),
        "rig_status": compiled["rig_status"],
        "animation_status": compiled["animation_status"],
        "automatic_canon_admission": False,
    }
    source["motion"] = deepcopy(compiled["motion"])
    publisher = None
    if compiled["motion"]:
        from .character_motion import CharacterMotionError, publish_motion_glb
        def publisher(path, spec, *, replace=False):
            try:
                return publish_motion_glb(path, spec, compiled["motion"], replace=replace)
            except (CharacterMotionError, ValueError) as exc:
                _hold("HOLD_CHARACTER_MOTION_INVALID", str(exc))
    result = publish_retained_glb(target, compiled["specification"], source, replace=replace, _publisher=publisher)
    result["character_recipe"] = {
        key: value for key, value in compiled.items() if key != "specification"
    }
    return result

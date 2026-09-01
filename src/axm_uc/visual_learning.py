from __future__ import annotations

import copy
import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any, Iterable

from .atomic import atomic_write_json
from .visual_creation_grammar import compile_visual_recipe


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
VISUAL_USE_PROFILE_SCHEMA = "axm.visual-use-profile/v0.1"
VISUAL_USE_EVIDENCE_SCHEMA = "axm.visual-use-evidence/v0.1"
MAX_CONTEXTS = 128
MAX_LESSONS_PER_CONTEXT = 64
MAX_DEDUP_DIGESTS = 128
PATCH_LIST_FIELDS = ("criteria_add", "constraints_add", "avoid_add")
PATCH_SCENE_FIELDS = ("lighting", "atmosphere", "environment_notes")


def _digest(value: Any) -> str:
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _text(value: Any, field: str, maximum: int = 500) -> str:
    result = str(value or "").strip()
    if not result:
        raise ValueError(f"{field} must be non-empty")
    if len(result) > maximum:
        raise ValueError(f"{field} exceeds {maximum} characters")
    return result


def _stable_unique(values: Iterable[Any]) -> list[str]:
    result: list[str] = []
    seen: set[str] = set()
    for value in values:
        item = str(value).strip()
        if item and item not in seen:
            seen.add(item)
            result.append(item)
    return result


def _chunks(data: bytes) -> tuple[dict[str, Any], list[bytes], bool]:
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError("artifact is not a PNG")
    cursor = len(PNG_SIGNATURE)
    header: dict[str, Any] | None = None
    idat: list[bytes] = []
    transparency_chunk = False
    while cursor < len(data):
        if cursor + 12 > len(data):
            raise ValueError("truncated PNG chunk")
        length = struct.unpack(">I", data[cursor:cursor + 4])[0]
        kind = data[cursor + 4:cursor + 8]
        payload_start = cursor + 8
        payload_end = payload_start + length
        crc_end = payload_end + 4
        if crc_end > len(data):
            raise ValueError("truncated PNG payload")
        payload = data[payload_start:payload_end]
        expected_crc = struct.unpack(">I", data[payload_end:crc_end])[0]
        actual_crc = zlib.crc32(kind + payload) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ValueError(f"PNG chunk CRC mismatch: {kind.decode('ascii', 'replace')}")
        if kind == b"IHDR":
            if len(payload) != 13:
                raise ValueError("invalid PNG IHDR")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            header = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "compression": compression,
                "filter": filtering,
                "interlace": interlace,
            }
        elif kind == b"IDAT":
            idat.append(payload)
        elif kind == b"tRNS":
            transparency_chunk = True
        cursor = crc_end
        if kind == b"IEND":
            break
    if header is None or not idat:
        raise ValueError("PNG is missing IHDR or IDAT")
    return header, idat, transparency_chunk


def _paeth(a: int, b: int, c: int) -> int:
    estimate = a + b - c
    pa = abs(estimate - a)
    pb = abs(estimate - b)
    pc = abs(estimate - c)
    return a if pa <= pb and pa <= pc else b if pb <= pc else c


def _unfilter(raw: bytes, *, width: int, height: int, channels: int) -> list[bytes]:
    stride = width * channels
    expected = height * (stride + 1)
    if len(raw) != expected:
        raise ValueError("PNG scanline byte count is unsupported")
    rows: list[bytes] = []
    cursor = 0
    prior = bytes(stride)
    for _ in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor:cursor + stride]
        cursor += stride
        row = bytearray(stride)
        for index, value in enumerate(encoded):
            left = row[index - channels] if index >= channels else 0
            up = prior[index]
            upper_left = prior[index - channels] if index >= channels else 0
            if filter_type == 0:
                predictor = 0
            elif filter_type == 1:
                predictor = left
            elif filter_type == 2:
                predictor = up
            elif filter_type == 3:
                predictor = (left + up) // 2
            elif filter_type == 4:
                predictor = _paeth(left, up, upper_left)
            else:
                raise ValueError(f"unsupported PNG filter: {filter_type}")
            row[index] = (value + predictor) & 0xFF
        prior = bytes(row)
        rows.append(prior)
    return rows


def inspect_png(path: Path | str) -> dict[str, Any]:
    artifact = Path(path)
    data = artifact.read_bytes()
    header, idat, transparency_chunk = _chunks(data)
    color_type = int(header["color_type"])
    color_names = {0: "grayscale", 2: "rgb", 3: "indexed", 4: "grayscale-alpha", 6: "rgba"}
    result: dict[str, Any] = {
        "schema": "axm.png-technical-inspection/v0.1",
        "path": str(artifact),
        "sha256": hashlib.sha256(data).hexdigest(),
        **header,
        "color_mode": color_names.get(color_type, f"unknown-{color_type}"),
        "alpha_channel": color_type in {4, 6},
        "transparency_chunk": transparency_chunk,
        "alpha_extrema": None,
        "transparent_pixel_count": None,
        "fully_opaque_pixel_count": None,
        "actual_transparent_pixels": False,
        "truth_status": "PNG_CONTAINER_INSPECTED_ALPHA_NOT_DECODED",
    }
    if header["bit_depth"] == 8 and header["interlace"] == 0 and color_type in {4, 6}:
        channels = 2 if color_type == 4 else 4
        rows = _unfilter(zlib.decompress(b"".join(idat)), width=header["width"], height=header["height"], channels=channels)
        alpha_index = channels - 1
        alpha = [row[index] for row in rows for index in range(alpha_index, len(row), channels)]
        minimum, maximum = min(alpha), max(alpha)
        result.update({
            "alpha_extrema": [minimum, maximum],
            "transparent_pixel_count": sum(value == 0 for value in alpha),
            "fully_opaque_pixel_count": sum(value == 255 for value in alpha),
            "actual_transparent_pixels": minimum == 0,
            "truth_status": "PNG_ALPHA_PIXELS_DECODED",
        })
    return result


def _profile_path(root: Path | str) -> Path:
    return Path(root).resolve() / "state" / "visual-use-profile.json"


def _load_profile(root: Path | str) -> dict[str, Any]:
    path = _profile_path(root)
    if not path.exists():
        return {"schema": VISUAL_USE_PROFILE_SCHEMA, "contexts": {}}
    value = json.loads(path.read_text(encoding="utf-8"))
    if value.get("schema") != VISUAL_USE_PROFILE_SCHEMA or not isinstance(value.get("contexts"), dict):
        raise ValueError("visual-use profile has unsupported schema")
    return value


def _lesson_patch(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError("lesson patch must be an object")
    unknown = set(value) - set(PATCH_LIST_FIELDS) - {"scene", "technical_requirements"}
    if unknown:
        raise ValueError(f"unsupported lesson patch field: {', '.join(sorted(unknown))}")
    result: dict[str, Any] = {}
    for field in PATCH_LIST_FIELDS:
        if field in value:
            if not isinstance(value[field], list):
                raise TypeError(f"{field} must be a list")
            result[field] = _stable_unique(value[field])
    if "scene" in value:
        scene = value["scene"]
        if not isinstance(scene, dict):
            raise TypeError("lesson scene patch must be an object")
        unknown_scene = set(scene) - set(PATCH_SCENE_FIELDS)
        if unknown_scene:
            raise ValueError(f"unsupported lesson scene field: {', '.join(sorted(unknown_scene))}")
        result["scene"] = {field: _text(scene[field], f"scene.{field}", 1000) for field in scene}
    if "technical_requirements" in value:
        technical = value["technical_requirements"]
        if not isinstance(technical, dict):
            raise TypeError("technical_requirements must be an object")
        result["technical_requirements"] = copy.deepcopy(technical)
    if not result:
        raise ValueError("lesson patch must contain at least one supported change")
    return result


def record_visual_use(root: Path | str, observation: Any) -> dict[str, Any]:
    if not isinstance(observation, dict):
        raise TypeError("visual-use observation must be an object")
    context_key = _text(observation.get("context_key"), "context_key", 300)
    source = _text(observation.get("source"), "source", 300)
    executor = _text(observation.get("executor"), "executor", 300)
    artifact_path = Path(_text(observation.get("artifact_path"), "artifact_path", 2000)).expanduser()
    if not artifact_path.is_absolute():
        artifact_path = (Path(root) / artifact_path).resolve()
    inspection = inspect_png(artifact_path)

    criteria = observation.get("criteria", {})
    if not isinstance(criteria, dict):
        raise TypeError("criteria must be an object")
    normalized_criteria: dict[str, str] = {}
    for name, status in criteria.items():
        key = _text(name, "criterion", 120)
        value = str(status).strip().upper()
        if value not in {"PASS", "FAIL", "UNKNOWN"}:
            raise ValueError("criterion status must be PASS, FAIL, or UNKNOWN")
        normalized_criteria[key] = value

    requirements = observation.get("technical_requirements", {})
    if not isinstance(requirements, dict):
        raise TypeError("technical_requirements must be an object")
    technical: dict[str, bool] = {}
    if requirements.get("real_alpha") is not None:
        technical["real_alpha"] = bool(inspection["alpha_channel"] and inspection["actual_transparent_pixels"])

    lessons_value = observation.get("lessons", [])
    if not isinstance(lessons_value, list):
        raise TypeError("lessons must be a list")
    lessons = []
    for lesson in lessons_value:
        if not isinstance(lesson, dict):
            raise TypeError("each lesson must be an object")
        lessons.append({
            "id": _text(lesson.get("id"), "lesson.id", 160),
            "evidence": _text(lesson.get("evidence"), "lesson.evidence", 1000),
            "patch": _lesson_patch(lesson.get("patch")),
        })

    evidence_core = {
        "schema": VISUAL_USE_EVIDENCE_SCHEMA,
        "context_key": context_key,
        "recipe_sha256": str(observation.get("recipe_sha256", "")).strip() or None,
        "artifact_sha256": inspection["sha256"],
        "source": source,
        "executor": executor,
        "technical": technical,
        "criteria": normalized_criteria,
        "lessons": lessons,
    }
    evidence_digest = _digest(evidence_core)
    profile = _load_profile(root)
    contexts = profile["contexts"]
    if context_key not in contexts and len(contexts) >= MAX_CONTEXTS:
        raise ValueError(f"visual-use profile exceeds {MAX_CONTEXTS} contexts")
    context = contexts.setdefault(context_key, {
        "use_count": 0,
        "technical": {},
        "criteria": {},
        "lessons": {},
        "dedup_digests": [],
    })
    if evidence_digest in context["dedup_digests"]:
        return {
            "status": "VISUAL_USE_ALREADY_RECORDED",
            "evidence_digest": evidence_digest,
            "context_key": context_key,
            "inspection": inspection,
            "profile_path": str(_profile_path(root)),
        }

    context["use_count"] += 1
    for name, passed in technical.items():
        stat = context["technical"].setdefault(name, {"pass": 0, "fail": 0})
        stat["pass" if passed else "fail"] += 1
    for name, status in normalized_criteria.items():
        stat = context["criteria"].setdefault(name, {"pass": 0, "fail": 0, "unknown": 0})
        stat[status.casefold()] += 1
    for lesson in lessons:
        existing = context["lessons"].get(lesson["id"])
        if existing is not None and existing["patch"] != lesson["patch"]:
            raise ValueError(f"lesson {lesson['id']} conflicts with its existing exact-context patch")
        if existing is None:
            if len(context["lessons"]) >= MAX_LESSONS_PER_CONTEXT:
                raise ValueError(f"visual-use context exceeds {MAX_LESSONS_PER_CONTEXT} lessons")
            existing = {
                "status": "ACTIVE_EXACT_CONTEXT",
                "confirmations": 0,
                "patch": lesson["patch"],
                "last_evidence": lesson["evidence"],
                "last_evidence_digest": None,
            }
            context["lessons"][lesson["id"]] = existing
        existing["confirmations"] += 1
        existing["last_evidence"] = lesson["evidence"]
        existing["last_evidence_digest"] = evidence_digest
    context["dedup_digests"].append(evidence_digest)
    context["dedup_digests"] = context["dedup_digests"][-MAX_DEDUP_DIGESTS:]
    atomic_write_json(_profile_path(root), profile)
    return {
        "status": "VISUAL_USE_PROFILE_UPDATED",
        "truth_status": "OBSERVED_EXACT_CONTEXT_LESSONS_ACTIVE_FOR_REPLAY",
        "evidence_digest": evidence_digest,
        "context_key": context_key,
        "inspection": inspection,
        "active_lesson_ids": sorted(context["lessons"]),
        "profile_path": str(_profile_path(root)),
        "automatic_source_modification": False,
        "global_generalization": False,
    }


def inspect_visual_learning(root: Path | str, *, context_key: Any = None) -> dict[str, Any]:
    profile = _load_profile(root)
    if context_key is None:
        contexts = copy.deepcopy(profile["contexts"])
        selected = None
    else:
        selected = _text(context_key, "context_key", 300)
        contexts = {selected: copy.deepcopy(profile["contexts"].get(selected))} if selected in profile["contexts"] else {}
    for context in contexts.values():
        context.pop("dedup_digests", None)
    return {
        "schema": VISUAL_USE_PROFILE_SCHEMA,
        "truth_status": "CURRENT_EXACT_CONTEXT_VISUAL_USE_PROFILE",
        "context_key": selected,
        "contexts": contexts,
        "raw_prompt_history_stored": False,
        "raw_image_history_stored": False,
        "automatic_source_modification": False,
        "global_generalization": False,
    }


def _apply_lessons(request: dict[str, Any], lessons: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    adapted = copy.deepcopy(request)
    applied: list[str] = []
    for lesson_id in sorted(lessons):
        lesson = lessons[lesson_id]
        if lesson.get("status") != "ACTIVE_EXACT_CONTEXT":
            continue
        patch = lesson["patch"]
        for field in PATCH_LIST_FIELDS:
            if field in patch:
                target = field.removesuffix("_add")
                adapted[target] = _stable_unique(list(adapted.get(target, [])) + patch[field])
        if "scene" in patch:
            scene = adapted.setdefault("scene", {})
            for field, value in patch["scene"].items():
                scene.setdefault(field, value)
        if "technical_requirements" in patch:
            technical = adapted.setdefault("technical_requirements", {})
            for field, value in patch["technical_requirements"].items():
                technical.setdefault(field, copy.deepcopy(value))
        applied.append(lesson_id)
    return adapted, applied


def compile_adaptive_visual_recipe(root: Path | str, request: Any) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise TypeError("adaptive visual request must be an object")
    context_key = _text(request.get("context_key"), "context_key", 300)
    profile = _load_profile(root)
    context = profile["contexts"].get(context_key)
    adapted, applied = _apply_lessons(request, context.get("lessons", {}) if context else {})
    recipe = compile_visual_recipe(adapted)
    return {
        "schema": "axm.adaptive-visual-recipe/v0.1",
        "context_key": context_key,
        "learning_status": "EXACT_CONTEXT_LESSONS_REPLAYED" if applied else "NO_EXACT_CONTEXT_LESSONS",
        "applied_lesson_ids": applied,
        "adapted_request": adapted,
        "recipe": recipe,
        "truth": {
            "observationsAreContextBound": True,
            "oneContextDoesNotBecomeGlobalLaw": True,
            "explicitRequestOverridesLearnedSceneDefaults": True,
            "automaticSourceModification": False,
        },
    }

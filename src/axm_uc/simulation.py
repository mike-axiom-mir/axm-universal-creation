from __future__ import annotations

import copy
import math
from typing import Any

from .paintgun import (
    PAINTGUN_THOUGHT_SCHEMA,
    PAINT_CHANNELS,
    PaintgunError,
    render_cinematic_svg,
    thought_digest,
    validate_visual_thought,
)


MAX_SIMULATION_ITERATIONS = 32
KNOWN_IMPROVEMENT_RULES = (
    "complete-paint-channel-dependencies",
    "derive-neutral-surface-channels",
    "choose-higher-contrast-known-color",
    "fit-known-shapes-inside-canvas",
    "clamp-known-render-parameters",
)


class SimulationError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _required_text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise SimulationError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise SimulationError(f"{label} exceeds its {maximum}-character bound")
    return text


def _number(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise SimulationError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise SimulationError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise SimulationError(f"{label} must be <= {maximum}")
    return result


def _initial_thought(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise SimulationError("thought must be an object")
    canvas = raw.get("canvas")
    if not isinstance(canvas, dict):
        raise SimulationError("thought.canvas must be an object")
    width = int(_number(canvas.get("width"), "thought.canvas.width", 1, 8192))
    height = int(_number(canvas.get("height"), "thought.canvas.height", 1, 8192))
    background = str(canvas.get("background", "#000000"))
    objects = raw.get("objects")
    if not isinstance(objects, list) or not objects:
        raise SimulationError("thought.objects must be a non-empty list")
    if len(objects) > 128:
        raise SimulationError("thought.objects exceeds the 128-object simulation bound")
    normalized_objects: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw_object in enumerate(objects):
        if not isinstance(raw_object, dict):
            raise SimulationError(f"thought.objects[{index}] must be an object")
        object_id = _required_text(raw_object.get("id"), f"thought.objects[{index}].id", 120)
        if object_id in ids:
            raise SimulationError("thought object ids must be unique", {"duplicate": object_id})
        ids.add(object_id)
        row = copy.deepcopy(raw_object)
        row["id"] = object_id
        row["z"] = int(row.get("z", index))
        normalized_objects.append(row)
    camera = raw.get("camera", {})
    if not isinstance(camera, dict):
        raise SimulationError("thought.camera must be an object")
    return {
        "schema": PAINTGUN_THOUGHT_SCHEMA,
        "intent": _required_text(raw.get("intent", "visual creation"), "thought.intent"),
        "canvas": {"width": width, "height": height, "background": background},
        "camera": {
            "x": float(camera.get("x", 0)),
            "y": float(camera.get("y", 0)),
            "zoom": float(camera.get("zoom", 1)),
        },
        "objects": normalized_objects,
    }


def _hex_rgb(value: str) -> tuple[int, int, int] | None:
    text = str(value).strip()
    if len(text) not in {7, 9} or not text.startswith("#"):
        return None
    try:
        return tuple(int(text[index:index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError:
        return None


def _relative_luminance(color: str) -> float | None:
    rgb = _hex_rgb(color)
    if rgb is None:
        return None
    channels = []
    for value in rgb:
        c = value / 255
        channels.append(c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4)
    return channels[0] * 0.2126 + channels[1] * 0.7152 + channels[2] * 0.0722


def _contrast_ratio(a: str, b: str) -> float | None:
    first = _relative_luminance(a)
    second = _relative_luminance(b)
    if first is None or second is None:
        return None
    high, low = max(first, second), min(first, second)
    return (high + 0.05) / (low + 0.05)


def _alternatives_for(alternatives: Any, object_id: str, channel: str) -> list[Any]:
    if not isinstance(alternatives, dict):
        return []
    by_object = alternatives.get(object_id)
    if not isinstance(by_object, dict):
        return []
    rows = by_object.get(channel)
    return copy.deepcopy(rows) if isinstance(rows, list) else []


def _channel_default(defaults: Any, channel: str) -> Any:
    if not isinstance(defaults, dict) or channel not in defaults:
        return None
    return copy.deepcopy(defaults[channel])


def _known_gaps(thought: dict[str, Any], defaults: Any, palette: Any) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    known_palette = [value for value in palette if isinstance(value, str)] if isinstance(palette, list) else []
    for obj in thought["objects"]:
        for channel in PAINT_CHANNELS:
            if channel in obj:
                continue
            can_derive = channel in {"material", "light", "shade", "skin"}
            if channel == "color" and known_palette:
                can_derive = True
            if _channel_default(defaults, channel) is not None:
                can_derive = True
            gaps.append({
                "object_id": obj["id"],
                "type": "missing-paint-channel",
                "channel": channel,
                "known_improvement_available": can_derive,
            })
        if "shape" in obj and isinstance(obj["shape"], dict):
            kind = str(obj["shape"].get("kind", "")).casefold()
            if kind not in {"rect", "circle", "ellipse", "polygon", "path"}:
                gaps.append({
                    "object_id": obj["id"],
                    "type": "unsupported-shape",
                    "kind": kind,
                    "known_improvement_available": False,
                })
    return gaps


def _complete_channels(thought: dict[str, Any], defaults: Any, palette: Any) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    palette_rows = [str(value) for value in palette] if isinstance(palette, list) else []
    for obj in thought["objects"]:
        object_id = obj["id"]
        for channel in PAINT_CHANNELS:
            if channel in obj:
                continue
            configured = _channel_default(defaults, channel)
            if configured is not None:
                obj[channel] = configured
                changes.append({"rule": "complete-paint-channel-dependencies", "object_id": object_id, "channel": channel, "source": "caller-default"})
                continue
            if channel == "color" and palette_rows:
                obj[channel] = {"fill": palette_rows[0], "stroke": palette_rows[0], "stroke_width": 0}
                changes.append({"rule": "complete-paint-channel-dependencies", "object_id": object_id, "channel": channel, "source": "known-palette"})
            elif channel == "material":
                obj[channel] = {"name": "neutral-surface", "metallic": 0, "roughness": 0.5, "opacity": 1, "emission": 0}
                changes.append({"rule": "derive-neutral-surface-channels", "object_id": object_id, "channel": channel})
            elif channel == "light":
                obj[channel] = {"color": "#FFFFFF", "intensity": 0, "x": 0, "y": 0, "radius": 0}
                changes.append({"rule": "derive-neutral-surface-channels", "object_id": object_id, "channel": channel})
            elif channel == "shade":
                obj[channel] = {"color": "#000000", "dx": 0, "dy": 0, "blur": 0, "opacity": 0}
                changes.append({"rule": "derive-neutral-surface-channels", "object_id": object_id, "channel": channel})
            elif channel == "skin" and isinstance(obj.get("color"), dict) and isinstance(obj["color"].get("fill"), str):
                obj[channel] = {"kind": "solid", "colors": [obj["color"]["fill"]], "angle": 0}
                changes.append({"rule": "derive-neutral-surface-channels", "object_id": object_id, "channel": channel})
    return changes


def _improve_contrast(thought: dict[str, Any], alternatives: Any, palette: Any, criteria: Any) -> list[dict[str, Any]]:
    if not isinstance(criteria, dict):
        return []
    minimum = criteria.get("minimum_contrast")
    if minimum is None:
        return []
    minimum_value = _number(minimum, "criteria.minimum_contrast", 1, 21)
    background = thought["canvas"]["background"]
    shared_palette = [str(value) for value in palette] if isinstance(palette, list) else []
    changes: list[dict[str, Any]] = []
    for obj in thought["objects"]:
        color = obj.get("color")
        if not isinstance(color, dict) or not isinstance(color.get("fill"), str):
            continue
        current = _contrast_ratio(background, color["fill"])
        if current is None or current >= minimum_value:
            continue
        candidates: list[str] = []
        for alternative in _alternatives_for(alternatives, obj["id"], "color"):
            if isinstance(alternative, str):
                candidates.append(alternative)
            elif isinstance(alternative, dict) and isinstance(alternative.get("fill"), str):
                candidates.append(alternative["fill"])
        candidates.extend(shared_palette)
        scored = [
            (ratio, candidate)
            for candidate in candidates
            if (ratio := _contrast_ratio(background, candidate)) is not None and ratio > current
        ]
        if not scored:
            continue
        scored.sort(key=lambda row: (-row[0], row[1]))
        best_ratio, best = scored[0]
        color["fill"] = best
        skin = obj.get("skin")
        skin_colors = skin.get("colors") if isinstance(skin, dict) else None
        first_skin_color = skin_colors[0] if isinstance(skin_colors, list) and skin_colors else None
        if first_skin_color is not None and color.get("stroke") == first_skin_color:
            color["stroke"] = best
        if isinstance(skin, dict) and skin.get("kind") == "solid":
            skin["colors"] = [best]
        changes.append({
            "rule": "choose-higher-contrast-known-color",
            "object_id": obj["id"],
            "before_ratio": current,
            "after_ratio": best_ratio,
            "selected_fill": best,
            "minimum_contrast": minimum_value,
        })
    return changes


def _fit_shape(shape: dict[str, Any], width: float, height: float) -> bool:
    changed = False
    kind = str(shape.get("kind", "")).casefold()
    if kind == "rect" and all(key in shape for key in ("x", "y", "width", "height")):
        old = (shape["x"], shape["y"], shape["width"], shape["height"])
        shape["width"] = max(0.0, min(float(shape["width"]), width))
        shape["height"] = max(0.0, min(float(shape["height"]), height))
        shape["x"] = max(0.0, min(float(shape["x"]), width - shape["width"]))
        shape["y"] = max(0.0, min(float(shape["y"]), height - shape["height"]))
        changed = old != (shape["x"], shape["y"], shape["width"], shape["height"])
    elif kind == "circle" and all(key in shape for key in ("cx", "cy", "r")):
        old = (shape["cx"], shape["cy"], shape["r"])
        shape["r"] = max(0.0, min(float(shape["r"]), width / 2, height / 2))
        shape["cx"] = max(shape["r"], min(float(shape["cx"]), width - shape["r"]))
        shape["cy"] = max(shape["r"], min(float(shape["cy"]), height - shape["r"]))
        changed = old != (shape["cx"], shape["cy"], shape["r"])
    elif kind == "ellipse" and all(key in shape for key in ("cx", "cy", "rx", "ry")):
        old = (shape["cx"], shape["cy"], shape["rx"], shape["ry"])
        shape["rx"] = max(0.0, min(float(shape["rx"]), width / 2))
        shape["ry"] = max(0.0, min(float(shape["ry"]), height / 2))
        shape["cx"] = max(shape["rx"], min(float(shape["cx"]), width - shape["rx"]))
        shape["cy"] = max(shape["ry"], min(float(shape["cy"]), height - shape["ry"]))
        changed = old != (shape["cx"], shape["cy"], shape["rx"], shape["ry"])
    elif kind == "polygon" and isinstance(shape.get("points"), list):
        normalized = []
        for point in shape["points"]:
            if not isinstance(point, list) or len(point) != 2:
                return changed
            normalized.append([max(0.0, min(float(point[0]), width)), max(0.0, min(float(point[1]), height))])
        changed = normalized != shape["points"]
        shape["points"] = normalized
    return changed


def _fit_canvas(thought: dict[str, Any], criteria: Any) -> list[dict[str, Any]]:
    if not isinstance(criteria, dict) or criteria.get("fit_canvas") is not True:
        return []
    width = float(thought["canvas"]["width"])
    height = float(thought["canvas"]["height"])
    changes: list[dict[str, Any]] = []
    for obj in thought["objects"]:
        shape = obj.get("shape")
        if isinstance(shape, dict) and _fit_shape(shape, width, height):
            changes.append({"rule": "fit-known-shapes-inside-canvas", "object_id": obj["id"]})
    return changes


def _clamp(value: Any, minimum: float, maximum: float) -> tuple[Any, bool]:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return value, False
    clamped = max(minimum, min(float(value), maximum))
    return clamped, clamped != value


def _clamp_parameters(thought: dict[str, Any]) -> list[dict[str, Any]]:
    changes: list[dict[str, Any]] = []
    specs = {
        "material": {"metallic": (0, 1), "roughness": (0, 1), "opacity": (0, 1), "emission": (0, 4)},
        "light": {"intensity": (0, 4), "radius": (0, 8192)},
        "shade": {"opacity": (0, 1), "blur": (0, 256)},
    }
    for obj in thought["objects"]:
        for channel, fields in specs.items():
            row = obj.get(channel)
            if not isinstance(row, dict):
                continue
            for field, (minimum, maximum) in fields.items():
                if field not in row:
                    continue
                next_value, changed = _clamp(row[field], minimum, maximum)
                if changed:
                    before = row[field]
                    row[field] = next_value
                    changes.append({
                        "rule": "clamp-known-render-parameters",
                        "object_id": obj["id"],
                        "channel": channel,
                        "field": field,
                        "before": before,
                        "after": next_value,
                    })
    return changes


def _projection(thought: dict[str, Any]) -> dict[str, Any]:
    try:
        normalized = validate_visual_thought(thought)
        svg = render_cinematic_svg(normalized)
        return {"available": True, "thought_digest": thought_digest(normalized), "svg": svg}
    except PaintgunError as exc:
        return {"available": False, "reason": str(exc), "details": exc.details}


def simulate_until_no_known_improvements(
    raw_thought: Any,
    *,
    defaults: Any = None,
    alternatives: Any = None,
    palette: Any = None,
    criteria: Any = None,
    max_iterations: int = MAX_SIMULATION_ITERATIONS,
) -> dict[str, Any]:
    if isinstance(max_iterations, bool) or not isinstance(max_iterations, int) or max_iterations < 1 or max_iterations > MAX_SIMULATION_ITERATIONS:
        raise SimulationError(f"max_iterations must be an integer from 1 to {MAX_SIMULATION_ITERATIONS}")
    thought = _initial_thought(raw_thought)
    palette = palette if isinstance(palette, list) else []
    history: list[dict[str, Any]] = []

    for iteration in range(1, max_iterations + 1):
        before_digest = thought_digest(thought)
        changes: list[dict[str, Any]] = []
        changes.extend(_complete_channels(thought, defaults, palette))
        changes.extend(_clamp_parameters(thought))
        changes.extend(_fit_canvas(thought, criteria))
        changes.extend(_improve_contrast(thought, alternatives, palette, criteria))
        gaps = _known_gaps(thought, defaults, palette)
        frame = _projection(thought)
        history.append({
            "iteration": iteration,
            "before_digest": before_digest,
            "after_digest": thought_digest(thought),
            "improvements": copy.deepcopy(changes),
            "known_gaps": copy.deepcopy(gaps),
            "cinematic_frame": frame,
        })
        if changes:
            continue
        unresolved = [gap for gap in gaps if gap.get("known_improvement_available") is not True]
        if unresolved:
            return {
                "operation": "simulate-creation",
                "truth_status": "SIMULATED_CREATION_WITH_EXPLICIT_KNOWN_GAPS",
                "status": "HOLD_KNOWN_GAPS_NO_AVAILABLE_IMPROVEMENT",
                "thought": thought,
                "thought_digest": thought_digest(thought),
                "iterations": iteration,
                "history": history,
                "known_gaps": gaps,
                "known_improvement_rules": list(KNOWN_IMPROVEMENT_RULES),
                "cinematic_projection": frame,
                "materialization_ready": False,
                "perfect_claimed": False,
            }
        try:
            normalized = validate_visual_thought(thought)
        except PaintgunError as exc:
            return {
                "operation": "simulate-creation",
                "truth_status": "SIMULATED_CREATION_REACHED_UNSUPPORTED_STATE",
                "status": "HOLD_SIMULATION_STATE_NOT_MATERIALIZABLE",
                "thought": thought,
                "thought_digest": thought_digest(thought),
                "iterations": iteration,
                "history": history,
                "known_gaps": [{"type": "paintgun-validation", "reason": str(exc), "details": exc.details}],
                "known_improvement_rules": list(KNOWN_IMPROVEMENT_RULES),
                "cinematic_projection": frame,
                "materialization_ready": False,
                "perfect_claimed": False,
            }
        svg = render_cinematic_svg(normalized)
        digest = thought_digest(normalized)
        return {
            "operation": "simulate-creation",
            "truth_status": "NO_CURRENT_REGISTERED_SIMULATION_RULE_CAN_IMPROVE_THIS_THOUGHT",
            "status": "NO_KNOWN_IMPROVEMENTS",
            "thought": normalized,
            "thought_digest": digest,
            "iterations": iteration,
            "history": history,
            "known_gaps": [],
            "known_improvement_rules": list(KNOWN_IMPROVEMENT_RULES),
            "cinematic_projection": {"available": True, "thought_digest": digest, "svg": svg},
            "materialization_ready": True,
            "perfect_claimed": False,
            "stop_meaning": "no currently registered deterministic improvement rule can identify a further change; new evidence or a new improvement rule may reopen simulation",
            "limitations": [
                "NO_KNOWN_IMPROVEMENTS is not a claim of perfection or optimality",
                "the current simulator knows structural paint-channel completion, bounded parameter repair, known-shape canvas fit, and contrast improvement from supplied alternatives/palette",
                "semantic quality, physical material realism, animation, browser behavior, and human aesthetic preference require additional evidence providers or future simulation rules",
            ],
        }

    gaps = _known_gaps(thought, defaults, palette)
    return {
        "operation": "simulate-creation",
        "truth_status": "SIMULATION_STOPPED_AT_EXPLICIT_ITERATION_BOUND",
        "status": "HOLD_SIMULATION_ITERATION_BOUND",
        "thought": thought,
        "thought_digest": thought_digest(thought),
        "iterations": max_iterations,
        "history": history,
        "known_gaps": gaps,
        "known_improvement_rules": list(KNOWN_IMPROVEMENT_RULES),
        "cinematic_projection": _projection(thought),
        "materialization_ready": False,
        "perfect_claimed": False,
    }


def operate_simulation(root: Any, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "simulate-creation")).strip().casefold()
    if operation in {"resolve-vector-cells", "vector-cell-thought", "adaptive-vector-scene"} or "fabric" in inputs:
        from .vector_cells import VectorCellError, resolve_vector_cells

        try:
            return resolve_vector_cells(
                inputs.get("fabric"),
                observation_scale=inputs.get("observation_scale"),
                choice=inputs.get("choice", "default"),
            )
        except VectorCellError as exc:
            raise SimulationError(str(exc), exc.details) from exc

    del root
    return simulate_until_no_known_improvements(
        inputs.get("thought"),
        defaults=inputs.get("defaults"),
        alternatives=inputs.get("alternatives"),
        palette=inputs.get("palette"),
        criteria=inputs.get("criteria"),
        max_iterations=inputs.get("max_iterations", MAX_SIMULATION_ITERATIONS),
    )

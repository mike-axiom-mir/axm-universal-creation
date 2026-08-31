from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .atomic import atomic_write_json
from .paintgun import PaintgunError, render_cinematic_svg, thought_digest, validate_visual_thought
from .simulation import SimulationError, simulate_until_no_known_improvements
from .vector_cells import VectorCellError, resolve_vector_cells


MORPH_SCHEMA = "axm.chameleon-morph/v0.1"
MATERIAL_GRAPH_SCHEMA = "axm.material-graph/v0.1"
ENVIRONMENT_SCHEMA = "axm.chameleon-environment-adaptation/v0.1"
REALITY_FEEDBACK_SCHEMA = "axm.simulation-reality-feedback/v0.1"
CALIBRATION_LEDGER_SCHEMA = "axm.simulation-calibration-ledger/v0.1"
MAX_CALIBRATION_ENTRIES = 2048
MAX_MORPH_OBJECTS = 128
HEX_DIGITS = set("0123456789abcdefABCDEF")


class ChameleonError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 500) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ChameleonError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise ChameleonError(f"{label} exceeds {maximum} characters")
    return text


def _num(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise ChameleonError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise ChameleonError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise ChameleonError(f"{label} must be <= {maximum}")
    return result


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(maximum, value))


def _lerp(a: float, b: float, t: float) -> float:
    return a + (b - a) * t


def _is_hex_color(value: Any) -> bool:
    if not isinstance(value, str) or len(value) not in {7, 9} or not value.startswith("#"):
        return False
    return all(char in HEX_DIGITS for char in value[1:])


def _rgba(value: str) -> tuple[int, int, int, int]:
    raw = value[1:]
    if len(raw) == 6:
        raw += "FF"
    return tuple(int(raw[index:index + 2], 16) for index in (0, 2, 4, 6))  # type: ignore[return-value]


def _blend_color(a: str, b: str, t: float) -> str:
    first = _rgba(a)
    second = _rgba(b)
    values = [round(_lerp(first[index], second[index], t)) for index in range(4)]
    suffix = "" if len(a) == len(b) == 7 and values[3] == 255 else f"{values[3]:02X}"
    return f"#{values[0]:02X}{values[1]:02X}{values[2]:02X}{suffix}"


def _blend_value(a: Any, b: Any, t: float) -> Any:
    if isinstance(a, bool) or isinstance(b, bool):
        return copy.deepcopy(a if t < 0.5 else b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return _lerp(float(a), float(b), t)
    if _is_hex_color(a) and _is_hex_color(b):
        return _blend_color(str(a), str(b), t)
    if isinstance(a, dict) and isinstance(b, dict):
        result: dict[str, Any] = {}
        for key in sorted(set(a) | set(b)):
            if key in a and key in b:
                result[key] = _blend_value(a[key], b[key], t)
            elif key in a:
                result[key] = copy.deepcopy(a[key] if t < 0.5 else b.get(key))
            else:
                result[key] = copy.deepcopy(a.get(key) if t < 0.5 else b[key])
        return result
    if isinstance(a, list) and isinstance(b, list) and len(a) == len(b):
        return [_blend_value(first, second, t) for first, second in zip(a, b)]
    return copy.deepcopy(a if t < 0.5 else b)


def _shape_compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    kind = str(a.get("kind", "")).casefold()
    if kind != str(b.get("kind", "")).casefold():
        return False
    if kind == "polygon":
        return isinstance(a.get("points"), list) and isinstance(b.get("points"), list) and len(a["points"]) == len(b["points"])
    if kind == "path":
        return str(a.get("d", "")) == str(b.get("d", ""))
    return kind in {"rect", "circle", "ellipse"}


def _skin_compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    if a.get("kind") != b.get("kind"):
        return False
    first = a.get("colors")
    second = b.get("colors")
    return isinstance(first, list) and isinstance(second, list) and len(first) == len(second)


def _objects_morph_compatible(a: dict[str, Any], b: dict[str, Any]) -> bool:
    return _shape_compatible(a.get("shape", {}), b.get("shape", {})) and _skin_compatible(a.get("skin", {}), b.get("skin", {}))


def _fade_object(raw: dict[str, Any], alpha: float, *, object_id: str) -> dict[str, Any]:
    out = copy.deepcopy(raw)
    out["id"] = object_id
    material = out.setdefault("material", {})
    material["opacity"] = _clamp(float(material.get("opacity", 1)) * alpha, 0, 1)
    material["emission"] = _clamp(float(material.get("emission", 0)) * alpha, 0, 4)
    light = out.setdefault("light", {})
    light["intensity"] = _clamp(float(light.get("intensity", 0)) * alpha, 0, 4)
    shade = out.setdefault("shade", {})
    shade["opacity"] = _clamp(float(shade.get("opacity", 0)) * alpha, 0, 1)
    return out


def _morph_object(a: dict[str, Any], b: dict[str, Any], t: float) -> dict[str, Any]:
    out = copy.deepcopy(a)
    out["id"] = a["id"]
    out["z"] = round(_lerp(float(a.get("z", 0)), float(b.get("z", 0)), t))
    for channel in ("shape", "material", "color", "light", "shade", "skin"):
        out[channel] = _blend_value(a[channel], b[channel], t)
    return out


def morph_thoughts(from_thought: Any, to_thought: Any, factor: Any) -> dict[str, Any]:
    t = _num(factor, "factor", 0, 1)
    try:
        first = validate_visual_thought(from_thought)
        second = validate_visual_thought(to_thought)
    except PaintgunError as exc:
        raise ChameleonError(str(exc), exc.details) from exc

    if first["canvas"]["width"] != second["canvas"]["width"] or first["canvas"]["height"] != second["canvas"]["height"]:
        raise ChameleonError("morph endpoints must use the same canvas dimensions")
    if t == 0:
        result = first
        trace = [{"mode": "exact-source-endpoint"}]
    elif t == 1:
        result = second
        trace = [{"mode": "exact-target-endpoint"}]
    else:
        by_first = {row["id"]: row for row in first["objects"]}
        by_second = {row["id"]: row for row in second["objects"]}
        objects: list[dict[str, Any]] = []
        trace: list[dict[str, Any]] = []
        for object_id in sorted(set(by_first) | set(by_second)):
            left = by_first.get(object_id)
            right = by_second.get(object_id)
            if left is not None and right is not None and _objects_morph_compatible(left, right):
                objects.append(_morph_object(left, right, t))
                trace.append({"object_id": object_id, "mode": "continuous-channel-and-geometry-interpolation"})
            elif left is not None and right is not None:
                objects.append(_fade_object(left, 1 - t, object_id=f"{object_id}::morph-source"))
                objects.append(_fade_object(right, t, object_id=f"{object_id}::morph-target"))
                trace.append({"object_id": object_id, "mode": "continuous-crossfade-incompatible-geometry"})
            elif left is not None:
                objects.append(_fade_object(left, 1 - t, object_id=object_id))
                trace.append({"object_id": object_id, "mode": "continuous-fade-out-source-only"})
            elif right is not None:
                objects.append(_fade_object(right, t, object_id=object_id))
                trace.append({"object_id": object_id, "mode": "continuous-fade-in-target-only"})
        if not objects or len(objects) > MAX_MORPH_OBJECTS:
            raise ChameleonError(
                "morph intermediate exceeds the current Paintgun object bound",
                {"resolved_objects": len(objects), "maximum": MAX_MORPH_OBJECTS},
            )
        raw = {
            "intent": f"continuous morph: {first['intent']} -> {second['intent']}",
            "canvas": {
                "width": first["canvas"]["width"],
                "height": first["canvas"]["height"],
                "background": _blend_color(first["canvas"]["background"], second["canvas"]["background"], t),
            },
            "camera": _blend_value(first["camera"], second["camera"], t),
            "objects": objects,
        }
        try:
            result = validate_visual_thought(raw)
        except PaintgunError as exc:
            raise ChameleonError("morph intermediate is not Paintgun-materializable", {"reason": str(exc), "details": exc.details}) from exc

    digest = thought_digest(result)
    return {
        "schema": MORPH_SCHEMA,
        "operation": "morph-thoughts",
        "truth_status": "DETERMINISTIC_CONTINUOUS_VISUAL_STATE_MORPH",
        "factor": t,
        "from_digest": thought_digest(first),
        "to_digest": thought_digest(second),
        "thought": result,
        "thought_digest": digest,
        "morph_trace": trace,
        "cinematic_projection": {"available": True, "thought_digest": digest, "svg": render_cinematic_svg(result)},
        "limitations": [
            "compatible shapes interpolate geometry and channels continuously",
            "incompatible geometry uses a continuous source/target crossfade rather than claiming impossible topology interpolation",
            "SVG path geometry interpolates only when path data is identical; otherwise it crossfades",
        ],
    }


def morph_vector_cells(
    fabric: Any,
    *,
    from_state: Any,
    to_state: Any,
    factor: Any,
) -> dict[str, Any]:
    if not isinstance(from_state, dict) or not isinstance(to_state, dict):
        raise ChameleonError("from_state and to_state must be objects")
    try:
        first = resolve_vector_cells(
            fabric,
            observation_scale=from_state.get("observation_scale"),
            choice=from_state.get("choice", "default"),
        )
        second = resolve_vector_cells(
            fabric,
            observation_scale=to_state.get("observation_scale"),
            choice=to_state.get("choice", "default"),
        )
    except VectorCellError as exc:
        raise ChameleonError(str(exc), exc.details) from exc
    result = morph_thoughts(first["thought"], second["thought"], factor)
    result.update({
        "operation": "morph-vector-cells",
        "fabric_digest": first["fabric_digest"],
        "from_state": copy.deepcopy(from_state),
        "to_state": copy.deepcopy(to_state),
        "from_resolution": first["resolution"],
        "to_resolution": second["resolution"],
    })
    return result


def _material_microstructure(raw: Any) -> dict[str, Any]:
    raw = {} if raw is None else raw
    if not isinstance(raw, dict):
        raise ChameleonError("material_graph.microstructure must be an object")
    kind = str(raw.get("kind", "none")).strip().casefold()
    supported = {"none", "fibers", "stripes", "checker", "noise", "scales"}
    if kind not in supported:
        raise ChameleonError("material microstructure kind is unsupported", {"kind": kind, "supported": sorted(supported)})
    return {
        "kind": kind,
        "scale": _num(raw.get("scale", 1), "material_graph.microstructure.scale", 0.001, 10000),
        "strength": _num(raw.get("strength", 0), "material_graph.microstructure.strength", 0, 4),
        "angle": _num(raw.get("angle", 0), "material_graph.microstructure.angle", -360, 360),
        "seed": int(_num(raw.get("seed", 0), "material_graph.microstructure.seed", 0, 2**31 - 1)),
    }


def compile_material_graph(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") not in {None, MATERIAL_GRAPH_SCHEMA}:
        raise ChameleonError("material graph is missing or has unsupported schema")
    graph_id = _text(raw.get("id", "material-graph"), "material_graph.id", 120)
    base_color = str(raw.get("base_color", "#808080"))
    secondary_color = str(raw.get("secondary_color", base_color))
    if not _is_hex_color(base_color) or not _is_hex_color(secondary_color):
        raise ChameleonError("material graph colors must be #RRGGBB or #RRGGBBAA")
    micro = _material_microstructure(raw.get("microstructure"))
    surface = {
        "name": _text(raw.get("name", graph_id), "material_graph.name", 120),
        "metallic": _num(raw.get("metallic", 0), "material_graph.metallic", 0, 1),
        "roughness": _num(raw.get("roughness", 0.5), "material_graph.roughness", 0, 1),
        "opacity": _num(raw.get("opacity", 1), "material_graph.opacity", 0, 1),
        "emission": _num(raw.get("emission", 0), "material_graph.emission", 0, 4),
        "transmission": _num(raw.get("transmission", 0), "material_graph.transmission", 0, 1),
        "ior": _num(raw.get("ior", 1.5), "material_graph.ior", 1, 3),
        "clearcoat": _num(raw.get("clearcoat", 0), "material_graph.clearcoat", 0, 1),
        "anisotropy": _num(raw.get("anisotropy", 0), "material_graph.anisotropy", -1, 1),
        "subsurface": _num(raw.get("subsurface", 0), "material_graph.subsurface", 0, 1),
        "normal_strength": _num(raw.get("normal_strength", 0), "material_graph.normal_strength", 0, 4),
        "displacement": _num(raw.get("displacement", 0), "material_graph.displacement", -4, 4),
        "microstructure": micro,
    }
    skin_kind = "solid"
    colors = [base_color]
    angle = micro["angle"]
    approximation: list[dict[str, Any]] = []
    if micro["kind"] in {"fibers", "stripes"}:
        skin_kind = "linear-gradient"
        colors = [base_color, secondary_color, base_color]
        approximation.append({"source": "microstructure", "rendered_as": "linear-gradient", "kind": micro["kind"]})
    elif micro["kind"] in {"checker", "noise", "scales"}:
        skin_kind = "radial-gradient"
        colors = [base_color, secondary_color, base_color]
        approximation.append({"source": "microstructure", "rendered_as": "radial-gradient", "kind": micro["kind"]})

    visual_opacity = _clamp(surface["opacity"] * (1 - surface["transmission"] * 0.35), 0, 1)
    visual_roughness = _clamp(surface["roughness"] * (1 - surface["clearcoat"] * 0.35), 0, 1)
    material = copy.deepcopy(surface)
    material.update({
        "opacity": visual_opacity,
        "roughness": visual_roughness,
        "material_graph_schema": MATERIAL_GRAPH_SCHEMA,
        "material_graph_id": graph_id,
        "base_color": base_color,
        "secondary_color": secondary_color,
        "declared_surface_opacity": surface["opacity"],
        "render_model": "svg-approximation-with-retained-rich-material-truth",
    })
    approximation.extend([
        {"source": "transmission", "rendered_as": "partial-opacity-approximation", "value": surface["transmission"]},
        {"source": "clearcoat", "rendered_as": "roughness-reduction-approximation", "value": surface["clearcoat"]},
        {"source": "normal_strength", "rendered_as": "metadata-only-normal-descriptor", "value": surface["normal_strength"]},
        {"source": "displacement", "rendered_as": "metadata-only-displacement-descriptor", "value": surface["displacement"]},
        {"source": "ior", "rendered_as": "metadata-only-refraction-descriptor", "value": surface["ior"]},
        {"source": "anisotropy", "rendered_as": "metadata-only-directional-reflection-descriptor", "value": surface["anisotropy"]},
        {"source": "subsurface", "rendered_as": "metadata-only-subsurface-descriptor", "value": surface["subsurface"]},
    ])
    return {
        "schema": MATERIAL_GRAPH_SCHEMA,
        "operation": "compile-material-graph",
        "truth_status": "RICH_MATERIAL_GRAPH_COMPILED_TO_CURRENT_PAINTGUN_APPROXIMATION",
        "graph_id": graph_id,
        "graph_digest": _digest({**copy.deepcopy(raw), "schema": MATERIAL_GRAPH_SCHEMA}),
        "material": material,
        "color": {"fill": base_color, "stroke": base_color, "stroke_width": 0},
        "skin": {"kind": skin_kind, "colors": colors, "angle": angle},
        "light": {"color": base_color, "intensity": surface["emission"], "x": 0, "y": 0, "radius": 0},
        "shade": {
            "color": "#000000",
            "dx": surface["displacement"] * 0.5,
            "dy": surface["displacement"] * 0.5,
            "blur": _clamp(surface["roughness"] * 8 + surface["subsurface"] * 4, 0, 256),
            "opacity": _clamp(0.2 + surface["normal_strength"] * 0.05, 0, 1),
        },
        "normal_descriptor": {"kind": "procedural-normal", "strength": surface["normal_strength"], "seed": micro["seed"]},
        "displacement_descriptor": {"kind": "scalar-displacement", "amount": surface["displacement"], "scale": micro["scale"]},
        "render_approximation": approximation,
        "limitations": [
            "rich material fields remain inspectable even when the SVG renderer cannot physically realize them",
            "normal, displacement, IOR/refraction, anisotropy and subsurface are retained as material truth descriptors in this renderer generation",
            "procedural microstructure currently maps to bounded SVG gradient approximations rather than arbitrary shader code or raster texture files",
        ],
    }


def apply_material_graph(raw_thought: Any, object_id: Any, graph: Any) -> dict[str, Any]:
    target_id = _text(object_id, "object_id", 120)
    try:
        thought = validate_visual_thought(raw_thought)
    except PaintgunError as exc:
        raise ChameleonError(str(exc), exc.details) from exc
    compiled = compile_material_graph(graph)
    found = False
    for obj in thought["objects"]:
        if obj["id"] != target_id:
            continue
        found = True
        obj["material"] = copy.deepcopy(compiled["material"])
        obj["color"] = copy.deepcopy(compiled["color"])
        obj["skin"] = copy.deepcopy(compiled["skin"])
        obj["light"] = copy.deepcopy(compiled["light"])
        obj["shade"] = copy.deepcopy(compiled["shade"])
    if not found:
        raise ChameleonError("material graph target object was not found", {"object_id": target_id})
    try:
        normalized = validate_visual_thought(thought)
    except PaintgunError as exc:
        raise ChameleonError("compiled material graph produced an invalid Paintgun thought", {"reason": str(exc), "details": exc.details}) from exc
    digest = thought_digest(normalized)
    return {
        "operation": "apply-material-graph",
        "truth_status": "RICH_MATERIAL_GRAPH_APPLIED_WITH_EXPLICIT_RENDER_APPROXIMATION",
        "object_id": target_id,
        "material_graph": compiled,
        "thought": normalized,
        "thought_digest": digest,
        "cinematic_projection": {"available": True, "thought_digest": digest, "svg": render_cinematic_svg(normalized)},
    }


def _sensor_factor(readings: Any, drivers: Any) -> tuple[float, list[dict[str, Any]]]:
    if not isinstance(readings, dict) or not readings:
        raise ChameleonError("environment readings must be a non-empty object")
    if not isinstance(drivers, list) or not drivers:
        raise ChameleonError("environment policy drivers must be a non-empty list")
    weighted = 0.0
    weight_total = 0.0
    trace: list[dict[str, Any]] = []
    for index, driver in enumerate(drivers):
        if not isinstance(driver, dict):
            raise ChameleonError(f"drivers[{index}] must be an object")
        sensor = _text(driver.get("sensor"), f"drivers[{index}].sensor", 120)
        if sensor not in readings:
            raise ChameleonError("environment policy references a missing sensor reading", {"sensor": sensor})
        value = _num(readings[sensor], f"readings.{sensor}")
        minimum = _num(driver.get("min"), f"drivers[{index}].min")
        maximum = _num(driver.get("max"), f"drivers[{index}].max")
        if maximum <= minimum:
            raise ChameleonError(f"drivers[{index}] max must be greater than min")
        weight = _num(driver.get("weight", 1), f"drivers[{index}].weight", 0.0001, 1000)
        normalized = _clamp((value - minimum) / (maximum - minimum), 0, 1)
        if driver.get("invert") is True:
            normalized = 1 - normalized
        weighted += normalized * weight
        weight_total += weight
        trace.append({
            "sensor": sensor,
            "reading": value,
            "min": minimum,
            "max": maximum,
            "weight": weight,
            "invert": driver.get("invert") is True,
            "normalized": normalized,
        })
    return weighted / weight_total, trace


def adapt_environment(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ChameleonError("environment adaptation input must be an object")
    policy = raw.get("policy")
    if not isinstance(policy, dict):
        raise ChameleonError("environment adaptation requires a policy object")
    factor, sensor_trace = _sensor_factor(raw.get("readings"), policy.get("drivers"))
    from_state = policy.get("from_state")
    to_state = policy.get("to_state")
    morph = morph_vector_cells(raw.get("fabric"), from_state=from_state, to_state=to_state, factor=factor)
    return {
        "schema": ENVIRONMENT_SCHEMA,
        "operation": "adapt-environment",
        "truth_status": "EXPLICIT_SENSOR_FUSION_SELECTED_CONTINUOUS_CHAMELEON_STATE",
        "readings": copy.deepcopy(raw.get("readings")),
        "policy_digest": _digest(policy),
        "sensor_trace": sensor_trace,
        "adaptation_factor": factor,
        "from_state": copy.deepcopy(from_state),
        "to_state": copy.deepcopy(to_state),
        "morph": morph,
        "thought": morph["thought"],
        "thought_digest": morph["thought_digest"],
        "cinematic_projection": morph["cinematic_projection"],
        "limitations": [
            "sensor readings are explicit supplied observations; this capability does not pretend hardware sensors were sampled",
            "the current fusion policy is a bounded weighted normalization rule whose inputs and influence remain inspectable",
        ],
    }


def _simulation_thought(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("status") != "NO_KNOWN_IMPROVEMENTS":
        raise ChameleonError("reality feedback requires a completed NO_KNOWN_IMPROVEMENTS simulation")
    thought = raw.get("thought")
    try:
        normalized = validate_visual_thought(thought)
    except PaintgunError as exc:
        raise ChameleonError("simulation thought is not Paintgun-valid", {"reason": str(exc), "details": exc.details}) from exc
    if raw.get("thought_digest") != thought_digest(normalized):
        raise ChameleonError("simulation thought digest does not match its supplied thought")
    return normalized


def _measurement_expected(thought: dict[str, Any], row: dict[str, Any]) -> Any:
    object_id = _text(row.get("object_id"), "measurement.object_id", 120)
    channel = _text(row.get("channel"), "measurement.channel", 40)
    field = _text(row.get("field"), "measurement.field", 80)
    obj = next((candidate for candidate in thought["objects"] if candidate["id"] == object_id), None)
    if obj is None:
        raise ChameleonError("measurement references an unknown object", {"object_id": object_id})
    body = obj.get(channel)
    if not isinstance(body, dict) or field not in body:
        raise ChameleonError("measurement references an unknown object channel field", {"object_id": object_id, "channel": channel, "field": field})
    return body[field]


def compare_reality(simulation: Any, observation: Any, *, context_key: Any) -> dict[str, Any]:
    thought = _simulation_thought(simulation)
    context = _text(context_key, "context_key", 300)
    if not isinstance(observation, dict):
        raise ChameleonError("observation must be an object")
    source = _text(observation.get("source"), "observation.source", 300)
    executor = _text(observation.get("executor"), "observation.executor", 300)
    measurements = observation.get("measurements")
    if not isinstance(measurements, list) or not measurements:
        raise ChameleonError("observation.measurements must be a non-empty list")
    discrepancies: list[dict[str, Any]] = []
    confirmed: list[dict[str, Any]] = []
    for index, raw in enumerate(measurements):
        if not isinstance(raw, dict):
            raise ChameleonError(f"observation.measurements[{index}] must be an object")
        expected = _measurement_expected(thought, raw)
        observed = raw.get("observed")
        tolerance = _num(raw.get("tolerance", 0), f"measurement[{index}].tolerance", 0)
        base = {
            "object_id": raw.get("object_id"),
            "channel": raw.get("channel"),
            "field": raw.get("field"),
            "expected": expected,
            "observed": copy.deepcopy(observed),
            "tolerance": tolerance,
        }
        if isinstance(expected, bool) or isinstance(observed, bool):
            mismatch = expected != observed
            delta = None
        elif isinstance(expected, (int, float)) and isinstance(observed, (int, float)):
            if not math.isfinite(float(observed)):
                raise ChameleonError(f"measurement[{index}].observed must be finite")
            delta = float(observed) - float(expected)
            mismatch = abs(delta) > tolerance
            base["delta"] = delta
            base["compensating_input_candidate"] = float(expected) - delta
        else:
            delta = None
            mismatch = expected != observed
        if mismatch:
            discrepancies.append(base)
        else:
            confirmed.append(base)
    feedback = {
        "schema": REALITY_FEEDBACK_SCHEMA,
        "operation": "compare-reality",
        "truth_status": "EXTERNALLY_SUPPLIED_REALITY_OBSERVATION_COMPARED_TO_SIMULATED_STATE",
        "context_key": context,
        "simulation_digest": simulation["thought_digest"],
        "observation": {"source": source, "executor": executor, "measurements": copy.deepcopy(measurements)},
        "confirmed_measurements": confirmed,
        "discrepancies": discrepancies,
        "reopen_simulation": bool(discrepancies),
        "generalization_allowed": False,
        "feedback_meaning": "a discrepancy is evidence about this observed condition, not a universal law",
    }
    feedback["feedback_digest"] = _digest(feedback)
    return feedback


def recalibrate_simulation(simulation: Any, feedback: Any) -> dict[str, Any]:
    thought = _simulation_thought(simulation)
    if not isinstance(feedback, dict) or feedback.get("schema") != REALITY_FEEDBACK_SCHEMA:
        raise ChameleonError("feedback schema is unsupported")
    supplied = feedback.get("feedback_digest")
    body = copy.deepcopy(feedback)
    body.pop("feedback_digest", None)
    if supplied != _digest(body):
        raise ChameleonError("feedback digest mismatch")
    if feedback.get("simulation_digest") != simulation.get("thought_digest"):
        raise ChameleonError("feedback is not bound to this simulation")
    if not feedback.get("discrepancies"):
        return {
            "operation": "recalibrate-simulation",
            "status": "NO_REALITY_DISCREPANCY_TO_REOPEN",
            "truth_status": "OBSERVED_REALITY_MATCHED_WITHIN_SUPPLIED_TOLERANCES",
            "simulation": copy.deepcopy(simulation),
        }
    corrected = copy.deepcopy(thought)
    applied: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for row in feedback["discrepancies"]:
        candidate = row.get("compensating_input_candidate")
        if candidate is None:
            skipped.append({**copy.deepcopy(row), "reason": "non-numeric discrepancy has no deterministic inverse correction in v0"})
            continue
        obj = next(item for item in corrected["objects"] if item["id"] == row["object_id"])
        channel = obj.get(row["channel"])
        if not isinstance(channel, dict) or row["field"] not in channel:
            skipped.append({**copy.deepcopy(row), "reason": "target field disappeared before correction"})
            continue
        before = channel[row["field"]]
        channel[row["field"]] = candidate
        applied.append({
            "object_id": row["object_id"],
            "channel": row["channel"],
            "field": row["field"],
            "before": before,
            "after": candidate,
            "basis": "first-order exact-condition inverse of observed numeric discrepancy",
        })
    if not applied:
        return {
            "operation": "recalibrate-simulation",
            "status": "HOLD_NO_DETERMINISTIC_NUMERIC_CORRECTION",
            "truth_status": "REALITY_DISCREPANCY_REQUIRES_A_NEW_SIMULATION_RULE",
            "feedback_digest": supplied,
            "skipped": skipped,
            "reopened": False,
        }
    try:
        rerun = simulate_until_no_known_improvements(corrected)
    except (SimulationError, PaintgunError) as exc:
        raise ChameleonError("recalibration could not re-run simulation", {"reason": str(exc)}) from exc
    return {
        "operation": "recalibrate-simulation",
        "status": "REOPENED_AND_RESIMULATED_FROM_REALITY_DISCREPANCY",
        "truth_status": "EXACT_CONDITION_REALITY_CORRECTION_CANDIDATE_RESIMULATED",
        "feedback_digest": supplied,
        "context_key": feedback["context_key"],
        "applied_corrections": applied,
        "skipped": skipped,
        "reopened": True,
        "simulation": rerun,
        "generalization_allowed": False,
        "limitations": [
            "the inverse correction is first-order and exact-condition only",
            "one observation never becomes a global simulator law",
            "non-numeric discrepancies remain explicit gaps until a dedicated rule exists",
        ],
    }


def _ledger_path(root: Path) -> Path:
    return Path(root).resolve() / "state" / "simulation-calibration.json"


def _load_ledger(root: Path) -> dict[str, Any]:
    path = _ledger_path(root)
    if not path.exists():
        return {"schema": CALIBRATION_LEDGER_SCHEMA, "entries": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ChameleonError("could not read simulation calibration ledger") from exc
    if value.get("schema") != CALIBRATION_LEDGER_SCHEMA or not isinstance(value.get("entries"), list):
        raise ChameleonError("simulation calibration ledger has unsupported schema")
    return value


def record_calibration(root: Path, feedback: Any) -> dict[str, Any]:
    if not isinstance(feedback, dict) or feedback.get("schema") != REALITY_FEEDBACK_SCHEMA:
        raise ChameleonError("feedback schema is unsupported")
    supplied = feedback.get("feedback_digest")
    body = copy.deepcopy(feedback)
    body.pop("feedback_digest", None)
    if supplied != _digest(body):
        raise ChameleonError("feedback digest mismatch")
    ledger = _load_ledger(root)
    if any(row.get("feedback_digest") == supplied for row in ledger["entries"]):
        return {"status": "CALIBRATION_ALREADY_RECORDED", "feedback_digest": supplied, "ledger_path": str(_ledger_path(root))}
    entry = {
        "feedback_digest": supplied,
        "context_key": feedback["context_key"],
        "simulation_digest": feedback["simulation_digest"],
        "source": feedback["observation"]["source"],
        "executor": feedback["observation"]["executor"],
        "discrepancies": copy.deepcopy(feedback["discrepancies"]),
        "generalization_allowed": False,
    }
    ledger["entries"].append(entry)
    if len(ledger["entries"]) > MAX_CALIBRATION_ENTRIES:
        raise ChameleonError(f"simulation calibration ledger exceeds {MAX_CALIBRATION_ENTRIES} entries")
    atomic_write_json(_ledger_path(root), ledger)
    return {
        "status": "EXACT_CONTEXT_CALIBRATION_RECORDED",
        "truth_status": "OBSERVED_DISCREPANCY_RETAINED_WITH_PROVENANCE",
        "feedback_digest": supplied,
        "context_key": feedback["context_key"],
        "ledger_path": str(_ledger_path(root)),
        "recorded_entries": len(ledger["entries"]),
        "generalization_allowed": False,
    }


def inspect_calibrations(root: Path, *, context_key: Any = None) -> dict[str, Any]:
    ledger = _load_ledger(root)
    context = None if context_key is None else _text(context_key, "context_key", 300)
    rows = [row for row in ledger["entries"] if context is None or row.get("context_key") == context]
    numeric_stats: dict[str, dict[str, Any]] = {}
    for entry in rows:
        for discrepancy in entry.get("discrepancies", []):
            if not isinstance(discrepancy.get("delta"), (int, float)):
                continue
            key = f"{discrepancy.get('object_id')}::{discrepancy.get('channel')}::{discrepancy.get('field')}"
            stat = numeric_stats.setdefault(key, {"count": 0, "mean_delta": 0.0})
            count = stat["count"] + 1
            stat["mean_delta"] = stat["mean_delta"] + (float(discrepancy["delta"]) - stat["mean_delta"]) / count
            stat["count"] = count
    return {
        "schema": CALIBRATION_LEDGER_SCHEMA,
        "truth_status": "EXACT_CONTEXT_REALITY_CALIBRATION_HISTORY",
        "context_key": context,
        "entries": copy.deepcopy(rows),
        "numeric_stats": numeric_stats,
        "generalization_allowed": False,
        "warning": "repeated exact-context deltas are evidence for future rule design; they are not silently promoted into universal laws",
    }


def operate_chameleon(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "morph-vector-cells")).strip().casefold()
    if operation in {"morph-thoughts", "continuous-morph"}:
        return morph_thoughts(inputs.get("from_thought"), inputs.get("to_thought"), inputs.get("factor"))
    if operation in {"morph-vector-cells", "morph-cells", "chameleon-morph"}:
        return morph_vector_cells(
            inputs.get("fabric"),
            from_state=inputs.get("from_state"),
            to_state=inputs.get("to_state"),
            factor=inputs.get("factor"),
        )
    if operation in {"compile-material-graph", "compile-material", "rich-material"}:
        return compile_material_graph(inputs.get("material_graph"))
    if operation in {"apply-material-graph", "apply-material"}:
        return apply_material_graph(inputs.get("thought"), inputs.get("object_id"), inputs.get("material_graph"))
    if operation in {"adapt-environment", "sensor-adapt", "environment-adapt"}:
        return adapt_environment(inputs)
    if operation in {"compare-reality", "reality-feedback", "simulation-reality-feedback"}:
        return compare_reality(inputs.get("simulation"), inputs.get("observation"), context_key=inputs.get("context_key"))
    if operation in {"recalibrate-simulation", "reopen-from-reality", "re-simulate-reality-gap"}:
        return recalibrate_simulation(inputs.get("simulation"), inputs.get("feedback"))
    if operation in {"record-calibration", "learn-exact-context"}:
        return record_calibration(root, inputs.get("feedback"))
    if operation in {"inspect-calibrations", "calibration-history"}:
        return inspect_calibrations(root, context_key=inputs.get("context_key"))
    raise ChameleonError("unsupported chameleon operation", {"operation": operation})

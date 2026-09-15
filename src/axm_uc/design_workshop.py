from __future__ import annotations

import copy
import hashlib
import html
import json
import math
from pathlib import Path
from typing import Any

from axm_stickers.placement import rigid
from .project import ProjectError, build_project

SKETCH_SCHEMA = "axm.design-sketch/v0.1"
OBSERVATION_SCHEMA = "axm.design-workshop-observation/v0.1"
REPORT_SCHEMA = "axm.design-workshop-report/v0.1"
MAX_PARTS = 256
MAX_GAUGES = 256
SHAPES = {"box", "cylinder", "sphere", "plane", "marker"}
AXES = {"x": (1.0, 0.0, 0.0), "y": (0.0, 1.0, 0.0), "z": (0.0, 0.0, 1.0)}


class DesignWorkshopError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignWorkshopError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignWorkshopError(f"{label} exceeds its {maximum}-character bound")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 80)
    if not result[0].isalnum() or any(not (ch.isalnum() or ch in "_.-") for ch in result):
        raise DesignWorkshopError(f"{label} is not a portable identifier", {"value": result})
    return result


def _number(value: Any, label: str, minimum: float = -1_000_000.0, maximum: float = 1_000_000.0) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise DesignWorkshopError(f"{label} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise DesignWorkshopError(f"{label} is outside bounds", {"minimum": minimum, "maximum": maximum, "value": result})
    return result


def _vec3(value: Any, label: str, *, positive: bool = False) -> list[float]:
    if not isinstance(value, list) or len(value) != 3:
        raise DesignWorkshopError(f"{label} must contain three numbers")
    result = [_number(item, f"{label}[{index}]") for index, item in enumerate(value)]
    if positive and any(item <= 0 for item in result):
        raise DesignWorkshopError(f"{label} values must be positive")
    return result


def _frame(value: Any, label: str) -> list[float]:
    try:
        return [float(item) for item in rigid(value)]
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopError(f"{label} must be a rigid 4x4 frame") from exc


def _position(frame: list[float]) -> tuple[float, float, float]:
    return float(frame[3]), float(frame[7]), float(frame[11])


def _axis_vector(frame: list[float], axis: str) -> tuple[float, float, float]:
    column = {"x": 0, "y": 1, "z": 2}[axis]
    return float(frame[column]), float(frame[4 + column]), float(frame[8 + column])


def _distance(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    return math.sqrt(sum((a[index] - b[index]) ** 2 for index in range(3)))


def _angle(a: tuple[float, float, float], b: tuple[float, float, float]) -> float:
    dot = max(-1.0, min(1.0, sum(a[index] * b[index] for index in range(3))))
    return math.degrees(math.acos(dot))


def _rotation_delta_degrees(expected: list[float], observed: list[float]) -> float:
    trace = sum(expected[row * 4 + column] * observed[row * 4 + column]
                for row in range(3) for column in range(3))
    cosine = max(-1.0, min(1.0, (trace - 1.0) / 2.0))
    return math.degrees(math.acos(cosine))


def _part(raw: Any, index: int) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"id", "shape", "frame", "size", "role", "notes"}:
        raise DesignWorkshopError(f"parts[{index}] must use id, shape, frame, size, role, and notes")
    shape = _text(raw["shape"], f"parts[{index}].shape", 32).casefold()
    if shape not in SHAPES:
        raise DesignWorkshopError(f"parts[{index}].shape is unsupported", {"supported": sorted(SHAPES)})
    return {"id": _identifier(raw["id"], f"parts[{index}].id"), "shape": shape,
            "frame": _frame(raw["frame"], f"parts[{index}].frame"),
            "size": _vec3(raw["size"], f"parts[{index}].size", positive=True),
            "role": _text(raw["role"], f"parts[{index}].role", 120),
            "notes": _text(raw["notes"], f"parts[{index}].notes", 500)}


def _axis(value: Any, label: str) -> str:
    axis = _text(value, label, 8).casefold()
    if axis not in AXES:
        raise DesignWorkshopError(f"{label} must be x, y, or z")
    return axis


def _gauge(raw: Any, index: int, part_ids: set[str]) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise DesignWorkshopError(f"gauges[{index}] must be an object")
    kind = _text(raw.get("type"), f"gauges[{index}].type", 32).casefold()
    gauge_id = _identifier(raw.get("id"), f"gauges[{index}].id")
    common = {"id": gauge_id, "type": kind}
    if kind == "distance":
        if set(raw) != {"id", "type", "a", "b", "target", "tolerance"}:
            raise DesignWorkshopError("distance gauge fields are closed")
        a = _identifier(raw["a"], "distance.a"); b = _identifier(raw["b"], "distance.b")
        if a not in part_ids or b not in part_ids or a == b:
            raise DesignWorkshopError("distance gauge must reference two distinct sketch parts")
        return {**common, "a": a, "b": b, "target": _number(raw["target"], "distance.target", 0),
                "tolerance": _number(raw["tolerance"], "distance.tolerance", 0)}
    if kind in {"alignment", "spacing"}:
        required = {"id", "type", "parts", "axis", "tolerance"} | ({"target"} if kind == "spacing" else set())
        if set(raw) != required or not isinstance(raw.get("parts"), list) or not 2 <= len(raw["parts"]) <= MAX_PARTS:
            raise DesignWorkshopError(f"{kind} gauge is invalid")
        parts = [_identifier(value, f"{kind}.parts") for value in raw["parts"]]
        if len(parts) != len(set(parts)) or any(value not in part_ids for value in parts):
            raise DesignWorkshopError(f"{kind} gauge parts must be unique known sketch parts")
        result = {**common, "parts": parts, "axis": _axis(raw["axis"], f"{kind}.axis"),
                  "tolerance": _number(raw["tolerance"], f"{kind}.tolerance", 0)}
        if kind == "spacing":
            result["target"] = _number(raw["target"], "spacing.target", 0)
        return result
    if kind == "angle":
        expected = {"id", "type", "a", "a_axis", "b", "b_axis", "target_degrees", "tolerance_degrees"}
        if set(raw) != expected:
            raise DesignWorkshopError("angle gauge fields are closed")
        a = _identifier(raw["a"], "angle.a"); b = _identifier(raw["b"], "angle.b")
        if a not in part_ids or b not in part_ids:
            raise DesignWorkshopError("angle gauge references unknown part")
        return {**common, "a": a, "a_axis": _axis(raw["a_axis"], "angle.a_axis"),
                "b": b, "b_axis": _axis(raw["b_axis"], "angle.b_axis"),
                "target_degrees": _number(raw["target_degrees"], "angle.target_degrees", 0, 180),
                "tolerance_degrees": _number(raw["tolerance_degrees"], "angle.tolerance_degrees", 0, 180)}
    if kind == "orientation":
        expected = {"id", "type", "part", "local_axis", "world_axis", "target_degrees", "tolerance_degrees"}
        if set(raw) != expected:
            raise DesignWorkshopError("orientation gauge fields are closed")
        part = _identifier(raw["part"], "orientation.part")
        if part not in part_ids:
            raise DesignWorkshopError("orientation gauge references unknown part")
        return {**common, "part": part, "local_axis": _axis(raw["local_axis"], "orientation.local_axis"),
                "world_axis": _axis(raw["world_axis"], "orientation.world_axis"),
                "target_degrees": _number(raw["target_degrees"], "orientation.target_degrees", 0, 180),
                "tolerance_degrees": _number(raw["tolerance_degrees"], "orientation.tolerance_degrees", 0, 180)}
    if kind == "symmetry":
        if set(raw) != {"id", "type", "pairs", "axis", "center", "tolerance"} or not isinstance(raw.get("pairs"), list) or not 1 <= len(raw["pairs"]) <= MAX_PARTS:
            raise DesignWorkshopError("symmetry gauge is invalid")
        pairs = []; seen = set()
        for pair_index, pair in enumerate(raw["pairs"]):
            if not isinstance(pair, dict) or set(pair) != {"a", "b"}:
                raise DesignWorkshopError("symmetry pairs require a and b")
            a = _identifier(pair["a"], f"symmetry.pairs[{pair_index}].a")
            b = _identifier(pair["b"], f"symmetry.pairs[{pair_index}].b")
            if a not in part_ids or b not in part_ids or a == b or (a, b) in seen:
                raise DesignWorkshopError("symmetry pair is invalid")
            seen.add((a, b)); pairs.append({"a": a, "b": b})
        return {**common, "pairs": pairs, "axis": _axis(raw["axis"], "symmetry.axis"),
                "center": _number(raw["center"], "symmetry.center"),
                "tolerance": _number(raw["tolerance"], "symmetry.tolerance", 0)}
    if kind == "size":
        if set(raw) != {"id", "type", "part", "target", "tolerance"}:
            raise DesignWorkshopError("size gauge fields are closed")
        part = _identifier(raw["part"], "size.part")
        if part not in part_ids:
            raise DesignWorkshopError("size gauge references unknown part")
        return {**common, "part": part, "target": _vec3(raw["target"], "size.target", positive=True),
                "tolerance": _number(raw["tolerance"], "size.tolerance", 0)}
    raise DesignWorkshopError("unsupported workshop gauge", {"type": kind,
        "supported": ["distance", "alignment", "spacing", "angle", "orientation", "symmetry", "size"]})


def validate_sketch(raw: Any) -> dict[str, Any]:
    required = {"schema", "id", "purpose", "units", "parts", "gauges", "tolerances", "provenance"}
    allowed = required | {"sketch_digest"}
    if not isinstance(raw, dict) or set(raw) not in (required, allowed) or raw.get("schema") != SKETCH_SCHEMA:
        raise DesignWorkshopError("design sketch has missing, unsupported, or wrong-schema fields")
    if not isinstance(raw["parts"], list) or not 1 <= len(raw["parts"]) <= MAX_PARTS:
        raise DesignWorkshopError(f"sketch requires 1..{MAX_PARTS} parts")
    parts = [_part(item, index) for index, item in enumerate(raw["parts"])]
    ids = [item["id"] for item in parts]
    if len(ids) != len(set(ids)):
        raise DesignWorkshopError("sketch part ids must be unique")
    if not isinstance(raw["gauges"], list) or len(raw["gauges"]) > MAX_GAUGES:
        raise DesignWorkshopError(f"sketch gauges must contain at most {MAX_GAUGES} entries")
    gauges = [_gauge(item, index, set(ids)) for index, item in enumerate(raw["gauges"])]
    if len({item["id"] for item in gauges}) != len(gauges):
        raise DesignWorkshopError("sketch gauge ids must be unique")
    tolerances = raw["tolerances"]
    if not isinstance(tolerances, dict) or set(tolerances) != {"position", "size", "orientation_degrees"}:
        raise DesignWorkshopError("sketch tolerances must declare position, size, and orientation_degrees")
    provenance = copy.deepcopy(raw["provenance"])
    try:
        _canonical(provenance)
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopError("sketch provenance must be deterministic JSON") from exc
    result = {"schema": SKETCH_SCHEMA, "id": _identifier(raw["id"], "sketch.id"),
              "purpose": _text(raw["purpose"], "sketch.purpose", 2000),
              "units": _identifier(raw["units"], "sketch.units"), "parts": parts, "gauges": gauges,
              "tolerances": {"position": _number(tolerances["position"], "tolerances.position", 0),
                             "size": _number(tolerances["size"], "tolerances.size", 0),
                             "orientation_degrees": _number(tolerances["orientation_degrees"], "tolerances.orientation_degrees", 0, 180)},
              "provenance": provenance}
    expected = _digest(result)
    if "sketch_digest" in raw and raw["sketch_digest"] != expected:
        raise DesignWorkshopError("sketch digest does not match normalized sketch body")
    result["sketch_digest"] = expected
    return result


def validate_observation(raw: Any, sketch: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(raw, dict) or set(raw) != {"schema", "sketch_digest", "parts", "observer"} or raw.get("schema") != OBSERVATION_SCHEMA:
        raise DesignWorkshopError("workshop observation has invalid fields or schema")
    if raw["sketch_digest"] != sketch["sketch_digest"]:
        raise DesignWorkshopError("workshop observation does not match exact sketch digest")
    if not isinstance(raw["parts"], list) or len(raw["parts"]) > MAX_PARTS:
        raise DesignWorkshopError("workshop observation parts are invalid")
    parts = []; seen = set()
    for index, item in enumerate(raw["parts"]):
        if not isinstance(item, dict) or set(item) != {"id", "frame", "size"}:
            raise DesignWorkshopError(f"observation.parts[{index}] is invalid")
        part_id = _identifier(item["id"], f"observation.parts[{index}].id")
        if part_id in seen:
            raise DesignWorkshopError("observed part ids must be unique")
        seen.add(part_id)
        parts.append({"id": part_id, "frame": _frame(item["frame"], f"observation.parts[{index}].frame"),
                      "size": _vec3(item["size"], f"observation.parts[{index}].size", positive=True)})
    observer = copy.deepcopy(raw["observer"])
    try:
        _canonical(observer)
    except (TypeError, ValueError) as exc:
        raise DesignWorkshopError("observation observer must be deterministic JSON") from exc
    return {"schema": OBSERVATION_SCHEMA, "sketch_digest": sketch["sketch_digest"], "parts": parts, "observer": observer}


def _gauge_result(gauge: dict[str, Any], observed: dict[str, dict[str, Any]]) -> dict[str, Any]:
    kind = gauge["type"]
    if kind in {"distance", "angle"}: needed = [gauge["a"], gauge["b"]]
    elif kind in {"alignment", "spacing"}: needed = gauge["parts"]
    elif kind in {"orientation", "size"}: needed = [gauge["part"]]
    else: needed = [value for pair in gauge["pairs"] for value in (pair["a"], pair["b"])]
    missing = sorted(set(needed) - set(observed))
    if missing:
        return {"id": gauge["id"], "type": kind, "status": "HOLD", "missing_parts": missing}
    tolerance = gauge.get("tolerance", gauge.get("tolerance_degrees", 0.0)); measured: Any
    if kind == "distance":
        measured = _distance(_position(observed[gauge["a"]]["frame"]), _position(observed[gauge["b"]]["frame"])); residual = abs(measured - gauge["target"])
    elif kind == "alignment":
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]; first = _position(observed[gauge["parts"][0]]["frame"])
        residual = max(math.sqrt(sum((position[index] - first[index]) ** 2 for index in range(3) if index != axis_index))
                       for position in (_position(observed[part]["frame"]) for part in gauge["parts"])); measured = residual
    elif kind == "spacing":
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]; values = [_position(observed[part]["frame"])[axis_index] for part in gauge["parts"]]
        measured = [abs(values[index + 1] - values[index]) for index in range(len(values) - 1)]; residual = max(abs(value - gauge["target"]) for value in measured)
    elif kind == "angle":
        measured = _angle(_axis_vector(observed[gauge["a"]]["frame"], gauge["a_axis"]), _axis_vector(observed[gauge["b"]]["frame"], gauge["b_axis"])); residual = abs(measured - gauge["target_degrees"])
    elif kind == "orientation":
        measured = _angle(_axis_vector(observed[gauge["part"]]["frame"], gauge["local_axis"]), AXES[gauge["world_axis"]]); residual = abs(measured - gauge["target_degrees"])
    elif kind == "symmetry":
        axis_index = {"x": 0, "y": 1, "z": 2}[gauge["axis"]]; measured = []
        for pair in gauge["pairs"]:
            first = _position(observed[pair["a"]]["frame"]); second = list(_position(observed[pair["b"]]["frame"])); second[axis_index] = 2.0 * gauge["center"] - second[axis_index]
            measured.append(_distance(first, tuple(second)))
        residual = max(measured)
    else:
        measured = observed[gauge["part"]]["size"]; residual = max(abs(measured[index] - gauge["target"][index]) for index in range(3))
    return {"id": gauge["id"], "type": kind, "status": "PASS" if residual <= tolerance else "FAIL",
            "measured": measured, "residual": round(residual, 12), "tolerance": tolerance}


def compare_sketch(sketch_raw: Any, observation_raw: Any) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw); observation = validate_observation(observation_raw, sketch)
    planned = {item["id"]: item for item in sketch["parts"]}; observed = {item["id"]: item for item in observation["parts"]}; part_results = []
    for part_id, expected in planned.items():
        actual = observed.get(part_id)
        if actual is None:
            part_results.append({"id": part_id, "status": "HOLD", "reason": "part not observed"}); continue
        position_residual = _distance(_position(expected["frame"]), _position(actual["frame"]))
        size_residual = max(abs(expected["size"][index] - actual["size"][index]) for index in range(3))
        orientation_residual = _rotation_delta_degrees(expected["frame"], actual["frame"]); failures = []
        if position_residual > sketch["tolerances"]["position"]: failures.append("position")
        if size_residual > sketch["tolerances"]["size"]: failures.append("size")
        if orientation_residual > sketch["tolerances"]["orientation_degrees"]: failures.append("orientation")
        part_results.append({"id": part_id, "status": "PASS" if not failures else "FAIL", "position_residual": round(position_residual, 12),
                             "size_residual": round(size_residual, 12), "orientation_residual_degrees": round(orientation_residual, 12), "failed_dimensions": failures})
    gauge_results = [_gauge_result(gauge, observed) for gauge in sketch["gauges"]]; statuses = [row["status"] for row in part_results + gauge_results]
    status = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    report = {"schema": REPORT_SCHEMA, "truth_status": "DETERMINISTIC_SKETCH_VS_OBSERVED_STATE_MEASUREMENT", "status": status, "passed": status == "PASS",
              "sketch_digest": sketch["sketch_digest"], "observer": copy.deepcopy(observation["observer"]), "parts": part_results, "gauges": gauge_results,
              "repair_direction": [row["id"] for row in part_results + gauge_results if row["status"] != "PASS"],
              "limitations": ["measurements compare caller-supplied rigid frames and sizes only", "PASS does not prove mesh fit, collision clearance, strength, manufacturability, physics, semantics, aesthetics, or target-engine quality", "schematic sketch intent is not an automatic design-quality verdict"]}
    report["report_digest"] = _digest(report); return report


def _svg(sketch: dict[str, Any]) -> str:
    views = [("front", 0, 1), ("top", 0, 2), ("side", 2, 1)]
    chunks = ['<svg xmlns="http://www.w3.org/2000/svg" width="1200" height="420" viewBox="0 0 1200 420">', '<rect width="1200" height="420" fill="white"/>', '<text x="20" y="24" font-family="monospace" font-size="14">AXM schematic blockout — center/size projection, not a render</text>']
    for view_index, (title, first_axis, second_axis) in enumerate(views):
        x_offset = 10.0 + view_index * 400.0; bounds = []
        for part in sketch["parts"]:
            position = _position(part["frame"]); size = part["size"]
            bounds.append((position[first_axis] - size[first_axis] / 2, position[first_axis] + size[first_axis] / 2, position[second_axis] - size[second_axis] / 2, position[second_axis] + size[second_axis] / 2))
        min_x = min(v[0] for v in bounds); max_x = max(v[1] for v in bounds); min_y = min(v[2] for v in bounds); max_y = max(v[3] for v in bounds)
        scale = min(340.0 / max(max_x - min_x, 1e-9), 300.0 / max(max_y - min_y, 1e-9))
        chunks.append(f'<rect x="{x_offset}" y="40" width="390" height="360" fill="none" stroke="black"/>'); chunks.append(f'<text x="{x_offset + 8}" y="60" font-family="monospace" font-size="13">{html.escape(title)}</text>')
        for part, bound in zip(sketch["parts"], bounds):
            x = x_offset + 25 + (bound[0] - min_x) * scale; y = 370 - (bound[3] - min_y) * scale; width = max((bound[1] - bound[0]) * scale, 2); height = max((bound[3] - bound[2]) * scale, 2)
            chunks.append(f'<rect x="{x:.3f}" y="{y:.3f}" width="{width:.3f}" height="{height:.3f}" fill="none" stroke="black"/>'); chunks.append(f'<text x="{x + 3:.3f}" y="{y + 13:.3f}" font-family="monospace" font-size="10">{html.escape(part["id"])}</text>')
    chunks.append('<text x="20" y="414" font-family="monospace" font-size="11">Rotated extents are not rasterized; exact rigid frames remain in sketch.json.</text>'); chunks.append('</svg>'); return "\n".join(chunks) + "\n"


def _resolve_path(root: Path, requested: str) -> Path:
    value = Path(requested).expanduser(); return (Path(root) / value).resolve() if not value.is_absolute() else value.resolve()


def _machine_body(root: Path, target: Path) -> bool:
    root = Path(root).resolve(); target = target.resolve()
    try: relative = target.relative_to(root)
    except ValueError: return False
    return not relative.parts or relative.parts[0] not in {"creations", ".axm-build"}


def materialize_sketch(root: Path, path: str, sketch_raw: Any, *, replace: bool = False) -> dict[str, Any]:
    sketch = validate_sketch(sketch_raw); target = _resolve_path(root, _text(path, "path", 4000))
    if _machine_body(root, target): raise DesignWorkshopError("design sketch materialization cannot rewrite the live machine body")
    files = {"sketch.json": json.dumps(sketch, ensure_ascii=False, indent=2, sort_keys=True) + "\n", "sketch.svg": _svg(sketch)}
    try:
        result = build_project(target=target, files=files, project_type="generic", checks=[{"type": "file-set", "files": sorted(files), "mode": "exact"}, {"type": "json-valid", "path": "sketch.json"}], replace=replace, publish_mode="validated")
    except ProjectError as exc:
        raise DesignWorkshopError(str(exc), exc.details) from exc
    result["truth_status"] = "VALIDATED_DESIGN_SKETCH_DESCRIPTOR_PROJECT"; result["sketch_digest"] = sketch["sketch_digest"]; return result


def design_workshop_summary() -> dict[str, Any]:
    return {"sketch_schema": SKETCH_SCHEMA, "observation_schema": OBSERVATION_SCHEMA, "report_schema": REPORT_SCHEMA,
            "operations": ["inspect-workshop", "validate-sketch", "compare-sketch", "measure-design", "materialize-sketch"],
            "instruments": ["distance/ruler", "alignment/straightedge", "spacing/jig", "angle/square", "orientation/level", "symmetry", "size/caliper"],
            "truth_boundary": "numeric plan/state comparison only; no automatic geometric-fit or aesthetic claim"}


def operate_design_workshop(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-workshop": return {"truth_status": "DECLARED_DESIGN_WORKSHOP_V0_1", **design_workshop_summary()}
    if operation == "validate-sketch": return {"truth_status": "DETERMINISTIC_DESIGN_SKETCH_VALIDATION", "sketch": validate_sketch(inputs.get("sketch"))}
    if operation in {"compare-sketch", "measure-design"}: return compare_sketch(inputs.get("sketch"), inputs.get("observation"))
    if operation == "materialize-sketch":
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool): raise DesignWorkshopError("replace must be boolean")
        return materialize_sketch(root, _text(inputs.get("path"), "path", 4000), inputs.get("sketch"), replace=replace)
    raise DesignWorkshopError("design workshop operation is unsupported", {"operation": operation, "supported": design_workshop_summary()["operations"]})

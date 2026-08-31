from __future__ import annotations

import copy
import hashlib
import json
import math
from typing import Any

from .paintgun import PaintgunError, render_cinematic_svg, thought_digest, validate_visual_thought

VECTOR_CELL_FABRIC_SCHEMA = "axm.vector-cell-fabric/v0.1"
VECTOR_CELL_RESOLUTION_SCHEMA = "axm.vector-cell-resolution/v0.1"
MAX_CELLS = 512
MAX_DEPTH = 16


class VectorCellError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _digest(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return f"sha256:{hashlib.sha256(raw).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 400) -> str:
    if not isinstance(value, str) or not value.strip():
        raise VectorCellError(f"{label} must be non-empty text")
    value = value.strip()
    if len(value) > maximum:
        raise VectorCellError(f"{label} exceeds {maximum} characters")
    return value


def _num(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise VectorCellError(f"{label} must be a finite number")
    value = float(value)
    if minimum is not None and value < minimum:
        raise VectorCellError(f"{label} must be >= {minimum}")
    if maximum is not None and value > maximum:
        raise VectorCellError(f"{label} must be <= {maximum}")
    return value


def _transform(raw: Any, label: str) -> dict[str, float]:
    raw = {} if raw is None else raw
    if not isinstance(raw, dict):
        raise VectorCellError(f"{label} must be an object")
    return {
        "x": _num(raw.get("x", 0), f"{label}.x", -8192, 8192),
        "y": _num(raw.get("y", 0), f"{label}.y", -8192, 8192),
        "scale": _num(raw.get("scale", 1), f"{label}.scale", 0.0001, 1000),
    }


def _compose(parent: dict[str, float], local: dict[str, float]) -> dict[str, float]:
    return {
        "x": parent["x"] + local["x"] * parent["scale"],
        "y": parent["y"] + local["y"] * parent["scale"],
        "scale": parent["scale"] * local["scale"],
    }


def _select(cell: dict[str, Any], scale: float, choice: str, label: str) -> dict[str, Any]:
    reps = cell.get("representations")
    if not isinstance(reps, list) or not reps:
        raise VectorCellError(f"{label}.representations must be non-empty")
    generic, exact = [], []
    for index, rep in enumerate(reps):
        if not isinstance(rep, dict):
            raise VectorCellError(f"{label}.representations[{index}] must be an object")
        minimum = _num(rep.get("min_scale", 0), f"{label}.representations[{index}].min_scale", 0)
        maximum = rep.get("max_scale")
        maximum = None if maximum is None else _num(maximum, f"{label}.representations[{index}].max_scale", 0)
        if maximum is not None and maximum <= minimum:
            raise VectorCellError(f"{label}.representations[{index}] has invalid scale interval")
        if scale < minimum or (maximum is not None and scale >= maximum):
            continue
        choices = rep.get("choices")
        if choices is None:
            generic.append(rep)
        elif isinstance(choices, list) and choice in choices:
            exact.append(rep)
        elif not isinstance(choices, list):
            raise VectorCellError(f"{label}.representations[{index}].choices must be a list")
    matches = exact or generic
    if len(matches) != 1:
        raise VectorCellError(
            "vector cell must resolve to exactly one representation",
            {"cell_id": cell.get("id"), "scale": scale, "choice": choice, "matches": [r.get("id") for r in matches]},
        )
    return copy.deepcopy(matches[0])


def _shape(shape: Any, t: dict[str, float], label: str) -> Any:
    if not isinstance(shape, dict):
        return shape
    out = copy.deepcopy(shape)
    kind, s, ox, oy = str(out.get("kind", "")).casefold(), t["scale"], t["x"], t["y"]
    if kind == "rect" and all(k in out for k in ("x", "y", "width", "height")):
        out.update(x=float(out["x"]) * s + ox, y=float(out["y"]) * s + oy,
                   width=float(out["width"]) * s, height=float(out["height"]) * s)
        if "rx" in out:
            out["rx"] = float(out["rx"]) * s
    elif kind == "circle" and all(k in out for k in ("cx", "cy", "r")):
        out.update(cx=float(out["cx"]) * s + ox, cy=float(out["cy"]) * s + oy, r=float(out["r"]) * s)
    elif kind == "ellipse" and all(k in out for k in ("cx", "cy", "rx", "ry")):
        out.update(cx=float(out["cx"]) * s + ox, cy=float(out["cy"]) * s + oy,
                   rx=float(out["rx"]) * s, ry=float(out["ry"]) * s)
    elif kind == "polygon" and isinstance(out.get("points"), list):
        out["points"] = [[float(p[0]) * s + ox, float(p[1]) * s + oy] for p in out["points"]]
    elif kind == "path" and (ox != 0 or oy != 0 or s != 1):
        raise VectorCellError("v0 cannot transform SVG path data", {"label": label, "transform": t})
    return out


def _object(raw: Any, cell_path: str, t: dict[str, float], z_offset: int, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise VectorCellError(f"{label} must be an object")
    out = copy.deepcopy(raw)
    local_id = _text(out.get("id"), f"{label}.id", 80)
    out["id"] = f"{cell_path}::{local_id}"
    if len(out["id"]) > 120:
        raise VectorCellError("resolved object id exceeds Paintgun bound", {"object_id": out["id"]})
    out["z"] = int(out.get("z", 0)) + z_offset
    out["shape"] = _shape(out.get("shape"), t, f"{label}.shape")
    s = t["scale"]
    if isinstance(out.get("color"), dict) and isinstance(out["color"].get("stroke_width"), (int, float)):
        out["color"]["stroke_width"] = float(out["color"]["stroke_width"]) * s
    if isinstance(out.get("shade"), dict):
        for key in ("dx", "dy", "blur"):
            if isinstance(out["shade"].get(key), (int, float)):
                out["shade"][key] = float(out["shade"][key]) * s
    if isinstance(out.get("light"), dict):
        if isinstance(out["light"].get("x"), (int, float)):
            out["light"]["x"] = float(out["light"]["x"]) * s + t["x"]
        if isinstance(out["light"].get("y"), (int, float)):
            out["light"]["y"] = float(out["light"]["y"]) * s + t["y"]
        if isinstance(out["light"].get("radius"), (int, float)):
            out["light"]["radius"] = float(out["light"]["radius"]) * s
    return out


def _cell(raw: Any, *, scale: float, choice: str, parent_t: dict[str, float], prefix: str,
          depth: int, seen: set[str], stats: dict[str, int], trace: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if depth > MAX_DEPTH or not isinstance(raw, dict):
        raise VectorCellError("invalid vector-cell nesting")
    cell_id = _text(raw.get("id"), "cell.id", 80)
    if cell_id in seen:
        raise VectorCellError("vector-cell ids must be globally unique", {"duplicate": cell_id})
    seen.add(cell_id)
    stats["cells_visited"] += 1
    if stats["cells_visited"] > MAX_CELLS:
        raise VectorCellError(f"vector-cell fabric exceeds {MAX_CELLS} cells")
    path = f"{prefix}/{cell_id}" if prefix else cell_id
    t = _compose(parent_t, _transform(raw.get("transform"), f"cell[{cell_id}].transform"))
    rep = _select(raw, scale, choice, f"cell[{cell_id}]")
    rep_id = _text(rep.get("id"), f"cell[{cell_id}].representation.id", 80)
    mode = _text(rep.get("mode"), f"cell[{cell_id}].representation.mode", 40).casefold()
    children = raw.get("children", [])
    if not isinstance(children, list):
        raise VectorCellError(f"cell[{cell_id}].children must be a list")
    row = {"cell_id": cell_id, "path": path, "role": _text(raw.get("role", "visual-cell"), f"cell[{cell_id}].role"),
           "representation_id": rep_id, "mode": mode, "choice": choice, "observation_scale": scale,
           "child_count": len(children), "transform": t}
    if mode == "expression":
        objects = rep.get("objects")
        if not isinstance(objects, list) or not objects:
            raise VectorCellError("expression representation requires objects", {"cell_id": cell_id, "representation_id": rep_id})
        resolved = [_object(o, path, t, int(rep.get("z_offset", 0)),
                            f"cell[{cell_id}].representation[{rep_id}].objects[{i}]") for i, o in enumerate(objects)]
        row.update(resolved_object_count=len(resolved), merged_child_cells=len(children), split_child_cells=0)
        stats["expression_cells"] += 1
        stats["merged_child_cells"] += len(children)
        stats["resolved_objects"] += len(resolved)
        trace.append(row)
        return resolved
    if mode != "children" or not children:
        raise VectorCellError("children representation requires child cells", {"cell_id": cell_id, "representation_id": rep_id})
    row.update(resolved_object_count=0, merged_child_cells=0, split_child_cells=len(children))
    stats["split_parent_cells"] += 1
    stats["split_child_cells"] += len(children)
    trace.append(row)
    resolved: list[dict[str, Any]] = []
    for child in children:
        resolved.extend(_cell(child, scale=scale, choice=choice, parent_t=t, prefix=path,
                              depth=depth + 1, seen=seen, stats=stats, trace=trace))
    return resolved


def resolve_vector_cells(raw: Any, *, observation_scale: Any, choice: Any = "default") -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") not in {None, VECTOR_CELL_FABRIC_SCHEMA}:
        raise VectorCellError("vector-cell fabric is missing or has unsupported schema")
    scale = _num(observation_scale, "observation_scale", 0.0001, 1_000_000)
    choice = _text(choice, "choice", 120)
    canvas = raw.get("canvas")
    cells = raw.get("cells")
    if not isinstance(canvas, dict) or not isinstance(cells, list) or not cells:
        raise VectorCellError("vector-cell fabric requires canvas and non-empty cells")
    fabric = copy.deepcopy(raw)
    fabric["schema"] = VECTOR_CELL_FABRIC_SCHEMA
    fabric["intent"] = _text(raw.get("intent", "adaptive vector-cell creation"), "intent", 2000)
    fabric["canvas"] = {"width": int(_num(canvas.get("width"), "canvas.width", 1, 8192)),
                        "height": int(_num(canvas.get("height"), "canvas.height", 1, 8192)),
                        "background": _text(canvas.get("background", "#000000"), "canvas.background", 9)}
    trace: list[dict[str, Any]] = []
    stats = dict(cells_visited=0, expression_cells=0, split_parent_cells=0,
                 merged_child_cells=0, split_child_cells=0, resolved_objects=0)
    objects: list[dict[str, Any]] = []
    seen: set[str] = set()
    for cell in cells:
        objects.extend(_cell(cell, scale=scale, choice=choice, parent_t={"x": 0.0, "y": 0.0, "scale": 1.0},
                             prefix="", depth=1, seen=seen, stats=stats, trace=trace))
    raw_thought = {"intent": fabric["intent"], "canvas": fabric["canvas"],
                   "camera": copy.deepcopy(raw.get("camera", {"x": 0, "y": 0, "zoom": 1})), "objects": objects}
    try:
        thought = validate_visual_thought(raw_thought)
        svg = render_cinematic_svg(thought)
    except PaintgunError as exc:
        raise VectorCellError("resolved vector cells are not Paintgun-materializable",
                              {"reason": str(exc), "details": exc.details}) from exc
    digest = thought_digest(thought)
    return {
        "schema": VECTOR_CELL_RESOLUTION_SCHEMA,
        "operation": "resolve-vector-cells",
        "truth_status": "EXACT_SCALE_AND_CHOICE_BOUND_VECTOR_CELL_RESOLUTION",
        "status": "READY_VECTOR_CELL_THOUGHT",
        "fabric_digest": _digest(fabric),
        "observation": {"scale": scale, "choice": choice},
        "resolution": trace,
        "stats": stats,
        "thought": thought,
        "thought_digest": digest,
        "cinematic_projection": {"available": True, "thought_digest": digest, "svg": svg},
        "simulation_input": {"thought": thought},
        "limitations": [
            "representations are selected from explicitly supplied cell states; missing detail is not invented",
            "merged and split forms preserve cell identity structurally, not as proof of semantic or physical equivalence",
            "vector geometry stays resolution-independent until rasterized at an observation boundary; this does not create infinite physical detail",
            "v0 transformed SVG path data is intentionally unsupported",
        ],
    }

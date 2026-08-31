from __future__ import annotations

import copy
import hashlib
import html
import json
import math
import re
from pathlib import Path
from typing import Any

from .project import ProjectError, build_project


PAINTGUN_THOUGHT_SCHEMA = "axm.paintgun-visual-thought/v0.1"
PAINT_CHANNELS = ("shape", "material", "color", "light", "shade", "skin")
SHAPE_KINDS = {"rect", "circle", "ellipse", "polygon", "path"}
SKIN_KINDS = {"solid", "linear-gradient", "radial-gradient"}
HEX_COLOR_RE = re.compile(r"#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?")
MAX_OBJECTS = 128
MAX_CANVAS = 8192


class PaintgunError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def thought_digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical_bytes(value)).hexdigest()}"


def _required_text(value: Any, label: str, maximum: int = 400) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PaintgunError(f"{label} must be non-empty text")
    text = value.strip()
    if len(text) > maximum:
        raise PaintgunError(f"{label} exceeds its {maximum}-character bound")
    return text


def _number(value: Any, label: str, minimum: float | None = None, maximum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise PaintgunError(f"{label} must be a finite number")
    result = float(value)
    if minimum is not None and result < minimum:
        raise PaintgunError(f"{label} must be >= {minimum}")
    if maximum is not None and result > maximum:
        raise PaintgunError(f"{label} must be <= {maximum}")
    return result


def _color(value: Any, label: str) -> str:
    text = _required_text(value, label, maximum=9)
    if HEX_COLOR_RE.fullmatch(text) is None:
        raise PaintgunError(f"{label} must be #RRGGBB or #RRGGBBAA", {"value": text})
    return text.upper()


def _validate_shape(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    kind = _required_text(raw.get("kind"), f"{label}.kind", 40).casefold()
    if kind not in SHAPE_KINDS:
        raise PaintgunError(f"{label}.kind is unsupported", {"kind": kind, "supported": sorted(SHAPE_KINDS)})
    result = copy.deepcopy(raw)
    result["kind"] = kind
    if kind == "rect":
        for key in ("x", "y", "width", "height"):
            result[key] = _number(raw.get(key), f"{label}.{key}", 0)
        result["rx"] = _number(raw.get("rx", 0), f"{label}.rx", 0)
    elif kind == "circle":
        result["cx"] = _number(raw.get("cx"), f"{label}.cx", 0)
        result["cy"] = _number(raw.get("cy"), f"{label}.cy", 0)
        result["r"] = _number(raw.get("r"), f"{label}.r", 0)
    elif kind == "ellipse":
        result["cx"] = _number(raw.get("cx"), f"{label}.cx", 0)
        result["cy"] = _number(raw.get("cy"), f"{label}.cy", 0)
        result["rx"] = _number(raw.get("rx"), f"{label}.rx", 0)
        result["ry"] = _number(raw.get("ry"), f"{label}.ry", 0)
    elif kind == "polygon":
        points = raw.get("points")
        if not isinstance(points, list) or len(points) < 3 or len(points) > 256:
            raise PaintgunError(f"{label}.points must contain 3..256 coordinate pairs")
        normalized: list[list[float]] = []
        for index, point in enumerate(points):
            if not isinstance(point, list) or len(point) != 2:
                raise PaintgunError(f"{label}.points[{index}] must be [x, y]")
            normalized.append([
                _number(point[0], f"{label}.points[{index}][0]", 0),
                _number(point[1], f"{label}.points[{index}][1]", 0),
            ])
        result["points"] = normalized
    elif kind == "path":
        result["d"] = _required_text(raw.get("d"), f"{label}.d", 10000)
    return result


def _validate_material(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    result = copy.deepcopy(raw)
    result["name"] = _required_text(raw.get("name"), f"{label}.name", 120)
    result["metallic"] = _number(raw.get("metallic", 0), f"{label}.metallic", 0, 1)
    result["roughness"] = _number(raw.get("roughness", 0.5), f"{label}.roughness", 0, 1)
    result["opacity"] = _number(raw.get("opacity", 1), f"{label}.opacity", 0, 1)
    result["emission"] = _number(raw.get("emission", 0), f"{label}.emission", 0, 4)
    return result


def _validate_color(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    result = copy.deepcopy(raw)
    result["fill"] = _color(raw.get("fill"), f"{label}.fill")
    result["stroke"] = _color(raw.get("stroke", result["fill"]), f"{label}.stroke")
    result["stroke_width"] = _number(raw.get("stroke_width", 0), f"{label}.stroke_width", 0, 100)
    return result


def _validate_light(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    result = copy.deepcopy(raw)
    result["color"] = _color(raw.get("color", "#FFFFFF"), f"{label}.color")
    result["intensity"] = _number(raw.get("intensity", 0), f"{label}.intensity", 0, 4)
    result["x"] = _number(raw.get("x", 0), f"{label}.x")
    result["y"] = _number(raw.get("y", 0), f"{label}.y")
    result["radius"] = _number(raw.get("radius", 0), f"{label}.radius", 0, MAX_CANVAS)
    return result


def _validate_shade(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    result = copy.deepcopy(raw)
    result["color"] = _color(raw.get("color", "#000000"), f"{label}.color")
    result["dx"] = _number(raw.get("dx", 0), f"{label}.dx", -MAX_CANVAS, MAX_CANVAS)
    result["dy"] = _number(raw.get("dy", 0), f"{label}.dy", -MAX_CANVAS, MAX_CANVAS)
    result["blur"] = _number(raw.get("blur", 0), f"{label}.blur", 0, 256)
    result["opacity"] = _number(raw.get("opacity", 0), f"{label}.opacity", 0, 1)
    return result


def _validate_skin(raw: Any, label: str, fallback_color: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError(f"{label} must be an object")
    kind = _required_text(raw.get("kind", "solid"), f"{label}.kind", 40).casefold()
    if kind not in SKIN_KINDS:
        raise PaintgunError(f"{label}.kind is unsupported", {"kind": kind, "supported": sorted(SKIN_KINDS)})
    result = copy.deepcopy(raw)
    result["kind"] = kind
    colors = raw.get("colors", [fallback_color])
    if not isinstance(colors, list) or not colors or len(colors) > 16:
        raise PaintgunError(f"{label}.colors must contain 1..16 colors")
    result["colors"] = [_color(value, f"{label}.colors[{index}]") for index, value in enumerate(colors)]
    result["angle"] = _number(raw.get("angle", 0), f"{label}.angle", -360, 360)
    return result


def validate_visual_thought(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise PaintgunError("visual thought must be an object")
    if raw.get("schema") not in {None, PAINTGUN_THOUGHT_SCHEMA}:
        raise PaintgunError("visual thought schema is unsupported", {"actual_schema": raw.get("schema")})
    canvas = raw.get("canvas")
    if not isinstance(canvas, dict):
        raise PaintgunError("visual thought canvas must be an object")
    width = int(_number(canvas.get("width"), "canvas.width", 1, MAX_CANVAS))
    height = int(_number(canvas.get("height"), "canvas.height", 1, MAX_CANVAS))
    background = _color(canvas.get("background", "#000000"), "canvas.background")
    objects = raw.get("objects")
    if not isinstance(objects, list) or not objects or len(objects) > MAX_OBJECTS:
        raise PaintgunError(f"visual thought objects must contain 1..{MAX_OBJECTS} entries")
    normalized_objects: list[dict[str, Any]] = []
    ids: set[str] = set()
    for index, raw_object in enumerate(objects):
        if not isinstance(raw_object, dict):
            raise PaintgunError(f"objects[{index}] must be an object")
        object_id = _required_text(raw_object.get("id"), f"objects[{index}].id", 120)
        if object_id in ids:
            raise PaintgunError("visual object ids must be unique", {"duplicate": object_id})
        ids.add(object_id)
        missing = [channel for channel in PAINT_CHANNELS if channel not in raw_object]
        if missing:
            raise PaintgunError(
                "paintgun object is not composition-complete",
                {"object_id": object_id, "missing_channels": missing, "required_channels": list(PAINT_CHANNELS)},
            )
        color = _validate_color(raw_object["color"], f"objects[{index}].color")
        normalized_objects.append({
            "id": object_id,
            "z": int(_number(raw_object.get("z", index), f"objects[{index}].z", -100000, 100000)),
            "shape": _validate_shape(raw_object["shape"], f"objects[{index}].shape"),
            "material": _validate_material(raw_object["material"], f"objects[{index}].material"),
            "color": color,
            "light": _validate_light(raw_object["light"], f"objects[{index}].light"),
            "shade": _validate_shade(raw_object["shade"], f"objects[{index}].shade"),
            "skin": _validate_skin(raw_object["skin"], f"objects[{index}].skin", color["fill"]),
        })
    camera = raw.get("camera", {})
    if not isinstance(camera, dict):
        raise PaintgunError("camera must be an object")
    normalized_camera = {
        "x": _number(camera.get("x", 0), "camera.x", -MAX_CANVAS, MAX_CANVAS),
        "y": _number(camera.get("y", 0), "camera.y", -MAX_CANVAS, MAX_CANVAS),
        "zoom": _number(camera.get("zoom", 1), "camera.zoom", 0.05, 20),
    }
    return {
        "schema": PAINTGUN_THOUGHT_SCHEMA,
        "intent": _required_text(raw.get("intent", "visual creation"), "intent", 2000),
        "canvas": {"width": width, "height": height, "background": background},
        "camera": normalized_camera,
        "objects": sorted(normalized_objects, key=lambda row: (row["z"], row["id"])),
    }


def _svg_shape(shape: dict[str, Any], *, fill: str, stroke: str, stroke_width: float, filter_id: str, opacity: float) -> str:
    common = (
        f' fill="{html.escape(fill)}" stroke="{html.escape(stroke)}" '
        f'stroke-width="{stroke_width:g}" opacity="{opacity:g}" filter="url(#{filter_id})"'
    )
    kind = shape["kind"]
    if kind == "rect":
        return f'<rect x="{shape["x"]:g}" y="{shape["y"]:g}" width="{shape["width"]:g}" height="{shape["height"]:g}" rx="{shape["rx"]:g}"{common}/>'
    if kind == "circle":
        return f'<circle cx="{shape["cx"]:g}" cy="{shape["cy"]:g}" r="{shape["r"]:g}"{common}/>'
    if kind == "ellipse":
        return f'<ellipse cx="{shape["cx"]:g}" cy="{shape["cy"]:g}" rx="{shape["rx"]:g}" ry="{shape["ry"]:g}"{common}/>'
    if kind == "polygon":
        points = " ".join(f"{point[0]:g},{point[1]:g}" for point in shape["points"])
        return f'<polygon points="{points}"{common}/>'
    return f'<path d="{html.escape(shape["d"], quote=True)}"{common}/>'


def render_cinematic_svg(raw_thought: Any) -> str:
    thought = validate_visual_thought(raw_thought)
    width = thought["canvas"]["width"]
    height = thought["canvas"]["height"]
    defs: list[str] = []
    bodies: list[str] = []
    for index, obj in enumerate(thought["objects"]):
        filter_id = f"axm-filter-{index}"
        shade = obj["shade"]
        emission = obj["material"]["emission"]
        light = obj["light"]
        defs.append(
            f'<filter id="{filter_id}" x="-50%" y="-50%" width="200%" height="200%">'
            f'<feDropShadow dx="{shade["dx"]:g}" dy="{shade["dy"]:g}" stdDeviation="{shade["blur"]:g}" '
            f'flood-color="{shade["color"]}" flood-opacity="{shade["opacity"]:g}"/>'
            f'<feDropShadow dx="0" dy="0" stdDeviation="{max(0.0, emission * 3 + light["intensity"]):g}" '
            f'flood-color="{light["color"]}" flood-opacity="{min(1.0, (emission + light["intensity"]) / 4):g}"/>'
            "</filter>"
        )
        skin = obj["skin"]
        fill = obj["color"]["fill"]
        if skin["kind"] in {"linear-gradient", "radial-gradient"} and len(skin["colors"]) > 1:
            gradient_id = f"axm-skin-{index}"
            stops = []
            denominator = max(1, len(skin["colors"]) - 1)
            for color_index, color in enumerate(skin["colors"]):
                stops.append(f'<stop offset="{(color_index / denominator) * 100:g}%" stop-color="{color}"/>')
            if skin["kind"] == "linear-gradient":
                radians = math.radians(skin["angle"])
                x2 = 50 + math.cos(radians) * 50
                y2 = 50 + math.sin(radians) * 50
                defs.append(f'<linearGradient id="{gradient_id}" x1="{100-x2:g}%" y1="{100-y2:g}%" x2="{x2:g}%" y2="{y2:g}%">{"".join(stops)}</linearGradient>')
            else:
                defs.append(f'<radialGradient id="{gradient_id}">{"".join(stops)}</radialGradient>')
            fill = f"url(#{gradient_id})"
        bodies.append(
            f'<g id="{html.escape(obj["id"], quote=True)}" data-material="{html.escape(obj["material"]["name"], quote=True)}" '
            f'data-metallic="{obj["material"]["metallic"]:g}" data-roughness="{obj["material"]["roughness"]:g}">'
            + _svg_shape(
                obj["shape"],
                fill=fill,
                stroke=obj["color"]["stroke"],
                stroke_width=obj["color"]["stroke_width"],
                filter_id=filter_id,
                opacity=obj["material"]["opacity"],
            )
            + "</g>"
        )
    camera = thought["camera"]
    transform = f'translate({camera["x"]:g} {camera["y"]:g}) scale({camera["zoom"]:g})'
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
        f'role="img" aria-label="AXM simulated visual thought">'
        f'<rect width="100%" height="100%" fill="{thought["canvas"]["background"]}"/>'
        f'<defs>{"".join(defs)}</defs><g transform="{transform}">{"".join(bodies)}</g></svg>\n'
    )


def materialize_simulated_thought(
    target: Path,
    simulation: Any,
    *,
    replace: bool = False,
) -> dict[str, Any]:
    if not isinstance(simulation, dict):
        raise PaintgunError("simulation must be an object")
    if simulation.get("status") != "NO_KNOWN_IMPROVEMENTS":
        raise PaintgunError(
            "paintgun materialization requires a simulation that reached NO_KNOWN_IMPROVEMENTS",
            {"status": simulation.get("status")},
        )
    thought = validate_visual_thought(simulation.get("thought"))
    digest = thought_digest(thought)
    if simulation.get("thought_digest") != digest:
        raise PaintgunError(
            "simulated thought digest does not match the thought being materialized",
            {"expected": simulation.get("thought_digest"), "actual": digest},
        )
    svg = render_cinematic_svg(thought)
    preview = simulation.get("cinematic_projection")
    if not isinstance(preview, dict) or preview.get("svg") != svg:
        raise PaintgunError("cinematic projection does not match the exact simulated thought")
    thought_json = json.dumps(thought, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    index = (
        "<!doctype html><html lang=\"en\"><head><meta charset=\"utf-8\">"
        "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        "<title>AXM Paintgun Thought Materialization</title>"
        "<style>html,body{margin:0;background:#05070b;color:#fff;font-family:system-ui}main{min-height:100vh;display:grid;place-items:center}img{max-width:100%;height:auto}</style>"
        "</head><body><main><img src=\"scene.svg\" alt=\"Materialized simulated thought\"></main></body></html>\n"
    )
    try:
        built = build_project(
            target=Path(target),
            files={"index.html": index, "scene.svg": svg, "thought.json": thought_json},
            project_type="static-web",
            checks=[
                {"type": "file-exists", "path": "scene.svg"},
                {"type": "file-exists", "path": "thought.json"},
                {"type": "contains", "path": "scene.svg", "text": "AXM simulated visual thought"},
            ],
            replace=replace,
            publish_mode="validated",
        )
    except ProjectError as exc:
        raise PaintgunError(str(exc), exc.details) from exc
    return {
        "operation": "materialize-simulated-thought",
        "truth_status": "MATERIALIZED_EXACT_SIMULATED_VISUAL_THOUGHT",
        "path": str(Path(target).resolve()),
        "thought_digest": digest,
        "simulation_status": simulation["status"],
        "paint_channels": list(PAINT_CHANNELS),
        "cinematic_projection_equal_to_materialized_scene": True,
        "project": built,
        "limitations": [
            "the renderer expresses the current bounded SVG paint grammar, not every physical material or lighting phenomenon",
            "material names are open descriptors; metallic, roughness, opacity, emission, shade, skin, and light fields are the currently rendered surface parameters",
            "matching the cinematic projection proves state transfer for this grammar, not that the simulation predicted all real browser, physical, or human-perception effects",
        ],
    }


def operate_paintgun(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    target = Path(str(inputs.get("path", ""))).expanduser()
    if not target.is_absolute():
        target = Path(root) / target
    replace = inputs.get("replace", False)
    if not isinstance(replace, bool):
        raise PaintgunError("replace must be boolean")
    return materialize_simulated_thought(target.resolve(), inputs.get("simulation"), replace=replace)

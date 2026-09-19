from __future__ import annotations

import hashlib
import json
import math
import re
from copy import deepcopy
from pathlib import Path
from typing import Any

from .procedural_3d import MAX_PRIMITIVES, publish_glb


SCHEMA = "axm.shape-recipe/v0.1"
MAX_RECIPE_DEPTH = 8
MAX_COMPOSITION_DEPTH = 4
MAX_DEFINITIONS = 64
MAX_RECIPE_NODES = 4_000
MAX_EXPRESSION_DEPTH = 32
SOURCE_PROVENANCE = {
    "kind": "behavioral-design-donor",
    "repository": "https://github.com/mike-axiom-mir/axm-morphtile",
    "commit": "379098956c4da962b70ad68b60ea1bb8a75f5028",
    "source_path": "core/morphtile.js",
    "source_feature": "bounded recipe meshes, composed definitions, per-use settings, and position-driven paint",
    "integration": "UC-native Python implementation targeting axm.procedural-3d/v0.1; no MorphTile runtime is embedded",
}
_NAME_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,63}$")
_SHAPES = {"box", "cylinder", "pyramid"}
_DEFAULT_MATERIAL = {"color": "#9999B3FF", "metallic": 0.0, "roughness": 0.6}


class ShapeRecipeError(RuntimeError):
    def __init__(self, status: str, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.status = status
        self.details = {"status": status, **(details or {})}


def shape_recipe_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_BOUNDED_DETERMINISTIC_SHAPE_RECIPE_COMPILER",
        "schema": SCHEMA,
        "expression_operators": [
            "var", "+", "-", "*", "/", "%", "min", "max", "floor",
            "==", "!=", "<", ">", "<=", ">=", "and", "or", "not", "if",
        ],
        "primitive_grammar": sorted(_SHAPES),
        "maximum_parts": MAX_PRIMITIVES,
        "maximum_recipe_depth": MAX_RECIPE_DEPTH,
        "maximum_composition_depth": MAX_COMPOSITION_DEPTH,
        "maximum_definitions": MAX_DEFINITIONS,
        "maximum_recipe_nodes_visited": MAX_RECIPE_NODES,
        "composed_definitions": True,
        "per_use_settings": True,
        "position_paint": "evaluated at each generated primitive center",
        "source_provenance": deepcopy(SOURCE_PROVENANCE),
        "rendered_appearance_or_host_compatibility_proven": False,
    }


def _hold(status: str, message: str, **details: Any) -> None:
    raise ShapeRecipeError(status, message, details)


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ShapeRecipeError(
            "HOLD_SHAPE_RECIPE_INVALID",
            "shape recipe must be finite JSON data",
        ) from exc


def _closed(raw: Any, label: str, *, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} must be an object", label=label)
    optional = optional or set()
    missing = sorted(required - set(raw))
    unexpected = sorted(set(raw) - required - optional)
    if missing or unexpected:
        _hold(
            "HOLD_SHAPE_RECIPE_INVALID",
            f"{label} fields do not match the bounded grammar",
            label=label,
            missing_fields=missing,
            unexpected_fields=unexpected,
        )
    return raw


def _literal_number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} must be a finite number", label=label)
    result = float(value)
    if not math.isfinite(result) or not minimum <= result <= maximum:
        _hold(
            "HOLD_SHAPE_RECIPE_INVALID",
            f"{label} must be from {minimum} through {maximum}",
            label=label,
        )
    return result


def _truthy(value: Any) -> bool:
    if value is None or value is False:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return value != 0 and not math.isnan(float(value))
    return bool(value)


def _same_value(left: Any, right: Any) -> bool:
    if isinstance(left, bool) or isinstance(right, bool):
        return isinstance(left, bool) and isinstance(right, bool) and left == right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return float(left) == float(right)
    return type(left) is type(right) and left == right


def _evaluate(expression: Any, variables: dict[str, float], scope: dict[str, float], depth: int = 0) -> Any:
    if depth > MAX_EXPRESSION_DEPTH:
        _hold(
            "HOLD_SHAPE_RECIPE_EXPRESSION_TOO_DEEP",
            f"shape recipe expressions may nest at most {MAX_EXPRESSION_DEPTH} levels",
        )
    if isinstance(expression, bool):
        return expression
    if isinstance(expression, (int, float)):
        if not math.isfinite(float(expression)):
            _hold("HOLD_SHAPE_RECIPE_EXPRESSION", "shape recipe expression contains a non-finite number")
        return expression
    if not isinstance(expression, list) or not expression or not isinstance(expression[0], str):
        _hold(
            "HOLD_SHAPE_RECIPE_EXPRESSION",
            "shape recipe expressions must be finite numbers, booleans, or operator arrays",
            expression=expression,
        )

    operator = expression[0]
    arity = {
        "var": 1,
        "+": 2,
        "-": 2,
        "*": 2,
        "/": 2,
        "%": 2,
        "min": 2,
        "max": 2,
        "floor": 1,
        "==": 2,
        "!=": 2,
        "<": 2,
        ">": 2,
        "<=": 2,
        ">=": 2,
        "and": 2,
        "or": 2,
        "not": 1,
        "if": 3,
    }
    if operator not in arity or len(expression) != arity[operator] + 1:
        _hold(
            "HOLD_SHAPE_RECIPE_EXPRESSION",
            "shape recipe expression uses an unknown operator or wrong arity",
            operator=operator,
        )
    if operator == "var":
        name = expression[1]
        if not isinstance(name, str) or not _NAME_RE.fullmatch(name):
            _hold("HOLD_SHAPE_RECIPE_EXPRESSION", "shape recipe variable name is invalid", variable=name)
        if name in scope:
            return scope[name]
        if name in variables:
            return variables[name]
        _hold("HOLD_SHAPE_RECIPE_UNKNOWN_VARIABLE", "shape recipe variable is not defined", variable=name)

    def value(index: int) -> Any:
        return _evaluate(expression[index + 1], variables, scope, depth + 1)

    if operator == "and":
        return bool(_truthy(value(0)) and _truthy(value(1)))
    if operator == "or":
        return bool(_truthy(value(0)) or _truthy(value(1)))
    if operator == "not":
        return not _truthy(value(0))
    if operator == "if":
        return value(1) if _truthy(value(0)) else value(2)
    if operator in {"==", "!="}:
        same = _same_value(value(0), value(1))
        return same if operator == "==" else not same

    left = value(0)
    right = value(1) if arity[operator] == 2 else None
    if isinstance(left, bool) or not isinstance(left, (int, float)):
        _hold("HOLD_SHAPE_RECIPE_EXPRESSION", "numeric operator received a non-number", operator=operator)
    left = float(left)
    if right is not None:
        if isinstance(right, bool) or not isinstance(right, (int, float)):
            _hold("HOLD_SHAPE_RECIPE_EXPRESSION", "numeric operator received a non-number", operator=operator)
        right = float(right)

    if operator == "+":
        result = left + right
    elif operator == "-":
        result = left - right
    elif operator == "*":
        result = left * right
    elif operator == "/":
        result = 0.0 if right == 0 else left / right
    elif operator == "%":
        result = 0.0 if right == 0 else left - math.trunc(left / right) * right
    elif operator == "min":
        result = min(left, right)
    elif operator == "max":
        result = max(left, right)
    elif operator == "floor":
        result = math.floor(left)
    elif operator == "<":
        return left < right
    elif operator == ">":
        return left > right
    elif operator == "<=":
        return left <= right
    else:
        return left >= right
    if not math.isfinite(float(result)):
        _hold("HOLD_SHAPE_RECIPE_EXPRESSION", "shape recipe expression produced a non-finite number")
    return result


def _number(expression: Any, variables: dict[str, float], scope: dict[str, float], label: str,
            minimum: float, maximum: float) -> float:
    value = _evaluate(expression, variables, scope)
    return _literal_number(value, label, minimum, maximum)


def _vector(expression: Any, variables: dict[str, float], scope: dict[str, float], label: str,
            default: list[float], minimum: float, maximum: float) -> list[float]:
    if expression is None:
        return list(default)
    if not isinstance(expression, list) or len(expression) != 3:
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} must contain exactly three expressions", label=label)
    return [
        _number(item, variables, scope, f"{label}[{index}]", minimum, maximum)
        for index, item in enumerate(expression)
    ]


def _material(raw: Any, label: str) -> dict[str, Any]:
    material = _closed(raw, label, required={"color", "metallic", "roughness"}, optional={"emissive"})
    color = material["color"]
    if not isinstance(color, str) or len(color) not in {7, 9} or not color.startswith("#"):
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label}.color must be #RRGGBB or #RRGGBBAA")
    try:
        int(color[1:], 16)
    except ValueError:
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label}.color must be #RRGGBB or #RRGGBBAA")
    normalized = {
        "color": color.upper(),
        "metallic": _literal_number(material["metallic"], f"{label}.metallic", 0.0, 1.0),
        "roughness": _literal_number(material["roughness"], f"{label}.roughness", 0.0, 1.0),
    }
    if "emissive" in material:
        emissive = material["emissive"]
        if not isinstance(emissive, str) or len(emissive) not in {7, 9} or not emissive.startswith("#"):
            _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label}.emissive must be #RRGGBB or #RRGGBBAA")
        try:
            int(emissive[1:], 16)
        except ValueError:
            _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label}.emissive must be #RRGGBB or #RRGGBBAA")
        normalized["emissive"] = emissive.upper()
    return normalized


def _color_material(raw: Any, variables: dict[str, float], scope: dict[str, float],
                    base: dict[str, Any], label: str) -> dict[str, Any]:
    if not isinstance(raw, list) or len(raw) not in {3, 4}:
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} must contain three or four expressions")
    channels = [
        _number(item, variables, scope, f"{label}[{index}]", 0.0, 1.0)
        for index, item in enumerate(raw)
    ]
    if len(channels) == 3:
        channels.append(1.0)
    encoded = "#" + "".join(f"{math.floor(channel * 255 + 0.5):02X}" for channel in channels)
    material = deepcopy(base)
    material["color"] = encoded
    return material


def _variables(raw: Any, label: str) -> dict[str, float]:
    if not isinstance(raw, dict):
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} must be an object", label=label)
    variables: dict[str, float] = {}
    for key, value in raw.items():
        if not isinstance(key, str) or not _NAME_RE.fullmatch(key):
            _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label} contains an invalid variable name", variable=key)
        variables[key] = _literal_number(value, f"{label}.{key}", -100_000.0, 100_000.0)
    return variables


def _paint(raw: Any, label: str) -> dict[str, Any]:
    paint = _closed(raw, label, required={"color"}, optional={"vars"})
    color = paint["color"]
    if not isinstance(color, list) or len(color) not in {3, 4}:
        _hold("HOLD_SHAPE_RECIPE_INVALID", f"{label}.color must contain three or four expressions")
    return {"vars": _variables(paint.get("vars", {}), f"{label}.vars"), "color": deepcopy(color)}


def _scale_vector(raw: Any, variables: dict[str, float], scope: dict[str, float], label: str) -> list[float]:
    if raw is None:
        return [1.0, 1.0, 1.0]
    if isinstance(raw, (int, float)) and not isinstance(raw, bool):
        value = _literal_number(raw, label, 0.001, 10_000.0)
        return [value, value, value]
    return _vector(raw, variables, scope, label, [1.0, 1.0, 1.0], 0.001, 10_000.0)


def compile_shape_recipe(raw: Any) -> dict[str, Any]:
    recipe = _closed(
        raw,
        "recipe",
        required={"schema", "name", "parts"},
        optional={"vars", "budget", "material", "definitions", "paint"},
    )
    if recipe["schema"] != SCHEMA:
        _hold("HOLD_SHAPE_RECIPE_INVALID", "unsupported shape recipe schema", expected=SCHEMA)
    name = recipe["name"]
    if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
        _hold("HOLD_SHAPE_RECIPE_INVALID", "recipe.name must contain 1 through 120 characters")
    parts = recipe["parts"]
    if not isinstance(parts, list) or not parts:
        _hold("HOLD_SHAPE_RECIPE_INVALID", "recipe.parts must be a non-empty list")
    variables = _variables(recipe.get("vars", {}), "recipe.vars")

    declared_budget = recipe.get("budget", MAX_RECIPE_NODES)
    if isinstance(declared_budget, bool) or not isinstance(declared_budget, int) or not 1 <= declared_budget <= MAX_RECIPE_NODES:
        _hold(
            "HOLD_SHAPE_RECIPE_INVALID",
            f"recipe.budget must be an integer from 1 through {MAX_RECIPE_NODES}",
        )
    effective_budget = min(declared_budget, MAX_PRIMITIVES)
    default_material = _material(recipe.get("material", _DEFAULT_MATERIAL), "recipe.material")
    root_paint = _paint(recipe["paint"], "recipe.paint") if "paint" in recipe else None

    raw_definitions = recipe.get("definitions", {})
    if not isinstance(raw_definitions, dict) or len(raw_definitions) > MAX_DEFINITIONS:
        _hold(
            "HOLD_SHAPE_RECIPE_INVALID",
            f"recipe.definitions must be an object with at most {MAX_DEFINITIONS} entries",
        )
    definitions: dict[str, dict[str, Any]] = {}
    for definition_name, raw_definition in raw_definitions.items():
        if not isinstance(definition_name, str) or not _NAME_RE.fullmatch(definition_name):
            _hold(
                "HOLD_SHAPE_RECIPE_INVALID",
                "recipe definition name is invalid",
                definition=definition_name,
            )
        definition = _closed(
            raw_definition,
            f"recipe.definitions.{definition_name}",
            required={"parts"},
            optional={"vars", "material", "paint"},
        )
        definition_parts = definition["parts"]
        if not isinstance(definition_parts, list) or not definition_parts:
            _hold(
                "HOLD_SHAPE_RECIPE_INVALID",
                f"recipe.definitions.{definition_name}.parts must be a non-empty list",
            )
        definitions[definition_name] = {
            "parts": definition_parts,
            "vars": _variables(
                definition.get("vars", {}),
                f"recipe.definitions.{definition_name}.vars",
            ),
            "material": _material(
                definition.get("material", _DEFAULT_MATERIAL),
                f"recipe.definitions.{definition_name}.material",
            ),
            "paint": _paint(
                definition["paint"],
                f"recipe.definitions.{definition_name}.paint",
            ) if "paint" in definition else None,
        }

    nodes_visited = 0
    generated_count = 0
    composition_uses = 0
    settings_overrides = 0
    paint_applications = 0
    deepest_composition_depth = 0

    def expand(
        nodes: Any,
        active_variables: dict[str, float],
        active_material: dict[str, Any],
        active_paint: dict[str, Any] | None,
        seen: tuple[str, ...],
        composition_depth: int,
        label: str,
    ) -> list[dict[str, Any]]:
        nonlocal nodes_visited, generated_count, composition_uses
        nonlocal settings_overrides, paint_applications, deepest_composition_depth
        expanded: list[dict[str, Any]] = []

        def walk(body: Any, scope: dict[str, float], depth: int) -> None:
            nonlocal nodes_visited, generated_count, composition_uses
            nonlocal settings_overrides, deepest_composition_depth
            if depth > MAX_RECIPE_DEPTH:
                _hold(
                    "HOLD_SHAPE_RECIPE_TOO_DEEP",
                    f"shape recipe bodies may nest at most {MAX_RECIPE_DEPTH} levels",
                    depth=depth,
                    body=label,
                )
            if not isinstance(body, list):
                _hold("HOLD_SHAPE_RECIPE_INVALID", "recipe body must be a list", body=label)
            for raw_node in body:
                nodes_visited += 1
                if nodes_visited > MAX_RECIPE_NODES:
                    _hold(
                        "HOLD_SHAPE_RECIPE_NODE_BUDGET",
                        "shape recipe exceeded its structural node-visit budget",
                        maximum=MAX_RECIPE_NODES,
                    )
                if not isinstance(raw_node, dict):
                    _hold("HOLD_SHAPE_RECIPE_INVALID", "recipe node must be an object", body=label)
                if "repeat" in raw_node:
                    node = _closed(raw_node, "repeat node", required={"repeat", "body"}, optional={"as"})
                    loop_name = node.get("as", "i")
                    if not isinstance(loop_name, str) or not _NAME_RE.fullmatch(loop_name):
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "repeat.as must be a portable variable name")
                    raw_count = _number(
                        node["repeat"], active_variables, scope, "repeat", -100_000.0, 100_000.0
                    )
                    count = max(0, math.floor(raw_count))
                    if count > effective_budget:
                        _hold(
                            "HOLD_SHAPE_RECIPE_OVER_BUDGET",
                            "shape recipe loop exceeds the receiver's primitive budget",
                            repeat=count,
                            maximum=effective_budget,
                        )
                    for index in range(count):
                        inner = dict(scope)
                        inner[loop_name] = float(index)
                        inner[f"{loop_name}_of"] = float(count)
                        inner[f"{loop_name}_at"] = index / (count - 1) if count > 1 else 0.0
                        walk(node["body"], inner, depth + 1)
                    continue
                if "body" in raw_node:
                    node = _closed(raw_node, "group node", required={"body"}, optional={"when"})
                    if "when" in node and not _truthy(_evaluate(node["when"], active_variables, scope)):
                        continue
                    walk(node["body"], scope, depth + 1)
                    continue
                if "use" in raw_node:
                    node = _closed(
                        raw_node,
                        "use node",
                        required={"use"},
                        optional={"when", "with", "pos", "scale", "rot", "color", "material"},
                    )
                    if "when" in node and not _truthy(_evaluate(node["when"], active_variables, scope)):
                        continue
                    definition_name = node["use"]
                    if not isinstance(definition_name, str) or not _NAME_RE.fullmatch(definition_name):
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "use must name a portable recipe definition")
                    if definition_name not in definitions:
                        _hold(
                            "HOLD_SHAPE_RECIPE_DEFINITION_NOT_FOUND",
                            "composed recipe definition is not present",
                            definition=definition_name,
                        )
                    if definition_name in seen:
                        _hold(
                            "HOLD_SHAPE_RECIPE_USES_ITSELF",
                            "a composed shape cannot contain itself",
                            definition=definition_name,
                            chain=list(seen) + [definition_name],
                        )
                    if composition_depth >= MAX_COMPOSITION_DEPTH:
                        _hold(
                            "HOLD_SHAPE_RECIPE_COMPOSITION_TOO_DEEP",
                            f"composed recipes may nest at most {MAX_COMPOSITION_DEPTH} definitions",
                            definition=definition_name,
                        )
                    rotation = _vector(
                        node.get("rot"), active_variables, scope, "use.rot",
                        [0.0, 0.0, 0.0], -1_000_000.0, 1_000_000.0,
                    )
                    if any(value != 0 for value in rotation):
                        _hold(
                            "HOLD_SHAPE_RECIPE_ROTATION_UNSUPPORTED",
                            "the current UC procedural-3D receiver does not preserve composed rotation",
                            rotation=rotation,
                        )
                    definition = definitions[definition_name]
                    child_variables = deepcopy(definition["vars"])
                    overrides = node.get("with", {})
                    if not isinstance(overrides, dict):
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "use.with must be an object")
                    unknown_settings = sorted(set(overrides) - set(child_variables))
                    if unknown_settings:
                        _hold(
                            "HOLD_SHAPE_RECIPE_SETTINGS_NOT_ACCEPTED",
                            "composed shape does not declare every requested setting",
                            definition=definition_name,
                            unknown_settings=unknown_settings,
                        )
                    for setting, expression in overrides.items():
                        child_variables[setting] = _number(
                            expression,
                            active_variables,
                            scope,
                            f"use.with.{setting}",
                            -100_000.0,
                            100_000.0,
                        )
                    composition_uses += 1
                    settings_overrides += len(overrides)
                    next_depth = composition_depth + 1
                    deepest_composition_depth = max(deepest_composition_depth, next_depth)
                    child_parts = expand(
                        definition["parts"],
                        child_variables,
                        definition["material"],
                        definition["paint"],
                        seen + (definition_name,),
                        next_depth,
                        f"recipe.definitions.{definition_name}",
                    )
                    offset = _vector(
                        node.get("pos"), active_variables, scope, "use.pos",
                        [0.0, 0.0, 0.0], -100_000.0, 100_000.0,
                    )
                    scale = _scale_vector(node.get("scale"), active_variables, scope, "use.scale")
                    if "material" in node and "color" in node:
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "use node may declare material or color, not both")
                    material_override = _material(node["material"], "use.material") if "material" in node else None
                    for child in child_parts:
                        child = deepcopy(child)
                        child["size"] = [
                            _literal_number(child["size"][axis] * scale[axis], f"use.size[{axis}]", 0.001, 10_000.0)
                            for axis in range(3)
                        ]
                        child["translation"] = [
                            _literal_number(
                                child["translation"][axis] * scale[axis] + offset[axis],
                                f"use.translation[{axis}]",
                                -100_000.0,
                                100_000.0,
                            )
                            for axis in range(3)
                        ]
                        if material_override is not None:
                            child["material"] = deepcopy(material_override)
                        elif "color" in node:
                            child["material"] = _color_material(
                                node["color"], active_variables, scope, child["material"], "use.color"
                            )
                        expanded.append(child)
                    continue

                node = _closed(
                    raw_node,
                    "part node",
                    required=set(),
                    optional={"shape", "size", "pos", "rot", "color", "segments", "material", "when"},
                )
                if "when" in node and not _truthy(_evaluate(node["when"], active_variables, scope)):
                    continue
                if generated_count >= effective_budget:
                    _hold(
                        "HOLD_SHAPE_RECIPE_OVER_BUDGET",
                        "shape recipe exceeds the receiver's primitive budget",
                        maximum=effective_budget,
                    )
                shape = node.get("shape", "box")
                if not isinstance(shape, str) or shape not in _SHAPES:
                    _hold(
                        "HOLD_SHAPE_RECIPE_UNSUPPORTED_SHAPE",
                        "shape recipe requests a primitive the UC receiver cannot express",
                        shape=shape,
                        supported=sorted(_SHAPES),
                    )
                size = _vector(
                    node.get("size"), active_variables, scope, "part.size",
                    [1.0, 1.0, 1.0], 0.001, 10_000.0,
                )
                translation = _vector(
                    node.get("pos"), active_variables, scope, "part.pos",
                    [0.0, 0.0, 0.0], -100_000.0, 100_000.0,
                )
                rotation = _vector(
                    node.get("rot"), active_variables, scope, "part.rot",
                    [0.0, 0.0, 0.0], -1_000_000.0, 1_000_000.0,
                )
                if any(value != 0 for value in rotation):
                    _hold(
                        "HOLD_SHAPE_RECIPE_ROTATION_UNSUPPORTED",
                        "the current UC procedural-3D receiver does not preserve primitive rotation",
                        rotation=rotation,
                    )
                if "material" in node and "color" in node:
                    _hold("HOLD_SHAPE_RECIPE_INVALID", "part node may declare material or color, not both")
                material = (
                    _material(node["material"], "part.material")
                    if "material" in node
                    else _color_material(
                        node["color"], active_variables, scope, active_material, "part.color"
                    )
                    if "color" in node
                    else deepcopy(active_material)
                )
                primitive: dict[str, Any] = {
                    "type": shape,
                    "size": size,
                    "translation": translation,
                    "material": material,
                }
                if "segments" in node:
                    if shape != "cylinder":
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "part.segments is allowed only for cylinders")
                    segments = _number(
                        node["segments"], active_variables, scope, "part.segments", 3, 64
                    )
                    if not segments.is_integer():
                        _hold("HOLD_SHAPE_RECIPE_INVALID", "part.segments must resolve to an integer")
                    primitive["segments"] = int(segments)
                expanded.append(primitive)
                generated_count += 1

        walk(nodes, {}, 0)
        if active_paint is not None:
            for primitive in expanded:
                x, y, z = primitive["translation"]
                primitive["material"] = _color_material(
                    active_paint["color"],
                    active_paint["vars"],
                    {"x": x, "y": y, "z": z},
                    primitive["material"],
                    f"{label}.paint.color",
                )
                paint_applications += 1
        return expanded

    generated = expand(
        parts,
        variables,
        default_material,
        root_paint,
        (),
        0,
        "recipe",
    )
    if not generated:
        _hold("HOLD_SHAPE_RECIPE_EMPTY", "shape recipe produced no primitives")
    for index, primitive in enumerate(generated, start=1):
        primitive["id"] = f"part-{index:03d}"
    specification = {
        "schema": "axm.procedural-3d/v0.1",
        "name": name.strip(),
        "primitives": generated,
    }
    return {
        "truth_status": "COMPILED_BOUNDED_SHAPE_RECIPE",
        "schema": SCHEMA,
        "recipe_sha256": hashlib.sha256(_canonical(recipe)).hexdigest(),
        "declared_budget": declared_budget,
        "effective_budget": effective_budget,
        "recipe_nodes_visited": nodes_visited,
        "parts_generated": len(generated),
        "definitions_declared": len(definitions),
        "composition_uses": composition_uses,
        "settings_overrides": settings_overrides,
        "deepest_composition_depth": deepest_composition_depth,
        "paint_mode": "primitive-center",
        "paint_applications": paint_applications,
        "source_provenance": deepcopy(SOURCE_PROVENANCE),
        "specification": specification,
    }


def publish_shape_recipe(target: Path, recipe: Any, *, replace: bool = False) -> dict[str, Any]:
    compiled = compile_shape_recipe(recipe)
    result = publish_glb(target, compiled["specification"], replace=replace)
    result["shape_recipe"] = {key: value for key, value in compiled.items() if key != "specification"}
    return result

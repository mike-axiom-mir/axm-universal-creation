"""Renderer-neutral deterministic procedural effects for AXM Universal Creation.

v0.1 implements one bounded capability: an electric-arc path graph. The
canonical result is topology/state, not a bitmap. The same graph may be
realized as SVG now and by game/app/3D adapters later without changing the
source recipe.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import heapq
import html
import json
import math
import random
from pathlib import Path

from .atomic import atomic_write_json, atomic_write_text


RECIPE_SCHEMA = "axm.procedural-effect-recipe/v0.1"
GRAPH_SCHEMA = "axm.procedural-effect-graph/v0.1"
RECEIPT_SCHEMA = "axm.procedural-effect-receipt/v0.1"
KIND = "electric-arc"


def _canonical(value) -> bytes:
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def _digest(value) -> str:
    return hashlib.sha256(_canonical(value)).hexdigest()


def _number(value, label, low, high) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be a finite number")
    value = float(value)
    if not low <= value <= high:
        raise ValueError(f"{label} must be from {low} to {high}")
    return value


def _integer(value, label, low, high) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not low <= value <= high:
        raise ValueError(f"{label} must be an integer from {low} to {high}")
    return value


def _name(value, label) -> str:
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValueError(f"{label} must contain 1..128 visible characters")
    return value.strip()


def _point(value, label) -> tuple[float, float]:
    if not isinstance(value, (list, tuple)) or len(value) != 2:
        raise ValueError(f"{label} must contain exactly two normalized numbers")
    return (
        _number(value[0], f"{label}[0]", 0.0, 1.0),
        _number(value[1], f"{label}[1]", 0.0, 1.0),
    )


def _color(value, label) -> str:
    if not isinstance(value, str) or len(value) != 7 or value[0] != "#":
        raise ValueError(f"{label} must be #RRGGBB")
    try:
        int(value[1:], 16)
    except ValueError as exc:
        raise ValueError(f"{label} must be #RRGGBB") from exc
    return value.lower()


def procedural_effect_catalog() -> dict:
    return {
        "schema": "axm.procedural-effect-catalog/v0.1",
        "truth_status": "EXECUTABLE_BOUNDED_CAPABILITY",
        "effects": {
            KIND: {
                "canonical_output": GRAPH_SCHEMA,
                "realizations": ["svg"],
                "portable_uses": [
                    "website/app SVG",
                    "game/app polyline or particle adapter",
                    "future 3D curve extrusion",
                    "future animation by edge/path phase",
                ],
            }
        },
        "dependencies": [],
        "offline": True,
        "ai_required": False,
        "truth": (
            "The electric-arc capability authors deterministic path topology and an SVG "
            "realization. It does not simulate plasma physics, electrical discharge, "
            "volumetric light, collision, or target-engine performance."
        ),
    }


def _validate(raw: dict) -> dict:
    before = copy.deepcopy(raw)
    required = {"name", "kind", "seed", "canvas", "topology", "guides", "realization"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError(f"request must contain exactly {sorted(required)}")
    if raw["kind"] != KIND:
        raise ValueError(f"kind must be {KIND}")
    canvas = raw["canvas"]
    if not isinstance(canvas, dict) or set(canvas) != {"width", "height"}:
        raise ValueError("canvas must contain exactly width and height")
    topology = raw["topology"]
    top_keys = {"source", "target", "grid", "walkers", "spread", "octaves", "roughness"}
    if not isinstance(topology, dict) or set(topology) != top_keys:
        raise ValueError(f"topology must contain exactly {sorted(top_keys)}")
    guides = raw["guides"]
    if not isinstance(guides, dict) or set(guides) != {"points", "strength", "radius"}:
        raise ValueError("guides must contain exactly points, strength and radius")
    if not isinstance(guides["points"], list) or len(guides["points"]) > 32:
        raise ValueError("guides.points must contain 0..32 points")
    realization = raw["realization"]
    real_keys = {"color", "background", "core_width", "glow_width", "glow_strength"}
    if not isinstance(realization, dict) or set(realization) != real_keys:
        raise ValueError(f"realization must contain exactly {sorted(real_keys)}")

    result = {
        "schema": RECIPE_SCHEMA,
        "name": _name(raw["name"], "name"),
        "kind": KIND,
        "seed": _integer(raw["seed"], "seed", 0, 2_147_483_647),
        "canvas": {
            "width": _integer(canvas["width"], "canvas.width", 64, 4096),
            "height": _integer(canvas["height"], "canvas.height", 64, 4096),
        },
        "topology": {
            "source": list(_point(topology["source"], "topology.source")),
            "target": list(_point(topology["target"], "topology.target")),
            "grid": _integer(topology["grid"], "topology.grid", 16, 192),
            "walkers": _integer(topology["walkers"], "topology.walkers", 1, 256),
            "spread": _number(topology["spread"], "topology.spread", 0.0, 0.35),
            "octaves": _integer(topology["octaves"], "topology.octaves", 1, 8),
            "roughness": _number(topology["roughness"], "topology.roughness", 0.0, 1.0),
        },
        "guides": {
            "points": [list(_point(p, f"guides.points[{i}]")) for i, p in enumerate(guides["points"])],
            "strength": _number(guides["strength"], "guides.strength", 0.0, 0.95),
            "radius": _number(guides["radius"], "guides.radius", 0.01, 1.0),
        },
        "realization": {
            "color": _color(realization["color"], "realization.color"),
            "background": None
            if realization["background"] is None
            else _color(realization["background"], "realization.background"),
            "core_width": _number(realization["core_width"], "realization.core_width", 0.1, 64.0),
            "glow_width": _number(realization["glow_width"], "realization.glow_width", 0.0, 256.0),
            "glow_strength": _number(realization["glow_strength"], "realization.glow_strength", 0.0, 1.0),
        },
    }
    if raw != before:
        raise AssertionError("validation mutated caller request")
    if result["topology"]["source"] == result["topology"]["target"]:
        raise ValueError("topology.source and topology.target must differ")
    return result


def _hash01(seed: int, x: int, y: int, octave: int) -> float:
    payload = f"{seed}:{x}:{y}:{octave}".encode("ascii")
    return int.from_bytes(hashlib.blake2s(payload, digest_size=8).digest(), "big") / (2**64 - 1)


def _field_costs(recipe: dict) -> list[float]:
    n = recipe["topology"]["grid"]
    octaves = recipe["topology"]["octaves"]
    roughness = recipe["topology"]["roughness"]
    guides = recipe["guides"]
    values = [0.0] * (n * n)
    for y in range(n):
        for x in range(n):
            total = 0.0
            weight = 1.0
            weight_sum = 0.0
            for octave in range(octaves):
                frequency = 1 << octave
                sx = (x * frequency) // max(1, n - 1)
                sy = (y * frequency) // max(1, n - 1)
                total += _hash01(recipe["seed"], sx, sy, octave) * weight
                weight_sum += weight
                weight *= 0.35 + 0.55 * roughness
            noise = total / weight_sum
            cost = 0.18 + noise * noise * 5.0
            if guides["points"] and guides["strength"] > 0:
                nx = x / (n - 1)
                ny = y / (n - 1)
                d2 = min((nx - gx) ** 2 + (ny - gy) ** 2 for gx, gy in guides["points"])
                sigma2 = guides["radius"] ** 2
                attraction = math.exp(-d2 / (2.0 * sigma2))
                cost *= max(0.08, 1.0 - guides["strength"] * attraction)
            values[y * n + x] = cost
    return values


_NEIGHBORS = (
    (-1, -1, math.sqrt(2.0)), (0, -1, 1.0), (1, -1, math.sqrt(2.0)),
    (-1, 0, 1.0),                           (1, 0, 1.0),
    (-1, 1, math.sqrt(2.0)),  (0, 1, 1.0),  (1, 1, math.sqrt(2.0)),
)


def _cell(point: list[float], n: int) -> tuple[int, int]:
    return (
        min(n - 1, max(0, int(round(point[0] * (n - 1))))),
        min(n - 1, max(0, int(round(point[1] * (n - 1))))),
    )


def _routing(costs: list[float], n: int, target: tuple[int, int]) -> tuple[list[float], list[int]]:
    count = n * n
    dist = [math.inf] * count
    parent = [-1] * count
    target_index = target[1] * n + target[0]
    dist[target_index] = 0.0
    heap = [(0.0, target_index)]
    while heap:
        current_distance, index = heapq.heappop(heap)
        if current_distance != dist[index]:
            continue
        x, y = index % n, index // n
        for dx, dy, step in _NEIGHBORS:
            xx, yy = x + dx, y + dy
            if not (0 <= xx < n and 0 <= yy < n):
                continue
            nxt = yy * n + xx
            edge = step * (costs[index] + costs[nxt]) * 0.5
            candidate = current_distance + edge
            if candidate < dist[nxt] - 1e-12 or (
                abs(candidate - dist[nxt]) <= 1e-12 and index < parent[nxt]
            ):
                dist[nxt] = candidate
                parent[nxt] = index
                heapq.heappush(heap, (candidate, nxt))
    return dist, parent


def _trace(parent: list[int], n: int, start: tuple[int, int], target: tuple[int, int]) -> list[tuple[int, int]]:
    current = start[1] * n + start[0]
    end = target[1] * n + target[0]
    result = []
    seen = set()
    while True:
        if current in seen or current < 0:
            raise ValueError("routing field did not produce a valid target path")
        seen.add(current)
        result.append((current % n, current // n))
        if current == end:
            return result
        current = parent[current]


def _walker_start(recipe: dict, index: int, n: int, rng: random.Random) -> tuple[int, int]:
    source = recipe["topology"]["source"]
    if index == 0 or recipe["topology"]["spread"] == 0:
        return _cell(source, n)
    angle = rng.random() * math.tau
    radius = recipe["topology"]["spread"] * math.sqrt(rng.random())
    point = (
        min(1.0, max(0.0, source[0] + math.cos(angle) * radius)),
        min(1.0, max(0.0, source[1] + math.sin(angle) * radius)),
    )
    return _cell(point, n)


def _point_from_cell(cell: tuple[int, int], n: int) -> list[float]:
    return [cell[0] / (n - 1), cell[1] / (n - 1)]


def _path_length(points: list[list[float]]) -> float:
    return sum(math.dist(a, b) for a, b in zip(points, points[1:]))


def build_electric_arc(raw: dict) -> dict:
    recipe = _validate(raw)
    n = recipe["topology"]["grid"]
    target_cell = _cell(recipe["topology"]["target"], n)
    costs = _field_costs(recipe)
    distances, parent = _routing(costs, n, target_cell)
    rng = random.Random(recipe["seed"] ^ 0xA58C_91D7)
    paths = []
    edge_counts: dict[tuple[tuple[float, float], tuple[float, float]], int] = {}
    walkers = recipe["topology"]["walkers"]

    for index in range(walkers):
        start_cell = _walker_start(recipe, index, n, rng)
        cells = _trace(parent, n, start_cell, target_cell)
        points = [_point_from_cell(cell, n) for cell in cells]
        if index == 0:
            points[0] = list(recipe["topology"]["source"])
        points[-1] = list(recipe["topology"]["target"])
        clean = [points[0]]
        for point in points[1:]:
            if point != clean[-1]:
                clean.append(point)
        total = _path_length(clean)
        paths.append(
            {
                "id": f"path-{index:03d}",
                "points": clean,
                "length_normalized": total,
                "phase": index / max(1, walkers - 1),
            }
        )
        for a, b in zip(clean, clean[1:]):
            aa, bb = tuple(a), tuple(b)
            key = (aa, bb) if aa <= bb else (bb, aa)
            edge_counts[key] = edge_counts.get(key, 0) + 1

    edges = []
    maximum = max(edge_counts.values(), default=1)
    for index, ((a, b), count) in enumerate(sorted(edge_counts.items())):
        edges.append(
            {
                "id": f"edge-{index:05d}",
                "a": list(a),
                "b": list(b),
                "traversals": count,
                "intensity": count / maximum,
            }
        )

    topology_source = {
        "name": recipe["name"],
        "kind": recipe["kind"],
        "seed": recipe["seed"],
        "topology": recipe["topology"],
        "guides": recipe["guides"],
    }
    source_cell = _cell(recipe["topology"]["source"], n)
    graph = {
        "schema": GRAPH_SCHEMA,
        "name": recipe["name"],
        "kind": KIND,
        "topology_sha256": _digest(topology_source),
        "source": list(recipe["topology"]["source"]),
        "target": list(recipe["topology"]["target"]),
        "paths": paths,
        "edges": edges,
        "metrics": {
            "grid": n,
            "walkers": walkers,
            "unique_edges": len(edges),
            "maximum_edge_traversals": maximum,
            "source_route_cost": distances[source_cell[1] * n + source_cell[0]],
        },
        "truth": (
            "Deterministic cost-field minimal paths with reusable topology. "
            "This is an authored visual/path effect, not a plasma or electrical simulation."
        ),
    }
    return {
        "recipe": recipe,
        "graph": graph,
        "recipe_sha256": _digest(recipe),
        "graph_sha256": _digest(graph),
    }


def _svg(result: dict) -> str:
    recipe, graph = result["recipe"], result["graph"]
    width, height = recipe["canvas"]["width"], recipe["canvas"]["height"]
    color = recipe["realization"]["color"]
    background = recipe["realization"]["background"]
    core = recipe["realization"]["core_width"]
    glow = recipe["realization"]["glow_width"]
    strength = recipe["realization"]["glow_strength"]
    esc_name = html.escape(recipe["name"])
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-label="{esc_name}">',
        "<defs>",
        f'<filter id="axm-glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="{max(0.1, glow / 5):.4f}" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        "</defs>",
    ]
    if background is not None:
        lines.append(f'<rect width="100%" height="100%" fill="{background}"/>')
    lines.append(f'<g fill="none" stroke-linecap="round" stroke-linejoin="round" stroke="{color}">')
    maximum = graph["metrics"]["maximum_edge_traversals"]
    for edge in graph["edges"]:
        ax, ay = edge["a"][0] * width, edge["a"][1] * height
        bx, by = edge["b"][0] * width, edge["b"][1] * height
        weight = edge["traversals"] / maximum
        if glow > 0 and strength > 0:
            alpha = min(0.9, (0.08 + 0.42 * weight) * strength)
            glow_width = core + glow * (0.35 + 0.65 * weight)
            lines.append(
                f'<path d="M {ax:.3f} {ay:.3f} L {bx:.3f} {by:.3f}" stroke-width="{glow_width:.3f}" opacity="{alpha:.4f}" filter="url(#axm-glow)"/>'
            )
        alpha = 0.35 + 0.65 * weight
        line_width = core * (0.55 + 0.9 * weight)
        lines.append(
            f'<path d="M {ax:.3f} {ay:.3f} L {bx:.3f} {by:.3f}" stroke-width="{line_width:.3f}" opacity="{alpha:.4f}"/>'
        )
    lines.append("</g></svg>")
    return "\n".join(lines) + "\n"


def _preview_html(recipe: dict) -> str:
    name = html.escape(recipe["name"])
    return (
        "<!doctype html><meta charset=\"utf-8\"><meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
        f"<title>{name}</title>"
        "<style>html,body{margin:0;min-height:100%;background:#05070c}body{display:grid;place-items:center;overflow:hidden}"
        "img{max-width:100vw;max-height:100vh;filter:drop-shadow(0 0 16px currentColor);animation:axmArc 3.7s infinite}"
        "@keyframes axmArc{0%,7%,11%,100%{opacity:1}8%{opacity:.68}9%{opacity:.96}10%{opacity:.78}}</style>"
        f'<img src="effect.svg" alt="{name}">'
    )


def publish_procedural_effect(path, raw: dict) -> dict:
    target = Path(path)
    if target.exists():
        raise FileExistsError(f"refusing to overwrite existing path: {target}")
    result = build_electric_arc(raw)
    target.mkdir(parents=True)
    atomic_write_json(target / "recipe.json", result["recipe"])
    atomic_write_json(target / "effect-graph.json", result["graph"])
    atomic_write_text(target / "effect.svg", _svg(result))
    atomic_write_text(target / "preview.html", _preview_html(result["recipe"]))
    receipt = {
        "schema": RECEIPT_SCHEMA,
        "recipe_sha256": result["recipe_sha256"],
        "graph_sha256": result["graph_sha256"],
        "artifacts": ["recipe.json", "effect-graph.json", "effect.svg", "preview.html"],
        "canonical_authority": "effect-graph.json plus recipe.json; SVG/HTML are replaceable realizations",
        "offline": True,
        "ai_required": False,
        "truth": (
            "Graph identity proves deterministic topology for this implementation and recipe. "
            "SVG/HTML generation proves file creation, not target-engine visual quality or electrical realism."
        ),
    }
    atomic_write_json(target / "receipt.json", receipt)
    return {"result": result, "receipt": receipt}


def operate_procedural_effect(root, inputs: dict) -> dict:
    if not isinstance(inputs, dict) or set(inputs) != {"request", "path"}:
        raise ValueError("inputs must contain exactly request and path")
    base = Path(root).resolve()
    path = Path(inputs["path"])
    if path.is_absolute():
        target = path.resolve()
    else:
        target = (base / path).resolve()
    try:
        target.relative_to(base)
    except ValueError as exc:
        raise ValueError("path must stay inside root") from exc
    return publish_procedural_effect(target, inputs["request"])


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="axm-effects", description="AXM portable procedural effect graph")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("catalog")
    build = sub.add_parser("electric-arc")
    build.add_argument("request")
    build.add_argument("output")
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "catalog":
        print(json.dumps(procedural_effect_catalog(), indent=2, sort_keys=True))
        return 0
    request = json.loads(Path(args.request).read_text(encoding="utf-8"))
    published = publish_procedural_effect(args.output, request)
    print(json.dumps(published["receipt"], indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

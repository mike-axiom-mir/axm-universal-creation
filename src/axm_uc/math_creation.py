"""Bind deterministic math-family results into real Universal Creation requests."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any

from axm_stickers import resolve_family, value_map

SCHEMA = "axm.math-create/v1"
BOUND_SCHEMA = "axm.math-bound-request/v1"
MAX_BINDINGS = 256
MAX_REQUEST_BYTES = 4 * 1024 * 1024


def _path_target(root: Any, path: Any) -> tuple[Any, Any, Any]:
    if not isinstance(path, list) or not 1 <= len(path) <= 16:
        raise ValueError("binding path must have 1..16 segments")
    current = root
    for part in path:
        if isinstance(current, dict) and isinstance(part, str) and part in current:
            parent, current = current, current[part]
        elif isinstance(current, list) and type(part) is int and 0 <= part < len(current):
            parent, current = current, current[part]
        else:
            raise ValueError("binding path does not exist in template")
    return parent, path[-1], current


def bind_request(spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("math-create request must be an object")
    required = {"schema", "family", "template", "bindings"}
    optional = {"variant", "overrides"}
    if not required <= set(spec) or set(spec) - required - optional or spec["schema"] != SCHEMA:
        raise ValueError("unsupported math-create request")

    template = spec["template"]
    bindings = spec["bindings"]
    if not isinstance(template, dict):
        raise ValueError("template must be a Universal Creation request object")
    if not isinstance(bindings, dict) or not 1 <= len(bindings) <= MAX_BINDINGS:
        raise ValueError("bindings must contain 1..256 value paths")

    result = resolve_family(
        spec["family"],
        variant=spec.get("variant"),
        overrides=spec.get("overrides"),
    )
    values = value_map(result)
    request = copy.deepcopy(template)
    seen_paths = set()

    for source, path in bindings.items():
        if source not in values:
            raise ValueError(f"unknown math value binding: {source}")
        if not isinstance(path, list):
            raise ValueError("binding path must be an array")
        key = json.dumps(path, sort_keys=False, separators=(",", ":"))
        if key in seen_paths:
            raise ValueError("multiple values cannot target one binding path")
        seen_paths.add(key)
        parent, target, original = _path_target(request, path)
        if type(original) not in (int, float):
            raise ValueError("math bindings may only replace existing numeric template values")
        parent[target] = values[source]

    encoded = json.dumps(request, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    if len(encoded) > MAX_REQUEST_BYTES:
        raise ValueError("bound creation request exceeds 4 MiB")

    return {
        "schema": BOUND_SCHEMA,
        "math": result,
        "request": request,
        "bindings": copy.deepcopy(bindings),
        "truth_boundary": (
            "Math bindings replace only declared numeric template targets. The downstream creation "
            "machine remains responsible for its own capability checks and output evidence."
        ),
    }


def execute(machine: Any, spec: Any) -> dict[str, Any]:
    bound = bind_request(spec)
    creation = machine.create(bound["request"])
    return {
        "type": "MATH_CREATION_RESULT",
        "math": bound["math"],
        "bindings": bound["bindings"],
        "bound_request": bound["request"],
        "creation": creation,
        "truth_boundary": bound["truth_boundary"],
    }


def _read_request(path: str) -> dict[str, Any]:
    with Path(path).open("rb") as source:
        data = source.read(MAX_REQUEST_BYTES + 1)
    if len(data) > MAX_REQUEST_BYTES:
        raise ValueError("math-create request exceeds 4 MiB")
    return json.loads(data)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="axm-math-create",
        description="Resolve a declarative math family and bind it into a Universal Creation request",
    )
    parser.add_argument("request", help="axm.math-create/v1 JSON request")
    parser.add_argument("--root", help="Universal Creation machine root; normally auto-detected")
    args = parser.parse_args(argv)

    from .machine import UniversalCreationMachine
    from .paths import find_machine_root

    try:
        spec = _read_request(args.request)
        root = find_machine_root(args.root) if args.root else find_machine_root()
        result = execute(UniversalCreationMachine(root), spec)
    except (ValueError, OSError, json.JSONDecodeError) as exc:
        parser.error(str(exc))

    print(json.dumps(result, indent=2, ensure_ascii=False, sort_keys=True))
    return 0 if result["creation"].get("type") == "CREATION_RESULT" else 1


if __name__ == "__main__":
    raise SystemExit(main())

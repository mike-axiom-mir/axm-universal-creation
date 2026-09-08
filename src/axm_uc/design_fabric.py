from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from .project import ProjectError, build_project


DESIGN_OBSERVATION_SCHEMA = "axm.design-observation/v0.1"
DESIGN_GENOME_SCHEMA = "axm.design-genome/v0.1"
DESIGN_PLAN_SCHEMA = "axm.design-plan/v0.1"
DESIGN_JUDGMENT_SCHEMA = "axm.design-judgment/v0.1"
MAX_SOURCE_FILES = 128
MAX_SOURCE_BYTES = 2_000_000
MAX_ITEMS = 128
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
HEX_RE = re.compile(r"#[0-9A-Fa-f]{6}(?:[0-9A-Fa-f]{2})?")
LENGTH_RE = re.compile(r"(?<![\w.-])-?(?:\d+(?:\.\d+)?|\.\d+)(?:px|rem|em|vh|vw|vmin|vmax|%)\b", re.I)
DURATION_RE = re.compile(r"(?<![\w.-])(?:\d+(?:\.\d+)?|\.\d+)(?:ms|s)\b", re.I)
CLASS_RE = re.compile(r"\.([A-Za-z_][A-Za-z0-9_-]*)")
STATE_RE = re.compile(r":(hover|focus-visible|focus|active|disabled|checked|selected)\b", re.I)
CUSTOM_RE = re.compile(r"(--[A-Za-z0-9_-]+)\s*:\s*([^;{}]+);")
DECL_RE = re.compile(r"([A-Za-z-]+)\s*:\s*([^;{}]+);")
RULE_RE = re.compile(r"([^{}]+)\{([^{}]*)\}", re.M)
MEDIA_RE = re.compile(r"\((?:min|max)-width\s*:\s*([^)]+)\)", re.I)
FONT_RE = re.compile(r"font-family\s*:\s*([^;{}]+);", re.I)
TAG_RE = re.compile(r"<\s*([A-Za-z][A-Za-z0-9:-]*)\b", re.I)
ARIA_RE = re.compile(r"\baria-[A-Za-z-]+\s*=", re.I)
SOURCE_EXTENSIONS = {".css", ".html", ".htm", ".svg", ".js", ".jsx", ".ts", ".tsx", ".vue", ".svelte"}
IGNORED_DIRS = {".git", "node_modules", "dist", "build", ".next", ".cache", "vendor"}
INTERACTIVE_TAGS = {"a", "button", "input", "select", "textarea", "summary"}


class DesignFabricError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignFabricError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignFabricError(f"{label} exceeds its {maximum}-character bound")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 128)
    if ID_RE.fullmatch(result) is None:
        raise DesignFabricError(f"{label} is invalid", {"value": result})
    return result


def _list(value: Any, label: str, *, identifiers: bool = False, maximum: int = MAX_ITEMS) -> list[str]:
    if not isinstance(value, list) or len(value) > maximum:
        raise DesignFabricError(f"{label} must be a list with at most {maximum} entries")
    result: list[str] = []
    for index, item in enumerate(value):
        normalized = _identifier(item, f"{label}[{index}]") if identifiers else _text(item, f"{label}[{index}]", 500)
        if normalized in result:
            raise DesignFabricError(f"{label} entries must be unique", {"duplicate": normalized})
        result.append(normalized)
    return result


def _number(value: Any, label: str, minimum: float, maximum: float) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(float(value)):
        raise DesignFabricError(f"{label} must be a finite number")
    result = float(value)
    if not minimum <= result <= maximum:
        raise DesignFabricError(f"{label} must be between {minimum} and {maximum}")
    return result


def _resolve_path(root: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    if not path.is_absolute():
        path = Path(root).resolve() / path
    return path.resolve()


def _is_machine_body_path(root: Path, target: Path) -> bool:
    root = Path(root).resolve()
    target = Path(target).resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        try:
            root.relative_to(target)
        except ValueError:
            return False
        return True
    if not relative.parts:
        return True
    return relative.parts[0] not in {"creations", ".axm-build"}


def _source_files(target: Path) -> list[Path]:
    if not target.exists():
        raise DesignFabricError("design reference path does not exist", {"path": str(target)})
    if target.is_file():
        if target.suffix.casefold() not in SOURCE_EXTENSIONS:
            raise DesignFabricError("design reference file type is unsupported", {"path": str(target)})
        return [target]
    files = []
    for path in sorted(target.rglob("*")):
        if not path.is_file() or path.suffix.casefold() not in SOURCE_EXTENSIONS:
            continue
        relative = path.relative_to(target)
        if any(part in IGNORED_DIRS for part in relative.parts[:-1]):
            continue
        files.append(path)
        if len(files) > MAX_SOURCE_FILES:
            raise DesignFabricError("design reference exceeds the source-file bound", {"maximum": MAX_SOURCE_FILES})
    if not files:
        raise DesignFabricError("design reference contains no supported source files")
    return files


def _rows(counter: Counter[str], limit: int = 64) -> list[dict[str, Any]]:
    return [{"value": value, "count": count} for value, count in sorted(counter.items(), key=lambda item: (-item[1], item[0]))[:limit]]


def _state(value: str) -> str:
    return "focus" if value.casefold() == "focus-visible" else value.casefold()


def observe_project_style(target: Path) -> dict[str, Any]:
    target = Path(target).resolve()
    files = _source_files(target)
    colors: Counter[str] = Counter()
    lengths: Counter[str] = Counter()
    radii: Counter[str] = Counter()
    durations: Counter[str] = Counter()
    fonts: Counter[str] = Counter()
    materials: Counter[str] = Counter()
    breakpoints: Counter[str] = Counter()
    custom: Counter[tuple[str, str]] = Counter()
    selector_counts: Counter[str] = Counter()
    selector_states: dict[str, set[str]] = defaultdict(set)
    tags: Counter[str] = Counter()
    aria_count = 0
    evidence = []

    for path in files:
        size = path.stat().st_size
        if size > MAX_SOURCE_BYTES:
            raise DesignFabricError("design reference source exceeds the byte bound", {"path": str(path), "bytes": size})
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError as exc:
            raise DesignFabricError("design reference source must be UTF-8 text", {"path": str(path)}) from exc
        relative = path.name if target.is_file() else str(path.relative_to(target)).replace("\\", "/")
        evidence.append({"path": relative, "bytes": size, "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest()})
        colors.update(match.group(0).upper() for match in HEX_RE.finditer(text))
        lengths.update(match.group(0).casefold() for match in LENGTH_RE.finditer(text))
        durations.update(match.group(0).casefold() for match in DURATION_RE.finditer(text))
        for name, value in CUSTOM_RE.findall(text):
            custom[(name.strip(), value.strip())] += 1
        fonts.update(value.strip() for value in FONT_RE.findall(text))
        breakpoints.update(value.strip().casefold() for value in MEDIA_RE.findall(text))
        for selector_text, declarations in RULE_RE.findall(text):
            if selector_text.lstrip().startswith("@"):
                continue
            for selector in selector_text.split(","):
                for class_name in CLASS_RE.findall(selector):
                    selector_counts[class_name] += 1
                    selector_states[class_name].update(_state(value) for value in STATE_RE.findall(selector))
            for prop, value in DECL_RE.findall(declarations):
                prop = prop.casefold()
                if prop == "border-radius":
                    radii.update(match.group(0).casefold() for match in LENGTH_RE.finditer(value))
                lowered = value.casefold()
                if prop in {"box-shadow", "text-shadow", "backdrop-filter", "filter", "background", "background-image"} and any(signal in lowered for signal in ("shadow", "blur", "gradient", "drop-shadow")):
                    materials[f"{prop}: {value.strip()}"] += 1
        tags.update(tag.casefold() for tag in TAG_RE.findall(text))
        aria_count += len(ARIA_RE.findall(text))

    components = []
    for name, count in sorted(selector_counts.items(), key=lambda item: (-item[1], item[0]))[:64]:
        states = sorted(selector_states[name])
        components.append({
            "selector": f".{name}",
            "occurrences": count,
            "states_observed": states,
            "interactive_signal": bool(states),
            "truth_status": "SELECTOR_SIGNAL_ONLY_NOT_SEMANTIC_COMPONENT_PROOF",
        })
    observation = {
        "schema": DESIGN_OBSERVATION_SCHEMA,
        "truth_status": "OBSERVED_LOCAL_SOURCE_STYLE_SIGNALS",
        "source": {"path": str(target), "file_count": len(files), "files": evidence},
        "signals": {
            "colors": _rows(colors),
            "lengths": _rows(lengths),
            "radii": _rows(radii),
            "durations": _rows(durations),
            "font_families": _rows(fonts),
            "material_signals": _rows(materials),
            "breakpoints": _rows(breakpoints),
            "custom_properties": [{"name": name, "value": value, "count": count} for (name, value), count in sorted(custom.items(), key=lambda item: (-item[1], item[0]))[:64]],
            "component_selector_signals": components,
            "html_tags": _rows(tags),
            "interactive_html_tag_count": sum(tags[tag] for tag in INTERACTIVE_TAGS),
            "aria_attribute_count": aria_count,
        },
        "limitations": [
            "source observation is lexical and structural, not visual perception",
            "selector names are not proof of component semantics",
            "source observation does not prove accessibility, responsive quality, interaction quality, or aesthetic quality",
            "no screenshot, browser rendering, external URL, Figma document, or proprietary source is fetched by this operation",
        ],
    }
    observation["observation_digest"] = _digest(observation)
    return observation


def _token_rows(raw: Any, label: str, *, color: bool = False, font: bool = False) -> list[dict[str, str]]:
    if not isinstance(raw, list) or len(raw) > MAX_ITEMS:
        raise DesignFabricError(f"{label} must be a bounded list")
    rows = []
    seen = set()
    for index, item in enumerate(raw):
        if not isinstance(item, dict) or set(item) - {"id", "value", "font_family", "usage"}:
            raise DesignFabricError(f"{label}[{index}] has unsupported fields")
        token_id = _identifier(item.get("id"), f"{label}[{index}].id")
        if token_id in seen:
            raise DesignFabricError(f"{label} ids must be unique", {"duplicate": token_id})
        seen.add(token_id)
        key = "font_family" if font else "value"
        value = _text(item.get(key), f"{label}[{index}].{key}", 500)
        if color:
            value = value.upper()
            if HEX_RE.fullmatch(value) is None:
                raise DesignFabricError(f"{label}[{index}].value must be hexadecimal color")
        row = {"id": token_id, key: value}
        if "usage" in item:
            row["usage"] = _text(item["usage"], f"{label}[{index}].usage", 500)
        rows.append(row)
    return rows


def validate_design_genome(raw: Any) -> dict[str, Any]:
    required = {"schema", "id", "version", "purpose", "tokens", "layout", "components", "motion", "materials", "quality_gates", "provenance"}
    if not isinstance(raw, dict) or required - set(raw) or set(raw) - (required | {"genome_digest"}):
        raise DesignFabricError("design genome has missing or unsupported top-level fields")
    if raw["schema"] != DESIGN_GENOME_SCHEMA:
        raise DesignFabricError("design genome schema is unsupported")
    tokens = raw["tokens"]
    if not isinstance(tokens, dict) or set(tokens) != {"colors", "spacing", "radii", "typography", "custom"}:
        raise DesignFabricError("design genome.tokens must contain the closed token groups")
    normalized_tokens = {
        "colors": _token_rows(tokens["colors"], "tokens.colors", color=True),
        "spacing": _token_rows(tokens["spacing"], "tokens.spacing"),
        "radii": _token_rows(tokens["radii"], "tokens.radii"),
        "typography": _token_rows(tokens["typography"], "tokens.typography", font=True),
        "custom": _token_rows(tokens["custom"], "tokens.custom"),
    }
    token_ids = [row["id"] for group in normalized_tokens.values() for row in group]
    if len(token_ids) != len(set(token_ids)):
        raise DesignFabricError("design token ids must be unique across token groups")

    layout = raw["layout"]
    if not isinstance(layout, dict) or set(layout) != {"breakpoints", "principles"} or not isinstance(layout["breakpoints"], list) or len(layout["breakpoints"]) > 32:
        raise DesignFabricError("design genome.layout is invalid")
    breakpoints = []
    seen_bp = set()
    for index, item in enumerate(layout["breakpoints"]):
        if not isinstance(item, dict) or set(item) - {"id", "query", "width_px"} or not {"id", "query"}.issubset(item):
            raise DesignFabricError(f"layout.breakpoints[{index}] is invalid")
        bp_id = _identifier(item["id"], f"layout.breakpoints[{index}].id")
        if bp_id in seen_bp:
            raise DesignFabricError("breakpoint ids must be unique")
        seen_bp.add(bp_id)
        row: dict[str, Any] = {"id": bp_id, "query": _text(item["query"], f"layout.breakpoints[{index}].query", 200)}
        if "width_px" in item:
            row["width_px"] = _number(item["width_px"], f"layout.breakpoints[{index}].width_px", 0, 1_000_000)
        breakpoints.append(row)

    components_raw = raw["components"]
    if not isinstance(components_raw, list) or len(components_raw) > MAX_ITEMS:
        raise DesignFabricError("design genome.components must be a bounded list")
    components = []
    seen_components = set()
    component_fields = {"id", "description", "roles", "tags", "interactive", "states", "source_status"}
    for index, item in enumerate(components_raw):
        if not isinstance(item, dict) or set(item) != component_fields:
            raise DesignFabricError(f"components[{index}] must use the closed component fields")
        component_id = _identifier(item["id"], f"components[{index}].id")
        if component_id in seen_components:
            raise DesignFabricError("component ids must be unique")
        seen_components.add(component_id)
        if not isinstance(item["interactive"], bool):
            raise DesignFabricError(f"components[{index}].interactive must be boolean")
        states = list(dict.fromkeys(_state(value) for value in _list(item["states"], f"components[{index}].states")))
        components.append({
            "id": component_id,
            "description": _text(item["description"], f"components[{index}].description", 500),
            "roles": _list(item["roles"], f"components[{index}].roles", identifiers=True),
            "tags": _list(item["tags"], f"components[{index}].tags", identifiers=True),
            "interactive": item["interactive"],
            "states": states,
            "source_status": _text(item["source_status"], f"components[{index}].source_status", 160),
        })

    motion = raw["motion"]
    if not isinstance(motion, dict) or set(motion) != {"durations", "easings", "reduced_motion_strategy"}:
        raise DesignFabricError("design genome.motion is invalid")
    strategy = _text(motion["reduced_motion_strategy"], "motion.reduced_motion_strategy", 120).casefold()
    if strategy not in {"disable-nonessential", "shorten", "replace", "none", "unknown"}:
        raise DesignFabricError("reduced motion strategy is unsupported")
    normalized_motion = {
        "durations": _token_rows(motion["durations"], "motion.durations"),
        "easings": _token_rows(motion["easings"], "motion.easings"),
        "reduced_motion_strategy": strategy,
    }
    materials = raw["materials"]
    if not isinstance(materials, dict) or set(materials) != {"signals", "principles"}:
        raise DesignFabricError("design genome.materials is invalid")
    gates = raw["quality_gates"]
    gate_fields = {"minimum_text_contrast", "focus_visible_required", "reduced_motion_required", "responsive_required", "policy_origin"}
    if not isinstance(gates, dict) or set(gates) != gate_fields:
        raise DesignFabricError("design genome.quality_gates is invalid")
    for key in ("focus_visible_required", "reduced_motion_required", "responsive_required"):
        if not isinstance(gates[key], bool):
            raise DesignFabricError(f"quality_gates.{key} must be boolean")
    normalized = {
        "schema": DESIGN_GENOME_SCHEMA,
        "id": _identifier(raw["id"], "design genome.id"),
        "version": _text(raw["version"], "design genome.version", 64),
        "purpose": _text(raw["purpose"], "design genome.purpose"),
        "tokens": normalized_tokens,
        "layout": {"breakpoints": breakpoints, "principles": _list(layout["principles"], "layout.principles")},
        "components": components,
        "motion": normalized_motion,
        "materials": {"signals": _list(materials["signals"], "materials.signals"), "principles": _list(materials["principles"], "materials.principles")},
        "quality_gates": {
            "minimum_text_contrast": _number(gates["minimum_text_contrast"], "quality_gates.minimum_text_contrast", 1, 21),
            "focus_visible_required": gates["focus_visible_required"],
            "reduced_motion_required": gates["reduced_motion_required"],
            "responsive_required": gates["responsive_required"],
            "policy_origin": _text(gates["policy_origin"], "quality_gates.policy_origin", 200),
        },
        "provenance": copy.deepcopy(raw["provenance"]),
    }
    try:
        _canonical(normalized["provenance"])
    except (TypeError, ValueError) as exc:
        raise DesignFabricError("design genome.provenance must be deterministic JSON") from exc
    normalized["genome_digest"] = _digest(normalized)
    return normalized


def _values(rows: Any, limit: int) -> list[str]:
    return [row["value"] for row in rows[:limit] if isinstance(row, dict) and isinstance(row.get("value"), str)] if isinstance(rows, list) else []


def _px(value: str) -> float | None:
    match = re.fullmatch(r"([+-]?(?:\d+(?:\.\d+)?|\.\d+))px", value.strip(), re.I)
    return float(match.group(1)) if match else None


def derive_design_genome(observation: Any, genome_id: Any, version: Any, purpose: Any) -> dict[str, Any]:
    if not isinstance(observation, dict) or observation.get("schema") != DESIGN_OBSERVATION_SCHEMA or not isinstance(observation.get("signals"), dict):
        raise DesignFabricError("derive-genome requires an axm.design-observation/v0.1 observation")
    signals = observation["signals"]
    colors = [{"id": f"observed-color-{i:02d}", "value": value, "usage": "observed source color; semantic role not inferred"} for i, value in enumerate(_values(signals.get("colors"), 24), 1) if HEX_RE.fullmatch(value)]
    spacing = [{"id": f"observed-space-{i:02d}", "value": value, "usage": "frequent observed length; spacing semantics not inferred"} for i, value in enumerate(_values(signals.get("lengths"), 16), 1)]
    radii = [{"id": f"observed-radius-{i:02d}", "value": value, "usage": "observed border radius"} for i, value in enumerate(_values(signals.get("radii"), 16), 1)]
    typography = [{"id": f"observed-font-{i:02d}", "font_family": value, "usage": "observed font-family declaration"} for i, value in enumerate(_values(signals.get("font_families"), 12), 1)]
    custom = []
    for i, row in enumerate(signals.get("custom_properties", [])[:32], 1):
        if isinstance(row, dict) and isinstance(row.get("name"), str) and isinstance(row.get("value"), str):
            custom.append({"id": f"observed-custom-{i:02d}", "value": f"{row['name']}={row['value']}", "usage": "observed CSS custom property; semantic role not inferred"})
    breakpoints = []
    for i, value in enumerate(_values(signals.get("breakpoints"), 16), 1):
        row: dict[str, Any] = {"id": f"observed-breakpoint-{i:02d}", "query": value}
        width = _px(value)
        if width is not None:
            row["width_px"] = width
        breakpoints.append(row)
    components = []
    for row in signals.get("component_selector_signals", [])[:64]:
        if not isinstance(row, dict) or not isinstance(row.get("selector"), str):
            continue
        name = re.sub(r"[^A-Za-z0-9_.:-]", "-", row["selector"].lstrip("."))[:128]
        if not name or not name[0].isalpha():
            continue
        components.append({
            "id": name,
            "description": f"Observed CSS selector {row['selector']}; semantics remain unproven.",
            "roles": [],
            "tags": ["observed-selector"],
            "interactive": bool(row.get("interactive_signal")),
            "states": list(row.get("states_observed", [])) if isinstance(row.get("states_observed"), list) else [],
            "source_status": "selector-signal-only-not-semantic-proof",
        })
    durations = [{"id": f"observed-duration-{i:02d}", "value": value, "usage": "observed motion duration"} for i, value in enumerate(_values(signals.get("durations"), 16), 1)]
    genome = validate_design_genome({
        "schema": DESIGN_GENOME_SCHEMA,
        "id": _identifier(genome_id, "genome_id"),
        "version": _text(version, "version", 64),
        "purpose": _text(purpose, "purpose"),
        "tokens": {"colors": colors, "spacing": spacing, "radii": radii, "typography": typography, "custom": custom},
        "layout": {"breakpoints": breakpoints, "principles": ["preserve observed token rhythm without copying source page composition"]},
        "components": components,
        "motion": {"durations": durations, "easings": [], "reduced_motion_strategy": "unknown"},
        "materials": {"signals": _values(signals.get("material_signals"), 24), "principles": ["retain surface signals as ingredients, not renderer proof"]},
        "quality_gates": {"minimum_text_contrast": 4.5, "focus_visible_required": True, "reduced_motion_required": True, "responsive_required": True, "policy_origin": "AXM_DESIGN_FABRIC_DEFAULT_NOT_REFERENCE_DERIVED"},
        "provenance": {
            "kind": "derived-local-source-observation",
            "observation_digest": observation.get("observation_digest"),
            "source_file_count": observation.get("source", {}).get("file_count") if isinstance(observation.get("source"), dict) else None,
            "derivation_method": "deterministic lexical and structural style-signal normalization",
            "source_composition_copied": False,
            "semantic_roles_inferred": False,
            "visual_quality_observed": False,
        },
    })
    return {
        "truth_status": "DETERMINISTIC_DESIGN_GENOME_DERIVED_FROM_OBSERVED_SOURCE_SIGNALS",
        "genome": genome,
        "coverage": {
            "colors": len(genome["tokens"]["colors"]),
            "spacing": len(genome["tokens"]["spacing"]),
            "radii": len(genome["tokens"]["radii"]),
            "typography": len(genome["tokens"]["typography"]),
            "breakpoints": len(genome["layout"]["breakpoints"]),
            "component_selector_signals": len(genome["components"]),
            "motion_durations": len(genome["motion"]["durations"]),
            "material_signals": len(genome["materials"]["signals"]),
        },
        "gaps": [
            "semantic component roles require explicit human/model/source evidence",
            "screenshot/rendered visual quality is not observed by this deterministic source lens",
            "reduced-motion strategy is not inferred from mere source-token presence",
        ],
    }


def _luminance(color: str) -> float:
    raw = color[1:7]
    channels = [int(raw[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4 for value in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def compose_design_plan(genome_raw: Any, request_raw: Any) -> dict[str, Any]:
    genome = validate_design_genome(genome_raw)
    required = {"goal", "required_roles", "components", "viewports", "contrast_pairs"}
    if not isinstance(request_raw, dict) or set(request_raw) != required:
        raise DesignFabricError("design request must use goal, required_roles, components, viewports, and contrast_pairs")
    goal = _text(request_raw["goal"], "design request.goal")
    roles = _list(request_raw["required_roles"], "design request.required_roles", identifiers=True)
    explicit = _list(request_raw["components"], "design request.components", identifiers=True)
    viewports = _list(request_raw["viewports"], "design request.viewports", identifiers=True)
    if not viewports:
        raise DesignFabricError("design request.viewports must not be empty")
    by_id = {row["id"]: row for row in genome["components"]}
    selected: list[str] = []
    missing_components = []
    for component_id in explicit:
        if component_id not in by_id:
            missing_components.append(component_id)
        elif component_id not in selected:
            selected.append(component_id)
    role_coverage = {}
    for role in roles:
        matches = [row["id"] for row in genome["components"] if role in row["roles"]]
        role_coverage[role] = matches
        for component_id in matches:
            if component_id not in selected:
                selected.append(component_id)
    colors = {row["id"]: row["value"] for row in genome["tokens"]["colors"]}
    raw_pairs = request_raw["contrast_pairs"]
    if not isinstance(raw_pairs, list) or len(raw_pairs) > 64:
        raise DesignFabricError("design request.contrast_pairs must be a bounded list")
    pairs = []
    for index, pair in enumerate(raw_pairs):
        if not isinstance(pair, dict) or set(pair) - {"foreground", "background", "minimum"} or not {"foreground", "background"}.issubset(pair):
            raise DesignFabricError(f"contrast_pairs[{index}] is invalid")
        foreground = _identifier(pair["foreground"], f"contrast_pairs[{index}].foreground")
        background = _identifier(pair["background"], f"contrast_pairs[{index}].background")
        if foreground not in colors or background not in colors:
            raise DesignFabricError("contrast pair references unknown color token", {"foreground": foreground, "background": background})
        if len(colors[foreground]) != 7 or len(colors[background]) != 7:
            raise DesignFabricError("contrast calculation requires opaque #RRGGBB tokens")
        minimum = _number(pair.get("minimum", genome["quality_gates"]["minimum_text_contrast"]), f"contrast_pairs[{index}].minimum", 1, 21)
        ratio = _contrast(colors[foreground], colors[background])
        pairs.append({"foreground": foreground, "background": background, "ratio": round(ratio, 3), "minimum": minimum, "passed": ratio >= minimum})
    plan = {
        "schema": DESIGN_PLAN_SCHEMA,
        "truth_status": "DETERMINISTIC_DESIGN_GRAMMAR_COMPOSITION_PLAN",
        "goal": goal,
        "genome": {"id": genome["id"], "version": genome["version"], "digest": genome["genome_digest"]},
        "selected_components": [copy.deepcopy(by_id[item]) for item in selected],
        "role_coverage": role_coverage,
        "missing_roles": sorted(role for role, matches in role_coverage.items() if not matches),
        "missing_components": missing_components,
        "viewports": viewports,
        "layout": copy.deepcopy(genome["layout"]),
        "token_bindings": copy.deepcopy(genome["tokens"]),
        "motion": copy.deepcopy(genome["motion"]),
        "materials": copy.deepcopy(genome["materials"]),
        "contrast_pairs": pairs,
        "quality_gates": copy.deepcopy(genome["quality_gates"]),
        "composition_rule": "reuse grammar and component semantics; do not copy a reference page composition by default",
        "limitations": ["this plan does not render a browser or inspect a screenshot", "component selection is exact role/id matching", "structural PASS is not aesthetic proof"],
    }
    plan["plan_digest"] = _digest(plan)
    return plan


def judge_design_plan(plan_raw: Any) -> dict[str, Any]:
    if not isinstance(plan_raw, dict) or plan_raw.get("schema") != DESIGN_PLAN_SCHEMA:
        raise DesignFabricError("judge-plan requires an axm.design-plan/v0.1 plan")
    plan = copy.deepcopy(plan_raw)
    gates = plan.get("quality_gates") if isinstance(plan.get("quality_gates"), dict) else {}
    results = []
    missing_roles = plan.get("missing_roles") if isinstance(plan.get("missing_roles"), list) else []
    missing_components = plan.get("missing_components") if isinstance(plan.get("missing_components"), list) else []
    results.append({"gate": "requested-component-and-role-coverage", "status": "PASS" if not missing_roles and not missing_components else "FAIL", "evidence": {"missing_roles": missing_roles, "missing_components": missing_components}})
    focus_missing = []
    if gates.get("focus_visible_required"):
        for component in plan.get("selected_components", []):
            if isinstance(component, dict) and component.get("interactive") and "focus" not in {_state(str(value)) for value in component.get("states", [])}:
                focus_missing.append(component.get("id"))
    results.append({"gate": "interactive-focus-state", "status": "PASS" if not focus_missing else "FAIL", "evidence": {"components_missing_focus": focus_missing}})
    viewports = plan.get("viewports") if isinstance(plan.get("viewports"), list) else []
    breakpoints = plan.get("layout", {}).get("breakpoints", []) if isinstance(plan.get("layout"), dict) else []
    responsive_needed = bool(gates.get("responsive_required")) and len(viewports) > 1
    results.append({"gate": "responsive-layout-evidence", "status": "PASS" if not responsive_needed or breakpoints else "HOLD", "evidence": {"viewports": viewports, "breakpoint_count": len(breakpoints)}})
    strategy = str(plan.get("motion", {}).get("reduced_motion_strategy", "unknown")).casefold() if isinstance(plan.get("motion"), dict) else "unknown"
    reduced_ok = not gates.get("reduced_motion_required") or strategy in {"disable-nonessential", "shorten", "replace"}
    results.append({"gate": "reduced-motion-strategy", "status": "PASS" if reduced_ok else "HOLD", "evidence": {"required": bool(gates.get("reduced_motion_required")), "strategy": strategy}})
    pairs = plan.get("contrast_pairs") if isinstance(plan.get("contrast_pairs"), list) else []
    if pairs:
        failed = [row for row in pairs if isinstance(row, dict) and row.get("passed") is not True]
        results.append({"gate": "explicit-text-contrast", "status": "PASS" if not failed else "FAIL", "evidence": {"pair_count": len(pairs), "failed_pairs": failed}})
    else:
        results.append({"gate": "explicit-text-contrast", "status": "HOLD", "evidence": {"pair_count": 0, "reason": "no explicit foreground/background text contrast pairs were supplied"}})
    statuses = [row["status"] for row in results]
    status = "FAIL" if "FAIL" in statuses else "HOLD" if "HOLD" in statuses else "PASS"
    judgment = {
        "schema": DESIGN_JUDGMENT_SCHEMA,
        "truth_status": "DETERMINISTIC_DESIGN_PLAN_GATE_EVIDENCE",
        "status": status,
        "passed": status == "PASS",
        "plan_digest": plan.get("plan_digest"),
        "gates": results,
        "unobserved": ["rendered visual hierarchy", "screenshot similarity or originality", "actual browser interaction", "subjective aesthetic quality", "runtime animation smoothness"],
        "repair_direction": [row["gate"] for row in results if row["status"] != "PASS"],
    }
    judgment["judgment_digest"] = _digest(judgment)
    return judgment


def materialize_design_package(target: Path, genome_raw: Any, request_raw: Any, *, replace: bool = False) -> dict[str, Any]:
    genome = validate_design_genome(genome_raw)
    plan = compose_design_plan(genome, request_raw)
    judgment = judge_design_plan(plan)
    files = {
        "design.genome.json": json.dumps(genome, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "design.plan.json": json.dumps(plan, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        "design.judgment.json": json.dumps(judgment, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
    }
    try:
        result = build_project(
            target=Path(target).resolve(),
            files=files,
            project_type="generic",
            checks=[
                {"type": "file-set", "files": sorted(files), "mode": "exact"},
                {"type": "json-valid", "path": "design.genome.json"},
                {"type": "json-valid", "path": "design.plan.json"},
                {"type": "json-valid", "path": "design.judgment.json"},
            ],
            replace=replace,
            publish_mode="validated",
        )
    except ProjectError as exc:
        raise DesignFabricError(str(exc), exc.details) from exc
    result["truth_status"] = "VALIDATED_DESIGN_FABRIC_DESCRIPTOR_PROJECT"
    result["design_judgment"] = judgment
    return result


def design_fabric_summary() -> dict[str, Any]:
    return {
        "observation_schema": DESIGN_OBSERVATION_SCHEMA,
        "genome_schema": DESIGN_GENOME_SCHEMA,
        "plan_schema": DESIGN_PLAN_SCHEMA,
        "judgment_schema": DESIGN_JUDGMENT_SCHEMA,
        "operations": ["inspect-schema", "observe-project", "derive-genome", "validate-genome", "compose-plan", "judge-plan", "materialize"],
        "reference_lens": "deterministic local UTF-8 source observation",
        "design_genome": "reusable tokens, layout, component semantics/states, motion, materials, quality gates, and provenance",
        "composition": "exact component id/role selection plus token/layout/motion/material binding",
        "judge": "deterministic structural gates with explicit HOLD for unobserved evidence",
        "visual_runtime_observed": False,
        "screenshot_comparison_available": False,
        "external_design_service_required": False,
        "boundaries": [
            "reference observation does not fetch external URLs or proprietary source",
            "reference signals do not prove semantic roles or visual quality",
            "derived genomes preserve grammar signals without copying source page composition by default",
            "rendered screenshot/browser judgment remains a future observer adapter rather than a fake current capability",
        ],
    }


def operate_design_fabric(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    supported = set(design_fabric_summary()["operations"])
    if operation not in supported:
        raise DesignFabricError("design fabric operation is unsupported", {"operation": operation, "supported_operations": sorted(supported)})
    if operation == "inspect-schema":
        return {"truth_status": "DECLARED_DESIGN_FABRIC_V0_1", **design_fabric_summary()}
    if operation == "observe-project":
        return observe_project_style(_resolve_path(root, _text(inputs.get("path"), "path")))
    if operation == "derive-genome":
        return derive_design_genome(inputs.get("observation"), inputs.get("genome_id"), inputs.get("version", "0.1.0"), inputs.get("purpose"))
    if operation == "validate-genome":
        return {"truth_status": "DETERMINISTIC_DESIGN_GENOME_VALIDATION", "genome": validate_design_genome(inputs.get("genome"))}
    if operation == "compose-plan":
        return compose_design_plan(inputs.get("genome"), inputs.get("request"))
    if operation == "judge-plan":
        return judge_design_plan(inputs.get("plan"))
    if operation == "materialize":
        replace = inputs.get("replace", False)
        if not isinstance(replace, bool):
            raise DesignFabricError("design fabric materialize replace must be boolean")
        target = _resolve_path(root, _text(inputs.get("path"), "path"))
        if _is_machine_body_path(root, target):
            raise DesignFabricError("design fabric materialization is an ordinary creation and cannot rewrite the live machine body")
        return materialize_design_package(target, inputs.get("genome"), inputs.get("request"), replace=replace)
    raise AssertionError("unreachable")

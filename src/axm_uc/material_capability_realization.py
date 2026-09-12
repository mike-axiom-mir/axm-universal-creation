from __future__ import annotations

import copy
import hashlib
import html
import json
from pathlib import Path
from typing import Any, Callable

from . import material_capability_exchange as exchange
from .material_capability_full_intake import (
    PATTERN_SCHEMA,
    RECIPE_SCHEMA,
    SPRITE_SCHEMA,
    FullMaterialCapabilityError,
    consume_material_capability_pack_full,
)


VERSION = "0.20.0"
REALIZATION_SCHEMA = "axm.uc.material-capability-realization/v0.1"
MAX_CANVAS = 2048
REALIZER_CONSUMER = {
    "system": "AXM Universal Creation",
    "repository": "mike-axiom-mir/axm-universal-creation",
    "adapter": "material-capability-realizer/v0.20.0",
    "instance": None,
}
REQUIRED_KINDS = (
    "material-entry",
    "material-family",
    "sprite-candidate",
    "recipe",
    "pattern",
)


class MaterialCapabilityRealizationError(FullMaterialCapabilityError):
    pass


def _stable_json(value: Any) -> str:
    return exchange._stable_json(value)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _fmt(value: float) -> str:
    text = f"{float(value):.4f}".rstrip("0").rstrip(".")
    return text if text and text != "-0" else "0"


def _number(value: Any, default: float, lo: float, hi: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    if number != number or number in {float("inf"), float("-inf")}:
        number = default
    return max(lo, min(hi, number))


def _color(seed: str, offset: int) -> str:
    digest = hashlib.sha256(f"{seed}|{offset}".encode("utf-8")).digest()
    # Keep hash-derived colors away from near-black so structure stays inspectable.
    channels = [48 + (digest[index] % 176) for index in range(3)]
    return "#" + "".join(f"{channel:02X}" for channel in channels)


def _prng(seed: str) -> Callable[[], float]:
    state = int.from_bytes(hashlib.sha256(seed.encode("utf-8")).digest()[:8], "big") or 1

    def next_value() -> float:
        nonlocal state
        state = (6364136223846793005 * state + 1442695040888963407) & 0xFFFFFFFFFFFFFFFF
        return state / 18446744073709551616.0

    return next_value


def _selection(pack: dict[str, Any], selected: dict[str, str] | None) -> dict[str, dict[str, Any]]:
    requested = selected or {}
    result: dict[str, dict[str, Any]] = {}
    for kind in REQUIRED_KINDS:
        candidates = [row for row in pack["capabilities"] if row.get("kind") == kind]
        wanted = str(requested.get(kind) or "").strip()
        if wanted:
            candidates = [row for row in candidates if row.get("id") == wanted]
            if not candidates:
                raise MaterialCapabilityRealizationError(
                    f"selected {kind} capability is not present in the pack",
                    {"capability_id": wanted},
                )
        if len(candidates) != 1:
            raise MaterialCapabilityRealizationError(
                f"native realization requires exactly one selected {kind} capability",
                {"kind": kind, "available": [row.get("id") for row in candidates]},
            )
        result[kind] = candidates[0]
    return result


def _projection_map(intake: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_schema = {row["schema"]: row for row in intake.get("detached_visual_capabilities") or []}
    missing = [schema for schema in (SPRITE_SCHEMA, RECIPE_SCHEMA, PATTERN_SCHEMA) if schema not in by_schema]
    if missing:
        raise MaterialCapabilityRealizationError(
            "full intake did not produce every required detached visual descriptor",
            {"missing": missing},
        )
    return by_schema


def _layer_box(layer: dict[str, Any], width: int, height: int) -> dict[str, float]:
    transform = layer.get("transform") if isinstance(layer.get("transform"), dict) else {}
    cx = _number(transform.get("x"), 0.5, -2, 3) * width
    cy = _number(transform.get("y"), 0.5, -2, 3) * height
    box_width = _number(transform.get("width"), 0.75, 0.02, 4) * width
    box_height = _number(transform.get("height"), 0.75, 0.02, 4) * height
    return {
        "x": cx - box_width / 2,
        "y": cy - box_height / 2,
        "width": box_width,
        "height": box_height,
        "cx": cx,
        "cy": cy,
        "rotation": _number(transform.get("rotation"), 0, -3600, 3600),
    }


def _blend(value: Any) -> str:
    mode = str(value or "normal").strip().casefold()
    if mode == "lighter":
        return "screen"
    if mode in {"normal", "multiply", "screen", "overlay", "soft-light", "hard-light", "difference"}:
        return mode
    return "normal"


def _motif_elements(
    *,
    seed: str,
    box: dict[str, float],
    colors: list[str],
    category: str,
    count: int,
) -> list[str]:
    rand = _prng(seed)
    out: list[str] = []
    corrosion = "corrosion" in category or "weather" in category or "wear" in category
    grid_like = "grid" in category or "panel" in category or "circuit" in category
    for index in range(max(1, min(64, count))):
        x = box["x"] + rand() * box["width"]
        y = box["y"] + rand() * box["height"]
        color = colors[(index + int(rand() * len(colors))) % len(colors)]
        opacity = 0.18 + rand() * 0.42
        if grid_like and index % 2 == 0:
            length = box["width"] * (0.12 + rand() * 0.42)
            out.append(
                f'<path d="M {_fmt(x)} {_fmt(y)} h {_fmt(length)}" '
                f'stroke="{color}" stroke-width="{_fmt(1 + rand() * 4)}" opacity="{_fmt(opacity)}" fill="none" />'
            )
        elif corrosion:
            rx = max(2.0, box["width"] * (0.012 + rand() * 0.06))
            ry = max(2.0, box["height"] * (0.012 + rand() * 0.05))
            out.append(
                f'<ellipse cx="{_fmt(x)}" cy="{_fmt(y)}" rx="{_fmt(rx)}" ry="{_fmt(ry)}" '
                f'fill="{color}" opacity="{_fmt(opacity)}" />'
            )
        else:
            size = max(2.0, min(box["width"], box["height"]) * (0.018 + rand() * 0.07))
            out.append(
                f'<rect x="{_fmt(x - size / 2)}" y="{_fmt(y - size / 2)}" width="{_fmt(size)}" '
                f'height="{_fmt(size)}" rx="{_fmt(size * 0.22)}" fill="{color}" opacity="{_fmt(opacity)}" />'
            )
    return out


def build_material_capability_svg(
    raw_pack: Any,
    *,
    selected: dict[str, str] | None = None,
    seed: str = "native-realization",
) -> dict[str, Any]:
    pack = exchange.validate_material_capability_pack(raw_pack)
    intake = consume_material_capability_pack_full(pack, strict=True)
    chosen = _selection(pack, selected)
    projections = _projection_map(intake)
    sprite = projections[SPRITE_SCHEMA]
    recipe_projection = projections[RECIPE_SCHEMA]
    pattern_projection = projections[PATTERN_SCHEMA]
    recipe = recipe_projection["recipe"]
    canvas = recipe.get("canvas") or {}
    width = int(_number(canvas.get("width"), 1024, 1, MAX_CANVAS))
    height = int(_number(canvas.get("height"), 1024, 1, MAX_CANVAS))
    if canvas.get("transparent") is not True:
        raise MaterialCapabilityRealizationError("native realization requires the imported recipe to remain transparent")

    creation_basis = {
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "selected": {kind: chosen[kind]["id"] for kind in REQUIRED_KINDS},
        "seed": str(seed),
    }
    creation_id = f"uc-material-creation-{hashlib.sha256(_stable_json(creation_basis).encode('utf-8')).hexdigest()[:20]}"

    palette_seed = "|".join(
        [
            chosen["material-entry"]["fingerprint"],
            chosen["material-family"]["fingerprint"],
            pack["fingerprint"],
            str(seed),
        ]
    )
    colors = [_color(palette_seed, index) for index in range(5)]
    layers = recipe.get("layers") or []
    if not layers:
        raise MaterialCapabilityRealizationError("native realization requires at least one imported recipe layer")

    sprite_bounds = sprite["normalizedBounds"]
    pattern = pattern_projection["pattern"]
    slots = sorted(pattern.get("slots") or [], key=lambda row: row.get("order", 0))
    support = int(pattern_projection["support"])
    pattern_categories = [str(slot.get("category") or "") for slot in slots]

    metadata = {
        "schema": REALIZATION_SCHEMA,
        "version": VERSION,
        "id": creation_id,
        "sourcePackId": pack["id"],
        "sourcePackFingerprint": pack["fingerprint"],
        "capabilityIds": {kind: chosen[kind]["id"] for kind in REQUIRED_KINDS},
        "nativeUse": {
            "material-entry": "hash-derived native palette seed; producer image pixels are not sampled",
            "material-family": "material grouping participates in native palette/creation identity",
            "sprite-candidate": "normalized alpha bounds constrain the matching native motif region",
            "recipe": "canvas, layer order, transforms, opacity and blend structure drive the SVG composition",
            "pattern": "ordered slots, categories and support drive motif structure/density",
        },
        "truthBoundary": {
            "producerPixelsRendered": False,
            "sourceAtlasBytesInstalled": False,
            "semanticRecognition": False,
            "rasterRenderVerified": False,
            "physicalMaterialTruth": False,
        },
    }

    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        f'<metadata>{html.escape(_stable_json(metadata), quote=False)}</metadata>',
        '<defs>',
        f'<linearGradient id="axm-base" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{colors[0]}"/><stop offset="0.52" stop-color="{colors[1]}"/><stop offset="1" stop-color="{colors[2]}"/></linearGradient>',
    ]

    # The sprite candidate is atlas-relative producer evidence. In this native reinterpretation
    # it acts as a normalized motif window inside the matching recipe layer, not as a claim that
    # source atlas pixels were cropped or rendered.
    sprite_layer_index = next(
        (index for index, layer in enumerate(layers) if str(layer.get("assetId") or "") == str(sprite.get("atlasId") or "")),
        None,
    )
    if sprite_layer_index is not None:
        sprite_box_parent = _layer_box(layers[sprite_layer_index], width, height)
        clip_x = sprite_box_parent["x"] + sprite_bounds["x"] * sprite_box_parent["width"]
        clip_y = sprite_box_parent["y"] + sprite_bounds["y"] * sprite_box_parent["height"]
        clip_w = sprite_bounds["width"] * sprite_box_parent["width"]
        clip_h = sprite_bounds["height"] * sprite_box_parent["height"]
        parts.append(
            f'<clipPath id="axm-sprite-window"><rect x="{_fmt(clip_x)}" y="{_fmt(clip_y)}" width="{_fmt(clip_w)}" height="{_fmt(clip_h)}" rx="{_fmt(min(clip_w, clip_h) * 0.08)}"/></clipPath>'
        )
    parts.append('</defs>')

    for index, layer in enumerate(layers):
        if layer.get("visible") is False:
            continue
        box = _layer_box(layer, width, height)
        opacity = _number(layer.get("opacity"), 1.0, 0.0, 1.0)
        asset_id = str(layer.get("assetId") or "")
        transform = f'rotate({_fmt(box["rotation"])} {_fmt(box["cx"])} {_fmt(box["cy"])})'
        if index == 0:
            if "globe" in asset_id:
                parts.append(
                    f'<ellipse data-layer="{html.escape(str(layer.get("id") or index))}" data-asset="{html.escape(asset_id)}" '
                    f'cx="{_fmt(box["cx"])}" cy="{_fmt(box["cy"])}" rx="{_fmt(box["width"] / 2)}" ry="{_fmt(box["height"] / 2)}" '
                    f'fill="url(#axm-base)" opacity="{_fmt(opacity)}" transform="{transform}" />'
                )
            else:
                parts.append(
                    f'<rect data-layer="{html.escape(str(layer.get("id") or index))}" data-asset="{html.escape(asset_id)}" '
                    f'x="{_fmt(box["x"])}" y="{_fmt(box["y"])}" width="{_fmt(box["width"])}" height="{_fmt(box["height"])}" '
                    f'rx="{_fmt(min(box["width"], box["height"]) * 0.08)}" fill="url(#axm-base)" opacity="{_fmt(opacity)}" transform="{transform}" />'
                )
            continue

        category = pattern_categories[min(index, len(pattern_categories) - 1)] if pattern_categories else asset_id
        motif_count = 8 + support * 3 + len(slots) * 2 + index
        clip_attr = ' clip-path="url(#axm-sprite-window)"' if sprite_layer_index == index else ""
        parts.append(
            f'<g data-layer="{html.escape(str(layer.get("id") or index))}" data-asset="{html.escape(asset_id)}" '
            f'data-pattern-category="{html.escape(category)}" opacity="{_fmt(opacity)}" style="mix-blend-mode:{_blend(layer.get("blendMode"))}" transform="{transform}"{clip_attr}>'
        )
        parts.extend(
            _motif_elements(
                seed=f"{creation_id}|{index}|{asset_id}|{pattern_projection['id']}",
                box=box,
                colors=colors[1:],
                category=category,
                count=motif_count,
            )
        )
        parts.append('</g>')

    # Add one thin structural frame derived from the pattern slot count so a pattern-only change
    # is observable even when imported recipe layers stay otherwise identical.
    inset = 4 + min(48, len(slots) * 3)
    parts.append(
        f'<rect x="{inset}" y="{inset}" width="{max(1, width - inset * 2)}" height="{max(1, height - inset * 2)}" '
        f'rx="{max(1, inset / 2)}" fill="none" stroke="{colors[4]}" stroke-width="2" opacity="0.45" />'
    )
    parts.append('</svg>')
    svg = "\n".join(parts) + "\n"
    return {
        "schema": REALIZATION_SCHEMA,
        "version": VERSION,
        "id": creation_id,
        "svg": svg,
        "width": width,
        "height": height,
        "selected": {kind: chosen[kind]["id"] for kind in REQUIRED_KINDS},
        "intake": intake,
        "truthBoundary": copy.deepcopy(metadata["truthBoundary"]),
    }


def _feedback_event(capability: dict[str, Any], creation_id: str, output_sha256: str, use_mode: str) -> dict[str, Any]:
    return exchange._event(
        capability["id"],
        "reused",
        "PASS",
        evidence={
            "nativeCreationId": creation_id,
            "artifactFormat": "image/svg+xml",
            "artifactSha256": output_sha256,
            "useMode": use_mode,
            "svgArtifactGenerated": True,
            "producerPixelsRendered": False,
            "rasterRenderVerified": False,
        },
        derived_ids=[creation_id],
        note="Capability state directly influenced a deterministic native Universal Creation SVG artifact; this is not a faithful render of producer atlas pixels.",
    )


def _create_realization_feedback(pack: dict[str, Any], chosen: dict[str, dict[str, Any]], creation_id: str, output_sha256: str) -> dict[str, Any]:
    modes = {
        "material-entry": "hash-derived-native-palette-seed",
        "material-family": "native-material-family-grouping",
        "sprite-candidate": "alpha-bounds-native-motif-window",
        "recipe": "layout-transform-opacity-blend-structure",
        "pattern": "slot-order-category-support-motif-structure",
    }
    events = [_feedback_event(chosen[kind], creation_id, output_sha256, modes[kind]) for kind in REQUIRED_KINDS]
    basis = {
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": REALIZER_CONSUMER,
        "events": events,
    }
    fingerprint = exchange._fnv1a_js(_stable_json(basis))
    return {
        "format": exchange.FEEDBACK_FORMAT,
        "version": exchange.FEEDBACK_VERSION,
        "id": f"material-use-feedback-{fingerprint}",
        "fingerprint": fingerprint,
        "packId": pack["id"],
        "packFingerprint": pack["fingerprint"],
        "consumer": copy.deepcopy(REALIZER_CONSUMER),
        "events": events,
        "note": "AXM Universal Creation native structural material-capability realization receipt.",
        "truthBoundary": {
            "use": "PASS reused means the named capability directly influenced the generated native SVG state.",
            "pixels": "The producer atlas/image pixels were not rendered or sampled; material-entry bytes only seed deterministic native palette state by fingerprint.",
            "rendering": "An SVG artifact was generated and hashed; cross-browser raster output was not verified.",
            "quality": "Reuse does not prove aesthetics, realism, PBR correctness, semantic understanding, or universal usefulness.",
            "authority": "Actual use evidence does not auto-promote either repository's canonical state.",
        },
    }


def validate_realization_feedback(feedback: Any, raw_pack: Any) -> dict[str, Any]:
    pack = exchange.validate_material_capability_pack(raw_pack)
    if not isinstance(feedback, dict):
        raise MaterialCapabilityRealizationError("realization feedback must be an object")
    if feedback.get("format") != exchange.FEEDBACK_FORMAT or feedback.get("version") != exchange.FEEDBACK_VERSION:
        raise MaterialCapabilityRealizationError(f"expected {exchange.FEEDBACK_FORMAT}/{exchange.FEEDBACK_VERSION}")
    if feedback.get("packId") != pack["id"] or feedback.get("packFingerprint") != pack["fingerprint"]:
        raise MaterialCapabilityRealizationError("realization feedback pack linkage mismatch")
    if feedback.get("consumer") != REALIZER_CONSUMER:
        raise MaterialCapabilityRealizationError("realization feedback consumer identity mismatch")
    events = feedback.get("events")
    if not isinstance(events, list) or len(events) != len(REQUIRED_KINDS):
        raise MaterialCapabilityRealizationError("realization feedback requires exactly one event for every current capability kind")
    capability_ids = {row["id"] for row in pack["capabilities"]}
    normalized: list[dict[str, Any]] = []
    for index, event in enumerate(events):
        if not isinstance(event, dict) or event.get("capabilityId") not in capability_ids:
            raise MaterialCapabilityRealizationError(f"realization feedback event {index} references an unknown capability")
        rebuilt = exchange._event(
            event["capabilityId"],
            str(event.get("action") or ""),
            str(event.get("outcome") or ""),
            evidence=event.get("evidence") if isinstance(event.get("evidence"), dict) else {},
            derived_ids=event.get("derivedIds") if isinstance(event.get("derivedIds"), list) else [],
            note=str(event.get("note") or ""),
        )
        if rebuilt != event or event.get("action") != "reused" or event.get("outcome") != "PASS":
            raise MaterialCapabilityRealizationError("realization feedback event identity/content mismatch", {"index": index})
        normalized.append(copy.deepcopy(event))
    basis = {
        "packId": feedback["packId"],
        "packFingerprint": feedback["packFingerprint"],
        "consumer": feedback["consumer"],
        "events": normalized,
    }
    expected = exchange._fnv1a_js(_stable_json(basis))
    if feedback.get("fingerprint") != expected or feedback.get("id") != f"material-use-feedback-{expected}":
        raise MaterialCapabilityRealizationError("realization feedback fingerprint/id mismatch")
    return copy.deepcopy(feedback)


def realize_material_capability_pack(
    raw_pack: Any,
    target: Path | str,
    *,
    selected: dict[str, str] | None = None,
    seed: str = "native-realization",
    replace: bool = False,
) -> dict[str, Any]:
    pack = exchange.validate_material_capability_pack(raw_pack)
    built = build_material_capability_svg(pack, selected=selected, seed=seed)
    chosen = _selection(pack, selected)
    path = Path(target)
    if path.exists() and not replace:
        raise FileExistsError(f"target already exists: {path}; pass replace=True to overwrite")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = built["svg"].encode("utf-8")
    path.write_bytes(payload)
    output_sha256 = _sha256_bytes(payload)
    feedback = _create_realization_feedback(pack, chosen, built["id"], output_sha256)
    validate_realization_feedback(feedback, pack)
    return {
        "schema": REALIZATION_SCHEMA,
        "version": VERSION,
        "id": built["id"],
        "truth_status": "OBSERVED_GENERATED_NATIVE_MATERIAL_CAPABILITY_CREATION",
        "source": {
            "pack_id": pack["id"],
            "pack_fingerprint": pack["fingerprint"],
            "producer": copy.deepcopy(pack["producer"]),
            "selected_capabilities": copy.deepcopy(built["selected"]),
        },
        "output": {
            "format": "svg",
            "mime": "image/svg+xml",
            "path": str(path),
            "sha256": output_sha256,
            "bytes": len(payload),
            "width": built["width"],
            "height": built["height"],
            "transparent": True,
        },
        "feedback": feedback,
        "truthBoundary": {
            "actualUse": "Every selected capability kind directly influences the emitted SVG state and receives a PASS reused event.",
            "producerPixels": "This is a native structural realization, not a faithful render of Material / Surface atlas/image pixels.",
            "rendering": "The SVG file is generated and byte-hashed; raster/browser visual parity is not claimed.",
            "semantics": "Alpha bounds and pattern slots are used as supplied structural state without upgrading them into semantic recognition.",
            "physical": "No PBR or physical-material correctness is claimed.",
            "authority": "Creation use and feedback do not silently modify canonical project/topology or producer memory.",
        },
    }

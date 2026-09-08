from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

from .design_observer import RENDER_OBSERVATION_SCHEMA
from .design_visual import _inflate_scanlines, _parse_png, _row_rgba


RENDER_COMPARISON_SCHEMA = "axm.design-render-comparison/v0.1"
MAX_REGIONS_PER_AXIS = 8


class DesignCompareError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _bytes_digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignCompareError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignCompareError(f"{label} exceeds its {maximum}-character bound")
    return result


def _resolve_path(root: Path, value: Any, label: str) -> Path:
    text = _text(value, label)
    path = Path(text).expanduser()
    if not path.is_absolute():
        path = Path(root).resolve() / path
    path = path.resolve()
    if not path.is_file() or path.suffix.casefold() != ".png":
        raise DesignCompareError(f"{label} must resolve to a local PNG file", {"path": str(path)})
    return path


def _observation(raw: Any, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != RENDER_OBSERVATION_SCHEMA:
        raise DesignCompareError(f"{label} must be an axm.design-render-observation/v0.1 receipt")
    if not isinstance(raw.get("plan_digest"), str) or not isinstance(raw.get("captures"), list):
        raise DesignCompareError(f"{label} is missing plan/capture evidence")
    return json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))


def _capture_for_viewport(observation: dict[str, Any], viewport_id: str, label: str) -> dict[str, Any]:
    matches = [
        row
        for row in observation.get("captures", [])
        if isinstance(row, dict)
        and isinstance(row.get("viewport"), dict)
        and row["viewport"].get("id") == viewport_id
    ]
    if len(matches) != 1:
        raise DesignCompareError(
            f"{label} must contain exactly one capture for viewport {viewport_id}",
            {"viewport": viewport_id, "matches": len(matches)},
        )
    return matches[0]


def _screenshot_digest(capture: dict[str, Any], label: str) -> str:
    rows = [
        artifact
        for artifact in capture.get("artifacts", [])
        if isinstance(artifact, dict) and artifact.get("kind") == "screenshot"
    ]
    if len(rows) != 1 or not isinstance(rows[0].get("digest"), str):
        raise DesignCompareError(f"{label} must contain exactly one screenshot artifact digest")
    digest = rows[0]["digest"].casefold()
    if not digest.startswith("sha256:") or len(digest) != 71:
        raise DesignCompareError(f"{label} screenshot digest is invalid")
    return digest


def _decode_rgba(data: bytes) -> tuple[dict[str, Any], list[list[tuple[int, int, int, int]]]]:
    ihdr, compressed, palette, transparency = _parse_png(data)
    rows, _channels = _inflate_scanlines(ihdr, compressed)
    pixels = [
        _row_rgba(row, ihdr["color_type"], palette, transparency)
        for row in rows
    ]
    return ihdr, pixels


def _region_bounds(length: int, index: int, count: int) -> tuple[int, int]:
    start = math.floor(index * length / count)
    end = math.floor((index + 1) * length / count)
    return start, max(start + 1, end)


def compare_render_screenshots(
    root: Path,
    before_path_raw: Any,
    after_path_raw: Any,
    before_observation_raw: Any,
    after_observation_raw: Any,
    viewport_raw: Any,
) -> dict[str, Any]:
    viewport_id = _text(viewport_raw, "viewport", 128)
    before_observation = _observation(before_observation_raw, "before_observation")
    after_observation = _observation(after_observation_raw, "after_observation")
    before_capture = _capture_for_viewport(before_observation, viewport_id, "before_observation")
    after_capture = _capture_for_viewport(after_observation, viewport_id, "after_observation")

    before_path = _resolve_path(root, before_path_raw, "before_path")
    after_path = _resolve_path(root, after_path_raw, "after_path")
    before_bytes = before_path.read_bytes()
    after_bytes = after_path.read_bytes()
    before_actual_digest = _bytes_digest(before_bytes)
    after_actual_digest = _bytes_digest(after_bytes)
    before_declared_digest = _screenshot_digest(before_capture, "before_observation")
    after_declared_digest = _screenshot_digest(after_capture, "after_observation")
    if before_actual_digest != before_declared_digest:
        raise DesignCompareError(
            "before screenshot bytes do not match the bound observation receipt",
            {"declared": before_declared_digest, "actual": before_actual_digest},
        )
    if after_actual_digest != after_declared_digest:
        raise DesignCompareError(
            "after screenshot bytes do not match the bound observation receipt",
            {"declared": after_declared_digest, "actual": after_actual_digest},
        )

    before_header, before_pixels = _decode_rgba(before_bytes)
    after_header, after_pixels = _decode_rgba(after_bytes)
    before_dimensions = [before_header["width"], before_header["height"]]
    after_dimensions = [after_header["width"], after_header["height"]]
    if before_dimensions != after_dimensions:
        result = {
            "schema": RENDER_COMPARISON_SCHEMA,
            "truth_status": "HOLD_RENDER_COMPARISON_DIMENSION_MISMATCH",
            "status": "HOLD",
            "viewport": viewport_id,
            "before": {
                "plan_digest": before_observation["plan_digest"],
                "observation_digest": before_observation.get("observation_digest"),
                "artifact_digest": before_actual_digest,
                "dimensions": before_dimensions,
            },
            "after": {
                "plan_digest": after_observation["plan_digest"],
                "observation_digest": after_observation.get("observation_digest"),
                "artifact_digest": after_actual_digest,
                "dimensions": after_dimensions,
            },
            "change": None,
            "claim_boundary": {
                "quality_improved": False,
                "regression_proven": False,
                "aesthetic_judgment": False,
                "semantic_change_inferred": False,
            },
        }
        result["comparison_digest"] = _digest(result)
        return result

    width, height = before_dimensions
    pixel_count = width * height
    changed_pixel_count = 0
    rgb_l1_sum = 0
    rgb_l1_max = 0
    alpha_delta_sum = 0
    luminance_delta_sum = 0.0

    region_cols = min(MAX_REGIONS_PER_AXIS, width)
    region_rows = min(MAX_REGIONS_PER_AXIS, height)
    region_changed = [[0 for _ in range(region_cols)] for _ in range(region_rows)]
    region_total = [[0 for _ in range(region_cols)] for _ in range(region_rows)]

    for y in range(height):
        region_y = min(region_rows - 1, math.floor(y * region_rows / height))
        for x in range(width):
            region_x = min(region_cols - 1, math.floor(x * region_cols / width))
            before = before_pixels[y][x]
            after = after_pixels[y][x]
            region_total[region_y][region_x] += 1
            if before != after:
                changed_pixel_count += 1
                region_changed[region_y][region_x] += 1
            rgb_delta = abs(before[0] - after[0]) + abs(before[1] - after[1]) + abs(before[2] - after[2])
            rgb_l1_sum += rgb_delta
            rgb_l1_max = max(rgb_l1_max, rgb_delta)
            alpha_delta_sum += abs(before[3] - after[3])
            before_luma = (0.2126 * before[0] + 0.7152 * before[1] + 0.0722 * before[2]) / 255.0
            after_luma = (0.2126 * after[0] + 0.7152 * after[1] + 0.0722 * after[2]) / 255.0
            luminance_delta_sum += abs(before_luma - after_luma)

    regions = []
    for region_y in range(region_rows):
        y0, y1 = _region_bounds(height, region_y, region_rows)
        for region_x in range(region_cols):
            x0, x1 = _region_bounds(width, region_x, region_cols)
            total = region_total[region_y][region_x]
            changed = region_changed[region_y][region_x]
            regions.append({
                "row": region_y,
                "column": region_x,
                "bounds": {"x0": x0, "y0": y0, "x1": x1, "y1": y1},
                "pixel_count": total,
                "changed_pixel_count": changed,
                "changed_fraction": round(changed / total, 8) if total else 0.0,
            })

    change = {
        "pixel_count": pixel_count,
        "changed_pixel_count": changed_pixel_count,
        "changed_fraction": round(changed_pixel_count / pixel_count, 8),
        "unchanged_fraction": round((pixel_count - changed_pixel_count) / pixel_count, 8),
        "mean_rgb_l1_delta": round(rgb_l1_sum / pixel_count, 6),
        "maximum_rgb_l1_delta": rgb_l1_max,
        "mean_alpha_absolute_delta": round(alpha_delta_sum / pixel_count, 6),
        "mean_encoded_luminance_absolute_delta": round(luminance_delta_sum / pixel_count, 8),
        "region_grid": {
            "rows": region_rows,
            "columns": region_cols,
            "regions": regions,
        },
    }
    result = {
        "schema": RENDER_COMPARISON_SCHEMA,
        "truth_status": "DETERMINISTIC_BOUND_SCREENSHOT_CHANGE_MEASUREMENT",
        "status": "PASS",
        "viewport": viewport_id,
        "before": {
            "plan_digest": before_observation["plan_digest"],
            "observation_digest": before_observation.get("observation_digest"),
            "artifact_digest": before_actual_digest,
            "dimensions": before_dimensions,
        },
        "after": {
            "plan_digest": after_observation["plan_digest"],
            "observation_digest": after_observation.get("observation_digest"),
            "artifact_digest": after_actual_digest,
            "dimensions": after_dimensions,
        },
        "change": change,
        "claim_boundary": {
            "quality_improved": False,
            "regression_proven": False,
            "aesthetic_judgment": False,
            "semantic_change_inferred": False,
            "only_pixel_change_measured": True,
        },
    }
    result["comparison_digest"] = _digest(result)
    return result


def design_compare_summary() -> dict[str, Any]:
    return {
        "comparison_schema": RENDER_COMPARISON_SCHEMA,
        "operations": ["inspect-render-comparison", "compare-render-screenshots"],
        "requires": [
            "before and after local PNG bytes",
            "before and after render-observation receipts",
            "one exact viewport id present in both receipts",
        ],
        "measurements": [
            "exact changed-pixel fraction",
            "mean and maximum RGB L1 delta",
            "mean alpha delta",
            "mean encoded-luminance delta",
            "bounded 8x8-or-smaller regional change grid",
        ],
        "artifact_digest_reverified": True,
        "quality_improvement_inferred": False,
        "automatic_acceptance": False,
    }


def operate_design_compare(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-render-comparison":
        return {"truth_status": "DECLARED_RENDER_COMPARISON_V0_1", **design_compare_summary()}
    if operation == "compare-render-screenshots":
        return compare_render_screenshots(
            root,
            inputs.get("before_path"),
            inputs.get("after_path"),
            inputs.get("before_observation"),
            inputs.get("after_observation"),
            inputs.get("viewport"),
        )
    raise DesignCompareError(
        "render comparison operation is unsupported",
        {"operation": operation, "supported_operations": design_compare_summary()["operations"]},
    )

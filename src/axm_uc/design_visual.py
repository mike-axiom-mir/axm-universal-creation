from __future__ import annotations

import hashlib
import json
import math
import struct
import zlib
from collections import Counter
from pathlib import Path
from typing import Any

from .design_fabric import DESIGN_OBSERVATION_SCHEMA, derive_design_genome, validate_design_genome
from .design_observer import record_render_observation


SCREENSHOT_PIXEL_SCHEMA = "axm.design-screenshot-pixels/v0.1"
SCREENSHOT_OBSERVATION_SCHEMA = "axm.design-screenshot-observation/v0.1"
MAX_PNG_BYTES = 50_000_000
MAX_PIXELS = 8_000_000
PALETTE_BUCKET_BITS = 4
MAX_PALETTE_ROWS = 16
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
SUPPORTED_COLOR_TYPES = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}


class DesignVisualError(RuntimeError):
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


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignVisualError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignVisualError(f"{label} exceeds its {maximum}-character bound")
    return result


def _resolve_path(root: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    if not path.is_absolute():
        path = Path(root).resolve() / path
    return path.resolve()


def _paeth(left: int, up: int, upper_left: int) -> int:
    estimate = left + up - upper_left
    left_distance = abs(estimate - left)
    up_distance = abs(estimate - up)
    upper_left_distance = abs(estimate - upper_left)
    if left_distance <= up_distance and left_distance <= upper_left_distance:
        return left
    if up_distance <= upper_left_distance:
        return up
    return upper_left


def _parse_png(data: bytes) -> tuple[dict[str, Any], bytes, bytes | None, bytes | None]:
    if len(data) > MAX_PNG_BYTES:
        raise DesignVisualError("PNG exceeds the screenshot byte bound", {"bytes": len(data), "maximum": MAX_PNG_BYTES})
    if not data.startswith(PNG_SIGNATURE):
        raise DesignVisualError("screenshot must be a PNG file")

    offset = len(PNG_SIGNATURE)
    ihdr: dict[str, Any] | None = None
    idat_parts: list[bytes] = []
    palette: bytes | None = None
    transparency: bytes | None = None
    saw_iend = False

    while offset < len(data):
        if offset + 12 > len(data):
            raise DesignVisualError("PNG chunk header is truncated")
        length = struct.unpack(">I", data[offset:offset + 4])[0]
        chunk_type = data[offset + 4:offset + 8]
        chunk_start = offset + 8
        chunk_end = chunk_start + length
        crc_end = chunk_end + 4
        if crc_end > len(data):
            raise DesignVisualError("PNG chunk data is truncated")
        chunk_data = data[chunk_start:chunk_end]
        declared_crc = struct.unpack(">I", data[chunk_end:crc_end])[0]
        actual_crc = zlib.crc32(chunk_type)
        actual_crc = zlib.crc32(chunk_data, actual_crc) & 0xFFFFFFFF
        if declared_crc != actual_crc:
            raise DesignVisualError("PNG chunk CRC mismatch", {"chunk": chunk_type.decode("ascii", "replace")})

        if chunk_type == b"IHDR":
            if ihdr is not None or length != 13:
                raise DesignVisualError("PNG must contain one valid IHDR chunk")
            width, height, bit_depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", chunk_data)
            ihdr = {
                "width": width,
                "height": height,
                "bit_depth": bit_depth,
                "color_type": color_type,
                "compression": compression,
                "filtering": filtering,
                "interlace": interlace,
            }
        elif chunk_type == b"PLTE":
            palette = chunk_data
        elif chunk_type == b"tRNS":
            transparency = chunk_data
        elif chunk_type == b"IDAT":
            idat_parts.append(chunk_data)
        elif chunk_type == b"IEND":
            if length != 0:
                raise DesignVisualError("PNG IEND chunk must be empty")
            saw_iend = True
            offset = crc_end
            break
        offset = crc_end

    if ihdr is None or not idat_parts or not saw_iend:
        raise DesignVisualError("PNG is missing required IHDR, IDAT, or IEND chunks")
    if offset != len(data):
        raise DesignVisualError("PNG contains trailing bytes after IEND")
    if ihdr["bit_depth"] != 8:
        raise DesignVisualError("visual observer currently supports 8-bit PNG channels only", {"bit_depth": ihdr["bit_depth"]})
    color_type = ihdr["color_type"]
    if color_type not in SUPPORTED_COLOR_TYPES:
        raise DesignVisualError("PNG color type is unsupported", {"color_type": color_type})
    if ihdr["compression"] != 0 or ihdr["filtering"] != 0:
        raise DesignVisualError("PNG uses an unsupported compression or filter method")
    if ihdr["interlace"] != 0:
        raise DesignVisualError("interlaced PNG screenshots are not supported by the minimal observer")
    if ihdr["width"] < 1 or ihdr["height"] < 1:
        raise DesignVisualError("PNG dimensions must be positive")
    pixel_count = ihdr["width"] * ihdr["height"]
    if pixel_count > MAX_PIXELS:
        raise DesignVisualError("PNG exceeds the decoded pixel bound", {"pixels": pixel_count, "maximum": MAX_PIXELS})
    if color_type == 3:
        if palette is None or not palette or len(palette) % 3 != 0 or len(palette) > 768:
            raise DesignVisualError("indexed PNG requires a valid PLTE palette")
    return ihdr, b"".join(idat_parts), palette, transparency


def _inflate_scanlines(ihdr: dict[str, Any], compressed: bytes) -> tuple[list[bytes], int]:
    width = ihdr["width"]
    height = ihdr["height"]
    channels = SUPPORTED_COLOR_TYPES[ihdr["color_type"]]
    row_bytes = width * channels
    expected = height * (row_bytes + 1)

    try:
        decompressor = zlib.decompressobj()
        raw = decompressor.decompress(compressed, expected + 1)
        if decompressor.unconsumed_tail or len(raw) > expected:
            raise DesignVisualError("PNG decompressed data exceeds the expected scanline bound")
        remaining = expected + 1 - len(raw)
        if remaining > 0:
            raw += decompressor.flush(remaining)
    except zlib.error as exc:
        raise DesignVisualError("PNG IDAT stream could not be decompressed", {"reason": str(exc)}) from exc
    if len(raw) != expected or not decompressor.eof:
        raise DesignVisualError(
            "PNG decompressed scanline size does not match image dimensions",
            {"expected": expected, "actual": len(raw)},
        )

    rows: list[bytes] = []
    previous = bytearray(row_bytes)
    cursor = 0
    for row_index in range(height):
        filter_type = raw[cursor]
        cursor += 1
        encoded = raw[cursor:cursor + row_bytes]
        cursor += row_bytes
        if filter_type > 4:
            raise DesignVisualError("PNG row uses an unsupported filter", {"row": row_index, "filter": filter_type})
        decoded = bytearray(row_bytes)
        for index, byte in enumerate(encoded):
            left = decoded[index - channels] if index >= channels else 0
            up = previous[index]
            upper_left = previous[index - channels] if index >= channels else 0
            if filter_type == 0:
                value = byte
            elif filter_type == 1:
                value = byte + left
            elif filter_type == 2:
                value = byte + up
            elif filter_type == 3:
                value = byte + ((left + up) // 2)
            else:
                value = byte + _paeth(left, up, upper_left)
            decoded[index] = value & 0xFF
        rows.append(bytes(decoded))
        previous = decoded
    return rows, channels


def _row_rgba(
    row: bytes,
    color_type: int,
    palette: bytes | None,
    transparency: bytes | None,
) -> list[tuple[int, int, int, int]]:
    pixels: list[tuple[int, int, int, int]] = []
    if color_type == 0:
        transparent_gray = None
        if transparency is not None:
            if len(transparency) != 2:
                raise DesignVisualError("grayscale tRNS chunk is invalid")
            transparent_gray = struct.unpack(">H", transparency)[0]
        for gray in row:
            alpha = 0 if transparent_gray == gray else 255
            pixels.append((gray, gray, gray, alpha))
    elif color_type == 2:
        transparent_rgb = None
        if transparency is not None:
            if len(transparency) != 6:
                raise DesignVisualError("truecolor tRNS chunk is invalid")
            transparent_rgb = struct.unpack(">HHH", transparency)
        for index in range(0, len(row), 3):
            red, green, blue = row[index:index + 3]
            alpha = 0 if transparent_rgb == (red, green, blue) else 255
            pixels.append((red, green, blue, alpha))
    elif color_type == 3:
        assert palette is not None
        palette_rows = [tuple(palette[index:index + 3]) for index in range(0, len(palette), 3)]
        for palette_index in row:
            if palette_index >= len(palette_rows):
                raise DesignVisualError("indexed PNG references a palette entry that does not exist")
            red, green, blue = palette_rows[palette_index]
            alpha = transparency[palette_index] if transparency is not None and palette_index < len(transparency) else 255
            pixels.append((red, green, blue, alpha))
    elif color_type == 4:
        for index in range(0, len(row), 2):
            gray, alpha = row[index:index + 2]
            pixels.append((gray, gray, gray, alpha))
    elif color_type == 6:
        for index in range(0, len(row), 4):
            red, green, blue, alpha = row[index:index + 4]
            pixels.append((red, green, blue, alpha))
    else:
        raise AssertionError("unsupported color type passed normalization")
    return pixels


def _bucket_channel(value: int) -> int:
    shift = 8 - PALETTE_BUCKET_BITS
    high = value >> shift
    maximum = (1 << PALETTE_BUCKET_BITS) - 1
    return round(high * 255 / maximum)


def analyze_png_bytes(data: bytes) -> dict[str, Any]:
    ihdr, compressed, palette, transparency = _parse_png(data)
    rows, _channels = _inflate_scanlines(ihdr, compressed)

    pixel_count = ihdr["width"] * ihdr["height"]
    visible_count = 0
    opaque_count = 0
    transparent_count = 0
    palette_counts: Counter[tuple[int, int, int]] = Counter()
    channel_sums = [0, 0, 0, 0]
    luminance_sum = 0.0
    luminance_square_sum = 0.0
    luminance_min = 1.0
    luminance_max = 0.0
    horizontal_delta_sum = 0
    horizontal_delta_pairs = 0
    vertical_delta_sum = 0
    vertical_delta_pairs = 0
    previous_pixels: list[tuple[int, int, int, int]] | None = None

    for row in rows:
        pixels = _row_rgba(row, ihdr["color_type"], palette, transparency)
        for index, (red, green, blue, alpha) in enumerate(pixels):
            channel_sums[0] += red
            channel_sums[1] += green
            channel_sums[2] += blue
            channel_sums[3] += alpha
            if alpha == 255:
                opaque_count += 1
            if alpha == 0:
                transparent_count += 1
            if alpha > 0:
                visible_count += 1
                bucket = (_bucket_channel(red), _bucket_channel(green), _bucket_channel(blue))
                palette_counts[bucket] += 1
                luminance = (0.2126 * red + 0.7152 * green + 0.0722 * blue) / 255.0
                luminance_sum += luminance
                luminance_square_sum += luminance * luminance
                luminance_min = min(luminance_min, luminance)
                luminance_max = max(luminance_max, luminance)
            if index > 0:
                prior = pixels[index - 1]
                horizontal_delta_sum += abs(red - prior[0]) + abs(green - prior[1]) + abs(blue - prior[2])
                horizontal_delta_pairs += 1
            if previous_pixels is not None:
                prior = previous_pixels[index]
                vertical_delta_sum += abs(red - prior[0]) + abs(green - prior[1]) + abs(blue - prior[2])
                vertical_delta_pairs += 1
        previous_pixels = pixels

    if visible_count:
        luminance_mean = luminance_sum / visible_count
        variance = max(0.0, luminance_square_sum / visible_count - luminance_mean * luminance_mean)
        luminance_stddev = math.sqrt(variance)
    else:
        luminance_min = 0.0
        luminance_max = 0.0
        luminance_mean = 0.0
        luminance_stddev = 0.0

    top_buckets = []
    for (red, green, blue), count in sorted(palette_counts.items(), key=lambda item: (-item[1], item[0]))[:MAX_PALETTE_ROWS]:
        top_buckets.append({
            "value": f"#{red:02X}{green:02X}{blue:02X}",
            "count": count,
            "visible_fraction": round(count / visible_count, 8) if visible_count else 0.0,
        })

    evidence = {
        "schema": SCREENSHOT_PIXEL_SCHEMA,
        "truth_status": "DETERMINISTIC_DECODED_PNG_PIXEL_FACTS",
        "artifact_digest": _bytes_digest(data),
        "mime_type": "image/png",
        "decoder": {
            "id": "axm-stdlib-png-observer",
            "version": "0.1",
            "third_party_dependency": False,
            "supported_contract": "8-bit non-interlaced PNG color types 0,2,3,4,6",
        },
        "image": {
            "width": ihdr["width"],
            "height": ihdr["height"],
            "pixel_count": pixel_count,
            "visible_pixel_count": visible_count,
            "bit_depth": ihdr["bit_depth"],
            "color_type": ihdr["color_type"],
            "interlace": ihdr["interlace"],
        },
        "palette": {
            "quantization_bits_per_rgb_channel": PALETTE_BUCKET_BITS,
            "top_buckets": top_buckets,
        },
        "channels": {
            "mean": {
                "r": round(channel_sums[0] / pixel_count, 6),
                "g": round(channel_sums[1] / pixel_count, 6),
                "b": round(channel_sums[2] / pixel_count, 6),
                "a": round(channel_sums[3] / pixel_count, 6),
            }
        },
        "alpha": {
            "opaque_fraction": round(opaque_count / pixel_count, 8),
            "transparent_fraction": round(transparent_count / pixel_count, 8),
        },
        "luminance": {
            "basis": "visible RGB pixels using Rec.709 coefficients on encoded 8-bit channels",
            "minimum": round(luminance_min, 8),
            "maximum": round(luminance_max, 8),
            "mean": round(luminance_mean, 8),
            "stddev": round(luminance_stddev, 8),
        },
        "spatial": {
            "horizontal_neighbor_rgb_l1_delta_mean": round(horizontal_delta_sum / horizontal_delta_pairs, 6) if horizontal_delta_pairs else 0.0,
            "vertical_neighbor_rgb_l1_delta_mean": round(vertical_delta_sum / vertical_delta_pairs, 6) if vertical_delta_pairs else 0.0,
        },
        "claim_boundary": {
            "semantic_roles_inferred": False,
            "layout_quality_judged": False,
            "visual_hierarchy_judged": False,
            "aesthetic_quality_judged": False,
            "originality_judged": False,
        },
    }
    evidence["evidence_digest"] = _digest(evidence)
    return evidence


def validate_screenshot_pixel_evidence(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SCREENSHOT_PIXEL_SCHEMA:
        raise DesignVisualError("screenshot pixel evidence schema is unsupported")
    expected_digest = raw.get("evidence_digest")
    if not isinstance(expected_digest, str):
        raise DesignVisualError("screenshot pixel evidence is missing evidence_digest")
    normalized = json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    supplied = normalized.pop("evidence_digest", None)
    actual = _digest(normalized)
    if supplied != actual:
        raise DesignVisualError(
            "screenshot pixel evidence digest does not match its contents",
            {"supplied": supplied, "actual": actual},
        )
    image = normalized.get("image")
    if not isinstance(image, dict):
        raise DesignVisualError("screenshot pixel evidence image metadata is invalid")
    for key in ("width", "height", "pixel_count", "visible_pixel_count"):
        value = image.get(key)
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            raise DesignVisualError(f"screenshot pixel evidence image.{key} is invalid")
    if image["width"] < 1 or image["height"] < 1 or image["width"] * image["height"] != image["pixel_count"]:
        raise DesignVisualError("screenshot pixel evidence dimensions do not match pixel_count")
    claim_boundary = normalized.get("claim_boundary")
    required_false = {
        "semantic_roles_inferred",
        "layout_quality_judged",
        "visual_hierarchy_judged",
        "aesthetic_quality_judged",
        "originality_judged",
    }
    if not isinstance(claim_boundary, dict) or any(claim_boundary.get(key) is not False for key in required_false):
        raise DesignVisualError("screenshot pixel evidence exceeds the allowed claim boundary")
    normalized["evidence_digest"] = actual
    return normalized


def observe_screenshot_style(target: Path) -> dict[str, Any]:
    target = Path(target).resolve()
    if not target.is_file() or target.suffix.casefold() != ".png":
        raise DesignVisualError("visual observer target must be a local .png screenshot", {"path": str(target)})
    data = target.read_bytes()
    evidence = analyze_png_bytes(data)
    colors = [
        {"value": row["value"], "count": row["count"]}
        for row in evidence["palette"]["top_buckets"]
    ]
    observation = {
        "schema": SCREENSHOT_OBSERVATION_SCHEMA,
        "truth_status": "OBSERVED_LOCAL_SCREENSHOT_PIXEL_SIGNALS",
        "source": {
            "kind": "local-png-screenshot",
            "path": str(target),
            "file_count": 1,
            "files": [{
                "path": target.name,
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }],
        },
        "signals": {
            "colors": colors,
            "lengths": [],
            "radii": [],
            "durations": [],
            "font_families": [],
            "material_signals": [],
            "breakpoints": [],
            "custom_properties": [],
            "component_selector_signals": [],
            "html_tags": [],
            "interactive_html_tag_count": 0,
            "aria_attribute_count": 0,
            "visual_pixel_facts": evidence,
        },
        "limitations": [
            "the observer decodes bounded local PNG pixels only; it does not identify semantic components or text",
            "palette colors are deterministic 4-bit-per-channel buckets and are not semantic design-token roles",
            "pixel statistics do not prove spacing quality, visual hierarchy, component coherence, beauty, originality, accessibility, or intent",
            "no aesthetic preference is promoted to an automatic truth claim",
        ],
    }
    observation["observation_digest"] = _digest(observation)
    return observation


def _screenshot_observation(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != SCREENSHOT_OBSERVATION_SCHEMA:
        raise DesignVisualError("derive-screenshot-genome requires an axm.design-screenshot-observation/v0.1 observation")
    signals = raw.get("signals")
    if not isinstance(signals, dict) or not isinstance(signals.get("visual_pixel_facts"), dict):
        raise DesignVisualError("screenshot observation is missing pixel facts")
    validate_screenshot_pixel_evidence(signals["visual_pixel_facts"])
    return json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))


def derive_screenshot_genome(
    observation_raw: Any,
    genome_id: Any,
    version: Any,
    purpose: Any,
) -> dict[str, Any]:
    observation = _screenshot_observation(observation_raw)
    adapted = {
        "schema": DESIGN_OBSERVATION_SCHEMA,
        "truth_status": observation["truth_status"],
        "source": observation.get("source", {}),
        "signals": observation["signals"],
        "limitations": observation.get("limitations", []),
        "observation_digest": observation.get("observation_digest"),
    }
    derived = derive_design_genome(adapted, genome_id, version, purpose)
    genome = derived["genome"]
    genome["provenance"] = {
        "kind": "derived-local-screenshot-pixel-observation",
        "screenshot_observation_digest": observation.get("observation_digest"),
        "pixel_evidence_digest": observation["signals"]["visual_pixel_facts"].get("evidence_digest"),
        "derivation_method": "deterministic screenshot color-bucket signals normalized through the existing Design Genome derivation path",
        "source_composition_copied": False,
        "semantic_roles_inferred": False,
        "screenshot_pixels_observed": True,
        "visual_quality_observed": False,
        "aesthetic_preference_promoted_to_truth": False,
    }
    genome = validate_design_genome(genome)
    derived["truth_status"] = "DETERMINISTIC_DESIGN_GENOME_DERIVED_FROM_SCREENSHOT_PIXEL_SIGNALS"
    derived["genome"] = genome
    derived["coverage"]["screenshot_pixel_observation"] = 1
    derived["gaps"] = [
        "screenshot pixels expose color and coarse image statistics but not semantic component roles",
        "spacing, hierarchy, component coherence, beauty, originality, accessibility, and intent remain unproven",
        "quality gates remain AXM policy rather than reference-screenshot preference",
    ]
    return derived


def _viewport(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not {"id", "width", "height"}.issubset(raw) or set(raw) - {"id", "width", "height", "device_pixel_ratio"}:
        raise DesignVisualError("viewport must use id, width, height, and optional device_pixel_ratio")
    viewport_id = _text(raw["id"], "viewport.id", 128)
    for key in ("width", "height"):
        value = raw[key]
        if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= 100_000:
            raise DesignVisualError(f"viewport.{key} must be an integer between 1 and 100000")
    ratio = raw.get("device_pixel_ratio", 1)
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not math.isfinite(float(ratio)) or not 0.1 <= float(ratio) <= 32:
        raise DesignVisualError("viewport.device_pixel_ratio must be between 0.1 and 32")
    return {
        "id": viewport_id,
        "width": raw["width"],
        "height": raw["height"],
        "device_pixel_ratio": float(ratio),
    }


def observe_render_screenshot(plan_digest: Any, viewport_raw: Any, target: Path) -> dict[str, Any]:
    viewport = _viewport(viewport_raw)
    target = Path(target).resolve()
    if not target.is_file() or target.suffix.casefold() != ".png":
        raise DesignVisualError("render screenshot target must be a local .png file", {"path": str(target)})
    data = target.read_bytes()
    pixel_evidence = analyze_png_bytes(data)
    image = pixel_evidence["image"]
    expected_width = round(viewport["width"] * viewport["device_pixel_ratio"])
    expected_height = round(viewport["height"] * viewport["device_pixel_ratio"])
    dimension_status = "PASS" if image["width"] == expected_width and image["height"] == expected_height else "HOLD"
    dimension_basis = (
        f"decoded PNG dimensions {image['width']}x{image['height']}; expected viewport raster "
        f"{expected_width}x{expected_height} from declared viewport and device pixel ratio"
    )
    evidence_bytes = _canonical(pixel_evidence)
    observation = record_render_observation(
        plan_digest,
        {
            "kind": "other",
            "id": "axm-stdlib-png-observer",
            "version": "0.1",
            "basis": "deterministic local PNG byte decoding and pixel measurement only; no aesthetic or semantic inference",
        },
        [{
            "viewport": viewport,
            "artifacts": [
                {
                    "kind": "screenshot",
                    "digest": _bytes_digest(data),
                    "uri": str(target),
                    "mime_type": "image/png",
                    "bytes": len(data),
                },
                {
                    "kind": "other",
                    "digest": _bytes_digest(evidence_bytes),
                    "mime_type": "application/vnd.axm.design-screenshot-pixels+json",
                    "bytes": len(evidence_bytes),
                },
            ],
            "measurements": {},
            "assessments": [{
                "id": "pixel-dimension-integrity",
                "status": dimension_status,
                "confidence": 1.0,
                "basis": dimension_basis + "; this assessment is evidence integrity only, not visual quality",
            }],
        }],
    )
    return {
        "truth_status": "LOCAL_SCREENSHOT_PIXEL_EVIDENCE_READY_FOR_EXISTING_RENDER_JUDGE",
        "pixel_evidence": pixel_evidence,
        "observation": observation,
        "judge_usage": {
            "operation": "judge-rendered",
            "observation_field": "observation",
            "default_perceptual_quality_still_required": True,
            "automatic_aesthetic_pass_possible_from_pixel_facts": False,
        },
    }


def design_visual_summary() -> dict[str, Any]:
    return {
        "pixel_schema": SCREENSHOT_PIXEL_SCHEMA,
        "screenshot_observation_schema": SCREENSHOT_OBSERVATION_SCHEMA,
        "operations": ["inspect-visual-observer", "observe-screenshot", "derive-screenshot-genome", "observe-render-screenshot"],
        "input": "bounded local 8-bit non-interlaced PNG screenshot",
        "third_party_python_dependency_required": False,
        "facts": [
            "verified PNG structure and CRC",
            "decoded dimensions and pixel count",
            "quantized color occurrence buckets",
            "channel means and alpha coverage",
            "luminance distribution",
            "horizontal and vertical neighboring RGB delta means",
        ],
        "genome_bridge": "screenshot color buckets enter the existing deterministic Design Genome token derivation path with screenshot-specific provenance",
        "judge_bridge": "render screenshots become ordinary attributed render observations; pixel dimension integrity may be explicitly required, while default perceptual assessments remain separate",
        "semantic_component_inference": False,
        "automatic_aesthetic_judgment": False,
    }


def operate_design_visual(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    supported = set(design_visual_summary()["operations"])
    if operation not in supported:
        raise DesignVisualError("visual observer operation is unsupported", {"operation": operation, "supported_operations": sorted(supported)})
    if operation == "inspect-visual-observer":
        return {"truth_status": "DECLARED_MINIMAL_SCREENSHOT_VISUAL_OBSERVER_V0_1", **design_visual_summary()}
    if operation == "observe-screenshot":
        path = _resolve_path(root, _text(inputs.get("path"), "path", 1000))
        return observe_screenshot_style(path)
    if operation == "derive-screenshot-genome":
        return derive_screenshot_genome(
            inputs.get("observation"),
            inputs.get("genome_id"),
            inputs.get("version", "0.1.0"),
            inputs.get("purpose"),
        )
    if operation == "observe-render-screenshot":
        path = _resolve_path(root, _text(inputs.get("path"), "path", 1000))
        return observe_render_screenshot(inputs.get("plan_digest"), inputs.get("viewport"), path)
    raise AssertionError("unreachable")

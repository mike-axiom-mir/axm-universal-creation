from __future__ import annotations

import hashlib
import json
import struct
import zlib
from pathlib import Path
from typing import Any

from .atomic import atomic_write_bytes


PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
MAX_RASTER_SIDE = 2048
MAX_RASTER_PIXELS = 4_194_304
MAX_SHAPES = 512
MAX_TONES = 128
MAX_AUDIO_MILLISECONDS = 30_000
MAX_REPLACED_FILE_BYTES = 64 * 1024 * 1024


class ProceduralMediaError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def procedural_media_summary() -> dict[str, Any]:
    return {
        "truth_status": "LIVE_DETERMINISTIC_PROCEDURAL_MEDIA_GENERATION",
        "operations": ["png", "wav"],
        "png_grammar": ["background", "rectangle", "circle"],
        "wav_grammar": ["mono-pcm16", "square-tone", "silence"],
        "maximum_raster_side": MAX_RASTER_SIDE,
        "maximum_raster_pixels": MAX_RASTER_PIXELS,
        "maximum_shapes": MAX_SHAPES,
        "maximum_tones": MAX_TONES,
        "maximum_audio_milliseconds": MAX_AUDIO_MILLISECONDS,
        "container_and_payload_reverified_after_publish": True,
        "appearance_or_audio_quality_proven": False,
    }


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
        raise ProceduralMediaError("media specification must be finite JSON data") from exc


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise ProceduralMediaError(f"{label} must be an integer from {minimum} through {maximum}")
    return value


def _object(raw: Any, label: str, *, required: set[str], optional: set[str] | None = None) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise ProceduralMediaError(f"{label} must be an object")
    optional = optional or set()
    missing = sorted(required - set(raw))
    unexpected = sorted(set(raw) - required - optional)
    if missing or unexpected:
        raise ProceduralMediaError(
            f"{label} fields do not match the bounded grammar",
            {"label": label, "missing_fields": missing, "unexpected_fields": unexpected},
        )
    return raw


def _color(value: Any, label: str) -> tuple[str, tuple[int, int, int, int]]:
    if not isinstance(value, str) or len(value) not in {7, 9} or not value.startswith("#"):
        raise ProceduralMediaError(f"{label} must be #RRGGBB or #RRGGBBAA")
    try:
        values = tuple(int(value[index : index + 2], 16) for index in range(1, len(value), 2))
    except ValueError as exc:
        raise ProceduralMediaError(f"{label} must be #RRGGBB or #RRGGBBAA") from exc
    rgba = values if len(values) == 4 else (*values, 255)
    return value.upper(), rgba


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


def _normalize_png_spec(raw: Any) -> dict[str, Any]:
    spec = _object(
        raw,
        "specification",
        required={"width", "height", "background"},
        optional={"shapes"},
    )
    width = _integer(spec["width"], "specification.width", 1, MAX_RASTER_SIDE)
    height = _integer(spec["height"], "specification.height", 1, MAX_RASTER_SIDE)
    if width * height > MAX_RASTER_PIXELS:
        raise ProceduralMediaError(f"PNG raster exceeds the {MAX_RASTER_PIXELS}-pixel boundary")
    background, _ = _color(spec["background"], "specification.background")
    raw_shapes = spec.get("shapes", [])
    if not isinstance(raw_shapes, list) or len(raw_shapes) > MAX_SHAPES:
        raise ProceduralMediaError(f"specification.shapes must contain at most {MAX_SHAPES} entries")
    shapes: list[dict[str, Any]] = []
    for index, raw_shape in enumerate(raw_shapes):
        label = f"specification.shapes[{index}]"
        if not isinstance(raw_shape, dict):
            raise ProceduralMediaError(f"{label} must be an object")
        kind = raw_shape.get("kind")
        if kind == "rectangle":
            shape = _object(
                raw_shape,
                label,
                required={"kind", "x", "y", "width", "height", "color"},
            )
            x = _integer(shape["x"], f"{label}.x", 0, width - 1)
            y = _integer(shape["y"], f"{label}.y", 0, height - 1)
            shape_width = _integer(shape["width"], f"{label}.width", 1, width)
            shape_height = _integer(shape["height"], f"{label}.height", 1, height)
            if x + shape_width > width or y + shape_height > height:
                raise ProceduralMediaError(f"{label} must stay inside the raster")
            color, _ = _color(shape["color"], f"{label}.color")
            shapes.append(
                {
                    "kind": "rectangle",
                    "x": x,
                    "y": y,
                    "width": shape_width,
                    "height": shape_height,
                    "color": color,
                }
            )
        elif kind == "circle":
            shape = _object(raw_shape, label, required={"kind", "cx", "cy", "radius", "color"})
            cx = _integer(shape["cx"], f"{label}.cx", 0, width - 1)
            cy = _integer(shape["cy"], f"{label}.cy", 0, height - 1)
            radius = _integer(shape["radius"], f"{label}.radius", 1, min(width, height))
            if cx - radius < 0 or cy - radius < 0 or cx + radius >= width or cy + radius >= height:
                raise ProceduralMediaError(f"{label} must stay inside the raster")
            color, _ = _color(shape["color"], f"{label}.color")
            shapes.append({"kind": "circle", "cx": cx, "cy": cy, "radius": radius, "color": color})
        else:
            raise ProceduralMediaError(
                f"{label}.kind must be rectangle or circle",
                {"actual_kind": kind},
            )
    return {"width": width, "height": height, "background": background, "shapes": shapes}


def render_png(raw: Any) -> dict[str, Any]:
    spec = _normalize_png_spec(raw)
    _, background = _color(spec["background"], "specification.background")
    width = spec["width"]
    height = spec["height"]
    pixels = bytearray(background * (width * height))

    def paint(x: int, y: int, rgba: tuple[int, int, int, int]) -> None:
        offset = (y * width + x) * 4
        pixels[offset : offset + 4] = bytes(rgba)

    for shape in spec["shapes"]:
        _, rgba = _color(shape["color"], "shape.color")
        if shape["kind"] == "rectangle":
            for y in range(shape["y"], shape["y"] + shape["height"]):
                for x in range(shape["x"], shape["x"] + shape["width"]):
                    paint(x, y, rgba)
        else:
            radius_squared = shape["radius"] * shape["radius"]
            for y in range(shape["cy"] - shape["radius"], shape["cy"] + shape["radius"] + 1):
                dy = y - shape["cy"]
                for x in range(shape["cx"] - shape["radius"], shape["cx"] + shape["radius"] + 1):
                    dx = x - shape["cx"]
                    if dx * dx + dy * dy <= radius_squared:
                        paint(x, y, rgba)

    raw_rows = b"".join(
        b"\x00" + bytes(pixels[y * width * 4 : (y + 1) * width * 4])
        for y in range(height)
    )
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    body = PNG_SIGNATURE + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw_rows, 9)) + _png_chunk(b"IEND", b"")
    return {"operation": "png", "specification": spec, "body": body}


def verify_png(body: bytes) -> dict[str, Any]:
    if not body.startswith(PNG_SIGNATURE):
        raise ProceduralMediaError("generated PNG signature is invalid")
    offset = len(PNG_SIGNATURE)
    chunks: list[tuple[bytes, bytes]] = []
    while offset < len(body):
        if offset + 12 > len(body):
            raise ProceduralMediaError("generated PNG chunk is truncated")
        size = struct.unpack(">I", body[offset : offset + 4])[0]
        kind = body[offset + 4 : offset + 8]
        end = offset + 12 + size
        if end > len(body):
            raise ProceduralMediaError("generated PNG chunk body is truncated")
        data = body[offset + 8 : offset + 8 + size]
        expected_crc = struct.unpack(">I", body[offset + 8 + size : end])[0]
        actual_crc = zlib.crc32(kind + data) & 0xFFFFFFFF
        if expected_crc != actual_crc:
            raise ProceduralMediaError("generated PNG chunk CRC is invalid", {"chunk": kind.decode("ascii", "replace")})
        chunks.append((kind, data))
        offset = end
        if kind == b"IEND":
            break
    if offset != len(body) or not chunks or chunks[0][0] != b"IHDR" or chunks[-1][0] != b"IEND":
        raise ProceduralMediaError("generated PNG chunk ordering is invalid")
    ihdr = chunks[0][1]
    if len(ihdr) != 13:
        raise ProceduralMediaError("generated PNG IHDR is invalid")
    width, height, depth, color_type, compression, filtering, interlace = struct.unpack(">IIBBBBB", ihdr)
    if (depth, color_type, compression, filtering, interlace) != (8, 6, 0, 0, 0):
        raise ProceduralMediaError("generated PNG format is outside the RGBA8 non-interlaced contract")
    compressed = b"".join(data for kind, data in chunks if kind == b"IDAT")
    try:
        raster = zlib.decompress(compressed)
    except zlib.error as exc:
        raise ProceduralMediaError("generated PNG raster cannot be decompressed") from exc
    row_bytes = width * 4 + 1
    if len(raster) != row_bytes * height or any(raster[row * row_bytes] != 0 for row in range(height)):
        raise ProceduralMediaError("generated PNG raster shape or filter is invalid")
    return {
        "format": "png",
        "passed": True,
        "width": width,
        "height": height,
        "pixel_format": "rgba8",
        "decoded_payload_bytes": width * height * 4,
        "chunk_types": [kind.decode("ascii") for kind, _ in chunks],
    }


def _normalize_wav_spec(raw: Any) -> dict[str, Any]:
    spec = _object(raw, "specification", required={"sample_rate", "tones"})
    sample_rate = _integer(spec["sample_rate"], "specification.sample_rate", 8_000, 48_000)
    raw_tones = spec["tones"]
    if not isinstance(raw_tones, list) or not raw_tones or len(raw_tones) > MAX_TONES:
        raise ProceduralMediaError(f"specification.tones must contain 1..{MAX_TONES} entries")
    tones: list[dict[str, int]] = []
    total_ms = 0
    for index, raw_tone in enumerate(raw_tones):
        label = f"specification.tones[{index}]"
        tone = _object(raw_tone, label, required={"frequency_hz", "duration_ms", "amplitude"})
        frequency = _integer(tone["frequency_hz"], f"{label}.frequency_hz", 0, sample_rate // 2)
        duration = _integer(tone["duration_ms"], f"{label}.duration_ms", 1, 5_000)
        amplitude = _integer(tone["amplitude"], f"{label}.amplitude", 0, 32_767)
        total_ms += duration
        tones.append({"frequency_hz": frequency, "duration_ms": duration, "amplitude": amplitude})
    if total_ms > MAX_AUDIO_MILLISECONDS:
        raise ProceduralMediaError(f"WAV duration exceeds the {MAX_AUDIO_MILLISECONDS}-millisecond boundary")
    return {"sample_rate": sample_rate, "tones": tones}


def render_wav(raw: Any) -> dict[str, Any]:
    spec = _normalize_wav_spec(raw)
    sample_rate = spec["sample_rate"]
    pcm = bytearray()
    for tone in spec["tones"]:
        frames = sample_rate * tone["duration_ms"] // 1000
        frequency = tone["frequency_hz"]
        amplitude = tone["amplitude"]
        phase = 0
        for _ in range(frames):
            if frequency == 0 or amplitude == 0:
                sample = 0
            else:
                sample = amplitude if phase * 2 < sample_rate else -amplitude
                phase = (phase + frequency) % sample_rate
            pcm.extend(struct.pack("<h", sample))
    fmt = struct.pack("<HHIIHH", 1, 1, sample_rate, sample_rate * 2, 2, 16)
    riff_size = 4 + (8 + len(fmt)) + (8 + len(pcm))
    body = b"RIFF" + struct.pack("<I", riff_size) + b"WAVEfmt " + struct.pack("<I", len(fmt)) + fmt + b"data" + struct.pack("<I", len(pcm)) + bytes(pcm)
    return {"operation": "wav", "specification": spec, "body": body}


def verify_wav(body: bytes) -> dict[str, Any]:
    if len(body) < 44 or body[:4] != b"RIFF" or body[8:12] != b"WAVE":
        raise ProceduralMediaError("generated WAV signature is invalid")
    if struct.unpack("<I", body[4:8])[0] != len(body) - 8:
        raise ProceduralMediaError("generated WAV RIFF size is invalid")
    if body[12:16] != b"fmt " or struct.unpack("<I", body[16:20])[0] != 16:
        raise ProceduralMediaError("generated WAV fmt chunk is invalid")
    audio_format, channels, sample_rate, byte_rate, block_align, bits = struct.unpack("<HHIIHH", body[20:36])
    if (audio_format, channels, byte_rate, block_align, bits) != (1, 1, sample_rate * 2, 2, 16):
        raise ProceduralMediaError("generated WAV is outside the mono PCM16 contract")
    if body[36:40] != b"data":
        raise ProceduralMediaError("generated WAV data chunk is missing")
    data_bytes = struct.unpack("<I", body[40:44])[0]
    if data_bytes != len(body) - 44 or data_bytes % 2:
        raise ProceduralMediaError("generated WAV payload size is invalid")
    return {
        "format": "wav",
        "passed": True,
        "channels": channels,
        "sample_rate": sample_rate,
        "sample_width_bits": bits,
        "frames": data_bytes // 2,
        "duration_milliseconds_floor": (data_bytes // 2) * 1000 // sample_rate,
    }


def generate_media(operation: Any, specification: Any) -> dict[str, Any]:
    normalized_operation = str(operation).strip().casefold()
    if normalized_operation == "png":
        rendered = render_png(specification)
        validation = verify_png(rendered["body"])
    elif normalized_operation == "wav":
        rendered = render_wav(specification)
        validation = verify_wav(rendered["body"])
    else:
        raise ProceduralMediaError("procedural media operation must be png or wav")
    body = rendered["body"]
    normalized = rendered["specification"]
    return {
        "operation": normalized_operation,
        "specification": normalized,
        "specification_digest": hashlib.sha256(_canonical({"operation": normalized_operation, "specification": normalized})).hexdigest(),
        "body": body,
        "bytes": len(body),
        "sha256": hashlib.sha256(body).hexdigest(),
        "format_validation": validation,
    }


def publish_media_asset(
    target: Path,
    *,
    operation: Any,
    specification: Any,
    replace: bool = False,
) -> dict[str, Any]:
    target = Path(target).resolve()
    generated = generate_media(operation, specification)
    expected_suffix = f".{generated['operation']}"
    if target.suffix.casefold() != expected_suffix:
        raise ProceduralMediaError(f"{generated['operation']} output path must end with {expected_suffix}")
    if target.is_symlink():
        raise ProceduralMediaError("procedural media target cannot be a symlink")
    if target.exists() and not target.is_file():
        raise ProceduralMediaError("procedural media target exists and is not a regular file")
    if target.exists() and not replace:
        raise ProceduralMediaError(f"target asset already exists: {target}")
    previous: bytes | None = None
    if target.exists():
        if target.stat().st_size > MAX_REPLACED_FILE_BYTES:
            raise ProceduralMediaError("existing target exceeds the bounded rollback buffer")
        previous = target.read_bytes()
    target.parent.mkdir(parents=True, exist_ok=True)
    published = False
    try:
        atomic_write_bytes(target, generated["body"])
        published = True
        observed = target.read_bytes()
        observed_digest = hashlib.sha256(observed).hexdigest()
        if observed_digest != generated["sha256"] or observed != generated["body"]:
            raise ProceduralMediaError(
                "procedural media bytes drifted during publication",
                {"expected_sha256": generated["sha256"], "observed_sha256": observed_digest},
            )
        post_validation = verify_png(observed) if generated["operation"] == "png" else verify_wav(observed)
    except Exception:
        if published:
            if previous is None:
                target.unlink(missing_ok=True)
            else:
                atomic_write_bytes(target, previous)
        raise
    return {
        "path": str(target),
        "published": True,
        "creation_status": "VALIDATED_PROCEDURAL_MEDIA_ASSET",
        "operation": generated["operation"],
        "specification": generated["specification"],
        "specification_digest": generated["specification_digest"],
        "bytes": generated["bytes"],
        "sha256": generated["sha256"],
        "format_validation": post_validation,
        "publication_integrity": True,
        "appearance_or_audio_quality_proven": False,
    }

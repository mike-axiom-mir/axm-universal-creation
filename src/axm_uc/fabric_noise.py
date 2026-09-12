"""Local Game Assets donor subset. See DONOR_ABSORPTION.md for provenance.
Modified: extracted only fabric noise and PNG dependencies; no donor imports.
"""
import math, struct, zlib

def _hash2(x: int, y: int, seed: int) -> float:
    n = (x * 0x1F123BB5) ^ (y * 0x5F356495) ^ (seed * 0x6C8E9CF5)
    n ^= n >> 15
    n = (n * 0x2C1B3C6D) & 0xFFFFFFFF
    n ^= n >> 12
    n = (n * 0x297A2D39) & 0xFFFFFFFF
    n ^= n >> 15
    return n / 0xFFFFFFFF

def _smoothstep(t: float) -> float:
    return t * t * (3.0 - 2.0 * t)

def value_noise(x: float, y: float, seed: int) -> float:
    xi, yi = math.floor(x), math.floor(y)
    tx, ty = _smoothstep(x - xi), _smoothstep(y - yi)
    a = _hash2(xi, yi, seed)
    b = _hash2(xi + 1, yi, seed)
    c = _hash2(xi, yi + 1, seed)
    d = _hash2(xi + 1, yi + 1, seed)
    top = a + (b - a) * tx
    bottom = c + (d - c) * tx
    return top + (bottom - top) * ty

def fbm(x: float, y: float, seed: int, octaves: int = 5) -> float:
    total = 0.0
    amplitude = 0.5
    frequency = 1.0
    norm = 0.0
    for octave in range(octaves):
        total += value_noise(x * frequency, y * frequency, seed + octave * 1013) * amplitude
        norm += amplitude
        frequency *= 2.03
        amplitude *= 0.5
    return total / norm if norm else 0.0

def _png_chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)

def png_bytes(width: int, height: int, channels: int, pixels: bytes) -> bytes:
    if channels not in (1, 3, 4):
        raise ValueError("channels must be 1, 3, or 4")
    if len(pixels) != width * height * channels:
        raise ValueError("pixel byte count does not match dimensions")
    color_type = {1: 0, 3: 2, 4: 6}[channels]
    stride = width * channels
    raw = b"".join(b"\x00" + pixels[y * stride:(y + 1) * stride] for y in range(height))
    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", width, height, 8, color_type, 0, 0, 0)
    return signature + _png_chunk(b"IHDR", ihdr) + _png_chunk(b"IDAT", zlib.compress(raw, 9)) + _png_chunk(b"IEND", b"")

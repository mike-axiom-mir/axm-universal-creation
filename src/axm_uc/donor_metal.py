"""Pinned Game Assets field math. See third_party/absorption-v3.json."""
from __future__ import annotations
import math, random
from dataclasses import dataclass
from .fabric_noise import fbm

@dataclass(frozen=True, slots=True)
class PaintedMetalSpec:
    paint_rgb: tuple[int, int, int] = (54, 67, 73)
    metal_rgb: tuple[int, int, int] = (112, 118, 121)
    paint_roughness: float = 0.48
    metal_roughness: float = 0.27
    wear: float = 0.32
    scratches: int = 18
    grain_scale: float = 28.0
    # The original v0.1 defaults are preserved exactly below so existing
    # material proofs do not silently change. More restrained materials can
    # author lower amplitudes explicitly and preserve those choices in receipts.
    height_grain_amplitude: float = 0.11
    height_broad_amplitude: float = 0.05
    height_scratch_depth: float = 0.18
    height_pit_depth: float = 0.12
    pit_wear_strength: float = 0.42
    base_grain_variation: float = 0.16
    roughness_grain_variation: float = 0.10
    normal_strength: float = 4.0


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _u8(value: float) -> int:
    return max(0, min(255, int(round(value * 255.0))))


def _distance_to_segment(px: float, py: float, ax: float, ay: float, bx: float, by: float) -> float:
    vx, vy = bx - ax, by - ay
    wx, wy = px - ax, py - ay
    vv = vx * vx + vy * vy
    if vv <= 1e-12:
        return math.hypot(px - ax, py - ay)
    t = max(0.0, min(1.0, (wx * vx + wy * vy) / vv))
    qx, qy = ax + t * vx, ay + t * vy
    return math.hypot(px - qx, py - qy)


def _scratch_segments(seed: int, count: int) -> list[tuple[float, float, float, float, float]]:
    rng = random.Random(seed ^ 0xA51E7)
    segments = []
    for _ in range(count):
        ax, ay = rng.random(), rng.random()
        angle = rng.uniform(-math.pi, math.pi)
        length = rng.uniform(0.035, 0.24)
        bx = ax + math.cos(angle) * length
        by = ay + math.sin(angle) * length
        width = rng.uniform(0.0008, 0.0045)
        segments.append((ax, ay, bx, by, width))
    return segments


def painted_metal_fields(size: int, seed: int, spec: PaintedMetalSpec = PaintedMetalSpec()) -> dict[str, object]:
    if size < 8:
        raise ValueError("size must be >= 8")
    if spec.normal_strength < 0.0 or not math.isfinite(spec.normal_strength):
        raise ValueError("normal_strength must be finite and non-negative")
    scratches = _scratch_segments(seed, max(0, spec.scratches))
    height = [0.0] * (size * size)
    wear = [0.0] * (size * size)

    for y in range(size):
        v = (y + 0.5) / size
        for x in range(size):
            u = (x + 0.5) / size
            grain = fbm(u * spec.grain_scale, v * spec.grain_scale, seed)
            broad = fbm(u * 5.2, v * 5.2, seed + 701)
            pits = max(0.0, (fbm(u * 54.0, v * 54.0, seed + 1907) - 0.63) * 2.2)
            scratch_mask = 0.0
            for ax, ay, bx, by, width in scratches:
                d = _distance_to_segment(u, v, ax, ay, bx, by)
                if d < width * 2.5:
                    scratch_mask = max(scratch_mask, 1.0 - d / (width * 2.5))
            chip_seed = fbm(u * 15.0, v * 15.0, seed + 2903)
            chip = _clamp01((chip_seed - (0.72 - spec.wear * 0.20)) * 6.5)
            w = _clamp01(
                chip * 0.82
                + scratch_mask * 0.92
                + pits * spec.pit_wear_strength
            )
            idx = y * size + x
            wear[idx] = w
            height[idx] = _clamp01(
                0.54
                + (grain - 0.5) * spec.height_grain_amplitude
                + (broad - 0.5) * spec.height_broad_amplitude
                - scratch_mask * spec.height_scratch_depth
                - pits * spec.height_pit_depth
            )

    base = bytearray()
    rough = bytearray()
    metal = bytearray()
    ao = bytearray()
    height_bytes = bytearray(_u8(v) for v in height)
    normal = bytearray()
    orm = bytearray()
    pr, pg, pb = spec.paint_rgb
    mr, mg, mb = spec.metal_rgb

    for y in range(size):
        for x in range(size):
            idx = y * size + x
            w = wear[idx]
            grain = fbm((x + 0.5) / size * 31.0, (y + 0.5) / size * 31.0, seed + 4201)
            shade = 0.91 + (grain - 0.5) * spec.base_grain_variation
            r = (pr * (1.0 - w) + mr * w) * shade
            g = (pg * (1.0 - w) + mg * w) * shade
            b = (pb * (1.0 - w) + mb * w) * shade
            base.extend((max(0, min(255, round(r))), max(0, min(255, round(g))), max(0, min(255, round(b)))))
            roughness = (
                spec.paint_roughness * (1.0 - w)
                + spec.metal_roughness * w
                + (grain - 0.5) * spec.roughness_grain_variation
            )
            rough.append(_u8(_clamp01(roughness)))
            metal.append(_u8(_clamp01(w)))
            ao_value = _u8(_clamp01(0.82 + height[idx] * 0.18))
            ao.append(ao_value)
            orm.extend((ao_value, rough[-1], metal[-1]))

            left = height[y * size + max(0, x - 1)]
            right = height[y * size + min(size - 1, x + 1)]
            down = height[max(0, y - 1) * size + x]
            up = height[min(size - 1, y + 1) * size + x]
            dx = (right - left) * spec.normal_strength
            dy = (up - down) * spec.normal_strength
            nx, ny, nz = -dx, -dy, 1.0
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
            normal.extend((_u8(nx * inv * 0.5 + 0.5), _u8(ny * inv * 0.5 + 0.5), _u8(nz * inv * 0.5 + 0.5)))

    return {
        "base_color": (3, bytes(base)),
        "roughness": (1, bytes(rough)),
        "metallic": (1, bytes(metal)),
        "height": (1, bytes(height_bytes)),
        "normal": (3, bytes(normal)),
        "ao": (1, bytes(ao)),
        "orm": (3, bytes(orm)),
    }

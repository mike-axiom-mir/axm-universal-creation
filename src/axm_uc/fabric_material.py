#!/usr/bin/env python3
"""AXM woven fabric donor v0.1. Modified: local imports and strict input checks.
See DONOR_ABSORPTION.md for original source and license.
"""
from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path

from .fabric_noise import fbm, png_bytes


@dataclass(frozen=True, slots=True)
class FabricSpec:
    base_rgb: tuple[int, int, int] = (63, 70, 67)
    warp_threads: int = 58
    weft_threads: int = 54
    weave_depth: float = 0.12
    roughness: float = 0.72
    fiber_noise: float = 0.11
    thickness_hint_mm: float = 1.2


def _clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))


def _u8(value: float) -> int:
    return max(0, min(255, int(round(_clamp01(value) * 255.0))))


def _sha(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def fabric_fields(size: int, seed: int, spec: FabricSpec = FabricSpec()) -> dict[str, tuple[int, bytes]]:
    if isinstance(size, bool) or not isinstance(size, int) or not 16 <= size <= 1024:
        raise ValueError('size must be an integer from 16 to 1024')
    if isinstance(seed, bool) or not isinstance(seed, int) or not 0 <= seed <= 2147483647:
        raise ValueError('seed must be an integer from 0 to 2147483647')
    if not isinstance(spec, FabricSpec):
        raise ValueError('spec must be FabricSpec')
    if len(spec.base_rgb) != 3 or any(type(v) is not int or not 0 <= v <= 255 for v in spec.base_rgb):
        raise ValueError('base_rgb must contain three byte integers')
    for value in (spec.warp_threads, spec.weft_threads):
        if type(value) is not int or not 2 <= value <= 512:
            raise ValueError('thread counts must be integers from 2 to 512')
    for value in (spec.weave_depth, spec.roughness, spec.fiber_noise):
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or not 0 <= value <= 1:
            raise ValueError('material strengths must be finite values from 0 to 1')
    if isinstance(spec.thickness_hint_mm,bool) or not isinstance(spec.thickness_hint_mm,(int,float)) or not math.isfinite(spec.thickness_hint_mm) or not 0 < spec.thickness_hint_mm <= 100:
        raise ValueError('thickness hint must be finite and positive, at most 100 mm')
    if size < 16:
        raise ValueError("fabric texture size must be >=16")
    if spec.warp_threads < 2 or spec.weft_threads < 2:
        raise ValueError("fabric weave needs at least two warp/weft threads")
    height = [0.0] * (size * size)
    base = bytearray()
    rough = bytearray()
    ao = bytearray()
    thickness = bytearray()
    orm = bytearray()
    br, bg, bb = spec.base_rgb

    for y in range(size):
        v = (y + 0.5) / size
        for x in range(size):
            u = (x + 0.5) / size
            warp_phase = u * spec.warp_threads * math.pi
            weft_phase = v * spec.weft_threads * math.pi
            warp = 0.5 + 0.5 * math.cos(warp_phase)
            weft = 0.5 + 0.5 * math.cos(weft_phase)
            cell_x = int(u * spec.warp_threads)
            cell_y = int(v * spec.weft_threads)
            over = (cell_x + cell_y) & 1
            # Plain-weave signal: one thread family rises while the other passes below.
            weave = warp * (0.62 if over else 0.34) + weft * (0.34 if over else 0.62)
            fiber = fbm(u * 150.0, v * 150.0, seed + 101, octaves=3)
            macro = fbm(u * 5.0, v * 5.0, seed + 701)
            idx = y * size + x
            height[idx] = _clamp01(0.48 + (weave - 0.5) * spec.weave_depth + (fiber - 0.5) * spec.fiber_noise * 0.28)
            shade = 0.88 + macro * 0.16 + (fiber - 0.5) * 0.07
            tint = (weave - 0.5) * 0.055
            base.extend((
                max(0, min(255, round(br * shade * (1.0 + tint)))),
                max(0, min(255, round(bg * shade * (1.0 + tint * 0.8)))),
                max(0, min(255, round(bb * shade * (1.0 - tint * 0.5)))),
            ))
            roughness = spec.roughness + (fiber - 0.5) * 0.10 - (weave - 0.5) * 0.035
            rough_byte = _u8(roughness)
            rough.append(rough_byte)
            ao_value = _u8(0.84 + height[idx] * 0.15)
            ao.append(ao_value)
            thickness_value = _u8(_clamp01(0.62 + (macro - 0.5) * 0.14))
            thickness.append(thickness_value)
            orm.extend((ao_value, rough_byte, 0))

    normal = bytearray()
    height_bytes = bytearray(_u8(value) for value in height)
    for y in range(size):
        for x in range(size):
            left = height[y * size + max(0, x - 1)]
            right = height[y * size + min(size - 1, x + 1)]
            down = height[max(0, y - 1) * size + x]
            up = height[min(size - 1, y + 1) * size + x]
            dx = (right - left) * 5.5
            dy = (up - down) * 5.5
            nx, ny, nz = -dx, -dy, 1.0
            inv = 1.0 / math.sqrt(nx * nx + ny * ny + nz * nz)
            normal.extend((_u8(nx * inv * 0.5 + 0.5), _u8(ny * inv * 0.5 + 0.5), _u8(nz * inv * 0.5 + 0.5)))

    return {
        "base_color": (3, bytes(base)),
        "roughness": (1, bytes(rough)),
        "height": (1, bytes(height_bytes)),
        "normal": (3, bytes(normal)),
        "ao": (1, bytes(ao)),
        "thickness": (1, bytes(thickness)),
        "orm": (3, bytes(orm)),
    }


def fabric_request(path, size=256, seed=1, spec=FabricSpec()):
    """Build a request for UC's existing transactional mixed-media project path."""
    import base64
    from dataclasses import asdict
    fields=fabric_fields(size,seed,spec)
    binaries={};maps={}
    for name,(channels,pixels) in fields.items():
        data=png_bytes(size,size,channels,pixels);filename=name+'.png'
        digest=hashlib.sha256(data).hexdigest()
        binaries[filename]={'encoding':'base64','content':base64.b64encode(data).decode(),
                           'media_type':'image/png','sha256':digest}
        maps[name]={'file':filename,'channels':channels,'sha256':digest}
    manifest={'schema':'axm.uc.fabric-material/v0.1','size':size,'seed':seed,'spec':asdict(spec),'maps':maps,
              'donor_commit':'d6a930251e4a99f1f98365b8d01fc968025b1fd9',
              'truth':'Procedural authored maps; not measured cloth or renderer-certified material.',
              'orm_channels':['ambient-occlusion','roughness','metallic'],
              'thickness':'Normalized artistic proxy; not measured millimetres.'}
    html='<!doctype html><html lang="en"><meta charset="utf-8"><title>Woven fabric maps</title><style>body{font:16px system-ui;background:#14202b;color:#eee}main{display:flex;flex-wrap:wrap}figure{margin:16px}img{width:256px;max-width:80vw;image-rendering:pixelated}</style><h1>Woven fabric maps</h1><p>Procedural maps · not a shaded cloth preview</p><main>'
    for name in maps:html+='<figure><img src="'+name+'.png" alt="'+name+'"><figcaption>'+name+'</figcaption></figure>'
    html+='</main></html>'
    return {'kind':'mixed-media-project','direction':'generate standalone woven fabric material maps',
            'inputs':{'path':str(path),'project_type':'static-web','text_files':{'index.html':html,'fabric-material.json':json.dumps(manifest,indent=2)},
                      'binary_files':binaries,'checks':[{'type':'media-signature','path':k,'format':'png'} for k in binaries]}}

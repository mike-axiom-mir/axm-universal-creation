"""Validated standalone adapters for pinned Game Assets and FrameState functions."""
from __future__ import annotations

import base64
import hashlib
import html
import io
import json
import math
import wave
from dataclasses import asdict

from .donor_audio import decode_wav_bytes
from .donor_bitmap import FONT, bitmap_text
from .donor_metal import PaintedMetalSpec, painted_metal_fields
from .fabric_noise import png_bytes


def _integer(value, name, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f'{name} must be an integer from {low} to {high}')


def _number(value, name, low, high):
    if type(value) not in (int, float) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f'{name} must be finite and from {low} to {high}')


def _rgb(value, name):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError(f'{name} must contain three byte integers')
    for v in value:
        _integer(v, name, 0, 255)


def _project(path, title, files, manifest):
    """Return the existing transactional UC request; never write directly."""
    binaries, items = {}, []
    for name, (mime, data) in files.items():
        binaries[name] = {'encoding': 'base64', 'content': base64.b64encode(data).decode(),
                          'media_type': mime, 'sha256': hashlib.sha256(data).hexdigest()}
        label = html.escape(name)
        if mime == 'image/png':
            items.append(f'<figure><img src="{label}" alt="{label}"><figcaption>{label}</figcaption></figure>')
        else:
            items.append(f'<figure><audio controls src="{label}"></audio><figcaption>{label}</figcaption></figure>')
    manifest = dict(manifest, files={k: {'sha256': v['sha256'], 'media_type': v['media_type']} for k,v in binaries.items()})
    page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>{html.escape(title)}</title><style>body{{font:16px system-ui;background:#14202b;color:#eee;padding:20px}}'
            'main{display:flex;flex-wrap:wrap;gap:20px}figure{margin:0}img{max-width:90vw;image-rendering:pixelated}'
            'figcaption{margin:10px 0}p{max-width:75ch;line-height:1.5}</style>'
            f'<h1>{html.escape(title)}</h1><p>{html.escape(manifest["truth"])}</p><main>'+''.join(items)+'</main></html>')
    return {'kind': 'mixed-media-project', 'direction': title,
            'inputs': {'path': str(path), 'project_type': 'static-web',
                       'text_files': {'index.html': page, 'media.json': json.dumps(manifest, indent=2)},
                       'binary_files': binaries,
                       'checks': [{'type':'media-signature', 'path':k, 'format':'png' if v['media_type']=='image/png' else 'wav'} for k,v in binaries.items()]}}


def metal_fields(size=128, seed=1, spec=PaintedMetalSpec()):
    _integer(size, 'size', 16, 512)
    _integer(seed, 'seed', 0, 2147483647)
    if not isinstance(spec, PaintedMetalSpec):
        raise ValueError('spec must be PaintedMetalSpec')
    _rgb(spec.paint_rgb, 'paint_rgb'); _rgb(spec.metal_rgb, 'metal_rgb')
    _integer(spec.scratches, 'scratches', 0, 128)
    for name, value in asdict(spec).items():
        if name in ('paint_rgb', 'metal_rgb', 'scratches'):
            continue
        _number(value, name, 0.1 if name == 'grain_scale' else 0,
                256 if name == 'grain_scale' else 32 if name == 'normal_strength' else 1)
    return painted_metal_fields(size, seed, spec)


def metal_request(path, size=128, seed=1, spec=PaintedMetalSpec()):
    fields = metal_fields(size, seed, spec)
    files = {name+'.png': ('image/png', png_bytes(size, size, channels, pixels))
             for name, (channels, pixels) in fields.items()}
    return _project(path, 'Painted metal maps', files,
                    {'schema':'axm.uc.painted-metal/v0.1', 'size':size, 'seed':seed, 'spec':asdict(spec),
                     'orm_channels':['ambient-occlusion','roughness','metallic'],
                     'normal_convention':'RGB signed XYZ encoded to bytes; image Y increases downward',
                     'truth':'Procedural authored material maps, not a measured scan or a shaded preview. Tiling and engine lighting are not verified.'})


def label_request(path, text, scale=4, color=(120, 230, 255), padding=4):
    if not isinstance(text, str) or not text.strip() or len(text) > 1024:
        raise ValueError('text must contain 1..1024 characters and not be blank')
    _integer(scale, 'scale', 1, 16); _integer(padding, 'padding', 0, 64); _rgb(color, 'color')
    # Validate expanded uppercase text before allocating the donor pixel list.
    upper = text.upper(); lines = upper.split('\n')
    width = max(1, max((6*len(line)-1)*scale if line else 0 for line in lines)+2*padding)
    height = len(lines)*7*scale + (len(lines)-1)*scale + 2*padding
    if width > 4096 or height > 4096 or width*height > 1048576:
        raise ValueError('label must fit 4096 pixels per side and 1,048,576 total pixels')
    w,h,pixels,evidence = bitmap_text(text, scale, color, padding=padding)
    return _project(path, 'Bitmap interface label', {'label.png': ('image/png', png_bytes(w,h,4,pixels))},
                    {'schema':'axm.uc.bitmap-label/v0.1','text':text,'size':[w,h], 'scale':scale,
                     'unsupported_glyphs':sorted(set(upper)-set(FONT)-{'\n'}), 'render':evidence,
                     'truth':'Native uppercase 5×7 bitmap text with transparent background. Unsupported glyphs become visible boxes; this is not Unicode font shaping.'})


def normalize_wav(data, rate=48000, channels=1):
    """Normalize PCM WAV with explicit cheap bounds before donor allocation."""
    if not isinstance(data, bytes) or not 12 <= len(data) <= 16*1024*1024:
        raise ValueError('WAV input must be bytes, from 12 bytes to 16 MiB')
    _integer(rate, 'rate', 8000, 96000); _integer(channels, 'channels', 1, 2)
    try:
        with wave.open(io.BytesIO(data), 'rb') as wf:
            frames = wf.getnframes(); source_rate = wf.getframerate()
            if wf.getnchannels() > 8 or wf.getsampwidth() not in (1,2,3,4) or source_rate < 1:
                raise ValueError('WAV must be 1..8 channel integer PCM with 8/16/24/32-bit samples')
            if frames < 1 or frames > 1048576 or max(1,frames*rate//source_rate) > 1048576:
                raise ValueError('source and output must contain 1..1,048,576 frames')
    except (wave.Error, EOFError) as exc:
        raise ValueError('invalid PCM WAV container') from exc
    pcm,evidence = decode_wav_bytes(data, rate, channels)
    out = io.BytesIO()
    with wave.open(out, 'wb') as wf:
        wf.setnchannels(channels); wf.setsampwidth(2); wf.setframerate(rate); wf.writeframes(pcm)
    return out.getvalue(), evidence


def wav_request(path, data, rate=48000, channels=1):
    body,evidence = normalize_wav(data, rate, channels)
    return _project(path, 'Normalized PCM audio', {'audio.wav': ('audio/wav', body)},
                    {'schema':'axm.uc.normalized-wav/v0.1', 'source_sha256':hashlib.sha256(data).hexdigest(),
                     'conversion':evidence,
                     'truth':'16-bit PCM conversion with nearest-sample resampling. Mono averages source channels; stereo uses the first two or duplicates mono. This does not improve audio fidelity.'})

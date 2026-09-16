"""Bounded native PNG texture sets, glTF bindings and inspection sampling.

No image library, network, GPU or Blender dependency. Supports the explicit UC
8-bit RGB PNG subset, not an arbitrary image decoder or material importer.
"""
from __future__ import annotations

import base64
import hashlib
import math
import struct
import zlib

from .fabric_noise import png_bytes

MAX_SIDE = 2048
MAX_PNG_BYTES = 16 * 1024 * 1024
MAX_TEXTURE_BYTES = 64 * 1024 * 1024
SLOTS = ("base_color", "normal", "orm")
SRGB = tuple(v / 255 / 12.92 if v / 255 <= .04045 else ((v / 255 + .055) / 1.055) ** 2.4 for v in range(256))


def srgb_byte(value):
    value = max(0.0, min(1.0, value))
    return round(255 * (12.92 * value if value <= .0031308 else 1.055 * value ** (1 / 2.4) - .055))


def decode_png(data):
    if not isinstance(data, bytes) or not 45 <= len(data) <= MAX_PNG_BYTES or data[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError("native textures require bounded PNG bytes")
    cursor, chunks, compressed = 8, [], bytearray()
    size = None
    while cursor + 12 <= len(data):
        length = struct.unpack_from(">I", data, cursor)[0]
        kind = data[cursor + 4:cursor + 8]
        end = cursor + 8 + length
        if end + 4 > len(data) or kind not in (b"IHDR", b"IDAT", b"IEND"):
            raise ValueError("unsupported/truncated native PNG chunk")
        payload = data[cursor + 8:end]
        if zlib.crc32(kind + payload) & 0xffffffff != struct.unpack_from(">I", data, end)[0]:
            raise ValueError("native PNG CRC mismatch")
        if kind == b"IHDR":
            if chunks or length != 13:
                raise ValueError("invalid PNG header order")
            w, h, bits, color, compression, filtering, interlace = struct.unpack(">IIBBBBB", payload)
            if not 1 <= w <= MAX_SIDE or not 1 <= h <= MAX_SIDE or (bits, color, compression, filtering, interlace) != (8, 2, 0, 0, 0):
                raise ValueError("native textures require 8-bit RGB noninterlaced PNG, at most 2048 square")
            size = w, h
        elif kind == b"IDAT":
            compressed.extend(payload)
        elif length:
            raise ValueError("invalid PNG end")
        chunks.append(kind)
        cursor = end + 4
    if (cursor != len(data) or len(chunks) < 3 or chunks[0] != b"IHDR" or chunks[-1] != b"IEND"
            or any(k != b"IDAT" for k in chunks[1:-1]) or size is None):
        raise ValueError("invalid native PNG sequence")
    w, h = size
    expected = h * (w * 3 + 1)
    decoder = zlib.decompressobj()
    raw = decoder.decompress(compressed, expected + 1)
    if len(raw) != expected or not decoder.eof or decoder.unused_data:
        raise ValueError("invalid or oversized PNG scanlines")
    stride = w * 3
    pixels = bytearray(stride * h)
    for y in range(h):
        offset, dest = y * (stride + 1), y * stride
        kind = raw[offset]
        if kind > 4:
            raise ValueError("unsupported PNG scanline filter")
        for x in range(stride):
            a = pixels[dest + x - 3] if x >= 3 else 0
            b = pixels[dest + x - stride] if y else 0
            c = pixels[dest + x - stride - 3] if y and x >= 3 else 0
            if kind == 4:
                p = a + b - c
                da, db, dc = abs(p-a), abs(p-b), abs(p-c)
                prediction = a if da <= db and da <= dc else b if db <= dc else c
            else:
                prediction = (0, a, b, (a+b)//2)[kind]
            pixels[dest+x] = (raw[offset+1+x] + prediction) & 255
    return w, h, bytes(pixels)


def normalize_texture_set(raw):
    required = {*SLOTS, "normal_convention", "wrap"}
    if not isinstance(raw, dict) or set(raw) != required:
        raise ValueError("texture set requires base_color, normal, orm, normal_convention and wrap")
    if raw["normal_convention"] != "tangent +Y" or raw["wrap"] not in ("clamp", "repeat"):
        raise ValueError("native texture sets require explicit tangent +Y and clamp/repeat wrap")
    result, dimensions, decoded_bytes = {}, None, 0
    for name in SLOTS:
        encoded = raw[name]
        if not isinstance(encoded, str) or len(encoded) > MAX_PNG_BYTES * 4 // 3 + 4:
            raise ValueError("texture payload exceeds bounds")
        try:
            payload = base64.b64decode(encoded, validate=True)
        except (ValueError, TypeError) as exc:
            raise ValueError("texture payload must be base64 PNG") from exc
        w, h, pixels = decode_png(payload)
        decoded_bytes += len(pixels)
        if dimensions is not None and dimensions != (w, h):
            raise ValueError("texture set dimensions differ")
        dimensions = w, h
        result[name] = base64.b64encode(payload).decode("ascii")
    if decoded_bytes > MAX_TEXTURE_BYTES:
        raise ValueError("decoded texture set exceeds 64 MiB")
    return {**result, "normal_convention": "tangent +Y", "wrap": raw["wrap"]}


def texture_set_from_bundle(bundle, *, wrap="clamp"):
    result = {name: bundle["pngs"][name] for name in SLOTS}
    if bundle["normal_convention"] == "tangent -Y":
        w, h, pixels = decode_png(result["normal"])
        pixels = bytearray(pixels)
        pixels[1::3] = bytes(255-v for v in pixels[1::3])
        result["normal"] = png_bytes(w, h, 3, bytes(pixels))
    return {**{name: base64.b64encode(data).decode("ascii") for name, data in result.items()},
            "normal_convention": "tangent +Y", "wrap": wrap}


def embed_texture_set(raw, document_parts, append_buffer):
    """Embed image bytes once and share the ORM texture across its core slots."""
    images, textures, samplers, seen = document_parts
    wrap = 33071 if raw["wrap"] == "clamp" else 10497
    sampler = {"magFilter": 9729, "minFilter": 9987, "wrapS": wrap, "wrapT": wrap}
    if sampler not in samplers:
        samplers.append(sampler)
    sampler_id = samplers.index(sampler)
    refs = {}
    for slot in SLOTS:
        data = base64.b64decode(raw[slot], validate=True)
        identity = hashlib.sha256(data).hexdigest(), sampler_id
        if identity not in seen:
            image_id = len(images)
            images.append({"mimeType": "image/png", "bufferView": append_buffer(data, target=None)})
            seen[identity] = len(textures)
            textures.append({"source": image_id, "sampler": sampler_id})
        refs[slot] = {"index": seen[identity], "texCoord": 0}
    return refs


def _index(rows, ref, label):
    if not isinstance(rows, list) or type(ref) is not int or not 0 <= ref < len(rows):
        raise ValueError("invalid native texture " + label)
    return rows[ref]


def material_textures(document, binary, material, *, cache=None, build_mips=True):
    """Read the supported core slots from exact embedded bytes; reject gaps."""
    cache = {} if cache is None else cache
    pbr = material.get("pbrMetallicRoughness", {})
    infos = {"base_color": pbr.get("baseColorTexture"), "orm": pbr.get("metallicRoughnessTexture"),
             "normal": material.get("normalTexture"), "ao": material.get("occlusionTexture")}
    result = {}
    for name, info in infos.items():
        if info is None:
            continue
        if not isinstance(info, dict) or info.get("extensions") or info.get("texCoord", 0) != 0:
            raise ValueError("texture inspection requires core TEXCOORD_0 without transforms")
        texture = _index(document.get("textures"), info.get("index"), "reference")
        if texture.get("extensions"):
            raise ValueError("extended textures require their own decoder")
        image = _index(document.get("images"), texture.get("source"), "image")
        if image.get("mimeType") != "image/png" or "uri" in image or image.get("extensions"):
            raise ValueError("native texture inspection requires embedded RGB PNG")
        view = _index(document.get("bufferViews"), image.get("bufferView"), "image bufferView")
        start, length = view.get("byteOffset", 0), view.get("byteLength")
        if (view.get("buffer") != 0 or view.get("extensions") or type(start) is not int or type(length) is not int
                or start < 0 or length <= 0 or start + length > len(binary)):
            raise ValueError("texture image exceeds embedded buffer")
        sampler = _index(document.get("samplers"), texture["sampler"], "sampler") if "sampler" in texture else {}
        wrap_s, wrap_t = sampler.get("wrapS", 10497), sampler.get("wrapT", 10497)
        if sampler.get("extensions") or wrap_s not in (33071, 10497) or wrap_t not in (33071, 10497):
            raise ValueError("native preview supports clamp/repeat texture wrapping")
        # Respect supported filtering declarations instead of ignoring them.
        if sampler.get("magFilter", 9729) != 9729 or sampler.get("minFilter", 9987) not in (9729, 9987):
            raise ValueError("native preview supports linear/trilinear texture filtering")
        key = (image["bufferView"], name == "base_color", name == "normal")
        if key not in cache:
            decoded = decode_png(binary[start:start+length])
            if sum(t.width * t.height * 3 for t in cache.values()) + len(decoded[2]) > MAX_TEXTURE_BYTES:
                raise ValueError("preview decoded texture budget exceeded")
            cache[key] = Texture(decoded, srgb=name == "base_color", normal=name == "normal", mipmaps=build_mips)
        result[name] = {"texture": cache[key], "wrap_s": wrap_s, "wrap_t": wrap_t,
                        "mipmaps": sampler.get("minFilter", 9987) == 9987,
                        "scale": info.get("scale", 1), "strength": info.get("strength", 1)}
        for param in ("scale", "strength"):
            value = result[name][param]
            if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("native texture scale/strength must be in 0..1")
    if material.get("emissiveTexture"):
        raise ValueError("emissive texture inspection is not implemented")
    return result


class Texture:
    def __init__(self, decoded, *, srgb=False, normal=False, mipmaps=True):
        self.width, self.height, _ = decoded
        self.srgb = srgb
        self.levels = [decoded]
        w, h, data = decoded
        while mipmaps and (w > 1 or h > 1):
            nw, nh = max(1, w // 2), max(1, h // 2)
            out = bytearray(nw * nh * 3)
            for y in range(nh):
                for x in range(nw):
                    # Area weighting retains the final row/column for odd sizes.
                    left, right, top, bottom = x*w/nw, (x+1)*w/nw, y*h/nh, (y+1)*h/nh
                    weighted = [((yy*w+xx)*3, (min(right,xx+1)-max(left,xx))*(min(bottom,yy+1)-max(top,yy)))
                                for yy in range(math.floor(top), math.ceil(bottom))
                                for xx in range(math.floor(left), math.ceil(right))]
                    area = (right-left)*(bottom-top)
                    rgb = [sum((SRGB[data[i+c]] if srgb else data[i+c]/255)*weight for i,weight in weighted)/area for c in range(3)]
                    if normal:
                        vector = [2*v-1 for v in rgb]
                        length = math.sqrt(sum(v*v for v in vector))
                        rgb = [v/length*.5+.5 for v in vector] if length > 1e-8 else [.5, .5, 1]
                    out[(y*nw+x)*3:(y*nw+x)*3+3] = bytes(srgb_byte(v) if srgb else round(255*v) for v in rgb)
            w, h, data = nw, nh, bytes(out)
            self.levels.append((w, h, data))

    def sample(self, u, v, lod, wrap_s, wrap_t):
        lod = min(len(self.levels)-1, max(0, lod))
        low, high = math.floor(lod), math.ceil(lod)
        def at(level):
            w, h, data = self.levels[level]
            x, y = u*w-.5, v*h-.5
            ix, iy = math.floor(x), math.floor(y)
            tx, ty = x-ix, y-iy
            result = [0.0, 0.0, 0.0]
            for dy, wy in ((0, 1-ty), (1, ty)):
                yy = (iy+dy) % h if wrap_t == 10497 else min(h-1, max(0, iy+dy))
                for dx, wx in ((0, 1-tx), (1, tx)):
                    xx = (ix+dx) % w if wrap_s == 10497 else min(w-1, max(0, ix+dx))
                    index = (yy*w+xx)*3
                    for c in range(3):
                        value = SRGB[data[index+c]] if self.srgb else data[index+c]/255
                        result[c] += value*wx*wy
            return result
        a = at(low)
        if low == high:
            return a
        b = at(high)
        return [x*(high-lod)+y*(lod-low) for x, y in zip(a, b)]

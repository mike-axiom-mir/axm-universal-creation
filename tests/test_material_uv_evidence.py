from __future__ import annotations

import hashlib
import json
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.material_uv_evidence import EVIDENCE_SCHEMA, inspect_material_uv_density


def _chunk(kind: bytes, payload: bytes) -> bytes:
    return struct.pack(">I", len(payload)) + kind + payload + struct.pack(">I", zlib.crc32(kind + payload) & 0xffffffff)


def png(width=4, height=4) -> bytes:
    header = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    rows = b"".join(b"\0" + b"\x80\x80\x80" * width for _ in range(height))
    return b"\x89PNG\r\n\x1a\n" + _chunk(b"IHDR", header) + _chunk(b"IDAT", zlib.compress(rows)) + _chunk(b"IEND", b"")


def fixture(*, uv_scale=1.0, node_scale=None, collapse_uv=False, clamp=False):
    positions = [(0,0,0),(1,0,0),(1,1,0),(0,1,0)]
    uvs = [(0,0),(uv_scale,0),(uv_scale,uv_scale),(0,uv_scale)]
    if collapse_uv:
        uvs = [(0,0)] * 4
    indices = [0,1,2,0,2,3]
    image = png(4,4)
    binary = bytearray()
    views = []

    def append(payload, stride=None):
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(payload)
        row = {"buffer":0,"byteOffset":offset,"byteLength":len(payload)}
        if stride is not None:
            row["byteStride"] = stride
        views.append(row)
        return len(views)-1

    pos_view = append(b"".join(struct.pack("<3f", *p) for p in positions), 12)
    uv_view = append(b"".join(struct.pack("<2f", *uv) for uv in uvs), 8)
    index_view = append(struct.pack("<6H", *indices))
    image_view = append(image)
    node = {"name":"Body","mesh":0}
    if node_scale is not None:
        node["scale"] = list(node_scale)
    sampler = {"wrapS":33071,"wrapT":33071} if clamp else {"wrapS":10497,"wrapT":10497}
    doc = {
        "asset":{"version":"2.0"}, "scene":0, "scenes":[{"nodes":[0]}], "nodes":[node],
        "meshes":[{"primitives":[{"attributes":{"POSITION":0,"TEXCOORD_0":1},"indices":2,"material":0}]}],
        "materials":[{"name":"Panel","pbrMetallicRoughness":{"baseColorTexture":{"index":0}}}],
        "textures":[{"source":0,"sampler":0}], "samplers":[sampler],
        "images":[{"bufferView":image_view,"mimeType":"image/png"}],
        "buffers":[{"byteLength":len(binary)}], "bufferViews":views,
        "accessors":[
            {"bufferView":pos_view,"componentType":5126,"count":4,"type":"VEC3"},
            {"bufferView":uv_view,"componentType":5126,"count":4,"type":"VEC2"},
            {"bufferView":index_view,"componentType":5123,"count":6,"type":"SCALAR"},
        ],
    }
    return doc, bytes(binary)


def encode(doc, binary):
    encoded = json.dumps(doc, separators=(",",":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    body = binary + b"\0" * (-len(binary) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(body))
            + struct.pack("<I4s", len(encoded), b"JSON") + encoded
            + struct.pack("<I4s", len(body), b"BIN\0") + body)


class MaterialUVEvidenceTests(unittest.TestCase):
    def inspect(self, doc=None, binary=None):
        if doc is None:
            doc, binary = fixture()
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "asset.glb"
            raw = encode(doc, binary)
            path.write_bytes(raw)
            result = inspect_material_uv_density(path)
            self.assertEqual(path.read_bytes(), raw)
            self.assertEqual(result["artifact_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(result["schema"], EVIDENCE_SCHEMA)
            return result

    def test_one_metre_square_reports_actual_four_texels_per_metre(self):
        result = self.inspect()
        self.assertEqual(result["status"], "MEASURED")
        self.assertEqual(result["measurements"]["measured_binding_count"], 1)
        row = result["primitives"][0]
        self.assertEqual(row["triangles"], 2)
        self.assertAlmostEqual(row["world_area_m2"], 1.0)
        self.assertAlmostEqual(row["uv_area"], 1.0)
        binding = row["bindings"][0]
        self.assertEqual((binding["slot"], binding["width"], binding["height"]), ("base-color",4,4))
        for key in ("weighted_geometric_mean","p10","p50","p90"):
            self.assertAlmostEqual(binding["texels_per_m"][key], 4.0)
        self.assertAlmostEqual(binding["texels_per_m"]["p90_p10_ratio"], 1.0)

    def test_world_scale_and_uv_scale_change_density_for_the_expected_reason(self):
        result = self.inspect(*fixture(node_scale=(2,2,1)))
        self.assertAlmostEqual(result["primitives"][0]["world_area_m2"], 4.0)
        self.assertAlmostEqual(result["primitives"][0]["bindings"][0]["texels_per_m"]["p50"], 2.0)
        result = self.inspect(*fixture(uv_scale=2.0))
        self.assertAlmostEqual(result["primitives"][0]["bindings"][0]["texels_per_m"]["p50"], 8.0)

    def test_clamped_texture_with_out_of_range_uvs_is_explicit(self):
        result = self.inspect(*fixture(uv_scale=2.0, clamp=True))
        self.assertEqual(result["status"], "MEASURED")
        self.assertIn("UV_OUTSIDE_CLAMP", {row["code"] for row in result["findings"]})

    def test_collapsed_uvs_hold_instead_of_inventing_density(self):
        result = self.inspect(*fixture(collapse_uv=True))
        self.assertEqual(result["status"], "HOLD")
        codes = {row["code"] for row in result["findings"]}
        self.assertIn("UV_COLLAPSE", codes)
        self.assertIn("NO_MEASURABLE_BINDINGS", codes)

    def test_texture_transform_and_alternate_uv_set_hold_without_fake_measurement(self):
        for mutate, code in [
            (lambda d: d["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"].update(extensions={"KHR_texture_transform":{"scale":[2,2]}}), "TEXTURE_TRANSFORM_UNMEASURED"),
            (lambda d: d["materials"][0]["pbrMetallicRoughness"]["baseColorTexture"].update(texCoord=1), "ALTERNATE_UV_SET_UNMEASURED"),
        ]:
            with self.subTest(code=code):
                doc, binary = fixture(); mutate(doc)
                result = self.inspect(doc, binary)
                self.assertEqual(result["status"], "HOLD")
                self.assertIn(code, {row["code"] for row in result["findings"]})

    def test_external_images_are_not_fetched(self):
        doc, binary = fixture()
        doc["images"][0] = {"uri":"https://example.invalid/material.png","mimeType":"image/png"}
        result = self.inspect(doc, binary)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("EXTERNAL_OR_EXTENDED_IMAGE", {row["code"] for row in result["findings"]})

    def test_missing_uv_or_material_does_not_become_a_zero_density_pass(self):
        for mutate, code in [
            (lambda d: d["meshes"][0]["primitives"][0]["attributes"].pop("TEXCOORD_0"), "MISSING_TEXCOORD_0"),
            (lambda d: d["meshes"][0]["primitives"][0].pop("material"), "MISSING_MATERIAL"),
        ]:
            with self.subTest(code=code):
                doc, binary = fixture(); mutate(doc)
                result = self.inspect(doc, binary)
                self.assertEqual(result["status"], "HOLD")
                self.assertIn(code, {row["code"] for row in result["findings"]})

    def test_deformation_is_outside_static_uv_evidence_scope(self):
        doc, binary = fixture(); doc["animations"] = [{}]
        result = self.inspect(doc, binary)
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("DEFORMATION_NOT_REVIEWED", {row["code"] for row in result["findings"]})

    def test_invalid_image_header_cannot_supply_fake_dimensions(self):
        doc, binary = fixture()
        view = doc["images"][0]["bufferView"]
        offset = doc["bufferViews"][view]["byteOffset"]
        binary = bytearray(binary); binary[offset:offset+8] = b"notapng!"
        result = self.inspect(doc, bytes(binary))
        self.assertEqual(result["status"], "HOLD")
        self.assertIn("INVALID_IMAGE", {row["code"] for row in result["findings"]})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
import math
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


def fixture(*, uv_scale=1.0, uv_scale_xy=None, world_size=(1.0, 1.0), image_size=(4, 4),
            node_scale=None, collapse_uv=False, clamp=False, positions=None, indices=None):
    width_m, height_m = world_size
    if positions is None:
        positions = [(0,0,0),(width_m,0,0),(width_m,height_m,0),(0,height_m,0)]
    if uv_scale_xy is None:
        uv_scale_xy = (uv_scale, uv_scale)
    u_scale, v_scale = uv_scale_xy
    uvs = [(0,0),(u_scale,0),(u_scale,v_scale),(0,v_scale)]
    if collapse_uv:
        uvs = [(0,0)] * 4
    if indices is None:
        indices = [0,1,2,0,2,3]
    image = png(*image_size)
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
    index_view = append(struct.pack(f"<{len(indices)}H", *indices))
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
            {"bufferView":index_view,"componentType":5123,"count":len(indices),"type":"SCALAR"},
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


def directional(binding):
    row = binding["directional_texels_per_m"]
    if row["status"] != "MEASURED":
        raise AssertionError(f"directional measurement unexpectedly held: {row}")
    return row


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
        self.assertEqual(result["measurements"]["directional_binding_count"], 1)
        row = result["primitives"][0]
        self.assertEqual(row["triangles"], 2)
        self.assertAlmostEqual(row["world_area_m2"], 1.0)
        self.assertAlmostEqual(row["uv_area"], 1.0)
        binding = row["bindings"][0]
        self.assertEqual((binding["slot"], binding["width"], binding["height"]), ("base-color",4,4))
        for key in ("weighted_geometric_mean","p10","p50","p90"):
            self.assertAlmostEqual(binding["texels_per_m"][key], 4.0)
        self.assertAlmostEqual(binding["texels_per_m"]["p90_p10_ratio"], 1.0)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], 4.0)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], 4.0)
        self.assertAlmostEqual(measured["anisotropy_ratio"]["weighted_geometric_mean"], 1.0)

    def test_world_scale_and_uv_scale_change_density_for_the_expected_reason(self):
        result = self.inspect(*fixture(node_scale=(2,2,1)))
        self.assertAlmostEqual(result["primitives"][0]["world_area_m2"], 4.0)
        binding = result["primitives"][0]["bindings"][0]
        self.assertAlmostEqual(binding["texels_per_m"]["p50"], 2.0)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], 2.0)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], 2.0)
        result = self.inspect(*fixture(uv_scale=2.0))
        binding = result["primitives"][0]["bindings"][0]
        self.assertAlmostEqual(binding["texels_per_m"]["p50"], 8.0)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], 8.0)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], 8.0)

    def test_building_style_metric_aware_square_image_is_directionally_isotropic(self):
        result = self.inspect(*fixture(
            world_size=(1.10, 1.50),
            uv_scale_xy=(352/512, 480/512),
            image_size=(512, 512),
        ))
        binding = result["primitives"][0]["bindings"][0]
        # GLB POSITION/TEXCOORD_0 fixtures are FLOAT32, so decimal dimensions such as
        # 1.10 are intentionally checked within their encoded precision, not as ideal reals.
        self.assertAlmostEqual(binding["texels_per_m"]["weighted_geometric_mean"], 320.0, delta=1e-4)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], 320.0, delta=1e-4)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], 320.0, delta=1e-4)
        self.assertAlmostEqual(measured["anisotropy_ratio"]["weighted_geometric_mean"], 1.0, delta=1e-6)

    def test_aspect_blind_unit_square_exposes_directional_anisotropy_without_changing_scalar_semantics(self):
        result = self.inspect(*fixture(world_size=(1.10, 1.50), image_size=(512, 512)))
        binding = result["primitives"][0]["bindings"][0]
        expected_min = 512 / 1.50
        expected_max = 512 / 1.10
        expected_ratio = 1.50 / 1.10
        expected_scalar = math.sqrt(expected_min * expected_max)
        self.assertAlmostEqual(binding["texels_per_m"]["weighted_geometric_mean"], expected_scalar, delta=1e-4)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], expected_min, delta=1e-4)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], expected_max, delta=1e-4)
        self.assertAlmostEqual(measured["anisotropy_ratio"]["weighted_geometric_mean"], expected_ratio, delta=1e-6)
        self.assertAlmostEqual(
            math.sqrt(measured["principal_min"]["weighted_geometric_mean"]
                      * measured["principal_max"]["weighted_geometric_mean"]),
            binding["texels_per_m"]["weighted_geometric_mean"], delta=1e-6,
        )

    def test_rectangular_image_dimensions_are_applied_per_axis(self):
        result = self.inspect(*fixture(image_size=(8, 4)))
        binding = result["primitives"][0]["bindings"][0]
        self.assertAlmostEqual(binding["texels_per_m"]["weighted_geometric_mean"], math.sqrt(32.0), places=12)
        measured = directional(binding)
        self.assertAlmostEqual(measured["principal_min"]["weighted_geometric_mean"], 4.0, places=12)
        self.assertAlmostEqual(measured["principal_max"]["weighted_geometric_mean"], 8.0, places=12)
        self.assertAlmostEqual(measured["anisotropy_ratio"]["weighted_geometric_mean"], 2.0, places=12)

    def test_directional_density_is_invariant_to_triangle_order_and_rigid_position_transform(self):
        baseline = self.inspect(*fixture(image_size=(8, 4)))
        baseline_binding = baseline["primitives"][0]["bindings"][0]
        baseline_directional = directional(baseline_binding)

        transformed_positions = [
            (3.0, -2.0, 5.0),
            (3.0, -1.0, 5.0),
            (2.0, -1.0, 5.0),
            (2.0, -2.0, 5.0),
        ]
        reordered = self.inspect(*fixture(
            image_size=(8, 4),
            positions=transformed_positions,
            indices=[2,1,0,3,2,0],
        ))
        reordered_binding = reordered["primitives"][0]["bindings"][0]
        reordered_directional = directional(reordered_binding)
        self.assertAlmostEqual(
            reordered_binding["texels_per_m"]["weighted_geometric_mean"],
            baseline_binding["texels_per_m"]["weighted_geometric_mean"], places=12,
        )
        for key in ("principal_min", "principal_max", "anisotropy_ratio"):
            self.assertAlmostEqual(
                reordered_directional[key]["weighted_geometric_mean"],
                baseline_directional[key]["weighted_geometric_mean"], places=12,
            )

    def test_clamped_texture_with_out_of_range_uvs_is_explicit(self):
        result = self.inspect(*fixture(uv_scale=2.0, clamp=True))
        self.assertEqual(result["status"], "MEASURED")
        self.assertIn("UV_OUTSIDE_CLAMP", {row["code"] for row in result["findings"]})

    def test_collapsed_uvs_hold_instead_of_inventing_density(self):
        result = self.inspect(*fixture(collapse_uv=True))
        self.assertEqual(result["status"], "HOLD")
        self.assertEqual(result["measurements"]["directional_binding_count"], 0)
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

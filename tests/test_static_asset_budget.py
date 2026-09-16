from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
import zlib
from pathlib import Path

from axm_uc.static_asset_budget import (
    BUDGET_SCHEMA,
    inspect_static_asset_budget,
    validate_static_asset_budget,
)


def _png(width: int, height: int) -> bytes:
    payload = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + struct.pack(">I", 13) + b"IHDR" + payload
            + struct.pack(">I", zlib.crc32(b"IHDR" + payload) & 0xFFFFFFFF))


def _glb_bytes(doc: dict, binary: bytes) -> bytes:
    doc = json.loads(json.dumps(doc))
    doc["buffers"] = [{"byteLength": len(binary)}]
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * ((-len(encoded)) % 4)
    bin_chunk = binary + b"\0" * ((-len(binary)) % 4)
    total = 12 + 8 + len(encoded) + 8 + len(bin_chunk)
    return (struct.pack("<4sII", b"glTF", 2, total)
            + struct.pack("<I4s", len(encoded), b"JSON") + encoded
            + struct.pack("<I4s", len(bin_chunk), b"BIN\0") + bin_chunk)


def _asset(path: Path, *, instances: int = 1, double_sided: bool = True,
           external_image: bool = False, animated: bool = False) -> bytes:
    binary = bytearray()
    views: list[dict] = []

    def add(data: bytes) -> int:
        while len(binary) % 4:
            binary.append(0)
        offset = len(binary)
        binary.extend(data)
        views.append({"buffer": 0, "byteOffset": offset, "byteLength": len(data)})
        return len(views) - 1

    positions = add(struct.pack("<9f", 0, 0, 0, 1, 0, 0, 0, 1, 0))
    indices = add(struct.pack("<3H", 0, 1, 2))
    image = None if external_image else add(_png(4, 4))
    nodes = [{"mesh": 0, "name": f"Instance {i}"} for i in range(instances)]
    image_row = {"uri": "external.png"} if external_image else {"bufferView": image, "mimeType": "image/png"}
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": list(range(instances))}],
        "nodes": nodes,
        "meshes": [{"primitives": [{
            "attributes": {"POSITION": 0}, "indices": 1, "material": 0,
        }]}],
        "materials": [{
            "name": "Panel",
            "doubleSided": double_sided,
            "pbrMetallicRoughness": {"baseColorTexture": {"index": 0}},
        }],
        "textures": [{"source": 0}],
        "images": [image_row],
        "bufferViews": views,
        "accessors": [
            {"bufferView": positions, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": indices, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
    }
    if animated:
        doc["animations"] = [{}]
    raw = _glb_bytes(doc, bytes(binary))
    path.write_bytes(raw)
    return raw


class StaticAssetBudgetTests(unittest.TestCase):
    def test_measures_real_default_scene_and_passes_explicit_budget(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "asset.glb"
            raw = _asset(target)
            budget = {
                "schema": BUDGET_SCHEMA,
                "max_triangles": 1,
                "max_vertices": 3,
                "max_primitives": 1,
                "max_material_batches": 1,
                "max_unique_materials": 1,
                "max_embedded_images": 1,
                "max_compressed_image_bytes": 33,
                "max_estimated_rgba8_mip_bytes": 84,
                "max_double_sided_materials": 1,
                "max_double_sided_batches": 1,
            }
            report = inspect_static_asset_budget(target, budget)
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["artifact_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report["measurements"]["triangle_count"], 1)
            self.assertEqual(report["measurements"]["vertex_count"], 3)
            self.assertEqual(report["measurements"]["material_batch_count"], 1)
            self.assertEqual(report["measurements"]["unique_material_count"], 1)
            self.assertEqual(report["measurements"]["embedded_image_count"], 1)
            self.assertEqual(report["measurements"]["compressed_image_bytes"], 33)
            self.assertEqual(report["measurements"]["estimated_rgba8_mip_bytes"], 84)
            self.assertEqual(report["measurements"]["double_sided_material_count"], 1)
            self.assertEqual(report["measurements"]["double_sided_batch_count"], 1)
            self.assertEqual(target.read_bytes(), raw)

    def test_budget_excess_is_fail_not_automatic_optimization(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "asset.glb"
            _asset(target)
            report = inspect_static_asset_budget(target, {
                "schema": BUDGET_SCHEMA,
                "max_double_sided_materials": 0,
                "max_estimated_rgba8_mip_bytes": 80,
            })
            self.assertEqual(report["status"], "FAIL")
            excess = [row for row in report["findings"] if row["code"] == "BUDGET_EXCEEDED"]
            self.assertEqual({row["metric"] for row in excess}, {
                "double_sided_material_count", "estimated_rgba8_mip_bytes",
            })

    def test_instanced_mesh_counts_each_default_scene_draw_surface(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "instanced.glb"
            _asset(target, instances=2, double_sided=False)
            report = inspect_static_asset_budget(target, {
                "schema": BUDGET_SCHEMA,
                "max_triangles": 2,
                "max_vertices": 6,
                "max_material_batches": 2,
                "max_unique_materials": 1,
                "max_double_sided_batches": 0,
            })
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["measurements"]["mesh_instance_count"], 2)
            self.assertEqual(report["measurements"]["triangle_count"], 2)
            self.assertEqual(report["measurements"]["material_batch_count"], 2)
            self.assertEqual(report["measurements"]["unique_material_count"], 1)

    def test_external_images_hold_and_are_never_fetched(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "external.glb"
            _asset(target, external_image=True)
            report = inspect_static_asset_budget(target, {
                "schema": BUDGET_SCHEMA, "max_embedded_images": 1,
            })
            self.assertEqual(report["status"], "HOLD")
            self.assertIn("EXTERNAL_OR_EXTENDED_IMAGE", report["finding_counts"])

    def test_deformation_holds_outside_static_scope(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "animated.glb"
            _asset(target, animated=True)
            report = inspect_static_asset_budget(target, {
                "schema": BUDGET_SCHEMA, "max_triangles": 1,
            })
            self.assertEqual(report["status"], "HOLD")
            self.assertIn("DEFORMATION_NOT_REVIEWED", report["finding_counts"])

    def test_contract_is_closed_and_requires_a_limit(self):
        with self.assertRaises(ValueError):
            validate_static_asset_budget({"schema": BUDGET_SCHEMA})
        with self.assertRaises(ValueError):
            validate_static_asset_budget({"schema": BUDGET_SCHEMA, "max_triangles": -1})
        with self.assertRaises(ValueError):
            validate_static_asset_budget({"schema": BUDGET_SCHEMA, "max_triangles": 1, "quality": "good"})


if __name__ == "__main__":
    unittest.main()

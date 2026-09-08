from __future__ import annotations

import hashlib
import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_compare import (
    RENDER_COMPARISON_SCHEMA,
    DesignCompareError,
    compare_render_screenshots,
)
from axm_uc.design_observer import record_render_observation
from axm_uc.machine import UniversalCreationMachine


def png_rgba(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
    if len(pixels) != width * height:
        raise ValueError("pixel count mismatch")
    raw = bytearray()
    cursor = 0
    for _y in range(height):
        raw.append(0)
        for _x in range(width):
            raw.extend(pixels[cursor])
            cursor += 1

    def chunk(kind: bytes, body: bytes) -> bytes:
        crc = zlib.crc32(kind)
        crc = zlib.crc32(body, crc) & 0xFFFFFFFF
        return struct.pack(">I", len(body)) + kind + body + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw))) + chunk(b"IEND", b"")


def render_observation(plan_digest: str, viewport: str, width: int, height: int, png_bytes: bytes) -> dict:
    digest = "sha256:" + hashlib.sha256(png_bytes).hexdigest()
    return record_render_observation(
        plan_digest,
        {"kind": "test-fixture", "id": "render-compare-fixture", "version": "1"},
        [{
            "viewport": {"id": viewport, "width": width, "height": height, "device_pixel_ratio": 1},
            "artifacts": [{
                "kind": "screenshot",
                "digest": digest,
                "mime_type": "image/png",
                "bytes": len(png_bytes),
            }],
            "measurements": {},
            "assessments": [],
        }],
    )


class DesignCompareTests(unittest.TestCase):
    def test_exact_before_after_change_is_measured_without_quality_claim(self):
        before_bytes = png_rgba(2, 2, [
            (0, 0, 0, 255), (0, 0, 0, 255),
            (0, 0, 0, 255), (0, 0, 0, 255),
        ])
        after_bytes = png_rgba(2, 2, [
            (255, 0, 0, 255), (0, 0, 0, 255),
            (0, 0, 0, 255), (0, 0, 0, 255),
        ])
        before_observation = render_observation("sha256:" + "1" * 64, "mobile", 2, 2, before_bytes)
        after_observation = render_observation("sha256:" + "2" * 64, "mobile", 2, 2, after_bytes)

        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            before = parent / "before.png"
            after = parent / "after.png"
            before.write_bytes(before_bytes)
            after.write_bytes(after_bytes)
            result = compare_render_screenshots(
                ROOT,
                str(before),
                str(after),
                before_observation,
                after_observation,
                "mobile",
            )

        self.assertEqual(result["schema"], RENDER_COMPARISON_SCHEMA)
        self.assertEqual(result["status"], "PASS")
        self.assertEqual(result["change"]["pixel_count"], 4)
        self.assertEqual(result["change"]["changed_pixel_count"], 1)
        self.assertEqual(result["change"]["changed_fraction"], 0.25)
        self.assertEqual(result["change"]["maximum_rgb_l1_delta"], 255)
        self.assertFalse(result["claim_boundary"]["quality_improved"])
        self.assertFalse(result["claim_boundary"]["regression_proven"])
        self.assertFalse(result["claim_boundary"]["aesthetic_judgment"])
        self.assertTrue(result["comparison_digest"].startswith("sha256:"))

    def test_identical_images_replay_to_zero_change(self):
        image = png_rgba(2, 1, [(10, 20, 30, 255), (40, 50, 60, 255)])
        observation = render_observation("sha256:" + "3" * 64, "desktop", 2, 1, image)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            a = parent / "a.png"
            b = parent / "b.png"
            a.write_bytes(image)
            b.write_bytes(image)
            first = compare_render_screenshots(ROOT, str(a), str(b), observation, observation, "desktop")
            second = compare_render_screenshots(ROOT, str(a), str(b), observation, observation, "desktop")

        self.assertEqual(first["change"]["changed_pixel_count"], 0)
        self.assertEqual(first["change"]["changed_fraction"], 0.0)
        self.assertEqual(first["comparison_digest"], second["comparison_digest"])

    def test_digest_drift_and_dimension_mismatch_fail_or_hold_closed(self):
        before_bytes = png_rgba(1, 1, [(0, 0, 0, 255)])
        after_bytes = png_rgba(2, 1, [(0, 0, 0, 255), (0, 0, 0, 255)])
        before_observation = render_observation("sha256:" + "4" * 64, "desktop", 1, 1, before_bytes)
        after_observation = render_observation("sha256:" + "5" * 64, "desktop", 2, 1, after_bytes)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            before = parent / "before.png"
            after = parent / "after.png"
            before.write_bytes(before_bytes)
            after.write_bytes(after_bytes)
            held = compare_render_screenshots(ROOT, str(before), str(after), before_observation, after_observation, "desktop")
            self.assertEqual(held["status"], "HOLD")
            self.assertEqual(held["truth_status"], "HOLD_RENDER_COMPARISON_DIMENSION_MISMATCH")
            self.assertIsNone(held["change"])

            before.write_bytes(png_rgba(1, 1, [(255, 255, 255, 255)]))
            with self.assertRaises(DesignCompareError):
                compare_render_screenshots(ROOT, str(before), str(after), before_observation, after_observation, "desktop")

    def test_live_machine_routes_render_comparison_through_design_fabric(self):
        image = png_rgba(1, 1, [(0, 0, 0, 255)])
        observation = render_observation("sha256:" + "6" * 64, "desktop", 1, 1, image)
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            before = parent / "before.png"
            after = parent / "after.png"
            before.write_bytes(image)
            after.write_bytes(image)
            result = UniversalCreationMachine(ROOT).create({
                "kind": "compare-design-render-screenshots",
                "inputs": {
                    "operation": "compare-render-screenshots",
                    "before_path": str(before),
                    "after_path": str(after),
                    "before_observation": observation,
                    "after_observation": observation,
                    "viewport": "desktop",
                },
            })

        self.assertEqual(result["type"], "CREATION_RESULT", result)
        self.assertEqual(result["capability"], "AXM-CAP-DESIGN-FABRIC")
        self.assertEqual(result["result"]["schema"], RENDER_COMPARISON_SCHEMA)
        self.assertEqual(result["result"]["change"]["changed_fraction"], 0.0)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import json
import math
import struct
import tempfile
import unittest
from pathlib import Path

from axm_uc.hard_surface_frames import (
    FRAME_PLAN_SCHEMA,
    review_hard_surface_frames,
    validate_frame_plan,
)


def glb(nodes, scene_nodes=(0,), *, animations=False):
    binary = b"\0\0\0\0"
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": list(scene_nodes)}],
        "nodes": nodes,
        "buffers": [{"byteLength": len(binary)}],
    }
    if animations:
        doc["animations"] = [{}]
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    binary += b"\0" * (-len(binary) % 4)
    total = 28 + len(encoded) + len(binary)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(encoded), b"JSON")
        + encoded
        + struct.pack("<I4s", len(binary), b"BIN\0")
        + binary
    )


def plan(**frame):
    base = {
        "position": [0, 0, 0],
        "forward": [0, 0, 1],
        "up": [0, 1, 0],
    }
    base.update(frame)
    return {
        "schema": FRAME_PLAN_SCHEMA,
        "position_tolerance_m": 0.0001,
        "angle_tolerance_deg": 0.1,
        "frames": {"Mount": base},
    }


class HardSurfaceFrameTests(unittest.TestCase):
    def review(self, raw, spec=None):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "fixture.glb"
            path.write_bytes(raw)
            before = path.read_bytes()
            result = review_hard_surface_frames(path, spec or plan())
            self.assertEqual(path.read_bytes(), before)
            return result

    def test_identity_frame_passes(self):
        r = self.review(glb([{"name": "Root", "children": [1]}, {"name": "Mount"}]))
        self.assertEqual(r["status"], "PASS")
        self.assertEqual(r["measurements"]["frames"]["Mount"]["actual_forward"], [0.0, 0.0, 1.0])
        self.assertEqual(r["measurements"]["frames"]["Mount"]["handedness"], 1.0)

    def test_nested_rotation_and_translation_measure_world_frame(self):
        q = math.sqrt(0.5)
        raw = glb([
            {"name": "Root", "translation": [2, 3, 4], "children": [1]},
            {"name": "Mount", "translation": [0, 1, 0], "rotation": [0, q, 0, q]},
        ])
        r = self.review(raw, plan(position=[2, 4, 4], forward=[1, 0, 0]))
        self.assertEqual(r["status"], "PASS")
        self.assertLess(r["measurements"]["frames"]["Mount"]["forward_error_deg"], 1e-6)

    def test_position_and_axis_drift_fail_separately(self):
        r = self.review(
            glb([{"name": "Root", "children": [1]}, {"name": "Mount", "translation": [0.01, 0, 0]}]),
            plan(forward=[1, 0, 0]),
        )
        codes = {f["code"] for f in r["findings"]}
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("FRAME_POSITION", codes)
        self.assertIn("FRAME_FORWARD", codes)
        self.assertNotIn("FRAME_UP", codes)

    def test_duplicate_and_missing_marker_names_fail_identity(self):
        duplicate = glb([{"name": "Root", "children": [1, 2]}, {"name": "Mount"}, {"name": "Mount"}])
        r = self.review(duplicate)
        self.assertEqual(r["status"], "FAIL")
        self.assertEqual(r["findings"][0], {"code": "FRAME_IDENTITY", "name": "Mount", "matches": 2})
        missing = self.review(glb([{"name": "Root"}]))
        self.assertEqual(missing["findings"][0]["matches"], 0)

    def test_mirrored_attachment_basis_fails_even_when_forward_up_match(self):
        raw = glb([{"name": "Root", "children": [1]}, {"name": "Mount", "scale": [-1, 1, 1]}])
        r = self.review(raw)
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("FRAME_MIRRORED", {f["code"] for f in r["findings"]})
        self.assertEqual(r["measurements"]["frames"]["Mount"]["handedness"], -1.0)

    def test_sheared_basis_fails_orthogonality(self):
        # glTF matrices are column-major; this adds X into the local +Y axis.
        matrix = [1, 0, 0, 0, 0.25, 1, 0, 0, 0, 0, 1, 0, 0, 0, 0, 1]
        raw = glb([{"name": "Root", "children": [1]}, {"name": "Mount", "matrix": matrix}])
        r = self.review(raw)
        self.assertEqual(r["status"], "FAIL")
        self.assertIn("FRAME_NONORTHOGONAL", {f["code"] for f in r["findings"]})

    def test_plan_validation_fails_closed(self):
        bad_cases = [
            dict(plan(), unknown=True),
            {**plan(), "frames": {}},
            {**plan(), "position_tolerance_m": float("nan")},
            {**plan(), "angle_tolerance_deg": 90},
            {**plan(), "frames": {"Mount": {"position": [0, 0, 0], "forward": [0, 0, 0], "up": [0, 1, 0]}}},
            {**plan(), "frames": {"Mount": {"position": [0, 0, 0], "forward": [0, 1, 0], "up": [0, 1, 0]}}},
        ]
        for bad in bad_cases:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                validate_frame_plan(bad)

    def test_static_scope_holds_on_animated_glb(self):
        raw = glb([{"name": "Root", "children": [1]}, {"name": "Mount"}], animations=True)
        r = self.review(raw)
        self.assertEqual(r["status"], "HOLD")
        self.assertIn("DEFORMATION_NOT_REVIEWED", {f["code"] for f in r["findings"]})


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import copy
import json
import math
from pathlib import Path
import struct
import tempfile
import unittest

from axm_stickers import Registry
from axm_stickers.core import digest
from axm_stickers.placement import identity
from axm_uc.design_workshop import SKETCH_SCHEMA, validate_sketch
from axm_uc.design_workshop_construction import BUILD_PLAN_SCHEMA, compare_sticker_assembly, save_sticker_build
from axm_uc.game_pose_runtime import _parse
from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb
from axm_uc.sticker_adapter import register_glb
from axm_uc.sticker_create import execute as sticker_execute
from axm_uc.sticker_geometry_calipers import (
    compare_sticker_geometry,
    measure_sticker_assembly_parts,
    measure_sticker_geometry,
)
from axm_uc.sticker_multiplier import MULTIPLICATION_SCHEMA, multiply_stickers

ROOT = Path(__file__).resolve().parents[1]


def pin(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def frame(x=0.0, y=0.0, z=0.0, degrees=0.0):
    value = identity()
    angle = math.radians(degrees)
    c, s = math.cos(angle), math.sin(angle)
    value[0] = c; value[1] = -s; value[4] = s; value[5] = c
    value[3] = float(x); value[7] = float(y); value[11] = float(z)
    return value


def box_body(size=(1.0, 0.2, 0.2)):
    return build_glb({
        "schema": "axm.procedural-3d/v0.1",
        "name": "Caliper box",
        "primitives": [{
            "id": "body",
            "type": "box",
            "size": list(size),
            "translation": [0.0, 0.0, 0.0],
            "material": {"color": "#808080FF", "metallic": 0.2, "roughness": 0.6},
        }],
    })["body"]


def register_box(registry, *, sticker_id="caliper-box", body=None):
    return register_glb(
        registry,
        box_body() if body is None else body,
        id=sticker_id,
        name="Caliper box",
        socket="mount",
        author="AXM test",
        license="CC0-1.0",
        source="explicit geometry caliper fixture",
    )


def part(part_id, x, *, size=(1.0, 0.2, 0.2), degrees=0.0):
    return {
        "id": part_id,
        "shape": "box",
        "frame": frame(x, degrees=degrees),
        "size": list(size),
        "role": "structure",
        "notes": "rough workshop geometry target",
    }


def sketch(parts=None, *, units="m", size_gauge=True):
    rows = parts or [part("left", -1.0), part("center", 0.0), part("right", 1.0)]
    gauges = []
    if len(rows) == 3:
        gauges.extend([
            {"id": "straightedge", "type": "alignment", "parts": [row["id"] for row in rows], "axis": "x", "tolerance": 0.01},
            {"id": "spacing", "type": "spacing", "parts": [row["id"] for row in rows], "axis": "x", "target": 1.0, "tolerance": 0.01},
        ])
    if size_gauge:
        gauges.append({"id": "caliper", "type": "size", "part": rows[0]["id"], "target": list(rows[0]["size"]), "tolerance": 0.001})
    return {
        "schema": SKETCH_SCHEMA,
        "id": "actual-geometry-plan",
        "purpose": "compare exact sticker geometry to workshop dimensions",
        "units": units,
        "parts": rows,
        "gauges": gauges,
        "tolerances": {"position": 0.01, "size": 0.001, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "explicit geometry fixture"},
    }


def build_plan(definition, checked, placements=None):
    placements = placements or {}
    return {
        "schema": BUILD_PLAN_SCHEMA,
        "sketch_digest": checked["sketch_digest"],
        "bindings": [{
            "part": row["id"],
            "sticker": pin(definition),
            "overrides": {},
            "placement": copy.deepcopy(placements.get(row["id"], {})),
        } for row in checked["parts"]],
    }


def save_build(registry, definition, checked, *, assembly_id="geometry-frame", placements=None):
    return save_sticker_build(
        registry,
        checked,
        build_plan(definition, checked, placements),
        id=assembly_id,
        name="Geometry frame",
        origin={"author": "AXM test", "license": "CC0-1.0", "source": "geometry caliper build"},
    )


def reencode(document, binary):
    body = json.dumps(document, separators=(",", ":"), allow_nan=False).encode("utf-8")
    body += b" " * (-len(body) % 4)
    payload = binary + b"\0" * (-len(binary) % 4)
    result = struct.pack("<4sII", b"glTF", 2, 28 + len(body) + len(payload))
    result += struct.pack("<II", len(body), 0x4E4F534A) + body
    result += struct.pack("<II", len(payload), 0x004E4942) + payload
    return result


class StickerGeometryCaliperTests(unittest.TestCase):
    def test_actual_triangle_geometry_closes_the_prior_size_hold(self):
        checked = validate_sketch(sketch())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry)
            saved = save_build(registry, source, checked)
            structural = compare_sticker_assembly(registry, checked, saved["pin"])
            self.assertEqual(structural["placement_status"], "PASS")
            self.assertEqual(structural["status"], "HOLD")

            report = compare_sticker_geometry(registry, checked, saved["pin"])
            self.assertEqual(report["status"], "PASS")
            self.assertTrue(report["passed"])
            self.assertEqual(report["geometry_units"], "m")
            self.assertEqual({row["id"]: row["status"] for row in report["gauges"]}["caliper"], "PASS")
            by_part = {row["id"]: row for row in report["parts"]}
            self.assertEqual(by_part["left"]["size_evidence"]["measured"], [1.0, 0.2, 0.2])
            self.assertEqual(by_part["center"]["size_status"], "PASS")

    def test_rotation_does_not_swap_local_caliper_axes(self):
        checked = validate_sketch(sketch([part("rotated", 0.0, degrees=90.0)]))
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry)
            saved = save_build(registry, source, checked, assembly_id="rotated-frame")
            measured = measure_sticker_assembly_parts(registry, saved["pin"])
            self.assertEqual(measured["status"], "PASS")
            self.assertEqual(measured["parts"][0]["size_m"], [1.0, 0.2, 0.2])
            self.assertEqual(compare_sticker_geometry(registry, checked, saved["pin"])["status"], "PASS")

    def test_explicit_placement_scale_changes_real_measured_size(self):
        doubled = validate_sketch(sketch([part("scaled", 0.0, size=(2.0, 0.4, 0.4))]))
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry)
            saved = save_build(registry, source, doubled, assembly_id="scaled-frame", placements={"scaled": {"scale": 2.0}})
            report = compare_sticker_geometry(registry, doubled, saved["pin"])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["parts"][0]["size_evidence"]["measured"], [2.0, 0.4, 0.4])

            wrong = copy.deepcopy(doubled)
            wrong.pop("sketch_digest")
            wrong["parts"][0]["size"] = [1.0, 0.2, 0.2]
            wrong["gauges"][0]["target"] = [1.0, 0.2, 0.2]
            wrong = validate_sketch(wrong)
            failed = compare_sticker_geometry(registry, wrong, saved["pin"])
            self.assertEqual(failed["status"], "FAIL")
            self.assertEqual(failed["parts"][0]["size_status"], "FAIL")

    def test_multiplied_wrapper_flattens_into_actual_nested_dimensions(self):
        checked = validate_sketch(sketch([part("module", 0.0, size=(1.5, 0.3, 0.3))]))
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry)
            multiplied = multiply_stickers(registry, {
                "schema": MULTIPLICATION_SCHEMA,
                "source": pin(source),
                "author": "AXM test",
                "license": "CC0-1.0",
                "id_prefix": "scaled-family",
                "name_prefix": "Scaled family",
                "tags": ["family"],
                "variants": [{"id": "scaled-module", "name": "Scaled module", "placement": {"scale": 1.5}}],
            })
            wrapper = registry.get(multiplied["stickers"][0]["id"], 1)
            saved = save_build(registry, wrapper, checked, assembly_id="nested-frame")
            report = compare_sticker_geometry(registry, checked, saved["pin"])
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["parts"][0]["size_evidence"]["measured"], [1.5, 0.3, 0.3])
            self.assertGreaterEqual(report["geometry"]["parts"][0]["leaf_instances"], 1)

    def test_non_metre_sketch_holds_instead_of_guessing_conversion(self):
        checked = validate_sketch(sketch([part("metric", 0.0, size=(100.0, 20.0, 20.0))], units="cm"))
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry)
            saved = save_build(registry, source, checked, assembly_id="cm-frame")
            report = compare_sticker_geometry(registry, checked, saved["pin"])
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["parts"][0]["size_status"], "HOLD")
            self.assertIn("no conversion is guessed", report["parts"][0]["size_evidence"]["reason"])

    def test_accessor_metadata_cannot_fake_actual_caliper_bounds(self):
        original = box_body()
        document, binary = _parse(original)
        position_ref = document["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        document["accessors"][position_ref]["min"] = [100.0, 100.0, 100.0]
        document["accessors"][position_ref]["max"] = [101.0, 101.0, 101.0]
        falsified = reencode(document, binary)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            source = register_box(registry, sticker_id="metadata-box", body=falsified)
            report = measure_sticker_geometry(registry, pin(source))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["measurement"]["size_m"], [1.0, 0.2, 0.2])
            self.assertLess(report["measurement"]["bounds_m"]["max"][0], 2.0)

    def test_machine_and_json_cli_return_same_geometry_report(self):
        checked = validate_sketch(sketch())
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "stickers.sqlite"
            with Registry(database) as registry:
                source = register_box(registry)
                saved = save_build(registry, source, checked)
                cli = sticker_execute(registry, {"operation": "compare_sketch_geometry", "sketch": checked, "assembly": saved["pin"]}, Path(temp))
            result = UniversalCreationMachine(ROOT).create({
                "kind": "sticker-geometry-calipers",
                "inputs": {"operation": "compare-sticker-geometry", "database": str(database), "sketch": checked, "assembly": saved["pin"]},
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-STICKER-GEOMETRY-CALIPERS")
            self.assertEqual(result["result"]["report_digest"], cli["report_digest"])


if __name__ == "__main__":
    unittest.main()

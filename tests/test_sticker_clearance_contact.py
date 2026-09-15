from __future__ import annotations

import math
from pathlib import Path
import tempfile
import unittest

from axm_stickers import Registry, instance
from axm_stickers.assembly import ASSEMBLY, save_assembly
from axm_stickers.core import digest
from axm_stickers.placement import identity
from axm_uc.design_workshop import SKETCH_SCHEMA, validate_sketch
from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb
from axm_uc.sticker_adapter import register_glb
from axm_uc.sticker_clearance_contact import (
    PLAN_SCHEMA,
    compare_sketch_clearance,
    measure_sticker_assembly_clearances,
    measure_sticker_clearance_pair,
)
from axm_uc.sticker_create import execute as sticker_execute
from axm_uc.sticker_multiplier import MULTIPLICATION_SCHEMA, multiply_stickers

ROOT = Path(__file__).resolve().parents[1]


def pin(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def frame(x=0.0, y=0.0, z=0.0, yaw_degrees=0.0):
    angle = math.radians(yaw_degrees); c, s = math.cos(angle), math.sin(angle)
    return [c, 0.0, s, float(x),
            0.0, 1.0, 0.0, float(y),
            -s, 0.0, c, float(z),
            0.0, 0.0, 0.0, 1.0]


def primitive_spec(kind, size):
    primitive = {"id": "body", "type": kind, "size": list(size), "translation": [0, 0, 0],
                 "material": {"color": "#808080FF", "metallic": 0.2, "roughness": 0.6}}
    if kind == "cylinder": primitive["segments"] = 32
    return {"schema": "axm.procedural-3d/v0.1", "name": kind + " fixture", "primitives": [primitive]}


def register_shape(registry, sticker_id, kind="box", size=(1.0, 1.0, 1.0)):
    body = build_glb(primitive_spec(kind, size))["body"]
    return register_glb(registry, body, id=sticker_id, name=sticker_id, socket="mount",
                        author="AXM test", license="CC0-1.0", source="clearance/contact fixture")


def make_assembly(registry, assembly_id, rows):
    children = []
    for part_id, definition, target_frame, placement in rows:
        children.append({"instance": instance(definition, part_id, placement=placement or {}),
                         "target": {"space": "3d", "socket": definition["attachment"]["socket"], "frame": target_frame},
                         "motion": None, "clip": None})
    return save_assembly(registry, id=assembly_id, name=assembly_id, children=children,
                         origin={"author": "AXM test", "license": "CC0-1.0", "source": "clearance assembly fixture"})


def sketch_two():
    return {
        "schema": SKETCH_SCHEMA,
        "id": "clearance-sketch",
        "purpose": "two exact workshop parts with an external clearance contract",
        "units": "m",
        "parts": [
            {"id": "a", "shape": "box", "frame": frame(0), "size": [1, 1, 1], "role": "fixture", "notes": "first"},
            {"id": "b", "shape": "box", "frame": frame(2), "size": [1, 1, 1], "role": "fixture", "notes": "second"},
        ],
        "gauges": [],
        "tolerances": {"position": 0.001, "size": 0.001, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "clearance fixture"},
    }


def clearance_plan(sketch, minimum):
    checked = validate_sketch(sketch)
    return {"schema": PLAN_SCHEMA, "sketch_digest": checked["sketch_digest"], "requirements": [
        {"id": "a-b-gap", "a": "a", "b": "b", "kind": "minimum-clearance", "minimum_m": minimum, "tolerance_m": 1e-6}
    ]}


class StickerClearanceContactTests(unittest.TestCase):
    def test_separated_boxes_report_true_triangle_clearance(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cube = register_shape(registry, "cube")
            assembly = make_assembly(registry, "separated", [("a", cube, frame(0), {}), ("b", cube, frame(2), {})])
            result = measure_sticker_clearance_pair(registry, pin(assembly), "a", "b")
            self.assertEqual(result["pair"]["relation"], "SEPARATED")
            self.assertAlmostEqual(result["pair"]["clearance_m"], 1.0, places=6)
            self.assertAlmostEqual(result["pair"]["surface_distance_m"], 1.0, places=6)

    def test_face_touching_boxes_are_touching_not_penetrating(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cube = register_shape(registry, "cube")
            assembly = make_assembly(registry, "touching", [("a", cube, frame(0), {}), ("b", cube, frame(1), {})])
            pair = measure_sticker_clearance_pair(registry, pin(assembly), "a", "b")["pair"]
            self.assertEqual(pair["relation"], "TOUCHING")
            self.assertEqual(pair["clearance_m"], 0.0)
            self.assertIsNone(pair["penetration_witness"])

    def test_containment_is_penetration_even_with_positive_surface_distance(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            outer = register_shape(registry, "outer", size=(3, 3, 3)); inner = register_shape(registry, "inner", size=(1, 1, 1))
            assembly = make_assembly(registry, "contained", [("outer", outer, frame(), {}), ("inner", inner, frame(), {})])
            pair = measure_sticker_clearance_pair(registry, pin(assembly), "outer", "inner")["pair"]
            self.assertEqual(pair["relation"], "PENETRATING")
            self.assertGreater(pair["surface_distance_m"], 0.9)
            self.assertEqual(pair["clearance_m"], 0.0)
            self.assertIsNotNone(pair["penetration_witness"])

    def test_aabb_overlap_does_not_fake_real_contact(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cylinder = register_shape(registry, "cylinder", kind="cylinder", size=(1, 0.2, 1))
            assembly = make_assembly(registry, "aabb-false-positive", [
                ("a", cylinder, frame(0, 0, 0), {}), ("b", cylinder, frame(0.8, 0, 0.8), {})])
            pair = measure_sticker_clearance_pair(registry, pin(assembly), "a", "b")["pair"]
            self.assertTrue(pair["broad_phase"]["aabb_overlap"])
            self.assertEqual(pair["relation"], "SEPARATED")
            self.assertGreater(pair["clearance_m"], 0.05)

    def test_rotated_part_uses_actual_world_triangles(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            beam = register_shape(registry, "beam", size=(2, 0.2, 0.2)); probe = register_shape(registry, "probe", size=(0.2, 0.2, 0.2))
            assembly = make_assembly(registry, "rotated", [
                ("beam", beam, frame(0, 0, 0, 90), {}), ("probe", probe, frame(0, 0, 1.2), {})])
            pair = measure_sticker_clearance_pair(registry, pin(assembly), "beam", "probe")["pair"]
            self.assertEqual(pair["relation"], "SEPARATED")
            self.assertAlmostEqual(pair["clearance_m"], 0.1, places=5)

    def test_multiplied_wrapper_flattens_before_clearance_measurement(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cube = register_shape(registry, "source-cube")
            plan = {"schema": MULTIPLICATION_SCHEMA, "source": pin(cube), "author": "AXM test", "license": "CC0-1.0",
                    "id_prefix": "cube-family", "name_prefix": "Cube family", "tags": [],
                    "variants": [{"id": "double-cube", "name": "Double cube", "placement": {"scale": 2.0}}]}
            multiplied = multiply_stickers(registry, plan); wrapper = registry.get(multiplied["stickers"][0]["id"], 1)
            self.assertEqual(wrapper["adapter"], ASSEMBLY)
            assembly = make_assembly(registry, "nested-clearance", [("big", wrapper, frame(0), {}), ("normal", cube, frame(2), {})])
            pair = measure_sticker_clearance_pair(registry, pin(assembly), "big", "normal")["pair"]
            self.assertEqual(pair["relation"], "SEPARATED")
            self.assertAlmostEqual(pair["clearance_m"], 0.5, places=6)

    def test_sketch_bound_minimum_clearance_can_pass_and_fail_without_rewriting_sketch(self):
        body = sketch_two(); checked = validate_sketch(body)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cube = register_shape(registry, "cube")
            assembly = make_assembly(registry, "planned-gap", [("a", cube, frame(0), {}), ("b", cube, frame(2), {})])
            passing = compare_sketch_clearance(registry, checked, pin(assembly), clearance_plan(checked, 0.9))
            failing = compare_sketch_clearance(registry, checked, pin(assembly), clearance_plan(checked, 1.1))
            self.assertEqual(passing["status"], "PASS")
            self.assertEqual(failing["status"], "FAIL")
            self.assertEqual(checked, validate_sketch(body))

    def test_machine_and_json_cli_return_same_pair_report_digest(self):
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "stickers.sqlite"
            with Registry(database) as registry:
                cube = register_shape(registry, "cube")
                assembly = make_assembly(registry, "parity", [("a", cube, frame(0), {}), ("b", cube, frame(2), {})])
                request = {"operation": "measure_sticker_clearance_pair", "assembly": pin(assembly), "part_a": "a", "part_b": "b"}
                cli = sticker_execute(registry, request, Path(temp))
            machine = UniversalCreationMachine(ROOT)
            result = machine.create({"kind": "sticker-clearance-contact", "inputs": {
                "operation": "measure-sticker-clearance-pair", "database": str(database),
                "assembly": pin(assembly), "part_a": "a", "part_b": "b"}})
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-STICKER-CLEARANCE-CONTACT")
            self.assertEqual(result["result"]["report_digest"], cli["report_digest"])

    def test_bounded_all_pairs_scan_keeps_relationships_explicit(self):
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            cube = register_shape(registry, "cube")
            assembly = make_assembly(registry, "three", [("a", cube, frame(0), {}), ("b", cube, frame(2), {}), ("c", cube, frame(4), {})])
            scan = measure_sticker_assembly_clearances(registry, pin(assembly))
            self.assertEqual(scan["pair_count"], 3)
            self.assertEqual({row["relation"] for row in scan["pairs"]}, {"SEPARATED"})


if __name__ == "__main__":
    unittest.main()

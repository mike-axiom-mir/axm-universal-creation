from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from axm_stickers import Registry, instance
from axm_stickers.assembly import ASSEMBLY, library_bundle, save_assembly
from axm_stickers.core import SCHEMA, digest, validate
from axm_stickers.placement import identity
from axm_uc.design_workshop import SKETCH_SCHEMA, validate_sketch
from axm_uc.design_workshop_construction import (
    BUILD_PLAN_SCHEMA,
    compare_sticker_assembly,
    compile_sticker_build,
    propose_sticker_repair,
    save_sticker_build,
    save_sticker_repair,
)
from axm_uc.machine import UniversalCreationMachine
from axm_uc.sticker_create import execute as sticker_execute
from axm_uc.sticker_multiplier import MULTIPLICATION_SCHEMA, multiply_stickers

ROOT = Path(__file__).resolve().parents[1]


def frame(x=0.0, y=0.0, z=0.0):
    value = identity(); value[3] = float(x); value[7] = float(y); value[11] = float(z); return value


def source_definition():
    return validate({
        "schema": SCHEMA,
        "id": "workshop-beam",
        "version": 1,
        "name": "Workshop beam",
        "tags": ["fixture"],
        "origin": {"author": "AXM test", "license": "CC0-1.0", "source": "explicit workshop construction fixture"},
        "adapter": "example.rigid/v1",
        "attachment": {"space": "3d", "socket": "mount", "anchor": identity()},
        "recipe": {"length": 1.0},
        "assets": {},
        "parameters": {"length": {"path": ["length"], "default": 1.0, "type": "number", "min": 0.5, "max": 3.0}}
    })


def exact_pin(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def part(part_id, x):
    return {"id": part_id, "shape": "box", "frame": frame(x), "size": [1.0, 0.2, 0.2],
            "role": "structure", "notes": "rough workshop block"}


def sketch():
    return {
        "schema": SKETCH_SCHEMA,
        "id": "sticker-frame",
        "purpose": "construct three reusable stickers along one measured frame",
        "units": "m",
        "parts": [part("left", -1), part("center", 0), part("right", 1)],
        "gauges": [
            {"id": "straightedge", "type": "alignment", "parts": ["left", "center", "right"], "axis": "x", "tolerance": 0.01},
            {"id": "spacing", "type": "spacing", "parts": ["left", "center", "right"], "axis": "x", "target": 1.0, "tolerance": 0.01},
            {"id": "caliper", "type": "size", "part": "left", "target": [1.0, 0.2, 0.2], "tolerance": 0.001}
        ],
        "tolerances": {"position": 0.01, "size": 0.001, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "explicit fixture"}
    }


def single_sketch():
    body = sketch(); body["id"] = "moving-sticker"; body["parts"] = [part("moving", 0)]; body["gauges"] = []
    return body


def build_plan(definition, sketch_body=None):
    checked = validate_sketch(sketch() if sketch_body is None else sketch_body)
    return {
        "schema": BUILD_PLAN_SCHEMA,
        "sketch_digest": checked["sketch_digest"],
        "bindings": [
            {"part": row["id"], "sticker": exact_pin(definition), "overrides": {}, "placement": {}}
            for row in checked["parts"]
        ]
    }


def origin(label="workshop test"):
    return {"author": "AXM test", "license": "CC0-1.0", "source": label}


class DesignWorkshopConstructionTests(unittest.TestCase):
    def test_sketch_compiles_and_saves_as_plain_reusable_assembly_while_size_stays_hold(self):
        source = source_definition(); checked = validate_sketch(sketch())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            compiled = compile_sticker_build(registry, checked, build_plan(source, checked))
            self.assertEqual([row["instance"]["id"] for row in compiled["children"]], ["left", "center", "right"])
            self.assertEqual([row["target"]["frame"][3] for row in compiled["children"]], [-1.0, 0.0, 1.0])
            self.assertTrue(all(row["instance"]["sticker"] == exact_pin(source) for row in compiled["children"]))

            saved = save_sticker_build(registry, checked, build_plan(source, checked),
                                       id="frame-assembly", name="Frame assembly", origin=origin())
            self.assertEqual(saved["assembly"]["adapter"], ASSEMBLY)
            report = compare_sticker_assembly(registry, checked, saved["pin"])
            self.assertEqual(report["placement_status"], "PASS")
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual({row["id"]: row["status"] for row in report["gauges"]}["caliper"], "HOLD")
            bundle = library_bundle(registry, "frame-assembly", 1)
            self.assertEqual({row["id"] for row in bundle["definitions"]}, {"frame-assembly", source["id"]})

    def test_numeric_drift_produces_one_grounded_repair_and_new_immutable_version(self):
        source = source_definition(); checked = validate_sketch(sketch())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            v1 = save_sticker_build(registry, checked, build_plan(source, checked),
                                    id="frame-assembly", name="Frame v1", origin=origin("v1"))
            drifted_children = copy.deepcopy(v1["assembly"]["recipe"]["children"])
            drifted_children[1]["target"]["frame"][7] = 0.2
            v2 = save_assembly(registry, id="frame-assembly", ver=2, name="Frame drifted", children=drifted_children,
                               origin=origin("intentional drift"))
            v2_pin = exact_pin(v2)
            report = compare_sticker_assembly(registry, checked, v2_pin)
            self.assertEqual(report["placement_status"], "FAIL")
            gauges = {row["id"]: row for row in report["gauges"]}
            self.assertEqual(gauges["straightedge"]["status"], "FAIL")
            repair = propose_sticker_repair(registry, checked, v2_pin)
            self.assertEqual(repair["status"], "READY_BOUNDED_PLACEMENT_REPAIR")
            self.assertEqual([(row["part"], row["operation"]) for row in repair["actions"]], [("center", "set-target-frame")])

            fixed = save_sticker_repair(registry, checked, v2_pin, id="frame-assembly", ver=3,
                                        name="Frame repaired", origin=origin("repair request"))
            self.assertEqual(fixed["verification"]["placement_status"], "PASS")
            self.assertEqual(registry.get("frame-assembly", 2)["recipe"]["children"][1]["target"]["frame"][7], 0.2)
            self.assertEqual(registry.get("frame-assembly", 3)["recipe"]["children"][1]["target"]["frame"][7], 0.0)
            self.assertIn("repair-of=frame-assembly@2", fixed["assembly"]["origin"]["source"])

    def test_repair_rebases_existing_rigid_motion_instead_of_dropping_it(self):
        source = source_definition(); checked = validate_sketch(single_sketch())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            placed = instance(source, "moving")
            old = frame(0, 0.2, 0); end = frame(1, 0.2, 0)
            moving = save_assembly(registry, id="moving-assembly", ver=1, name="Moving drifted",
                                   children=[{"instance": placed, "target": {"space": "3d", "socket": "mount", "frame": old},
                                              "motion": [{"time": 0, "frame": old}, {"time": 1, "frame": end}], "clip": None}],
                                   origin=origin("moving drift"))
            repaired = save_sticker_repair(registry, checked, exact_pin(moving), id="moving-assembly", ver=2,
                                            name="Moving repaired", origin=origin("moving repair"))
            child = repaired["assembly"]["recipe"]["children"][0]
            self.assertEqual(child["target"]["frame"], frame())
            self.assertEqual(child["motion"][0]["frame"], frame())
            self.assertAlmostEqual(child["motion"][1]["frame"][3], 1.0)
            self.assertAlmostEqual(child["motion"][1]["frame"][7], 0.0)

    def test_missing_part_holds_repair_instead_of_inventing_a_source_sticker(self):
        source = source_definition(); checked = validate_sketch(sketch())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            compiled = compile_sticker_build(registry, checked, build_plan(source, checked))
            incomplete = save_assembly(registry, id="incomplete", name="Incomplete", children=compiled["children"][:2], origin=origin("incomplete"))
            repair = propose_sticker_repair(registry, checked, exact_pin(incomplete))
            self.assertEqual(repair["status"], "HOLD_STRUCTURAL_MISMATCH")
            self.assertEqual(repair["unresolved"][0]["kind"], "missing-part")
            with self.assertRaisesRegex(Exception, "on HOLD"):
                save_sticker_repair(registry, checked, exact_pin(incomplete), id="incomplete", ver=2,
                                    name="Should not exist", origin=origin("blocked"))

    def test_machine_and_sticker_cli_compile_the_same_exact_plan(self):
        source = source_definition(); checked = validate_sketch(sketch()); plan = build_plan(source, checked)
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "stickers.sqlite"
            with Registry(database) as registry:
                registry.register(source)
                cli = sticker_execute(registry, {"operation": "compile_sketch_build", "sketch": checked, "plan": plan}, Path(temp))
            machine = UniversalCreationMachine(ROOT)
            result = machine.create({"kind": "workshop-construction-loop", "inputs": {
                "operation": "compile-sticker-build", "database": str(database), "sketch": checked, "plan": plan
            }})
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(result["capability"], "AXM-CAP-WORKSHOP-CONSTRUCTION-LOOP")
            self.assertEqual(result["result"]["receipt_digest"], cli["receipt_digest"])

    def test_multiplied_sticker_is_ordinary_input_to_sketch_construction(self):
        source = source_definition(); checked = validate_sketch(single_sketch())
        multiplication = {
            "schema": MULTIPLICATION_SCHEMA,
            "source": exact_pin(source),
            "author": "AXM test",
            "license": "CC0-1.0",
            "id_prefix": "beam-family",
            "name_prefix": "Beam family",
            "tags": ["family"],
            "variants": [{"id": "beam-long", "name": "Beam long", "overrides": {"length": 2.0}}]
        }
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            multiplied = multiply_stickers(registry, multiplication)
            wrapper = registry.get(multiplied["stickers"][0]["id"], 1)
            plan = {
                "schema": BUILD_PLAN_SCHEMA,
                "sketch_digest": checked["sketch_digest"],
                "bindings": [{"part": "moving", "sticker": exact_pin(wrapper), "overrides": {}, "placement": {}}]
            }
            compiled = compile_sticker_build(registry, checked, plan)
            self.assertEqual(compiled["children"][0]["instance"]["sticker"], exact_pin(wrapper))
            self.assertEqual(wrapper["adapter"], ASSEMBLY)


if __name__ == "__main__":
    unittest.main()

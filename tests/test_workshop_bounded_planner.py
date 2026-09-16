from __future__ import annotations

import copy
from pathlib import Path
import tempfile
import unittest

from axm_stickers import Registry, instance
from axm_stickers.assembly import save_assembly
from axm_stickers.core import digest
from axm_uc.design_workshop import SKETCH_SCHEMA, validate_sketch
from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb
from axm_uc.sticker_adapter import GLB, register_glb
from axm_uc.sticker_clearance_contact import PLAN_SCHEMA as CLEARANCE_PLAN_SCHEMA
from axm_uc.sticker_create import execute as sticker_execute
from axm_uc.workshop_bounded_planner import (
    PLANNER_SCHEMA,
    WorkshopBoundedPlannerError,
    preview_workshop_plan,
    retain_workshop_plan,
)

ROOT = Path(__file__).resolve().parents[1]


def pin(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def frame(x=0.0, y=0.0, z=0.0):
    return [1.0, 0.0, 0.0, float(x),
            0.0, 1.0, 0.0, float(y),
            0.0, 0.0, 1.0, float(z),
            0.0, 0.0, 0.0, 1.0]


def box_spec(size):
    return {"schema": "axm.procedural-3d/v0.1", "name": "planner box", "primitives": [{
        "id": "body", "type": "box", "size": list(size), "translation": [0, 0, 0],
        "material": {"color": "#808080FF", "metallic": 0.2, "roughness": 0.6},
    }]}


def register_box(registry, sticker_id, size=(1.0, 1.0, 1.0), *, tags=None):
    body = build_glb(box_spec(size))["body"]
    return register_glb(registry, body, id=sticker_id, name=sticker_id, socket="mount", tags=tags or [],
                        author="AXM test", license="CC0-1.0", source="bounded planner fixture")


def sketch_single(target=1.0, tolerance=0.5):
    return {
        "schema": SKETCH_SCHEMA,
        "id": "planner-single",
        "purpose": "choose one measured reusable part rather than trusting first candidate",
        "units": "m",
        "parts": [{"id": "body", "shape": "box", "frame": frame(), "size": [target, target, target],
                   "role": "fixture", "notes": "single measured part"}],
        "gauges": [],
        "tolerances": {"position": 0.001, "size": tolerance, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "planner fixture"},
    }


def sketch_two(target=1.0, tolerance=0.5):
    return {
        "schema": SKETCH_SCHEMA,
        "id": "planner-two",
        "purpose": "choose two parts under actual size and clearance evidence",
        "units": "m",
        "parts": [
            {"id": "a", "shape": "box", "frame": frame(0), "size": [target, target, target], "role": "fixture", "notes": "first"},
            {"id": "b", "shape": "box", "frame": frame(2), "size": [target, target, target], "role": "fixture", "notes": "second"},
        ],
        "gauges": [],
        "tolerances": {"position": 0.001, "size": tolerance, "orientation_degrees": 0.01},
        "provenance": {"author": "AXM test", "basis": "planner fixture"},
    }


def sketch_four():
    body = sketch_two()
    body["id"] = "planner-four"
    body["parts"] = [
        {"id": f"p{index}", "shape": "box", "frame": frame(index * 3), "size": [1, 1, 1],
         "role": "fixture", "notes": f"part {index}"} for index in range(4)
    ]
    return body


def objective():
    return {"kind": "minimize-size-error", "require_all_evidence_pass": True, "incumbent_policy": "strict-improvement"}


def planner(sketch, slots, *, clearance=None, incumbent=None):
    checked = validate_sketch(sketch)
    result = {"schema": PLANNER_SCHEMA, "sketch_digest": checked["sketch_digest"], "slots": slots, "objective": objective()}
    if clearance is not None: result["clearance_plan"] = clearance
    if incumbent is not None: result["incumbent"] = incumbent
    return result


def clearance_plan(sketch, minimum):
    checked = validate_sketch(sketch)
    return {"schema": CLEARANCE_PLAN_SCHEMA, "sketch_digest": checked["sketch_digest"], "requirements": [
        {"id": "gap", "a": "a", "b": "b", "kind": "minimum-clearance", "minimum_m": minimum, "tolerance_m": 1e-6}
    ]}


def make_assembly(registry, assembly_id, sketch, selections, *, ver=1):
    checked = validate_sketch(sketch); children = []
    for part in checked["parts"]:
        definition = selections[part["id"]]
        children.append({"instance": instance(definition, part["id"]),
                         "target": {"space": "3d", "socket": definition["attachment"]["socket"], "frame": part["frame"]},
                         "motion": None, "clip": None})
    return save_assembly(registry, id=assembly_id, ver=ver, name=assembly_id, children=children,
                         origin={"author": "AXM test", "license": "CC0-1.0", "source": "planner incumbent fixture"})


def query_slot(part, tag="candidate", limit=8):
    return {"part": part, "query": {"adapter": GLB, "socket": "mount", "tag": tag, "limit": limit}}


class WorkshopBoundedPlannerTests(unittest.TestCase):
    def test_registry_query_selects_measured_best_not_first_available(self):
        sketch = sketch_single(target=1.0, tolerance=0.5); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            wrong = register_box(registry, "a-first-wrong", (1.2, 1.2, 1.2), tags=["candidate"])
            exact = register_box(registry, "z-exact", (1, 1, 1), tags=["candidate"])
            request = planner(checked, [query_slot("body")])
            report = preview_workshop_plan(registry, checked, request)
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["evaluated_candidates"], 2)
            self.assertEqual(report["selection"]["selection"]["body"], pin(exact))
            self.assertNotEqual(report["selection"]["selection"]["body"], pin(wrong))
            self.assertEqual(report["selection"]["score"]["max_axis_size_error_m"], 0.0)

    def test_clearance_gate_can_reject_numerically_best_sized_combination(self):
        sketch = sketch_two(target=1.4, tolerance=0.5); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            small = register_box(registry, "small", (1, 1, 1))
            large = register_box(registry, "large", (1.4, 1.4, 1.4))
            slot_candidates = [pin(large), pin(small)]
            request = planner(checked,
                              [{"part": "a", "candidates": slot_candidates}, {"part": "b", "candidates": slot_candidates}],
                              clearance=clearance_plan(checked, 0.9))
            report = preview_workshop_plan(registry, checked, request)
            self.assertEqual(report["status"], "PASS", report)
            self.assertEqual(report["combination_count"], 4)
            self.assertEqual(report["selection"]["selection"], {"a": pin(small), "b": pin(small)})
            self.assertEqual(report["selection_evidence"]["clearance"]["status"], "PASS")
            large_large = next(row for row in report["candidates"] if row["selection"] == {"a": pin(large), "b": pin(large)})
            self.assertFalse(large_large["accepted"])
            self.assertEqual(large_large["clearance_status"], "FAIL")

    def test_passing_incumbent_wins_equal_evidence_instead_of_churning_versions(self):
        sketch = sketch_single(target=1.0, tolerance=0.1); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            exact = register_box(registry, "exact", (1, 1, 1))
            incumbent = make_assembly(registry, "incumbent", checked, {"body": exact})
            request = planner(checked, [{"part": "body", "candidates": [pin(exact)]}], incumbent=pin(incumbent))
            report = preview_workshop_plan(registry, checked, request)
            self.assertEqual(report["outcome"], "INCUMBENT_RETAINED_NO_STRICT_IMPROVEMENT")
            self.assertEqual(report["selection"]["kind"], "incumbent")
            retained = retain_workshop_plan(registry, checked, request, {
                "id": "unused", "name": "unused", "version": 1, "socket": "mount", "tags": [],
                "origin": {"author": "AXM test", "license": "CC0-1.0", "source": "should not write"}})
            self.assertFalse(retained["new_registry_entry"])
            with self.assertRaises(ValueError): registry.get("unused", 1)

    def test_strictly_better_passing_candidate_replaces_worse_passing_incumbent(self):
        sketch = sketch_single(target=1.0, tolerance=0.3); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            worse = register_box(registry, "worse", (1.2, 1.2, 1.2)); exact = register_box(registry, "exact", (1, 1, 1))
            incumbent = make_assembly(registry, "incumbent", checked, {"body": worse})
            request = planner(checked, [{"part": "body", "candidates": [pin(exact)]}], incumbent=pin(incumbent))
            report = preview_workshop_plan(registry, checked, request)
            self.assertEqual(report["outcome"], "SELECTED_STRICT_NUMERIC_IMPROVEMENT")
            self.assertEqual(report["selection"]["kind"], "candidate")
            self.assertEqual(report["selection"]["selection"]["body"], pin(exact))
            self.assertLess(report["selection"]["score"]["total_axis_size_error_m"], report["incumbent"]["score"]["total_axis_size_error_m"])

    def test_no_passing_candidate_holds_instead_of_promoting_least_bad(self):
        sketch = sketch_single(target=1.0, tolerance=0.05); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            bad = register_box(registry, "bad", (1.2, 1.2, 1.2))
            request = planner(checked, [{"part": "body", "candidates": [pin(bad)]}])
            report = preview_workshop_plan(registry, checked, request)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["outcome"], "HOLD_NO_PASSING_CANDIDATE")
            self.assertIsNone(report["selection"])
            self.assertFalse(report["candidates"][0]["accepted"])

    def test_preview_candidate_assemblies_never_pollute_source_registry(self):
        sketch = sketch_single(); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            exact = register_box(registry, "exact", tags=["candidate"])
            request = planner(checked, [query_slot("body")])
            report = preview_workshop_plan(registry, checked, request)
            self.assertFalse(report["source_registry_mutated"])
            self.assertEqual(registry.search(tag="planner-candidate")["entries"], [])
            self.assertEqual(registry.get("exact", 1), exact)

    def test_retention_uses_prewrite_resolved_query_even_when_winner_matches_same_query(self):
        sketch = sketch_single(); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            register_box(registry, "wrong", (1.2, 1.2, 1.2), tags=["candidate"])
            exact = register_box(registry, "exact", (1, 1, 1), tags=["candidate"])
            request = planner(checked, [query_slot("body")])
            preview = preview_workshop_plan(registry, checked, request)
            pinned_request = copy.deepcopy(request); pinned_request["planner_digest"] = preview["planner_digest"]
            retained = retain_workshop_plan(registry, checked, pinned_request, {
                "id": "retained", "name": "Retained", "version": 1, "socket": "mount", "tags": ["candidate"],
                "origin": {"author": "AXM test", "license": "CC0-1.0", "source": "explicit retain"}})
            self.assertEqual(retained["status"], "PASS", retained)
            self.assertTrue(retained["new_registry_entry"])
            saved = registry.get("retained", 1)
            self.assertEqual(saved["recipe"]["children"][0]["instance"]["sticker"], pin(exact))
            self.assertIn(preview["planner_digest"], saved["origin"]["source"])

    def test_machine_and_sticker_cli_preview_same_report(self):
        sketch = sketch_single(); checked = validate_sketch(sketch)
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "stickers.sqlite"
            with Registry(database) as registry:
                register_box(registry, "exact", tags=["candidate"])
                request = planner(checked, [query_slot("body")])
                cli = sticker_execute(registry, {"operation": "preview_workshop_plan", "sketch": checked, "planner": request}, Path(temp))
            result = UniversalCreationMachine(ROOT).create({"kind": "workshop-bounded-planner", "inputs": {
                "operation": "preview-workshop-plan", "database": str(database), "sketch": checked, "planner": request}})
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-WORKSHOP-BOUNDED-PLANNER")
            self.assertEqual(result["result"]["report_digest"], cli["report_digest"])

    def test_cartesian_candidate_growth_is_bounded_before_evaluation(self):
        sketch = validate_sketch(sketch_four())
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            candidates = [register_box(registry, f"box-{index}", (1 + index * 0.01,) * 3) for index in range(5)]
            pins = [pin(row) for row in candidates]
            request = planner(sketch, [{"part": f"p{index}", "candidates": pins} for index in range(4)])
            with self.assertRaisesRegex(WorkshopBoundedPlannerError, "Cartesian product"):
                preview_workshop_plan(registry, sketch, request)
            self.assertEqual(registry.search(tag="planner-candidate")["entries"], [])


if __name__ == "__main__":
    unittest.main()

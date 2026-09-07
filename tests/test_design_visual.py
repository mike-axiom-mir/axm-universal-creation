from __future__ import annotations

import struct
import sys
import tempfile
import unittest
import zlib
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_observer import judge_rendered_design
from axm_uc.design_visual import (
    SCREENSHOT_OBSERVATION_SCHEMA,
    SCREENSHOT_PIXEL_SCHEMA,
    DesignVisualError,
    derive_screenshot_genome,
    observe_render_screenshot,
    observe_screenshot_style,
)
from axm_uc.machine import UniversalCreationMachine


def _chunk(kind: bytes, data: bytes) -> bytes:
    crc = zlib.crc32(data, zlib.crc32(kind)) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def rgba_png(width: int, height: int, pixels: list[tuple[int, int, int, int]]) -> bytes:
    if len(pixels) != width * height:
        raise ValueError("pixel count mismatch")
    rows = []
    for y in range(height):
        row = b"".join(bytes(pixels[y * width + x]) for x in range(width))
        rows.append(b"\x00" + row)
    header = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + _chunk(b"IHDR", header)
        + _chunk(b"IDAT", zlib.compress(b"".join(rows)))
        + _chunk(b"IEND", b"")
    )


class DesignVisualTests(unittest.TestCase):
    @staticmethod
    def write_sample(path: Path, width: int = 2, height: int = 2) -> None:
        base = [
            (255, 0, 0, 255),
            (0, 255, 0, 255),
            (0, 0, 255, 255),
            (255, 255, 255, 0),
        ]
        pixels = [base[index % len(base)] for index in range(width * height)]
        path.write_bytes(rgba_png(width, height, pixels))

    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.visual-observer",
            "version": "0.4.0",
            "purpose": "exercise deterministic screenshot evidence without aesthetic auto-truth",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [],
                "radii": [],
                "typography": [],
                "custom": [],
            },
            "layout": {"breakpoints": [], "principles": ["single explicit viewport"]},
            "components": [],
            "motion": {"durations": [], "easings": [], "reduced_motion_strategy": "disable-nonessential"},
            "materials": {"signals": [], "principles": []},
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": False,
                "reduced_motion_required": False,
                "responsive_required": False,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture"},
        })
        return compose_design_plan(
            genome,
            {
                "goal": "observe one rendered screenshot",
                "required_roles": [],
                "components": [],
                "viewports": ["sample"],
                "contrast_pairs": [{"foreground": "text", "background": "surface"}],
            },
        )

    def test_png_observer_emits_deterministic_pixel_facts_without_aesthetic_claims(self):
        with tempfile.TemporaryDirectory() as td:
            screenshot = Path(td) / "sample.png"
            self.write_sample(screenshot)
            first = observe_screenshot_style(screenshot)
            second = observe_screenshot_style(screenshot)

        self.assertEqual(first["schema"], SCREENSHOT_OBSERVATION_SCHEMA)
        self.assertEqual(first["observation_digest"], second["observation_digest"])
        facts = first["signals"]["visual_pixel_facts"]
        self.assertEqual(facts["schema"], SCREENSHOT_PIXEL_SCHEMA)
        self.assertEqual(facts["image"]["width"], 2)
        self.assertEqual(facts["image"]["height"], 2)
        self.assertFalse(facts["claim_boundary"]["aesthetic_quality_judged"])
        self.assertFalse(facts["claim_boundary"]["visual_hierarchy_judged"])
        colors = {row["value"] for row in first["signals"]["colors"]}
        self.assertTrue({"#FF0000", "#00FF00", "#0000FF"}.issubset(colors))

    def test_screenshot_color_evidence_can_enter_existing_genome_flow_with_correct_provenance(self):
        with tempfile.TemporaryDirectory() as td:
            screenshot = Path(td) / "reference.png"
            self.write_sample(screenshot)
            observation = observe_screenshot_style(screenshot)
            result = derive_screenshot_genome(
                observation,
                "axm.test.screenshot-genome",
                "0.4.0",
                "screenshot-derived color grammar",
            )

        genome = result["genome"]
        self.assertEqual(genome["schema"], DESIGN_GENOME_SCHEMA)
        self.assertGreaterEqual(result["coverage"]["colors"], 3)
        self.assertEqual(genome["provenance"]["kind"], "derived-local-screenshot-pixel-observation")
        self.assertTrue(genome["provenance"]["screenshot_pixels_observed"])
        self.assertFalse(genome["provenance"]["semantic_roles_inferred"])
        self.assertFalse(genome["provenance"]["visual_quality_observed"])
        self.assertFalse(genome["provenance"]["aesthetic_preference_promoted_to_truth"])
        self.assertEqual(genome["components"], [])
        self.assertEqual(genome["quality_gates"]["policy_origin"], "AXM_DESIGN_FABRIC_DEFAULT_NOT_REFERENCE_DERIVED")

    def test_render_screenshot_becomes_judge_evidence_but_cannot_fake_visual_quality_pass(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            screenshot = Path(td) / "render.png"
            self.write_sample(screenshot)
            result = observe_render_screenshot(
                plan["plan_digest"],
                {"id": "sample", "width": 2, "height": 2, "device_pixel_ratio": 1},
                screenshot,
            )
            judgment = judge_rendered_design(plan, result["observation"])
            integrity_only = judge_rendered_design(
                plan,
                result["observation"],
                required_assessments=["pixel-dimension-integrity"],
            )

        self.assertEqual(result["truth_status"], "LOCAL_SCREENSHOT_PIXEL_EVIDENCE_READY_FOR_EXISTING_RENDER_JUDGE")
        self.assertEqual(result["observation"]["observer"]["id"], "axm-stdlib-png-observer")
        kinds = {row["kind"] for row in result["observation"]["captures"][0]["artifacts"]}
        self.assertEqual(kinds, {"screenshot", "other"})
        self.assertEqual(judgment["status"], "HOLD")
        default_gate = next(row for row in judgment["gates"] if row["gate"] == "external-perceptual-assessments")
        self.assertEqual(default_gate["status"], "HOLD")
        integrity_gate = next(row for row in integrity_only["gates"] if row["gate"] == "external-perceptual-assessments")
        self.assertEqual(integrity_gate["status"], "PASS")
        self.assertTrue(result["judge_usage"]["default_perceptual_quality_still_required"])
        self.assertFalse(result["judge_usage"]["automatic_aesthetic_pass_possible_from_pixel_facts"])

    def test_dimension_mismatch_holds_and_invalid_png_fails_closed(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            screenshot = Path(td) / "render.png"
            self.write_sample(screenshot)
            mismatched = observe_render_screenshot(
                plan["plan_digest"],
                {"id": "sample", "width": 3, "height": 2, "device_pixel_ratio": 1},
                screenshot,
            )
            assessment = mismatched["observation"]["captures"][0]["assessments"][0]
            self.assertEqual(assessment["status"], "HOLD")

            bad = Path(td) / "bad.png"
            bad.write_bytes(b"not-a-png")
            with self.assertRaises(DesignVisualError):
                observe_screenshot_style(bad)

    def test_live_machine_routes_visual_observer_through_existing_design_capability_handles(self):
        machine = UniversalCreationMachine(ROOT)
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            screenshot = Path(td) / "sample.png"
            self.write_sample(screenshot)
            observed = machine.create({
                "kind": "observe-design-reference",
                "inputs": {"operation": "observe-screenshot", "path": str(screenshot)},
            })
            self.assertEqual(observed["type"], "CREATION_RESULT", observed)
            self.assertEqual(observed["capability"], "AXM-CAP-DESIGN-FABRIC")

            derived = machine.create({
                "kind": "derive-design-genome",
                "inputs": {
                    "operation": "derive-screenshot-genome",
                    "observation": observed["result"],
                    "genome_id": "axm.test.machine-screenshot",
                    "version": "0.4.0",
                    "purpose": "machine screenshot genome bridge",
                },
            })
            self.assertEqual(derived["type"], "CREATION_RESULT", derived)
            self.assertTrue(derived["result"]["genome"]["provenance"]["screenshot_pixels_observed"])

            render_observed = machine.create({
                "kind": "record-design-render-observation",
                "inputs": {
                    "operation": "observe-render-screenshot",
                    "plan_digest": plan["plan_digest"],
                    "viewport": {"id": "sample", "width": 2, "height": 2},
                    "path": str(screenshot),
                },
            })
            self.assertEqual(render_observed["type"], "CREATION_RESULT", render_observed)
            judged = machine.create({
                "kind": "judge-rendered-design",
                "inputs": {
                    "operation": "judge-rendered",
                    "plan": plan,
                    "observation": render_observed["result"]["observation"],
                },
            })
            self.assertEqual(judged["type"], "CREATION_RESULT", judged)
            self.assertEqual(judged["result"]["status"], "HOLD")


if __name__ == "__main__":
    unittest.main()

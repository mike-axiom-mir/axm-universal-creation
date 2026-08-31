from __future__ import annotations

import tempfile
import unittest
from pathlib import Path


import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_media import ProceduralMediaError, generate_media, verify_png, verify_wav


def png_spec() -> dict:
    return {
        "width": 64,
        "height": 64,
        "background": "#00000000",
        "shapes": [
            {"kind": "circle", "cx": 32, "cy": 32, "radius": 24, "color": "#FF315CFF"},
            {"kind": "rectangle", "x": 29, "y": 8, "width": 6, "height": 48, "color": "#36E2D5FF"},
        ],
    }


def wav_spec() -> dict:
    return {
        "sample_rate": 16_000,
        "tones": [
            {"frequency_hz": 880, "duration_ms": 45, "amplitude": 5_000},
            {"frequency_hz": 0, "duration_ms": 15, "amplitude": 0},
        ],
    }


class ProceduralMediaTests(unittest.TestCase):
    def test_png_and_wav_generation_are_deterministic_and_reparsed(self):
        png_a = generate_media("png", png_spec())
        png_b = generate_media("png", png_spec())
        self.assertEqual(png_a["body"], png_b["body"])
        self.assertEqual(png_a["sha256"], png_b["sha256"])
        self.assertEqual(verify_png(png_a["body"])["pixel_format"], "rgba8")
        self.assertEqual(verify_png(png_a["body"])["decoded_payload_bytes"], 64 * 64 * 4)

        wav_a = generate_media("wav", wav_spec())
        wav_b = generate_media("wav", wav_spec())
        self.assertEqual(wav_a["body"], wav_b["body"])
        self.assertEqual(wav_a["sha256"], wav_b["sha256"])
        observed = verify_wav(wav_a["body"])
        self.assertEqual(observed["sample_rate"], 16_000)
        self.assertEqual(observed["duration_milliseconds_floor"], 60)

    def test_capability_atomically_publishes_each_supported_asset(self):
        with tempfile.TemporaryDirectory() as td:
            machine = UniversalCreationMachine(ROOT)
            png_path = Path(td) / "target.png"
            wav_path = Path(td) / "fire.wav"
            png = machine.create(
                {
                    "kind": "procedural-png-asset",
                    "inputs": {"operation": "png", "path": str(png_path), "specification": png_spec()},
                }
            )
            wav = machine.create(
                {
                    "kind": "procedural-wav-asset",
                    "inputs": {"operation": "wav", "path": str(wav_path), "specification": wav_spec()},
                }
            )
            self.assertEqual(png["type"], "CREATION_RESULT", png)
            self.assertEqual(wav["type"], "CREATION_RESULT", wav)
            self.assertTrue(png["result"]["format_validation"]["passed"])
            self.assertTrue(wav["result"]["format_validation"]["passed"])
            self.assertEqual(png_path.read_bytes(), generate_media("png", png_spec())["body"])
            self.assertEqual(wav_path.read_bytes(), generate_media("wav", wav_spec())["body"])
            self.assertFalse(png["result"]["appearance_or_audio_quality_proven"])

    def test_closed_grammar_bounds_and_output_suffix_hold_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            machine = UniversalCreationMachine(ROOT)
            bad_path = Path(td) / "wrong.wav"
            suffix = machine.create(
                {
                    "kind": "procedural-png-asset",
                    "inputs": {"operation": "png", "path": str(bad_path), "specification": png_spec()},
                }
            )
            self.assertEqual(suffix["type"], "CREATION_ERROR", suffix)
            self.assertFalse(bad_path.exists())

            unexpected = png_spec()
            unexpected["prompt"] = "invent an image"
            held = machine.create(
                {
                    "kind": "procedural-png-asset",
                    "inputs": {"operation": "png", "path": str(Path(td) / "held.png"), "specification": unexpected},
                }
            )
            self.assertEqual(held["type"], "CREATION_ERROR", held)
            self.assertIn("bounded grammar", held["message"])
            self.assertFalse((Path(td) / "held.png").exists())

    def test_corrupted_payloads_are_rejected_and_boolean_types_are_not_coerced(self):
        png = bytearray(generate_media("png", png_spec())["body"])
        png[-5] ^= 1
        with self.assertRaises(ProceduralMediaError):
            verify_png(bytes(png))
        wav = generate_media("wav", wav_spec())["body"][:-2]
        with self.assertRaises(ProceduralMediaError):
            verify_wav(wav)

        with tempfile.TemporaryDirectory() as td:
            result = UniversalCreationMachine(ROOT).create(
                {
                    "kind": "procedural-png-asset",
                    "inputs": {
                        "operation": "png",
                        "path": str(Path(td) / "target.png"),
                        "specification": png_spec(),
                        "replace": "false",
                    },
                }
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("boolean", result["message"])


if __name__ == "__main__":
    unittest.main()

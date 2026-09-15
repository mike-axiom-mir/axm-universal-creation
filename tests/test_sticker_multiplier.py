from pathlib import Path
import tempfile
import unittest

from axm_stickers import Registry
from axm_stickers.assembly import ASSEMBLY, library_bundle
from axm_stickers.core import SCHEMA, digest, validate
from axm_stickers.placement import identity
from axm_uc.machine import UniversalCreationMachine
from axm_uc.sticker_create import execute as sticker_execute
from axm_uc.sticker_multiplier import MULTIPLICATION_SCHEMA, multiply_stickers, preview_multiplication

ROOT = Path(__file__).resolve().parents[1]


def source_definition():
    return validate({
        "schema": SCHEMA,
        "id": "source-beam",
        "version": 1,
        "name": "Source beam",
        "tags": ["fixture"],
        "origin": {"author": "AXM test", "license": "CC0-1.0", "source": "explicit multiplier fixture"},
        "adapter": "example.rigid/v1",
        "attachment": {"space": "3d", "socket": "mount", "anchor": identity()},
        "recipe": {"length": 1.0},
        "assets": {},
        "parameters": {"length": {"path": ["length"], "default": 1.0, "type": "number", "min": 0.5, "max": 3.0}}
    })


def pin(definition):
    return {"id": definition["id"], "version": definition["version"], "digest": digest(definition)}


def matrix_plan(definition):
    return {
        "schema": MULTIPLICATION_SCHEMA,
        "source": pin(definition),
        "author": "AXM test",
        "license": "CC0-1.0",
        "id_prefix": "beam-family",
        "name_prefix": "Beam family",
        "tags": ["family"],
        "matrix": {"axes": [
            {"kind": "parameter", "name": "length", "values": [1.0, 2.0]},
            {"kind": "scale", "name": "scale", "values": [1.0, 1.5]}
        ]}
    }


class StickerMultiplierTests(unittest.TestCase):
    def test_matrix_preview_and_atomic_save_create_four_reusable_wrappers(self):
        source = source_definition()
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            preview = preview_multiplication(registry, matrix_plan(source))
            self.assertEqual(preview["variant_count"], 4)
            self.assertEqual(len({row["digest"] for row in preview["variants"]}), 4)
            with self.assertRaisesRegex(ValueError, "unknown sticker version"):
                registry.get(preview["variants"][0]["id"], 1)
            result = multiply_stickers(registry, matrix_plan(source))
            self.assertEqual(result["variant_count"], 4)
            self.assertFalse(result["source_assets_duplicated"])
            first = registry.get(result["stickers"][0]["id"], 1)
            self.assertEqual(first["adapter"], ASSEMBLY)
            child = first["recipe"]["children"][0]
            self.assertEqual(child["instance"]["sticker"], pin(source))
            bundle = library_bundle(registry, first["id"], 1)
            self.assertEqual({row["id"] for row in bundle["definitions"]}, {first["id"], source["id"]})

    def test_invalid_late_variant_leaves_no_partial_batch(self):
        source = source_definition()
        plan = {
            "schema": MULTIPLICATION_SCHEMA,
            "source": pin(source),
            "author": "AXM test",
            "license": "CC0-1.0",
            "id_prefix": "explicit-family",
            "name_prefix": "Explicit family",
            "tags": [],
            "variants": [
                {"id": "valid-first", "name": "Valid first", "overrides": {"length": 2.0}},
                {"id": "invalid-second", "name": "Invalid second", "overrides": {"length": 99.0}}
            ]
        }
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            with self.assertRaises(ValueError):
                multiply_stickers(registry, plan)
            with self.assertRaisesRegex(ValueError, "unknown sticker version"):
                registry.get("valid-first", 1)

    def test_sticker_create_uses_same_saved_multiplication_request(self):
        source = source_definition()
        with tempfile.TemporaryDirectory() as temp, Registry(Path(temp) / "stickers.sqlite") as registry:
            registry.register(source)
            preview = sticker_execute(registry, {"operation": "preview_multiplication", "plan": matrix_plan(source)}, Path(temp))
            self.assertEqual(preview["variant_count"], 4)
            result = sticker_execute(registry, {"operation": "multiply_stickers", "plan": matrix_plan(source)}, Path(temp))
            self.assertEqual(result["variant_count"], 4)

    def test_universal_creation_machine_routes_multiplier_to_external_registry(self):
        source = source_definition()
        with tempfile.TemporaryDirectory() as temp:
            database = Path(temp) / "stickers.sqlite"
            with Registry(database) as registry:
                registry.register(source)
            machine = UniversalCreationMachine(ROOT)
            result = machine.create({"kind": "multiply-stickers", "inputs": {
                "operation": "multiply-stickers", "database": str(database), "plan": matrix_plan(source)
            }})
            self.assertEqual(result["type"], "CREATION_RESULT")
            self.assertEqual(result["capability"], "AXM-CAP-STICKER-MULTIPLIER")
            self.assertEqual(result["result"]["variant_count"], 4)


if __name__ == "__main__":
    unittest.main()

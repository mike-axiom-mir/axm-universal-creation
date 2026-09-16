from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.standalone_creation_capabilities import register_standalone_creation_builtins


class AdapterError(RuntimeError):
    def __init__(self, message: str, details=None):
        super().__init__(message)
        self.details = details or {}


class NativeVisualMachineAdapterTests(unittest.TestCase):
    def builtins(self):
        return register_standalone_creation_builtins(
            capability_error=AdapterError,
            resolve_output_path=lambda root, raw: (root / raw).resolve() if not Path(raw).is_absolute() else Path(raw).resolve(),
            is_machine_body_path=lambda root, target: target == root.resolve(),
            grammar_inventory=lambda path: {},
            project_error=RuntimeError,
        )

    def test_native_visual_builtin_is_registered_and_inspectable(self):
        fn = self.builtins()["builtin:native_visual_runtime"]
        with tempfile.TemporaryDirectory() as temporary:
            result = fn(Path(temporary), {"operation": "inspect"})
        self.assertEqual(result["truth_status"], "EXECUTABLE_CODED_VISUAL_RUNTIME")

    def test_live_manifest_routes_through_universal_creation_machine(self):
        machine = UniversalCreationMachine(ROOT)
        result = machine.create({
            "kind": "native-visual-scene",
            "inputs": {"operation": "inspect"},
        })
        self.assertEqual(result["type"], "CREATION_RESULT")
        self.assertEqual(result["capability"], "AXM-CAP-NATIVE-VISUAL-RUNTIME")
        self.assertEqual(result["result"]["truth_status"], "EXECUTABLE_CODED_VISUAL_RUNTIME")

    def test_machine_adapter_can_compile_and_bundle_demo(self):
        fn = self.builtins()["builtin:native_visual_runtime"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            compiled = fn(root, {"operation": "compile", "scene": {"objects": [{"id": "unit"}]}})
            receipt = fn(root, {"operation": "demo", "path": "creations/native-demo"})
            html_exists = (root / "creations" / "native-demo" / "index.html").is_file()
        self.assertEqual(compiled["objects"][0]["id"], "unit")
        self.assertEqual(receipt["status"], "NATIVE_VISUAL_BUNDLE_COMPILED")
        self.assertTrue(html_exists)

    def test_machine_adapter_rejects_live_body_write(self):
        fn = self.builtins()["builtin:native_visual_runtime"]
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaises(AdapterError):
                fn(root, {"operation": "demo", "path": "."})


if __name__ == "__main__":
    unittest.main()

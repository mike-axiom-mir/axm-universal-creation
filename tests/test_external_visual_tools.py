from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.external_visual_tools import (
    EXTERNAL_VISUAL_TOOLS,
    ExternalVisualToolError,
    catalog_external_visual_tools,
    execute_external_visual_tool,
    probe_external_visual_tool,
)


class ExternalVisualToolTests(unittest.TestCase):
    def test_catalog_marks_every_connector_external_not_native(self):
        with patch("axm_uc.external_visual_tools.shutil.which", return_value=None):
            catalog = catalog_external_visual_tools()
        self.assertEqual(catalog["truth_status"], "EXTERNAL_OPTIONAL_CONNECTOR_CATALOG")
        self.assertFalse(catalog["native"])
        self.assertEqual(len(catalog["tools"]), len(EXTERNAL_VISUAL_TOOLS))
        self.assertTrue(all(item["native"] is False for item in catalog["tools"]))
        self.assertTrue(all(item["dependency_class"] == "EXTERNAL_OPTIONAL" for item in catalog["tools"]))

    def test_connector_set_contains_declared_visual_tools(self):
        self.assertTrue(
            {"blender", "godot", "unreal", "krita", "gimp", "imagemagick", "ffmpeg", "openscad", "houdini", "inkscape"}
            <= set(EXTERNAL_VISUAL_TOOLS)
        )

    @patch("axm_uc.external_visual_tools.subprocess.run")
    @patch("axm_uc.external_visual_tools.shutil.which", return_value="/opt/ffmpeg")
    def test_probe_receipts_actual_external_execution(self, _which, run):
        run.return_value = subprocess.CompletedProcess(["/opt/ffmpeg", "-version"], 0, "ffmpeg fake\n", "")
        result = probe_external_visual_tool("ffmpeg")
        self.assertEqual(result["truth_status"], "EXTERNAL_TOOL_EXECUTION_OBSERVED")
        self.assertFalse(result["native"])
        self.assertTrue(result["external_dependency_used"])
        self.assertTrue(result["probe_executed"])
        self.assertFalse(result["visual_output_observed"])
        self.assertFalse(run.call_args.kwargs["shell"])

    def test_execute_requires_explicit_permission(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(ExternalVisualToolError):
                execute_external_visual_tool(
                    "ffmpeg",
                    args=["-version"],
                    cwd=Path(temporary),
                    allow_execute=False,
                )

    @patch("axm_uc.external_visual_tools.subprocess.run")
    @patch("axm_uc.external_visual_tools.shutil.which", return_value="/opt/ffmpeg")
    def test_execute_never_uses_shell_and_hashes_output(self, _which, run):
        run.return_value = subprocess.CompletedProcess(["/opt/ffmpeg", "-version"], 0, "ok", "warn")
        with tempfile.TemporaryDirectory() as temporary:
            result = execute_external_visual_tool(
                "ffmpeg",
                args=["-version"],
                cwd=Path(temporary),
                allow_execute=True,
            )
        self.assertTrue(result["success"])
        self.assertEqual(len(result["stdout_sha256"]), 64)
        self.assertEqual(len(result["stderr_sha256"]), 64)
        self.assertFalse(run.call_args.kwargs["shell"])


if __name__ == "__main__":
    unittest.main()

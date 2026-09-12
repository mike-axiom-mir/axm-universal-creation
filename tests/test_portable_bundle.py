from __future__ import annotations

import base64
import json
import sys
import tempfile
import unittest
import zipfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.portable_bundle import MANIFEST_NAME


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class PortableBundleTests(unittest.TestCase):
    def _source(self, parent: Path) -> Path:
        source = parent / "source"
        source.mkdir()
        (source / "index.html").write_text('<img src="pixel.png">', encoding="utf-8")
        (source / "pixel.png").write_bytes(PNG)
        return source

    def test_pack_is_reproducible_and_unpack_reverifies_exact_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = self._source(base)
            runtime = UniversalCreationMachine(ROOT)
            packed = []
            for name in ("one.axmcreation.zip", "two.axmcreation.zip"):
                result = runtime.create(
                    {
                        "kind": "portable-creation-bundle",
                        "inputs": {
                            "operation": "pack",
                            "source": str(source),
                            "path": str(base / name),
                            "project_type": "static-web",
                            "name": "portable demo",
                        },
                    }
                )
                self.assertEqual(result["type"], "CREATION_RESULT", result)
                packed.append(result["result"])
            self.assertEqual(packed[0]["archive_sha256"], packed[1]["archive_sha256"])
            self.assertEqual((base / "one.axmcreation.zip").read_bytes(), (base / "two.axmcreation.zip").read_bytes())

            target = base / "restored"
            unpacked = runtime.create(
                {
                    "kind": "axm-creation-import",
                    "inputs": {
                        "operation": "unpack",
                        "path": str(base / "one.axmcreation.zip"),
                        "target": str(target),
                    },
                }
            )
            self.assertEqual(unpacked["type"], "CREATION_RESULT", unpacked)
            self.assertEqual((target / "pixel.png").read_bytes(), PNG)
            self.assertTrue(unpacked["result"]["validation"]["passed"])

    def test_manifest_body_drift_is_rejected_before_unpack(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            source = self._source(base)
            good = base / "good.zip"
            runtime = UniversalCreationMachine(ROOT)
            created = runtime.create(
                {
                    "kind": "axm-creation-export",
                    "inputs": {"operation": "pack", "source": str(source), "path": str(good), "project_type": "static-web"},
                }
            )
            self.assertEqual(created["type"], "CREATION_RESULT", created)
            broken = base / "broken.zip"
            with zipfile.ZipFile(good, "r") as original, zipfile.ZipFile(broken, "w", compression=zipfile.ZIP_STORED) as changed:
                for info in original.infolist():
                    body = original.read(info.filename)
                    if info.filename == "body/pixel.png":
                        body = b"changed"
                    changed.writestr(info, body)
            inspected = runtime.create(
                {"kind": "portable-creation-bundle", "inputs": {"operation": "inspect", "path": str(broken)}}
            )
            self.assertEqual(inspected["type"], "CREATION_ERROR", inspected)
            self.assertIn("does not match", inspected["message"])

    def test_unsafe_manifest_path_and_symlink_source_are_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            unsafe = base / "unsafe.zip"
            manifest = {
                "schema": "axm.portable-creation-bundle/v0.1",
                "name": "unsafe",
                "project_type": "generic",
                "files": [{"path": "../escape.txt", "bytes": 1, "sha256": "0" * 64}],
            }
            with zipfile.ZipFile(unsafe, "w", compression=zipfile.ZIP_STORED) as archive:
                archive.writestr(MANIFEST_NAME, json.dumps(manifest))
                archive.writestr("body/../escape.txt", b"x")
            runtime = UniversalCreationMachine(ROOT)
            result = runtime.create(
                {"kind": "portable-creation-bundle", "inputs": {"operation": "inspect", "path": str(unsafe)}}
            )
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertFalse((base / "escape.txt").exists())

            source = base / "linked"
            source.mkdir()
            outside = base / "outside.txt"
            outside.write_text("outside", encoding="utf-8")
            (source / "escape.txt").symlink_to(outside)
            packed = runtime.create(
                {
                    "kind": "portable-creation-bundle",
                    "inputs": {"operation": "pack", "source": str(source), "path": str(base / "linked.zip")},
                }
            )
            self.assertEqual(packed["type"], "CREATION_ERROR", packed)
            self.assertIn("symlink", packed["message"])

    def test_operation_specific_bundle_inputs_surface_as_input_gaps(self):
        runtime = UniversalCreationMachine(ROOT)
        pack = runtime.create(
            {"kind": "portable-creation-bundle", "inputs": {"operation": "pack", "path": "creations/a.zip"}}
        )
        unpack = runtime.create(
            {"kind": "portable-creation-bundle", "inputs": {"operation": "unpack", "path": "creations/a.zip"}}
        )
        self.assertEqual(pack["missing_required_inputs"], ["source"])
        self.assertEqual(unpack["missing_required_inputs"], ["target"])

        invalid_bool = runtime.create(
            {
                "kind": "portable-creation-bundle",
                "inputs": {"operation": "inspect", "path": "creations/a.zip", "replace": "false"},
            }
        )
        self.assertEqual(invalid_bool["type"], "CREATION_ERROR", invalid_bool)
        self.assertIn("boolean", invalid_bool["message"])


if __name__ == "__main__":
    unittest.main()

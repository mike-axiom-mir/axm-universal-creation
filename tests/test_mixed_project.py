from __future__ import annotations

import base64
import hashlib
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.machine import UniversalCreationMachine
from axm_uc.project import validate_project


PNG = base64.b64decode(
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII="
)


class MixedProjectTests(unittest.TestCase):
    def _request(self, target: Path, *, content: str | None = None) -> dict:
        return {
            "kind": "mixed-media-project",
            "inputs": {
                "path": str(target),
                "project_type": "static-web",
                "text_files": {
                    "index.html": '<img src="assets/pixel.png" alt="pixel">',
                },
                "binary_files": {
                    "assets/pixel.png": {
                        "encoding": "base64",
                        "content": content if content is not None else base64.b64encode(PNG).decode("ascii"),
                        "media_type": "image/png",
                        "sha256": hashlib.sha256(PNG).hexdigest(),
                    }
                },
                "checks": [{"type": "media-signature", "path": "assets/pixel.png", "format": "png"}],
            },
        }

    def test_mixed_project_publishes_exact_text_and_binary_bytes(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "mixed"
            result = UniversalCreationMachine(ROOT).create(self._request(target))
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            created = result["result"]
            self.assertTrue(created["validation"]["passed"], created)
            self.assertEqual((target / "assets/pixel.png").read_bytes(), PNG)
            self.assertEqual(created["binary_receipts"][0]["sha256"], hashlib.sha256(PNG).hexdigest())
            self.assertFalse(created["binary_receipts"][0]["media_type_verified"])
            checks = {row["type"]: row for row in created["validation"]["checks"]}
            self.assertTrue(checks["expected-file-digests"]["passed"])
            self.assertTrue(checks["expected-files-exact"]["passed"])
            self.assertTrue(checks["media-signature"]["passed"])

    def test_strict_base64_and_declared_digest_fail_before_publication(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "bad"
            invalid = UniversalCreationMachine(ROOT).create(self._request(target, content="not base64!!"))
            self.assertEqual(invalid["type"], "CREATION_ERROR", invalid)
            self.assertFalse(target.exists())

            request = self._request(target)
            request["inputs"]["binary_files"]["assets/pixel.png"]["sha256"] = "0" * 64
            drift = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(drift["type"], "CREATION_ERROR", drift)
            self.assertIn("does not match", drift["message"])
            self.assertFalse(target.exists())

    def test_text_binary_path_collision_is_rejected(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "collision"
            request = self._request(target)
            request["inputs"]["text_files"]["assets/pixel.png"] = "not a PNG"
            result = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("duplicate", result["message"])
            self.assertFalse(target.exists())

    def test_bad_media_signature_is_a_visible_grounded_draft_or_strict_hold(self):
        with tempfile.TemporaryDirectory() as td:
            base = Path(td)
            body = base64.b64encode(b"not a PNG").decode("ascii")
            strict_request = self._request(base / "strict", content=body)
            del strict_request["inputs"]["binary_files"]["assets/pixel.png"]["sha256"]
            strict = UniversalCreationMachine(ROOT).create(strict_request)
            self.assertEqual(strict["type"], "CREATION_ERROR", strict)
            self.assertFalse((base / "strict").exists())

            draft_request = self._request(base / "draft", content=body)
            del draft_request["inputs"]["binary_files"]["assets/pixel.png"]["sha256"]
            draft_request["inputs"]["publish_mode"] = "grounded-draft"
            draft = UniversalCreationMachine(ROOT).create(draft_request)
            self.assertEqual(draft["type"], "CREATION_RESULT", draft)
            self.assertEqual(draft["result"]["creation_status"], "GROUNDED_DRAFT")
            failed = [row for row in draft["result"]["validation"]["checks"] if row.get("passed") is not True]
            self.assertEqual([row["type"] for row in failed], ["media-signature"])

    def test_required_maps_prevent_false_ready_route(self):
        result = UniversalCreationMachine(ROOT).create(
            {"kind": "asset-project", "inputs": {"path": "creations/not-written"}}
        )
        self.assertEqual(result["type"], "CAPABILITY_INPUT_GAP", result)
        self.assertEqual(result["missing_required_inputs"], ["binary_files", "text_files"])

    def test_trial_independently_reverifies_mixed_project_digests(self):
        with tempfile.TemporaryDirectory() as td:
            trial = UniversalCreationMachine(ROOT).trial(self._request(Path(td) / "trial"))
            self.assertTrue(trial["passed"], trial)
            verification = trial["verification"]["result"]
            digest_check = next(
                row for row in verification["checks"] if row["type"] == "expected-file-digests"
            )
            self.assertTrue(digest_check["passed"])
            self.assertEqual(len(digest_check["files"]), 2)

    def test_utf8_check_rejects_invalid_bytes_and_optional_types_are_not_coerced(self):
        with tempfile.TemporaryDirectory() as td:
            target = Path(td) / "bytes"
            target.mkdir()
            (target / "raw.bin").write_bytes(b"\xff\xfe")
            report = validate_project(target, checks=[{"type": "utf8-valid", "path": "raw.bin"}])
            utf8 = next(row for row in report["checks"] if row["type"] == "utf8-valid")
            self.assertFalse(utf8["passed"])

            request = self._request(Path(td) / "coercion")
            request["inputs"]["replace"] = "false"
            result = UniversalCreationMachine(ROOT).create(request)
            self.assertEqual(result["type"], "CREATION_ERROR", result)
            self.assertIn("boolean", result["message"])


if __name__ == "__main__":
    unittest.main()

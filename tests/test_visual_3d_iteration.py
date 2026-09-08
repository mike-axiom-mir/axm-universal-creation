from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch
import zlib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.atomic import atomic_write_json
from axm_uc.visual_3d import AAA_QUALITY_GATES, compile_adaptive_3d_request
from axm_uc.visual_3d_iteration import (
    _locked, _run_path, forge_3d_iteration, inspect_3d_iteration, plan_3d_iteration,
    reject_3d_iteration, review_3d_iteration, start_3d_iteration,
)
from axm_uc.visual_assets_bridge import operate_visual_expansion
from axm_uc.visual_assets_cli import main


def fixture_png(value):
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xffffffff)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", 1, 1, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(b"\0" + bytes((value % 256, 20, 30, 255)))) + chunk(b"IEND", b""))


def fixture_glb(triangles, revision):
    # Structural fixture only, not a rendered/usable character or AAA evidence.
    payload = {"asset": {"version": "2.0", "generator": f"test-{revision}"},
               "meshes": [{"primitives": [{"indices": 0}]}], "accessors": [{"count": triangles * 3}],
               "materials": [{"name": f"material-{i}"} for i in range(5)],
               "images": [{}] * 15, "textures": [{}] * 15}
    data = json.dumps(payload).encode()
    data += b" " * (-len(data) % 4)
    return struct.pack("<4sII", b"glTF", 2, len(data) + 20) + struct.pack("<I4s", len(data), b"JSON") + data


class IterationTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.revision = 0
        self.spec = {"run_id": "test", "output": "versions", "request": {"asset_id": "axiom-bastion-frame"}}
        self.forge_mock = patch("axm_uc.visual_3d_iteration.forge_3d_asset", side_effect=self.fake_forge).start()
        self.addCleanup(patch.stopall)

    def fake_forge(self, root, request, directory, **kwargs):
        self.revision += 1
        return self.write_bundle(request, directory, self.revision)

    def write_bundle(self, request, directory, revision):
        def artifact(name, data):
            (directory / name).write_bytes(data)
            return {"path": name, "sha256": hashlib.sha256(data).hexdigest()}
        atomic_write_json(directory / "forge-request.json", request)
        manifest = {"asset_id": request["asset_id"], "source": artifact("source.blend", b"source"),
                    "exports": {name: artifact(f"{name}.glb", fixture_glb(count, revision))
                                for name, count in (("lod0", 100000), ("lod1", 48000), ("lod2", 18000), ("collision", 12))},
                    "render_proofs": [{**artifact(f"view-{i}.png", fixture_png(revision * 4 + i)), "angle_degrees": i * 90}
                                      for i in range(4)]}
        atomic_write_json(directory / "asset-manifest.json", manifest)
        return {"acceptance": {"status": "DO_NOT_TRUST_THIS_RECEIPT"}}

    def start(self, **overrides):
        return start_3d_iteration(self.root, {**self.spec, **overrides})

    def forge(self):
        return forge_3d_iteration(self.root, "test", change_summary=f"Authored revision {self.revision + 1}")

    def review(self, **criteria_overrides):
        state = inspect_3d_iteration(self.root, "test")
        pending = state["attempts"][state["pending"] - 1]
        criteria = {name: "PASS" for name in AAA_QUALITY_GATES["required_visual_criteria"]}
        criteria.update(criteria_overrides)
        return {"notes": "Synthetic test observations, not actual asset quality evidence.",
                "views": [{"artifact_sha256": digest, "criteria": dict(criteria)} for digest in pending["proof_hashes"]]}

    def test_defaults_identity_and_read_only_plan(self):
        state = self.start()
        self.assertEqual(state["minimum_iterations"], 7)
        self.assertEqual(state["maximum_iterations"], 24)
        plan = plan_3d_iteration(self.root, "test")
        self.assertEqual(plan["stage"], "silhouette")
        self.assertIn("test-001-silhouette", plan["output"])
        self.assertFalse((self.root / "versions").exists())
        self.assertEqual(inspect_3d_iteration(self.root, "test"), state)
        with self.assertRaises(FileExistsError):
            self.start()
        for invalid in ("../bad", "Test", "a/b", "", None):
            with self.assertRaises(ValueError):
                self.start(run_id=invalid)
        for minimum, maximum in ((1, 24), (7, 5), (True, 24), (7, 101)):
            with self.assertRaises(ValueError):
                self.start(run_id="limits", minimum_iterations=minimum, maximum_iterations=maximum)

    def test_full_workflow_requires_seven_distinct_reviewed_versions(self):
        self.start()
        stages = []
        for number in range(1, 8):
            stages.append(plan_3d_iteration(self.root, "test")["stage"])
            self.forge()
            state = review_3d_iteration(self.root, "test", self.review())
            self.assertEqual(state["outcome"] is not None, number == 7)
        self.assertEqual(stages, ["silhouette", "structure", "materials", "polish", "engine-final", "engine-final", "engine-final"])
        self.assertEqual(state["status"], "AAA_ACCEPTED")
        self.assertEqual(state["outcome"]["attempt"], 7)
        self.assertTrue(all(Path(row["output"]).is_dir() for row in state["attempts"]))
        self.assertFalse(plan_3d_iteration(self.root, "test")["can_forge"])
        with self.assertRaises(ValueError):
            self.forge()

    def test_failure_replays_lesson_in_exact_context_and_repeats_stage(self):
        self.start()
        self.forge()
        review = self.review(**{"faction-silhouette": "FAIL"})
        review["lessons"] = [{"id": "silhouette-repair", "evidence": "Test silhouette failed.",
                              "patch": {"constraints_add": ["Reshape shoulder silhouette"]}}]
        state = review_3d_iteration(self.root, "test", review)
        self.assertEqual(state["status"], "NEEDS_REVISION")
        next_plan = plan_3d_iteration(self.root, "test")
        self.assertEqual(next_plan["stage"], "silhouette")
        self.assertIn("Reshape shoulder silhouette", next_plan["request"]["constraints"])
        self.assertIn("silhouette-repair", next_plan["applied_lesson_ids"])
        other = compile_adaptive_3d_request(self.root, {"asset_id": "mir-sanctuary-keeper"})
        self.assertEqual(other["applied_lesson_ids"], [])

    def test_regression_returns_to_earliest_failed_stage(self):
        self.start()
        for _ in range(3):
            self.forge()
            review_3d_iteration(self.root, "test", self.review())
        self.forge()
        state = review_3d_iteration(self.root, "test", self.review(**{"faction-silhouette": "FAIL"}))
        self.assertEqual(state["stage_index"], 0)
        self.assertEqual(state["last_stage_pass"], 3)

    def test_pending_review_blocks_forge(self):
        self.start()
        before = self.forge()
        with self.assertRaises(ValueError):
            self.forge()
        self.assertEqual(inspect_3d_iteration(self.root, "test"), before)

    def test_missing_duplicate_and_foreign_views_do_not_mutate_learning(self):
        self.start()
        before = self.forge()
        review = self.review()
        for views in (review["views"][:1], review["views"][:3] + [review["views"][0]],
                      review["views"][:3] + [{"artifact_sha256": "f" * 64}]):
            with self.assertRaises(ValueError):
                review_3d_iteration(self.root, "test", {**review, "views": views})
            self.assertFalse((self.root / "state" / "visual-use-profile.json").exists())
            self.assertEqual(inspect_3d_iteration(self.root, "test"), before)

    def test_single_failed_angle_holds_stage(self):
        self.start()
        self.forge()
        review = self.review()
        review["views"][3]["criteria"]["faction-silhouette"] = "FAIL"
        self.assertEqual(review_3d_iteration(self.root, "test", review)["stage_index"], 0)

    def test_tampered_asset_is_rejected_and_can_be_released_without_deletion(self):
        self.start()
        state = self.forge()
        review = self.review()
        lod = Path(state["attempts"][-1]["output"]) / "lod0.glb"
        lod.write_bytes(b"tampered")
        with self.assertRaisesRegex(ValueError, "hash mismatch"):
            review_3d_iteration(self.root, "test", review)
        state = reject_3d_iteration(self.root, "test", "Damaged GLB; rebuild")
        self.assertEqual(state["status"], "NEEDS_REVISION")
        self.assertTrue(lod.exists())
        self.assertTrue(plan_3d_iteration(self.root, "test")["can_forge"])

    def test_manifest_replacement_rejected(self):
        self.start()
        state = self.forge()
        review = self.review()
        path = Path(state["attempts"][-1]["output"]) / "asset-manifest.json"
        data = json.loads(path.read_text())
        data["asset_id"] = "mir-sanctuary-keeper"
        atomic_write_json(path, data)
        with self.assertRaisesRegex(ValueError, "manifest changed"):
            review_3d_iteration(self.root, "test", review)

    def test_unchanged_revision_does_not_count_as_progress(self):
        self.start()
        self.forge()
        review_3d_iteration(self.root, "test", self.review())
        self.revision = 0
        with self.assertRaisesRegex(ValueError, "unchanged asset"):
            self.forge()
        state = inspect_3d_iteration(self.root, "test")
        self.assertEqual(state["stage_index"], 1)
        self.assertEqual(state["attempts"][-1]["status"], "FORGE_FAILED")
        self.assertIsNone(state["outcome"])

    def test_renderer_failure_preserved_and_next_attempt_has_new_directory(self):
        self.start()
        self.forge_mock.side_effect = RuntimeError("fixture renderer failed")
        with self.assertRaises(RuntimeError):
            self.forge()
        state = inspect_3d_iteration(self.root, "test")
        self.assertEqual(state["status"], "NEEDS_REVISION")
        self.assertTrue(Path(state["attempts"][0]["output"]).exists())
        self.forge_mock.side_effect = self.fake_forge
        self.assertEqual(self.forge()["pending"], 2)

    def test_attempt_limit_never_becomes_success(self):
        self.start(minimum_iterations=5, maximum_iterations=5)
        for _ in range(5):
            self.forge()
            state = review_3d_iteration(self.root, "test", self.review(**{"faction-silhouette": "FAIL"}))
        self.assertEqual(state["status"], "LIMIT_REACHED")
        self.assertIsNone(state["outcome"])
        self.assertFalse(plan_3d_iteration(self.root, "test")["can_forge"])

    def test_active_writer_rejected_and_lock_released(self):
        with _locked(self.root):
            with self.assertRaises(RuntimeError):
                self.start()
        self.assertEqual(self.start()["status"], "READY")

    def test_interrupted_forge_resumes_without_overwriting(self):
        self.start()
        self.forge_mock.side_effect = KeyboardInterrupt()
        with self.assertRaises(KeyboardInterrupt):
            self.forge()
        self.assertEqual(inspect_3d_iteration(self.root, "test")["status"], "FORGING")
        self.forge_mock.side_effect = self.fake_forge
        state = self.forge()
        self.assertEqual(state["attempts"][0]["status"], "INTERRUPTED")
        self.assertEqual(state["pending"], 2)

    def test_existing_version_is_not_overwritten(self):
        self.start()
        plan = plan_3d_iteration(self.root, "test")
        Path(plan["output"]).mkdir(parents=True)
        with self.assertRaises(FileExistsError):
            self.forge()
        self.assertEqual(inspect_3d_iteration(self.root, "test")["attempts"], [])

    def test_wrong_context_or_escaped_artifact_fails_before_review(self):
        self.start()
        def wrong_context(root, request, directory, **kwargs):
            self.write_bundle({**request, "context_key": "wrong-context"}, directory, 1)
        self.forge_mock.side_effect = wrong_context
        with self.assertRaisesRegex(ValueError, "does not match"):
            self.forge()
        def escaped(root, request, directory, **kwargs):
            self.write_bundle(request, directory, 2)
            path = directory / "asset-manifest.json"
            manifest = json.loads(path.read_text())
            manifest["source"]["path"] = "../outside.blend"
            atomic_write_json(path, manifest)
        self.forge_mock.side_effect = escaped
        with self.assertRaisesRegex(ValueError, "escapes"):
            self.forge()
        self.assertFalse((self.root / "state" / "visual-use-profile.json").exists())

    def test_technical_failure_uses_actual_files_not_forge_return_value(self):
        self.start()
        def small_mesh(root, request, directory, **kwargs):
            self.write_bundle(request, directory, 1)
            path = directory / "asset-manifest.json"
            manifest = json.loads(path.read_text())
            data = fixture_glb(100, 1)
            (directory / "lod0.glb").write_bytes(data)
            manifest["exports"]["lod0"]["sha256"] = hashlib.sha256(data).hexdigest()
            atomic_write_json(path, manifest)
            return {"acceptance": {"status": "AAA_ACCEPTED", "technical_pass": True}}
        self.forge_mock.side_effect = small_mesh
        self.forge()
        state = review_3d_iteration(self.root, "test", self.review())
        self.assertEqual(state["stage_index"], 0)
        self.assertFalse(state["attempts"][0]["assessment"]["technical_pass"])
        self.assertIsNone(state["outcome"])

    def test_cli_and_bridge_routing(self):
        spec_path = self.root / "spec.json"
        atomic_write_json(spec_path, self.spec)
        with patch("sys.stdout", new_callable=io.StringIO) as output:
            self.assertEqual(main(["3d-iteration-start", str(spec_path), "--state-root", str(self.root)]), 0)
            self.assertEqual(json.loads(output.getvalue())["status"], "READY")
        plan = operate_visual_expansion(self.root, {"operation": "3d-iteration-next", "run_id": "test"})
        self.assertEqual(plan["stage"], "silhouette")
        operate_visual_expansion(self.root, {"operation": "3d-iteration-forge", "run_id": "test", "change_summary": "Fixture"})
        state = operate_visual_expansion(self.root, {"operation": "3d-iteration-review", "run_id": "test", "review": self.review()})
        self.assertEqual(state["stage_index"], 1)


if __name__ == "__main__":
    unittest.main()

from __future__ import annotations

import hashlib
import json
import struct
import tempfile
import unittest
from pathlib import Path

from axm_uc.static_asset_target_evidence import (
    PACKET_SCHEMA,
    validate_static_asset_target_evidence,
    verify_static_asset_target_evidence,
)


def _glb_bytes() -> bytes:
    binary = struct.pack("<9f3H", 0, 0, 0, 1, 0, 0, 0, 1, 0, 0, 1, 2)
    doc = {
        "asset": {"version": "2.0"},
        "scene": 0,
        "scenes": [{"nodes": [0]}],
        "nodes": [{"mesh": 0}],
        "meshes": [{"primitives": [{"attributes": {"POSITION": 0}, "indices": 1}]}],
        "bufferViews": [
            {"buffer": 0, "byteOffset": 0, "byteLength": 36},
            {"buffer": 0, "byteOffset": 36, "byteLength": 6},
        ],
        "accessors": [
            {"bufferView": 0, "componentType": 5126, "count": 3, "type": "VEC3"},
            {"bufferView": 1, "componentType": 5123, "count": 3, "type": "SCALAR"},
        ],
        "buffers": [{"byteLength": len(binary)}],
    }
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * ((-len(encoded)) % 4)
    bin_chunk = binary + b"\0" * ((-len(binary)) % 4)
    total = 12 + 8 + len(encoded) + 8 + len(bin_chunk)
    return (
        struct.pack("<4sII", b"glTF", 2, total)
        + struct.pack("<I4s", len(encoded), b"JSON")
        + encoded
        + struct.pack("<I4s", len(bin_chunk), b"BIN\0")
        + bin_chunk
    )


def _packet(raw: bytes) -> dict:
    return {
        "schema": PACKET_SCHEMA,
        "artifact_sha256": hashlib.sha256(raw).hexdigest(),
        "target": {"engine": "Example Engine", "version": "1.2", "context": "RTS building"},
        "required_lanes": [
            "target_engine_import",
            "scale_pivot",
            "collision",
            "navigation",
            "resource_budget",
        ],
        "lanes": {
            "target_engine_import": {
                "status": "PASS",
                "evidence": [{"kind": "TESTED", "source": "engine-import-test", "summary": "Imported without loader errors."}],
            },
            "scale_pivot": {
                "status": "PASS",
                "evidence": [{"kind": "MEASURED", "source": "engine-transform-report", "summary": "Scale and pivot matched the declared target transform."}],
            },
            "collision": {
                "status": "PASS",
                "evidence": [{"kind": "TESTED", "source": "collision-scene", "summary": "Representative collision contacts matched the target collider policy."}],
            },
            "navigation": {
                "status": "PASS",
                "evidence": [{"kind": "TESTED", "source": "navigation-scene", "summary": "Required walkable and blocked routes were exercised."}],
            },
            "resource_budget": {
                "status": "PASS",
                "evidence": [{"kind": "MEASURED", "source": "static-asset-budget-report", "summary": "Caller target budget was measured and passed."}],
            },
        },
    }


class StaticAssetTargetEvidenceTests(unittest.TestCase):
    def _target(self, root: str) -> tuple[Path, bytes]:
        path = Path(root) / "asset.glb"
        raw = _glb_bytes()
        path.write_bytes(raw)
        return path, raw

    def test_complete_bound_required_packet_passes_only_as_evidence_gate(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            report = verify_static_asset_target_evidence(target, _packet(raw))
            self.assertEqual(report["status"], "PASS")
            self.assertEqual(report["artifact_sha256"], hashlib.sha256(raw).hexdigest())
            self.assertEqual(report["lane_results"]["collision"]["status"], "PASS")
            self.assertIn("does not itself launch the target engine", report["scope"])
            self.assertEqual(target.read_bytes(), raw)

    def test_missing_required_lane_holds_instead_of_inference(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            del packet["lanes"]["navigation"]
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["lane_results"]["navigation"]["reason"], "MISSING_REQUIRED_LANE")
            self.assertIn("MISSING_REQUIRED_LANE", report["finding_counts"])

    def test_pass_with_only_source_inspection_is_not_promoted(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["lanes"]["collision"]["evidence"] = [{
                "kind": "SOURCE_INSPECTED",
                "source": "collider-config.json",
                "summary": "Collider configuration exists in source.",
            }]
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["lane_results"]["collision"]["reason"], "INSUFFICIENT_EVIDENCE_KIND")

    def test_visual_equivalence_requires_visual_inspection(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["required_lanes"].append("lod_perceptual_equivalence")
            packet["lanes"]["lod_perceptual_equivalence"] = {
                "status": "PASS",
                "evidence": [{"kind": "TESTED", "source": "lod-structure-test", "summary": "LOD files exist and triangle counts decrease."}],
            }
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["lane_results"]["lod_perceptual_equivalence"]["reason"], "INSUFFICIENT_EVIDENCE_KIND")
            packet["lanes"]["lod_perceptual_equivalence"]["evidence"] = [{
                "kind": "VISUALLY_INSPECTED",
                "source": "rts-camera-comparison",
                "summary": "Both LODs were compared at the declared RTS camera distance.",
            }]
            self.assertEqual(verify_static_asset_target_evidence(target, packet)["status"], "PASS")

    def test_artifact_hash_mismatch_fails_before_lane_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["artifact_sha256"] = "0" * 64
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("ARTIFACT_SHA_MISMATCH", report["finding_counts"])

    def test_supplied_failure_blocks_even_when_lane_is_optional(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["lanes"]["target_device_performance"] = {
                "status": "FAIL",
                "evidence": [{"kind": "MEASURED", "source": "device-benchmark", "summary": "Measured target frame budget was exceeded."}],
            }
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "FAIL")
            self.assertEqual(report["lane_results"]["target_device_performance"]["status"], "FAIL")

    def test_weak_optional_pass_holds_whole_packet(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["lanes"]["target_device_performance"] = {
                "status": "PASS",
                "evidence": [{"kind": "SOURCE_INSPECTED", "source": "device-config", "summary": "A target device profile exists."}],
            }
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["lane_results"]["target_device_performance"]["reason"], "INSUFFICIENT_EVIDENCE_KIND")

    def test_not_tested_required_lane_holds(self):
        with tempfile.TemporaryDirectory() as tmp:
            target, raw = self._target(tmp)
            packet = _packet(raw)
            packet["lanes"]["navigation"] = {"status": "NOT_TESTED", "notes": ["No target navigation scene yet."]}
            report = verify_static_asset_target_evidence(target, packet)
            self.assertEqual(report["status"], "HOLD")
            self.assertEqual(report["lane_results"]["navigation"]["reason"], "REQUIRED_NOT_TESTED")

    def test_contract_rejects_unknown_or_ambiguous_fields(self):
        raw = _glb_bytes()
        packet = _packet(raw)
        packet["quality"] = "great"
        with self.assertRaises(ValueError):
            validate_static_asset_target_evidence(packet)
        packet = _packet(raw)
        packet["required_lanes"].append("unknown_lane")
        with self.assertRaises(ValueError):
            validate_static_asset_target_evidence(packet)
        packet = _packet(raw)
        packet["lanes"]["collision"]["evidence"][0]["kind"] = "CLAIMED"
        with self.assertRaises(ValueError):
            validate_static_asset_target_evidence(packet)

    def test_invalid_glb_fails_without_treating_hash_binding_as_structure(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "not-a-glb.glb"
            raw = b"not-a-glb"
            target.write_bytes(raw)
            report = verify_static_asset_target_evidence(target, _packet(raw))
            self.assertEqual(report["status"], "FAIL")
            self.assertIn("INVALID_GLB", report["finding_counts"])


if __name__ == "__main__":
    unittest.main()

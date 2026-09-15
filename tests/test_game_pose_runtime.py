"""Analytical fixtures, independent of Blender and the production evaluator."""
import copy
from contextlib import redirect_stdout
import hashlib
import io
import json
import math
from pathlib import Path
import struct
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from axm_uc.game_pose_runtime import GamePoseAsset, load_game_pose_glb, publish_game_pose, game_pose_runtime_catalog
from axm_uc.visual_assets_cli import main


def fixture():
    """Two-joint rig with translated mesh and a nontrivial inverse bind.

    Rig root x=2; child is at y=1. Bind vertex (1,1,0) is one unit from
    the child's pivot; turning child by 90 degrees moves it to (2,2,0).
    Mesh-node translation is deliberately unrelated to catch double transforms.
    """
    binary = bytearray()
    doc = {"asset": {"version": "2.0"}, "bufferViews": [], "accessors": [],
           "nodes": [{"name": "Rig", "translation": [2, 0, 0], "children": [1]},
                     {"name": "Hinge", "translation": [0, 1, 0]},
                     {"name": "Mesh", "translation": [99, 0, 0], "mesh": 0, "skin": 0}],
           "scenes": [{"nodes": [0, 2]}], "scene": 0}

    def add(rows, shape, code="f", component=5126, normalized=False, padding=0):
        while len(binary) % 4:
            binary.append(0)
        start = len(binary)
        for row in rows:
            binary.extend(struct.pack("<" + code * len(row), *row))
            binary.extend(b"\0" * padding)
        view = {"buffer": 0, "byteOffset": start, "byteLength": len(binary) - start}
        if padding:
            view["byteStride"] = struct.calcsize(code) * len(rows[0]) + padding
        doc["bufferViews"].append(view)
        a = {"bufferView": len(doc["bufferViews"]) - 1, "count": len(rows), "type": shape, "componentType": component}
        if normalized:
            a["normalized"] = True
        doc["accessors"].append(a)
        return len(doc["accessors"]) - 1

    times = add([[0], [1]], "SCALAR")
    rotation = add([[0, 0, 0, 1], [0, 0, 1, 0]], "VEC4")
    slide = add([[2, 0, 0], [4, 0, 0]], "VEC3")
    doc["animations"] = [
        {"name": "Turn", "samplers": [{"input": times, "output": rotation, "interpolation": "LINEAR"}],
         "channels": [{"sampler": 0, "target": {"node": 1, "path": "rotation"}}]},
        {"name": "Slide", "samplers": [{"input": times, "output": slide, "interpolation": "LINEAR"}],
         "channels": [{"sampler": 0, "target": {"node": 0, "path": "translation"}}]},
    ]
    # Inverse bind matrices stored column-major as required by GLB.
    identity = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,0,0,1]
    child_inverse = [1,0,0,0, 0,1,0,0, 0,0,1,0, 0,-1,0,1]
    inverse = add([identity, child_inverse], "MAT4")
    doc["skins"] = [{"joints": [0, 1], "inverseBindMatrices": inverse}]
    positions = add([[1,1,0], [0,1,0], [1,0,0]], "VEC3", padding=4)
    joints = add([[1,0,0,0], [0,1,0,0], [1,0,0,0]], "VEC4", "B", 5121)
    weights = add([[1,0,0,0], [.25,.75,0,0], [1,0,0,0]], "VEC4")
    doc["meshes"] = [{"primitives": [{"attributes": {"POSITION": positions, "JOINTS_0": joints, "WEIGHTS_0": weights}}]}]
    doc["buffers"] = [{"byteLength": len(binary)}]
    return doc, binary


def encode(doc, binary):
    encoded = json.dumps(doc, separators=(",", ":")).encode()
    encoded += b" " * (-len(encoded) % 4)
    binary = bytes(binary) + b"\0" * (-len(binary) % 4)
    return (struct.pack("<4sII", b"glTF", 2, 28 + len(encoded) + len(binary)) +
            struct.pack("<II", len(encoded), 0x4E4F534A) + encoded +
            struct.pack("<II", len(binary), 0x004E4942) + binary)


class GamePoseRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.doc, self.binary = fixture()

    def asset(self):
        return GamePoseAsset(encode(self.doc, self.binary))

    def vector(self, actual, expected):
        self.assertEqual(len(actual), len(expected))
        for a, b in zip(actual, expected):
            self.assertAlmostEqual(a, b, places=7)

    def test_rest_hierarchy_and_child_local_socket(self):
        a = self.asset(); pose = a.sample(vertices=True)
        self.vector(a.point(pose, 1), [2, 1, 0])
        self.vector(a.point(pose, 1, [1,0,0]), [3, 1, 0])
        self.vector(pose["meshes"][0]["positions"][0], [3, 1, 0])

    def test_half_turn_slerp_world_joint_and_skin_positions(self):
        a = self.asset(); pose = a.sample("Turn", .5, vertices=True)
        self.vector(pose["local"][1]["rotation"], [0,0,math.sqrt(.5),math.sqrt(.5)])
        self.vector(a.point(pose, 1, [1,0,0]), [2,2,0])
        self.vector(pose["meshes"][0]["positions"][0], [2,2,0])
        # Blended influences share a pivot; mesh-node x=99 must not be applied.
        self.vector(pose["meshes"][0]["positions"][1], [2,1,0])
        self.vector(pose["meshes"][0]["positions"][2], [3,2,0])

    def test_skin_blended_influences_with_different_results(self):
        p = self.doc["meshes"][0]["primitives"][0]["attributes"]["POSITION"]
        offset = self.doc["bufferViews"][self.doc["accessors"][p]["bufferView"]]["byteOffset"]
        struct.pack_into("<3f", self.binary, offset + 16, 1, 1, 0)
        pose = self.asset().sample("Turn", .5, vertices=True)
        self.vector(pose["meshes"][0]["positions"][1], [2.25,1.75,0])

    def test_antipodal_quaternion_does_not_spin(self):
        ref = self.doc["animations"][0]["samplers"][0]["output"]
        view = self.doc["bufferViews"][self.doc["accessors"][ref]["bufferView"]]
        struct.pack_into("<4f", self.binary, view["byteOffset"] + 16, 0,0,0,-1)
        pose = self.asset().sample("Turn", .5)
        self.vector(pose["local"][1]["rotation"], [0,0,0,1])

    def test_step_exact_boundary_hold_clamp_and_loop(self):
        self.doc["animations"][0]["samplers"][0]["interpolation"] = "STEP"
        a = self.asset()
        self.vector(a.sample("Turn", .999)["local"][1]["rotation"], [0,0,0,1])
        self.vector(a.sample("Turn", 1)["local"][1]["rotation"], [0,0,1,0])
        self.assertEqual(a.sample("Turn", 9)["time_s"], 1)
        self.assertEqual(a.sample("Turn", 1, loop=True)["time_s"], 0)

    def test_partial_channels_reset_to_rest_between_samples(self):
        a = self.asset(); a.sample("Turn", 1)
        pose = a.sample("Slide", .5)
        self.vector(pose["local"][1]["rotation"], [0,0,0,1])
        self.vector(pose["local"][0]["translation"], [3,0,0])

    def test_explicit_crossfade_endpoints_and_midpoint(self):
        a = self.asset()
        for weight in (0, .5, 1):
            result = a.sample("Slide", 1, blend={"clip":"Turn", "time_s":1, "loop":False, "weight":weight})
            self.vector(result["local"][0]["translation"], [2 + 2*weight,0,0])
            angle = math.pi * (1-weight) / 2
            self.vector(result["local"][1]["rotation"], [0,0,math.sin(angle),math.cos(angle)])

    def test_nonuniform_scale_uses_parent_before_child_translation(self):
        self.doc["nodes"][0]["scale"] = [2,3,4]
        a = self.asset(); self.vector(a.point(a.sample(), 1, [1,0,0]), [4,3,0])

    def test_static_matrix_column_major_conversion(self):
        self.doc["nodes"].append({"name":"Fixed", "matrix":[1,0,0,0, 0,1,0,0, 0,0,1,0, 7,8,9,1]})
        a = self.asset(); self.vector(a.point(a.sample(), 3), [7,8,9])

    def test_static_unskinned_mesh_uses_own_world_transform(self):
        del self.doc["nodes"][2]["skin"]
        self.vector(self.asset().sample(vertices=True)["meshes"][0]["positions"][0], [100,1,0])

    def test_normalized_integer_weights_are_supported(self):
        ref = self.doc["meshes"][0]["primitives"][0]["attributes"]["WEIGHTS_0"]
        a = self.doc["accessors"][ref]; a.update(componentType=5121, normalized=True)
        view = self.doc["bufferViews"][a["bufferView"]]
        view["byteStride"] = 16
        for i in range(3):
            struct.pack_into("<4B", self.binary, view["byteOffset"] + 16*i, 255,0,0,0)
        self.vector(self.asset().sample("Turn", .5, vertices=True)["meshes"][0]["positions"][0], [2,2,0])

    def test_input_bytes_and_previous_samples_are_immutable(self):
        body = encode(self.doc, self.binary); before = hashlib.sha256(body).hexdigest()
        a = GamePoseAsset(body); one = a.sample("Turn", .4, vertices=True); expected = copy.deepcopy(one)
        a.sample("Slide", .7); self.assertEqual(one, expected)
        one["local"][0]["translation"][0] = 100
        self.assertEqual(a.sample("Turn", .4, vertices=True), expected)
        self.assertEqual(before, hashlib.sha256(body).hexdigest())

    def test_invalid_glb_chunks_and_offsets_fail(self):
        body = encode(self.doc, self.binary)
        for broken in (body[:15], body[:-1], b"nope" + body[4:], body + b"extra"):
            with self.subTest(length=len(broken)), self.assertRaises(ValueError): GamePoseAsset(broken)
        self.doc["accessors"][0]["byteOffset"] = 999999
        with self.assertRaises(ValueError): self.asset()

    def test_unsupported_and_ambiguous_motion_fail_closed(self):
        mutations = [
            lambda d: d["animations"][0]["samplers"][0].update(interpolation="CUBICSPLINE"),
            lambda d: d["animations"][0]["channels"][0]["target"].update(path="weights"),
            lambda d: d["animations"][0]["channels"].append(copy.deepcopy(d["animations"][0]["channels"][0])),
            lambda d: d["animations"][1].update(name="Turn"),
            lambda d: d["accessors"][0].update(sparse={}),
            lambda d: d["buffers"][0].update(uri="https://example.invalid/data"),
            lambda d: d["nodes"][1].update(children=[0]),
            lambda d: d["nodes"][2].update(children=[1]),
            lambda d: d["nodes"][1].update(matrix=[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),
        ]
        for mutate in mutations:
            d = copy.deepcopy(self.doc); mutate(d)
            with self.subTest(mutate=mutate), self.assertRaises(ValueError): GamePoseAsset(encode(d, self.binary))

    def test_nonfinite_zero_rotation_and_nonmonotonic_keys_rejected(self):
        for value in (0., -1., float("nan")):
            binary = bytearray(self.binary); struct.pack_into("<f", binary, 4, value)
            with self.assertRaises(ValueError): GamePoseAsset(encode(self.doc, binary))
        self.doc["nodes"][0]["rotation"] = [0,0,0,0]
        with self.assertRaises(ValueError): self.asset()

    def test_bad_skin_weights_and_joint_indices_rejected(self):
        attrs = self.doc["meshes"][0]["primitives"][0]["attributes"]
        for key in ("JOINTS_0", "WEIGHTS_0"):
            ref = attrs[key]; offset = self.doc["bufferViews"][self.doc["accessors"][ref]["bufferView"]]["byteOffset"]
            binary = bytearray(self.binary)
            struct.pack_into("<B" if key=="JOINTS_0" else "<f", binary, offset, 9)
            with self.assertRaises(ValueError): GamePoseAsset(encode(self.doc, binary))

    def test_queries_validate_clip_time_and_blend(self):
        a = self.asset()
        for time in (-1, float("nan"), True):
            with self.assertRaises(ValueError): a.sample("Turn", time)
        with self.assertRaises(ValueError): a.sample("missing")
        with self.assertRaises(ValueError): a.sample("Turn", blend={"weight":.5})
        with self.assertRaises(ValueError): a.sample("Turn", blend={"clip":"Slide","time_s":0,"loop":False,"weight":2})

    def test_cli_reopens_glb_and_preserves_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); asset_path = root / "fixture.glb"
            body = encode(self.doc, self.binary); asset_path.write_bytes(body)
            request = root / "request.json"; request.write_text(json.dumps({"clip":"Turn","time_s":.5,"vertices":True}))
            with redirect_stdout(io.StringIO()):
                self.assertEqual(main(["pose-sample", str(asset_path), str(request), str(root / "out")]), 0)
            result = json.loads((root / "out" / "pose.json").read_text())
            self.vector(result["meshes"][0]["positions"][0], [2,2,0])
            self.assertEqual(asset_path.read_bytes(), body)
            with self.assertRaises(FileExistsError): publish_game_pose(root / "out", asset_path, {})

    def test_publication_failure_cleans_stage(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); source = root / "fixture.glb"; source.write_bytes(encode(self.doc,self.binary))
            with patch("axm_uc.game_pose_runtime.atomic_write_json", side_effect=OSError("full disk")):
                with self.assertRaises(OSError): publish_game_pose(root / "out", source, {"clip":"Turn"})
            self.assertFalse((root / "out").exists())
            self.assertEqual(list(root.iterdir()), [source])

    def test_catalog_exposes_actual_scope(self):
        catalog = game_pose_runtime_catalog()
        self.assertEqual(catalog["dependencies"], [])
        self.assertIn("Root translation remains", catalog["truth"])


if __name__ == "__main__": unittest.main()

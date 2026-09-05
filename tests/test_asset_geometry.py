from __future__ import annotations

import copy
import hashlib
import io
import json
import math
import struct
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.asset_geometry import CONTRACT_SCHEMA, review_static_glb, validate_static_contract
from axm_uc.visual_assets_bridge import operate_visual_expansion
from axm_uc.visual_assets_cli import main
from axm_uc.visual_3d import assess_3d_output, forge_3d_asset


def fixture(*, positions=None, indices=None, component=5123, stride=12):
    positions = positions if positions is not None else [(0,0,0),(1,0,0),(0,1,0),(0,0,1)]
    indices = indices if indices is not None else [0,2,1,0,1,3,0,3,2,1,2,3]
    vertex_bytes = b"".join(struct.pack("<3f", *p) + b"\0"*(stride-12) for p in positions)
    binary = vertex_bytes + struct.pack("<"+{5121:"B",5123:"H",5125:"I"}[component]*len(indices), *indices)
    doc = {"asset":{"version":"2.0"}, "scene":0, "scenes":[{"nodes":[0]}],
           "nodes":[{"name":"Root","children":[1,2]}, {"name":"Body","mesh":0}, {"name":"Contact","translation":[0,0,0]}],
           "meshes":[{"primitives":[{"attributes":{"POSITION":0},"indices":1}]}],
           "buffers":[{"byteLength":len(binary)}],
           "bufferViews":[{"buffer":0,"byteOffset":0,"byteLength":len(vertex_bytes),"byteStride":stride},
                          {"buffer":0,"byteOffset":len(vertex_bytes),"byteLength":len(binary)-len(vertex_bytes)}],
           "accessors":[{"bufferView":0,"componentType":5126,"count":len(positions),"type":"VEC3","min":[0,0,0],"max":[1,1,1]},
                        {"bufferView":1,"componentType":component,"count":len(indices),"type":"SCALAR"}]}
    return doc, binary


def encode(doc, binary):
    encoded=json.dumps(doc,separators=(",",":")).encode();encoded+=b" "*(-len(encoded)%4)
    binary+=b"\0"*(-len(binary)%4)
    return struct.pack("<4sII",b"glTF",2,28+len(encoded)+len(binary))+struct.pack("<I4s",len(encoded),b"JSON")+encoded+struct.pack("<I4s",len(binary),b"BIN\0")+binary


def contract():
    return {"schema":CONTRACT_SCHEMA,"bounds":{"min":[0,0,0],"max":[1,1,1]},"floor_y":0,
            "require_root_identity":True,"max_triangles":4,"max_primitives":1,"markers":{"Contact":[0,0,0]},
            "collision_boxes":[{"min":[0,0,0],"max":[1,1,1]}]}


class StaticGeometryTests(unittest.TestCase):
    def review(self, doc=None, binary=None, spec=None):
        if doc is None:doc,binary=fixture()
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"body.glb";raw=encode(doc,binary);p.write_bytes(raw)
            result=review_static_glb(p,contract() if spec is None else spec)
            self.assertEqual(p.read_bytes(),raw)
            self.assertEqual(result["artifact_sha256"],hashlib.sha256(raw).hexdigest())
            return result

    def test_real_interleaved_positions_and_all_unsigned_indices(self):
        for component in (5121,5123,5125):
            with self.subTest(component=component):
                doc,binary=fixture(component=component,stride=16);r=self.review(doc,binary)
                self.assertEqual(r["status"],"PASS");self.assertEqual(r["measurements"]["triangles"],4)
                self.assertEqual(r["measurements"]["collision_triangles_tested"],4)

    def test_nested_trs_and_marker_world_transform(self):
        doc,binary=fixture();doc["nodes"][0]["children"]=[1];doc["nodes"][1].update(children=[2],translation=[2,0,3],scale=[2,1,1],rotation=[0,math.sqrt(.5),0,math.sqrt(.5)])
        doc["nodes"][2]["translation"]=[0,.5,0]
        spec=contract();spec["bounds"]={"min":[2,0,1],"max":[3,1,3]};spec["collision_boxes"]=[spec["bounds"]];spec["markers"]={"Contact":[2,.5,3]}
        self.assertEqual(self.review(doc,binary,spec)["status"],"PASS")

    def test_column_major_matrix_and_negative_scale(self):
        doc,binary=fixture();doc["nodes"][1]["matrix"]=[-2,0,0,0,0,3,0,0,0,0,4,0,5,6,7,1]
        spec=contract();spec["floor_y"]=6;spec["bounds"]={"min":[3,6,7],"max":[5,9,11]};spec["collision_boxes"]=[spec["bounds"]]
        r=self.review(doc,binary,spec);self.assertEqual(r["status"],"PASS");self.assertEqual(r["measurements"]["bounds"],spec["bounds"])

    def test_rendered_instances_count_twice(self):
        doc,binary=fixture();doc["nodes"].append({"name":"Instance","mesh":0,"translation":[2,0,0]});doc["nodes"][0]["children"].append(3)
        spec={"schema":CONTRACT_SCHEMA,"max_triangles":8,"max_primitives":2}
        r=self.review(doc,binary,spec);self.assertEqual(r["status"],"PASS");self.assertEqual(r["measurements"]["triangles"],8)
        self.assertEqual(r["measurements"]["bounds"]["max"],[3,1,1])

    def test_metadata_bounds_cannot_hide_overflow(self):
        doc,binary=fixture();doc["accessors"][0]["max"]=[.1,.1,.1]
        spec={"schema":CONTRACT_SCHEMA,"bounds":{"min":[0,0,0],"max":[.1,.1,.1]}}
        r=self.review(doc,binary,spec);self.assertEqual(r["status"],"FAIL")
        self.assertIn("OUTSIDE_ENVELOPE",[f["code"] for f in r["findings"]])
        self.assertIn("triangle",r["findings"][0])
        self.assertEqual(r["findings"][0]["name"],"Body")

    def test_triangle_crossing_collision_gap_is_unproven(self):
        spec=contract();spec["collision_boxes"]=[{"min":[-.1,-.1,-.1],"max":[.1,1.1,1.1]}, {"min":[.9,-.1,-.1],"max":[1.1,1.1,1.1]}]
        r=self.review(spec=spec);self.assertEqual(r["status"],"FAIL")
        self.assertGreater(r["measurements"]["collision_triangles_unproven"],0)
        self.assertIn("triangle",r["findings"][0])

    def test_wrong_marker_root_floor_and_budget_return_actionable_findings(self):
        spec=contract();spec.update(floor_y=.2,max_triangles=3,markers={"Contact":[1,0,0],"Missing":[0,0,0]})
        doc,binary=fixture();doc["nodes"][0]["translation"]=[.1,0,0]
        codes={f["code"] for f in self.review(doc,binary,spec)["findings"]}
        self.assertTrue({"ROOT_TRANSFORM","FLOOR_CONTACT","MARKER_POSITION","MARKER_IDENTITY","BUDGET_EXCEEDED"}<=codes)

    def test_duplicate_marker_names_are_ambiguous(self):
        doc,binary=fixture();doc["nodes"][1]["name"]="Contact"
        r=self.review(doc,binary);self.assertEqual(r["status"],"FAIL")
        self.assertEqual(next(f for f in r["findings"] if f["code"]=="MARKER_IDENTITY")["matches"],2)

    def test_nonindexed_triangle_is_measured(self):
        doc,binary=fixture(positions=[(0,0,0),(1,0,0),(0,1,0)],indices=[0,1,2]);del doc["meshes"][0]["primitives"][0]["indices"]
        r=self.review(doc,binary);self.assertEqual(r["status"],"PASS");self.assertEqual(r["measurements"]["triangles"],1)

    def test_invalid_index_degenerate_and_nonfinite_positions_fail(self):
        for args,code in [({"indices":[0,1,99]},"INVALID_TRIANGLES"),({"indices":[0,1,2,0]},"INVALID_TRIANGLES"),
                          ({"indices":[0,0,1]},"DEGENERATE_TRIANGLE"),({"positions":[(float('nan'),0,0),(1,0,0),(0,1,0)],"indices":[0,1,2]},"NONFINITE_GEOMETRY")]:
            with self.subTest(code=code):
                r=self.review(*fixture(**args));self.assertEqual(r["status"],"FAIL");self.assertIn(code,[f["code"] for f in r["findings"]])

    def test_declared_count_cannot_read_adjacent_buffer_data(self):
        doc,binary=fixture();doc["accessors"][0]["count"]=5
        r=self.review(doc,binary);self.assertEqual(r["status"],"FAIL");self.assertEqual(r["findings"][0]["code"],"INVALID_ACCESSOR_RANGE")

    def test_cycles_and_multiple_parent_references_fail(self):
        for child in (0,2):
            doc,binary=fixture();doc["nodes"][1]["children"]=[child]
            r=self.review(doc,binary);self.assertEqual(r["status"],"FAIL");self.assertEqual(r["findings"][-1]["code"],"INVALID_NODE_GRAPH")

    def test_unsupported_inputs_hold_without_partial_pass(self):
        cases=[lambda d:d.update(skins=[{}]),lambda d:d.update(animations=[{}]),
               lambda d:d["buffers"][0].update(uri="https://example.invalid/no-fetch.bin"),
               lambda d:d["accessors"][0].update(sparse={}),lambda d:d["meshes"][0]["primitives"][0].update(targets=[{}]),
               lambda d:d.update(extensionsRequired=["KHR_draco_mesh_compression"]),
               lambda d:d["bufferViews"][0].update(extensions={"EXT_meshopt_compression":{}})]
        for change in cases:
            doc,binary=fixture();change(doc);self.assertEqual(self.review(doc,binary)["status"],"HOLD")

    def test_malformed_container_and_bounded_work(self):
        with tempfile.TemporaryDirectory() as tmp:
            p=Path(tmp)/"broken.glb";p.write_bytes(b"glTF"*5)
            self.assertEqual(review_static_glb(p,contract())["status"],"FAIL")
        with patch("axm_uc.asset_geometry.MAX_COVERAGE_PAIRS",1):self.assertEqual(self.review()["status"],"HOLD")
        with patch("axm_uc.asset_geometry.MAX_ELEMENTS",1):self.assertEqual(self.review()["status"],"HOLD")

    def test_invalid_contracts_are_rejected_before_reading(self):
        for update in ({"unknown":True},{"tolerance_m":float('nan')},{"floor_y":10**1000},{"max_triangles":True}, {"collision_boxes":[]},
                       {"bounds":{"min":[1,0,0],"max":[0,1,1]}},{"markers":{"Bad":[0,'x',0]}}):
            with self.subTest(update=update),self.assertRaises(ValueError):validate_static_contract(dict(contract(),**update))

    def test_cli_and_bridge_are_connected_and_fail_nonzero(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);p=root/"asset.glb";p.write_bytes(encode(*fixture()));c=root/"contract.json";c.write_text(json.dumps(contract()))
            self.assertEqual(operate_visual_expansion(root,{"operation":"3d-contract-review","artifact_path":"asset.glb","contract":contract()})["status"],"PASS")
            with redirect_stdout(io.StringIO()) as stream:self.assertEqual(main(["3d-contract-review",str(p),str(c)]),0)
            self.assertEqual(json.loads(stream.getvalue())["status"],"PASS")
            c.write_text(json.dumps(dict(contract(),max_triangles=1)))
            with redirect_stdout(io.StringIO()):self.assertEqual(main(["3d-contract-review",str(p),str(c)]),2)
            self.assertEqual(set(x.name for x in root.iterdir()),{"asset.glb","contract.json"})

    def test_spatial_failure_or_stale_hash_blocks_assessment(self):
        r=self.review();receipt={"inspections":{"lod0":{"sha256":r["artifact_sha256"]}},"spatial_contract_review":r}
        self.assertTrue(assess_3d_output(receipt,{})["gates"]["static-spatial-contract"])
        stale=copy.deepcopy(receipt);stale["spatial_contract_review"]["artifact_sha256"]="0"*64
        self.assertFalse(assess_3d_output(stale,{})["gates"]["static-spatial-contract"])
        receipt["spatial_contract_review"]["status"]="FAIL"
        self.assertFalse(assess_3d_output(receipt,{})["technical_pass"])

    def test_forge_applies_requested_contract_to_actual_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);script=root/"tools/blender/axm_blender_forge.py";script.parent.mkdir(parents=True);script.write_text("# fixture")
            output=root/"output"
            def fake_blender(*args,**kwargs):
                exports={k:{"path":k+".glb"} for k in ("lod0","lod1","lod2","collision")}
                for v in exports.values():(output/v["path"]).write_bytes(encode(*fixture()))
                (output/"asset-manifest.json").write_text(json.dumps({"exports":exports}))
                return SimpleNamespace(returncode=0,stdout="",stderr="")
            with patch("axm_uc.visual_3d.compile_adaptive_3d_request",return_value={"request":{"asset_id":"fixture"}}),patch("axm_uc.visual_3d.resolve_blender",return_value=(Path(sys.executable),{})),patch("axm_uc.visual_3d.subprocess.run",side_effect=fake_blender):
                r=forge_3d_asset(root,{},output,spatial_contract=dict(contract(),max_triangles=1))
            self.assertEqual(r["spatial_contract_review"]["status"],"FAIL")
            self.assertFalse(r["acceptance"]["gates"]["static-spatial-contract"])
            self.assertTrue((output/"static-contract-review.json").is_file())


if __name__=="__main__":unittest.main()

import copy
import hashlib
import json
from pathlib import Path
import struct
import tempfile
import unittest

from axm_uc.machine import UniversalCreationMachine
from axm_uc.procedural_3d import build_glb, verify_glb, Procedural3DError
from axm_uc.survivor_workshop import workshop_spec
from axm_uc.workshop_project import workshop_request

ROOT = Path(__file__).resolve().parents[1]


def triangle():
    return {"schema": "axm.surface-3d/v0.1", "name": "triangle", "primitives": [{
        "id": "metal", "positions": [[0, 0, 0], [1, 0, 0], [0, 1, 0]],
        "normals": [[0, 0, 1]] * 3, "indices": [0, 1, 2],
        "colors": [[.2, .3, .4, 1]] * 3,
        "material": {"color": "#808080ff", "metallic": .5, "roughness": .8}}]}


class SurfaceWorkshopTests(unittest.TestCase):
    def test_surface_contract_rejects_bad_geometry_before_publication(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/"surface.glb"
            target.write_bytes(b"preserve")
            for key, value in (("indices", [0, 2, 1]), ("indices", [0, 0, 2]),
                               ("indices", [0, 1, True]), ("indices", [0, 1, 3]),
                               ("positions", [[float('nan'), 0, 0]]*3),
                               ("colors", [[1, 0, 0, 1]]), ("colors", [[2, 0, 0, 1]]*3)):
                spec = triangle(); spec["primitives"][0][key] = value
                with self.subTest(field=key, value=str(value)):
                    result = UniversalCreationMachine(ROOT).create({"kind": "procedural-glb-asset", "inputs": {
                        "path": str(target), "specification": spec, "replace": True}})
                    self.assertEqual(result["type"], "CREATION_ERROR")
                    self.assertEqual(target.read_bytes(), b"preserve")
        spec = triangle(); spec["primitives"][0]["positions"] *= 21846
        with self.assertRaises(Procedural3DError): build_glb(spec)

    def test_surface_export_is_repeatable_and_native_primitives_stay_independent(self):
        from axm_uc.procedural_3d import _geometry
        original = _geometry
        spec = triangle(); before = copy.deepcopy(spec)
        a = build_glb(spec); b = build_glb(spec)
        self.assertEqual(a["body"], b["body"])
        self.assertEqual(spec, before)
        self.assertEqual(a["document"]["extras"]["axmSpecificationSchema"], spec["schema"])
        self.assertEqual(verify_glb(a["body"])["triangles"], 1)
        self.assertIs(__import__('axm_uc.procedural_3d', fromlist=['_geometry'])._geometry, original)

    def test_workshop_preserves_original_exported_geometry_and_colors(self):
        reference = json.loads((ROOT/'examples/surfaces/workshop-v03-reference.json').read_text())
        for lod, expected_triangles in (("near", 11338), ("far", 3174)):
            built = build_glb(workshop_spec(lod)); raw, doc = built["body"], built["document"]
            length = struct.unpack_from('<I', raw, 12)[0]; blob = raw[28+length:]
            self.assertEqual(verify_glb(raw)["triangles"], expected_triangles)
            self.assertEqual(len(doc["meshes"]), 9)
            for mesh in doc["meshes"]:
                primitive = mesh["primitives"][0]
                expected = reference["lods"][lod]["groups"][mesh["name"]]
                self.assertEqual(doc["materials"][primitive["material"]]["pbrMetallicRoughness"], expected["material"])
                for key, ref in dict(primitive["attributes"], indices=primitive["indices"]).items():
                    a = doc["accessors"][ref]; v = doc["bufferViews"][a["bufferView"]]
                    start = v.get("byteOffset", 0) + a.get("byteOffset", 0)
                    size = a["count"] * {5123: 2, 5126: 4}[a["componentType"]] * {"SCALAR": 1, "VEC3": 3, "VEC4": 4}[a["type"]]
                    self.assertEqual(hashlib.sha256(blob[start:start+size]).hexdigest(), expected["attributes"][key], (lod, mesh["name"], key))

    def test_workshop_executes_existing_transactional_project_route(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp)/'workshop'
            request = workshop_request(target)
            self.assertFalse(target.exists())
            machine = UniversalCreationMachine(ROOT)
            result = machine.create(request)
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            manifest = json.loads((target/'manifest.json').read_text())
            for item in manifest["items"]:
                body = (target/item["path"]).read_bytes()
                self.assertEqual(hashlib.sha256(body).hexdigest(), item["sha256"])
                self.assertTrue(verify_glb(body)["passed"])
            self.assertFalse(manifest["boundaries"]["target_game_imported"])
            self.assertFalse(manifest["boundaries"]["browser_observed_by_generation"])
            self.assertNotIn('__ASSET_DATA__', (target/'index.html').read_text())
            before = {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()}
            self.assertEqual(machine.create(request)["type"], "CREATION_ERROR")
            self.assertEqual(before, {p.name: p.read_bytes() for p in target.iterdir() if p.is_file()})

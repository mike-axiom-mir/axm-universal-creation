import hashlib,json,tempfile,unittest
from pathlib import Path
from axm_uc.fabric_material import FabricSpec,fabric_fields,fabric_request
from axm_uc.machine import UniversalCreationMachine
ROOT=Path(__file__).resolve().parents[1]
class FabricTests(unittest.TestCase):
    def test_exact_donor_vectors_and_repeat(self):
        fields=fabric_fields(32,7)
        expected=json.loads((Path(__file__).with_name('fabric_donor_vectors.json')).read_text())
        self.assertEqual({k:hashlib.sha256(v[1]).hexdigest() for k,v in fields.items()},expected)
        self.assertEqual(fields,fabric_fields(32,7))
        self.assertNotEqual(fields['base_color'],fabric_fields(32,8)['base_color'])
        for channels,data in fields.values():self.assertEqual(len(data),32*32*channels)
        self.assertEqual(fields['orm'][1][2::3],bytes(32*32))
    def test_invalid_inputs(self):
        for size,seed,spec in [(True,1,FabricSpec()),(2048,1,FabricSpec()),(32,-1,FabricSpec()),(32,1,FabricSpec(roughness=float('nan'))),(32,1,FabricSpec(warp_threads=2.5))]:
            with self.assertRaises(ValueError):fabric_fields(size,seed,spec)
    def test_machine_build_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as td:
            path=Path(td)/'fabric';m=UniversalCreationMachine(ROOT)
            request=fabric_request(path,16,3);r=m.create(request)
            self.assertEqual(r['type'],'CREATION_RESULT',r)
            manifest=json.loads((path/'fabric-material.json').read_text())
            for row in manifest['maps'].values():
                self.assertEqual(hashlib.sha256((path/row['file']).read_bytes()).hexdigest(),row['sha256'])
            (path/'keep.txt').write_text('keep')
            self.assertNotEqual(m.create(request)['type'],'CREATION_RESULT')
            self.assertEqual((path/'keep.txt').read_text(),'keep')

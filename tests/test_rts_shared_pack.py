"""Data-loss regressions for the optional compact RTS exporter (no Blender)."""
import importlib.util,json,struct,tempfile,unittest
from pathlib import Path

spec=importlib.util.spec_from_file_location('pack_rts_shared',Path(__file__).parents[1]/'tools/blender/pack_rts_shared.py')
pack=importlib.util.module_from_spec(spec);spec.loader.exec_module(pack)

class SharedPackTests(unittest.TestCase):
    def fixture(self,p):
        geometry=struct.pack('<9f',0,0,0,1,0,0,0,1,0);image=b'\x89PNG\r\n\x1a\n' # Opaque image bytes: exporter does not decode/re-encode.
        binary=image+geometry
        doc={'asset':{'version':'2.0'},'buffers':[{'byteLength':len(binary)}],
             'bufferViews':[{'buffer':0,'byteOffset':0,'byteLength':len(image)},{'buffer':0,'byteOffset':len(image),'byteLength':len(geometry),'target':34962}],
             'accessors':[{'bufferView':1,'componentType':5126,'count':3,'type':'VEC3'}],
             'images':[{'bufferView':0,'mimeType':'image/png'}],
             'nodes':[{'name':'triangle','mesh':0}],'meshes':[{'primitives':[{'attributes':{'POSITION':0}}]}],
             'scenes':[{'nodes':[0]}],'scene':0}
        j=json.dumps(doc).encode();j+=b' '*(-len(j)%4);b=binary+b'\0'*(-len(binary)%4)
        p.write_bytes(struct.pack('<III',0x46546c67,2,28+len(j)+len(b))+struct.pack('<II',len(j),0x4e4f534a)+j+struct.pack('<II',len(b),0x004e4942)+b)
        return geometry,image

    def test_relocated_geometry_and_shared_images_are_byte_exact(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'a.glb';geometry,image=self.fixture(src);tex=root/'textures';tex.mkdir()
            for name in ['a','b']:
                dst=root/'assets'/name/(name+'.gltf');r=pack.convert(src,dst,tex);self.assertTrue(r['lossless_views_verified'])
                doc=json.loads(dst.read_text());self.assertEqual(doc['accessors'][0]['bufferView'],0)
                self.assertEqual(dst.with_suffix('.bin').read_bytes(),geometry)
                self.assertEqual((dst.parent/doc['images'][0]['uri']).read_bytes(),image)
            self.assertEqual(len(list(tex.iterdir())),1)

    def test_rejects_truncated_source_before_output(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'a.glb';self.fixture(src);src.write_bytes(src.read_bytes()[:-2])
            with self.assertRaises(AssertionError):pack.read_glb(src)

    def test_existing_hash_collision_or_corruption_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as t:
            root=Path(t);src=root/'a.glb';_,im=self.fixture(src);tex=root/'textures';tex.mkdir();bad=tex/(pack.sha(im)+'.png');bad.write_bytes(b'corrupt')
            with self.assertRaises(AssertionError):pack.convert(src,root/'assets/a/a.gltf',tex)
            self.assertEqual(bad.read_bytes(),b'corrupt')

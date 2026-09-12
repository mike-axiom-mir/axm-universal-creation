"""The local inspector server exposes a bounded model, not the workspace."""
import importlib.util
from http.server import ThreadingHTTPServer
from pathlib import Path
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.request import urlopen

ROOT=Path(__file__).resolve().parents[1]
SPEC=importlib.util.spec_from_file_location("character_inspector",ROOT/"tools"/"serve_character_inspector.py")
INSPECTOR=importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(INSPECTOR)


class CharacterInspectorTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        for lod in range(3):
            (self.root/f"AXM_OOPS_LOD{lod}.glb").write_bytes(f"glTF{lod}".encode())
        (self.root/"private.txt").write_text("not an inspector asset")
        self.server=ThreadingHTTPServer(("127.0.0.1",0),INSPECTOR.create_handler(self.root))
        self.worker=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.worker.start()
        self.addCleanup(self.close)
        self.url=f"http://127.0.0.1:{self.server.server_port}"

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.worker.join(timeout=3)

    def test_explicit_assets_and_headers(self):
        with urlopen(self.url+"/AXM_OOPS_LOD2.glb") as response:
            self.assertEqual(response.read(),b"glTF2")
            self.assertEqual(response.headers["Content-Type"],"model/gltf-binary")
            self.assertEqual(response.headers["X-Content-Type-Options"],"nosniff")
        with urlopen(self.url+"/") as response:
            self.assertIn(b"AXM",response.read())
        with urlopen(self.url+"/inspection_controls.js") as response:
            body=response.read()
            self.assertIn(b"InspectionInputRouter",body)
            self.assertEqual(response.headers["Content-Type"],"text/javascript; charset=utf-8")

    def test_no_directory_listing_or_arbitrary_files(self):
        for path in ("/private.txt","/../private.txt","/%2e%2e/private.txt","/textures/","/AGENTS.md","/inspection_controls.test.mjs"):
            with self.assertRaises(HTTPError) as error:
                urlopen(self.url+path)
            self.assertEqual(error.exception.code,404)

    def test_incomplete_model_is_rejected_before_serving(self):
        with tempfile.TemporaryDirectory() as empty:
            with self.assertRaises(FileNotFoundError):
                INSPECTOR.create_handler(Path(empty))


if __name__=="__main__":
    unittest.main()

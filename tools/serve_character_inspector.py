"""Serve only the character inspector and a selected local character's GLBs."""
from __future__ import annotations

import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


def create_handler(directory: Path):
    directory=directory.resolve(strict=True)
    static=Path(__file__).resolve().parent/"character_inspector"
    routes={"/":(static/"index.html","text/html; charset=utf-8"),
            "/index.html":(static/"index.html","text/html; charset=utf-8"),
            "/viewer.js":(static/"viewer.js","text/javascript; charset=utf-8")}
    for lod in range(3):
        path=(directory/f"AXM_OOPS_LOD{lod}.glb").resolve(strict=True)
        if not path.is_relative_to(directory):
            raise ValueError("model symlink escapes selected character directory")
        routes[f"/AXM_OOPS_LOD{lod}.glb"]=(path,"model/gltf-binary")

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            route=routes.get(urlsplit(self.path).path)
            if route is None:
                self.send_error(404)
                return
            path,mime=route
            self.send_response(200)
            self.send_header("Content-Type",mime)
            self.send_header("Content-Length",str(path.stat().st_size))
            self.send_header("Cache-Control","no-store")
            self.send_header("X-Content-Type-Options","nosniff")
            self.send_header("Referrer-Policy","no-referrer")
            self.end_headers()
            try:
                with path.open("rb") as source:
                    while chunk:=source.read(1024*1024):
                        self.wfile.write(chunk)
            except (BrokenPipeError,ConnectionResetError):
                pass
    return Handler


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("directory",type=Path)
    parser.add_argument("--port",type=int,default=8769)
    args=parser.parse_args()
    server=ThreadingHTTPServer(("127.0.0.1",args.port),create_handler(args.directory))
    print(f"Local character inspector: http://127.0.0.1:{server.server_port}/",flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__=="__main__":
    main()

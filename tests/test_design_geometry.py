from __future__ import annotations

import base64
import hashlib
import json
import os
import socket
import stat
import struct
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.design_geometry import (
    CDP_GEOMETRY_SCHEMA,
    DesignGeometryError,
    _normalize_geometry,
    capture_cdp_geometry,
)
from axm_uc.design_observer import judge_rendered_design
from axm_uc.machine import UniversalCreationMachine


GEOMETRY_FIXTURE = {
    "schema": CDP_GEOMETRY_SCHEMA,
    "method": "fixture",
    "limits": {
        "geometry_elements": 128,
        "text_runs": 64,
        "overlap_elements": 64,
        "overlap_pairs_returned": 128,
    },
    "document": {
        "viewport_width": 800,
        "viewport_height": 600,
        "device_pixel_ratio": 1,
        "scroll_width": 800,
        "scroll_height": 900,
        "horizontal_overflow": False,
    },
    "geometry": {
        "visible_candidate_count": 3,
        "element_count_observed": 3,
        "truncated": False,
        "ancestor_clipped_element_count": 1,
        "own_scroll_overflow_element_count": 1,
        "outside_horizontal_viewport_count": 0,
        "elements": [
            {
                "ref": {"dom_index": 3, "tag": "main", "id": "shell"},
                "rect": {"x": 0, "y": 0, "width": 800, "height": 600, "right": 800, "bottom": 600},
                "position": "static",
                "z_index": "auto",
                "overflow_x": "hidden",
                "overflow_y": "visible",
                "client_width": 800,
                "client_height": 600,
                "scroll_width": 800,
                "scroll_height": 600,
                "own_scroll_overflow_x": False,
                "own_scroll_overflow_y": False,
                "outside_horizontal_viewport": False,
                "ancestor_clipping": {"x": False, "y": False, "ancestor_count": 0, "ancestors": []},
            }
        ],
    },
    "overlap": {
        "scanned_element_count": 3,
        "pair_count": 5,
        "returned_pair_count": 1,
        "truncated": True,
        "pairs": [
            {
                "first": {"dom_index": 4, "tag": "div", "id": "a"},
                "second": {"dom_index": 5, "tag": "div", "id": "b"},
                "intersection": {"width": 20, "height": 10, "area": 200},
                "first_area_fraction": 0.1,
                "second_area_fraction": 0.2,
            }
        ],
    },
    "text_geometry": {
        "candidate_count": 1,
        "run_count": 1,
        "truncated": False,
        "ancestor_clipped_run_count": 1,
        "runs": [
            {
                "ref": {"dom_index": 6, "tag": "p", "id": "copy"},
                "text_length": 12,
                "font_size_px": 16,
                "line_height_px": 24,
                "line_box_count": 2,
                "line_boxes": [
                    {"x": 20, "y": 40, "width": 160, "height": 24, "right": 180, "bottom": 64},
                    {"x": 20, "y": 64, "width": 120, "height": 24, "right": 140, "bottom": 88},
                ],
                "ancestor_clipping": {"x": False, "y": True, "ancestor_count": 1, "ancestors": [{"tag": "div", "id": "clip", "x": False, "y": True}]},
                "own_scroll_overflow_x": False,
                "own_scroll_overflow_y": False,
            }
        ],
    },
    "truth_boundary": {
        "rectangles_and_line_boxes_observed": True,
        "overlap_is_quality_failure": False,
        "clipping_is_quality_failure": False,
        "semantic_component_roles_inferred": False,
        "spacing_quality_inferred": False,
        "hierarchy_quality_inferred": False,
        "aesthetic_quality_inferred": False,
        "text_content_retained": False,
    },
}


FAKE_CDP_GEOMETRY_BROWSER = r'''#!/usr/bin/env python3
import base64
import hashlib
import json
import os
import socket
import struct
import sys

GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
profile = None
target = None
for arg in sys.argv[1:]:
    if arg.startswith("--user-data-dir="):
        profile = arg.split("=", 1)[1]
    elif arg.startswith("file://"):
        target = arg
if profile is None or target is None:
    raise SystemExit(2)

fixture = json.loads(''' + repr(json.dumps(GEOMETRY_FIXTURE, separators=(",", ":"))) + r''')
listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", 0))
listener.listen(8)
port = listener.getsockname()[1]
os.makedirs(profile, exist_ok=True)
with open(os.path.join(profile, "DevToolsActivePort"), "w", encoding="utf-8") as handle:
    handle.write(str(port) + "\n/devtools/browser/fake\n")

def recv_exact(conn, count):
    data = bytearray()
    while len(data) < count:
        chunk = conn.recv(count - len(data))
        if not chunk:
            raise EOFError
        data.extend(chunk)
    return bytes(data)

def recv_frame(conn):
    first, second = recv_exact(conn, 2)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", recv_exact(conn, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", recv_exact(conn, 8))[0]
    mask = recv_exact(conn, 4) if second & 0x80 else None
    payload = recv_exact(conn, length)
    if mask:
        payload = bytes(value ^ mask[index % 4] for index, value in enumerate(payload))
    return first & 0x0F, payload

def send_frame(conn, payload):
    if isinstance(payload, str):
        payload = payload.encode("utf-8")
    length = len(payload)
    if length < 126:
        header = bytes([0x81, length])
    elif length <= 65535:
        header = bytes([0x81, 126]) + struct.pack("!H", length)
    else:
        header = bytes([0x81, 127]) + struct.pack("!Q", length)
    conn.sendall(header + payload)

def cdp_result(method, params):
    if method in {"Page.enable", "Runtime.enable", "Page.bringToFront", "Emulation.setDeviceMetricsOverride"}:
        return {}
    if method == "Browser.getVersion":
        return {"protocolVersion": "1.3", "product": "Chrome/FakeGeometry-1.0", "userAgent": "AXM Fake Geometry"}
    if method == "Page.captureScreenshot":
        return {"data": base64.b64encode(b"\x89PNG\r\n\x1a\nAXM-CDP-GEOMETRY-FIXTURE").decode("ascii")}
    if method == "Runtime.evaluate":
        expression = params.get("expression", "")
        if expression == "document.readyState":
            return {"result": {"type": "string", "value": "complete"}}
        return {"result": {"type": "object", "value": fixture}}
    return {}

while True:
    conn, _addr = listener.accept()
    with conn:
        request = bytearray()
        while b"\r\n\r\n" not in request:
            chunk = conn.recv(4096)
            if not chunk:
                break
            request.extend(chunk)
        text = bytes(request).decode("latin-1", "replace")
        first = text.split("\r\n", 1)[0]
        path = first.split(" ")[1] if " " in first else "/"
        if path == "/json/list":
            body = json.dumps([{"type": "page", "url": target, "webSocketDebuggerUrl": f"ws://127.0.0.1:{port}/devtools/page/1"}]).encode("utf-8")
            conn.sendall(b"HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: " + str(len(body)).encode("ascii") + b"\r\nConnection: close\r\n\r\n" + body)
            continue
        if path != "/devtools/page/1":
            conn.sendall(b"HTTP/1.1 404 Not Found\r\nContent-Length: 0\r\n\r\n")
            continue
        key = ""
        for line in text.split("\r\n"):
            if line.lower().startswith("sec-websocket-key:"):
                key = line.split(":", 1)[1].strip()
        accept = base64.b64encode(hashlib.sha1((key + GUID).encode("ascii")).digest()).decode("ascii")
        conn.sendall((
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode("ascii"))
        while True:
            try:
                opcode, payload = recv_frame(conn)
            except EOFError:
                break
            if opcode == 8:
                break
            if opcode != 1:
                continue
            request_body = json.loads(payload.decode("utf-8"))
            result = cdp_result(request_body.get("method", ""), request_body.get("params") or {})
            send_frame(conn, json.dumps({"id": request_body["id"], "result": result}, separators=(",", ":")))
'''


class DesignGeometryTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.cdp-geometry",
            "version": "0.10.0",
            "purpose": "CDP geometry fixture",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [], "radii": [], "typography": [], "custom": [],
            },
            "layout": {"breakpoints": [], "principles": ["single viewport fixture"]},
            "components": [],
            "motion": {"durations": [], "easings": [], "reduced_motion_strategy": "none"},
            "materials": {"signals": [], "principles": []},
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": False,
                "reduced_motion_required": False,
                "responsive_required": False,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture"},
        })
        return compose_design_plan(genome, {
            "goal": "geometry-observed local design",
            "required_roles": [],
            "components": [],
            "viewports": ["desktop"],
            "contrast_pairs": [{"foreground": "text", "background": "surface"}],
        })

    @staticmethod
    def write_browser(path: Path) -> None:
        path.write_text(FAKE_CDP_GEOMETRY_BROWSER, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_geometry_normalization_keeps_overlap_and_clipping_as_facts(self):
        normalized = _normalize_geometry(GEOMETRY_FIXTURE)
        self.assertEqual(normalized["geometry"]["ancestor_clipped_element_count"], 1)
        self.assertEqual(normalized["overlap"]["pair_count"], 5)
        self.assertEqual(normalized["text_geometry"]["run_count"], 1)
        self.assertFalse(normalized["truth_boundary"]["overlap_is_quality_failure"])
        self.assertFalse(normalized["truth_boundary"]["clipping_is_quality_failure"])
        self.assertFalse(normalized["truth_boundary"]["aesthetic_quality_inferred"])

    def test_cdp_geometry_materializes_screenshot_and_computed_geometry_without_quality_claim(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body><main id='shell'><p id='copy'>Geometry evidence</p></main></body></html>", encoding="utf-8")
            browser = parent / "fake-cdp-geometry-browser"
            self.write_browser(browser)
            output = parent / "geometry"
            result = capture_cdp_geometry(
                ROOT,
                plan,
                target,
                output,
                browser,
                {"id": "desktop", "width": 800, "height": 600, "device_pixel_ratio": 1},
                timeout_seconds=10,
            )

            self.assertEqual(result["truth_status"], "LOCAL_CDP_LAYOUT_GEOMETRY_EVIDENCE_MATERIALIZED")
            self.assertEqual(result["receipt"]["schema"], CDP_GEOMETRY_SCHEMA)
            self.assertEqual(result["receipt"]["geometry_summary"]["overlap_pair_count"], 5)
            self.assertEqual(result["receipt"]["geometry_summary"]["ancestor_clipped_element_count"], 1)
            self.assertFalse(result["receipt"]["geometry_summary"]["quality_verdict_generated"])
            self.assertFalse(result["receipt"]["truth_boundary"]["overlap_classified_as_defect"])
            self.assertFalse(result["receipt"]["truth_boundary"]["clipping_classified_as_defect"])
            self.assertTrue((output / "desktop.png").is_file())
            self.assertTrue((output / "desktop.layout-geometry.json").is_file())
            self.assertTrue((output / "cdp-geometry.capture.json").is_file())

            capture = result["observation"]["captures"][0]
            self.assertEqual(capture["measurements"]["horizontal_overflow"], False)
            self.assertEqual({artifact["kind"] for artifact in capture["artifacts"]}, {"screenshot", "computed-style"})
            geometry_assessment = next(row for row in capture["assessments"] if row["id"] == "layout-geometry-integrity")
            self.assertEqual(geometry_assessment["status"], "PASS")
            self.assertIn("evidence integrity only", geometry_assessment["basis"])

            judgment = judge_rendered_design(plan, result["observation"], required_assessments=[])
            by_gate = {row["gate"]: row for row in judgment["gates"]}
            self.assertEqual(by_gate["screenshot-evidence-coverage"]["status"], "PASS")
            self.assertEqual(by_gate["horizontal-overflow"]["status"], "PASS")
            self.assertNotEqual(judgment["status"], "FAIL")
            self.assertNotIn("layout-geometry-integrity", judgment["repair_direction"])

    def test_live_machine_routes_geometry_and_url_target_fails_closed(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body>AXM</body></html>", encoding="utf-8")
            browser = parent / "fake-cdp-geometry-browser"
            self.write_browser(browser)
            result = UniversalCreationMachine(ROOT).create({
                "kind": "capture-design-cdp-geometry",
                "inputs": {
                    "operation": "capture-cdp-geometry",
                    "plan": plan,
                    "target": str(target),
                    "path": str(parent / "geometry"),
                    "browser_executable": str(browser),
                    "viewport": {"id": "desktop", "width": 800, "height": 600},
                    "timeout_seconds": 10,
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-DESIGN-FABRIC")
            self.assertEqual(result["result"]["receipt"]["schema"], CDP_GEOMETRY_SCHEMA)

            with self.assertRaises(DesignGeometryError):
                capture_cdp_geometry(
                    ROOT,
                    plan,
                    "https://example.com",
                    parent / "blocked",
                    browser,
                    {"id": "desktop", "width": 800, "height": 600},
                )


if __name__ == "__main__":
    unittest.main()

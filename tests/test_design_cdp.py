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
import textwrap
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from axm_uc.design_cdp import (
    CDP_SEMANTICS_SCHEMA,
    DesignCdpError,
    capture_cdp_semantics,
    summarize_accessibility_tree,
)
from axm_uc.design_fabric import DESIGN_GENOME_SCHEMA, compose_design_plan, validate_design_genome
from axm_uc.machine import UniversalCreationMachine


FAKE_CDP_BROWSER = r'''#!/usr/bin/env python3
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

listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
listener.bind(("127.0.0.1", 0))
listener.listen(8)
port = listener.getsockname()[1]
os.makedirs(profile, exist_ok=True)
with open(os.path.join(profile, "DevToolsActivePort"), "w", encoding="utf-8") as handle:
    handle.write(str(port) + "\n/devtools/browser/fake\n")

state = {"tab": 0}

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
    if method in {"Page.enable", "Runtime.enable", "Accessibility.enable", "Page.bringToFront", "Emulation.setDeviceMetricsOverride"}:
        return {}
    if method == "Browser.getVersion":
        return {"protocolVersion": "1.3", "product": "Chrome/FakeCDP-1.0", "userAgent": "AXM Fake CDP"}
    if method == "Accessibility.getFullAXTree":
        return {"nodes": [
            {"nodeId": "1", "ignored": False, "role": {"value": "RootWebArea"}, "name": {"value": "AXM"}, "properties": []},
            {"nodeId": "2", "ignored": False, "role": {"value": "button"}, "name": {"value": "First"}, "properties": [{"name": "focusable", "value": {"value": True}}]},
            {"nodeId": "3", "ignored": False, "role": {"value": "link"}, "name": {"value": ""}, "properties": [{"name": "focusable", "value": {"value": True}}]},
        ]}
    if method == "Input.dispatchKeyEvent":
        if params.get("type") == "rawKeyDown" and params.get("key") == "Tab":
            state["tab"] += 1
        return {}
    if method == "Runtime.evaluate":
        expression = params.get("expression", "")
        if expression == "document.readyState":
            return {"result": {"type": "string", "value": "complete"}}
        current = state["tab"]
        if current % 2:
            value = {"kind": "element", "tag": "button", "id": "first", "role": "", "tabindex": None, "aria_label": "First", "text": "First", "visible": True, "focus_visible": True, "rect": {"x": 10, "y": 10, "width": 80, "height": 30}}
        else:
            value = {"kind": "element", "tag": "a", "id": "second", "role": "", "tabindex": None, "aria_label": "", "text": "Second", "visible": True, "focus_visible": True, "rect": {"x": 10, "y": 50, "width": 80, "height": 30}}
        return {"result": {"type": "object", "value": value}}
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
        response = (
            "HTTP/1.1 101 Switching Protocols\r\n"
            "Upgrade: websocket\r\nConnection: Upgrade\r\n"
            f"Sec-WebSocket-Accept: {accept}\r\n\r\n"
        ).encode("ascii")
        conn.sendall(response)
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
            method = request_body.get("method", "")
            params = request_body.get("params") or {}
            result = cdp_result(method, params)
            send_frame(conn, json.dumps({"id": request_body["id"], "result": result}, separators=(",", ":")))
'''


class DesignCdpTests(unittest.TestCase):
    @staticmethod
    def plan() -> dict:
        genome = validate_design_genome({
            "schema": DESIGN_GENOME_SCHEMA,
            "id": "axm.test.cdp",
            "version": "0.9.0",
            "purpose": "CDP semantics fixture",
            "tokens": {
                "colors": [
                    {"id": "text", "value": "#FFFFFF", "usage": "foreground"},
                    {"id": "surface", "value": "#000000", "usage": "background"},
                ],
                "spacing": [], "radii": [], "typography": [], "custom": [],
            },
            "layout": {"breakpoints": [], "principles": ["single viewport fixture"]},
            "components": [{
                "id": "primary-button",
                "description": "Explicit primary control.",
                "roles": ["primary-action"],
                "tags": ["control"],
                "interactive": True,
                "states": ["default", "focus"],
                "source_status": "explicit-test-semantics",
            }],
            "motion": {"durations": [], "easings": [], "reduced_motion_strategy": "none"},
            "materials": {"signals": [], "principles": []},
            "quality_gates": {
                "minimum_text_contrast": 4.5,
                "focus_visible_required": True,
                "reduced_motion_required": False,
                "responsive_required": False,
                "policy_origin": "AXM_TEST_POLICY",
            },
            "provenance": {"kind": "test-fixture"},
        })
        return compose_design_plan(genome, {
            "goal": "CDP-observed local design",
            "required_roles": ["primary-action"],
            "components": [],
            "viewports": ["desktop"],
            "contrast_pairs": [{"foreground": "text", "background": "surface"}],
        })

    @staticmethod
    def write_browser(path: Path) -> None:
        path.write_text(FAKE_CDP_BROWSER, encoding="utf-8")
        path.chmod(path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    def test_accessibility_tree_summary_keeps_conformance_separate(self):
        summary = summarize_accessibility_tree({"nodes": [
            {"ignored": False, "role": {"value": "button"}, "name": {"value": "Go"}, "properties": [{"name": "focusable", "value": {"value": True}}]},
            {"ignored": True, "role": {"value": "generic"}, "name": {"value": ""}, "properties": []},
            {"ignored": False, "role": {"value": "link"}, "name": {"value": ""}, "properties": [{"name": "focusable", "value": {"value": True}}]},
        ]})
        self.assertEqual(summary["node_count"], 3)
        self.assertEqual(summary["ignored_node_count"], 1)
        self.assertEqual(summary["focusable_node_count"], 2)
        self.assertEqual(summary["unnamed_focusable_node_count"], 1)
        self.assertFalse(summary["claim_boundary"]["wcag_conformance_inferred"])

    def test_fake_cdp_browser_materializes_real_semantic_artifacts_and_tab_evidence(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body><button id='first'>First</button><a id='second' href='#'>Second</a></body></html>", encoding="utf-8")
            browser = parent / "fake-cdp-browser"
            self.write_browser(browser)
            output = parent / "capture"
            result = capture_cdp_semantics(
                ROOT,
                plan,
                target,
                output,
                browser,
                {"id": "desktop", "width": 1280, "height": 720, "device_pixel_ratio": 1},
                keyboard_tab_steps=2,
                timeout_seconds=10,
            )

            self.assertEqual(result["truth_status"], "LOCAL_CDP_SEMANTIC_EVIDENCE_MATERIALIZED")
            self.assertEqual(result["receipt"]["schema"], CDP_SEMANTICS_SCHEMA)
            self.assertEqual(result["receipt"]["browser"]["product"], "Chrome/FakeCDP-1.0")
            self.assertEqual(result["receipt"]["accessibility_tree"]["focusable_node_count"], 2)
            self.assertEqual(result["receipt"]["accessibility_tree"]["unnamed_focusable_node_count"], 1)
            self.assertEqual(result["receipt"]["keyboard_tab_traversal"]["observed_steps"], 2)
            self.assertTrue(result["receipt"]["keyboard_tab_traversal"]["all_observed_focus_targets_visible"])
            self.assertFalse(result["receipt"]["keyboard_tab_traversal"]["truth_boundary"]["trusted_human_keyboard_input"])
            self.assertTrue((output / "desktop.accessibility-tree.json").is_file())
            self.assertTrue((output / "desktop.keyboard-tab.json").is_file())
            self.assertTrue((output / "cdp.capture.json").is_file())

            observation = result["observation"]
            capture = observation["captures"][0]
            self.assertEqual(capture["measurements"]["focus_visible"], True)
            self.assertEqual(capture["measurements"]["interaction_error_count"], 0)
            self.assertTrue(observation["evidence_boundary"]["artifact_bytes_fetched_or_verified"])
            self.assertFalse(observation["evidence_boundary"]["trusted_human_input_claimed"])
            self.assertFalse(observation["evidence_boundary"]["accessibility_conformance_claimed"])

    def test_live_machine_routes_cdp_observer_and_fail_closed_boundaries(self):
        plan = self.plan()
        with tempfile.TemporaryDirectory() as td:
            parent = Path(td)
            target = parent / "index.html"
            target.write_text("<!doctype html><html><body><button>Go</button></body></html>", encoding="utf-8")
            browser = parent / "fake-cdp-browser"
            self.write_browser(browser)
            result = UniversalCreationMachine(ROOT).create({
                "kind": "capture-design-cdp-semantics",
                "inputs": {
                    "operation": "capture-cdp-semantics",
                    "plan": plan,
                    "target": str(target),
                    "path": str(parent / "capture"),
                    "browser_executable": str(browser),
                    "viewport": {"id": "desktop", "width": 800, "height": 600},
                    "keyboard_tab_steps": 1,
                    "timeout_seconds": 10,
                },
            })
            self.assertEqual(result["type"], "CREATION_RESULT", result)
            self.assertEqual(result["capability"], "AXM-CAP-DESIGN-FABRIC")
            self.assertEqual(result["result"]["receipt"]["schema"], CDP_SEMANTICS_SCHEMA)

            with self.assertRaises(DesignCdpError):
                capture_cdp_semantics(
                    ROOT,
                    plan,
                    "https://example.com",
                    parent / "url-output",
                    browser,
                    {"id": "desktop", "width": 800, "height": 600},
                )
            with self.assertRaises(DesignCdpError):
                capture_cdp_semantics(
                    ROOT,
                    plan,
                    target,
                    parent / "too-many-tabs",
                    browser,
                    {"id": "desktop", "width": 800, "height": 600},
                    keyboard_tab_steps=65,
                )


if __name__ == "__main__":
    unittest.main()

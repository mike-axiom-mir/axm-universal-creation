from __future__ import annotations

import base64
import hashlib
import json
import os
import shutil
import socket
import struct
import subprocess
import tempfile
import time
import urllib.request
from collections import Counter
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from .design_fabric import DESIGN_PLAN_SCHEMA
from .design_observer import RENDER_OBSERVATION_SCHEMA, record_render_observation


CDP_SEMANTICS_SCHEMA = "axm.design-cdp-semantics/v0.1"
MAX_TIMEOUT_SECONDS = 120
MAX_TAB_STEPS = 64
_WS_GUID = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"


class DesignCdpError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _bytes_digest(data: bytes) -> str:
    return f"sha256:{hashlib.sha256(data).hexdigest()}"


def _text(value: Any, label: str, maximum: int = 2000) -> str:
    if isinstance(value, os.PathLike):
        value = os.fspath(value)
    if not isinstance(value, str) or not value.strip():
        raise DesignCdpError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignCdpError(f"{label} exceeds its {maximum}-character bound")
    return result


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise DesignCdpError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _resolve_path(root: Path, value: Any, label: str) -> Path:
    path = Path(_text(value, label, 1000)).expanduser()
    if not path.is_absolute():
        path = Path(root).resolve() / path
    return path.resolve()


def _machine_body_path(root: Path, target: Path) -> bool:
    root = Path(root).resolve()
    target = Path(target).resolve()
    try:
        relative = target.relative_to(root)
    except ValueError:
        try:
            root.relative_to(target)
        except ValueError:
            return False
        return True
    if not relative.parts:
        return True
    return relative.parts[0] not in {"creations", ".axm-build"}


def _resolve_browser(value: Any) -> Path:
    requested = _text(value, "browser_executable", 1000)
    direct = Path(requested).expanduser()
    if direct.is_file():
        resolved = direct.resolve()
    else:
        found = shutil.which(requested)
        if found is None:
            raise DesignCdpError(
                "CDP browser executable is unavailable",
                {"browser_executable": requested, "status": "HOLD_CDP_BROWSER_EXECUTOR_UNAVAILABLE"},
            )
        resolved = Path(found).resolve()
    if not os.access(resolved, os.X_OK):
        raise DesignCdpError("CDP browser executable is not executable", {"path": str(resolved)})
    return resolved


def _target_html(root: Path, value: Any) -> Path:
    text = _text(value, "target", 1000)
    if "://" in text:
        raise DesignCdpError(
            "CDP observer accepts local HTML paths only; URL/network targets are unsupported",
            {"target": text},
        )
    target = _resolve_path(root, text, "target")
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() or target.suffix.casefold() not in {".html", ".htm"}:
        raise DesignCdpError("CDP target must resolve to a local HTML file", {"target": str(target)})
    return target.resolve()


def _viewport(plan: dict[str, Any], raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or not {"id", "width", "height"}.issubset(raw) or set(raw) - {"id", "width", "height", "device_pixel_ratio"}:
        raise DesignCdpError("viewport must use id, width, height, and optional device_pixel_ratio")
    viewport_id = _text(raw["id"], "viewport.id", 128)
    if viewport_id not in (plan.get("viewports") or []):
        raise DesignCdpError(
            "viewport id is not declared by the design plan",
            {"viewport": viewport_id, "plan_viewports": plan.get("viewports")},
        )
    width = _integer(raw["width"], "viewport.width", 1, 100_000)
    height = _integer(raw["height"], "viewport.height", 1, 100_000)
    ratio = raw.get("device_pixel_ratio", 1)
    if isinstance(ratio, bool) or not isinstance(ratio, (int, float)) or not 0.1 <= float(ratio) <= 8:
        raise DesignCdpError("viewport.device_pixel_ratio must be between 0.1 and 8")
    return {"id": viewport_id, "width": width, "height": height, "device_pixel_ratio": float(ratio)}


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    chunks = bytearray()
    while len(chunks) < length:
        chunk = sock.recv(length - len(chunks))
        if not chunk:
            raise DesignCdpError("CDP websocket closed unexpectedly")
        chunks.extend(chunk)
    return bytes(chunks)


def _ws_send(sock: socket.socket, payload: bytes, opcode: int = 0x1) -> None:
    first = 0x80 | opcode
    length = len(payload)
    mask = os.urandom(4)
    if length < 126:
        header = bytes([first, 0x80 | length])
    elif length <= 0xFFFF:
        header = bytes([first, 0x80 | 126]) + struct.pack("!H", length)
    else:
        header = bytes([first, 0x80 | 127]) + struct.pack("!Q", length)
    masked = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    sock.sendall(header + mask + masked)


def _ws_recv(sock: socket.socket) -> tuple[int, bytes]:
    first, second = _recv_exact(sock, 2)
    fin = bool(first & 0x80)
    opcode = first & 0x0F
    masked = bool(second & 0x80)
    length = second & 0x7F
    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    if length > 16_000_000:
        raise DesignCdpError("CDP websocket frame exceeds the 16 MB bound", {"bytes": length})
    mask = _recv_exact(sock, 4) if masked else None
    payload = _recv_exact(sock, length)
    if mask is not None:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    if not fin:
        raise DesignCdpError("fragmented CDP websocket frames are unsupported by the minimal observer")
    return opcode, payload


def _ws_connect(url: str, timeout: int) -> socket.socket:
    parsed = urlparse(url)
    if parsed.scheme != "ws" or parsed.hostname not in {"127.0.0.1", "localhost"} or not parsed.port:
        raise DesignCdpError("CDP websocket endpoint must be local ws://127.0.0.1 or localhost", {"url": url})
    sock = socket.create_connection((parsed.hostname, parsed.port), timeout=timeout)
    sock.settimeout(timeout)
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    path = parsed.path or "/"
    if parsed.query:
        path += "?" + parsed.query
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {parsed.hostname}:{parsed.port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n\r\n"
    ).encode("ascii")
    sock.sendall(request)
    response = bytearray()
    while b"\r\n\r\n" not in response and len(response) < 64_000:
        chunk = sock.recv(4096)
        if not chunk:
            break
        response.extend(chunk)
    header_text = bytes(response).decode("latin-1", "replace")
    first_line = header_text.split("\r\n", 1)[0]
    if " 101 " not in first_line:
        sock.close()
        raise DesignCdpError("CDP websocket handshake failed", {"status_line": first_line})
    headers: dict[str, str] = {}
    for line in header_text.split("\r\n")[1:]:
        if ":" in line:
            name, value = line.split(":", 1)
            headers[name.strip().casefold()] = value.strip()
    expected = base64.b64encode(hashlib.sha1((key + _WS_GUID).encode("ascii")).digest()).decode("ascii")
    if headers.get("sec-websocket-accept") != expected:
        sock.close()
        raise DesignCdpError("CDP websocket accept key is invalid")
    return sock


class _CdpConnection:
    def __init__(self, url: str, timeout: int):
        self.sock = _ws_connect(url, timeout)
        self.next_id = 1

    def close(self) -> None:
        try:
            _ws_send(self.sock, b"", opcode=0x8)
        except Exception:
            pass
        self.sock.close()

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        request_id = self.next_id
        self.next_id += 1
        message: dict[str, Any] = {"id": request_id, "method": method}
        if params is not None:
            message["params"] = params
        _ws_send(self.sock, _canonical(message))
        while True:
            opcode, payload = _ws_recv(self.sock)
            if opcode == 0x8:
                raise DesignCdpError("CDP websocket closed while awaiting a response", {"method": method})
            if opcode == 0x9:
                _ws_send(self.sock, payload, opcode=0xA)
                continue
            if opcode != 0x1:
                continue
            try:
                body = json.loads(payload.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise DesignCdpError("CDP websocket returned invalid JSON", {"method": method}) from exc
            if not isinstance(body, dict) or body.get("id") != request_id:
                continue
            if "error" in body:
                raise DesignCdpError("CDP command failed", {"method": method, "error": body.get("error")})
            result = body.get("result", {})
            return result if isinstance(result, dict) else {}


def _wait_devtools_port(profile: Path, process: subprocess.Popen[Any], timeout: int) -> int:
    deadline = time.monotonic() + timeout
    port_file = profile / "DevToolsActivePort"
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise DesignCdpError(
                "CDP browser exited before publishing DevToolsActivePort",
                {"returncode": process.returncode, "status": "HOLD_CDP_BROWSER_START_FAILED"},
            )
        if port_file.is_file():
            lines = port_file.read_text(encoding="utf-8", errors="replace").splitlines()
            if lines:
                try:
                    port = int(lines[0])
                except ValueError:
                    port = 0
                if 1 <= port <= 65535:
                    return port
        time.sleep(0.05)
    raise DesignCdpError("timed out waiting for DevToolsActivePort", {"timeout_seconds": timeout, "status": "HOLD_CDP_ENDPOINT_UNAVAILABLE"})


def _page_endpoint(port: int, target_uri: str, timeout: int) -> str:
    deadline = time.monotonic() + timeout
    url = f"http://127.0.0.1:{port}/json/list"
    last_error: str | None = None
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=min(timeout, 2)) as response:
                raw = json.loads(response.read().decode("utf-8"))
            if isinstance(raw, list):
                pages = [row for row in raw if isinstance(row, dict) and row.get("type") == "page" and isinstance(row.get("webSocketDebuggerUrl"), str)]
                exact = [row for row in pages if row.get("url") == target_uri]
                selected = exact[0] if exact else pages[0] if pages else None
                if selected is not None:
                    return str(selected["webSocketDebuggerUrl"])
        except Exception as exc:
            last_error = str(exc)
        time.sleep(0.05)
    raise DesignCdpError(
        "could not resolve a local CDP page endpoint",
        {"port": port, "reason": last_error, "status": "HOLD_CDP_PAGE_ENDPOINT_UNAVAILABLE"},
    )


def _property_bool(node: dict[str, Any], name: str) -> bool | None:
    for row in node.get("properties", []):
        if not isinstance(row, dict) or row.get("name") != name:
            continue
        value = row.get("value")
        if isinstance(value, dict) and isinstance(value.get("value"), bool):
            return value["value"]
    return None


def summarize_accessibility_tree(tree: dict[str, Any]) -> dict[str, Any]:
    nodes = tree.get("nodes") if isinstance(tree, dict) else None
    if not isinstance(nodes, list):
        raise DesignCdpError("Accessibility.getFullAXTree did not return a nodes list")
    roles: Counter[str] = Counter()
    ignored = 0
    focusable = 0
    unnamed_focusable = 0
    for node in nodes:
        if not isinstance(node, dict):
            continue
        if node.get("ignored") is True:
            ignored += 1
        role_body = node.get("role")
        role = role_body.get("value") if isinstance(role_body, dict) else None
        if isinstance(role, str) and role:
            roles[role] += 1
        if _property_bool(node, "focusable") is True:
            focusable += 1
            name_body = node.get("name")
            name = name_body.get("value") if isinstance(name_body, dict) else None
            if not isinstance(name, str) or not name.strip():
                unnamed_focusable += 1
    return {
        "node_count": len(nodes),
        "ignored_node_count": ignored,
        "focusable_node_count": focusable,
        "unnamed_focusable_node_count": unnamed_focusable,
        "role_counts": [{"role": role, "count": count} for role, count in sorted(roles.items())],
        "claim_boundary": {
            "accessibility_tree_captured": True,
            "wcag_conformance_inferred": False,
            "assistive_technology_behavior_proven": False,
            "accessibility_quality_pass_inferred": False,
        },
    }


_FOCUS_EXPRESSION = r"""
(() => {
  const element = document.activeElement;
  if (!(element instanceof Element)) return {kind:"none",focus_visible:null,visible:null};
  const style = getComputedStyle(element);
  const rect = element.getBoundingClientRect();
  const visible = style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
  const outline = style.outlineStyle !== "none" && (Number.parseFloat(style.outlineWidth || "0") || 0) > 0;
  const shadow = Boolean(style.boxShadow && style.boxShadow !== "none");
  return {
    kind:(element === document.body || element === document.documentElement) ? "document" : "element",
    tag:String(element.tagName || "").toLowerCase(),
    id:String(element.id || "").slice(0,120),
    role:String(element.getAttribute("role") || "").slice(0,120),
    tabindex:element.getAttribute("tabindex"),
    aria_label:String(element.getAttribute("aria-label") || "").slice(0,200),
    text:String(element.textContent || "").trim().slice(0,200),
    visible,
    focus_visible:document.activeElement === element && (outline || shadow),
    rect:{x:Math.round(rect.x*1000)/1000,y:Math.round(rect.y*1000)/1000,width:Math.round(rect.width*1000)/1000,height:Math.round(rect.height*1000)/1000}
  };
})()
"""


def _evaluate_value(cdp: _CdpConnection, expression: str) -> Any:
    result = cdp.call("Runtime.evaluate", {"expression": expression, "returnByValue": True, "awaitPromise": True})
    body = result.get("result")
    return body.get("value") if isinstance(body, dict) else None


def _wait_document_ready(cdp: _CdpConnection, timeout: int) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        state = _evaluate_value(cdp, "document.readyState")
        if state in {"interactive", "complete"}:
            return
        time.sleep(0.05)
    raise DesignCdpError("CDP page did not reach interactive/complete readyState", {"status": "HOLD_CDP_PAGE_NOT_READY"})


def _tab_traversal(cdp: _CdpConnection, steps: int) -> dict[str, Any]:
    rows = []
    focus_targets = 0
    focus_visible_targets = 0
    for index in range(steps):
        cdp.call(
            "Input.dispatchKeyEvent",
            {"type": "rawKeyDown", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9},
        )
        cdp.call(
            "Input.dispatchKeyEvent",
            {"type": "keyUp", "key": "Tab", "code": "Tab", "windowsVirtualKeyCode": 9, "nativeVirtualKeyCode": 9},
        )
        value = _evaluate_value(cdp, _FOCUS_EXPRESSION)
        descriptor = value if isinstance(value, dict) else {"kind": "unknown"}
        if descriptor.get("kind") == "element":
            focus_targets += 1
            if descriptor.get("focus_visible") is True:
                focus_visible_targets += 1
        rows.append({"step": index + 1, "key": "Tab", "dispatch": "cdp.Input.dispatchKeyEvent", "active_element": descriptor})
    return {
        "method": "CDP Input.dispatchKeyEvent Tab traversal",
        "requested_steps": steps,
        "observed_steps": len(rows),
        "focus_target_steps": focus_targets,
        "focus_visible_target_steps": focus_visible_targets,
        "all_observed_focus_targets_visible": (focus_visible_targets == focus_targets) if focus_targets else None,
        "steps": rows,
        "truth_boundary": {
            "browser_native_tab_navigation_invoked_via_cdp": True,
            "trusted_human_keyboard_input": False,
            "operating_system_keyboard_event": False,
            "semantic_usability_proven": False,
            "assistive_technology_behavior_proven": False,
        },
    }


def _artifact_bytes(value: Any) -> bytes:
    return (json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n").encode("utf-8")


def capture_cdp_semantics(
    root: Path,
    plan_raw: Any,
    target_raw: Any,
    output_raw: Any,
    browser_raw: Any,
    viewport_raw: Any,
    keyboard_tab_steps: Any = 0,
    timeout_seconds: Any = 20,
) -> dict[str, Any]:
    if not isinstance(plan_raw, dict) or plan_raw.get("schema") != DESIGN_PLAN_SCHEMA or not isinstance(plan_raw.get("plan_digest"), str):
        raise DesignCdpError("capture-cdp-semantics requires an axm.design-plan/v0.1 plan with plan_digest")
    plan = json.loads(json.dumps(plan_raw, ensure_ascii=False, allow_nan=False))
    target = _target_html(root, target_raw)
    output = _resolve_path(root, output_raw, "path")
    if _machine_body_path(root, output):
        raise DesignCdpError("CDP evidence is an ordinary creation and cannot write into the live machine body")
    if output.exists():
        raise DesignCdpError("CDP evidence target already exists; silent replacement is forbidden", {"path": str(output)})
    output.parent.mkdir(parents=True, exist_ok=True)
    browser = _resolve_browser(browser_raw)
    viewport = _viewport(plan, viewport_raw)
    steps = _integer(keyboard_tab_steps, "keyboard_tab_steps", 0, MAX_TAB_STEPS)
    timeout = _integer(timeout_seconds, "timeout_seconds", 1, MAX_TIMEOUT_SECONDS)
    target_uri = target.as_uri()

    process: subprocess.Popen[Any] | None = None
    with tempfile.TemporaryDirectory(prefix=".axm-cdp-profile-", dir=output.parent) as profile_dir, tempfile.TemporaryDirectory(prefix=".axm-cdp-evidence-", dir=output.parent) as stage_dir:
        profile = Path(profile_dir)
        stage = Path(stage_dir)
        command = [
            str(browser),
            "--headless=new",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
            "--remote-debugging-address=127.0.0.1",
            "--remote-debugging-port=0",
            f"--user-data-dir={profile}",
            "--host-resolver-rules=MAP * 0.0.0.0,EXCLUDE localhost",
            f"--window-size={viewport['width']},{viewport['height']}",
            f"--force-device-scale-factor={viewport['device_pixel_ratio']}",
            target_uri,
        ]
        try:
            process = subprocess.Popen(command, cwd=target.parent, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            port = _wait_devtools_port(profile, process, timeout)
            websocket_url = _page_endpoint(port, target_uri, timeout)
            cdp = _CdpConnection(websocket_url, timeout)
            try:
                cdp.call("Page.enable")
                cdp.call("Runtime.enable")
                cdp.call("Accessibility.enable")
                cdp.call("Page.bringToFront")
                cdp.call(
                    "Emulation.setDeviceMetricsOverride",
                    {
                        "width": viewport["width"],
                        "height": viewport["height"],
                        "deviceScaleFactor": viewport["device_pixel_ratio"],
                        "mobile": False,
                    },
                )
                _wait_document_ready(cdp, timeout)
                version = cdp.call("Browser.getVersion")
                ax_tree = cdp.call("Accessibility.getFullAXTree")
                ax_summary = summarize_accessibility_tree(ax_tree)
                tab = _tab_traversal(cdp, steps) if steps else None
            finally:
                cdp.close()
        except OSError as exc:
            raise DesignCdpError("CDP browser could not start", {"reason": str(exc), "status": "HOLD_CDP_BROWSER_START_FAILED"}) from exc
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)

        ax_bytes = _artifact_bytes(ax_tree)
        ax_path = stage / f"{viewport['id']}.accessibility-tree.json"
        ax_path.write_bytes(ax_bytes)
        artifacts = [{
            "kind": "accessibility-tree",
            "digest": _bytes_digest(ax_bytes),
            "uri": ax_path.name,
            "mime_type": "application/json",
            "bytes": len(ax_bytes),
        }]
        assessments = [{
            "id": "accessibility-tree-integrity",
            "status": "PASS" if ax_summary["node_count"] > 0 else "HOLD",
            "confidence": 1.0,
            "basis": "Accessibility.getFullAXTree returned a bounded local browser tree; this proves artifact capture, not accessibility conformance",
        }]
        measurements: dict[str, Any] = {}

        if tab is not None:
            tab_bytes = _artifact_bytes(tab)
            tab_path = stage / f"{viewport['id']}.keyboard-tab.json"
            tab_path.write_bytes(tab_bytes)
            artifacts.append({
                "kind": "interaction-log",
                "digest": _bytes_digest(tab_bytes),
                "uri": tab_path.name,
                "mime_type": "application/json",
                "bytes": len(tab_bytes),
            })
            focus_visible = tab.get("all_observed_focus_targets_visible")
            if isinstance(focus_visible, bool):
                measurements["focus_visible"] = focus_visible
            measurements["interaction_error_count"] = 0
            assessments.append({
                "id": "cdp-tab-traversal-integrity",
                "status": "PASS" if tab["observed_steps"] == steps else "HOLD",
                "confidence": 1.0,
                "basis": "Tab keys were dispatched through Chrome DevTools Protocol and activeElement state was read after each bounded step; events are browser-synthetic, not trusted human keyboard input",
            })

        observation = record_render_observation(
            plan["plan_digest"],
            {
                "kind": "browser-tool",
                "id": "chromium-cdp-semantics",
                "version": str(version.get("product") or version.get("protocolVersion") or "unknown"),
                "basis": "caller-selected local Chromium-compatible browser controlled through a loopback-only Chrome DevTools Protocol endpoint and a fresh temporary browser profile",
            },
            [{
                "viewport": viewport,
                "artifacts": artifacts,
                "measurements": measurements,
                "assessments": assessments,
            }],
        )
        observation["truth_status"] = "OBSERVED_LOCAL_CDP_ACCESSIBILITY_AND_KEYBOARD_EVIDENCE"
        observation["evidence_boundary"]["artifact_bytes_fetched_or_verified"] = True
        observation["evidence_boundary"]["browser_or_screen_control_claimed"] = True
        observation["evidence_boundary"]["trusted_human_input_claimed"] = False
        observation["evidence_boundary"]["accessibility_conformance_claimed"] = False
        for capture in observation["captures"]:
            for artifact in capture["artifacts"]:
                artifact["bytes_verified_or_fetched_by_design_fabric"] = True
        observation["observation_digest"] = _digest({key: value for key, value in observation.items() if key != "observation_digest"})

        receipt = {
            "schema": CDP_SEMANTICS_SCHEMA,
            "truth_status": "LOCAL_CDP_SEMANTIC_EVIDENCE_CAPTURED",
            "plan_digest": plan["plan_digest"],
            "target": {"path": str(target), "uri": target_uri},
            "viewport": viewport,
            "browser": {
                "path": str(browser),
                "product": version.get("product"),
                "protocol_version": version.get("protocolVersion"),
                "user_agent": version.get("userAgent"),
                "loopback_cdp_only": True,
                "fresh_temporary_profile": True,
            },
            "accessibility_tree": ax_summary,
            "keyboard_tab_traversal": tab,
            "observation": observation,
            "limitations": [
                "Accessibility.getFullAXTree is browser accessibility semantics, not a WCAG conformance verdict or proof of assistive-technology behavior",
                "Tab traversal is dispatched through CDP Input.dispatchKeyEvent and follows browser tab navigation, but it is not trusted human or operating-system keyboard input",
                "the observer does not activate controls, submit forms, or navigate links during CDP keyboard traversal",
                "remote debugging binds to loopback and uses a fresh temporary profile, but this is not claimed as complete operating-system process isolation",
                "CDP semantic evidence does not manufacture visual hierarchy, spacing consistency, component coherence, beauty, originality, or product-intent claims",
            ],
        }
        receipt["receipt_digest"] = _digest(receipt)
        (stage / "cdp.capture.json").write_text(json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.rename(output)

    return {
        "truth_status": "LOCAL_CDP_SEMANTIC_EVIDENCE_MATERIALIZED",
        "path": str(output),
        "files": sorted(path.name for path in output.iterdir() if path.is_file()),
        "receipt": receipt,
        "observation": observation,
    }


def design_cdp_summary() -> dict[str, Any]:
    return {
        "schema": CDP_SEMANTICS_SCHEMA,
        "operations": ["inspect-cdp-observer", "capture-cdp-semantics"],
        "browser_contract": "caller-selected local Chromium-compatible executable with loopback Chrome DevTools Protocol",
        "accessibility_tree": "Accessibility.getFullAXTree raw artifact plus bounded deterministic summary",
        "keyboard": "bounded Tab traversal through Input.dispatchKeyEvent with activeElement/focus-style observations",
        "maximum_tab_steps": MAX_TAB_STEPS,
        "trusted_human_input": False,
        "automatic_activation": False,
        "accessibility_conformance_inferred": False,
        "automatic_aesthetic_judgment": False,
        "third_party_python_dependency_required": False,
    }


def operate_design_cdp(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-cdp-observer":
        return {"truth_status": "DECLARED_CDP_SEMANTIC_OBSERVER_V0_1", **design_cdp_summary()}
    if operation == "capture-cdp-semantics":
        return capture_cdp_semantics(
            root,
            inputs.get("plan"),
            inputs.get("target"),
            inputs.get("path"),
            inputs.get("browser_executable"),
            inputs.get("viewport"),
            inputs.get("keyboard_tab_steps", 0),
            inputs.get("timeout_seconds", 20),
        )
    raise DesignCdpError(
        "CDP design observer operation is unsupported",
        {"operation": operation, "supported_operations": design_cdp_summary()["operations"]},
    )

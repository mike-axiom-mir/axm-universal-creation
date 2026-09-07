from __future__ import annotations

import base64
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .design_cdp import (
    DesignCdpError,
    _CdpConnection,
    _artifact_bytes,
    _bytes_digest,
    _digest,
    _integer,
    _machine_body_path,
    _page_endpoint,
    _resolve_browser,
    _resolve_path,
    _target_html,
    _viewport,
    _wait_devtools_port,
    _wait_document_ready,
    _evaluate_value,
)
from .design_fabric import DESIGN_PLAN_SCHEMA
from .design_observer import record_render_observation


CDP_GEOMETRY_SCHEMA = "axm.design-cdp-geometry/v0.1"
MAX_TIMEOUT_SECONDS = 120
MAX_GEOMETRY_ELEMENTS = 128
MAX_TEXT_RUNS = 64
MAX_OVERLAP_ELEMENTS = 64
MAX_OVERLAP_PAIRS = 128


class DesignGeometryError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


_GEOMETRY_EXPRESSION = r"""
(() => {
  const SCHEMA = "axm.design-cdp-geometry/v0.1";
  const MAX_ELEMENTS = 128;
  const MAX_TEXT_RUNS = 64;
  const MAX_OVERLAP_ELEMENTS = 64;
  const MAX_OVERLAP_PAIRS = 128;
  const round = (value) => Number.isFinite(Number(value)) ? Math.round(Number(value) * 1000) / 1000 : null;
  const rectValue = (rect) => ({
    x: round(rect.x), y: round(rect.y), width: round(rect.width), height: round(rect.height),
    right: round(rect.right), bottom: round(rect.bottom)
  });
  const visible = (element) => {
    if (!(element instanceof Element)) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
  };
  const overflowClips = (value) => ["hidden", "clip", "auto", "scroll"].includes(String(value || "").toLowerCase());
  const refFor = (element, domIndex) => ({
    dom_index: domIndex,
    tag: String(element.tagName || "").toLowerCase(),
    id: String(element.id || "").slice(0, 120)
  });
  const clipping = (element, rect) => {
    let current = element.parentElement;
    let x = false;
    let y = false;
    const ancestors = [];
    let depth = 0;
    while (current && current !== document.documentElement && depth < 32) {
      depth += 1;
      const style = getComputedStyle(current);
      const parentRect = current.getBoundingClientRect();
      const left = parentRect.left + current.clientLeft;
      const top = parentRect.top + current.clientTop;
      const right = left + current.clientWidth;
      const bottom = top + current.clientHeight;
      const clipX = overflowClips(style.overflowX) && (rect.left < left - 0.5 || rect.right > right + 0.5);
      const clipY = overflowClips(style.overflowY) && (rect.top < top - 0.5 || rect.bottom > bottom + 0.5);
      if (clipX || clipY) {
        if (ancestors.length < 4) ancestors.push({tag:String(current.tagName || "").toLowerCase(), id:String(current.id || "").slice(0,120), x:clipX, y:clipY});
        x = x || clipX;
        y = y || clipY;
      }
      current = current.parentElement;
    }
    return {x, y, ancestor_count: ancestors.length, ancestors};
  };

  const all = Array.from(document.querySelectorAll("*"));
  const candidates = [];
  for (let index = 0; index < all.length; index += 1) {
    const element = all[index];
    const tag = String(element.tagName || "").toLowerCase();
    if (["html", "body", "head", "script", "style", "meta", "link", "title", "template"].includes(tag)) continue;
    if (visible(element)) candidates.push({element, dom_index:index});
  }
  const observed = candidates.slice(0, MAX_ELEMENTS);
  const rows = [];
  let ancestorClipped = 0;
  let ownOverflow = 0;
  let outsideHorizontalViewport = 0;
  for (const item of observed) {
    const element = item.element;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    const clip = clipping(element, rect);
    const overflowX = element.scrollWidth > element.clientWidth + 1;
    const overflowY = element.scrollHeight > element.clientHeight + 1;
    const outsideX = rect.left < -0.5 || rect.right > innerWidth + 0.5;
    if (clip.x || clip.y) ancestorClipped += 1;
    if (overflowX || overflowY) ownOverflow += 1;
    if (outsideX) outsideHorizontalViewport += 1;
    rows.push({
      ref: refFor(element, item.dom_index),
      rect: rectValue(rect),
      position: String(style.position || ""),
      z_index: String(style.zIndex || "").slice(0, 80),
      overflow_x: String(style.overflowX || ""),
      overflow_y: String(style.overflowY || ""),
      client_width: element.clientWidth,
      client_height: element.clientHeight,
      scroll_width: element.scrollWidth,
      scroll_height: element.scrollHeight,
      own_scroll_overflow_x: overflowX,
      own_scroll_overflow_y: overflowY,
      outside_horizontal_viewport: outsideX,
      ancestor_clipping: clip
    });
  }

  const overlapSource = observed.slice(0, MAX_OVERLAP_ELEMENTS);
  const overlapPairs = [];
  let overlapPairCount = 0;
  for (let i = 0; i < overlapSource.length; i += 1) {
    for (let j = i + 1; j < overlapSource.length; j += 1) {
      const a = overlapSource[i];
      const b = overlapSource[j];
      if (a.element.contains(b.element) || b.element.contains(a.element)) continue;
      const ar = a.element.getBoundingClientRect();
      const br = b.element.getBoundingClientRect();
      const width = Math.min(ar.right, br.right) - Math.max(ar.left, br.left);
      const height = Math.min(ar.bottom, br.bottom) - Math.max(ar.top, br.top);
      if (width <= 0.5 || height <= 0.5) continue;
      const area = width * height;
      const aArea = Math.max(1, ar.width * ar.height);
      const bArea = Math.max(1, br.width * br.height);
      overlapPairCount += 1;
      if (overlapPairs.length < MAX_OVERLAP_PAIRS) {
        overlapPairs.push({
          first: refFor(a.element, a.dom_index),
          second: refFor(b.element, b.dom_index),
          intersection: {width:round(width), height:round(height), area:round(area)},
          first_area_fraction: round(area / aArea),
          second_area_fraction: round(area / bArea)
        });
      }
    }
  }

  const textCandidates = [];
  for (const item of observed) {
    const directTextNodes = Array.from(item.element.childNodes).filter((node) => node.nodeType === Node.TEXT_NODE && String(node.textContent || "").trim());
    if (directTextNodes.length) textCandidates.push({...item, directTextNodes});
  }
  const textRows = [];
  let textAncestorClipped = 0;
  for (const item of textCandidates.slice(0, MAX_TEXT_RUNS)) {
    const lineBoxes = [];
    let textLength = 0;
    for (const node of item.directTextNodes) {
      textLength += String(node.textContent || "").trim().length;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of Array.from(range.getClientRects())) {
        if (rect.width > 0 && rect.height > 0 && lineBoxes.length < 32) lineBoxes.push(rectValue(rect));
      }
      range.detach?.();
    }
    const elementRect = item.element.getBoundingClientRect();
    const clip = clipping(item.element, elementRect);
    if (clip.x || clip.y) textAncestorClipped += 1;
    const style = getComputedStyle(item.element);
    textRows.push({
      ref: refFor(item.element, item.dom_index),
      text_length: textLength,
      font_size_px: round(Number.parseFloat(style.fontSize || "")),
      line_height_px: String(style.lineHeight || "").toLowerCase() === "normal" ? null : round(Number.parseFloat(style.lineHeight || "")),
      line_box_count: lineBoxes.length,
      line_boxes: lineBoxes,
      ancestor_clipping: clip,
      own_scroll_overflow_x: item.element.scrollWidth > item.element.clientWidth + 1,
      own_scroll_overflow_y: item.element.scrollHeight > item.element.clientHeight + 1
    });
  }

  const root = document.documentElement;
  return {
    schema: SCHEMA,
    method: "CDP Runtime.evaluate bounded getBoundingClientRect/getClientRects/getComputedStyle observation",
    limits: {
      geometry_elements: MAX_ELEMENTS,
      text_runs: MAX_TEXT_RUNS,
      overlap_elements: MAX_OVERLAP_ELEMENTS,
      overlap_pairs_returned: MAX_OVERLAP_PAIRS
    },
    document: {
      viewport_width: Math.round(innerWidth),
      viewport_height: Math.round(innerHeight),
      device_pixel_ratio: Number(devicePixelRatio) || 1,
      scroll_width: Math.round(root.scrollWidth),
      scroll_height: Math.round(root.scrollHeight),
      horizontal_overflow: root.scrollWidth > innerWidth + 1
    },
    geometry: {
      visible_candidate_count: candidates.length,
      element_count_observed: rows.length,
      truncated: candidates.length > MAX_ELEMENTS,
      ancestor_clipped_element_count: ancestorClipped,
      own_scroll_overflow_element_count: ownOverflow,
      outside_horizontal_viewport_count: outsideHorizontalViewport,
      elements: rows
    },
    overlap: {
      scanned_element_count: overlapSource.length,
      pair_count: overlapPairCount,
      returned_pair_count: overlapPairs.length,
      truncated: overlapPairCount > overlapPairs.length,
      pairs: overlapPairs
    },
    text_geometry: {
      candidate_count: textCandidates.length,
      run_count: textRows.length,
      truncated: textCandidates.length > MAX_TEXT_RUNS,
      ancestor_clipped_run_count: textAncestorClipped,
      runs: textRows
    },
    truth_boundary: {
      rectangles_and_line_boxes_observed: true,
      overlap_is_quality_failure: false,
      clipping_is_quality_failure: false,
      semantic_component_roles_inferred: false,
      spacing_quality_inferred: false,
      hierarchy_quality_inferred: false,
      aesthetic_quality_inferred: false,
      text_content_retained: false
    }
  };
})()
"""


def _normalize_geometry(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != CDP_GEOMETRY_SCHEMA:
        raise DesignGeometryError("CDP geometry evaluation did not return the expected schema")
    geometry = raw.get("geometry")
    overlap = raw.get("overlap")
    text_geometry = raw.get("text_geometry")
    document = raw.get("document")
    if not all(isinstance(value, dict) for value in (geometry, overlap, text_geometry, document)):
        raise DesignGeometryError("CDP geometry evidence is missing a required object")
    elements = geometry.get("elements")
    pairs = overlap.get("pairs")
    runs = text_geometry.get("runs")
    if not isinstance(elements, list) or len(elements) > MAX_GEOMETRY_ELEMENTS:
        raise DesignGeometryError("CDP geometry element evidence exceeds its bound")
    if not isinstance(pairs, list) or len(pairs) > MAX_OVERLAP_PAIRS:
        raise DesignGeometryError("CDP overlap evidence exceeds its bound")
    if not isinstance(runs, list) or len(runs) > MAX_TEXT_RUNS:
        raise DesignGeometryError("CDP text geometry evidence exceeds its bound")
    try:
        return json.loads(json.dumps(raw, ensure_ascii=False, allow_nan=False))
    except (TypeError, ValueError) as exc:
        raise DesignGeometryError("CDP geometry evidence must be deterministic JSON") from exc


def _summary(geometry: dict[str, Any]) -> dict[str, Any]:
    document = geometry["document"]
    layout = geometry["geometry"]
    overlap = geometry["overlap"]
    text = geometry["text_geometry"]
    return {
        "horizontal_overflow": document.get("horizontal_overflow"),
        "visible_candidate_count": layout.get("visible_candidate_count"),
        "element_count_observed": layout.get("element_count_observed"),
        "element_scan_truncated": layout.get("truncated"),
        "ancestor_clipped_element_count": layout.get("ancestor_clipped_element_count"),
        "own_scroll_overflow_element_count": layout.get("own_scroll_overflow_element_count"),
        "outside_horizontal_viewport_count": layout.get("outside_horizontal_viewport_count"),
        "overlap_pair_count": overlap.get("pair_count"),
        "overlap_pairs_returned": overlap.get("returned_pair_count"),
        "overlap_scan_truncated": overlap.get("truncated"),
        "text_run_count": text.get("run_count"),
        "text_ancestor_clipped_run_count": text.get("ancestor_clipped_run_count"),
        "text_scan_truncated": text.get("truncated"),
        "quality_verdict_generated": False,
    }


def capture_cdp_geometry(
    root: Path,
    plan_raw: Any,
    target_raw: Any,
    output_raw: Any,
    browser_raw: Any,
    viewport_raw: Any,
    timeout_seconds: Any = 20,
) -> dict[str, Any]:
    if not isinstance(plan_raw, dict) or plan_raw.get("schema") != DESIGN_PLAN_SCHEMA or not isinstance(plan_raw.get("plan_digest"), str):
        raise DesignGeometryError("capture-cdp-geometry requires an axm.design-plan/v0.1 plan with plan_digest")
    plan = json.loads(json.dumps(plan_raw, ensure_ascii=False, allow_nan=False))
    try:
        target = _target_html(root, target_raw)
        output = _resolve_path(root, output_raw, "path")
        browser = _resolve_browser(browser_raw)
        viewport = _viewport(plan, viewport_raw)
        timeout = _integer(timeout_seconds, "timeout_seconds", 1, MAX_TIMEOUT_SECONDS)
    except DesignCdpError as exc:
        raise DesignGeometryError(str(exc), getattr(exc, "details", {})) from exc
    if _machine_body_path(root, output):
        raise DesignGeometryError("CDP geometry evidence is an ordinary creation and cannot write into the live machine body")
    if output.exists():
        raise DesignGeometryError("CDP geometry evidence target already exists; silent replacement is forbidden", {"path": str(output)})
    output.parent.mkdir(parents=True, exist_ok=True)
    target_uri = target.as_uri()

    process: subprocess.Popen[Any] | None = None
    with tempfile.TemporaryDirectory(prefix=".axm-cdp-geometry-profile-", dir=output.parent) as profile_dir, tempfile.TemporaryDirectory(prefix=".axm-cdp-geometry-evidence-", dir=output.parent) as stage_dir:
        profile = Path(profile_dir)
        stage = Path(stage_dir)
        command = [
            str(browser),
            "--headless=new",
            "--disable-background-networking",
            "--disable-default-apps",
            "--disable-extensions",
            "--disable-sync",
            "--metrics-recording-only",
            "--no-first-run",
            "--allow-file-access-from-files",
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
            try:
                port = _wait_devtools_port(profile, process, timeout)
                websocket_url = _page_endpoint(port, target_uri, timeout)
                cdp = _CdpConnection(websocket_url, timeout)
                try:
                    cdp.call("Page.enable")
                    cdp.call("Runtime.enable")
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
                    raw_geometry = _evaluate_value(cdp, _GEOMETRY_EXPRESSION)
                    geometry = _normalize_geometry(raw_geometry)
                    screenshot_result = cdp.call("Page.captureScreenshot", {"format": "png", "fromSurface": True})
                finally:
                    cdp.close()
            except DesignCdpError as exc:
                raise DesignGeometryError(str(exc), getattr(exc, "details", {})) from exc
        except OSError as exc:
            raise DesignGeometryError("CDP geometry browser could not start", {"reason": str(exc), "status": "HOLD_CDP_GEOMETRY_BROWSER_START_FAILED"}) from exc
        finally:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=2)

        encoded = screenshot_result.get("data") if isinstance(screenshot_result, dict) else None
        if not isinstance(encoded, str) or not encoded:
            raise DesignGeometryError("CDP geometry capture produced no screenshot bytes", {"status": "HOLD_CDP_GEOMETRY_SCREENSHOT_UNAVAILABLE"})
        try:
            screenshot_bytes = base64.b64decode(encoded, validate=True)
        except ValueError as exc:
            raise DesignGeometryError("CDP geometry screenshot payload is invalid base64") from exc
        if not screenshot_bytes:
            raise DesignGeometryError("CDP geometry screenshot payload is empty")

        geometry_bytes = _artifact_bytes(geometry)
        geometry_path = stage / f"{viewport['id']}.layout-geometry.json"
        screenshot_path = stage / f"{viewport['id']}.png"
        geometry_path.write_bytes(geometry_bytes)
        screenshot_path.write_bytes(screenshot_bytes)
        summary = _summary(geometry)

        measurements: dict[str, Any] = {}
        if isinstance(summary.get("horizontal_overflow"), bool):
            measurements["horizontal_overflow"] = summary["horizontal_overflow"]

        observation = record_render_observation(
            plan["plan_digest"],
            {
                "kind": "browser-tool",
                "id": "chromium-cdp-geometry",
                "version": str(version.get("product") or version.get("protocolVersion") or "unknown"),
                "basis": "caller-selected local Chromium-compatible browser observed through a loopback-only CDP endpoint; geometry facts are bounded measurements rather than aesthetic interpretation",
            },
            [{
                "viewport": viewport,
                "artifacts": [
                    {
                        "kind": "screenshot",
                        "digest": _bytes_digest(screenshot_bytes),
                        "uri": screenshot_path.name,
                        "mime_type": "image/png",
                        "bytes": len(screenshot_bytes),
                    },
                    {
                        "kind": "computed-style",
                        "digest": _bytes_digest(geometry_bytes),
                        "uri": geometry_path.name,
                        "mime_type": "application/vnd.axm.design-cdp-geometry+json",
                        "bytes": len(geometry_bytes),
                    },
                ],
                "measurements": measurements,
                "assessments": [{
                    "id": "layout-geometry-integrity",
                    "status": "PASS",
                    "confidence": 1.0,
                    "basis": "bounded CDP geometry and text line-box evidence was captured and normalized; PASS means evidence integrity only and does not classify clipping, overlap, spacing, hierarchy, or aesthetics as good or bad",
                }],
            }],
        )
        observation["truth_status"] = "OBSERVED_LOCAL_CDP_LAYOUT_GEOMETRY_AND_SCREENSHOT_EVIDENCE"
        observation["evidence_boundary"]["artifact_bytes_fetched_or_verified"] = True
        observation["evidence_boundary"]["browser_or_screen_control_claimed"] = True
        observation["evidence_boundary"]["layout_geometry_quality_claimed"] = False
        observation["evidence_boundary"]["aesthetic_quality_claimed"] = False
        observation["evidence_boundary"]["semantic_component_roles_inferred"] = False
        for capture in observation["captures"]:
            for artifact in capture["artifacts"]:
                artifact["bytes_verified_or_fetched_by_design_fabric"] = True
        observation["observation_digest"] = _digest({key: value for key, value in observation.items() if key != "observation_digest"})

        receipt = {
            "schema": CDP_GEOMETRY_SCHEMA,
            "truth_status": "LOCAL_CDP_LAYOUT_GEOMETRY_EVIDENCE_CAPTURED",
            "plan_digest": plan["plan_digest"],
            "target": {"path": str(target), "uri": target_uri},
            "viewport": viewport,
            "browser": {
                "path": str(browser),
                "product": version.get("product"),
                "protocol_version": version.get("protocolVersion"),
                "loopback_cdp_only": True,
                "fresh_temporary_profile": True,
            },
            "geometry_summary": summary,
            "observation": observation,
            "truth_boundary": {
                "geometry_measurements_observed": True,
                "overlap_classified_as_defect": False,
                "clipping_classified_as_defect": False,
                "spacing_quality_inferred": False,
                "visual_hierarchy_inferred": False,
                "aesthetic_quality_inferred": False,
                "semantic_component_roles_inferred": False,
                "raw_text_content_retained_in_geometry_artifact": False,
            },
            "limitations": [
                "overlap and clipping are recorded as geometric facts because both can be intentional design choices; they are not automatic failures",
                "text geometry records line boxes, text length, font size, and line height without retaining raw text content or inferring readability",
                "ancestor clipping uses computed overflow plus observed client/bounding rectangles and is bounded rather than a complete compositor model",
                "only the first bounded visible elements/text runs and overlap pairs are retained; truncation flags remain explicit",
                "the screenshot and geometry are captured from the exact local viewport under a caller-selected browser with a fresh temporary profile",
                "loopback CDP plus host-resolution blocking is not claimed as complete operating-system isolation",
                "geometry evidence can bind into the existing render-observation/judge lineage, but default perceptual hierarchy, spacing, and coherence still require separately attributed observation",
            ],
        }
        receipt["receipt_digest"] = _digest(receipt)
        (stage / "cdp-geometry.capture.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        stage.rename(output)

    return {
        "truth_status": "LOCAL_CDP_LAYOUT_GEOMETRY_EVIDENCE_MATERIALIZED",
        "path": str(output),
        "files": sorted(path.name for path in output.iterdir() if path.is_file()),
        "receipt": receipt,
        "observation": observation,
    }


def design_geometry_summary() -> dict[str, Any]:
    return {
        "schema": CDP_GEOMETRY_SCHEMA,
        "operations": ["inspect-cdp-geometry", "capture-cdp-geometry"],
        "browser_contract": "caller-selected local Chromium-compatible executable with loopback Chrome DevTools Protocol",
        "facts": [
            "bounded visible element rectangles and scroll/client geometry",
            "ancestor overflow clipping evidence",
            "horizontal viewport escape counts",
            "bounded non-ancestor overlap intersections and area fractions",
            "bounded direct-text line boxes, text length, font size, and line height without raw text retention",
            "document viewport/scroll size and horizontal-overflow fact",
            "same-viewport screenshot bytes bound to the exact geometry observation",
        ],
        "maximum_geometry_elements": MAX_GEOMETRY_ELEMENTS,
        "maximum_text_runs": MAX_TEXT_RUNS,
        "maximum_overlap_elements": MAX_OVERLAP_ELEMENTS,
        "maximum_overlap_pairs": MAX_OVERLAP_PAIRS,
        "automatic_geometry_quality_judgment": False,
        "automatic_aesthetic_judgment": False,
        "semantic_component_inference": False,
        "third_party_python_dependency_required": False,
    }


def operate_design_geometry(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation == "inspect-cdp-geometry":
        return {"truth_status": "DECLARED_CDP_LAYOUT_GEOMETRY_OBSERVER_V0_1", **design_geometry_summary()}
    if operation == "capture-cdp-geometry":
        return capture_cdp_geometry(
            root=root,
            plan_raw=inputs.get("plan"),
            target_raw=inputs.get("target"),
            output_raw=inputs.get("path"),
            browser_raw=inputs.get("browser_executable"),
            viewport_raw=inputs.get("viewport"),
            timeout_seconds=inputs.get("timeout_seconds", 20),
        )
    raise DesignGeometryError(
        "design geometry operation is unsupported",
        {"operation": operation, "supported_operations": design_geometry_summary()["operations"]},
    )

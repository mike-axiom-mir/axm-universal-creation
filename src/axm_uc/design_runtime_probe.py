from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin

RUNTIME_PROBE_SCHEMA = "axm.browser-runtime-probe/v0.1"
RUNTIME_PROBE_ELEMENT_ID = "axm-design-runtime-probe"

PROBE_SCRIPT = r"""
(() => {
  const errors = [];
  const recordError = (kind, value) => {
    if (errors.length < 128) errors.push({kind, message: String(value ?? "").slice(0, 500)});
  };
  window.addEventListener("error", (event) => recordError("window-error", event.message || event.error), true);
  window.addEventListener("unhandledrejection", (event) => recordError("unhandled-rejection", event.reason));
  try {
    const original = console.error.bind(console);
    console.error = (...args) => { recordError("console-error", args.join(" ")); original(...args); };
  } catch (_) {}

  const parseColor = (value) => {
    const m = String(value || "").match(/^rgba?\(\s*([\d.]+)\s*,\s*([\d.]+)\s*,\s*([\d.]+)(?:\s*,\s*([\d.]+))?\s*\)$/i);
    if (!m) return null;
    return {r:Number(m[1]), g:Number(m[2]), b:Number(m[3]), a:m[4] === undefined ? 1 : Number(m[4])};
  };
  const luminance = (color) => {
    const linear = [color.r, color.g, color.b].map((channel) => {
      const v = channel / 255;
      return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    });
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2];
  };
  const contrast = (a, b) => {
    const values = [luminance(a), luminance(b)].sort((x, y) => y - x);
    return (values[0] + 0.05) / (values[1] + 0.05);
  };
  const maxTimeMs = (value) => {
    let maximum = 0;
    for (const raw of String(value || "").split(",")) {
      const item = raw.trim().toLowerCase();
      const number = Number.parseFloat(item);
      if (!Number.isFinite(number)) continue;
      maximum = Math.max(maximum, item.endsWith("ms") ? number : item.endsWith("s") ? number * 1000 : 0);
    }
    return maximum;
  };
  const visible = (element) => {
    if (!(element instanceof Element)) return false;
    const style = getComputedStyle(element);
    const rect = element.getBoundingClientRect();
    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
  };
  const opaqueBackground = (element) => {
    let current = element;
    while (current && current instanceof Element) {
      const color = parseColor(getComputedStyle(current).backgroundColor);
      if (color && color.a >= 0.999) return color;
      current = current.parentElement;
    }
    return {r:255,g:255,b:255,a:1};
  };
  const accessibleName = (element) => {
    const aria = element.getAttribute("aria-label");
    if (aria && aria.trim()) return aria.trim();
    const labelled = element.getAttribute("aria-labelledby");
    if (labelled) {
      const text = labelled.split(/\s+/).map((id) => document.getElementById(id)?.textContent || "").join(" ").trim();
      if (text) return text;
    }
    if (element instanceof HTMLInputElement && element.labels?.length) {
      const text = Array.from(element.labels).map((label) => label.textContent || "").join(" ").trim();
      if (text) return text;
    }
    return (element.textContent || element.getAttribute("placeholder") || element.getAttribute("value") || "").trim();
  };

  const finish = () => {
    try {
      const root = document.documentElement;
      const all = Array.from(document.querySelectorAll("*"));
      const focusables = Array.from(document.querySelectorAll('a[href],button,input:not([type="hidden"]),select,textarea,summary,[tabindex]')).filter((element) => {
        if (!visible(element) || element.hasAttribute("disabled")) return false;
        const tabindex = element.getAttribute("tabindex");
        return tabindex === null || Number(tabindex) >= 0;
      });
      let focusVisibleCount = 0;
      const activeBefore = document.activeElement;
      for (const element of focusables) {
        try {
          element.focus({preventScroll:true});
          const style = getComputedStyle(element);
          const outline = style.outlineStyle !== "none" && (Number.parseFloat(style.outlineWidth || "0") || 0) > 0;
          const shadow = Boolean(style.boxShadow && style.boxShadow !== "none");
          if (document.activeElement === element && (outline || shadow)) focusVisibleCount += 1;
        } catch (error) { recordError("focus-probe", error); }
      }
      try {
        if (activeBefore instanceof HTMLElement && activeBefore !== document.body) activeBefore.focus({preventScroll:true});
        else if (document.activeElement instanceof HTMLElement) document.activeElement.blur();
      } catch (_) {}

      let maxMotion = 0;
      let motionCount = 0;
      for (const element of all) {
        if (!visible(element)) continue;
        const style = getComputedStyle(element);
        const duration = Math.max(maxTimeMs(style.transitionDuration), maxTimeMs(style.animationDuration));
        if (duration > 0) { motionCount += 1; maxMotion = Math.max(maxMotion, duration); }
      }

      const contrastSamples = [];
      for (const element of all) {
        if (!visible(element) || !(element.textContent || "").trim()) continue;
        if (Array.from(element.children).some((child) => (child.textContent || "").trim())) continue;
        const style = getComputedStyle(element);
        const foreground = parseColor(style.color);
        const background = opaqueBackground(element);
        if (!foreground || foreground.a < 0.999 || background.a < 0.999 || Number(style.opacity) < 0.999) continue;
        contrastSamples.push(contrast(foreground, background));
      }

      const issues = [];
      const addIssue = (kind, element, detail) => {
        if (issues.length >= 128) return;
        issues.push({kind, tag:String(element?.tagName || "").toLowerCase(), id:String(element?.id || "").slice(0,120), detail:String(detail || "").slice(0,300)});
      };
      for (const image of document.querySelectorAll("img")) if (!image.hasAttribute("alt")) addIssue("image-missing-alt", image, "img has no alt attribute");
      for (const control of document.querySelectorAll("button,input,select,textarea")) {
        if (String(control.getAttribute("type") || "").toLowerCase() !== "hidden" && !accessibleName(control)) addIssue("control-missing-accessible-name", control, "control has no observed label/name");
      }
      const seen = new Set();
      const duplicate = new Set();
      for (const element of document.querySelectorAll("[id]")) {
        if (!element.id) continue;
        if (seen.has(element.id) && !duplicate.has(element.id)) { duplicate.add(element.id); addIssue("duplicate-id", element, `duplicate id ${element.id}`); }
        seen.add(element.id);
      }

      const probe = {
        schema:"axm.browser-runtime-probe/v0.1",
        viewport:{width:Math.round(innerWidth),height:Math.round(innerHeight),device_pixel_ratio:Number(devicePixelRatio)||1,scroll_width:Math.round(root.scrollWidth),scroll_height:Math.round(root.scrollHeight)},
        horizontal_overflow:root.scrollWidth > innerWidth + 1,
        focus:{method:"programmatic-focus-computed-outline",focusable_count:focusables.length,focus_visible_count:focusVisibleCount,all_focusables_visible:focusables.length ? focusVisibleCount === focusables.length : null},
        motion:{prefers_reduced_motion:Boolean(matchMedia?.("(prefers-reduced-motion: reduce)").matches),observed_motion_element_count:motionCount,max_duration_ms:Math.round(maxMotion*1000)/1000},
        contrast:{method:"opaque-computed-text-on-nearest-opaque-background",sample_count:contrastSamples.length,minimum_text_contrast:contrastSamples.length ? Math.round(Math.min(...contrastSamples)*1000)/1000 : null},
        runtime_errors:errors.slice(0,128),runtime_error_count:errors.length,
        accessibility:{method:"bounded-dom-heuristics-not-accessibility-tree",issue_count:issues.length,issues,landmark_count:document.querySelectorAll("main,nav,header,footer,aside,[role='main'],[role='navigation']").length,heading_count:document.querySelectorAll("h1,h2,h3,h4,h5,h6,[role='heading']").length,control_count:document.querySelectorAll("button,input:not([type='hidden']),select,textarea,a[href],[role='button'],[role='link']").length}
      };
      const marker = document.createElement("script"); marker.id = "axm-design-runtime-probe"; marker.type = "application/json"; marker.textContent = JSON.stringify(probe); (document.body || root).appendChild(marker);
    } catch (error) {
      recordError("probe-fatal", error);
      const marker = document.createElement("script"); marker.id = "axm-design-runtime-probe"; marker.type = "application/json"; marker.textContent = JSON.stringify({schema:"axm.browser-runtime-probe/v0.1",fatal:true,runtime_errors:errors.slice(0,128),runtime_error_count:errors.length}); (document.body || document.documentElement).appendChild(marker);
    }
  };
  const schedule = () => requestAnimationFrame(() => requestAnimationFrame(finish));
  if (document.readyState === "complete") schedule(); else addEventListener("load", schedule, {once:true});
})();
"""

class _ProbeHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "script" and dict(attrs).get("id") == RUNTIME_PROBE_ELEMENT_ID:
            self.active = True

    def handle_endtag(self, tag: str) -> None:
        if self.active and tag.casefold() == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)

_BASE_RE = re.compile(r"(<base\b[^>]*\bhref\s*=\s*)([\"'])(.*?)(\2)", re.I | re.S)
_HEAD_RE = re.compile(r"<head\b[^>]*>", re.I)
_HTML_RE = re.compile(r"<html\b[^>]*>", re.I)

def instrument_local_html(target: Path) -> dict[str, Any]:
    target = Path(target).resolve()
    source = target.read_text(encoding="utf-8")
    target_uri = target.as_uri()
    existing = _BASE_RE.search(source)
    if existing:
        base_uri = urljoin(target_uri, html.unescape(existing.group(3)))
        source = source[:existing.start(3)] + html.escape(base_uri, quote=True) + source[existing.end(3):]
        prefix = f'<script data-axm-runtime-probe="v0.1">{PROBE_SCRIPT}</script>\n'
    else:
        base_uri = target.parent.as_uri().rstrip("/") + "/"
        prefix = f'<base href="{html.escape(base_uri, quote=True)}">\n<script data-axm-runtime-probe="v0.1">{PROBE_SCRIPT}</script>\n'
    head = _HEAD_RE.search(source)
    if head:
        body = source[:head.end()] + "\n" + prefix + source[head.end():]
    else:
        root = _HTML_RE.search(source)
        synthetic = f"<head>{prefix}</head>"
        body = source[:root.end()] + synthetic + source[root.end():] if root else "<!doctype html><html>" + synthetic + "<body>" + source + "</body></html>"
    return {"html":body,"base_uri":base_uri,"probe_schema":RUNTIME_PROBE_SCHEMA,"method":"temporary-instrumented-copy-with-original-relative-url-base"}

def parse_runtime_probe(dom_text: str) -> dict[str, Any] | None:
    parser = _ProbeHTMLParser()
    try:
        parser.feed(dom_text)
        parser.close()
        raw = json.loads(html.unescape("".join(parser.parts))) if parser.parts else None
    except (ValueError, TypeError):
        return None
    return raw if isinstance(raw, dict) and raw.get("schema") == RUNTIME_PROBE_SCHEMA else None

def runtime_measurements(normal_probe: dict[str, Any] | None, reduced_probe: dict[str, Any] | None = None) -> dict[str, Any]:
    if not isinstance(normal_probe, dict) or normal_probe.get("schema") != RUNTIME_PROBE_SCHEMA:
        return {}
    result: dict[str, Any] = {}
    if isinstance(normal_probe.get("horizontal_overflow"), bool): result["horizontal_overflow"] = normal_probe["horizontal_overflow"]
    focus = normal_probe.get("focus")
    if isinstance(focus, dict) and isinstance(focus.get("all_focusables_visible"), bool): result["focus_visible"] = focus["all_focusables_visible"]
    contrast = normal_probe.get("contrast")
    value = contrast.get("minimum_text_contrast") if isinstance(contrast, dict) else None
    if isinstance(value, (int,float)) and not isinstance(value,bool) and 1 <= float(value) <= 21: result["minimum_text_contrast"] = float(value)
    normal_motion = normal_probe.get("motion")
    reduced_motion = reduced_probe.get("motion") if isinstance(reduced_probe, dict) else None
    if isinstance(normal_motion, dict):
        count = normal_motion.get("observed_motion_element_count")
        normal_max = normal_motion.get("max_duration_ms")
        if isinstance(count, int) and count == 0:
            result["reduced_motion_honored"] = True
        elif isinstance(normal_max,(int,float)) and float(normal_max) > 0 and isinstance(reduced_motion,dict) and reduced_motion.get("prefers_reduced_motion") is True:
            reduced_max = reduced_motion.get("max_duration_ms")
            if isinstance(reduced_max,(int,float)) and float(reduced_max) < float(normal_max) and (float(reduced_max) <= 100 or float(reduced_max) <= float(normal_max)*0.5):
                result["reduced_motion_honored"] = True
    return result

def runtime_probe_artifact(probe: dict[str, Any]) -> bytes:
    return (json.dumps(probe,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False)+"\n").encode("utf-8")

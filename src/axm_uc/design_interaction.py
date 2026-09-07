from __future__ import annotations

import html
import json
import re
from html.parser import HTMLParser
from typing import Any


INTERACTION_PROBE_SCHEMA = "axm.browser-interaction-probe/v0.1"
INTERACTION_PROBE_ELEMENT_ID = "axm-design-interaction-probe"
MAX_RECIPES = 16
MAX_STEPS_PER_RECIPE = 32
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
SUPPORTED_ACTIONS = {"focus", "activate"}


class DesignInteractionError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _text(value: Any, label: str, maximum: int = 1000) -> str:
    if not isinstance(value, str) or not value.strip():
        raise DesignInteractionError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignInteractionError(f"{label} exceeds its {maximum}-character bound")
    return result


def _identifier(value: Any, label: str) -> str:
    result = _text(value, label, 128)
    if ID_RE.fullmatch(result) is None:
        raise DesignInteractionError(f"{label} is invalid", {"value": result})
    return result


def normalize_interaction_recipes(raw: Any, allow_synthetic_activation: Any = False) -> list[dict[str, Any]]:
    if not isinstance(allow_synthetic_activation, bool):
        raise DesignInteractionError("allow_synthetic_activation must be boolean")
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_RECIPES:
        raise DesignInteractionError(f"interaction_recipes must be a list with at most {MAX_RECIPES} entries")
    result = []
    ids: set[str] = set()
    for recipe_index, recipe in enumerate(raw):
        label = f"interaction_recipes[{recipe_index}]"
        if not isinstance(recipe, dict) or set(recipe) != {"id", "steps"}:
            raise DesignInteractionError(f"{label} must use exactly id and steps")
        recipe_id = _identifier(recipe["id"], f"{label}.id")
        if recipe_id in ids:
            raise DesignInteractionError("interaction recipe ids must be unique", {"id": recipe_id})
        ids.add(recipe_id)
        steps_raw = recipe["steps"]
        if not isinstance(steps_raw, list) or not 1 <= len(steps_raw) <= MAX_STEPS_PER_RECIPE:
            raise DesignInteractionError(f"{label}.steps must contain 1..{MAX_STEPS_PER_RECIPE} entries")
        steps = []
        for step_index, step in enumerate(steps_raw):
            step_label = f"{label}.steps[{step_index}]"
            if not isinstance(step, dict) or set(step) != {"action", "selector"}:
                raise DesignInteractionError(f"{step_label} must use exactly action and selector")
            action = _text(step["action"], f"{step_label}.action", 40).casefold()
            if action not in SUPPORTED_ACTIONS:
                raise DesignInteractionError(
                    f"{step_label}.action is unsupported",
                    {"action": action, "supported": sorted(SUPPORTED_ACTIONS)},
                )
            if action == "activate" and not allow_synthetic_activation:
                raise DesignInteractionError(
                    "synthetic activation is disabled unless explicitly authorized",
                    {"recipe": recipe_id, "step": step_index},
                )
            selector = _text(step["selector"], f"{step_label}.selector", 500)
            steps.append({"action": action, "selector": selector})
        result.append({"id": recipe_id, "steps": steps})
    return result


def _safe_json_for_script(value: Any) -> str:
    text = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return (
        text.replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _interaction_script(recipes: list[dict[str, Any]], allow_synthetic_activation: bool) -> str:
    payload = _safe_json_for_script(recipes)
    allowed = "true" if allow_synthetic_activation else "false"
    return rf"""
+(() => {{
+  const schema = "{INTERACTION_PROBE_SCHEMA}";
+  const recipes = {payload};
+  const activationAuthorized = {allowed};
+  const probeErrors = [];
+  const visible = (element) => {{
+    if (!(element instanceof Element)) return false;
+    const style = getComputedStyle(element);
+    const rect = element.getBoundingClientRect();
+    return style.display !== "none" && style.visibility !== "hidden" && Number(style.opacity) !== 0 && rect.width > 0 && rect.height > 0;
+  }};
+  const state = (element) => {{
+    const style = getComputedStyle(element);
+    return {{
+      tag:String(element.tagName || "").toLowerCase(),
+      id:String(element.id || "").slice(0,120),
+      role:String(element.getAttribute("role") || "").slice(0,120),
+      aria_expanded:element.getAttribute("aria-expanded"),
+      aria_pressed:element.getAttribute("aria-pressed"),
+      checked:"checked" in element ? Boolean(element.checked) : null,
+      disabled:"disabled" in element ? Boolean(element.disabled) : element.hasAttribute("aria-disabled"),
+      hidden:!visible(element),
+      class_name:String(element.className || "").slice(0,300),
+      text:String(element.textContent || "").trim().slice(0,300),
+      outline_style:String(style.outlineStyle || ""),
+      outline_width:String(style.outlineWidth || ""),
+      box_shadow:String(style.boxShadow || "").slice(0,300),
+    }};
+  }};
+  const focusVisible = (element) => {{
+    const style = getComputedStyle(element);
+    const outline = style.outlineStyle !== "none" && (Number.parseFloat(style.outlineWidth || "0") || 0) > 0;
+    const shadow = Boolean(style.boxShadow && style.boxShadow !== "none");
+    return document.activeElement === element && (outline || shadow);
+  }};
+  const activationAllowedFor = (element) => {{
+    const tag = String(element.tagName || "").toLowerCase();
+    const type = String(element.getAttribute("type") || "").toLowerCase();
+    const role = String(element.getAttribute("role") || "").toLowerCase();
+    return tag === "button" || tag === "summary" || role === "button" || (tag === "input" && ["checkbox","radio","button"].includes(type));
+  }};
+  addEventListener("submit", (event) => {{ event.preventDefault(); probeErrors.push({{kind:"blocked-form-submit",message:"form submission blocked during temporary interaction probe"}}); }}, true);
+  const finish = () => {{
+    const recipeResults = [];
+    let interactionErrorCount = 0;
+    for (const recipe of recipes) {{
+      const steps = [];
+      let recipeFailed = false;
+      for (let index = 0; index < recipe.steps.length; index += 1) {{
+        const step = recipe.steps[index];
+        const row = {{index,action:step.action,selector:step.selector,status:"HOLD"}};
+        try {{
+          const element = document.querySelector(step.selector);
+          if (!element) {{
+            row.status = "FAIL"; row.reason = "selector-not-found"; recipeFailed = true; interactionErrorCount += 1; steps.push(row); continue;
+          }}
+          row.before = state(element);
+          if (step.action === "focus") {{
+            if (!(element instanceof HTMLElement) || !visible(element)) {{
+              row.status = "FAIL"; row.reason = "target-not-visible-focusable-html-element"; recipeFailed = true; interactionErrorCount += 1;
+            }} else {{
+              element.focus({{preventScroll:true}});
+              row.focus_active = document.activeElement === element;
+              row.focus_visible = focusVisible(element);
+              row.status = row.focus_active ? "PASS" : "FAIL";
+              if (row.status === "FAIL") {{ recipeFailed = true; interactionErrorCount += 1; }}
+            }}
+          }} else if (step.action === "activate") {{
+            if (!activationAuthorized) {{
+              row.status = "FAIL"; row.reason = "activation-not-authorized"; recipeFailed = true; interactionErrorCount += 1;
+            }} else if (!(element instanceof HTMLElement) || !visible(element) || !activationAllowedFor(element)) {{
+              row.status = "FAIL"; row.reason = "activation-target-outside-bounded-control-contract"; recipeFailed = true; interactionErrorCount += 1;
+            }} else {{
+              element.click();
+              row.status = "PASS";
+              row.synthetic_activation = true;
+            }}
+          }}
+          row.after = state(element);
+          row.state_change_detected = JSON.stringify(row.before) !== JSON.stringify(row.after);
+        }} catch (error) {{
+          row.status = "FAIL"; row.reason = "exception"; row.error = String(error).slice(0,500); recipeFailed = true; interactionErrorCount += 1;
+        }}
+        steps.push(row);
+      }}
+      recipeResults.push({{id:recipe.id,status:recipeFailed ? "FAIL" : "PASS",steps}});
+    }}
+    const probe = {{
+      schema,
+      method:"explicit-programmatic-focus-and-bounded-synthetic-activation-on-temporary-local-copy",
+      activation_authorized:activationAuthorized,
+      requested_recipe_count:recipes.length,
+      completed_recipe_count:recipeResults.filter((row) => row.status === "PASS").length,
+      interaction_error_count:interactionErrorCount,
+      blocked_or_probe_errors:probeErrors.slice(0,128),
+      recipes:recipeResults,
+      truth_boundary:{{
+        real_keyboard_tab_traversal:false,
+        trusted_user_input_events:false,
+        form_submission_allowed:false,
+        arbitrary_link_navigation_allowed:false,
+        original_source_modified:false,
+      }},
+    }};
+    const marker = document.createElement("script");
+    marker.id = "{INTERACTION_PROBE_ELEMENT_ID}";
+    marker.type = "application/json";
+    marker.textContent = JSON.stringify(probe);
+    (document.body || document.documentElement).appendChild(marker);
+  }};
+  const schedule = () => requestAnimationFrame(() => requestAnimationFrame(finish));
+  if (document.readyState === "complete") schedule(); else addEventListener("load", schedule, {{once:true}});
+}})();
+"""


_BODY_END_RE = re.compile(r"</body\s*>", re.I)
_HTML_END_RE = re.compile(r"</html\s*>", re.I)


def instrument_interaction_html(
    html_text: str,
    recipes_raw: Any,
    allow_synthetic_activation: Any = False,
) -> dict[str, Any]:
    if not isinstance(html_text, str):
        raise DesignInteractionError("html_text must be text")
    recipes = normalize_interaction_recipes(recipes_raw, allow_synthetic_activation)
    if not recipes:
        return {
            "html": html_text,
            "recipes": [],
            "instrumented": False,
            "activation_authorized": bool(allow_synthetic_activation),
        }
    script = f'<script data-axm-interaction-probe="v0.1">{_interaction_script(recipes, bool(allow_synthetic_activation))}</script>\n'
    body_match = _BODY_END_RE.search(html_text)
    if body_match:
        instrumented = html_text[:body_match.start()] + script + html_text[body_match.start():]
    else:
        html_match = _HTML_END_RE.search(html_text)
        if html_match:
            instrumented = html_text[:html_match.start()] + script + html_text[html_match.start():]
        else:
            instrumented = html_text + script
    return {
        "html": instrumented,
        "recipes": recipes,
        "instrumented": True,
        "activation_authorized": bool(allow_synthetic_activation),
    }


class _InteractionHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.active = False
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "script" and dict(attrs).get("id") == INTERACTION_PROBE_ELEMENT_ID:
            self.active = True

    def handle_endtag(self, tag: str) -> None:
        if self.active and tag.casefold() == "script":
            self.active = False

    def handle_data(self, data: str) -> None:
        if self.active:
            self.parts.append(data)


def parse_interaction_probe(dom_text: str) -> dict[str, Any] | None:
    parser = _InteractionHTMLParser()
    try:
        parser.feed(dom_text)
        parser.close()
        raw = json.loads(html.unescape("".join(parser.parts))) if parser.parts else None
    except (ValueError, TypeError):
        return None
    return raw if isinstance(raw, dict) and raw.get("schema") == INTERACTION_PROBE_SCHEMA else None


def interaction_measurements(probe: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(probe, dict) or probe.get("schema") != INTERACTION_PROBE_SCHEMA:
        return {}
    requested = probe.get("requested_recipe_count")
    errors = probe.get("interaction_error_count")
    if isinstance(requested, int) and not isinstance(requested, bool) and requested > 0 and isinstance(errors, int) and not isinstance(errors, bool) and errors >= 0:
        return {"interaction_error_count": errors}
    return {}


def interaction_probe_artifact(probe: dict[str, Any]) -> bytes:
    return (
        json.dumps(probe, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        + "\n"
    ).encode("utf-8")


def design_interaction_summary() -> dict[str, Any]:
    return {
        "schema": INTERACTION_PROBE_SCHEMA,
        "maximum_recipes": MAX_RECIPES,
        "maximum_steps_per_recipe": MAX_STEPS_PER_RECIPE,
        "actions": sorted(SUPPORTED_ACTIONS),
        "activation_requires_explicit_authorization": True,
        "activation_target_contract": "visible button/summary/role=button/checkbox/radio/button-input only",
        "form_submission_blocked": True,
        "real_keyboard_tab_traversal": False,
        "trusted_user_input_events": False,
        "original_source_modified": False,
    }

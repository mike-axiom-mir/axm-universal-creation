"""Deterministic visual archetypes for screens and whole products.

Visual templates are known-good structural starting points, not aesthetic canon.
They preserve semantic hierarchy in normalized coordinates and resolve those
coordinates to an explicit viewport. The catalog is offline and dependency-free.

Sticker Fabric remains the immutable/versioned registry. ``sticker_definition``
wraps a visual archetype as an ordinary exact sticker definition when a caller
wants local registry discovery and pinning; no template is silently promoted or
selected as ``latest``.
"""
from __future__ import annotations

from copy import deepcopy
from html import escape
import hashlib
import json
import math
import re
from typing import Any

SCHEMA = "axm.visual-template/v1"
PRODUCT_SCHEMA = "axm.visual-product/v1"
ADAPTER = "axm.visual-template/v1"
PRODUCT_ADAPTER = "axm.visual-product/v1"
_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,79}\Z")
MAX_REGIONS = 32
MAX_SLOTS = 24


def _origin() -> dict[str, str]:
    return {"author": "AXM", "license": "repository-license", "source": "axm-universal-creation"}


STYLE_SYSTEMS: dict[str, dict[str, Any]] = {
    "racing.performance": {
        "intent": "high-speed legibility with one dominant race metric and restrained peripheral chrome",
        "tokens": {
            "canvas": "#090d12", "surface": "#111923", "surface_raised": "#172430",
            "text": "#edf6f6", "muted": "#9fb0b7", "accent": "#67e8dc",
            "warning": "#ffb45c", "danger": "#ff6f6f", "line": "#31414a",
        },
        "shape": {"panel_radius_ratio": 0.018, "cut_ratio": 0.010, "line_ratio": 0.0015},
        "type": {"display_weight": 760, "body_weight": 520, "metric_scale": 1.85, "tracking": 0.025},
        "depth": {"layers": 4, "shadow": "tight", "glass": "restrained"},
        "motion": {"fast_ms": 90, "standard_ms": 180, "slow_ms": 320, "principle": "state first; flourish second"},
    },
    "studio.precision": {
        "intent": "dense professional creation workspace with persistent context and inspectable controls",
        "tokens": {
            "canvas": "#0b0f14", "surface": "#151b22", "surface_raised": "#1c2530",
            "text": "#eff3f6", "muted": "#9ba8b4", "accent": "#82b9ff",
            "warning": "#f2c572", "danger": "#ef7b7b", "line": "#36414d",
        },
        "shape": {"panel_radius_ratio": 0.010, "cut_ratio": 0.0, "line_ratio": 0.0012},
        "type": {"display_weight": 700, "body_weight": 480, "metric_scale": 1.45, "tracking": 0.010},
        "depth": {"layers": 5, "shadow": "subtle", "glass": "none"},
        "motion": {"fast_ms": 80, "standard_ms": 160, "slow_ms": 260, "principle": "preserve editing context"},
    },
    "system.command": {
        "intent": "operational overview with strong status hierarchy and low ambiguity",
        "tokens": {
            "canvas": "#081016", "surface": "#10202a", "surface_raised": "#17303c",
            "text": "#e9f4f6", "muted": "#9eb4ba", "accent": "#7ed6c4",
            "warning": "#eac46c", "danger": "#ef7474", "line": "#31505a",
        },
        "shape": {"panel_radius_ratio": 0.012, "cut_ratio": 0.004, "line_ratio": 0.0014},
        "type": {"display_weight": 720, "body_weight": 500, "metric_scale": 1.6, "tracking": 0.018},
        "depth": {"layers": 4, "shadow": "subtle", "glass": "light"},
        "motion": {"fast_ms": 100, "standard_ms": 190, "slow_ms": 340, "principle": "changes must remain traceable"},
    },
    "mobile.focus": {
        "intent": "touch-first focus with one primary action and comfortable scan rhythm",
        "tokens": {
            "canvas": "#0d1117", "surface": "#171d26", "surface_raised": "#202936",
            "text": "#f1f5f8", "muted": "#aab6c2", "accent": "#92c7ff",
            "warning": "#efc16f", "danger": "#f07e7e", "line": "#354150",
        },
        "shape": {"panel_radius_ratio": 0.026, "cut_ratio": 0.0, "line_ratio": 0.0015},
        "type": {"display_weight": 720, "body_weight": 500, "metric_scale": 1.45, "tracking": 0.008},
        "depth": {"layers": 3, "shadow": "soft", "glass": "none"},
        "motion": {"fast_ms": 100, "standard_ms": 190, "slow_ms": 300, "principle": "direct manipulation, no surprise movement"},
    },
    "commerce.gallery": {
        "intent": "visual browsing with clear comparison, selection state and purchase-safe hierarchy",
        "tokens": {
            "canvas": "#0f1115", "surface": "#1a1d23", "surface_raised": "#232832",
            "text": "#f5f5f2", "muted": "#b4b5b2", "accent": "#ffd477",
            "warning": "#f0ae67", "danger": "#ec7777", "line": "#41444c",
        },
        "shape": {"panel_radius_ratio": 0.018, "cut_ratio": 0.0, "line_ratio": 0.0013},
        "type": {"display_weight": 720, "body_weight": 480, "metric_scale": 1.5, "tracking": 0.012},
        "depth": {"layers": 4, "shadow": "soft", "glass": "none"},
        "motion": {"fast_ms": 100, "standard_ms": 180, "slow_ms": 300, "principle": "selection state stays obvious"},
    },
}


PRIMITIVES: dict[str, dict[str, Any]] = {
    "panel": {"role": "contain related state", "states": ["rest", "focus", "disabled"], "minimum_contrast": "boundary-or-surface"},
    "primary-action": {"role": "one dominant action per local decision zone", "states": ["rest", "hover", "pressed", "disabled", "busy"]},
    "metric": {"role": "fast numeric reading", "states": ["normal", "warning", "critical"], "alignment": "tabular-or-fixed-width"},
    "progress": {"role": "bounded progress or charge", "states": ["empty", "partial", "full", "blocked"], "requires_text_fallback": True},
    "navigation": {"role": "location and movement", "states": ["rest", "selected", "unavailable"], "selection_must_not_depend_on_color": True},
    "list-row": {"role": "repeatable comparable item", "states": ["rest", "selected", "disabled"], "stable_alignment": True},
    "viewport": {"role": "primary content/world surface", "states": ["active", "paused", "loading"], "must_preserve_focus": True},
    "toast": {"role": "non-blocking feedback", "states": ["info", "success", "warning", "error"], "must_not_hold_unique_critical_state": True},
}


def _screen(template_id: str, name: str, domain: str, style: str, intent: str,
            variants: dict[str, dict[str, tuple[float, float, float, float]]],
            *, slots: list[dict[str, Any]] | None = None, tags: list[str] | None = None,
            math_hooks: dict[str, Any] | None = None, quality: list[str] | None = None) -> dict[str, Any]:
    return {
        "schema": SCHEMA,
        "id": template_id,
        "version": 1,
        "name": name,
        "kind": "screen",
        "domain": domain,
        "tags": list(tags or []),
        "origin": _origin(),
        "style": style,
        "intent": intent,
        "variants": {variant: {region: list(box) for region, box in regions.items()} for variant, regions in variants.items()},
        "slots": deepcopy(slots or []),
        "math_hooks": deepcopy(math_hooks or {}),
        "quality": list(quality or []),
    }


RACING_COMMON = [
    "preserve world/vehicle visibility ahead of decorative chrome",
    "critical race state must remain readable without color alone",
    "secondary information must not compete with speed, route, threats or objective",
    "animations may reinforce state changes but may not delay control feedback",
]


SCREEN_TEMPLATES: dict[str, dict[str, Any]] = {
    "game.racing.hud.performance": _screen(
        "game.racing.hud.performance", "Performance racing HUD", "game.racing", "racing.performance",
        "keep speed, route, position and immediate vehicle state readable during high-motion play",
        {
            "compact": {
                "position": (0.025, 0.035, 0.18, 0.10), "objective": (0.29, 0.035, 0.42, 0.10),
                "minimap": (0.79, 0.035, 0.185, 0.235), "world": (0.0, 0.0, 1.0, 1.0),
                "vehicle-state": (0.025, 0.805, 0.19, 0.15), "speed": (0.395, 0.80, 0.21, 0.165),
                "event-feed": (0.73, 0.77, 0.245, 0.19),
            },
            "standard": {
                "position": (0.022, 0.035, 0.15, 0.095), "objective": (0.335, 0.035, 0.33, 0.085),
                "minimap": (0.82, 0.035, 0.158, 0.255), "world": (0.0, 0.0, 1.0, 1.0),
                "vehicle-state": (0.022, 0.805, 0.17, 0.15), "speed": (0.41, 0.795, 0.18, 0.17),
                "event-feed": (0.76, 0.77, 0.218, 0.19),
            },
            "wide": {
                "position": (0.018, 0.04, 0.125, 0.09), "objective": (0.37, 0.04, 0.26, 0.08),
                "minimap": (0.855, 0.04, 0.127, 0.245), "world": (0.0, 0.0, 1.0, 1.0),
                "vehicle-state": (0.018, 0.815, 0.145, 0.14), "speed": (0.425, 0.805, 0.15, 0.155),
                "event-feed": (0.80, 0.785, 0.182, 0.17),
            },
        },
        slots=[
            {"id": "speed-cluster", "kind": "sticker", "socket": "surface", "tags": ["hud", "metric"], "required": False},
            {"id": "minimap-frame", "kind": "sticker", "socket": "surface", "tags": ["hud", "navigation"], "required": False},
        ],
        tags=["game", "racing", "hud", "performance"],
        math_hooks={"focal_region": "speed", "edge_safe_ratio": [0.018, 0.04], "major_minor_type_ratio": [1.55, 2.15]},
        quality=RACING_COMMON,
    ),
    "game.racing.garage": _screen(
        "game.racing.garage", "Racing garage and vehicle setup", "game.racing", "racing.performance",
        "make the vehicle the hero while tuning, comparison and primary actions stay immediately inspectable",
        {
            "compact": {"topbar": (0.03,0.03,0.94,0.08), "vehicle": (0.03,0.14,0.94,0.43), "stats": (0.03,0.60,0.45,0.25), "tuning": (0.52,0.60,0.45,0.25), "actions": (0.03,0.88,0.94,0.085)},
            "standard": {"topbar": (0.025,0.03,0.95,0.08), "vehicle": (0.22,0.13,0.56,0.58), "stats": (0.025,0.17,0.17,0.54), "tuning": (0.805,0.17,0.17,0.54), "actions": (0.25,0.80,0.50,0.11)},
            "wide": {"topbar": (0.02,0.03,0.96,0.075), "vehicle": (0.24,0.13,0.52,0.60), "stats": (0.02,0.18,0.18,0.53), "tuning": (0.80,0.18,0.18,0.53), "actions": (0.31,0.82,0.38,0.10)},
        },
        slots=[{"id":"vehicle-stage","kind":"content","required":True},{"id":"manufacturer-mark","kind":"sticker","socket":"surface","tags":["identity"],"required":False}],
        tags=["game","racing","garage","loadout"],
        math_hooks={"hero_area_ratio":[0.45,0.68],"side_panel_ratio":[0.16,0.22]}, quality=RACING_COMMON,
    ),
    "game.racing.event-select": _screen(
        "game.racing.event-select", "Racing event selection", "game.racing", "racing.performance",
        "show route identity, risk and reward before commitment without burying the primary start decision",
        {
            "compact": {"header":(0.03,0.03,0.94,0.08),"route-map":(0.03,0.14,0.94,0.36),"event-list":(0.03,0.53,0.50,0.33),"details":(0.56,0.53,0.41,0.33),"actions":(0.03,0.89,0.94,0.08)},
            "standard": {"header":(0.025,0.03,0.95,0.08),"event-list":(0.025,0.14,0.25,0.72),"route-map":(0.30,0.14,0.45,0.55),"details":(0.775,0.14,0.20,0.55),"actions":(0.30,0.74,0.675,0.12)},
            "wide": {"header":(0.02,0.03,0.96,0.075),"event-list":(0.02,0.14,0.22,0.72),"route-map":(0.27,0.14,0.50,0.56),"details":(0.80,0.14,0.18,0.56),"actions":(0.27,0.76,0.71,0.105)},
        }, tags=["game","racing","events","map"], quality=RACING_COMMON,
    ),
    "game.racing.results": _screen(
        "game.racing.results", "Racing results", "game.racing", "racing.performance",
        "celebrate outcome while making placement, rewards and next actions unambiguous",
        {
            "compact": {"headline":(0.04,0.05,0.92,0.13),"placement":(0.04,0.21,0.28,0.23),"summary":(0.35,0.21,0.61,0.23),"leaderboard":(0.04,0.48,0.92,0.30),"rewards":(0.04,0.81,0.55,0.13),"actions":(0.62,0.81,0.34,0.13)},
            "standard": {"headline":(0.04,0.06,0.92,0.12),"placement":(0.04,0.22,0.24,0.48),"summary":(0.31,0.22,0.31,0.22),"leaderboard":(0.65,0.22,0.31,0.48),"rewards":(0.31,0.48,0.31,0.22),"actions":(0.31,0.76,0.65,0.13)},
            "wide": {"headline":(0.05,0.06,0.90,0.11),"placement":(0.05,0.22,0.20,0.49),"summary":(0.28,0.22,0.30,0.22),"leaderboard":(0.61,0.22,0.34,0.49),"rewards":(0.28,0.48,0.30,0.23),"actions":(0.28,0.78,0.67,0.11)},
        }, tags=["game","racing","results","rewards"], quality=RACING_COMMON,
    ),
    "game.racing.lobby": _screen(
        "game.racing.lobby", "Racing co-op lobby", "game.racing", "racing.performance",
        "keep player readiness, seat ownership, event choice and launch state visible without setup clutter",
        {
            "compact": {"header":(0.03,0.03,0.94,0.08),"event":(0.03,0.14,0.94,0.22),"players":(0.03,0.39,0.94,0.36),"options":(0.03,0.78,0.46,0.17),"launch":(0.52,0.78,0.45,0.17)},
            "standard": {"header":(0.025,0.03,0.95,0.08),"event":(0.025,0.14,0.28,0.68),"players":(0.33,0.14,0.42,0.68),"options":(0.775,0.14,0.20,0.45),"launch":(0.775,0.64,0.20,0.18)},
            "wide": {"header":(0.02,0.03,0.96,0.075),"event":(0.02,0.14,0.25,0.69),"players":(0.30,0.14,0.45,0.69),"options":(0.78,0.14,0.20,0.46),"launch":(0.78,0.65,0.20,0.18)},
        }, tags=["game","racing","lobby","coop"], quality=RACING_COMMON,
    ),
    "game.racing.pause": _screen(
        "game.racing.pause", "Racing pause overlay", "game.racing", "racing.performance",
        "preserve paused-world context while keeping resume and recovery actions dominant",
        {
            "compact": {"context":(0,0,1,1),"menu":(0.18,0.14,0.64,0.70),"status":(0.20,0.17,0.60,0.12),"actions":(0.25,0.35,0.50,0.43)},
            "standard": {"context":(0,0,1,1),"menu":(0.30,0.12,0.40,0.76),"status":(0.33,0.17,0.34,0.11),"actions":(0.35,0.34,0.30,0.45)},
            "wide": {"context":(0,0,1,1),"menu":(0.34,0.12,0.32,0.76),"status":(0.37,0.17,0.26,0.11),"actions":(0.39,0.34,0.22,0.45)},
        }, tags=["game","racing","pause","settings"], quality=RACING_COMMON,
    ),
    "product.dashboard.command": _screen(
        "product.dashboard.command", "Command dashboard", "software.dashboard", "system.command",
        "surface the current state, important changes, exceptions and next actions in one operational view",
        {
            "compact": {"header":(0.03,0.025,0.94,0.075),"summary":(0.03,0.125,0.94,0.16),"primary":(0.03,0.31,0.94,0.34),"alerts":(0.03,0.68,0.45,0.28),"activity":(0.52,0.68,0.45,0.28)},
            "standard": {"nav":(0.015,0.02,0.14,0.96),"header":(0.18,0.025,0.80,0.075),"summary":(0.18,0.125,0.80,0.16),"primary":(0.18,0.31,0.52,0.65),"alerts":(0.73,0.31,0.25,0.30),"activity":(0.73,0.64,0.25,0.32)},
            "wide": {"nav":(0.012,0.02,0.11,0.96),"header":(0.145,0.025,0.835,0.075),"summary":(0.145,0.125,0.835,0.15),"primary":(0.145,0.30,0.56,0.66),"alerts":(0.73,0.30,0.25,0.30),"activity":(0.73,0.63,0.25,0.33)},
        }, tags=["software","dashboard","operations"], quality=["exceptions outrank decoration","status language must be explicit","dense panels need stable alignment"],
    ),
    "product.editor.workspace": _screen(
        "product.editor.workspace", "Professional editor workspace", "software.editor", "studio.precision",
        "preserve a large primary work surface with stable tools, hierarchy, properties and evidence",
        {
            "compact": {"topbar":(0.02,0.02,0.96,0.07),"tools":(0.02,0.11,0.10,0.77),"viewport":(0.14,0.11,0.84,0.57),"hierarchy":(0.14,0.71,0.40,0.27),"properties":(0.56,0.71,0.42,0.27)},
            "standard": {"topbar":(0.015,0.02,0.97,0.065),"hierarchy":(0.015,0.105,0.16,0.875),"tools":(0.19,0.105,0.055,0.67),"viewport":(0.26,0.105,0.53,0.67),"properties":(0.805,0.105,0.18,0.67),"timeline":(0.19,0.795,0.795,0.185)},
            "wide": {"topbar":(0.012,0.02,0.976,0.06),"hierarchy":(0.012,0.10,0.14,0.88),"tools":(0.165,0.10,0.045,0.68),"viewport":(0.225,0.10,0.57,0.68),"properties":(0.81,0.10,0.178,0.68),"timeline":(0.165,0.80,0.823,0.18)},
        }, tags=["software","editor","creative","workspace"], quality=["viewport remains the dominant surface","tools stay position-stable","properties expose state instead of hiding it"],
    ),
    "product.mobile.home": _screen(
        "product.mobile.home", "Mobile product home", "software.mobile", "mobile.focus",
        "give a touch user immediate orientation, recent state and one clear next action",
        {
            "compact": {"system":(0.04,0.02,0.92,0.055),"identity":(0.04,0.095,0.92,0.105),"primary":(0.04,0.23,0.92,0.27),"recent":(0.04,0.53,0.92,0.29),"nav":(0.04,0.86,0.92,0.10)},
            "standard": {"identity":(0.06,0.05,0.88,0.10),"primary":(0.06,0.19,0.88,0.30),"recent":(0.06,0.53,0.88,0.30),"nav":(0.06,0.87,0.88,0.09)},
            "wide": {"identity":(0.08,0.05,0.84,0.10),"primary":(0.08,0.19,0.84,0.30),"recent":(0.08,0.53,0.84,0.30),"nav":(0.08,0.87,0.84,0.09)},
        }, tags=["software","mobile","home","touch"], quality=["one dominant next action","touch targets need breathing room","recent state stays recoverable"],
    ),
    "product.store.browse": _screen(
        "product.store.browse", "Store and catalog browse", "software.commerce", "commerce.gallery",
        "support browsing and comparison while keeping filters, selection and ownership state clear",
        {
            "compact": {"header":(0.03,0.03,0.94,0.08),"filters":(0.03,0.14,0.94,0.10),"gallery":(0.03,0.27,0.94,0.52),"selection":(0.03,0.82,0.94,0.15)},
            "standard": {"header":(0.025,0.03,0.95,0.08),"filters":(0.025,0.14,0.18,0.82),"gallery":(0.23,0.14,0.50,0.82),"selection":(0.755,0.14,0.22,0.82)},
            "wide": {"header":(0.02,0.03,0.96,0.075),"filters":(0.02,0.14,0.15,0.82),"gallery":(0.19,0.14,0.56,0.82),"selection":(0.77,0.14,0.21,0.82)},
        }, tags=["software","commerce","store","gallery"], quality=["price/ownership state must not hide in decoration","filters preserve active state","comparison geometry stays stable"],
    ),
    "product.settings.system": _screen(
        "product.settings.system", "Settings and preferences", "software.settings", "system.command",
        "make scope, current values, consequences and reversible changes obvious",
        {
            "compact": {"header":(0.04,0.03,0.92,0.08),"categories":(0.04,0.14,0.92,0.15),"settings":(0.04,0.32,0.92,0.52),"actions":(0.04,0.87,0.92,0.10)},
            "standard": {"header":(0.03,0.03,0.94,0.08),"categories":(0.03,0.14,0.22,0.82),"settings":(0.28,0.14,0.69,0.68),"actions":(0.28,0.85,0.69,0.11)},
            "wide": {"header":(0.025,0.03,0.95,0.075),"categories":(0.025,0.14,0.19,0.82),"settings":(0.245,0.14,0.73,0.68),"actions":(0.245,0.85,0.73,0.11)},
        }, tags=["software","settings","preferences"], quality=["show current value and scope","dangerous actions require distinct treatment","reversible changes should say how to reverse"],
    ),
}


PRODUCT_ARCHETYPES: dict[str, dict[str, Any]] = {
    "game.racing.performance": {
        "schema": PRODUCT_SCHEMA, "id": "game.racing.performance", "version": 1,
        "name": "Performance racing game product", "kind": "product", "domain": "game.racing",
        "tags": ["game","racing","product","coop"], "origin": _origin(), "style": "racing.performance",
        "intent": "a coherent professional racing shell from lobby through race, garage and results",
        "screens": [
            "game.racing.lobby", "game.racing.event-select", "game.racing.garage",
            "game.racing.hud.performance", "game.racing.pause", "game.racing.results",
        ],
        "flow": [
            ["game.racing.lobby","game.racing.event-select","choose-event"],
            ["game.racing.event-select","game.racing.garage","prepare-vehicle"],
            ["game.racing.garage","game.racing.hud.performance","start-race"],
            ["game.racing.hud.performance","game.racing.pause","pause"],
            ["game.racing.pause","game.racing.hud.performance","resume"],
            ["game.racing.hud.performance","game.racing.results","finish"],
            ["game.racing.results","game.racing.lobby","continue"],
        ],
        "quality": [
            "one visual language across shell and HUD, not six unrelated screens",
            "race information density rises only when driving begins",
            "player/seat readiness remains explicit for co-op",
            "results preserve a clear return/continue loop",
            "template geometry is a starting constraint system, not finished art",
        ],
    },
    "software.creator.studio": {
        "schema": PRODUCT_SCHEMA, "id": "software.creator.studio", "version": 1,
        "name": "Creator studio product", "kind": "product", "domain": "software.creator",
        "tags": ["software","creator","product","editor"], "origin": _origin(), "style": "studio.precision",
        "intent": "a professional creation product with command overview, editing and explicit preferences",
        "screens": ["product.dashboard.command","product.editor.workspace","product.settings.system"],
        "flow": [
            ["product.dashboard.command","product.editor.workspace","open-project"],
            ["product.editor.workspace","product.settings.system","configure"],
            ["product.settings.system","product.editor.workspace","return"],
        ],
        "quality": ["creation state remains primary","settings never silently rewrite projects","operational dashboard shows exceptions without replacing source truth"],
    },
}


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def _id(value: Any, label: str = "id") -> str:
    if not isinstance(value, str) or _ID.fullmatch(value) is None:
        raise ValueError(f"{label} must be a portable identifier")
    return value


def _finite_ratio(value: Any, label: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError(f"{label} must be finite")
    value = float(value)
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{label} must be within 0..1")
    return value


def _validate_box(box: Any, label: str) -> list[float]:
    if not isinstance(box, (list, tuple)) or len(box) != 4:
        raise ValueError(f"{label} requires x, y, width, height")
    x, y, width, height = [_finite_ratio(v, label) for v in box]
    if width <= 0 or height <= 0 or x + width > 1.000000001 or y + height > 1.000000001:
        raise ValueError(f"{label} exceeds normalized viewport")
    return [x, y, width, height]


def validate_screen(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != SCHEMA or value.get("kind") != "screen":
        raise ValueError("not an AXM visual screen template")
    required = {"schema","id","version","name","kind","domain","tags","origin","style","intent","variants","slots","math_hooks","quality"}
    if set(value) != required:
        raise ValueError("unsupported visual screen fields")
    _id(value["id"]); _id(value["domain"], "domain"); _id(value["style"], "style")
    if type(value["version"]) is not int or value["version"] < 1:
        raise ValueError("version must be a positive integer")
    for field in ("name","intent"):
        if not isinstance(value[field], str) or not value[field].strip() or len(value[field]) > 600:
            raise ValueError(f"{field} must be bounded nonempty text")
    if value["style"] not in STYLE_SYSTEMS:
        raise ValueError("unknown style system")
    if not isinstance(value["tags"], list) or len(value["tags"]) > 24 or len(set(value["tags"])) != len(value["tags"]):
        raise ValueError("tags must be unique and bounded")
    for tag in value["tags"]: _id(tag, "tag")
    origin = value["origin"]
    if not isinstance(origin, dict) or set(origin) != {"author","license","source"} or not all(isinstance(x,str) and x.strip() for x in origin.values()):
        raise ValueError("origin requires author, license and source")
    variants = value["variants"]
    if not isinstance(variants, dict) or not variants or len(variants) > 6:
        raise ValueError("variants must contain 1..6 responsive layouts")
    for variant, regions in variants.items():
        _id(variant, "variant")
        if not isinstance(regions, dict) or not regions or len(regions) > MAX_REGIONS:
            raise ValueError("each variant requires bounded regions")
        for region, box in regions.items():
            _id(region, "region")
            _validate_box(box, f"{variant}.{region}")
    slots = value["slots"]
    if not isinstance(slots, list) or len(slots) > MAX_SLOTS:
        raise ValueError("slots must be bounded")
    seen = set()
    for slot in slots:
        if not isinstance(slot, dict) or not {"id","kind","required"} <= slot.keys() or set(slot)-{"id","kind","required","socket","tags"}:
            raise ValueError("invalid visual slot")
        sid = _id(slot["id"], "slot id")
        if sid in seen: raise ValueError("duplicate visual slot")
        seen.add(sid)
        if slot["kind"] not in {"content","sticker","system"} or type(slot["required"]) is not bool:
            raise ValueError("invalid visual slot kind/required flag")
        if slot["kind"] == "sticker":
            _id(slot.get("socket"), "slot socket")
            tags = slot.get("tags", [])
            if not isinstance(tags,list) or len(tags) > 12: raise ValueError("invalid slot tags")
            for tag in tags: _id(tag, "slot tag")
        elif "socket" in slot or "tags" in slot:
            raise ValueError("only sticker slots declare socket/tags")
    if not isinstance(value["math_hooks"], dict) or not isinstance(value["quality"], list) or not all(isinstance(x,str) and x.strip() for x in value["quality"]):
        raise ValueError("math_hooks/quality malformed")
    canonical_bytes(value)
    return deepcopy(value)


def validate_product(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or value.get("schema") != PRODUCT_SCHEMA or value.get("kind") != "product":
        raise ValueError("not an AXM visual product archetype")
    required = {"schema","id","version","name","kind","domain","tags","origin","style","intent","screens","flow","quality"}
    if set(value) != required: raise ValueError("unsupported visual product fields")
    _id(value["id"]); _id(value["domain"],"domain"); _id(value["style"],"style")
    if type(value["version"]) is not int or value["version"] < 1: raise ValueError("version must be positive")
    if value["style"] not in STYLE_SYSTEMS: raise ValueError("unknown product style")
    if not isinstance(value["screens"],list) or not 1 <= len(value["screens"]) <= 32 or len(set(value["screens"])) != len(value["screens"]): raise ValueError("invalid product screens")
    for screen in value["screens"]:
        if screen not in SCREEN_TEMPLATES: raise ValueError("product references unknown screen")
    if not isinstance(value["flow"],list) or len(value["flow"]) > 64: raise ValueError("invalid product flow")
    for edge in value["flow"]:
        if not isinstance(edge,list) or len(edge) != 3 or edge[0] not in value["screens"] or edge[1] not in value["screens"]:
            raise ValueError("product flow must connect declared screens")
        _id(edge[2],"flow action")
    if not isinstance(value["tags"],list) or len(value["tags"]) > 24 or len(set(value["tags"])) != len(value["tags"]): raise ValueError("invalid product tags")
    for tag in value["tags"]: _id(tag,"tag")
    if not isinstance(value["name"],str) or not value["name"].strip() or not isinstance(value["intent"],str) or not value["intent"].strip(): raise ValueError("name/intent required")
    if not isinstance(value["quality"],list) or not all(isinstance(x,str) and x.strip() for x in value["quality"]): raise ValueError("quality must be text list")
    canonical_bytes(value)
    return deepcopy(value)


def validate_catalog() -> dict[str, int]:
    for screen in SCREEN_TEMPLATES.values(): validate_screen(screen)
    for product in PRODUCT_ARCHETYPES.values(): validate_product(product)
    return {"styles":len(STYLE_SYSTEMS),"primitives":len(PRIMITIVES),"screens":len(SCREEN_TEMPLATES),"products":len(PRODUCT_ARCHETYPES)}


def catalog() -> dict[str, Any]:
    counts = validate_catalog()
    return {
        "schema": "axm.visual-template-catalog/v1", "counts": counts,
        "styles": sorted(STYLE_SYSTEMS), "primitives": sorted(PRIMITIVES),
        "screens": [{"id":v["id"],"name":v["name"],"domain":v["domain"],"style":v["style"],"tags":list(v["tags"])} for v in sorted(SCREEN_TEMPLATES.values(), key=lambda x:x["id"])],
        "products": [{"id":v["id"],"name":v["name"],"domain":v["domain"],"style":v["style"],"screens":list(v["screens"])} for v in sorted(PRODUCT_ARCHETYPES.values(), key=lambda x:x["id"])],
        "truth": "Known structural starting points; not finished art, aesthetic acceptance, gameplay proof or product canon.",
    }


def get(template_id: str) -> dict[str, Any]:
    _id(template_id)
    if template_id in SCREEN_TEMPLATES: return validate_screen(SCREEN_TEMPLATES[template_id])
    if template_id in PRODUCT_ARCHETYPES: return validate_product(PRODUCT_ARCHETYPES[template_id])
    raise ValueError("unknown visual template: "+template_id)


def select_variant(width: int, height: int) -> str:
    if type(width) is not int or type(height) is not int or not 240 <= width <= 16384 or not 240 <= height <= 16384:
        raise ValueError("viewport width/height must be integer pixels within 240..16384")
    ratio = width / height
    if width < 900 or ratio < 1.15: return "compact"
    if ratio >= 1.9: return "wide"
    return "standard"


def resolve(template_id: str, width: int, height: int, *, variant: str | None = None) -> dict[str, Any]:
    screen = get(template_id)
    if screen["kind"] != "screen": raise ValueError("resolve requires a screen template")
    chosen = select_variant(width,height) if variant is None else _id(variant,"variant")
    if chosen not in screen["variants"]:
        raise ValueError("template does not declare variant: "+chosen)
    regions = {}
    for name, (x,y,w,h) in screen["variants"][chosen].items():
        regions[name] = [round(x*width,4),round(y*height,4),round(w*width,4),round(h*height,4)]
    style = deepcopy(STYLE_SYSTEMS[screen["style"]])
    return {
        "schema":"axm.visual-template-resolution/v1", "template":{"id":screen["id"],"version":screen["version"],"digest":digest(screen)},
        "viewport":{"width":width,"height":height,"variant":chosen,"aspect_ratio":width/height},
        "style_id":screen["style"], "style":style, "intent":screen["intent"], "regions":regions,
        "slots":deepcopy(screen["slots"]), "math_hooks":deepcopy(screen["math_hooks"]), "quality":list(screen["quality"]),
        "truth":"Resolved structural geometry and style intent only; no finished artwork or interaction behavior was observed.",
    }


def product_resolution(product_id: str, width: int, height: int) -> dict[str, Any]:
    product = get(product_id)
    if product["kind"] != "product": raise ValueError("product_resolution requires a product archetype")
    screens = [resolve(screen,width,height) for screen in product["screens"]]
    return {
        "schema":"axm.visual-product-resolution/v1",
        "product":{"id":product["id"],"version":product["version"],"digest":digest(product)},
        "viewport":{"width":width,"height":height}, "style_id":product["style"], "intent":product["intent"],
        "screens":screens, "flow":deepcopy(product["flow"]), "quality":list(product["quality"]),
        "truth":"Product archetype resolved from exact built-in screen versions; it remains an editable foundation, not canon.",
    }


def sticker_definition(template_id: str) -> dict[str, Any]:
    """Wrap one visual archetype for the existing immutable Sticker Registry."""
    template = get(template_id)
    adapter = ADAPTER if template["kind"] == "screen" else PRODUCT_ADAPTER
    return {
        "schema":"axm.sticker/v1", "id":"visual."+template["id"], "version":template["version"], "name":template["name"],
        "tags":sorted(set(["visual-template",template["kind"],*template["tags"]])), "origin":deepcopy(template["origin"]),
        "adapter":adapter, "attachment":{"space":"2d","socket":"product-template","anchor":[0,0]},
        "recipe":{"visual_template":template}, "assets":{}, "parameters":{},
    }


def install_builtins(registry: Any) -> list[dict[str, Any]]:
    """Explicitly register every built-in archetype; idempotence is delegated to Registry."""
    definitions = [sticker_definition(k) for k in sorted(SCREEN_TEMPLATES)] + [sticker_definition(k) for k in sorted(PRODUCT_ARCHETYPES)]
    return registry.register_many(definitions)


def bind_sticker_slots(template_id: str, registry: Any, bindings: Any) -> dict[str, Any]:
    """Validate explicit exact sticker pins against a screen's optional/required slots.

    No search, latest-version choice or implicit substitution happens here.
    """
    screen = get(template_id)
    if screen["kind"] != "screen": raise ValueError("slot binding requires a screen template")
    if not isinstance(bindings,dict): raise ValueError("bindings must be an object")
    slots = {slot["id"]:slot for slot in screen["slots"] if slot["kind"] == "sticker"}
    if set(bindings)-set(slots): raise ValueError("binding references undeclared sticker slot")
    missing = sorted(slot_id for slot_id,slot in slots.items() if slot["required"] and slot_id not in bindings)
    if missing: raise ValueError("required sticker slots are missing: "+", ".join(missing))
    resolved = {}
    try:
        from axm_stickers import digest as sticker_digest
    except ImportError as exc:
        raise ValueError("Sticker Fabric is unavailable") from exc
    for slot_id,pin in bindings.items():
        if not isinstance(pin,dict) or set(pin) != {"id","version","digest"}: raise ValueError("binding requires exact sticker pin")
        definition = registry.get(pin["id"],pin["version"])
        expected = {"id":definition["id"],"version":definition["version"],"digest":sticker_digest(definition)}
        if pin != expected: raise ValueError("binding does not match exact sticker version")
        slot = slots[slot_id]
        if definition["attachment"]["socket"] != slot["socket"]: raise ValueError("sticker binding socket mismatch")
        if set(slot.get("tags",[]))-set(definition["tags"]): raise ValueError("sticker binding lacks required tags")
        resolved[slot_id] = deepcopy(pin)
    return {"schema":"axm.visual-slot-bindings/v1","template":{"id":screen["id"],"version":screen["version"],"digest":digest(screen)},"bindings":resolved}


def _svg_for_resolution(resolved: dict[str, Any], title: str) -> str:
    width=resolved["viewport"]["width"]; height=resolved["viewport"]["height"]
    tokens=resolved["style"]["tokens"]
    radius=max(4.0,min(width,height)*resolved["style"]["shape"]["panel_radius_ratio"])
    line=max(1.0,min(width,height)*resolved["style"]["shape"]["line_ratio"])
    focal=resolved.get("math_hooks",{}).get("focal_region")
    body=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">',
          f'<title>{escape(title)}</title>',
          '<defs>',
          f'<linearGradient id="bg" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{tokens["canvas"]}"/><stop offset="1" stop-color="{tokens["surface"]}"/></linearGradient>',
          f'<linearGradient id="panel" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="{tokens["surface_raised"]}"/><stop offset="1" stop-color="{tokens["surface"]}"/></linearGradient>',
          f'<pattern id="grid" width="{max(24,width/48):g}" height="{max(24,height/28):g}" patternUnits="userSpaceOnUse"><path d="M 0 0 H {max(24,width/48):g} M 0 0 V {max(24,height/28):g}" stroke="{tokens["line"]}" stroke-opacity=".15" stroke-width="1"/></pattern>',
          '</defs>',
          f'<rect width="{width}" height="{height}" fill="url(#bg)"/>',
          f'<rect width="{width}" height="{height}" fill="url(#grid)"/>']
    regions=resolved["regions"]
    background_names=[n for n in regions if n in {"world","context","viewport","vehicle","route-map"}]
    foreground_names=[n for n in regions if n not in background_names]
    for index,name in enumerate(background_names+foreground_names):
        x,y,w,h=regions[name]
        background=name in background_names
        stroke=tokens["accent"] if name == focal else tokens["line"]
        stroke_width=line*2.2 if name == focal else line
        fill=tokens["surface"] if background else "url(#panel)"
        opacity="0.40" if background else "0.94"
        body.append(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius:g}" fill="{fill}" fill-opacity="{opacity}" stroke="{stroke}" stroke-width="{stroke_width:g}"/>')
        pad=max(8.0,min(w,h)*0.055)
        size=max(10.0,min(w*0.075,h*0.20,28.0))
        body.append(f'<text x="{x+pad:g}" y="{y+pad+size:g}" fill="{tokens["text"]}" font-family="system-ui,sans-serif" font-size="{size:g}" font-weight="700" letter-spacing=".04em">{escape(name.replace("-"," ").upper())}</text>')
        if not background and h > size*3.2 and w > 80:
            bar_y=y+pad+size*1.65
            body.append(f'<rect x="{x+pad:g}" y="{bar_y:g}" width="{max(8,w-pad*2):g}" height="{max(2,line*1.2):g}" rx="1" fill="{tokens["line"]}"/>')
            body.append(f'<rect x="{x+pad:g}" y="{bar_y:g}" width="{max(6,(w-pad*2)*(.68 if name==focal else .34)):g}" height="{max(2,line*1.2):g}" rx="1" fill="{tokens["accent"]}"/>')
            if h > size*5:
                for row in range(2):
                    ry=bar_y+size*(1.45+row*1.2)
                    rw=(w-pad*2)*(0.78-row*.17)
                    body.append(f'<rect x="{x+pad:g}" y="{ry:g}" width="{max(8,rw):g}" height="{max(3,line*2):g}" rx="2" fill="{tokens["muted"]}" fill-opacity=".22"/>')
        if name == focal and w > 70 and h > 45:
            metric_size=max(18.0,min(w*.24,h*.36,64.0))
            body.append(f'<text x="{x+w-pad:g}" y="{y+h-pad:g}" text-anchor="end" fill="{tokens["accent"]}" font-family="system-ui,sans-serif" font-size="{metric_size:g}" font-weight="800">000</text>')
    footer_size=max(10,min(width,height)*0.016)
    body.append(f'<line x1="{width*.02:g}" y1="{height*.965:g}" x2="{width*.98:g}" y2="{height*.965:g}" stroke="{tokens["line"]}" stroke-width="{line:g}"/>')
    body.append(f'<text x="{width*.02:g}" y="{height*.988:g}" fill="{tokens["muted"]}" font-family="system-ui,sans-serif" font-size="{footer_size:g}">AXM visual archetype · {escape(resolved["viewport"]["variant"])} · structural preview</text>')
    body.append('</svg>')
    return ''.join(body)


def screen_project(template_id: str, width: int = 1920, height: int = 1080, title: str | None = None) -> dict[str, Any]:
    resolved=resolve(template_id,width,height); screen=get(template_id); title=screen["name"] if title is None else title
    if not isinstance(title,str) or not title.strip() or len(title)>160: raise ValueError("title must be bounded text")
    svg=_svg_for_resolution(resolved,title)
    manifest=json.dumps(resolved,indent=2,ensure_ascii=False,sort_keys=True)
    html=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>body{{margin:0;background:#070a0e;color:#eef4f6;font:16px system-ui}}main{{max-width:1500px;margin:auto;padding:28px}}img{{width:100%;height:auto;border:1px solid #33424c;border-radius:14px}}code{{color:#9ee8df}}</style><main><h1>{escape(title)}</h1><p>{escape(screen["intent"])}</p><img src="screen.svg" alt="structural visual template preview"><p><code>{escape(template_id)}</code> · exact normalized structure resolved to {width}×{height}px. This preview is not finished art.</p></main></html>'''
    return {"id":"axm.visual."+template_id,"version":"1.0.0","project_type":"static-web","files":{"index.html":html,"screen.svg":svg,"template.json":manifest}}


def product_project(product_id: str, width: int = 1920, height: int = 1080, title: str | None = None) -> dict[str, Any]:
    product=get(product_id)
    if product["kind"] != "product": raise ValueError("product_project requires a product archetype")
    resolved=product_resolution(product_id,width,height); title=product["name"] if title is None else title
    if not isinstance(title,str) or not title.strip() or len(title)>160: raise ValueError("title must be bounded text")
    files={"product.json":json.dumps(resolved,indent=2,ensure_ascii=False,sort_keys=True)}
    cards=[]
    for index,screen in enumerate(resolved["screens"]):
        sid=screen["template"]["id"]; filename=f"screen-{index+1:02d}.svg"
        files[filename]=_svg_for_resolution(screen,get(sid)["name"])
        cards.append(f'<article><h2>{escape(get(sid)["name"])}</h2><img src="{filename}" alt="{escape(sid,quote=True)} structural preview"><code>{escape(sid)}</code></article>')
    flow=' → '.join(escape(edge[2]) for edge in product["flow"])
    tokens=STYLE_SYSTEMS[product["style"]]["tokens"]
    files["index.html"]=f'''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>{escape(title)}</title><style>body{{margin:0;background:{tokens['canvas']};color:{tokens['text']};font:16px system-ui}}main{{max-width:1500px;margin:auto;padding:28px}}section{{display:grid;grid-template-columns:repeat(auto-fit,minmax(420px,1fr));gap:22px}}article{{background:{tokens['surface']};border:1px solid {tokens['line']};padding:16px;border-radius:16px}}img{{width:100%;height:auto;background:#070a0e}}code{{color:{tokens['accent']}}}.flow{{color:{tokens['muted']};overflow-wrap:anywhere}}</style><main><h1>{escape(title)}</h1><p>{escape(product['intent'])}</p><p class="flow">Flow: {flow}</p><section>{''.join(cards)}</section><p>Known structural foundation only: editable, replaceable and non-canonical.</p></main></html>'''
    return {"id":"axm.visual.product."+product_id,"version":"1.0.0","project_type":"static-web","files":files}


# Validate shipped data at import time. A broken built-in is a package defect, not a user input issue.
validate_catalog()

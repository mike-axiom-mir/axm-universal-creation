"""Second-wave professional visual foundations for AXM Universal Creation.

This module deliberately extends the v1 visual-template dictionaries instead of
creating a second registry or schema. It is imported by ``visual_templates``
before built-in validation. Everything remains deterministic, offline, editable
and non-canonical.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _merge_unique(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap = sorted(set(target) & set(additions))
    if overlap:
        raise RuntimeError(f"visual template {label} extension collides with built-ins: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def extend_catalog(namespace: dict[str, Any]) -> None:
    """Install professional game foundations into the existing v1 catalog once."""
    styles = namespace["STYLE_SYSTEMS"]
    primitives = namespace["PRIMITIVES"]
    screens = namespace["SCREEN_TEMPLATES"]
    products = namespace["PRODUCT_ARCHETYPES"]
    screen = namespace["_screen"]
    origin = namespace["_origin"]
    racing_common = namespace["RACING_COMMON"]

    new_styles = {
        "game.coop.tactical": {
            "intent": "co-op action clarity with readable team state, decisive objectives and restrained tactical chrome",
            "tokens": {
                "canvas": "#0a1016", "surface": "#121c25", "surface_raised": "#1a2833",
                "text": "#edf5f4", "muted": "#9eafb2", "accent": "#84dfb9",
                "warning": "#f4c66f", "danger": "#f07878", "line": "#334750",
            },
            "shape": {"panel_radius_ratio": 0.014, "cut_ratio": 0.006, "line_ratio": 0.0014},
            "type": {"display_weight": 740, "body_weight": 510, "metric_scale": 1.65, "tracking": 0.018},
            "depth": {"layers": 4, "shadow": "tight", "glass": "light"},
            "motion": {"fast_ms": 85, "standard_ms": 170, "slow_ms": 300, "principle": "team state before flourish"},
        },
        "game.rts.command": {
            "intent": "macro-scale command readability with dense state, stable spatial anchors and explicit strategic consequences",
            "tokens": {
                "canvas": "#080e13", "surface": "#101a22", "surface_raised": "#172631",
                "text": "#edf2f3", "muted": "#98a8ae", "accent": "#8fc7ff",
                "warning": "#eec774", "danger": "#ef7777", "line": "#344650",
            },
            "shape": {"panel_radius_ratio": 0.009, "cut_ratio": 0.003, "line_ratio": 0.0012},
            "type": {"display_weight": 710, "body_weight": 500, "metric_scale": 1.48, "tracking": 0.012},
            "depth": {"layers": 5, "shadow": "subtle", "glass": "restrained"},
            "motion": {"fast_ms": 75, "standard_ms": 150, "slow_ms": 260, "principle": "preserve map context while state changes"},
        },
    }

    new_primitives = {
        "selection-card": {"role": "choose one comparable object without losing context", "states": ["rest", "focused", "selected", "locked", "owned", "unavailable"], "selection_must_have_non_color_cue": True},
        "player-seat": {"role": "show seat identity, controller ownership and readiness", "states": ["empty", "joining", "ready", "not-ready", "disconnected", "ai-seat"], "ownership_must_be_explicit": True},
        "stat-comparison": {"role": "compare current and candidate values", "states": ["equal", "gain", "loss", "unknown"], "requires_numeric_or_text_delta": True},
        "slider-row": {"role": "bounded tuning or preference control", "states": ["rest", "focused", "adjusting", "disabled", "default"], "show_current_and_default": True},
        "segmented-control": {"role": "small mutually exclusive mode choice", "states": ["rest", "selected", "disabled"], "selection_must_not_depend_on_color": True},
        "leaderboard-row": {"role": "stable placement comparison", "states": ["normal", "local-player", "team-mate", "disconnected"], "stable_columns": True},
        "countdown": {"role": "time-critical transition into control", "states": ["waiting", "three", "two", "one", "go", "aborted"], "must_not_delay_input_activation": True},
        "modal": {"role": "bounded blocking decision", "states": ["info", "confirm", "danger", "busy"], "requires_escape_or_explicit_cancel_when_reversible": True},
        "telemetry-strip": {"role": "compact changing performance signals", "states": ["normal", "warning", "critical", "unavailable"], "history_must_not_obscure_current_value": True},
        "tooltip": {"role": "secondary explanation without becoming required for core operation", "states": ["hidden", "visible"], "must_not_hold_unique_critical_state": True},
        "carousel": {"role": "browse visual choices while preserving current selection", "states": ["rest", "focused", "selected", "loading"], "selection_position_must_remain_clear": True},
        "tab-strip": {"role": "switch peer views without changing product location", "states": ["rest", "selected", "disabled"], "stable_order": True},
        "input-hint": {"role": "explain available player input for the current seat/device", "states": ["keyboard", "gamepad", "touch", "mixed", "hidden"], "device_source_must_be_explicit": True},
        "loading-state": {"role": "show bounded waiting and what is being prepared", "states": ["starting", "progress", "ready", "failed", "cancelled"], "fake_progress_forbidden": True},
        "empty-state": {"role": "explain an intentionally empty surface and a valid next action", "states": ["empty", "filtered-empty", "unavailable"], "must_not_fake_content": True},
        "recovery-banner": {"role": "surface degraded/disconnected state and safe recovery choices", "states": ["warning", "reconnecting", "recovered", "failed"], "must_preserve_user_choice": True},
    }

    _merge_unique(styles, new_styles, "style")
    _merge_unique(primitives, new_primitives, "primitive")

    race_quality = list(racing_common) + [
        "setup screens must preserve the selected vehicle/event identity across transitions",
        "destructive or network-dependent actions require explicit visible state",
        "controller and split-screen ownership must be understandable before launch",
    ]
    coop_quality = [
        "team state and objective state outrank decorative chrome",
        "each human or machine seat exposes comparable player-facing information",
        "revive, danger and disconnect state must not depend on color alone",
        "loadout changes remain inspectable before commitment",
    ]
    rts_quality = [
        "world/map context remains primary while command panels change",
        "selection and ownership stay legible at macro scale",
        "resource, production and threat changes use stable anchors",
        "strategic consequences are explicit before irreversible commitment",
    ]

    racing_screens = {
        "game.racing.home": screen(
            "game.racing.home", "Racing home and main menu", "game.racing", "racing.performance",
            "establish identity, current progression and one obvious path back into driving",
            {
                "compact": {"identity":(0.04,0.05,0.92,0.16),"hero":(0.04,0.24,0.92,0.35),"primary":(0.04,0.62,0.56,0.25),"secondary":(0.63,0.62,0.33,0.25),"status":(0.04,0.90,0.92,0.06)},
                "standard": {"identity":(0.04,0.06,0.44,0.13),"hero":(0.36,0.11,0.60,0.63),"primary":(0.04,0.27,0.27,0.47),"secondary":(0.04,0.78,0.92,0.14),"status":(0.52,0.06,0.44,0.07)},
                "wide": {"identity":(0.035,0.06,0.36,0.12),"hero":(0.36,0.10,0.61,0.65),"primary":(0.035,0.25,0.26,0.50),"secondary":(0.035,0.80,0.935,0.12),"status":(0.68,0.04,0.29,0.06)},
            },
            slots=[{"id":"hero-vehicle","kind":"content","required":False},{"id":"game-mark","kind":"sticker","socket":"surface","tags":["identity"],"required":False}],
            tags=["game","racing","home","menu"], math_hooks={"hero_area_ratio":[0.48,0.68]}, quality=race_quality,
        ),
        "game.racing.vehicle-select": screen(
            "game.racing.vehicle-select", "Racing vehicle selection", "game.racing", "racing.performance",
            "compare vehicles visually and numerically while keeping ownership, class and current choice obvious",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"vehicle":(0.03,0.14,0.94,0.38),"carousel":(0.03,0.55,0.94,0.16),"stats":(0.03,0.74,0.58,0.18),"actions":(0.64,0.74,0.33,0.18)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"carousel":(0.025,0.14,0.19,0.72),"vehicle":(0.245,0.14,0.49,0.58),"stats":(0.76,0.14,0.215,0.58),"actions":(0.245,0.76,0.73,0.12)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"carousel":(0.02,0.14,0.16,0.73),"vehicle":(0.21,0.14,0.54,0.59),"stats":(0.78,0.14,0.20,0.59),"actions":(0.21,0.78,0.77,0.105)},
            },
            slots=[{"id":"vehicle-stage","kind":"content","required":True},{"id":"class-mark","kind":"sticker","socket":"surface","tags":["identity"],"required":False}],
            tags=["game","racing","vehicle","selection"], math_hooks={"hero_area_ratio":[0.46,0.62],"comparison_panel_ratio":[0.18,0.24]}, quality=race_quality,
        ),
        "game.racing.tuning": screen(
            "game.racing.tuning", "Detailed racing tuning", "game.racing", "racing.performance",
            "support precise reversible tuning while showing live deltas and preserving vehicle context",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"vehicle":(0.03,0.14,0.94,0.26),"tabs":(0.03,0.43,0.94,0.08),"controls":(0.03,0.54,0.58,0.36),"telemetry":(0.64,0.54,0.33,0.23),"actions":(0.64,0.80,0.33,0.10)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"vehicle":(0.025,0.14,0.31,0.67),"tabs":(0.36,0.14,0.615,0.08),"controls":(0.36,0.25,0.39,0.56),"telemetry":(0.775,0.25,0.20,0.39),"actions":(0.775,0.67,0.20,0.14)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"vehicle":(0.02,0.14,0.34,0.68),"tabs":(0.39,0.14,0.59,0.075),"controls":(0.39,0.245,0.39,0.575),"telemetry":(0.80,0.245,0.18,0.40),"actions":(0.80,0.68,0.18,0.14)},
            },
            slots=[{"id":"vehicle-stage","kind":"content","required":True}], tags=["game","racing","tuning","telemetry"],
            math_hooks={"control_row_height_ratio":[0.055,0.085],"delta_column_ratio":[0.18,0.28]}, quality=race_quality,
        ),
        "game.racing.livery": screen(
            "game.racing.livery", "Racing livery and appearance", "game.racing", "racing.performance",
            "keep vehicle appearance dominant while exposing layers, palette, decals and explicit save state",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"vehicle":(0.03,0.14,0.94,0.40),"layers":(0.03,0.57,0.30,0.31),"tools":(0.36,0.57,0.61,0.20),"actions":(0.36,0.80,0.61,0.08)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"layers":(0.025,0.14,0.19,0.73),"vehicle":(0.24,0.14,0.50,0.61),"tools":(0.765,0.14,0.21,0.61),"actions":(0.24,0.79,0.735,0.08)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"layers":(0.02,0.14,0.17,0.74),"vehicle":(0.22,0.14,0.55,0.62),"tools":(0.80,0.14,0.18,0.62),"actions":(0.22,0.80,0.76,0.08)},
            },
            slots=[{"id":"vehicle-stage","kind":"content","required":True},{"id":"decal-library","kind":"system","required":False}],
            tags=["game","racing","livery","appearance"], math_hooks={"hero_area_ratio":[0.48,0.66]}, quality=race_quality,
        ),
        "game.racing.pre-race": screen(
            "game.racing.pre-race", "Pre-race briefing and grid", "game.racing", "racing.performance",
            "confirm event, route, vehicle, players and launch conditions before control begins",
            {
                "compact": {"event":(0.03,0.03,0.94,0.14),"route":(0.03,0.20,0.94,0.27),"grid":(0.03,0.50,0.58,0.34),"conditions":(0.64,0.50,0.33,0.20),"launch":(0.64,0.73,0.33,0.11)},
                "standard": {"event":(0.03,0.04,0.94,0.12),"route":(0.03,0.20,0.42,0.57),"grid":(0.48,0.20,0.29,0.57),"conditions":(0.80,0.20,0.17,0.35),"launch":(0.80,0.60,0.17,0.17)},
                "wide": {"event":(0.025,0.04,0.95,0.11),"route":(0.025,0.19,0.45,0.59),"grid":(0.50,0.19,0.28,0.59),"conditions":(0.81,0.19,0.165,0.36),"launch":(0.81,0.61,0.165,0.17)},
            }, tags=["game","racing","briefing","grid"], quality=race_quality,
        ),
        "game.racing.loading": screen(
            "game.racing.loading", "Racing loading and readiness", "game.racing", "racing.performance",
            "show exactly what is loading, seat readiness and failure/retry state without fake progress",
            {
                "compact": {"hero":(0.04,0.08,0.92,0.42),"event":(0.04,0.54,0.56,0.15),"players":(0.63,0.54,0.33,0.15),"progress":(0.04,0.74,0.92,0.09),"status":(0.04,0.86,0.92,0.08)},
                "standard": {"hero":(0.05,0.08,0.62,0.69),"event":(0.70,0.08,0.25,0.22),"players":(0.70,0.34,0.25,0.27),"progress":(0.05,0.82,0.90,0.07),"status":(0.70,0.65,0.25,0.12)},
                "wide": {"hero":(0.05,0.07,0.64,0.71),"event":(0.72,0.07,0.23,0.22),"players":(0.72,0.33,0.23,0.29),"progress":(0.05,0.84,0.90,0.065),"status":(0.72,0.66,0.23,0.12)},
            }, tags=["game","racing","loading","readiness"], quality=race_quality + ["loading progress must be observed or explicitly indeterminate"],
        ),
        "game.racing.countdown": screen(
            "game.racing.countdown", "Race start countdown", "game.racing", "racing.performance",
            "transition from waiting to control without obscuring the road, vehicle or start state",
            {
                "compact": {"world":(0,0,1,1),"countdown":(0.36,0.25,0.28,0.34),"grid-status":(0.03,0.05,0.28,0.12),"input":(0.69,0.05,0.28,0.12)},
                "standard": {"world":(0,0,1,1),"countdown":(0.40,0.24,0.20,0.36),"grid-status":(0.025,0.05,0.24,0.11),"input":(0.735,0.05,0.24,0.11)},
                "wide": {"world":(0,0,1,1),"countdown":(0.425,0.23,0.15,0.37),"grid-status":(0.02,0.05,0.20,0.10),"input":(0.78,0.05,0.20,0.10)},
            }, tags=["game","racing","countdown","start"], math_hooks={"focal_region":"countdown","focal_width_ratio":[0.15,0.28]}, quality=race_quality,
        ),
        "game.racing.hud.split": screen(
            "game.racing.hud.split", "Split-screen racing HUD", "game.racing", "racing.performance",
            "give each local seat the essential race state inside its own viewport without cross-seat ambiguity",
            {
                "compact": {"world":(0,0,1,1),"seat":(0.025,0.035,0.22,0.10),"position":(0.025,0.15,0.20,0.10),"route":(0.75,0.035,0.225,0.22),"speed":(0.39,0.79,0.22,0.17),"vehicle-state":(0.025,0.81,0.20,0.14)},
                "standard": {"world":(0,0,1,1),"seat":(0.022,0.035,0.17,0.09),"position":(0.022,0.14,0.16,0.09),"route":(0.80,0.035,0.178,0.22),"speed":(0.405,0.80,0.19,0.16),"vehicle-state":(0.022,0.815,0.16,0.13)},
                "wide": {"world":(0,0,1,1),"seat":(0.018,0.04,0.14,0.085),"position":(0.018,0.14,0.13,0.085),"route":(0.85,0.04,0.132,0.21),"speed":(0.425,0.81,0.15,0.15),"vehicle-state":(0.018,0.82,0.13,0.12)},
            }, tags=["game","racing","hud","splitscreen"], math_hooks={"focal_region":"speed","edge_safe_ratio":[0.018,0.04]}, quality=race_quality + ["every viewport must expose seat identity before shared-screen confusion can occur"],
        ),
        "game.racing.replay": screen(
            "game.racing.replay", "Race replay and photo review", "game.racing", "racing.performance",
            "keep recorded action dominant while timeline, cameras, markers and export state remain inspectable",
            {
                "compact": {"viewer":(0.03,0.03,0.94,0.52),"timeline":(0.03,0.58,0.94,0.10),"cameras":(0.03,0.71,0.29,0.22),"markers":(0.35,0.71,0.29,0.22),"actions":(0.67,0.71,0.30,0.22)},
                "standard": {"viewer":(0.025,0.03,0.73,0.70),"cameras":(0.78,0.03,0.195,0.32),"markers":(0.78,0.38,0.195,0.35),"timeline":(0.025,0.77,0.73,0.18),"actions":(0.78,0.77,0.195,0.18)},
                "wide": {"viewer":(0.02,0.03,0.76,0.71),"cameras":(0.80,0.03,0.18,0.32),"markers":(0.80,0.38,0.18,0.36),"timeline":(0.02,0.78,0.76,0.17),"actions":(0.80,0.78,0.18,0.17)},
            }, tags=["game","racing","replay","photo"], quality=race_quality,
        ),
        "game.racing.season": screen(
            "game.racing.season", "Racing season and progression", "game.racing", "racing.performance",
            "show progression, upcoming events and rewards without disguising locked or incomplete state",
            {
                "compact": {"header":(0.03,0.03,0.94,0.09),"progress":(0.03,0.15,0.94,0.13),"calendar":(0.03,0.31,0.94,0.34),"standings":(0.03,0.68,0.46,0.26),"rewards":(0.52,0.68,0.45,0.26)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"progress":(0.025,0.14,0.95,0.12),"calendar":(0.025,0.29,0.55,0.66),"standings":(0.605,0.29,0.18,0.66),"rewards":(0.81,0.29,0.165,0.66)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"progress":(0.02,0.14,0.96,0.11),"calendar":(0.02,0.28,0.58,0.67),"standings":(0.625,0.28,0.17,0.67),"rewards":(0.82,0.28,0.16,0.67)},
            }, tags=["game","racing","season","progression"], quality=race_quality,
        ),
        "game.racing.settings": screen(
            "game.racing.settings", "Racing settings", "game.racing", "racing.performance",
            "separate driving, controls, display, audio and online preferences with visible scope and defaults",
            {
                "compact": {"header":(0.04,0.03,0.92,0.08),"categories":(0.04,0.14,0.92,0.13),"settings":(0.04,0.30,0.92,0.54),"actions":(0.04,0.87,0.92,0.09)},
                "standard": {"header":(0.03,0.03,0.94,0.08),"categories":(0.03,0.14,0.20,0.82),"settings":(0.26,0.14,0.71,0.68),"actions":(0.26,0.85,0.71,0.11)},
                "wide": {"header":(0.025,0.03,0.95,0.075),"categories":(0.025,0.14,0.18,0.82),"settings":(0.23,0.14,0.745,0.68),"actions":(0.23,0.85,0.745,0.11)},
            }, tags=["game","racing","settings","controls"], quality=race_quality + ["control remapping must expose conflicts instead of silently replacing bindings"],
        ),
        "game.racing.accessibility": screen(
            "game.racing.accessibility", "Racing accessibility", "game.racing", "racing.performance",
            "make readability, input, assistance and sensory options understandable with immediate consequence previews",
            {
                "compact": {"header":(0.04,0.03,0.92,0.08),"categories":(0.04,0.14,0.92,0.13),"options":(0.04,0.30,0.58,0.54),"preview":(0.65,0.30,0.31,0.38),"actions":(0.65,0.72,0.31,0.12)},
                "standard": {"header":(0.03,0.03,0.94,0.08),"categories":(0.03,0.14,0.20,0.82),"options":(0.26,0.14,0.43,0.70),"preview":(0.72,0.14,0.25,0.48),"actions":(0.72,0.66,0.25,0.18)},
                "wide": {"header":(0.025,0.03,0.95,0.075),"categories":(0.025,0.14,0.18,0.82),"options":(0.23,0.14,0.46,0.70),"preview":(0.72,0.14,0.255,0.48),"actions":(0.72,0.66,0.255,0.18)},
            }, tags=["game","racing","accessibility","preferences"], quality=race_quality + ["accessibility options must not be hidden behind expert terminology","preview must be labeled when it is only illustrative"],
        ),
        "game.racing.recovery": screen(
            "game.racing.recovery", "Racing disconnect and recovery", "game.racing", "racing.performance",
            "preserve race/session truth while making reconnection, retry and exit choices explicit",
            {
                "compact": {"context":(0,0,1,1),"banner":(0.12,0.14,0.76,0.18),"status":(0.18,0.36,0.64,0.18),"choices":(0.18,0.58,0.64,0.25)},
                "standard": {"context":(0,0,1,1),"banner":(0.24,0.16,0.52,0.16),"status":(0.29,0.37,0.42,0.16),"choices":(0.29,0.58,0.42,0.23)},
                "wide": {"context":(0,0,1,1),"banner":(0.28,0.16,0.44,0.16),"status":(0.33,0.37,0.34,0.16),"choices":(0.33,0.58,0.34,0.23)},
            }, tags=["game","racing","recovery","network"], quality=race_quality + ["never present reconnection as successful until observed","leaving must not silently destroy recoverable session state"],
        ),
    }

    coop_screens = {
        "game.coop.home": screen(
            "game.coop.home", "Co-op action home", "game.coop", "game.coop.tactical",
            "make continue/play-together the dominant path while preserving recent party and progress state",
            {
                "compact": {"identity":(0.04,0.05,0.92,0.14),"hero":(0.04,0.22,0.92,0.35),"party":(0.04,0.60,0.44,0.25),"actions":(0.52,0.60,0.44,0.25),"status":(0.04,0.89,0.92,0.07)},
                "standard": {"identity":(0.04,0.05,0.40,0.12),"hero":(0.36,0.11,0.60,0.61),"party":(0.04,0.25,0.27,0.31),"actions":(0.04,0.60,0.27,0.24),"status":(0.52,0.05,0.44,0.07)},
                "wide": {"identity":(0.035,0.05,0.34,0.11),"hero":(0.35,0.10,0.62,0.63),"party":(0.035,0.24,0.25,0.32),"actions":(0.035,0.60,0.25,0.24),"status":(0.70,0.04,0.27,0.06)},
            }, tags=["game","coop","home","menu"], quality=coop_quality,
        ),
        "game.coop.lobby": screen(
            "game.coop.lobby", "Co-op party lobby", "game.coop", "game.coop.tactical",
            "make seat ownership, readiness, mission choice and party state immediately inspectable",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"mission":(0.03,0.14,0.94,0.20),"seats":(0.03,0.37,0.94,0.38),"options":(0.03,0.78,0.46,0.17),"launch":(0.52,0.78,0.45,0.17)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"mission":(0.025,0.14,0.27,0.69),"seats":(0.32,0.14,0.45,0.69),"options":(0.795,0.14,0.18,0.46),"launch":(0.795,0.65,0.18,0.18)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"mission":(0.02,0.14,0.25,0.70),"seats":(0.30,0.14,0.48,0.70),"options":(0.81,0.14,0.17,0.47),"launch":(0.81,0.66,0.17,0.18)},
            }, tags=["game","coop","lobby","party"], quality=coop_quality,
        ),
        "game.coop.loadout": screen(
            "game.coop.loadout", "Co-op loadout", "game.coop", "game.coop.tactical",
            "compare role, weapons, equipment and team fit before a seat commits its loadout",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"character":(0.03,0.14,0.94,0.28),"inventory":(0.03,0.45,0.58,0.39),"team-fit":(0.64,0.45,0.33,0.22),"actions":(0.64,0.70,0.33,0.14)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"inventory":(0.025,0.14,0.24,0.72),"character":(0.29,0.14,0.45,0.58),"team-fit":(0.765,0.14,0.21,0.39),"actions":(0.29,0.76,0.685,0.10)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"inventory":(0.02,0.14,0.21,0.73),"character":(0.26,0.14,0.49,0.59),"team-fit":(0.78,0.14,0.20,0.40),"actions":(0.26,0.78,0.72,0.09)},
            }, tags=["game","coop","loadout","equipment"], quality=coop_quality,
        ),
        "game.coop.hud": screen(
            "game.coop.hud", "Co-op action HUD", "game.coop", "game.coop.tactical",
            "keep objective, self state, team state and immediate threats readable without covering the play space",
            {
                "compact": {"world":(0,0,1,1),"objective":(0.31,0.03,0.38,0.09),"self":(0.025,0.79,0.23,0.17),"team":(0.025,0.04,0.20,0.25),"ability":(0.37,0.84,0.26,0.12),"threat":(0.76,0.04,0.215,0.16)},
                "standard": {"world":(0,0,1,1),"objective":(0.35,0.03,0.30,0.08),"self":(0.022,0.81,0.19,0.15),"team":(0.022,0.04,0.17,0.24),"ability":(0.39,0.85,0.22,0.11),"threat":(0.80,0.04,0.178,0.15)},
                "wide": {"world":(0,0,1,1),"objective":(0.38,0.03,0.24,0.075),"self":(0.018,0.82,0.16,0.14),"team":(0.018,0.04,0.14,0.23),"ability":(0.41,0.86,0.18,0.10),"threat":(0.84,0.04,0.142,0.14)},
            }, tags=["game","coop","hud","action"], math_hooks={"focal_region":"objective","edge_safe_ratio":[0.018,0.04]}, quality=coop_quality,
        ),
        "game.coop.pause": screen(
            "game.coop.pause", "Co-op pause and session overlay", "game.coop", "game.coop.tactical",
            "preserve session context while distinguishing local pause, shared pause and leave-session consequences",
            {
                "compact": {"context":(0,0,1,1),"menu":(0.16,0.12,0.68,0.76),"party":(0.20,0.17,0.60,0.14),"actions":(0.25,0.37,0.50,0.43)},
                "standard": {"context":(0,0,1,1),"menu":(0.29,0.11,0.42,0.78),"party":(0.33,0.16,0.34,0.14),"actions":(0.35,0.37,0.30,0.44)},
                "wide": {"context":(0,0,1,1),"menu":(0.34,0.11,0.32,0.78),"party":(0.37,0.16,0.26,0.14),"actions":(0.39,0.37,0.22,0.44)},
            }, tags=["game","coop","pause","session"], quality=coop_quality,
        ),
        "game.coop.results": screen(
            "game.coop.results", "Co-op mission results", "game.coop", "game.coop.tactical",
            "show shared outcome plus each seat's contribution without turning teamwork into a misleading single score",
            {
                "compact": {"outcome":(0.04,0.05,0.92,0.14),"team":(0.04,0.22,0.92,0.22),"players":(0.04,0.47,0.92,0.29),"rewards":(0.04,0.79,0.55,0.15),"actions":(0.62,0.79,0.34,0.15)},
                "standard": {"outcome":(0.04,0.05,0.92,0.13),"team":(0.04,0.22,0.23,0.49),"players":(0.30,0.22,0.42,0.49),"rewards":(0.75,0.22,0.21,0.49),"actions":(0.30,0.76,0.66,0.13)},
                "wide": {"outcome":(0.05,0.05,0.90,0.12),"team":(0.05,0.22,0.20,0.49),"players":(0.28,0.22,0.45,0.49),"rewards":(0.76,0.22,0.19,0.49),"actions":(0.28,0.77,0.67,0.12)},
            }, tags=["game","coop","results","team"], quality=coop_quality,
        ),
        "game.coop.settings": screen(
            "game.coop.settings", "Co-op game settings", "game.coop", "game.coop.tactical",
            "keep local preferences distinct from party/session rules and show who can change each scope",
            {
                "compact": {"header":(0.04,0.03,0.92,0.08),"scope":(0.04,0.14,0.92,0.11),"categories":(0.04,0.28,0.92,0.12),"settings":(0.04,0.43,0.92,0.40),"actions":(0.04,0.86,0.92,0.10)},
                "standard": {"header":(0.03,0.03,0.94,0.08),"categories":(0.03,0.14,0.20,0.82),"scope":(0.26,0.14,0.71,0.10),"settings":(0.26,0.27,0.71,0.55),"actions":(0.26,0.85,0.71,0.11)},
                "wide": {"header":(0.025,0.03,0.95,0.075),"categories":(0.025,0.14,0.18,0.82),"scope":(0.23,0.14,0.745,0.10),"settings":(0.23,0.27,0.745,0.55),"actions":(0.23,0.85,0.745,0.11)},
            }, tags=["game","coop","settings","scope"], quality=coop_quality,
        ),
    }

    rts_screens = {
        "game.rts.lobby": screen(
            "game.rts.lobby", "RTS world-entry lobby", "game.rts", "game.rts.command",
            "show faction/seat, world state, allies and entry conditions before joining the persistent command layer",
            {
                "compact": {"world":(0.03,0.03,0.94,0.30),"seat":(0.03,0.36,0.45,0.25),"allies":(0.52,0.36,0.45,0.25),"conditions":(0.03,0.64,0.62,0.28),"launch":(0.68,0.64,0.29,0.28)},
                "standard": {"world":(0.025,0.03,0.54,0.78),"seat":(0.59,0.03,0.185,0.36),"allies":(0.79,0.03,0.185,0.36),"conditions":(0.59,0.43,0.385,0.23),"launch":(0.59,0.70,0.385,0.11)},
                "wide": {"world":(0.02,0.03,0.58,0.80),"seat":(0.625,0.03,0.17,0.37),"allies":(0.81,0.03,0.17,0.37),"conditions":(0.625,0.44,0.355,0.23),"launch":(0.625,0.72,0.355,0.11)},
            }, tags=["game","rts","lobby","world"], quality=rts_quality,
        ),
        "game.rts.world": screen(
            "game.rts.world", "RTS persistent world map", "game.rts", "game.rts.command",
            "keep the strategic world primary while surfacing regions, fronts, logistics and selected context",
            {
                "compact": {"world":(0.02,0.03,0.96,0.61),"regions":(0.02,0.68,0.35,0.28),"selection":(0.40,0.68,0.35,0.28),"alerts":(0.78,0.68,0.20,0.28)},
                "standard": {"world":(0.18,0.03,0.62,0.94),"regions":(0.015,0.03,0.145,0.94),"selection":(0.82,0.03,0.165,0.59),"alerts":(0.82,0.66,0.165,0.31)},
                "wide": {"world":(0.15,0.03,0.67,0.94),"regions":(0.012,0.03,0.12,0.94),"selection":(0.84,0.03,0.148,0.59),"alerts":(0.84,0.66,0.148,0.31)},
            }, tags=["game","rts","world","strategy"], quality=rts_quality,
        ),
        "game.rts.hud": screen(
            "game.rts.hud", "RTS command HUD", "game.rts", "game.rts.command",
            "support continuous selection, resources, production and tactical command without shrinking the battlefield into a dashboard",
            {
                "compact": {"world":(0,0,1,1),"resources":(0.02,0.02,0.42,0.08),"alerts":(0.66,0.02,0.32,0.15),"selection":(0.02,0.77,0.28,0.21),"commands":(0.33,0.82,0.42,0.16),"minimap":(0.78,0.75,0.20,0.23)},
                "standard": {"world":(0,0,1,1),"resources":(0.02,0.02,0.34,0.075),"alerts":(0.76,0.02,0.22,0.15),"selection":(0.02,0.78,0.24,0.20),"commands":(0.30,0.83,0.42,0.15),"minimap":(0.78,0.73,0.20,0.25)},
                "wide": {"world":(0,0,1,1),"resources":(0.018,0.02,0.28,0.07),"alerts":(0.82,0.02,0.162,0.14),"selection":(0.018,0.79,0.20,0.19),"commands":(0.29,0.84,0.42,0.14),"minimap":(0.80,0.72,0.182,0.26)},
            }, tags=["game","rts","hud","command"], quality=rts_quality,
        ),
        "game.rts.build": screen(
            "game.rts.build", "RTS production and build planner", "game.rts", "game.rts.command",
            "compare build options, queues, prerequisites and map placement consequences before commitment",
            {
                "compact": {"world":(0.03,0.03,0.94,0.35),"catalog":(0.03,0.42,0.45,0.38),"queue":(0.52,0.42,0.45,0.22),"details":(0.52,0.67,0.45,0.13),"actions":(0.03,0.83,0.94,0.13)},
                "standard": {"catalog":(0.02,0.03,0.22,0.94),"world":(0.27,0.03,0.49,0.69),"queue":(0.79,0.03,0.19,0.33),"details":(0.79,0.39,0.19,0.33),"actions":(0.27,0.76,0.71,0.21)},
                "wide": {"catalog":(0.018,0.03,0.19,0.94),"world":(0.235,0.03,0.55,0.70),"queue":(0.81,0.03,0.172,0.34),"details":(0.81,0.40,0.172,0.33),"actions":(0.235,0.77,0.747,0.20)},
            }, tags=["game","rts","build","production"], quality=rts_quality,
        ),
        "game.rts.tech": screen(
            "game.rts.tech", "RTS research and technology", "game.rts", "game.rts.command",
            "show prerequisites, opportunity cost and unlocked consequences across a large research graph",
            {
                "compact": {"header":(0.03,0.03,0.94,0.08),"tree":(0.03,0.14,0.94,0.53),"details":(0.03,0.70,0.62,0.24),"actions":(0.68,0.70,0.29,0.24)},
                "standard": {"header":(0.025,0.03,0.95,0.08),"tree":(0.025,0.14,0.70,0.82),"details":(0.76,0.14,0.215,0.55),"actions":(0.76,0.72,0.215,0.24)},
                "wide": {"header":(0.02,0.03,0.96,0.075),"tree":(0.02,0.14,0.73,0.82),"details":(0.78,0.14,0.20,0.55),"actions":(0.78,0.72,0.20,0.24)},
            }, tags=["game","rts","technology","research"], quality=rts_quality,
        ),
        "game.rts.diplomacy": screen(
            "game.rts.diplomacy", "RTS diplomacy and faction relations", "game.rts", "game.rts.command",
            "make relationships, proposals, obligations and consequences explicit before a strategic agreement changes state",
            {
                "compact": {"factions":(0.03,0.03,0.94,0.18),"relations":(0.03,0.24,0.94,0.30),"proposal":(0.03,0.57,0.58,0.36),"consequence":(0.64,0.57,0.33,0.22),"actions":(0.64,0.82,0.33,0.11)},
                "standard": {"factions":(0.025,0.03,0.19,0.94),"relations":(0.24,0.03,0.35,0.94),"proposal":(0.615,0.03,0.36,0.55),"consequence":(0.615,0.61,0.36,0.19),"actions":(0.615,0.83,0.36,0.14)},
                "wide": {"factions":(0.02,0.03,0.17,0.94),"relations":(0.215,0.03,0.38,0.94),"proposal":(0.62,0.03,0.36,0.55),"consequence":(0.62,0.61,0.36,0.19),"actions":(0.62,0.83,0.36,0.14)},
            }, tags=["game","rts","diplomacy","factions"], quality=rts_quality,
        ),
        "game.rts.pause": screen(
            "game.rts.pause", "RTS pause and strategic overview", "game.rts", "game.rts.command",
            "preserve world position and strategic context while exposing pause, save, settings and exit consequences",
            {
                "compact": {"context":(0,0,1,1),"overview":(0.08,0.09,0.84,0.25),"menu":(0.18,0.38,0.64,0.50)},
                "standard": {"context":(0,0,1,1),"overview":(0.18,0.08,0.64,0.22),"menu":(0.30,0.35,0.40,0.53)},
                "wide": {"context":(0,0,1,1),"overview":(0.22,0.08,0.56,0.22),"menu":(0.34,0.35,0.32,0.53)},
            }, tags=["game","rts","pause","overview"], quality=rts_quality,
        ),
        "game.rts.results": screen(
            "game.rts.results", "RTS campaign / battle outcome", "game.rts", "game.rts.command",
            "explain world-state consequences, losses, gains and next strategic choices rather than only a win/lose banner",
            {
                "compact": {"outcome":(0.04,0.04,0.92,0.14),"world-change":(0.04,0.21,0.92,0.25),"forces":(0.04,0.49,0.44,0.30),"economy":(0.52,0.49,0.44,0.30),"actions":(0.04,0.83,0.92,0.12)},
                "standard": {"outcome":(0.04,0.04,0.92,0.13),"world-change":(0.04,0.21,0.40,0.55),"forces":(0.47,0.21,0.23,0.55),"economy":(0.73,0.21,0.23,0.55),"actions":(0.47,0.80,0.49,0.12)},
                "wide": {"outcome":(0.05,0.04,0.90,0.12),"world-change":(0.05,0.21,0.43,0.55),"forces":(0.51,0.21,0.21,0.55),"economy":(0.75,0.21,0.20,0.55),"actions":(0.51,0.80,0.44,0.12)},
            }, tags=["game","rts","results","world-state"], quality=rts_quality,
        ),
    }

    all_new_screens = {}
    all_new_screens.update(racing_screens)
    all_new_screens.update(coop_screens)
    all_new_screens.update(rts_screens)
    _merge_unique(screens, all_new_screens, "screen")

    new_products = {
        "game.racing.full": {
            "schema": namespace["PRODUCT_SCHEMA"], "id": "game.racing.full", "version": 1,
            "name": "Full professional racing product", "kind": "product", "domain": "game.racing",
            "tags": ["game","racing","product","complete"], "origin": origin(), "style": "racing.performance",
            "intent": "a complete professional racing presentation shell from home and setup through race, recovery, replay and progression",
            "screens": [
                "game.racing.home", "game.racing.lobby", "game.racing.event-select", "game.racing.vehicle-select",
                "game.racing.garage", "game.racing.tuning", "game.racing.livery", "game.racing.pre-race",
                "game.racing.loading", "game.racing.countdown", "game.racing.hud.performance", "game.racing.hud.split",
                "game.racing.pause", "game.racing.recovery", "game.racing.results", "game.racing.replay",
                "game.racing.season", "game.racing.settings", "game.racing.accessibility",
            ],
            "flow": [
                ["game.racing.home","game.racing.lobby","play-together"],
                ["game.racing.home","game.racing.season","open-season"],
                ["game.racing.home","game.racing.settings","open-settings"],
                ["game.racing.settings","game.racing.accessibility","open-accessibility"],
                ["game.racing.accessibility","game.racing.settings","return-settings"],
                ["game.racing.lobby","game.racing.event-select","choose-event"],
                ["game.racing.event-select","game.racing.vehicle-select","choose-vehicle"],
                ["game.racing.vehicle-select","game.racing.garage","inspect-garage"],
                ["game.racing.garage","game.racing.tuning","tune"],
                ["game.racing.garage","game.racing.livery","customize"],
                ["game.racing.tuning","game.racing.pre-race","confirm-setup"],
                ["game.racing.livery","game.racing.pre-race","confirm-appearance"],
                ["game.racing.pre-race","game.racing.loading","launch"],
                ["game.racing.loading","game.racing.countdown","ready"],
                ["game.racing.countdown","game.racing.hud.performance","start-race"],
                ["game.racing.hud.performance","game.racing.pause","pause"],
                ["game.racing.pause","game.racing.hud.performance","resume"],
                ["game.racing.hud.performance","game.racing.recovery","connection-loss"],
                ["game.racing.recovery","game.racing.hud.performance","recovered"],
                ["game.racing.hud.performance","game.racing.results","finish"],
                ["game.racing.hud.split","game.racing.results","finish-local"],
                ["game.racing.results","game.racing.replay","watch-replay"],
                ["game.racing.replay","game.racing.results","return-results"],
                ["game.racing.results","game.racing.season","continue-season"],
                ["game.racing.results","game.racing.lobby","race-again"],
            ],
            "quality": [
                "all shell screens inherit one coherent racing language before game-specific art direction mutates it",
                "driving screens reduce chrome compared with setup screens",
                "loading, network and recovery states tell the truth about what is observed",
                "split-screen preserves seat ownership and readable essential state",
                "settings and accessibility are part of the product foundation rather than post-launch extras",
            ],
        },
        "game.coop.action": {
            "schema": namespace["PRODUCT_SCHEMA"], "id": "game.coop.action", "version": 1,
            "name": "Co-op action game product", "kind": "product", "domain": "game.coop",
            "tags": ["game","coop","product","action"], "origin": origin(), "style": "game.coop.tactical",
            "intent": "a reusable co-op game presentation shell with equal seat clarity from party formation through mission results",
            "screens": ["game.coop.home","game.coop.lobby","game.coop.loadout","game.coop.hud","game.coop.pause","game.coop.results","game.coop.settings"],
            "flow": [
                ["game.coop.home","game.coop.lobby","play"],
                ["game.coop.lobby","game.coop.loadout","prepare"],
                ["game.coop.loadout","game.coop.hud","launch"],
                ["game.coop.hud","game.coop.pause","pause"],
                ["game.coop.pause","game.coop.hud","resume"],
                ["game.coop.pause","game.coop.settings","settings"],
                ["game.coop.settings","game.coop.pause","return"],
                ["game.coop.hud","game.coop.results","complete"],
                ["game.coop.results","game.coop.lobby","continue"],
            ],
            "quality": ["human and machine seats share the same player-facing state language","party ownership and readiness remain explicit","team outcome stays distinct from individual contribution"],
        },
        "game.rts.command": {
            "schema": namespace["PRODUCT_SCHEMA"], "id": "game.rts.command", "version": 1,
            "name": "Persistent RTS command product", "kind": "product", "domain": "game.rts",
            "tags": ["game","rts","product","strategy"], "origin": origin(), "style": "game.rts.command",
            "intent": "a persistent-world RTS presentation foundation that preserves macro context across command, production and diplomacy surfaces",
            "screens": ["game.rts.lobby","game.rts.world","game.rts.hud","game.rts.build","game.rts.tech","game.rts.diplomacy","game.rts.pause","game.rts.results"],
            "flow": [
                ["game.rts.lobby","game.rts.world","enter-world"],
                ["game.rts.world","game.rts.hud","command-region"],
                ["game.rts.hud","game.rts.build","open-production"],
                ["game.rts.build","game.rts.hud","return-command"],
                ["game.rts.hud","game.rts.tech","research"],
                ["game.rts.tech","game.rts.hud","return-command"],
                ["game.rts.world","game.rts.diplomacy","diplomacy"],
                ["game.rts.diplomacy","game.rts.world","return-world"],
                ["game.rts.hud","game.rts.pause","pause"],
                ["game.rts.pause","game.rts.hud","resume"],
                ["game.rts.hud","game.rts.results","resolve-battle"],
                ["game.rts.results","game.rts.world","continue-world"],
            ],
            "quality": ["persistent world state remains the referent across screens","command surfaces preserve spatial context","strategic consequences precede irreversible choices"],
        },
    }
    _merge_unique(products, new_products, "product")

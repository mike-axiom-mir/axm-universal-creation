from __future__ import annotations

import hashlib
import json
import math
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .design_browser import DesignBrowserError, capture_local_browser
from .design_fabric import DESIGN_PLAN_SCHEMA
from .game_pose_runtime import load_game_pose_glb
from .project import ProjectError, validate_project

SELF_TEST_SCHEMA = "axm.evolution-aftertouch-self-test/v0.1"
MEDIA_OBSERVER_SCHEMA = "axm.aftertouch-media-observation/v0.1"
GLB_KINDS = {"3d", "3d-asset", "glb", "game-asset", "animated-3d", "animated-3d-asset"}
GAME_KINDS = {"game", "browser-game", "playable-game", "offline-browser-game"}
BROWSERS = ("chromium", "chromium-browser", "google-chrome", "google-chrome-stable", "chrome")


class AftertouchMediaObserverError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _artifact(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise AftertouchMediaObserverError("candidate must be an object")
    value = raw.get("artifact", raw)
    if not isinstance(value, dict):
        raise AftertouchMediaObserverError("candidate artifact must be an object")
    return value


def _path(root: Path, raw: Any, label: str = "artifact.path") -> Path:
    if not isinstance(raw, (str, os.PathLike)) or not str(raw).strip():
        raise AftertouchMediaObserverError(f"{label} must be non-empty path text")
    value = Path(raw).expanduser()
    return (value if value.is_absolute() else Path(root) / value).resolve()


def _allowed(root: Path, target: Path) -> bool:
    try:
        rel = target.resolve().relative_to(Path(root).resolve())
    except ValueError:
        return True
    return bool(rel.parts) and rel.parts[0] in {"creations", ".axm-build"}


def _row(lane: str, status: str, evidence: str, source: str) -> dict[str, str]:
    return {"lane": lane, "status": status, "evidence": evidence, "source": source}


def _overall(rows: list[dict[str, str]]) -> str:
    states = {row["status"] for row in rows}
    return "FAIL" if "FAIL" in states else "HOLD" if states & {"HOLD", "NOT_TESTED"} else "PASS"


def _finish(adapter: str, rows: list[dict[str, str]], **extra: Any) -> dict[str, Any]:
    result = {
        "schema": SELF_TEST_SCHEMA,
        "media_observer_schema": MEDIA_OBSERVER_SCHEMA,
        "adapter": adapter,
        "status": _overall(rows),
        "verification": rows,
        "perfect_claimed": False,
        **extra,
    }
    result["observation_digest"] = _digest(result)
    return result


def _hold(adapter: str, lane: str, evidence: str, **extra: Any) -> dict[str, Any]:
    return _finish(adapter, [_row(lane, "HOLD", evidence, adapter)], **extra)


def _glb_target(root: Path, artifact: dict[str, Any]) -> tuple[Path | None, dict[str, Any] | None]:
    raw = artifact.get("path", artifact.get("glb_path"))
    if raw is None:
        return None, _hold("uc-glb-pose-observer", "structural", "3D self-test requires path or glb_path")
    target = _path(root, raw)
    if not _allowed(root, target):
        return None, _hold("uc-glb-pose-observer", "structural", "3D self-test refuses the live UC machine body")
    if target.is_file():
        return (target, None) if target.suffix.casefold() == ".glb" else (None, _hold("uc-glb-pose-observer", "structural", "3D self-test requires a .glb file"))
    if not target.is_dir():
        return None, _hold("uc-glb-pose-observer", "structural", "3D self-test path does not exist")
    asset = artifact.get("asset")
    if asset is not None:
        rel = Path(str(asset))
        selected = (target / rel).resolve()
        try:
            selected.relative_to(target)
        except ValueError:
            return None, _hold("uc-glb-pose-observer", "structural", "artifact.asset escaped the candidate directory")
        return (selected, None) if selected.is_file() and selected.suffix.casefold() == ".glb" else (None, _hold("uc-glb-pose-observer", "structural", "artifact.asset did not resolve to a .glb file"))
    glbs = sorted(p for p in target.rglob("*.glb") if ".git" not in p.parts and "node_modules" not in p.parts)
    if len(glbs) == 1:
        return glbs[0].resolve(), None
    if not glbs:
        return None, _hold("uc-glb-pose-observer", "structural", "candidate directory contains no .glb asset")
    return None, _hold("uc-glb-pose-observer", "structural", f"candidate contains {len(glbs)} GLBs; select one with artifact.asset", candidates=[str(p.relative_to(target)) for p in glbs[:32]])


def _bounds(sample: dict[str, Any]) -> dict[str, Any] | None:
    points = [p for mesh in sample.get("meshes", []) if isinstance(mesh, dict) for p in mesh.get("positions", []) if isinstance(p, list) and len(p) == 3]
    if not points:
        return None
    lo = [min(float(p[i]) for p in points) for i in range(3)]
    hi = [max(float(p[i]) for p in points) for i in range(3)]
    return {"min": lo, "max": hi, "size": [hi[i] - lo[i] for i in range(3)]}


def observe_glb_candidate(root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    target, boundary = _glb_target(root, artifact)
    if boundary is not None:
        return boundary
    assert target is not None
    try:
        asset = load_game_pose_glb(target)
        description = asset.describe()
        static = asset.sample(vertices=True)
    except (OSError, ValueError) as exc:
        return _finish("uc-glb-pose-observer", [_row("structural", "FAIL", str(exc), "builtin:game_pose_runtime")], path=str(target))

    rows = [_row("structural", "PASS", f"parsed GLB sha256={description['source_sha256']} nodes={len(description['nodes'])} primitives={description['primitives']} vertices={description['vertices']}", "builtin:game_pose_runtime")]
    static_bounds = _bounds(static)
    clips = description.get("clips", []) if isinstance(description.get("clips"), list) else []
    sampled: list[dict[str, Any]] = []
    max_displacement = 0.0
    try:
        for clip in clips[:16]:
            name = clip["name"]
            duration = float(clip["duration_s"])
            poses = []
            for label, time_s in (("start", 0.0), ("mid", duration / 2), ("end", duration)):
                pose = asset.sample(name, time_s, loop=False, vertices=(label == "mid"))
                poses.append((label, pose))
            start_world = poses[0][1]["world_matrices"]
            for _, pose in poses[1:]:
                for a, b in zip(start_world, pose["world_matrices"]):
                    da = [float(a[3]), float(a[7]), float(a[11])]
                    db = [float(b[3]), float(b[7]), float(b[11])]
                    max_displacement = max(max_displacement, math.dist(da, db))
            sampled.append({"clip": name, "duration_s": duration, "mid_bounds": _bounds(poses[1][1])})
    except (ValueError, OverflowError) as exc:
        rows.append(_row("functional", "FAIL", f"pose sampling failed: {exc}", "builtin:game_pose_runtime"))
    else:
        if clips:
            rows.append(_row("functional", "PASS", f"sampled {len(sampled)} animation clip(s); max sampled node displacement={max_displacement:.6g}", "builtin:game_pose_runtime"))
        elif artifact.get("animation_expected") is True:
            rows.append(_row("functional", "FAIL", "animation_expected=true but the GLB declares no supported animation clips", "builtin:game_pose_runtime"))
        else:
            rows.append(_row("functional", "HOLD", "static GLB parsed; no supported animation clip was available to exercise", "builtin:game_pose_runtime"))

    node_names = {row["name"]: row["index"] for row in description.get("nodes", []) if isinstance(row, dict)}
    required = artifact.get("required_sockets", [])
    if required is None:
        required = []
    if not isinstance(required, list) or any(not isinstance(x, str) or not x.strip() for x in required):
        raise AftertouchMediaObserverError("artifact.required_sockets must be a list of non-empty node names")
    missing = [name for name in required if name not in node_names]
    socket_positions = {name: asset.point(static, node_names[name]) for name in required if name in node_names}
    rows.append(_row("context", "FAIL" if missing else "PASS", f"required sockets missing={missing}; observed positions={socket_positions}", "builtin:game_pose_runtime"))

    finite = static_bounds is not None and all(math.isfinite(v) for values in (static_bounds["min"], static_bounds["max"], static_bounds["size"]) for v in values)
    rows.append(_row("adversarial", "PASS" if finite else "HOLD", f"static skinned geometry bounds={static_bounds}", "builtin:game_pose_runtime"))
    for lane in ("visual", "experience", "polish"):
        rows.append(_row(lane, "NOT_TESTED", "GLB pose/geometry execution does not render or judge this lane", "builtin:game_pose_runtime"))
    return _finish(
        "uc-glb-pose-observer", rows, path=str(target), description=description, static_bounds=static_bounds,
        clip_samples=sampled, max_sampled_node_displacement=max_displacement, socket_positions=socket_positions,
        truth_boundary="supported GLB parsing/pose/skin/socket facts were executed; shading, engine playback, collision, readability, aesthetics and human experience were not inferred",
    )


def _browser(artifact: dict[str, Any]) -> str | None:
    explicit = artifact.get("browser_executable")
    if explicit is not None:
        return str(explicit)
    discover = artifact.get("auto_discover_browser", False)
    if not isinstance(discover, bool):
        raise AftertouchMediaObserverError("artifact.auto_discover_browser must be boolean")
    if not discover:
        return None
    return next((found for name in BROWSERS if (found := shutil.which(name))), None)


def _game_recipes(entrypoint: Path, allow_activation: bool) -> list[dict[str, Any]]:
    text = entrypoint.read_text(encoding="utf-8", errors="replace")
    ids = {name for name in ("sessionButton", "fireButton", "targetButton", "reloadButton", "resetButton") if f'id="{name}"' in text or f"id='{name}'" in text}
    if not ids:
        return []
    if not allow_activation:
        return [{"id": "focus-controls", "steps": [{"action": "focus", "selector": f"#{name}"} for name in sorted(ids)]}]
    primary_order = [name for name in ("sessionButton", "targetButton", "fireButton", "reloadButton") if name in ids]
    recipes = [{"id": "primary-game-controls", "steps": [{"action": "activate", "selector": f"#{name}"} for name in primary_order]}] if primary_order else []
    if "resetButton" in ids:
        steps = ([{"action": "activate", "selector": "#sessionButton"}] if "sessionButton" in ids else []) + [{"action": "activate", "selector": "#resetButton"}]
        recipes.append({"id": "reset-recovery", "steps": steps})
    return recipes


def _plan(viewport: dict[str, Any], reduced_motion: bool) -> dict[str, Any]:
    body = {
        "schema": DESIGN_PLAN_SCHEMA, "truth_status": "AFTERTOUCH_BROWSER_OBSERVATION_PLAN", "goal": "observe actual local playable-game runtime",
        "genome": {"id": "aftertouch-game-observer", "version": "0.1", "digest": "sha256:" + "0" * 64},
        "selected_components": [], "role_coverage": {}, "missing_roles": [], "missing_components": [], "viewports": ["game"], "layout": {"breakpoints": [], "principles": []},
        "token_bindings": {"colors": [], "spacing": [], "radii": [], "typography": [], "custom": []}, "motion": {"durations": [], "easings": [], "reduced_motion_strategy": "unknown"},
        "materials": {"signals": [], "principles": []}, "contrast_pairs": [],
        "quality_gates": {"minimum_text_contrast": 4.5, "focus_visible_required": False, "reduced_motion_required": reduced_motion, "responsive_required": False, "policy_origin": "AFTERTOUCH_OBSERVATION_ONLY"},
        "composition_rule": "observation only", "limitations": ["this plan exists only to bind exact browser evidence"],
    }
    body["plan_digest"] = _digest(body)
    return body


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def observe_game_candidate(root: Path, artifact: dict[str, Any]) -> dict[str, Any]:
    if "path" not in artifact:
        return _hold("uc-playable-game-observer", "structural", "playable-game self-test requires artifact.path")
    target = _path(root, artifact["path"])
    if not _allowed(root, target):
        return _hold("uc-playable-game-observer", "structural", "playable-game self-test refuses the live UC machine body")
    checks = artifact.get("checks") if isinstance(artifact.get("checks"), list) else None
    try:
        report = validate_project(target, project_type=str(artifact.get("project_type", "static-web")), checks=checks)
    except ProjectError as exc:
        return _finish("uc-playable-game-observer", [_row("structural", "FAIL", str(exc), "builtin:verify_project")], path=str(target))
    project_passed = report.get("passed") is True
    rows = [_row("structural", "PASS" if project_passed else "FAIL", f"project validator passed={project_passed}", "builtin:verify_project")]
    entrypoint = target / str(artifact.get("entrypoint", "index.html")) if target.is_dir() else target
    browser = _browser(artifact)
    if not entrypoint.is_file():
        rows += [_row("functional", "FAIL", f"browser entrypoint missing: {entrypoint}", "builtin:design_browser")]
        return _finish("uc-playable-game-observer", rows, report=report, entrypoint=str(entrypoint))
    if browser is None:
        for lane in ("functional", "visual", "experience", "context", "adversarial", "polish"):
            rows.append(_row(lane, "NOT_TESTED", "local Chromium-compatible executor was not supplied; PATH discovery is opt-in", "builtin:design_browser"))
        return _finish("uc-playable-game-observer", rows, report=report, entrypoint=str(entrypoint), next_gate="supply browser_executable or set auto_discover_browser=true")

    allow_activation = artifact.get("allow_synthetic_activation", False)
    if not isinstance(allow_activation, bool):
        raise AftertouchMediaObserverError("artifact.allow_synthetic_activation must be boolean")
    recipes = artifact.get("interaction_recipes")
    if recipes is None:
        recipes = _game_recipes(entrypoint, allow_activation)
    viewport = artifact.get("viewport", {"width": 1280, "height": 720, "device_pixel_ratio": 1})
    if not isinstance(viewport, dict) or not isinstance(viewport.get("width"), int) or not isinstance(viewport.get("height"), int):
        raise AftertouchMediaObserverError("artifact.viewport must provide integer width and height")
    viewport = {"width": viewport["width"], "height": viewport["height"], "device_pixel_ratio": viewport.get("device_pixel_ratio", 1)}
    timeout = artifact.get("timeout_seconds", 20)
    if isinstance(timeout, bool) or not isinstance(timeout, int) or not 1 <= timeout <= 120:
        raise AftertouchMediaObserverError("artifact.timeout_seconds must be an integer from 1 to 120")
    reduced = artifact.get("reduced_motion_probe", False)
    if not isinstance(reduced, bool):
        raise AftertouchMediaObserverError("artifact.reduced_motion_probe must be boolean")

    runtime = interaction = None
    screenshot = False
    measurements: dict[str, Any] = {}
    artifacts: list[dict[str, Any]] = []
    try:
        with tempfile.TemporaryDirectory(prefix="axm-aftertouch-browser-") as td:
            output = Path(td) / "capture"
            captured = capture_local_browser(
                root=root, plan_raw=_plan(viewport, reduced), target_value=str(entrypoint), output_value=str(output), browser_value=browser,
                viewport_sizes_raw={"game": viewport}, timeout_seconds=timeout, interaction_recipes_raw=recipes, allow_synthetic_activation=allow_activation,
            )
            runtime = _read_json(output / "game.runtime.json")
            interaction = _read_json(output / "game.interaction.json")
            screenshot = (output / "game.png").is_file() and (output / "game.png").stat().st_size > 0
            captures = captured.get("observation", {}).get("captures", [])
            if isinstance(captures, list) and captures and isinstance(captures[0], dict):
                measurements = captures[0].get("measurements", {}) if isinstance(captures[0].get("measurements"), dict) else {}
                artifacts = captures[0].get("artifacts", []) if isinstance(captures[0].get("artifacts"), list) else []
    except DesignBrowserError as exc:
        rows.append(_row("functional", "HOLD" if exc.details.get("status") == "HOLD_BROWSER_EXECUTOR_UNAVAILABLE" else "FAIL", str(exc), "builtin:design_browser"))
        for lane in ("visual", "experience", "context", "adversarial", "polish"):
            rows.append(_row(lane, "NOT_TESTED", "browser execution did not produce complete evidence", "builtin:design_browser"))
        return _finish("uc-playable-game-observer", rows, report=report, entrypoint=str(entrypoint), browser_executable=str(browser))

    runtime_errors = runtime.get("runtime_error_count") if isinstance(runtime, dict) else None
    rows.append(_row("functional", "PASS" if runtime_errors == 0 else "FAIL" if isinstance(runtime_errors, int) else "HOLD", f"runtime_error_count={runtime_errors!r}", "builtin:design_browser"))
    rows.append(_row("visual", "HOLD" if screenshot else "FAIL", "real screenshot bytes captured; screenshot presence is observation, not aesthetic proof" if screenshot else "non-empty screenshot not observed", "builtin:design_browser"))
    interaction_errors = interaction.get("interaction_error_count") if isinstance(interaction, dict) else None
    if not recipes:
        exp_status, exp_evidence = "NOT_TESTED", "no explicit interaction recipes were available"
    elif not isinstance(interaction_errors, int):
        exp_status, exp_evidence = "HOLD", "interaction recipes requested but probe result was not observed"
    elif interaction_errors:
        exp_status, exp_evidence = "FAIL", f"interaction probe recorded {interaction_errors} error(s)"
    elif allow_activation:
        exp_status, exp_evidence = "PASS", f"bounded activation-authorized recipes completed={interaction.get('completed_recipe_count', 0)} with zero errors"
    else:
        exp_status, exp_evidence = "HOLD", "focus-only probe completed; gameplay activation was not authorized"
    rows.append(_row("experience", exp_status, exp_evidence, "builtin:design_browser"))
    overflow = measurements.get("horizontal_overflow")
    rows.append(_row("context", "PASS" if overflow is False else "HOLD", f"horizontal_overflow={overflow!r}", "builtin:design_browser"))
    recovery = next((r for r in interaction.get("recipes", []) if isinstance(r, dict) and r.get("id") == "reset-recovery"), None) if isinstance(interaction, dict) else None
    rows.append(_row("adversarial", "PASS" if isinstance(recovery, dict) and recovery.get("status") == "PASS" else "FAIL" if isinstance(recovery, dict) else "NOT_TESTED", f"reset-recovery={recovery.get('status') if isinstance(recovery, dict) else 'not observed'}", "builtin:design_browser"))
    rows.append(_row("polish", "NOT_TESTED", "runtime, interaction and screenshot evidence do not prove aesthetic polish", "builtin:design_browser"))
    return _finish(
        "uc-playable-game-observer", rows, report=report, entrypoint=str(entrypoint), browser_executable=str(browser),
        browser_evidence={"artifacts": artifacts, "measurements": measurements, "runtime_probe": runtime, "interaction_probe": interaction},
        truth_boundary="browser PASS rows mean exact local runtime/interaction observations on a temporary offline copy; screenshot presence is not aesthetic proof and synthetic activation is only used when explicitly authorized",
    )


def media_self_test_candidate(root: Path, raw_candidate: Any) -> dict[str, Any] | None:
    artifact = _artifact(raw_candidate)
    kind = str(artifact.get("kind", "generic")).strip().casefold()
    if kind in GLB_KINDS:
        return observe_glb_candidate(Path(root), artifact)
    if kind in GAME_KINDS:
        return observe_game_candidate(Path(root), artifact)
    return None


def media_observer_summary() -> dict[str, Any]:
    return {
        "schema": MEDIA_OBSERVER_SCHEMA,
        "3d_kinds": sorted(GLB_KINDS), "game_kinds": sorted(GAME_KINDS),
        "3d_observer": "existing pure-Python GLB pose/skin runtime with bounded clip/socket/geometry measurements",
        "game_observer": "existing offline headless-browser capture with runtime probe, real screenshot bytes and optional explicit bounded interaction recipes",
        "automatic_visual_quality_claim": False, "synthetic_game_activation_default": False,
        "unsupported_media_falls_back_to_existing_aftertouch_not_tested_boundary": True,
    }

from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from .design_fabric import DESIGN_PLAN_SCHEMA
from .design_interaction import (
    INTERACTION_PROBE_SCHEMA,
    DesignInteractionError,
    instrument_interaction_html,
    interaction_measurements,
    interaction_probe_artifact,
    normalize_interaction_recipes,
    parse_interaction_probe,
)
from .design_observer import record_render_observation
from .design_runtime_probe import (
    RUNTIME_PROBE_SCHEMA,
    instrument_local_html,
    parse_runtime_probe,
    runtime_measurements,
    runtime_probe_artifact,
)

BROWSER_CAPTURE_SCHEMA = "axm.design-browser-capture-receipt/v0.3"
DEFAULT_TIMEOUT_SECONDS = 20
MAX_TIMEOUT_SECONDS = 120
MAX_VIEWPORTS = 16


class DesignBrowserError(RuntimeError):
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
        raise DesignBrowserError(f"{label} must be non-empty text")
    result = value.strip()
    if len(result) > maximum:
        raise DesignBrowserError(f"{label} exceeds its {maximum}-character bound")
    return result


def _integer(value: Any, label: str, minimum: int, maximum: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not minimum <= value <= maximum:
        raise DesignBrowserError(f"{label} must be an integer between {minimum} and {maximum}")
    return value


def _resolve_path(root: Path, requested: str) -> Path:
    path = Path(requested).expanduser()
    if not path.is_absolute():
        path = Path(root).resolve() / path
    return path.resolve()


def _is_machine_body_path(root: Path, target: Path) -> bool:
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
            raise DesignBrowserError(
                "browser executable is unavailable",
                {"browser_executable": requested, "status": "HOLD_BROWSER_EXECUTOR_UNAVAILABLE"},
            )
        resolved = Path(found).resolve()
    if not os.access(resolved, os.X_OK):
        raise DesignBrowserError("browser executable is not executable", {"path": str(resolved)})
    return resolved


def _target_html(root: Path, value: Any) -> Path:
    text = _text(value, "target", 1000)
    if "://" in text:
        raise DesignBrowserError(
            "browser capture v0.3 accepts local paths only; URL/network capture is unsupported",
            {"target": text},
        )
    target = _resolve_path(root, text)
    if target.is_dir():
        target = target / "index.html"
    if not target.is_file() or target.suffix.casefold() not in {".html", ".htm"}:
        raise DesignBrowserError("browser capture target must resolve to a local HTML file", {"target": str(target)})
    return target.resolve()


def _viewport_sizes(plan: dict[str, Any], raw: Any) -> list[dict[str, Any]]:
    required = plan.get("viewports")
    if not isinstance(required, list) or not required or len(required) > MAX_VIEWPORTS:
        raise DesignBrowserError("design plan must declare 1..16 viewport ids")
    if not isinstance(raw, dict) or set(raw) != set(required):
        raise DesignBrowserError(
            "viewport_sizes must define exactly every design-plan viewport",
            {"required": required, "supplied": sorted(raw) if isinstance(raw, dict) else None},
        )
    rows: list[dict[str, Any]] = []
    for viewport_id in required:
        size = raw[viewport_id]
        if (
            not isinstance(size, dict)
            or not {"width", "height"}.issubset(size)
            or set(size) - {"width", "height", "device_pixel_ratio"}
        ):
            raise DesignBrowserError(f"viewport_sizes.{viewport_id} is invalid")
        row: dict[str, Any] = {
            "id": str(viewport_id),
            "width": _integer(size["width"], f"viewport_sizes.{viewport_id}.width", 1, 100_000),
            "height": _integer(size["height"], f"viewport_sizes.{viewport_id}.height", 1, 100_000),
            "device_pixel_ratio": 1,
        }
        if "device_pixel_ratio" in size:
            ratio = size["device_pixel_ratio"]
            if (
                isinstance(ratio, bool)
                or not isinstance(ratio, (int, float))
                or not 0.1 <= float(ratio) <= 8
            ):
                raise DesignBrowserError(
                    f"viewport_sizes.{viewport_id}.device_pixel_ratio must be between 0.1 and 8"
                )
            row["device_pixel_ratio"] = float(ratio)
        rows.append(row)
    return rows


def _run_version(browser: Path, timeout_seconds: int) -> str:
    try:
        completed = subprocess.run(
            [str(browser), "--version"],
            check=False,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout_seconds,
        )
    except (OSError, subprocess.SubprocessError) as exc:
        raise DesignBrowserError(
            "browser version probe failed",
            {"path": str(browser), "reason": str(exc)},
        ) from exc
    text = (completed.stdout or completed.stderr or "unknown-version").strip()
    return text[:500] or "unknown-version"


def _offline_browser_command(
    browser: Path,
    viewport: dict[str, Any],
    screenshot: Path,
    target: Path,
    profile_dir: Path,
    *,
    reduced_motion: bool = False,
) -> list[str]:
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
        "--host-resolver-rules=MAP * 0.0.0.0,EXCLUDE localhost",
        "--virtual-time-budget=1200",
        f"--user-data-dir={profile_dir}",
        f"--window-size={viewport['width']},{viewport['height']}",
        f"--force-device-scale-factor={viewport['device_pixel_ratio']}",
        f"--screenshot={screenshot}",
        "--dump-dom",
    ]
    if reduced_motion:
        command.append("--force-prefers-reduced-motion=reduce")
    command.append(target.as_uri())
    return command


def _run_capture_command(
    browser: Path,
    viewport: dict[str, Any],
    screenshot: Path,
    target: Path,
    timeout: int,
    profile_dir: Path,
    *,
    reduced_motion: bool = False,
) -> subprocess.CompletedProcess[str]:
    profile_dir.mkdir(parents=True, exist_ok=False)
    command = _offline_browser_command(
        browser,
        viewport,
        screenshot,
        target,
        profile_dir,
        reduced_motion=reduced_motion,
    )
    try:
        try:
            completed = subprocess.run(
                command,
                cwd=target.parent,
                check=False,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=timeout,
            )
        except subprocess.TimeoutExpired as exc:
            raise DesignBrowserError(
                "browser capture timed out",
                {
                    "viewport": viewport["id"],
                    "timeout_seconds": timeout,
                    "reduced_motion": reduced_motion,
                },
            ) from exc
        except OSError as exc:
            raise DesignBrowserError(
                "browser capture could not start",
                {
                    "viewport": viewport["id"],
                    "reason": str(exc),
                    "reduced_motion": reduced_motion,
                },
            ) from exc
        if completed.returncode != 0:
            raise DesignBrowserError(
                "browser capture failed",
                {
                    "viewport": viewport["id"],
                    "returncode": completed.returncode,
                    "stderr": completed.stderr[-2000:],
                    "reduced_motion": reduced_motion,
                },
            )
        return completed
    finally:
        shutil.rmtree(profile_dir, ignore_errors=True)


def capture_local_browser(
    root: Path,
    plan_raw: Any,
    target_value: Any,
    output_value: Any,
    browser_value: Any,
    viewport_sizes_raw: Any,
    timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
    interaction_recipes_raw: Any = None,
    allow_synthetic_activation: Any = False,
) -> dict[str, Any]:
    if (
        not isinstance(plan_raw, dict)
        or plan_raw.get("schema") != DESIGN_PLAN_SCHEMA
        or not isinstance(plan_raw.get("plan_digest"), str)
    ):
        raise DesignBrowserError(
            "capture-browser requires an axm.design-plan/v0.1 plan with plan_digest"
        )
    plan = json.loads(json.dumps(plan_raw))
    target = _target_html(root, target_value)
    output = _resolve_path(root, _text(output_value, "path", 1000))
    if _is_machine_body_path(root, output):
        raise DesignBrowserError(
            "browser capture is an ordinary creation and cannot write into the live machine body"
        )
    if output.exists():
        raise DesignBrowserError(
            "browser capture target already exists; choose a new path rather than silently replacing evidence",
            {"path": str(output)},
        )

    try:
        interaction_recipes = normalize_interaction_recipes(
            interaction_recipes_raw,
            allow_synthetic_activation,
        )
    except DesignInteractionError as exc:
        raise DesignBrowserError(str(exc), getattr(exc, "details", {})) from exc

    browser = _resolve_browser(browser_value)
    timeout = _integer(timeout_seconds, "timeout_seconds", 1, MAX_TIMEOUT_SECONDS)
    viewports = _viewport_sizes(plan, viewport_sizes_raw)
    browser_version = _run_version(browser, timeout)
    target_bytes = target.read_bytes()
    reduced_required = bool(plan.get("quality_gates", {}).get("reduced_motion_required"))
    output.parent.mkdir(parents=True, exist_ok=True)

    staging_parent = output.parent
    with tempfile.TemporaryDirectory(prefix=".axm-design-browser-", dir=staging_parent) as temporary:
        staging = Path(temporary)
        runtime_instrumented = instrument_local_html(target)
        try:
            interaction_instrumented = instrument_interaction_html(
                runtime_instrumented["html"],
                interaction_recipes,
                allow_synthetic_activation,
            )
        except DesignInteractionError as exc:
            raise DesignBrowserError(str(exc), getattr(exc, "details", {})) from exc

        probe_source = staging / ".axm-runtime-interaction-probe.html"
        probe_source.write_text(interaction_instrumented["html"], encoding="utf-8")
        reduced_probe_source = staging / ".axm-runtime-reduced-probe.html"
        reduced_probe_source.write_text(runtime_instrumented["html"], encoding="utf-8")

        captures = []
        executions = []
        runtime_probe_coverage = []
        interaction_probe_coverage = []

        for viewport in viewports:
            viewport_id = viewport["id"]
            screenshot = staging / f"{viewport_id}.png"
            dom_path = staging / f"{viewport_id}.dom.html"
            completed = _run_capture_command(
                browser,
                viewport,
                screenshot,
                probe_source,
                timeout,
                staging / f".profile-{viewport_id}-normal",
            )
            if not screenshot.is_file() or screenshot.stat().st_size == 0:
                raise DesignBrowserError(
                    "browser reported success but produced no screenshot bytes",
                    {"viewport": viewport_id},
                )
            dom_text = completed.stdout
            if not dom_text.strip():
                raise DesignBrowserError(
                    "browser reported success but produced no DOM snapshot",
                    {"viewport": viewport_id},
                )
            dom_path.write_text(dom_text, encoding="utf-8")

            normal_probe = parse_runtime_probe(dom_text)
            interaction_probe = parse_interaction_probe(dom_text)
            reduced_probe = None
            if reduced_required and isinstance(normal_probe, dict):
                reduced_screenshot = staging / f".{viewport_id}.reduced.png"
                reduced = _run_capture_command(
                    browser,
                    viewport,
                    reduced_screenshot,
                    reduced_probe_source,
                    timeout,
                    staging / f".profile-{viewport_id}-reduced",
                    reduced_motion=True,
                )
                reduced_probe = parse_runtime_probe(reduced.stdout)
                if reduced_screenshot.exists():
                    reduced_screenshot.unlink()

            screenshot_bytes = screenshot.read_bytes()
            dom_bytes = dom_path.read_bytes()
            artifacts = [
                {
                    "kind": "screenshot",
                    "digest": _bytes_digest(screenshot_bytes),
                    "uri": f"{viewport_id}.png",
                    "mime_type": "image/png",
                    "bytes": len(screenshot_bytes),
                },
                {
                    "kind": "dom-snapshot",
                    "digest": _bytes_digest(dom_bytes),
                    "uri": f"{viewport_id}.dom.html",
                    "mime_type": "text/html",
                    "bytes": len(dom_bytes),
                },
            ]

            measurements = runtime_measurements(normal_probe, reduced_probe)
            runtime_probe_status = "HOLD_RUNTIME_PROBE_NOT_OBSERVED"
            if isinstance(normal_probe, dict):
                probe_bytes = runtime_probe_artifact(normal_probe)
                probe_path = staging / f"{viewport_id}.runtime.json"
                probe_path.write_bytes(probe_bytes)
                artifacts.append(
                    {
                        "kind": "other",
                        "digest": _bytes_digest(probe_bytes),
                        "uri": probe_path.name,
                        "mime_type": "application/vnd.axm.browser-runtime-probe+json",
                        "bytes": len(probe_bytes),
                    }
                )
                runtime_probe_status = "OBSERVED_BROWSER_RUNTIME_PROBE"

            interaction_probe_status = "NOT_REQUESTED"
            interaction_probe_filename = None
            if interaction_recipes:
                interaction_probe_status = "HOLD_EXPLICIT_INTERACTION_PROBE_NOT_OBSERVED"
                if isinstance(interaction_probe, dict):
                    interaction_bytes = interaction_probe_artifact(interaction_probe)
                    interaction_path = staging / f"{viewport_id}.interaction.json"
                    interaction_path.write_bytes(interaction_bytes)
                    interaction_probe_filename = interaction_path.name
                    artifacts.append(
                        {
                            "kind": "interaction-log",
                            "digest": _bytes_digest(interaction_bytes),
                            "uri": interaction_path.name,
                            "mime_type": "application/vnd.axm.browser-interaction-probe+json",
                            "bytes": len(interaction_bytes),
                        }
                    )
                    measurements.update(interaction_measurements(interaction_probe))
                    interaction_probe_status = "OBSERVED_EXPLICIT_INTERACTION_PROBE"

            captures.append({
                "viewport": viewport,
                "artifacts": artifacts,
                "measurements": measurements,
                "assessments": [],
            })
            runtime_probe_coverage.append({
                "viewport": viewport_id,
                "status": runtime_probe_status,
                "measurements": sorted(runtime_measurements(normal_probe, reduced_probe)),
                "reduced_motion_probe_observed": isinstance(reduced_probe, dict),
            })
            interaction_probe_coverage.append({
                "viewport": viewport_id,
                "status": interaction_probe_status,
                "measurements": sorted(interaction_measurements(interaction_probe)),
                "artifact": interaction_probe_filename,
            })
            executions.append({
                "viewport": viewport_id,
                "returncode": completed.returncode,
                "network_policy": "offline-host-resolution-block",
                "profile_policy": "temporary-isolated-browser-profile",
                "screenshot": f"{viewport_id}.png",
                "dom": f"{viewport_id}.dom.html",
                "runtime_probe": f"{viewport_id}.runtime.json" if isinstance(normal_probe, dict) else None,
                "interaction_probe": interaction_probe_filename,
            })

        observation = record_render_observation(
            plan["plan_digest"],
            {
                "kind": "browser-tool",
                "id": "chromium-headless-cli",
                "version": browser_version,
                "basis": (
                    "caller-selected local Chromium-compatible executable; screenshot/DOM bytes plus "
                    "optional runtime and caller-authorized bounded interaction probes on temporary copies"
                ),
            },
            captures,
        )
        observation["truth_status"] = "OBSERVED_LOCAL_BROWSER_ARTIFACT_RUNTIME_AND_BOUNDED_INTERACTION_BYTES"
        observation["evidence_boundary"]["artifact_bytes_fetched_or_verified"] = True
        observation["evidence_boundary"]["browser_or_screen_control_claimed"] = True
        for capture in observation["captures"]:
            for artifact in capture["artifacts"]:
                artifact["bytes_verified_or_fetched_by_design_fabric"] = True
        observation["observation_digest"] = _digest(
            {key: value for key, value in observation.items() if key != "observation_digest"}
        )

        receipt = {
            "schema": BROWSER_CAPTURE_SCHEMA,
            "truth_status": "LOCAL_HEADLESS_BROWSER_CAPTURE_WITH_OPTIONAL_RUNTIME_AND_INTERACTION_PROBES_COMPLETED",
            "plan_digest": plan["plan_digest"],
            "target": {
                "path": str(target),
                "html_sha256": _bytes_digest(target_bytes),
                "network_policy": "external host resolution blocked",
            },
            "browser": {
                "path": str(browser),
                "version": browser_version,
                "family_contract": "Chromium-compatible headless CLI",
                "profile_policy": "fresh temporary user-data directory for every normal/reduced viewport run",
            },
            "runtime_probe": {
                "schema": RUNTIME_PROBE_SCHEMA,
                "instrumentation": runtime_instrumented["method"],
                "base_uri": runtime_instrumented["base_uri"],
                "coverage": runtime_probe_coverage,
                "perceptual_assessments_generated": False,
                "accessibility_tree_claimed": False,
                "autonomous_interaction_crawl_executed": False,
            },
            "interaction_probe": {
                "schema": INTERACTION_PROBE_SCHEMA,
                "requested": bool(interaction_recipes),
                "recipe_count": len(interaction_recipes),
                "recipes": interaction_recipes,
                "activation_authorized": bool(allow_synthetic_activation),
                "coverage": interaction_probe_coverage,
                "real_keyboard_tab_traversal_claimed": False,
                "trusted_user_input_claimed": False,
                "form_submission_allowed": False,
                "arbitrary_link_navigation_allowed": False,
            },
            "executions": executions,
            "observation": observation,
            "limitations": [
                "runtime probing executes injected nonvisual code in a temporary HTML copy and may HOLD when page/runtime policy prevents a marker from appearing",
                "every browser run receives a fresh temporary user-data directory so cookies/localStorage/session effects are not intentionally shared with the caller browser profile",
                "focus evidence is programmatic focus plus computed outline/shadow evidence, not complete keyboard-navigation or tab-order proof",
                "explicit interaction recipes use programmatic focus and optional synthetic HTMLElement.click, not trusted user input events",
                "synthetic activation is disabled by default and, when explicitly authorized, is limited to visible button-like controls on the temporary local copy",
                "form submission is blocked by the interaction probe and arbitrary link navigation is outside the activation contract",
                "text contrast is measured only for observed opaque computed text on an opaque ancestor background; gradients/transparency remain unproven",
                "accessibility issue counts are bounded DOM heuristics, not a browser accessibility-tree audit",
                "reduced-motion PASS is emitted only when no motion is observed or a duration reduction is directly observed under prefers-reduced-motion",
                "interaction PASS means only that the exact supplied recipes completed without recorded probe errors for the exact selectors and viewport; it is not a usability claim",
                "local page JavaScript may execute inside the supplied browser; external host resolution is blocked by the command contract but this is not claimed as a complete OS network sandbox",
                "the browser executable and explicit interaction recipes are caller-selected and therefore part of the evidence provenance",
                "successful runtime/interaction probes are not perceptual visual-quality PASS; attributed hierarchy/spacing/coherence evidence remains separate",
            ],
        }
        receipt["capture_receipt_digest"] = _digest(receipt)
        (staging / "browser.capture.json").write_text(
            json.dumps(receipt, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        for source in (probe_source, reduced_probe_source):
            if source.exists():
                source.unlink()
        staging.rename(output)

    return {
        "truth_status": "LOCAL_HEADLESS_BROWSER_CAPTURE_MATERIALIZED",
        "path": str(output),
        "files": sorted(path.name for path in output.iterdir() if path.is_file()),
        "receipt": receipt,
        "observation": observation,
    }


def design_browser_summary() -> dict[str, Any]:
    return {
        "capture_schema": BROWSER_CAPTURE_SCHEMA,
        "runtime_probe_schema": RUNTIME_PROBE_SCHEMA,
        "interaction_probe_schema": INTERACTION_PROBE_SCHEMA,
        "operation": "capture-browser",
        "browser_contract": "caller-selected Chromium-compatible headless executable",
        "network_policy": "local file target only; external host resolution blocked",
        "profile_policy": "fresh temporary user-data directory per viewport/run",
        "third_party_python_dependency_required": False,
        "real_screenshot_bytes_captured_when_executor_available": True,
        "real_dom_bytes_captured_when_executor_available": True,
        "runtime_probe_attempted_when_executor_available": True,
        "explicit_interaction_recipes_available": True,
        "synthetic_activation_requires_explicit_authorization": True,
        "runtime_measurements": [
            "horizontal_overflow",
            "programmatic focus visibility",
            "opaque rendered text contrast",
            "runtime error receipts",
            "bounded DOM accessibility heuristics",
            "duration-based reduced-motion response when directly observed",
            "interaction error count when explicit recipes are observed",
        ],
        "automatic_perceptual_judgment": False,
        "real_keyboard_tab_traversal": False,
        "trusted_user_input_events": False,
        "automatic_browser_discovery": "PATH lookup only when caller explicitly names an executable",
    }


def operate_design_browser(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation != "capture-browser":
        raise DesignBrowserError(
            "design browser operation is unsupported",
            {"operation": operation},
        )
    timeout = inputs.get("timeout_seconds", DEFAULT_TIMEOUT_SECONDS)
    return capture_local_browser(
        root=root,
        plan_raw=inputs.get("plan"),
        target_value=inputs.get("target"),
        output_value=inputs.get("path"),
        browser_value=inputs.get("browser_executable"),
        viewport_sizes_raw=inputs.get("viewport_sizes"),
        timeout_seconds=timeout,
        interaction_recipes_raw=inputs.get("interaction_recipes"),
        allow_synthetic_activation=inputs.get("allow_synthetic_activation", False),
    )

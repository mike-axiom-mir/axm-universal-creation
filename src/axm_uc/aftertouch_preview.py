from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from .aftertouch_media_observers import _allowed, _browser, _game_recipes, _path, _plan
from .design_browser import DesignBrowserError, capture_local_browser
from .simulation import SimulationError, simulate_until_no_known_improvements

PREVIEW_SCHEMA = "axm.aftertouch-preview-checkpoint/v0.1"
PREVIEW_POLICY_SCHEMA = "axm.aftertouch-preview-policy/v0.1"
PREVIEW_REVIEW_SCHEMA = "axm.aftertouch-preview-review/v0.1"
CHAMBER_SCHEMA = "axm.evolution-aftertouch-chamber/v0.1"
MODES = {"off", "internal", "user-milestones", "user-every-round"}
MILESTONE_DEFAULTS = [3, 6, 7]
IMAGE_SUFFIXES = {".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg", ".webp": "image/webp", ".gif": "image/gif"}
GAME_KINDS = {"game", "browser-game", "playable-game", "offline-browser-game"}
GLB_KINDS = {"3d", "3d-asset", "glb", "game-asset", "animated-3d", "animated-3d-asset"}
VISUAL_KINDS = {"visual-thought", "paintgun-thought", "visual"}


class AftertouchPreviewError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _canonical(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise AftertouchPreviewError("preview state must be finite JSON") from exc


def _digest(value: Any) -> str:
    return f"sha256:{hashlib.sha256(_canonical(value)).hexdigest()}"


def _bytes_digest(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _chamber_digest(chamber: dict[str, Any]) -> str:
    body = copy.deepcopy(chamber)
    body.pop("chamber_digest", None)
    return _digest(body)


def _candidate_digest(candidate: dict[str, Any]) -> str:
    body = copy.deepcopy(candidate)
    body.pop("candidate_digest", None)
    return _digest(body)


def normalize_preview_policy(raw: Any = None) -> dict[str, Any]:
    if raw is None:
        raw = {}
    if not isinstance(raw, dict):
        raise AftertouchPreviewError("preview_policy must be an object")
    # A normalized policy is deliberately accepted as input on later round
    # transitions. Derived fields are never trusted: they are recomputed below.
    allowed = {
        "mode",
        "milestone_rounds",
        "retain_artifacts",
        "ai_review",
        "schema",
        "machine_observation",
        "user_feedback_policy",
        "ai_review_is_opt_in",
    }
    unexpected = sorted(set(raw) - allowed)
    if unexpected:
        raise AftertouchPreviewError("preview_policy has unsupported fields", {"unsupported": unexpected})
    if "schema" in raw and raw.get("schema") != PREVIEW_POLICY_SCHEMA:
        raise AftertouchPreviewError(
            "preview_policy schema is unsupported",
            {"schema": raw.get("schema"), "expected": PREVIEW_POLICY_SCHEMA},
        )
    mode = str(raw.get("mode", "internal")).strip().casefold()
    if mode not in MODES:
        raise AftertouchPreviewError("preview_policy.mode is unsupported", {"supported": sorted(MODES)})
    rounds = raw.get("milestone_rounds", MILESTONE_DEFAULTS)
    if not isinstance(rounds, list) or any(type(value) is not int or not 1 <= value <= 7 for value in rounds):
        raise AftertouchPreviewError("preview_policy.milestone_rounds must contain round numbers 1..7")
    rounds = sorted(set(rounds))
    retain = raw.get("retain_artifacts", True)
    ai_review = raw.get("ai_review", False)
    if not isinstance(retain, bool) or not isinstance(ai_review, bool):
        raise AftertouchPreviewError("preview_policy retain_artifacts and ai_review must be booleans")
    return {
        "schema": PREVIEW_POLICY_SCHEMA,
        "mode": mode,
        "milestone_rounds": rounds,
        "retain_artifacts": retain,
        "ai_review": ai_review,
        "machine_observation": mode != "off",
        "user_feedback_policy": (
            "every-round" if mode == "user-every-round" else "milestones" if mode == "user-milestones" else "never"
        ),
        "ai_review_is_opt_in": True,
    }


def preview_due(policy: dict[str, Any], round_number: int) -> bool:
    return policy.get("mode") != "off" and 1 <= round_number <= 7


def user_feedback_due(policy: dict[str, Any], round_number: int) -> bool:
    mode = policy.get("mode")
    return mode == "user-every-round" or (mode == "user-milestones" and round_number in policy.get("milestone_rounds", []))


def _artifact(candidate: dict[str, Any]) -> dict[str, Any]:
    proposal = candidate.get("proposal") if isinstance(candidate.get("proposal"), dict) else candidate
    value = proposal.get("artifact", proposal) if isinstance(proposal, dict) else {}
    return value if isinstance(value, dict) else {}


def _preview_root(root: Path, candidate: dict[str, Any], round_number: int) -> Path:
    candidate_id = str(candidate.get("candidate_id") or _digest(candidate)[7:27])
    safe = "".join(ch if ch.isalnum() or ch in "-_" else "-" for ch in candidate_id)[:100]
    return (Path(root).resolve() / "creations" / ".aftertouch-previews" / f"round-{round_number}" / safe).resolve()


def _existing_image(root: Path, artifact: dict[str, Any]) -> Path | None:
    raw = artifact.get("preview_image_path")
    if raw is None:
        return None
    path = _path(root, raw, "artifact.preview_image_path")
    if not path.is_file() or path.suffix.casefold() not in IMAGE_SUFFIXES:
        raise AftertouchPreviewError("preview_image_path must resolve to a supported image file")
    return path


def _image_receipt(path: Path, source: str) -> dict[str, Any]:
    body = path.read_bytes()
    return {
        "kind": "screenshot",
        "path": str(path),
        "mime_type": IMAGE_SUFFIXES[path.suffix.casefold()],
        "bytes": len(body),
        "digest": _bytes_digest(body),
        "source": source,
    }


def _copy_image(source: Path, output: Path) -> Path:
    output.mkdir(parents=True, exist_ok=True)
    target = output / f"preview{source.suffix.casefold()}"
    if target.exists():
        if target.read_bytes() == source.read_bytes():
            return target
        raise AftertouchPreviewError("preview checkpoint path already contains different image bytes", {"path": str(target)})
    shutil.copy2(source, target)
    return target


def _visual_preview(root: Path, artifact: dict[str, Any], output: Path, retain: bool) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    try:
        simulation = simulate_until_no_known_improvements(
            artifact.get("thought"),
            defaults=artifact.get("defaults"),
            alternatives=artifact.get("alternatives"),
            palette=artifact.get("palette"),
            criteria=artifact.get("criteria"),
            max_iterations=artifact.get("max_iterations", 32),
        )
    except SimulationError as exc:
        return [], {"simulation_error": str(exc), "details": exc.details}, "HOLD"
    projection = simulation.get("cinematic_projection", {})
    svg = projection.get("svg") if isinstance(projection, dict) else None
    if not isinstance(svg, str) or not svg.strip():
        return [], {"simulation_status": simulation.get("status")}, "HOLD"
    body = svg.encode("utf-8")
    if retain:
        output.mkdir(parents=True, exist_ok=True)
        path = output / "preview.svg"
        if path.exists() and path.read_bytes() != body:
            raise AftertouchPreviewError("visual preview path already contains different bytes", {"path": str(path)})
        if not path.exists():
            path.write_bytes(body)
        artifact_row = {"kind": "render-preview", "path": str(path), "mime_type": "image/svg+xml", "bytes": len(body), "digest": _bytes_digest(body), "source": "builtin:simulate_creation"}
    else:
        artifact_row = {"kind": "render-preview", "path": None, "mime_type": "image/svg+xml", "bytes": len(body), "digest": _bytes_digest(body), "source": "builtin:simulate_creation"}
    return [artifact_row], {"simulation_status": simulation.get("status"), "materialization_ready": simulation.get("materialization_ready")}, "CAPTURED"


def _game_preview(root: Path, artifact: dict[str, Any], output: Path, retain: bool) -> tuple[list[dict[str, Any]], dict[str, Any], str]:
    if "path" not in artifact:
        return [], {"reason": "playable preview requires artifact.path"}, "HOLD"
    target = _path(root, artifact["path"])
    if not _allowed(root, target):
        return [], {"reason": "preview refuses the live UC machine body"}, "HOLD"
    entrypoint = target / str(artifact.get("entrypoint", "index.html")) if target.is_dir() else target
    if not entrypoint.is_file():
        return [], {"reason": f"entrypoint missing: {entrypoint}"}, "HOLD"
    browser = _browser(artifact)
    if browser is None:
        return [], {"reason": "Chromium-compatible executor not supplied; PATH discovery is opt-in"}, "HOLD"
    allow_activation = artifact.get("allow_synthetic_activation", False)
    if not isinstance(allow_activation, bool):
        raise AftertouchPreviewError("artifact.allow_synthetic_activation must be boolean")
    recipes = artifact.get("interaction_recipes")
    if recipes is None:
        recipes = _game_recipes(entrypoint, allow_activation)
    viewport = artifact.get("viewport", {"width": 1280, "height": 720, "device_pixel_ratio": 1})
    if not isinstance(viewport, dict) or type(viewport.get("width")) is not int or type(viewport.get("height")) is not int:
        raise AftertouchPreviewError("artifact.viewport must contain integer width and height")
    viewport = {"width": viewport["width"], "height": viewport["height"], "device_pixel_ratio": viewport.get("device_pixel_ratio", 1)}
    timeout = artifact.get("timeout_seconds", 20)
    if type(timeout) is not int or not 1 <= timeout <= 120:
        raise AftertouchPreviewError("artifact.timeout_seconds must be an integer from 1 to 120")
    capture_path = output if retain else output.parent / (output.name + "-ephemeral")
    if capture_path.exists() and (capture_path / "game.png").is_file():
        screenshot = capture_path / "game.png"
        receipt = _read_capture(capture_path)
        return [_image_receipt(screenshot, "builtin:design_browser")], receipt, "CAPTURED"
    try:
        captured = capture_local_browser(
            root=root,
            plan_raw=_plan(viewport, bool(artifact.get("reduced_motion_probe", False))),
            target_value=str(entrypoint),
            output_value=str(capture_path),
            browser_value=browser,
            viewport_sizes_raw={"game": viewport},
            timeout_seconds=timeout,
            interaction_recipes_raw=recipes,
            allow_synthetic_activation=allow_activation,
        )
    except DesignBrowserError as exc:
        return [], {"reason": str(exc), "details": exc.details}, "HOLD"
    screenshot = capture_path / "game.png"
    if not screenshot.is_file() or screenshot.stat().st_size == 0:
        return [], {"reason": "browser capture produced no screenshot bytes"}, "HOLD"
    evidence = {
        "observation_digest": captured.get("observation", {}).get("observation_digest") if isinstance(captured.get("observation"), dict) else None,
        "runtime_probe": captured.get("receipt", {}).get("runtime_probe") if isinstance(captured.get("receipt"), dict) else None,
        "interaction_probe": captured.get("receipt", {}).get("interaction_probe") if isinstance(captured.get("receipt"), dict) else None,
    }
    if not retain:
        image = _image_receipt(screenshot, "builtin:design_browser")
        image["path"] = None
        shutil.rmtree(capture_path, ignore_errors=True)
        return [image], evidence, "CAPTURED_EPHEMERAL"
    return [_image_receipt(screenshot, "builtin:design_browser")], evidence, "CAPTURED"


def _read_capture(path: Path) -> dict[str, Any]:
    receipt = path / "browser.capture.json"
    if not receipt.is_file():
        return {"reused_existing_capture": True}
    try:
        value = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"reused_existing_capture": True, "receipt_parse": "unavailable"}
    return {"reused_existing_capture": True, "capture_receipt_digest": value.get("capture_receipt_digest") if isinstance(value, dict) else None}


def capture_candidate_preview(root: Path, raw_candidate: Any, *, round_number: int = 0, policy: Any = None) -> dict[str, Any]:
    if not isinstance(raw_candidate, dict):
        raise AftertouchPreviewError("candidate must be an object")
    normalized_policy = normalize_preview_policy(policy)
    if normalized_policy["mode"] == "off":
        return {"schema": PREVIEW_SCHEMA, "status": "OFF_BY_USER_POLICY", "artifacts": [], "policy": normalized_policy, "perceptual_quality_claimed": False}
    candidate = copy.deepcopy(raw_candidate)
    artifact = _artifact(candidate)
    kind = str(artifact.get("kind", "generic")).strip().casefold()
    output = _preview_root(Path(root), candidate, round_number or int(candidate.get("round", 0) or 0))
    existing = _existing_image(Path(root), artifact)
    evidence: dict[str, Any] = {}
    if existing is not None:
        preview = _copy_image(existing, output) if normalized_policy["retain_artifacts"] else existing
        rows = [_image_receipt(preview, "caller-supplied-preview-image")]
        if not normalized_policy["retain_artifacts"]:
            rows[0]["path"] = str(existing)
        status = "CAPTURED"
    elif kind in GAME_KINDS:
        rows, evidence, status = _game_preview(Path(root), artifact, output, normalized_policy["retain_artifacts"])
    elif kind in VISUAL_KINDS and "thought" in artifact:
        rows, evidence, status = _visual_preview(Path(root), artifact, output, normalized_policy["retain_artifacts"])
    elif kind in GLB_KINDS:
        rows, evidence, status = [], {"reason": "3D pose/geometry can be tested without pixels, but screenshot review requires a renderer-provided preview_image_path"}, "HOLD_NO_RENDER_PREVIEW"
    else:
        rows, evidence, status = [], {"reason": "artifact kind has no registered pixel preview adapter"}, "NOT_APPLICABLE"
    checkpoint = {
        "schema": PREVIEW_SCHEMA,
        "status": status,
        "round": round_number or candidate.get("round"),
        "candidate_id": candidate.get("candidate_id"),
        "candidate_digest": candidate.get("candidate_digest"),
        "artifact_kind": kind or "generic",
        "artifacts": rows,
        "machine_observation": evidence,
        "review_audience": {
            "machine": True,
            "ai": normalized_policy["ai_review"],
            "user": normalized_policy["mode"] in {"user-milestones", "user-every-round"},
        },
        "user_feedback_required": user_feedback_due(normalized_policy, int(round_number or candidate.get("round", 0) or 0)),
        "policy": normalized_policy,
        "reviews": [],
        "perceptual_quality_claimed": False,
        "meaning": "preview pixels are evidence for adjustment between creation rounds; capture alone is never aesthetic PASS",
    }
    checkpoint["preview_digest"] = _digest(checkpoint)
    return checkpoint


def _verify_chamber(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict) or raw.get("schema") != CHAMBER_SCHEMA:
        raise AftertouchPreviewError("preview feedback requires an evolution-aftertouch chamber")
    supplied = raw.get("chamber_digest")
    if supplied != _chamber_digest(raw):
        raise AftertouchPreviewError("chamber digest mismatch")
    return copy.deepcopy(raw)


def _summary(candidate: dict[str, Any]) -> dict[str, Any]:
    return {
        "candidate_id": candidate.get("candidate_id"),
        "candidate_digest": candidate.get("candidate_digest"),
        "origin_team_id": candidate.get("origin_team_id"),
        "proposal": copy.deepcopy(candidate.get("proposal")),
        "evidence": copy.deepcopy(candidate.get("evidence", [])),
        "verification": copy.deepcopy(candidate.get("verification", [])),
        "unknowns": copy.deepcopy(candidate.get("unknowns", [])),
        "preview_checkpoint": copy.deepcopy(candidate.get("preview_checkpoint")),
    }


def _replace_candidate_copies(chamber: dict[str, Any], candidate: dict[str, Any]) -> None:
    cid = candidate.get("candidate_id")
    for key in ("survivors", "finalists"):
        rows = chamber.get(key)
        if isinstance(rows, list):
            chamber[key] = [copy.deepcopy(candidate) if isinstance(row, dict) and row.get("candidate_id") == cid else row for row in rows]
    for round_row in chamber.get("rounds", []):
        if not isinstance(round_row, dict):
            continue
        survivors = round_row.get("survivors")
        if isinstance(survivors, list):
            round_row["survivors"] = [copy.deepcopy(candidate) if isinstance(row, dict) and row.get("candidate_id") == cid else row for row in survivors]
        parents = round_row.get("parent_candidates")
        if isinstance(parents, list):
            round_row["parent_candidates"] = [_summary(candidate) if isinstance(row, dict) and row.get("candidate_id") == cid else row for row in parents]
        packets = round_row.get("creative_packets")
        if isinstance(packets, list):
            for packet in packets:
                if isinstance(packet, dict) and packet.get("parent_candidate_id") == cid:
                    packet["parent_candidate"] = _summary(candidate)
                    packet["preview_adjustment_context"] = copy.deepcopy(candidate.get("preview_checkpoint"))


def bind_prepare_preview(inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("schema") != CHAMBER_SCHEMA:
        return result
    result = copy.deepcopy(result)
    result["preview_policy"] = normalize_preview_policy(inputs.get("preview_policy"))
    result["preview_state"] = {"pending_user_feedback": False, "last_completed_round": 0, "checkpoints": []}
    result["policy"]["intermediate_preview_observation"] = result["preview_policy"]["mode"] != "off"
    result["policy"]["ai_preview_review_opt_in"] = result["preview_policy"]["ai_review"]
    result["policy"]["user_preview_interruptions"] = result["preview_policy"]["user_feedback_policy"]
    result.pop("chamber_digest", None)
    result["chamber_digest"] = _chamber_digest(result)
    return result


def preflight_preview_advance(inputs: dict[str, Any]) -> None:
    operation = str(inputs.get("operation", "")).strip().casefold()
    if operation not in {"advance", "advance-round", "judge-round"}:
        return
    chamber = inputs.get("chamber")
    if not isinstance(chamber, dict):
        return
    state = chamber.get("preview_state")
    if isinstance(state, dict) and state.get("pending_user_feedback") is True:
        raise AftertouchPreviewError(
            "user preview feedback is required before the next evolution round may advance",
            {"next_operation": "record-preview-feedback", "round": state.get("last_completed_round")},
        )


def bind_advance_preview(root: Path, inputs: dict[str, Any], result: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(result, dict) or result.get("schema") != CHAMBER_SCHEMA:
        return result
    before = inputs.get("chamber") if isinstance(inputs.get("chamber"), dict) else {}
    round_number = int(before.get("current_round", result.get("current_round", 0)) or 0)
    policy = normalize_preview_policy(result.get("preview_policy", before.get("preview_policy")))
    result = copy.deepcopy(result)
    result["preview_policy"] = policy
    state = result.get("preview_state") if isinstance(result.get("preview_state"), dict) else {"pending_user_feedback": False, "last_completed_round": 0, "checkpoints": []}
    if not preview_due(policy, round_number):
        result["preview_state"] = state
        result.pop("chamber_digest", None)
        result["chamber_digest"] = _chamber_digest(result)
        return result

    survivors = result.get("survivors") if isinstance(result.get("survivors"), list) else []
    updated = []
    checkpoints = []
    for candidate in survivors:
        if not isinstance(candidate, dict):
            continue
        candidate = copy.deepcopy(candidate)
        checkpoint = capture_candidate_preview(Path(root), candidate, round_number=round_number, policy=policy)
        candidate["preview_checkpoint"] = checkpoint
        candidate["candidate_digest"] = _candidate_digest(candidate)
        updated.append(candidate)
        checkpoints.append(checkpoint)
    for candidate in updated:
        _replace_candidate_copies(result, candidate)

    state["last_completed_round"] = round_number
    state.setdefault("checkpoints", []).append({"round": round_number, "candidate_previews": copy.deepcopy(checkpoints)})
    requires_user = user_feedback_due(policy, round_number)
    state["pending_user_feedback"] = requires_user
    if requires_user:
        state["resume_status"] = result.get("status")
        result["status"] = f"ROUND_{round_number}_PREVIEW_AWAITING_USER_FEEDBACK"
        if isinstance(result.get("final_gate"), dict):
            state["output_ready_before_user_preview"] = result["final_gate"].get("output_ready_under_declared_gates")
            result["final_gate"]["preview_feedback_pending"] = True
            result["final_gate"]["output_ready_under_declared_gates"] = False
    result["preview_state"] = state
    result.pop("chamber_digest", None)
    result["chamber_digest"] = _chamber_digest(result)
    return result


def _review(value: Any, candidate_id: str, policy: dict[str, Any]) -> list[dict[str, Any]]:
    rows = value if isinstance(value, list) else [value]
    result = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            raise AftertouchPreviewError(f"feedback.{candidate_id}[{index}] must be an object")
        reviewer = str(row.get("reviewer", "user")).strip().casefold()
        if reviewer not in {"machine", "ai", "user"}:
            raise AftertouchPreviewError("preview reviewer must be machine, ai, or user")
        if reviewer == "ai" and not policy.get("ai_review"):
            raise AftertouchPreviewError("AI preview review is disabled by user policy")
        observation = row.get("observation", "")
        if not isinstance(observation, str) or not observation.strip():
            raise AftertouchPreviewError("preview review observation must be non-empty text")
        decision = str(row.get("decision", "continue")).strip().casefold()
        if decision not in {"continue", "adjust", "hold"}:
            raise AftertouchPreviewError("preview review decision must be continue, adjust, or hold")
        changes = row.get("requested_changes", [])
        if not isinstance(changes, list) or any(not isinstance(item, str) or not item.strip() for item in changes):
            raise AftertouchPreviewError("requested_changes must be a list of non-empty text")
        result.append({
            "schema": PREVIEW_REVIEW_SCHEMA,
            "reviewer": reviewer,
            "observation": observation.strip(),
            "decision": decision,
            "requested_changes": [item.strip() for item in changes],
        })
    return result


def record_preview_feedback(raw_chamber: Any, feedback: Any) -> dict[str, Any]:
    chamber = _verify_chamber(raw_chamber)
    state = chamber.get("preview_state")
    if not isinstance(state, dict) or state.get("pending_user_feedback") is not True:
        raise AftertouchPreviewError("chamber is not awaiting user preview feedback")
    policy = normalize_preview_policy(chamber.get("preview_policy"))
    if not isinstance(feedback, dict):
        raise AftertouchPreviewError("feedback must be an object keyed by candidate_id")
    survivors = chamber.get("survivors") if isinstance(chamber.get("survivors"), list) else []
    expected = {row.get("candidate_id") for row in survivors if isinstance(row, dict) and row.get("candidate_id")}
    if set(feedback) != expected:
        raise AftertouchPreviewError("feedback must cover exactly both retained candidates", {"expected": sorted(expected), "supplied": sorted(feedback)})
    held = False
    adjusted = False
    for candidate in list(survivors):
        if not isinstance(candidate, dict):
            continue
        cid = candidate["candidate_id"]
        reviews = _review(feedback[cid], cid, policy)
        if not any(row["reviewer"] == "user" for row in reviews):
            raise AftertouchPreviewError("user checkpoint requires a user review for each retained candidate", {"candidate_id": cid})
        checkpoint = candidate.get("preview_checkpoint") if isinstance(candidate.get("preview_checkpoint"), dict) else None
        if checkpoint is None:
            raise AftertouchPreviewError("retained candidate has no preview checkpoint", {"candidate_id": cid})
        candidate = copy.deepcopy(candidate)
        checkpoint = copy.deepcopy(checkpoint)
        checkpoint["reviews"] = reviews
        checkpoint["review_status"] = "HOLD" if any(row["decision"] == "hold" for row in reviews) else "ADJUST" if any(row["decision"] == "adjust" for row in reviews) else "CONTINUE"
        checkpoint.pop("preview_digest", None)
        checkpoint["preview_digest"] = _digest(checkpoint)
        candidate["preview_checkpoint"] = checkpoint
        candidate["candidate_digest"] = _candidate_digest(candidate)
        held = held or checkpoint["review_status"] == "HOLD"
        adjusted = adjusted or checkpoint["review_status"] == "ADJUST"
        _replace_candidate_copies(chamber, candidate)
    state["pending_user_feedback"] = False
    state["last_feedback_status"] = "HOLD" if held else "ADJUST" if adjusted else "CONTINUE"
    resume_status = state.pop("resume_status", chamber.get("status"))
    chamber["status"] = "USER_PREVIEW_HOLD_BEFORE_OUTPUT_OR_NEXT_ROUND" if held else resume_status
    if isinstance(chamber.get("final_gate"), dict):
        chamber["final_gate"]["preview_feedback_pending"] = False
        ready_before = bool(state.pop("output_ready_before_user_preview", False))
        chamber["final_gate"]["output_ready_under_declared_gates"] = ready_before and not held and not adjusted
        if adjusted:
            chamber["final_gate"]["next_gate"] = "apply requested preview adjustments and re-observe before output"
        elif held:
            chamber["final_gate"]["next_gate"] = "user held output at preview checkpoint"
    chamber["preview_state"] = state
    chamber.pop("chamber_digest", None)
    chamber["chamber_digest"] = _chamber_digest(chamber)
    return chamber


def inspect_preview() -> dict[str, Any]:
    return {
        "schema": PREVIEW_SCHEMA,
        "policy_schema": PREVIEW_POLICY_SCHEMA,
        "modes": sorted(MODES),
        "default_policy": normalize_preview_policy(),
        "capture_adapters": ["visual-thought-svg", "offline-browser-game-screenshot", "caller-rendered-image"],
        "3d_rule": "3D geometry/pose evidence remains separate; pixel review binds a renderer-provided preview_image_path until a renderer executor is explicitly available",
        "reviewers": ["machine", "ai", "user"],
        "ai_review_default": False,
        "user_checkpoint_can_block_next_round": True,
        "capture_is_not_aesthetic_pass": True,
    }


def operate_aftertouch_preview(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "inspect-preview")).strip().casefold()
    if operation in {"inspect-preview", "preview-summary", "inspect-preview-policy"}:
        return {"truth_status": "DECLARED_INTERMEDIATE_AFTERTOUCH_PREVIEW_CONTRACT", **inspect_preview()}
    if operation in {"capture-preview", "preview-candidate", "capture-intermediate-preview"}:
        return capture_candidate_preview(
            Path(root), inputs.get("candidate"), round_number=int(inputs.get("round", 0) or 0), policy=inputs.get("preview_policy")
        )
    if operation in {"record-preview-feedback", "review-preview", "record-user-preview"}:
        return record_preview_feedback(inputs.get("chamber"), inputs.get("feedback"))
    raise AftertouchPreviewError("unsupported preview operation", {"operation": operation, "supported": inspect_preview()})

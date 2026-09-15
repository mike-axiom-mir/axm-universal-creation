from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

MAX_REQUEST_BYTES = 64 * 1024 * 1024
DEFAULT_TIMEOUT_SECONDS = 180
BRIDGE_RELATIVE = Path("capabilities/platform-hands/shared/asset-hands/creative-flow-bridge.js")


class CreativeFlowError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def integration_summary(root: Path) -> dict[str, Any]:
    root = Path(root).resolve()
    bridge = root / BRIDGE_RELATIVE
    return {
        "type": "CREATIVE_FLOW_SPINE",
        "version": "1.2.0",
        "creation_kind": "creative-flow",
        "bridge": str(BRIDGE_RELATIVE).replace("\\", "/"),
        "bridge_present": bridge.is_file(),
        "runtime": "node",
        "machine_route": "live capability registry",
        "policy": (
            "explicit plan execution plus deterministic discovery; known adaptive quality profiles may derive "
            "bounded plans from goal + quality + machine budget, while unknown goals still HOLD"
        ),
        "adaptive_quality": True,
        "adaptive_modes": ["adaptive-plan", "adaptive-execute", "adaptive-calibrate"],
        "calibration": "explicit bounded local execution returns observational work-units-per-ms; never inferred from a hardware label",
        "parallel_runtime": "planned-not-executed",
        "source_state_mutation": False,
    }


def run_creative_flow(root: Path, request: dict[str, Any], *, timeout: int = DEFAULT_TIMEOUT_SECONDS) -> dict[str, Any]:
    if not isinstance(request, dict):
        raise CreativeFlowError("creative flow request must be an object")
    root = Path(root).resolve()
    bridge = root / BRIDGE_RELATIVE
    if not bridge.is_file():
        raise CreativeFlowError(
            "creative flow bridge is missing",
            {"bridge": str(bridge)},
        )
    node = shutil.which("node")
    if node is None:
        raise CreativeFlowError(
            "creative flow requires the local Node runtime used by Platform Hands",
            {"runtime": "node", "network_required": False},
        )
    payload = json.dumps(request, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    if len(payload) > MAX_REQUEST_BYTES:
        raise CreativeFlowError(
            "creative flow request exceeds 64 MiB",
            {"bytes": len(payload), "maximum_bytes": MAX_REQUEST_BYTES},
        )
    try:
        completed = subprocess.run(
            [node, str(bridge)],
            cwd=root,
            input=payload,
            capture_output=True,
            timeout=timeout,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise CreativeFlowError(
            "creative flow runtime timed out",
            {"timeout_seconds": timeout},
        ) from exc
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace")[-8000:]
        raise CreativeFlowError(
            "creative flow runtime failed",
            {"returncode": completed.returncode, "stderr": stderr},
        )
    try:
        result = json.loads(completed.stdout.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise CreativeFlowError(
            "creative flow runtime returned unreadable JSON",
            {"stdout_bytes": len(completed.stdout)},
        ) from exc
    if not isinstance(result, dict):
        raise CreativeFlowError("creative flow runtime must return an object")
    return result

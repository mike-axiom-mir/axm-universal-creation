from __future__ import annotations

import hashlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

MAX_CAPTURE_CHARS = 65536
MAX_TIMEOUT_SECONDS = 600

EXTERNAL_VISUAL_TOOLS: dict[str, dict[str, Any]] = {
    "blender": {"label": "Blender", "categories": ["3d", "modeling", "animation", "rendering"], "binary_candidates": ["blender"], "probe_args": ["--version"]},
    "godot": {"label": "Godot", "categories": ["game-engine", "scene-runtime", "rendering"], "binary_candidates": ["godot", "godot4"], "probe_args": ["--version"]},
    "unreal": {"label": "Unreal Engine", "categories": ["game-engine", "scene-runtime", "rendering"], "binary_candidates": ["UnrealEditor-Cmd", "UnrealEditor", "UE4Editor-Cmd", "UE4Editor"], "probe_args": null},
    "krita": {"label": "Krita", "categories": ["2d", "painting", "textures"], "binary_candidates": ["krita"], "probe_args": ["--version"]},
    "gimp": {"label": "GIMP", "categories": ["2d", "image-processing", "compositing"], "binary_candidates": ["gimp", "gimp-3.0"], "probe_args": ["--version"]},
    "imagemagick": {"label": "ImageMagick", "categories": ["2d", "image-processing", "compositing"], "binary_candidates": ["magick", "convert"], "probe_args": ["-version"]},
    "ffmpeg": {"label": "FFmpeg", "categories": ["video", "audio", "compositing"], "binary_candidates": ["ffmpeg"], "probe_args": ["-version"]},
    "openscad": {"label": "OpenSCAD", "categories": ["3d", "parametric", "cad"], "binary_candidates": ["openscad"], "probe_args": ["--version"]},
    "houdini": {"label": "Houdini", "categories": ["3d", "procedural", "vfx", "simulation"], "binary_candidates": ["hython", "houdini"], "probe_args": null},
    "inkscape": {"label": "Inkscape", "categories": ["2d", "vector", "svg"], "binary_candidates": ["inkscape"], "probe_args": ["--version"]},
}


class ExternalVisualToolError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _normalize_tool(tool: Any) -> str:
    value = str(tool or "").strip().casefold()
    if value not in EXTERNAL_VISUAL_TOOLS:
        raise ExternalVisualToolError(
            f"unsupported external visual tool: {value or '<empty>'}",
            {"supported_tools": sorted(EXTERNAL_VISUAL_TOOLS)},
        )
    return value


def _resolve_executable(tool: str) -> str | None:
    spec = EXTERNAL_VISUAL_TOOLS[tool]
    for candidate in spec["binary_candidates"]:
        resolved = shutil.which(candidate)
        if resolved:
            return str(Path(resolved).resolve())
    return None


def _tool_record(tool: str) -> dict[str, Any]:
    spec = EXTERNAL_VISUAL_TOOLS[tool]
    executable = _resolve_executable(tool)
    return {
        "tool": tool,
        "label": spec["label"],
        "categories": list(spec["categories"]),
        "binary_candidates": list(spec["binary_candidates"]),
        "available": executable is not None,
        "resolved_executable": executable,
        "native": False,
        "dependency_class": "EXTERNAL_OPTIONAL",
        "identity_claim": "candidate executable discovered by PATH only; semantic identity is not inferred beyond the selected connector",
    }


def catalog_external_visual_tools() -> dict[str, Any]:
    return {
        "truth_status": "EXTERNAL_OPTIONAL_CONNECTOR_CATALOG",
        "native": False,
        "dependency_class": "EXTERNAL_OPTIONAL",
        "network_install_performed": False,
        "tools": [_tool_record(tool) for tool in sorted(EXTERNAL_VISUAL_TOOLS)],
        "boundary": (
            "These connectors do not make external software part of AXM's native capability. "
            "They only expose installed third-party executables through an explicit, receipted boundary."
        ),
    }


def inspect_external_visual_tool(tool: Any) -> dict[str, Any]:
    normalized = _normalize_tool(tool)
    result = _tool_record(normalized)
    result["truth_status"] = "EXTERNAL_CONNECTOR_INSPECTED"
    result["probe_executed"] = False
    return result


def _capture_digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8", errors="replace")).hexdigest()


def _run(*, tool: str, executable: str, args: list[str], cwd: Path | None, timeout: int, operation: str) -> dict[str, Any]:
    command = [executable, *args]
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd is not None else None,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ExternalVisualToolError(
            f"{tool} {operation} timed out after {timeout}s",
            {"tool": tool, "operation": operation, "timeout_seconds": timeout},
        ) from exc
    except OSError as exc:
        raise ExternalVisualToolError(
            f"{tool} {operation} could not start: {exc}",
            {"tool": tool, "operation": operation, "executable": executable},
        ) from exc

    stdout = completed.stdout or ""
    stderr = completed.stderr or ""
    return {
        "truth_status": "EXTERNAL_TOOL_EXECUTION_OBSERVED",
        "operation": operation,
        "tool": tool,
        "native": False,
        "dependency_class": "EXTERNAL_OPTIONAL",
        "external_dependency_used": True,
        "resolved_executable": executable,
        "argv": command,
        "cwd": str(cwd) if cwd is not None else None,
        "returncode": int(completed.returncode),
        "success": completed.returncode == 0,
        "stdout": stdout[:MAX_CAPTURE_CHARS],
        "stderr": stderr[:MAX_CAPTURE_CHARS],
        "stdout_truncated": len(stdout) > MAX_CAPTURE_CHARS,
        "stderr_truncated": len(stderr) > MAX_CAPTURE_CHARS,
        "stdout_sha256": _capture_digest(stdout),
        "stderr_sha256": _capture_digest(stderr),
        "tool_execution_observed": True,
        "visual_output_observed": False,
        "network_install_performed": False,
    }


def probe_external_visual_tool(tool: Any, *, timeout: int = 10) -> dict[str, Any]:
    normalized = _normalize_tool(tool)
    spec = EXTERNAL_VISUAL_TOOLS[normalized]
    executable = _resolve_executable(normalized)
    if executable is None:
        return {**_tool_record(normalized), "truth_status": "EXTERNAL_CONNECTOR_UNAVAILABLE", "probe_executed": False}
    probe_args = spec.get("probe_args")
    if not probe_args:
        return {
            **_tool_record(normalized),
            "truth_status": "EXTERNAL_CONNECTOR_AVAILABLE_UNPROBED",
            "probe_executed": False,
            "reason": "no conservative default probe is declared for this connector",
        }
    bounded_timeout = max(1, min(int(timeout), 30))
    result = _run(
        tool=normalized,
        executable=executable,
        args=[str(item) for item in probe_args],
        cwd=None,
        timeout=bounded_timeout,
        operation="probe",
    )
    result["probe_executed"] = True
    return result


def execute_external_visual_tool(tool: Any, *, args: Any, cwd: Path, allow_execute: Any, timeout: Any = 120) -> dict[str, Any]:
    normalized = _normalize_tool(tool)
    if allow_execute is not True:
        raise ExternalVisualToolError(
            "external visual tool execution requires allow_execute=true",
            {"tool": normalized},
        )
    if not isinstance(args, list) or not all(isinstance(item, str) for item in args):
        raise ExternalVisualToolError("external visual tool args must be a list of strings")
    if any("\x00" in item for item in args):
        raise ExternalVisualToolError("external visual tool args cannot contain NUL bytes")
    executable = _resolve_executable(normalized)
    if executable is None:
        raise ExternalVisualToolError(
            f"external visual tool is not installed or not visible on PATH: {normalized}",
            {"tool": normalized, "binary_candidates": EXTERNAL_VISUAL_TOOLS[normalized]["binary_candidates"]},
        )
    if not cwd.is_dir():
        raise ExternalVisualToolError(f"external visual tool cwd does not exist: {cwd}")
    try:
        bounded_timeout = max(1, min(int(timeout), MAX_TIMEOUT_SECONDS))
    except (TypeError, ValueError) as exc:
        raise ExternalVisualToolError("external visual tool timeout must be an integer") from exc
    return _run(
        tool=normalized,
        executable=executable,
        args=args,
        cwd=cwd,
        timeout=bounded_timeout,
        operation="execute",
    )


def operate_external_visual_tool(root: Path, inputs: dict[str, Any]) -> dict[str, Any]:
    operation = str(inputs.get("operation", "catalog")).strip().casefold()
    if operation == "catalog":
        return catalog_external_visual_tools()
    if operation == "inspect":
        return inspect_external_visual_tool(inputs.get("tool"))
    if operation == "probe":
        return probe_external_visual_tool(inputs.get("tool"), timeout=inputs.get("timeout", 10))
    if operation == "execute":
        cwd_raw = str(inputs.get("cwd", "creations"))
        cwd = Path(cwd_raw).expanduser()
        if not cwd.is_absolute():
            cwd = (root / cwd).resolve()
        else:
            cwd = cwd.resolve()
        return execute_external_visual_tool(
            inputs.get("tool"),
            args=inputs.get("args", []),
            cwd=cwd,
            allow_execute=inputs.get("allow_execute", False),
            timeout=inputs.get("timeout", 120),
        )
    raise ExternalVisualToolError(
        f"unsupported external visual tool operation: {operation}",
        {"supported_operations": ["catalog", "inspect", "probe", "execute"]},
    )

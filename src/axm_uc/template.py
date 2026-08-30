from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .project import ProjectError, build_project


PLACEHOLDER_RE = re.compile(r"\[\[AXM:([A-Za-z][A-Za-z0-9_.-]{0,127})\]\]")
VARIABLE_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.-]{0,127}")
PROJECT_TYPES = {"generic", "static-web", "python"}
RESERVED_PREFIX = "[[AXM:"


def _template_text(value: Any, label: str) -> str:
    if not isinstance(value, str):
        raise ProjectError(f"{label} must be text")
    residue = PLACEHOLDER_RE.sub("", value)
    if RESERVED_PREFIX in residue:
        raise ProjectError(f"{label} contains a malformed reserved AXM placeholder")
    return value


def _render(text: str, variables: dict[str, str]) -> str:
    return PLACEHOLDER_RE.sub(lambda match: variables[match.group(1)], text)


def render_project_template(
    template: Any,
    variables: Any,
    reject_unused_variables: bool = True,
) -> dict[str, Any]:
    if not isinstance(template, dict):
        raise ProjectError("template must be an object")

    template_id = template.get("id")
    version = template.get("version")
    project_type = str(template.get("project_type", "")).strip().casefold()
    files = template.get("files")
    if not isinstance(template_id, str) or not template_id.strip():
        raise ProjectError("template.id must be non-empty text")
    if not isinstance(version, str) or not version.strip():
        raise ProjectError("template.version must be non-empty text")
    if project_type not in PROJECT_TYPES:
        raise ProjectError("template.project_type must be generic, static-web, or python")
    if not isinstance(files, dict) or not files:
        raise ProjectError("template.files must be a non-empty object mapping paths to template text")
    if not isinstance(variables, dict):
        raise ProjectError("variables must be an object mapping placeholder names to exact text")

    normalized_variables: dict[str, str] = {}
    for raw_name, raw_value in variables.items():
        if not isinstance(raw_name, str) or VARIABLE_NAME_RE.fullmatch(raw_name) is None:
            raise ProjectError(f"invalid template variable name: {raw_name!r}")
        if not isinstance(raw_value, str):
            raise ProjectError(f"template variable must be exact text: {raw_name}")
        normalized_variables[raw_name] = raw_value

    prepared: list[tuple[str, str, str]] = []
    referenced: set[str] = set()
    for raw_path, raw_content in files.items():
        template_path = _template_text(raw_path, "template file path")
        template_content = _template_text(raw_content, f"template content for {template_path}")
        referenced.update(PLACEHOLDER_RE.findall(template_path))
        referenced.update(PLACEHOLDER_RE.findall(template_content))
        prepared.append((template_path, template_content, str(raw_path)))

    provided = set(normalized_variables)
    missing = sorted(referenced - provided)
    unused = sorted(provided - referenced)
    if missing:
        raise ProjectError("template variables are missing", {"missing_variables": missing})
    if unused and reject_unused_variables:
        raise ProjectError("template variables were supplied but not used", {"unused_variables": unused})

    rendered_files: dict[str, str] = {}
    path_receipts: list[dict[str, str]] = []
    for template_path, template_content, raw_path in prepared:
        rendered_path = _render(template_path, normalized_variables)
        if rendered_path in rendered_files:
            raise ProjectError(
                "template paths collide after variable substitution",
                {"rendered_path": rendered_path},
            )
        rendered_files[rendered_path] = _render(template_content, normalized_variables)
        path_receipts.append({"template_path": raw_path, "rendered_path": rendered_path})

    return {
        "files": rendered_files,
        "template_instance": {
            "truth_status": "DETERMINISTIC_SINGLE_PASS_TEMPLATE_INSTANTIATION",
            "template_id": template_id.strip(),
            "template_version": version.strip(),
            "project_type": project_type,
            "variables_used": sorted(referenced),
            "rendered_paths": sorted(path_receipts, key=lambda row: row["rendered_path"]),
            "substitution": "raw exact text",
            "recursive_expansion": False,
            "escaping_or_semantic_rewrite": False,
            "limitations": [
                "template substitution is not parser-aware",
                "callers or templates must provide any grammar-specific escaping",
                "loops, conditionals, and recursive placeholder expansion are not implemented",
            ],
        },
    }


def instantiate_project_template(
    target: Path,
    template: Any,
    variables: Any,
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
    publish_mode: str = "grounded-draft",
) -> dict[str, Any]:
    rendered = render_project_template(template, variables)
    instance = rendered["template_instance"]
    result = build_project(
        target=target,
        files=rendered["files"],
        project_type=instance["project_type"],
        checks=checks,
        replace=replace,
        publish_mode=publish_mode,
    )
    result["template_instance"] = instance
    return result

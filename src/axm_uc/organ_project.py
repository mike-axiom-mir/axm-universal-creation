from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .project import ProjectError, build_project
from .template import PROJECT_TYPES, render_project_template


INTERFACE_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ProjectError(f"{label} must be non-empty text")
    return value.strip()


def _interface_names(value: Any, label: str, organ_id: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ProjectError(f"software organ {label} must be a list", {"organ_id": organ_id})
    names: list[str] = []
    for raw in value:
        name = _required_text(raw, f"software organ {label} entry for {organ_id}")
        if INTERFACE_NAME_RE.fullmatch(name) is None:
            raise ProjectError(
                "software organ interface names must use letters, numbers, dot, underscore, colon, or hyphen",
                {"organ_id": organ_id, "interface": name, "field": label},
            )
        if name in names:
            raise ProjectError(
                f"software organ {label} entries must be unique",
                {"organ_id": organ_id, "duplicate_interface": name, "field": label},
            )
        names.append(name)
    return names


def _prepare_organs(raw_organs: Any) -> tuple[list[dict[str, Any]], dict[str, int]]:
    if not isinstance(raw_organs, list) or not raw_organs:
        raise ProjectError("assembly.organs must be a non-empty list")

    organs: list[dict[str, Any]] = []
    positions: dict[str, int] = {}
    for position, raw in enumerate(raw_organs):
        if not isinstance(raw, dict):
            raise ProjectError("every software organ must be an object", {"position": position})
        organ_id = _required_text(raw.get("id"), f"assembly.organs[{position}].id")
        version = _required_text(raw.get("version"), f"assembly.organs[{position}].version")
        if organ_id in positions:
            raise ProjectError("software organ ids must be unique", {"duplicate_organ_id": organ_id})
        purpose = raw.get("purpose")
        if purpose is not None and not isinstance(purpose, str):
            raise ProjectError("software organ purpose must be text when supplied", {"organ_id": organ_id})
        raw_dependencies = raw.get("depends_on", [])
        if not isinstance(raw_dependencies, list):
            raise ProjectError("software organ depends_on must be a list", {"organ_id": organ_id})
        dependencies: list[str] = []
        for dependency in raw_dependencies:
            dependency_id = _required_text(dependency, f"software organ dependency for {organ_id}")
            if dependency_id in dependencies:
                raise ProjectError(
                    "software organ dependencies must be unique",
                    {"organ_id": organ_id, "duplicate_dependency": dependency_id},
                )
            dependencies.append(dependency_id)
        bindings = raw.get("bindings")
        if bindings is not None and not isinstance(bindings, dict):
            raise ProjectError("software organ bindings must be an object when supplied", {"organ_id": organ_id})
        positions[organ_id] = position
        organs.append({
            "id": organ_id,
            "version": version,
            "purpose": purpose.strip() if isinstance(purpose, str) else None,
            "depends_on": dependencies,
            "provides": _interface_names(raw.get("provides"), "provides", organ_id),
            "requires": _interface_names(raw.get("requires"), "requires", organ_id),
            "files": raw.get("files"),
            "bindings": bindings,
            "package_ref": raw.get("package_ref"),
            "package_id": raw.get("package_id"),
            "package_source_path": raw.get("package_source_path"),
        })
    return organs, positions


def _dependency_order(organs: list[dict[str, Any]], positions: dict[str, int]) -> list[str]:
    known = set(positions)
    missing = sorted({
        dependency
        for organ in organs
        for dependency in organ["depends_on"]
        if dependency not in known
    })
    if missing:
        dependants = {
            dependency: [organ["id"] for organ in organs if dependency in organ["depends_on"]]
            for dependency in missing
        }
        raise ProjectError(
            "software organ dependencies reference missing organs",
            {"missing_dependencies": missing, "required_by": dependants},
        )

    pending = {organ["id"]: set(organ["depends_on"]) for organ in organs}
    ordered: list[str] = []
    while pending:
        ready = sorted(
            (organ_id for organ_id, dependencies in pending.items() if not dependencies),
            key=positions.__getitem__,
        )
        if not ready:
            unresolved = sorted(pending, key=positions.__getitem__)
            raise ProjectError(
                "software organ dependency cycle detected",
                {
                    "cycle_candidates": unresolved,
                    "unresolved_dependencies": {
                        organ_id: sorted(pending[organ_id], key=positions.__getitem__)
                        for organ_id in unresolved
                    },
                },
            )
        for organ_id in ready:
            ordered.append(organ_id)
            del pending[organ_id]
            for dependencies in pending.values():
                dependencies.discard(organ_id)
    return ordered


def _resolve_interfaces(
    organs: list[dict[str, Any]],
    order: list[str],
) -> tuple[dict[str, str], dict[str, set[str]]]:
    by_id = {organ["id"]: organ for organ in organs}
    providers: dict[str, str] = {}
    for organ in organs:
        for interface in organ["provides"]:
            if interface in providers:
                raise ProjectError(
                    "software organ interface has more than one provider",
                    {
                        "interface": interface,
                        "first_organ": providers[interface],
                        "second_organ": organ["id"],
                    },
                )
            providers[interface] = organ["id"]

    dependency_closure: dict[str, set[str]] = {}
    for organ_id in order:
        direct = set(by_id[organ_id]["depends_on"])
        transitive = set(direct)
        for dependency in direct:
            transitive.update(dependency_closure[dependency])
        dependency_closure[organ_id] = transitive

    missing: dict[str, list[str]] = {}
    unreachable: list[dict[str, Any]] = []
    for organ in organs:
        for interface in organ["requires"]:
            provider = providers.get(interface)
            if provider is None:
                missing.setdefault(interface, []).append(organ["id"])
            elif provider not in dependency_closure[organ["id"]]:
                unreachable.append({
                    "organ_id": organ["id"],
                    "interface": interface,
                    "provider": provider,
                    "dependency_closure": sorted(dependency_closure[organ["id"]]),
                })
    if missing:
        raise ProjectError(
            "software organ requirements reference interfaces with no provider",
            {"missing_interfaces": sorted(missing), "required_by": missing},
        )
    if unreachable:
        raise ProjectError(
            "software organ required interfaces must be provided through declared dependencies",
            {"unreachable_interfaces": unreachable},
        )
    return providers, dependency_closure


def preview_organ_project(assembly: Any, variables: Any) -> dict[str, Any]:
    """Resolve and render one organ assembly without publishing any files."""
    if not isinstance(assembly, dict):
        raise ProjectError("assembly must be an object")
    assembly_id = _required_text(assembly.get("id"), "assembly.id")
    version = _required_text(assembly.get("version"), "assembly.version")
    project_type = str(assembly.get("project_type", "")).strip().casefold()
    if project_type not in PROJECT_TYPES:
        raise ProjectError("assembly.project_type must be generic, static-web, or python")
    if not isinstance(variables, dict):
        raise ProjectError("variables must be an object mapping placeholder names to exact text")

    organs, positions = _prepare_organs(assembly.get("organs"))
    order = _dependency_order(organs, positions)
    interface_providers, dependency_closure = _resolve_interfaces(organs, order)
    by_id = {organ["id"]: organ for organ in organs}

    combined_files: dict[str, str] = {}
    owners: dict[str, str] = {}
    organ_receipts: list[dict[str, Any]] = []
    assembly_variables_used: set[str] = set()
    for organ_id in order:
        organ = by_id[organ_id]
        uses_package_bindings = organ["bindings"] is not None
        render_variables = organ["bindings"] if uses_package_bindings else variables
        try:
            rendered = render_project_template(
                {
                    "id": organ_id,
                    "version": organ["version"],
                    "project_type": project_type,
                    "files": organ["files"],
                },
                render_variables,
                reject_unused_variables=uses_package_bindings,
            )
        except ProjectError as exc:
            raise ProjectError(
                f"software organ {organ_id} could not be rendered: {exc}",
                {"organ_id": organ_id, **exc.details},
            ) from exc

        instance = rendered["template_instance"]
        if not uses_package_bindings:
            assembly_variables_used.update(instance["variables_used"])
        for path, content in rendered["files"].items():
            if path in combined_files:
                raise ProjectError(
                    "software organs cannot claim the same rendered file path",
                    {
                        "rendered_path": path,
                        "first_organ": owners[path],
                        "second_organ": organ_id,
                    },
                )
            combined_files[path] = content
            owners[path] = organ_id
        receipt = {
            "id": organ_id,
            "version": organ["version"],
            "purpose": organ["purpose"],
            "depends_on": organ["depends_on"],
            "dependency_closure": sorted(dependency_closure[organ_id]),
            "provides": organ["provides"],
            "requires": organ["requires"],
            "variables_used": instance["variables_used"],
            "variable_scope": "organ-bindings" if uses_package_bindings else "assembly-variables",
            "rendered_paths": instance["rendered_paths"],
        }
        if organ["package_ref"] is not None:
            receipt.update({
                "package_ref": organ["package_ref"],
                "package_id": organ["package_id"],
                "package_source_path": organ["package_source_path"],
            })
        organ_receipts.append(receipt)

    unused_variables = sorted(set(variables) - assembly_variables_used)
    if unused_variables:
        raise ProjectError(
            "organ assembly variables were supplied but not used",
            {"unused_variables": unused_variables},
        )

    organ_assembly = {
        "truth_status": "DETERMINISTIC_DEPENDENCY_ORDERED_SOFTWARE_ORGAN_ASSEMBLY",
        "assembly_id": assembly_id,
        "assembly_version": version,
        "project_type": project_type,
        "declared_organ_count": len(organs),
        "dependency_order": order,
        "dependency_edges": [
            {"from": dependency, "to": organ["id"]}
            for organ in organs
            for dependency in organ["depends_on"]
        ],
        "interface_providers": [
            {"interface": interface, "organ_id": interface_providers[interface]}
            for interface in sorted(interface_providers)
        ],
        "organs": organ_receipts,
        "file_ownership": [
            {"path": path, "organ_id": owners[path]}
            for path in sorted(owners)
        ],
        "variables_used": sorted(assembly_variables_used),
        "assembly_variables_used": sorted(assembly_variables_used),
        "organ_scoped_bindings_available": True,
        "composition": "disjoint rendered file ownership followed by one project publication",
        "recursive_template_expansion": False,
        "declared_interface_contracts_verified": True,
        "source_interface_conformance_verified": False,
        "semantic_dependency_wiring": False,
        "limitations": [
            "provided/required interface names validate declared organ relationships but do not prove source-level interface conformance",
            "organ dependencies determine deterministic assembly order but do not invent imports or runtime wiring",
            "each rendered file has exactly one organ owner; shared-file merge semantics are not implemented",
            "organ templates remain raw single-pass text substitution and are not parser-aware",
        ],
    }
    return {
        "project_type": project_type,
        "files": combined_files,
        "organ_assembly": organ_assembly,
    }


def assemble_organ_project(
    target: Path,
    assembly: Any,
    variables: Any,
    checks: list[dict[str, Any]] | None = None,
    replace: bool = False,
    publish_mode: str = "grounded-draft",
) -> dict[str, Any]:
    preview = preview_organ_project(assembly, variables)
    result = build_project(
        target=target,
        files=preview["files"],
        project_type=preview["project_type"],
        checks=checks,
        replace=replace,
        publish_mode=publish_mode,
    )
    result["organ_assembly"] = preview["organ_assembly"]
    return result

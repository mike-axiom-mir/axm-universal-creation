from __future__ import annotations

import copy
import json
import re
import tempfile
from pathlib import Path
from typing import Any

from .project import CHECKS, ProjectError, build_project, preview_project_files, validate_project
from .template import PROJECT_TYPES, VARIABLE_NAME_RE, render_project_template


EXECUTABLE_ORGAN_SCHEMA_V1 = "axm.executable-software-organ/v0.1"
EXECUTABLE_ORGAN_SCHEMA = "axm.executable-software-organ/v0.2"
EXECUTABLE_ORGAN_SCHEMAS = {EXECUTABLE_ORGAN_SCHEMA_V1, EXECUTABLE_ORGAN_SCHEMA}
ORGAN_ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
VERSION_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,63}")
INTERFACE_NAME_RE = re.compile(r"[A-Za-z][A-Za-z0-9_.:-]{0,127}")
FIXTURE_CHECK_FIELDS = {
    "project-nonempty": {"type"},
    "file-exists": {"type", "path"},
    "file-absent": {"type", "path"},
    "nonempty": {"type", "path"},
    "contains": {"type", "path", "text"},
    "not-contains": {"type", "path", "text"},
    "line-count": {"type", "path", "minimum", "maximum"},
    "byte-size": {"type", "path", "minimum", "maximum"},
    "sha256": {"type", "path", "sha256"},
    "json-valid": {"type", "path"},
    "json-value": {"type", "path", "json_path", "equals"},
    "file-set": {"type", "files", "mode"},
    "python-compile": {"type", "path"},
    "html-local-links": {"type", "path"},
    "css-local-links": {"type", "path"},
    "javascript-local-imports": {"type", "path"},
}


class ExecutableOrganError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExecutableOrganError(f"{label} must be non-empty text")
    return value.strip()


def _unique_names(value: Any, label: str, pattern: re.Pattern[str], allow_empty: bool = True) -> list[str]:
    if not isinstance(value, list) or (not value and not allow_empty):
        qualifier = "a non-empty list" if not allow_empty else "a list"
        raise ExecutableOrganError(f"{label} must be {qualifier}")
    names: list[str] = []
    for raw in value:
        name = _required_text(raw, f"{label} entry")
        if pattern.fullmatch(name) is None:
            raise ExecutableOrganError(f"invalid {label} entry", {"field": label, "value": name})
        if name in names:
            raise ExecutableOrganError(f"{label} entries must be unique", {"field": label, "duplicate": name})
        names.append(name)
    return names


def _public_package(package: dict[str, Any], include_source: bool) -> dict[str, Any]:
    visible = {key: copy.deepcopy(value) for key, value in package.items() if not key.startswith("_")}
    if not include_source:
        visible.pop("files", None)
        if "fixtures" in visible:
            visible["fixtures"] = [
                {
                    "id": fixture["id"],
                    "project_type": fixture["project_type"],
                    "check_count": len(fixture["checks"]),
                    "expected_paths": sorted(fixture["expected_files"]),
                }
                for fixture in visible["fixtures"]
            ]
    visible["ref"] = package["_ref"]
    visible["source_path"] = package["_source_path"]
    return visible


def _validate_fixtures(
    value: Any,
    *,
    organ_id: str,
    version: str,
    project_types: list[str],
    parameters: list[str],
    files: Any,
) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not value:
        raise ExecutableOrganError("v0.2 package.fixtures must be a non-empty list")
    fixtures: list[dict[str, Any]] = []
    fixture_ids: set[str] = set()
    for position, raw in enumerate(value):
        label = f"package.fixtures[{position}]"
        if not isinstance(raw, dict):
            raise ExecutableOrganError(f"{label} must be an object")
        unexpected = sorted(set(raw) - {"id", "project_type", "bindings", "expected_files", "checks"})
        if unexpected:
            raise ExecutableOrganError(
                f"{label} has unsupported fields",
                {"fixture_position": position, "unexpected_fixture_fields": unexpected},
            )
        fixture_id = _required_text(raw.get("id"), f"{label}.id")
        if ORGAN_ID_RE.fullmatch(fixture_id) is None:
            raise ExecutableOrganError(f"{label}.id is invalid", {"fixture_id": fixture_id})
        if fixture_id in fixture_ids:
            raise ExecutableOrganError("package fixture IDs must be unique", {"duplicate_fixture_id": fixture_id})
        fixture_ids.add(fixture_id)

        project_type = _required_text(raw.get("project_type"), f"{label}.project_type").casefold()
        if project_type not in project_types:
            raise ExecutableOrganError(
                f"{label}.project_type is not supported by the package",
                {"fixture_id": fixture_id, "project_type": project_type, "package_project_types": project_types},
            )
        bindings = raw.get("bindings")
        if not isinstance(bindings, dict):
            raise ExecutableOrganError(f"{label}.bindings must be an object")
        invalid_binding_names = sorted(
            str(name)
            for name in bindings
            if not isinstance(name, str) or VARIABLE_NAME_RE.fullmatch(name) is None
        )
        if invalid_binding_names:
            raise ExecutableOrganError(
                f"{label}.bindings has invalid names",
                {"fixture_id": fixture_id, "invalid_binding_names": invalid_binding_names},
            )
        non_text_bindings = sorted(name for name, binding in bindings.items() if not isinstance(binding, str))
        if non_text_bindings:
            raise ExecutableOrganError(
                f"{label}.bindings values must be exact text",
                {"fixture_id": fixture_id, "non_text_bindings": non_text_bindings},
            )
        supplied = set(bindings)
        declared = set(parameters)
        if supplied != declared:
            raise ExecutableOrganError(
                f"{label}.bindings must exactly match package parameters",
                {
                    "fixture_id": fixture_id,
                    "missing_parameters": sorted(declared - supplied),
                    "unexpected_parameters": sorted(supplied - declared),
                },
            )
        try:
            fixture_rendered = render_project_template(
                {
                    "id": organ_id,
                    "version": version,
                    "project_type": project_type,
                    "files": files,
                },
                bindings,
            )
            preview_project_files(fixture_rendered["files"], project_type=project_type)
        except ProjectError as exc:
            raise ExecutableOrganError(
                f"{label} cannot render a safe project file map: {exc}",
                {"fixture_id": fixture_id, **exc.details},
            ) from exc

        expected_files = raw.get("expected_files")
        try:
            normalized_expected = preview_project_files(expected_files, project_type=project_type)["files"]
        except ProjectError as exc:
            raise ExecutableOrganError(
                f"{label}.expected_files is invalid: {exc}",
                {"fixture_id": fixture_id, **exc.details},
            ) from exc

        checks = raw.get("checks")
        if not isinstance(checks, list) or not checks:
            raise ExecutableOrganError(f"{label}.checks must be a non-empty list")
        normalized_checks: list[dict[str, Any]] = []
        for check_position, check in enumerate(checks):
            if not isinstance(check, dict):
                raise ExecutableOrganError(
                    f"{label}.checks[{check_position}] must be an object",
                    {"fixture_id": fixture_id},
                )
            check_type = str(check.get("type", "")).strip().casefold()
            if check_type not in CHECKS or check_type not in FIXTURE_CHECK_FIELDS:
                raise ExecutableOrganError(
                    f"{label}.checks[{check_position}] has an unsupported deterministic check",
                    {"fixture_id": fixture_id, "check_type": check_type or None},
                )
            unexpected_check_fields = sorted(set(check) - FIXTURE_CHECK_FIELDS[check_type])
            if unexpected_check_fields:
                raise ExecutableOrganError(
                    f"{label}.checks[{check_position}] has unsupported fields",
                    {
                        "fixture_id": fixture_id,
                        "check_type": check_type,
                        "unexpected_check_fields": unexpected_check_fields,
                    },
                )
            normalized_check = copy.deepcopy(check)
            normalized_check["type"] = check_type
            normalized_checks.append(normalized_check)

        fixtures.append({
            "id": fixture_id,
            "project_type": project_type,
            "bindings": copy.deepcopy(bindings),
            "expected_files": normalized_expected,
            "checks": normalized_checks,
        })
    return fixtures


class ExecutableOrganLibrary:
    """Load and resolve exact local executable-organ packages.

    Descriptive anatomy records under ``organs/`` are deliberately not loaded
    here. Only packages under ``executable-organs/`` enter this executable body.
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        self.folder = self.root / "executable-organs"
        self._packages = self._load()

    def _load(self) -> dict[str, dict[str, Any]]:
        packages: dict[str, dict[str, Any]] = {}
        if not self.folder.exists():
            return packages
        for path in sorted(self.folder.glob("*.json")):
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
                package = self._validate(raw, path)
            except (OSError, UnicodeError, json.JSONDecodeError, ProjectError, ExecutableOrganError) as exc:
                if isinstance(exc, ExecutableOrganError):
                    details = exc.details
                elif isinstance(exc, ProjectError):
                    details = exc.details
                else:
                    details = {}
                raise ExecutableOrganError(
                    f"invalid executable organ package {path.name}: {exc}",
                    {"source_path": path.relative_to(self.root).as_posix(), **details},
                ) from exc
            ref = package["_ref"]
            if ref in packages:
                raise ExecutableOrganError(
                    "executable organ package refs must be unique",
                    {
                        "duplicate_ref": ref,
                        "first_source": packages[ref]["_source_path"],
                        "second_source": package["_source_path"],
                    },
                )
            packages[ref] = package
        return packages

    def _validate(self, raw: Any, path: Path) -> dict[str, Any]:
        if not isinstance(raw, dict):
            raise ExecutableOrganError("package must be an object")
        schema = raw.get("schema")
        if schema not in EXECUTABLE_ORGAN_SCHEMAS:
            raise ExecutableOrganError(
                "package schema is unsupported",
                {"expected_schemas": sorted(EXECUTABLE_ORGAN_SCHEMAS), "actual_schema": schema},
            )
        allowed_fields = {
            "schema",
            "id",
            "version",
            "status",
            "purpose",
            "project_types",
            "parameters",
            "provides",
            "requires",
            "files",
            "anatomy_refs",
            "provenance",
            "limitations",
        }
        if schema == EXECUTABLE_ORGAN_SCHEMA:
            allowed_fields.add("fixtures")
        unexpected_fields = sorted(set(raw) - allowed_fields)
        if unexpected_fields:
            raise ExecutableOrganError("package has unsupported fields", {"unexpected_fields": unexpected_fields})
        organ_id = _required_text(raw.get("id"), "package.id")
        version = _required_text(raw.get("version"), "package.version")
        if ORGAN_ID_RE.fullmatch(organ_id) is None:
            raise ExecutableOrganError("package.id is invalid", {"id": organ_id})
        if VERSION_RE.fullmatch(version) is None:
            raise ExecutableOrganError("package.version is invalid", {"version": version})
        if raw.get("status") != "executable":
            raise ExecutableOrganError("package.status must be executable")
        purpose = _required_text(raw.get("purpose"), "package.purpose")

        project_types = _unique_names(raw.get("project_types"), "package.project_types", ORGAN_ID_RE, allow_empty=False)
        unsupported = sorted(set(project_types) - PROJECT_TYPES)
        if unsupported:
            raise ExecutableOrganError("package has unsupported project types", {"unsupported_project_types": unsupported})
        parameters = _unique_names(raw.get("parameters", []), "package.parameters", VARIABLE_NAME_RE)
        provides = _unique_names(raw.get("provides"), "package.provides", INTERFACE_NAME_RE, allow_empty=False)
        requires = _unique_names(raw.get("requires", []), "package.requires", INTERFACE_NAME_RE)
        overlap = sorted(set(provides) & set(requires))
        if overlap:
            raise ExecutableOrganError("package cannot both provide and require the same interface", {"interfaces": overlap})

        anatomy_refs = raw.get("anatomy_refs", [])
        if not isinstance(anatomy_refs, list) or any(not isinstance(item, str) or not item.strip() for item in anatomy_refs):
            raise ExecutableOrganError("package.anatomy_refs must be a list of non-empty anatomy IDs")
        if len(set(anatomy_refs)) != len(anatomy_refs):
            raise ExecutableOrganError("package.anatomy_refs entries must be unique")

        provenance = raw.get("provenance")
        if not isinstance(provenance, dict):
            raise ExecutableOrganError("package.provenance must be an object")
        unexpected_provenance = sorted(set(provenance) - {"kind", "basis"})
        if unexpected_provenance:
            raise ExecutableOrganError(
                "package.provenance has unsupported fields",
                {"unexpected_provenance_fields": unexpected_provenance},
            )
        _required_text(provenance.get("kind"), "package.provenance.kind")
        _required_text(provenance.get("basis"), "package.provenance.basis")

        limitations = raw.get("limitations", [])
        if not isinstance(limitations, list) or any(not isinstance(item, str) or not item.strip() for item in limitations):
            raise ExecutableOrganError("package.limitations must be a list of non-empty text entries")

        rendered = render_project_template(
            {
                "id": organ_id,
                "version": version,
                "project_type": project_types[0],
                "files": raw.get("files"),
            },
            {name: f"axm_parameter_{index}" for index, name in enumerate(parameters)},
        )
        referenced = rendered["template_instance"]["variables_used"]
        if referenced != sorted(parameters):
            raise ExecutableOrganError(
                "package.parameters must exactly match template placeholders",
                {"declared_parameters": sorted(parameters), "template_parameters": referenced},
            )

        fixtures = (
            _validate_fixtures(
                raw.get("fixtures"),
                organ_id=organ_id,
                version=version,
                project_types=project_types,
                parameters=parameters,
                files=raw.get("files"),
            )
            if schema == EXECUTABLE_ORGAN_SCHEMA
            else []
        )

        package = copy.deepcopy(raw)
        package.update({
            "schema": schema,
            "id": organ_id,
            "version": version,
            "purpose": purpose,
            "project_types": project_types,
            "parameters": parameters,
            "provides": provides,
            "requires": requires,
            "anatomy_refs": anatomy_refs,
            "limitations": limitations,
            "_ref": f"{organ_id}@{version}",
            "_source_path": path.relative_to(self.root).as_posix(),
            "_fixtures": fixtures,
        })
        if schema == EXECUTABLE_ORGAN_SCHEMA:
            package["fixtures"] = fixtures
        return package

    def summary(self) -> dict[str, Any]:
        packages = list(self._packages.values())
        return {
            "truth_status": "EXACT_LOCAL_EXECUTABLE_ORGAN_PACKAGES",
            "schema": EXECUTABLE_ORGAN_SCHEMA,
            "supported_schemas": sorted(EXECUTABLE_ORGAN_SCHEMAS),
            "packages": len(packages),
            "packages_by_schema": {
                schema: sum(package["schema"] == schema for package in packages)
                for schema in sorted(EXECUTABLE_ORGAN_SCHEMAS)
            },
            "packages_with_declared_fixtures": sum(bool(package["_fixtures"]) for package in packages),
            "declared_fixtures": sum(len(package["_fixtures"]) for package in packages),
            "package_refs": sorted(self._packages),
            "project_types": sorted({project_type for package in packages for project_type in package["project_types"]}),
            "provided_interfaces": sorted({interface for package in packages for interface in package["provides"]}),
            "descriptive_anatomy_organs_automatically_executable": False,
        }

    def list(self, project_type: str | None = None, provides: str | None = None) -> list[dict[str, Any]]:
        normalized_type = str(project_type).strip().casefold() if project_type else None
        normalized_interface = str(provides).strip() if provides else None
        rows: list[dict[str, Any]] = []
        for ref in sorted(self._packages):
            package = self._packages[ref]
            if normalized_type and normalized_type not in package["project_types"]:
                continue
            if normalized_interface and normalized_interface not in package["provides"]:
                continue
            rows.append(_public_package(package, include_source=False))
        return rows

    def resolve(self, ref: Any, project_type: str | None = None) -> dict[str, Any]:
        exact_ref = _required_text(ref, "organ ref")
        package = self._packages.get(exact_ref)
        if package is None:
            raise ExecutableOrganError(
                "executable organ ref is not installed",
                {"requested_ref": exact_ref, "available_refs": sorted(self._packages)},
            )
        normalized_type = str(project_type).strip().casefold() if project_type else None
        if normalized_type and normalized_type not in package["project_types"]:
            raise ExecutableOrganError(
                "executable organ does not support the assembly project type",
                {
                    "requested_ref": exact_ref,
                    "project_type": normalized_type,
                    "supported_project_types": package["project_types"],
                },
            )
        return copy.deepcopy(package)

    def inspect(self, ref: Any) -> dict[str, Any]:
        return _public_package(self.resolve(ref), include_source=True)

    def test(self, ref: Any) -> dict[str, Any]:
        package = self.resolve(ref)
        if not package["_fixtures"]:
            return {
                "truth_status": "EXECUTABLE_ORGAN_SCHEMA_ONLY_EVIDENCE",
                "ref": package["_ref"],
                "schema": package["schema"],
                "passed": True,
                "fixture_count": 0,
                "fixtures": [],
                "runtime_executed": False,
                "limitations": [
                    "The v0.1 package has no declared fixture contract; only package structure was validated.",
                    "Generated source and runtime behavior were not executed.",
                ],
            }

        fixture_results: list[dict[str, Any]] = []
        for fixture in package["_fixtures"]:
            rendered = render_project_template(
                {
                    "id": package["id"],
                    "version": package["version"],
                    "project_type": fixture["project_type"],
                    "files": package["files"],
                },
                fixture["bindings"],
            )
            rendered_files = rendered["files"]
            with tempfile.TemporaryDirectory(prefix="axm-organ-fixture-") as temp_dir:
                target = Path(temp_dir) / "project"
                build = build_project(
                    target=target,
                    files=rendered_files,
                    project_type=fixture["project_type"],
                    checks=fixture["checks"],
                    publish_mode="grounded-draft",
                )
                validation = validate_project(
                    target,
                    project_type=fixture["project_type"],
                    checks=fixture["checks"],
                    expected_files=fixture["expected_files"],
                )
                expected_paths = sorted(fixture["expected_files"])
                rendered_paths = sorted(rendered_files)
                exact_file_set = {
                    "type": "fixture-exact-file-set",
                    "passed": rendered_paths == expected_paths,
                    "expected": expected_paths,
                    "actual": rendered_paths,
                    "missing": sorted(set(expected_paths) - set(rendered_paths)),
                    "unexpected": sorted(set(rendered_paths) - set(expected_paths)),
                }
                fixture_results.append({
                    "id": fixture["id"],
                    "project_type": fixture["project_type"],
                    "passed": validation["passed"] and exact_file_set["passed"],
                    "bindings": copy.deepcopy(fixture["bindings"]),
                    "template_instance": rendered["template_instance"],
                    "exact_file_set": exact_file_set,
                    "validation": validation,
                    "build_creation_status": build["creation_status"],
                    "runtime_executed": False,
                })
        return {
            "truth_status": "DECLARED_EXECUTABLE_ORGAN_FIXTURES_EXECUTED",
            "ref": package["_ref"],
            "schema": package["schema"],
            "passed": all(fixture["passed"] for fixture in fixture_results),
            "fixture_count": len(fixture_results),
            "fixtures": fixture_results,
            "runtime_executed": False,
            "limitations": [
                "Only declared deterministic fixtures were rendered and checked in disposable project space.",
                "Generated source and runtime behavior were not executed.",
                "A passing fixture does not prove semantic conformance for untested bindings or environments.",
            ],
        }


def resolve_organ_assembly(root: Path, assembly: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    if not isinstance(assembly, dict):
        raise ExecutableOrganError("assembly must be an object")
    raw_organs = assembly.get("organs")
    if not isinstance(raw_organs, list):
        raise ExecutableOrganError("assembly.organs must be a list")
    project_type = str(assembly.get("project_type", "")).strip().casefold()
    library = ExecutableOrganLibrary(root)
    resolved_organs: list[Any] = []
    package_receipts: list[dict[str, Any]] = []
    inline_instance_ids: list[str] = []
    allowed_reference_fields = {"instance_id", "ref", "depends_on", "bindings"}

    for position, raw in enumerate(raw_organs):
        if not isinstance(raw, dict) or "ref" not in raw:
            resolved_organs.append(copy.deepcopy(raw))
            if isinstance(raw, dict) and isinstance(raw.get("id"), str):
                inline_instance_ids.append(raw["id"])
            continue
        unexpected = sorted(set(raw) - allowed_reference_fields)
        if unexpected:
            raise ExecutableOrganError(
                "referenced organ instances cannot override package source or contracts",
                {"position": position, "unexpected_fields": unexpected},
            )
        instance_id = _required_text(raw.get("instance_id"), f"assembly.organs[{position}].instance_id")
        package = library.resolve(raw.get("ref"), project_type=project_type)
        bindings = raw.get("bindings", {})
        if not isinstance(bindings, dict):
            raise ExecutableOrganError("referenced organ bindings must be an object", {"instance_id": instance_id})
        invalid_binding_names = sorted(
            str(name)
            for name in bindings
            if not isinstance(name, str) or VARIABLE_NAME_RE.fullmatch(name) is None
        )
        if invalid_binding_names:
            raise ExecutableOrganError(
                "referenced organ binding names are invalid",
                {"instance_id": instance_id, "invalid_binding_names": invalid_binding_names},
            )
        non_text_bindings = sorted(name for name, value in bindings.items() if not isinstance(value, str))
        if non_text_bindings:
            raise ExecutableOrganError(
                "referenced organ binding values must be exact text",
                {"instance_id": instance_id, "non_text_bindings": non_text_bindings},
            )
        supplied_parameters = set(bindings)
        declared_parameters = set(package["parameters"])
        if supplied_parameters != declared_parameters:
            raise ExecutableOrganError(
                "referenced organ bindings must exactly match package parameters",
                {
                    "instance_id": instance_id,
                    "ref": package["_ref"],
                    "missing_parameters": sorted(declared_parameters - supplied_parameters),
                    "unexpected_parameters": sorted(supplied_parameters - declared_parameters),
                },
            )
        resolved_organs.append({
            "id": instance_id,
            "version": package["version"],
            "purpose": package["purpose"],
            "depends_on": copy.deepcopy(raw.get("depends_on", [])),
            "provides": copy.deepcopy(package["provides"]),
            "requires": copy.deepcopy(package["requires"]),
            "files": copy.deepcopy(package["files"]),
            "bindings": copy.deepcopy(bindings),
            "package_ref": package["_ref"],
            "package_id": package["id"],
            "package_source_path": package["_source_path"],
        })
        package_receipts.append({
            "instance_id": instance_id,
            "ref": package["_ref"],
            "package_id": package["id"],
            "version": package["version"],
            "source_path": package["_source_path"],
            "parameters_bound": sorted(bindings),
            "provides": copy.deepcopy(package["provides"]),
            "requires": copy.deepcopy(package["requires"]),
        })

    resolved = copy.deepcopy(assembly)
    resolved["organs"] = resolved_organs
    return resolved, {
        "truth_status": "EXACT_EXECUTABLE_ORGAN_REFERENCE_RESOLUTION",
        "schema": EXECUTABLE_ORGAN_SCHEMA,
        "referenced_packages": package_receipts,
        "referenced_package_count": len(package_receipts),
        "inline_instance_ids": inline_instance_ids,
        "inline_organs_remain_explicit_request_source": True,
        "descriptive_anatomy_organs_promoted": False,
        "automatic_or_fuzzy_selection": False,
    }

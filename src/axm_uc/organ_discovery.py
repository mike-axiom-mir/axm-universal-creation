from __future__ import annotations

import copy
import re
from pathlib import Path
from typing import Any

from .organ_library import (
    INTERFACE_NAME_RE,
    ORGAN_ID_RE,
    VERSION_RE,
    ExecutableOrganLibrary,
)
from .template import PROJECT_TYPES, VARIABLE_NAME_RE


ORGAN_GOAL_SCHEMA = "axm.interface-organ-goal/v0.1"
ORGAN_DISCOVERY_SCHEMA = "axm.interface-organ-discovery/v0.1"
MAX_DISCOVERY_STATES = 10_000
INSTANCE_SLUG_RE = re.compile(r"[^a-z0-9]+")


class OrganDiscoveryError(RuntimeError):
    def __init__(self, message: str, details: dict[str, Any] | None = None):
        super().__init__(message)
        self.details = details or {}


def _required_text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise OrganDiscoveryError(f"{label} must be non-empty text")
    return value.strip()


def _required_interfaces(value: Any) -> list[str]:
    if not isinstance(value, list) or not value:
        raise OrganDiscoveryError("organ_goal.required_interfaces must be a non-empty list")
    result: list[str] = []
    for raw in value:
        interface = _required_text(raw, "organ_goal.required_interfaces entry")
        if INTERFACE_NAME_RE.fullmatch(interface) is None:
            raise OrganDiscoveryError(
                "organ_goal.required_interfaces entries must be exact interface names",
                {"interface": interface},
            )
        if interface in result:
            raise OrganDiscoveryError(
                "organ_goal.required_interfaces entries must be unique",
                {"duplicate_interface": interface},
            )
        result.append(interface)
    return result


def _bindings(value: Any) -> dict[str, dict[str, str]]:
    if not isinstance(value, dict):
        raise OrganDiscoveryError("organ_goal.bindings must be an object keyed by provided interface")
    result: dict[str, dict[str, str]] = {}
    for raw_interface, raw_values in value.items():
        interface = _required_text(raw_interface, "organ_goal.bindings interface")
        if INTERFACE_NAME_RE.fullmatch(interface) is None:
            raise OrganDiscoveryError(
                "organ_goal.bindings keys must be exact interface names",
                {"interface": interface},
            )
        if not isinstance(raw_values, dict):
            raise OrganDiscoveryError(
                "organ_goal.bindings values must be parameter objects",
                {"interface": interface},
            )
        values: dict[str, str] = {}
        for raw_name, raw_value in raw_values.items():
            name = _required_text(raw_name, f"organ_goal.bindings.{interface} parameter")
            if VARIABLE_NAME_RE.fullmatch(name) is None:
                raise OrganDiscoveryError(
                    "organ_goal binding parameter names are invalid",
                    {"interface": interface, "parameter": name},
                )
            if not isinstance(raw_value, str):
                raise OrganDiscoveryError(
                    "organ_goal binding parameter values must be exact text",
                    {"interface": interface, "parameter": name},
                )
            values[name] = raw_value
        result[interface] = values
    return result


def _normalize_goal(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise OrganDiscoveryError("organ_goal must be an object")
    allowed = {"schema", "id", "version", "project_type", "required_interfaces", "bindings"}
    unexpected = sorted(set(value) - allowed)
    if unexpected:
        raise OrganDiscoveryError(
            "organ_goal has unsupported fields",
            {"unexpected_fields": unexpected},
        )
    schema = value.get("schema", ORGAN_GOAL_SCHEMA)
    if schema != ORGAN_GOAL_SCHEMA:
        raise OrganDiscoveryError(
            "organ_goal schema is unsupported",
            {"expected_schema": ORGAN_GOAL_SCHEMA, "actual_schema": schema},
        )
    goal_id = _required_text(value.get("id"), "organ_goal.id")
    version = _required_text(value.get("version"), "organ_goal.version")
    if ORGAN_ID_RE.fullmatch(goal_id) is None:
        raise OrganDiscoveryError("organ_goal.id is invalid", {"id": goal_id})
    if VERSION_RE.fullmatch(version) is None:
        raise OrganDiscoveryError("organ_goal.version is invalid", {"version": version})
    project_type = _required_text(value.get("project_type"), "organ_goal.project_type").casefold()
    if project_type not in PROJECT_TYPES:
        raise OrganDiscoveryError(
            "organ_goal.project_type is unsupported",
            {"project_type": project_type, "supported_project_types": sorted(PROJECT_TYPES)},
        )
    return {
        "schema": ORGAN_GOAL_SCHEMA,
        "id": goal_id,
        "version": version,
        "project_type": project_type,
        "required_interfaces": _required_interfaces(value.get("required_interfaces")),
        "bindings": _bindings(value.get("bindings", {})),
    }


def _provider_map(
    selected_refs: frozenset[str],
    packages: dict[str, dict[str, Any]],
) -> dict[str, str] | None:
    providers: dict[str, str] = {}
    for ref in sorted(selected_refs):
        for interface in packages[ref]["provides"]:
            if interface in providers and providers[interface] != ref:
                return None
            providers[interface] = ref
    return providers


def _dependency_map(
    selected_refs: frozenset[str],
    packages: dict[str, dict[str, Any]],
    providers: dict[str, str],
) -> dict[str, set[str]]:
    return {
        ref: {
            providers[interface]
            for interface in packages[ref]["requires"]
            if providers[interface] != ref
        }
        for ref in selected_refs
    }


def _dependency_order(dependencies: dict[str, set[str]]) -> list[str] | None:
    pending = {ref: set(required) for ref, required in dependencies.items()}
    ordered: list[str] = []
    while pending:
        ready = sorted(ref for ref, required in pending.items() if not required)
        if not ready:
            return None
        for ref in ready:
            ordered.append(ref)
            del pending[ref]
            for required in pending.values():
                required.discard(ref)
    return ordered


def _reachable(start: str, target: str, dependencies: dict[str, set[str]]) -> bool:
    pending = list(dependencies.get(start, set()))
    visited: set[str] = set()
    while pending:
        current = pending.pop()
        if current == target:
            return True
        if current in visited:
            continue
        visited.add(current)
        pending.extend(dependencies.get(current, set()))
    return False


def _reduced_dependencies(dependencies: dict[str, set[str]]) -> dict[str, set[str]]:
    reduced: dict[str, set[str]] = {}
    for ref, direct in dependencies.items():
        retained = set(direct)
        for candidate in direct:
            if any(
                other != candidate and _reachable(other, candidate, dependencies)
                for other in direct
            ):
                retained.discard(candidate)
        reduced[ref] = retained
    return reduced


def _instance_ids(order: list[str], packages: dict[str, dict[str, Any]]) -> dict[str, str]:
    result: dict[str, str] = {}
    used: set[str] = set()
    for ref in order:
        tail = packages[ref]["id"].split(".")[-1].casefold()
        base = INSTANCE_SLUG_RE.sub("-", tail).strip("-") or "organ"
        base = f"{base}-organ"
        instance_id = base
        suffix = 2
        while instance_id in used:
            instance_id = f"{base}-{suffix}"
            suffix += 1
        used.add(instance_id)
        result[ref] = instance_id
    return result


def _candidate_receipt(
    selected_refs: frozenset[str],
    packages: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    providers = _provider_map(selected_refs, packages)
    if providers is None:
        return None
    dependencies = _dependency_map(selected_refs, packages, providers)
    order = _dependency_order(dependencies)
    if order is None:
        return None
    reduced = _reduced_dependencies(dependencies)
    return {
        "package_refs": order,
        "package_count": len(order),
        "provided_interfaces": sorted(providers),
        "dependency_edges": [
            {"from": dependency, "to": ref}
            for ref in order
            for dependency in sorted(reduced[ref])
        ],
    }


def _missing_contracts(
    missing_interfaces: set[str],
    goal: dict[str, Any],
    packages: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    contracts: list[dict[str, Any]] = []
    for interface in sorted(missing_interfaces):
        required_by = [
            package["ref"]
            for package in packages.values()
            if interface in package["requires"]
        ]
        if interface in goal["required_interfaces"]:
            required_by.insert(0, "creation-goal")
        contracts.append({
            "schema": "axm.missing-executable-organ-contract/v0.1",
            "kind": "organ",
            "project_type": goal["project_type"],
            "must_provide": [interface],
            "required_by": required_by,
            "source_and_tests_required": True,
            "suggested_forge_kind": "organ",
            "automatic_source_invention": False,
            "admission_authority": "NONE",
        })
    return contracts


def _bind_unique_solution(
    goal: dict[str, Any],
    candidate: dict[str, Any],
    packages: dict[str, dict[str, Any]],
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    order = candidate["package_refs"]
    selected_refs = frozenset(order)
    providers = _provider_map(selected_refs, packages)
    if providers is None:
        return None, [{"reason": "selected packages expose duplicate interface providers"}]
    dependencies = _reduced_dependencies(_dependency_map(selected_refs, packages, providers))
    instance_ids = _instance_ids(order, packages)
    used_binding_namespaces: set[str] = set()
    issues: list[dict[str, Any]] = []
    organs: list[dict[str, Any]] = []
    for ref in order:
        package = packages[ref]
        matching_namespaces = sorted(set(package["provides"]) & set(goal["bindings"]))
        parameters = set(package["parameters"])
        if parameters and len(matching_namespaces) != 1:
            issues.append({
                "ref": ref,
                "provided_interfaces": package["provides"],
                "required_parameters": sorted(parameters),
                "matching_binding_namespaces": matching_namespaces,
                "reason": "a parameterized selected organ requires exactly one binding namespace keyed by one interface it provides",
            })
            continue
        if not parameters and len(matching_namespaces) > 1:
            issues.append({
                "ref": ref,
                "provided_interfaces": package["provides"],
                "matching_binding_namespaces": matching_namespaces,
                "reason": "an unparameterized selected organ may use at most one empty binding namespace",
            })
            continue
        namespace = matching_namespaces[0] if matching_namespaces else None
        supplied = goal["bindings"].get(namespace, {}) if namespace else {}
        missing_parameters = sorted(parameters - set(supplied))
        unexpected_parameters = sorted(set(supplied) - parameters)
        if missing_parameters or unexpected_parameters:
            issues.append({
                "ref": ref,
                "binding_namespace": namespace,
                "missing_parameters": missing_parameters,
                "unexpected_parameters": unexpected_parameters,
                "reason": "binding parameters must exactly match the selected organ package contract",
            })
            continue
        if namespace is not None:
            used_binding_namespaces.add(namespace)
        organs.append({
            "instance_id": instance_ids[ref],
            "ref": ref,
            "depends_on": [instance_ids[item] for item in sorted(dependencies[ref])],
            "bindings": copy.deepcopy(supplied),
        })
    unused_namespaces = sorted(set(goal["bindings"]) - used_binding_namespaces)
    if unused_namespaces:
        issues.append({
            "unused_binding_namespaces": unused_namespaces,
            "reason": "binding namespaces must belong to exactly one selected organ provider",
        })
    if issues:
        return None, issues
    return {
        "id": goal["id"],
        "version": goal["version"],
        "project_type": goal["project_type"],
        "organs": organs,
    }, []


def discover_interface_assembly(root: Path, raw_goal: Any) -> dict[str, Any]:
    goal = _normalize_goal(raw_goal)
    library = ExecutableOrganLibrary(root)
    compatible = library.list(project_type=goal["project_type"])
    packages = {str(package["ref"]): package for package in compatible}
    provider_index: dict[str, list[str]] = {}
    for ref, package in packages.items():
        for interface in package["provides"]:
            provider_index.setdefault(interface, []).append(ref)
    for refs in provider_index.values():
        refs.sort()

    states = 0
    search_bound_reached = False
    visited: set[frozenset[str]] = set()
    solution_sets: set[frozenset[str]] = set()
    missing_interfaces: set[str] = set()
    rejected_collisions = 0
    rejected_cycles = 0

    def explore(selected_refs: frozenset[str]) -> None:
        nonlocal states, search_bound_reached, rejected_collisions, rejected_cycles
        if selected_refs in visited or search_bound_reached:
            return
        if states >= MAX_DISCOVERY_STATES:
            search_bound_reached = True
            return
        states += 1
        visited.add(selected_refs)
        providers = _provider_map(selected_refs, packages)
        if providers is None:
            rejected_collisions += 1
            return
        obligations = set(goal["required_interfaces"])
        for ref in selected_refs:
            obligations.update(packages[ref]["requires"])
        unresolved = sorted(obligations - set(providers))
        if not unresolved:
            dependencies = _dependency_map(selected_refs, packages, providers)
            if _dependency_order(dependencies) is None:
                rejected_cycles += 1
                return
            solution_sets.add(selected_refs)
            return
        interface = unresolved[0]
        candidates = provider_index.get(interface, [])
        if not candidates:
            missing_interfaces.add(interface)
            return
        for ref in candidates:
            explore(frozenset({*selected_refs, ref}))

    explore(frozenset())
    base = {
        "schema": ORGAN_DISCOVERY_SCHEMA,
        "goal": copy.deepcopy(goal),
        "project_type": goal["project_type"],
        "required_interfaces": copy.deepcopy(goal["required_interfaces"]),
        "compatible_package_count": len(packages),
        "compatible_package_refs": sorted(packages),
        "search": {
            "strategy": "bounded exact interface-provider constraint search",
            "states_observed": states,
            "maximum_states": MAX_DISCOVERY_STATES,
            "search_bound_reached": search_bound_reached,
            "rejected_provider_collisions": rejected_collisions,
            "rejected_dependency_cycles": rejected_cycles,
        },
        "automatic_or_fuzzy_selection": False,
        "semantic_source_invented": False,
        "source_interface_conformance_proven": False,
        "runtime_wiring_invented": False,
        "selection_authority": "NONE",
        "admission_authority": "NONE",
    }
    if search_bound_reached:
        return {
            **base,
            "status": "HOLD_ORGAN_DISCOVERY_SEARCH_BOUND",
            "truth_status": "DETERMINISTIC_BOUNDED_SEARCH_HOLD",
            "hold_reason": "interface-provider search reached its explicit state bound",
            "candidate_assemblies": [],
            "assembly": None,
        }

    receipts = [
        receipt
        for selected_refs in solution_sets
        if (receipt := _candidate_receipt(selected_refs, packages)) is not None
    ]
    if receipts:
        minimum = min(receipt["package_count"] for receipt in receipts)
        candidates = sorted(
            (receipt for receipt in receipts if receipt["package_count"] == minimum),
            key=lambda item: item["package_refs"],
        )
    else:
        candidates = []
    if len(candidates) > 1:
        return {
            **base,
            "status": "HOLD_AMBIGUOUS_ORGAN_ASSEMBLY",
            "truth_status": "DETERMINISTIC_AMBIGUITY_HOLD",
            "hold_reason": "more than one equally small complete exact-interface assembly exists",
            "candidate_assemblies": candidates,
            "assembly": None,
        }
    if not candidates:
        contracts = _missing_contracts(missing_interfaces, goal, packages)
        if contracts:
            return {
                **base,
                "status": "HOLD_MISSING_ORGAN_INTERFACE",
                "truth_status": "DETERMINISTIC_MISSING_INTERFACE_HOLD",
                "hold_reason": "one or more required interfaces have no compatible executable-organ provider",
                "missing_interfaces": sorted(missing_interfaces),
                "missing_unit_contracts": contracts,
                "candidate_assemblies": [],
                "assembly": None,
            }
        return {
            **base,
            "status": "HOLD_NO_COMPLETE_ORGAN_ASSEMBLY",
            "truth_status": "DETERMINISTIC_INCOMPLETE_ASSEMBLY_HOLD",
            "hold_reason": "installed exact interface contracts cannot form an acyclic collision-free assembly",
            "candidate_assemblies": [],
            "assembly": None,
        }

    selected = candidates[0]
    assembly, binding_issues = _bind_unique_solution(goal, selected, packages)
    if assembly is None:
        return {
            **base,
            "status": "HOLD_ORGAN_BINDING_CONTRACT",
            "truth_status": "DETERMINISTIC_BINDING_HOLD",
            "hold_reason": "the unique exact assembly is known but its parameter bindings are incomplete or ambiguous",
            "candidate_assemblies": candidates,
            "selected_candidate": selected,
            "binding_issues": binding_issues,
            "assembly": None,
        }
    return {
        **base,
        "status": "READY_EXACT_INTERFACE_ASSEMBLY",
        "truth_status": "DETERMINISTIC_EXACT_INTERFACE_ASSEMBLY",
        "hold_reason": None,
        "candidate_assemblies": candidates,
        "selected_candidate": selected,
        "assembly": assembly,
        "variables": {},
        "selection_basis": "one uniquely smallest acyclic collision-free package set satisfies the requested and transitive exact interface contracts",
        "selection_is_semantic_proof": False,
    }


def organ_discovery_summary() -> dict[str, Any]:
    return {
        "schema": ORGAN_DISCOVERY_SCHEMA,
        "goal_schema": ORGAN_GOAL_SCHEMA,
        "strategy": "bounded exact interface-provider constraint search",
        "maximum_search_states": MAX_DISCOVERY_STATES,
        "unique_minimum_complete_assembly_may_be_selected": True,
        "ambiguous_minimum_assemblies_are_held": True,
        "missing_interfaces_emit_organ_contracts": True,
        "bindings_remain_explicit_input": True,
        "fuzzy_or_semantic_package_selection": False,
        "source_interface_conformance_proven": False,
        "runtime_wiring_invention": False,
        "automatic_forge_or_admission": False,
    }

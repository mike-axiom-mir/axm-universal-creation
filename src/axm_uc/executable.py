from __future__ import annotations

from typing import Any

from .capabilities import CapabilityStore
from .registry import Registry
from .topology import KernelTopology

VALID_ROLES = {"implements", "supports", "uses"}


class ExecutableAnatomy:
    """Map explicit live-capability declarations onto the broad anatomy.

    This layer never infers implementation from lexical similarity. A master
    record counts as live-backed only when a live capability explicitly declares
    an `anatomy_refs` entry with role `implements` and the referenced master ID
    exists. Other roles remain visible but do not count as implementation proof.
    """

    def __init__(self, registry: Registry, capabilities: CapabilityStore, topology: KernelTopology):
        self.registry = registry
        self.capabilities = capabilities
        self.topology = topology
        self.master_index = {str(row.get("id")): row for row in registry.master_records() if row.get("id")}
        self.bindings = self._collect_bindings()

    def _collect_bindings(self) -> list[dict[str, Any]]:
        rows: list[dict[str, Any]] = []
        for capability in self.capabilities.live():
            capability_id = str(capability.get("id"))
            refs = capability.get("anatomy_refs")
            if not isinstance(refs, list):
                continue
            for raw in refs:
                if not isinstance(raw, dict):
                    rows.append({
                        "capability_id": capability_id,
                        "resolved": False,
                        "role": "invalid",
                        "reason": "anatomy ref is not an object",
                    })
                    continue
                master_id = str(raw.get("id", "")).strip()
                role = str(raw.get("role", "")).strip().casefold()
                basis = raw.get("basis")
                master = self.master_index.get(master_id)
                resolved = master is not None and role in VALID_ROLES and isinstance(basis, str) and bool(basis.strip())
                row: dict[str, Any] = {
                    "capability_id": capability_id,
                    "master_id": master_id,
                    "role": role,
                    "basis": basis,
                    "resolved": resolved,
                }
                if master is not None:
                    row.update({
                        "master_name": master.get("name"),
                        "master_level": master.get("level"),
                        "master_domain": master.get("domain"),
                    })
                    mapping = self.topology.mapping_for_master(master_id, include_suggestions=False)
                    if mapping.get("traversable") is True:
                        row["core_id"] = mapping.get("core_id")
                        row["core_name"] = mapping.get("core_name")
                if not resolved:
                    if master is None:
                        row["reason"] = "referenced master anatomy ID does not exist"
                    elif role not in VALID_ROLES:
                        row["reason"] = "role must be implements, supports, or uses"
                    else:
                        row["reason"] = "binding requires a non-empty inspectable basis"
                rows.append(row)
        return rows

    def summary(self) -> dict[str, Any]:
        live = self.capabilities.live()
        resolved = [row for row in self.bindings if row.get("resolved") is True]
        implemented = [row for row in resolved if row.get("role") == "implements"]
        implemented_master = {str(row["master_id"]) for row in implemented}
        implemented_core = {str(row["core_id"]) for row in implemented if row.get("core_id")}
        bound_caps = {str(row["capability_id"]) for row in resolved}
        by_level: dict[str, int] = {}
        for master_id in implemented_master:
            level = str(self.master_index[master_id].get("level", "unknown"))
            by_level[level] = by_level.get(level, 0) + 1
        return {
            "truth_status": "EXPLICIT_LIVE_CAPABILITY_BINDINGS",
            "rule": "only explicit resolved anatomy_refs with role=implements count as live-backed anatomy",
            "master_records": len(self.master_index),
            "live_capabilities": len(live),
            "declared_bindings": len(self.bindings),
            "resolved_bindings": len(resolved),
            "unresolved_bindings": len(self.bindings) - len(resolved),
            "implemented_master_records": len(implemented_master),
            "implemented_master_by_level": by_level,
            "implemented_core_records_via_exact_crosswalk": len(implemented_core),
            "live_capabilities_with_anatomy_binding": len(bound_caps),
            "live_capabilities_without_anatomy_binding": sorted(
                str(cap.get("id")) for cap in live if str(cap.get("id")) not in bound_caps
            ),
        }

    def for_master(self, master_id: str) -> dict[str, Any]:
        master_id = str(master_id)
        master = self.master_index.get(master_id)
        if master is None:
            raise KeyError(f"unknown master record: {master_id}")
        bindings = [row for row in self.bindings if row.get("master_id") == master_id]
        implemented_by = sorted(
            str(row["capability_id"])
            for row in bindings
            if row.get("resolved") is True and row.get("role") == "implements"
        )
        return {
            "truth_status": "EXPLICIT_LIVE_CAPABILITY_BINDINGS",
            "master": {
                "id": master_id,
                "name": master.get("name"),
                "level": master.get("level"),
                "domain": master.get("domain"),
            },
            "status": "live-backed" if implemented_by else "definition-only",
            "implemented_by": implemented_by,
            "bindings": bindings,
            "kernel_mapping": self.topology.mapping_for_master(master_id, include_suggestions=False),
        }

    def for_core(self, core_id: str) -> dict[str, Any]:
        core_id = str(core_id)
        core = self.topology.core_index.get(core_id)
        if core is None:
            raise KeyError(f"unknown core record: {core_id}")
        masters = self.topology.master_matches_for_core(core_id)
        master_views = [self.for_master(str(row["id"])) for row in masters]
        implemented_by = sorted({cap for view in master_views for cap in view["implemented_by"]})
        return {
            "truth_status": "EXPLICIT_LIVE_CAPABILITY_BINDINGS",
            "core": {
                "id": core_id,
                "name": core.get("name"),
                "level": core.get("level"),
            },
            "status": "live-backed-via-master-crosswalk" if implemented_by else "kernel-definition-only",
            "implemented_by": implemented_by,
            "master_views": master_views,
        }

    def for_selected(self, selected: dict[str, list[dict[str, Any]]]) -> dict[str, Any]:
        rows: list[dict[str, Any]] = []
        for level in ("organ", "component", "atom"):
            for hit in selected.get(level, []):
                master_id = str(hit.get("id"))
                view = self.for_master(master_id)
                if view["bindings"]:
                    rows.append({
                        "master_id": master_id,
                        "master_name": view["master"]["name"],
                        "master_level": view["master"]["level"],
                        "status": view["status"],
                        "implemented_by": view["implemented_by"],
                        "bindings": view["bindings"],
                    })
        return {
            "truth_status": "EXPLICIT_LIVE_CAPABILITY_BINDINGS",
            "selected_records_with_declared_binding": rows,
        }

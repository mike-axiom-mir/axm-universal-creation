"""Semantic atom deduplication for retained creation parts.

Exact variants remain reproducible evidence, but only meaningful structural,
material-family, behavior or assembly changes enlarge the reusable atom library.
"""
from __future__ import annotations

import hashlib
import json
import re


IDENTITY_KEYS = {
    "author", "id", "license", "name", "source", "tags", "ver", "version"
}
APPEARANCE_KEYS = {
    "albedo", "basecolor", "color", "colour", "diffuse", "effectcolor",
    "emissioncolor", "palette", "tint"
}
MATERIAL_KEYS = {"appearance", "material", "materials"}


def _token(value):
    return re.sub(r"[^a-z0-9]", "", value.lower()) if isinstance(value, str) else value


def _digest(value):
    body = json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    return hashlib.sha256(body).hexdigest()


def _normalized(value, *, omit_material=False, dependency_atoms=None):
    dependency_atoms = {} if dependency_atoms is None else dependency_atoms
    if isinstance(value, dict):
        if set(value) == {"$instance"} and isinstance(value["$instance"], dict):
            ref = value["$instance"]
            task = ref.get("task")
            return {
                "$atom": dependency_atoms.get(task, task),
                "overrides": _normalized(ref.get("overrides", {}), omit_material=omit_material,
                                         dependency_atoms=dependency_atoms),
                "placement": _normalized(ref.get("placement", {}), omit_material=omit_material,
                                         dependency_atoms=dependency_atoms),
            }
        if set(value) == {"$task"} and isinstance(value["$task"], str):
            task = value["$task"]
            return {"$atom": dependency_atoms.get(task, task)}
        if set(value) == {"$asset"} and isinstance(value["$asset"], dict):
            ref = value["$asset"]
            task = ref.get("task")
            return {"$atom": dependency_atoms.get(task, task), "key": ref.get("key")}
        result = {}
        for key in sorted(value):
            token = _token(key)
            if token in IDENTITY_KEYS or token in APPEARANCE_KEYS:
                continue
            if omit_material and token in MATERIAL_KEYS:
                continue
            result[key] = _normalized(value[key], omit_material=omit_material,
                                      dependency_atoms=dependency_atoms)
        return result
    if isinstance(value, list):
        return [_normalized(item, omit_material=omit_material,
                            dependency_atoms=dependency_atoms) for item in value]
    return value


def _appearance_values(value, path=()):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if _token(key) in APPEARANCE_KEYS:
                found.append({"path": list(path + (key,)), "value": child})
            else:
                found.extend(_appearance_values(child, path + (key,)))
    elif isinstance(value, list):
        for index, child in enumerate(value):
            found.extend(_appearance_values(child, path + (index,)))
    return found


def _material_families(value):
    found = []
    if isinstance(value, dict):
        for key, child in value.items():
            if _token(key) in MATERIAL_KEYS and isinstance(child, (dict, list)):
                values = child if isinstance(child, list) else [child]
                found.extend(_digest(_normalized(item)) for item in values)
            else:
                found.extend(_material_families(child))
    elif isinstance(value, list):
        for child in value:
            found.extend(_material_families(child))
    return sorted(set(found))


def classify_creator_atoms(plan):
    """Group successful plan tasks by reusable semantics, not cosmetic variants."""
    tasks = list(plan["tasks"])
    pending = {task["id"]: task for task in tasks}
    classified = {}
    while pending:
        ready = [task for task in tasks if task["id"] in pending
                 and set(task["dependencies"]) <= set(classified)]
        if not ready:
            raise ValueError("atom classification requires an acyclic declared task graph")
        for task in ready:
            request = task["request"]
            operation = request["operation"]
            dependencies = {name: classified[name]["atom_signature"] for name in task["dependencies"]}
            if operation == "create_3d":
                kind = "geometry"
                semantic = {
                    "operation": operation,
                    "socket": request.get("socket"),
                    "anchor": request.get("anchor"),
                    "spec": _normalized(request.get("spec"), omit_material=True),
                }
            elif operation == "save_assembly":
                kind = "assembly"
                semantic = _normalized(request, omit_material=True, dependency_atoms=dependencies)
            elif operation == "create_material":
                kind = "material-family"
                semantic = _normalized(request, dependency_atoms=dependencies)
            elif operation == "create_effect":
                kind = "effect-topology"
                semantic = _normalized(request, dependency_atoms=dependencies)
            else:
                kind = "composition"
                semantic = _normalized(request, dependency_atoms=dependencies)
            classified[task["id"]] = {
                "task": task["id"],
                "kind": kind,
                "atom_signature": _digest(semantic),
                "exact_variant_digest": _digest(request),
                "material_family_signatures": _material_families(request),
                "appearance_overrides": _appearance_values(request),
            }
            pending.pop(task["id"])

    canonical = {}
    records = []
    for task in tasks:
        record = classified[task["id"]]
        signature = record["atom_signature"]
        first = canonical.setdefault(signature, task["id"])
        records.append({
            **record,
            "novel_atom": first == task["id"],
            "canonical_task": first,
            "duplicate_of": None if first == task["id"] else first,
            "variant_not_growth": first != task["id"],
        })

    grouped = []
    for signature in dict.fromkeys(record["atom_signature"] for record in records):
        members = [record for record in records if record["atom_signature"] == signature]
        grouped.append({
            "signature": signature,
            "kind": members[0]["kind"],
            "canonical_task": members[0]["canonical_task"],
            "tasks": [member["task"] for member in members],
            "exact_variants": sorted({member["exact_variant_digest"] for member in members}),
        })
    appearances = sorted({signature for record in records
                          for signature in record["material_family_signatures"]})
    return {
        "schema": "axm.creator-atom-library/v1",
        "deduplication": "SEMANTIC_STRUCTURE_WITH_APPEARANCE_OVERRIDES",
        "atoms": grouped,
        "appearance_atoms": appearances,
        "tasks": records,
        "counts": {
            "successful_parts": len(records),
            "novel_atoms": len(grouped),
            "deduplicated_variants": len(records) - len(grouped),
            "appearance_families": len(appearances),
        },
        "truth": (
            "Identity labels and color/tint/palette values do not create new atoms. Exact variants remain "
            "reproducible in the registry, but only semantic geometry, topology, attachment, behavior, "
            "material-family, effect-topology or assembly changes enlarge this atom catalog."
        ),
    }

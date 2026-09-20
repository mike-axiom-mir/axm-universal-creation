from __future__ import annotations

import base64
import hashlib
import json
from copy import deepcopy
from typing import Any


FORMAT = "axm-neutral-compute-runtime"
VERSION = "0.1"


class NeutralComputeError(RuntimeError):
    pass


def _clone(value: Any) -> Any:
    return deepcopy(value)


def canonical_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise NeutralComputeError("value is not finite canonical JSON") from exc


def hash_canonical(value: Any) -> str:
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def hash_bytes(value: bytes | bytearray | memoryview) -> str:
    return hashlib.sha256(bytes(value)).hexdigest()


def _seal(body: dict[str, Any], field: str) -> dict[str, Any]:
    value = _clone(body)
    value[field] = hash_canonical(body)
    return value


def _verify_seal(value: Any, field: str) -> bool:
    if not isinstance(value, dict) or not isinstance(value.get(field), str):
        return False
    body = _clone(value)
    claimed = body.pop(field)
    return claimed == hash_canonical(body)


def _hold(status: str, **extra: Any) -> dict[str, Any]:
    return {"status": status, **extra}


def selector_matches(pattern: str, selector: str) -> bool:
    pattern = str(pattern or "")
    selector = str(selector or "")
    if not pattern or not selector:
        return False
    if pattern == "**" or pattern == selector:
        return True
    if pattern.endswith("/**"):
        prefix = pattern[:-3]
        return selector == prefix or selector.startswith(prefix + "/")
    if pattern.endswith("**"):
        return selector.startswith(pattern[:-2])
    if pattern.endswith("*"):
        return selector.startswith(pattern[:-1])
    return False


def normalize_contract(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict) or not isinstance(value.get("id"), str) or not value["id"]:
        raise NeutralComputeError("contract id required")
    depends_on = sorted(set(str(v) for v in value.get("depends_on", []) if str(v)))
    if not depends_on:
        raise NeutralComputeError(f"contract {value['id']} requires depends_on")
    return {
        "id": value["id"],
        "kind": value.get("kind", "derived-state"),
        "depends_on": depends_on,
        "allowed_routes": sorted(set(str(v) for v in value.get("allowed_routes", []) if str(v))),
        "policy_kind": value.get("policy_kind", "contract-local"),
        "metadata": _clone(value.get("metadata")),
    }


def normalize_artifact_ref(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise NeutralComputeError("artifact ref must be an object")
    digest = value.get("artifact_sha256")
    if not isinstance(digest, str) or len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise NeutralComputeError("artifact_sha256 must be sha256")
    hash_kind = value.get("hash_kind", "canonical-json")
    if hash_kind not in {"canonical-json", "bytes"}:
        raise NeutralComputeError(f"unsupported artifact hash_kind {hash_kind}")
    for field in ("source_sha256", "proof_sha256"):
        current = value.get(field)
        if current is not None and (
            not isinstance(current, str)
            or len(current) != 64
            or any(c not in "0123456789abcdef" for c in current)
        ):
            raise NeutralComputeError(f"{field} must be sha256")
    return {
        "artifact_sha256": digest,
        "hash_kind": hash_kind,
        "representation": value.get("representation", "opaque"),
        "source_sha256": value.get("source_sha256"),
        "proof_sha256": value.get("proof_sha256"),
        "metadata": _clone(value.get("metadata")),
    }


def artifact_ref(value: Any, *, hash_kind: str | None = None, representation: str | None = None,
                 source_sha256: str | None = None, proof_sha256: str | None = None,
                 metadata: Any = None) -> dict[str, Any]:
    if hash_kind is None:
        hash_kind = "bytes" if isinstance(value, (bytes, bytearray, memoryview)) else "canonical-json"
    digest = hash_bytes(value) if hash_kind == "bytes" else hash_canonical(value)
    return normalize_artifact_ref({
        "artifact_sha256": digest,
        "hash_kind": hash_kind,
        "representation": representation or ("bytes" if hash_kind == "bytes" else "canonical-json"),
        "source_sha256": source_sha256,
        "proof_sha256": proof_sha256,
        "metadata": metadata,
    })


def verify_artifact(ref: dict[str, Any], value: Any) -> dict[str, Any]:
    normalized = normalize_artifact_ref(ref)
    observed = hash_bytes(value) if normalized["hash_kind"] == "bytes" else hash_canonical(value)
    return {
        "ok": observed == normalized["artifact_sha256"],
        "claimed": normalized["artifact_sha256"],
        "observed": observed,
        "hash_kind": normalized["hash_kind"],
    }


def _generation_body(sequence: int, parent: str | None, plan_sha: str | None,
                     selectors: list[str], contracts: dict[str, Any]) -> dict[str, Any]:
    return {
        "sequence": sequence,
        "parent_generation_sha256": parent,
        "plan_sha256": plan_sha,
        "mutation_selectors": _clone(selectors),
        "contracts": _clone(contracts),
    }


def create_runtime(*, contracts: list[dict[str, Any]], artifacts: dict[str, Any],
                   label: str | None = None) -> dict[str, Any]:
    normalized = [normalize_contract(value) for value in contracts]
    if not normalized:
        raise NeutralComputeError("at least one contract required")
    registry: dict[str, Any] = {}
    for contract in normalized:
        if contract["id"] in registry:
            raise NeutralComputeError(f"duplicate contract {contract['id']}")
        registry[contract["id"]] = contract

    base_contracts: dict[str, Any] = {}
    for contract_id in sorted(registry):
        initial = artifacts.get(contract_id)
        if initial is None:
            raise NeutralComputeError(f"missing initial artifact for {contract_id}")
        base_contracts[contract_id] = {
            "decision": "BASE",
            "route": None,
            "previous_artifact_sha256": None,
            **normalize_artifact_ref(initial),
        }

    base = _seal(_generation_body(0, None, None, [], base_contracts), "generation_sha256")
    return {
        "format": FORMAT,
        "version": VERSION,
        "label": label,
        "registry": registry,
        "generations": {base["generation_sha256"]: base},
        "current_generation_sha256": base["generation_sha256"],
        "receipts": [],
        "hot": {},
    }


def current_generation(runtime: dict[str, Any]) -> dict[str, Any] | None:
    return runtime.get("generations", {}).get(runtime.get("current_generation_sha256"))


def current_head(runtime: dict[str, Any]) -> dict[str, Any] | None:
    generation = current_generation(runtime)
    if generation is None:
        return None
    return {
        "sequence": generation["sequence"],
        "generation_sha256": generation["generation_sha256"],
        "parent_generation_sha256": generation["parent_generation_sha256"],
        "contracts": _clone(generation["contracts"]),
    }


def plan_mutation(runtime: dict[str, Any], *, selectors: list[str], reason: str | None = None) -> dict[str, Any]:
    base = current_generation(runtime)
    if base is None:
        return _hold("HOLD_NO_CURRENT_GENERATION")
    unique = sorted(set(str(v) for v in selectors if str(v)))
    if not unique:
        return _hold("HOLD_MUTATION_SELECTORS_REQUIRED")

    rows: dict[str, Any] = {}
    claimed: set[str] = set()
    for contract_id in sorted(runtime["registry"]):
        contract = runtime["registry"][contract_id]
        matched: list[str] = []
        for selector in unique:
            if any(selector_matches(pattern, selector) for pattern in contract["depends_on"]):
                matched.append(selector)
                claimed.add(selector)
        rows[contract_id] = {
            "action": "UPDATE_REQUIRED" if matched else "REUSE_EXACT",
            "matched_selectors": matched,
            "allowed_routes": _clone(contract["allowed_routes"]),
            "policy_kind": contract["policy_kind"],
        }

    unknown = [selector for selector in unique if selector not in claimed]
    if unknown:
        return _hold("HOLD_UNKNOWN_SELECTOR", selectors=unique, unknown_selectors=unknown)

    body = {
        "base_generation_sha256": base["generation_sha256"],
        "base_sequence": base["sequence"],
        "selectors": unique,
        "reason": reason,
        "contracts": rows,
    }
    return {"status": "PLANNED", **_seal(body, "plan_sha256")}


def _valid_plan(plan: Any) -> bool:
    if not isinstance(plan, dict) or plan.get("status") != "PLANNED":
        return False
    body = _clone(plan)
    body.pop("status", None)
    return _verify_seal(body, "plan_sha256")


def stage_generation(runtime: dict[str, Any], plan: dict[str, Any],
                     updates: dict[str, dict[str, Any]]) -> dict[str, Any]:
    if not _valid_plan(plan):
        return _hold("HOLD_INVALID_PLAN")
    if plan["base_generation_sha256"] != runtime["current_generation_sha256"]:
        return _hold(
            "HOLD_STALE_BASE",
            planned_base=plan["base_generation_sha256"],
            current_generation_sha256=runtime["current_generation_sha256"],
        )

    prior = current_generation(runtime)
    assert prior is not None
    contracts: dict[str, Any] = {}
    updated: list[str] = []
    reused: list[str] = []

    for contract_id in sorted(runtime["registry"]):
        decision = plan["contracts"].get(contract_id)
        if decision is None:
            return _hold("HOLD_PLAN_CONTRACT_MISSING", contract=contract_id)
        if decision["action"] == "REUSE_EXACT":
            if contract_id in updates:
                return _hold("HOLD_REUSE_OVERRIDE", contract=contract_id)
            contracts[contract_id] = {
                **_clone(prior["contracts"][contract_id]),
                "decision": "REUSED_EXACT",
                "route": None,
                "previous_artifact_sha256": prior["contracts"][contract_id]["artifact_sha256"],
            }
            reused.append(contract_id)
            continue
        if decision["action"] != "UPDATE_REQUIRED":
            return _hold("HOLD_UNKNOWN_PLAN_ACTION", contract=contract_id, action=decision["action"])
        update = updates.get(contract_id)
        if update is None:
            return _hold("HOLD_UPDATE_MISSING", contract=contract_id)
        route = update.get("route")
        if not isinstance(route, str) or not route:
            return _hold("HOLD_ROUTE_REQUIRED", contract=contract_id)
        if decision["allowed_routes"] and route not in decision["allowed_routes"]:
            return _hold(
                "HOLD_ROUTE_NOT_ALLOWED",
                contract=contract_id,
                route=route,
                allowed_routes=_clone(decision["allowed_routes"]),
            )
        try:
            ref = normalize_artifact_ref(update)
        except NeutralComputeError as exc:
            return _hold("HOLD_INVALID_ARTIFACT_REF", contract=contract_id, detail=str(exc))
        contracts[contract_id] = {
            **ref,
            "decision": "UPDATED",
            "route": route,
            "previous_artifact_sha256": prior["contracts"][contract_id]["artifact_sha256"],
        }
        updated.append(contract_id)

    unknown_updates = sorted(set(updates) - set(runtime["registry"]))
    if unknown_updates:
        return _hold("HOLD_UNKNOWN_UPDATE_CONTRACT", contract=unknown_updates[0])

    generation = _seal(
        _generation_body(
            prior["sequence"] + 1,
            prior["generation_sha256"],
            plan["plan_sha256"],
            plan["selectors"],
            contracts,
        ),
        "generation_sha256",
    )
    body = {
        "base_generation_sha256": prior["generation_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "generation": generation,
        "updated": updated,
        "reused": reused,
    }
    return {"status": "STAGED", **_seal(body, "stage_sha256")}


def _valid_stage(stage: Any) -> bool:
    if not isinstance(stage, dict) or stage.get("status") != "STAGED":
        return False
    body = _clone(stage)
    body.pop("status", None)
    return _verify_seal(body, "stage_sha256") and _verify_seal(stage["generation"], "generation_sha256")


def _invalidate_hot(runtime: dict[str, Any]) -> None:
    current = current_generation(runtime)
    for contract_id in list(runtime.get("hot", {})):
        if (
            current is None
            or contract_id not in current["contracts"]
            or runtime["hot"][contract_id]["artifact_sha256"] != current["contracts"][contract_id]["artifact_sha256"]
        ):
            del runtime["hot"][contract_id]


def commit_generation(runtime: dict[str, Any], stage: dict[str, Any], actor: str | None = None) -> dict[str, Any]:
    if not _valid_stage(stage):
        return _hold("HOLD_INVALID_STAGE")
    if stage["base_generation_sha256"] != runtime["current_generation_sha256"]:
        return _hold(
            "HOLD_STALE_STAGE",
            staged_base=stage["base_generation_sha256"],
            current_generation_sha256=runtime["current_generation_sha256"],
        )
    generation = _clone(stage["generation"])
    runtime["generations"][generation["generation_sha256"]] = generation
    runtime["current_generation_sha256"] = generation["generation_sha256"]
    _invalidate_hot(runtime)
    receipt = _seal({
        "type": "generation.commit",
        "sequence": generation["sequence"],
        "generation_sha256": generation["generation_sha256"],
        "parent_generation_sha256": generation["parent_generation_sha256"],
        "plan_sha256": generation["plan_sha256"],
        "updated": _clone(stage["updated"]),
        "reused": _clone(stage["reused"]),
        "actor": actor,
    }, "receipt_sha256")
    runtime["receipts"].append(receipt)
    return {"status": "COMMITTED", "head": current_head(runtime), "receipt": _clone(receipt)}


def _is_ancestor(runtime: dict[str, Any], target: str, start: str) -> bool:
    cursor: str | None = start
    seen: set[str] = set()
    while cursor is not None:
        if cursor == target:
            return True
        if cursor in seen:
            return False
        seen.add(cursor)
        generation = runtime["generations"].get(cursor)
        if generation is None:
            return False
        cursor = generation["parent_generation_sha256"]
    return False


def rollback(runtime: dict[str, Any], target: str, actor: str | None = None) -> dict[str, Any]:
    if target not in runtime["generations"]:
        return _hold("HOLD_UNKNOWN_GENERATION", target_generation_sha256=target)
    current = runtime["current_generation_sha256"]
    if current == target:
        return {"status": "ALREADY_CURRENT", "head": current_head(runtime)}
    if not _is_ancestor(runtime, target, current):
        return _hold("HOLD_TARGET_NOT_ANCESTOR", current_generation_sha256=current, target_generation_sha256=target)
    runtime["current_generation_sha256"] = target
    _invalidate_hot(runtime)
    receipt = _seal({
        "type": "generation.rollback",
        "from_generation_sha256": current,
        "to_generation_sha256": target,
        "actor": actor,
    }, "receipt_sha256")
    runtime["receipts"].append(receipt)
    return {"status": "ROLLED_BACK", "head": current_head(runtime), "receipt": _clone(receipt)}


def reactivate(runtime: dict[str, Any], target: str, actor: str | None = None) -> dict[str, Any]:
    if target not in runtime["generations"]:
        return _hold("HOLD_UNKNOWN_GENERATION", target_generation_sha256=target)
    current = runtime["current_generation_sha256"]
    if current == target:
        return {"status": "ALREADY_CURRENT", "head": current_head(runtime)}
    if not _is_ancestor(runtime, current, target):
        return _hold("HOLD_TARGET_NOT_DESCENDANT", current_generation_sha256=current, target_generation_sha256=target)
    runtime["current_generation_sha256"] = target
    _invalidate_hot(runtime)
    receipt = _seal({
        "type": "generation.reactivate",
        "from_generation_sha256": current,
        "to_generation_sha256": target,
        "actor": actor,
    }, "receipt_sha256")
    runtime["receipts"].append(receipt)
    return {"status": "REACTIVATED", "head": current_head(runtime), "receipt": _clone(receipt)}


def wake_contract(runtime: dict[str, Any], contract_id: str, value: Any) -> dict[str, Any]:
    generation = current_generation(runtime)
    if generation is None or contract_id not in generation["contracts"]:
        return _hold("HOLD_UNKNOWN_CONTRACT", contract=contract_id)
    check = verify_artifact(generation["contracts"][contract_id], value)
    if not check["ok"]:
        return _hold(
            "HOLD_ARTIFACT_HASH_MISMATCH",
            contract=contract_id,
            claimed=check["claimed"],
            observed=check["observed"],
            hash_kind=check["hash_kind"],
        )
    if check["hash_kind"] == "bytes":
        stored = {"encoded_as": "base64-bytes", "value": base64.b64encode(bytes(value)).decode("ascii")}
    else:
        stored = {"encoded_as": "canonical-json", "value": _clone(value)}
    runtime["hot"][contract_id] = {"artifact_sha256": check["observed"], **stored}
    return {
        "status": "AWAKE_VERIFIED",
        "contract": contract_id,
        "artifact_sha256": check["observed"],
        "generation_sha256": generation["generation_sha256"],
    }


def hot_artifact(runtime: dict[str, Any], contract_id: str) -> Any:
    value = runtime.get("hot", {}).get(contract_id)
    if value is None:
        return None
    if value["encoded_as"] == "base64-bytes":
        return base64.b64decode(value["value"])
    return _clone(value["value"])


def sleep_contract(runtime: dict[str, Any], contract_id: str) -> dict[str, Any]:
    if contract_id not in runtime.get("hot", {}):
        return {"status": "ALREADY_DORMANT", "contract": contract_id}
    del runtime["hot"][contract_id]
    return {"status": "DORMANT", "contract": contract_id}


def export_runtime(runtime: dict[str, Any]) -> dict[str, Any]:
    body = {
        "format": runtime["format"],
        "version": runtime["version"],
        "label": runtime.get("label"),
        "registry": _clone(runtime["registry"]),
        "generations": _clone(runtime["generations"]),
        "current_generation_sha256": runtime["current_generation_sha256"],
        "receipts": _clone(runtime["receipts"]),
    }
    return _seal(body, "runtime_sha256")


def validate_runtime(data: Any) -> bool:
    if not isinstance(data, dict) or data.get("format") != FORMAT or data.get("version") != VERSION:
        raise NeutralComputeError("unsupported neutral compute runtime")
    if not _verify_seal(data, "runtime_sha256"):
        raise NeutralComputeError("runtime hash mismatch")
    registry_ids = sorted(data.get("registry", {}))
    if not registry_ids:
        raise NeutralComputeError("runtime registry empty")
    generations = data.get("generations", {})
    if data.get("current_generation_sha256") not in generations:
        raise NeutralComputeError("current generation missing")
    for digest, generation in generations.items():
        if digest != generation.get("generation_sha256") or not _verify_seal(generation, "generation_sha256"):
            raise NeutralComputeError(f"generation hash mismatch {digest}")
        parent_sha = generation.get("parent_generation_sha256")
        if parent_sha is None:
            if generation.get("sequence") != 0:
                raise NeutralComputeError(f"non-root generation missing parent {digest}")
        else:
            parent = generations.get(parent_sha)
            if parent is None:
                raise NeutralComputeError(f"missing parent {parent_sha}")
            if generation.get("sequence") != parent.get("sequence") + 1:
                raise NeutralComputeError(f"generation sequence mismatch {digest}")
        for contract_id in registry_ids:
            if contract_id not in generation.get("contracts", {}):
                raise NeutralComputeError(f"generation missing contract {contract_id}")
            normalize_artifact_ref(generation["contracts"][contract_id])
    for receipt in data.get("receipts", []):
        if not _verify_seal(receipt, "receipt_sha256"):
            raise NeutralComputeError("receipt hash mismatch")
    return True


def import_runtime(data: dict[str, Any]) -> dict[str, Any]:
    validate_runtime(data)
    body = _clone(data)
    body.pop("runtime_sha256", None)
    body["hot"] = {}
    return body

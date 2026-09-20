"""Goal-directed composition of installed typed operators, independent of AI."""
from __future__ import annotations

from copy import deepcopy
import platform
import sys

from .atlas_pipeline import _capability_gaps, _parameters
from .creation_atlas import CreationAtlas, digest, runtime_pin
from .workflow_contracts import load_operators, matches, validate_request


class SearchLimit(Exception):
    pass


def source_values(request, atlas):
    used = set()
    for source in request["inputs"].values():
        source["values"] = [_parameters(v, atlas, used) for v in source["values"]]
    for scenario in request["scenarios"]:
        scenario["inputs"] = {k: _parameters(v, atlas, used) for k, v in scenario["inputs"].items()}
    return sorted(used)


def origin(ref, nodes, operators):
    if "source" in ref:
        return "source:" + ref["source"]
    node = next(n for n in nodes if n["id"] == ref["node"])
    port = operators[node["operator"]].get("identity_from")
    return origin(node["inputs"][port], nodes, operators) if port else node["id"]


def uses(ref, wanted, nodes):
    by_id, pending, seen = {n["id"]: n for n in nodes}, [ref], set()
    while pending:
        current = pending.pop()
        if "node" not in current or current["node"] in seen:
            continue
        seen.add(current["node"])
        children = list(by_id[current["node"]]["inputs"].values())
        if wanted in children:
            return True
        pending.extend(children)
    return False


def choice_order(candidate):
    return tuple(v for _, v in sorted(candidate["program"]["choices"].items()))


def technical_fit(request, operators):
    """Type reachability is a preflight fact, never an execution success claim."""
    providers = [("source:" + k, v["type"]) for k, v in sorted(request["inputs"].items())]
    pending, connections = set(operators), {}
    while pending:
        ready = []
        for key in sorted(pending):
            ports = {p: [identity for identity, contract in providers if matches(contract, needs)]
                     for p, needs in operators[key]["needs"].items()}
            if all(ports.values()):
                connections[key] = {"type_reachable": True, "inputs": ports}
                ready.append(key)
        if not ready:
            break
        for key in ready:
            providers.append(("operator:" + key, operators[key]["provides"]))
            pending.remove(key)
    for key in sorted(pending):
        ports = {p: {"required": needs, "matches": [identity for identity, contract in providers if matches(contract, needs)],
                     "available_same_kind": [{"provider": identity, "type": contract} for identity, contract in providers
                                             if contract["kind"] == needs["kind"]]}
                 for p, needs in operators[key]["needs"].items()}
        connections[key] = {"type_reachable": False, "inputs": ports}
    return connections


def workflow_signature(program, request, operators):
    """Structure, source sharing and contracts; excludes settings and prose labels."""
    nodes, sources, mapped = {n["id"]: n for n in program["nodes"]}, {}, {}
    def visit(ref):
        if "source" in ref:
            key = ref["source"]
            if key not in sources:
                sources[key] = len(sources)
            return {"source": sources[key], "type": request["inputs"][key]["type"]}
        key = ref["node"]
        if key in mapped:
            return {"shared": mapped[key]}
        node = nodes[key]
        index = len(mapped)
        mapped[key] = index
        op = operators[node["operator"]]
        return {"node": index, "operator": op["id"], "version": op["version"],
                "inputs": {p: visit(r) for p, r in sorted(node["inputs"].items())}}
    # Sort outputs by type and producer, not caller labels.
    refs = sorted(program["outputs"].values(), key=lambda r: (nodes[r["node"]]["operator"], r["node"]))
    return digest([visit(r) for r in refs])


def compose(request, operators, goal_order):
    limits = request["budget"]
    state_count, truncated = 0, False
    candidates, identities = [], set()

    def tick():
        nonlocal state_count
        state_count += 1
        if state_count > limits["states"]:
            raise SearchLimit()

    def resolve(required, state, metrics, stack):
        tick()
        # Already-built ports are preferred and preserve dependency identity.
        for node in state["nodes"]:
            op = operators[node["operator"]]
            if matches(op["provides"], required) and all(op["metrics"].get(k) == v for k, v in metrics.items()):
                yield {"node": node["id"]}, state
        if not metrics:
            for key, source in sorted(request["inputs"].items()):
                if not matches(source["type"], required):
                    continue
                choices = [state["choices"][key]] if key in state["choices"] else range(len(source["values"]))
                for choice in choices:
                    updated = {**state, "choices": {**state["choices"], key: choice}}
                    yield {"source": key}, updated
        if len(state["nodes"]) >= limits["steps"]:
            return
        for identity, op in sorted(operators.items(), key=lambda pair: (pair[1]["cost"], pair[0])):
            if (identity in stack or not matches(op["provides"], required)
                    or not all(op["metrics"].get(k) == v for k, v in metrics.items())):
                continue
            ports = sorted(op["needs"])
            def wire(index, current, bindings):
                if index == len(ports):
                    yield current, bindings
                    return
                port = ports[index]
                for ref, next_state in resolve(op["needs"][port], current, {}, stack | {identity}):
                    yield from wire(index + 1, next_state, {**bindings, port: ref})
            for current, bindings in wire(0, state, {}):
                tick()
                node = {"operator": identity, "inputs": bindings}
                node["id"] = "n" + digest(node)[:16]
                if any(n["id"] == node["id"] for n in current["nodes"]):
                    continue
                if len(current["nodes"]) >= limits["steps"]:
                    continue
                yield {"node": node["id"]}, {**current, "nodes": [*current["nodes"], node]}

    def finish(index, state, outputs):
        if index == len(goal_order):
            # Drop branches created while attempting a different goal binding.
            needed = set()
            by_id = {n["id"]: n for n in state["nodes"]}
            def mark(ref):
                if "node" in ref and ref["node"] not in needed:
                    needed.add(ref["node"])
                    for child in by_id[ref["node"]]["inputs"].values():
                        mark(child)
            for ref in outputs.values():
                mark(ref)
            nodes = [n for n in state["nodes"] if n["id"] in needed]
            used_sources = {r["source"] for n in nodes for r in n["inputs"].values() if "source" in r}
            program = {"nodes": nodes, "outputs": outputs,
                       "choices": {k: v for k, v in sorted(state["choices"].items()) if k in used_sources}}
            identity = digest(program)
            if identity not in identities:
                identities.add(identity)
                candidates.append({"id": identity, "program": program,
                    "signature": workflow_signature(program, request, operators),
                    "cost": sum(operators[n["operator"]]["cost"] for n in nodes)})
                if len(candidates) >= limits["plans"]:
                    raise SearchLimit()
            return
        goal_id = goal_order[index]
        goal = request["goals"][goal_id]
        metrics = {c["metric"]: c["unit"] for c in goal["checks"]}
        metrics.update({o["metric"]: o["unit"] for o in request["objectives"] if o["goal"] == goal_id})
        for ref, current in resolve(goal["type"], state, metrics, set()):
            parent = goal.get("same_origin_as")
            if parent and origin(ref, current["nodes"], operators) != origin(outputs[parent], current["nodes"], operators):
                continue
            parent = goal.get("uses_goal")
            if parent and not uses(ref, outputs[parent], current["nodes"]):
                continue
            finish(index + 1, current, {**outputs, goal_id: ref})

    try:
        finish(0, {"nodes": [], "choices": {}}, {})
    except SearchLimit:
        truncated = True
    candidates.sort(key=lambda c: (c["cost"], len(c["program"]["nodes"]), choice_order(c), c["id"]))
    return candidates, {"states": min(state_count, limits["states"]), "truncated": truncated,
                         "space": "Installed typed operators and declared input choices only; not an exhaustive universe."}


def plan(root, raw, *, memory=None):
    operators, source_kinds = load_operators(root)
    request, order = validate_request(raw, source_kinds)
    atlas = CreationAtlas(root)
    used = source_values(request, atlas)
    request, order = validate_request(request, source_kinds)
    requested = request.get("operators", sorted(operators))
    unknown = sorted(set(requested) - set(operators))
    gaps, unavailable, available = [], {}, {}
    if unknown:
        gaps.append("unknown operators: " + ", ".join(unknown))
    for identity in requested:
        if identity not in operators:
            continue
        op = operators[identity]
        missing = []
        for cap in [op["capability"], *op["dependencies"]]:
            missing.extend(_capability_gaps(atlas, cap))
        if op["operation"] == "verify-code":
            import shutil
            if shutil.which("node") is None:
                missing.append("Node is unavailable for actual code verification")
        if missing:
            unavailable[identity] = sorted(set(missing))
        else:
            available[identity] = op
    for goal_id, goal in request["goals"].items():
        metrics = [(c["metric"], c["unit"]) for c in goal["checks"]]
        metrics += [(o["metric"], o["unit"]) for o in request["objectives"] if o["goal"] == goal_id]
        producers = [o for o in available.values() if matches(o["provides"], goal["type"])]
        if not producers:
            gaps.append("no installed producer for goal: " + goal_id)
        for metric, unit in metrics:
            if not any(o["metrics"].get(metric) == unit for o in producers):
                gaps.append(f"no observer for {goal_id}.{metric} in {unit}")
    pins = {"runtime": runtime_pin(), "atlas": atlas.summary()["snapshot_sha256"],
            "operators": digest(available), "python": sys.version, "platform": platform.platform()}
    if any(op["operation"] == "verify-code" for op in available.values()):
        import subprocess
        import shutil
        try:
            result = subprocess.run([shutil.which("node"), "--version"], capture_output=True, text=True, timeout=5, check=True)
            pins["node"] = result.stdout.strip()
        except (OSError, subprocess.SubprocessError):
            pins["node"] = "VERSION_UNAVAILABLE"
    from .workflow_memory import read_memory
    memory_data = read_memory(root, memory, pins=pins)
    retained = {r["signature"] for r in memory_data["workflows"] if r["fresh"]}
    candidates, search = ([], {"states": 0, "truncated": False}) if gaps else compose(request, available, order)
    if not gaps:
        from .workflow_reuse import rebind_workflows
        reused, reuse_gaps = rebind_workflows(memory_data["workflows"], request, available, order)
        memory_data["ignored"].extend(reuse_gaps)
        merged = {c["id"]: c for c in [*reused, *candidates]}
        candidates = sorted(merged.values(), key=lambda c: (c["signature"] not in retained, c["cost"], choice_order(c), c["id"]))
        if len(candidates) > request["budget"]["plans"]:
            search["truncated"] = True
            candidates = candidates[:request["budget"]["plans"]]
    if not candidates and not gaps:
        gaps.append("no compatible workflow within the declared type, unit, origin and search budgets")
    for candidate in candidates:
        candidate["reused_structure"] = candidate["signature"] in retained
    report = {"schema": "axm.workflow-plan/v0.1", "status": "READY" if candidates and not gaps else "HOLD_CAPABILITY_GAP",
              "request": request, "operators": available, "candidates": candidates, "search": search,
              "gaps": gaps, "unavailable_operators": unavailable, "pins": pins, "atlas_inputs": used,
              "technical_fit": technical_fit(request, available),
              "memory": {"eligible_structures": len(retained), "stale": memory_data["stale"], "ignored": memory_data["ignored"]},
              "ranking": "All hard checks first. Weighted worst-scenario target deficits, then declared cost and stable identity.",
              "boundary": "A composed route is untested. Missing observers are gaps; prose and confidence are not invented measurements."}
    report["plan_sha256"] = digest(report)
    return report


def compile_candidate(candidate, request, operators, scenario):
    program = candidate["program"]
    parameters = {key: {"value": deepcopy(scenario["inputs"].get(key, request["inputs"][key]["values"][choice]))}
                  for key, choice in program["choices"].items()}
    steps, goals = [], {}
    for node in program["nodes"]:
        op = operators[node["operator"]]
        values = {port: {"from": ("request." + ref["source"] + ".value" if "source" in ref
                                   else "steps." + ref["node"] + ".value")} for port, ref in node["inputs"].items()}
        steps.append({"id": node["id"], "capability": op["capability"],
                      "depends_on": sorted({r["node"] for r in node["inputs"].values() if "node" in r}),
                      "inputs": {"operation": op["operation"], "path": {"output": node["id"]}, "values": values},
                      "checks": [{"step": node["id"], "path": ["status"], "equals": "PASS"}]})
    for identity, goal in request["goals"].items():
        node_id = program["outputs"][identity]["node"]
        checks = [{"step": node_id, "path": ["metrics", c["metric"]],
                   **{k: c[k] for k in ("min", "max") if k in c}} for c in goal["checks"]]
        goals[identity] = checks
        next(s for s in steps if s["id"] == node_id)["checks"].extend(deepcopy(checks))
    blueprint = {"id": "discovered-" + candidate["id"], "version": "0.1.0", "purpose": request["intent"],
                 "direction": "workflow-experiment", "parameters": {key: "object" for key in parameters},
                 "defaults": {}, "uses": ["operator:" + key for key in sorted({n["operator"] for n in program["nodes"]})],
                 "steps": steps, "goals": goals, "artifacts": {},
                 "limitations": [s for key in sorted({n["operator"] for n in program["nodes"]}) for s in operators[key]["limitations"]]}
    intent = {"purpose": request["intent"], "direction": "workflow-experiment", "goals": sorted(goals),
              "blueprint": blueprint["id"], "parameters": parameters}
    return blueprint, intent


def operate(root, inputs):
    operation = inputs.get("operation", "plan")
    if operation == "catalog":
        operators, kinds = load_operators(root)
        return {"operators": operators, "source_kinds": sorted(kinds)}
    if operation == "memory":
        from .workflow_memory import read_memory
        return read_memory(root, inputs["memory"])
    if operation == "plan":
        return plan(root, inputs["request"], memory=inputs.get("memory"))
    if operation == "experiment":
        from .workflow_experiments import experiment
        return experiment(root, inputs["request"], inputs["path"], memory=inputs.get("memory"),
                          expected_plan=inputs.get("plan_sha256"))
    raise ValueError("unknown workflow discovery operation")

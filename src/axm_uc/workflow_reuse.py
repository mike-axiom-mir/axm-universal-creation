"""Rebind retained structures to current types and goals; never replay a past PASS."""
from __future__ import annotations

from itertools import product

from .creation_atlas import digest
from .workflow_contracts import matches
from .workflow_discovery import origin, uses, workflow_signature


def rebind_workflows(records, request, operators, goal_order):
    candidates, ignored, visited = [], [], 0
    maximum = request["budget"]["plans"]
    for record in records:
        if not record["fresh"]:
            continue
        try:
            template = record["program"]
            if not 1 <= len(template["nodes"]) <= request["budget"]["steps"]:
                continue
            source_keys = sorted(record["source_types"])
            source_options = [sorted((k for k, v in request["inputs"].items()
                                      if matches(v["type"], record["source_types"][old])), key=lambda k: (k != old, k))
                              for old in source_keys]
            for mapped in product(*source_options):
                visited += 1
                if visited > 4096:
                    return candidates, [*ignored, {"reason": "retained binding budget reached"}]
                if len(set(mapped)) != len(mapped):
                    continue
                sources = dict(zip(source_keys, mapped))
                nodes, replacements, types = [], {}, {}
                for old in template["nodes"]:
                    op = operators[old["operator"]]
                    if op["version"] != record["operators"][op["id"]] or set(old["inputs"]) != set(op["needs"]):
                        raise ValueError("retained operator contract changed")
                    bindings = {}
                    for port, ref in old["inputs"].items():
                        if set(ref) == {"source"}:
                            key = sources[ref["source"]]
                            current, provided = {"source": key}, request["inputs"][key]["type"]
                        elif set(ref) == {"node"}:
                            key = replacements[ref["node"]]
                            current, provided = {"node": key}, types[key]
                        else:
                            raise ValueError("invalid retained port reference")
                        if not matches(provided, op["needs"][port]):
                            raise ValueError("retained port no longer fits")
                        bindings[port] = current
                    node = {"operator": op["id"], "inputs": bindings}
                    node["id"] = "n" + digest(node)[:16]
                    if node["id"] in types:
                        raise ValueError("duplicate retained node")
                    nodes.append(node)
                    replacements[old["id"]], types[node["id"]] = node["id"], op["provides"]
                output_options = []
                for goal_id in goal_order:
                    goal = request["goals"][goal_id]
                    measurements = [(c["metric"], c["unit"]) for c in goal["checks"]]
                    measurements += [(o["metric"], o["unit"]) for o in request["objectives"] if o["goal"] == goal_id]
                    output_options.append([{"node": n["id"]} for n in nodes
                        if matches(types[n["id"]], goal["type"])
                        and all(operators[n["operator"]]["metrics"].get(k) == unit for k, unit in measurements)])
                for refs in product(*output_options):
                    visited += 1
                    if visited > 4096:
                        return candidates, [*ignored, {"reason": "retained binding budget reached"}]
                    outputs = dict(zip(goal_order, refs))
                    if any(g.get("same_origin_as") and origin(outputs[k], nodes, operators)
                           != origin(outputs[g["same_origin_as"]], nodes, operators) for k, g in request["goals"].items()):
                        continue
                    if any(g.get("uses_goal") and not uses(outputs[k], outputs[g["uses_goal"]], nodes)
                           for k, g in request["goals"].items()):
                        continue
                    # Retain only ancestors of the newly bound goals.
                    needed = {r["node"] for r in refs}
                    for node in reversed(nodes):
                        if node["id"] in needed:
                            needed.update(r["node"] for r in node["inputs"].values() if "node" in r)
                    selected = [n for n in nodes if n["id"] in needed]
                    keys = sorted({r["source"] for n in selected for r in n["inputs"].values() if "source" in r})
                    for choices in product(*(range(len(request["inputs"][k]["values"])) for k in keys)):
                        program = {"nodes": selected, "outputs": outputs, "choices": dict(zip(keys, choices))}
                        candidates.append({"id": digest(program), "program": program,
                            "signature": workflow_signature(program, request, operators),
                            "cost": sum(operators[n["operator"]]["cost"] for n in selected)})
                        if len(candidates) >= maximum:
                            return candidates, ignored
        except (KeyError, ValueError, TypeError) as exc:
            ignored.append({"signature": record.get("signature"), "reason": str(exc)})
    return candidates, ignored

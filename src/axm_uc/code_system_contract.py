"""Bind typed programs to UC's existing deterministic state graph."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import re

from .state_machine import compile_state_machine

SCHEMA = "axm.code-system/v0.1"
ARCHIVE_SCHEMA = "axm.code-system-archive/v0.1"
ID = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,79}\Z")
RESERVED = {"ucSystemInitial", "ucSystemIdentity"}
STATUSES = {"APPLIED", "HOLD_NO_TRANSITION", "HOLD_GUARD", "HOLD_ARGUMENTS", "HOLD_EXECUTION", "HOLD_INVARIANT"}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def exact(value, required, optional=()):
    if not isinstance(value, dict) or set(value) - set(required) - set(optional) or set(required) - set(value):
        raise ValueError("expected fields " + ", ".join(sorted(required)) + "; optional " + ", ".join(sorted(optional)))


def identity(value, label):
    if not isinstance(value, str) or not ID.fullmatch(value):
        raise ValueError(label + " must be an ASCII identifier of 1..80 characters")
    return value


def rows(value, label, maximum, minimum=1):
    if not isinstance(value, list) or not minimum <= len(value) <= maximum:
        raise ValueError(f"{label} needs {minimum}..{maximum} entries")
    return value


def integer(value, label, low, high):
    if type(value) is not int or not low <= value <= high:
        raise ValueError(f"{label} must be an integer in {low}..{high}")


def event(value, bindings):
    exact(value, {"type", "args"})
    if value["type"] not in bindings or not isinstance(value["args"], list) or len(value["args"]) > 15:
        raise ValueError("event requires a declared type and at most 15 arguments")


def prepare(request):
    # Round trip rejects non-JSON numbers before any generated code is executed.
    body = canonical(request)
    if len(body.encode()) > 1048576:
        raise ValueError("code-system request exceeds 1 MiB")
    request = json.loads(body)
    exact(request, {"action", "job", "system"}, {"archive", "system_archive"})
    if request["action"] not in {"build", "verify", "retain"}:
        raise ValueError("action must be build, verify or retain")
    if request["action"] != "retain" and ({"archive", "system_archive"} & set(request)):
        raise ValueError("archives belong only to explicit retain requests")
    job, system = request["job"], request["system"]
    exact(job, {"id", "program", "cases", "requirements"}, {"languages"})
    exact(system, {"schema", "domain", "initial_model", "machine", "bindings", "invariants", "scenarios", "exploration"})
    if system["schema"] != SCHEMA or system["domain"] not in {"software", "game"}:
        raise ValueError("unsupported code-system schema or domain")
    compiled = compile_state_machine(system["machine"])
    system["machine"] = compiled["machine"]
    # Declaration order is not transition priority.
    system["machine"]["states"].sort()
    program = job["program"]
    exact(program, {"schema", "name", "functions", "exports"})
    functions = {}
    for function in rows(program["functions"], "program functions", 30):
        exact(function, {"name", "params", "returns", "body"})
        name = function["name"]
        if name in functions or name in RESERVED:
            raise ValueError("duplicate or reserved function name")
        functions[name] = function
    exports = program["exports"]
    if not isinstance(exports, list):
        raise ValueError("program exports must be a list")

    def exported(name):
        if not isinstance(name, str) or name not in functions or name not in exports:
            raise ValueError("system function must be an explicit program export: " + str(name))
        return functions[name]

    bindings, signals, model_type = {}, set(), None
    for binding in rows(system["bindings"], "bindings", 32):
        exact(binding, {"event", "reducer"}, {"guard", "routes"})
        key = identity(binding["event"], "binding event")
        if key in bindings:
            raise ValueError("duplicate event binding")
        reducer = exported(binding["reducer"])
        params = rows(reducer["params"], "reducer parameters", 16)
        for parameter in params:
            exact(parameter, {"name", "type"})
        current_type = params[0]["type"]
        if not isinstance(current_type, dict) or set(current_type) != {"record"}:
            raise ValueError("system model must be an explicit record type")
        if model_type is None:
            model_type = current_type
        if current_type != model_type or reducer["returns"] != model_type:
            raise ValueError("every reducer must consume and return the same model type")
        if "guard" in binding:
            guard = exported(binding["guard"])
            if [p["type"] for p in guard["params"]] != [p["type"] for p in params] or guard["returns"] != "boolean":
                raise ValueError("guard must match reducer parameters and return boolean")
        if "routes" in binding:
            route = binding["routes"]
            exact(route, {"function", "events"})
            selector = exported(route["function"])
            if [p["type"] for p in selector["params"]] != [model_type] or selector["returns"] != "string":
                raise ValueError("route selector must consume the proposed model and return a string")
            routes = rows(route["events"], "route events", 32)
            if any(not isinstance(v, str) or not v for v in routes) or len(set(routes)) != len(routes):
                raise ValueError("route events must be unique nonempty strings")
            route["events"].sort()
        else:
            routes = [key]
        signals.update(routes)
        bindings[key] = binding
    graph_signals = {row["event"] for row in system["machine"]["transitions"]}
    if signals != graph_signals:
        raise ValueError("bound transition signals and state-graph events must match exactly")
    invariant_ids = set()
    for invariant in rows(system["invariants"], "invariants", 32):
        exact(invariant, {"id", "function", "statement"})
        key = identity(invariant["id"], "invariant id")
        if key in invariant_ids or not isinstance(invariant["statement"], str) or not invariant["statement"].strip():
            raise ValueError("invariants need unique ids and nonempty statements")
        invariant_ids.add(key)
        function = exported(invariant["function"])
        if [p["type"] for p in function["params"]] != [model_type] or function["returns"] != "boolean":
            raise ValueError("invariant must consume the model and return boolean")

    scenario_ids, step_count = set(), 0
    for scenario in rows(system["scenarios"], "scenarios", 64):
        exact(scenario, {"id", "steps"})
        key = identity(scenario["id"], "scenario id")
        if key in scenario_ids:
            raise ValueError("duplicate scenario id")
        scenario_ids.add(key)
        for step in rows(scenario["steps"], "scenario steps", 128):
            exact(step, {"event", "expect"})
            event(step["event"], bindings)
            exact(step["expect"], {"status", "state"}, {"effects"})
            if step["expect"]["status"] not in STATUSES:
                raise ValueError("unknown scenario expected status")
            exact(step["expect"]["state"], {"phase", "model"})
            if step["expect"]["state"]["phase"] not in system["machine"]["states"]:
                raise ValueError("scenario expects an undeclared phase")
            if "effects" in step["expect"] and not isinstance(step["expect"]["effects"], list):
                raise ValueError("expected effects must be a list")
            step_count += 1
    if step_count > 1024:
        raise ValueError("scenario suite exceeds 1024 steps")
    exploration = system["exploration"]
    exact(exploration, {"events", "max_depth", "max_states", "max_edges"})
    for field, low, high in (("max_depth", 1, 32), ("max_states", 1, 4096), ("max_edges", 1, 20000)):
        integer(exploration[field], field, low, high)
    events = rows(exploration["events"], "exploration events", 32)
    for value in events:
        event(value, bindings)
    if len({canonical(value) for value in events}) != len(events):
        raise ValueError("duplicate exploration events")
    # Alphabet order is a declared tie breaker for shortest counterexamples.
    system["bindings"].sort(key=lambda row: row["event"])
    system["invariants"].sort(key=lambda row: row["id"])
    system["scenarios"].sort(key=lambda row: row["id"])
    program["functions"] += [
        {"name": "ucSystemInitial", "params": [], "returns": model_type,
         "body": {"op": "literal", "type": model_type, "value": system["initial_model"]}},
        {"name": "ucSystemIdentity", "params": [{"name": "model", "type": model_type}], "returns": model_type,
         "body": {"op": "ref", "name": "model"}},
    ]
    program["exports"] += sorted(RESERVED)
    case_ids = {row.get("id") for row in job["cases"]}
    if case_ids & RESERVED or any(row.get("id") == "ucSystemModelContract" for row in job["requirements"]):
        raise ValueError("reserved system acceptance id")
    job["cases"] += [
        {"id": "ucSystemInitial", "function": "ucSystemInitial", "args": [], "expected": system["initial_model"]},
        {"id": "ucSystemIdentity", "function": "ucSystemIdentity", "args": [system["initial_model"]], "expected": system["initial_model"]},
    ]
    job["requirements"].append({"id": "ucSystemModelContract", "statement": "The initial and restored model obey its declared record type.", "cases": sorted(RESERVED)})
    return request, compile_state_machine(system["machine"])


def structural_system(system, captures):
    """Code identities ignore private function names; event/field/phase names are public semantics."""
    functions = {row["function"]: row["structuralSha256"] for row in captures}
    body = {key: deepcopy(system[key]) for key in ("initial_model", "machine", "bindings", "invariants")}
    body["machine"].pop("id")
    for binding in body["bindings"]:
        for field in ("reducer", "guard"):
            if field in binding:
                binding[field] = functions[binding[field]]
        if "routes" in binding:
            binding["routes"]["function"] = functions[binding["routes"]["function"]]
    body["invariants"] = sorted({functions[row["function"]] for row in body["invariants"]})
    return body


def validate_archive(previous):
    archive = deepcopy(previous) if previous is not None else {"schema": ARCHIVE_SCHEMA, "entries": []}
    exact(archive, {"schema", "entries"})
    if archive["schema"] != ARCHIVE_SCHEMA:
        raise ValueError("unknown system archive schema")
    entries, seen = rows(archive["entries"], "archive entries", 128, 0), set()
    for row in entries:
        exact(row, {"structural_sha256", "structure", "construction", "construction_sha256", "observations"})
        if row["structural_sha256"] != digest(row["structure"]) or row["structural_sha256"] in seen:
            raise ValueError("system archive structural identity mismatch")
        if row["construction_sha256"] != digest(row["construction"]):
            raise ValueError("system archive construction identity mismatch")
        seen.add(row["structural_sha256"])
        rows(row["observations"], "archive observations", 128)
        for observation in row["observations"]:
            exact(observation, {"request_sha256", "verification_sha256"})
            if any(not isinstance(value, str) or not re.fullmatch(r"[0-9a-f]{64}", value) for value in observation.values()):
                raise ValueError("invalid retained observation identity")
    return archive


def retain_system(previous, system, captures, request, verification):
    archive = validate_archive(previous)
    entries = archive["entries"]
    structure = structural_system(system, captures)
    key = digest(structure)
    construction = deepcopy(request)
    construction.pop("archive", None)
    construction.pop("system_archive", None)
    observation = {"request_sha256": digest(construction), "verification_sha256": digest(verification)}
    entry = next((row for row in entries if row["structural_sha256"] == key), None)
    if entry is None:
        if len(entries) >= 128:
            raise ValueError("system archive is full; no entries were evicted")
        entry = {"structural_sha256": key, "structure": structure, "construction": construction,
                 "construction_sha256": digest(construction), "observations": []}
        entries.append(entry)
    if observation not in entry["observations"]:
        if len(entry["observations"]) >= 128:
            raise ValueError("system observation archive is full")
        entry["observations"].append(observation)
        entry["observations"].sort(key=canonical)
    entries.sort(key=lambda row: row["structural_sha256"])
    if len(canonical(archive).encode()) > 1048576:
        raise ValueError("system archive exceeds 1 MiB; no entries were evicted")
    return {"structural_sha256": key, "archive": archive, "status": "RETAINED_VERIFIED_CONSTRUCTION"}

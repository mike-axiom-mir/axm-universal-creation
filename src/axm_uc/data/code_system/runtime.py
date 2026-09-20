"""Portable generated-system host. Only the CLI reads files or writes stdout."""
from collections import deque
from copy import deepcopy
import json


def same(a, b):
    if type(a) in (int, float) and type(b) in (int, float):
        return a == b
    if type(a) is not type(b):
        return False
    if isinstance(a, dict):
        return set(a) == set(b) and all(same(a[k], b[k]) for k in a)
    if isinstance(a, list):
        return len(a) == len(b) and all(same(x, y) for x, y in zip(a, b))
    return a == b


def key(value):
    # Normalize integral floats for state deduplication (True remains boolean).
    if type(value) is float and value.is_integer():
        value = int(value)
    if isinstance(value, dict):
        return "{" + ",".join(json.dumps(k, ensure_ascii=False) + ":" + key(value[k]) for k in sorted(value)) + "}"
    if isinstance(value, list):
        return "[" + ",".join(key(v) for v in value) + "]"
    return json.dumps(value, ensure_ascii=False, allow_nan=False)


class System:
    def __init__(self, config, functions):
        self.config = deepcopy(config)
        self.spec = self.config["system"]
        self.functions = dict(functions)
        self.bindings = {row["event"]: row for row in self.spec["bindings"]}
        self.transitions = {(row["from"], row["event"]): row for row in self.spec["machine"]["transitions"]}

    def _violations(self, model):
        return [row["id"] for row in self.spec["invariants"] if self.functions[row["function"]](deepcopy(model)) is not True]

    def _state(self, value):
        if not isinstance(value, dict) or set(value) != {"phase", "model"} or value["phase"] not in self.spec["machine"]["states"]:
            raise ValueError("STATE_INVALID")
        self.functions["ucSystemIdentity"](value["model"])
        if self._violations(value["model"]):
            raise ValueError("STATE_INVARIANT")
        return deepcopy(value)

    def initial(self):
        return self._state({"phase": self.spec["machine"]["initial_state"], "model": self.functions["ucSystemInitial"]()})

    def step(self, state, event):
        current = self._state(state)
        held = lambda status, **extra: {"status": status, "state": deepcopy(current), "effects": [], **extra}
        if not isinstance(event, dict) or set(event) != {"type", "args"} or not isinstance(event.get("type"), str) or not isinstance(event.get("args"), list):
            return held("HOLD_ARGUMENTS")
        binding = self.bindings.get(event["type"])
        if binding is None:
            return held("HOLD_NO_TRANSITION")
        routes = binding.get("routes", {}).get("events", [event["type"]])
        if not any((current["phase"], signal) in self.transitions for signal in routes):
            return held("HOLD_NO_TRANSITION")
        try:
            args = [deepcopy(current["model"]), *deepcopy(event["args"])]
            if "guard" in binding and self.functions[binding["guard"]](*args) is not True:
                return held("HOLD_GUARD")
            proposed = self.functions[binding["reducer"]](*args)
            self.functions["ucSystemIdentity"](proposed)
            signal = self.functions[binding["routes"]["function"]](deepcopy(proposed)) if "routes" in binding else event["type"]
            if signal not in routes or (current["phase"], signal) not in self.transitions:
                return held("HOLD_EXECUTION", error="ROUTE_UNDECLARED")
            violations = self._violations(proposed)
            if violations:
                return held("HOLD_INVARIANT", violations=violations)
            transition = self.transitions[(current["phase"], signal)]
            return {"status": "APPLIED", "state": {"phase": transition["to"], "model": deepcopy(proposed)},
                    "effects": deepcopy(transition["effects"]), "transition": {k: transition[k] for k in ("from", "event", "to")}}
        except (ValueError, TypeError, OverflowError) as exc:
            code = str(exc)
            if code == "ARGUMENT_COUNT" or code == "VALUE_TYPE" or isinstance(exc, TypeError):
                return held("HOLD_ARGUMENTS")
            return held("HOLD_EXECUTION", error=code[:160])

    def replay(self, events, state=None):
        if not isinstance(events, list) or len(events) > 10000:
            raise ValueError("EVENT_LIMIT")
        current = self.initial() if state is None else self._state(state)
        results = []
        for event in events:
            result = self.step(current, event)
            results.append(result)
            current = result["state"]
        return {"state": current, "results": results}

    def checkpoint(self, events):
        replay = self.replay(events)
        return {"schema": "axm.code-system-checkpoint/v0.1", "system_sha256": self.config["system_sha256"],
                "events": deepcopy(events), "state": replay["state"]}

    def restore(self, checkpoint):
        if not isinstance(checkpoint, dict) or set(checkpoint) != {"schema", "system_sha256", "events", "state"}:
            raise ValueError("CHECKPOINT_INVALID")
        if checkpoint["schema"] != "axm.code-system-checkpoint/v0.1" or checkpoint["system_sha256"] != self.config["system_sha256"]:
            raise ValueError("CHECKPOINT_SYSTEM_MISMATCH")
        self._state(checkpoint["state"])
        replay = self.replay(checkpoint["events"])
        if not same(replay["state"], checkpoint["state"]):
            raise ValueError("CHECKPOINT_REPLAY_MISMATCH")
        return deepcopy(replay["state"])

    def explore(self):
        contract = self.spec["exploration"]
        initial = self.initial()
        queue = deque([(initial, [])])
        seen = {key(initial)}
        edges = applied = holds = frontier = 0
        covered = set()
        accepted_events = set()
        phases = {initial["phase"]}

        def report(status, counterexample=None):
            return {"status": status, "states": len(seen), "edges": edges, "applied": applied, "holds": holds,
                    "depth_frontier": frontier, "max_depth": contract["max_depth"], "phases": sorted(phases),
                    "transitions": [json.loads(row) for row in sorted(covered)], "accepted_events": sorted(accepted_events), "counterexample": counterexample}

        while queue:
            state, trace = queue.popleft()
            if len(trace) == contract["max_depth"]:
                frontier += 1
                continue
            for event in contract["events"]:
                if edges >= contract["max_edges"]:
                    return report("BUDGET_EXHAUSTED")
                result = self.step(state, event)
                edges += 1
                if result["status"] not in {"APPLIED", "HOLD_NO_TRANSITION", "HOLD_GUARD"}:
                    return report("COUNTEREXAMPLE", {"events": trace + [deepcopy(event)], "before": state, "result": result})
                if result["status"] != "APPLIED":
                    holds += 1
                    continue
                applied += 1
                accepted_events.add(event["type"])
                covered.add(key(result["transition"]))
                phases.add(result["state"]["phase"])
                state_key = key(result["state"])
                if state_key not in seen:
                    if len(seen) >= contract["max_states"]:
                        return report("BUDGET_EXHAUSTED")
                    seen.add(state_key)
                    queue.append((result["state"], trace + [deepcopy(event)]))
        return report("BOUNDED_COMPLETE")

    def observe(self):
        scenarios, input_unchanged = [], True
        for scenario in self.spec["scenarios"]:
            current, actual, events = self.initial(), [], []
            for step in scenario["steps"]:
                before_state, before_event = deepcopy(current), deepcopy(step["event"])
                result = self.step(current, step["event"])
                input_unchanged &= same(current, before_state) and same(step["event"], before_event)
                actual.append(result)
                events.append(step["event"])
                current = result["state"]
            replay = self.replay(events)
            cut = len(events) // 2
            restored = self.restore(self.checkpoint(events[:cut]))
            resumed = self.replay(events[cut:], restored)
            scenarios.append({"id": scenario["id"], "steps": actual, "replay_equal": same(replay["results"], actual),
                              "recovery_equal": same(resumed["results"], actual[cut:]) and same(self.restore(self.checkpoint(events)), current)})
        return {"system_sha256": self.config["system_sha256"], "scenarios": scenarios,
                "input_unchanged": input_unchanged, "exploration": self.explore()}

    def verify(self):
        observed, issues = self.observe(), []
        coverage, events = set(), set()
        for expected, actual in zip(self.spec["scenarios"], observed["scenarios"]):
            if not actual["replay_equal"] or not actual["recovery_equal"]:
                issues.append({"code": "REPLAY_OR_RECOVERY", "scenario": expected["id"]})
            for index, (step, output) in enumerate(zip(expected["steps"], actual["steps"])):
                if not all(same(output.get(field), value) for field, value in step["expect"].items()):
                    issues.append({"code": "SCENARIO_EXPECTATION", "scenario": expected["id"], "step": index})
                if output["status"] == "APPLIED":
                    coverage.add(key(output["transition"])); events.add(step["event"]["type"])
        exploration = observed["exploration"]
        if exploration["status"] != "BOUNDED_COMPLETE":
            issues.append({"code": "EXPLORATION_" + exploration["status"]})
        coverage.update(key(row) for row in exploration["transitions"])
        events.update(exploration["accepted_events"])
        required = {key({k: row[k] for k in ("from", "event", "to")}) for row in self.spec["machine"]["transitions"]}
        if required - coverage or {row["event"] for row in self.spec["bindings"]} - events:
            issues.append({"code": "TRANSITION_COVERAGE_INCOMPLETE"})
        if not observed["input_unchanged"]:
            issues.append({"code": "INPUT_MUTATED"})
        return {"status": "PASS" if not issues else "HOLD", "issues": issues, "observations": observed}


def load():
    import hashlib
    from pathlib import Path
    folder = Path(__file__).resolve().parent
    lock = json.loads((folder / "source-lock.json").read_text(encoding="utf-8"))
    for name in ("runtime.py", "module.py", "system.json"):
        if hashlib.sha256((folder / name).read_bytes()).hexdigest() != lock.get(name):
            raise ValueError("RUNTIME_SOURCE_CHANGED:" + name)
    # Execute the checked source bytes, avoiding stale/tampered bytecode caches
    # and global module-name collisions between independent generated products.
    namespace = {"__name__": "uc_code_" + lock["module.py"], "__file__": str(folder / "module.py")}
    exec(compile((folder / "module.py").read_bytes(), str(folder / "module.py"), "exec"), namespace)
    config = json.loads((folder / "system.json").read_text(encoding="utf-8"))
    return System(config, namespace["FUNCTIONS"])


if __name__ == "__main__":
    import sys
    from pathlib import Path
    try:
        system = load()
        if len(sys.argv) == 1 or sys.argv[1:] == ["verify"]:
            result = system.verify()
        elif sys.argv[1:] == ["observe"]:
            result = system.observe()
        elif len(sys.argv) == 3 and sys.argv[1] in {"replay", "checkpoint", "restore"}:
            raw = Path(sys.argv[2]).read_bytes()
            if len(raw) > 1048576:
                raise ValueError("REQUEST_BYTES_LIMIT")
            def invalid_constant(value):
                raise ValueError("JSON_NONFINITE:" + value)
            result = getattr(system, sys.argv[1])(json.loads(raw, parse_constant=invalid_constant))
        else:
            raise ValueError("usage: runtime.py [verify | replay events.json | checkpoint events.json | restore checkpoint.json]")
        output = json.dumps(result, sort_keys=True, ensure_ascii=False, allow_nan=False)
        if len(output.encode()) > 8 * 1048576:
            raise ValueError("RESULT_BYTES_LIMIT")
        print(output)
        if result.get("status") == "HOLD":
            sys.exit(1)
    except (ValueError, TypeError, OSError, KeyError) as error:
        print(json.dumps({"status": "HOLD", "error": str(error)[:300]}), file=sys.stderr)
        sys.exit(2)

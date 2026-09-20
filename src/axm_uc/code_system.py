"""Create portable stateful software/game systems over bundled code professionals."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from .code_system_contract import SCHEMA, canonical, digest, exact, prepare, retain_system, validate_archive
from .data.code_system.runtime import same
from .grammar_workbench import run_grammar_tool
from .state_machine import StateMachineError

WORKFLOW_SCHEMA = "axm.code-system-workflow/v0.1"
RUNTIME = Path(__file__).parent / "data/code_system"
STATIONS = [
    {"id": "system-contract", "profession": "software-architect", "procedure": "Bind the typed model, guards, reducers and route selectors to an explicit state graph."},
    {"id": "code-workflow", "profession": "six bundled coding procedures", "procedure": "Typecheck, compile twice, build, execute requirement cases, assess and optionally retain function closures."},
    {"id": "state-exploration", "profession": "game-systems-designer", "procedure": "Explore the declared finite event alphabet breadth-first; measure states/edges and preserve shortest failing traces."},
    {"id": "system-evidence", "profession": "software-qa-playtest", "procedure": "Compare declared step oracles, repeats, languages, input preservation, replay, recovery and observed transition coverage."},
    {"id": "system-retention", "profession": "software-maintainer", "procedure": "Retain verified construction and semantically deduplicated behavior composition on explicit request."},
]


def _files(root, system, workflow):
    plan = workflow["build"]["plan"]
    behavior = {key: system[key] for key in ("initial_model", "machine", "bindings", "invariants")}
    hosts = {suffix: (RUNTIME / ("runtime." + suffix)).read_text(encoding="utf-8") for suffix in ("js", "py")}
    host_hashes = {suffix: hashlib.sha256(source.encode()).hexdigest() for suffix, source in hosts.items()}
    config = {"system": system, "system_sha256": digest({"program": plan["program"], "behavior": behavior, "hosts": host_hashes})}
    files = {}
    for target in workflow["build"]["targets"]:
        language = target["language"]
        suffix = "js" if language == "javascript" else "py"
        for artifact in target["artifacts"]:
            files[language + "/" + artifact["path"]] = artifact["content"]
        files[language + "/runtime." + suffix] = hosts[suffix]
        files[language + "/system.json"] = canonical(config) + "\n"
        lock = {name: hashlib.sha256(files[language + "/" + name].encode()).hexdigest()
                for name in ("module." + suffix, "runtime." + suffix, "system.json")}
        files[language + "/source-lock.json"] = canonical(lock) + "\n"
    return config, files


def _execute(files, language, run):
    """Fresh fixed commands against emitted source, not caller-supplied receipts."""
    node = shutil.which("node")
    command = [node, "runtime.js", "observe"] if language == "javascript" else [sys.executable, "runtime.py", "observe"]
    with tempfile.TemporaryDirectory(prefix="uc-code-system-") as temp:
        folder = Path(temp)
        prefix = language + "/"
        for name, content in files.items():
            if name.startswith(prefix):
                (folder / name[len(prefix):]).write_text(content, encoding="utf-8", newline="\n")
        # Output goes to temporary files so a failed observer cannot fill memory.
        with tempfile.TemporaryFile() as out, tempfile.TemporaryFile() as err:
            try:
                completed = subprocess.run(command, cwd=folder, stdin=subprocess.DEVNULL, stdout=out, stderr=err, timeout=20, check=False)
            except subprocess.TimeoutExpired:
                return {"language": language, "run": run, "status": "HOLD", "error": "SYSTEM_OBSERVER_TIMEOUT"}
            out.seek(0); err.seek(0)
            body, errors = out.read(8 * 1048576 + 1), err.read(4096)
        if completed.returncode or len(body) > 8 * 1048576:
            return {"language": language, "run": run, "status": "HOLD", "error": errors.decode(errors="replace") or "SYSTEM_OBSERVER_OUTPUT_LIMIT"}
        return {"language": language, "run": run, "status": "OBSERVED", "output": json.loads(body)}


def assess(system, config, observations, languages):
    """Compare observations with authored oracles outside the generated runtime."""
    issues, cases = [], []
    if len(observations) != len(languages) * 2:
        issues.append({"code": "OBSERVATIONS_INCOMPLETE"})
    baseline = None
    observed_transitions, accepted_events = set(), set()
    for observation in observations:
        context = {key: observation[key] for key in ("language", "run")}
        if observation["status"] != "OBSERVED":
            issues.append({"code": "EXECUTION_FAILED", **context, "detail": observation.get("error")})
            continue
        output = observation["output"]
        if output.get("system_sha256") != config["system_sha256"] or output.get("input_unchanged") is not True:
            issues.append({"code": "SYSTEM_OR_INPUT_IDENTITY", **context})
        if baseline is None:
            baseline = output
        elif not same(baseline, output):
            issues.append({"code": "REPEAT_OR_LANGUAGE_DIVERGENCE", **context})
        actual_scenarios = output.get("scenarios", [])
        if [row.get("id") for row in actual_scenarios] != [row["id"] for row in system["scenarios"]]:
            issues.append({"code": "SCENARIOS_INCOMPLETE", **context})
            continue
        for scenario, observed in zip(system["scenarios"], actual_scenarios):
            if observed.get("replay_equal") is not True or observed.get("recovery_equal") is not True:
                issues.append({"code": "REPLAY_OR_RECOVERY_MISMATCH", "scenario": scenario["id"], **context})
            if len(observed.get("steps", [])) != len(scenario["steps"]):
                issues.append({"code": "SCENARIO_STEPS_INCOMPLETE", "scenario": scenario["id"], **context})
                continue
            for index, (step, actual) in enumerate(zip(scenario["steps"], observed["steps"])):
                expected = step["expect"]
                passed = all(same(actual.get(field), wanted) for field, wanted in expected.items())
                cases.append({**context, "scenario": scenario["id"], "step": index, "passed": passed})
                if not passed:
                    issues.append({"code": "SCENARIO_EXPECTATION", **context, "scenario": scenario["id"], "step": index, "expected": expected, "actual": actual})
                if actual["status"] == "APPLIED":
                    observed_transitions.add(canonical(actual["transition"]))
                    accepted_events.add(step["event"]["type"])
        explored = output.get("exploration", {})
        if explored.get("status") != "BOUNDED_COMPLETE":
            issues.append({"code": "EXPLORATION_" + str(explored.get("status", "MISSING")), **context,
                           "counterexample": explored.get("counterexample")})
        observed_transitions.update(canonical(row) for row in explored.get("transitions", []))
        accepted_events.update(explored.get("accepted_events", []))
    required_transitions = {canonical({key: row[key] for key in ("from", "event", "to")}) for row in system["machine"]["transitions"]}
    missing = required_transitions - observed_transitions
    missing_events = {row["event"] for row in system["bindings"]} - accepted_events
    if missing or missing_events:
        issues.append({"code": "TRANSITION_COVERAGE_INCOMPLETE", "transitions": [json.loads(row) for row in sorted(missing)], "events": sorted(missing_events)})
    return {"status": "PASS" if not issues else "HOLD", "issues": issues, "case_checks": cases,
            "observed_transition_count": len(observed_transitions), "required_transition_count": len(required_transitions),
            "observations": observations, "scope": "Authored scenarios and invariants over the declared event alphabet through the stated depth; not arbitrary inputs or whole-program correctness."}


def operate_code_system(root, raw):
    stages = []
    try:
        if len(canonical(raw).encode()) > 1048576:
            raise ValueError("code-system request exceeds 1 MiB")
        if isinstance(raw, dict) and raw.get("action") == "catalog":
            exact(raw, {"action"})
            return {"schema": WORKFLOW_SCHEMA, "status": "CATALOG", "system_schema": SCHEMA,
                    "actions": ["build", "verify", "retain", "restore"], "stations": STATIONS,
                    "languages": ["javascript", "python"], "domains": ["software", "game"], "ai_required": False}
        if isinstance(raw, dict) and raw.get("action") == "restore":
            exact(raw, {"action", "system_archive", "structural_sha256"})
            archive = validate_archive(raw["system_archive"])
            row = next((entry for entry in archive["entries"] if entry["structural_sha256"] == raw["structural_sha256"]), None)
            if row is None:
                raise ValueError("retained system identity is absent")
            return {"schema": WORKFLOW_SCHEMA, "status": "RESTORED_CONSTRUCTION", "request": deepcopy(row["construction"]), "verification": "REQUIRES_FRESH_EXECUTION"}
        request, graph = prepare(raw)
        stages.append({"id": "system-contract", "status": "CONTRACT_READY", "state_graph": graph})
        workflow_request = {"action": request["action"], "job": request["job"]}
        if "archive" in request:
            workflow_request["archive"] = request["archive"]
        if "system_archive" in request:
            validate_archive(request["system_archive"])
        workflow = run_grammar_tool(root, "code-workflow", workflow_request)
        stages.append({"id": "code-workflow", "status": workflow["result"], "stations": workflow["stations"]})
        result = {"schema": WORKFLOW_SCHEMA, "status": "HOLD", "stages": stages, "code_workflow": workflow,
                  "verification": None, "retention": None, "files": {}}
        if workflow["result"] not in {"CANDIDATE", "VERIFIED_FOR_CASES"}:
            return result
        config, files = _files(root, request["system"], workflow)
        result.update({"system_sha256": config["system_sha256"], "files": files, "status": "CANDIDATE"})
        if request["action"] != "build":
            languages = workflow["build"]["plan"]["languages"]
            observations = [_execute(files, language, run) for language in languages for run in (1, 2)]
            verification = assess(request["system"], config, observations, languages)
            result["verification"] = verification
            explored = all(row.get("output", {}).get("exploration", {}).get("status") == "BOUNDED_COMPLETE" for row in observations)
            stages.append({"id": "state-exploration", "status": "PASS" if explored else "HOLD"})
            stages.append({"id": "system-evidence", "status": verification["status"], "transitions": verification["observed_transition_count"]})
            result["status"] = "VERIFIED_FOR_SCENARIOS" if verification["status"] == "PASS" else "HOLD"
            if verification["status"] != "PASS":
                result["files"] = {}
                return result
            if request["action"] == "retain":
                result["retention"] = retain_system(request.get("system_archive"), request["system"],
                    workflow["retention"]["captured"], raw, verification)
                stages.append({"id": "system-retention", "status": result["retention"]["status"]})
        result["artifact_sha256"] = {name: hashlib.sha256(content.encode()).hexdigest() for name, content in sorted(files.items())}
        return result
    except (ValueError, TypeError, KeyError, AttributeError, OSError, StateMachineError, RecursionError) as exc:
        return {"schema": WORKFLOW_SCHEMA, "status": "HOLD", "stages": stages, "diagnostic": str(exc)[:1000], "files": {}, "retention": None}


def create_code_system_project(root, inputs):
    from .capabilities import CapabilityError, _is_machine_body_path, _resolve_output_path, builtin_write_project
    try:
        exact(inputs, {"path", "request"})
        if not isinstance(inputs["path"], str) or not inputs["path"].strip():
            raise ValueError("path must be a nonempty string")
        target = _resolve_output_path(Path(root), inputs["path"])
        if _is_machine_body_path(Path(root), target) or target.exists():
            raise ValueError("code-system project must be a new directory outside the machine body")
        report = operate_code_system(root, inputs["request"])
        if report["status"] not in {"CANDIDATE", "VERIFIED_FOR_SCENARIOS"}:
            raise CapabilityError("code-system workflow did not pass", {"workflow": report})
        files = report.pop("files")
        files["request.json"] = canonical(inputs["request"]) + "\n"
        files["workflow.json"] = canonical(report) + "\n"
        files["construction.json"] = canonical({"system": inputs["request"]["system"], "program": report["code_workflow"]["build"]["plan"]["program"]}) + "\n"
        files["LICENSE-UC.txt"] = (Path(root) / "LICENSE").read_text(encoding="utf-8")
        files["CREATOR_OUTPUT_PERMISSION.md"] = (Path(root) / "CREATOR_OUTPUT_PERMISSION.md").read_text(encoding="utf-8")
        files["LICENSE-GRAMMAR-MPL-2.0.txt"] = (Path(root) / "third_party/code-professions/source/LICENSE").read_text(encoding="utf-8")
        files["NOTICE.txt"] = "Copyright 2026 Mike - Axiom/Mir.\nGenerated with AXM Universal Creation and bundled Grammar 102 / Profession Fabric.\nGrammar modules retain MPL-2.0; UC session-host sources retain UC's attached license.\nThe existing creator-output permission and its runtime-code boundary are attached without alteration.\nExact donor provenance and source identities are in workflow.json. No third-party runtime package is required.\n"
        files["README.md"] = _readme(inputs["request"], report)
        if report["retention"] is not None:
            files["system-archive.json"] = canonical(report["retention"]["archive"]) + "\n"
            files["archive.json"] = canonical(report["code_workflow"]["retention"]["archive"]) + "\n"
        result = builtin_write_project(root, {"path": inputs["path"], "files": files, "project_type": "generic", "publish_mode": "validated", "replace": False})
        result["code_system"] = {"status": report["status"], "system_sha256": report["system_sha256"], "verification": report["verification"],
                                 "retained": report["retention"] is not None, "evidence": "workflow.json"}
        return result
    except (ValueError, TypeError, OSError) as exc:
        raise CapabilityError(str(exc)) from exc


def run_code_system_station(root, inputs):
    """Typed workflow-discovery station backed by actual system execution."""
    from .atlas_pipeline import _output
    from .atomic import atomic_write_json
    exact(inputs, {"operation", "path", "values"})
    exact(inputs["values"], {"request"})
    request = inputs["values"]["request"]
    if inputs["operation"] != "verify-code-system" or not isinstance(request, dict) or request.get("action") not in {"verify", "retain"}:
        raise ValueError("code-system station requires explicit verify or retain execution")
    target = _output(root, inputs["path"])
    target.mkdir(parents=True, exist_ok=False)
    atomic_write_json(target / "inputs.json", inputs["values"])
    project = target / "project"
    evidence = create_code_system_project(root, {"path": str(project), "request": request})
    verification = evidence["code_system"]["verification"]
    observations = verification["observations"]
    measured = observations[0]["output"]
    metrics = {"scenarios": len(measured["scenarios"]),
               "scenario_steps": sum(len(row["steps"]) for row in measured["scenarios"]),
               "transitions": verification["observed_transition_count"],
               "transition_coverage": verification["observed_transition_count"] / verification["required_transition_count"],
               "explored_states": measured["exploration"]["states"], "explored_edges": measured["exploration"]["edges"],
               "exploration_depth": measured["exploration"]["max_depth"],
               "languages": len({row["language"] for row in observations}),
               "artifact_bytes": sum(path.stat().st_size for path in project.rglob("*") if path.is_file())}
    result = {"status": "PASS", "value": str(project), "metrics": metrics, "evidence": evidence}
    atomic_write_json(target / "observation.json", result)
    return result


def _readme(request, report):
    return ("# " + request["job"]["id"] + "\n\nPortable " + request["system"]["domain"] + " system: `" + report["status"] + "`.\n\n"
            "The generated modules and session hosts need only Node.js or Python, independently of UC.\n\n"
            "```sh\nnode javascript/runtime.js verify\npython python/runtime.py verify\nnode javascript/runtime.js replay events.json\npython python/runtime.py checkpoint events.json\nnode javascript/runtime.js restore checkpoint.json\n```\n\n"
            "Choose the commands for the languages requested in your construction. An event is `{\"type\":\"eventName\",\"args\":[]}`; event files contain arrays. "
            "`verify` compares scenarios, exploration and recovery and exits nonzero on failure. `observe` emits raw measurements; UC independently assesses them against the authored expectations.\n\n"
            "Library: JavaScript `require('./javascript/runtime').load()`; Python `runtime.load()` with `python/` on the import path. "
            "Both expose initial, step, replay, checkpoint, restore, explore, observe and verify. Refused steps leave state unchanged. Replay records refusals and continues. "
            "Effects are returned as data and never performed. The loader checks the emitted source bytes before use. Checkpoints bind this program/behavior/host version and re-execute their history before restoring state; these checks are not authentication.\n\n"
            "Keep typed construction and explicit cases when reshaping this output. Retained archives preserve construction, not only generated text. "
            "Exploration covers the stated finite alphabet and depth, not all inputs, arbitrary timing, balance, visuals, external side effects or whole-program correctness.\n")

"""Goal-bound blueprint execution and reusable, rechecked construction experience."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .atomic import atomic_write_json
from .creation_atlas import CreationAtlas, REFERENCE_DEPENDENCIES, canonical, digest, local_file, runtime_pin, strings, text

PLAN_SCHEMA = "axm.atlas-intent-plan/v0.1"
RUN_SCHEMA = "axm.atlas-creation-run/v0.1"
EXPERIENCE_SCHEMA = "axm.atlas-experience/v0.1"


def _relative(value):
    value = text(value, "output path")
    path = Path(value)
    if path.is_absolute() or ".." in path.parts or "\\" in value or value in {".", ""}:
        raise ValueError("blueprint output must be a non-empty relative path")
    if path.parts[0] in {"intent.json", "run.json", "experience.json"}:
        raise ValueError("blueprint output conflicts with retained pipeline state")
    return path.as_posix()


def _output(root, value):
    from .capabilities import _is_machine_body_path, _resolve_output_path
    path = _resolve_output_path(Path(root), text(value, "path"))
    if _is_machine_body_path(Path(root), path):
        raise ValueError("atlas creation cannot rewrite the live machine body")
    return path


def _at(value, path):
    if not isinstance(path, list) or len(path) > 32:
        raise ValueError("field path must be a list with at most 32 components")
    for key in path:
        if isinstance(value, dict) and isinstance(key, str) and key in value:
            value = value[key]
        elif isinstance(value, list) and type(key) is int and 0 <= key < len(value):
            value = value[key]
        else:
            raise ValueError("referenced field is absent: " + str(path))
    return deepcopy(value)


def _parameters(value, atlas, used):
    if isinstance(value, dict) and "atlas" in value:
        if set(value) - {"atlas", "path"}:
            raise ValueError("atlas parameter accepts only atlas and path")
        entry = atlas.get(value["atlas"])
        used.add(entry["id"])
        # A loaded value is literal data, never recursively evaluated as bindings.
        return _at(entry["data"], value.get("path", []))
    if isinstance(value, dict):
        return {key: _parameters(child, atlas, used) for key, child in value.items()}
    if isinstance(value, list):
        return [_parameters(child, atlas, used) for child in value]
    return deepcopy(value)


def _bindings(value, parameters, results, target):
    from .capabilities import _resolve_binding
    if isinstance(value, dict) and "output" in value:
        if set(value) != {"output"}:
            raise ValueError("output binding accepts only output")
        path = target / _relative(value["output"])
        if not path.resolve().is_relative_to(target.resolve()):
            raise ValueError("output binding leaves the creation directory")
        return str(path)
    if isinstance(value, dict) and "from" in value:
        return _resolve_binding(value, parameters, results)
    if isinstance(value, dict):
        return {key: _bindings(child, parameters, results, target) for key, child in value.items()}
    if isinstance(value, list):
        return [_bindings(child, parameters, results, target) for child in value]
    return deepcopy(value)


def _binding_refs(value):
    if isinstance(value, dict):
        if "from" in value:
            if set(value) - {"from", "default"} or not isinstance(value["from"], str):
                raise ValueError("blueprint bindings accept from and optional default")
            yield value
        elif "output" in value:
            if set(value) != {"output"}:
                raise ValueError("invalid output binding")
            _relative(value["output"])
        else:
            for child in value.values():
                yield from _binding_refs(child)
    elif isinstance(value, list):
        for child in value:
            yield from _binding_refs(child)


def _check_contract(check, step_ids, artifacts):
    if not isinstance(check, dict):
        raise ValueError("goal checks must be objects")
    if "artifact" in check:
        if set(check) != {"artifact"} or check["artifact"] not in artifacts:
            raise ValueError("goal check references an unknown artifact")
        return
    if set(check) - {"step", "path", "equals", "min", "max"} or check.get("step") not in step_ids:
        raise ValueError("goal check references an unknown step or unsupported field")
    path = check.get("path")
    if not isinstance(path, list) or not path or len(path) > 32 or any(type(k) not in {str, int} for k in path):
        raise ValueError("goal check needs a field path")
    comparisons = set(check) & {"equals", "min", "max"}
    if not comparisons or ("equals" in comparisons and len(comparisons) > 1):
        raise ValueError("goal check needs equals or numeric bounds")
    for key in ("min", "max"):
        if key in check and (type(check[key]) not in {int, float} or not math.isfinite(check[key])):
            raise ValueError("check bounds must be finite numbers")
    if check.get("min", -math.inf) > check.get("max", math.inf):
        raise ValueError("check minimum exceeds maximum")


def _validate_blueprint(blueprint):
    allowed = {"id", "version", "purpose", "direction", "parameters", "defaults", "uses", "steps", "goals", "artifacts", "limitations"}
    if not isinstance(blueprint, dict) or set(blueprint) - allowed:
        raise ValueError("unsupported blueprint fields")
    for field in ("id", "version", "purpose", "direction"):
        text(blueprint.get(field), "blueprint " + field)
    parameters, defaults = blueprint.get("parameters"), blueprint.get("defaults", {})
    if not isinstance(parameters, dict) or not isinstance(defaults, dict) or set(defaults) - set(parameters):
        raise ValueError("blueprint parameters/defaults must agree")
    for name, kind in parameters.items():
        text(name, "parameter")
        if kind not in {"object", "array", "string", "number", "boolean"}:
            raise ValueError("unsupported parameter type")
    strings(blueprint.get("uses", []), "blueprint uses")
    steps = blueprint.get("steps")
    if not isinstance(steps, list) or not 1 <= len(steps) <= 32:
        raise ValueError("blueprint requires 1..32 steps")
    ordered, by_id = [], {}
    for step in steps:
        if not isinstance(step, dict) or set(step) != {"id", "capability", "depends_on", "inputs", "checks"}:
            raise ValueError("step requires id, capability, depends_on, inputs and checks")
        identity = text(step["id"], "step id")
        if "." in identity or identity in by_id:
            raise ValueError("step ids must be unique and cannot contain dots")
        text(step["capability"], "capability")
        strings(step["depends_on"], "step dependencies")
        if not isinstance(step["inputs"], dict) or not isinstance(step["checks"], list):
            raise ValueError("invalid step inputs/checks")
        by_id[identity] = step
    pending = set(by_id)
    while pending:
        ready = sorted(key for key in pending if set(by_id[key]["depends_on"]) <= set(ordered))
        if not ready:
            raise ValueError("blueprint has cyclic or missing step dependencies")
        ordered.extend(ready)
        pending.difference_update(ready)
    ancestors = {}
    for identity in ordered:
        step = by_id[identity]
        ancestors[identity] = set(step["depends_on"])
        for parent in step["depends_on"]:
            ancestors[identity].update(ancestors[parent])
        for ref in _binding_refs(step["inputs"]):
            parts = ref["from"].split(".")
            if len(parts) < 2 or parts[0] not in {"request", "steps"}:
                raise ValueError("binding must name an explicit request field or prior step")
            if parts[0] == "request" and parts[1] not in parameters:
                raise ValueError("binding references an undeclared parameter")
            if parts[0] == "steps" and parts[1] not in ancestors[identity]:
                raise ValueError("step binding must name a dependency")
        for check in step["checks"]:
            _check_contract(check, {identity}, {})
    artifacts = blueprint.get("artifacts", {})
    if not isinstance(artifacts, dict) or len(artifacts) > 64:
        raise ValueError("artifacts must map at most 64 names to relative files")
    for value in artifacts.values():
        _relative(value)
    goals = blueprint.get("goals")
    if not isinstance(goals, dict) or not 1 <= len(goals) <= 32:
        raise ValueError("blueprint needs 1..32 goals tied to checks")
    for goal, checks in goals.items():
        text(goal, "goal")
        if not isinstance(checks, list) or not checks:
            raise ValueError("every goal needs an observable check")
        for check in checks:
            _check_contract(check, by_id, artifacts)
    return [deepcopy(by_id[key]) for key in ordered]


def _capability_gaps(atlas, identity, seen=None):
    from .capabilities import BUILTINS
    seen = set() if seen is None else set(seen)
    if identity in seen:
        return ["capability dependency cycle: " + identity]
    seen.add(identity)
    record = atlas.records.get("capability:" + identity)
    if record is None:
        return ["missing capability: " + identity]
    manifest, gaps = record["data"], []
    impl = manifest.get("implementation", {})
    kind = impl.get("kind")
    dependencies = list(manifest.get("dependencies", []))
    if kind in {"DETERMINISTIC_SOURCE", "LOCAL_PROVIDER_BOUNDARY", "EXTERNAL_EVIDENCE_BOUNDARY"}:
        if impl.get("entrypoint") not in BUILTINS:
            gaps.append("entrypoint unavailable: " + identity)
        if impl.get("entrypoint") == "builtin:creation_atlas":
            gaps.append("blueprint cannot recursively invoke the atlas pipeline")
    elif kind == "DETERMINISTIC_ALIAS":
        dependencies.append(impl.get("delegate", ""))
    elif kind == "DETERMINISTIC_COMPOSITE":
        dependencies.extend(s.get("capability", "") for s in impl.get("steps", []))
    else:
        gaps.append("unsupported capability implementation: " + identity)
    for dependency in sorted(set(dependencies)):
        if dependency in REFERENCE_DEPENDENCIES:
            if REFERENCE_DEPENDENCIES[dependency] not in atlas.records:
                gaps.append("missing source registry: " + dependency)
        else:
            gaps.extend(_capability_gaps(atlas, dependency, seen))
    return sorted(set(gaps))


def _preflight(step, parameters, atlas, used):
    """Ask existing domain contracts about readiness without performing creation."""
    if any(ref["from"].startswith("steps.") for ref in _binding_refs(step["inputs"])):
        return []
    from .capabilities import CapabilityError, CapabilityStore
    try:
        inputs = _bindings(step["inputs"], parameters, {}, Path("/atlas-planning-only"))
        manifest = atlas.get("capability:" + step["capability"])["data"]
        missing = CapabilityStore.missing_required_inputs(manifest, inputs)
        if missing:
            return ["step " + step["id"] + " missing input: " + key for key in missing]
        if step["capability"] == "AXM-CAP-CONSTRUCTION-SEARCH":
            from .construction_search import _validate
            _validate(inputs["search"])
        elif step["capability"] == "AXM-CAP-COMPOSE-ORGAN-PROJECT":
            from .organ_discovery import discover_interface_assembly
            result = discover_interface_assembly(atlas.root, inputs["organ_goal"])
            if result["status"] != "READY_EXACT_INTERFACE_ASSEMBLY":
                return ["organ goal: " + result["status"]]
            used.update("organ:" + ref for ref in result["selected_candidate"]["package_refs"])
        elif step["capability"] == "AXM-CAP-CODE-PROGRAM-PROJECT":
            import shutil
            if shutil.which("node") is None:
                return ["typed-code workflow needs an installed Node runtime"]
            if inputs["request"].get("action") not in {"verify", "retain"}:
                return ["verified-code blueprint requires an explicit verify or retain action"]
        elif step["capability"] == "AXM-CAP-CODE-SYSTEM-PROJECT":
            import shutil
            from .code_system_contract import prepare
            from .state_machine import StateMachineError
            if shutil.which("node") is None:
                return ["code-system workflow needs an installed Node runtime"]
            if inputs["request"].get("action") not in {"verify", "retain"}:
                return ["code-system blueprint requires an explicit verify or retain action"]
            try:
                prepare(inputs["request"])
            except (ValueError, TypeError, KeyError, AttributeError, StateMachineError) as exc:
                return ["code-system contract: " + str(exc)]
    except (CapabilityError, ValueError, RuntimeError, KeyError) as exc:
        return ["step " + step["id"] + ": " + str(exc)]
    return []


def _experience(root, memory):
    if memory is None:
        return [], []
    folder = _output(root, memory)
    if folder.exists() and not folder.is_dir():
        raise ValueError("memory path must be a directory")
    paths = sorted(folder.glob("*.json"))
    if len(paths) > 4096:
        raise ValueError("experience collection exceeds 4096 records; select a scoped collection")
    if sum(p.lstat().st_size for p in paths) > 64_000_000:
        raise ValueError("experience collection exceeds 64 MB; select a scoped collection")
    records, ignored = [], []
    for path in paths:
        try:
            value = json.loads(local_file(folder, path.name).read_text())
            if value.get("schema") != EXPERIENCE_SCHEMA or path.stem != digest(value):
                raise ValueError("experience schema or content identity does not match")
            if (value.get("status") not in {"CHECKS_PASSED", "HOLD_FAILED_CHECK", "HOLD_EXECUTION_ERROR"}
                    or not isinstance(value.get("searches"), list) or not isinstance(value.get("intent"), dict)
                    or not all(isinstance(value["intent"].get(k), str) for k in ("purpose", "direction"))
                    or not isinstance(value.get("blueprint"), str)):
                raise ValueError("experience observation is incomplete")
            for seed in value["searches"]:
                if (not isinstance(seed, dict) or not isinstance(seed.get("space_sha256"), str)
                        or not isinstance(seed.get("warm_start"), dict) or not isinstance(seed.get("semantic_signature"), str)):
                    raise ValueError("experience search seed is incomplete")
            records.append(value)
        except (ValueError, OSError) as exc:
            ignored.append({"file": path.name, "reason": str(exc)})
    return records, ignored


def _search_key(search):
    # Goals/budgets may change; the construction space must match exactly.
    return digest({k: search.get(k) for k in ("schema", "recipe", "controls", "motion_probe")})


def plan_intent(root, request, *, memory=None, candidate_blueprint=None):
    from .capabilities import CapabilityStore
    if not isinstance(request, dict) or set(request) - {"purpose", "direction", "goals", "parameters", "blueprint"}:
        raise ValueError("intent accepts purpose, direction, goals, parameters and optional blueprint")
    text(request.get("purpose"), "intent purpose")
    direction = text(request.get("direction"), "intent direction")
    goals = strings(request.get("goals"), "intent goals")
    if not goals or len(goals) > 32 or len(canonical(request).encode()) > 2_000_000:
        raise ValueError("intent requires 1..32 goals and at most 2 MB")
    raw_parameters = request.get("parameters", {})
    if not isinstance(raw_parameters, dict):
        raise ValueError("intent parameters must be an object")
    atlas, candidates = CreationAtlas(root), []
    if candidate_blueprint is not None:
        # Internal composition boundary: normal atlas requests cannot supply this.
        # The workflow planner constructs it from installed typed operators.
        _validate_blueprint(candidate_blueprint)
        identity = candidate_blueprint["id"]
        if identity in atlas.blueprints:
            raise ValueError("candidate blueprint cannot replace an installed blueprint")
        atlas.blueprints[identity] = deepcopy(candidate_blueprint)
        atlas.add("blueprint:" + identity, "blueprint", identity, candidate_blueprint["purpose"],
                  {"scope": "request-composition", "sha256": digest(candidate_blueprint)},
                  data=candidate_blueprint, status="UNTESTED_COMPOSITION",
                  relations=[{"relation": "uses", "target": ref} for ref in candidate_blueprint.get("uses", [])])
    records, ignored = _experience(root, memory)
    atlas.add_experience(records, memory)
    pin = runtime_pin()
    for identity, blueprint in sorted(atlas.blueprints.items()):
        if request.get("blueprint") and identity != request["blueprint"]:
            continue
        if blueprint["direction"] != direction:
            continue
        gaps, used = [], {"blueprint:" + identity}
        steps = _validate_blueprint(blueprint)
        missing_goals = sorted(set(goals) - set(blueprint["goals"]))
        gaps.extend("unbound goal: " + goal for goal in missing_goals)
        params = {**deepcopy(blueprint.get("defaults", {})), **deepcopy(raw_parameters)}
        unknown, missing = set(params) - set(blueprint["parameters"]), set(blueprint["parameters"]) - set(params)
        gaps.extend("unknown parameter: " + key for key in sorted(unknown))
        gaps.extend("missing parameter: " + key for key in sorted(missing))
        try:
            params = _parameters(params, atlas, used)
        except ValueError as exc:
            gaps.append(str(exc))
        for key, value in params.items():
            actual = ("boolean" if type(value) is bool else "object" if isinstance(value, dict) else
                      "array" if isinstance(value, list) else "string" if isinstance(value, str) else
                      "number" if type(value) in {int, float} else "null")
            if key in blueprint["parameters"] and actual != blueprint["parameters"][key]:
                gaps.append("parameter type mismatch: " + key)
        for ref in blueprint.get("uses", []):
            used.add(ref)
            if ref not in atlas.records:
                gaps.append("missing atlas requirement: " + ref)
        for step in steps:
            gaps.extend(_capability_gaps(atlas, step["capability"]))
            manifest = atlas.records.get("capability:" + step["capability"], {}).get("data")
            if manifest:
                gaps.extend("step " + step["id"] + " missing input: " + key
                            for key in CapabilityStore.missing_required_inputs(manifest, step["inputs"]))
            for binding in _binding_refs(step["inputs"]):
                if binding["from"].startswith("request.") and "default" not in binding:
                    try:
                        _at(params, binding["from"].split(".")[1:])
                    except ValueError as exc:
                        gaps.append(str(exc))
            if not gaps:
                gaps.extend(_preflight(step, params, atlas, used))
        candidates.append({"blueprint": identity, "gaps": sorted(set(gaps)), "parameters": params,
                           "steps": steps, "used": sorted(used), "missing_goals": missing_goals})
    candidates.sort(key=lambda c: (len(c["missing_goals"]), len(c["gaps"]), len(c["steps"]), c["blueprint"]))
    chosen = next((candidate for candidate in candidates if not candidate["gaps"]), None)
    selected, reused = None, []
    if chosen:
        blueprint = atlas.blueprints[chosen["blueprint"]]
        parameters = deepcopy(chosen["parameters"])
        search = parameters.get("search")
        if isinstance(search, dict) and search.get("schema") == "axm.construction-search/v0.1":
            key = _search_key(search)
            starts = list(search.get("warm_starts", []))
            for record in records:
                if record.get("runtime_pin") != pin or record.get("status") != "CHECKS_PASSED":
                    continue
                for item in record.get("searches", []):
                    if item.get("space_sha256") == key and item.get("warm_start") not in starts and len(starts) < 16:
                        starts.append(deepcopy(item["warm_start"]))
                        reused.append(digest(record))
            if starts:
                search["warm_starts"] = starts
        closure = atlas.closure(chosen["used"] + ["experience:" + ref for ref in reused])
        selected = {"blueprint": deepcopy(blueprint), "steps": chosen["steps"], "parameters": parameters,
                    "knowledge": closure, "reused_experience": sorted(set(reused))}
    plan = {"schema": PLAN_SCHEMA, "status": "READY" if selected else "HOLD_CAPABILITY_GAP",
            "intent": deepcopy(request), "selected": selected,
            "candidates": [{"blueprint": c["blueprint"], "gaps": c["gaps"]} for c in candidates],
            "gaps": [] if selected else (candidates[0]["gaps"] if candidates else ["no blueprint for direction: " + direction]),
            "runtime_pin": pin, "atlas_snapshot_sha256": atlas.summary()["snapshot_sha256"],
            "experience": {"observations": len(records), "ignored": ignored},
            "selection_rule": "Exact direction and complete declared goals; sufficient routes ordered by step count then id.",
            "boundary": "READY means a bound route. Only execution can supply observed checks; prose is retained, not silently scored."}
    plan["plan_sha256"] = digest(plan)
    return plan


def _observe(check, results, target, artifacts):
    try:
        if "artifact" in check:
            path = local_file(target, artifacts[check["artifact"]])
            return {"check": check, "passed": True, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        value = _at(results[check["step"]], check["path"])
        if "equals" in check:
            passed = canonical(value) == canonical(check["equals"])
        else:
            passed = (type(value) in {int, float} and math.isfinite(value)
                      and check.get("min", -math.inf) <= value <= check.get("max", math.inf))
        return {"check": check, "passed": passed, "observed": value}
    except (ValueError, KeyError, OSError) as exc:
        return {"check": check, "passed": False, "error": str(exc)}


def build_intent(root, request, path, *, memory=None, plan_sha256=None, candidate_blueprint=None):
    from .capabilities import CapabilityError, CapabilityStore
    target = _output(root, path)
    memory_path = _output(root, memory) if memory is not None else None
    if memory_path and (target == memory_path or target in memory_path.parents or memory_path in target.parents):
        raise ValueError("output and experience collection must be separate directories")
    plan = plan_intent(root, request, memory=memory, candidate_blueprint=candidate_blueprint)
    if plan_sha256 is not None and plan_sha256 != plan["plan_sha256"]:
        return {"schema": RUN_SCHEMA, "status": "HOLD_STALE_PLAN", "fresh_plan": plan}
    if plan["status"] != "READY":
        return {"schema": RUN_SCHEMA, "status": plan["status"], "plan": plan}
    if target.exists():
        raise ValueError("atlas creation output already exists")
    selected = plan["selected"]
    blueprint, params = selected["blueprint"], selected["parameters"]
    target.mkdir(parents=True, exist_ok=False)
    atomic_write_json(target / "intent.json", plan)
    results, checks, error, status = {}, [], None, "CHECKS_PASSED"
    store = CapabilityStore(root)
    for step in selected["steps"]:
        try:
            inputs = _bindings(step["inputs"], params, results, target)
            manifest = store.by_id(step["capability"])
            if manifest is None:
                raise ValueError("planned capability is no longer installed")
            results[step["id"]] = store.invoke(manifest, inputs)
            observed = [_observe(c, results, target, blueprint.get("artifacts", {})) for c in step["checks"]]
            checks.extend(observed)
            if not all(c["passed"] for c in observed):
                status = "HOLD_FAILED_CHECK"
                break
        except (CapabilityError, ValueError, RuntimeError, OSError) as exc:
            status, error = "HOLD_EXECUTION_ERROR", {"step": step["id"], "message": str(exc)}
            break
    goals = {goal: [_observe(c, results, target, blueprint.get("artifacts", {})) for c in blueprint["goals"][goal]]
             for goal in request["goals"]}
    if status == "CHECKS_PASSED" and not all(c["passed"] for group in goals.values() for c in group):
        status = "HOLD_FAILED_CHECK"
    files = {}
    for file in sorted(target.rglob("*")):
        if file.is_file():
            relative = file.relative_to(target).as_posix()
            verified = local_file(target, relative)
            files[relative] = hashlib.sha256(verified.read_bytes()).hexdigest()
    searches, code_systems = [], []
    for step in selected["steps"]:
        if step["capability"] == "AXM-CAP-CODE-SYSTEM-PROJECT" and step["id"] in results:
            product = results[step["id"]]
            if product["code_system"].get("retained") and product["code_system"]["status"] == "VERIFIED_FOR_SCENARIOS":
                from .code_system_contract import validate_archive
                relative = (Path(product["path"]) / "system-archive.json").relative_to(target).as_posix()
                archive = validate_archive(json.loads(local_file(target, relative).read_text(encoding="utf-8")))
                # Only the current creation's accepted construction enters this observation.
                report_path = (Path(product["path"]) / "workflow.json").relative_to(target).as_posix()
                report = json.loads(local_file(target, report_path).read_text(encoding="utf-8"))
                key = report["retention"]["structural_sha256"]
                entry = next(row for row in archive["entries"] if row["structural_sha256"] == key)
                code_systems.append({"structural_sha256": key, "construction": entry["construction"],
                    "construction_sha256": entry["construction_sha256"], "verification_sha256": digest(report["verification"]),
                    "scope": report["verification"]["scope"]})
        if step["capability"] != "AXM-CAP-CONSTRUCTION-SEARCH" or step["id"] not in results:
            continue
        report = json.loads(local_file(target, str(Path(results[step["id"]]["report_path"]).relative_to(target))).read_text())
        candidate = report.get("growth_candidate")
        if candidate:
            searches.append({"space_sha256": _search_key(report["search_contract"]),
                "warm_start": candidate["warm_start"], "semantic_signature": candidate["semantic_signature"],
                "checks": report["selected"]["checks"], "recipe": candidate["recipe"]})
    experience = {"schema": EXPERIENCE_SCHEMA, "status": status, "runtime_pin": plan["runtime_pin"],
                  "intent": deepcopy(request), "blueprint": blueprint["id"], "plan_sha256": plan["plan_sha256"],
                  "goals": goals, "error": error, "searches": searches, "code_systems": code_systems,
                  "run_path": str(target), "files": files,
                  "use": "Rechecked search seeds and inspectable observations; no automatic capability or canon admission."}
    atomic_write_json(target / "experience.json", experience)
    if memory_path:
        memory_path.mkdir(parents=True, exist_ok=True)
        atomic_write_json(memory_path / (digest(experience) + ".json"), experience)
    run = {"schema": RUN_SCHEMA, "status": status, "path": str(target), "plan_sha256": plan["plan_sha256"],
           "steps": results, "checks": checks, "goals": goals, "error": error, "files": files,
           "experience_sha256": digest(experience), "reused_experience": selected["reused_experience"],
           "automatic_canon_admission": False,
           "boundary": "Checks cover the declared goals and observed artifacts only. Target, aesthetic and physical claims need their own checks."}
    atomic_write_json(target / "run.json", run)
    return run


def operate_atlas(root, inputs):
    operation = inputs.get("operation", "query")
    if operation in {"plan", "build"}:
        if operation == "plan":
            return plan_intent(root, inputs["intent"], memory=inputs.get("memory"))
        return build_intent(root, inputs["intent"], inputs["path"], memory=inputs.get("memory"),
                            plan_sha256=inputs.get("plan_sha256"))
    if operation == "experience":
        records, ignored = _experience(root, inputs["memory"])
        limit = inputs.get("limit", 20)
        if type(limit) is not int or not 1 <= limit <= 100:
            raise ValueError("experience limit must be 1..100")
        signatures = {s["semantic_signature"] for r in records if r.get("status") == "CHECKS_PASSED"
                      for s in r.get("searches", [])}
        code_signatures = {s["structural_sha256"] for r in records if r.get("status") == "CHECKS_PASSED"
                           for s in r.get("code_systems", [])}
        return {"observations": len(records), "retained_measured_signatures": len(signatures),
                "retained_code_system_signatures": len(code_signatures),
                "records": [{"id": "experience:" + digest(r), "status": r["status"], "intent": r["intent"]["purpose"],
                             "blueprint": r["blueprint"], "run_path": r["run_path"]} for r in records[:limit]],
                "ignored": ignored, "automatic_canon_admission": False}
    atlas = CreationAtlas(root)
    if inputs.get("memory") is not None:
        records, _ = _experience(root, inputs["memory"])
        atlas.add_experience(records, inputs["memory"])
        from .workflow_memory import add_to_atlas
        add_to_atlas(atlas, inputs["memory"])
    if operation == "summary":
        return atlas.summary()
    if operation == "get":
        return atlas.get(inputs["id"])
    if operation == "closure":
        return atlas.closure(strings(inputs["ids"], "ids"))
    if operation == "query":
        return atlas.query(inputs.get("query", ""), inputs.get("categories"), inputs.get("limit", 20))
    raise ValueError("unknown atlas operation")

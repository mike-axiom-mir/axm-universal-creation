"""Reproduce portable software/game builds, a found defect and construction reuse."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.atlas_pipeline import build_intent, operate_atlas
from axm_uc.code_system import operate_code_system
from axm_uc.code_system_contract import canonical
from axm_uc.data.code_system.runtime import same
from axm_uc.workflow_discovery import plan
from axm_uc.workflow_experiments import experiment


def write(path, value):
    path.write_text(json.dumps(value, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8", newline="\n")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def demonstrate(output):
    output = Path(output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    memory, projects = output / "experience", []

    def build(name, intent):
        result = build_intent(ROOT, intent, str(output / name), memory=str(memory))
        require(result["status"] == "CHECKS_PASSED", str(result.get("error", result.get("plan"))))
        project = output / name / "code"
        receipt = json.loads((project / "workflow.json").read_text(encoding="utf-8"))
        outputs = []
        for language, command in (("javascript", ["node", "javascript/runtime.js", "verify"]),
                                  ("python", [sys.executable, "python/runtime.py", "verify"])):
            run = subprocess.run(command, cwd=project, check=False, capture_output=True, text=True, encoding="utf-8", timeout=30)
            require(run.returncode == 0, run.stdout + run.stderr)
            observed = json.loads(run.stdout)
            require(observed["status"] == "PASS", "standalone verifier did not pass")
            outputs.append(observed)
        require(same(*outputs), "standalone JavaScript/Python session observations differ")
        measured = outputs[0]["observations"]
        projects.append({"name": name, "status": receipt["status"], "system_sha256": receipt["system_sha256"],
            "behavior_sha256": receipt["retention"]["structural_sha256"], "source_sha256": receipt["artifact_sha256"],
            "scenarios": len(measured["scenarios"]), "scenario_steps": sum(len(s["steps"]) for s in measured["scenarios"]),
            "standalone_verifiers": "PASS_BOTH_LANGUAGES", "input_unchanged": measured["input_unchanged"],
            "replay_and_recovery": all(s["replay_equal"] and s["recovery_equal"] for s in measured["scenarios"]),
            "exploration": measured["exploration"], "function_atoms": len(receipt["code_workflow"]["retention"]["archive"]["entries"]),
            "system_atoms_in_project_archive": len(receipt["retention"]["archive"]["entries"])})
        return receipt

    for name in ("inventory", "combat"):
        intent = json.loads((ROOT / "examples/creation-atlas" / (name + "-system.json")).read_text())["inputs"]["intent"]
        build(name, intent)

    # The current example oracles deliberately do not cover repeated lethal hits.
    flawed = json.loads((ROOT / "examples/code-systems/combat.json").read_text())
    flawed["action"] = "verify"
    hit = next(f for f in flawed["job"]["program"]["functions"] if f["name"] == "hit")
    hit["body"]["fields"]["health"] = hit["body"]["fields"]["health"]["right"]
    held = operate_code_system(ROOT, flawed)
    require(held["status"] == "HOLD" and held["code_workflow"]["result"] == "VERIFIED_FOR_CASES", "seeded defect was not isolated by sequence exploration")
    require(all(row["passed"] for row in held["verification"]["case_checks"]), "seeded probe unexpectedly failed a scripted scenario")
    failures = [row["output"]["exploration"]["counterexample"] for row in held["verification"]["observations"]]
    require(all(same(failures[0], row) for row in failures[1:]), "counterexample differed across runs or languages")
    write(output / "seeded-defect.json", held)

    patterns = operate_atlas(ROOT, {"operation": "query", "categories": ["code-pattern"], "memory": str(memory)})
    identity = next(row["id"] for row in patterns["entries"] if row["label"] == "inventory-system")
    retained = operate_atlas(ROOT, {"operation": "get", "id": identity, "memory": str(memory)})
    request = copy.deepcopy(retained["data"]["request"])
    request["job"]["id"] = "inventory-with-audit"
    request["system"]["machine"]["transitions"].append({"from": "open", "event": "audit", "to": "open", "effects": [{"type": "audit-requested"}]})
    request["system"]["bindings"].append({"event": "audit", "reducer": "idle"})
    request["system"]["exploration"]["events"].append({"type": "audit", "args": []})
    request["archive"] = json.loads((output / "inventory/code/archive.json").read_text())
    request["system_archive"] = json.loads((output / "inventory/code/system-archive.json").read_text())
    build("inventory-audit", {"purpose": "Compose a new audit command from retained inventory parts without replacing the original.",
        "direction": "software-systems", "goals": ["session-behavior", "invariant-exploration", "portable-recovery", "retained-system"],
        "parameters": {"request": request}})
    require(projects[0]["function_atoms"] == projects[2]["function_atoms"], "reuse unexpectedly created duplicate function atoms")
    require(projects[2]["system_atoms_in_project_archive"] == 2, "new system did not preserve its prior construction")
    knowledge = operate_atlas(ROOT, {"operation": "experience", "memory": str(memory)})
    discovery_request = {"schema": "axm.workflow-experiment/v0.1", "intent": "Create recoverable combat logic in both languages",
        "inputs": {"construction": {"type": {"kind": "code-system-request"},
                                    "values": [json.loads((ROOT / "examples/code-systems/combat.json").read_text())]}},
        "goals": {"session": {"type": {"kind": "stateful-code-project", "quality": "checked"},
            "checks": [{"metric": "transition_coverage", "unit": "ratio", "min": 1, "max": 1},
                       {"metric": "languages", "unit": "count", "min": 2},
                       {"metric": "exploration_depth", "unit": "count", "min": 6}]}},
        "budget": {"trials": 2}}
    write(output / "discovery-request.json", discovery_request)
    discovered = plan(ROOT, discovery_request)
    require(discovered["status"] == "READY", "stateful-code workflow was not discovered")
    experiment_path, workflow_memory = output / "discovered-code", output / "workflow-memory"
    discovered_result = experiment(ROOT, discovery_request, str(experiment_path), memory=str(workflow_memory))
    require(discovered_result["status"] == "VERIFIED_WORKFLOWS", canonical(discovered_result))
    observation = json.loads((experiment_path / discovered_result["selected"]["observation"]).read_text())
    require(all(row["repeatable"] for row in observation["confirmation"]), "discovered system did not reproduce")
    source_paths = ["src/axm_uc/code_system.py", "src/axm_uc/code_system_contract.py", "src/axm_uc/data/code_system/runtime.py",
                    "src/axm_uc/data/code_system/runtime.js", "src/axm_uc/atlas_pipeline.py", "src/axm_uc/creation_atlas.py",
                    "src/axm_uc/workflow_discovery.py", "src/axm_uc/workflow_experiments.py", "atlas/operators/code-systems.json",
                    "examples/code-systems/inventory.json", "examples/code-systems/combat.json", "atlas/code-systems.json",
                    "tools/code_system_demo.py"]
    proof = {"schema": "axm.code-system-proof/v0.1", "status": "PASS", "environment": {"python": platform.python_version(),
        "node": subprocess.check_output(["node", "--version"], text=True).strip(), "platform": platform.system()},
        "sources": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest() for name in source_paths},
        "projects": projects, "seeded_defect": {"change": "Removed the zero clamp from the combat hit reducer.",
        "function_cases": "PASS", "scripted_scenarios": "PASS", "exploration": "COUNTEREXAMPLE", "shortest_trace": failures[0],
        "same_in_both_languages_and_repeats": True}, "retained_code_system_signatures": knowledge["retained_code_system_signatures"],
        "workflow_discovery": {"status": discovered_result["status"], "trials": discovered_result["trials"],
            "operators": [node["operator"] for node in observation["program"]["nodes"]],
            "metrics": observation["cases"][0]["metrics"], "confirmation_repeatable": True,
            "retained_structures": discovered_result["retained_structures"],
            "product_hashes": observation["cases"][0]["product_hashes"]},
        "scope": "Generated code and sessions, finite declared event alphabets, replay/recovery, portable execution and construction reuse. No rendered UI, gameplay balance, timing, external effects or universal correctness claim."}
    write(output / "proof.json", proof)
    return proof


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", help="New directory for full runnable products and evidence")
    args = parser.parse_args()
    print(canonical(demonstrate(args.output)))

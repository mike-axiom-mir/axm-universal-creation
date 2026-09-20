"""Execute connected atlas routes and demonstrate reuse plus an honest failed goal."""
import argparse
import copy
import json
from pathlib import Path

from axm_uc.atlas_pipeline import operate_atlas
from axm_uc.creation_atlas import CreationAtlas
from axm_uc.machine import UniversalCreationMachine


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("directory", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    target = args.directory.resolve()
    target.mkdir(parents=True, exist_ok=False)
    machine = UniversalCreationMachine(root)
    memory = str(target / "experience")
    outcomes = []
    for name, example in (("vessel", "vessel"), ("vessel-reuse", "vessel"),
                          ("walker", "walker"), ("material", "material"), ("software", "software"), ("programming", "programming"),
                          ("impossible-envelope", "vessel")):
        request = json.loads((root / "examples/creation-atlas" / (example + ".json")).read_text())
        request["inputs"].update(path=str(target / name), memory=memory)
        if name == "impossible-envelope":
            search = CreationAtlas(root).get("recipe:vessel")["data"]["value"]
            search["criteria"][0].update(min=50, max=60)
            request["inputs"]["intent"]["parameters"]["search"] = search
        result = machine.create(copy.deepcopy(request))
        if result["type"] != "CREATION_RESULT":
            raise RuntimeError(result)
        run = result["result"]
        expected = "HOLD_FAILED_CHECK" if name == "impossible-envelope" else "CHECKS_PASSED"
        if run["status"] != expected:
            raise RuntimeError(run)
        counts = run["steps"].get("search", {}).get("counts", {})
        outcomes.append({"case": name, "status": run["status"], "files": len(run["files"]),
                         "visited": counts.get("visited"), "reused": len(run["reused_experience"])})
    summary = {"atlas": operate_atlas(root, {"operation": "summary", "memory": memory}),
               "experience": operate_atlas(root, {"operation": "experience", "memory": memory}),
               "outcomes": outcomes}
    (target / "proof.json").write_text(json.dumps(summary, indent=2) + "\n")
    rows = ["| Case | Observed status | Search trials | Reused observations |", "| --- | --- | ---: | ---: |"]
    rows.extend("| {case} | {status} | {trials} | {reused} |".format(**row, trials=row["visited"] if row["visited"] is not None else "n/a")
                for row in outcomes)
    (target / "README.md").write_text(
        "# UC connected atlas proof\n\n"
        "These are actual executions of the installed construction, material and software blueprints. "
        "Each case contains retained intent, source/artifacts, goal checks and an experience record.\n\n"
        + "\n".join(rows) + "\n\n"
        "The second vessel search remeasures saved settings. The impossible envelope still fails. "
        "Seven observations contain two distinct measured construction signatures; repeated use is not counted as a new capability.\n\n"
        "Material evidence covers decoded maps and the stated policy. Software evidence covers exact organ composition and structural project checks. "
        "These do not claim artistic quality, live browser behavior, physical balance or an untested engine.\n\n"
        "Run and memory paths record the original execution location. To reproduce in a current UC checkout: "
        "`PYTHONPATH=src python tools/creation_atlas_demo.py /tmp/uc-atlas-demo`.\n"
    )
    print(json.dumps({"path": str(target), "outcomes": outcomes,
                      "observations": summary["experience"]["observations"],
                      "construction_patterns": summary["experience"]["retained_measured_signatures"]}, indent=2))


if __name__ == "__main__":
    main()

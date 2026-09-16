"""Real, offline failure-to-learning demonstration; no model or network calls."""
import copy
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.profession_crew import operate_profession_crew


def main():
    with tempfile.TemporaryDirectory(prefix="uc-profession-demo-") as tmp:
        root = Path(tmp)
        shutil.copytree(ROOT / "capabilities/live", root / "capabilities/live")
        request = {"operation": "run", "crew_id": "demo", "run_id": "observed-failure", "work_type": "software",
                   "goal": "Learn to catch a repeated project defect before writing its next target",
                   "context": {"target": "offline-python"},
                   "steps": [{"id": "build", "profession_id": "backend-engineer", "action": {"kind": "python-project",
                              "inputs": {"path": "creations/first", "files": {"main.py": "def broken(:\n"}}}}]}
        first = operate_profession_crew(root, request)
        retry = copy.deepcopy(request)
        retry["run_id"] = "learned-preflight"
        retry["steps"][0]["action"]["inputs"]["path"] = "creations/retry"
        second = operate_profession_crew(root, retry)
        retry_target_absent = not (root / "creations/retry").exists()
        repaired = copy.deepcopy(retry)
        repaired["run_id"] = "corrected-input"
        repaired["steps"][0]["action"]["inputs"]["files"] = {"main.py": "print('Corrected and checked')\n"}
        third = operate_profession_crew(root, repaired)
        verification = operate_profession_crew(root, {"operation": "verify", "crew_id": "demo", "run_id": "corrected-input"})
        state = operate_profession_crew(root, {"operation": "inspect", "crew_id": "demo"})
        summary = {"first_job": first["status"], "repeated_defect": second["status"],
                   "repeated_defect_target_absent": retry_target_absent,
                   "corrected_job": third["status"], "fresh_verification": verification["status"],
                   "practice_contexts": len(state["practice"]), "professional_acceptance": "NOT_TESTED",
                   "visual_quality": "NOT_TESTED"}
        print(json.dumps(summary, indent=2))
        return 0 if (first["status"] == "HOLD_FAILED_CHECK" and second["status"] == "HOLD_LEARNED_PREFLIGHT"
                     and retry_target_absent and third["status"] == "COMPLETE_BOUNDED_CHECKS" and verification["status"] == "PASS") else 1


if __name__ == "__main__":
    raise SystemExit(main())

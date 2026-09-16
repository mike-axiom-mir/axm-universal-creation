"""Real, offline failure-to-learning demonstration; no model or network calls."""
import copy
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from axm_uc.profession_crew import operate_profession_crew
from axm_uc.procedural_3d import build_glb
from axm_uc.static_asset_target_evidence import PACKET_SCHEMA


def target_handoff_demo(root):
    artifact = root / "creations/target-fixture.glb"
    artifact.write_bytes(build_glb({"schema": "axm.procedural-3d/v0.1", "name": "Handoff fixture",
        "primitives": [{"id": "body", "type": "box", "size": [2, 1, 3], "translation": [0, 0, 0],
                        "material": {"color": "#446688FF", "metallic": 0.5, "roughness": 0.4}}]})["body"])
    target = {"engine": "Unexecuted demo target", "version": "1", "context": "RTS vehicle"}
    required = ["target_engine_import", "collision", "navigation"]
    packet = {"schema": PACKET_SCHEMA, "artifact_sha256": hashlib.sha256(artifact.read_bytes()).hexdigest(),
              "target": target, "required_lanes": required, "lanes": {}}
    result = operate_profession_crew(root, {"operation": "run", "crew_id": "target-demo", "run_id": "missing-evidence",
        "work_type": "3d", "goal": "Name owners for target work that has not been performed",
        "steps": [{"id": "target-check", "profession_id": "technical-artist", "action": {
            "kind": "verify-static-asset-target", "inputs": {"path": str(artifact), "packet": packet,
                "target": target, "required_lanes": required}}}]})
    state = operate_profession_crew(root, {"operation": "inspect", "crew_id": "target-demo"})
    owners = {r["lane"]: r["profession_id"] for r in result["handoff"]["requirements"]}
    return {"status": result["status"], "owners": owners, "practice_contexts": len(state["practice"]),
            "independently_reproduced": result["observations"][0]["target_evidence"]["independently_reproduced"]}


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
        target_demo = target_handoff_demo(root)
        summary = {"first_job": first["status"], "repeated_defect": second["status"],
                   "repeated_defect_target_absent": retry_target_absent,
                   "corrected_job": third["status"], "fresh_verification": verification["status"],
                   "practice_contexts": len(state["practice"]), "professional_acceptance": "NOT_TESTED",
                   "visual_quality": "NOT_TESTED", "target_evidence": target_demo}
        print(json.dumps(summary, indent=2))
        return 0 if (first["status"] == "HOLD_FAILED_CHECK" and second["status"] == "HOLD_LEARNED_PREFLIGHT"
                     and retry_target_absent and third["status"] == "COMPLETE_BOUNDED_CHECKS" and verification["status"] == "PASS"
                     and target_demo["status"] == "HOLD_TARGET_EVIDENCE" and target_demo["practice_contexts"] == 0
                     and target_demo["independently_reproduced"] is False
                     and target_demo["owners"] == {"collision": "gameplay-engineer", "navigation": "world-encounter-designer",
                                                   "target_engine_import": "technical-artist"}) else 1


if __name__ == "__main__":
    raise SystemExit(main())

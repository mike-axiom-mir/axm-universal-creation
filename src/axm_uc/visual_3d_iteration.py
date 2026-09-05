"""Persistent review-driven 3D iteration, independent of publication transport.

The machine retains exact-context lessons; it does not invent visual judgments
or pretend a prose constraint automatically changes procedural geometry.
"""
from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import re
from typing import Any

from .atomic import atomic_write_json
from .visual_3d import (
    ITERATION_RUN_SCHEMA, ITERATION_STAGES, _sha256, assess_3d_output,
    compile_3d_request, compile_adaptive_3d_request, forge_3d_asset,
    inspect_glb, record_3d_review,
)
from .visual_learning import inspect_png


def _run_path(root: str | Path, run_id: str) -> Path:
    if not isinstance(run_id, str) or not re.fullmatch(r"[a-z0-9][a-z0-9-]{0,63}", run_id):
        raise ValueError("run_id must be 1-64 lowercase letters, digits, or hyphens")
    return Path(root).resolve() / "state" / "3d-iterations" / f"run-{run_id}.json"


@contextmanager
def _locked(root: str | Path):
    # OS-released lock also covers lesson writes by this adapter. A killed forge
    # does not strand a stale lock or permit two iterations to overwrite state.
    folder = Path(root).resolve() / "state" / "3d-iterations"
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / ".writer.lock").open("a+b") as stream:
        stream.seek(0, os.SEEK_END)
        if stream.tell() == 0:
            stream.write(b"0")
            stream.flush()
        stream.seek(0)
        if os.name == "nt":
            import msvcrt
            acquire = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            release = lambda: msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            acquire = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            release = lambda: fcntl.flock(stream.fileno(), fcntl.LOCK_UN)
        try:
            acquire()
        except OSError as exc:
            raise RuntimeError("another 3D iteration writer is active; retry after it finishes") from exc
        try:
            yield
        finally:
            stream.seek(0)
            release()


def inspect_3d_iteration(root: str | Path, run_id: str) -> dict[str, Any]:
    state = json.loads(_run_path(root, run_id).read_text(encoding="utf-8"))
    if state.get("schema") != ITERATION_RUN_SCHEMA or state.get("run_id") != run_id:
        raise ValueError("iteration state schema or identity mismatch")
    return state


def start_3d_iteration(root: str | Path, spec: Any) -> dict[str, Any]:
    if not isinstance(spec, dict):
        raise TypeError("iteration specification must be an object")
    path = _run_path(root, spec.get("run_id"))
    minimum, maximum = spec.get("minimum_iterations", 7), spec.get("maximum_iterations", 24)
    if type(minimum) is not int or type(maximum) is not int or not 5 <= minimum <= maximum <= 100:
        raise ValueError("iteration limits must be integers with 5 <= minimum <= maximum <= 100")
    if not isinstance(spec.get("output"), str) or not spec["output"].strip():
        raise ValueError("iteration requires an explicit output directory")
    output = Path(spec["output"])
    if not output.is_absolute():
        output = Path(root) / output
    state = {
        "schema": ITERATION_RUN_SCHEMA, "run_id": spec["run_id"],
        "request": compile_3d_request(spec.get("request")),
        "output": str(output.resolve()), "minimum_iterations": minimum,
        "maximum_iterations": maximum, "status": "READY", "stage_index": 0,
        "attempts": [], "pending": None, "last_stage_pass": None, "outcome": None,
        "truth": {
            "iterationCountDoesNotProveQuality": True,
            "visualReviewRequiresAnObserver": True,
            "automaticSourceModification": False,
            "acceptanceIsNotRiggingOrEngineImportCertification": True,
        },
    }
    with _locked(root):
        if path.exists():
            raise FileExistsError(f"iteration run already exists: {spec['run_id']}")
        atomic_write_json(path, state)
    return state


def plan_3d_iteration(root: str | Path, run_id: str) -> dict[str, Any]:
    state = inspect_3d_iteration(root, run_id)
    stage = ITERATION_STAGES[state["stage_index"]]
    adaptive = compile_adaptive_3d_request(root, state["request"])
    adaptive["request"]["constraints"].append(stage["constraint"])
    number = len(state["attempts"]) + 1
    can_forge = state["outcome"] is None and state["pending"] is None and number <= state["maximum_iterations"]
    return {
        "run_id": run_id, "status": state["status"], "stage": stage["id"],
        "required_criteria": sorted({name for row in ITERATION_STAGES[:state["stage_index"] + 1] for name in row["criteria"]}),
        "can_forge": can_forge, "next_attempt": number,
        "output": str(Path(state["output"]) / f"{run_id}-{number:03d}-{stage['id']}"),
        "request": adaptive["request"], "applied_lesson_ids": adaptive["applied_lesson_ids"],
        "pending": state["pending"], "outcome": state["outcome"],
    }


def _verified_bundle(directory: Path, expected: dict[str, Any]) -> tuple[dict, dict]:
    manifest = json.loads((directory / "asset-manifest.json").read_text(encoding="utf-8"))
    request = compile_3d_request(json.loads((directory / "forge-request.json").read_text(encoding="utf-8")))
    if request != compile_3d_request(expected) or manifest.get("asset_id") != expected["asset_id"]:
        raise ValueError("artifact request or asset does not match this iteration")

    def verified_path(row):
        path = (directory / row["path"]).resolve()
        if not path.is_relative_to(directory.resolve()):
            raise ValueError("artifact path escapes the iteration output directory")
        if _sha256(path) != row.get("sha256"):
            raise ValueError(f"artifact hash mismatch: {path.name}")
        return path

    verified_path(manifest["source"])
    inspections = {name: inspect_glb(verified_path(manifest["exports"][name]))
                   for name in ("lod0", "lod1", "lod2", "collision")}
    for proof in manifest.get("render_proofs", []):
        inspect_png(verified_path(proof))
    return {"inspections": inspections}, manifest


def forge_3d_iteration(
    root: str | Path, run_id: str, *, change_summary: str,
    blender: str | Path | None = None, auto_provision_runtime: bool = True,
    timeout_seconds: int = 1800,
) -> dict[str, Any]:
    if not isinstance(change_summary, str) or not change_summary.strip() or len(change_summary) > 2000:
        raise ValueError("describe the concrete revision in change_summary (1-2000 characters)")
    with _locked(root):
        state = inspect_3d_iteration(root, run_id)
        # Acquiring the writer lock proves a previous FORGING process is gone.
        if state["status"] == "FORGING":
            state["attempts"][-1]["status"] = "INTERRUPTED"
            state["status"] = "READY"
            atomic_write_json(_run_path(root, run_id), state)
        plan = plan_3d_iteration(root, run_id)
        if not plan["can_forge"]:
            raise ValueError("run is complete, awaiting review, or has reached its attempt limit")
        directory = Path(plan["output"])
        directory.mkdir(parents=True, exist_ok=False)
        attempt = {
            "number": plan["next_attempt"], "stage": plan["stage"], "output": str(directory),
            "request": plan["request"], "change_summary": change_summary.strip(),
            "applied_lesson_ids": plan["applied_lesson_ids"], "status": "FORGING",
        }
        state["attempts"].append(attempt)
        state["status"] = "FORGING"
        atomic_write_json(_run_path(root, run_id), state)
        try:
            forge_3d_asset(root, plan["request"], directory, blender=blender,
                           auto_provision_runtime=auto_provision_runtime, timeout_seconds=timeout_seconds)
            receipt, manifest = _verified_bundle(directory, plan["request"])
            digest = receipt["inspections"]["lod0"]["sha256"]
            previous = state["attempts"][:-1]
            proof_set = sorted(row["sha256"] for row in manifest.get("render_proofs", []))
            if any(row.get("lod0_sha256") == digest or row.get("proof_hashes") == proof_set for row in previous):
                raise ValueError("unchanged asset or reused proof set; implement a revision before trying again")
            attempt.update(lod0_sha256=digest, proof_hashes=proof_set,
                           manifest_sha256=_sha256(directory / "asset-manifest.json"),
                           status="AWAITING_REVIEW")
            state["pending"] = attempt["number"]
            state["status"] = "AWAITING_REVIEW"
        except Exception as exc:
            attempt.update(status="FORGE_FAILED", error=f"{type(exc).__name__}: {exc}")
            state["status"] = "LIMIT_REACHED" if len(state["attempts"]) >= state["maximum_iterations"] else "NEEDS_REVISION"
            atomic_write_json(_run_path(root, run_id), state)
            raise
        atomic_write_json(_run_path(root, run_id), state)
        return state


def review_3d_iteration(root: str | Path, run_id: str, review: Any) -> dict[str, Any]:
    if not isinstance(review, dict) or not isinstance(review.get("notes"), str) or not review["notes"].strip():
        raise ValueError("review requires concrete observation notes")
    with _locked(root):
        state = inspect_3d_iteration(root, run_id)
        if state["pending"] is None:
            raise ValueError("run has no pending artifact to review")
        attempt = state["attempts"][state["pending"] - 1]
        directory = Path(attempt["output"])
        if _sha256(directory / "asset-manifest.json") != attempt["manifest_sha256"]:
            raise ValueError("pending manifest changed after forging")
        receipt, manifest = _verified_bundle(directory, attempt["request"])
        assessment = assess_3d_output(receipt, manifest, review)
        if not assessment["visual_review"]["artifact_bound"]:
            raise ValueError("review must cover every current proof hash exactly once")
        criteria = assessment["visual_review"]["criteria"]
        current = state["stage_index"]
        earliest_failure = next((index for index, stage in enumerate(ITERATION_STAGES[:current + 1])
                                 if any(criteria.get(name) != "PASS" for name in stage["criteria"])), None)
        passed = earliest_failure is None and assessment["technical_pass"]
        # One all-angle judgment is persisted into the existing exact-context
        # learner. Bundle binding above happens before any learning mutation.
        learning = record_3d_review(root, {
            "context_key": state["request"]["context_key"],
            "artifact_path": str(directory / manifest["render_proofs"][0]["path"]),
            "criteria": criteria, "lessons": review.get("lessons", []),
        })
        attempt.update(status="STAGE_PASS" if passed else "REVIEW_FAILED", assessment=assessment,
                       notes=review["notes"], learning_digest=learning["evidence_digest"])
        state["pending"] = None
        if passed:
            state["last_stage_pass"] = attempt["number"]
            state["stage_index"] = min(current + 1, len(ITERATION_STAGES) - 1)
        elif earliest_failure is not None:
            state["stage_index"] = earliest_failure
        reviewed = sum(row["status"] in {"STAGE_PASS", "REVIEW_FAILED"} for row in state["attempts"])
        if passed and current == len(ITERATION_STAGES) - 1 and reviewed >= state["minimum_iterations"] and assessment["status"] == "AAA_ACCEPTED":
            state["status"] = "AAA_ACCEPTED"
            state["outcome"] = {"attempt": attempt["number"], "output": str(directory),
                                "lod0_sha256": attempt["lod0_sha256"], "proof_hashes": attempt["proof_hashes"]}
        elif len(state["attempts"]) >= state["maximum_iterations"]:
            state["status"] = "LIMIT_REACHED"
        else:
            state["status"] = "READY" if passed else "NEEDS_REVISION"
        atomic_write_json(_run_path(root, run_id), state)
        return state


def reject_3d_iteration(root: str | Path, run_id: str, reason: str) -> dict[str, Any]:
    """Release an unusable pending version without deleting it or claiming review."""
    if not isinstance(reason, str) or not reason.strip():
        raise ValueError("a rejection reason is required")
    with _locked(root):
        state = inspect_3d_iteration(root, run_id)
        if state["pending"] is None:
            raise ValueError("run has no pending artifact")
        state["attempts"][state["pending"] - 1].update(status="REJECTED", reason=reason.strip())
        state["pending"] = None
        state["status"] = "LIMIT_REACHED" if len(state["attempts"]) >= state["maximum_iterations"] else "NEEDS_REVISION"
        atomic_write_json(_run_path(root, run_id), state)
        return state

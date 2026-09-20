"""Caller-owned workflow experience; measured candidates, never machine canon."""
from __future__ import annotations

import json

from .atomic import atomic_write_json
from .atlas_pipeline import _output
from .creation_atlas import digest, local_file

OBSERVATION_SCHEMA = "axm.workflow-observation/v0.1"
TEMPLATE_SCHEMA = "axm.learned-workflow/v0.1"


def read_memory(root, memory, *, pins=None):
    result = {"workflows": [], "observations": 0, "stale": [], "ignored": [], "automatic_canon_admission": False}
    if memory is None:
        return result
    folder = _output(root, memory)
    if not folder.exists():
        return result
    if not folder.is_dir():
        raise ValueError("workflow memory must be a directory")
    paths = sorted(folder.glob("workflow-observations/*.json"))
    templates = sorted(folder.glob("workflows/*.json"))
    if len(paths) + len(templates) > 4096 or sum(p.lstat().st_size for p in paths + templates) > 64_000_000:
        raise ValueError("workflow memory exceeds 4096 records or 64 MB; choose a scoped collection")
    admissions = {}
    for path in paths:
        try:
            value = json.loads(local_file(folder, path.relative_to(folder).as_posix()).read_text())
            if not isinstance(value, dict) or value.get("schema") != OBSERVATION_SCHEMA or path.stem != digest(value):
                raise ValueError("observation schema or identity mismatch")
            if value.get("status") not in {"CONFIRMED", "REJECTED", "INCOMPLETE", "CONFIRMATION_FAILED"}:
                raise ValueError("unknown observation status")
            result["observations"] += 1
            if value["status"] == "CONFIRMED":
                if not value.get("confirmation") or not value.get("cases"):
                    raise ValueError("confirmation and case evidence required")
                if (any(c.get("status") != "PASS" or c.get("run_status") != "CHECKS_PASSED"
                        or not isinstance(c.get("metrics"), dict) or not c.get("run_sha256")
                        for c in [*value["cases"], *value["confirmation"]])
                        or not all(c.get("repeatable") is True for c in value["confirmation"])):
                    raise ValueError("workflow lacks complete passing and repeatable evidence")
                admissions.setdefault(value["signature"], []).append((path.stem, value))
        except (ValueError, KeyError, OSError, TypeError, AttributeError) as exc:
            result["ignored"].append({"file": path.relative_to(folder).as_posix(), "reason": str(exc)})
    for path in templates:
        try:
            value = json.loads(local_file(folder, path.relative_to(folder).as_posix()).read_text())
            if not isinstance(value, dict) or value.get("schema") != TEMPLATE_SCHEMA or path.stem != digest(value):
                raise ValueError("workflow schema or identity mismatch")
            observations = admissions.get(value["signature"], [])
            if not observations:
                raise ValueError("workflow has no retained confirmed observation")
            fresh = any(v.get("pins") == pins for _, v in observations) if pins is not None else False
            result["workflows"].append({**value, "fresh": fresh, "observations": [key for key, _ in observations],
                                         "evidence": "PAST_OBSERVATION_RECHECK_REQUIRED"})
            if pins is not None and not fresh:
                result["stale"].append(value["signature"])
        except (ValueError, KeyError, OSError, TypeError, AttributeError) as exc:
            result["ignored"].append({"file": path.relative_to(folder).as_posix(), "reason": str(exc)})
    # More than one version of a structurally identical template is not growth.
    unique = {}
    for item in result["workflows"]:
        if item["signature"] not in unique or item["fresh"]:
            unique[item["signature"]] = item
    result["workflows"] = [unique[key] for key in sorted(unique)]
    return result


def retain(root, memory, observation, candidate, request, operators):
    if memory is None:
        return None
    folder = _output(root, memory)
    identity = digest(observation)
    atomic_write_json(folder / "workflow-observations" / (identity + ".json"), observation)
    if observation["status"] == "CONFIRMED":
        known = read_memory(root, memory)
        if candidate["signature"] not in {r["signature"] for r in known["workflows"]}:
            value = {"schema": TEMPLATE_SCHEMA, "signature": candidate["signature"],
                     "program": {k: v for k, v in candidate["program"].items() if k != "choices"},
                     "source_types": {k: request["inputs"][k]["type"] for k in candidate["program"]["choices"]},
                     "operators": {n["operator"]: operators[n["operator"]]["version"] for n in candidate["program"]["nodes"]},
                     "use": "Reusable structure. Rebind inputs, compile current goals and execute fresh checks on every use.",
                     "automatic_canon_admission": False}
            atomic_write_json(folder / "workflows" / (digest(value) + ".json"), value)
    return identity


def add_to_atlas(atlas, memory):
    records = read_memory(atlas.root, memory)
    for item in records["workflows"]:
        atlas.add("workflow:" + item["signature"], "learned-workflow", item["signature"], item["use"],
                  {"scope": "workflow-memory", "collection": str(memory), "observations": item["observations"]},
                  data=item, status="MEASURED_CANDIDATE_RECHECK_REQUIRED",
                  relations=[{"relation": "uses", "target": "operator:" + key} for key in item["operators"]])

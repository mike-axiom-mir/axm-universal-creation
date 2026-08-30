from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


TOKEN_RE = re.compile(r"[a-z0-9+#./-]+")
AXES = ("runtime", "execution", "state", "quality", "risk", "verification", "distribution")
OBSERVATION_FIELDS = ("goals", "requirements", "constraints", "capabilities", "risks", "notes")
STOP = frozenset({
    "a", "an", "as", "in", "is", "of", "on", "or", "to", "the", "and", "for", "with", "from", "into",
    "software", "system", "application", "tool", "build",
})


def _normalize(value: Any) -> str:
    return " ".join(TOKEN_RE.findall(str(value).casefold()))


def _words(value: Any) -> list[str]:
    return [word for word in TOKEN_RE.findall(str(value).casefold()) if len(word) > 1 and word not in STOP]


def _flatten(value: Any) -> list[str]:
    out: list[str] = []
    if isinstance(value, dict):
        for key in sorted(value):
            if key == "software_directions":
                continue
            out.extend(_flatten(value[key]))
    elif isinstance(value, (list, tuple, set)):
        for item in value:
            out.extend(_flatten(item))
    elif value is not None:
        out.append(str(value))
    return out


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError("software direction axis values must be arrays")
    result: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError("software direction values must be non-empty strings")
        result.append(item.strip())
    return result


def _source_union(profiles: list[dict[str, Any]], field: str, explicit: list[str] | None = None) -> list[dict[str, Any]]:
    sources: dict[str, list[str]] = {}
    for profile in profiles:
        for value in profile.get(field, []):
            sources.setdefault(str(value), []).append(str(profile["id"]))
    for value in explicit or []:
        sources.setdefault(str(value), []).append("EXPLICIT_AXIS")
    return [
        {"id": item, "source_directions": sorted(set(source_ids))}
        for item, source_ids in sorted(sources.items())
    ]


def _signal_score(signal: str, haystack: str, token_set: set[str]) -> int:
    normalized = _normalize(signal)
    if not normalized:
        return 0
    if normalized in haystack:
        return 8 + len(_words(normalized))
    tokens = _words(normalized)
    if not tokens:
        return 0
    hit = sum(1 for token in tokens if token in token_set)
    if hit == len(tokens):
        return 4 + hit
    if len(tokens) >= 3 and hit >= (len(tokens) * 3 + 3) // 4:
        return 2
    return 0


class SoftwareDirections:
    """Deterministic software-direction knowledge above language grammar.

    Full Universal Creation ships the donor-derived 29-profile body. Deliberately
    minimal machine roots used for focused tests or embedding may omit it; in that
    case the direction layer reports itself unavailable instead of preventing the
    rest of the machine from starting.
    """

    def __init__(self, root: Path):
        self.root = Path(root).resolve()
        data_root = self.root / "reference" / "software-directions"
        catalog_path = data_root / "direction-catalog.json"
        axis_path = data_root / "axis-catalog.json"
        self.available = catalog_path.is_file() and axis_path.is_file()
        if not self.available:
            self.catalog = {"profiles": []}
            self.axis_catalog = {"axes": {axis: [] for axis in AXES}}
            self.profiles: list[dict[str, Any]] = []
            self.profile_index: dict[str, dict[str, Any]] = {}
            return

        self.catalog = json.loads(catalog_path.read_text(encoding="utf-8"))
        self.axis_catalog = json.loads(axis_path.read_text(encoding="utf-8"))
        self.profiles = list(self.catalog.get("profiles", []))
        self.profile_index = {str(profile["id"]): profile for profile in self.profiles}
        if len(self.profiles) != 29 or len(self.profile_index) != 29:
            raise ValueError("software direction catalog must contain 29 unique profiles")
        axes = self.axis_catalog.get("axes")
        if not isinstance(axes, dict) or set(axes) != set(AXES):
            raise ValueError("software direction axis catalog must contain the seven expected axes")

    def summary(self) -> dict[str, Any]:
        if not self.available:
            return {
                "truth_status": "UNAVAILABLE_IN_THIS_MACHINE_BODY",
                "profiles": 0,
                "axes": {},
                "automatic_selection": False,
                "direction_is_authority": False,
                "reason": "reference/software-directions is absent from this deliberately minimal machine root",
            }
        families: dict[str, int] = {}
        for profile in self.profiles:
            family = str(profile.get("family", "unknown"))
            families[family] = families.get(family, 0) + 1
        return {
            "truth_status": "DONOR_DERIVED_TESTED_DIRECTION_MODEL",
            "profiles": len(self.profiles),
            "families": dict(sorted(families.items())),
            "axes": {axis: len(self.axis_catalog["axes"][axis]) for axis in AXES},
            "automatic_selection": False,
            "direction_is_authority": False,
            "engineering_quality_and_risk_axes_are_not_axm_roots": True,
            "donor": {
                "repository": "mike-axiom-mir/axm-102-grammer",
                "branch": "codex/standalone-capability-verification-v1",
                "path": "software-directions/",
            },
        }

    def profile(self, direction_id: str) -> dict[str, Any] | None:
        profile = self.profile_index.get(str(direction_id))
        return dict(profile) if profile is not None else None

    def _tensions(self, axes: dict[str, list[dict[str, Any]]]) -> list[dict[str, Any]]:
        def has(axis: str, item: str) -> bool:
            return any(row["id"] == item for row in axes[axis])

        out: list[dict[str, Any]] = []
        if has("execution", "hard-real-time") and has("state", "distributed-replicated"):
            out.append({"id": "REAL_TIME_DISTRIBUTED_STATE_TENSION", "meaning": "Network and replicated-state uncertainty may conflict with hard real-time deadlines.", "automatic_rejection": False})
        if has("risk", "safety-critical") and has("risk", "experimental"):
            out.append({"id": "SAFETY_EXPERIMENT_TENSION", "meaning": "Experimental behavior and a safety-critical deployment create an engineering tension requiring explicit evidence boundaries.", "automatic_rejection": False})
        if has("runtime", "browser") and has("execution", "interrupt-driven"):
            out.append({"id": "BROWSER_INTERRUPT_MODEL_TENSION", "meaning": "Browser code cannot directly own a hardware interrupt model without an external adapter/runtime.", "automatic_rejection": False})
        if has("risk", "irreversible-deployment") and not has("verification", "security-review"):
            out.append({"id": "IRREVERSIBLE_WITHOUT_SECURITY_REVIEW_TENSION", "meaning": "The selected software direction describes irreversible deployment without security-review evidence in its verification context.", "automatic_rejection": False})
        return out

    def compose(self, raw: dict[str, Any] | None) -> dict[str, Any]:
        if not self.available:
            return {"result": "DIRECTION_MODEL_UNAVAILABLE", "truth_status": "UNAVAILABLE_IN_THIS_MACHINE_BODY", "automatic_selection": False}
        if raw is None:
            return {"result": "NO_EXPLICIT_DIRECTION_SELECTION", "truth_status": "NO_SELECTION", "automatic_selection": False}
        if not isinstance(raw, dict):
            return {"result": "INVALID_DIRECTION_INPUT", "truth_status": "DETERMINISTIC_INPUT_VALIDATION", "error": "software_directions must be an object", "automatic_selection": False}
        try:
            direction_ids = _strings(raw.get("direction_ids", raw.get("directionIds", [])))
            explicit_axes = {axis: _strings(raw.get(axis, [])) for axis in AXES}
        except ValueError as exc:
            return {"result": "INVALID_DIRECTION_INPUT", "truth_status": "DETERMINISTIC_INPUT_VALIDATION", "error": str(exc), "automatic_selection": False}
        if not direction_ids and not any(explicit_axes.values()):
            return {"result": "DIRECTION_INPUT_REQUIRED", "truth_status": "DETERMINISTIC_INPUT_VALIDATION", "automatic_selection": False}
        unknown = [item for item in direction_ids if item not in self.profile_index]
        if unknown:
            return {"result": "UNKNOWN_DIRECTION", "truth_status": "DETERMINISTIC_INPUT_VALIDATION", "unknown_directions": unknown, "automatic_selection": False}
        for axis in AXES:
            allowed = {str(item["id"]) for item in self.axis_catalog["axes"][axis]}
            unknown_values = [item for item in explicit_axes[axis] if item not in allowed]
            if unknown_values:
                return {"result": "UNKNOWN_DIRECTION_AXIS_VALUE", "truth_status": "DETERMINISTIC_INPUT_VALIDATION", "axis": axis, "unknown_values": unknown_values, "automatic_selection": False}

        unique_ids = list(dict.fromkeys(direction_ids))
        profiles = [self.profile_index[item] for item in unique_ids]
        axes = {
            "runtime": _source_union(profiles, "typicalRuntimes", explicit_axes["runtime"]),
            "execution": _source_union(profiles, "executionModels", explicit_axes["execution"]),
            "state": _source_union(profiles, "stateModels", explicit_axes["state"]),
            "quality": _source_union(profiles, "qualityPriorities", explicit_axes["quality"]),
            "risk": _source_union(profiles, "riskFlags", explicit_axes["risk"]),
            "verification": _source_union(profiles, "verifierNeeds", explicit_axes["verification"]),
            "distribution": _source_union(profiles, "distributionModels", explicit_axes["distribution"]),
        }
        expectations = {
            "capabilities": _source_union(profiles, "capabilityNeeds"),
            "verifiers": axes["verification"],
            "gap_questions": _source_union(profiles, "gapQuestions"),
        }
        return {
            "result": "DIRECTION_STACK_READY_NO_AUTHORITY",
            "truth_status": "EXPLICIT_SOFTWARE_DIRECTION_SELECTION",
            "direction_ids": unique_ids,
            "duplicate_direction_count": len(direction_ids) - len(unique_ids),
            "selected_profiles": [{"id": profile["id"], "display_name": profile["displayName"], "family": profile["family"]} for profile in profiles],
            "axes": axes,
            "expectations": expectations,
            "tensions": self._tensions(axes),
            "automatic_selection": False,
            "direction_is_authority": False,
            "expectations_are_implementation_proof": False,
            "engineering_quality_and_risk_axes_are_not_axm_roots": True,
        }

    def suggest(self, observation: dict[str, Any], top_n: int = 8) -> dict[str, Any]:
        if not self.available:
            return {"result": "DIRECTION_MODEL_UNAVAILABLE", "truth_status": "UNAVAILABLE_IN_THIS_MACHINE_BODY", "candidates": [], "automatic_selection": False}
        if not isinstance(observation, dict):
            return {"result": "INVALID_DIRECTION_OBSERVATION", "candidates": [], "automatic_selection": False}
        fields: dict[str, list[str]] = {}
        try:
            for field in OBSERVATION_FIELDS:
                fields[field] = _strings(observation.get(field, []))
        except ValueError as exc:
            return {"result": "INVALID_DIRECTION_OBSERVATION", "error": str(exc), "candidates": [], "automatic_selection": False}

        text = " | ".join(item for field in OBSERVATION_FIELDS for item in fields[field])
        haystack = _normalize(text)
        token_set = set(_words(text))
        candidates: list[dict[str, Any]] = []
        for profile in self.profiles:
            matches = [{"signal": signal, "score": _signal_score(signal, haystack, token_set)} for signal in profile.get("signals", [])]
            matches = [match for match in matches if match["score"] > 0]
            if not matches:
                continue
            matches.sort(key=lambda item: (-int(item["score"]), str(item["signal"])))
            candidates.append({
                "direction_id": profile["id"],
                "display_name": profile["displayName"],
                "family": profile["family"],
                "score": sum(int(item["score"]) for item in matches),
                "matched_signals": matches,
                "candidate_is_selection": False,
            })
        candidates.sort(key=lambda item: (-int(item["score"]), str(item["direction_id"])))
        return {
            "result": "DIRECTION_CANDIDATES_READY_NO_SELECTION" if candidates else "NO_DIRECTION_CANDIDATE",
            "truth_status": "DETERMINISTIC_SIGNAL_MATCH",
            "candidate_count": len(candidates),
            "candidates": candidates[: max(1, min(29, int(top_n)))],
            "automatic_selection": False,
            "reason_inference_without_caller_evidence": "FORBIDDEN",
        }

    def analyze_request(self, request: dict[str, Any], top_n: int = 8) -> dict[str, Any]:
        text = " ".join(_flatten(request))
        suggestions = self.suggest({"goals": [text]}, top_n=top_n)
        stack = self.compose(request.get("software_directions"))
        return {"summary": self.summary(), "suggestions": suggestions, "stack": stack, "automatic_selection": False}

    @staticmethod
    def planning_context(stack: dict[str, Any]) -> dict[str, Any] | None:
        if stack.get("result") != "DIRECTION_STACK_READY_NO_AUTHORITY":
            return None
        return {
            "source": "explicit software_directions selection",
            "selected_directions": [item["display_name"] for item in stack["selected_profiles"]],
            "capability_needs": [item["id"] for item in stack["expectations"]["capabilities"]],
            "verifier_needs": [item["id"] for item in stack["expectations"]["verifiers"]],
            "execution_models": [item["id"] for item in stack["axes"]["execution"]],
            "state_models": [item["id"] for item in stack["axes"]["state"]],
            "runtime_models": [item["id"] for item in stack["axes"]["runtime"]],
        }

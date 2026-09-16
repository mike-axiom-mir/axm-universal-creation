"""Connect static target evidence to a job contract and profession handoffs.

This adapter checks external declarations against bytes and requirements. It
does not execute evidence sources, launch an engine, or award crew experience.
"""
from __future__ import annotations

from pathlib import Path

from .static_asset_target_evidence import (
    validate_static_asset_target_evidence,
    verify_static_asset_target_evidence,
)

ACTION_KIND = "verify-static-asset-target"
EVIDENCE_SCOPE = "EXTERNAL_PACKET_VALIDATION_ONLY"
LANE_OWNERS = {
    "target_engine_import": "technical-artist",
    "scale_pivot": "technical-artist",
    "material_shader": "technical-artist",
    "collision": "gameplay-engineer",
    "navigation": "world-encounter-designer",
    "resource_budget": "graphics-engineer",
    "material_sidedness": "technical-artist",
    "lod_perceptual_equivalence": "art-director",
    "target_runtime_integration": "gameplay-engineer",
    "target_device_performance": "graphics-engineer",
}


def target_contract(inputs: dict) -> dict:
    """Validate expectations with the existing closed packet vocabulary.

    The second validation only normalizes job requirements; it is never passed
    to the verifier as evidence or substituted for the supplied packet.
    """
    packet = validate_static_asset_target_evidence(inputs.get("packet"))
    contract = validate_static_asset_target_evidence({
        **packet, "target": inputs.get("target"),
        "required_lanes": inputs.get("required_lanes"), "lanes": {},
    })
    return {"target": contract["target"], "required_lanes": sorted(contract["required_lanes"])}


def assess_target_evidence(path: Path, inputs: dict) -> dict:
    contract = target_contract(inputs)
    report = verify_static_asset_target_evidence(path, inputs["packet"])
    report["execution_scope"] = EVIDENCE_SCOPE
    report["independently_reproduced"] = False
    report["job_contract"] = contract
    report["nonclaims"].append("Evidence source locators are not opened or authenticated by this adapter.")

    def hold(code: str, **details) -> None:
        report["findings"].append({"code": code, **details})
        report["finding_count"] += 1
        report["finding_counts"][code] = report["finding_counts"].get(code, 0) + 1
        if report["status"] != "FAIL":
            report["status"] = "HOLD"

    if report["target"] != contract["target"]:
        hold("TARGET_CONTEXT_MISMATCH", expected=contract["target"], supplied=report["target"])
    for lane in contract["required_lanes"]:
        if lane not in report["required_lanes"]:
            hold("REQUIRED_LANES_OMITTED", lane=lane)
    report["handoff_requirements"] = [
        {"lane": finding.get("lane"),
         "profession_id": LANE_OWNERS.get(finding.get("lane"), "technical-artist"),
         "reason": finding["code"]}
        for finding in report["findings"]
    ]
    return report

from __future__ import annotations

from typing import Any

ROOTS = ("truth", "agency", "continuity", "wisdom-before-speed")


def evaluate_declared_root_fit(candidate: dict[str, Any]) -> dict[str, Any]:
    """Validate the candidate's inspectable v0 root-fit declaration.

    This is deliberately not a hidden classifier or score. The declaration and
    its basis remain visible in the candidate manifest.
    """
    declaration = candidate.get("root_fit")
    if not isinstance(declaration, dict):
        return {"fit": False, "reason": "missing root_fit declaration", "roots": {}}

    checked: dict[str, Any] = {}
    overall = True
    for root in ROOTS:
        item = declaration.get(root)
        valid = (
            isinstance(item, dict)
            and item.get("fit") is True
            and isinstance(item.get("basis"), str)
            and bool(item["basis"].strip())
        )
        checked[root] = {
            "fit": bool(valid),
            "basis": item.get("basis") if isinstance(item, dict) else None,
        }
        overall = overall and valid
    return {"fit": overall, "reason": "all four declared roots fit" if overall else "one or more roots do not have a positive inspectable basis", "roots": checked}

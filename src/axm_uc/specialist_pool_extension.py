from __future__ import annotations

from pathlib import Path
from typing import Any

from .registry import Registry
from . import specialist_pool as base

# Capture the concrete v0 builder before __init__.py installs this wrapper.
_BASE_BUILD_SPECIALIST_POOL = base.build_specialist_pool


def build_specialist_pool(root: Path, challenge: str, *, pool_size: int = 32) -> dict[str, Any]:
    """Build the pool while keeping challenge context independent of display size.

    Small pools may intentionally contain only universal perspectives. Contextual
    fit should still describe the challenge itself, so a hidden three-record
    registry probe establishes the context without forcing those records into the
    displayed pool.
    """
    pool = _BASE_BUILD_SPECIALIST_POOL(root, challenge, pool_size=pool_size)
    if pool.get("context_key") != "general-unmatched":
        return pool

    registry = Registry(root)
    _, domains = base._derived_specialists(registry, challenge, 3)
    top_domains: list[str] = []
    for domain in domains:
        if domain and domain not in top_domains:
            top_domains.append(domain)
        if len(top_domains) == 3:
            break
    if not top_domains:
        return pool

    context_key = "|".join(top_domains)
    ledger = base.load_fit_ledger(root)
    for profile in pool["specialists"]:
        profile["fit"] = base._record_view(ledger, profile["id"], context_key)
    pool["specialists"].sort(key=base._fit_sort_key)
    pool["context_key"] = context_key
    pool["context_probe"] = {
        "kind": "registry-domain-probe-without-forcing-derived-specialists-into-small-pool",
        "matched_domains": top_domains,
    }
    return pool

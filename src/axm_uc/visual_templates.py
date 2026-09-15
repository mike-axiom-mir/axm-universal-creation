"""Canonical AXM visual-template facade.

The original deterministic template kernel is retained in ``visual_template_core``.
Professional foundation packs extend those same dictionaries before this facade
exports the public surface. This is one catalog/schema, not parallel template
systems.
"""
from __future__ import annotations

from . import visual_template_core as _core
from .visual_template_growth import extend_catalog as _extend_catalog

_extend_catalog(vars(_core))
_core.validate_catalog()

__all__ = []
for _name in dir(_core):
    if not _name.startswith("_"):
        globals()[_name] = getattr(_core, _name)
        __all__.append(_name)

CATALOG_COMPOSITION = {
    "schema": "axm.visual-template-composition/v1",
    "core": "visual_template_core",
    "extensions": ["visual_template_growth"],
    "counts": _core.validate_catalog(),
    "truth": "One v1 catalog composed deterministically from retained core plus explicit foundation extensions.",
}

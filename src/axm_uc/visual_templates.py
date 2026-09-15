"""Canonical AXM visual-template facade.

The original deterministic template kernel is retained in ``visual_template_core``.
Professional foundation packs extend those same dictionaries before this facade
exports the public surface. This is one catalog/schema, not parallel template
systems.
"""
from __future__ import annotations

from . import visual_template_core as _core
from .visual_template_growth import extend_catalog as _extend_catalog
from .visual_template_game_systems import extend_game_system_catalog as _extend_game_system_catalog
from .visual_template_creative_narrative import extend_creative_narrative_catalog as _extend_creative_narrative_catalog
from .visual_template_axm_system import extend_axm_system_catalog as _extend_axm_system_catalog
from .visual_template_game_shared import extend_game_shared_catalog as _extend_game_shared_catalog

_COMPOSITION=("visual_template_growth","visual_template_game_systems","visual_template_creative_narrative","visual_template_axm_system","visual_template_game_shared")
_applied=getattr(_core,"_AXM_VISUAL_COMPOSITION",None)
if _applied is None:
    _extend_catalog(vars(_core))
    _extend_game_system_catalog(vars(_core))
    _extend_creative_narrative_catalog(vars(_core))
    _extend_axm_system_catalog(vars(_core))
    _extend_game_shared_catalog(vars(_core))
    _core._AXM_VISUAL_COMPOSITION=_COMPOSITION
elif _applied != _COMPOSITION:
    raise RuntimeError("visual template composition changed inside a live process; restart with one exact catalog")
_core.validate_catalog()

__all__=[]
for _name in dir(_core):
    if not _name.startswith("_"):
        globals()[_name]=getattr(_core,_name)
        __all__.append(_name)

CATALOG_COMPOSITION={
    "schema":"axm.visual-template-composition/v1",
    "core":"visual_template_core",
    "extensions":list(_COMPOSITION),
    "counts":_core.validate_catalog(),
    "truth":"One v1 catalog composed deterministically from retained core plus explicit foundation extensions.",
}
__all__.append("CATALOG_COMPOSITION")

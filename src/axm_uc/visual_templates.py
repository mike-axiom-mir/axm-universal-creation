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
from .visual_template_keyart import extend_keyart_catalog as _extend_keyart_catalog
from .visual_template_cards import extend_card_catalog as _extend_card_catalog
from .visual_template_cinematic import extend_cinematic_catalog as _extend_cinematic_catalog
from .visual_template_video_overlay import extend_video_overlay_catalog as _extend_video_overlay_catalog
from .visual_template_diagram import extend_diagram_catalog as _extend_diagram_catalog
from .visual_template_atlas import extend_atlas_catalog as _extend_atlas_catalog
from .visual_template_novel import extend_novel_catalog as _extend_novel_catalog
from .visual_template_showroom import extend_showroom_catalog as _extend_showroom_catalog
from .visual_template_music import extend_music_catalog as _extend_music_catalog
from .visual_template_presentation import extend_presentation_catalog as _extend_presentation_catalog
from .visual_template_character_reference import extend_character_reference_catalog as _extend_character_reference_catalog
from .visual_template_configurator import extend_configurator_catalog as _extend_configurator_catalog
from .visual_template_motion import extend_motion_catalog as _extend_motion_catalog
from .visual_template_brand import extend_brand_catalog as _extend_brand_catalog
from .visual_template_environment import extend_environment_catalog as _extend_environment_catalog
from .visual_template_vfx import extend_vfx_catalog as _extend_vfx_catalog

_COMPOSITION=("visual_template_growth","visual_template_game_systems","visual_template_creative_narrative","visual_template_axm_system","visual_template_game_shared","visual_template_keyart","visual_template_cards","visual_template_cinematic","visual_template_video_overlay","visual_template_diagram","visual_template_atlas","visual_template_novel","visual_template_showroom","visual_template_music","visual_template_presentation","visual_template_character_reference","visual_template_configurator","visual_template_motion","visual_template_brand","visual_template_environment","visual_template_vfx")
_applied=getattr(_core,"_AXM_VISUAL_COMPOSITION",None)
if _applied is None:
    _extend_catalog(vars(_core))
    _extend_game_system_catalog(vars(_core))
    _extend_creative_narrative_catalog(vars(_core))
    _extend_axm_system_catalog(vars(_core))
    _extend_game_shared_catalog(vars(_core))
    _extend_keyart_catalog(vars(_core))
    _extend_card_catalog(vars(_core))
    _extend_cinematic_catalog(vars(_core))
    _extend_video_overlay_catalog(vars(_core))
    _extend_diagram_catalog(vars(_core))
    _extend_atlas_catalog(vars(_core))
    _extend_novel_catalog(vars(_core))
    _extend_showroom_catalog(vars(_core))
    _extend_music_catalog(vars(_core))
    _extend_presentation_catalog(vars(_core))
    _extend_character_reference_catalog(vars(_core))
    _extend_configurator_catalog(vars(_core))
    _extend_motion_catalog(vars(_core))
    _extend_brand_catalog(vars(_core))
    _extend_environment_catalog(vars(_core))
    _extend_vfx_catalog(vars(_core))
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

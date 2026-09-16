from pathlib import Path
import sys

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from axm_uc.rich_game_materials import (
    PROFILE_BY_NAME,
    PROFILES,
    generate_rich_game_material,
    rich_game_material_catalog,
    rich_game_material_fields,
)
from axm_uc.rich_game_material_bridge import load_rich_material_bundle


def test_rich_catalog_exposes_broad_game_surface_range():
    names = {profile.name for profile in PROFILES}
    assert len(names) >= 18
    assert {
        "molded-plastic", "sun-faded-plastic", "painted-fiberglass",
        "canvas", "sailcloth", "dry-rope", "weathered-aluminum",
        "oxidized-steel", "driftwood", "eva-foam", "weathered-rubber",
    } <= names
    catalog = rich_game_material_catalog()
    assert catalog["schema"] == "axm.rich-game-material-catalog/v0.1"
    assert catalog["dependencies"] == []


@pytest.mark.parametrize("profile", sorted(PROFILE_BY_NAME))
def test_rich_material_fields_are_complete_and_deterministic(profile):
    first = rich_game_material_fields(profile, size=24, seed=77)
    second = rich_game_material_fields(profile, size=24, seed=77)
    assert first == second
    assert set(first) == {"base_color", "roughness", "metallic", "height", "normal", "ao", "orm"}
    assert len(first["base_color"][1]) == 24 * 24 * 3
    assert len(first["normal"][1]) == 24 * 24 * 3
    assert len(first["orm"][1]) == 24 * 24 * 3
    assert first["orm"][1][0::3] == first["ao"][1]
    assert first["orm"][1][1::3] == first["roughness"][1]
    assert first["orm"][1][2::3] == first["metallic"][1]


def test_profiles_are_visually_distinct_in_generated_fields():
    plastic = rich_game_material_fields("molded-plastic", 32, 9)
    rope = rich_game_material_fields("dry-rope", 32, 9)
    metal = rich_game_material_fields("weathered-aluminum", 32, 9)
    assert plastic["base_color"][1] != rope["base_color"][1]
    assert plastic["normal"][1] != rope["normal"][1]
    assert metal["metallic"][1] != plastic["metallic"][1]


def test_bundle_roundtrip_and_tamper_detection(tmp_path):
    folder = tmp_path / "material"
    manifest = generate_rich_game_material(folder, "sun-faded-plastic", 32, 123, (220, 132, 31))
    loaded = load_rich_material_bundle(folder)
    assert loaded["manifest"]["profile"] == "sun-faded-plastic"
    assert loaded["manifest"]["maps"]["base_color"]["sha256"] == manifest["maps"]["base_color"]["sha256"]

    base = folder / "base_color.png"
    base.write_bytes(base.read_bytes() + b"x")
    with pytest.raises(ValueError, match="digest mismatch"):
        load_rich_material_bundle(folder)

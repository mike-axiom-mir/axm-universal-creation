# Vehicle art direction

`axm_uc.vehicle_art_direction` turns an explicit vehicle surface and an explicit style request into a deterministic material realization. It keeps the canonical source beside the styled output and emits an actual GLB.

The request can select one of five palettes, override any individual colour slot, choose factory/matte/satin/gloss/bare-metal/damaged finishes, set four independent wear channels, add panel-conforming marking geometry, and bind material variants to explicit upgrade levels.

The portable slots are `primary`, `secondary`, `trim`, `structure`, `metal_dark`, `metal_bright`, `rubber`, `glass`, `warning`, `light_primary`, `light_brake`, `dirt`, and `damage`. Material names such as `paint`, `iron`, `tin`, `rubber`, `windshield`, `cyan`, and `red` have defaults; callers may provide bounded replacements.

Markings are real surface primitives rather than labels in a receipt. `panel`, `stripe`, and `chevron` layers use an authored centre and perpendicular right/up basis, so the caller owns placement and outward orientation. The machine does not guess where a logo or readable panel belongs.

Upgrade tracks contain a current level, maximum level, target patterns, and one colour slot per level. Optional finish choices may also vary by level. The compiler publishes every level as a compact variant registry and applies only the explicitly active level.

Weathering changes vertex colours deterministically in object space. Dirt uses height and bounded variation; wear, scratches, and edge damage reveal the selected substrate colour. These are visual proposals, not reconstructed damage history or UV-space texture bakes.

```sh
python -m axm_uc.visual_assets_cli vehicle-art-catalog
python -m axm_uc.visual_assets_cli vehicle-art-compose request.json vehicle-surface.json output-directory
```

The output contains `source.json`, `realization.json`, `art-direction.json`, and `asset.glb`. Target-engine clearcoat, reflections, texture projection, transparency, colour management, artistic approval, and runtime performance remain separate evidence gates.

# Portable game render styles

`axm_uc.game_render_styles` converts a bounded `axm.surface-3d/v0.1` mesh into
one of three explicit render realizations while retaining the exact canonical
surface beside it.

| Style | Realization | Portable result |
| --- | --- | --- |
| `realistic-pbr` | Identity | Existing metallic/roughness materials and vertex colours stay unchanged. |
| `graphic-toon-baked` | Three authored light bands | Final linear vertex colours plus `KHR_materials_unlit`. |
| `painted-adventure-baked` | Six light bands with object-space pigment rhythm | Final linear vertex colours plus `KHR_materials_unlit`. |

The two stylized paths bake a fixed normalized light direction. They fold the
source material factor and source vertex colour into each final linear RGBA
vertex colour, then use a white unlit material. This makes the authored result
independent of a viewer's light rig while preserving geometry, normals and
indices exactly. The realistic path is deliberately an identity and does not
add an extension, protecting existing output shape and appearance.

## Usage

```sh
axm-assets game-render-catalog
axm-assets game-render request.json output/graphic \
  --style graphic-toon-baked --seed 471 --light -.45 .82 .35
axm-assets game-render request.json output/painted \
  --style painted-adventure-baked --seed 471 --light -.45 .82 .35
```

`request.json` contains exactly `{ "mesh": <surface-3d object> }`. Publication
is transactional and refuses to overwrite an existing directory. It writes:

- `source.json`: immutable canonical input;
- `realization.json`: selected renderer-neutral output;
- `render-style.json`: parameters, hashes, gates and limitations;
- `asset.glb`: actual portable GLB.

Python callers can use `apply_game_render_style`,
`game_render_style_catalog`, or `publish_game_render_style`.

## Truth boundary

This capability proves a fixed-light, export-safe realization. It does not
implement or claim camera-responsive outlines, dynamic light-band direction,
screen-space paper grain, camera rim lighting or animated brush crawl. Those
features need a target-engine adapter because glTF core plus
`KHR_materials_unlit` cannot express them portably. Target-engine colour
management, animation, gameplay-distance readability and performance remain
separate acceptance steps.

The bounded Blender specimen in
`tools/blender/game_render_style_roundtrip.py` exports all three styles,
re-imports them into a fresh process, checks decoded geometry and colour data,
and renders both the editable source and fresh GLBs. Its receipt is
`docs/evidence/game-render-style-roundtrip-2026-09-13.json`.

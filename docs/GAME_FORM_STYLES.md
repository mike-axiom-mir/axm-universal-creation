# Game form styles

`game_form_styles.py` provides renderer-neutral, deterministic silhouette and
proportion derivation for `axm.surface-3d/v0.1` meshes. It changes actual vertex
positions and rebuilt normals; it is not a palette filter or polygon multiplier.

The input mesh remains embedded byte-for-byte as canonical `source`. The cheaper
or more stylized `realization` is a derivative and cannot overwrite source truth.
Parts must be explicitly classified as body, armor, functional, or detail and as
large, medium, or small. The machine therefore does not invent semantic roles.

Available profiles:

- `realistic`: identity geometry, preserving the product-design option;
- `comic-salvage`: squat/tapered mass, enlarged functional pieces, controlled
  asymmetry, broad large forms, and restrained small detail;
- `heroic-toon`: taller, top-heavy mass and larger armor/function landmarks;
- `storybook-chunky`: strongest squash and functional exaggeration with the
  clearest large/medium/small separation.

## Portable request

```json
{
  "mesh": {"schema": "axm.surface-3d/v0.1", "name": "bot", "primitives": []},
  "parts": {
    "body": {
      "role": "body",
      "hierarchy": "large",
      "strength": 1,
      "anchors": {"ground": [0, 0, 0]},
      "anchor_falloff": 0.2
    }
  }
}
```

The abbreviated mesh above is illustrative; a real request needs bounded
triangle primitives with positions, normals, colors, indices, and material.
Part keys must exactly cover the component prefix before `__` in every primitive
ID. This fails closed instead of silently leaving an unclassified component.

```sh
axm-assets game-form-catalog
axm-assets game-form request.json out/comic --style comic-salvage --seed 471
```

Publishing refuses an existing path and writes `source.json`,
`realization.json`, and `form-manifest.json`.

## Protected anchors

Any number of named contact/socket coordinates may be declared per part. A
bounded radial falloff fades displacement to exactly zero at each anchor. The
receipt records before/after coordinates and drift. This proves those points are
fixed by the derivation; it does **not** prove complete contact patches,
articulation clearance, skin deformation, collision behavior, or animation.

`tools/blender/game_form_roundtrip.py` creates one neutral/comic-salvage courier
comparison, exports actual GLB, reopens editable `.blend`, independently imports
the GLB, and compares every imported mesh bound with the renderer-neutral source.
The proof is static and intentionally stops short of calling the courier a
finished game asset.

## Donor boundary

The pinned theme-park cartoon/fantasy renderers were reviewed for the useful
category of coordinated squash/pop and asymmetrical dressing. They remain bound
to their park renderer and state. No donor source code was copied; this module is
an original renderer-neutral geometry contract.

## Next boundary

Form derivation does not judge whether a silhouette is attractive or readable.
It does not generate topology, UVs, rig weights, LODs, collisions, clips, or
engine shaders. The next checkpoint should realize graphic/painterly lighting
that survives export, then combine that with form on a properly rigged asset.

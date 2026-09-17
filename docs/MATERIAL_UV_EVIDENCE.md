# Static material UV / texel-density evidence

`axm_uc.material_uv_evidence.inspect_material_uv_density()` is a bounded
look-development instrument for **actual static GLB artifacts**. It exists to
measure a class of surface-scale problem that visual inspection has already
exposed in UC: the first Blender material proof used spherical UVs and visibly
stretched woven cloth/wood into radial rings before the proof scene was repaired
to front-planar UVs.

The instrument does not decide a studio-wide texel-density target or an
acceptable distortion threshold. Different assets, camera distances and
realization budgets can legitimately need different surface scale. It provides
comparable evidence so Art Direction / LookDev can choose those targets
explicitly rather than relying on mesh names or exporter metadata.

## What is measured

For every measurable textured triangle primitive in the default GLB scene the
reviewer reads the actual embedded bytes for:

- `POSITION`;
- `TEXCOORD_0`;
- triangle indices;
- node transforms;
- material-to-texture bindings; and
- core embedded PNG/JPEG image dimensions.

For each bound base-color, metallic/roughness, normal, occlusion or emissive
texture it retains the original area-weighted scalar texels-per-metre evidence
(`p10`, `p50`, `p90` and weighted geometric mean), UV/world area, UV bounds,
wrap modes and exact image/artifact SHA-256 identity.

It also reports a sibling **directional** measurement. Each measurable triangle
is expressed in an orthonormal basis of its world-space plane. UV edges are
converted to texel edges with image width and image height kept separate. The
resulting 2x2 world-plane -> texel Jacobian is measured through its two singular
values:

- `principal_min` — smaller principal directional sampling scale in texels/metre;
- `principal_max` — larger principal directional sampling scale in texels/metre;
- `anisotropy_ratio` — `principal_max / principal_min`.

The directional values are aggregated with world-area weighting and expose
weighted geometric mean plus observed minimum/maximum. This is **measurement**,
not an automatic defect verdict. Deliberate directional scaling can be valid.

The pre-existing scalar remains the area/geometric-mean view. For a locally
affine measurable triangle, the geometric mean of the two principal directional
scales corresponds to the same local area scale that the scalar observer already
reported. Existing scalar callers therefore keep their original semantics.

Examples:

- one square metre mapped across one `1024x1024` image reports about `1024`
  texels/metre in both principal directions;
- the same square mapped across an `2048x1024` image reports principal scales of
  about `1024` and `2048` texels/metre while the retained scalar area scale is
  about `sqrt(1024*2048)`;
- a `1.10 x 1.50 m` planar surface mapped blindly to a full square image can have
  a perfectly valid UV bijection while still exposing different principal
  texels/metre along its physical directions.

`MEASURED` means only that these numbers came from the exact artifact bytes. It
is **not** aesthetic approval.

## Fail-closed / HOLD boundaries

The observer deliberately HOLDs rather than estimating when the result would be
misleading, including:

- animation / skin deformation;
- external image URIs (nothing is fetched);
- sparse, compressed or extended geometry/UV buffer views;
- alternate UV sets;
- texture transforms that alter UV scale;
- extended image/texture sources;
- collapsed UV area with no measurable sample; or
- missing materials / `TEXCOORD_0` / measurable embedded textures.

A clamped texture whose UVs leave the normalized 0..1 range is retained as a
measurement but receives an explicit `UV_OUTSIDE_CLAMP` finding.

The directional sibling additionally refuses a singular/non-finite local
world-plane or texel Jacobian. It does not fabricate a principal scale. If a
binding cannot be completed directionally, its directional result is marked
`HOLD` while the already-supported scalar evidence remains separately visible.

## Truth boundary

This does **not** prove:

- that the UV unwrap has attractive seams;
- that a measured anisotropy ratio is good or bad;
- that a chosen texel density is correct for an asset or camera distance;
- texture pixel validity beyond the bounded PNG/JPEG dimension header needed for
  scale evidence;
- shader correctness, color management, normal orientation or material response;
- actual rendering quality in Blender, the AXM native visual runtime or a game
  engine;
- mip/filter/compression quality or target-device memory/performance;
- deformation-time density; or
- any automatic repair, UV rescale, seam generation, unwrapping or atlas packing
  capability.

Use the measurements beside renders, not instead of renders. Product repositories
retain authority over physical source meaning, target texel density, acceptable
directional distortion, atlas policy, visual acceptance and runtime adoption.

## Focused regression

```sh
python -m unittest tests.test_material_uv_evidence -v
```

The fixtures preserve the original scalar regression and additionally prove:

- isotropic square mapping;
- a Building-style metric-aware rectangular surface mapped isotropically inside
  a square image;
- an aspect-blind mapping that is structurally valid but directionally
  anisotropic;
- rectangular image width/height handling without prematurely collapsing them to
  `sqrt(width*height)`;
- triangle-order and rigid-position invariance;
- collapsed-UV fail-closed behavior; and
- source-artifact immutability.

No regression installs a studio-wide target or anisotropy threshold.

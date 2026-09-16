# Static material UV / texel-density evidence

`axm_uc.material_uv_evidence.inspect_material_uv_density()` is a bounded
look-development instrument for **actual static GLB artifacts**. It exists to
measure a class of surface-scale problem that visual inspection has already
exposed in UC: the first Blender material proof used spherical UVs and visibly
stretched woven cloth/wood into radial rings before the proof scene was repaired
to front-planar UVs.

The instrument does not decide a studio-wide texel-density target. Different
assets, camera distances and realization budgets can legitimately need different
surface scale. It provides comparable evidence so Art Direction / LookDev can
choose those targets explicitly rather than relying on mesh names or exporter
metadata.

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
texture it reports area-weighted texels-per-metre evidence (`p10`, `p50`, `p90`
and weighted geometric mean), UV/world area, UV bounds, wrap modes and exact
image/artifact SHA-256 identity.

A one-square-metre surface mapped across one 1024x1024 texture therefore measures
approximately 1024 texels/metre. Doubling the world dimensions without changing
UVs measures approximately 512 texels/metre; doubling UV span without changing
the object measures approximately 2048 texels/metre.

`MEASURED` means only that these numbers came from the exact artifact bytes. It
is **not** aesthetic approval.

## Fail-closed / HOLD boundaries

The first version deliberately HOLDs rather than estimating when the result
would be misleading, including:

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

## Truth boundary

This does **not** prove:

- that the UV unwrap has attractive seams or low directional distortion;
- that a chosen texel density is correct for an asset or camera distance;
- texture pixel validity beyond the bounded PNG/JPEG dimension header needed for
  scale evidence;
- shader correctness, color management, normal orientation or material response;
- actual rendering quality in Blender, the AXM native visual runtime or a game
  engine;
- mip/filter/compression quality or target-device memory/performance;
- deformation-time density; or
- any automatic repair/unwrapping capability.

Use the measurements beside renders, not instead of renders. A later lookdev
pass can bind explicit project/asset targets only after cross-domain visual
evidence justifies them.

## Focused regression

```sh
python -m unittest tests.test_material_uv_evidence -v
```

The fixtures prove direct scale response, node-scale response, clamped out-of-
range UV reporting, collapsed-UV HOLD, texture-transform/alternate-UV HOLD,
no-fetch external-image behavior, missing-evidence HOLD, deformation HOLD,
image-header integrity and source-artifact immutability.

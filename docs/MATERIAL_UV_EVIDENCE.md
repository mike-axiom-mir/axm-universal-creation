# Static material UV / texel-density evidence

`axm_uc.material_uv_evidence.inspect_material_uv_density()` is a bounded
look-development instrument for **actual static GLB artifacts**. It exists to
measure surface-scale problems from the exact artifact rather than infer them
from mesh names, exporter metadata or visual intent.

The instrument does not decide a studio-wide texel-density or anisotropy target.
Different assets, camera distances and realization budgets can legitimately need
different surface scale. It provides comparable evidence so Art Direction /
LookDev can choose those targets explicitly.

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
texture it retains the existing area-equivalent texels-per-metre evidence
(`p10`, `p50`, `p90` and weighted geometric mean), UV/world area, UV bounds,
wrap modes and exact image/artifact SHA-256 identity.

It additionally derives the local 2D world-plane -> texel Jacobian for each
non-degenerate measurable triangle. The singular values of that Jacobian are
the principal directional sampling densities. Each binding reports bounded
area-weighted summaries for the lower and upper principal densities plus local
anisotropy (`max / min`). Image width and height are applied on their own axes;
they are not collapsed to `sqrt(width * height)` for the directional evidence.

A one-square-metre surface mapped across one 1024x1024 texture therefore has
principal densities near 1024 texels/metre in both directions. A one-square-
metre surface mapped across a 1024x512 texture has principal densities near
512 and 1024 texels/metre and anisotropy near 2, while the retained scalar
area-equivalent view remains their geometric mean.

`MEASURED` means only that the numbers came from the exact artifact bytes. It
is **not** aesthetic approval. No anisotropy threshold is invented.

## Fail-closed / explicit-finding boundaries

The observer deliberately HOLDs rather than estimates when its existing static
evidence contract is unsupported, including:

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

Directional calculation is also fail-closed per binding/triangle. If the local
world-plane -> texel Jacobian cannot be represented as a finite nonsingular
mapping, the observer emits `DIRECTIONAL_UV_UNMEASURABLE`, increments the
directional skip count and does not fabricate principal densities for that
sample. Existing scalar evidence remains separate and backward compatible.

## Truth boundary

This observer reports local directional sampling distortion; it does **not**
prove:

- that the UV unwrap has attractive seams or acceptable directional distortion;
- that any anisotropy ratio is good or bad for an asset;
- that a chosen texel density is correct for an asset or camera distance;
- texture pixel validity beyond the bounded PNG/JPEG dimension header needed
  for scale evidence;
- shader correctness, color management, normal orientation or material response;
- actual rendering quality in Blender, the AXM native visual runtime or a game
  engine;
- mip/filter/compression quality or target-device memory/performance;
- deformation-time density; or
- any automatic UV rescale, repair, packing or unwrapping capability.

Use the measurements beside renders, not instead of renders. Product repositories
retain authority over source metric meaning, target px/m, acceptable anisotropy,
atlas policy and visual acceptance.

## Focused regression

```sh
python -m unittest tests.test_material_uv_evidence -v
```

The fixtures preserve the existing scalar-scale, HOLD and immutability checks and
add isotropic principal-density equivalence, Building-style aspect-correct versus
aspect-blind mapping, rectangular-image axis handling, triangle-order invariance
and rigid-transform invariance.

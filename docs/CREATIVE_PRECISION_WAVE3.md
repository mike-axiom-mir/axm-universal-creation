# Creative Precision Fabric — executable hand wave 3

Wave 3 continues the same rule as the first two waves:

`outside creative-tool influence -> UC-native deterministic primitive -> executable hand -> composable recipe -> exact evidence`

It does **not** clone Photoshop, GIMP, Krita, Substance, Blender, Audacity, a DAW, NLE, or any other product. Product behavior is conceptual influence only. No external product UI, branding, proprietary implementation, or hidden remote service is embedded.

## Exact installed creative-hand body

The Creative Hands registry now contains **144 deterministic executable hands**. The composed Creative Recipe registry exposes **151 callable recipes**.

Wave 3 adds 58 hands on top of the 86 from wave 2:

| new family | hands |
| --- | ---: |
| advanced masks / matting | 6 |
| liquify / field warps | 6 |
| advanced raster / photo | 12 |
| material-channel operations | 12 |
| audio micro-operations | 13 |
| timeline edit operations | 9 |
| **wave 3 total** | **58** |

`capabilities/platform-hands/index.js` now exposes `creativeHands`, a stable service with:

- `list()`
- `get(id)`
- `invoke(id, args)`
- `audit()`
- `recipeRegistry()`
- `invokeRecipe(id, args)`

Hosts no longer need to know the internal upgrade-program path to use these hands.

## Advanced mask / matting

Executable additions:

- border extraction;
- soft thresholding;
- bounded signed distance fields;
- distance-field to mask conversion;
- deterministic mask smoothing;
- matte choke/spread.

Distance-field execution is intentionally capped at 262,144 pixels and radius 64 because its current implementation is a bounded local search, not a production-scale Euclidean distance-transform kernel.

## Liquify / field transforms

Six deterministic displacement-field hands now execute through the existing precision displacement warp:

- push;
- twirl;
- bloat;
- pucker;
- ripple;
- wave.

The generated field is explicit and reproducible. Liquify is limited to 4,194,304 pixels to keep the two floating displacement arrays bounded. This is raster field deformation, not a claim of mesh/cage/puppet deformation parity.

## Advanced raster / photo

New executable operators:

- motion blur;
- radial blur;
- bilateral blur;
- unsharp mask;
- local contrast;
- median-domain denoise;
- tone mapping;
- bounded dark-channel-inspired dehaze;
- normal-map derivation from height/luminance;
- seamless-edge blending;
- bump shading;
- chromatic aberration.

Expensive neighborhood operators have smaller explicit pixel ceilings than the generic raster format. The hand exists only inside those declared bounds.

## Material-channel body

A new `axm.precision-material/v1` state keeps named raster channels together without flattening them into one beauty image.

Executable hands include:

- material creation;
- set channel;
- brush paint one channel;
- invert one channel;
- levels on one channel;
- derive normal from height;
- ORM packing;
- ORM unpacking;
- edge/wear mask generation;
- deterministic dust mask generation;
- deterministic scratch mask generation;
- decal application through an explicit mask.

Supported named starting channels include base colour, roughness, metallic, normal, height, emissive, opacity and AO, plus bounded custom channels. This makes Substance-like ideas usable as deterministic channel operations without cloning Substance.

## Audio micro-operations

`axm.precision-audio/v1` adds an inspectable PCM working state and thirteen executable operations:

- create;
- gain;
- peak normalize;
- reverse;
- trim;
- fade;
- stereo pan;
- gate;
- hard clip;
- linear resample;
- deterministic time stretch;
- playback-rate pitch shift;
- mix.

The current time-stretch and pitch-shift algorithms are deliberately simple deterministic resampling operations. They do **not** claim phase-vocoder, formant-preserving, Elastique-class, or transparent mastering quality. Their receipts/state explicitly preserve the method and changed duration/pitch semantics.

## Timeline / video editing state

Nine hands execute against `axm.precision-timeline/v1`:

- create timeline;
- trim clip;
- cut clip;
- concatenate timelines;
- change clip speed;
- reverse clip intent;
- add fade intent;
- overlay a clip on another track;
- add caption cues.

These operations really edit deterministic timeline state. They **do not render or encode final video frames**. Final video realization remains the job of the existing video/FFmpeg substrate and its evidence boundary.

## Public evidence

`creative-hands-wave3-selftest.js` executes real data across every new family, asserts the exact 144-hand / 151-recipe census, exercises the public Platform Hands service, and checks expensive-operation bounds fail closed.

`tests/test_creative_precision_fabric.py` executes that JavaScript proof in the normal repository unittest suite.

The roots remain the merge gate:

- **Truth** — named capabilities are separated from quality/parity claims; timeline state is not called rendered video; simple audio algorithms are named honestly.
- **Agency / non-domination** — the same callable hands remain available to humans, deterministic software and machine users; no hidden external service takes control.
- **Continuity** — wave 3 extends the same raster/mask/transform/vector bodies rather than replacing the existing Studio or creation controls.
- **Wisdom before speed** — expensive algorithms receive tighter explicit bounds and fail closed instead of pretending generic-raster limits are safe.

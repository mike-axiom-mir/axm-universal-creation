# Creative Precision Fabric — executable hand wave 2

This wave converts a large part of the influence-derived creative microtool map into actual deterministic UC-native execution.

It does **not** clone Photoshop, GIMP, Krita, Inkscape, Aseprite or any other product. Product behaviour is used only as conceptual influence. The implementation contracts, state, code and naming are AXM/UC-native.

## Executable creative-hand registry

`upgrade-program/creative-hands.js` exposes 56 deterministic hands:

| family | executable hands |
| --- | ---: |
| colour / adjustment | 17 |
| raster filters | 11 |
| brush-domain pixel operators | 12 |
| masked retouch | 2 |
| vector precision | 9 |
| pixel-art / sprite | 5 |
| **total** | **56** |

Each hand has an inspectable descriptor and returns a digest-bound `axm.creative-executable-hand-result/v1` result. `audit()` enumerates the exact installed hand set rather than inferring capability from documentation.

## Raster adjustment depth

Executable adjustment hands now include brightness, contrast, gamma, exposure, saturation, vibrance, hue, grayscale, invert, threshold, posterize, tint, levels, piecewise curves, 3x3 channel mixing, gradient mapping and bounded white balance.

Adjustment output can be restricted through an existing precision mask, so these same operators can act as local adjustments rather than requiring separate implementations.

## Raster filters

The wave adds bounded executable box blur, discrete Gaussian blur, median blur, pixelation, deterministic noise/grain, Sobel edge detection, emboss, sharpen, high-pass and arbitrary bounded convolution.

The point is not the filter names. `convolution + mask + brush-plan + effect graph` is a reusable deterministic vocabulary from which many higher-level tools can be assembled.

## Brush operators

The wave turns the wave-1 dab planner into actual pixel-edit execution. The same deterministic dabs, pressure/tilt/velocity/direction dynamics and masking can now drive:

- paint;
- erase;
- replace colour;
- dodge;
- burn;
- saturate;
- desaturate;
- blur;
- sharpen;
- clone;
- heal;
- smudge.

Clone/heal can use a separate precision raster as a source. This keeps the source relationship explicit and allows later compositions such as perspective clone to be built from `projective warp -> source raster -> clone hand` rather than hard-coding a separate opaque tool.

## Retouch

Two bounded masked retouch hands apply clone or heal through arbitrary precision masks with explicit source offsets and optional separate source images.

## Vector operations

Nine deterministic vector hands add affine path transforms, quadratic-to-cubic conversion, elliptical arc construction, Ramer-Douglas-Peucker simplification, Chaikin smoothing, regular polygons, stars, variable-width stroke outlines and rounded rectangles.

They extend the existing precision-vector engine rather than introducing another vector document model.

## Pixel-art operations

Five executable hands provide palette quantization, Bayer ordered dithering, Floyd-Steinberg error diffusion, spritesheet assembly and tilemap assembly.

The indexed result from quantization retains explicit palette indices, so pixel state is not merely flattened into an opaque render.

## Recipe promotion

`creative-recipes.js` now discovers the executable hand registry. Familiar concepts such as `brush.dodge`, `colour.levels`, `filter.gaussian-blur`, `vector.star` and `pixel.error-diffusion` route to exact installed hands.

`retouch.perspective-clone` is also composed from the existing homography/projective-warp machinery plus the new clone execution path.

Effect graphs and smart layers remain `EXECUTABLE_CONTRACT` where graph construction is real but not every arbitrary node type has an installed executor. No capability is promoted merely because its name appears in the microtool catalog.

## Verification boundary

`creative-hands-selftest.js` executes representative adjustment, filter, brush, retouch, vector and pixel-art paths and checks that the registry reports exactly 56 executable hands. `tests/test_creative_precision_fabric.py` invokes that exact JavaScript proof inside the repository CI suite.

The next useful waves should continue the same rule:

`influence -> smallest reusable primitive -> deterministic executor -> hand descriptor -> recipe composition -> exact test`

Good candidates are deeper mask fields, raster geometry/liquify, frequency-domain and denoise operations, full path surgery, multi-channel material painting, procedural material generators, and time-domain audio/video micro-operations.

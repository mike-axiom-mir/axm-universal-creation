# Creative Precision Fabric — executable hand wave 2

This wave converts a large part of the influence-derived creative microtool map into actual deterministic UC-native execution.

It does **not** clone Photoshop, GIMP, Krita, Inkscape, Aseprite or any other product. Product behaviour is used only as conceptual influence. The implementation contracts, state, code and naming are AXM/UC-native.

## Executable creative-hand registry

`upgrade-program/creative-hands.js` exposes **86 deterministic hands**:

| family | executable hands |
| --- | ---: |
| colour / adjustment | 17 |
| raster filters | 11 |
| brush-domain pixel operators | 12 |
| masked retouch | 2 |
| vector precision | 9 |
| pixel-art / sprite | 5 |
| selection / mask | 18 |
| projective transform | 5 |
| existing vector-core surgery | 6 |
| effect-graph compilation | 1 |
| **total** | **86** |

Each hand has an inspectable descriptor and returns a digest-bound `axm.creative-executable-hand-result/v1` result. `audit()` enumerates the exact installed hand set rather than inferring capability from documentation.

## Raster adjustment depth

Executable adjustment hands now include brightness, contrast, gamma, exposure, saturation, vibrance, hue, grayscale, invert, threshold, posterize, tint, levels, piecewise curves, 3x3 channel mixing, gradient mapping and bounded white balance.

Adjustment output can be restricted through an existing precision mask, so these same operators can act as local adjustments rather than requiring separate implementations.

## Raster filters

The wave adds bounded executable box blur, discrete Gaussian blur, median blur, pixelation, deterministic noise/grain, Sobel edge detection, emboss, sharpen, high-pass and arbitrary bounded convolution.

The point is not the filter names. `convolution + mask + brush-plan + effect graph` is a reusable deterministic vocabulary from which many higher-level tools can be assembled.

The public hand descriptors expose effective radius bounds for blur/sharpen operations. Out-of-contract radii reject at the hand boundary instead of relying on a deeper kernel failure.

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

Clone/heal can use a separate precision raster as a source. This keeps the source relationship explicit and allows compositions such as perspective clone to be built from `projective warp -> source raster -> clone hand` rather than hard-coding a separate opaque tool.

## Selection and masks

Eighteen existing precision operations are now first-class executable hands: rectangle, ellipse and polygon selection; contiguous-colour / magic-wand, colour-range, luminance, channel and edge masks; union, intersection, subtract and XOR; invert, feather, grow, shrink, open and close.

These promote already-real wave-1 primitives into the same callable hand registry. No duplicate mask engine is introduced.

## Retouch

Two bounded masked retouch hands apply clone or heal through arbitrary precision masks with explicit source offsets and optional separate source images.

## Transform operations

Five existing transform primitives are first-class hands: homography solve, projective raster warp, displacement-field warp, 3x3 matrix inversion and projective point transformation.

## Vector operations

Nine new deterministic vector hands add affine path transforms, quadratic-to-cubic conversion, elliptical arc construction, Ramer-Douglas-Peucker simplification, Chaikin smoothing, regular polygons, stars, variable-width stroke outlines and rounded rectangles.

Six existing vector-core operations are also promoted to first-class hands: cubic splitting, path joining, polyline offset, exact axis-aligned rectangle booleans, variable-width outline calculation and SVG appearance realization.

They extend the existing precision-vector engine rather than introducing another vector document model. The rectangle boolean hand remains honestly scoped to the existing engine's axis-aligned rectangle contract.

## Pixel-art operations

Five executable hands provide palette quantization, Bayer ordered dithering, Floyd-Steinberg error diffusion, spritesheet assembly and tilemap assembly.

The indexed result from quantization retains explicit palette indices, so pixel state is not merely flattened into an opaque render.

## Effect graphs

The existing acyclic effect-graph compiler is now itself an executable hand. That means graph structure, dependency order, masks and output selection are real callable machinery.

This does **not** mean every arbitrary effect node has a renderer. Smart adjustment/filter/material graphs remain `EXECUTABLE_CONTRACT` where the graph is real but a requested node may still require a matching installed execution hand.

## Recipe promotion

`creative-recipes.js` discovers the executable hand registry. Familiar concepts such as `brush.dodge`, `colour.levels`, `filter.gaussian-blur`, `selection.magic-wand`, `vector.star`, `vector-core.split-cubic`, `graph.compile` and `pixel.error-diffusion` route to exact installed hands.

`retouch.perspective-clone` is composed from the existing homography/projective-warp machinery plus the clone execution path.

No capability is promoted merely because its name appears in the 217-item influence catalog.

## Verification boundary

`creative-hands-selftest.js` executes representative adjustment, filter, brush, retouch, selection, transform, vector-core, graph, vector and pixel-art paths and checks that the registry reports exactly **86 executable hands**. It also verifies an out-of-contract blur radius fails visibly. `tests/test_creative_precision_fabric.py` invokes that exact JavaScript proof inside the repository CI suite.

The next useful waves should continue the same rule:

`influence -> smallest reusable primitive -> deterministic executor -> hand descriptor -> recipe composition -> exact test`

Good candidates are raster geometry/liquify, richer mask fields and distance transforms, frequency-domain and denoise operations, general path booleans and path effects, multi-channel material painting, procedural material generators, and time-domain audio/video micro-operations.

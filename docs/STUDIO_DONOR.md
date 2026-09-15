# Studio layers and effects in Universal Creation

The original collaboration-platform raster compositor now runs directly in UC.
Python handles PNG intake and publication; local Node executes the unchanged
JavaScript. No browser, npm modules, AI service or platform server is required.
Node 22 is exercised by CI. Core UC still has no required Python dependencies;
Node is an optional runtime needed only for this compositor. The catalog works
without Node. No automatic installation occurs.

## Create and edit

```sh
axm-assets studio-compositor-catalog
axm-assets studio-compose project.json output-directory
axm-assets studio-edit output-directory/project.json edits.json revised-directory
python tools/studio_compositor_proof.py /tmp/axm-studio-proof
```

A minimal project:

```json
{
  "schema": "axm.studio-composition-project/v1",
  "sources": {},
  "recipe": {
    "schema": "axm.raster-composition/v1",
    "canvas": {"width": 128, "height": 128},
    "layers": [
      {"id": "base", "fill": "#263748"},
      {"id": "paint", "fill": "#D99130", "opacity": 0.6, "blend_mode": "overlay"}
    ]
  }
}
```

Layers composite from first/bottom to last/top. Replace `fill` with
`source_artifact_id` and declare that ID in `sources` as a relative PNG path.
Both humans and machines can use the same recipe or these explicit layer edits:

```json
[
  {"op":"change", "id":"paint", "patch":{"opacity":0.3}},
  {"op":"add", "layer":{"id":"highlight", "fill":"#80DDEE", "blend_mode":"screen", "opacity":0.15}},
  {"op":"move", "id":"highlight", "before":"paint"}
]
```

`remove` takes an `id`; omitting `before` places added/moved layers at the top.
`change` replaces supplied top-level layer fields; it is not a recursive merge.
Changing the layer ID, unknown IDs/operations and removing the last layer fail.
Python `edit_studio_layers(project, operations)` returns a copy; donor validation
and actual pixel execution occur during composition/publication. An invalid
revision cannot overwrite the previous project.

Layer controls include name, visibility, opacity, blend mode, integer x/y offset,
filter list and a mask `{source_artifact_id, channel, invert}`. Mask channels are
alpha or luminance and dimensions must match the source layer. A fill layer uses
canvas dimensions. `global_filters` operate after the layer stack.

| Filters | Parameters |
| --- | --- |
| brightness, contrast | `value`: -1..1 |
| saturation | `value`: 0..3 |
| hue | `value`: -180..180 degrees |
| grayscale, invert | `amount`: 0..1 |
| gamma | `value`: 0.1..4 |
| threshold | `value`: 0..1 |
| posterize | `levels`: 2..64 |
| tint | `colour`: hex RGB/RGBA, `amount`: 0..1; donor uses tint RGB, preserves source alpha |
| blur | `radius`: 1..12 |
| sharpen | `amount`: 0..3 |
| pixelate | `size`: 2..64 |

## Editable output

Each new directory contains `composition.png`, original source PNGs,
`request.json` (the complete request), relocated `project.json` (replayable),
`normalized-recipe.json` and `receipt.json`. Replaying project.json produces the
same PNG. Donor normalization adds defaults and discards unknown extension fields;
the original request and replay project retain them. Output and source SHA-256
values supplement the donor's non-cryptographic internal receipt. Hashes prove
byte identity, not appearance. Existing destination directories are refused.

Canonical material/style/animation systems are not overwritten. A composed PNG
can serve as a texture input; this pass does not implement mesh projection,
normal/height conversion, animation compositing or Photoshop/GIMP interoperability.

## Bounded behavior and limitations

- RGBA8 in encoded sRGB, not linear-light blending. Untagged PNGs are treated as
  sRGB. ICC, explicit chromaticity, non-sRGB gamma and APNG are rejected instead
  of silently converted. Intake supports UC's 8-bit non-interlaced PNG formats.
- Maximum canvas/source dimension 1024, 32 source images, 4,194,304 decoded source
  pixels, 8 MiB per PNG, 32 MiB total compressed source bytes, 32 layers/64 filters.
  A conservative filter-work cap rejects expensive blur stacks before composition.
  Node has a 384 MiB heap flag and a 30-second timeout; these are not a total OS
  memory guarantee or performance benchmark.
- Source paths must stay under the project directory, including resolved symlinks.
  Declared sources and masks must remain available, even for hidden layers.
- Donor `alpha:false` has no flattening implementation and is refused. Add an
  opaque bottom layer instead. Donor box blur averages straight-alpha channels;
  invisible RGB may bleed. The proof uses opaque black screen-blend effect layers.
- No original Studio UI, external connector, global launcher or remote service is
  executed. The complete Studio source and UCP are recovered separately under
  `donors/collaboration-studio`; see its README for dependency and truth boundaries.

## Verification

`tests/test_studio_compositor.py` checks pinned byte identity, analytical source-over
alpha, layer ordering, blend examples, every filter family, masks, clipping,
immutability, replay, layer editing, path/profile rejection, work limits,
timeout/publication cleanup and CLI creation/revision. Sixteen focused tests pass
locally with Node 24/Python 3.12. The dedicated CI requires Node 22 and Python 3.11,
also installs the package and executes its shipped compositor outside the checkout.

The unchanged UCP and mirror bridge fixtures pass. `tools/studio_donor_checks.cjs`
checks the 84 action definitions and compiles recovered inline scripts without
starting a browser. No claim is made that the original whole-platform suites pass
in this partial extraction. Full UC suite results must come from the actual PR CI
head: this local recovery lacks unrelated registry fixtures for a complete run.

The original 384-pixel salvage-panel proof independently decodes with Pillow and
retains identical pixels across its protected AXM nameplate. Static inspection of
AXM-Studio-Donor-Proof.png shows a distinct cyan branched glow and paint overlay,
legible nameplate and full panel framing. This is a 2D effect demonstration, not
a 3D asset or continuous animation. No temporary visual crops were needed.

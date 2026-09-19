# Creation first, editable assets afterward

UC creates assets through machine capabilities. A human can request a creation
through a prompt interface or click a creation control; the machine handles the
internal steps. AI may compose those steps too. This adds no Photoshop-like UI.
Studio remains the existing hands-on editor. Finished assets can be reused to
build something else or edited further there.

`axm-create-surface REQUEST.json NEW_DIRECTORY` and
`axm_uc.surface_creation.create_surface(request, output)` demonstrate that route.
The request contains creation controls, not a hand-written sequence of tool jobs:

```json
{
  "schema": "axm.surface-creation/v1",
  "name": "Stormpost coil housing",
  "seed": 41,
  "size": 256,
  "family": "painted-metal",
  "finish": "comic-salvage",
  "color": [40, 78, 88],
  "effect_color": "#b5eeff",
  "wear": 0.32,
  "charge": 0.95
}
```

A prompt interpreter or existing clickable front door can pass these controls.
This module does not itself interpret arbitrary natural-language prompts. The
current high-level composition is a charged surface; it is an executable example
of reusable internal tool composition, not a claim to automatically create any
possible asset. `axm-create-surface catalog` exposes the supported controls.

| Output | Purpose |
| --- | --- |
| `asset.png` | Finished surface that other creations can use |
| `studio-project.json` + `input.*.png` | Editable layer project and exact captured source images |
| `sources/` + `source-index.json` | Original material bundle, effect graph/SVG and earlier composition |
| `library.json` | Complete portable dependency closure with exact content pins |
| `stickers.sqlite` | Every successful task saved for reuse |
| `parts-index.json` | Discoverable roots for all retained successful creator parts, including unselected parts |
| `atom-library.json` | Semantic novelty groups; cosmetic variants remain overrides/evidence rather than fake growth |
| `plan.json` / `receipt.json` | Inspectable machine execution and evidence |

The retained parts, recipes, controls and exact dependency pins are the machine's
growth memory. Finished PNG/GLB output is useful evidence and distribution, but
is not the source of future capability. Free creation grows only when accepted
construction causes remain available for deterministic reuse and recombination.

The proof calls existing Studio layer tools afterward, lowers the charge opacity,
and saves that separate revision. The saved Studio project exactly reproduces
the finished PNG. The underlying material bundle still loads through the existing
material bridge with its normal, ORM, height, wear and protection maps intact.
This verifies the programmatic Studio handoff, not live UI interaction or native
PSD/XCF export. A PNG is widely usable; the rich layer file is AXM Studio's format.

## Internal tool wiring

- `create_material`: existing six material families and four finishes, optional
  WearLayer controls and normalized protected rectangles. Outputs original PBR
  maps and manifest. The realistic option remains selectable.
- `create_effect`: existing electric-arc topology, canonical recipe and SVG;
  new bounded transparent PNG realization for layer composition. PNG uses radial
  segment coverage and a soft halo, while SVG keeps its original Gaussian blur.
- `compose_layers`: existing Studio masks, blend modes, opacity and filters. Its
  source map uses `{"$asset":{"task":"material","key":"base_color"}}` references
  to exact completed PNG outputs, never caller filesystem paths.
- `edit_layers`: a `{"$task":"composition"}` source plus the existing add/change/
  move/remove edits. Produces a new saved creation and preserves the earlier one.

These operations coexist with procedural 3D parts and animated assembly jobs.
Each task carries id, name and origin; optional version and tags are explicit.
The machine resolves typed references only to declared completed dependencies.
Wrong media, missing inputs, bad pins or conflicting definitions reject the run.

Creative outputs use `axm.sticker.creative-task/v1`; their `recipe.dependencies`
contains exact sticker pins. The independent registry library walker retains that
closure without executing UC. Shared sources are stored once in the portable
bundle, including diamond-shaped dependency graphs. Existing 16-depth, 4096-item
and 32 MiB asset limits remain; the limits are never silently truncated.

Workers have separate registries. Timeout/cancellation terminates the worker tool
tree, including Studio's Node subprocess (Linux process groups; Windows taskkill).
This is trusted local execution, not a hostile-code sandbox or enforced RAM quota.
Effect rasterization additionally caps dimensions at 512 and pixel visits at
16 MiB. Source PNGs and composition retain Studio's existing limits.

The composited color image does not automatically replace an entire physically
consistent PBR material: its artistic overlay has no corresponding new normal or
roughness interpretation. Original material channels remain separate. Explicit
3D projection/binding and more high-level creation compositions are next steps.

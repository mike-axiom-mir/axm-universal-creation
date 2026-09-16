# Product workflows and native textures

UC now prepares production steps from the product type and runs supported draft
recipes through its existing profession crews. Logical steps remain separate
even when they finish in one call. Existing stepwise checkpoints, specialist
tournaments, source-backed profession bodies and scoped practice remain the
orchestration machinery.

## Product coverage

| Product | Product-specific work in the plan | Executable draft recipe in this change |
| --- | --- | --- |
| Material | Surface intent, maps/layers, map checks, look development | Generate maps, independently reopen/check them, preserve source and delivery manifest |
| Static 3D | Blockout, geometry, UVs, materials, assembly, LOD/collision | Generate/check materials, optional automatic UVs and mesh baking, measure density/coverage, native previews and optional Blender/Cycles or Godot targets |
| Animated 3D | Static production plus rig, deformation, timing and playback | Preserve supplied rigged GLB, check sampled deformation/declared contacts and loops; optional fresh Blender/Cycles imports and renders |
| Game | Playable loop, rules, world, asset production, audio and playtests | Plan with explicit evidence and owners; existing game capabilities need selected bindings |
| Software | Brief, architecture, implementation and behavior checks | Publish supplied source and independently run supported project checks |
| Web | Direction, interaction states, implementation and browser checks | Publish supplied source and run static project checks; browser evidence remains separate |
| Image | Composition, editable layers, colour and intended-size inspection | Plan with explicit evidence and owners |
| Audio | Sonic intent, sources, mix and listening | Plan with explicit evidence and owners |

All profiles include refinement, target validation, delivery and retained local
practice. Profile ownership changes by domain. Planning does not mean those
specialists executed or that the product passed their judgment.

`product-workflow` operations:

- `catalog`: inspect profiles and executable recipes.
- `plan`: supply `product_type` and a `brief` with `purpose`, `target` and
  `quality_intent`. Optional `stage_actions` bind exact existing capability
  requests. The result includes a validated `stepwise_plan` for the existing
  `stepwise-workflow` surface. Unbound steps remain analysis/evidence work.
- `build`: add `path`, `run_id`, optional `crew_id`, and recipe/source inputs.
  Every automatic station is executed and independently observed by the crew.
- `refine`: build at a **new sibling directory**, naming `refines` (the previous
  `delivery.json`) and `revision_reason`. The previous source/artifacts remain.
- `verify`: reopen a `delivery.json` and recheck artifacts and crew observations.

The compiled draft sequence is source/brief -> material generation -> map checks
-> textured assembly -> geometry/UV checks -> studio preview -> garage preview
-> delivery manifest. Missing/failed checks stop downstream work. Images prove a
render exists; artistic acceptance remains an explicit later step.

Repeating the same crew/run request returns its record and rechecks freshness.
An interrupted run does not silently repeat uncertain writes. A changed request
requires a new run identifier. A new run refuses an existing output directory.

Run the included example:

```sh
python tools/product_workflow_demo.py creations/product-demo
```

The example first builds maps below its stated size requirement and stops before
asset export. A linked revision increases the maps to that requirement, then
creates a textured 656-triangle field case and renders it under two lights.
The previous failed draft remains available. `--quick` uses smaller real assets
and renders for CI; it is not the visual evidence run.

Machine request examples live in `examples/requests/product-workflow-*.json`.
Use `PYTHONPATH=src python -m axm_uc create <request.json>`.

## Material and texture capabilities

The earlier generator already provided six families (painted metal, woven
fabric, rubber, leather, ceramic, carved wood), finishes and protected wear
layers. This change connects that machinery to native asset realization.

Painted-metal recipes also accept bounded `surface_parameters`: wear, scratch
count, grain scale, paint/metal roughness, normal strength, height amplitudes,
scratch/pit depth and colour/roughness variation. The chosen controls are stored
with the material. Omitting them preserves the previous generator defaults.
Other families reject these metal-specific controls rather than ignoring them.

| Capability | Artifact or measurement |
| --- | --- |
| `generate-game-material` | Existing deterministic map bundle from explicit recipe |
| `inspect-game-material` | Fresh PNG/integrity/colour-space, map size, normal length, byte-budget and optional opposite-edge checks |
| `bind-textured-asset` | Native GLB from supplied surface geometry/UVs and verified named bundles |
| `inspect-textured-asset` | Decoded geometry, texture coverage, actual UV texel density and optional maximum world dimensions |
| `render-asset-preview` | Actual embedded GLB maps rendered by UC, with exact source/PNG receipts |

The `axm.surface-3d/v0.1` encoder accepts optional `texcoords` per vertex and a
`textures` object per material group. That object requires base64 RGB PNG values
for `base_color`, `normal` and `orm`, plus `normal_convention: "tangent +Y"` and
`wrap: "clamp"` or `"repeat"`. Missing/collapsed UVs and unsupported encoding
fail before publication. Existing untextured specifications retain their form.

The encoder embeds image bytes, `TEXCOORD_0`, core material bindings and samplers.
Occlusion shares the packed ORM image with metallic/roughness. The source bundle
stays intact; its declared -Y normal map is converted only in the +Y derivative.
Base colour uses sRGB; roughness, metallic, AO and normal values stay linear
data. Material factors and vertex colours remain explicit multipliers.

The inspection renderer supports bilinear magnification and trilinear mip
sampling, with sRGB decoded before filtering and normal mips renormalized.
Odd-sized maps retain their edge pixels. Direct lighting uses metal/rough
microfacet terms and a triangle-derived tangent frame. AO affects the approximate
ambient term. These improvements do not establish target-renderer parity.

Image decoding is deliberately bounded to noninterlaced 8-bit RGB PNG with
IHDR/IDAT/IEND chunks, each side at most 2048, 16 MiB encoded per map and 64 MiB
decoded base-level texture data per inspection scene. Material generation retains
its existing 16..512 size bound; this work does not equate larger maps with
better art. Native PNG decoding accepts all five standard scanline filters.

No Blender, GPU, network connection or AI is required for the native route.
The optional production route now adds automatic UVs, mesh baking, physically
lit reflection rendering using local Blender/Cycles, plus real Godot import,
render and stepped-animation observations. Use `production.targets` to require
multiple independently observed engines.
See [Mesh production](MESH_PRODUCTION.md) for requests, runtime setup and limits.

## Quality work still needed

The workflow records these requirements instead of implying they are solved:

| Area | Remaining work |
| --- | --- |
| Art direction | Per-product references, silhouette/composition judgment, coherent detail hierarchy and actual user acceptance |
| UV authoring | UDIM, painted-atlas repacking, seam editing and all-mip padding; automatic per-material unwrap and overlap/base-padding checks now execute |
| Baking | Curvature/thickness, explicit cage meshes and universal tangent parity; AO/high-to-low normals with extrusion/distance hit checks now execute |
| Materials | Mesh-aware edge wear, authored decals, richer material graphs, perceptually seamless tiling and compressed texture delivery |
| Rendering | Transparency, anisotropic filtering and additional engine comparisons; environment/reflections and Blender/Cycles and Godot target observation now execute |
| Animation | Automatic rig creation, secondary motion, self-intersection, transition quality and real-time continuous playback; actual stepped Godot playback, sampled collapse/stretch and declared contacts/loops now execute |
| Games/software | Real controls and full loops, sound, accessibility, recovery and measured device performance |
| Refinement | Defect-led revisions, representative comparisons, dependency-aware partial rebuilds and semantic review |

Opposite-edge pixel agreement is only a bounded tiling check. The original product_workflow_demo's UVs are explicit per-polygon projections
with intentional shared space. mesh_production_demo uses actual automatic unique
atlases and native overlap/padding checks. The field case is an original inspection fixture, not
a claim of cinematic realism or a finished game asset.

The output status is `DRAFT_BUILT_REVIEW_REQUIRED` after its automatic recipe
passes. `delivery.json` preserves per-stage observed/partial/declared/pending
status and `released: false`. Technical PASS does not imply all lifecycle work
or professional acceptance is complete.

## Sources consulted

The implementation follows core glTF channel/colour conventions described by
[Khronos's PBR guide](https://www.khronos.org/gltf/pbr/) and the
[glTF material schema](https://github.com/KhronosGroup/glTF/blob/main/specification/2.0/schema/material.schema.json).
The broader gaps align with the separate UV/mesh/texture stages described by
[Blender's UV workflows](https://docs.blender.org/manual/en/latest/modeling/meshes/uv/workflows/index.html)
and the typed colour-management concepts in the
[MaterialX specification](https://materialx.org/Specification.html).
No implementation code or artwork was copied from those references.

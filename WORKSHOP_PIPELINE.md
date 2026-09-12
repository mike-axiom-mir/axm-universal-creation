# Reproducible survivor workshop

The custom workshop v03 was previously an external authored recipe that
temporarily replaced `procedural_3d._geometry`, then amended the exported GLB.
UC now supports explicit surface meshes through the existing native 3D
capability. The workshop uses that supported contract, with no global function
replacement and no post-export geometry rewriting.

```bash
PYTHONPATH=src python -m axm_uc survivor-workshop creations/workshop
PYTHONPATH=src python -m axm_uc pipelines --goal result.kind.mixed-project-directory
```

Open the generated `index.html` locally. It embeds the actual GLBs, decodes their
position/normal/color/index buffers, and renders both detail levels with a
small offline WebGL viewer. Near/far selection, orbit, zoom and reset are
included. Download links point to the same exported files. No CDN, account,
network service, Blender or AI is needed to generate or open this bundle.
The viewer requires a WebGL-capable browser and uses simple directional
lighting, not a full physically based material renderer.

The composition is executable today:

`authored recipe -> explicit surface specification -> native GLB encoder -> decoded geometry validation -> mixed-project request -> transactional publication`

`workshop_project.workshop_request(path)` is also a normal Python API. The
pipeline mapper exposes the fifth explicit request builder and its connection
to the existing mixed-project capability. It still does not execute arbitrary
discovered pipelines automatically. Counts are now 52 mapped nodes and 25
candidate edges, while live capability and executable-package counts remain
32 and 15.

## Reusable surface contract

The existing `procedural-glb-asset` route accepts
`axm.surface-3d/v0.1` alongside the unchanged primitive schema. A surface request
supplies a name and material groups; each group supplies a portable ID,
positions, normals, triangle indices, material color/metallic/roughness, and
optional linear RGBA vertex colors. Coordinates are authored directly; surface
nodes use identity translation/scale. Material base colors supplied as hex are
interpreted numerically as linear factors, consistent with the native writer.
The workshop converts its authored sRGB palette before supplying those factors.

Bounds: 128 groups, 65,535 vertices per group, 131,072 total vertices and
131,072 triangles. Input is data, not executable Python or JavaScript. Invalid
values, counts, indices and geometry fail before publication. Emitted float32
geometry is decoded and checked, including vertex-color ranges. The validator
does not prove manifoldness, collision fitness, self-intersection absence,
texture quality or target-engine compatibility.

The reusable `SurfaceBuilder` in `surface_geometry.py` contains the authored
surface operations used by the recipe: beams, boxes, bent pipes, tire rings,
sagging cloth and vertex weathering. `survivor_workshop.py` retains the authored
building composition. These helpers construct supplied designs; they do not
independently invent art direction.

## Artifact handoff

| File | Role |
| --- | --- |
| `building-workshop-a.glb` | Near model, 11,338 triangles, nine material groups |
| `building-workshop-a-lod1.glb` | Far model, 3,174 triangles, nine material groups |
| `manifest.json` | Digests, decoded verification, bounds, source identities and explicit limitations |
| `index.html` | Offline inspection of the exact GLB data |
| `README.txt` | Controls, regeneration command and scope |

The two detail levels are authored versions of one recipe, not automatic
arbitrary-mesh simplification. Bounds include canopy and ropes. Entrance and
fabrication-output markers are manifest metadata, not embedded GLB sockets or
collision geometry. The generated status remains `CREATED`. Neither game rules
nor the RTS repository are changed by the command.

## Provenance and verification

Original assistant-authored workshop recipe SHA-256:
`72b8a6419155546d7dbf062d40bef2cf8c9550990374a5f132ce3e26b92f1b87`.
Source originated in this conversation's workshop v03 handoff; no downloaded
artwork was introduced. The original handoff remains unchanged.

`examples/surfaces/workshop-v03-reference.json` retains hashes of the original
exported attribute buffers and material factors. Tests compare every material
group of both new exports against that reference: positions, normals, indices,
linear vertex colors and scalar material factors match exactly. Container
metadata and GLB digests change because the supported encoder now truthfully
records the surface specification instead of a temporary primitive surrogate.

Additional regressions cover repeatability, input preservation, bad geometry,
color limits, output verification and refusal to overwrite an existing project.
The viewer's JavaScript was syntax-checked. Cloud Browser rejected opening the
local preview URL under its URL policy; no workaround was attempted. This pass
does not claim actual browser rendering or interaction verification.

Full validation: `python tools/build.py` passed 492 tests in 57.176 seconds
(`BUILD_OK`). The CLI produced a real five-file workshop handoff through
`AXM-CAP-WRITE-MIXED-PROJECT`. Both exported attribute sets matched the v03
reference. The current mapper reported 52 nodes and 25 candidate edges.

Next integration: import one selected detail level and its material groups into
the target outpost renderer, define collision/placement independently of visual
bounds, and observe the result at gameplay distance. This change closes the
supported generation/publication gap; that runtime integration remains open.

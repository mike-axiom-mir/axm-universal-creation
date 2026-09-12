# RTS reference foundry

The eight supplied AXM Global State RTS concept sheets now have an authored
83-design catalog and an executable local 3D creation path. Seven repeated
labels on the overview sheet resolve to existing designs. Header panoramas,
palette swatches and silhouette legends are reference context, not extra assets.

```bash
PYTHONPATH=src python -m axm_uc rts-reference-pack OUTPUT
PYTHONPATH=src python -m axm_uc rts-reference-pack OUTPUT --asset crew-worker --asset bathtub-turret
```

`rts_foundry.reference_pack_request(path, asset_ids=None)` is a normal mixed-project
request builder. It is visible in the pipeline mapper, alongside the previous
workshop path. The old workshop recipe and its exact-output tests are unchanged.

## What the machine gained

- Dependency-free ellipsoids, beveled boxes, revolved profiles, elliptic hollow
  tubs, parabolic dishes, tires and track modules, corrugated panels, vegetation,
  lamps, fasteners, patch plates, tied cargo and geometric stencil lettering.
- Shared small detail operations improve every relevant authored asset family.
- Exact attribute welding reduces repeated vertices without merging distinct
  normals/colors or altering triangle topology. Far views remove bevels and
  reduce surface/ring/cloth subdivisions and small detail.
- Named component pivots and bounded glTF rotation clips. Crew have rigid limb
  walk cycles; wheeled vehicles have drive clips; turrets have aim clips; gates,
  scanners and drills have the applicable bounded mechanism clips.
- Linear PBR material factors, weathered vertex colors and emitted lamp/meteor
  material factors. The export does not require external textures or models.
- Explicit collision/placement proxies and sockets, separate from visual meshes.
  Gate-closed collision is conditional. The market gate leaves its passage open.
  Props do not automatically become navigation obstacles.
- A local file-picker WebGL viewer reads the actual GLBs, including rigid node
  clips. It never fetches files or scripts from a server.

The catalog holds the original reference filenames and SHA-256 values. The
models are assistant-authored interpretations of the supplied images, with
inferred unseen sides. Pixels from those images are not used as fake 3D panels.
Source images remain unchanged. No claim of automatic image reconstruction is
made: explicit recipes bridge visual interpretation to deterministic machinery.

## Publication and limits

Small selections publish loose files through the existing transactional mixed
project writer. Above 50 MiB, the same builder packages the validated files into
a deterministic ZIP with fixed entry metadata. The writer then publishes the ZIP
and a small download page. The generic 64 MiB project / 16 MiB file limits remain
unchanged. The reference archive also refuses more than 256 MiB uncompressed or
16 MiB compressed. Select smaller subsets if an expanded catalog reaches either
limit. No automatic extraction or overwrite is performed by the machine.

An extracted complete pack contains 166 visual GLBs (near/far), 69 collision
GLBs, the offline viewer, catalog, manifest and README. Supplied dimensions use
meters, Y up and Z forward. The game controls LOD distance, hit detection,
pathfinding, animation scheduling, scaling and terrain alignment.

## Evidence and boundaries

The encoder decodes all emitted triangles, normals, indices and colors. The
assembly verifier checks local pivots against the declared bind transforms,
finite animation time arrays, normalized quaternions, valid targets and clip
identity. Tests independently check positive volume of closed helper surfaces,
repeatability, bind-pose reconstruction, nonconstant limb animation, malformed
clip rejection, all 83 near/far exports and existing-output preservation.

`tools/review_rts_foundry.py` independently decodes the exported GLBs with NumPy,
rasterizes their actual triangles with depth testing and backface culling, and
produces eight family contact sheets plus three sampled animation GIFs. Pillow
and NumPy are optional review dependencies; creation itself stays standard-library
only. Review images are evidence of those software-rendered meshes, not browser,
physics engine or target RTS behavior. The viewer JavaScript is syntax-checked.
The earlier cloud-browser local-file policy block remains in force; this work
uses no workaround and does not claim browser observation.

These are stylized geometric first-edition interpretations. They do not equal
the illustration detail or finish of the references. There is no skinned human
rig, full combat animation set, UV texture baking, transparent glass, measured
GPU budget or certified target-engine import. A GLB that parses does not prove
its game integration. Coarse colliders are not detailed walkable interiors.

## Root review

Truth: all counts come from the explicit catalog/exports; prototype visual
fidelity and runtime limitations remain visible. Agency: local explicit calls,
no service dependency or overwrite, and no silent edits to the RTS project.
Continuity: source references, aliases, material intent, old workshop outputs and
other main material integrations are retained. Wisdom before speed: real shared
geometry, validation and handoff data provide reusable capability; no claim of
400 completed organs or AAA quality follows from the catalog size.

Root fit supports integration after the final repository checks pass. This
review does not substitute for those checks or for the target-game acceptance.

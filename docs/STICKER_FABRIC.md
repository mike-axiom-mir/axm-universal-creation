# Sticker fabric and local registry

A sticker is an immutable, versioned editable creation. A placed instance pins
that exact definition and stores its own parameter overrides and placement.
Registering a new version does not update existing creations. Rich source remains
canonical; cached images and attached GLBs are derived realizations.

## Repository boundary

`src/axm_stickers/` is the standalone fabric core, including the registry.
It imports only Python's standard library. Other programs can use this package,
the JSON contracts, or the portable SQLite/JSON bundles. No UC, AI, browser,
Node, network, account or registry service is needed to register/search/resolve.

`src/axm_uc/sticker_adapter.py` is a separate consumer. Its 2D adapter executes
UC's existing Studio compositor (local Node required). Its rigid 3D adapter uses
UC's existing GLB pose reader (standard library only).

The suggested future dedicated repository is `axm-sticker-fabric`; keep registry
code in it initially. A public registry service may be added later if actual
sharing/discovery needs it. This change creates no repository or service.
`tools/sticker_proof.py` produces an independently installable `standalone-core`
folder, with license and a pyproject for `axm-sticker-fabric` v0.1.0. The same
source is packaged in UC today. Avoid maintaining divergent copies when moving
it: choose one package source and pin consumers to released versions.

## Definition and instance contracts

| Definition field | Meaning |
| --- | --- |
| `schema` | `axm.sticker/v1` |
| `id`, `version` | Portable name and positive integer version |
| `name`, `tags` | Display name and indexed exact search tags |
| `origin` | Required author, license and source declarations; not a rights audit |
| `adapter` | Explicit recipe interpreter identifier |
| `attachment` | 2D/3D space, compatible socket kind and source anchor |
| `recipe` | Original editable declarative creation state |
| `assets` | Logical source IDs mapped to exact content digests |
| `parameters` | Explicit controls, defaults, ranges/choices and recipe paths |

The core validates contracts, not an arbitrary recipe's execution. UC adapters
validate their supported recipe forms before rendering. Nothing in a recipe or
bundle is evaluated as Python, JavaScript or shell code.

Parameters support numbers, integers, booleans and explicit choices. Paths refer
only inside the recipe, must already exist, must not overlap, and their defaults
must equal source values. Out-of-range or undeclared changes fail. Edit the
canonical recipe and register a new version to expose new controls.

An `axm.sticker-instance/v1` contains an independent ID, exact
`{id, version, digest}` pin, overrides and placement. A wrong pin or socket kind
fails. The API deliberately has no floating `latest` reference or silent upgrade.
Instance state belongs to the consuming project; the registry does not silently
modify a project's placements.

## Registry API and CLI

```python
from axm_stickers import Registry, instance, resolve

with Registry('stickers.sqlite') as registry:
    definition = registry.get('salvage-signal', 1)
    placed = instance(definition, 'helmet-badge',
                      overrides={'signal-opacity': 0.7},
                      placement={'translation': [120, 80], 'rotation': -15})
    editable_recipe = resolve(definition, placed)
    matches = registry.search(tag='salvage', socket='surface', limit=30)
    portable_bundle = registry.bundle('salvage-signal', 1)
```

`register(definition, assets)` accepts a digest-to-bytes map; existing verified
asset blobs can be reused without resupplying them. Same version/same definition
is idempotent; same version/different definition fails. Source assets are shared
by digest. `import_bundle` checks exact declared asset membership and byte
integrity before committing. Metadata, tags and assets commit together.

```sh
axm-stickers stickers.sqlite request.json
# or, using just the standalone package:
python -m axm_stickers stickers.sqlite request.json
```

Example request: `{"operation":"search","tag":"salvage","limit":30}`.
The CLI also accepts `get`, `register`, `bundle` and `import_bundle` with the
same keyword arguments as Python. For binary intake through JSON, use a bundle
with base64 assets. Search supports adapter/socket/tag filters and row cursors;
it does not load every asset or choose a most-recent version for the caller.

## 2D layered stickers

`register_studio` captures an existing Studio project's exact source PNGs and
editable layer recipe. Parameters can expose layer opacity, filters and other
existing values. The first adapter provides translation, positive X/Y scale,
rotation in degrees, opacity, declared pixel anchor and ordered alpha compositing.

`stamp_layer` resolves instances, renders each unique resolved recipe once per
call, and reuses those pixels. Pixel-edge coordinates and nearest-neighbour
sampling are explicit. Positive angles rotate clockwise in image coordinates.
Rendering is encoded sRGB RGBA8, following the existing Studio donor.
Antialiased resampling, arbitrary surface wrapping, mesh UV projection and
normal/roughness decal channels are not implemented in this first adapter.

`publish_sticker_scene(output, registry, host, source_root, instances)` writes:

- `scene.json`: canonical host and independently editable instance placements;
- `stickers.sqlite`: only the selected definitions and exact shared sources;
- `preview/`: a replayable Studio project and composed PNG;
- `receipt.json`: instance count, cache reuse, clipped work and claim boundaries.

The preview's combined placement layer is flattened for rendering. The nested
source recipes and instance controls remain in the scene and selected registry.
Reload `scene.json`, adjust an instance and publish a new output to regenerate.
Do not use its flattened preview as a replacement for the editable scene.
The publisher refuses to overwrite an existing target. Original host layers and
source data remain retained; host global filters still apply to the composition.

## 3D and animated sockets

`register_glb` retains a rigid GLB and optionally exact editable source bytes.
`attach_glb` creates a derivative by adding a mount node and target socket node.
Original mesh, material, source buffer and internal animation definitions remain
intact. Source bytes remain unchanged in the registry. The first adapter refuses
skinned assets, external images and multiple scenes; it is not mesh fusion or a
skin/retargeting system.

Frames use row-major matrices multiplying column vectors; GLB matrices are
converted to glTF's column-major serialization. Use glTF metres and +Y up.
Source and target sockets must be proper rigid frames. Uniform positive instance
scale and a rigid local offset are allowed. The transform is:

`target_frame × local_offset_and_scale × inverse(source_anchor_frame)`

An optional trace of 2–240 `{time, frame}` samples creates a named glTF LINEAR
animation for the target socket. Times strictly increase from zero; its initial
frame must match the declared target. Translation and quaternion rotation are
exported, with shortest-path continuity. Existing internal clips are retained,
but the adapter does not implicitly mix them with the new attachment clip.
An engine or another host can instead evaluate `attachment_matrix` directly for
each current socket frame. No renderer is necessary for the placement math.

## Evidence and limits

Run `python tools/sticker_proof.py OUTPUT`. It creates one original salvage
signal badge as layered 2D and raised 3D forms, actual original/animated GLBs,
editable source, portable scene, registry and standalone installable core.
A fresh registry replays the 2D scene byte-identically. The GLB pose reader
independently samples the new exported socket motion at 17 times.

The proof also registers 1,000 synthetic metadata entries sharing the same two
source images and places 1,000 instances using one render. These are load-test
fixtures, **not 1,000 distinct finished designs**. Timings in `proof.json` are
local observations, not an instant-render promise for arbitrary hardware/assets.
Optional `python tools/sticker_proof.py preview OUTPUT` uses matplotlib to plot
actual GLB geometry and poses; it is flat-colour inspection, not PBR rendering or
continuous target-engine playback. The first preview's per-object painter sorting
hid the raised emblem; sorting all faces together repairs that inspection error.

Bounds: 2 MiB per definition/instance, 64 parameters/assets, 32 MiB referenced
assets per sticker, 512 MiB registry, 100 search results per page. 2D placement:
1–4,096 instances, 32 unique renders, 4M cached pixels, 16M clipped pixel visits,
and Studio's existing 1,024-pixel dimension/runtime bounds. Resource ceilings
reject work; they never silently remove details from canonical source.

Next: a human/machine placement panel, smoother optional resampling, measured
surface projection and nested assembly references. Practice-to-registry promotion
should remain an explicit registration with source and evidence; it is not wired
automatically by this pass. No physics/collision, shader portability, arbitrary
3D sticker material editing or continuous playback acceptance is claimed.

# Create, save and assemble reusable parts

UC is standalone. Its own installation contains the local registry, creation
commands and render adapters. `axm-sticker-fabric` is an optional catalog/tool
sharing repository; UC needs neither that checkout nor a network service.

Humans, deterministic scripts and AI orchestrators use exactly the same requests:

```sh
axm-sticker-create parts.sqlite request.json
axm-stickers parts.sqlite registry-request.json
```

`axm-sticker-create` accepts these operations:

| Operation | Inputs besides `operation` | Result |
| --- | --- | --- |
| `create_3d` | `spec`, `id`, `name`, `socket`, `author`, `license`, `source` | Procedural GLB saved with exact editable JSON source |
| `save_glb` | `file`, optional `editable_source_file`, same metadata | Existing rigid GLB captured as a reusable part |
| `save_2d` | `project`, `id`, `name`, `author`, `license`, `source` | Editable Studio layers and source images captured |
| `instance` | `sticker_id`, `version`, `id`, optional `overrides`, `placement` | Explicit pinned independent instance |
| `save_assembly` | `id`, `name`, `children`, `origin`, optional `ver`, `socket`, `anchor`, `tags`, `parameters` | Group saved as another reusable sticker |
| `export_assembly` | `id`, `ver`, `output` | Actual GLB and measured receipt |
| `export_library` | `id`, `ver`, `output` | Root, transitive definitions and all exact assets |
| `import_library` | `bundle` | Atomic verified import of portable library |
| `search` | optional `tag`, `adapter`, `socket`, `after`, `limit` | Indexed discovery |

Paths resolve relative to the request file. Existing outputs are refused. Core
`axm-stickers` also exposes `save_assembly`, `library_bundle`, `import_library`,
`instance`, `register_many` and its prior registry operations. These commands
are an authoring interface, not a claim that a drag-and-drop editor exists.

## Composition contract

A child is `{instance, target, motion, clip}`. `instance` is the ordinary pinned
sticker instance. `target` is `{space: "3d", socket: "mount", frame: [...]}`.
Frames are proper rigid row-major matrices multiplying column vectors. Target
frames are local to the saved parent's original source coordinates. A sticker's
anchor and instance offset/uniform scale remain explicit. `motion` is null or
2..240 local `{time, frame}` samples starting at zero with the declared target.
`clip` is null or the exact leaf GLB clip name to participate in AssemblyMotion.
Assemblies may contain assemblies; unique child IDs are scoped to each group.

The exporter shares mesh, material, texture, sampler and binary resources for
identical GLB source bytes. Placements have independent nodes and inherited
parent transforms. All original leaf clips are retained under path-qualified
names. Only explicitly selected clips join the combined clip; source clocks
are preserved without resampling, retiming or automatic loop repair. Short
tracks hold their endpoint while longer tracks continue. Do not play a retained
source clip and AssemblyMotion on the same nodes simultaneously.

The exported GLB is a derivative. Its extras contain pins/origin and its receipt
maps source paths to nodes. The portable library contains every original GLB,
editable source and definition, including the saved assembly tree. Shared assets
appear once in a library. No expensive output replaces the original recipe.

## Reproduce a complete original example

```sh
python tools/sticker_assembly_proof.py /new/output/directory
python tools/sticker_assembly_proof.py preview /new/output/directory
```

Rivetwing is a mechanical dispatch beacon built from saved gear-eye and wing
assemblies: 277 expanded records / 272 rigid leaf placements, 15 unique source
GLBs, 826 nodes, 206104-byte animated GLB. `create-requests.json` contains the
ordinary authoring requests in dependency order. A person can edit them, or a
machine can generate them. Replay with the same public function:

```python
import json
from axm_stickers import Registry
from axm_uc.sticker_create import execute
with Registry('new-parts.sqlite') as registry:
    for request in json.load(open('create-requests.json')):
        execute(registry, request, '.')
    execute(registry, {'operation':'export_assembly', 'id':'rivetwing',
                      'ver':1, 'output':'rivetwing.glb'}, '.')
```

Change an existing source by saving a new version, then explicitly repin selected
instances. A model is optional; the registry does not invent parts or silently
promote practice output. Learning sessions can call these same save commands.

## Evidence and current bounds

Tests decode exported hierarchy, sampled source/socket motion, shared resources,
material texture references, atomic failure, exact bundle rebuild, independent
instances, invalid sockets/pins and recursive expansion limits. Source and cheap
realizations remain separate. Preview is offline flat-color decoded geometry,
not material rendering, continuous playback, physics or aesthetic acceptance.

Assembly planning is bounded to 4096 expanded records and 16 levels. This GLB
realizer inherits the stricter pose intake: 2048 nodes, 250000 instantiated
vertices, 128 clips, bounded decoded scalars and 64 MiB output. Resources are
bounded to 32 MiB; unsupported extensions, skins, morphs, cameras and external
resources fail rather than being discarded. PBR core texture slots and unlit
materials are remapped; no surface wrapping, cloth solver, collision, mesh fusion
or automatic LOD is claimed. Bound exhaustion is explicit, never truncation.

Batch registration commits all entries once or none; it does not weaken exact
source verification. A portable library exports exactly the root's dependency
closure. Its import rejects missing, conflicting, corrupt or unrelated content.

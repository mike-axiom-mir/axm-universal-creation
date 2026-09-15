# Parallel creative parts

UC bundles the actual scheduler from `mike-axiom-mir/axm-parallel-capability`
at `85f6d75bf8517bb0171d6a223b2389e03299e4b6`. `fabric.mjs` is byte-exact
upstream source; LICENSE, NOTICE and UPSTREAM.json retain its origin. The original
16-test scheduler fixture runs through a local export facade. UC does not need
that repository, an AI, a service, or a network connection to execute a plan.

Install UC and provide local Python 3.11+ and Node 20+. Run:

```sh
axm-create-parallel plan.json new-asset-directory --workers 4 --timeout 120
```

Python callers use `axm_uc.parallel_create.build(plan, output, workers=4)`.
Humans, deterministic software and AI use the same explicit JSON contract. The
current adapters are `create_3d` and `save_assembly`, using the existing sticker
creator's parameters. This is two wired operation families, not a claim that
hundreds of tool adapters are already available.

Each task runs in a separate Python process with a private SQLite registry.
Independent tasks can run concurrently. Assembly tasks wait for exact completed
dependencies and import their validated, editable library closures. No worker
writes another worker's registry. Final merge uses declaration order, independent
of process completion order. Different content for an existing id/version rejects
the merge, including conflicting successful tasks outside the chosen root.

The plan has exactly `schema`, `tasks`, and `result`:

```json
{
  "schema": "axm.parallel-creation/v1",
  "tasks": [
    {
      "id": "bolt",
      "dependencies": [],
      "request": {
        "operation": "create_3d",
        "id": "steel-bolt",
        "name": "Steel bolt",
        "socket": "mount",
        "author": "AXM",
        "license": "CC0-1.0",
        "source": "Original example",
        "spec": {
          "schema": "axm.procedural-3d/v0.1",
          "name": "Bolt",
          "primitives": [{"id": "head", "type": "box", "size": [0.1, 0.1, 0.1], "translation": [0, 0, 0], "material": {"color": "#87979F", "metallic": 0.8, "roughness": 0.5}}]
        }
      }
    },
    {
      "id": "assembled",
      "dependencies": ["bolt"],
      "request": {
        "operation": "save_assembly",
        "id": "bolt-assembly",
        "name": "Reusable bolt assembly",
        "origin": {"author": "AXM", "license": "CC0-1.0", "source": "Original example"},
        "children": [{
          "instance": {"$instance": {"task": "bolt", "id": "placed-bolt"}},
          "target": {"space": "3d", "socket": "mount", "frame": [1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
          "motion": null,
          "clip": null
        }]
      }
    }
  ],
  "result": "assembled"
}
```

`$instance` may also include `placement` and `overrides`. It must name a declared
direct dependency. The adapter creates the ordinary pinned sticker instance from
the actual completed definition. Saved groups can be dependencies of larger
groups. Children accept the existing explicit socket animation traces and source
clip selection; the executor does not alter animation, material or style intent.

Successful output contains `asset.glb`, `library.json`, `stickers.sqlite`,
`plan.json`, and `receipt.json`. The library contains the chosen asset's closure;
the registry retains every successful task so unused parts remain reusable too.
Source dictionary order is preserved because existing authoring tools save that
order in editable source bytes. Execution timestamps and PIDs vary; authored
source, pins and GLB content remain deterministic for the same plan/tool version.

Limits: 1..256 tasks, 1..8 worker processes, 1..600 seconds per worker, 48 MiB per
plan/library transfer, and existing geometry/assembly/asset limits. Worker count
is a concurrency budget, not enforced CPU/RAM isolation. Disk use scales with
the dependency libraries copied into private jobs. Workers are trusted local UC
tools; this is not a hostile-code sandbox or a distributed device executor.

Failures block dependent tasks while independent tasks can finish. No final asset
directory is created for failed execution or conflicting libraries. Python raises
`CreationFailed` with the full receipt; the CLI writes it to stderr and exits 1.
Temporary worker files are cleaned, so failure receipts do not imply their output
blobs are retained. Successful publication reserves a new directory without
clobbering existing data, then moves the fully verified files into it. Consumers
should wait for the command/API to complete; whole-directory visibility is not
transactional. Interrupts cancel queued jobs and terminate active child workers.

The donor supports pause/resume and checkpointing internally, but this UC adapter
does not expose checkpoint reuse: safe persistent reuse also needs exact tool and
artifact lifetime binding. Nor does this adapter accept arbitrary shell commands,
plugins, remote workers or file-reading tools. Add further tool families through
explicit validated adapters, with their input capture and output merge rules.

`python tools/parallel_creation_proof.py NEW_DIRECTORY` constructs Rivetwing as
19 jobs (15 parts, three groups and final assembly), verifies actual process
overlap, dependencies, serial/direct byte identity, and samples exported motion.
The original 272 rigid placements are preserved. This tests orchestration, not
new artistic quality, CPU utilization, rendered playback or universal speedup.
For tiny jobs, process startup may cost more than the tool computation.

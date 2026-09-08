# Review-driven 3D iteration

The 3D forge has a persistent staged workflow inside the machine. It needs no
GitHub connection. It currently adapts the Axiom and Mir 3D builders; this is not
a claim that all other creation formats have iteration adapters already.

The ordered stages are **silhouette → structure → materials → polish → engine-final**.
Each review must retain the criteria from earlier stages. A regression returns
the run to its earliest failed stage. Every attempt has a separate directory;
failed and interrupted attempts are preserved. The last stage-passing version
remains referenced in state, without implying it is still the final candidate.

The default minimum is seven distinct reviewed versions and the maximum is 24
forge attempts. Seven is a workflow default, not a quality score: failed reviews
count as reviewed versions but cannot pass a stage. Failed renders and exact
duplicates do not count as reviewed versions. In an entirely passing run, the
five stages are followed by two further engine-final revision/review cycles.
The limit produces `LIMIT_REACHED`, never success. Limits can be supplied at
start (`5 <= minimum_iterations <= maximum_iterations <= 100`).

## Start and use

Set `PYTHONPATH` to the machine's `src` directory. The commands below use an
available Python executable; on PowerShell use `$env:PYTHONPATH = 'src'` first.

Create a JSON specification (relative output paths resolve against state-root):

```json
{
  "run_id": "axiom-cowl-refinement",
  "request": {"asset_id": "axiom-bastion-frame", "quality": "hero", "render_resolution": 1024},
  "output": "creations/axiom-cowl-refinement",
  "minimum_iterations": 7,
  "maximum_iterations": 24
}
```

```text
python -m axm_uc.visual_assets_cli 3d-iteration-start spec.json --state-root .
python -m axm_uc.visual_assets_cli 3d-iteration-next axiom-cowl-refinement --state-root .
python -m axm_uc.visual_assets_cli 3d-iteration-forge axiom-cowl-refinement --state-root . --change-summary "Recessed reactor and rebuilt rear pelvis cowls"
python -m axm_uc.visual_assets_cli 3d-iteration-review axiom-cowl-refinement review.json --state-root .
python -m axm_uc.visual_assets_cli 3d-iteration-status axiom-cowl-refinement --state-root .
```

`next` and `status` are read-only. `forge` also accepts `--blender`,
`--no-runtime-bootstrap`, and `--timeout-seconds`. Its new version directory
contains the normal source, GLBs, collision, manifest, and render proofs.
Supply a concrete revision description: changing only the description does
not change the asset. Implement the needed builder/request changes before
forging again. Exact repeated LOD0 hashes or repeated proof sets are rejected;
changed bytes alone do not demonstrate visual improvement.

Inspect every proof image and create `review.json`. Include exactly one entry
per current proof SHA-256, taken from the pending version's manifest:

```json
{
  "notes": "Describe concrete observations across all current views.",
  "views": [
    {
      "artifact_sha256": "REPLACE_WITH_CURRENT_PROOF_HASH",
      "criteria": {
        "faction-silhouette": "PASS",
        "non-toy-proportions": "PASS",
        "functional-topology-all-angles": "UNKNOWN",
        "material-authenticity": "UNKNOWN",
        "aaa-form-hierarchy": "FAIL"
      }
    }
  ],
  "lessons": [
    {
      "id": "recess-reactor-example",
      "evidence": "Replace this with an actual rendered observation.",
      "patch": {"constraints_add": ["Recess the reactor behind a deep protective frame"]}
    }
  ]
}
```

The single entry above illustrates the structure, **not a complete review**.
Repeat it for every current view, with independently observed criteria. Unknown
and failed criteria hold the relevant stage. Lessons are optional; supplied
lessons reuse the existing exact-context learner and are replayed into the next
plan. New patches need new lesson IDs if an existing ID has a different patch.
The observer supplies the judgment and lesson; this workflow does not invent
visual reviews or automatically rewrite the procedural builder.

For an unusable pending version, use:

```text
python -m axm_uc.visual_assets_cli 3d-iteration-reject axiom-cowl-refinement --state-root . --reason "Damaged export; rebuild required"
```

This releases the pending version without deleting it, recording a successful
review, or learning from an unverified artifact. If a forge process is killed,
the OS releases the writer lock; the next forge marks that attempt interrupted
and uses a new version. Existing output directories are never overwritten.
Iteration writers share a nonblocking per-machine lock; retry if one is active.
Do not concurrently use legacy direct learning writers against the same profile.

## Machine interface

The visual expansion bridge exposes the same operations:

- `3d-iteration-start`: `spec` object shown above.
- `3d-iteration-next` / `3d-iteration-status`: `run_id`.
- `3d-iteration-forge`: `run_id`, `change_summary`, optional `blender`,
  `timeout_seconds`, `auto_provision_runtime`.
- `3d-iteration-review`: `run_id`, `review` object.
- `3d-iteration-reject`: `run_id`, `reason`.

State lives in `state/3d-iterations/run-<run_id>.json`. Reopening a run does not
start a background worker; the caller explicitly drives each step.

## Evidence and acceptance boundaries

Before review, the adapter rechecks actual source/export/proof bytes, decodes
GLBs and PNGs, binds the request and asset identity, and rejects changed manifests
or paths outside the version. It does not trust a forge receipt's pass label.
The final artifact needs every technical check and every required visual
criterion to pass in all proof views. Proofs must be distinct and distributed
around the asset (at least four angles, maximum circular gap 135 degrees).

`3d-assess` now also requires a `views` review covering all current proofs.
Legacy single-view reviews still describe that image but cannot grant
`AAA_ACCEPTED`. This intentionally closes the previous single-image loophole.

`AAA_ACCEPTED` is the machine's bounded review result for that exact version,
not an industry certification. Structural GLB inspection and rendered appearance
do not establish watertight topology, rigging, skin weights, animation, or actual
engine import/performance. The current Axiom/Mir exports remain static prototypes
until that separate character-production work is completed.

Tests use synthetic artifacts and mocked rendering to verify workflow behavior;
their passing results are not evidence that the actual characters are AAA.

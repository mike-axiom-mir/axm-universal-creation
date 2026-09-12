# Installed capability connections

Universal Creation can now inspect possible connections between its installed
request builders, live capability manifests and executable organ packages.
The mapper runs offline, reads the current catalog each time, and executes none
of the suggested operations.

```bash
# Discover candidate chains and missing organ-interface providers.
PYTHONPATH=src python -m axm_uc pipelines

# Find routes that end in the mixed-media project writer.
PYTHONPATH=src python -m axm_uc pipelines --goal result.kind.mixed-project-directory

# Find the installed web-interface composition paths.
PYTHONPATH=src python -m axm_uc pipelines --goal interface.local-interaction

# Explicit traversal and result limits.
PYTHONPATH=src python -m axm_uc pipelines --max-hops 3 --limit 20 --search-budget 2000
```

Python: `from axm_uc.pipeline_map import map_capabilities`, then
`map_capabilities(machine_root, goal='result.kind.mixed-project-directory')`.
The return value is JSON-serializable. No files are written by this function or
the CLI; redirect stdout explicitly if you want to save a report.

## What the map means

| Entry or relationship | Source | Meaning |
|---|---|---|
| `request-builder::metal`, `fabric`, `bitmap-label`, `normalize-wav` | Four explicit adapters, checked for local source/function presence | Functions that construct mixed-media creation requests. Source presence alone does not prove their execution. |
| `capability::…` | Current live capability manifests | Declared request kinds, output kind, dependencies and input contracts. A live declaration does not prove host availability or successful invocation. |
| `organ::…@version` | Validated installed executable-organ packages | Exact provided/required interfaces, project types, parameters and limitations. Some packages emit policy documents; the map preserves those limitations. |
| Candidate edge | Exact case-sensitive token match | A declared connection to investigate; no conversion or implicit argument binding. |
| Candidate chain | Bounded traversal of those edges | A possible sequence, never an executable plan or proof of end-to-end compatibility. |

The initial snapshot maps 32 live capability declarations, 15 organ packages,
and four request builders: 51 entries and 24 candidate edges. These counts are
observations of this checkout, not hard-coded catalog totals. New live manifests
and valid organ packages are read automatically. Other Python/JavaScript helpers,
asset files, descriptive anatomy and donor repositories do not automatically
become callable entries. Additional request-builder adapters must be explicit.

The material query finds four paths: fabric, metal, bitmap-label and normalize-wav
each connect to `AXM-CAP-WRITE-MIXED-PROJECT`. Those helpers construct request
**envelopes** for `machine.create`; they are not direct positional arguments to
the writer's internal function. The mapper does not invoke the writer.

## Inputs, alternatives and missing work

`additional_required_interfaces` lists organ inputs not supplied by earlier
nodes in that specific path. A path satisfying one required interface is not
reported as satisfying all of them. `required_parameters` retains caller input
contracts, and `required_dependencies` retains live capability dependencies.
Those dependencies are not confused with output-to-input edges, and their full
execution closure is not certified by this map. The existing organ resolver
continues to own exact assembly resolution, bindings, ambiguity and fixtures.

Edges between organ packages require shared project types; a complete organ
path must share at least one project type across all of its nodes. Cycles cannot
repeat nodes in one path. Multiple valid providers remain separate alternatives.

`missing_interface_providers` is scoped to this catalog and exact organ tokens.
It does not mean a missing ability is impossible or requires a new repository.
A goal with one provider but no chain appears in `single_capabilities`.
Goals are output tokens or case-sensitive namespace prefixes, not natural-language
instructions or semantic similarity searches. Inspect graph node `provides`
values for available goal tokens.

## Search and evidence boundaries

The adapter permits at most 256 catalog nodes and 4096 candidate edges, 1..6 hops,
1..200 returned paths and 1..50,000 visited states. Both work and pending traversal
state are bounded. Results use deterministic breadth-first order, not a quality
score. Goal relevance is applied before result limits. `search.truncated` is true
when work, queue or result limits leave possible paths unexamined; the mapper
never claims completeness in that case. Completeness is always relative to the
chosen hop limit, catalog and goal.

Catalog identity includes manifest content and available declared source hashes.
The report is an observation of local files, not a signed attestation, external
runtime measurement or proof that the inspected bytes executed. It grants no
execution, install, merge or adoption authority.

Selected graph helpers are exact source slices from AXM Monolith at
`6f5b7893d142c5eeaae79897518b3c0b4a57a2e5`, recorded in
`third_party/pipeline-provenance.json`. That snapshot has no LICENSE file;
owned-repo reuse follows the user's authorization without inventing a license.
The donor's writer, refresh command, lexical matching and exhaustive traversal
are not imported. UC supplies its own source-grounded inventory, exact matching,
required-input reporting, project compatibility checks and bounded search.

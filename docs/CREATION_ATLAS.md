# Direction, knowledge, construction and evidence

UC's creation atlas joins its existing libraries into one inspectable graph.
It does not replace the capability store, executable-organ library, asset atoms,
material machinery, product workflows or construction search.

The installed view currently contains 2,385 entries across 27 categories. These
include descriptive research records. They are **not 2,385 working capabilities**.
The index reports the evidence level, source and source digest on each entry.

| Atlas category | Existing source | What the entry establishes |
| --- | --- | --- |
| Shape | Form-pattern grammar and asset atoms | Available construction operations, or explicitly unresolved mesh descriptors |
| Texture | Material channel contracts and texture atoms | Channel meaning and descriptor references; an external asset URI is not an installed texture |
| Material | Native generator families and material-response pack | Generatable map families versus richer response intent requiring a renderer binding |
| Organ | Executable packages and research anatomy | Installed source/declared fixtures versus descriptive organs; indexing does not run fixtures |
| Capability | Live manifests and implementation references | Installed route, inputs, dependencies, implementation and limitations |
| Protocol | Construction, material-bundle and organ-goal contracts | The contract used by an existing executor or verifier |
| Workflow | Product lifecycle profiles | Required stages, owners and evidence; unexecuted stages remain work to do |
| Blueprint | Installed `atlas/*.json` packs | Goal checks and a dependency graph of existing capabilities |
| Recipe | Existing construction-search examples | Editable starting contracts, loaded from their original files |
| File | Grammar profiles and bounded native output formats | Actual supported format/validation scope, not an incentive to emit every format |
| Direction | Software direction catalog | Domain knowledge for choosing a route, not automatic capability sufficiency |
| Experience | An explicitly selected persistent collection | Prior success/failure, measurements and causes; current reuse must be checked again |
| Construction pattern | Semantically grouped successful observations | Measured reusable candidates, separate from admitted capabilities and canon |
| Operator | Typed adapters under `atlas/operators/` | Input/output contracts, metric units and executable tools for discovering new workflows |
| Learned workflow | Confirmed workflow experiment collection | Deduplicated composition structure; current goals and inputs must be rechecked |

Experience, construction patterns and learned workflows appear when a collection contains observations. Extra
categories such as acoustics, joints, manufacturing processes or accessibility
rules can be added as data. Defining a category does not implement its subject.

[Workflow discovery](WORKFLOW_DISCOVERY.md) builds new operator graphs, executes
bounded experiments, ranks measured outcomes across scenarios and retains
structures only after fresh confirmation. It uses this atlas and the same
blueprint executor; the four installed blueprints remain available.

## Retrieve only what the direction needs

Use the ordinary machine route `creation-atlas` (alias `atlas-creation`):

```python
from pathlib import Path
from axm_uc.machine import UniversalCreationMachine

machine = UniversalCreationMachine(Path.cwd())
result = machine.create({
    "kind": "creation-atlas",
    "inputs": {"operation": "query", "query": "ceramic",
               "categories": ["material"], "limit": 10}
})
```

`summary` returns category counts; `get` returns one full record; `closure` follows
its typed relationships. Search is deterministic lexical retrieval with explicit
category filters. Search rank is not evidence that a part meets a goal.

For creation, `purpose` retains the human direction, `direction` selects an exact
route family, `goals` name required outcomes, and `parameters` carry executable
contracts. Humans and optional AI can supply these same values. UC does not
silently translate arbitrary prose into geometry, physics or an aesthetic score.

```json
{
  "purpose": "Find a vessel inside the declared display envelope",
  "direction": "construction",
  "goals": ["construction-criteria", "retained-source", "glb-output"],
  "parameters": {
    "search": {"atlas": "recipe:vessel", "path": ["value"]}
  }
}
```

The `atlas` reference pulls the original recipe into the request as literal
construction data. Supply a changed search contract directly to change its
dimensions, options, acceptance criteria, motion probe or budget. Each intent
keeps its original request plus the resolved parameters and selected knowledge.

Four installed blueprints execute useful work:

| Direction | Goals | Executed work |
| --- | --- | --- |
| `construction` | `construction-criteria`, `retained-source`, `glb-output` | Headless form/character search, decoded-output measurement, retained GLB and creator source |
| `material` | `material-policy`, `material-maps` | Material generation, PNG decoding, channel/integrity checks and caller-defined size/normal/budget policy |
| `software` | `interface-closure`, `project-checks` | Exact installed-organ dependency discovery, source composition, independent project verification |
| `programming` | `acceptance-cases`, `retained-code` | Typed JavaScript/Python compilation, explicit case execution, repeatability and function archive retention |

Choose the goals relevant to the requested deliverable. These do not imply
photorealism, physical balance, live browser interaction or acceptance in an
unobserved target engine.

The programming route connects the standalone compiler/workflow already on
`main`; it requires local Node and Python. It verifies bounded pure functions
against declared cases. See [PROGRAMMING_CREATION.md](../PROGRAMMING_CREATION.md).
The portable runtime carries both donor packages and the atlas pack, and its
relocation test creates a vessel plus verified retained code from another working
directory without a donor checkout or runtime network service.

## Planning and execution

`operation: plan` takes `intent` and optional `memory`. It writes nothing. It
requires complete declared goal coverage, typed parameters, existing knowledge,
available capability entrypoints and an acyclic step graph. Existing search and
organ contracts also receive domain preflight. Organ selection pins the exact
packages selected by the existing interface resolver.

Sufficient blueprints are ordered by step count, then id. An explicit `blueprint`
can select one. Unknown directions, goals, interfaces, parameters and required
capabilities return gaps. A blueprint is not selected merely because it shares a
keyword with the purpose.

`operation: build` adds a new `path`, optional `memory`, and optionally the
`plan_sha256` returned by planning. A changed plan holds before creation. Plans
pin the atlas snapshot, declared sources, Python/data runtime and resolved
request. This is deliberately conservative: unrelated indexed source changes
can require a fresh plan. It is not a sandbox or a complete external runtime lock.

Execution invokes the ordinary capability store in dependency order. Every
step's checks run before downstream work. Goals refer to observed result fields
or retained files. A failed check stops the pipeline and preserves its cause.
`CHECKS_PASSED` means the requested checks passed, within their stated scope.

Each run keeps:

- `intent.json`: resolved plan, original direction, selected knowledge and pins;
- the actual deliverables and each executor's source/evidence files;
- `run.json`: step results, checks, goal observations and file digests;
- `experience.json`: reusable observations and measured construction candidates.

Creation refuses an existing output directory and the protected live machine
body. Blueprint output bindings remain inside the new creation directory.
Installed blueprints are executable machine configuration and use the effects
and boundaries of their selected capabilities; this is not an untrusted-plugin
sandbox. Request parameters cannot install a blueprint or capability.

## Growth by use, with fresh verification

Set `memory` to a persistent experience directory shared by later requests.
Successes and executed failures enter it as content-addressed observations.
The output and memory directories must be separate. The same collection is
queryable through `query`, `get`, `closure`, `summary` and `experience`.

Successful searches contribute their actual settings, construction recipe,
semantic signature and checks. Compatible construction-space and runtime pins
allow a later search to try those settings first. New criteria and budgets still
govern acceptance; previous success cannot turn an impossible new request into a
pass. Failed observations remain retrievable and do not supply accepted seeds.

The construction-pattern view groups by UC's existing semantic signature.
Repeated uses, renames and appearance-only variants do not count as new
construction capability. Observation count and distinct construction signatures
are reported separately. These are candidates; existing tested acceptance and
admission rules still decide reusable-library/canon growth.

Experience is past evidence, not fresh verification of the old artifact. Its
content identity detects accidentally edited records; it is not an authorship or
trust signature. Warm seeds must undergo the receiving search's measurements.
The JSON backend loads a selected collection of at most 4,096 records/64 MB per
request. Larger deployments need scoped collections or an indexed storage
adapter; the category model has no fixed subject ceiling.

## Extending the connected machine

Add records/blueprints to a versioned `axm.creation-atlas-pack/v0.1` file under
`atlas/`. Records have unique ids, arbitrary categories, source-backed data,
evidence labels and typed relationships. `source_data` can point at an existing
JSON file and field path instead of copying a donor catalog.

A blueprint declares `direction`, typed `parameters`, optional `defaults`,
`uses`, `steps`, `artifacts`, `goals` and `limitations`. Each step names an installed
capability, explicit dependencies, inputs and checks. Inputs use literal JSON,
`{"from": "request.parameter"}`, `{"from": "steps.prior.field"}` or
`{"output": "relative/path"}`. Goal checks compare observed result fields with
`equals` or finite numeric bounds, or require a named artifact. Every goal needs
a check; forward references and cycles are rejected.

The next major build is **goal-driven composition of new blueprints**: typed
input/output/effect contracts, unit and coordinate compatibility, reusable
construction edits, and a planner that searches compatible compositions. It
should connect shape, motion, material and target-realization checks in the same
construction body, then propose any missing operator through existing growth
machinery. This atlas provides the inspectable parts, provenance, goals and
measured experience for that planner; it does not claim that synthesis already
exists.

Run the examples in `examples/creation-atlas/` through `machine.create`, or run:

```sh
PYTHONPATH=src python tools/creation_atlas_demo.py /tmp/uc-atlas-demo
PYTHONPATH=src:tests python -m unittest test_creation_atlas -v
```

# Standalone programming creation

UC builds standalone JavaScript and Python modules from typed program data and
explicit acceptance contracts. The compiler, six professional procedures and
observers live inside UC. Python and Node.js are host runtimes; no sibling
repository, npm install, network service, Git command or model is required.
Repository references record the origin of bundled components.

## Create a project

```sh
PYTHONPATH=src python -m axm_uc create examples/code/restock-project.json
node creations/restock-code/javascript/selftest.js
python creations/restock-code/python/selftest.py
```

The example builds a two-function restock planner: select low stock, compute
missing whole units, omit zero orders, trim labels and sort results. Four cases
cover mixed stock, empty input, fractional units and invalid boolean input.
The explicit operation tree generates both languages; the compiler contains no
prewritten restock implementation.

`code-program-project` uses UC's ordinary project writer. It creates a new
directory and protects existing projects and machine internals. `build` writes
candidates without execution, `verify` runs cases, and `retain` also saves
reusable construction after successful verification. Failed verification returns
a structured creation error without publishing a project or replacing archives.
A candidate remains labelled `CANDIDATE` even when its text files validate.

Each project keeps source modules, selftests, `request.json`, `construction.json`,
`workflow.json`, licenses/provenance, and optional `archive.json`/`retention.json`.
The generated modules run independently of UC. Retain construction data when
reshaping or reusing them; generated text is a realization of that construction.

## Inspect and compose

```sh
PYTHONPATH=src python -m axm_uc code-program examples/code/catalog.json
PYTHONPATH=src python -m axm_uc code-program examples/code/compile-invoice.json
PYTHONPATH=src python -m axm_uc code-workflow examples/code/restock-workflow.json
```

These commands return JSON without publishing files; held code commands exit 2.
Python callers use `run_grammar_tool(root, operation, request)` from
`axm_uc.grammar_workbench`.

`code-program` provides `catalog`, `validate`, `compile`, `recipe`, `capture`
and `restore`. Compile takes `program`, `languageId` and optional `cases`.
Recipe takes `id` and `languageId`. Restore takes `archive`, `structuralSha256`
and optional `name`, returning typed program data. Direct capture is structural
capture; use the professional `retain` action for verification before acceptance.

The 48 operations cover arithmetic, comparisons, lazy conditions, immutable
bindings, records, lists, typed calls, map/filter/fold, stable sorting, bounded
indexing/slicing, nullable defaults and explicit string operations. Programs
declare typed functions and exports with acyclic dependencies. Raw source,
arbitrary imports, shell and networking are absent. Operation shapes are in the
bundled compiler's `code-programs/README.md`; `examples/code/` has runnable JSON.

## Professional workflow

| Station | Procedure |
| --- | --- |
| Architect | Map requirements to cases and reachable exports; refuse contradictions |
| Developer Tools | Validate typed source and generate each language twice |
| Build | Compare builds and verify program, source-map and artifact identity |
| QA | Parse and run in fresh processes; compare values/errors, inputs, repeats and languages |
| Integration | Report readiness for the declared cases on the same artifacts |
| Maintainer | Retain additive function closures and construction causes on request |

Workflow actions are `catalog`, `build`, `verify` and `retain`. The latter three
take a `job`; retain optionally takes a previous `archive`. Jobs contain `id`,
one of `program`/`recipeId`, optional `languages`, `cases` and `requirements`.
Explicit programs need explicit cases/requirements. Recipe cases are always
retained; extra cases extend them. Every export needs a successful value case,
and every case must map to a requirement. Full profession bodies remain
EXPERIMENTAL. Matching cases does not establish that prose requirements are
complete or that all branches were exercised.

## Reuse and growth

Load a project's `archive.json` into a later retain request, or select a captured
structural identity and restore it. Compose restored typed functions with new
operations/functions, declare the next exports and cases, and verify afresh.
Renames add no structural atoms; helper dependency closures remain available.
No entries are silently evicted. The suite restores the restock planner, adds
a total-units fold, executes both languages and retains exactly one additional
function. It also runs a published project's own standalone selftests.

## Scope and evidence

This is a restricted pure-function grammar, not arbitrary source translation or
complete application generation. JavaScript and Python are executable targets;
the separate 102-language advisory catalog retains its meaning. Grammar's
100,000-unit per-call work budget and bounded data sizes apply. The executor
uses fixed commands and temporary directories, two runs per language,
15-second subprocess timeouts and bounded output; it is not an OS sandbox.
The workflow timeout is 150 seconds; other grammar operations retain 30 seconds.
Requests are capped at 1 MiB.

Ten local integration tests cover runtime behavior, repeatable builds, source
hashes, restored composition, archive growth, bad expectations, project
protections, refusal paths, CLI status and a relocated bundle with no donor
checkout. Altered source/archive bytes are refused. CI repeats these checks
on Linux and Windows. Whole-repository results are reported separately.

Bundled sources: Grammar 102 `6e9efc2ebf759f9e2d03c933eafaf71856357471` and
Profession Fabric `c7ab2a0e655a755770b962100d3b212aa56c45c8`, with MPL-2.0
licenses and exact provenance under `third_party/grammar-workbench/` and
`third_party/code-professions/`. Existing Grammar Glass components retain
their separate source and Apache-2.0 license.

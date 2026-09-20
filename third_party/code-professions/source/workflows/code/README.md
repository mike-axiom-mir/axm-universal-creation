# Deterministic coding workflow

Six existing Professional Bodies expose executable procedures for bounded code
creation. Humans, models and deterministic callers use the same JSON. The gap
was machinery and handoffs, not missing role names. Full bodies remain
**EXPERIMENTAL**; existing scoped maturity records are unchanged.

| Package | Public export | Work |
| --- | --- | --- |
| Software Architect | `code-plan` | Map requirements to cases and reachable exports; refuse contradictions |
| Developer Tools Engineer | `code-compiler` | Resolve typed source or a recipe; compile twice |
| Build Engineer | `code-build` | Compare builds, verify source identity, artifact paths and digests |
| Software QA / Playtest | `code-evidence` | Assess actual values/errors, input preservation, repeated runs and language agreement |
| Integration / Release Engineer | `code-readiness` | Give bounded readiness tied to the same build and QA |
| Software Maintainer | `code-retention` | Retain verified construction causes and deduplicated function closures on request |

Package manifests expose the public seams. `index.mjs` coordinates them without
copying specialist logic. `contract.mjs` supplies institutional JSON/identity
utilities. The compiler and optional executor are host-supplied capabilities.

## Run

Use a clean Grammar 102 checkout containing `code-programs/`. The tested source
is `mike-axiom-mir/axm-102-grammer` at
`6e9efc2ebf759f9e2d03c933eafaf71856357471`.

```sh
node tools/run-code-workflow.mjs ../axm-102-grammer workflows/code/examples/invoice.json python3
npm test
AXM_CODE_COMPILER=../axm-102-grammer npm run test:code
```

The CLI records the actual clean checkout revision; it does not install or
modify the compiler. An embedding consumer can carry an exact source snapshot:

```js
import {runCodeWorkflow} from './workflows/code/index.mjs';
import {createCodeExecutor} from './workflows/code/runtime.mjs';
const result = runCodeWorkflow(request, {
  compiler, compilerIdentity: {repository, commit},
  execute: createCodeExecutor({python: '/path/to/python'})
});
```

`compiler` implements Grammar's `catalog`, `getRecipe`, `validate`, `compile`
and `remember`. The host verifies the declared identity against its source.
Hashes detect changed/stale inputs; they do not authenticate a dishonest host.

## Request grammar

| Action | Fields | Behavior |
| --- | --- | --- |
| `catalog` | None | Operations, recipes and stations |
| `build` | `job` | Repeatable candidate source; no execution |
| `verify` | `job` | Rebuild, parse and run every case twice per target |
| `retain` | `job`, optional previous `archive` | Verify afresh; return additive archive only on PASS |

A job has `id`, exactly one of `program` or `recipeId`, and optional `languages`
(JavaScript and Python by default). Explicit programs require `cases` and
`requirements`. A case has `id`, `function`, `args`, and exactly one of `expected`
or `error`. A requirement has `id`, nonempty `statement`, and case IDs. Every
case must belong to a requirement; every export needs a successful value case.
All helpers must be reachable from exports. Reachability is not branch coverage.
Recipes retain their bundled cases; additional cases/requirements extend them.

Programs use Grammar's 48-operation typed expression language. Raw source,
hidden fields, recursion and unimplemented targets stay held. The result keeps
the normalized program, plan, source maps, artifacts, compiler revision, actual
observations, requirement coverage and readiness. Artifacts include standalone
source and selftests. The executor reports actual values independently of the
selftests' PASS text; QA compares those values with the declared oracles.

## Execution, retention and recovery

`build` constructs source only. `verify` and `retain` explicitly request the
optional executor: fixed Node/Python commands, fresh temporary directories,
syntax checks, 15-second process timeouts, 8 MiB output bounds, stripped
interpreter environment hooks, and no shell. Missing executables are BLOCKED;
process failures and mismatched cases cannot pass. Only freshly generated
closed-grammar modules enter this standard workflow. It is not an OS sandbox or
arbitrary-source runner. Grammar's per-invocation work limits still apply.
No model, network or caller workspace scan is needed.

Retention returns a new archive and its construction plan. It does not write
storage, evict old entries or promote canon. Consumers save returned values
through their ordinary persistence boundary. Grammar's `restore` export yields
a portable program to rerun with new requirements. Renames add no structural
atoms. On failure, the previous archive stays untouched. Removing the consumer
registration rolls back this integration without rewriting prior creations.

`VERIFIED_FOR_CASES` means the requested cases on the observed runtimes. It does
not prove complete requirements, all branches, application quality, deployment
readiness or whole-profession equivalence. External observations admitted by
`code-evidence` are caller supplied; the standard coordinator gets them directly
from its executor during the same invocation.

## Evidence

`tests/validate-code-workflow.mjs`: 27 checks cover incomplete/conflicting
requirements, omitted/duplicate/stale evidence, input mutation, runtime failure,
repeatability, language disagreement, unverified retention and actual execution
of a frozen Grammar-generated JavaScript fixture naming its source revision.

`tests/code-workflow-integration.mjs`: eight recipes plus a restored dependency
closure produce 9 successful jobs, 36 fresh runtime processes and 68 successful
case observations, with separate deliberate failures, build drift and unavailable
executor checks. CI exercises Node 20/Python 3.11 and Node 22/Python 3.13. Local
checks used Node 24.19.0 and Python 3.12.14; CI results remain separately visible.

Existing package, maturity and research checks pass. No occupational research
or maturity promotion is inferred. Procedures derive from existing package
ownership/evidence contracts and the inspected compiler contract. A seeded
first-run/second-run disagreement exposed a QA reporting defect during
development; QA now compares every complete run across languages.

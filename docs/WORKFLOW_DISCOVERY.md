# Discover, test and retain construction workflows

`workflow-discovery` composes installed typed operators into new dependency
graphs. It executes candidate graphs through the existing atlas blueprint
executor, observes their outcomes, iterates around failures and promising
results, and retains confirmed structures in caller-owned experience.

The initial catalog contains ten adapters for real native tools: form compilation,
derived UV removal, material generation and inspection, direct texture binding,
automatic UV baking, decoded asset inspection, CPU preview rendering, sampled
character motion and typed JavaScript/Python acceptance tests. They are indexed
as `operator` records in the existing creation atlas. A declaration is not a
successful test, and indexing a research organ does not implement it.

## Use the ordinary machine

```sh
python run.py create examples/workflows/vent-hood.json
```

The example supplies geometry, material/bake choices and measurable goals, not a
finished sequence of steps. The planner discovers both direct texturing and UV
regeneration. Insufficient density stops a candidate before preview rendering.
Valid products are compared on density, source map resolution and byte cost.
Source map resolution matters: increasing a baked atlas's size alone does not
create additional source detail. None of these metrics claims artistic quality.

The `workflow-discovery` capability accepts:

| Operation | Inputs | Result |
| --- | --- | --- |
| `catalog` | none | Installed operators, units, measurements and accepted source kinds |
| `plan` | `request`, optional `memory` | Compositions, type reachability, missing observers/tools, dependency pins and plan identity; no creation writes |
| `experiment` | `request`, new `path`, optional `memory`, optional `plan_sha256` | Bounded trials, diagnoses, ranking, confirmation and retained construction causes |
| `memory` | `memory` | Confirmed workflow structures and observation counts; reuse still requires execution |

Use `creation-atlas` with the same `memory` and category `learned-workflow` to
retrieve the resulting structures alongside existing knowledge. Calling through
Python, the CLI or an optional AI uses exactly the same operations.

## Intent must name observable outcomes

The experiment request schema is `axm.workflow-experiment/v0.1`:

- `intent` retains the direction in human language.
- `inputs` maps named sources to explicit types and a finite list of candidate
  JSON construction values. Atlas selectors can load existing recipes as values.
- `goals` names required output types and numeric checks with units and bounds.
- `objectives` defines ranking: goal, metric, unit, minimize/maximize, target,
  normalization scale and weight. Targets saturate; excess detail earns no credit.
- `scenarios` adds up to three stress cases by overriding input values. Baseline
  always runs. Passing baseline alone cannot satisfy a failing stress case.
- `budget` bounds search states, plans, graph steps, actual trials, iteration
  rounds, batch size and confirmation repetitions.
- `operators` can restrict the catalog available to this request.

Types match explicitly, including required units or coordinate attributes. There
is no implicit millimetre/metre conversion. Missing units, unknown measurements
and missing capabilities remain gaps. The current source adapters accept
construction objects, not arbitrary external paths with unpinned contents.

`same_origin_as` requires two goals to refer to the same constructed artifact:
the preview must depict the asset being measured. `uses_goal` requires a goal's
dependency closure to contain another goal's producer: the asset must use the
material whose source quality was checked. Unrelated good test objects cannot
satisfy a product's quality contract.

## Iteration before, during and after construction

Before execution, deterministic backward search wires compatible ports, shares
dependencies, checks goal relationships and bounds the graph. A separate type
reachability report explains which input ports lack matching providers.

During execution, every step retains its actual inputs and observations. Failed
checks stop dependent work. Diagnoses include operator, expected/observed values,
tool checks, errors and steps not executed. The next round first removes
candidates with exactly the same failed dependency closure and checks, then
explores nearby settings/structures around the best valid result or the failed
candidate that made the most progress. Execution exceptions are not cached as
deterministic failures. Batched rounds may spend work on similar candidates
before feedback reaches the next round; `batch_size: 1` applies feedback after
each candidate.

After a candidate passes every scenario, fresh directories receive confirmation
builds of its hardest observed cases. Declared goal metrics and realized
GLB/PNG/WAV/code bytes must reproduce exactly. Confirmation consumes the same
trial budget. Missing confirmation, interruption, incomplete scenarios and
changed bytes cannot become accepted workflows. A progress checkpoint preserves
completed evidence; interrupted experiments are restarted, not resumed as PASS.

This is bounded deterministic exploration and repair. It does not mutate
arbitrary source code, invent new algorithms without testing, or infer a
probability of correctness from repeated success. Failure reuse is local to one
experiment and one pinned context. Every new experiment reexecutes current goals.

## Rank product outcomes, not declarations

Only confirmed candidates enter the ranking. For each objective, the engine
computes the nonnegative distance from its target divided by the declared scale.
It takes that objective's worst deficit over all scenarios, then sums the
weighted deficits. Lower is better. Declared operator cost and stable candidate
identity break ties; wall-clock noise does not reorder results. The report also
retains the nondominated objective vectors as a Pareto frontier.

Hard checks cannot be traded away for a good score. A lower polygon count,
larger texture, smaller file or faster route is not universally better; the
request chooses the relevant constraints and targets. The engine does not
silently score aesthetic intent, physics or an external target it did not test.

The budgets currently allow at most 20,000 search states, 128 candidate plans,
16 graph steps, 256 actual trials and four confirmation repetitions. Individual
tools keep their existing geometry, image, process and other work limits. A
budgeted stop reports untried candidates and truncation; it is not proof of
global optimality. Search bounds are independently reported from experiment
bounds. The deterministic search order is not guaranteed to find the best route
in a truncated space.

## Learning keeps construction causes

`memory/workflow-observations/` stores successful, failed and incomplete observed
attempts with selected source values, goals, cases, wiring, runtime/catalog pins,
diagnoses and evidence hashes. `memory/workflows/` stores confirmed reusable
structure. Full per-step output and artifacts remain in each experiment folder;
keep those folders with the collection when moving a complete evidence archive.

Semantic identity includes operators, versions, wiring, source types and shared
dependencies. It excludes settings, names, colors and prose. Four accepted color
or resolution settings do not count as four new workflow capabilities. All
observations remain inspectable, while the reusable structure is deduplicated.

On reuse, matching structures can be rebound even when the new graph-search
budget is too small to rediscover them. Current input types, available operators,
units, goal relationships and checks are reapplied. Fresh execution is mandatory.
Changed source/runtime/catalog/environment pins make old observations stale.
Compatible structures remain useful: they can be rebound under current operator
contracts, explicitly marked as carrying stale prior evidence, and tested anew.
An unrelated tool update must not erase learned composition knowledge. Removed
operators, changed operator versions and incompatible ports prevent that reuse.
Pins cover the installed Python
and data runtime, indexed atlas, operator catalog, Python/platform and Node
version when available. They are not a complete external environment lock.

The collection is ordinary caller-owned data, not a tamper-proof authority.
Content identities detect accidental edits; a past observation does not authorize
execution outside the ordinary capability boundary. Neither a confirmed workflow
nor a GitHub merge silently promotes machine canon or modifies installed tools.

## Extending tested understanding

Add an operator catalog under `atlas/operators/` with schema
`axm.workflow-operators/v0.1`. Each operator declares version, capability,
operation, input/output types, metric units, cost, dependencies and limitations.
The capability accepts `operation`, `path` and `values`, and returns `status`,
`value`, `metrics` and evidence. A new source kind needs a real validating adapter.
Built-in station operations are implemented in `workflow_stations.py`; adding a
JSON name alone does not implement an operation. Ordinary capability source and
tests remain authoritative.

The next substantial expansion is more outcome observers and repair operators:
actual target-engine import/runtime tests, collision/support/physical constraints,
UV distortion and source-detail preservation, motion sweeps and task-specific
perceptual review. Each should expose measured quantities, units, applicability,
failure localization and retained test inputs through this same contract. That
allows a new tool to participate in discovered pipelines instead of requiring
another fixed end-to-end workflow. Open-ended intent interpretation can then map
human goals to these explicit contracts while leaving unknown requirements
visible and preserving the deterministic execution path.

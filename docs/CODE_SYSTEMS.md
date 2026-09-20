# Coding stateful software and games

UC's typed-code workflow now composes **stateful systems**, in addition to pure
functions. The same program, control graph and event contract generate standalone
JavaScript and Python implementations. Humans, AI and deterministic planners can
supply the same explicit construction data. No AI, sibling repository, package
download, Git checkout or network service is required at creation/runtime.
Creation uses the bundled Grammar/Profession packages and installed Node/Python.
Each emitted language subsequently runs on its own host runtime.

This builds reusable software/game logic and session hosts. It does not generate
an arbitrary application UI or a finished game from prose. The existing browser
arena, organ composition and product lifecycle capabilities remain separate
realization paths.

## Run the complete workflow

```sh
python tools/code_system_demo.py /tmp/code-system-proof
PYTHONPATH=src python -m axm_uc code-system examples/code-systems/inventory.json
PYTHONPATH=src python -m axm_uc create examples/creation-atlas/combat-system.json
```

The first command produces three portable examples, a discovered workflow with
two fresh builds, reusable construction collections and a proof receipt:

| Product | Authored behavior | Observed exploration |
| --- | --- | --- |
| Inventory service | Reserve, ship, cancel, restock, close/reopen; whole-number bounds and stock conservation | 64 states, 234 event checks through depth 5 |
| Combat session | Start, guarded attack, incoming damage, pause/resume, reload, victory/defeat and restart | 46 states, 245 event checks through depth 6 |
| Inventory with audit | Retrieve the accepted inventory construction from the atlas; add an audit transition using the retained identity reducer | New behavior composition, unchanged 13 reusable function atoms; prior system preserved |

The examples are editable contracts. The compiler contains no inventory or
combat implementation. Their arithmetic, conditions, records and calls are
ordinary Grammar operations. The state graph is compiled by UC's existing
`state_machine.py`; its original data-only effects contract is preserved.

The demo also removes the combat reducer's zero clamp. Its function cases and
scripted scenarios still pass. Breadth-first exploration discovers
`start → hit(4) → hit(4) → hit(4)`: health would go below zero. The attempted
transition is refused atomically, the shortest counterexample is retained, and
the defective system cannot receive successful verification or retention.

## Construction contract

`code-system` accepts `catalog`, `build`, `verify`, `retain` and `restore`.
The first three creation actions require `job` and `system`. `job` is the existing
typed-code job: `id`, explicit `program`, `cases`, `requirements`, and optional
`languages`. Every exported function still requires successful acceptance
coverage. Only `retain` accepts prior `archive` and `system_archive` values.

| System field | Contract |
| --- | --- |
| `schema` | `axm.code-system/v0.1` |
| `domain` | `software` or `game`; explicit direction metadata |
| `initial_model` | Exact initial typed record |
| `machine` | Existing `axm.deterministic-state-machine/v0.1` graph |
| `bindings` | Event names, reducer exports, optional guard and route-selector exports |
| `invariants` | Unique ids, explicit statements and boolean function exports |
| `scenarios` | Event sequences with independently authored expected status and complete state after every step; optional expected effects |
| `exploration` | Concrete event alphabet plus `max_depth`, `max_states` and `max_edges` |

An event is `{"type":"reserve","args":[3]}`. A state is
`{"phase":"open","model":{"stock":10,"reserved":0,"shipped":0,"received":10}}`.

A reducer receives the model followed by event arguments and returns the same
record type. Its optional guard has the same parameters and returns a boolean.
An invariant receives only the model and returns a boolean. The compiler checks
these bindings and adds reserved `ucSystemInitial`/`ucSystemIdentity` exports for
initialization and typed state admission. Their names are unavailable to authored
functions.

A normal event selects the graph transition with its name. A conditional binding
can instead declare `routes: {"function":"afterHit","events":["hit","defeat"]}`.
The selector receives the proposed model; its result must name an explicitly
allowed transition from the current phase. The combat example uses this to enter
defeat or victory automatically from the resulting resource values.

Refusal never partially changes the current state. Missing transitions, guard
refusals, argument errors, execution failures and attempted invariant violations
remain distinguishable. Effects are returned as data after a successful step;
the host never performs them. No clock, random source, I/O action or user-supplied
source string is hidden in the model.

## Executed specialist procedures

| Procedure | Actual operation/evidence |
| --- | --- |
| Software architect | Complete system/graph/type binding preflight, then existing requirement-to-case mapping |
| Developer tools and build | Bundled Grammar compilation in both targets, repeated-build/source identity checks |
| QA and integration | Existing fresh-process function cases, then independently assessed stateful observations |
| Game systems | `System.explore()` performs deterministic breadth-first exploration, state deduplication, invariant checks, transition coverage and shortest counterexamples |
| Stateful QA | Checks exact scenario states, refused-step preservation, repeats, language parity, replay and checkpoint recovery |
| Software maintainer | Existing function-closure retention plus additive behavior-composition archives and atlas retrieval |

These are bounded executable procedures with existing profession ownership, not
a claim that complete professional bodies or subjective judgment are solved.

Verification executes each requested language twice in fresh processes. The
Python assessor compares actual outputs with the declared oracles outside the
generated host. Every declared transition and every event binding must have been
observed successfully across the scenarios/exploration. Missing observations,
runtime failures, divergences, exhausted exploration budgets and counterexamples
return HOLD and cannot publish a verified project.

## Portable products and recovery

`code-system-project` uses the ordinary UC project writer with exactly `path` and
`request`. The destination must be new and outside machine internals. `build`
publishes a source CANDIDATE without runtime execution; `verify`/`retain` publish
only after their required checks pass. Atlas blueprints require verification.

Projects contain `request.json`, `construction.json`, `workflow.json`, source
modules, function selftests, session runtimes, exact source locks, licenses and
optional function/system archives. Generated sources remain realizations of the
retained construction.

```sh
node javascript/runtime.js verify
python python/runtime.py verify
node javascript/runtime.js replay events.json
python python/runtime.py checkpoint events.json > checkpoint.json
node javascript/runtime.js restore checkpoint.json
```

`verify` checks scenarios, exploration and recovery and returns a nonzero exit
status on failure. `observe` emits measurements for independent assessment.
The APIs expose `initial`, `step`, `replay`, `checkpoint`, `restore`, `explore`,
`observe` and `verify`. JavaScript uses `require('./runtime').load()`; Python can
load the runtime file through `importlib` or import it from its own project.
Multiple Python products can coexist without colliding on a shared `module`
import. Loading checks exact emitted source bytes before loading generated code.

Replay records refused events and continues. Checkpoints retain their explicit
event history and claimed final state, bind the program/behavior/host version,
and re-execute that history before restoring. A checkpoint produced by Python can
be restored by JavaScript and vice versa. Changed source, mismatched identities,
invalid states or inconsistent replay are refused. These checks are integrity
and compatibility evidence, not authenticated saves or an OS sandbox.

## Reusable atlas knowledge

`software-systems` and `game-systems` blueprint directions support
`session-behavior`, `invariant-exploration`, `portable-recovery` and
`retained-system` goals. See `examples/creation-atlas/*-system.json`.

Successful retained creations enter the explicitly selected experience
collection as `code-pattern` records. Retrieve a pattern's `data.request`, modify
the construction, and verify it under the new intent. An atlas parameter can use
`{"atlas":"code-pattern:<identity>","path":["request"]}` directly.

Function closures retain their existing structural deduplication. System
composition identity includes initial data, public phase/event/field names,
transitions/effects and the structural identities of reducer/guard/selector/
invariant functions. Module, function and graph labels do not create another
behavior atom. New public behavior does. Repeated retention is idempotent;
new observations are additive, and full archives hold without evicting entries.

`restore` returns construction with `REQUIRES_FRESH_EXECUTION`. Past observations
and descriptive atlas records cannot stand in for current checks. These updates
do not automatically mutate shared machine capabilities or promote canon.

## Discovery and measured goals

The installed `verify-code-system` operator connects these systems to
[workflow discovery](WORKFLOW_DISCOVERY.md). Its input type is
`code-system-request`; its output is `stateful-code-project` with `quality: checked`.
The planner finds the operator from those contracts without a supplied blueprint.
The station requires `verify` or `retain`, executes the full system workflow and
reports measured scenario, transition, exploration, language and artifact counts.

The demo requests complete declared transition coverage, two executed languages
and exploration through depth six. Discovery builds and independently rebuilds
the combat system, compares product bytes and goal measurements, then retains
the confirmed workflow structure. The emitted `discovery-request.json` is an
editable request for the ordinary `workflow-discovery` capability's `plan` and
`experiment` operations. A later request must run its checks again: requesting
depth seven cannot inherit the earlier depth-six result.

These measurements describe the scope actually checked. More states or event
checks do not imply better software, game design or statistical confidence.

## Bounds and remaining work

System requests are at most 1 MiB. The authored program can have up to 30
functions plus two host-validation functions; Grammar's existing type, data,
expression and per-call work bounds still apply. Systems allow up to 32 event
bindings/invariants/alphabet events, 64 scenarios, 128 steps per scenario and
1,024 scenario steps in total. Exploration declares depth 1..32, states 1..4,096
and edges 1..20,000. Each system observer has a 20-second timeout and an 8 MiB
output bound. Checkpoint histories are limited to 10,000 events.

`BOUNDED_COMPLETE` means all reachable states through the declared depth were
checked with the supplied concrete event alphabet. It does not quantify over
arbitrary numeric values, event timing or all possible programs. The report
retains depth/frontier, state/edge counts and observed transitions instead of
inventing a confidence score.

UI/input realization, fixed-time simulation integration, asynchronous external
effects, concurrency, multiplayer, migration of old saves, performance budgets,
game feel, visuals and sound need their own contracts and observations. This
workflow supplies reusable stateful code and evidence for those later products.

```sh
PYTHONPATH=src python -m unittest discover -s tests -p 'test_code_*.py' -v
```

CI repeats the coding tests and the full demo on Linux/Node 20/Python 3.11 and
Windows/Node 22/Python 3.13. Portable-runtime tests also unpack UC elsewhere and
create/execute a combat system without donor checkouts or the original cwd.

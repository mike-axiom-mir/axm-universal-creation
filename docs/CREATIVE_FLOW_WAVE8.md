# Creative Flow — machine-use spine (Wave 8)

Wave 8 turns the existing Creative Hands body from a callable toolbox into a first-class Universal Creation execution path.

The important boundary is unchanged: the creative capabilities belong to the machine. A human, deterministic recipe, program or AI may propose the same explicit flow plan, but no AI owns or privately implements the hands.

## Current body

At this wave the public Creative Hands service exposes:

- **314 executable creative hands**
- **321 callable creative recipes**

Creative Flow does not duplicate those implementations. It queries and invokes the existing `PlatformHands.creativeHands` service.

## Machine route

A new live capability handles:

- `creative-flow`
- `creative-hand-flow`
- `creative-tool-orchestration`

This means the existing `UniversalCreationMachine.create()` path can execute a Creative Flow without a special privileged branch in `machine.py`.

Example:

```bash
PYTHONPATH=src python -m axm_uc create examples/requests/creative_flow_mesh.json
```

JavaScript hosts can use the same machinery through:

```js
const PlatformHands = require('./capabilities/platform-hands');
PlatformHands.creativeFlow.run(request);
```

The Python live capability uses the local Node runtime through `creative-flow-bridge.js`. It requires no network access.

## V1 flow

The permanent conceptual path begins here:

```text
goal / explicit plan
        ↓
creative-hand discovery
        ↓
exact operation resolution
        ↓
dependency + state-reference compilation
        ↓
preflight
        ↓
deterministic DAG execution
        ↓
step receipts + candidate state
```

V1 intentionally stops short of pretending that arbitrary prose can already become a trustworthy full execution plan.

A prose-only `mode: plan` request returns candidate hands and:

`HOLD_PLAN_REQUIRED`

An AI can propose the exact same explicit plan format that a human, recipe or program can provide. The deterministic machine then owns validation and execution.

## Discovery

Discovery can filter or rank by:

- exact hand ID;
- family;
- operation;
- deterministic token query.

An execution selector must resolve uniquely. Equal best matches return `HOLD_AMBIGUOUS` rather than silently choosing one.

## Plan steps

Each step has exactly one operator source:

- `hand_id`
- `recipe_id`
- `selector`

A step may save its primary result into candidate state with `save_as`.

Arguments may refer to candidate state:

```json
{"$state": "mesh"}
```

or to an earlier raw step execution result:

```json
{"$ref": "step-id.result"}
```

Literal objects that would otherwise look like references can be wrapped as:

```json
{"$literal": {"$state": "not-a-reference"}}
```

## Dependency inference

Explicit `depends_on` remains supported, but callers do not need to repeat obvious state dependencies.

If step `make` saves `mesh` and step `edit` consumes `{"$state":"mesh"}`, the compiler automatically adds `make` as a dependency of `edit`.

V1 rejects:

- duplicate step IDs;
- missing dependencies;
- cycles;
- missing state producers;
- self-consumption of a step's own output;
- duplicate `save_as` names;
- overwriting caller-supplied initial state through `save_as`;
- steps that specify multiple operator sources.

## Candidate-state transaction

The supplied state is cloned before execution.

A successful flow returns:

- exact compiled plan digest;
- initial state digest;
- final candidate-state digest;
- per-step operation ID;
- dependency list;
- input digest;
- output digest;
- PASS receipt;
- final candidate state;
- optional explicitly exposed outputs.

If any hand fails, Creative Flow returns:

`HOLD_EXECUTION_FAILED`

with the successful receipts and failure evidence. It does **not** return a final candidate state and does not mutate the supplied source state.

This is candidate-state atomicity, not a claim that arbitrary future hands with external side effects can always be rolled back. Current Creative Hands are in-memory deterministic creative operations; external publication remains a separate machine boundary.

## Cross-registry proof

The Wave 8 selftest executes a real chain spanning different creative organs:

```text
mesh primitive
  → face selection
  → region extrusion
  → structural shear modifier
  → mesh bounds analysis
```

State outputs from one registry become validated inputs to another through the same Creative Flow DAG.

## Bounds

V1 limits:

- maximum 128 explicit steps;
- maximum 64 MiB encoded input request;
- local Node runtime required;
- every selected hand remains authoritative for its own parameter, schema and resource bounds.

The flow compiler currently proves structural compatibility: exact operator existence, unique selection, dependency acyclicity and state availability. It does not falsely claim a universal static type system for all 314 existing hand arguments. Runtime hand validation remains authoritative until richer accepted/produced schema metadata is added to every hand.

## What Wave 8 changes strategically

Before Wave 8:

```text
caller → knows hand ID → invoke hand
```

After Wave 8:

```text
caller / AI / recipe
        ↓
explicit shared plan contract
        ↓
Universal Creation live capability
        ↓
Creative Flow compiler/executor
        ↓
all Creative Hands registries
        ↓
candidate state + receipts
```

That is the spine later modeling, animation, rigging, UV/material, video, audio and vector waves should plug into.

## Next depth

Useful future orchestration growth includes:

- accepted/produced schema metadata for every hand;
- automatic schema-edge compatibility planning;
- cost/resource estimates;
- inspection and repair predicates;
- persistent project-state checkpoints;
- explicit undo/compensation contracts where external side effects exist;
- deterministic recipe synthesis from known subgoals;
- richer goal interpretation by optional AI without changing machine authority;
- inspection-driven loops: execute → inspect → select repair → re-run.

Wave 8 is therefore not a claim of autonomous artistic planning. It is the first real deterministic execution body that such planning can safely target.
